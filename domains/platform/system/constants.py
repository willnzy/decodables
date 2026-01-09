"""
System Domain Constants.

@module domains.platform.system.constants
@version 3.30
"""

import re

# Config value types
VALID_VALUE_TYPES = {"text", "json", "number", "boolean", "encrypted"}

# Config groups
VALID_CONFIG_GROUPS = {"general", "feature_flags", "payment", "ai", "notification", "security", "cache"}

# Cache key pattern validation
CACHE_KEY_PATTERN = re.compile(r"^[a-zA-Z0-9_:*\-\.]+$")
