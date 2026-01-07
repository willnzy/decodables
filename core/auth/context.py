"""
Auth Context - Request-scoped authentication context.

@module core.auth.context
@version 1.0.0
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from contextvars import ContextVar

# Context variable for request-scoped auth state
_auth_context: ContextVar[Optional['AuthContext']] = ContextVar(
    'auth_context',
    default=None
)


@dataclass
class AuthContext:
    """
    Request-scoped authentication context.

    Provides a consistent way to access auth information
    throughout request handling without passing user objects.

    Attributes:
        user_id: Authenticated user ID
        is_authenticated: Whether request is authenticated
        roles: User roles/permissions
        metadata: Additional context data
    """
    user_id: Optional[str] = None
    is_authenticated: bool = False
    roles: list = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles

    def has_any_role(self, roles: list) -> bool:
        """Check if user has any of the specified roles."""
        return bool(set(self.roles) & set(roles))

    def has_all_roles(self, roles: list) -> bool:
        """Check if user has all specified roles."""
        return set(roles).issubset(set(self.roles))

    @property
    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.has_role("admin")


def get_auth_context() -> Optional[AuthContext]:
    """
    Get current request's auth context.

    Returns:
        AuthContext or None if not in request scope
    """
    return _auth_context.get()


def set_auth_context(context: AuthContext) -> None:
    """
    Set auth context for current request.

    Args:
        context: AuthContext to set
    """
    _auth_context.set(context)


def clear_auth_context() -> None:
    """Clear auth context after request completes."""
    _auth_context.set(None)


def create_auth_context(
    user_id: str,
    roles: list = None,
    **metadata
) -> AuthContext:
    """
    Create and set auth context for authenticated user.

    Args:
        user_id: User's unique identifier
        roles: List of user roles
        **metadata: Additional context data

    Returns:
        Created AuthContext
    """
    context = AuthContext(
        user_id=user_id,
        is_authenticated=True,
        roles=roles or [],
        metadata=metadata,
    )
    set_auth_context(context)
    return context


def create_anonymous_context() -> AuthContext:
    """
    Create auth context for anonymous/unauthenticated request.

    Returns:
        Anonymous AuthContext
    """
    context = AuthContext(is_authenticated=False)
    set_auth_context(context)
    return context
