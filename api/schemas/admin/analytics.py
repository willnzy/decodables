"""
Analytics Schemas - Analytics event models

@module schemas.analytics
"""

from typing import Optional, List
from pydantic import BaseModel


class AnalyticsEvent(BaseModel):
    """Single analytics event."""
    event_type: str
    event_id: Optional[str] = None  # v3.19: For CAPI/sGTM deduplication
    event_level: Optional[str] = None
    timestamp: Optional[str] = None
    utc_timestamp: Optional[str] = None
    properties: Optional[dict] = None
    session_id: Optional[str] = None
    env: Optional[dict] = None
    user_properties: Optional[dict] = None


class AnalyticsEventsRequest(BaseModel):
    """Batch analytics events request."""
    events: List[AnalyticsEvent]


class UserEventsRequest(BaseModel):
    """User events tracking request."""
    events: List[dict]
