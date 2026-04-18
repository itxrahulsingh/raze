"""
RAZE Enterprise AI OS – Comprehensive Error Handling & Resilience

Provides:
  - Circuit breaker pattern for external services
  - Retry logic with exponential backoff
  - Graceful degradation strategies
  - Error logging & tracking
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Awaitable, Callable, TypeVar

import structlog
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)
T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states."""
    closed = "closed"      # Normal operation
    open = "open"          # Failing, reject requests
    half_open = "half_open"  # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker for protecting against cascading failures.

    States:
      - CLOSED: Normal operation
      - OPEN: Service failing, reject requests immediately
      - HALF_OPEN: Testing if service recovered
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type[Exception] = Exception,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.state = CircuitState.closed
        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.success_count = 0

    async def call(self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any) -> T:
        """Call a function with circuit breaker protection."""
        if self.state == CircuitState.open:
            # Check if we should transition to half-open
            if (
                self.last_failure_time
                and datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout)
            ):
                logger.info(f"circuit_breaker.half_open", name=self.name)
                self.state = CircuitState.half_open
                self.success_count = 0
            else:
                logger.warning(f"circuit_breaker.open", name=self.name)
                raise Exception(f"Circuit breaker {self.name} is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        """Handle successful call."""
        self.failure_count = 0
        if self.state == CircuitState.half_open:
            self.success_count += 1
            if self.success_count >= 3:
                logger.info(f"circuit_breaker.closed", name=self.name)
                self.state = CircuitState.closed

    def _on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            logger.error(f"circuit_breaker.open", name=self.name, failures=self.failure_count)
            self.state = CircuitState.open


class ResilienceHelper:
    """Helper functions for resilient operations."""

    @staticmethod
    async def retry_async(
        func: Callable[..., Awaitable[T]],
        *args: Any,
        max_attempts: int = 3,
        wait_base: int = 1,
        **kwargs: Any,
    ) -> T:
        """
        Retry an async function with exponential backoff.

        Args:
            func: Async function to call
            max_attempts: Maximum number of retry attempts
            wait_base: Base wait time in seconds
            *args, **kwargs: Arguments to pass to func
        """
        attempt = 0
        last_exception: Exception | None = None

        while attempt < max_attempts:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                attempt += 1
                last_exception = e

                if attempt < max_attempts:
                    wait_time = wait_base * (2 ** (attempt - 1))
                    logger.warning(
                        "retry_attempt",
                        func_name=func.__name__,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        wait_seconds=wait_time,
                        error=str(e),
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        "retry_exhausted",
                        func_name=func.__name__,
                        attempts=attempt,
                        error=str(e),
                    )

        if last_exception:
            raise last_exception

        raise Exception(f"Failed to execute {func.__name__} after {max_attempts} attempts")

    @staticmethod
    async def timeout_async(
        func: Callable[..., Awaitable[T]],
        timeout_seconds: float,
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """
        Execute an async function with a timeout.

        Args:
            func: Async function to call
            timeout_seconds: Timeout in seconds
            *args, **kwargs: Arguments to pass to func

        Raises:
            asyncio.TimeoutError: If function exceeds timeout
        """
        try:
            return await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.error(
                "operation_timeout",
                func_name=func.__name__,
                timeout_seconds=timeout_seconds,
            )
            raise

    @staticmethod
    async def retry_with_fallback(
        primary_func: Callable[..., Awaitable[T]],
        fallback_func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """
        Try primary function, fall back to secondary on failure.

        Args:
            primary_func: Primary function to try
            fallback_func: Fallback function if primary fails
            *args, **kwargs: Arguments to pass to functions
        """
        try:
            logger.debug(
                "trying_primary",
                primary=primary_func.__name__,
                fallback=fallback_func.__name__,
            )
            return await primary_func(*args, **kwargs)
        except Exception as e:
            logger.warning(
                "primary_failed_using_fallback",
                primary=primary_func.__name__,
                fallback=fallback_func.__name__,
                error=str(e),
            )
            try:
                return await fallback_func(*args, **kwargs)
            except Exception as fallback_error:
                logger.error(
                    "fallback_also_failed",
                    primary=primary_func.__name__,
                    fallback=fallback_func.__name__,
                    primary_error=str(e),
                    fallback_error=str(fallback_error),
                )
                raise


# Circuit breakers for critical services
QDRANT_CB = CircuitBreaker(
    "qdrant",
    failure_threshold=5,
    recovery_timeout=60,
)

LLM_CB = CircuitBreaker(
    "llm_router",
    failure_threshold=3,
    recovery_timeout=30,
)

KNOWLEDGE_CB = CircuitBreaker(
    "knowledge_engine",
    failure_threshold=5,
    recovery_timeout=60,
)

MEMORY_CB = CircuitBreaker(
    "memory_engine",
    failure_threshold=3,
    recovery_timeout=30,
)
