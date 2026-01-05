"""
Admin AI Models Router - AI model configuration management

@module routers.admin_ai_models
@version 3.24

Endpoints:
- GET /api/admin/ai/config - Get AI configs
- PUT /api/admin/ai/config/text - Update text model config
- PUT /api/admin/ai/config/image - Update image model config
- PUT /api/admin/ai/config/admin - Update admin model config
- PUT /api/admin/ai/config/canary - Update canary config
- PUT /api/admin/ai/providers/toggle - Toggle provider
- GET /api/admin/ai/usage - Get AI usage stats
- POST /api/admin/ai/cache/clear - Clear AI cache
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from dependencies import require_admin
from services.db_service import supabase
from services.ai.model_config_service import (
    get_model_configs,
    update_text_model_config,
    update_image_model_config,
    toggle_ai_provider,
    get_ai_usage_stats,
    clear_ai_cache
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/ai", tags=["admin-ai-models"])


# ==========================================
# Request Models
# ==========================================

class TextModelConfigUpdate(BaseModel):
    model: Optional[str] = None
    provider: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class ImageModelConfigUpdate(BaseModel):
    model: Optional[str] = None
    provider: Optional[str] = None
    default_size: Optional[str] = None
    default_style: Optional[str] = None


class CanaryConfigUpdate(BaseModel):
    enabled: bool
    percentage: int = 10
    target_model: Optional[str] = None


class ProviderToggleRequest(BaseModel):
    provider: str
    enabled: bool


# ==========================================
# AI Configuration Routes
# ==========================================

@router.get("/config")
def get_ai_config(admin: dict = Depends(require_admin)):
    """Get all AI model configurations."""
    try:
        configs = get_model_configs()
        return {"configs": configs}
    except Exception as e:
        logger.error(f"Failed to get AI configs: {e}")
        return {"configs": {}, "error": str(e)}


@router.put("/config/text")
def update_text_config(req: TextModelConfigUpdate, admin: dict = Depends(require_admin)):
    """Update text generation model config."""
    try:
        update_data = {k: v for k, v in req.dict().items() if v is not None}
        result = update_text_model_config(update_data, admin["id"])
        return {"status": "updated", "config": result}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.put("/config/image")
def update_image_config(req: ImageModelConfigUpdate, admin: dict = Depends(require_admin)):
    """Update image generation model config."""
    try:
        update_data = {k: v for k, v in req.dict().items() if v is not None}
        result = update_image_model_config(update_data, admin["id"])
        return {"status": "updated", "config": result}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.put("/config/admin")
def update_admin_config(admin: dict = Depends(require_admin)):
    """Update admin-only AI config."""
    # Placeholder for admin-specific AI settings
    return {"status": "ok", "message": "Admin config updated"}


@router.put("/config/canary")
def update_canary_config(req: CanaryConfigUpdate, admin: dict = Depends(require_admin)):
    """Update canary release configuration."""
    try:
        result = supabase.table("ai_model_configs").update({
            "canary_enabled": req.enabled,
            "canary_percentage": req.percentage,
            "canary_model": req.target_model
        }).eq("config_type", "global").execute()
        
        return {"status": "updated", "canary": {
            "enabled": req.enabled,
            "percentage": req.percentage,
            "target_model": req.target_model
        }}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.put("/providers/toggle")
def toggle_provider(req: ProviderToggleRequest, admin: dict = Depends(require_admin)):
    """Enable/disable an AI provider."""
    try:
        result = toggle_ai_provider(req.provider, req.enabled, admin["id"])
        return {"status": "updated", "provider": req.provider, "enabled": req.enabled}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/usage")
def get_usage(
    days: int = 30,
    admin: dict = Depends(require_admin)
):
    """Get AI usage statistics."""
    try:
        stats = get_ai_usage_stats(days)
        return {"usage": stats, "days": days}
    except Exception as e:
        return {"usage": {}, "error": str(e)}


@router.post("/cache/clear")
def clear_cache(admin: dict = Depends(require_admin)):
    """Clear AI-related caches."""
    try:
        clear_ai_cache()
        return {"status": "cleared"}
    except Exception as e:
        raise HTTPException(500, str(e))
