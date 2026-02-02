"""
Dynamic Rate Limiter
动态速率限制器 - 从数据库读取配置,使用 Redis 存储

Provides:
- Dynamic rate limits from system_configs via ConfigService
- Redis storage for distributed rate limiting
- Memory fallback when Redis unavailable

⚠️ NOTE: All rate limiting functions now use async ConfigService
"""

import json
import logging
from functools import wraps
from typing import Callable, Optional

from fastapi import Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.cache import is_redis_available
from core.cache.redis_provider import get_redis_client
from domains.platform.config_service import ConfigService, DEFAULT_RATE_LIMITS
from infrastructure.repositories.config_repository import SupabaseConfigRepository
from core.database import get_async_db_client

logger = logging.getLogger(__name__)


def create_limiter_from_url(redis_url: str = None) -> Limiter:
    """
    Create a Limiter with explicit Redis URL.

    Args:
        redis_url: Redis connection URL (e.g., redis://localhost:6379/0)

    Returns:
        Configured Limiter instance
    """
    import os

    url = redis_url or os.environ.get("REDIS_URL")

    if url:
        logger.info("[RateLimiter] Using Redis storage")
        return Limiter(
            key_func=get_remote_address,
            storage_uri=url
        )
    else:
        logger.warning("[RateLimiter] Using in-memory storage")
    return Limiter(key_func=get_remote_address)


# Global limiter instance
limiter = create_limiter_from_url()

# Global ConfigService instance (lazy initialized)
_config_service: Optional[ConfigService] = None


async def get_config_service() -> ConfigService:
    """Get or create global ConfigService instance (async)."""
    global _config_service
    if _config_service is None:
        db_client = await get_async_db_client()
        config_repo = SupabaseConfigRepository(db_client)
        _config_service = ConfigService(config_repo)
    return _config_service


def _parse_retry_after(limit_string: str) -> int:
    """
    Parse the window from a rate limit string to compute Retry-After seconds.

    Examples:
        "5/minute" → 60
        "100/hour" → 3600
        "10/second" → 1

    Returns:
        Retry-After value in seconds (defaults to 60 if unparseable)
    """
    window_map = {
        "second": 1,
        "minute": 60,
        "hour": 3600,
        "day": 86400,
    }
    try:
        window = limit_string.split("/")[1].strip().lower()
        return window_map.get(window, 60)
    except (IndexError, AttributeError):
        return 60


def dynamic_limit(config_key: str):
    """
    Decorator for dynamic rate limiting based on database config.

    Reads limit config from system_configs table via ConfigService.

    Args:
        config_key: Config key (e.g., "rate_limit.payment.checkout")

    Usage:
        @app.post("/api/payment/checkout")
        @dynamic_limit("rate_limit.payment.checkout")
        async def pay(request: Request, ...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(request: Request, *args, **kwargs):
            config_service = await get_config_service()

            # Check if rate limiting is enabled
            enabled = await config_service.is_rate_limit_enabled(config_key)
            if not enabled:
                return await func(request, *args, **kwargs)

            # Get limit string
            limit_string = await config_service.get_rate_limit_string(config_key)

            try:
                # Apply rate limit
                limited_func = limiter.limit(limit_string)(func)
                return await limited_func(request, *args, **kwargs)
            except Exception as e:
                if "RateLimitExceeded" in str(type(e)):
                    retry_after = _parse_retry_after(limit_string)
                    raise HTTPException(
                        status_code=429,
                        detail="Rate limit exceeded. Please try again later.",
                        headers={"Retry-After": str(retry_after)},
                    )
                raise

        @wraps(func)
        async def sync_wrapper(request: Request, *args, **kwargs):
            config_service = await get_config_service()

            # Check if rate limiting is enabled
            enabled = await config_service.is_rate_limit_enabled(config_key)
            if not enabled:
                return func(request, *args, **kwargs)

            limit_string = await config_service.get_rate_limit_string(config_key)

            try:
                limited_func = limiter.limit(limit_string)(func)
                return limited_func(request, *args, **kwargs)
            except Exception as e:
                if "RateLimitExceeded" in str(type(e)):
                    retry_after = _parse_retry_after(limit_string)
                    raise HTTPException(
                        status_code=429,
                        detail="Rate limit exceeded. Please try again later.",
                        headers={"Retry-After": str(retry_after)},
                    )
                raise

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        # Note: Sync functions still exist but wrapper is async for config access
        return sync_wrapper

    return decorator


async def get_current_limits() -> dict:
    """
    Get current rate limit settings (for admin API).

    Returns:
        {
            "global_enabled": True,
            "limits": {
                "rate_limit.payment.checkout": {"limit": 5, "window": "minute", "enabled": True},
                ...
            },
            "storage": "redis" or "memory"
        }
    """
    config_service = await get_config_service()
    configs = await config_service.get_all_configs("rate_limit")

    limits = {}
    global_enabled = True

    for config in configs:
        key = config.get("key")
        raw_value = config.get("value")
        try:
            value = json.loads(raw_value) if isinstance(raw_value, str) else raw_value
        except (json.JSONDecodeError, TypeError):
            value = raw_value

        if key == "rate_limit.global.enabled":
            global_enabled = value.get("enabled", True) if isinstance(value, dict) else True
        else:
            limits[key] = value

    # Use defaults if no limits found
    if not limits:
        limits = {k: v for k, v in DEFAULT_RATE_LIMITS.items() if k != "rate_limit.global.enabled"}

    return {
        "global_enabled": global_enabled,
        "limits": limits,
        "storage": "redis" if is_redis_available() else "memory"
    }
