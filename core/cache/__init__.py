"""
Core Cache Layer - Framework level caching abstractions.

This module provides:
- ICacheProvider: Abstract interface for cache providers
- RedisCacheProvider: Redis-based cache implementation
- MemoryCacheProvider: In-memory fallback implementation
- CacheService: Unified cache service with automatic fallback

@package core.cache
@version 1.0.0

Design Principles:
- NO business logic here (no domain-specific cache keys)
- All code should be reusable in any FastAPI project
- Domain-specific cache keys go to respective domain modules
"""

from .interface import ICacheProvider
from .memory_provider import MemoryCacheProvider
from .redis_provider import RedisCacheProvider, get_redis_client, is_redis_available, close_redis
from .service import CacheService, cache_service

__all__ = [
    # Interface
    'ICacheProvider',
    # Providers
    'MemoryCacheProvider',
    'RedisCacheProvider',
    'get_redis_client',
    'is_redis_available',
    'close_redis',
    # Service
    'CacheService',
    'cache_service',
]
