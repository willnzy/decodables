"""
AI API Retry Utilities
AI API 重试工具

Provides:
- Exponential backoff retry decorator for AI API calls
- Error classification for retryable errors
- Configurable retry strategies

v3.22: New module for AI API reliability
"""

import asyncio
import logging
from typing import Callable, Set
from functools import wraps

from .base import AIErrorType, classify_error

logger = logging.getLogger(__name__)


# ==========================================
# Retryable Error Types
# ==========================================

# Error types that should trigger retry
RETRYABLE_ERROR_TYPES: Set[str] = {
    AIErrorType.RATE_LIMIT,
    AIErrorType.TIMEOUT,
    AIErrorType.NETWORK_ERROR,
    AIErrorType.API_ERROR,  # 5xx server errors
}

# Error types that should NOT retry
NON_RETRYABLE_ERROR_TYPES: Set[str] = {
    AIErrorType.AUTH_ERROR,        # API key issues
    AIErrorType.INVALID_REQUEST,   # Bad request params
    AIErrorType.MODEL_NOT_FOUND,   # Wrong model name
    AIErrorType.CONTENT_FILTER,    # Content blocked
    AIErrorType.QUOTA_EXCEEDED,    # Account quota
}


def is_retryable_error(exception: Exception, provider: str = "") -> bool:
    """
    Determine if an exception should trigger a retry.
    
    Args:
        exception: The caught exception
        provider: Optional provider name for better classification
        
    Returns:
        True if the error is retryable
    """
    error_type = classify_error(exception, provider)
    return error_type in RETRYABLE_ERROR_TYPES


# ==========================================
# Retry Decorator
# ==========================================

def with_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 30.0,
    multiplier: float = 2.0,
    rate_limit_multiplier: float = 2.0
):
    """
    Async retry decorator with exponential backoff for AI API calls.
    
    Features:
    - Exponential backoff (wait doubles each retry)
    - Rate limit gets extra wait time
    - Only retries recoverable errors
    - Detailed logging for debugging
    
    Args:
        max_attempts: Maximum number of attempts (including first try)
        min_wait: Minimum wait time in seconds
        max_wait: Maximum wait time in seconds
        multiplier: Backoff multiplier
        rate_limit_multiplier: Extra multiplier for rate limit errors
    
    Usage:
        @with_retry(max_attempts=3)
        async def call_openai():
            ...
    
    Example:
        # Default: 3 attempts with 1s, 2s, 4s waits
        @with_retry()
        async def generate():
            return await client.complete(...)
        
        # Aggressive: 5 attempts with longer waits
        @with_retry(max_attempts=5, min_wait=2, max_wait=60)
        async def important_call():
            return await client.complete(...)
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            provider = ""
            
            # Try to extract provider name for logging
            if args and hasattr(args[0], 'provider_name'):
                provider = args[0].provider_name
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    error_type = classify_error(e, provider)
                    
                    # Check if error is retryable
                    if error_type not in RETRYABLE_ERROR_TYPES:
                        # Non-retryable error, raise immediately
                        logger.debug(
                            f"[AIRetry] {func.__name__} non-retryable error ({error_type}): {e}"
                        )
                        raise
                    
                    # Check if this was the last attempt
                    if attempt >= max_attempts - 1:
                        logger.error(
                            f"[AIRetry] {func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    
                    # Calculate wait time with exponential backoff
                    wait_time = min(max_wait, min_wait * (multiplier ** attempt))
                    
                    # Extra wait for rate limit errors
                    if error_type == AIErrorType.RATE_LIMIT:
                        wait_time = min(max_wait, wait_time * rate_limit_multiplier)
                    
                    logger.warning(
                        f"[AIRetry] {func.__name__} attempt {attempt + 1}/{max_attempts} "
                        f"failed ({error_type}), retrying in {wait_time:.1f}s: {e}"
                    )
                    
                    await asyncio.sleep(wait_time)
            
            # Should not reach here, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError(f"{func.__name__} failed without exception")
        
        return wrapper
    return decorator


# ==========================================
# Pre-configured Retry Strategies
# ==========================================

# Standard retry: 3 attempts, 1-30s backoff
STANDARD_RETRY = with_retry(
    max_attempts=3,
    min_wait=1.0,
    max_wait=30.0,
    multiplier=2.0
)

# Aggressive retry: 5 attempts, 2-60s backoff (for critical operations)
AGGRESSIVE_RETRY = with_retry(
    max_attempts=5,
    min_wait=2.0,
    max_wait=60.0,
    multiplier=2.0
)

# Light retry: 2 attempts, 0.5-10s backoff (for fast-fail scenarios)
LIGHT_RETRY = with_retry(
    max_attempts=2,
    min_wait=0.5,
    max_wait=10.0,
    multiplier=2.0
)

# Rate limit focused: More attempts, longer waits
RATE_LIMIT_RETRY = with_retry(
    max_attempts=4,
    min_wait=2.0,
    max_wait=120.0,
    multiplier=3.0,
    rate_limit_multiplier=3.0
)
