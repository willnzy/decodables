"""
Admin Config Router - System configuration and rate limits for admins

@module api.admin.config
@version 3.24

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

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel

from domains.platform.config_service import (
    get_config, set_config, get_all_configs,
    batch_update_configs, apply_rate_limit_preset,
    clear_config_cache, RATE_LIMIT_PRESETS
)
from infrastructure.rate_limiter import limiter, get_current_limits
from services.db_service import admin_log_operation
from dependencies import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["admin-config-v2"])


# ==========================================
# Request Models
# ==========================================

class ConfigUpdateRequest(BaseModel):
    config_key: str
    config_value: dict


class BatchConfigUpdateRequest(BaseModel):
    updates: List[dict]


class RateLimitPresetRequest(BaseModel):
    preset: str  # "strict", "normal", "relaxed", "disabled"


# ==========================================
# Configuration Endpoints
# ==========================================

@router.get("/config")
def adm_get_all_configs(
    category: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    """Fetch system configs, optionally filtered by category."""
    configs = get_all_configs(category)
    return {"configs": configs}


@router.get("/config/{config_key:path}")
def adm_get_config(
    config_key: str,
    admin: dict = Depends(require_admin)
):
    """Fetch a single config key (bypass cache)."""
    config = get_config(config_key, use_cache=False)
    if config is None:
        raise HTTPException(404, f"Config not found: {config_key}")
    return {"config_key": config_key, "config_value": config}


@router.put("/config")
@limiter.limit("30/minute")
def adm_update_config(
    request: Request,
    req: ConfigUpdateRequest,
    admin: dict = Depends(require_admin)
):
    """Update a single config entry."""
    success = set_config(req.config_key, req.config_value, admin["id"])
    if not success:
        raise HTTPException(500, "Failed to update config")
    
    admin_log_operation(
        admin_id=admin["id"],
        operation_type="config_update",
        target_user_id=None,
        details=f"Updated {req.config_key}",
        reason=None
    )
    
    return {"status": "ok", "config_key": req.config_key}


@router.put("/config/batch")
@limiter.limit("10/minute")
def adm_batch_update_configs(
    request: Request,
    req: BatchConfigUpdateRequest,
    admin: dict = Depends(require_admin)
):
    """Batch update multiple config entries."""
    results = batch_update_configs(req.updates, admin["id"])
    
    admin_log_operation(
        admin_id=admin["id"],
        operation_type="config_batch_update",
        target_user_id=None,
        details=f"Updated {len(req.updates)} configs",
        reason=None
    )
    
    return {"status": "ok", "results": results}


@router.post("/config/cache/clear")
@limiter.limit("10/minute")
def adm_clear_config_cache(
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
def adm_get_rate_limits(admin: dict = Depends(require_admin)):
    """Fetch the current formatted rate-limit configuration."""
    return get_current_limits()


@router.post("/rate-limits/preset")
@limiter.limit("5/minute")
def adm_apply_rate_limit_preset(
    request: Request,
    req: RateLimitPresetRequest,
    admin: dict = Depends(require_admin)
):
    """Apply a rate-limit preset ("strict" | "normal" | "relaxed" | "disabled")."""
    if req.preset not in RATE_LIMIT_PRESETS:
        raise HTTPException(400, f"Invalid preset. Available: {list(RATE_LIMIT_PRESETS.keys())}")
    
    success = apply_rate_limit_preset(req.preset, admin["id"])
    if not success:
        raise HTTPException(500, "Failed to apply preset")
    
    admin_log_operation(
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


@router.get("/rate-limits/presets")
def adm_get_rate_limit_presets(admin: dict = Depends(require_admin)):
    """Fetch available rate-limit presets."""
    return {"presets": RATE_LIMIT_PRESETS}
