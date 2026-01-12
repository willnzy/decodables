"""
System Service - Business logic for system configuration and cache management.

@module domains.platform.system.service
@version 3.30 (DDD Compliant)

Changes in v3.30:
- Complete DDD Migration from api/admin/system.py (SYS-CRITICAL-1)
- All business logic moved to Service layer
- API layer only handles HTTP concerns
- Unified ConfigService and Cache management

Architecture:
- API → Service → Repository (for Config)
- API → Service → CacheProvider (for Cache)
"""

import logging

from core.database import get_async_db_client
from typing import Optional, Dict, List, Any

from infrastructure.repositories import SupabaseConfigRepository
from domains.platform.config_service import ConfigService

logger = logging.getLogger(__name__)


def _get_config_service() -> ConfigService:
    """
    Get ConfigService instance.

    v3.30: DDD Migration helper.
    Returns ConfigService used by system service.
    """
    db_client = await get_async_db_client()
    config_repo = SupabaseConfigRepository(db_client)
    return ConfigService(config_repo)


# ==========================================
# Config Management Functions (7)
# ==========================================

async def get_configs(
    group: Optional[str] = None,
    search: Optional[str] = None,
    offset: int = 0,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Get all system configs with filtering and pagination.

    v3.30: DDD Migration - Uses ConfigRepository via helper.

    Args:
        group: Filter by config group
        search: Search term (not implemented yet)
        offset: Number of records to skip
        limit: Number of records to return

    Returns:
        Dict with items, total, offset, limit
    """
    try:
        db_client = await get_async_db_client()
        config_repo = SupabaseConfigRepository(db_client)

        result = await config_repo.get_paginated(group=group, offset=offset, limit=limit)
        return {
            "items": result["items"],
            "total": result["total"],
            "offset": offset,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"[System] Failed to get configs: {e}")
        return {"items": [], "total": 0, "offset": offset, "limit": limit}


async def get_config_groups() -> List[str]:
    """
    Get available config groups.

    v3.30: DDD Migration - Uses ConfigRepository.

    Returns:
        List of group names
    """
    try:
        db_client = await get_async_db_client()
        config_repo = SupabaseConfigRepository(db_client)

        groups = await config_repo.get_groups()
        return groups
    except Exception as e:
        logger.error(f"[System] Failed to get config groups: {e}")
        return []


async def create_config(
    key: str,
    value: str,
    value_type: str,
    group: str,
    description: Optional[str],
    admin_id: str
) -> Optional[Dict[str, Any]]:
    """
    Create a new system config.

    v3.30: DDD Migration - Uses ConfigRepository.

    Args:
        key: Config key
        value: Config value
        value_type: Value type (text/json/number/boolean/encrypted)
        group: Config group
        description: Optional description
        admin_id: Admin user ID

    Returns:
        Created config record or None
    """
    try:
        db_client = await get_async_db_client()
        config_repo = SupabaseConfigRepository(db_client)

        result = await config_repo.create(
            key=key,
            value=value,
            group=group,
            description=description,
            value_type=value_type,
            admin_id=admin_id
        )
        return result
    except Exception as e:
        logger.error(f"[System] Failed to create config: {e}")
        return None


async def update_config(
    key: str,
    value: Optional[str] = None,
    description: Optional[str] = None,
    is_active: Optional[bool] = None,
    admin_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Update an existing config.

    v3.30: DDD Migration - Uses ConfigRepository.

    Args:
        key: Config key
        value: New value
        description: New description
        is_active: Active status
        admin_id: Admin user ID

    Returns:
        Updated config record or None
    """
    try:
        db_client = await get_async_db_client()
        config_repo = SupabaseConfigRepository(db_client)

        result = await config_repo.update(
            key=key,
            value=value,
            description=description,
            is_active=is_active,
            admin_id=admin_id
        )
        return result
    except Exception as e:
        logger.error(f"[System] Failed to update config: {e}")
        return None


async def delete_config(key: str, admin_id: Optional[str] = None) -> bool:
    """
    Delete a system config.

    v3.30: DDD Migration - Uses ConfigRepository.

    Args:
        key: Config key
        admin_id: Admin user ID (for audit)

    Returns:
        True if deleted successfully
    """
    try:
        db_client = await get_async_db_client()
        config_repo = SupabaseConfigRepository(db_client)

        result = await config_repo.delete(key, admin_id)
        return result
    except Exception as e:
        logger.error(f"[System] Failed to delete config: {e}")
        return False


async def get_config_audit(
    config_key: Optional[str] = None,
    offset: int = 0,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Get config change history.

    v3.30: DDD Migration - Uses ConfigRepository.

    Args:
        config_key: Filter by config key
        offset: Number of records to skip
        limit: Number of records to return

    Returns:
        List of audit log records
    """
    try:
        db_client = await get_async_db_client()
        config_repo = SupabaseConfigRepository(db_client)

        logs = await config_repo.get_audit_logs(config_key=config_key, offset=offset, limit=limit)
        return logs
    except Exception as e:
        logger.error(f"[System] Failed to get config audit logs: {e}")
        return []


async def invalidate_config_cache(key: Optional[str] = None) -> bool:
    """
    Invalidate config cache.

    v3.30: DDD Migration - Uses ConfigRepository.

    Args:
        key: Specific key to invalidate, or None for all

    Returns:
        True if successful
    """
    try:
        db_client = await get_async_db_client()
        config_repo = SupabaseConfigRepository(db_client)

        config_repo.invalidate_cache(key)
        return True
    except Exception as e:
        logger.error(f"[System] Failed to invalidate cache: {e}")
        return False


# ==========================================
# Cache Management Functions (4)
# ==========================================

async def get_cache_status() -> Dict[str, Any]:
    """
    Get Redis cache status and statistics.

    v3.30: DDD Migration - Encapsulated cache access.

    Returns:
        Dict with status, used_memory, total_keys, etc.
    """
    from core.cache import get_cache_provider

    try:
        cache_provider = get_cache_provider()
        redis = getattr(cache_provider, '_client', None) if hasattr(cache_provider, '_client') else None

        if not redis:
            return {"status": "disconnected", "error": "Redis not connected"}

        info = redis.info()
        return {
            "status": "connected",
            "used_memory": info.get("used_memory_human"),
            "total_keys": redis.dbsize(),
            "connected_clients": info.get("connected_clients"),
            "uptime_seconds": info.get("uptime_in_seconds"),
        }
    except Exception as e:
        logger.error(f"[System] Failed to get cache status: {e}")
        return {"status": "error", "error": "Failed to get cache status"}


async def list_cache_keys(pattern: str = "*", limit: int = 100) -> Dict[str, Any]:
    """
    List cache keys matching pattern.

    v3.30: DDD Migration - Encapsulated cache access.

    Args:
        pattern: Key pattern to match
        limit: Max keys to return

    Returns:
        Dict with keys, total, pattern
    """
    from core.cache import get_cache_provider

    try:
        cache_provider = get_cache_provider()
        redis = getattr(cache_provider, '_client', None) if hasattr(cache_provider, '_client') else None

        if not redis:
            return {"keys": [], "error": "Redis not connected", "pattern": pattern}

        keys = []
        cursor = 0
        while len(keys) < limit:
            cursor, batch = redis.scan(cursor, match=pattern, count=100)
            keys.extend([k.decode() if isinstance(k, bytes) else k for k in batch])
            if cursor == 0:
                break

        return {"keys": keys[:limit], "total": len(keys), "pattern": pattern}
    except Exception as e:
        logger.error(f"[System] Failed to list cache keys: {e}")
        return {"keys": [], "error": "Failed to list cache keys", "pattern": pattern}


async def delete_cache_key(key: str) -> Dict[str, Any]:
    """
    Delete a specific cache key.

    v3.30: DDD Migration - Encapsulated cache access.

    Args:
        key: Cache key to delete

    Returns:
        Dict with status and key
    """
    from core.cache import get_cache_provider

    try:
        cache_provider = get_cache_provider()
        redis = getattr(cache_provider, '_client', None) if hasattr(cache_provider, '_client') else None

        if not redis:
            raise Exception("Redis not connected")

        deleted = redis.delete(key)
        return {"status": "deleted" if deleted else "not_found", "key": key}
    except Exception as e:
        logger.error(f"[System] Failed to delete cache key: {e}")
        raise


async def clear_all_cache() -> bool:
    """
    Clear all cache (use with caution).

    v3.30: DDD Migration - Encapsulated cache access.

    Returns:
        True if successful
    """
    from core.cache import get_cache_provider

    try:
        cache_provider = get_cache_provider()
        redis = getattr(cache_provider, '_client', None) if hasattr(cache_provider, '_client') else None

        if not redis:
            raise Exception("Redis not connected")

        redis.flushdb()
        return True
    except Exception as e:
        logger.error(f"[System] Failed to clear cache: {e}")
        raise
