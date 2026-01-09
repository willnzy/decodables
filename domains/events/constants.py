"""
Events Domain Constants

Business rules and constants for Events domain.

@module domains.events.constants
@version 1.0.0 (created for v3.27 refactor)
"""

import re

# Date validation pattern (YYYY-MM-DD or ISO 8601)
DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?)?$')

# Valid group_by options for event statistics
VALID_GROUP_BY = {"event_type", "user_id", "date", "hour"}

# Valid stat types for aggregated statistics
VALID_STAT_TYPES = {
    "daily_active_users",
    "hourly_active_users",
    "daily_events",
    "hourly_events"
}

# Valid task types for aggregation
VALID_TASK_TYPES = {"hourly", "daily", "all"}

# Default pagination limits
DEFAULT_LIMIT = 50
MAX_LIMIT = 100

# Date range defaults
DEFAULT_STATS_DAYS = 7
DEFAULT_RANGE_DAYS = 30
MAX_RANGE_DAYS = 90

# Query limits to prevent OOM
MAX_QUERY_LIMIT = 100000
