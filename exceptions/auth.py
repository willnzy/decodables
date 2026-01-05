"""
Authentication Exceptions

@module exceptions.auth
@version 3.24
"""

from typing import Optional, Dict, Any
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


class AdminRequiredException(AppException):
    """403: Admin privileges required."""
    status_code = 403
    default_code = ErrorCode.AUTH_ADMIN_REQUIRED
    default_message = "Administrator access required"


class MembershipRequiredException(AppException):
    """403: Paid membership required."""
    status_code = 403
    default_code = ErrorCode.AUTH_MEMBERSHIP_REQUIRED
    default_message = "A paid subscription is required for this feature"
    
    def __init__(self, feature: str = "this feature", **kwargs):
        message = f"A paid subscription is required for {feature}"
        super().__init__(message=message, context={"feature": feature}, **kwargs)


class TierRequiredException(AppException):
    """403: Specific subscription tier required."""
    status_code = 403
    default_code = ErrorCode.AUTH_TIER_REQUIRED
    default_message = "This feature requires a higher subscription tier"
    
    def __init__(self, required_tier: str, feature: str = "this feature", **kwargs):
        message = f"{feature.capitalize()} requires {required_tier} tier or higher"
        super().__init__(
            message=message,
            context={"required_tier": required_tier, "feature": feature},
            **kwargs
        )
