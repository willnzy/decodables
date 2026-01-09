"""
Admin System Router - System configs, cache, and metrics

@module api.admin.system
@version 3.30 (DDD Compliant)

Changes:
- v3.30: Complete DDD architecture migration (SYS-CRITICAL-1)
  - API layer now calls Service layer instead of Repository
  - Moved constants to domains/platform/system/constants.py (SYS-MEDIUM-1)
  - Unified config and cache management through SystemService
  - All 11 endpoints now follow API → Service → Repository pattern

- v3.25: Security improvements
  - SYS-MEDIUM-1: Added rate limiting to all 11 endpoints
  - SYS-MEDIUM-2: Migrated from page to offset pagination
  - SYS-MEDIUM-3: Added value_type and config_group enum validation
  - SYS-MEDIUM-4: Added pattern validation for cache keys
  - SYS-LOW-1: Added field length limits to request models
  - SYS-LOW-2: Limited error exposure

Includes:
- System configuration management
- Cache management
- System metrics
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request, Query
from pydantic import BaseModel, Field, field_validator

from dependencies import require_admin
from infrastructure.rate_limiter import limiter

# v3.30: Import from Domain layer (DDD Migration)
from domains.platform.system import (
    # Config management (7)
    get_configs,
    get_config_groups,
    create_config,
    update_config,
    delete_config,
    get_config_audit,
    invalidate_config_cache,
    # Cache management (4)
    get_cache_status,
    list_cache_keys,
    delete_cache_key,
    clear_all_cache,
)
from domains.platform.system.constants import (
    VALID_VALUE_TYPES,
    VALID_CONFIG_GROUPS,
    CACHE_KEY_PATTERN,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["admin-system-v2"])


# ==========================================
# Request Models (v3.25: Added field validation)
# ==========================================

class ConfigCreateRequest(BaseModel):
    # v3.25: SYS-LOW-1 - Field length limits
    key: str = Field(..., min_length=1, max_length=200)
    value: str = Field(..., min_length=0, max_length=10000)
    value_type: str = Field("text", max_length=20)
    config_group: str = Field("general", max_length=50)
    description: Optional[str] = Field(None, max_length=500)

    # v3.25: SYS-MEDIUM-3 - value_type enum validation
    @field_validator("value_type")
    @classmethod
    def validate_value_type(cls, v: str) -> str:
        if v not in VALID_VALUE_TYPES:
            raise ValueError(f"Invalid value_type. Must be one of: {', '.join(VALID_VALUE_TYPES)}")
        return v

    # v3.25: SYS-MEDIUM-3 - config_group enum validation
    @field_validator("config_group")
    @classmethod
    def validate_config_group(cls, v: str) -> str:
        if v not in VALID_CONFIG_GROUPS:
            raise ValueError(f"Invalid config_group. Must be one of: {', '.join(VALID_CONFIG_GROUPS)}")
        return v


class ConfigUpdateRequest(BaseModel):
    # v3.25: SYS-LOW-1 - Field length limits
    value: Optional[str] = Field(None, max_length=10000)
    value_type: Optional[str] = Field(None, max_length=20)
    config_group: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None

    # v3.25: SYS-MEDIUM-3 - value_type enum validation
    @field_validator("value_type")
    @classmethod
    def validate_value_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_VALUE_TYPES:
            raise ValueError(f"Invalid value_type. Must be one of: {', '.join(VALID_VALUE_TYPES)}")
        return v

    # v3.25: SYS-MEDIUM-3 - config_group enum validation
    @field_validator("config_group")
    @classmethod
    def validate_config_group(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_CONFIG_GROUPS:
            raise ValueError(f"Invalid config_group. Must be one of: {', '.join(VALID_CONFIG_GROUPS)}")
        return v


# ==========================================
# System Configuration Routes (v3.30: DDD Migration)
# ==========================================

@router.get("/configs")
@limiter.limit("30/minute")
async def get_configs_endpoint(
    request: Request,
    group: Optional[str] = Query(None, max_length=50),
    search: Optional[str] = Query(None, max_length=100),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return (1-100)"),
    admin: dict = Depends(require_admin)
):
    """Get all system configs with filtering."""
    result = await get_configs(group=group, search=search, offset=offset, limit=limit)
    return result


@router.get("/configs/groups")
@limiter.limit("30/minute")
async def get_config_groups_endpoint(request: Request, admin: dict = Depends(require_admin)):
    """Get available config groups."""
    groups = await get_config_groups()
    return {"groups": groups}


@router.post("/configs")
@limiter.limit("10/minute")
async def create_config_endpoint(request: Request, req: ConfigCreateRequest, admin: dict = Depends(require_admin)):
    """Create a new system config."""
    try:
        result = await create_config(
            key=req.key,
            value=req.value,
            value_type=req.value_type,
            group=req.config_group,
            description=req.description,
            admin_id=admin["id"]
        )

        if not result:
            raise HTTPException(400, "Failed to create config")

        return {"status": "created", "config": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin] Config create failed: {e}")
        raise HTTPException(400, "Failed to create config")


@router.put("/configs/{key:path}")
@limiter.limit("10/minute")
async def update_config_endpoint(request: Request, key: str, req: ConfigUpdateRequest, admin: dict = Depends(require_admin)):
    """Update an existing config."""
    # v3.25: SYS-LOW-1 - Validate key length
    if len(key) > 200:
        raise HTTPException(400, "Config key too long (max 200 characters)")

    try:
        result = await update_config(
            key=key,
            value=req.value,
            description=req.description,
            is_active=req.is_active,
            admin_id=admin["id"]
        )

        if not result:
            raise HTTPException(400, "Failed to update config")

        return {"status": "updated", "config": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin] Config update failed: {e}")
        raise HTTPException(400, "Failed to update config")


@router.delete("/configs/{key:path}")
@limiter.limit("10/minute")
async def delete_config_endpoint(request: Request, key: str, admin: dict = Depends(require_admin)):
    """Soft delete a config."""
    # v3.25: SYS-LOW-1 - Validate key length
    if len(key) > 200:
        raise HTTPException(400, "Config key too long (max 200 characters)")

    try:
        result = await delete_config(key, admin["id"])

        if not result:
            raise HTTPException(400, "Failed to delete config")

        return {"status": "deleted", "key": key}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin] Config delete failed: {e}")
        raise HTTPException(400, "Failed to delete config")


@router.get("/configs/audit")
@limiter.limit("30/minute")
async def get_config_audit_endpoint(
    request: Request,
    config_key: Optional[str] = Query(None, max_length=200),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return (1-100)"),
    admin: dict = Depends(require_admin)
):
    """Get config change history."""
    logs = await get_config_audit(config_key=config_key, offset=offset, limit=limit)
    return {"logs": logs, "total": len(logs), "offset": offset, "limit": limit}


@router.post("/configs/cache/invalidate")
@limiter.limit("5/minute")
async def invalidate_cache_endpoint(
    request: Request,
    key: Optional[str] = Query(None, max_length=200),
    admin: dict = Depends(require_admin)
):
    """Invalidate config cache."""
    try:
        result = await invalidate_config_cache(key)

        if not result:
            raise HTTPException(500, "Failed to invalidate cache")

        return {"status": "invalidated", "key": key or "all"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin] Cache invalidate failed: {e}")
        raise HTTPException(500, "Failed to invalidate cache")


# ==========================================
# Cache Management Routes (v3.30: DDD Migration)
# ==========================================

@router.get("/system/cache/status")
@limiter.limit("30/minute")
async def get_cache_status_endpoint(request: Request, admin: dict = Depends(require_admin)):
    """Get Redis cache status and statistics."""
    result = await get_cache_status()
    return result


@router.get("/system/cache/keys")
@limiter.limit("30/minute")
async def list_cache_keys_endpoint(
    request: Request,
    pattern: str = Query("*", max_length=100),
    limit: int = Query(100, ge=1, le=1000, description="Max keys to return (1-1000)"),
    admin: dict = Depends(require_admin)
):
    """List cache keys matching pattern."""
    # v3.25: SYS-MEDIUM-4 - Validate pattern to prevent injection
    if not CACHE_KEY_PATTERN.match(pattern):
        raise HTTPException(400, "Invalid pattern. Only alphanumeric, underscore, colon, asterisk, hyphen, and dot allowed")

    result = await list_cache_keys(pattern=pattern, limit=limit)
    return result


@router.delete("/system/cache/key/{key:path}")
@limiter.limit("10/minute")
async def delete_cache_key_endpoint(request: Request, key: str, admin: dict = Depends(require_admin)):
    """Delete a specific cache key."""
    # v3.25: SYS-MEDIUM-4 - Validate key pattern
    if len(key) > 200:
        raise HTTPException(400, "Cache key too long (max 200 characters)")

    try:
        result = await delete_cache_key(key)
        return result
    except Exception as e:
        logger.error(f"[Admin] Cache key delete failed: {e}")
        raise HTTPException(500, "Failed to delete cache key")


@router.post("/system/cache/clear-all")
@limiter.limit("2/minute")
async def clear_all_cache_endpoint(request: Request, admin: dict = Depends(require_admin)):
    """Clear all cache (use with caution)."""
    try:
        result = await clear_all_cache()

        if not result:
            raise HTTPException(500, "Failed to clear cache")

        return {"status": "cleared"}
    except Exception as e:
        logger.error(f"[Admin] Cache clear failed: {e}")
        raise HTTPException(500, "Failed to clear cache")
