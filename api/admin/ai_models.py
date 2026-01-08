"""
Admin AI Models Router - AI model configuration management

@module api.admin.ai_models
@version 3.25

Changes:
- v3.25: Security improvements
  - AIM-MEDIUM-1: Added rate limiting to all endpoints
  - AIM-MEDIUM-2: Added temperature range validation (0-2)
  - AIM-MEDIUM-3: Added max_tokens range validation (1-32000)
  - AIM-MEDIUM-4: Added canary percentage range validation (0-100)
  - AIM-MEDIUM-5: Added provider enum validation
  - AIM-MEDIUM-6: Added days parameter range validation (1-365)
  - AIM-LOW-1: Limited error detail exposure
  - AIM-LOW-2/3: Fixed service function call signatures

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

from fastapi import APIRouter, HTTPException, Depends, Request, Query
from pydantic import BaseModel, Field, field_validator

from dependencies import require_admin
from core.database import get_supabase_client
from infrastructure.rate_limiter import limiter
from shared.ai.model_config_service import (
    get_model_configs,
    update_text_model_config,
    update_image_model_config,
    toggle_ai_provider,
    get_ai_usage_stats,
    clear_ai_cache
)

supabase = get_supabase_client()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/models", tags=["admin-ai-models-v2"])


# ==========================================
# Constants (v3.25)
# ==========================================

# v3.25: AIM-MEDIUM-5 - Valid AI providers
VALID_PROVIDERS = {"openai", "fal", "dashscope", "anthropic", "replicate"}


# ==========================================
# Request Models (v3.25: Added field validations)
# ==========================================

class TextModelConfigUpdate(BaseModel):
    model: Optional[str] = Field(None, max_length=100)
    provider: Optional[str] = Field(None, max_length=50)
    # v3.25: AIM-MEDIUM-2 - Temperature range 0-2
    temperature: Optional[float] = Field(None, ge=0, le=2)
    # v3.25: AIM-MEDIUM-3 - Max tokens range 1-32000
    max_tokens: Optional[int] = Field(None, ge=1, le=32000)


class ImageModelConfigUpdate(BaseModel):
    model: Optional[str] = Field(None, max_length=100)
    provider: Optional[str] = Field(None, max_length=50)
    default_size: Optional[str] = Field(None, max_length=20)
    default_style: Optional[str] = Field(None, max_length=50)


class CanaryConfigUpdate(BaseModel):
    enabled: bool
    # v3.25: AIM-MEDIUM-4 - Percentage range 0-100
    percentage: int = Field(10, ge=0, le=100)
    target_model: Optional[str] = Field(None, max_length=100)


class ProviderToggleRequest(BaseModel):
    provider: str = Field(..., max_length=50)
    enabled: bool

    # v3.25: AIM-MEDIUM-5 - Provider validation
    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v):
        if v.lower() not in VALID_PROVIDERS:
            raise ValueError(f"Invalid provider. Must be one of: {', '.join(VALID_PROVIDERS)}")
        return v.lower()


# ==========================================
# AI Configuration Routes (v3.25: Added rate limiting)
# ==========================================

@router.get("/config")
@limiter.limit("30/minute")
async def get_ai_config(request: Request, admin: dict = Depends(require_admin)):
    """Get all AI model configurations."""
    try:
        configs = get_model_configs()
        return {"configs": configs}
    except Exception as e:
        logger.error(f"Failed to get AI configs: {e}")
        # v3.25: AIM-LOW-1 - Limited error exposure
        return {"configs": {}, "error": "Failed to load configurations"}


@router.put("/config/text")
@limiter.limit("20/minute")
async def update_text_config(
    request: Request,
    req: TextModelConfigUpdate,
    admin: dict = Depends(require_admin)
):
    """Update text generation model config."""
    try:
        # v3.25: AIM-LOW-2 - Call with proper kwargs
        result = update_text_model_config(
            provider=req.provider,
            model=req.model,
            max_tokens=req.max_tokens,
            temperature=req.temperature
        )
        return {"status": "updated", "config": result}
    except Exception as e:
        logger.error(f"Failed to update text config: {e}")
        raise HTTPException(500, "Failed to update text configuration")


@router.put("/config/image")
@limiter.limit("20/minute")
async def update_image_config(
    request: Request,
    req: ImageModelConfigUpdate,
    admin: dict = Depends(require_admin)
):
    """Update image generation model config."""
    try:
        # v3.25: AIM-LOW-3 - Call with proper kwargs (tier defaults to "all")
        result = update_image_model_config(
            tier="all",
            provider=req.provider,
            model=req.model
        )
        return {"status": "updated", "config": result}
    except Exception as e:
        logger.error(f"Failed to update image config: {e}")
        raise HTTPException(500, "Failed to update image configuration")


@router.put("/config/admin")
@limiter.limit("20/minute")
async def update_admin_config(request: Request, admin: dict = Depends(require_admin)):
    """Update admin-only AI config."""
    # Placeholder for admin-specific AI settings
    return {"status": "ok", "message": "Admin config updated"}


@router.put("/config/canary")
@limiter.limit("10/minute")
async def update_canary_config(
    request: Request,
    req: CanaryConfigUpdate,
    admin: dict = Depends(require_admin)
):
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
        logger.error(f"Failed to update canary config: {e}")
        raise HTTPException(500, "Failed to update canary configuration")


@router.put("/providers/toggle")
@limiter.limit("10/minute")
async def toggle_provider_endpoint(
    request: Request,
    req: ProviderToggleRequest,
    admin: dict = Depends(require_admin)
):
    """Enable/disable an AI provider."""
    try:
        result = toggle_ai_provider(req.provider, req.enabled)
        return {"status": "updated", "provider": req.provider, "enabled": req.enabled}
    except Exception as e:
        logger.error(f"Failed to toggle provider: {e}")
        raise HTTPException(500, "Failed to toggle provider")


@router.get("/usage")
@limiter.limit("30/minute")
async def get_usage(
    request: Request,
    # v3.25: AIM-MEDIUM-6 - Days range validation
    days: int = Query(30, ge=1, le=365, description="Number of days (1-365)"),
    admin: dict = Depends(require_admin)
):
    """Get AI usage statistics."""
    try:
        stats = get_ai_usage_stats(days)
        return {"usage": stats, "days": days}
    except Exception as e:
        logger.error(f"Failed to get usage stats: {e}")
        return {"usage": {}, "error": "Failed to load usage statistics"}


@router.post("/cache/clear")
@limiter.limit("5/minute")
async def clear_cache_endpoint(request: Request, admin: dict = Depends(require_admin)):
    """Clear AI-related caches."""
    try:
        clear_ai_cache()
        return {"status": "cleared"}
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(500, "Failed to clear cache")
