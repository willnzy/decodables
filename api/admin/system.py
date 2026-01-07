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
from infrastructure.db_compat import (
    admin_get_system_configs, admin_get_config_groups,
    admin_create_system_config, admin_update_system_config,
    admin_delete_system_config, admin_get_config_audit_logs,
    invalidate_config_cache_api, supabase
)

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
def get_configs(
    group: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    admin: dict = Depends(require_admin)
):
    """Get all system configs with filtering."""
    return admin_get_system_configs(group=group, search=search, page=page, limit=limit)


@router.get("/configs/groups")
def get_config_groups(admin: dict = Depends(require_admin)):
    """Get available config groups."""
    return admin_get_config_groups()


@router.post("/configs")
def create_config(req: ConfigCreateRequest, admin: dict = Depends(require_admin)):
    """Create a new system config."""
    try:
        result = admin_create_system_config(
            key=req.key,
            value=req.value,
            value_type=req.value_type,
            config_group=req.config_group,
            description=req.description,
            admin_id=admin["id"]
        )
        return {"status": "created", "config": result}
    except Exception as e:
        raise HTTPException(400, str(e))


@router.put("/configs/{key:path}")
def update_config(key: str, req: ConfigUpdateRequest, admin: dict = Depends(require_admin)):
    """Update an existing config."""
    try:
        result = admin_update_system_config(
            key=key,
            value=req.value,
            value_type=req.value_type,
            config_group=req.config_group,
            description=req.description,
            is_active=req.is_active,
            admin_id=admin["id"]
        )
        return {"status": "updated", "config": result}
    except Exception as e:
        raise HTTPException(400, str(e))


@router.delete("/configs/{key:path}")
def delete_config(key: str, admin: dict = Depends(require_admin)):
    """Soft delete a config."""
    try:
        admin_delete_system_config(key, admin["id"])
        return {"status": "deleted", "key": key}
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("/configs/audit")
def get_config_audit(
    config_key: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    admin: dict = Depends(require_admin)
):
    """Get config change history."""
    return admin_get_config_audit_logs(config_key=config_key, page=page, limit=limit)


@router.post("/configs/cache/invalidate")
def invalidate_cache(key: Optional[str] = None, admin: dict = Depends(require_admin)):
    """Invalidate config cache."""
    try:
        invalidate_config_cache_api(key)
        return {"status": "invalidated", "key": key or "all"}
    except Exception as e:
        raise HTTPException(500, str(e))


# ==========================================
# Cache Management Routes
# ==========================================

@router.get("/system/cache/status")
def get_cache_status(admin: dict = Depends(require_admin)):
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
def list_cache_keys(
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
def delete_cache_key(key: str, admin: dict = Depends(require_admin)):
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
def clear_all_cache(admin: dict = Depends(require_admin)):
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
