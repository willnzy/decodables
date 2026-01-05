"""
Admin AI Router - AI insights and report generation for admins

@module routers.admin_ai
@version 3.24

Endpoints:
- GET /api/admin/ai/insights - Get AI insights
- GET /api/admin/ai/recommendations - Get AI recommendations
- GET /api/admin/ai/behavior-analysis - Get behavior analysis
- POST /api/admin/ai/generate-report - Generate AI report
- GET /api/admin/ai/quick-insights - Get quick insights
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Depends

from services.db_service import (
    admin_get_ai_insights,
    admin_get_ai_recommendations,
    admin_get_behavior_analysis,
)
from services.rate_limiter import limiter
from dependencies import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/ai", tags=["admin-ai"])


# ==========================================
# AI Insights Endpoints
# ==========================================

@router.get("/insights")
def adm_get_ai_insights(
    type: str = "all",
    admin: dict = Depends(require_admin)
):
    """Fetch AI insights."""
    return admin_get_ai_insights(type)


@router.get("/recommendations")
def adm_get_ai_recommendations(
    area: str = "all",
    admin: dict = Depends(require_admin)
):
    """Fetch AI optimization recommendations."""
    return admin_get_ai_recommendations(area)


@router.get("/behavior-analysis")
def adm_get_behavior_analysis(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    """Fetch AI-powered user behavior analysis."""
    return admin_get_behavior_analysis(start_date, end_date)


@router.post("/generate-report")
@limiter.limit("5/minute")
async def adm_generate_ai_report(
    request: Request,
    report_type: str = "comprehensive",
    time_range: str = "30d",
    admin: dict = Depends(require_admin)
):
    """
    Generate a comprehensive AI-powered business intelligence report.
    """
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
def adm_get_quick_insights(
    admin: dict = Depends(require_admin)
):
    """
    Get quick rule-based insights for dashboard preview.
    """
    from services.ai_report_service import get_quick_insights
    
    try:
        insights = get_quick_insights()
        return {"insights": insights}
    except Exception as e:
        logger.error(f"Error getting quick insights: {e}")
        return {"insights": [], "error": str(e)}
