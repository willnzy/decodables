"""
Admin Domain Module

@module domains.admin
@version 1.0.0

Provides admin-specific business logic for user management,
separated from regular user operations.

WHY separate Admin domain?
- Admin operations require audit logging
- Different security context (admin authentication)
- Cross-domain operations (users + projects + assets + analytics)
"""

from .admin_users_service import AdminUsersService

__all__ = ["AdminUsersService"]
