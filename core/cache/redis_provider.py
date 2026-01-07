"""
Redis Cache Provider - Redis-based cache implementation.

@module core.cache.redis_provider
@version 1.0.0
"""

import os
import logging
from typing import Optional

import redis

from .interface import ICacheProvider

logger = logging.getLogger(__name__)

# Environment variable for Redis connection
REDIS_URL = os.environ.get("REDIS_URL")

# Connection pool configuration (Railway optimized)
# Can be overridden via environment variables for production scaling
POOL_MAX_CONNECTIONS = int(os.environ.get("REDIS_MAX_CONNECTIONS", "50"))  # Increased from 10 for multiple web instances
SOCKET_TIMEOUT = int(os.environ.get("REDIS_SOCKET_TIMEOUT", "5"))  # seconds
SOCKET_CONNECT_TIMEOUT = int(os.environ.get("REDIS_CONNECT_TIMEOUT", "5"))  # seconds
HEALTH_CHECK_INTERVAL = int(os.environ.get("REDIS_HEALTH_CHECK_INTERVAL", "30"))  # seconds

# Module-level singleton
_redis_pool: Optional[redis.ConnectionPool] = None
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> Optional[redis.Redis]:
    """
    Get Redis client (singleton with connection pooling).

    Returns:
        Redis client instance, or None if REDIS_URL not configured
    """
    global _redis_pool, _redis_client

    if not REDIS_URL:
        logger.warning("[Redis] REDIS_URL not configured, caching will use memory fallback")
        return None

    if _redis_client is None:
        try:
            _redis_pool = redis.ConnectionPool.from_url(
                REDIS_URL,
                max_connections=POOL_MAX_CONNECTIONS,
                socket_timeout=SOCKET_TIMEOUT,
                socket_connect_timeout=SOCKET_CONNECT_TIMEOUT,
                health_check_interval=HEALTH_CHECK_INTERVAL,
                decode_responses=True,
            )
            _redis_client = redis.Redis(connection_pool=_redis_pool)
            _redis_client.ping()
            logger.info("[Redis] Connected successfully")
        except redis.ConnectionError as e:
            logger.error(f"[Redis] Connection failed: {e}")
            _redis_client = None
        except Exception as e:
            logger.error(f"[Redis] Initialization failed: {e}")
            _redis_client = None

    return _redis_client


def is_redis_available() -> bool:
    """Check if Redis is available and responsive."""
    client = get_redis_client()
    if not client:
        return False
    try:
        return client.ping()
    except Exception as e:
        logger.warning(f"[Redis] Health check failed: {e}")
        return False


def close_redis():
    """Close Redis connection (for graceful shutdown)."""
    global _redis_pool, _redis_client

    if _redis_client:
        try:
            _redis_client.close()
        except Exception as e:
            logger.warning(f"[Redis] Error closing client: {e}")
        _redis_client = None

    if _redis_pool:
        try:
            _redis_pool.disconnect()
        except Exception as e:
            logger.warning(f"[Redis] Error closing pool: {e}")
        _redis_pool = None

    logger.info("[Redis] Connection closed")


def get_redis_info() -> dict:
    """Get Redis server info (for monitoring/debugging)."""
    client = get_redis_client()
    if not client:
        return {"status": "unavailable", "reason": "REDIS_URL not configured"}

    try:
        info = client.info()
        return {
            "status": "connected",
            "redis_version": info.get("redis_version"),
            "connected_clients": info.get("connected_clients"),
            "used_memory_human": info.get("used_memory_human"),
            "uptime_in_seconds": info.get("uptime_in_seconds"),
        }
    except Exception as e:
        return {"status": "error", "reason": str(e)}


class RedisCacheProvider(ICacheProvider):
    """
    Redis-based cache provider.

    Features:
    - Connection pooling
    - Automatic reconnection
    - Pattern-based deletion with SCAN
    """

    def __init__(self):
        self._client: Optional[redis.Redis] = None

    def _get_client(self) -> Optional[redis.Redis]:
        """Get or create Redis client."""
        if self._client is None:
            self._client = get_redis_client()
        return self._client

    def get(self, key: str) -> Optional[str]:
        """Get value from Redis."""
        client = self._get_client()
        if not client:
            return None
        try:
            return client.get(key)
        except Exception as e:
            logger.error(f"[Redis] Get error for {key}: {e}")
            return None

    def set(self, key: str, value: str, ttl: int = 0) -> bool:
        """Set value in Redis with optional TTL."""
        client = self._get_client()
        if not client:
            return False
        try:
            if ttl > 0:
                client.setex(key, ttl, value)
            else:
                client.set(key, value)
            return True
        except Exception as e:
            logger.error(f"[Redis] Set error for {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from Redis."""
        client = self._get_client()
        if not client:
            return False
        try:
            client.delete(key)
            return True
        except Exception as e:
            logger.error(f"[Redis] Delete error for {key}: {e}")
            return False

    def delete_pattern(self, pattern: str) -> bool:
        """Delete keys matching pattern using SCAN."""
        client = self._get_client()
        if not client:
            return False
        try:
            cursor = 0
            while True:
                cursor, keys = client.scan(cursor, match=pattern, count=100)
                if keys:
                    client.delete(*keys)
                if cursor == 0:
                    break
            return True
        except Exception as e:
            logger.error(f"[Redis] Delete pattern error for {pattern}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        client = self._get_client()
        if not client:
            return False
        try:
            return bool(client.exists(key))
        except Exception as e:
            logger.error(f"[Redis] Exists error for {key}: {e}")
            return False

    def clear(self) -> bool:
        """Clear all keys (use with caution)."""
        client = self._get_client()
        if not client:
            return False
        try:
            client.flushdb()
            return True
        except Exception as e:
            logger.error(f"[Redis] Clear error: {e}")
            return False

    def size(self) -> int:
        """Get number of keys in Redis."""
        client = self._get_client()
        if not client:
            return 0
        try:
            return client.dbsize()
        except Exception as e:
            logger.error(f"[Redis] Size error: {e}")
            return 0
