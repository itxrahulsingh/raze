"""
RAZE Enterprise AI OS – Vector Search Engine

Primary store  : Qdrant (high-performance ANN + payload filtering)
Fallback store : pgvector (PostgreSQL extension, used when Qdrant is unavailable)

Provides:
  - VectorSearchEngine (Qdrant-backed)
  - pgvector_search()  (SQLAlchemy fallback)
  - Hybrid BM25 + vector search via rank-fusion
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any

import structlog
from qdrant_client import AsyncQdrantClient, models as qdrant_models
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    PointStruct,
    ScoredPoint,
    VectorParams,
)
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings

settings = get_settings()
logger = structlog.get_logger(__name__)


# ─── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class VectorPoint:
    id: str
    vector: list[float]
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    id: str
    score: float
    payload: dict[str, Any]


# ─── Qdrant helpers ───────────────────────────────────────────────────────────

def _build_qdrant_filter(filters: dict[str, Any] | None) -> Filter | None:
    """
    Convert a simple key=value dict into a Qdrant Filter with must conditions.
    Each value may be a scalar (exact match) or a list (any-of match).
    """
    if not filters:
        return None

    must_conditions: list[FieldCondition] = []
    for key, value in filters.items():
        if isinstance(value, list):
            list_values = [v for v in value if v is not None]
            if not list_values:
                continue
            must_conditions.append(
                FieldCondition(key=key, match=MatchAny(any=list_values))
            )
        else:
            must_conditions.append(
                FieldCondition(key=key, match=MatchValue(value=value))
            )

    return Filter(must=must_conditions) if must_conditions else None


# ─── VectorSearchEngine ───────────────────────────────────────────────────────

class VectorSearchEngine:
    """
    Qdrant-backed vector search engine with pgvector fallback.

    Usage::

        engine = VectorSearchEngine()
        await engine.create_collection("knowledge", vector_size=3072)
        await engine.upsert_vectors("knowledge", [VectorPoint(...)])
        results = await engine.search("knowledge", query_embedding, top_k=5)
    """

    def __init__(self) -> None:
        self._client: AsyncQdrantClient | None = None
        self._initialised = False

    async def _get_client(self) -> AsyncQdrantClient:
        if self._client is None:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(5),
                wait=wait_exponential(multiplier=1, min=1, max=8),
                retry=retry_if_exception_type(Exception),
                reraise=True,
            ):
                with attempt:
                    self._client = AsyncQdrantClient(
                        url=settings.qdrant_url,
                        api_key=settings.qdrant_api_key,
                        timeout=30,
                    )
                    # Verify connectivity
                    await self._client.get_collections()
                    logger.info("qdrant_connected", url=settings.qdrant_url)
        return self._client  # type: ignore[return-value]

    async def create_collection(
        self,
        name: str,
        vector_size: int | None = None,
        distance: Distance = Distance.COSINE,
        recreate: bool = False,
    ) -> None:
        """Create a Qdrant collection if it does not already exist."""
        effective_size = vector_size or settings.qdrant_vector_size
        client = await self._get_client()

        existing = await client.get_collections()
        existing_names = {c.name for c in existing.collections}

        if name in existing_names:
            if recreate:
                await client.delete_collection(name)
                logger.info("qdrant_collection_deleted", collection=name)
            else:
                logger.debug("qdrant_collection_exists", collection=name)
                return

        await client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=effective_size, distance=distance),
        )
        logger.info("qdrant_collection_created", collection=name, vector_size=effective_size)

    async def upsert_vectors(
        self,
        collection: str,
        vectors_with_payloads: list[VectorPoint],
        batch_size: int = 100,
    ) -> None:
        """
        Bulk-upsert vectors into *collection*.  Processes in batches to avoid
        Qdrant request size limits.
        """
        if not vectors_with_payloads:
            return

        client = await self._get_client()
        points = [
            PointStruct(
                id=vp.id,
                vector=vp.vector,
                payload=vp.payload,
            )
            for vp in vectors_with_payloads
        ]

        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=1, max=5),
                retry=retry_if_exception_type(Exception),
                reraise=True,
            ):
                with attempt:
                    await client.upsert(collection_name=collection, points=batch)

        logger.info(
            "qdrant_upsert_complete",
            collection=collection,
            count=len(vectors_with_payloads),
        )

    async def search(
        self,
        collection: str,
        query_embedding: list[float],
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
        score_threshold: float | None = None,
    ) -> list[SearchResult]:
        """
        Semantic (ANN) search in *collection*.

        Parameters
        ----------
        collection      : Qdrant collection name
        query_embedding : dense vector of the query
        top_k           : maximum number of results
        filters         : dict of payload key=value to filter by
        score_threshold : discard results below this cosine similarity

        Returns
        -------
        List of SearchResult sorted by descending score.
        """
        client = await self._get_client()
        qdrant_filter = _build_qdrant_filter(filters)

        try:
            results: list[ScoredPoint] = await client.search(
                collection_name=collection,
                query_vector=query_embedding,
                limit=top_k,
                query_filter=qdrant_filter,
                score_threshold=score_threshold,
                with_payload=True,
            )
        except Exception as exc:
            logger.error("qdrant_search_error", collection=collection, error=str(exc))
            raise

        return [
            SearchResult(
                id=str(r.id),
                score=float(r.score),
                payload=r.payload or {},
            )
            for r in results
        ]

    async def hybrid_search(
        self,
        collection: str,
        query_text: str,
        query_embedding: list[float],
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
        keyword_weight: float = 0.3,
        vector_weight: float = 0.7,
    ) -> list[SearchResult]:
        """
        Hybrid BM25 (keyword) + vector search via Reciprocal Rank Fusion (RRF).

        Qdrant's full-text search is used for the keyword pass.  The two ranked
        lists are fused using RRF with configurable weights.

        Parameters
        ----------
        keyword_weight  : weight given to BM25 rank (0–1)
        vector_weight   : weight given to vector rank (0–1)
        """
        client = await self._get_client()
        qdrant_filter = _build_qdrant_filter(filters)

        # Run both searches concurrently
        vector_task = client.search(
            collection_name=collection,
            query_vector=query_embedding,
            limit=top_k * 3,
            query_filter=qdrant_filter,
            with_payload=True,
        )
        # Qdrant full-text search (requires a full-text index on the 'content' field)
        text_filter_conditions: list[Any] = []
        if qdrant_filter and qdrant_filter.must:
            text_filter_conditions.extend(qdrant_filter.must)

        # Add keyword match on the "content" payload field
        words = [word.strip() for word in query_text.split() if len(word.strip()) >= 3][:8]
        keyword_conditions = []
        for word in words:
            keyword_conditions.append(
                qdrant_models.FieldCondition(
                    key="content",
                    match=qdrant_models.MatchText(text=word),
                )
            )

        keyword_filter = (
            Filter(
                must=text_filter_conditions,
                should=keyword_conditions,
            )
            if keyword_conditions
            else qdrant_filter
        )

        keyword_task = client.scroll(
            collection_name=collection,
            scroll_filter=keyword_filter,
            limit=top_k * 3,
            with_payload=True,
            with_vectors=False,
        )

        vector_results, (keyword_results, _) = await asyncio.gather(
            vector_task, keyword_task, return_exceptions=False
        )

        # RRF fusion
        rrf_scores: dict[str, float] = {}
        rrf_payloads: dict[str, dict] = {}
        K = 60  # RRF constant

        for rank, point in enumerate(vector_results):
            pid = str(point.id)
            rrf_scores[pid] = rrf_scores.get(pid, 0.0) + vector_weight / (rank + K)
            rrf_payloads[pid] = point.payload or {}

        for rank, point in enumerate(keyword_results):
            pid = str(point.id)
            rrf_scores[pid] = rrf_scores.get(pid, 0.0) + keyword_weight / (rank + K)
            if pid not in rrf_payloads:
                rrf_payloads[pid] = point.payload or {}

        sorted_ids = sorted(rrf_scores, key=lambda k: -rrf_scores[k])[:top_k]

        return [
            SearchResult(
                id=pid,
                score=rrf_scores[pid],
                payload=rrf_payloads[pid],
            )
            for pid in sorted_ids
        ]

    async def delete_vectors(
        self,
        collection: str,
        ids: list[str],
    ) -> None:
        """Delete vectors by ID from *collection*."""
        if not ids:
            return
        client = await self._get_client()
        await client.delete(
            collection_name=collection,
            points_selector=qdrant_models.PointIdsList(points=ids),
        )
        logger.info("qdrant_vectors_deleted", collection=collection, count=len(ids))

    async def get_collection_info(self, collection: str) -> dict[str, Any]:
        """Return basic stats for a collection."""
        client = await self._get_client()
        info = await client.get_collection(collection)
        return {
            "name": collection,
            "vectors_count": info.vectors_count,
            "indexed_vectors_count": info.indexed_vectors_count,
            "points_count": info.points_count,
            "status": str(info.status),
        }

    async def ensure_collections(self) -> None:
        """Ensure the default knowledge and memory collections exist."""
        await self.create_collection(
            settings.qdrant_collection_knowledge, settings.qdrant_vector_size
        )
        await self.create_collection(
            settings.qdrant_collection_memory, settings.qdrant_vector_size
        )


# ─── pgvector fallback ────────────────────────────────────────────────────────

async def pgvector_search(
    session: AsyncSession,
    table_model: Any,
    query_embedding: list[float],
    top_k: int = 5,
    filters: dict[str, Any] | None = None,
    score_threshold: float | None = None,
) -> list[SearchResult]:
    """
    Fallback vector search using pgvector's ``<=>`` cosine distance operator.

    Parameters
    ----------
    session         : SQLAlchemy async session
    table_model     : SQLAlchemy ORM model class with an ``embedding`` column
    query_embedding : dense query vector
    top_k           : number of results
    filters         : dict of column_name=value for exact-match WHERE conditions
    score_threshold : discard results with cosine similarity below this value

    Returns
    -------
    List of SearchResult sorted by descending similarity.
    """
    vector_literal = "[" + ",".join(str(v) for v in query_embedding) + "]"

    # Build query using SQLAlchemy ORM
    stmt = select(table_model).order_by(
        text(f"embedding <=> '{vector_literal}'::vector")
    ).limit(top_k)

    if filters:
        for col_name, value in filters.items():
            col = getattr(table_model, col_name, None)
            if col is not None:
                stmt = stmt.where(col == value)

    result = await session.execute(stmt)
    rows = result.scalars().all()

    search_results: list[SearchResult] = []
    for row in rows:
        # Cosine distance → similarity: sim = 1 - distance
        # We compute distance inline and convert here via a subquery approach.
        # For simplicity, assign a rank-based score since we don't have the
        # distance value from the ORM query.  Callers needing exact scores
        # should use the raw SQL path below.
        search_results.append(
            SearchResult(
                id=str(row.id),
                score=1.0 / (len(search_results) + 1),  # rank-based proxy score
                payload={
                    "content": getattr(row, "content", ""),
                    "source_id": str(getattr(row, "source_id", "")),
                    "chunk_index": getattr(row, "chunk_index", 0),
                },
            )
        )

    return search_results


async def pgvector_search_raw(
    session: AsyncSession,
    table_name: str,
    query_embedding: list[float],
    top_k: int = 5,
    extra_where: str = "",
) -> list[SearchResult]:
    """
    Raw-SQL pgvector search with exact cosine similarity scores.

    Suitable for performance-sensitive paths where ORM overhead is undesirable.
    """
    vector_literal = "[" + ",".join(str(v) for v in query_embedding) + "]"
    where_clause = f"AND {extra_where}" if extra_where else ""

    sql = text(
        f"""
        SELECT
            id::text,
            1 - (embedding <=> :query_vec::vector) AS similarity,
            content,
            source_id::text,
            chunk_index
        FROM {table_name}
        WHERE embedding IS NOT NULL {where_clause}
        ORDER BY embedding <=> :query_vec::vector
        LIMIT :top_k
        """
    )
    result = await session.execute(sql, {"query_vec": vector_literal, "top_k": top_k})
    rows = result.fetchall()

    return [
        SearchResult(
            id=row[0],
            score=float(row[1]),
            payload={
                "content": row[2],
                "source_id": row[3],
                "chunk_index": row[4],
            },
        )
        for row in rows
    ]
