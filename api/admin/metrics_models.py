"""
Metrics API Response Models

@module api.admin.metrics_models
@version 3.28

v3.28: Created for type-safe API responses (MET-HIGH-2)
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any


# ==========================================
# Daily Metrics
# ==========================================

class DailyMetricItem(BaseModel):
    """Single day metric record."""
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    dau: Optional[int] = Field(None, description="Daily Active Users")
    mau: Optional[int] = Field(None, description="Monthly Active Users")
    new_users: Optional[int] = Field(None, description="New user signups")
    revenue: Optional[float] = Field(None, description="Revenue in USD")


class DailyMetricsResponse(BaseModel):
    """Response for GET /metrics/daily."""
    metrics: List[DailyMetricItem] = Field(..., description="List of daily metrics")
    start_date: str = Field(..., description="Query start date")
    end_date: str = Field(..., description="Query end date")


# ==========================================
# Monthly Metrics
# ==========================================

class MonthlyMetricItem(BaseModel):
    """Single month metric record."""
    month: str = Field(..., description="Month in YYYY-MM format")
    total_users: Optional[int] = Field(None, description="Total users at month end")
    total_revenue: Optional[float] = Field(None, description="Total revenue in USD")
    new_users: Optional[int] = Field(None, description="New users in month")


class MonthlyMetricsResponse(BaseModel):
    """Response for GET /metrics/monthly."""
    metrics: List[MonthlyMetricItem] = Field(..., description="List of monthly metrics")
    months: int = Field(..., description="Number of months returned")


# ==========================================
# Retention Metrics
# ==========================================

class RetentionMetricsResponse(BaseModel):
    """
    Response for GET /metrics/retention.

    Retention rates as percentages (0-100).
    """
    day_1: Optional[float] = Field(None, description="Day 1 retention rate (%)")
    day_7: Optional[float] = Field(None, description="Day 7 retention rate (%)")
    day_30: Optional[float] = Field(None, description="Day 30 retention rate (%)")
    week_1: Optional[float] = Field(None, description="Week 1 retention rate (%)")
    month_1: Optional[float] = Field(None, description="Month 1 retention rate (%)")


# ==========================================
# Funnel Metrics
# ==========================================

class FunnelStepData(BaseModel):
    """Single funnel step data."""
    step: str = Field(..., description="Step name (visitors, signups, etc.)")
    count: int = Field(..., ge=0, description="Number of events")


class FunnelMetricsResponse(BaseModel):
    """Response for GET /metrics/funnel."""
    funnel: List[FunnelStepData] = Field(..., description="Conversion funnel data")
    period: str = Field(..., description="Time period (7d, 14d, 30d, 60d, 90d)")


# ==========================================
# Error Metrics
# ==========================================

class ErrorMetricsResponse(BaseModel):
    """Response for GET /metrics/errors."""
    total: int = Field(..., ge=0, description="Total error count")
    hours: int = Field(..., ge=1, le=168, description="Time range in hours")
    by_type: Dict[str, int] = Field(..., description="Error counts grouped by type")
    by_status: Dict[int, int] = Field(..., description="Error counts grouped by HTTP status code")


# ==========================================
# DAU Trend
# ==========================================

class DAUTrendItem(BaseModel):
    """Single DAU trend data point."""
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    dau: int = Field(..., ge=0, description="Daily Active Users")


class DAUTrendResponse(BaseModel):
    """Response for GET /metrics/dau-trend."""
    trend: List[DAUTrendItem] = Field(..., description="DAU trend data")
    days: int = Field(..., ge=1, le=365, description="Number of days returned")


# ==========================================
# Refresh Metrics
# ==========================================

class RefreshMetricsResponse(BaseModel):
    """Response for POST /metrics/refresh."""
    status: str = Field(..., description="Refresh status (refreshed)")
    type: str = Field(..., description="Aggregation type (all, hourly, daily)")
    result: Dict[str, Any] = Field(..., description="Refresh result details")
