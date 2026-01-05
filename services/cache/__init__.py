"""
Cache Module
缓存模块

Provides unified caching with Redis primary and memory fallback.

Usage:
    from services.cache import cache_service
    
    # Generic caching
    cache_service.set("my_key", "my_value", ttl=60)
    value = cache_service.get("my_key")
    
    # JSON caching
    cache_service.set_json("my_data", {"foo": "bar"}, ttl=300)
    data = cache_service.get_json("my_data")
    
    # Domain-specific caching
    cache_service.set_config("rate_limit.api", {"limit": 100})
    config = cache_service.get_config("rate_limit.api")
"""

from .cache_service import cache_service
from .cache_keys import CacheTTL, CacheNamespace
from .redis_client import (
    is_redis_available,
    get_redis_client,
    close_redis,
    get_redis_info,
)

__all__ = [
    "cache_service",
    "CacheTTL",
    "CacheNamespace",
    "is_redis_available",
    "get_redis_client",
    "close_redis",
    "get_redis_info",
]
