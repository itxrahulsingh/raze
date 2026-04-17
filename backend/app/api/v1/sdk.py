"""SDK-specific API routes for embeddable chat widget."""
from fastapi import APIRouter, Depends, HTTPException, Header, Cookie, Request
from fastapi.responses import StreamingResponse
import json
import uuid
from typing import Optional

from app.database import get_db, get_redis
from app.models.user import APIKey
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from app.api.v1 import deps

from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/sdk", tags=["sdk"])

@router.post("/init")
async def init_chat_session(
    request: Request,
    x_api_key: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """Initialize a chat session for SDK."""
    await deps.apply_rate_limit(request, "sdk_init", 10, 60)
    # Validate API key if provided
    if x_api_key:
        result = await db.execute(
            select(APIKey).where(APIKey.key_hash == x_api_key)
        )
        api_key = result.scalar_one_or_none()
        if not api_key or not api_key.is_active:
            raise HTTPException(status_code=401, detail="Invalid API key")

    # Generate session ID
    session_id = str(uuid.uuid4())

    # Store in Redis
    await redis.setex(f"raze:session:{session_id}", 86400 * 30, json.dumps({
        "created_at": str(__import__('datetime').datetime.utcnow()),
        "api_key": x_api_key
    }))

    return {
        "session_id": session_id,
        "expires_in": 2592000,  # 30 days
        "config": {
            "bot_name": "RAZE AI",
            "welcome_message": "Hi! I'm RAZE AI. How can I help you?",
            "theme": {
                "primary_color": "#7C3AED",
                "text_color": "#1F2937",
                "background_color": "#FFFFFF"
            }
        }
    }

@router.post("/message")
async def send_message(
    request_body: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """Send message via SDK (non-streaming)."""
    await deps.apply_rate_limit(request, "sdk_message", 10, 60)
    # Validate session exists
    session_data = await redis.get(f"raze:session:{request_body.session_id}")
    if not session_data:
        raise HTTPException(status_code=401, detail="Invalid session")

    # Process message (would call orchestrator)
    return {
        "message_id": str(uuid.uuid4()),
        "content": "This is a response from RAZE AI.",
        "timestamp": __import__('datetime').datetime.utcnow().isoformat()
    }

@router.post("/stream")
async def stream_message(
    request_body: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """Send message via SDK (streaming response)."""
    await deps.apply_rate_limit(request, "sdk_stream", 10, 60)
    # Validate session
    session_data = await redis.get(f"raze:session:{request_body.session_id}")
    if not session_data:
        raise HTTPException(status_code=401, detail="Invalid session")

    async def generate():
        # Simulate streaming response
        response = "This is a streamed response from RAZE AI."
        for char in response:
            yield f"data: {json.dumps({'type': 'text', 'content': char})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

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
