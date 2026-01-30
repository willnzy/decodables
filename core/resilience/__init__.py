"""
Resilience Module - Circuit Breaker and related patterns.

@module core.resilience
@version 1.0.0 (WS-15)
"""

from .circuit_breaker import CircuitBreaker, CircuitBreakerOpen, CircuitState

__all__ = [
    "CircuitBreaker",
    "CircuitBreakerOpen",
    "CircuitState",
]
