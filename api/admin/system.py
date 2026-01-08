"""
Admin System Router - System configs, cache, and metrics

@module api.admin.system
@version 3.25

Changes:
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
import re
from typing import Optional
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Depends, Request, Query
from pydantic import BaseModel, Field, field_validator

from dependencies import require_admin
from core.database import get_database_client
from infrastructure.repositories import SupabaseConfigRepository
from infrastructure.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["admin-system-v2"])


# ==========================================
# Constants (v3.25)
# ==========================================

# v3.25: SYS-MEDIUM-3 - Valid config value types
VALID_VALUE_TYPES = {"text", "json", "number", "boolean", "encrypted"}

# v3.25: SYS-MEDIUM-3 - Valid config groups
VALID_CONFIG_GROUPS = {"general", "feature_flags", "payment", "ai", "notification", "security", "cache"}

# v3.25: SYS-MEDIUM-4 - Cache key pattern validation
CACHE_KEY_PATTERN = re.compile(r"^[a-zA-Z0-9_:*\-\.]+$")


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
# System Configuration Routes (v3.25: Added rate limiting and validation)
# ==========================================

@router.get("/configs")
@limiter.limit("30/minute")
async def get_configs(
    request: Request,
    group: Optional[str] = Query(None, max_length=50),
    search: Optional[str] = Query(None, max_length=100),
    # v3.25: SYS-MEDIUM-2 - Migrated to offset pagination
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return (1-100)"),
    admin: dict = Depends(require_admin)
):
    """Get all system configs with filtering."""
    db_client = get_database_client()
    config_repo = SupabaseConfigRepository(db_client)

    result = await config_repo.get_paginated(group=group, offset=offset, limit=limit)
    return {"items": result["items"], "total": result["total"], "offset": offset, "limit": limit}


@router.get("/configs/groups")
@limiter.limit("30/minute")
async def get_config_groups(request: Request, admin: dict = Depends(require_admin)):
    """Get available config groups."""
    db_client = get_database_client()
    config_repo = SupabaseConfigRepository(db_client)

    groups = await config_repo.get_groups()
    return {"groups": groups}


@router.post("/configs")
@limiter.limit("10/minute")
async def create_config(request: Request, req: ConfigCreateRequest, admin: dict = Depends(require_admin)):
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
        # v3.25: SYS-LOW-2 - Limit error exposure
        logger.error(f"[Admin] Config create failed: {e}")
        raise HTTPException(400, "Failed to create config")


@router.put("/configs/{key:path}")
@limiter.limit("10/minute")
async def update_config(request: Request, key: str, req: ConfigUpdateRequest, admin: dict = Depends(require_admin)):
    """Update an existing config."""
    # v3.25: SYS-LOW-1 - Validate key length
    if len(key) > 200:
        raise HTTPException(400, "Config key too long (max 200 characters)")

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
        # v3.25: SYS-LOW-2 - Limit error exposure
        logger.error(f"[Admin] Config update failed: {e}")
        raise HTTPException(400, "Failed to update config")


@router.delete("/configs/{key:path}")
@limiter.limit("10/minute")
async def delete_config(request: Request, key: str, admin: dict = Depends(require_admin)):
    """Soft delete a config."""
    # v3.25: SYS-LOW-1 - Validate key length
    if len(key) > 200:
        raise HTTPException(400, "Config key too long (max 200 characters)")

    try:
        db_client = get_database_client()
        config_repo = SupabaseConfigRepository(db_client)

        await config_repo.delete(key, admin["id"])
        return {"status": "deleted", "key": key}
    except Exception as e:
        # v3.25: SYS-LOW-2 - Limit error exposure
        logger.error(f"[Admin] Config delete failed: {e}")
        raise HTTPException(400, "Failed to delete config")


@router.get("/configs/audit")
@limiter.limit("30/minute")
async def get_config_audit(
    request: Request,
    config_key: Optional[str] = Query(None, max_length=200),
    # v3.25: SYS-MEDIUM-2 - Migrated to offset pagination
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return (1-100)"),
    admin: dict = Depends(require_admin)
):
    """Get config change history."""
    db_client = get_database_client()
    config_repo = SupabaseConfigRepository(db_client)

    logs = await config_repo.get_audit_logs(config_key=config_key, offset=offset, limit=limit)
    return {"logs": logs, "total": len(logs), "offset": offset, "limit": limit}


@router.post("/configs/cache/invalidate")
@limiter.limit("5/minute")
async def invalidate_cache(
    request: Request,
    key: Optional[str] = Query(None, max_length=200),
    admin: dict = Depends(require_admin)
):
    """Invalidate config cache."""
    try:
        db_client = get_database_client()
        config_repo = SupabaseConfigRepository(db_client)

        config_repo.invalidate_cache(key)
        return {"status": "invalidated", "key": key or "all"}
    except Exception as e:
        # v3.25: SYS-LOW-2 - Limit error exposure
        logger.error(f"[Admin] Cache invalidate failed: {e}")
        raise HTTPException(500, "Failed to invalidate cache")


# ==========================================
# Cache Management Routes (v3.25: Added rate limiting and validation)
# ==========================================

@router.get("/system/cache/status")
@limiter.limit("30/minute")
async def get_cache_status(request: Request, admin: dict = Depends(require_admin)):
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
        # v3.25: SYS-LOW-2 - Limit error exposure
        logger.error(f"[Admin] Cache status check failed: {e}")
        return {"status": "error", "error": "Failed to get cache status"}


@router.get("/system/cache/keys")
@limiter.limit("30/minute")
async def list_cache_keys(
    request: Request,
    # v3.25: SYS-MEDIUM-4 - Pattern validation
    pattern: str = Query("*", max_length=100),
    limit: int = Query(100, ge=1, le=1000, description="Max keys to return (1-1000)"),
    admin: dict = Depends(require_admin)
):
    """List cache keys matching pattern."""
    from core.cache import get_cache_provider

    # v3.25: SYS-MEDIUM-4 - Validate pattern to prevent injection
    if not CACHE_KEY_PATTERN.match(pattern):
        raise HTTPException(400, "Invalid pattern. Only alphanumeric, underscore, colon, asterisk, hyphen, and dot allowed")

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
        # v3.25: SYS-LOW-2 - Limit error exposure
        logger.error(f"[Admin] Cache keys list failed: {e}")
        return {"keys": [], "error": "Failed to list cache keys"}


@router.delete("/system/cache/key/{key:path}")
@limiter.limit("10/minute")
async def delete_cache_key(request: Request, key: str, admin: dict = Depends(require_admin)):
    """Delete a specific cache key."""
    from core.cache import get_cache_provider

    # v3.25: SYS-MEDIUM-4 - Validate key pattern
    if len(key) > 200:
        raise HTTPException(400, "Cache key too long (max 200 characters)")

    try:
        cache_provider = get_cache_provider()
        redis = getattr(cache_provider, '_client', None) if hasattr(cache_provider, '_client') else None
        if not redis:
            raise HTTPException(503, "Redis not connected")

        deleted = redis.delete(key)
        return {"status": "deleted" if deleted else "not_found", "key": key}
    except HTTPException:
        raise
    except Exception as e:
        # v3.25: SYS-LOW-2 - Limit error exposure
        logger.error(f"[Admin] Cache key delete failed: {e}")
        raise HTTPException(500, "Failed to delete cache key")


@router.post("/system/cache/clear-all")
@limiter.limit("2/minute")
async def clear_all_cache(request: Request, admin: dict = Depends(require_admin)):
    """Clear all cache (use with caution)."""
    from core.cache import get_cache_provider

    try:
        cache_provider = get_cache_provider()
        redis = getattr(cache_provider, '_client', None) if hasattr(cache_provider, '_client') else None
        if not redis:
            raise HTTPException(503, "Redis not connected")

        redis.flushdb()
        return {"status": "cleared"}
    except HTTPException:
        raise
    except Exception as e:
        # v3.25: SYS-LOW-2 - Limit error exposure
        logger.error(f"[Admin] Cache clear failed: {e}")
        raise HTTPException(500, "Failed to clear cache")
