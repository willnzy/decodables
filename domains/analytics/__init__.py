"""
Analytics Domain - Analytics events processing.

@module domains.analytics
@version 2.0.0

Complete DDD implementation with entities, value objects, and repository interfaces.
"""

from .service import AnalyticsService
from .entities import AnalyticsEvent
from .value_objects import (
    EventSource,
    EventLevel,
    StandardEventTypes,
    AnalyticsEvents,
    USER_EVENT_TYPES,
    ACTIVITY_LOG_EVENT_MAPPING,
)
from .repository import IAnalyticsRepository

__all__ = [
    # Service (main entry point)
    "AnalyticsService",
    
    # Entities
    "AnalyticsEvent",
    
    # Value Objects
    "EventSource",
    "EventLevel",
    "StandardEventTypes",
    "AnalyticsEvents",  # Backward compatibility
    "USER_EVENT_TYPES",
    "ACTIVITY_LOG_EVENT_MAPPING",
    
    # Repository Interface
    "IAnalyticsRepository",
]
