"""
DEPRECATED: schemas package has been moved to api/schemas/

This module provides backward compatibility.
Please update your imports to use api.schemas instead.

Old: from schemas.generation import StoryGenRequest
New: from api.schemas.user.generation import StoryGenRequest

Or: from api.schemas import StoryGenRequest
"""

import warnings

warnings.warn(
    "The 'schemas' package is deprecated. Use 'api.schemas' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from api.schemas for backward compatibility
from api.schemas import *
from api.schemas import __all__
