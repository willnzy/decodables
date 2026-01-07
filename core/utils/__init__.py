"""
Core Utils Layer - Framework level utility functions.

This module provides:
- datetime: Timezone-aware datetime utilities
- hash: Hashing utilities (MD5, SHA256)
- string: String manipulation utilities
- pagination: Pagination helpers

@package core.utils
@version 1.0.0

Design Principles:
- NO business logic here
- All code should be reusable in any FastAPI project
- Business-specific utilities go to shared/utils/
"""

from .datetime import (
    utc_now,
    to_utc,
    format_iso,
    parse_iso,
    is_valid_timezone,
)
from .hash import (
    md5_hash,
    sha256_hash,
    generate_token,
)
from .string import (
    slugify,
    truncate,
    safe_filename,
)
from .pagination import (
    PaginationParams,
    PaginatedResponse,
    paginate,
)

__all__ = [
    # DateTime
    'utc_now',
    'to_utc',
    'format_iso',
    'parse_iso',
    'is_valid_timezone',
    # Hash
    'md5_hash',
    'sha256_hash',
    'generate_token',
    # String
    'slugify',
    'truncate',
    'safe_filename',
    # Pagination
    'PaginationParams',
    'PaginatedResponse',
    'paginate',
]
