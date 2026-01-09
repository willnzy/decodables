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
    """
    Fetch AI-generated insights for platform metrics.

    Returns insights about user growth, engagement, and revenue based on the specified type.
    Insights are generated from the last 7 days of data.

    Args:
        type: Filter insights by category
            - `all`: All insight types
            - `growth`: User acquisition and growth metrics
            - `engagement`: User engagement and activity metrics
            - `revenue`: Revenue and monetization metrics

    Returns:
        List[Dict]: Array of insight objects, each containing:
            - category: Insight category (growth/engagement/revenue)
            - title: Short title
            - description: Detailed description
            - metric_value: Numerical value
            - trend: Trend indicator (up/down/stable)

    Raises:
        400: Invalid type parameter
        401: Unauthorized - admin access required
        500: Server error fetching insights
    """
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
    """
    Fetch AI-generated optimization recommendations.

    Analyzes platform metrics and generates actionable recommendations for improvement
    in specific business areas.

    Args:
        area: Focus area for recommendations
            - `all`: All recommendation areas
            - `growth`: User acquisition and signup optimization
            - `retention`: User engagement and retention strategies
            - `monetization`: Revenue optimization and conversion

    Returns:
        List[Dict]: Array of recommendation objects, each containing:
            - priority: Urgency level (high/medium/low)
            - area: Recommendation area
            - title: Short recommendation title
            - description: Detailed analysis
            - action: Suggested action to take

    Raises:
        400: Invalid area parameter
        401: Unauthorized - admin access required
        500: Server error fetching recommendations
    """
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
    """
    Fetch AI-powered user behavior analysis.

    Analyzes user activity patterns, peak hours, and user segments over a specified date range.
    Limited to 50,000 events to prevent performance issues.

    Args:
        start_date: Analysis period start (defaults to 30 days ago)
            - Format: YYYY-MM-DD or ISO 8601
            - Example: "2024-01-01" or "2024-01-01T00:00:00"
        end_date: Analysis period end (defaults to today)
            - Format: YYYY-MM-DD or ISO 8601
            - Example: "2024-01-31" or "2024-01-31T23:59:59"

    Returns:
        Dict: Behavior analysis report containing:
            - patterns: Event distribution, peak hours, hourly activity
                - event_distribution: Count by event type
                - peak_activity_hour: Hour with most activity (0-23)
                - hourly_activity: Activity count for each hour
                - total_events_analyzed: Number of events processed
                - limited: Boolean indicating if data was truncated
            - segments: User segmentation data
                - by_tier: Count of users by tier (free/starter/pro)
                - total_users: Total user count
            - period: Analysis period (start/end dates)

    Raises:
        400: Invalid date format
        401: Unauthorized - admin access required
        500: Server error during analysis
    """
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

    Uses OpenAI GPT-4o to analyze platform metrics and generate detailed business insights,
    recommendations, and anomaly detection. Rate limited to 5 requests per minute.

    Args:
        report_type: Type of report to generate
            - `comprehensive`: Full analysis (deep analysis depth)
            - `growth`: Focus on user acquisition metrics
            - `engagement`: Focus on user activity metrics
            - `revenue`: Focus on monetization metrics
            - `quick`: Lightweight rule-based insights (no AI)
        time_range: Analysis time window
            - `7d`: Last 7 days
            - `30d`: Last 30 days (default)
            - `90d`: Last 90 days
            - `365d`: Last year

    Returns:
        Dict: AI-generated report containing:
            - executive_summary: High-level business overview
            - key_insights: Array of detailed insights with priority
            - anomalies: List of detected metric anomalies
            - recommendations: Top prioritized action items
            - metrics_analyzed: Count of metrics processed
            - report_type: Report type used
            - time_range: Time range analyzed
            - generated_at: ISO timestamp

        On OpenAI API failure, returns fallback with quick insights.

    Raises:
        400: Invalid report_type or time_range
        401: Unauthorized - admin access required
        500: Report generation failed

    Notes:
        - OpenAI API timeout: 30 seconds
        - Falls back to rule-based insights if AI unavailable
        - Collects metrics for growth, conversion, retention, product
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

    Provides fast, lightweight insights without AI processing. Suitable for dashboard
    widgets and real-time updates. Returns immediately without external API calls.

    Returns:
        Dict: Response containing:
            - insights: Array of insight objects:
                - title: Short insight title
                - description: Brief description
                - priority: Urgency level (high/medium/low)
                - category: Insight category (growth/revenue/engagement)
                - metric_value: Optional numerical value
                - change: Optional percentage change
                - recommendation: Optional action suggestion
            - error: Error message if generation fails (insights will be empty array)

    Raises:
        401: Unauthorized - admin access required

    Notes:
        - No OpenAI API calls - purely rule-based
        - Analyzes growth metrics and conversion rates
        - Detects significant metric changes (anomalies)
        - Falls back gracefully on errors
        - Higher rate limit (60/minute) vs full reports (5/minute)
    """
    from application.services.ai_report_service import get_quick_insights

    try:
        insights = get_quick_insights()
        return {"insights": insights}
    except Exception as e:
        logger.error(f"Error getting quick insights: {e}")
        # v3.25: Don't expose error details
        return {"insights": [], "error": "Failed to get insights"}
