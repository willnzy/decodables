"""
Admin System Router - System configs, cache, and metrics

@module api.admin.system
@version 3.24

Includes:
- System configuration management
- Cache management
- System metrics
"""

import logging
from typing import Optional
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from dependencies import require_admin
from core.database import get_database_client
from infrastructure.repositories import SupabaseConfigRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["admin-system-v2"])


# ==========================================
# Request Models
# ==========================================

class ConfigCreateRequest(BaseModel):
    key: str
    value: str
    value_type: str = "text"
    config_group: str = "general"
    description: Optional[str] = None


class ConfigUpdateRequest(BaseModel):
    value: Optional[str] = None
    value_type: Optional[str] = None
    config_group: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


# ==========================================
# System Configuration Routes
# ==========================================

@router.get("/configs")
async def get_configs(
    group: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    admin: dict = Depends(require_admin)
):
    """Get all system configs with filtering."""
    db_client = get_database_client()
    config_repo = SupabaseConfigRepository(db_client)

    result = await config_repo.get_paginated(group=group, page=page, limit=limit)
    return {"items": result["items"], "total": result["total"]}


@router.get("/configs/groups")
async def get_config_groups(admin: dict = Depends(require_admin)):
    """Get available config groups."""
    db_client = get_database_client()
    config_repo = SupabaseConfigRepository(db_client)

    groups = await config_repo.get_groups()
    return {"groups": groups}


@router.post("/configs")
async def create_config(req: ConfigCreateRequest, admin: dict = Depends(require_admin)):
    """Create a new system config."""
    try:
        db_client = get_database_client()
        config_repo = SupabaseConfigRepository(db_client)

        result = await config_repo.create(
            key=req.key,
            value=req.value,
            value_type=req.value_type,
            group=req.config_group,
            description=req.description,
            admin_id=admin["id"]
        )
        return {"status": "created", "config": result}
    except Exception as e:
        raise HTTPException(400, str(e))


@router.put("/configs/{key:path}")
async def update_config(key: str, req: ConfigUpdateRequest, admin: dict = Depends(require_admin)):
    """Update an existing config."""
    try:
        db_client = get_database_client()
        config_repo = SupabaseConfigRepository(db_client)

        result = await config_repo.update(
            key=key,
            value=req.value,
            description=req.description,
            is_active=req.is_active,
            admin_id=admin["id"]
        )
        return {"status": "updated", "config": result}
    except Exception as e:
        raise HTTPException(400, str(e))


@router.delete("/configs/{key:path}")
async def delete_config(key: str, admin: dict = Depends(require_admin)):
    """Soft delete a config."""
    try:
        db_client = get_database_client()
        config_repo = SupabaseConfigRepository(db_client)

        await config_repo.delete(key, admin["id"])
        return {"status": "deleted", "key": key}
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("/configs/audit")
async def get_config_audit(
    config_key: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    admin: dict = Depends(require_admin)
):
    """Get config change history."""
    db_client = get_database_client()
    config_repo = SupabaseConfigRepository(db_client)

    logs = await config_repo.get_audit_logs(config_key=config_key, page=page, limit=limit)
    return {"logs": logs, "total": len(logs)}


@router.post("/configs/cache/invalidate")
async def invalidate_cache(key: Optional[str] = None, admin: dict = Depends(require_admin)):
    """Invalidate config cache."""
    try:
        db_client = get_database_client()
        config_repo = SupabaseConfigRepository(db_client)

        config_repo.invalidate_cache(key)
        return {"status": "invalidated", "key": key or "all"}
    except Exception as e:
        raise HTTPException(500, str(e))


# ==========================================
# Cache Management Routes
# ==========================================

@router.get("/system/cache/status")
async def get_cache_status(admin: dict = Depends(require_admin)):
    """Get Redis cache status and statistics."""
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
        return {"status": "error", "error": str(e)}


@router.get("/system/cache/keys")
async def list_cache_keys(
    pattern: str = "*",
    limit: int = 100,
    admin: dict = Depends(require_admin)
):
    """List cache keys matching pattern."""
    from core.cache import get_cache_provider

    try:
        cache_provider = get_cache_provider()
        redis = getattr(cache_provider, '_client', None) if hasattr(cache_provider, '_client') else None
        if not redis:
            return {"keys": [], "error": "Redis not connected"}

        keys = []
        cursor = 0
        while len(keys) < limit:
            cursor, batch = redis.scan(cursor, match=pattern, count=100)
            keys.extend([k.decode() if isinstance(k, bytes) else k for k in batch])
            if cursor == 0:
                break

        return {"keys": keys[:limit], "total": len(keys), "pattern": pattern}
    except Exception as e:
        return {"keys": [], "error": str(e)}


@router.delete("/system/cache/key/{key:path}")
async def delete_cache_key(key: str, admin: dict = Depends(require_admin)):
    """Delete a specific cache key."""
    from core.cache import get_cache_provider

    try:
        cache_provider = get_cache_provider()
        redis = getattr(cache_provider, '_client', None) if hasattr(cache_provider, '_client') else None
        if not redis:
            raise HTTPException(503, "Redis not connected")

        deleted = redis.delete(key)
        return {"status": "deleted" if deleted else "not_found", "key": key}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/system/cache/clear-all")
async def clear_all_cache(admin: dict = Depends(require_admin)):
    """Clear all cache (use with caution)."""
    from core.cache import get_cache_provider

    try:
        cache_provider = get_cache_provider()
        redis = getattr(cache_provider, '_client', None) if hasattr(cache_provider, '_client') else None
        if not redis:
            raise HTTPException(503, "Redis not connected")

        redis.flushdb()
        return {"status": "cleared"}
    except Exception as e:
        raise HTTPException(500, str(e))
