"""
Shared Domain - Cross-cutting business rules.

Contains business logic shared across multiple domains.

@package domains.shared
@version 1.0.0
"""

from .access_control import (
    is_member,
    can_access_resource,
    get_total_credits,
    publish_permission,
    validate_allowed_tiers,
    listing_is_public_visible,
)

__all__ = [
    "is_member",
    "can_access_resource",
    "get_total_credits",
    "publish_permission",
    "validate_allowed_tiers",
    "listing_is_public_visible",
]
