"""
RAZE Enterprise AI OS – Multi-LLM Router

Provides a unified interface to OpenAI, Anthropic, Gemini and Ollama with:
  - Strategy-based routing (cost / performance / balanced)
  - Automatic failover with exponential back-off (tenacity)
  - Streaming and non-streaming generation
  - Embedding generation (OpenAI text-embedding-3-small by default)
  - Per-token cost tracking
  - Token counting per model
  - Decision reason logging via ObservabilityEngine
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Literal

import structlog
import tiktoken
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

import google.generativeai as genai
import httpx

from app.config import get_settings

settings = get_settings()
logger = structlog.get_logger(__name__)

# ─── Type aliases ─────────────────────────────────────────────────────────────

OpenAIMessage = dict[str, Any]  # {"role": "user"|"assistant"|"system", "content": str}
GenerationConfig = dict[str, Any]

# ─── Cost tables (USD per 1 000 tokens) ──────────────────────────────────────

MODEL_COSTS: dict[str, dict[str, float]] = {
    # OpenAI
    "gpt-4o":                    {"input": 0.005,   "output": 0.015},
    "gpt-4o-mini":               {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo":               {"input": 0.01,    "output": 0.03},
    "gpt-4":                     {"input": 0.03,    "output": 0.06},
    "gpt-3.5-turbo":             {"input": 0.0005,  "output": 0.0015},
    "o1":                        {"input": 0.015,   "output": 0.060},
    "o1-mini":                   {"input": 0.003,   "output": 0.012},
    # Anthropic
    "claude-opus-4-5":           {"input": 0.015,   "output": 0.075},
    "claude-sonnet-4-5":         {"input": 0.003,   "output": 0.015},
    "claude-haiku-3-5":          {"input": 0.00025, "output": 0.00125},
    "claude-3-5-sonnet-20241022":{"input": 0.003,   "output": 0.015},
    "claude-3-5-haiku-20241022": {"input": 0.001,   "output": 0.005},
    # Gemini
    "gemini-2.0-flash":          {"input": 0.000075,"output": 0.0003},
    "gemini-1.5-pro":            {"input": 0.00125, "output": 0.005},
    "gemini-1.5-flash":          {"input": 0.000075,"output": 0.0003},
    # Grok
    "grok-3":                    {"input": 0.003,   "output": 0.015},
    # Ollama (local – zero cost)
    "llama3.2":                  {"input": 0.0, "output": 0.0},
    "llama3.1":                  {"input": 0.0, "output": 0.0},
    "mistral":                   {"input": 0.0, "output": 0.0},
    "phi3":                      {"input": 0.0, "output": 0.0},
}

# ─── Model routing catalogue ──────────────────────────────────────────────────

@dataclass
class ModelSpec:
    provider: str
    model_id: str
    context_window: int
    cost_tier: Literal["free", "cheap", "medium", "expensive"]
    quality_score: float      # 0.0–1.0
    avg_latency_ms: float     # rough p50


ROUTING_CATALOGUE: list[ModelSpec] = [
    ModelSpec("ollama",    settings.ollama_default_model, 8192,    "free",      0.60, 500),
    ModelSpec("openai",    "gpt-4o-mini",                 128_000, "cheap",     0.72, 800),
    ModelSpec("anthropic", "claude-haiku-3-5",            200_000, "cheap",     0.74, 700),
    ModelSpec("gemini",    "gemini-2.0-flash",            1_000_000,"cheap",    0.73, 600),
    ModelSpec("openai",    "gpt-4o",                      128_000, "medium",    0.90, 1200),
    ModelSpec("anthropic", "claude-sonnet-4-5",           200_000, "medium",    0.92, 1100),
    ModelSpec("gemini",    "gemini-1.5-pro",              2_000_000,"medium",   0.88, 900),
    ModelSpec("anthropic", "claude-opus-4-5",             200_000, "expensive", 0.97, 2500),
    ModelSpec("openai",    "gpt-4-turbo",                 128_000, "expensive", 0.94, 2000),
]


# ─── Token counting ───────────────────────────────────────────────────────────

_TIKTOKEN_CACHE: dict[str, tiktoken.Encoding] = {}


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """Count tokens using tiktoken; falls back to word-count heuristic for non-OpenAI models."""
    try:
        enc = _TIKTOKEN_CACHE.get(model)
        if enc is None:
            try:
                enc = tiktoken.encoding_for_model(model)
            except KeyError:
                enc = tiktoken.get_encoding("cl100k_base")
            _TIKTOKEN_CACHE[model] = enc
        return len(enc.encode(text))
    except Exception:
        return len(text.split()) * 4 // 3  # rough approximation


def count_message_tokens(messages: list[OpenAIMessage], model: str = "gpt-4o") -> int:
    """Sum token counts across all message contents."""
    total = 0
    for msg in messages:
        content = msg.get("content") or ""
        if isinstance(content, list):
            # multimodal content blocks
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    total += count_tokens(block.get("text", ""), model)
        else:
            total += count_tokens(str(content), model)
        total += 4  # per-message overhead (role + separators)
    return total + 2  # reply overhead


# ─── Provider adapters ────────────────────────────────────────────────────────

class OpenAIAdapter:
    """Wraps AsyncOpenAI for both chat completions and embeddings."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            organization=settings.openai_org_id,
        )

    async def generate(
        self,
        messages: list[OpenAIMessage],
        model: str,
        temperature: float,
        max_tokens: int,
        top_p: float,
        stream: bool,
        tools: list[dict] | None = None,
        extra_params: dict | None = None,
    ) -> AsyncGenerator[str, None]:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": stream,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        if extra_params:
            kwargs.update(extra_params)

        if stream:
            async with self._client.chat.completions.stream(**kwargs) as stream_ctx:
                async for chunk in stream_ctx:
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if delta and delta.content:
                        yield delta.content
                    # yield tool call deltas as JSON blobs
                    if delta and delta.tool_calls:
                        for tc in delta.tool_calls:
                            if tc.function and tc.function.arguments:
                                yield tc.function.arguments
        else:
            response = await self._client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            content = choice.message.content or ""
            # If there are tool calls, yield them serialised
            if choice.message.tool_calls:
                import json
                tool_payload = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in choice.message.tool_calls
                ]
                yield json.dumps({"tool_calls": tool_payload})
            else:
                yield content

    async def generate_embedding(self, text: str, model: str | None = None) -> list[float]:
        effective_model = model or settings.openai_embedding_model
        response = await self._client.embeddings.create(
            input=text,
            model=effective_model,
        )
        return response.data[0].embedding


class AnthropicAdapter:
    """Wraps AsyncAnthropic; converts OpenAI-style messages to Anthropic format internally."""

    def __init__(self) -> None:
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    @staticmethod
    def _convert_messages(
        messages: list[OpenAIMessage],
    ) -> tuple[str | None, list[dict]]:
        """
        Convert OpenAI-format messages into (system_prompt, anthropic_messages).
        System messages are extracted and concatenated.
        """
        system_parts: list[str] = []
        anthropic_msgs: list[dict] = []

        for msg in messages:
            role = msg["role"]
            content = msg.get("content") or ""
            if role == "system":
                system_parts.append(str(content))
            elif role in ("user", "assistant"):
                # Anthropic roles are "user" / "assistant"
                anthropic_msgs.append({"role": role, "content": str(content)})
            elif role == "tool":
                # Tool result – append as a user message with tool result block
                tool_use_id = msg.get("tool_call_id", "")
                anthropic_msgs.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": str(content),
                            }
                        ],
                    }
                )

        system_prompt = "\n\n".join(system_parts) or None
        return system_prompt, anthropic_msgs

    @staticmethod
    def _convert_tools(tools: list[dict]) -> list[dict]:
        """Convert OpenAI function-calling schema to Anthropic tool schema."""
        anthropic_tools = []
        for tool in tools:
            fn = tool.get("function", tool)
            anthropic_tools.append(
                {
                    "name": fn["name"],
                    "description": fn.get("description", ""),
                    "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
                }
            )
        return anthropic_tools

    async def generate(
        self,
        messages: list[OpenAIMessage],
        model: str,
        temperature: float,
        max_tokens: int,
        top_p: float,
        stream: bool,
        tools: list[dict] | None = None,
        extra_params: dict | None = None,
    ) -> AsyncGenerator[str, None]:
        import json

        system_prompt, anthropic_msgs = self._convert_messages(messages)
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": anthropic_msgs,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        if tools:
            kwargs["tools"] = self._convert_tools(tools)
        if extra_params:
            kwargs.update(extra_params)

        if stream:
            async with self._client.messages.stream(**kwargs) as stream_ctx:
                async for text_chunk in stream_ctx.text_stream:
                    yield text_chunk
        else:
            response = await self._client.messages.create(**kwargs)
            for block in response.content:
                if block.type == "text":
                    yield block.text
                elif block.type == "tool_use":
                    tool_payload = {
                        "tool_calls": [
                            {
                                "id": block.id,
                                "type": "function",
                                "function": {
                                    "name": block.name,
                                    "arguments": json.dumps(block.input),
                                },
                            }
                        ]
                    }
                    yield json.dumps(tool_payload)


class GeminiAdapter:
    """Wraps google.generativeai; converts OpenAI-style messages to Gemini format."""

    def __init__(self) -> None:
        genai.configure(api_key=settings.google_api_key)

    @staticmethod
    def _convert_messages(
        messages: list[OpenAIMessage],
    ) -> tuple[str | None, list[dict]]:
        system_parts: list[str] = []
        gemini_history: list[dict] = []

        for msg in messages:
            role = msg["role"]
            content = msg.get("content") or ""
            if role == "system":
                system_parts.append(str(content))
            elif role == "user":
                gemini_history.append({"role": "user", "parts": [str(content)]})
            elif role == "assistant":
                gemini_history.append({"role": "model", "parts": [str(content)]})
            elif role == "tool":
                gemini_history.append(
                    {"role": "user", "parts": [f"Tool result: {content}"]}
                )

        # The last user message becomes the prompt; history is everything before
        system_instruction = "\n\n".join(system_parts) or None
        return system_instruction, gemini_history

    async def generate(
        self,
        messages: list[OpenAIMessage],
        model: str,
        temperature: float,
        max_tokens: int,
        top_p: float,
        stream: bool,
        tools: list[dict] | None = None,
        extra_params: dict | None = None,
    ) -> AsyncGenerator[str, None]:
        system_instruction, gemini_history = self._convert_messages(messages)

        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            top_p=top_p,
        )
        model_kwargs: dict[str, Any] = {"model_name": model}
        if system_instruction:
            model_kwargs["system_instruction"] = system_instruction

        gemini_model = genai.GenerativeModel(**model_kwargs)

        # Separate history from last user turn
        history = gemini_history[:-1] if len(gemini_history) > 1 else []
        last_turn = gemini_history[-1]["parts"][0] if gemini_history else ""

        chat = gemini_model.start_chat(history=history)

        if stream:
            response = await asyncio.to_thread(
                chat.send_message,
                last_turn,
                generation_config=generation_config,
                stream=True,
            )
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        else:
            response = await asyncio.to_thread(
                chat.send_message,
                last_turn,
                generation_config=generation_config,
            )
            yield response.text or ""


class OllamaAdapter:
    """Wraps the Ollama HTTP API using httpx."""

    def __init__(self) -> None:
        self._base_url = settings.ollama_base_url
        # Increased timeout for CPU-based inference
        timeout_config = httpx.Timeout(600.0, connect=30.0, read=600.0, write=30.0, pool=30.0)
        self._client = httpx.AsyncClient(timeout=timeout_config, limits=httpx.Limits(max_keepalive_connections=10))

    async def generate(
        self,
        messages: list[OpenAIMessage],
        model: str,
        temperature: float,
        max_tokens: int,
        top_p: float,
        stream: bool,
        tools: list[dict] | None = None,
        extra_params: dict | None = None,
    ) -> AsyncGenerator[str, None]:
        import json

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "num_predict": max_tokens,
            },
        }
        if extra_params:
            payload.update(extra_params)

        url = f"{self._base_url}/api/chat"

        if stream:
            async with self._client.stream("POST", url, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        chunk = data.get("message", {}).get("content", "")
                        if chunk:
                            yield chunk
                    except json.JSONDecodeError:
                        continue
        else:
            resp = await self._client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            yield data.get("message", {}).get("content", "")


# ─── LLM Router ───────────────────────────────────────────────────────────────

@dataclass
class RoutingDecision:
    provider: str
    model: str
    reason: str
    estimated_cost: float = 0.0
    fallback_provider: str | None = None
    fallback_model: str | None = None


class LLMRouter:
    """
    Routes LLM requests to the most appropriate provider/model based on
    strategy, budget mode, and context size.

    Strategies:
      "cost"        – cheapest model that fits the context window
      "performance" – highest quality_score model
      "balanced"    – maximise (quality_score / cost_tier_rank) trade-off
    """

    def __init__(self) -> None:
        self._openai = OpenAIAdapter()
        self._anthropic = AnthropicAdapter()
        self._gemini = GeminiAdapter()
        self._ollama = OllamaAdapter() if settings.ollama_enabled else None

        self._adapters: dict[str, Any] = {
            "openai": self._openai,
            "anthropic": self._anthropic,
            "gemini": self._gemini,
        }
        if self._ollama:
            self._adapters["ollama"] = self._ollama

        self._cost_tier_rank = {"free": 0, "cheap": 1, "medium": 2, "expensive": 3}

    def _available_models(self, context_tokens: int) -> list[ModelSpec]:
        """Filter catalogue to models whose context window fits and whose provider is configured."""
        available: list[ModelSpec] = []
        for spec in ROUTING_CATALOGUE:
            if spec.provider == "ollama" and not settings.ollama_enabled:
                continue
            if spec.provider == "openai" and not settings.openai_api_key:
                continue
            if spec.provider == "anthropic" and not settings.anthropic_api_key:
                continue
            if spec.provider == "gemini" and not settings.google_api_key:
                continue
            if spec.context_window >= context_tokens:
                available.append(spec)
        return available

    def route(
        self,
        task_type: str = "chat",
        context_tokens: int = 1000,
        budget_mode: Literal["cost", "performance", "balanced"] = "balanced",
        preferred_provider: str | None = None,
        preferred_model: str | None = None,
    ) -> RoutingDecision:
        """
        Select the best provider/model for the given task.

        Parameters
        ----------
        task_type       : hint for future specialised routing ("chat", "code", "summarise")
        context_tokens  : estimated tokens in the prompt
        budget_mode     : routing strategy
        preferred_provider : lock to a specific provider if set
        preferred_model    : lock to a specific model if set

        Returns
        -------
        RoutingDecision with primary + fallback selection.
        """
        # Override: explicit model/provider specified
        if preferred_provider and preferred_model:
            fallback = self._pick_fallback(preferred_provider, preferred_model)
            return RoutingDecision(
                provider=preferred_provider,
                model=preferred_model,
                reason="explicit_override",
                fallback_provider=fallback[0] if fallback else None,
                fallback_model=fallback[1] if fallback else None,
            )

        candidates = self._available_models(context_tokens)
        if not candidates:
            raise RuntimeError("No available LLM providers configured")

        if budget_mode == "cost":
            chosen = sorted(
                candidates,
                key=lambda s: (self._cost_tier_rank[s.cost_tier], -s.quality_score),
            )[0]
            reason = "cost_optimised"
        elif budget_mode == "performance":
            chosen = sorted(candidates, key=lambda s: -s.quality_score)[0]
            reason = "performance_optimised"
        else:  # balanced
            # Score = quality / (cost_tier_rank + 1) — avoids div-by-zero for free tier
            chosen = sorted(
                candidates,
                key=lambda s: -(s.quality_score / (self._cost_tier_rank[s.cost_tier] + 1)),
            )[0]
            reason = "balanced_strategy"

        # Estimate cost for 1 k output tokens as a rough budget signal
        cost_info = MODEL_COSTS.get(chosen.model_id, {"input": 0, "output": 0})
        estimated_cost = (context_tokens / 1000) * cost_info["input"]

        fallback = self._pick_fallback(chosen.provider, chosen.model_id)
        logger.info(
            "llm_routing_decision",
            provider=chosen.provider,
            model=chosen.model_id,
            reason=reason,
            budget_mode=budget_mode,
            context_tokens=context_tokens,
        )
        return RoutingDecision(
            provider=chosen.provider,
            model=chosen.model_id,
            reason=reason,
            estimated_cost=estimated_cost,
            fallback_provider=fallback[0] if fallback else None,
            fallback_model=fallback[1] if fallback else None,
        )

    def _pick_fallback(
        self, primary_provider: str, primary_model: str
    ) -> tuple[str, str] | None:
        """Pick a fallback different from the primary."""
        for spec in ROUTING_CATALOGUE:
            if spec.provider != primary_provider and spec.model_id != primary_model:
                if spec.provider not in self._adapters:
                    continue
                return spec.provider, spec.model_id
        return None

    async def generate(
        self,
        messages: list[OpenAIMessage],
        model_config: dict[str, Any],
        stream: bool = False,
        tools: list[dict] | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Generate a completion.  Automatically retries with exponential back-off
        and falls over to the fallback provider on hard errors.

        model_config keys: provider, model, temperature, max_tokens, top_p,
                           fallback_provider, fallback_model, extra_params
        """
        provider: str = model_config.get("provider", "openai")
        model: str = model_config.get("model", settings.openai_default_model)
        temperature: float = float(model_config.get("temperature", 0.7))
        max_tokens: int = int(model_config.get("max_tokens", 2048))
        top_p: float = float(model_config.get("top_p", 1.0))
        fallback_provider: str | None = model_config.get("fallback_provider")
        fallback_model: str | None = model_config.get("fallback_model")
        extra_params: dict = model_config.get("extra_params") or {}

        async def _attempt(
            prov: str, mdl: str
        ) -> AsyncGenerator[str, None]:
            adapter = self._adapters.get(prov)
            if adapter is None:
                raise ValueError(f"Provider '{prov}' not available")

            async def _call() -> AsyncGenerator[str, None]:
                return adapter.generate(
                    messages=messages,
                    model=mdl,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=top_p,
                    stream=stream,
                    tools=tools,
                    extra_params=extra_params,
                )

            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=1, max=10),
                retry=retry_if_exception_type((Exception,)),
                reraise=True,
            ):
                with attempt:
                    return await _call()

        try:
            gen = await _attempt(provider, model)
            async for chunk in gen:
                yield chunk
        except Exception as primary_err:
            logger.warning(
                "llm_primary_failed",
                provider=provider,
                model=model,
                error=str(primary_err),
            )
            if fallback_provider and fallback_model:
                logger.info(
                    "llm_failover",
                    fallback_provider=fallback_provider,
                    fallback_model=fallback_model,
                )
                try:
                    gen = await _attempt(fallback_provider, fallback_model)
                    async for chunk in gen:
                        yield chunk
                except Exception as fallback_err:
                    logger.error(
                        "llm_fallback_also_failed",
                        error=str(fallback_err),
                    )
                    raise RuntimeError(
                        f"Both primary ({provider}/{model}) and fallback "
                        f"({fallback_provider}/{fallback_model}) LLMs failed."
                    ) from fallback_err
            else:
                raise

    async def generate_embedding(
        self,
        text: str,
        model: str | None = None,
    ) -> list[float]:
        """
        Generate a dense embedding vector using OpenAI's embedding API by default.
        Falls back to a zero vector on error so downstream code can continue.
        """
        effective_model = model or settings.openai_embedding_model
        try:
            return await self._openai.generate_embedding(text, effective_model)
        except Exception as exc:
            logger.error("embedding_generation_failed", model=effective_model, error=str(exc))
            raise

    @staticmethod
    def calculate_cost(
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """Return estimated USD cost for a given token usage."""
        costs = MODEL_COSTS.get(model, {"input": 0.0, "output": 0.0})
        return (
            prompt_tokens / 1000 * costs["input"]
            + completion_tokens / 1000 * costs["output"]
        )
