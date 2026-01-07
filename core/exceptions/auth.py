"""
Authentication Exceptions - Framework-level auth errors.

Business-specific auth errors (MembershipRequired, TierRequired)
should go to domains/identity/exceptions.py

@module core.exceptions.auth
@version 1.0.0
"""

from .base import AppException, ErrorCode


class UnauthorizedException(AppException):
    """401: User is not authenticated."""
    status_code = 401
    default_code = ErrorCode.AUTH_UNAUTHORIZED
    default_message = "Authentication required"


class TokenExpiredException(AppException):
    """401: Authentication token has expired."""
    status_code = 401
    default_code = ErrorCode.AUTH_TOKEN_EXPIRED
    default_message = "Your session has expired. Please sign in again."


class TokenInvalidException(AppException):
    """401: Authentication token is invalid."""
    status_code = 401
    default_code = ErrorCode.AUTH_TOKEN_INVALID
    default_message = "Invalid authentication token"


class ForbiddenException(AppException):
    """403: User is not authorized for this action."""
    status_code = 403
    default_code = ErrorCode.AUTH_FORBIDDEN
    default_message = "You don't have permission to perform this action"
