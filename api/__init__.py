"""
API Layer - v2 API Structure.

DEPRECATED: Old DDD API router removed.
All APIs now organized under:
- api.user (User-facing APIs at /api/v2/user/*)
- api.admin (Admin-facing APIs at /api/v2/admin/*)

@package api
@version 2.0.0
"""

# Re-export the main routers for backward compatibility
from .user import user_router
from .admin import admin_router

__all__ = [
    'user_router',
    'admin_router',
]
