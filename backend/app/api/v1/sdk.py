"""
RAZE Enterprise AI OS — Modern Chat SDK API

Provides:
  - Session-based chat with SSE streaming
  - Knowledge base integration
  - Memory persistence
  - Tool/function calling
  - Admin control & rate limiting
  - Message cards (ChatGPT-style UI components)
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, UTC
from typing import Any, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.api.v1 import deps
from app.database import get_db, get_redis
from app.models.user import APIKey
from app.schemas.chat import ChatRequest, ChatResponse

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/sdk", tags=["sdk"])


# ─── Session Management ───────────────────────────────────────────────────────


@router.post("/init", summary="Initialize chat session", tags=["SDK"])
async def init_chat_session(
    request: Request,
    x_api_key: Optional[str] = Header(None),
    widget_id: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict[str, Any]:
    """
    Initialize a new chat session for SDK embedding.

    Returns session token valid for 30 days.

    Args:
        x_api_key: SDK API key for auth
        widget_id: Optional widget identifier for analytics
    """
    await deps.apply_rate_limit(request, "sdk_init", limit=10, window_seconds=60)

    # Validate API key if provided
    if x_api_key:
        result = await db.execute(
            select(APIKey).where(APIKey.key_hash == x_api_key)
        )
        api_key = result.scalar_one_or_none()
        if not api_key or not api_key.is_active:
            logger.warning("sdk_init_invalid_key", api_key=x_api_key)
            raise HTTPException(
                status_code=401, detail="Invalid or expired API key"
            )

    # Generate session
    session_id = str(uuid.uuid4())
    session_data = {
        "session_id": session_id,
        "created_at": datetime.now(UTC).isoformat(),
        "api_key": x_api_key,
        "widget_id": widget_id,
        "messages_count": 0,
    }

    # Store in Redis (30 days TTL)
    await redis.setex(
        f"raze:sdk_session:{session_id}",
        86400 * 30,
        json.dumps(session_data),
    )

    logger.info("sdk_session_created", session_id=session_id, widget_id=widget_id)

    return {
        "session_id": session_id,
        "expires_in": 2592000,  # 30 days in seconds
        "config": {
            "bot_name": "RAZE AI Assistant",
            "welcome_message": "Hello! I'm RAZE AI. How can I help you today?",
            "capabilities": [
                "answer_questions",
                "search_knowledge",
                "tool_calling",
                "memory_persistence",
            ],
            "theme": {
                "primary_color": "#7C3AED",
                "accent_color": "#06B6D4",
                "text_color": "#1F2937",
                "background_color": "#FFFFFF",
                "border_radius": "8px",
            },
            "features": {
                "show_knowledge_sources": True,
                "show_typing_indicator": True,
                "enable_file_upload": False,
                "enable_voice": False,
            },
        },
    }


# ─── Message Sending ──────────────────────────────────────────────────────────


@router.post("/message", response_model=ChatResponse, summary="Send message (non-streaming)")
async def send_message(
    body: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> ChatResponse:
    """
    Send message via SDK (non-streaming response).

    Best for one-off queries or client-side streaming UI.

    Args:
        body: ChatRequest with message content
    """
    await deps.apply_rate_limit(request, "sdk_message", limit=30, window_seconds=60)

    # Validate session
    session_key = f"raze:sdk_session:{body.session_id}"
    session_data = await redis.get(session_key)
    if not session_data:
        logger.warning("sdk_message_invalid_session", session_id=body.session_id)
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    start_time = time.time()

    try:
        # Import chat engine (lazy to avoid circular imports)
        from app.core.chat_engine import ChatEngine

        engine = ChatEngine(db=db, redis=redis)

        # Process message
        result = await engine.process(
            message=body.message,
            conversation_id=None,  # SDK doesn't maintain conversations
            session_id=body.session_id,
            user_id=None,
            use_knowledge=body.use_knowledge if hasattr(body, "use_knowledge") else True,
            use_memory=body.use_memory if hasattr(body, "use_memory") else True,
            tools_enabled=body.tools_enabled if hasattr(body, "tools_enabled") else True,
        )

        latency_ms = (time.time() - start_time) * 1000

        # Update session message count
        session = json.loads(session_data)
        session["messages_count"] = session.get("messages_count", 0) + 1
        await redis.setex(session_key, 86400 * 30, json.dumps(session))

        logger.info(
            "sdk_message_sent",
            session_id=body.session_id,
            latency_ms=round(latency_ms, 2),
        )

        return ChatResponse(
            message=result.get("message", ""),
            message_id=str(uuid.uuid4()),
            timestamp=datetime.now(UTC).isoformat(),
        )

    except Exception as e:
        logger.error("sdk_message_error", session_id=body.session_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to process message")


# ─── Streaming Messages ───────────────────────────────────────────────────────


@router.post(
    "/stream",
    response_class=StreamingResponse,
    summary="Send message (streaming SSE)",
)
async def stream_message(
    body: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> StreamingResponse:
    """
    Send message via SDK with Server-Sent Events streaming.

    Returns token-by-token streaming response. Best for real-time UX.

    Streaming format:
    ```
    data: {"type": "text", "content": "Hello"}
    data: {"type": "text", "content": " world"}
    data: {"type": "done", "message_id": "uuid"}
    ```
    """
    await deps.apply_rate_limit(request, "sdk_stream", limit=30, window_seconds=60)

    # Validate session
    session_key = f"raze:sdk_session:{body.session_id}"
    session_data = await redis.get(session_key)
    if not session_data:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    async def generate() -> Any:
        """Stream chat response tokens."""
        try:
            from app.core.chat_engine import ChatEngine

            engine = ChatEngine(db=db, redis=redis)
            message_id = str(uuid.uuid4())

            # Send typing indicator
            yield f"data: {json.dumps({'type': 'typing', 'status': 'start'})}\n\n"

            # Stream response
            accumulated = ""
            async for token in engine.stream_message(body.message):
                accumulated += token
                yield f"data: {json.dumps({'type': 'text', 'content': token})}\n\n"

            # Send completion with metadata
            yield f"data: {json.dumps({'type': 'done', 'message_id': message_id, 'total_tokens': len(accumulated.split())})}\n\n"

            # Update session count
            session = json.loads(session_data)
            session["messages_count"] = session.get("messages_count", 0) + 1
            await redis.setex(session_key, 86400 * 30, json.dumps(session))

        except Exception as e:
            logger.error("sdk_stream_error", session_id=body.session_id, error=str(e))
            yield f"data: {json.dumps({'type': 'error', 'message': 'Stream failed'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ─── Card/Component Rendering ─────────────────────────────────────────────────


@router.post("/card", summary="Render interactive card", tags=["SDK"])
async def render_card(
    body: dict[str, Any],
    request: Request,
    redis: Redis = Depends(get_redis),
) -> dict[str, Any]:
    """
    Render interactive card components (ChatGPT-style).

    Supported card types:
    - text: Plain text or markdown
    - code: Code block with syntax highlighting
    - table: Data table
    - image: Image with metadata
    - button: Clickable action
    - form: Input form
    """
    await deps.apply_rate_limit(request, "sdk_card", limit=60, window_seconds=60)

    card_type = body.get("type", "text")
    content = body.get("content", "")

    return {
        "card_id": str(uuid.uuid4()),
        "type": card_type,
        "content": content,
        "timestamp": datetime.now(UTC).isoformat(),
        "interactive": card_type in ["button", "form"],
    }


# ─── Knowledge Search ─────────────────────────────────────────────────────────


@router.post("/knowledge/search", summary="Search knowledge base via SDK", tags=["SDK"])
async def search_knowledge(
    query: dict[str, str],
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict[str, Any]:
    """
    Search the knowledge base directly.

    Useful for autocomplete, suggestions, or hybrid search in UI.
    """
    await deps.apply_rate_limit(
        request, "sdk_knowledge_search", limit=120, window_seconds=60
    )

    search_query = query.get("q", "")
    try:
        limit = max(1, min(50, int(query.get("limit", 5))))
    except Exception:
        limit = 5

    if not search_query:
        raise HTTPException(status_code=400, detail="Query required")

    try:
        from app.core.knowledge_engine import KnowledgeEngine
        from app.core.llm_router import LLMRouter
        from app.core.vector_search import VectorSearchEngine

        llm = LLMRouter()
        vs = VectorSearchEngine()
        engine = KnowledgeEngine(db, llm, vs)

        results = await engine.search_knowledge(
            query=search_query,
            top_k=limit,
            score_threshold=0.2,
            approved_only=True,
            use_case="search",
        )

        return {
            "query": search_query,
            "results": results,
            "total": len(results),
        }

    except Exception as e:
        logger.error("sdk_knowledge_search_error", query=search_query, error=str(e))
        raise HTTPException(status_code=500, detail="Search failed")


# ─── Session Info ─────────────────────────────────────────────────────────────


@router.get("/session/{session_id}", summary="Get session info", tags=["SDK"])
async def get_session_info(
    session_id: str,
    request: Request,
    redis: Redis = Depends(get_redis),
) -> dict[str, Any]:
    """Get current session status and metadata."""
    await deps.apply_rate_limit(request, "sdk_session_info", limit=60, window_seconds=60)

    session_key = f"raze:sdk_session:{session_id}"
    session_data = await redis.get(session_key)

    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")

    session = json.loads(session_data)
    ttl = await redis.ttl(session_key)

    return {
        "session_id": session_id,
        "messages_count": session.get("messages_count", 0),
        "created_at": session.get("created_at"),
        "expires_in": ttl if ttl > 0 else 0,
        "active": ttl > 0,
    }


@router.get("/config")
async def get_public_config(
    request: Request,
    x_api_key: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Get public SDK configuration."""
    await deps.apply_rate_limit(request, "sdk_config", 10, 60)
    # Validate API key
    if x_api_key:
        result = await db.execute(
            select(APIKey).where(APIKey.key_hash == x_api_key)
        )
        api_key = result.scalar_one_or_none()
        if not api_key or not api_key.is_active:
            raise HTTPException(status_code=401)

    return {
        "bot_name": "RAZE AI",
        "welcome_message": "Welcome to RAZE AI!",
        "placeholder": "Type your message...",
        "show_powered_by": True,
        "theme": {
            "primary_color": "#7C3AED",
            "text_color": "#1F2937",
            "background_color": "#FFFFFF",
            "border_color": "#E5E7EB"
        },
        "supported_features": [
            "streaming",
            "file_upload",
            "tool_execution",
            "markdown"
        ]
    }
