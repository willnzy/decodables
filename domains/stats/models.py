"""
Stats Domain Models - Pydantic models for statistics responses.

@module domains.stats.models
@version 1.0.0

P2-001 Fix: Migrate Stats module from Dict return types to typed Pydantic models.

Architecture:
- Service layer returns Entity objects (not dicts)
- API layer serializes Entity to JSON
- Type safety throughout the stack
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# ==========================================
# Core Statistics Models
# ==========================================

class DashboardStats(BaseModel):
    """Dashboard KPI statistics."""
    total_users: int = Field(..., description="Total registered users")
    new_users: int = Field(..., description="New users in period")
    total_projects: int = Field(..., description="Total projects created")
    paying_users: int = Field(..., description="Users with active subscriptions")


class UserGrowthDataPoint(BaseModel):
    """Single data point for user growth chart."""
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    new_users: int = Field(..., description="New signups on this date")
    total_users: int = Field(..., description="Cumulative total users")


class RevenueDataPoint(BaseModel):
    """Single data point for revenue chart."""
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    revenue: float = Field(..., description="Revenue amount (USD)")
    transactions: int = Field(..., description="Number of transactions")


class ProjectStats(BaseModel):
    """Project statistics."""
    total: int = Field(..., description="Total projects")
    new_in_period: int = Field(..., description="New projects in period")


class CreditUsageStats(BaseModel):
    """Credit usage statistics (summary)."""
    total_credits_purchased: int = Field(..., description="Total credits purchased")
    total_credits_consumed: int = Field(..., description="Total credits consumed")
    avg_credits_per_user: float = Field(..., description="Average credits per user")


class CreditUsageItem(BaseModel):
    """Credit usage by action type (for charts)."""
    action: str = Field(..., description="Action type (ai_generation, smart_scan, etc.)")
    credits: int = Field(..., description="Total credits consumed")
    count: int = Field(..., description="Number of operations")


class TierDistributionItem(BaseModel):
    """Tier distribution item."""
    tier: str = Field(..., description="Tier code (t1/t2/t3)")
    count: int = Field(..., description="Number of users in tier")
    percentage: float = Field(..., description="Percentage of total users")


class ConversionFunnelStep(BaseModel):
    """Conversion funnel step."""
    step: str = Field(..., description="Funnel step name")
    count: int = Field(..., description="Number of users at this step")
    conversion_rate: Optional[float] = Field(None, description="Conversion rate from previous step")


# ==========================================
# Aggregated Statistics Models
# ==========================================

class ExportStatsItem(BaseModel):
    """Export operation statistics item."""
    export_type: str = Field(..., description="Export type (pdf/zip/preview)")
    count: int = Field(..., description="Number of exports")
    avg_duration_seconds: Optional[float] = Field(None, description="Average export duration")


class AssetUsageRanking(BaseModel):
    """Asset usage ranking item."""
    asset_id: str = Field(..., description="Asset identifier")
    asset_name: Optional[str] = Field(None, description="Asset name")
    usage_count: int = Field(..., description="Number of times used")
    unique_users: int = Field(..., description="Number of unique users")


class TierActivityStats(BaseModel):
    """Per-tier activity statistics."""
    tier: str = Field(..., description="Tier code (t1/t2/t3)")
    active_users: int = Field(..., description="Active users in period")
    total_projects: int = Field(..., description="Projects created by tier")
    avg_projects_per_user: float = Field(..., description="Average projects per user")


class SubscriptionEventItem(BaseModel):
    """Subscription event item."""
    date: str = Field(..., description="Event date (YYYY-MM-DD)")
    event_type: str = Field(..., description="Event type (created/upgraded/cancelled)")
    count: int = Field(..., description="Number of events")


class PageViewsDataPoint(BaseModel):
    """Page views data point."""
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    page_views: int = Field(..., description="Number of page views")
    unique_visitors: int = Field(..., description="Number of unique visitors")


class ProjectDetailsDataPoint(BaseModel):
    """Detailed project statistics data point."""
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    projects_created: int = Field(..., description="Projects created")
    projects_published: int = Field(..., description="Projects published")
    projects_deleted: int = Field(..., description="Projects deleted")


class ReturningUsersStats(BaseModel):
    """Returning users statistics."""
    returning_users_count: int = Field(..., description="Number of returning users")
    new_users_count: int = Field(..., description="Number of new users")
    retention_rate: float = Field(..., description="Retention rate percentage")


class TierTrendDataPoint(BaseModel):
    """Tier trend over time data point."""
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    t1_count: int = Field(..., description="Free tier users")
    t2_count: int = Field(..., description="Starter tier users")
    t3_count: int = Field(..., description="Pro tier users")


class TierConversionMatrix(BaseModel):
    """Tier conversion statistics."""
    from_tier: str = Field(..., description="Source tier (t1/t2/t3)")
    to_tier: str = Field(..., description="Target tier (t1/t2/t3)")
    conversion_count: int = Field(..., description="Number of conversions")
    conversion_rate: float = Field(..., description="Conversion rate percentage")


class PerformanceMetrics(BaseModel):
    """Core Web Vitals and performance metrics."""
    avg_lcp: Optional[float] = Field(None, description="Average Largest Contentful Paint (ms)")
    avg_fid: Optional[float] = Field(None, description="Average First Input Delay (ms)")
    avg_cls: Optional[float] = Field(None, description="Average Cumulative Layout Shift")
    avg_ttfb: Optional[float] = Field(None, description="Average Time to First Byte (ms)")


class UserDistributionItem(BaseModel):
    """User distribution by geography/device."""
    dimension: str = Field(..., description="Dimension name (country/device/browser)")
    value: str = Field(..., description="Dimension value")
    user_count: int = Field(..., description="Number of users")
    percentage: float = Field(..., description="Percentage of total")


# ==========================================
# Response Wrapper Models (for API layer)
# ==========================================

class StatsResponse(BaseModel):
    """Generic statistics response wrapper."""
    data: DashboardStats | ProjectStats | CreditUsageStats | ReturningUsersStats | PerformanceMetrics
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class StatsListResponse(BaseModel):
    """Generic statistics list response wrapper."""
    data: List[
        UserGrowthDataPoint |
        RevenueDataPoint |
        TierDistributionItem |
        ConversionFunnelStep |
        ExportStatsItem |
        AssetUsageRanking |
        TierActivityStats |
        SubscriptionEventItem |
        PageViewsDataPoint |
        ProjectDetailsDataPoint |
        TierTrendDataPoint |
        TierConversionMatrix |
        UserDistributionItem
    ]
    total_count: int = Field(..., description="Total number of items")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


# ==========================================
# Specific Response Models for P3-001 Fix
# ==========================================

class ExportStatsResponse(BaseModel):
    """Response for GET /stats/exports."""
    exports: List[ExportStatsItem] = Field(..., description="Export statistics by type")
    total_exports: int = Field(..., description="Total number of exports")


class AssetUsageResponse(BaseModel):
    """Response for GET /stats/assets."""
    assets: List[AssetUsageRanking] = Field(..., description="Asset usage rankings")
    total_assets: int = Field(..., description="Total number of tracked assets")


class TierActivityStatsResponse(BaseModel):
    """Response for GET /stats/tier-activity."""
    tier_stats: List[TierActivityStats] = Field(..., description="Activity stats per tier")


class SubscriptionEventsResponse(BaseModel):
    """Response for GET /stats/subscription-events."""
    events: List[SubscriptionEventItem] = Field(..., description="Subscription events timeline")
    total_events: int = Field(..., description="Total number of events")


class PageViewsResponse(BaseModel):
    """Response for GET /stats/page-views."""
    page_views: List[PageViewsDataPoint] = Field(..., description="Page views over time")


class ProjectDetailsResponse(BaseModel):
    """Response for GET /stats/project-details."""
    projects: List[ProjectDetailsDataPoint] = Field(..., description="Detailed project stats over time")


class ReturningUsersStatsResponse(BaseModel):
    """Response for GET /stats/returning-users."""
    stats: ReturningUsersStats = Field(..., description="Returning users statistics")


class TierTrendResponse(BaseModel):
    """Response for GET /stats/tier-trend."""
    trend: List[TierTrendDataPoint] = Field(..., description="Tier distribution trend over time")


class TierConversionResponse(BaseModel):
    """Response for GET /stats/tier-conversion."""
    conversions: List[TierConversionMatrix] = Field(..., description="Tier conversion matrix")
    total_conversions: int = Field(..., description="Total number of tier conversions")


class PerformanceMetricsResponse(BaseModel):
    """Response for GET /stats/performance."""
    metrics: PerformanceMetrics = Field(..., description="Core Web Vitals metrics")


class UserDistributionResponse(BaseModel):
    """Response for GET /stats/user-distribution."""
    distribution: List[UserDistributionItem] = Field(..., description="User distribution breakdown")
    total_users: int = Field(..., description="Total number of users")
