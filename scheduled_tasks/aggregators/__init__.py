"""
Aggregators Package - Modular statistics aggregation

@package scheduled_tasks.aggregators
@version 3.24
"""

from .base import log, get_supabase, upsert_stats
from .user_stats import (
    aggregate_daily_user_stats,
    aggregate_tier_distribution,
    aggregate_retention_stats,
    aggregate_returning_users,
    aggregate_tier_trend,
    aggregate_tier_conversion,
    aggregate_user_distribution,
)
from .revenue_stats import (
    aggregate_daily_revenue,
    aggregate_subscription_events,
)
from .project_stats import (
    aggregate_daily_projects,
    aggregate_project_details,
)
from .usage_stats import (
    aggregate_credit_usage,
    aggregate_generation_stats,
    aggregate_feature_usage,
    aggregate_export_stats,
    aggregate_asset_usage,
)
from .marketplace_stats import (
    aggregate_marketplace_stats,
)
from .analytics_stats import (
    aggregate_conversion_funnel,
    aggregate_event_stats,
    aggregate_page_views,
    aggregate_tier_activity,
    aggregate_performance_metrics,
)

__all__ = [
    'log', 'get_supabase', 'upsert_stats',
    # User
    'aggregate_daily_user_stats', 'aggregate_tier_distribution',
    'aggregate_retention_stats', 'aggregate_returning_users',
    'aggregate_tier_trend', 'aggregate_tier_conversion', 'aggregate_user_distribution',
    # Revenue
    'aggregate_daily_revenue', 'aggregate_subscription_events',
    # Projects
    'aggregate_daily_projects', 'aggregate_project_details',
    # Usage
    'aggregate_credit_usage', 'aggregate_generation_stats',
    'aggregate_feature_usage', 'aggregate_export_stats', 'aggregate_asset_usage',
    # Marketplace
    'aggregate_marketplace_stats',
    # Analytics
    'aggregate_conversion_funnel', 'aggregate_event_stats',
    'aggregate_page_views', 'aggregate_tier_activity', 'aggregate_performance_metrics',
]
