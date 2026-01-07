"""
Cache Service - Unified caching interface with automatic fallback.

@module core.cache.service
@version 1.0.0
"""

import json
import time
import logging
from typing import Optional, Any, Callable

from .interface import ICacheProvider
from .redis_provider import RedisCacheProvider, get_redis_client, is_redis_available
from .memory_provider import MemoryCacheProvider

logger = logging.getLogger(__name__)


class CacheService:
    """
    Unified cache service with Redis primary and memory fallback.

    Features:
    - Automatic fallback to memory when Redis unavailable
    - Cache penetration protection with null markers
    - JSON serialization helpers
    - Async fetch support
    """

    NULL_MARKER = "__CACHE_NULL__"
    NULL_TTL = 60

    def __init__(self):
        self._redis = RedisCacheProvider()
        self._fallback = MemoryCacheProvider()
        self._using_redis = False
        self._last_redis_check = 0
        self._redis_check_interval = 30

    def _get_provider(self) -> ICacheProvider:
        """Get active cache provider with automatic fallback detection."""
        now = time.time()

        if now - self._last_redis_check > self._redis_check_interval:
            self._using_redis = is_redis_available()
            self._last_redis_check = now

        if self._using_redis:
            client = get_redis_client()
            if client:
                return self._redis
            self._using_redis = False

        return self._fallback

    # ==========================================
    # Generic Operations
    # ==========================================

    def get(self, key: str) -> Optional[str]:
        """Get string value from cache."""
        provider = self._get_provider()
        try:
            return provider.get(key)
        except Exception as e:
            logger.error(f"[Cache] Get error: {e}")
            return self._fallback.get(key)

    def set(self, key: str, value: str, ttl: int = 0) -> bool:
        """Set string value in cache."""
        provider = self._get_provider()
        try:
            return provider.set(key, value, ttl)
        except Exception as e:
            logger.error(f"[Cache] Set error: {e}")
            return self._fallback.set(key, value, ttl)

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        provider = self._get_provider()
        try:
            if provider != self._fallback:
                provider.delete(key)
            self._fallback.delete(key)
            return True
        except Exception as e:
            logger.error(f"[Cache] Delete error: {e}")
            self._fallback.delete(key)
            return True

    def delete_pattern(self, pattern: str) -> bool:
        """Delete keys matching pattern."""
        provider = self._get_provider()
        try:
            if provider != self._fallback:
                provider.delete_pattern(pattern)
            self._fallback.delete_pattern(pattern)
            return True
        except Exception as e:
            logger.error(f"[Cache] Delete pattern error: {e}")
            self._fallback.delete_pattern(pattern)
            return True

    # ==========================================
    # Cache Penetration Protection
    # ==========================================

    def get_with_null_protection(self, key: str) -> tuple:
        """
        Get value with null value protection.

        Returns:
            (is_cached, value) tuple
            - (False, None): Key not in cache
            - (True, None): Key cached as null
            - (True, value): Key cached with value
        """
        value = self.get(key)
        if value is None:
            return (False, None)
        if value == self.NULL_MARKER:
            return (True, None)
        try:
            return (True, json.loads(value))
        except json.JSONDecodeError:
            return (True, value)

    def set_null(self, key: str, ttl: int = None) -> bool:
        """Cache null value to prevent penetration."""
        return self.set(key, self.NULL_MARKER, ttl or self.NULL_TTL)

    def get_or_fetch(
        self,
        key: str,
        fetch_func: Callable,
        ttl: int = 300,
        null_ttl: int = None
    ) -> Optional[Any]:
        """Get from cache or fetch from source."""
        is_cached, value = self.get_with_null_protection(key)
        if is_cached:
            return value

        try:
            result = fetch_func()
        except Exception as e:
            logger.error(f"[Cache] Fetch error for {key}: {e}")
            return None

        if result is None:
            self.set_null(key, null_ttl)
        else:
            self.set_json(key, result, ttl)

        return result

    async def get_or_fetch_async(
        self,
        key: str,
        fetch_func,
        ttl: int = 300,
        null_ttl: int = None
    ) -> Optional[Any]:
        """Async version of get_or_fetch."""
        is_cached, value = self.get_with_null_protection(key)
        if is_cached:
            return value

        try:
            result = await fetch_func()
        except Exception as e:
            logger.error(f"[Cache] Async fetch error for {key}: {e}")
            return None

        if result is None:
            self.set_null(key, null_ttl)
        else:
            self.set_json(key, result, ttl)

        return result

    # ==========================================
    # JSON Operations
    # ==========================================

    def get_json(self, key: str) -> Optional[Any]:
        """Get JSON value from cache."""
        value = self.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            logger.warning(f"[Cache] Invalid JSON for key: {key}")
            return None

    def set_json(self, key: str, value: Any, ttl: int = 0) -> bool:
        """Set JSON value in cache."""
        try:
            return self.set(key, json.dumps(value), ttl)
        except (TypeError, ValueError) as e:
            logger.error(f"[Cache] JSON serialize error: {e}")
            return False

    # ==========================================
    # Utility Methods
    # ==========================================

    def is_redis_active(self) -> bool:
        """Check if Redis is currently active."""
        return self._using_redis and get_redis_client() is not None

    def get_backend_info(self) -> dict:
        """Get information about current cache backend."""
        return {
            "backend": "redis" if self.is_redis_active() else "memory",
            "redis_available": self._using_redis,
            "fallback_size": self._fallback.size(),
        }


# Singleton instance
cache_service = CacheService()
