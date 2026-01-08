"""
Admin Config Router - System configuration and rate limits for admins

@module api.admin.config
@version 3.25

Changes:
- v3.25: Security improvements
  - CFG-MEDIUM-1: Added rate limiting to all endpoints
  - CFG-MEDIUM-2: Added config_key length validation
  - CFG-MEDIUM-3: Added category parameter validation
  - CFG-MEDIUM-4: Added preset validation using field_validator
  - CFG-LOW-1: Added field length limits

Endpoints:
- GET /api/admin/config - Get all configs
- GET /api/admin/config/{config_key} - Get single config
- PUT /api/admin/config - Update single config
- PUT /api/admin/config/batch - Batch update configs
- GET /api/admin/rate-limits - Get current rate limits
- POST /api/admin/rate-limits/preset - Apply rate limit preset
- GET /api/admin/rate-limits/presets - Get available presets
- POST /api/admin/config/cache/clear - Clear config cache
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Request, Depends, Query
from pydantic import BaseModel, Field, field_validator

from domains.platform.config_service import (
    get_config, set_config, get_all_configs,
    batch_update_configs, apply_rate_limit_preset,
    clear_config_cache, RATE_LIMIT_PRESETS
)
from infrastructure.rate_limiter import limiter, get_current_limits
from infrastructure.repositories.admin_repository import SupabaseAdminUsersRepository
from core.database import get_database_client
from dependencies import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["admin-config-v2"])


# ==========================================
# Constants (v3.25)
# ==========================================

# v3.25: CFG-MEDIUM-3 - Valid config categories
VALID_CONFIG_CATEGORIES = {"rate_limit", "feature_flags", "system", "ai", "storage", "payment"}

# v3.25: CFG-MEDIUM-4 - Valid rate limit presets (imported from config_service)
VALID_RATE_LIMIT_PRESETS = set(RATE_LIMIT_PRESETS.keys())


# ==========================================
# Request Models (v3.25: Added field validations)
# ==========================================

class ConfigUpdateRequest(BaseModel):
    # v3.25: CFG-MEDIUM-2 - config_key length validation
    config_key: str = Field(..., min_length=1, max_length=200)
    config_value: dict


class BatchConfigUpdateRequest(BaseModel):
    updates: List[dict] = Field(..., max_length=100)


class RateLimitPresetRequest(BaseModel):
    preset: str = Field(..., max_length=50)

    # v3.25: CFG-MEDIUM-4 - Preset validation
    @field_validator("preset")
    @classmethod
    def validate_preset(cls, v):
        if v not in VALID_RATE_LIMIT_PRESETS:
            raise ValueError(f"Invalid preset. Must be one of: {', '.join(VALID_RATE_LIMIT_PRESETS)}")
        return v


# ==========================================
# Configuration Endpoints (v3.25: Added rate limiting)
# ==========================================

@router.get("/config")
@limiter.limit("30/minute")
async def adm_get_all_configs(
    request: Request,
    category: Optional[str] = Query(None, max_length=50, description="Config category filter"),
    admin: dict = Depends(require_admin)
):
    """Fetch system configs, optionally filtered by category."""
    # v3.25: CFG-MEDIUM-3 - Validate category parameter
    if category is not None and category not in VALID_CONFIG_CATEGORIES:
        raise HTTPException(400, f"Invalid category. Must be one of: {', '.join(VALID_CONFIG_CATEGORIES)}")

    configs = get_all_configs(category)
    return {"configs": configs}


@router.get("/config/{config_key:path}")
@limiter.limit("30/minute")
async def adm_get_config(
    request: Request,
    config_key: str,
    admin: dict = Depends(require_admin)
):
    """Fetch a single config key (bypass cache)."""
    # v3.25: CFG-MEDIUM-2 - Validate config_key length
    if len(config_key) > 200:
        raise HTTPException(400, "Config key too long (max 200 characters)")

    config = get_config(config_key, use_cache=False)
    if config is None:
        raise HTTPException(404, "Config not found")
    return {"config_key": config_key, "config_value": config}


@router.put("/config")
@limiter.limit("30/minute")
async def adm_update_config(
    request: Request,
    req: ConfigUpdateRequest,
    admin: dict = Depends(require_admin)
):
    """Update a single config entry."""
    success = set_config(req.config_key, req.config_value, admin["id"])
    if not success:
        raise HTTPException(500, "Failed to update config")

    admin_repo = SupabaseAdminUsersRepository(get_database_client())
    await admin_repo.admin_log_operation(
        admin_id=admin["id"],
        operation_type="config_update",
        target_user_id=None,
        details=f"Updated {req.config_key}",
        reason=None
    )

    return {"status": "ok", "config_key": req.config_key}


@router.put("/config/batch")
@limiter.limit("10/minute")
async def adm_batch_update_configs(
    request: Request,
    req: BatchConfigUpdateRequest,
    admin: dict = Depends(require_admin)
):
    """Batch update multiple config entries."""
    results = batch_update_configs(req.updates, admin["id"])

    admin_repo = SupabaseAdminUsersRepository(get_database_client())
    await admin_repo.admin_log_operation(
        admin_id=admin["id"],
        operation_type="config_batch_update",
        target_user_id=None,
        details=f"Updated {len(req.updates)} configs",
        reason=None
    )

    return {"status": "ok", "results": results}


@router.post("/config/cache/clear")
@limiter.limit("10/minute")
async def adm_clear_config_cache(
    request: Request,
    admin: dict = Depends(require_admin)
):
    """Clear config cache to apply new settings immediately."""
    clear_config_cache()
    return {"status": "ok", "message": "Config cache cleared"}


# ==========================================
# Rate Limit Endpoints
# ==========================================

@router.get("/rate-limits")
@limiter.limit("30/minute")
async def adm_get_rate_limits(
    request: Request,
    admin: dict = Depends(require_admin)
):
    """Fetch the current formatted rate-limit configuration."""
    return get_current_limits()


@router.post("/rate-limits/preset")
@limiter.limit("5/minute")
async def adm_apply_rate_limit_preset(
    request: Request,
    req: RateLimitPresetRequest,
    admin: dict = Depends(require_admin)
):
    """Apply a rate-limit preset ("strict" | "normal" | "relaxed" | "disabled")."""
    # Note: Validation is now done in RateLimitPresetRequest via field_validator
    try:
        success = apply_rate_limit_preset(req.preset, admin["id"])
        if not success:
            raise HTTPException(500, "Failed to apply preset")

        admin_repo = SupabaseAdminUsersRepository(get_database_client())
        await admin_repo.admin_log_operation(
            admin_id=admin["id"],
            operation_type="rate_limit_preset",
            target_user_id=None,
            details=f"Applied preset: {req.preset}",
            reason=None
        )

        return {
            "status": "ok",
            "preset": req.preset,
            "description": RATE_LIMIT_PRESETS[req.preset].get("description")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to apply rate limit preset: {e}")
        raise HTTPException(500, "Failed to apply preset")


@router.get("/rate-limits/presets")
@limiter.limit("30/minute")
async def adm_get_rate_limit_presets(
    request: Request,
    admin: dict = Depends(require_admin)
):
    """Fetch available rate-limit presets."""
    return {"presets": RATE_LIMIT_PRESETS}
