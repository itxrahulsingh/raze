"""
RAZE Enterprise AI OS – Chat Routes

Covers:
  POST /chat/message                          – non-streaming chat
  POST /chat/stream                           – SSE streaming chat
  GET  /chat/conversations                    – list conversations (paginated)
  GET  /chat/conversations/{id}               – get conversation + messages
  DELETE /chat/conversations/{id}             – delete conversation
  GET  /chat/conversations/{id}/messages      – get messages (paginated)
  POST /chat/conversations/{id}/export        – export as JSON / CSV / PDF

Auth: supports JWT Bearer OR X-API-Key header OR anonymous session_id cookie.
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
import time
import uuid
from datetime import UTC, datetime
from typing import Any, AsyncGenerator

import structlog
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Cookie,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import get_db, get_redis
from app.models.analytics import UserSession
from app.models.conversation import Conversation, ConversationStatus, Message, MessageRole
from app.models.user import APIKey, User
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationListResponse,
    ConversationResponse,
    MessageListResponse,
    MessageResponse,
    StreamChunk,
    StreamEventType,
)
from app.core.security import get_current_user, verify_api_key
from app.api.v1.deps import apply_rate_limit

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])


# ─── Flexible Auth Dependency ─────────────────────────────────────────────────


async def get_optional_user(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    session_id: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    Attempt JWT auth, then API key auth, then fall through to None
    (anonymous SDK users identified only by session_id cookie).
    """
    from app.core.security import verify_token

    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        try:
            payload = verify_token(token, expected_type="access")
            user_id: str | None = payload.get("sub")
            if user_id:
                result = await db.execute(select(User).where(User.id == user_id))
                user: User | None = result.scalar_one_or_none()
                if user and user.is_active:
                    return user
        except HTTPException:
            pass

    if x_api_key:
        try:
            return await verify_api_key(api_key=x_api_key, db=db)
        except HTTPException:
            pass

    return None


# ─── Session Tracking ─────────────────────────────────────────────────────────


async def _upsert_session(
    session_id: str,
    db: AsyncSession,
    user_id: uuid.UUID | None,
    request: Request,
) -> None:
    """Create or update the UserSession row for analytics tracking."""
    user_agent = request.headers.get("user-agent", "")
    ip_address = request.client.host if request.client else None

    existing = await db.execute(
        select(UserSession).where(UserSession.session_id == session_id).order_by(UserSession.created_at.desc()).limit(1)
    )
    us: UserSession | None = existing.scalars().first()

    now = datetime.now(UTC)
    if us is None:
        us = UserSession(
            session_id=session_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            started_at=now,
            last_seen=now,
            message_count=1,
            is_active=True,
        )
        db.add(us)
    else:
        us.last_seen = now
        us.message_count = (us.message_count or 0) + 1
        if user_id and us.user_id is None:
            us.user_id = user_id


# ─── Conversation Helpers ─────────────────────────────────────────────────────


async def _get_or_create_conversation(
    session_id: str,
    db: AsyncSession,
    user_id: uuid.UUID | None,
    ai_config_id: uuid.UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> Conversation:
    """Return the active conversation for the session, creating one if needed."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.session_id == session_id,
            Conversation.status == ConversationStatus.active.value,
        )
    )
    conv: Conversation | None = result.scalar_one_or_none()
    if conv is None:
        now = datetime.now(UTC)
        conv = Conversation(
            session_id=session_id,
            user_id=user_id,
            status=ConversationStatus.active.value,
            message_count=0,
            total_tokens=0,
            total_cost_usd=0.0,
            started_at=now,
            ai_config_id=ai_config_id,
            conv_metadata=metadata or {},
        )
        db.add(conv)
        await db.flush()
    return conv


async def _persist_message(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    role: str,
    content: str | None,
    *,
    tool_calls: list[dict] | None = None,
    tool_results: list[dict] | None = None,
    tokens_used: int | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    model_used: str | None = None,
    provider_used: str | None = None,
    latency_ms: int | None = None,
    cost_usd: float | None = None,
    is_error: bool = False,
    error_code: str | None = None,
) -> Message:
    msg = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        tool_calls=tool_calls,
        tool_results=tool_results,
        tokens_used=tokens_used,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        model_used=model_used,
        provider_used=provider_used,
        latency_ms=latency_ms,
        cost_usd=cost_usd,
        is_error=is_error,
        error_code=error_code,
    )
    db.add(msg)
    await db.flush()
    return msg


def _sse_line(chunk: StreamChunk) -> str:
    return f"data: {chunk.model_dump_json()}\n\n"


# ─── POST /chat/message ───────────────────────────────────────────────────────


@router.post(
    "/message",
    response_model=ChatResponse,
    summary="Send a message (non-streaming)",
    status_code=status.HTTP_200_OK,
)
async def send_message(
    body: ChatRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """
    Process a user message and return the full AI response.
    Session tracking and conversation state management are handled automatically.
    """
    await apply_rate_limit(request, "chat_message", 30, 60, current_user)
    settings = get_settings()
    session_id = body.session_id or str(uuid.uuid4())
    user_id = current_user.id if current_user else None

    # Upsert session analytics
    background_tasks.add_task(_upsert_session, session_id, db, user_id, request)

    # Collect metadata from request
    metadata = body.chat_metadata or {}
    metadata.setdefault('ip_address', request.client.host if request.client else None)
    metadata.setdefault('user_agent', request.headers.get('user-agent', ''))

    conv = await _get_or_create_conversation(
        session_id, db, user_id, body.ai_config_id, metadata
    )

    # Persist user message
    user_msg = await _persist_message(
        db,
        conv.id,
        MessageRole.user.value,
        body.message,
    )

    # Generate title from first message if not set
    if not conv.title and conv.message_count == 0:
        # Take first 50 chars or first sentence
        title = body.message.strip()[:50]
        if len(body.message) > 50:
            # Try to cut at sentence boundary
            period_idx = body.message.find('.', 40)
            if period_idx > 0:
                title = body.message[:period_idx + 1]
        conv.title = title
        await db.flush()

    start_ts = time.monotonic()

    # --- AI Engine call ---
    try:
        from app.core.chat_engine import ChatEngine

        redis_client = get_redis()
        engine = ChatEngine(db=db, redis=redis_client)
        result = await engine.process(
            message=body.message,
            conversation_id=conv.id,
            session_id=session_id,
            user_id=user_id,
            ai_config_id=body.ai_config_id,
            use_knowledge=body.use_knowledge,
            use_memory=body.use_memory,
            tools_enabled=body.tools_enabled,
            allowed_tools=body.allowed_tools,
            context=body.context,
            history=body.history,
        )
        ai_content = result["content"]
        model_used = result.get("model_used", settings.openai_default_model)
        provider_used = result.get("provider_used", "openai")
        tokens_used = result.get("tokens_used", 0)
        prompt_tokens = result.get("prompt_tokens", 0)
        completion_tokens = result.get("completion_tokens", 0)
        cost_usd = result.get("cost_usd", 0.0)
        knowledge_chunks_used = result.get("knowledge_chunks_used", 0)
        memory_items_used = result.get("memory_items_used", 0)
        tool_calls = result.get("tool_calls")
        tool_results = result.get("tool_results")
    except Exception as exc:
        logger.error("chat.process_error", error=str(exc))
        ai_content = "I encountered an error processing your request. Please try again."
        model_used = settings.openai_default_model
        provider_used = "openai"
        tokens_used = 0
        prompt_tokens = 0
        completion_tokens = 0
        cost_usd = 0.0
        knowledge_chunks_used = 0
        memory_items_used = 0
        tool_calls = None
        tool_results = None

    latency_ms = int((time.monotonic() - start_ts) * 1000)

    # Persist AI response
    ai_msg = await _persist_message(
        db,
        conv.id,
        MessageRole.assistant.value,
        ai_content,
        tool_calls=tool_calls,
        tool_results=tool_results,
        tokens_used=tokens_used,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        model_used=model_used,
        provider_used=provider_used,
        latency_ms=latency_ms,
        cost_usd=cost_usd,
    )

    # Update conversation stats
    conv.message_count = (conv.message_count or 0) + 2
    conv.total_tokens = (conv.total_tokens or 0) + tokens_used
    conv.total_cost_usd = (conv.total_cost_usd or 0.0) + cost_usd
    await db.commit()

    return ChatResponse(
        message_id=ai_msg.id,
        conversation_id=conv.id,
        session_id=session_id,
        content=ai_content,
        tool_calls=tool_calls,
        tool_results=tool_results,
        model_used=model_used,
        provider_used=provider_used,
        tokens_used=tokens_used,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        knowledge_chunks_used=knowledge_chunks_used,
        memory_items_used=memory_items_used,
        created_at=ai_msg.created_at,
    )


# ─── POST /chat/stream ────────────────────────────────────────────────────────


@router.post(
    "/stream",
    summary="Send a message (SSE streaming)",
    response_class=StreamingResponse,
)
async def stream_message(
    body: ChatRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Stream the AI response as Server-Sent Events.

    SSE format::

        data: {"event": "start", "conversation_id": "...", "message_id": "..."}\n\n
        data: {"event": "delta", "text": "Hello"}\n\n
        data: {"event": "done", "message_id": "...", "tokens_used": 42}\n\n
    """
    await apply_rate_limit(request, "chat_stream", 10, 60, current_user)
    settings = get_settings()
    session_id = body.session_id or str(uuid.uuid4())
    user_id = current_user.id if current_user else None

    background_tasks.add_task(_upsert_session, session_id, db, user_id, request)

    # Collect metadata from request
    metadata = body.chat_metadata or {}
    metadata.setdefault('ip_address', request.client.host if request.client else None)
    metadata.setdefault('user_agent', request.headers.get('user-agent', ''))

    conv = await _get_or_create_conversation(
        session_id, db, user_id, body.ai_config_id, metadata
    )
    conv_id = conv.id

    # Persist user message immediately
    user_msg = await _persist_message(
        db, conv_id, MessageRole.user.value, body.message
    )

    # Generate title from first message if not set
    if not conv.title and conv.message_count == 0:
        # Take first 50 chars or first sentence
        title = body.message.strip()[:50]
        if len(body.message) > 50:
            # Try to cut at sentence boundary
            period_idx = body.message.find('.', 40)
            if period_idx > 0:
                title = body.message[:period_idx + 1]
        conv.title = title

    await db.commit()

    msg_id = uuid.uuid4()
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
        model_used = settings.openai_default_model
        provider_used = "openai"
        prompt_tokens = 0
        completion_tokens = 0

        try:
            from app.core.chat_engine import ChatEngine

            _redis = get_redis()
            engine = ChatEngine(db=db, redis=_redis)
            async for delta in engine.stream(
                message=body.message,
                conversation_id=conv_id,
                session_id=session_id,
                user_id=user_id,
                ai_config_id=body.ai_config_id,
                use_knowledge=body.use_knowledge,
                use_memory=body.use_memory,
                tools_enabled=body.tools_enabled,
                allowed_tools=body.allowed_tools,
                context=body.context,
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
            logger.error("chat.stream_error", error=str(exc))
            error_msg = "An error occurred while generating the response."
            collected_text.append(error_msg)
            yield _sse_line(StreamChunk(event=StreamEventType.delta, text=error_msg))

        latency_ms = int((time.monotonic() - start_ts) * 1000)
        full_content = "".join(collected_text)

        # Persist AI message in background using a fresh session
        async def _persist_async() -> None:
            from app.database import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
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
                    session.add(ai_msg)
                    await session.commit()
                except Exception as exc:
                    logger.error("chat.stream_persist_error", error=str(exc))

        background_tasks.add_task(_persist_async)

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

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ─── GET /chat/conversations ──────────────────────────────────────────────────


@router.get(
    "/conversations",
    response_model=ConversationListResponse,
    summary="List conversations (paginated)",
)
async def list_conversations(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationListResponse:
    """
    Return a paginated list of conversations.  Authenticated users see their own
    conversations; anonymous callers receive an empty list.
    """
    await apply_rate_limit(request, "chat_conversations_list", 30, 60, current_user)
    if current_user is None:
        return ConversationListResponse(items=[], total=0, page=page, page_size=page_size)

    q = select(Conversation).where(Conversation.user_id == current_user.id)
    if status_filter:
        q = q.where(Conversation.status == status_filter)

    count_q = select(func.count()).select_from(q.subquery())
    total_result = await db.execute(count_q)
    total = total_result.scalar_one()

    q = q.order_by(Conversation.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    convs = result.scalars().all()

    return ConversationListResponse(
        items=list(convs),
        total=total,
        page=page,
        page_size=page_size,
    )


# ─── GET /chat/conversations/{id} ─────────────────────────────────────────────


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
    summary="Get conversation detail",
)
async def get_conversation(
    conversation_id: uuid.UUID,
    request: Request,
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> Conversation:
    """Return conversation metadata.  Ownership is enforced for authenticated users."""
    await apply_rate_limit(request, "chat_conversations_get", 30, 60, current_user)
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv: Conversation | None = result.scalar_one_or_none()
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    if current_user and conv.user_id and conv.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return conv


# ─── DELETE /chat/conversations/{id} ─────────────────────────────────────────


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    response_class=Response,
    summary="Delete conversation",
)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Hard-delete a conversation and all its messages."""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv: Conversation | None = result.scalar_one_or_none()
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    if conv.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    await db.delete(conv)
    await db.commit()
    logger.info("chat.conversation_deleted", conversation_id=str(conversation_id))


# ─── GET /chat/conversations/{id}/messages ────────────────────────────────────


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=MessageListResponse,
    summary="Get messages for a conversation (paginated)",
)
async def list_messages(
    conversation_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> MessageListResponse:
    """Return paginated messages for a conversation."""
    # Verify conversation access
    conv_result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv: Conversation | None = conv_result.scalar_one_or_none()
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    if current_user and conv.user_id and conv.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    q = select(Message).where(Message.conversation_id == conversation_id)
    count_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = count_result.scalar_one()

    q = q.order_by(Message.created_at.asc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    messages = result.scalars().all()

    return MessageListResponse(
        items=list(messages),
        total=total,
        conversation_id=conversation_id,
    )


# ─── POST /chat/conversations/{id}/export ─────────────────────────────────────


@router.post(
    "/conversations/{conversation_id}/export",
    summary="Export conversation as JSON or CSV",
)
async def export_conversation(
    conversation_id: uuid.UUID,
    format: str = Query(default="json", pattern="^(json|csv)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Export all messages in a conversation.

    - ``format=json`` returns a JSON array of message objects.
    - ``format=csv``  returns a CSV file with columns: role, content, created_at.
    """
    conv_result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(selectinload(Conversation.messages))
    )
    conv: Conversation | None = conv_result.scalar_one_or_none()
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    if conv.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    messages = sorted(conv.messages, key=lambda m: m.created_at)

    if format == "json":
        data = [
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "model_used": m.model_used,
                "tokens_used": m.tokens_used,
                "cost_usd": m.cost_usd,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ]
        return Response(
            content=json.dumps(data, indent=2),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="conversation_{conversation_id}.json"'
            },
        )

    # CSV export
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf, fieldnames=["id", "role", "content", "model_used", "tokens_used", "created_at"]
    )
    writer.writeheader()
    for m in messages:
        writer.writerow(
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content or "",
                "model_used": m.model_used or "",
                "tokens_used": m.tokens_used or 0,
                "created_at": m.created_at.isoformat(),
            }
        )

    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="conversation_{conversation_id}.csv"'
        },
    )
