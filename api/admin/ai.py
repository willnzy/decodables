"""
Admin AI Router - AI insights and report generation for admins

@module api.admin.ai
@version 3.26

Changes:
- v3.25: Security improvements
  - AI-BROKEN-1: Implemented 3 missing Repository methods
  - AI-MEDIUM-1: Added rate limiting to all endpoints
  - AI-MEDIUM-2: Added `type` parameter validation (enum)
  - AI-MEDIUM-3: Added `area` parameter validation (enum)
  - AI-MEDIUM-4: Added date format validation for start_date/end_date
  - AI-MEDIUM-5: Added `report_type` parameter validation (enum)
  - AI-MEDIUM-6: Added `time_range` parameter validation (enum)
  - AI-LOW-1: Limited error detail exposure in generate-report
- v3.26: Critical bug fixes (Deep Review)
  - AI-CRITICAL-1: Fixed generate_report parameter mismatch
  - AI-HIGH-1: Added error handling to insights/recommendations/behavior-analysis
  - AI-MEDIUM-9: Added OpenAI API timeout (30s)
  - Performance: Limited behavior_analysis data to 50K records

Endpoints:
- GET /api/admin/ai/insights - Get AI insights
- GET /api/admin/ai/recommendations - Get AI recommendations
- GET /api/admin/ai/behavior-analysis - Get behavior analysis
- POST /api/admin/ai/generate-report - Generate AI report
- GET /api/admin/ai/quick-insights - Get quick insights
"""

import logging
import re
from typing import Optional
from enum import Enum

from fastapi import APIRouter, HTTPException, Request, Depends, Query

from core.database import get_database_client
from infrastructure.repositories import SupabaseAdminStatsRepository
from infrastructure.rate_limiter import limiter
from dependencies import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["admin-ai-v2"])


# ==========================================
# Constants (v3.25)
# ==========================================

# v3.25: AI-MEDIUM-4 - Date format validation pattern
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2})?")

# v3.25: AI-MEDIUM-2 - Valid insight types
VALID_INSIGHT_TYPES = {"all", "growth", "engagement", "revenue"}

# v3.25: AI-MEDIUM-3 - Valid recommendation areas
VALID_RECOMMENDATION_AREAS = {"all", "growth", "retention", "monetization"}

# v3.25: AI-MEDIUM-5 - Valid report types
VALID_REPORT_TYPES = {"comprehensive", "growth", "engagement", "revenue", "quick"}

# v3.25: AI-MEDIUM-6 - Valid time ranges
VALID_TIME_RANGES = {"7d", "30d", "90d", "365d"}


def validate_date_format(date_str: Optional[str], field_name: str) -> None:
    """v3.25: AI-MEDIUM-4 - Validate date format (YYYY-MM-DD or ISO)."""
    if date_str is not None and not DATE_PATTERN.match(date_str):
        raise HTTPException(400, f"Invalid {field_name} format. Use YYYY-MM-DD or ISO format")


# ==========================================
# AI Insights Endpoints
# ==========================================

@router.get("/insights")
@limiter.limit("30/minute")
async def adm_get_ai_insights(
    request: Request,
    type: str = Query("all", description="Insight type: all, growth, engagement, revenue"),
    admin: dict = Depends(require_admin)
):
    """Fetch AI insights."""
    # v3.25: AI-MEDIUM-2 - Validate type parameter
    if type not in VALID_INSIGHT_TYPES:
        raise HTTPException(400, f"Invalid type. Must be one of: {', '.join(VALID_INSIGHT_TYPES)}")

    try:
        db_client = get_database_client()
        stats_repo = SupabaseAdminStatsRepository(db_client)
        return await stats_repo.admin_get_ai_insights(type)
    except Exception as e:
        logger.error(f"Error fetching AI insights: {e}")
        raise HTTPException(500, "Failed to fetch AI insights")


@router.get("/recommendations")
@limiter.limit("30/minute")
async def adm_get_ai_recommendations(
    request: Request,
    area: str = Query("all", description="Area: all, growth, retention, monetization"),
    admin: dict = Depends(require_admin)
):
    """Fetch AI optimization recommendations."""
    # v3.25: AI-MEDIUM-3 - Validate area parameter
    if area not in VALID_RECOMMENDATION_AREAS:
        raise HTTPException(400, f"Invalid area. Must be one of: {', '.join(VALID_RECOMMENDATION_AREAS)}")

    try:
        db_client = get_database_client()
        stats_repo = SupabaseAdminStatsRepository(db_client)
        return await stats_repo.admin_get_ai_recommendations(area)
    except Exception as e:
        logger.error(f"Error fetching AI recommendations: {e}")
        raise HTTPException(500, "Failed to fetch AI recommendations")


@router.get("/behavior-analysis")
@limiter.limit("20/minute")
async def adm_get_behavior_analysis(
    request: Request,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD or ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD or ISO format)"),
    admin: dict = Depends(require_admin)
):
    """Fetch AI-powered user behavior analysis."""
    # v3.25: AI-MEDIUM-4 - Validate date formats
    validate_date_format(start_date, "start_date")
    validate_date_format(end_date, "end_date")

    try:
        db_client = get_database_client()
        stats_repo = SupabaseAdminStatsRepository(db_client)
        return await stats_repo.admin_get_behavior_analysis(start_date, end_date)
    except Exception as e:
        logger.error(f"Error fetching behavior analysis: {e}")
        raise HTTPException(500, "Failed to fetch behavior analysis")


@router.post("/generate-report")
@limiter.limit("5/minute")
async def adm_generate_ai_report(
    request: Request,
    report_type: str = Query("comprehensive", description="Report type: comprehensive, growth, engagement, revenue, quick"),
    time_range: str = Query("30d", description="Time range: 7d, 30d, 90d, 365d"),
    admin: dict = Depends(require_admin)
):
    """
    Generate a comprehensive AI-powered business intelligence report.
    """
    # v3.25: AI-MEDIUM-5 - Validate report_type parameter
    if report_type not in VALID_REPORT_TYPES:
        raise HTTPException(400, f"Invalid report_type. Must be one of: {', '.join(VALID_REPORT_TYPES)}")

    # v3.25: AI-MEDIUM-6 - Validate time_range parameter
    if time_range not in VALID_TIME_RANGES:
        raise HTTPException(400, f"Invalid time_range. Must be one of: {', '.join(VALID_TIME_RANGES)}")

    from application.services.ai_report_service import generate_ai_business_report

    try:
        report = generate_ai_business_report(
            report_type=report_type,
            time_range=time_range
        )
        return report
    except Exception as e:
        logger.error(f"Error generating AI report: {e}")
        # v3.25: AI-LOW-1 - Limited error detail exposure
        raise HTTPException(500, detail="Failed to generate AI report")


@router.get("/quick-insights")
@limiter.limit("60/minute")
async def adm_get_quick_insights(
    request: Request,
    admin: dict = Depends(require_admin)
):
    """
    Get quick rule-based insights for dashboard preview.
    """
    from application.services.ai_report_service import get_quick_insights

    try:
        insights = get_quick_insights()
        return {"insights": insights}
    except Exception as e:
        logger.error(f"Error getting quick insights: {e}")
        # v3.25: Don't expose error details
        return {"insights": [], "error": "Failed to get insights"}
