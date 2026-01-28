"""
Database Retry Logic - Network and transient error handling with automatic retry.

Handles:
- Network-level errors (connection reset, timeout, DNS failure)
- Supabase/Cloudflare transient errors (502, 503, 504)
- PostgREST APIError with transient HTTP status codes

@module core.database.retry
@version 2.0.0
"""

import time
import random
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


# Network-level retryable error patterns
RETRYABLE_ERROR_PATTERNS = [
    # Network errors
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
    # Supabase/Cloudflare transient errors
    'json could not be generated',       # Cloudflare returns HTML instead of JSON
    'bad gateway',                        # 502 error message
    'service temporarily unavailable',    # 503 error message
    'gateway timeout',                    # 504 error message
    'internal server error',              # 500 from Cloudflare
    'cloudflare',                         # Cloudflare error pages
    'server error',                       # Generic server error
]

# PostgREST APIError codes that indicate transient failures
RETRYABLE_POSTGREST_CODES = {500, 502, 503, 504}


def _is_postgrest_transient_error(error: Exception) -> bool:
    """
    Check if a PostgREST APIError has a transient HTTP status code.

    PostgREST APIError includes a 'code' field that maps to HTTP status.
    Codes 502/503/504 indicate Supabase/Cloudflare infrastructure issues.

    Args:
        error: The exception to check

    Returns:
        True if error is a PostgREST APIError with a transient code
    """
    error_type = type(error).__name__
    if error_type != 'APIError':
        return False

    # Check .code attribute (postgrest.exceptions.APIError has this)
    code = getattr(error, 'code', None)
    if code is not None:
        try:
            return int(code) in RETRYABLE_POSTGREST_CODES
        except (ValueError, TypeError):
            pass

    # Fallback: check .details or .message for status code hints
    message = getattr(error, 'message', '')
    if message and any(str(c) in str(message) for c in RETRYABLE_POSTGREST_CODES):
        return True

    return False


def is_retryable_error(error: Exception, patterns: list = None) -> bool:
    """
    Check if error is retryable (network or transient infrastructure error).

    Checks two sources:
    1. Error message string against known retryable patterns
    2. PostgREST APIError code against transient HTTP status codes (502/503/504)

    Args:
        error: The exception to check
        patterns: Custom patterns to check against (uses defaults if None)

    Returns:
        True if error matches a retryable pattern or is a transient APIError
    """
    # Check PostgREST APIError transient codes first (fast path)
    if _is_postgrest_transient_error(error):
        return True

    # Check error message against string patterns
    error_str = str(error).lower()
    check_patterns = patterns or RETRYABLE_ERROR_PATTERNS
    return any(pattern in error_str for pattern in check_patterns)


def _jittered_delay(base_delay: float) -> float:
    """
    Apply Full Jitter to delay value to prevent thundering herd.

    Uses AWS-recommended Full Jitter strategy:
    sleep = random_between(base_delay * 0.5, base_delay)

    Reference: https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/

    Args:
        base_delay: The base delay in seconds

    Returns:
        Jittered delay value between 50%-100% of base_delay
    """
    return base_delay * random.uniform(0.5, 1.0)


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
                    time.sleep(_jittered_delay(current_delay))
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
                    await asyncio.sleep(_jittered_delay(current_delay))
                    current_delay *= backoff

            raise last_error

        return wrapper
    return decorator
