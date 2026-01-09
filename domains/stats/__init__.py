"""
Stats Domain - Statistics and analytics.

@module domains.stats
@version 3.29

This domain handles:
- Dashboard statistics
- User growth and revenue tracking
- Project and credit usage stats
- Tier distribution and conversion funnel
- Aggregated statistics from pre-computed data
"""

from domains.stats.service import (
    # Core statistics (7)
    get_dashboard_stats,
    get_user_growth_stats,
    get_revenue_stats,
    get_project_stats,
    get_credit_usage_stats,
    get_tier_distribution,
    get_conversion_funnel,
    # Aggregated statistics (11)
    get_export_stats,
    get_asset_usage_stats,
    get_tier_activity_stats,
    get_subscription_events_stats,
    get_page_views_stats,
    get_project_details_stats,
    get_returning_users_stats,
    get_tier_trend_stats,
    get_tier_conversion_stats,
    get_performance_metrics_stats,
    get_user_distribution_stats,
)

__all__ = [
    # Core statistics
    "get_dashboard_stats",
    "get_user_growth_stats",
    "get_revenue_stats",
    "get_project_stats",
    "get_credit_usage_stats",
    "get_tier_distribution",
    "get_conversion_funnel",
    # Aggregated statistics
    "get_export_stats",
    "get_asset_usage_stats",
    "get_tier_activity_stats",
    "get_subscription_events_stats",
    "get_page_views_stats",
    "get_project_details_stats",
    "get_returning_users_stats",
    "get_tier_trend_stats",
    "get_tier_conversion_stats",
    "get_performance_metrics_stats",
    "get_user_distribution_stats",
]
