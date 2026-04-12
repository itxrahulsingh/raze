"""
Main AI Orchestration Engine for RAZE AI OS.
Orchestrates the entire flow: intent detection → context building → decision making → response generation.
"""

import asyncio
import json
import logging
from typing import AsyncGenerator, Optional, List, Dict, Any
import uuid
from datetime import datetime
import time

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio import Redis

from app.models.conversation import Conversation, Message
from app.models.ai_config import AIConfig
from app.core.llm_router import LLMRouter
from app.core.memory_engine import MemoryEngine
from app.core.knowledge_engine import KnowledgeEngine
from app.core.tool_engine import ToolEngine
from app.core.vector_search import VectorSearchEngine
from app.core.observability import ObservabilityEngine
from app.config import get_settings

logger = logging.getLogger(__name__)


class AIOrchestrator:
    """Main AI orchestration engine - the heart of RAZE."""

    def __init__(
        self,
        db: AsyncSession,
        redis: Redis,
        llm_router: LLMRouter,
        memory_engine: MemoryEngine,
        knowledge_engine: KnowledgeEngine,
        tool_engine: ToolEngine,
        vector_search: VectorSearchEngine,
        observability: ObservabilityEngine
    ):
        self.db = db
        self.redis = redis
        self.llm_router = llm_router
        self.memory = memory_engine
        self.knowledge = knowledge_engine
        self.tools = tool_engine
        self.vector_search = vector_search
        self.observability = observability
        self.settings = get_settings()

        self.default_system_prompt = """You are RAZE, an enterprise AI assistant. You are:
- Helpful, harmless, and honest
- Knowledgeable about the organization's data and processes
- Able to execute actions via tools when appropriate
- Transparent about your reasoning and limitations

When executing tools, be clear about what you're doing and why."""

    async def process_message(
        self,
        session_id: str,
        user_message: str,
        user_id: Optional[str] = None,
        ai_config: Optional[AIConfig] = None,
        stream: bool = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Main entry point for processing user messages.
        Yields streamed response chunks as SSE events.
        """
        start_time = time.time()
        message_id = str(uuid.uuid4())
        conversation_id = None

        try:
            # Get or create conversation
            if user_id:
                stmt = select(Conversation).where(
                    Conversation.session_id == session_id,
                    Conversation.user_id == user_id
                )
                result = await self.db.execute(stmt)
                conversation = result.scalar_one_or_none()
            else:
                stmt = select(Conversation).where(
                    Conversation.session_id == session_id
                )
                result = await self.db.execute(stmt)
                conversation = result.scalar_one_or_none()

            if not conversation:
                conversation = Conversation(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    user_id=user_id,
                    title=user_message[:100],
                    status="active",
                    message_count=0,
                    total_tokens=0
                )
                self.db.add(conversation)
                await self.db.flush()

            conversation_id = conversation.id

            # Store user message in context
            await self.memory.add_to_context(session_id, "user", user_message)

            # Add to DB
            user_msg_db = Message(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                role="user",
                content=user_message
            )
            self.db.add(user_msg_db)
            await self.db.flush()

            # Get default AI config if not provided
            if not ai_config:
                stmt = select(AIConfig).where(AIConfig.is_default == True)
                result = await self.db.execute(stmt)
                ai_config = result.scalar_one_or_none()

            if not ai_config:
                # Fallback default config
                ai_config = AIConfig(
                    id=str(uuid.uuid4()),
                    name="Default",
                    is_default=True,
                    provider="openai",
                    model_name="gpt-4-turbo-preview",
                    temperature=0.7,
                    max_tokens=2000,
                    system_prompt=self.default_system_prompt,
                    routing_strategy="balanced"
                )

            # 1. Detect intent
            intent = await self._detect_intent(user_message, conversation, ai_config)
            yield {"type": "intent", "intent": intent}

            # 2. Build context
            context_items = await self._build_context(
                session_id, user_id, user_message, conversation, ai_config
            )

            # 3. Decide action
            action = await self._decide_action(intent, context_items)

            # 4. Execute action
            available_tools = await self.tools.list_tools(active_only=True)

            if action["type"] == "knowledge_query":
                # Search knowledge base
                knowledge_results = await self.knowledge.search_knowledge(
                    user_message, top_k=5
                )
                yield {"type": "knowledge_search", "results_count": len(knowledge_results)}

                # Format knowledge for context
                knowledge_context = self._format_knowledge_as_context(knowledge_results)
                context_items["knowledge"] = knowledge_context

            if action["type"] == "tool_use" and available_tools:
                # Let LLM decide which tool
                tool_selection = await self.tools.select_tool(
                    available_tools, intent, json.dumps(context_items)
                )
                if tool_selection:
                    action["selected_tool"] = tool_selection.id

            # 5. Build messages for LLM
            system_message = ai_config.system_prompt or self.default_system_prompt
            system_message += "\n\n" + self._inject_context(context_items)

            messages = [{"role": "system", "content": system_message}]

            # Add conversation history
            context_messages = await self.memory.get_context(session_id, max_tokens=3000)
            for msg in context_messages[-10:]:  # Last 10 messages
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

            # Add current message
            messages.append({"role": "user", "content": user_message})

            # 6. Generate response via LLM
            response_content = ""
            tool_calls = []

            async for chunk in await self._generate_response(
                messages, ai_config, available_tools, stream=stream
            ):
                if chunk["type"] == "text":
                    response_content += chunk["content"]
                    yield chunk
                elif chunk["type"] == "tool_call_start":
                    yield chunk
                    tool_calls.append(chunk)

            yield {"type": "response_end"}

            # 7. Execute tools if needed
            if tool_calls and action["type"] == "tool_use":
                for tool_call in tool_calls:
                    yield {"type": "tool_start", "tool_name": tool_call["tool_name"]}

                    tool_result = await self.tools.execute_tool(
                        tool_call["tool_id"],
                        tool_call["arguments"],
                        conversation_id,
                        user_id
                    )

                    yield {"type": "tool_result", "result": tool_result}

                    # Continue generation with tool results
                    messages.append({
                        "role": "assistant",
                        "content": response_content
                    })
                    messages.append({
                        "role": "tool",
                        "content": json.dumps(tool_result),
                        "tool_use_id": tool_call["id"]
                    })

                    async for final_chunk in await self._generate_response(
                        messages, ai_config, available_tools, stream=True
                    ):
                        if final_chunk["type"] == "text":
                            response_content += final_chunk["content"]
                        yield final_chunk

            # 8. Post-process and store
            await self._post_process(
                conversation_id, session_id, user_id,
                response_content, message_id, ai_config,
                intent, available_tools, tool_calls
            )

            # 9. Track observability
            latency_ms = int((time.time() - start_time) * 1000)

            await self.observability.log_decision(
                conversation_id=conversation_id,
                message_id=message_id,
                intent=intent,
                model=ai_config.model_name,
                tools_considered=[t.name for t in available_tools],
                tool_selected=tool_calls[0]["tool_name"] if tool_calls else None,
                confidence=0.85,  # Simplified
                context_retrieved={"knowledge_chunks": len(context_items.get("knowledge", []))},
                latency_ms=latency_ms
            )

            yield {"type": "done", "message_id": message_id}

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            yield {"type": "error", "error": str(e)}

    async def _detect_intent(
        self,
        message: str,
        conversation: Conversation,
        ai_config: AIConfig
    ) -> str:
        """Detect user intent: chat/knowledge_query/tool_use/clarification."""
        try:
            # Simple heuristics
            message_lower = message.lower()

            if any(kw in message_lower for kw in ["search", "find", "lookup", "what", "where", "how"]):
                return "knowledge_query"
            elif any(kw in message_lower for kw in ["execute", "run", "call", "check", "create", "delete"]):
                return "tool_use"
            elif any(kw in message_lower for kw in ["?", "clarify", "explain", "why", "what"]):
                return "clarification_needed"
            else:
                return "chat"

        except Exception as e:
            logger.error(f"Error detecting intent: {e}")
            return "chat"

    async def _build_context(
        self,
        session_id: str,
        user_id: Optional[str],
        query: str,
        conversation: Conversation,
        ai_config: AIConfig
    ) -> Dict[str, Any]:
        """Build comprehensive context from memories, knowledge, and conversation history."""
        try:
            context = {
                "user_memories": [],
                "knowledge": [],
                "conversation_history": [],
                "metadata": {}
            }

            # Get user memories
            if user_id:
                user_memories = await self.memory.search_memories(
                    user_id, query, top_k=3
                )
                context["user_memories"] = [m.content for m in user_memories]

            # Previous context in session
            context["conversation_history"] = await self.memory.get_context(session_id, max_tokens=2000)

            return context

        except Exception as e:
            logger.error(f"Error building context: {e}")
            return {}

    async def _decide_action(self, intent: str, context: Dict) -> Dict[str, Any]:
        """Decide what action to take: answer_directly, search_knowledge, execute_tool."""
        try:
            if intent == "knowledge_query":
                return {"type": "knowledge_query"}
            elif intent == "tool_use":
                return {"type": "tool_use"}
            elif intent == "clarification_needed":
                return {"type": "clarification"}
            else:
                return {"type": "chat"}
        except Exception as e:
            logger.error(f"Error deciding action: {e}")
            return {"type": "chat"}

    def _format_knowledge_as_context(self, knowledge_results: List) -> str:
        """Format retrieved knowledge for LLM prompt."""
        if not knowledge_results:
            return ""

        formatted = "# Relevant Knowledge:\n\n"
        for result in knowledge_results:
            formatted += f"- {result.get('content', '')}\n"

        return formatted

    def _inject_context(self, context_items: Dict) -> str:
        """Inject context into system prompt."""
        context_text = ""

        if context_items.get("user_memories"):
            context_text += "\nUser Preferences:\n"
            for mem in context_items["user_memories"]:
                context_text += f"- {mem}\n"

        if context_items.get("knowledge"):
            context_text += "\nRelevant Information:\n"
            context_text += context_items["knowledge"]

        return context_text

    async def _generate_response(
        self,
        messages: List[Dict],
        ai_config: AIConfig,
        available_tools: List,
        stream: bool = True
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate response via LLM router."""
        try:
            # Prepare tools in OpenAI format
            tools_defs = None
            if available_tools:
                tools_defs = [
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.schema
                        }
                    }
                    for tool in available_tools
                ]

            async for chunk in self.llm_router.generate(
                messages,
                ai_config,
                tools=tools_defs,
                stream=stream
            ):
                yield chunk

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            yield {"type": "error", "error": str(e)}

    async def _post_process(
        self,
        conversation_id: str,
        session_id: str,
        user_id: Optional[str],
        response_content: str,
        message_id: str,
        ai_config: AIConfig,
        intent: str,
        available_tools: List,
        tool_calls: List
    ) -> None:
        """Post-process response: store message, extract memories, update context."""
        try:
            # Store assistant response
            response_msg = Message(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                role="assistant",
                content=response_content,
                model_used=ai_config.model_name,
                metadata={
                    "intent": intent,
                    "tools_used": [t.get("tool_name") for t in tool_calls]
                }
            )
            self.db.add(response_msg)

            # Add to context
            await self.memory.add_to_context(session_id, "assistant", response_content)

            # Extract and store new memories
            if user_id and intent == "chat":
                # Simple memory extraction
                important_phrases = [
                    phrase for phrase in response_content.split(".")
                    if len(phrase) > 50 and len(phrase) < 300
                ]
                for phrase in important_phrases[:2]:
                    await self.memory.store_memory(
                        user_id, session_id, "knowledge",
                        phrase.strip(), importance_score=0.6
                    )

            await self.db.commit()

        except Exception as e:
            logger.error(f"Error in post-processing: {e}")
