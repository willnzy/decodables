"""
Dynamic Rate Limiter
动态速率限制器 - 从数据库读取配置，使用 Redis 存储

Provides:
- Dynamic rate limits from system_configs
- Redis storage for distributed rate limiting
- Memory fallback when Redis unavailable
"""

import json
import logging
from functools import wraps
from typing import Callable

from fastapi import Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address

from services.config_service import get_rate_limit_string, is_rate_limit_enabled, get_config
from core.cache import is_redis_available
from core.cache.redis_provider import get_redis_client

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


def dynamic_limit(config_key: str):
    """
    Decorator for dynamic rate limiting based on database config.
    
    Reads limit config from system_configs table and applies it.
    
    Args:
        config_key: Config key (e.g., "rate_limit.payment.checkout")
    
    Usage:
        @app.post("/api/payment/checkout")
        @dynamic_limit("rate_limit.payment.checkout")
        def pay(request: Request, ...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(request: Request, *args, **kwargs):
            # Check if rate limiting is enabled
            if not is_rate_limit_enabled(config_key):
                return await func(request, *args, **kwargs)
            
            # Get limit string
            limit_string = get_rate_limit_string(config_key)
            
            try:
                # Apply rate limit
                limited_func = limiter.limit(limit_string)(func)
                return await limited_func(request, *args, **kwargs)
            except Exception as e:
                if "RateLimitExceeded" in str(type(e)):
                    raise HTTPException(
                        status_code=429,
                        detail=f"Rate limit exceeded. Please try again later. (Limit: {limit_string})"
                    )
                raise
        
        @wraps(func)
        def sync_wrapper(request: Request, *args, **kwargs):
            # Check if rate limiting is enabled
            if not is_rate_limit_enabled(config_key):
                return func(request, *args, **kwargs)
            
            limit_string = get_rate_limit_string(config_key)
            
            try:
                limited_func = limiter.limit(limit_string)(func)
                return limited_func(request, *args, **kwargs)
            except Exception as e:
                if "RateLimitExceeded" in str(type(e)):
                    raise HTTPException(
                        status_code=429,
                        detail=f"Rate limit exceeded. Please try again later. (Limit: {limit_string})"
                    )
                raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def get_current_limits() -> dict:
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
    from services.config_service import get_all_configs, DEFAULT_RATE_LIMITS
    
    configs = get_all_configs("rate_limit")
    
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
