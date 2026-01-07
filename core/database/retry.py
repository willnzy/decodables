"""
Database Retry Logic - Network error handling with automatic retry.

@module core.database.retry
@version 1.0.0
"""

import time
import logging
from functools import wraps
from dataclasses import dataclass
from typing import Callable, Any

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    delay: float = 0.5
    backoff: float = 2.0


# Default retryable error patterns
RETRYABLE_ERROR_PATTERNS = [
    'resource temporarily unavailable',
    'connection reset',
    'connection refused',
    'timeout',
    'timed out',
    'network is unreachable',
    'name or service not known',
    'temporary failure in name resolution',
    'ssl: certificate_verify_failed',
    'readtimeout',
    'connecttimeout',
]


def is_retryable_error(error: Exception, patterns: list = None) -> bool:
    """
    Check if error is retryable (network-related).

    Args:
        error: The exception to check
        patterns: Custom patterns to check against (uses defaults if None)

    Returns:
        True if error matches a retryable pattern
    """
    error_str = str(error).lower()
    check_patterns = patterns or RETRYABLE_ERROR_PATTERNS
    return any(pattern in error_str for pattern in check_patterns)


def retry_on_network_error(
    max_retries: int = 3,
    delay: float = 0.5,
    backoff: float = 2.0,
    patterns: list = None
) -> Callable:
    """
    Decorator for automatic retry on network errors.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        patterns: Custom error patterns to retry on

    Returns:
        Decorated function

    Example:
        @retry_on_network_error(max_retries=3)
        def fetch_data():
            return db.query(...)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_error = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if not is_retryable_error(e, patterns):
                        raise e
                    if attempt >= max_retries:
                        logger.error(
                            f"[DB] {func.__name__} failed after "
                            f"{max_retries + 1} attempts: {e}"
                        )
                        raise e
                    logger.warning(
                        f"[DB] {func.__name__} retry "
                        f"{attempt + 1}/{max_retries + 1}: {e}"
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff

            raise last_error

        return wrapper
    return decorator


def retry_on_network_error_async(
    max_retries: int = 3,
    delay: float = 0.5,
    backoff: float = 2.0,
    patterns: list = None
) -> Callable:
    """
    Async version of retry decorator.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        patterns: Custom error patterns to retry on

    Returns:
        Decorated async function
    """
    import asyncio

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_error = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if not is_retryable_error(e, patterns):
                        raise e
                    if attempt >= max_retries:
                        logger.error(
                            f"[DB] {func.__name__} failed after "
                            f"{max_retries + 1} attempts: {e}"
                        )
                        raise e
                    logger.warning(
                        f"[DB] {func.__name__} retry "
                        f"{attempt + 1}/{max_retries + 1}: {e}"
                    )
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff

            raise last_error

        return wrapper
    return decorator
