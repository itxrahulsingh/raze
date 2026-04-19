"""Chat SDK and Embeddable Chat API."""
import hashlib
import json
import secrets
import time
import uuid
from datetime import UTC, datetime
from typing import Any, AsyncGenerator
from urllib.parse import urlparse
import asyncio

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, update, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.chat_domain import ChatDomain, DomainStatus
from app.models.user import User
from app.models.settings import AppSettings
from app.config import get_settings
from app.api.v1 import deps
from app.models.conversation import Conversation, ConversationStatus, Message, MessageRole
from app.schemas.chat import StreamChunk, StreamEventType
from app.database import AsyncSessionLocal
from app.core.prompt_builder import build_industry_system_prompt

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/chat-sdk", tags=["Chat SDK"])
settings = get_settings()
_sdk_schema_ready = False
_sdk_schema_lock = asyncio.Lock()


# Request schemas
class SDKChatRequest(BaseModel):
    """Chat request from SDK widget."""
    message: str
    session_id: str | None = None
    knowledge_ids: list[str] = []


def _generate_api_key(length: int = 32) -> str:
    """Generate a secure API key."""
    return f"raze_sk_{secrets.token_urlsafe(length)}"


def _hash_api_key(api_key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def _normalize_domain(value: str) -> str:
    """Normalize domain input to a bare hostname."""
    raw = (value or "").strip().lower()
    if not raw:
        return ""
    parsed = urlparse(raw if "://" in raw else f"http://{raw}")
    host = (parsed.hostname or "").strip().lower()
    return host


def _is_origin_allowed(origin: str | None, domain: str) -> bool:
    """Validate browser Origin against approved SDK domain."""
    if settings.chat_sdk_allow_all_origins:
        return True
    if not origin:
        return False
    try:
        host = (urlparse(origin).hostname or "").lower()
    except Exception:
        return False
    allowed = _normalize_domain(domain)
    if not allowed:
        return False
    return host == allowed or host.endswith(f".{allowed}")


def _cors_headers(origin: str | None) -> dict[str, str]:
    if settings.chat_sdk_allow_all_origins:
        return {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "false",
            "Access-Control-Allow-Headers": "Content-Type, X-API-Key, Authorization",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Vary": "Origin",
        }
    safe_origin = origin or "*"
    return {
        "Access-Control-Allow-Origin": safe_origin,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Headers": "Content-Type, X-API-Key, Authorization",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Vary": "Origin",
    }


def _cors_http_exception(status_code: int, detail: str, origin: str | None) -> HTTPException:
    return HTTPException(status_code=status_code, detail=detail, headers=_cors_headers(origin))


async def _ensure_chat_sdk_schema(db: AsyncSession) -> None:
    """Backfill chat-sdk table columns when migrations are not applied."""
    global _sdk_schema_ready
    if _sdk_schema_ready:
        return
    async with _sdk_schema_lock:
        if _sdk_schema_ready:
            return
        statements = [
            "ALTER TABLE chat_domains ADD COLUMN IF NOT EXISTS bot_name VARCHAR(128) NOT NULL DEFAULT 'Assistant'",
            "ALTER TABLE chat_domains ADD COLUMN IF NOT EXISTS welcome_message TEXT",
            "ALTER TABLE chat_domains ADD COLUMN IF NOT EXISTS widget_color VARCHAR(7) NOT NULL DEFAULT '#3B82F6'",
            "ALTER TABLE chat_domains ADD COLUMN IF NOT EXISTS show_knowledge_sources BOOLEAN NOT NULL DEFAULT TRUE",
            "ALTER TABLE chat_domains ADD COLUMN IF NOT EXISTS allow_file_upload BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE chat_domains ADD COLUMN IF NOT EXISTS custom_branding BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE chat_domains ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ",
            "ALTER TABLE chat_domains ADD COLUMN IF NOT EXISTS suspended_at TIMESTAMPTZ",
            "ALTER TABLE chat_domains ADD COLUMN IF NOT EXISTS last_used TIMESTAMPTZ",
        ]
        try:
            conn = await db.connection()
            await conn.run_sync(ChatDomain.__table__.create, checkfirst=True)
            for stmt in statements:
                await db.execute(text(stmt))
            await db.commit()
            _sdk_schema_ready = True
            logger.info("chat_sdk.schema_ready")
        except Exception as exc:
            await db.rollback()
            logger.warning("chat_sdk.schema_repair_failed", error=str(exc))


async def _get_or_create_sdk_conversation(
    db: AsyncSession,
    session_id: str,
    domain: str,
) -> Conversation:
    """Get active SDK conversation by session or create one."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.session_id == session_id,
            Conversation.status == ConversationStatus.active.value,
        ).order_by(Conversation.created_at.desc()).limit(1)
    )
    conv = result.scalars().first()
    if conv is None:
        now = datetime.now(UTC)
        conv = Conversation(
            session_id=session_id,
            user_id=None,
            status=ConversationStatus.active.value,
            message_count=0,
            total_tokens=0,
            total_cost_usd=0.0,
            started_at=now,
            conv_metadata={"source": "chat_sdk", "domain": domain},
        )
        db.add(conv)
        await db.flush()
    return conv


@router.post("/domains")
async def register_domain(
    request: Request,
    domain_data: dict[str, Any],
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Register a new domain for chat SDK (admin only)."""
    await _ensure_chat_sdk_schema(db)
    await deps.apply_rate_limit(request, "register_domain", 60, 60, current_user)

    domain = _normalize_domain(domain_data.get("domain", ""))
    display_name = domain_data.get("display_name", "")

    if not domain or not display_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="domain and display_name are required",
        )

    # Check if domain already exists
    existing = await db.execute(
        select(ChatDomain).where(ChatDomain.domain == domain)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Domain already registered",
        )

    # Generate API key
    api_key = _generate_api_key()
    api_key_hash = _hash_api_key(api_key)

    chat_domain = ChatDomain(
        domain=domain,
        display_name=display_name,
        description=domain_data.get("description"),
        api_key=api_key_hash,
        status=DomainStatus.pending.value,
        created_by=current_user.id,
    )
    db.add(chat_domain)
    await db.commit()
    await db.refresh(chat_domain)

    logger.info(
        "chat_domain.registered",
        domain=domain,
        admin_id=str(current_user.id),
    )

    return {
        "domain_id": str(chat_domain.id),
        "domain": domain,
        "api_key": api_key,  # Show only once!
        "status": chat_domain.status,
        "message": "Domain registered. Awaiting approval from admin.",
    }


@router.get("/domains")
async def list_domains(
    request: Request,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all registered domains (admin only)."""
    await _ensure_chat_sdk_schema(db)
    await deps.apply_rate_limit(request, "list_domains", 120, 60, current_user)

    result = await db.execute(select(ChatDomain).order_by(ChatDomain.created_at.desc()))
    domains = result.scalars().all()

    return {
        "domains": [
            {
                "id": str(d.id),
                "domain": d.domain,
                "display_name": d.display_name,
                "status": d.status,
                "is_active": d.is_active,
                "created_at": d.created_at.isoformat(),
                "last_used": d.last_used.isoformat() if d.last_used else None,
            }
            for d in domains
        ],
        "count": len(domains),
    }


@router.put("/domains/{domain_id}/approve")
async def approve_domain(
    domain_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Approve a domain for chat SDK (admin only)."""
    await _ensure_chat_sdk_schema(db)
    await deps.apply_rate_limit(request, "approve_domain", 60, 60, current_user)

    result = await db.execute(
        select(ChatDomain).where(ChatDomain.id == domain_id)
    )
    domain = result.scalar_one_or_none()

    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found",
        )

    domain.status = DomainStatus.approved.value
    domain.approved_at = datetime.now(UTC)
    domain.is_active = True
    await db.commit()

    logger.info(
        "chat_domain.approved",
        domain=domain.domain,
        admin_id=str(current_user.id),
    )

    return {"status": "approved", "domain": domain.domain}


@router.put("/domains/{domain_id}/suspend")
async def suspend_domain(
    domain_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Suspend a domain (admin only)."""
    await _ensure_chat_sdk_schema(db)
    await deps.apply_rate_limit(request, "suspend_domain", 60, 60, current_user)

    result = await db.execute(
        select(ChatDomain).where(ChatDomain.id == domain_id)
    )
    domain = result.scalar_one_or_none()

    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found",
        )

    domain.status = DomainStatus.suspended.value
    domain.is_active = False
    domain.suspended_at = datetime.now(UTC)
    await db.commit()

    logger.info(
        "chat_domain.suspended",
        domain=domain.domain,
        admin_id=str(current_user.id),
    )

    return {"status": "suspended", "domain": domain.domain}


@router.post("/domains/{domain_id}/regenerate-key")
async def regenerate_domain_api_key(
    domain_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Regenerate API key for a domain (admin only). Returns the new key once."""
    await _ensure_chat_sdk_schema(db)
    await deps.apply_rate_limit(request, "regenerate_domain_key", 30, 60, current_user)

    result = await db.execute(select(ChatDomain).where(ChatDomain.id == domain_id))
    domain = result.scalar_one_or_none()
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found",
        )

    api_key = _generate_api_key()
    domain.api_key = _hash_api_key(api_key)
    domain.last_used = None
    await db.commit()

    logger.info(
        "chat_domain.api_key_regenerated",
        domain=domain.domain,
        admin_id=str(current_user.id),
    )

    return {
        "domain_id": str(domain.id),
        "domain": domain.domain,
        "api_key": api_key,
        "message": "New API key generated. Store it securely; it won't be shown again.",
    }


@router.delete("/domains/{domain_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_domain(
    domain_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a chat SDK domain (admin only)."""
    await _ensure_chat_sdk_schema(db)
    await deps.apply_rate_limit(request, "delete_domain", 30, 60, current_user)

    result = await db.execute(select(ChatDomain).where(ChatDomain.id == domain_id))
    domain = result.scalar_one_or_none()
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found",
        )

    await db.delete(domain)
    await db.commit()

    logger.info(
        "chat_domain.deleted",
        domain=domain.domain,
        admin_id=str(current_user.id),
    )


@router.post("/chat")
async def chat_with_knowledge(
    request: Request,
    body: SDKChatRequest,
    x_api_key: str = Header(None),
    origin: str | None = Header(default=None, alias="Origin"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Chat endpoint for SDK embedding (requires valid API key)."""
    await _ensure_chat_sdk_schema(db)
    from app.core.chat_engine import ChatEngine
    from app.database import get_redis

    if not x_api_key or not body.message:
        raise _cors_http_exception(status.HTTP_400_BAD_REQUEST, "API key and message required", origin)

    # Hash and verify API key
    api_key_hash = _hash_api_key(x_api_key)
    result = await db.execute(
        select(ChatDomain).where(ChatDomain.api_key == api_key_hash)
    )
    domain = result.scalar_one_or_none()

    if not domain or not domain.is_active:
        raise _cors_http_exception(status.HTTP_401_UNAUTHORIZED, "Invalid or inactive API key", origin)

    if domain.status != DomainStatus.approved.value:
        raise _cors_http_exception(status.HTTP_403_FORBIDDEN, "Domain not approved for chat", origin)
    if origin and not _is_origin_allowed(origin, domain.domain):
        raise _cors_http_exception(status.HTTP_403_FORBIDDEN, "Origin not allowed for this SDK domain", origin)

    # Update last used
    domain.last_used = datetime.now(UTC)
    await db.commit()

    # Per-visitor session isolation
    session_id = body.session_id or f"sdk_{uuid.uuid4().hex[:8]}"

    logger.info(
        "chat_sdk.message_received",
        domain=domain.domain,
        knowledge_ids=body.knowledge_ids,
        session_id=session_id,
    )

    # Load industry config and build system prompt
    system_prompt_override = None
    try:
        settings_result = await db.execute(
            select(AppSettings).where(AppSettings.id == "singleton")
        )
        settings = settings_result.scalars().first()
        if settings:
            if settings.industry_system_prompt:
                system_prompt_override = settings.industry_system_prompt
            elif settings.industry_name:
                topics = json.loads(settings.industry_topics) if isinstance(settings.industry_topics, str) else settings.industry_topics or []
                system_prompt_override = build_industry_system_prompt(
                    industry_name=settings.industry_name,
                    topics=topics,
                    tone=settings.industry_tone,
                    restriction_mode=settings.industry_restriction_mode,
                    company_name=settings.company_name
                )
    except Exception as e:
        logger.warning("chat_sdk.settings_load_error", error=str(e))

    # Process with ChatEngine
    start_ts = time.monotonic()
    ai_content = "I encountered an error processing your request. Please try again."
    model_used = "unknown"
    provider_used = "unknown"
    tokens_used = 0

    conv = await _get_or_create_sdk_conversation(db, session_id, domain.domain)
    user_msg = Message(
        conversation_id=conv.id,
        role=MessageRole.user.value,
        content=body.message,
    )
    db.add(user_msg)
    if not conv.title and conv.message_count == 0:
        conv.title = body.message.strip()[:80]
    await db.flush()

    try:
        redis_client = get_redis()
        engine = ChatEngine(db=db, redis=redis_client)
        result = await engine.process(
            message=body.message,
            conversation_id=conv.id,
            session_id=session_id,
            user_id=None,
            ai_config_id=None,
            use_knowledge=True,
            use_memory=False,
            tools_enabled=True,
            allowed_tools=None,
            context={"domain": domain.domain, "knowledge_ids": body.knowledge_ids},
            history=None,
            system_prompt_override=system_prompt_override,
        )
        ai_content = result.get("content", ai_content)
        model_used = result.get("model_used", "unknown")
        provider_used = result.get("provider_used", "unknown")
        tokens_used = result.get("tokens_used", 0)
    except Exception as exc:
        logger.error("chat_sdk.process_error", error=str(exc), domain=domain.domain)

    latency_ms = int((time.monotonic() - start_ts) * 1000)

    ai_msg = Message(
        conversation_id=conv.id,
        role=MessageRole.assistant.value,
        content=ai_content,
        tokens_used=tokens_used,
        model_used=model_used,
        provider_used=provider_used,
        latency_ms=latency_ms,
        cost_usd=0.0,
    )
    db.add(ai_msg)
    conv.message_count = (conv.message_count or 0) + 2
    conv.total_tokens = (conv.total_tokens or 0) + (tokens_used or 0)
    await db.commit()

    return JSONResponse(
        content={
            "response": ai_content,
            "domain": domain.domain,
            "model_used": model_used,
            "provider_used": provider_used,
            "tokens_used": tokens_used,
            "latency_ms": latency_ms,
            "sources": [],
            "timestamp": datetime.now(UTC).isoformat(),
            "session_id": session_id,
        },
        headers=_cors_headers(origin),
    )


def _sse_line(chunk: StreamChunk) -> str:
    """Format SSE line."""
    return f"data: {chunk.model_dump_json()}\n\n"


@router.post("/chat/stream")
async def stream_chat_with_knowledge(
    request: Request,
    background_tasks: BackgroundTasks,
    body: SDKChatRequest,
    x_api_key: str = Header(None),
    origin: str | None = Header(default=None, alias="Origin"),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Streaming chat endpoint for SDK embedding (requires valid API key)."""
    await _ensure_chat_sdk_schema(db)
    from app.core.chat_engine import ChatEngine
    from app.database import get_redis

    if not x_api_key or not body.message:
        raise _cors_http_exception(status.HTTP_400_BAD_REQUEST, "API key and message required", origin)

    # Hash and verify API key
    api_key_hash = _hash_api_key(x_api_key)
    result = await db.execute(
        select(ChatDomain).where(ChatDomain.api_key == api_key_hash)
    )
    domain = result.scalar_one_or_none()

    if not domain or not domain.is_active:
        raise _cors_http_exception(status.HTTP_401_UNAUTHORIZED, "Invalid or inactive API key", origin)

    if domain.status != DomainStatus.approved.value:
        raise _cors_http_exception(status.HTTP_403_FORBIDDEN, "Domain not approved for chat", origin)
    if origin and not _is_origin_allowed(origin, domain.domain):
        raise _cors_http_exception(status.HTTP_403_FORBIDDEN, "Origin not allowed for this SDK domain", origin)

    # Update last used
    domain.last_used = datetime.now(UTC)
    await db.commit()

    # Per-visitor session isolation
    session_id = body.session_id or f"sdk_{uuid.uuid4().hex[:8]}"

    # Load industry config and build system prompt
    system_prompt_override = None
    try:
        settings_result = await db.execute(
            select(AppSettings).where(AppSettings.id == "singleton")
        )
        settings = settings_result.scalars().first()
        if settings:
            if settings.industry_system_prompt:
                system_prompt_override = settings.industry_system_prompt
            elif settings.industry_name:
                topics = json.loads(settings.industry_topics) if isinstance(settings.industry_topics, str) else settings.industry_topics or []
                system_prompt_override = build_industry_system_prompt(
                    industry_name=settings.industry_name,
                    topics=topics,
                    tone=settings.industry_tone,
                    restriction_mode=settings.industry_restriction_mode,
                    company_name=settings.company_name
                )
    except Exception as e:
        logger.warning("chat_sdk.settings_load_error", error=str(e))

    logger.info(
        "chat_sdk.stream_started",
        domain=domain.domain,
        knowledge_ids=body.knowledge_ids,
        session_id=session_id,
    )

    conv = await _get_or_create_sdk_conversation(db, session_id, domain.domain)
    conv_id = conv.id
    msg_id = uuid.uuid4()
    user_msg = Message(
        conversation_id=conv_id,
        role=MessageRole.user.value,
        content=body.message,
    )
    db.add(user_msg)
    if not conv.title and conv.message_count == 0:
        conv.title = body.message.strip()[:80]
    await db.commit()

    start_ts = time.monotonic()

    async def event_generator() -> AsyncGenerator[str, None]:
        # Start event
        yield _sse_line(
            StreamChunk(
                event=StreamEventType.start,
                conversation_id=conv_id,
                message_id=msg_id,
            )
        )

        collected_text: list[str] = []
        tokens_used = 0
        cost_usd = 0.0
        model_used = "unknown"
        provider_used = "unknown"
        prompt_tokens = 0
        completion_tokens = 0

        try:
            redis_client = get_redis()
            engine = ChatEngine(db=db, redis=redis_client)

            async for delta in engine.stream(
                message=body.message,
                conversation_id=conv_id,
                session_id=session_id,
                user_id=None,
                ai_config_id=None,
                use_knowledge=True,
                use_memory=False,
                tools_enabled=True,
                allowed_tools=None,
                context={"domain": domain.domain, "knowledge_ids": body.knowledge_ids},
                system_prompt_override=system_prompt_override,
            ):
                if delta.get("type") == "text":
                    text_chunk = delta["content"]
                    collected_text.append(text_chunk)
                    yield _sse_line(
                        StreamChunk(event=StreamEventType.delta, text=text_chunk)
                    )
                elif delta.get("type") == "meta":
                    tokens_used = delta.get("tokens_used", 0)
                    cost_usd = delta.get("cost_usd", 0.0)
                    model_used = delta.get("model_used", model_used)
                    provider_used = delta.get("provider_used", provider_used)
                    prompt_tokens = delta.get("prompt_tokens", 0)
                    completion_tokens = delta.get("completion_tokens", 0)
        except Exception as exc:
            logger.error("chat_sdk.stream_error", error=str(exc), domain=domain.domain)
            error_msg = f"Error: {str(exc)[:100]}"
            collected_text.append(error_msg)
            yield _sse_line(StreamChunk(event=StreamEventType.delta, text=error_msg))

        latency_ms = int((time.monotonic() - start_ts) * 1000)
        full_content = "".join(collected_text)

        try:
            ai_msg = Message(
                id=msg_id,
                conversation_id=conv_id,
                role=MessageRole.assistant.value,
                content=full_content,
                tokens_used=tokens_used,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                model_used=model_used,
                provider_used=provider_used,
                latency_ms=latency_ms,
                cost_usd=cost_usd,
            )
            db.add(ai_msg)
            conv.message_count = (conv.message_count or 0) + 2
            conv.total_tokens = (conv.total_tokens or 0) + (tokens_used or 0)
            conv.total_cost_usd = (conv.total_cost_usd or 0.0) + (cost_usd or 0.0)
            await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.error("chat_sdk.stream_persist_error", error=str(exc), domain=domain.domain)

        yield _sse_line(
            StreamChunk(
                event=StreamEventType.done,
                message_id=msg_id,
                conversation_id=conv_id,
                tokens_used=tokens_used,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
            )
        )

        logger.info(
            "chat_sdk.stream_complete",
            domain=domain.domain,
            tokens=tokens_used,
            latency_ms=latency_ms,
        )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
            **_cors_headers(origin),
        },
    )


@router.get("/config")
async def get_sdk_config(
    x_api_key: str = Header(None),
    origin: str | None = Header(default=None, alias="Origin"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get SDK widget configuration (requires valid API key)."""
    await _ensure_chat_sdk_schema(db)
    if not x_api_key:
        raise _cors_http_exception(status.HTTP_401_UNAUTHORIZED, "API key required", origin)

    # Hash and verify API key
    api_key_hash = _hash_api_key(x_api_key)
    result = await db.execute(
        select(ChatDomain).where(ChatDomain.api_key == api_key_hash)
    )
    domain = result.scalar_one_or_none()

    if not domain or not domain.is_active:
        raise _cors_http_exception(status.HTTP_401_UNAUTHORIZED, "Invalid or inactive API key", origin)

    if domain.status != DomainStatus.approved.value:
        raise _cors_http_exception(status.HTTP_403_FORBIDDEN, "Domain not approved", origin)
    if origin and not _is_origin_allowed(origin, domain.domain):
        raise _cors_http_exception(status.HTTP_403_FORBIDDEN, "Origin not allowed for this SDK domain", origin)

    # Get default brand config from AppSettings
    app_settings = None
    try:
        settings_result = await db.execute(
            select(AppSettings).where(AppSettings.id == "singleton")
        )
        app_settings = settings_result.scalars().first()
    except Exception as exc:
        logger.warning("chat_sdk.config_settings_load_failed", error=str(exc))

    return JSONResponse(
        content={
            "bot_name": domain.bot_name or (getattr(app_settings, "brand_name", None) or "Assistant"),
            "welcome_message": domain.welcome_message or "How can I help you today?",
            "widget_color": (getattr(app_settings, "primary_color", None) or "#007bff"),
            "show_knowledge_sources": True,
            "domain": domain.domain,
            "display_name": domain.display_name,
        },
        headers=_cors_headers(origin),
    )


@router.options("/chat")
async def chat_preflight(request: Request):
    """Preflight handler for /chat endpoint."""
    return Response(status_code=204, headers=_cors_headers(request.headers.get("origin")))


@router.options("/chat/stream")
async def chat_stream_preflight(request: Request):
    """Preflight handler for /chat/stream endpoint."""
    return Response(status_code=204, headers=_cors_headers(request.headers.get("origin")))


@router.options("/config")
async def config_preflight(request: Request):
    """Preflight handler for /config endpoint."""
    return Response(status_code=204, headers=_cors_headers(request.headers.get("origin")))
