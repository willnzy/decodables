"""
DEPRECATED: timezone_utils has been moved to core/utils/timezone.py

This module provides backward compatibility.
Please update your imports to use core.utils.timezone instead.

Old: from timezone_utils import get_request_timezone
New: from core.utils.timezone import get_request_timezone
"""

import warnings

warnings.warn(
    "The 'timezone_utils' module is deprecated. Use 'core.utils.timezone' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything for backward compatibility
from core.utils.timezone import *
from core.utils.timezone import (
    COMMON_TIMEZONES,
    COUNTRY_DEFAULT_TIMEZONES,
)
