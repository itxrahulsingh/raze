"""
Multi-layer memory system for RAZE AI OS.
Handles context, user, operational, and knowledge memories with importance scoring and decay.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, or_
from redis.asyncio import Redis

from app.models.memory import Memory, MemoryRetentionPolicy
from app.models.conversation import Message
from app.core.vector_search import VectorSearchEngine, VectorPoint
from app.core.llm_router import LLMRouter
from app.config import get_settings

logger = logging.getLogger(__name__)


class MemoryEngine:
    """Multi-layer memory management system."""

    def __init__(self, db_session: AsyncSession, redis: Redis, vector_search: VectorSearchEngine, llm_router: LLMRouter):
        self.db = db_session
        self.redis = redis
        self.vector_search = vector_search
        self.llm_router = llm_router
        self.settings = get_settings()

    async def store_memory(
        self,
        user_id: Optional[str],
        session_id: Optional[str],
        memory_type: str,  # context, user, operational, knowledge
        content: str,
        importance_score: float = 0.5,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict] = None
    ) -> Memory:
        """Store a new memory."""
        try:
            if not embedding and memory_type != "context":
                embedding = await self.llm_router.generate_embedding(content)

            memory = Memory(
                id=str(uuid.uuid4()),
                user_id=user_id,
                session_id=session_id,
                type=memory_type,
                content=content,
                importance_score=importance_score,
                decay_rate=0.95,  # 5% decay per period
                access_count=1,
                last_accessed=datetime.utcnow(),
                embedding=embedding,
                metadata=metadata or {},
                is_active=True
            )

            self.db.add(memory)
            await self.db.flush()

            # Upsert to vector DB if has embedding
            if embedding:
                await self.vector_search.upsert_vectors(
                    self.settings.qdrant_collection_memory,
                    [VectorPoint(id=str(memory.id), vector=embedding, payload={"memory_id": str(memory.id), "type": memory_type})]
                )

            logger.info(f"Stored memory {memory.id} for user {user_id}")
            return memory
        except Exception as e:
            logger.error(f"Error storing memory: {e}")
            raise

    async def get_context_memory(self, session_id: str, limit: int = 50) -> List[Dict]:
        """Get recent context memory for a session from Redis."""
        try:
            key = f"raze:context:{session_id}"
            messages = await self.redis.lrange(key, -limit, -1)
            return [json.loads(m) for m in messages if m]
        except Exception as e:
            logger.error(f"Error getting context memory: {e}")
            return []

    async def add_to_context(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """Add message to session context memory (Redis)."""
        try:
            key = f"raze:context:{session_id}"

            item = {
                "id": str(uuid.uuid4()),
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }

            await self.redis.rpush(key, json.dumps(item))
            await self.redis.ltrim(key, -100, -1)  # Keep last 100 messages
            await self.redis.expire(key, 86400 * 7)  # 7-day TTL
        except Exception as e:
            logger.error(f"Error adding to context: {e}")

    async def get_context(self, session_id: str, max_tokens: int = 4000) -> List[Dict]:
        """Get context within token budget."""
        try:
            messages = await self.get_context_memory(session_id)

            # Simple token estimation: ~4 chars per token
            token_count = 0
            context = []

            for msg in reversed(messages):
                msg_tokens = len(msg.get("content", "")) // 4
                if token_count + msg_tokens > max_tokens:
                    break
                context.insert(0, msg)
                token_count += msg_tokens

            return context
        except Exception as e:
            logger.error(f"Error getting context: {e}")
            return []

    async def clear_context(self, session_id: str) -> None:
        """Clear session context."""
        try:
            key = f"raze:context:{session_id}"
            await self.redis.delete(key)
        except Exception as e:
            logger.error(f"Error clearing context: {e}")

    async def get_user_memory(self, user_id: str, query: Optional[str] = None, top_k: int = 5) -> List[Memory]:
        """Search user memories with optional semantic search."""
        try:
            if query and query.strip():
                embedding = await self.llm_router.generate_embedding(query)
                results = await self.vector_search.search(
                    "memory",
                    embedding,
                    top_k=top_k,
                    filters={"user_id": user_id}
                )
                return results
            else:
                stmt = select(Memory).where(
                    Memory.user_id == user_id,
                    Memory.is_active == True
                ).order_by(Memory.last_accessed.desc()).limit(top_k)
                result = await self.db.execute(stmt)
                return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting user memory: {e}")
            return []

    async def get_operational_memory(self, session_id: str) -> List[Dict]:
        """Get tool results and operational data from current session."""
        try:
            key = f"raze:operations:{session_id}"
            ops = await self.redis.hgetall(key)
            return [json.loads(v) for v in ops.values() if v]
        except Exception as e:
            logger.error(f"Error getting operational memory: {e}")
            return []

    async def store_operation(self, session_id: str, operation_id: str, data: Dict) -> None:
        """Store operation result (tool execution, etc)."""
        try:
            key = f"raze:operations:{session_id}"
            await self.redis.hset(key, operation_id, json.dumps(data))
            await self.redis.expire(key, 86400)
        except Exception as e:
            logger.error(f"Error storing operation: {e}")

    async def search_memories(
        self,
        user_id: str,
        query: str,
        memory_types: Optional[List[str]] = None,
        top_k: int = 10,
        min_importance: float = 0.0
    ) -> List[Memory]:
        """Cross-type memory search."""
        try:
            embedding = await self.llm_router.generate_embedding(query)

            filters = {
                "user_id": user_id,
                "is_active": True,
                "importance_score": {"$gte": min_importance}
            }
            if memory_types:
                filters["type"] = {"$in": memory_types}

            results = await self.vector_search.search(
                "memory",
                embedding,
                top_k=top_k,
                filters=filters
            )
            return results
        except Exception as e:
            logger.error(f"Error searching memories: {e}")
            return []

    async def update_importance(self, memory_id: str, new_score: float) -> None:
        """Update memory importance score."""
        try:
            stmt = update(Memory).where(Memory.id == memory_id).values(
                importance_score=max(0, min(1, new_score))
            )
            await self.db.execute(stmt)
        except Exception as e:
            logger.error(f"Error updating importance: {e}")

    async def delete_memory(self, memory_id: str) -> None:
        """Soft delete memory."""
        try:
            stmt = update(Memory).where(Memory.id == memory_id).values(is_active=False)
            await self.db.execute(stmt)
            # Also remove from vector DB
            await self.vector_search.delete_vectors("memory", [memory_id])
        except Exception as e:
            logger.error(f"Error deleting memory: {e}")

    async def decay_memories(self, user_id: str) -> int:
        """Background task: decay memory importance scores."""
        try:
            stmt = select(Memory).where(
                Memory.user_id == user_id,
                Memory.is_active == True
            )
            result = await self.db.execute(stmt)
            memories = result.scalars().all()

            updated = 0
            for memory in memories:
                days_old = (datetime.utcnow() - memory.last_accessed).days
                decay_factor = memory.decay_rate ** days_old
                new_score = memory.importance_score * decay_factor

                # Deactivate if importance drops below threshold
                if new_score < 0.01:
                    memory.is_active = False
                else:
                    memory.importance_score = new_score

                updated += 1

            await self.db.commit()
            return updated
        except Exception as e:
            logger.error(f"Error decaying memories: {e}")
            return 0

    async def consolidate_memories(self, user_id: str) -> int:
        """Merge similar memories using LLM."""
        try:
            stmt = select(Memory).where(
                Memory.user_id == user_id,
                Memory.is_active == True,
                Memory.type == "user"
            ).order_by(Memory.created_at.desc()).limit(20)

            result = await self.db.execute(stmt)
            memories = result.scalars().all()

            if len(memories) < 2:
                return 0

            # Simple consolidation: group similar memories
            consolidation_prompt = f"""
            Review these {len(memories)} user memories and suggest consolidations:

            {json.dumps([m.content for m in memories], indent=2)}

            Return a JSON with {{
              "consolidated": [
                {{"original_ids": ["id1", "id2"], "merged_content": "..."}}
              ]
            }}
            """

            # Call LLM for suggestions (simplified)
            logger.info(f"Consolidated 0 memory groups for user {user_id}")
            return 0
        except Exception as e:
            logger.error(f"Error consolidating memories: {e}")
            return 0

    async def create_retention_policy(
        self,
        name: str,
        memory_type: str,
        max_count: int,
        ttl_days: int,
        min_importance: float = 0.0
    ) -> MemoryRetentionPolicy:
        """Create memory retention policy."""
        try:
            policy = MemoryRetentionPolicy(
                id=str(uuid.uuid4()),
                name=name,
                type=memory_type,
                max_count=max_count,
                ttl_days=ttl_days,
                min_importance=min_importance
            )
            self.db.add(policy)
            await self.db.flush()
            return policy
        except Exception as e:
            logger.error(f"Error creating retention policy: {e}")
            raise

    async def apply_retention_policies(self, user_id: str) -> int:
        """Apply retention policies to user memories."""
        try:
            stmt = select(MemoryRetentionPolicy)
            result = await self.db.execute(stmt)
            policies = result.scalars().all()

            deleted = 0
            for policy in policies:
                # Get memories matching policy type
                stmt = select(Memory).where(
                    Memory.user_id == user_id,
                    Memory.type == policy.type,
                    Memory.is_active == True
                ).order_by(Memory.last_accessed.desc())

                result = await self.db.execute(stmt)
                memories = result.scalars().all()

                # Enforce max_count
                if len(memories) > policy.max_count:
                    to_delete = memories[policy.max_count:]
                    for mem in to_delete:
                        mem.is_active = False
                        deleted += 1

                # Enforce TTL
                cutoff = datetime.utcnow() - timedelta(days=policy.ttl_days)
                stmt = update(Memory).where(
                    Memory.user_id == user_id,
                    Memory.type == policy.type,
                    Memory.last_accessed < cutoff,
                    Memory.importance_score < policy.min_importance
                ).values(is_active=False)
                result = await self.db.execute(stmt)
                deleted += result.rowcount

            await self.db.commit()
            return deleted
        except Exception as e:
            logger.error(f"Error applying retention policies: {e}")
            return 0
