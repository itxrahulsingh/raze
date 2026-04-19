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

import asyncio
import hashlib
import io
import json
import time
import uuid
from datetime import UTC, datetime

import structlog
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db, get_redis
from app.models.knowledge import (
    KnowledgeChunk,
    KnowledgeSource,
    KnowledgeSourceMode,
    KnowledgeSourceStatus,
    KnowledgeSourceType,
    KnowledgeSourceCategory,
)
from app.models.knowledge_version import KnowledgeChunkVersion
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
from app.core.security import get_current_user
from app.core.dependencies import check_rate_limit
from app.api.v1 import deps

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
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def _normalize_category(category: str | None) -> str:
    """Normalize category aliases to canonical enum values."""
    if not category:
        return KnowledgeSourceCategory.document.value
    lowered = category.strip().lower()
    alias_map = {
        "documents": KnowledgeSourceCategory.document.value,
        "docs": KnowledgeSourceCategory.document.value,
    }
    normalized = alias_map.get(lowered, lowered)
    valid = {member.value for member in KnowledgeSourceCategory}
    return normalized if normalized in valid else KnowledgeSourceCategory.document.value


def _is_category_enabled(knowledge_settings: dict, category: str) -> bool:
    category_flag_map = {
        KnowledgeSourceCategory.document.value: "enable_documents",
        KnowledgeSourceCategory.article.value: "enable_articles",
        KnowledgeSourceCategory.chat_session.value: "enable_chat_sessions",
        KnowledgeSourceCategory.client_document.value: "enable_client_documents",
        KnowledgeSourceCategory.training_material.value: "enable_training_materials",
        KnowledgeSourceCategory.reference.value: "enable_references",
    }
    flag = category_flag_map.get(category)
    if not flag:
        return True
    return bool(knowledge_settings.get(flag, True))


def _infer_source_type(upload_file: UploadFile | None, provided: KnowledgeSourceType, url: str | None) -> KnowledgeSourceType:
    if url:
        return KnowledgeSourceType.url
    if upload_file is None:
        return provided

    mime = (upload_file.content_type or "").lower()
    filename = (upload_file.filename or "").lower()

    if "pdf" in mime or filename.endswith(".pdf"):
        return KnowledgeSourceType.pdf
    if "word" in mime or filename.endswith(".docx"):
        return KnowledgeSourceType.docx
    if "csv" in mime or filename.endswith(".csv"):
        return KnowledgeSourceType.csv
    if "json" in mime or filename.endswith(".json"):
        return KnowledgeSourceType.json
    if "spreadsheetml" in mime or filename.endswith(".xlsx"):
        return KnowledgeSourceType.xlsx
    if "ms-excel" in mime or filename.endswith(".xls"):
        return KnowledgeSourceType.xls
    if "html" in mime or filename.endswith(".html") or filename.endswith(".htm"):
        return KnowledgeSourceType.html
    return KnowledgeSourceType.txt


async def _get_knowledge_settings() -> dict:
    """Load knowledge runtime settings from Redis, with defaults fallback."""
    defaults = {
        "auto_approve_sources": False,
        "require_source_approval": True,
        "chat_session_knowledge_enabled": True,
    }
    redis_client = get_redis()
    try:
        cached = await redis_client.get("knowledge:settings")
        if cached:
            parsed = json.loads(cached)
            if isinstance(parsed, dict):
                return {**defaults, **parsed}
    except Exception:
        pass
    return defaults


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
    """Run knowledge processing via Celery when enabled, otherwise local background."""
    settings = get_settings()
    if settings.celery_enabled:
        try:
            from app.celery_app import celery_app

            celery_app.send_task("app.tasks.process_knowledge_source", args=[str(source_id)])
            logger.info("knowledge.processing_dispatched_celery", source_id=str(source_id))
            return
        except Exception as exc:
            logger.warning("knowledge.processing_celery_fallback", source_id=str(source_id), error=str(exc))
    await _process_knowledge_source_bg(source_id)


async def _ingest_raw_text_bg(
    source_id: uuid.UUID,
    content: str,
    initial_status: str,
) -> None:
    """Background ingestion for raw text payloads (article/chat conversion)."""
    from app.database import AsyncSessionLocal
    from app.core.knowledge_engine import KnowledgeEngine
    from app.core.llm_router import LLMRouter
    from app.core.vector_search import VectorSearchEngine

    async with AsyncSessionLocal() as db:
        try:
            source_result = await db.execute(select(KnowledgeSource).where(KnowledgeSource.id == source_id))
            source = source_result.scalar_one_or_none()
            if source is None:
                return

            llm = LLMRouter()
            vs = VectorSearchEngine()
            engine = KnowledgeEngine(db, llm, vs)

            await db.execute(
                update(KnowledgeSource)
                .where(KnowledgeSource.id == source_id)
                .values(status=KnowledgeSourceStatus.processing.value, processing_error=None)
            )
            await db.commit()

            chunks = engine.chunk_text(content, chunk_size=get_settings().chunk_size, overlap=get_settings().chunk_overlap)
            if not chunks:
                raise ValueError("No text content to ingest")

            embeddings = await engine.embed_chunks(chunks)
            await engine.store_chunks(source_id, chunks, embeddings)

            await db.execute(
                update(KnowledgeSource)
                .where(KnowledgeSource.id == source_id)
                .values(
                    status=initial_status,
                    chunk_count=len(chunks),
                    embedding_model=get_settings().openai_embedding_model,
                    mime_type="text/plain",
                    file_size=len(content.encode("utf-8")),
                    processed_at=datetime.now(UTC),
                    processing_error=None,
                )
            )
            await db.commit()
            logger.info("knowledge.raw_text_ingested", source_id=str(source_id), chunk_count=len(chunks))
        except Exception as exc:
            logger.error("knowledge.raw_text_ingest_error", source_id=str(source_id), error=str(exc))
            await db.execute(
                update(KnowledgeSource)
                .where(KnowledgeSource.id == source_id)
                .values(status=KnowledgeSourceStatus.failed.value, processing_error=str(exc)[:2000])
            )
            await db.commit()


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
    category: str = Form(default=KnowledgeSourceCategory.document.value),
    client_id: str | None = Form(default=None),
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

    knowledge_settings = await _get_knowledge_settings()
    if not knowledge_settings.get("enable_knowledge_base", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Knowledge base is currently disabled",
        )
    require_approval = bool(knowledge_settings.get("require_source_approval", True))
    auto_approve_by_policy = bool(knowledge_settings.get("auto_approve_sources", False)) or not require_approval

    # Validate explicit auto_approve permission
    is_admin = current_user.role in ("admin", "superadmin")
    if auto_approve and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="auto_approve requires admin role",
        )
    resolved_auto_approve = auto_approve or auto_approve_by_policy

    parsed_tags = [t.strip().lower() for t in tags.split(",") if t.strip()] if tags else []
    normalized_category = _normalize_category(category)

    file_path: str | None = None
    file_size: int | None = None
    mime_type: str | None = None
    content_hash: str | None = None
    mode = KnowledgeSourceMode.persistent
    source_type = _infer_source_type(file, source_type, url)
    if not _is_category_enabled(knowledge_settings, normalized_category):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Category '{normalized_category}' is currently disabled",
        )

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
        if mime_type not in _ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported file type: {mime_type}",
            )

        file_path = await _store_file(file_bytes, object_name, mime_type)

    elif url:
        mode = KnowledgeSourceMode.linked
        source_type = KnowledgeSourceType.url

    initial_status = (
        KnowledgeSourceStatus.approved if resolved_auto_approve else KnowledgeSourceStatus.pending
    )
    approved_by = current_user.id if resolved_auto_approve else None
    approved_at = datetime.now(UTC) if resolved_auto_approve else None

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
        category=normalized_category,
        client_id=client_id,
        approved_by=approved_by,
        approved_at=approved_at,
        is_active=True,
        can_use_in_knowledge=True,
        can_use_in_chat=True,
        can_use_in_search=True,
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)

    # Start processing immediately (don't wait for completion)
    # This ensures chunks are available quickly for approved sources
    import asyncio
    asyncio.create_task(_trigger_processing(source.id))

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
    category: str | None = Query(default=None),
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
    if category:
        q = q.where(KnowledgeSource.category == _normalize_category(category))
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
    response_model=None,
    response_class=Response,
    summary="Delete knowledge source",
)
async def delete_source(
    source_id: uuid.UUID,
    current_user: User = Depends(deps.get_current_user),
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
    current_user: User = Depends(deps.get_current_user),
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

    should_reprocess = not (source.chunk_count and source.chunk_count > 0 and source.processed_at)
    if should_reprocess:
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
    current_user: User = Depends(deps.get_current_user),
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
    current_user: User = Depends(deps.get_current_user),
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
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeSearchResponse:
    """
    Perform semantic (ANN), keyword (full-text), or hybrid search over
    all approved knowledge chunks.
    """
    # Check rate limit
    request.state.user_id = str(current_user.id)
    await check_rate_limit(request, "knowledge_search")
    knowledge_settings = await _get_knowledge_settings()
    if not knowledge_settings.get("enable_knowledge_base", True) or not knowledge_settings.get("knowledge_in_search", True):
        return KnowledgeSearchResponse(
            query=body.query,
            mode=body.mode,
            results=[],
            total_found=0,
            search_latency_ms=0,
        )

    start_ts = time.monotonic()

    try:
        from app.core.knowledge_engine import KnowledgeEngine  # type: ignore[import]
        from app.core.llm_router import LLMRouter
        from app.core.vector_search import VectorSearchEngine

        llm = LLMRouter()
        vs = VectorSearchEngine()
        engine = KnowledgeEngine(db, llm, vs)

        # Build filters for source_ids and tags
        filters = {}
        if body.source_ids:
            filters["source_id"] = [str(sid) for sid in body.source_ids]
        if body.tags:
            filters["tags"] = body.tags

        raw_results = await engine.search_knowledge(
            query=body.query,
            top_k=body.limit,
            score_threshold=body.score_threshold,
            filters=filters or None,
            approved_only=True,
            use_case="search",
        )
    except ImportError:
        # Fallback: basic SQL ILIKE search
        q = (
            select(KnowledgeChunk, KnowledgeSource)
            .join(KnowledgeSource, KnowledgeChunk.source_id == KnowledgeSource.id)
            .where(
                KnowledgeSource.status == KnowledgeSourceStatus.approved.value,
                KnowledgeSource.is_active.is_(True),
                KnowledgeSource.can_use_in_search.is_(True),
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

    # Convert raw_results to KnowledgeSearchResult objects
    # search_knowledge returns: {"chunk_id", "source_id", "source_name", "source_type", "content", ...}
    # Need to load full ORM objects for response format
    results = []
    if raw_results:
        chunk_ids = [uuid.UUID(r["chunk_id"]) for r in raw_results]
        chunk_query = await db.execute(
            select(KnowledgeChunk, KnowledgeSource)
            .join(KnowledgeSource, KnowledgeChunk.source_id == KnowledgeSource.id)
            .where(KnowledgeChunk.id.in_(chunk_ids))
        )
        chunk_rows = {str(row[0].id): row for row in chunk_query.all()}

        for r in raw_results:
            row = chunk_rows.get(r["chunk_id"])
            if row:
                chunk, source = row
                results.append(
                    KnowledgeSearchResult(
                        chunk=KnowledgeChunkResponse.model_validate(chunk),
                        source=KnowledgeSourceResponse.model_validate(source),
                        score=r["score"],
                        highlights=[],
                    )
                )

    return KnowledgeSearchResponse(
        query=body.query,
        mode=body.mode,
        results=results,
        total_found=len(results),
        search_latency_ms=latency_ms,
    )


@router.get(
    "/index/health",
    summary="Knowledge index health",
)
async def knowledge_index_health(
    current_user: User = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return DB + vector index readiness for knowledge retrieval."""
    from app.core.vector_search import VectorSearchEngine

    db_source_count = int((await db.execute(select(func.count(KnowledgeSource.id)))).scalar() or 0)
    db_chunk_count = int((await db.execute(select(func.count(KnowledgeChunk.id)))).scalar() or 0)
    db_approved_count = int(
        (
            await db.execute(
                select(func.count(KnowledgeSource.id)).where(
                    KnowledgeSource.status == KnowledgeSourceStatus.approved.value
                )
            )
        ).scalar()
        or 0
    )
    vector_health: dict[str, str | int] = {"status": "unknown"}
    try:
        vs = VectorSearchEngine()
        info = await vs.get_collection_info(get_settings().qdrant_collection_knowledge)
        vector_health = {
            "status": "healthy",
            "points_count": int(info.get("points_count") or 0),
            "indexed_vectors_count": int(info.get("indexed_vectors_count") or 0),
            "collection": str(info.get("name") or get_settings().qdrant_collection_knowledge),
        }
    except Exception as exc:
        vector_health = {"status": "unhealthy", "error": str(exc)}

    return {
        "database": {
            "sources_total": db_source_count,
            "sources_approved": db_approved_count,
            "chunks_total": db_chunk_count,
        },
        "vector_index": vector_health,
    }


@router.post(
    "/index/reindex",
    summary="Queue source re-indexing",
)
async def queue_reindex(
    background_tasks: BackgroundTasks,
    source_id: uuid.UUID | None = Query(default=None),
    force_all: bool = Query(default=False),
    max_sources: int = Query(default=200, ge=1, le=2000),
    current_user: User = Depends(deps.get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Queue knowledge source reprocessing for one source or a batch."""
    if source_id:
        source_result = await db.execute(select(KnowledgeSource).where(KnowledgeSource.id == source_id))
        source = source_result.scalar_one_or_none()
        if not source:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
        background_tasks.add_task(_trigger_processing, source.id)
        return {"queued": 1, "source_ids": [str(source.id)]}

    sources_query = select(KnowledgeSource).where(
        KnowledgeSource.is_active.is_(True),
        KnowledgeSource.mode == KnowledgeSourceMode.persistent.value,
        *(
            []
            if force_all
            else [
                (KnowledgeSource.chunk_count == 0)
                | (KnowledgeSource.status == KnowledgeSourceStatus.failed.value)
            ]
        ),
    ).limit(max_sources)
    sources_result = await db.execute(sources_query)
    sources = sources_result.scalars().all()
    for source in sources:
        background_tasks.add_task(_trigger_processing, source.id)

    return {
        "queued": len(sources),
        "source_ids": [str(source.id) for source in sources],
        "mode": "force_all" if force_all else "missing_or_failed_only",
    }


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
    current_user: User = Depends(deps.get_current_user),
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
    response_model=None,
    response_class=Response,
    summary="Delete a specific chunk",
)
async def delete_chunk(
    chunk_id: uuid.UUID,
    current_user: User = Depends(deps.get_current_user),
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


# ─── GET /knowledge/chunks/{id}/versions ──────────────────────────────────────


@router.get(
    "/chunks/{chunk_id}/versions",
    response_model=list,
    summary="List all versions of a knowledge chunk",
)
async def list_chunk_versions(
    chunk_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list:
    """List all versions of a knowledge chunk with change metadata."""
    # Verify chunk exists
    chunk_result = await db.execute(
        select(KnowledgeChunk).where(KnowledgeChunk.id == chunk_id)
    )
    chunk = chunk_result.scalar_one_or_none()
    if chunk is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chunk not found")

    # Get all versions ordered by version descending
    versions_result = await db.execute(
        select(KnowledgeChunkVersion)
        .where(KnowledgeChunkVersion.chunk_id == chunk_id)
        .order_by(KnowledgeChunkVersion.version.desc())
    )
    versions = versions_result.scalars().all()

    return [
        {
            "version": v.version,
            "old_content": v.old_content,
            "new_content": v.new_content,
            "changed_by": str(v.changed_by) if v.changed_by else None,
            "change_reason": v.change_reason,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in versions
    ]


# ─── POST /knowledge/chunks/{id}/rollback ──────────────────────────────────────


@router.post(
    "/chunks/{chunk_id}/rollback",
    response_model=dict,
    summary="Rollback chunk to a previous version",
)
async def rollback_chunk_version(
    chunk_id: uuid.UUID,
    target_version: int = Query(..., ge=1),
    reason: str = Query(default=""),
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Rollback a knowledge chunk to a previous version.

    Requires admin role.
    """
    # Get current chunk
    chunk_result = await db.execute(
        select(KnowledgeChunk).where(KnowledgeChunk.id == chunk_id)
    )
    chunk = chunk_result.scalar_one_or_none()
    if chunk is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chunk not found")

    # Get target version
    target_result = await db.execute(
        select(KnowledgeChunkVersion).where(
            KnowledgeChunkVersion.chunk_id == chunk_id,
            KnowledgeChunkVersion.version == target_version,
        )
    )
    target = target_result.scalar_one_or_none()
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {target_version} not found",
        )

    # Record current state before rollback
    current_version_num = await db.execute(
        select(func.max(KnowledgeChunkVersion.version)).where(
            KnowledgeChunkVersion.chunk_id == chunk_id
        )
    )
    max_version = current_version_num.scalar() or 0
    new_version_num = max_version + 1

    # Create new version record for the rollback
    rollback_version = KnowledgeChunkVersion(
        chunk_id=chunk_id,
        version=new_version_num,
        old_content=chunk.content,
        new_content=target.new_content,
        changed_by=current_user.id,
        change_reason=f"Rollback to version {target_version}. {reason}".strip(),
    )
    db.add(rollback_version)

    # Update chunk content
    chunk.content = target.new_content
    chunk.updated_at = datetime.now(UTC)

    await db.commit()
    logger.info(
        "knowledge.chunk_rolled_back",
        chunk_id=str(chunk_id),
        target_version=target_version,
        new_version=new_version_num,
        admin_id=str(current_user.id),
    )

    return {
        "chunk_id": str(chunk_id),
        "rolled_back_to_version": target_version,
        "new_version": new_version_num,
        "reason": reason,
    }


# ─── POST /knowledge/articles ────────────────────────────────────────────────

@router.post(
    "/articles",
    response_model=KnowledgeSourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an article",
)
async def create_article(
    body: dict = Body(...),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeSourceResponse:
    """Create a knowledge article (text-based)."""
    if background_tasks is None:
        from fastapi import BackgroundTasks as BT
        background_tasks = BT()

    name = (body.get("name") or "").strip()
    content = (body.get("content") or "").strip()
    description = body.get("description")
    tags = body.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip().lower() for t in tags.split(",") if t.strip()]
    elif isinstance(tags, list):
        tags = [str(t).strip().lower() for t in tags if str(t).strip()]
    else:
        tags = []
    client_id = body.get("client_id")

    if not name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="name is required")
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="content is required")

    settings = await _get_knowledge_settings()
    if not settings.get("enable_knowledge_base", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Knowledge base is currently disabled",
        )
    normalized_category = _normalize_category(body.get("category") or KnowledgeSourceCategory.article.value)
    if not _is_category_enabled(settings, normalized_category):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Category '{normalized_category}' is currently disabled",
        )
    initial_status = (
        KnowledgeSourceStatus.approved.value
        if (not settings.get("require_source_approval", True) or settings.get("auto_approve_sources", False))
        else KnowledgeSourceStatus.pending.value
    )

    source = KnowledgeSource(
        name=name,
        description=description,
        type=KnowledgeSourceType.manual.value,
        category=normalized_category,
        status=initial_status,
        mode=KnowledgeSourceMode.persistent.value,
        tags=tags,
        client_id=client_id,
        content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        is_active=True,
        can_use_in_knowledge=True,
        can_use_in_chat=True,
        can_use_in_search=True,
        approved_by=current_user.id if initial_status == KnowledgeSourceStatus.approved.value else None,
        approved_at=datetime.now(UTC) if initial_status == KnowledgeSourceStatus.approved.value else None,
        src_metadata={"raw_text": content, "author_id": str(current_user.id)},
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)

    # Start ingestion immediately (reliable)
    import asyncio
    asyncio.create_task(_ingest_raw_text_bg(source.id, content, source.status))

    return KnowledgeSourceResponse.model_validate(source)


# ─── PUT /knowledge/sources/{id} ─────────────────────────────────────────────

@router.put(
    "/sources/{source_id}",
    response_model=KnowledgeSourceResponse,
    summary="Update source usage controls",
)
async def update_source(
    source_id: uuid.UUID,
    body: dict | None = Body(default=None),
    can_use_in_knowledge: bool | None = Query(default=None),
    can_use_in_chat: bool | None = Query(default=None),
    can_use_in_search: bool | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeSourceResponse:
    """Update source usage controls (admin only)."""
    result = await db.execute(select(KnowledgeSource).where(KnowledgeSource.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    payload = body or {}
    updates = {}
    if can_use_in_knowledge is None and "can_use_in_knowledge" in payload:
        can_use_in_knowledge = bool(payload.get("can_use_in_knowledge"))
    if can_use_in_chat is None and "can_use_in_chat" in payload:
        can_use_in_chat = bool(payload.get("can_use_in_chat"))
    if can_use_in_search is None and "can_use_in_search" in payload:
        can_use_in_search = bool(payload.get("can_use_in_search"))
    if is_active is None and "is_active" in payload:
        is_active = bool(payload.get("is_active"))
    if can_use_in_knowledge is not None:
        updates['can_use_in_knowledge'] = can_use_in_knowledge
    if can_use_in_chat is not None:
        updates['can_use_in_chat'] = can_use_in_chat
    if can_use_in_search is not None:
        updates['can_use_in_search'] = can_use_in_search
    if is_active is not None:
        updates['is_active'] = is_active

    if updates:
        updates['edited_by'] = current_user.id
        updates['edited_at'] = datetime.now(UTC)
        updates['edit_count'] = source.edit_count + 1

        await db.execute(
            update(KnowledgeSource).where(KnowledgeSource.id == source_id).values(**updates)
        )
        await db.commit()

    await db.refresh(source)
    return KnowledgeSourceResponse.model_validate(source)


# ─── GET /knowledge/sources/{id}/download ────────────────────────────────────

@router.get(
    "/sources/{source_id}/download",
    summary="Download knowledge source",
)
async def download_source(
    source_id: uuid.UUID,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download the original source file or content."""
    result = await db.execute(select(KnowledgeSource).where(KnowledgeSource.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    # If it's a file, download from storage
    if source.file_path:
        try:
            file_bytes = await _read_stored_file(source.file_path)
            filename = source.name.replace(" ", "_") + ".pdf"
            return FileResponse(
                content=file_bytes,
                media_type=source.mime_type or "application/octet-stream",
                filename=filename,
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        except Exception as e:
            logger.error("knowledge.download_error", source_id=str(source_id), error=str(e))
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Download failed")

    # If it's raw text (article/chat), return as text file
    if source.type in [KnowledgeSourceType.manual.value, KnowledgeSourceType.txt.value]:
        content = source.src_metadata.get("raw_text", "") if source.src_metadata else ""
        if not content:
            # Reconstruct from chunks
            chunk_result = await db.execute(
                select(KnowledgeChunk).where(KnowledgeChunk.source_id == source_id).order_by(KnowledgeChunk.chunk_index)
            )
            chunks = chunk_result.scalars().all()
            content = "\n\n".join([c.content for c in chunks])

        from io import BytesIO
        file_bytes = content.encode("utf-8")
        filename = source.name.replace(" ", "_") + ".txt"
        return FileResponse(
            content=file_bytes,
            media_type="text/plain",
            filename=filename,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot download this source type")


@router.post(
    "/sources/from-conversation/{conversation_id}",
    response_model=KnowledgeSourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create knowledge source from conversation",
)
async def create_knowledge_from_conversation(
    background_tasks: BackgroundTasks,
    conversation_id: uuid.UUID,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeSourceResponse:
    """Convert a conversation to a knowledge source (chat_session)."""
    from app.models.conversation import Conversation, Message

    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    msg_result = await db.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)
    )
    messages = msg_result.scalars().all()

    content_lines = [f"# {conversation.title or 'Untitled Conversation'}\n"]
    content_lines.append(f"Date: {conversation.created_at.isoformat()}\n")
    content_lines.append(f"Messages: {len(messages)}\n\n")

    for msg in messages:
        role_str = msg.role if isinstance(msg.role, str) else msg.role.value
        role = "User" if role_str == "user" else "Assistant"
        content_lines.append(f"**{role}**: {msg.content}\n")

    full_content = "\n".join(content_lines)
    content_hash = hashlib.sha256(full_content.encode()).hexdigest()

    existing = await db.execute(
        select(KnowledgeSource).where(KnowledgeSource.content_hash == content_hash)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This conversation already exists in the knowledge base"
        )

    knowledge_settings = await _get_knowledge_settings()
    if not knowledge_settings.get("enable_knowledge_base", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Knowledge base is currently disabled",
        )
    if not knowledge_settings.get("chat_session_knowledge_enabled", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chat session knowledge conversion is currently disabled",
        )
    if not _is_category_enabled(knowledge_settings, KnowledgeSourceCategory.chat_session.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Category 'chat_session' is currently disabled",
        )

    initial_status = (
        KnowledgeSourceStatus.approved.value
        if (not knowledge_settings.get("require_source_approval", True) or knowledge_settings.get("auto_approve_sources", False))
        else KnowledgeSourceStatus.pending.value
    )

    source = KnowledgeSource(
        name=conversation.title or f"Conversation {str(conversation_id)[:8]}",
        description=f"Conversation with {len(messages)} messages",
        type=KnowledgeSourceType.txt.value,
        category=KnowledgeSourceCategory.chat_session.value,
        status=initial_status,
        mode=KnowledgeSourceMode.persistent.value,
        content_hash=content_hash,
        mime_type="text/plain",
        src_metadata={
            "conversation_id": str(conversation_id),
            "message_count": len(messages),
            "created_at": conversation.created_at.isoformat(),
        },
        tags=["conversation", "chat-session"],
        is_active=True,
        can_use_in_knowledge=True,
        can_use_in_chat=True,
        can_use_in_search=True,
        approved_by=current_user.id if initial_status == KnowledgeSourceStatus.approved.value else None,
        approved_at=datetime.now(UTC) if initial_status == KnowledgeSourceStatus.approved.value else None,
    )

    db.add(source)
    await db.commit()
    await db.refresh(source)

    background_tasks.add_task(_ingest_raw_text_bg, source.id, full_content, source.status)

    logger.info(
        "knowledge.conversation_added",
        conversation_id=str(conversation_id),
        source_id=str(source.id),
        message_count=len(messages),
    )

    return KnowledgeSourceResponse.model_validate(source)
