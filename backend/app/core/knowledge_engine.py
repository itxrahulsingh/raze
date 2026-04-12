"""
RAZE Enterprise AI OS – Knowledge Management Engine

Handles the full knowledge lifecycle:
  1. Ingestion  – PDF / DOCX / TXT / HTML / URL → raw text
  2. Chunking   – intelligent overlap-aware splitting
  3. Embedding  – batch OpenAI embeddings
  4. Storage    – PostgreSQL (KnowledgeChunk) + Qdrant vectors
  5. Search     – hybrid BM25 + vector search
  6. Approval   – admin approval / rejection workflow
  7. Deletion   – clean removal from both DB and Qdrant
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import structlog
import tiktoken
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.llm_router import LLMRouter
from app.core.vector_search import VectorPoint, VectorSearchEngine
from app.models.knowledge import (
    KnowledgeChunk,
    KnowledgeSource,
    KnowledgeSourceMode,
    KnowledgeSourceStatus,
    KnowledgeSourceType,
)

settings = get_settings()
logger = structlog.get_logger(__name__)

# ─── Tokeniser ────────────────────────────────────────────────────────────────

_ENC = tiktoken.get_encoding("cl100k_base")


def _token_count(text: str) -> int:
    return len(_ENC.encode(text))


# ─── Text extractors ──────────────────────────────────────────────────────────

async def _extract_pdf(data: bytes) -> str:
    """Extract plain text from a PDF binary."""
    try:
        import pypdf

        reader = pypdf.PdfReader(io.BytesIO(data))
        parts: list[str] = []
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                parts.append(extracted)
        return "\n\n".join(parts)
    except ImportError:
        try:
            from pdfminer.high_level import extract_text as pdfminer_extract
            return await asyncio.to_thread(pdfminer_extract, io.BytesIO(data))
        except ImportError:
            raise RuntimeError("Neither pypdf nor pdfminer is installed; cannot parse PDF")


async def _extract_docx(data: bytes) -> str:
    """Extract plain text from a DOCX binary."""
    try:
        import docx

        doc = docx.Document(io.BytesIO(data))
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except ImportError:
        raise RuntimeError("python-docx is not installed; cannot parse DOCX")


async def _extract_html(data: bytes) -> str:
    """Strip HTML tags and return readable text."""
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(data, "html.parser")
        # Remove script/style noise
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)
    except ImportError:
        # Naive fallback
        import re
        text = data.decode("utf-8", errors="replace")
        return re.sub(r"<[^>]+>", " ", text)


async def _extract_text_from_bytes(data: bytes, file_type: str) -> str:
    """Dispatch extraction based on file type."""
    ft = file_type.lower().lstrip(".")
    if ft == "pdf":
        return await _extract_pdf(data)
    elif ft == "docx":
        return await _extract_docx(data)
    elif ft in ("html", "htm"):
        return await _extract_html(data)
    elif ft in ("txt", "md", "csv", "json"):
        return data.decode("utf-8", errors="replace")
    else:
        # Best-effort UTF-8 decode
        return data.decode("utf-8", errors="replace")


# ─── KnowledgeEngine ─────────────────────────────────────────────────────────

class KnowledgeEngine:
    """
    Manages the full knowledge lifecycle for RAZE.

    Parameters
    ----------
    db          : SQLAlchemy async session
    llm_router  : LLMRouter instance (used for embeddings)
    vector_search: VectorSearchEngine instance
    """

    def __init__(
        self,
        db: AsyncSession,
        llm_router: LLMRouter,
        vector_search: VectorSearchEngine,
    ) -> None:
        self._db = db
        self._llm = llm_router
        self._vs = vector_search

    # ── Ingestion ─────────────────────────────────────────────────────────────

    async def ingest_file(
        self,
        file_path: str | Path,
        source_id: str | uuid.UUID,
        mode: str = KnowledgeSourceMode.persistent.value,
    ) -> dict[str, Any]:
        """
        Ingest a local file into the knowledge base.

        Steps: read → compute hash → check dedup → extract text →
               chunk → embed → store → update source record.

        Returns a summary dict with chunk_count, token_count, etc.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        data = path.read_bytes()
        content_hash = hashlib.sha256(data).hexdigest()
        file_type = path.suffix.lstrip(".")

        # Deduplication check
        existing = await self._db.execute(
            select(KnowledgeSource).where(KnowledgeSource.content_hash == content_hash)
        )
        if existing.scalar_one_or_none():
            logger.info("knowledge_ingest_duplicate", hash=content_hash)
            return {"status": "duplicate", "content_hash": content_hash}

        # Update source to processing status
        await self._update_source_status(source_id, KnowledgeSourceStatus.processing.value)

        try:
            text = await _extract_text_from_bytes(data, file_type)
            return await self._process_text(
                text=text,
                source_id=source_id,
                content_hash=content_hash,
                file_size=len(data),
                mime_type=f"application/{file_type}",
                source_type=file_type,
            )
        except Exception as exc:
            await self._update_source_status(
                source_id, KnowledgeSourceStatus.failed.value, error=str(exc)
            )
            logger.error("knowledge_ingest_failed", source_id=str(source_id), error=str(exc))
            raise

    async def ingest_url(
        self,
        url: str,
        source_id: str | uuid.UUID,
        mode: str = KnowledgeSourceMode.linked.value,
    ) -> dict[str, Any]:
        """
        Fetch a URL and ingest its content into the knowledge base.
        """
        await self._update_source_status(source_id, KnowledgeSourceStatus.processing.value)
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()

            data = response.content
            content_hash = hashlib.sha256(data).hexdigest()
            content_type = response.headers.get("content-type", "text/html").split(";")[0]
            file_type = "html"
            if "pdf" in content_type:
                file_type = "pdf"
            elif "plain" in content_type:
                file_type = "txt"

            # Deduplication
            existing = await self._db.execute(
                select(KnowledgeSource).where(KnowledgeSource.content_hash == content_hash)
            )
            if existing.scalar_one_or_none():
                return {"status": "duplicate", "content_hash": content_hash}

            text = await _extract_text_from_bytes(data, file_type)
            return await self._process_text(
                text=text,
                source_id=source_id,
                content_hash=content_hash,
                file_size=len(data),
                mime_type=content_type,
                source_type="url",
            )
        except Exception as exc:
            await self._update_source_status(
                source_id, KnowledgeSourceStatus.failed.value, error=str(exc)
            )
            logger.error("knowledge_url_ingest_failed", url=url, error=str(exc))
            raise

    # ── Text processing pipeline ──────────────────────────────────────────────

    async def _process_text(
        self,
        text: str,
        source_id: str | uuid.UUID,
        content_hash: str,
        file_size: int,
        mime_type: str,
        source_type: str,
    ) -> dict[str, Any]:
        """Shared pipeline: chunk → embed → store → update source."""
        chunks = self.chunk_text(
            text,
            chunk_size=settings.chunk_size,
            overlap=settings.chunk_overlap,
        )
        if not chunks:
            raise ValueError("No text content extracted from source")

        embeddings = await self.embed_chunks(chunks)
        await self.store_chunks(source_id, chunks, embeddings)

        total_tokens = sum(_token_count(c) for c in chunks)

        # Update source record
        await self._db.execute(
            update(KnowledgeSource)
            .where(KnowledgeSource.id == source_id)
            .values(
                status=KnowledgeSourceStatus.pending.value,  # pending admin approval
                chunk_count=len(chunks),
                content_hash=content_hash,
                file_size=file_size,
                mime_type=mime_type,
                embedding_model=settings.openai_embedding_model,
                processed_at=datetime.now(timezone.utc),
                processing_error=None,
            )
        )
        await self._db.commit()

        logger.info(
            "knowledge_ingest_complete",
            source_id=str(source_id),
            chunks=len(chunks),
            tokens=total_tokens,
        )
        return {
            "status": "processed",
            "chunk_count": len(chunks),
            "total_tokens": total_tokens,
            "content_hash": content_hash,
        }

    def chunk_text(
        self,
        text: str,
        chunk_size: int = 1000,
        overlap: int = 200,
    ) -> list[str]:
        """
        Split *text* into overlapping token-aware chunks.

        Uses tiktoken for token counting so chunks respect the LLM context
        budget.  Splits on sentence/paragraph boundaries where possible.
        """
        if not text.strip():
            return []

        # Paragraph-aware splitting: prefer splitting at blank lines
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks: list[str] = []
        current_tokens: list[str] = []
        current_count = 0

        for para in paragraphs:
            para_tokens = _ENC.encode(para)
            para_count = len(para_tokens)

            if para_count > chunk_size:
                # Paragraph itself is too large – split it by tokens
                if current_tokens:
                    chunks.append(_ENC.decode(current_tokens))
                    current_tokens = []
                    current_count = 0

                for i in range(0, para_count, chunk_size - overlap):
                    slice_tokens = para_tokens[i : i + chunk_size]
                    chunks.append(_ENC.decode(slice_tokens))
            elif current_count + para_count > chunk_size:
                # Flush current buffer
                if current_tokens:
                    chunks.append(_ENC.decode(current_tokens))
                # Start new chunk with overlap from end of previous
                overlap_tokens = current_tokens[-overlap:] if overlap else []
                current_tokens = overlap_tokens + list(para_tokens)
                current_count = len(current_tokens)
            else:
                current_tokens.extend(para_tokens)
                current_count += para_count

        if current_tokens:
            chunks.append(_ENC.decode(current_tokens))

        return [c for c in chunks if c.strip()]

    async def embed_chunks(self, chunks: list[str]) -> list[list[float]]:
        """
        Generate embeddings for all chunks in parallel batches.
        Uses OpenAI batch limit of 2048 items / call.
        """
        BATCH = 100
        embeddings: list[list[float]] = []

        for i in range(0, len(chunks), BATCH):
            batch = chunks[i : i + BATCH]
            tasks = [self._llm.generate_embedding(chunk) for chunk in batch]
            batch_embeddings = await asyncio.gather(*tasks)
            embeddings.extend(batch_embeddings)

        return embeddings

    async def store_chunks(
        self,
        source_id: str | uuid.UUID,
        chunks: list[str],
        embeddings: list[list[float]],
    ) -> None:
        """
        Persist chunks to PostgreSQL (KnowledgeChunk) and upsert vectors to Qdrant.
        """
        sid = uuid.UUID(str(source_id)) if isinstance(source_id, str) else source_id

        # Delete any existing chunks for this source (re-ingestion)
        await self._db.execute(
            delete(KnowledgeChunk).where(KnowledgeChunk.source_id == sid)
        )

        chunk_records: list[KnowledgeChunk] = []
        vector_points: list[VectorPoint] = []

        for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = uuid.uuid4()
            token_count = _token_count(chunk_text)

            chunk_record = KnowledgeChunk(
                id=chunk_id,
                source_id=sid,
                content=chunk_text,
                chunk_index=idx,
                token_count=token_count,
                embedding=embedding,
                chunk_metadata={"chunk_index": idx, "token_count": token_count},
            )
            chunk_records.append(chunk_record)

            vector_points.append(
                VectorPoint(
                    id=str(chunk_id),
                    vector=embedding,
                    payload={
                        "source_id": str(sid),
                        "chunk_index": idx,
                        "content": chunk_text[:500],  # truncated for Qdrant payload
                        "token_count": token_count,
                    },
                )
            )

        self._db.add_all(chunk_records)
        await self._db.flush()

        # Upsert to Qdrant
        try:
            await self._vs.upsert_vectors(
                settings.qdrant_collection_knowledge, vector_points
            )
        except Exception as exc:
            logger.warning("qdrant_upsert_failed_continuing", error=str(exc))
            # Non-fatal: DB records are the source of truth; Qdrant can be re-synced

    # ── Search ────────────────────────────────────────────────────────────────

    async def search_knowledge(
        self,
        query: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
        score_threshold: float = 0.3,
        approved_only: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Hybrid semantic + keyword search over the knowledge base.

        Returns a list of enriched result dicts with chunk content and source metadata.
        """
        query_embedding = await self._llm.generate_embedding(query)

        # Qdrant hybrid search
        try:
            qdrant_filters = dict(filters) if filters else {}
            results = await self._vs.hybrid_search(
                collection=settings.qdrant_collection_knowledge,
                query_text=query,
                query_embedding=query_embedding,
                top_k=top_k,
                filters=qdrant_filters,
            )
        except Exception as exc:
            logger.warning("qdrant_search_failed_fallback", error=str(exc))
            # pgvector fallback
            from app.core.vector_search import pgvector_search_raw
            results = await pgvector_search_raw(
                session=self._db,
                table_name="knowledge_chunks",
                query_embedding=query_embedding,
                top_k=top_k,
                extra_where="embedding IS NOT NULL",
            )

        if not results:
            return []

        # Load full chunk content + source info from DB
        chunk_ids = [uuid.UUID(r.id) for r in results if _is_valid_uuid(r.id)]
        if not chunk_ids:
            return []

        chunks_result = await self._db.execute(
            select(KnowledgeChunk, KnowledgeSource)
            .join(KnowledgeSource, KnowledgeChunk.source_id == KnowledgeSource.id)
            .where(
                KnowledgeChunk.id.in_(chunk_ids),
                *(
                    [KnowledgeSource.status == KnowledgeSourceStatus.approved.value]
                    if approved_only
                    else []
                ),
            )
        )
        rows = chunks_result.all()

        # Score map for ordering
        score_map = {r.id: r.score for r in results}

        enriched: list[dict[str, Any]] = []
        for chunk, source in rows:
            score = score_map.get(str(chunk.id), 0.0)
            if score < score_threshold:
                continue
            enriched.append(
                {
                    "chunk_id": str(chunk.id),
                    "source_id": str(source.id),
                    "source_name": source.name,
                    "source_type": source.type,
                    "content": chunk.content,
                    "chunk_index": chunk.chunk_index,
                    "score": score,
                    "token_count": chunk.token_count,
                    "tags": source.tags,
                }
            )

        # Sort by score descending
        enriched.sort(key=lambda x: -x["score"])
        return enriched[:top_k]

    # ── Approval workflow ─────────────────────────────────────────────────────

    async def approve_source(
        self, source_id: str | uuid.UUID, admin_id: str | uuid.UUID
    ) -> None:
        """Mark a knowledge source as approved and activate its chunks in search."""
        sid = uuid.UUID(str(source_id)) if isinstance(source_id, str) else source_id
        aid = uuid.UUID(str(admin_id)) if isinstance(admin_id, str) else admin_id

        await self._db.execute(
            update(KnowledgeSource)
            .where(KnowledgeSource.id == sid)
            .values(
                status=KnowledgeSourceStatus.approved.value,
                approved_by=aid,
                approved_at=datetime.now(timezone.utc),
                is_active=True,
                rejection_reason=None,
            )
        )
        await self._db.commit()
        logger.info("knowledge_source_approved", source_id=str(sid), admin_id=str(aid))

    async def reject_source(
        self,
        source_id: str | uuid.UUID,
        admin_id: str | uuid.UUID,
        reason: str,
    ) -> None:
        """Mark a source as rejected and deactivate it from search."""
        sid = uuid.UUID(str(source_id)) if isinstance(source_id, str) else source_id

        await self._db.execute(
            update(KnowledgeSource)
            .where(KnowledgeSource.id == sid)
            .values(
                status=KnowledgeSourceStatus.rejected.value,
                rejection_reason=reason,
                is_active=False,
            )
        )
        await self._db.commit()
        logger.info("knowledge_source_rejected", source_id=str(sid), reason=reason)

    # ── Deletion ──────────────────────────────────────────────────────────────

    async def delete_source(self, source_id: str | uuid.UUID) -> None:
        """
        Remove a knowledge source and all its chunks from PostgreSQL and Qdrant.
        """
        sid = uuid.UUID(str(source_id)) if isinstance(source_id, str) else source_id

        # Collect chunk IDs for Qdrant deletion
        chunks_result = await self._db.execute(
            select(KnowledgeChunk.id).where(KnowledgeChunk.source_id == sid)
        )
        chunk_ids = [str(row[0]) for row in chunks_result.all()]

        # DB cascade will delete chunks when source is deleted
        await self._db.execute(
            delete(KnowledgeSource).where(KnowledgeSource.id == sid)
        )
        await self._db.commit()

        # Qdrant cleanup (best-effort)
        if chunk_ids:
            try:
                await self._vs.delete_vectors(
                    settings.qdrant_collection_knowledge, chunk_ids
                )
            except Exception as exc:
                logger.warning("qdrant_delete_failed", source_id=str(sid), error=str(exc))

        logger.info("knowledge_source_deleted", source_id=str(sid), chunks=len(chunk_ids))

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _update_source_status(
        self,
        source_id: str | uuid.UUID,
        status: str,
        error: str | None = None,
    ) -> None:
        sid = uuid.UUID(str(source_id)) if isinstance(source_id, str) else source_id
        values: dict[str, Any] = {"status": status}
        if error:
            values["processing_error"] = error
        await self._db.execute(
            update(KnowledgeSource).where(KnowledgeSource.id == sid).values(**values)
        )
        await self._db.commit()


def _is_valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False
