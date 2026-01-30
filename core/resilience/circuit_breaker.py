"""
Circuit Breaker Pattern (WS-15)

Three-state circuit breaker for external service calls:
- CLOSED: Normal operation, requests pass through
- OPEN: Failures exceeded threshold, fast-fail (raise CircuitBreakerOpen)
- HALF_OPEN: After reset_timeout, allow limited probe requests

Usage:
    cb = CircuitBreaker(name="fal", failure_threshold=5, reset_timeout=60.0)
    async with cb:
        result = await external_call()

@module core.resilience.circuit_breaker
@version 1.0.0
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Types
# =============================================================================


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpen(Exception):
    """Raised when circuit is open and request is rejected."""

    def __init__(self, name: str, retry_after: float):
        self.name = name
        self.retry_after = retry_after
        super().__init__(
            f"Circuit breaker '{name}' is OPEN. Retry after {retry_after:.0f}s."
        )


# =============================================================================
# Circuit Breaker
# =============================================================================


class CircuitBreaker:
    """
    Async circuit breaker for external service resilience.

    Args:
        name: Service name (for logging)
        failure_threshold: Consecutive failures to trip open (default: 5)
        reset_timeout: Seconds before transitioning open → half_open (default: 60)
        half_open_max_calls: Max probe calls in half_open state (default: 1)

    Example:
        cb = CircuitBreaker("fal-ai", failure_threshold=5, reset_timeout=60)

        async with cb:
            result = await fal_client.generate(...)
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        reset_timeout: float = 60.0,
        half_open_max_calls: int = 1,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.half_open_max_calls = half_open_max_calls

        # Internal state
        self._state: CircuitState = CircuitState.CLOSED
        self._failure_count: int = 0
        self._last_failure_time: float = 0.0
        self._half_open_calls: int = 0
        self._lock = asyncio.Lock()

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def state(self) -> CircuitState:
        """Current circuit state (may auto-transition from open → half_open)."""
        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self.reset_timeout:
                return CircuitState.HALF_OPEN
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    # =========================================================================
    # Context Manager
    # =========================================================================

    async def __aenter__(self):
        """Check circuit state before allowing the call."""
        async with self._lock:
            current_state = self.state

            if current_state == CircuitState.OPEN:
                retry_after = self.reset_timeout - (
                    time.monotonic() - self._last_failure_time
                )
                raise CircuitBreakerOpen(self.name, max(0, retry_after))

            if current_state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max_calls:
                    raise CircuitBreakerOpen(self.name, self.reset_timeout)
                self._half_open_calls += 1

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Record success or failure after the call."""
        if exc_type is None:
            await self._on_success()
        else:
            # Don't count CircuitBreakerOpen as a failure
            if exc_type is not CircuitBreakerOpen:
                await self._on_failure()
        # Don't suppress the exception
        return False

    # =========================================================================
    # State Transitions
    # =========================================================================

    async def _on_success(self) -> None:
        """Record successful call — reset to closed."""
        async with self._lock:
            prev_state = self._state
            self._failure_count = 0
            self._half_open_calls = 0
            self._state = CircuitState.CLOSED

            if prev_state != CircuitState.CLOSED:
                logger.info(
                    f"[CircuitBreaker:{self.name}] {prev_state.value} → CLOSED "
                    f"(probe succeeded)"
                )

    async def _on_failure(self) -> None:
        """Record failed call — may trip to open."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()

            if self._state == CircuitState.HALF_OPEN:
                # Probe failed → back to open
                self._state = CircuitState.OPEN
                self._half_open_calls = 0
                logger.warning(
                    f"[CircuitBreaker:{self.name}] HALF_OPEN → OPEN "
                    f"(probe failed, retry after {self.reset_timeout}s)"
                )
            elif self._failure_count >= self.failure_threshold:
                # Threshold reached → trip to open
                self._state = CircuitState.OPEN
                logger.warning(
                    f"[CircuitBreaker:{self.name}] CLOSED → OPEN "
                    f"(consecutive failures: {self._failure_count}, "
                    f"threshold: {self.failure_threshold})"
                )

    # =========================================================================
    # Manual Controls
    # =========================================================================

    async def reset(self) -> None:
        """Manually reset circuit to closed state."""
        async with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._half_open_calls = 0
            logger.info(f"[CircuitBreaker:{self.name}] Manually reset to CLOSED")

    def get_stats(self) -> dict:
        """Get current circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "reset_timeout": self.reset_timeout,
        }
