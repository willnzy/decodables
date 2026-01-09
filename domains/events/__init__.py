"""
Events Domain Package

Domain layer for Events module following DDD principles.

@package domains.events
@version 1.0.0 (created for v3.27 refactor)
"""

from .entities import UserEvent, EventStats, AggregatedStats
from .repository import IEventsRepository
from .service import EventsDomainService
from .constants import (
    DATE_PATTERN,
    VALID_GROUP_BY,
    VALID_STAT_TYPES,
    VALID_TASK_TYPES,
    DEFAULT_LIMIT,
    MAX_LIMIT,
    DEFAULT_STATS_DAYS,
    DEFAULT_RANGE_DAYS,
    MAX_RANGE_DAYS,
    MAX_QUERY_LIMIT,
)

__all__ = [
    # Entities
    "UserEvent",
    "EventStats",
    "AggregatedStats",
    # Repository Interface
    "IEventsRepository",
    # Domain Service
    "EventsDomainService",
    # Constants
    "DATE_PATTERN",
    "VALID_GROUP_BY",
    "VALID_STAT_TYPES",
    "VALID_TASK_TYPES",
    "DEFAULT_LIMIT",
    "MAX_LIMIT",
    "DEFAULT_STATS_DAYS",
    "DEFAULT_RANGE_DAYS",
    "MAX_RANGE_DAYS",
    "MAX_QUERY_LIMIT",
]
