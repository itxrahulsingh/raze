"""
RAZE Enterprise AI OS – Knowledge Management Routes

Covers:
  POST   /knowledge/sources                   – upload file or submit URL
  GET    /knowledge/sources                   – list sources (with status filter)
  GET    /knowledge/sources/{id}              – source detail + chunk count
  DELETE /knowledge/sources/{id}             – delete source + all chunks
  PUT    /knowledge/sources/{id}/approve      – approve pending source
  PUT    /knowledge/sources/{id}/reject       – reject with reason
  POST   /knowledge/sources/{id}/reprocess    – re-ingest a source
  POST   /knowledge/search                    – semantic search
  GET    /knowledge/sources/{id}/chunks       – list chunks (paginated)
  PUT    /knowledge/chunks/{id}               – edit chunk content
  DELETE /knowledge/chunks/{id}              – delete specific chunk
"""

from __future__ import annotations

import hashlib
import io
import time
import uuid
from datetime import UTC, datetime

import structlog
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.knowledge import (
    KnowledgeChunk,
    KnowledgeSource,
    KnowledgeSourceMode,
    KnowledgeSourceStatus,
    KnowledgeSourceType,
)
from app.models.user import User
from app.schemas.knowledge import (
    KnowledgeChunkListResponse,
    KnowledgeChunkResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeSearchResult,
    KnowledgeSourceCreate,
    KnowledgeSourceListResponse,
    KnowledgeSourceResponse,
)
from app.core.security import get_current_admin, get_current_user

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/knowledge", tags=["Knowledge"])

_ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/html",
    "text/csv",
    "application/json",
    "text/markdown",
}


# ─── Upload Helpers ───────────────────────────────────────────────────────────


def _compute_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def _store_file(file_bytes: bytes, object_name: str, content_type: str) -> str:
    """
    Save file bytes using the configured storage backend.

    Returns the storage path string (used later for retrieval during processing).
    """
    settings = get_settings()

    if settings.storage_backend == "local":
        import os
        base = settings.local_storage_path
        full_path = os.path.join(base, object_name)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        await asyncio.to_thread(_write_file_sync, full_path, file_bytes)
        return f"local:{full_path}"

    # Default: MinIO / S3
    try:
        from minio import Minio  # type: ignore[import]

        def _upload() -> str:
            client = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
            )
            bucket = settings.minio_bucket_documents
            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)
            client.put_object(
                bucket,
                object_name,
                io.BytesIO(file_bytes),
                length=len(file_bytes),
                content_type=content_type,
            )
            return f"minio:{bucket}/{object_name}"

        return await asyncio.to_thread(_upload)
    except Exception as exc:
        logger.warning("knowledge.minio_upload_failed_falling_back_to_local", error=str(exc))
        import os
        base = settings.local_storage_path
        full_path = os.path.join(base, object_name)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        await asyncio.to_thread(_write_file_sync, full_path, file_bytes)
        return f"local:{full_path}"


def _write_file_sync(path: str, data: bytes) -> None:
    with open(path, "wb") as f:
        f.write(data)


async def _read_stored_file(file_path: str) -> bytes:
    """Read file bytes back from MinIO or local storage."""
    settings = get_settings()

    if file_path.startswith("local:"):
        actual_path = file_path[len("local:"):]
        return await asyncio.to_thread(_read_file_sync, actual_path)

    if file_path.startswith("minio:"):
        path_part = file_path[len("minio:"):]
        bucket, *rest = path_part.split("/", 1)
        object_name = rest[0] if rest else path_part

        def _download() -> bytes:
            from minio import Minio  # type: ignore[import]
            client = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
            )
            response = client.get_object(bucket, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data

        return await asyncio.to_thread(_download)

    # Legacy paths without prefix
    if "/" in file_path and not file_path.startswith("/"):
        # Old minio format: "bucket/object"
        bucket, *rest = file_path.split("/", 1)
        object_name = rest[0] if rest else file_path

        def _download_legacy() -> bytes:
            from minio import Minio  # type: ignore[import]
            client = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
            )
            response = client.get_object(bucket, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data

        return await asyncio.to_thread(_download_legacy)

    return await asyncio.to_thread(_read_file_sync, file_path)


def _read_file_sync(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


async def _process_knowledge_source_bg(source_id: uuid.UUID) -> None:
    """
    Background task: ingest a knowledge source into the vector store.

    Creates a fresh DB session (cannot reuse request session after response).
    """
    from app.database import AsyncSessionLocal
    from app.core.knowledge_engine import KnowledgeEngine
    from app.core.llm_router import LLMRouter
    from app.core.vector_search import VectorSearchEngine

    logger.info("knowledge.bg_processing_start", source_id=str(source_id))

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(KnowledgeSource).where(KnowledgeSource.id == source_id)
            )
            source = result.scalar_one_or_none()
            if not source:
                logger.error("knowledge.bg_source_not_found", source_id=str(source_id))
                return

            llm = LLMRouter()
            vs = VectorSearchEngine()
            engine = KnowledgeEngine(db, llm, vs)

            if source.url:
                await engine.ingest_url(source.url, source_id)
            elif source.file_path:
                file_bytes = await _read_stored_file(source.file_path)
                # Determine extension from mime_type or file_path
                ext = "txt"
                if source.mime_type:
                    mt = source.mime_type
                    if "pdf" in mt:
                        ext = "pdf"
                    elif "word" in mt or "docx" in mt:
                        ext = "docx"
                    elif "html" in mt:
                        ext = "html"
                    elif "csv" in mt:
                        ext = "csv"
                    elif "json" in mt:
                        ext = "json"
                # Write to temp file for KnowledgeEngine
                import tempfile, os
                suffix = f".{ext}"
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    tmp.write(file_bytes)
                    tmp_path = tmp.name
                try:
                    await engine.ingest_file(tmp_path, source_id)
                finally:
                    os.unlink(tmp_path)
            else:
                logger.error("knowledge.bg_no_source_data", source_id=str(source_id))

            logger.info("knowledge.bg_processing_complete", source_id=str(source_id))
        except Exception as exc:
            logger.error("knowledge.bg_processing_error", source_id=str(source_id), error=str(exc))
            await db.execute(
                update(KnowledgeSource)
                .where(KnowledgeSource.id == source_id)
                .values(status=KnowledgeSourceStatus.failed.value, processing_error=str(exc)[:2000])
            )
            await db.commit()


async def _trigger_processing(source_id: uuid.UUID) -> None:
    """Dispatch processing to background (fire-and-forget)."""
    asyncio.create_task(_process_knowledge_source_bg(source_id))


# ─── POST /knowledge/sources ─────────────────────────────────────────────────


@router.post(
    "/sources",
    response_model=KnowledgeSourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload file or submit URL for ingestion",
)
async def create_knowledge_source(
    background_tasks: BackgroundTasks,
    # File upload (optional – one of file/url is required)
    file: UploadFile | None = File(default=None),
    # Form fields
    name: str = Form(..., min_length=1, max_length=512),
    description: str | None = Form(default=None),
    source_type: KnowledgeSourceType = Form(default=KnowledgeSourceType.txt),
    url: str | None = Form(default=None),
    tags: str = Form(default=""),
    auto_approve: bool = Form(default=False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeSourceResponse:
    """
    Accept a file upload (multipart/form-data) or a URL.
    The source is queued for background ingestion immediately after creation.

    ``auto_approve`` requires admin role.
    """
    settings = get_settings()

    if file is None and url is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either a file upload or a URL must be provided",
        )

    # Validate auto_approve permission
    is_admin = current_user.role in ("admin", "superadmin")
    if auto_approve and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="auto_approve requires admin role",
        )

    parsed_tags = [t.strip().lower() for t in tags.split(",") if t.strip()] if tags else []

    file_path: str | None = None
    file_size: int | None = None
    mime_type: str | None = None
    content_hash: str | None = None
    mode = KnowledgeSourceMode.persistent

    if file is not None:
        file_bytes = await file.read()
        if len(file_bytes) > settings.max_file_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum size of {settings.max_file_size_mb} MB",
            )

        content_hash = _compute_hash(file_bytes)

        # Check for duplicate
        existing = await db.execute(
            select(KnowledgeSource).where(KnowledgeSource.content_hash == content_hash)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A source with identical content already exists",
            )

        mime_type = file.content_type or "application/octet-stream"
        file_size = len(file_bytes)
        object_name = f"sources/{current_user.id}/{content_hash}/{file.filename}"
        file_path = await _save_to_minio(file_bytes, object_name, mime_type)

    elif url:
        mode = KnowledgeSourceMode.linked
        source_type = KnowledgeSourceType.url

    initial_status = (
        KnowledgeSourceStatus.approved if auto_approve else KnowledgeSourceStatus.pending
    )
    approved_by = current_user.id if auto_approve else None
    approved_at = datetime.now(UTC) if auto_approve else None

    source = KnowledgeSource(
        name=name,
        description=description,
        type=source_type.value,
        status=initial_status.value,
        mode=mode.value,
        file_path=file_path,
        url=url,
        file_size=file_size,
        mime_type=mime_type,
        content_hash=content_hash,
        tags=parsed_tags,
        approved_by=approved_by,
        approved_at=approved_at,
        is_active=True,
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)

    # Queue background processing for approved sources
    if source.status == KnowledgeSourceStatus.approved.value:
        background_tasks.add_task(_trigger_processing, source.id)

    logger.info(
        "knowledge.source_created",
        source_id=str(source.id),
        name=name,
        status=source.status,
    )
    return KnowledgeSourceResponse.model_validate(source)


# ─── GET /knowledge/sources ───────────────────────────────────────────────────


@router.get(
    "/sources",
    response_model=KnowledgeSourceListResponse,
    summary="List knowledge sources",
)
async def list_sources(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: KnowledgeSourceStatus | None = Query(default=None, alias="status"),
    source_type: KnowledgeSourceType | None = Query(default=None, alias="type"),
    tag: str | None = Query(default=None, max_length=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeSourceListResponse:
    """Return a paginated list of knowledge sources with optional filters."""
    q = select(KnowledgeSource).where(KnowledgeSource.is_active.is_(True))

    if status_filter:
        q = q.where(KnowledgeSource.status == status_filter.value)
    if source_type:
        q = q.where(KnowledgeSource.type == source_type.value)
    if tag:
        q = q.where(KnowledgeSource.tags.contains([tag]))

    count_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = count_result.scalar_one()

    q = q.order_by(KnowledgeSource.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    sources = result.scalars().all()

    return KnowledgeSourceListResponse(
        items=[KnowledgeSourceResponse.model_validate(s) for s in sources],
        total=total,
        page=page,
        page_size=page_size,
    )


# ─── GET /knowledge/sources/{id} ──────────────────────────────────────────────


@router.get(
    "/sources/{source_id}",
    response_model=KnowledgeSourceResponse,
    summary="Get knowledge source detail",
)
async def get_source(
    source_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeSourceResponse:
    """Return details for a single knowledge source including chunk count."""
    result = await db.execute(
        select(KnowledgeSource).where(KnowledgeSource.id == source_id)
    )
    source: KnowledgeSource | None = result.scalar_one_or_none()
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    # Refresh chunk count
    chunk_count_result = await db.execute(
        select(func.count(KnowledgeChunk.id)).where(
            KnowledgeChunk.source_id == source_id
        )
    )
    source.chunk_count = chunk_count_result.scalar_one()

    return KnowledgeSourceResponse.model_validate(source)


# ─── DELETE /knowledge/sources/{id} ───────────────────────────────────────────


@router.delete(
    "/sources/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete knowledge source",
)
async def delete_source(
    source_id: uuid.UUID,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Hard-delete a knowledge source and all its chunks (cascade)."""
    result = await db.execute(
        select(KnowledgeSource).where(KnowledgeSource.id == source_id)
    )
    source: KnowledgeSource | None = result.scalar_one_or_none()
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    await db.delete(source)
    await db.commit()
    logger.info("knowledge.source_deleted", source_id=str(source_id))


# ─── PUT /knowledge/sources/{id}/approve ──────────────────────────────────────


@router.put(
    "/sources/{source_id}/approve",
    response_model=KnowledgeSourceResponse,
    summary="Approve a pending knowledge source",
)
async def approve_source(
    source_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeSourceResponse:
    """Approve a pending source and trigger ingestion processing."""
    result = await db.execute(
        select(KnowledgeSource).where(KnowledgeSource.id == source_id)
    )
    source: KnowledgeSource | None = result.scalar_one_or_none()
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    if source.status not in (
        KnowledgeSourceStatus.pending.value,
        KnowledgeSourceStatus.rejected.value,
        KnowledgeSourceStatus.failed.value,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot approve source in status '{source.status}'",
        )

    now = datetime.now(UTC)
    await db.execute(
        update(KnowledgeSource)
        .where(KnowledgeSource.id == source_id)
        .values(
            status=KnowledgeSourceStatus.approved.value,
            approved_by=current_user.id,
            approved_at=now,
            rejection_reason=None,
        )
    )
    await db.commit()
    await db.refresh(source)

    background_tasks.add_task(_trigger_processing, source.id)
    logger.info("knowledge.source_approved", source_id=str(source_id), by=str(current_user.id))
    return KnowledgeSourceResponse.model_validate(source)


# ─── PUT /knowledge/sources/{id}/reject ───────────────────────────────────────


@router.put(
    "/sources/{source_id}/reject",
    response_model=KnowledgeSourceResponse,
    summary="Reject a pending knowledge source",
)
async def reject_source(
    source_id: uuid.UUID,
    reason: str = Query(..., min_length=1, max_length=2048),
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeSourceResponse:
    """Reject a knowledge source with a mandatory reason."""
    result = await db.execute(
        select(KnowledgeSource).where(KnowledgeSource.id == source_id)
    )
    source: KnowledgeSource | None = result.scalar_one_or_none()
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    await db.execute(
        update(KnowledgeSource)
        .where(KnowledgeSource.id == source_id)
        .values(
            status=KnowledgeSourceStatus.rejected.value,
            rejection_reason=reason,
        )
    )
    await db.commit()
    await db.refresh(source)

    logger.info("knowledge.source_rejected", source_id=str(source_id), reason=reason[:80])
    return KnowledgeSourceResponse.model_validate(source)


# ─── POST /knowledge/sources/{id}/reprocess ───────────────────────────────────


@router.post(
    "/sources/{source_id}/reprocess",
    response_model=KnowledgeSourceResponse,
    summary="Re-ingest a knowledge source",
)
async def reprocess_source(
    source_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeSourceResponse:
    """
    Delete existing chunks and re-queue the source for ingestion.
    Useful after updating the embedding model or fixing processing errors.
    """
    result = await db.execute(
        select(KnowledgeSource).where(KnowledgeSource.id == source_id)
    )
    source: KnowledgeSource | None = result.scalar_one_or_none()
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    # Delete existing chunks
    await db.execute(
        select(KnowledgeChunk).where(KnowledgeChunk.source_id == source_id)
    )
    # Use bulk delete
    from sqlalchemy import delete as sa_delete
    await db.execute(
        sa_delete(KnowledgeChunk).where(KnowledgeChunk.source_id == source_id)
    )

    await db.execute(
        update(KnowledgeSource)
        .where(KnowledgeSource.id == source_id)
        .values(
            status=KnowledgeSourceStatus.processing.value,
            chunk_count=0,
            processing_error=None,
            processed_at=None,
        )
    )
    await db.commit()
    await db.refresh(source)

    background_tasks.add_task(_trigger_processing, source.id)
    logger.info("knowledge.source_reprocessing", source_id=str(source_id))
    return KnowledgeSourceResponse.model_validate(source)


# ─── POST /knowledge/search ───────────────────────────────────────────────────


@router.post(
    "/search",
    response_model=KnowledgeSearchResponse,
    summary="Semantic search across knowledge base",
)
async def search_knowledge(
    body: KnowledgeSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeSearchResponse:
    """
    Perform semantic (ANN), keyword (full-text), or hybrid search over
    all approved knowledge chunks.
    """
    start_ts = time.monotonic()

    try:
        from app.core.knowledge_engine import KnowledgeEngine  # type: ignore[import]
        from app.core.llm_router import LLMRouter
        from app.core.vector_search import VectorSearchEngine

        llm = LLMRouter()
        vs = VectorSearchEngine()
        engine = KnowledgeEngine(db, llm, vs)
        raw_results = await engine.search(
            query=body.query,
            mode=body.mode,
            limit=body.limit,
            score_threshold=body.score_threshold,
            source_ids=[str(sid) for sid in body.source_ids],
            tags=body.tags,
            source_types=[t.value for t in body.source_types],
            semantic_weight=body.semantic_weight,
            keyword_weight=body.keyword_weight,
        )
    except ImportError:
        # Fallback: basic SQL ILIKE search
        q = (
            select(KnowledgeChunk, KnowledgeSource)
            .join(KnowledgeSource, KnowledgeChunk.source_id == KnowledgeSource.id)
            .where(
                KnowledgeSource.status == KnowledgeSourceStatus.approved.value,
                KnowledgeSource.is_active.is_(True),
                KnowledgeChunk.content.ilike(f"%{body.query}%"),
            )
            .limit(body.limit)
        )
        result = await db.execute(q)
        rows = result.all()
        raw_results = [
            {"chunk": row[0], "source": row[1], "score": 0.8, "highlights": []}
            for row in rows
        ]

    latency_ms = int((time.monotonic() - start_ts) * 1000)

    results = [
        KnowledgeSearchResult(
            chunk=KnowledgeChunkResponse.model_validate(r["chunk"]),
            source=KnowledgeSourceResponse.model_validate(r["source"]),
            score=r["score"],
            highlights=r.get("highlights", []),
        )
        for r in raw_results
    ]

    return KnowledgeSearchResponse(
        query=body.query,
        mode=body.mode,
        results=results,
        total_found=len(results),
        search_latency_ms=latency_ms,
    )


# ─── GET /knowledge/sources/{id}/chunks ───────────────────────────────────────


@router.get(
    "/sources/{source_id}/chunks",
    response_model=KnowledgeChunkListResponse,
    summary="List chunks for a knowledge source",
)
async def list_chunks(
    source_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeChunkListResponse:
    """Return paginated chunks for a knowledge source."""
    source_result = await db.execute(
        select(KnowledgeSource).where(KnowledgeSource.id == source_id)
    )
    if source_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    q = select(KnowledgeChunk).where(KnowledgeChunk.source_id == source_id)
    count_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = count_result.scalar_one()

    q = q.order_by(KnowledgeChunk.chunk_index.asc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    chunks = result.scalars().all()

    return KnowledgeChunkListResponse(
        items=[KnowledgeChunkResponse.model_validate(c) for c in chunks],
        total=total,
        source_id=source_id,
    )


# ─── PUT /knowledge/chunks/{id} ───────────────────────────────────────────────


@router.put(
    "/chunks/{chunk_id}",
    response_model=KnowledgeChunkResponse,
    summary="Edit chunk content",
)
async def update_chunk(
    chunk_id: uuid.UUID,
    content: str = Form(..., min_length=1, max_length=65536),
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeChunkResponse:
    """
    Overwrite the text content of a specific chunk.
    The embedding will be regenerated asynchronously.
    """
    result = await db.execute(
        select(KnowledgeChunk).where(KnowledgeChunk.id == chunk_id)
    )
    chunk: KnowledgeChunk | None = result.scalar_one_or_none()
    if chunk is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chunk not found")

    chunk.content = content
    chunk.embedding = None  # will be recomputed
    await db.commit()
    await db.refresh(chunk)

    logger.info("knowledge.chunk_updated", chunk_id=str(chunk_id))
    return KnowledgeChunkResponse.model_validate(chunk)


# ─── DELETE /knowledge/chunks/{id} ────────────────────────────────────────────


@router.delete(
    "/chunks/{chunk_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a specific chunk",
)
async def delete_chunk(
    chunk_id: uuid.UUID,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a single knowledge chunk."""
    result = await db.execute(
        select(KnowledgeChunk).where(KnowledgeChunk.id == chunk_id)
    )
    chunk: KnowledgeChunk | None = result.scalar_one_or_none()
    if chunk is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chunk not found")

    source_id = chunk.source_id
    await db.delete(chunk)

    # Decrement chunk count on source
    await db.execute(
        update(KnowledgeSource)
        .where(KnowledgeSource.id == source_id)
        .values(chunk_count=KnowledgeSource.chunk_count - 1)
    )
    await db.commit()
    logger.info("knowledge.chunk_deleted", chunk_id=str(chunk_id))
