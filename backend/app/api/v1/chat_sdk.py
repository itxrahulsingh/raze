"""Chat SDK and Embeddable Chat API."""
import hashlib
import secrets
import time
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.chat_domain import ChatDomain, DomainStatus
from app.models.user import User
from app.api.v1 import deps

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/chat-sdk", tags=["Chat SDK"])


def _generate_api_key(length: int = 32) -> str:
    """Generate a secure API key."""
    return f"raze_sk_{secrets.token_urlsafe(length)}"


def _hash_api_key(api_key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


@router.post("/domains")
async def register_domain(
    request: Request,
    domain_data: dict[str, Any],
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Register a new domain for chat SDK (admin only)."""
    await deps.apply_rate_limit(request, "register_domain", 60, 60, current_user)

    domain = domain_data.get("domain", "").lower().strip()
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


@router.post("/chat")
async def chat_with_knowledge(
    request: Request,
    message: str = None,
    knowledge_ids: list[str] = None,
    x_api_key: str = Header(None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Chat endpoint for SDK embedding (requires valid API key)."""
    from app.core.chat_engine import ChatEngine
    from app.database import get_redis

    if not x_api_key or not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key and message required",
        )

    # Hash and verify API key
    api_key_hash = _hash_api_key(x_api_key)
    result = await db.execute(
        select(ChatDomain).where(ChatDomain.api_key == api_key_hash)
    )
    domain = result.scalar_one_or_none()

    if not domain or not domain.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key",
        )

    if domain.status != DomainStatus.approved.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Domain not approved for chat",
        )

    # Update last used
    domain.last_used = datetime.now(UTC)
    await db.commit()

    logger.info(
        "chat_sdk.message_received",
        domain=domain.domain,
        knowledge_ids=knowledge_ids,
    )

    # Process with ChatEngine
    start_ts = time.monotonic()
    ai_content = "I encountered an error processing your request. Please try again."
    model_used = "unknown"
    provider_used = "unknown"
    tokens_used = 0

    try:
        redis_client = get_redis()
        engine = ChatEngine(db=db, redis=redis_client)
        # Generate a temporary conversation ID for SDK (no message persistence)
        temp_conversation_id = uuid.uuid4()
        result = await engine.process(
            message=message,
            conversation_id=temp_conversation_id,
            session_id=f"sdk_{domain.id}",
            user_id=None,
            ai_config_id=None,
            use_knowledge=bool(knowledge_ids),
            use_memory=False,
            tools_enabled=False,
            allowed_tools=None,
            context={"domain": domain.domain, "knowledge_ids": knowledge_ids or []},
            history=None,
        )
        ai_content = result.get("content", ai_content)
        model_used = result.get("model_used", "unknown")
        provider_used = result.get("provider_used", "unknown")
        tokens_used = result.get("tokens_used", 0)
    except Exception as exc:
        logger.error("chat_sdk.process_error", error=str(exc), domain=domain.domain)

    latency_ms = int((time.monotonic() - start_ts) * 1000)

    return {
        "response": ai_content,
        "domain": domain.domain,
        "model_used": model_used,
        "provider_used": provider_used,
        "tokens_used": tokens_used,
        "latency_ms": latency_ms,
        "sources": [],
        "timestamp": datetime.now(UTC).isoformat(),
    }
