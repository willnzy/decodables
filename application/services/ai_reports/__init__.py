"""
AI Reports Package - Business insights generation

@package services.ai_reports
@version 3.24
"""

from .models import InsightPriority, MetricTrend, MetricData, UserBehaviorTrend
from .collectors import (
    get_date_ranges,
    collect_growth_metrics,
    collect_conversion_metrics,
    collect_retention_metrics,
    collect_product_metrics,
    collect_user_behavior_trends,
)
from .report_generator import (
    identify_anomalies,
    generate_ai_business_report,
    get_quick_insights,
)

__all__ = [
    # Models
    'InsightPriority', 'MetricTrend', 'MetricData', 'UserBehaviorTrend',
    # Collectors
    'get_date_ranges', 'collect_growth_metrics', 'collect_conversion_metrics',
    'collect_retention_metrics', 'collect_product_metrics', 'collect_user_behavior_trends',
    # Report
    'identify_anomalies', 'generate_ai_business_report', 'get_quick_insights',
]
