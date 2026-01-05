"""
Redis Client Module
Redis 客户端管理模块

Provides:
- Connection pool management
- Health check
- Graceful shutdown

Uses Railway Redis plugin (REDIS_URL environment variable)
"""

import os
import logging
from typing import Optional

import redis

logger = logging.getLogger(__name__)

# Environment variable from Railway Redis plugin
REDIS_URL = os.environ.get("REDIS_URL")

# Connection pool configuration
POOL_MAX_CONNECTIONS = 10
SOCKET_TIMEOUT = 5  # seconds
SOCKET_CONNECT_TIMEOUT = 5  # seconds
HEALTH_CHECK_INTERVAL = 30  # seconds

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
                decode_responses=True,  # Return strings instead of bytes
            )
            _redis_client = redis.Redis(connection_pool=_redis_pool)
            
            # Test connection
            _redis_client.ping()
            logger.info("[Redis] ✅ Connected successfully")
            
        except redis.ConnectionError as e:
            logger.error(f"[Redis] ❌ Connection failed: {e}")
            _redis_client = None
        except Exception as e:
            logger.error(f"[Redis] ❌ Initialization failed: {e}")
            _redis_client = None
    
    return _redis_client


def is_redis_available() -> bool:
    """
    Check if Redis is available and responsive.
    
    Returns:
        True if Redis is available, False otherwise
    """
    client = get_redis_client()
    if not client:
        return False
    
    try:
        return client.ping()
    except Exception as e:
        logger.warning(f"[Redis] Health check failed: {e}")
        return False


def close_redis():
    """
    Close Redis connection (for graceful shutdown).
    """
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
    """
    Get Redis server info (for monitoring/debugging).
    
    Returns:
        Dict with Redis info or error message
    """
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
