"""
Events Management API Models - Request/Response schemas.

@module api.admin.events_models
@version 1.0.0
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ==========================================
# User Events Models
# ==========================================

class UserEventEntry(BaseModel):
    """Single user event entry."""
    id: Optional[str] = Field(None, description="Event ID")
    user_id: str = Field(..., description="User ID who triggered the event")
    event_type: str = Field(..., description="Event type/category")
    properties: Optional[Dict[str, Any]] = Field(None, description="Event properties (JSON)")
    session_id: Optional[str] = Field(None, description="Session ID")
    event_id: Optional[str] = Field(None, description="Client-side event ID")
    created_at: str = Field(..., description="Event timestamp (ISO format)")


class UserEventsResponse(BaseModel):
    """Response for GET /events/events."""
    events: List[UserEventEntry] = Field(..., description="List of user events")
    total: int = Field(..., description="Total number of events matching filters")
    offset: int = Field(..., description="Current pagination offset")
    limit: int = Field(..., description="Pagination limit")
    has_more: bool = Field(..., description="Whether more events are available")


# ==========================================
# Event Stats Models
# ==========================================

class EventStatsResponse(BaseModel):
    """Response for GET /events/stats."""
    stats: Dict[str, int] = Field(..., description="Event statistics grouped by specified field")
    group_by: str = Field(..., description="Grouping field used (event_type, user_id, date, hour)")
    start_date: Optional[str] = Field(None, description="Start date used for filtering")
    end_date: Optional[str] = Field(None, description="End date used for filtering")


# ==========================================
# Aggregated Stats Models
# ==========================================

class AggregatedStatsResponse(BaseModel):
    """Response for GET /aggregated/{stat_type}."""
    data: Optional[Dict[str, Any]] = Field(None, description="Aggregated statistics data")
    message: Optional[str] = Field(None, description="Message if no data available")


class AggregatedStatsEntry(BaseModel):
    """Single aggregated stats entry."""
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    stat_type: str = Field(..., description="Statistic type")
    data: Dict[str, Any] = Field(..., description="Statistics data (JSON)")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class AggregatedStatsRangeResponse(BaseModel):
    """Response for GET /aggregated/{stat_type}/range."""
    stats: List[AggregatedStatsEntry] = Field(..., description="List of aggregated stats over date range")
    stat_type: str = Field(..., description="Statistic type")
    days: int = Field(..., description="Number of days in range")


# ==========================================
# Aggregation Task Models
# ==========================================

class AggregationTriggerResponse(BaseModel):
    """Response for POST /aggregation/run."""
    status: str = Field(..., description="Task execution status")
    task_type: str = Field(..., description="Task type executed (all, hourly, daily)")
    message: Optional[str] = Field(None, description="Execution message")
    details: Optional[Dict[str, Any]] = Field(None, description="Execution details")
