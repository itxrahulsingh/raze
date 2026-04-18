"""
RAZE Enterprise AI OS – ChatEngine

The single entry point for all chat requests. Wires together:
  - Session memory (Redis via MemoryEngine)
  - User long-term memory (pgvector + Qdrant via MemoryEngine)
  - Knowledge base retrieval (hybrid search via KnowledgeEngine)
  - Tool/action execution (ToolEngine)
  - Multi-LLM generation with routing and failover (LLMRouter)
  - Observability logging (ObservabilityEngine)

Supports both non-streaming (process) and streaming (stream) modes.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, AsyncGenerator

import structlog
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.llm_router import LLMRouter, count_message_tokens
from app.core.memory_engine import MemoryEngine
from app.core.knowledge_engine import KnowledgeEngine
from app.core.tool_engine import ToolEngine
from app.core.vector_search import VectorSearchEngine
from app.database import get_redis
from app.models.ai_config import AIConfig

settings = get_settings()
logger = structlog.get_logger(__name__)

_DEFAULT_SYSTEM_PROMPT = """You are RAZE, an enterprise AI assistant. You are:
- Highly knowledgeable and helpful
- Bound strictly to the organization's approved knowledge and the boundaries set by administrators
- Transparent about your reasoning and limitations
- Precise, concise, and professional in tone

When referencing information from the knowledge base, cite your sources clearly.
When you don't know something or it falls outside your configured domain, say so honestly.
Never fabricate information. Never exceed the boundaries defined in your configuration."""


class ChatEngine:
    """
    Orchestrates a full chat turn: context retrieval → prompt construction →
    LLM generation → response post-processing.

    Parameters
    ----------
    db     : Async SQLAlchemy session (request-scoped)
    redis  : Redis async client
    """

    def __init__(self, db: AsyncSession, redis: Redis) -> None:
        self._db = db
        self._redis = redis
        self._llm = LLMRouter()
        self._vs = VectorSearchEngine()
        self._memory = MemoryEngine(db, redis, self._vs, self._llm)
        self._tools = ToolEngine(db)

    # ── Public API ────────────────────────────────────────────────────────────

    async def process(
        self,
        message: str,
        conversation_id: uuid.UUID,
        session_id: str,
        user_id: uuid.UUID | None = None,
        ai_config_id: uuid.UUID | None = None,
        use_knowledge: bool = True,
        use_memory: bool = True,
        tools_enabled: bool = True,
        allowed_tools: list[str] | None = None,
        context: dict[str, Any] | None = None,
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Process a message non-streaming. Returns a full result dict.
        """
        start_ts = time.monotonic()

        ai_config = await self._load_ai_config(ai_config_id)
        system_prompt, knowledge_chunks, memory_items = await self._build_context(
            message=message,
            session_id=session_id,
            user_id=str(user_id) if user_id else None,
            ai_config=ai_config,
            use_knowledge=use_knowledge,
            use_memory=use_memory,
        )

        messages = self._build_messages(
            system_prompt=system_prompt,
            session_messages=await self._memory.get_context(session_id, max_tokens=6000),
            extra_history=history or [],
            current_message=message,
        )

        # Tool definitions
        tools_defs: list[dict] | None = None
        if tools_enabled:
            available_tools = await self._tools.list_tools(active_only=True)
            if allowed_tools:
                available_tools = [t for t in available_tools if t.name in allowed_tools]
            if available_tools:
                tools_defs = self._format_tools(available_tools)

        model_config = self._resolve_model_config(ai_config, messages)

        full_text = ""
        tool_calls_out: list[dict] | None = None
        tool_results_out: list[dict] | None = None

        async for chunk in self._llm.generate(
            messages=messages,
            model_config=model_config,
            stream=False,
            tools=tools_defs,
        ):
            full_text += chunk

        # Handle tool calls embedded in the response text
        if tools_defs and full_text.startswith('{"tool_calls"'):
            import json as _json
            try:
                parsed = _json.loads(full_text)
                raw_tool_calls = parsed.get("tool_calls", [])
                tool_calls_out = raw_tool_calls
                tool_results_out = []
                for tc in raw_tool_calls:
                    fn = tc.get("function", {})
                    tool_id = fn.get("name", "")
                    import json as _json2
                    args = _json2.loads(fn.get("arguments", "{}"))
                    result = await self._tools.execute_tool(
                        tool_id, args, str(conversation_id), str(user_id) if user_id else None
                    )
                    tool_results_out.append({"tool": tool_id, "result": result})

                # Second LLM pass with tool results
                messages.append({"role": "assistant", "content": full_text})
                for tr in tool_results_out:
                    messages.append({"role": "user", "content": f"Tool result for {tr['tool']}: {tr['result']}"})

                final_text = ""
                async for chunk in self._llm.generate(messages, model_config, stream=False):
                    final_text += chunk
                full_text = final_text
            except Exception as exc:
                logger.warning("chat_engine.tool_parse_error", error=str(exc))

        # Estimate tokens (tiktoken would be more accurate but adds latency)
        prompt_tokens = count_message_tokens(messages, model_config.get("model", "gpt-4o"))
        completion_tokens = len(full_text.split()) * 4 // 3
        tokens_used = prompt_tokens + completion_tokens
        cost_usd = self._llm.calculate_cost(
            model_config.get("model", settings.openai_default_model),
            prompt_tokens,
            completion_tokens,
        )

        # Persist to context memory
        await self._memory.add_to_context(session_id, "user", message)
        await self._memory.add_to_context(session_id, "assistant", full_text)

        latency_ms = int((time.monotonic() - start_ts) * 1000)
        logger.info(
            "chat_engine.process_complete",
            session_id=session_id,
            latency_ms=latency_ms,
            tokens=tokens_used,
            model=model_config.get("model"),
        )

        return {
            "content": full_text,
            "model_used": model_config.get("model", settings.openai_default_model),
            "provider_used": model_config.get("provider", "openai"),
            "tokens_used": tokens_used,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_usd": cost_usd,
            "knowledge_chunks_used": len(knowledge_chunks),
            "memory_items_used": len(memory_items),
            "tool_calls": tool_calls_out,
            "tool_results": tool_results_out,
            "latency_ms": latency_ms,
        }

    async def stream(
        self,
        message: str,
        conversation_id: uuid.UUID,
        session_id: str,
        user_id: uuid.UUID | None = None,
        ai_config_id: uuid.UUID | None = None,
        use_knowledge: bool = True,
        use_memory: bool = True,
        tools_enabled: bool = True,
        allowed_tools: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Stream the response as delta chunks.

        Yields dicts:
          {"type": "text", "content": "<delta>"}
          {"type": "meta", "tokens_used": N, "cost_usd": F, "model_used": "...", ...}
        """
        start_ts = time.monotonic()

        ai_config = await self._load_ai_config(ai_config_id)
        system_prompt, knowledge_chunks, memory_items = await self._build_context(
            message=message,
            session_id=session_id,
            user_id=str(user_id) if user_id else None,
            ai_config=ai_config,
            use_knowledge=use_knowledge,
            use_memory=use_memory,
        )

        messages = self._build_messages(
            system_prompt=system_prompt,
            session_messages=await self._memory.get_context(session_id, max_tokens=6000),
            extra_history=[],
            current_message=message,
        )

        tools_defs: list[dict] | None = None
        if tools_enabled:
            available_tools = await self._tools.list_tools(active_only=True)
            if allowed_tools:
                available_tools = [t for t in available_tools if t.name in allowed_tools]
            if available_tools:
                tools_defs = self._format_tools(available_tools)

        model_config = self._resolve_model_config(ai_config, messages)

        collected: list[str] = []
        prompt_tokens = count_message_tokens(messages, model_config.get("model", "gpt-4o"))

        async for text_chunk in self._llm.generate(
            messages=messages,
            model_config=model_config,
            stream=True,
            tools=tools_defs,
        ):
            collected.append(text_chunk)
            yield {"type": "text", "content": text_chunk}

        full_text = "".join(collected)
        completion_tokens = len(full_text.split()) * 4 // 3
        tokens_used = prompt_tokens + completion_tokens
        cost_usd = self._llm.calculate_cost(
            model_config.get("model", settings.openai_default_model),
            prompt_tokens,
            completion_tokens,
        )
        latency_ms = int((time.monotonic() - start_ts) * 1000)

        # Persist to context memory after streaming
        await self._memory.add_to_context(session_id, "user", message)
        await self._memory.add_to_context(session_id, "assistant", full_text)

        yield {
            "type": "meta",
            "tokens_used": tokens_used,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_usd": cost_usd,
            "model_used": model_config.get("model", settings.openai_default_model),
            "provider_used": model_config.get("provider", "openai"),
            "knowledge_chunks_used": len(knowledge_chunks),
            "memory_items_used": len(memory_items),
            "latency_ms": latency_ms,
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _load_ai_config(self, ai_config_id: uuid.UUID | None) -> AIConfig | None:
        """Load AI config from DB, falling back to the default config."""
        if ai_config_id:
            result = await self._db.execute(
                select(AIConfig).where(AIConfig.id == ai_config_id, AIConfig.is_active.is_(True))
            )
            config = result.scalar_one_or_none()
            if config:
                return config

        result = await self._db.execute(
            select(AIConfig).where(AIConfig.is_default.is_(True), AIConfig.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def _build_context(
        self,
        message: str,
        session_id: str,
        user_id: str | None,
        ai_config: AIConfig | None,
        use_knowledge: bool,
        use_memory: bool,
    ) -> tuple[str, list[dict], list[Any]]:
        """
        Build the enriched system prompt from knowledge and memory.

        Returns
        -------
        system_prompt  : str    – final system message with injected context
        knowledge_chunks: list  – retrieved knowledge results
        memory_items   : list   – retrieved memory items
        """
        base_prompt = (
            ai_config.system_prompt
            if ai_config and ai_config.system_prompt
            else _DEFAULT_SYSTEM_PROMPT
        )

        knowledge_chunks: list[dict] = []
        memory_items: list[Any] = []
        context_sections: list[str] = []

        # Knowledge retrieval (parallel with memory)
        async def _empty_list():
            return []

        knowledge_task = (
            self._search_knowledge(message, ai_config)
            if use_knowledge and (ai_config is None or ai_config.knowledge_enabled)
            else _empty_list()
        )
        memory_task = (
            self._memory.search_memories(user_id, message, top_k=5)
            if use_memory and user_id and (ai_config is None or ai_config.memory_enabled)
            else _empty_list()
        )

        knowledge_chunks, memory_items = await asyncio.gather(
            knowledge_task, memory_task, return_exceptions=False
        )

        if knowledge_chunks:
            knowledge_section = "## Relevant Knowledge\n"
            for i, chunk in enumerate(knowledge_chunks, 1):
                knowledge_section += (
                    f"\n[{i}] Source: {chunk.get('source_name', 'Unknown')} "
                    f"(type: {chunk.get('source_type', '')})\n"
                    f"{chunk.get('content', '')}\n"
                )
            context_sections.append(knowledge_section)

        if memory_items:
            memory_section = "## User Context & Preferences\n"
            for item in memory_items:
                content = getattr(item, "content", str(item))
                memory_section += f"- {content}\n"
            context_sections.append(memory_section)

        if context_sections:
            full_prompt = base_prompt + "\n\n" + "\n\n".join(context_sections)
        else:
            full_prompt = base_prompt

        return full_prompt, knowledge_chunks, memory_items

    async def _search_knowledge(
        self, query: str, ai_config: AIConfig | None
    ) -> list[dict]:
        try:
            engine = KnowledgeEngine(self._db, self._llm, self._vs)
            return await engine.search_knowledge(
                query=query,
                top_k=settings.memory_max_context_items,
                score_threshold=0.4,
                approved_only=True,
            )
        except Exception as exc:
            logger.warning("chat_engine.knowledge_search_failed", error=str(exc))
            return []

    def _build_messages(
        self,
        system_prompt: str,
        session_messages: list[dict],
        extra_history: list[dict],
        current_message: str,
    ) -> list[dict]:
        """Build the full message list for the LLM."""
        messages: list[dict] = [{"role": "system", "content": system_prompt}]

        # Extra history passed directly from the client (e.g. SDK context)
        for h in extra_history[-10:]:
            if h.get("role") and h.get("content"):
                messages.append({"role": h["role"], "content": h["content"]})

        # Session context from Redis (last 20 turns max)
        for m in session_messages[-20:]:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role and content:
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": current_message})
        return messages

    def _resolve_model_config(
        self, ai_config: AIConfig | None, messages: list[dict]
    ) -> dict[str, Any]:
        """Derive a model_config dict from the AIConfig record (or defaults)."""
        context_tokens = count_message_tokens(messages)

        if ai_config:
            decision = self._llm.route(
                task_type="chat",
                context_tokens=context_tokens,
                budget_mode=ai_config.routing_strategy or "balanced",
                preferred_provider=ai_config.provider,
                preferred_model=ai_config.model_name,
            )
            return {
                "provider": decision.provider,
                "model": decision.model,
                "temperature": float(ai_config.temperature or 0.7),
                "max_tokens": int(ai_config.max_tokens or 4096),
                "top_p": float(ai_config.top_p or 1.0),
                "fallback_provider": decision.fallback_provider,
                "fallback_model": decision.fallback_model,
                "extra_params": ai_config.extra_params or {},
            }

        # No config in DB — use env defaults with balanced routing
        decision = self._llm.route(
            task_type="chat",
            context_tokens=context_tokens,
            budget_mode="balanced",
        )
        return {
            "provider": decision.provider,
            "model": decision.model,
            "temperature": 0.7,
            "max_tokens": 4096,
            "top_p": 1.0,
            "fallback_provider": decision.fallback_provider,
            "fallback_model": decision.fallback_model,
        }

    @staticmethod
    def _format_tools(tools: list[Any]) -> list[dict]:
        """Convert Tool ORM objects to OpenAI function-calling format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.schema or {"type": "object", "properties": {}},
                },
            }
            for tool in tools
            if tool.is_active
        ]
