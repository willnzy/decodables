"""
AI Insights Service - AI-powered analytics and recommendations.

@module domains.stats.ai_insights
@version 1.0.0

Changes in v1.0.0 (2026-01-10):
- DDD Migration from api/admin/ai.py (MASTER-P2-001)
- Moved admin_get_ai_insights from Repository to Service
- Moved admin_get_ai_recommendations from Repository to Service
- Moved admin_get_behavior_analysis from Repository to Service
- Architecture: API → Service → Repository (compliant with DDD)

This module handles:
- AI-generated insights (growth/engagement/revenue)
- AI-generated recommendations (optimization)
- User behavior analysis (patterns/segments)

Note:
- These are rule-based analytics, NOT OpenAI API calls
- No caching needed (fast database aggregations)
- For AI-powered report generation, see application/services/ai_report_service.py
"""

import logging
from typing import List, Dict, Any, Optional

from core.database import get_database_client
from infrastructure.repositories import SupabaseAdminStatsRepository

logger = logging.getLogger(__name__)


def _get_stats_repo():
    """
    Get SupabaseAdminStatsRepository instance.

    Returns:
        SupabaseAdminStatsRepository instance
    """
    db_client = get_database_client()
    return SupabaseAdminStatsRepository(db_client)


# ==========================================
# AI Insights
# ==========================================

async def get_ai_insights(insight_type: str = "all") -> List[Dict[str, Any]]:
    """
    Get AI-generated insights for platform metrics.

    Analyzes user growth, engagement, and revenue metrics from the last 7 days
    and generates actionable insights.

    Args:
        insight_type: Filter by category
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

    Example:
        >>> insights = await get_ai_insights("growth")
        >>> for insight in insights:
        ...     print(f"{insight['title']}: {insight['description']}")

    Note:
        - Rule-based insights, not OpenAI API calls
        - 7-day window for metric aggregation
        - Empty list returned on errors
    """
    try:
        stats_repo = _get_stats_repo()
        insights = await stats_repo.admin_get_ai_insights(insight_type)
        return insights
    except Exception as e:
        logger.error(f"[AIInsights] Failed to get insights: {e}")
        return []


# ==========================================
# AI Recommendations
# ==========================================

async def get_ai_recommendations(area: str = "all") -> List[Dict[str, Any]]:
    """
    Get AI-generated optimization recommendations.

    Analyzes platform metrics and generates actionable recommendations for improvement
    in specific business areas based on threshold rules.

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

    Example:
        >>> recommendations = await get_ai_recommendations("growth")
        >>> for rec in recommendations:
        ...     if rec['priority'] == 'high':
        ...         print(f"⚠️ {rec['title']}: {rec['action']}")

    Business Rules:
        - Growth: Weekly signups < 80% of monthly average → high priority
        - Retention: Project creation rate < 50% → medium priority
        - Monetization: Conversion rate < 5% → high priority

    Note:
        - Rule-based recommendations, not OpenAI API calls
        - Compares current vs historical metrics
        - Empty list returned on errors
    """
    try:
        stats_repo = _get_stats_repo()
        recommendations = await stats_repo.admin_get_ai_recommendations(area)
        return recommendations
    except Exception as e:
        logger.error(f"[AIInsights] Failed to get recommendations: {e}")
        return []


# ==========================================
# Behavior Analysis
# ==========================================

async def get_behavior_analysis(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get AI-powered user behavior analysis.

    Analyzes user activity patterns, peak hours, and user segments over a specified
    date range. Limited to 50,000 events to prevent performance issues.

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

    Example:
        >>> analysis = await get_behavior_analysis(
        ...     start_date="2024-01-01",
        ...     end_date="2024-01-31"
        ... )
        >>> print(f"Peak hour: {analysis['patterns']['peak_activity_hour']}")
        >>> print(f"Total events: {analysis['patterns']['total_events_analyzed']}")

    Performance:
        - Limited to 50,000 events to prevent OOM
        - Uses aggregation for hourly/event distribution
        - Defaults to 30-day window if no dates provided

    Note:
        - Rule-based analysis, not OpenAI API calls
        - Empty result returned on errors
    """
    try:
        stats_repo = _get_stats_repo()
        analysis = await stats_repo.admin_get_behavior_analysis(start_date, end_date)
        return analysis
    except Exception as e:
        logger.error(f"[AIInsights] Failed to get behavior analysis: {e}")
        return {
            "patterns": {
                "event_distribution": {},
                "peak_activity_hour": 0,
                "hourly_activity": {},
                "total_events_analyzed": 0,
                "limited": False
            },
            "segments": {
                "by_tier": {},
                "total_users": 0
            },
            "period": {
                "start_date": start_date or "",
                "end_date": end_date or ""
            }
        }
