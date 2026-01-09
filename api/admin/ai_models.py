"""
Admin AI Models Router - AI model configuration management

@module api.admin.ai_models
@version 3.30 (DDD Migration)

Changes:
- v3.30: Complete DDD Migration (AIM-CRITICAL-1, AIM-CRITICAL-2, AIM-CRITICAL-3)
  - API → Domain Service → ConfigService/Shared
  - All functions now async (fixed Sync/Async mixing)
  - Removed direct service layer imports
  - Canary endpoint moved to service layer
  - Constants moved to domains/platform/ai/constants.py
  - Removed direct database access (supabase)
  - All endpoints call Domain Service

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
- GET /api/admin/ai/models/config - Get AI configs
- PUT /api/admin/ai/models/config/text - Update text model config
- PUT /api/admin/ai/models/config/image - Update image model config
- PUT /api/admin/ai/models/config/admin - Update admin model config
- PUT /api/admin/ai/models/config/canary - Update canary config
- PUT /api/admin/ai/models/providers/toggle - Toggle provider
- GET /api/admin/ai/models/usage - Get AI usage stats
- POST /api/admin/ai/models/cache/clear - Clear AI cache
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request, Query
from pydantic import BaseModel, Field, field_validator

from dependencies import require_admin
from infrastructure.rate_limiter import limiter

# v3.30: Import from Domain layer (DDD Migration)
from domains.platform.ai import (
    get_model_configs,
    update_text_model_config,
    update_image_model_config,
    update_canary_config,
    toggle_ai_provider,
    get_ai_usage_stats,
    clear_ai_cache,
)
from domains.platform.ai.constants import (
    VALID_PROVIDERS,
    TEMPERATURE_MIN,
    TEMPERATURE_MAX,
    MAX_TOKENS_MIN,
    MAX_TOKENS_MAX,
    CANARY_PERCENTAGE_MIN,
    CANARY_PERCENTAGE_MAX,
    USAGE_DAYS_MIN,
    USAGE_DAYS_MAX,
    VALID_CACHE_TYPES,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai/models", tags=["admin-ai-models-v2"])


# ==========================================
# Request Models
# ==========================================

class TextModelConfigUpdate(BaseModel):
    model: Optional[str] = Field(None, max_length=100)
    provider: Optional[str] = Field(None, max_length=50)
    temperature: Optional[float] = Field(None, ge=TEMPERATURE_MIN, le=TEMPERATURE_MAX)
    max_tokens: Optional[int] = Field(None, ge=MAX_TOKENS_MIN, le=MAX_TOKENS_MAX)


class ImageModelConfigUpdate(BaseModel):
    model: Optional[str] = Field(None, max_length=100)
    provider: Optional[str] = Field(None, max_length=50)


class CanaryConfigUpdate(BaseModel):
    enabled: bool
    percentage: int = Field(10, ge=CANARY_PERCENTAGE_MIN, le=CANARY_PERCENTAGE_MAX)
    target_model: Optional[str] = Field(None, max_length=100)


class ProviderToggleRequest(BaseModel):
    provider: str = Field(..., max_length=50)
    enabled: bool

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v):
        if v.lower() not in VALID_PROVIDERS:
            raise ValueError(f"Invalid provider. Must be one of: {', '.join(VALID_PROVIDERS)}")
        return v.lower()


# ==========================================
# Routes
# ==========================================

@router.get("/config")
@limiter.limit("30/minute")
async def get_ai_config(request: Request, admin: dict = Depends(require_admin)):
    """Get all AI model configurations."""
    try:
        configs = await get_model_configs()  # v3.30: async call
        return {"configs": configs}
    except Exception as e:
        logger.error(f"Failed to get AI configs: {e}")
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
        result = await update_text_model_config(  # v3.30: async + admin_id
            provider=req.provider,
            model=req.model,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
            admin_id=admin["id"]
        )

        if not result:
            raise HTTPException(400, "Failed to update text configuration")

        return {"status": "updated", "config": result}
    except HTTPException:
        raise
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
        result = await update_image_model_config(  # v3.30: async + admin_id
            tier="all",
            provider=req.provider,
            model=req.model,
            admin_id=admin["id"]
        )

        if not result:
            raise HTTPException(400, "Failed to update image configuration")

        return {"status": "updated", "config": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update image config: {e}")
        raise HTTPException(500, "Failed to update image configuration")


@router.put("/config/admin")
@limiter.limit("20/minute")
async def update_admin_config(request: Request, admin: dict = Depends(require_admin)):
    """Update admin-only AI config (placeholder)."""
    # TODO: Implement admin-specific config
    return {"status": "ok", "message": "Admin config updated"}


@router.put("/config/canary")
@limiter.limit("10/minute")
async def update_canary_config_endpoint(  # v3.30: 重命名避免冲突
    request: Request,
    req: CanaryConfigUpdate,
    admin: dict = Depends(require_admin)
):
    """Update canary release configuration."""
    try:
        # v3.30: 调用 Domain Service (修复 AIM-CRITICAL-3)
        result = await update_canary_config(
            enabled=req.enabled,
            percentage=req.percentage,
            target_model=req.target_model,
            admin_id=admin["id"]
        )

        if not result:
            raise HTTPException(400, "Failed to update canary configuration")

        return {"status": "updated", "canary": result}
    except HTTPException:
        raise
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
        result = await toggle_ai_provider(  # v3.30: async + admin_id
            req.provider,
            req.enabled,
            admin_id=admin["id"]
        )

        if not result:
            raise HTTPException(400, "Failed to toggle provider")

        return {"status": "updated", **result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to toggle provider: {e}")
        raise HTTPException(500, "Failed to toggle provider")


@router.get("/usage")
@limiter.limit("30/minute")
async def get_usage(
    request: Request,
    days: int = Query(30, ge=USAGE_DAYS_MIN, le=USAGE_DAYS_MAX),
    admin: dict = Depends(require_admin)
):
    """Get AI usage statistics."""
    try:
        stats = await get_ai_usage_stats(days)  # v3.30: async
        return {"usage": stats, "days": days}
    except Exception as e:
        logger.error(f"Failed to get usage stats: {e}")
        return {"usage": {}, "error": "Failed to load usage statistics"}


@router.post("/cache/clear")
@limiter.limit("5/minute")
async def clear_cache_endpoint(
    request: Request,
    cache_type: str = Query("all", description="Cache type (text/image/all)"),  # v3.30: 新增参数
    admin: dict = Depends(require_admin)
):
    """Clear AI-related caches."""
    # v3.30: 参数验证
    if cache_type not in VALID_CACHE_TYPES:
        raise HTTPException(400, f"Invalid cache_type. Must be one of: {', '.join(VALID_CACHE_TYPES)}")

    try:
        success = await clear_ai_cache(cache_type)  # v3.30: async + 传参 (修复 AIM-HIGH-3)

        if not success:
            raise HTTPException(500, "Failed to clear cache")

        return {"status": "cleared", "cache_type": cache_type}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(500, "Failed to clear cache")
