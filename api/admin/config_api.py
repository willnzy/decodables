"""
Admin Config API - System configuration management for admins.

@module api.admin.config_api
@version 1.0.0

Endpoints:
- GET /config - Get all configs
- GET /config/{key} - Get single config
- PUT /config - Update single config
- PUT /config/batch - Batch update configs
- GET /config/rate-limits - Get current rate limits
- POST /config/rate-limits/preset - Apply rate limit preset
- GET /config/rate-limits/presets - Get available presets
- POST /config/cache/clear - Clear config cache
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from dependencies import require_admin
from services.config_service import (
    get_config, set_config, get_all_configs,
    batch_update_configs, apply_rate_limit_preset,
    clear_config_cache, RATE_LIMIT_PRESETS,
)
from services.rate_limiter import limiter, get_current_limits
from services.db_service import admin_log_operation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["admin-config-v2"])


# ==========================================
# Request Models
# ==========================================

class ConfigUpdateRequest(BaseModel):
    """Config update request."""
    config_key: str
    config_value: dict


class BatchConfigUpdateRequest(BaseModel):
    """Batch config update request."""
    updates: List[dict]


class RateLimitPresetRequest(BaseModel):
    """Rate limit preset request."""
    preset_name: str


# ==========================================
# Config Endpoints
# ==========================================

@router.get("")
async def get_all_configs_api(
    admin: dict = Depends(require_admin),
):
    """Get all configurations."""
    return get_all_configs()


@router.get("/{config_key}")
async def get_config_api(
    config_key: str,
    admin: dict = Depends(require_admin),
):
    """Get a single configuration."""
    value = get_config(config_key)
    if value is None:
        raise HTTPException(404, f"Config not found: {config_key}")
    return {"key": config_key, "value": value}


@router.put("")
async def update_config(
    req: ConfigUpdateRequest,
    admin: dict = Depends(require_admin),
):
    """Update a single configuration."""
    set_config(req.config_key, req.config_value)
    admin_log_operation(
        admin_id=admin["id"],
        operation_type="config_update",
        target_user_id=None,
        details=f"Updated config: {req.config_key}",
        reason=None,
    )
    return {"status": "ok", "key": req.config_key}


@router.put("/batch")
async def batch_update_configs_api(
    req: BatchConfigUpdateRequest,
    admin: dict = Depends(require_admin),
):
    """Batch update configurations."""
    batch_update_configs(req.updates)
    admin_log_operation(
        admin_id=admin["id"],
        operation_type="config_batch_update",
        target_user_id=None,
        details=f"Batch updated {len(req.updates)} configs",
        reason=None,
    )
    return {"status": "ok", "count": len(req.updates)}


# ==========================================
# Rate Limit Endpoints
# ==========================================

@router.get("/rate-limits")
async def get_rate_limits(
    admin: dict = Depends(require_admin),
):
    """Get current rate limits."""
    return get_current_limits()


@router.get("/rate-limits/presets")
async def get_rate_limit_presets(
    admin: dict = Depends(require_admin),
):
    """Get available rate limit presets."""
    return {"presets": list(RATE_LIMIT_PRESETS.keys()), "details": RATE_LIMIT_PRESETS}


@router.post("/rate-limits/preset")
@limiter.limit("5/minute")
async def apply_rate_limit_preset_api(
    request: Request,
    req: RateLimitPresetRequest,
    admin: dict = Depends(require_admin),
):
    """Apply a rate limit preset."""
    if req.preset_name not in RATE_LIMIT_PRESETS:
        raise HTTPException(400, f"Invalid preset: {req.preset_name}")

    apply_rate_limit_preset(req.preset_name)
    admin_log_operation(
        admin_id=admin["id"],
        operation_type="rate_limit_preset",
        target_user_id=None,
        details=f"Applied rate limit preset: {req.preset_name}",
        reason=None,
    )
    return {"status": "ok", "preset": req.preset_name}


@router.post("/cache/clear")
async def clear_config_cache_api(
    admin: dict = Depends(require_admin),
):
    """Clear the config cache."""
    clear_config_cache()
    admin_log_operation(
        admin_id=admin["id"],
        operation_type="cache_clear",
        target_user_id=None,
        details="Cleared config cache",
        reason=None,
    )
    return {"status": "ok", "message": "Config cache cleared"}
