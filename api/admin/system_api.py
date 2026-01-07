"""
Admin System API - System configs, cache, and metrics.

@module api.admin.system_api
@version 1.0.0

Endpoints:
- GET /system/configs - Get all system configs
- GET /system/configs/groups - Get config groups
- POST /system/configs - Create config
- PUT /system/configs/{key} - Update config
- DELETE /system/configs/{key} - Delete config
- GET /system/configs/audit - Get config audit logs
- POST /system/configs/cache/invalidate - Invalidate cache
- GET /system/cache/status - Get cache status
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from dependencies import require_admin
from services.db_service import (
    admin_get_system_configs, admin_get_config_groups,
    admin_create_system_config, admin_update_system_config,
    admin_delete_system_config, admin_get_config_audit_logs,
    invalidate_config_cache_api,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["admin-system-v2"])


# ==========================================
# Request Models
# ==========================================

class ConfigCreateRequest(BaseModel):
    """Config creation request."""
    key: str
    value: str
    value_type: str = "text"
    config_group: str = "general"
    description: Optional[str] = None


class ConfigUpdateRequest(BaseModel):
    """Config update request."""
    value: Optional[str] = None
    value_type: Optional[str] = None
    config_group: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


# ==========================================
# System Configuration
# ==========================================

@router.get("/configs")
async def get_configs(
    group: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    admin: dict = Depends(require_admin),
):
    """Get all system configs with filtering."""
    return admin_get_system_configs(group=group, search=search, page=page, limit=limit)


@router.get("/configs/groups")
async def get_config_groups(
    admin: dict = Depends(require_admin),
):
    """Get available config groups."""
    return admin_get_config_groups()


@router.post("/configs")
async def create_config(
    req: ConfigCreateRequest,
    admin: dict = Depends(require_admin),
):
    """Create a new system config."""
    try:
        result = admin_create_system_config(
            key=req.key,
            value=req.value,
            value_type=req.value_type,
            config_group=req.config_group,
            description=req.description,
            admin_id=admin["id"],
        )
        return {"status": "created", "config": result}
    except Exception as e:
        raise HTTPException(400, str(e))


@router.put("/configs/{key:path}")
async def update_config(
    key: str,
    req: ConfigUpdateRequest,
    admin: dict = Depends(require_admin),
):
    """Update an existing config."""
    try:
        result = admin_update_system_config(
            key=key,
            value=req.value,
            value_type=req.value_type,
            config_group=req.config_group,
            description=req.description,
            is_active=req.is_active,
            admin_id=admin["id"],
        )
        return {"status": "updated", "config": result}
    except Exception as e:
        raise HTTPException(400, str(e))


@router.delete("/configs/{key:path}")
async def delete_config(
    key: str,
    admin: dict = Depends(require_admin),
):
    """Soft delete a config."""
    try:
        admin_delete_system_config(key, admin["id"])
        return {"status": "deleted", "key": key}
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("/configs/audit")
async def get_config_audit(
    config_key: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    admin: dict = Depends(require_admin),
):
    """Get config change history."""
    return admin_get_config_audit_logs(config_key=config_key, page=page, limit=limit)


@router.post("/configs/cache/invalidate")
async def invalidate_cache(
    key: Optional[str] = None,
    admin: dict = Depends(require_admin),
):
    """Invalidate config cache."""
    try:
        invalidate_config_cache_api(key)
        return {"status": "invalidated", "key": key or "all"}
    except Exception as e:
        raise HTTPException(500, str(e))


# ==========================================
# Cache Management
# ==========================================

@router.get("/cache/status")
async def get_cache_status(
    admin: dict = Depends(require_admin),
):
    """Get Redis cache status and statistics."""
    from services.cache import get_redis_client

    try:
        redis_client = get_redis_client()
        if not redis_client:
            return {"status": "unavailable", "message": "Redis not configured"}

        info = redis_client.info("memory")
        db_info = redis_client.info("keyspace")

        return {
            "status": "connected",
            "memory": {
                "used_memory_human": info.get("used_memory_human"),
                "used_memory_peak_human": info.get("used_memory_peak_human"),
                "maxmemory_human": info.get("maxmemory_human", "unlimited"),
            },
            "keys": db_info,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
