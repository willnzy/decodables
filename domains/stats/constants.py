"""
Stats Domain Constants.

@module domains.stats.constants
@version 3.29
"""

import re

# Dashboard periods
VALID_DASHBOARD_PERIODS = {"day", "week", "month", "year"}

# Group by options for time-series data
VALID_GROUP_BY = {"day", "week", "month"}

# Date validation pattern (YYYY-MM-DD or ISO 8601)
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2})?")
