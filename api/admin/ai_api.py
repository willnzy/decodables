"""
Admin AI API - AI insights and report generation for admins.

@module api.admin.ai_api
@version 2.0.0

Endpoints:
- GET /ai/insights - Get AI insights
- GET /ai/recommendations - Get AI recommendations
- GET /ai/behavior-analysis - Get behavior analysis
- POST /ai/generate-report - Generate AI report
- GET /ai/quick-insights - Get quick insights
- GET /ai/config - Get AI model configurations
- PUT /ai/config/text - Update text model config
- PUT /ai/config/image - Update image model config
- PUT /ai/config/canary - Update canary config
- PUT /ai/providers/toggle - Toggle AI provider
- GET /ai/usage - Get AI usage stats
- POST /ai/cache/clear - Clear AI cache
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from dependencies import require_admin
from services.db_service import (
    admin_get_ai_insights,
    admin_get_ai_recommendations,
    admin_get_behavior_analysis,
    supabase,
)
from services.ai.model_config_service import (
    get_model_configs,
    update_text_model_config,
    update_image_model_config,
    toggle_ai_provider,
    get_ai_usage_stats,
    clear_ai_cache,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["admin-ai"])


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


class ProviderUpdateRequest(BaseModel):
    enabled: bool


# ==========================================
# AI Insights Endpoints
# ==========================================

@router.get("/insights")
def get_ai_insights(
    type: str = "all",
    admin: dict = Depends(require_admin)
):
    """Fetch AI insights."""
    return admin_get_ai_insights(type)


@router.get("/recommendations")
def get_ai_recommendations(
    area: str = "all",
    admin: dict = Depends(require_admin)
):
    """Fetch AI optimization recommendations."""
    return admin_get_ai_recommendations(area)


@router.get("/behavior-analysis")
def get_behavior_analysis(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    """Fetch AI-powered user behavior analysis."""
    return admin_get_behavior_analysis(start_date, end_date)


@router.post("/generate-report")
async def generate_ai_report(
    report_type: str = "comprehensive",
    time_range: str = "30d",
    admin: dict = Depends(require_admin)
):
    """Generate a comprehensive AI-powered business intelligence report."""
    from services.ai_report_service import generate_ai_business_report

    try:
        report = generate_ai_business_report(
            report_type=report_type,
            time_range=time_range
        )
        return report
    except Exception as e:
        logger.error(f"Error generating AI report: {e}")
        raise HTTPException(500, detail=f"Failed to generate AI report: {str(e)}")


@router.get("/quick-insights")
def get_quick_insights(admin: dict = Depends(require_admin)):
    """Get quick rule-based insights for dashboard preview."""
    from services.ai_report_service import get_quick_insights

    try:
        insights = get_quick_insights()
        return {"insights": insights}
    except Exception as e:
        logger.error(f"Error getting quick insights: {e}")
        return {"insights": [], "error": str(e)}


# ==========================================
# AI Model Configuration Endpoints
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
def update_text_config(
    req: TextModelConfigUpdate,
    admin: dict = Depends(require_admin)
):
    """Update text generation model config."""
    try:
        update_data = {k: v for k, v in req.model_dump().items() if v is not None}
        result = update_text_model_config(update_data, admin["id"])
        return {"status": "updated", "config": result}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.put("/config/image")
def update_image_config(
    req: ImageModelConfigUpdate,
    admin: dict = Depends(require_admin)
):
    """Update image generation model config."""
    try:
        update_data = {k: v for k, v in req.model_dump().items() if v is not None}
        result = update_image_model_config(update_data, admin["id"])
        return {"status": "updated", "config": result}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.put("/config/canary")
def update_canary_config(
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
        raise HTTPException(500, str(e))


@router.patch("/providers/{provider}")
def update_provider(
    provider: str,
    req: ProviderUpdateRequest,
    admin: dict = Depends(require_admin)
):
    """
    Update AI provider settings (enable/disable).

    **Recommended**: Use PATCH for partial resource updates.
    """
    enabled = req.enabled
    try:
        result = toggle_ai_provider(provider, enabled, admin["id"])
        return {"status": "updated", "provider": provider, "enabled": enabled}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.put("/providers/toggle", deprecated=True)
def toggle_provider(
    req: ProviderToggleRequest,
    admin: dict = Depends(require_admin)
):
    """
    Enable/disable an AI provider.

    **DEPRECATED**: Use `PATCH /providers/{provider}` instead.
    This endpoint will be removed in v3.0.
    """
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
