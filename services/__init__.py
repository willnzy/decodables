"""
Services Package
Business logic layer (transitioning to DDD architecture)

Note: credit_service, marketplace_service, and resource_service have been migrated to:
- domains/ (business rules)
- application/ (use cases)
- infrastructure/ (data access)
"""

from .access_control import AccessControl
from . import experiment_service
from . import experiment_ai_service

# Backward compatibility helper
def get_access_control():
    """Return AccessControl class instance (for backward compatibility)."""
    return AccessControl

__all__ = [
    'AccessControl',
    'get_access_control',
    'experiment_service',
    'experiment_ai_service',
]

