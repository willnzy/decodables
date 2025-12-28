"""
Custom Exceptions
Application-specific exception classes

@module exceptions
"""

from typing import Optional, Any
from fastapi import HTTPException


class AppException(HTTPException):
    """Base application exception."""
    
    def __init__(
        self, 
        status_code: int, 
        detail: str,
        code: str = None,
        headers: dict = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.code = code or self._default_code()
    
    def _default_code(self) -> str:
        return self.__class__.__name__.upper()


# ==========================================
# Authentication & Authorization
# ==========================================

class UnauthorizedException(AppException):
    """User is not authenticated."""
    
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(status_code=401, detail=detail, code="UNAUTHORIZED")


class ForbiddenException(AppException):
    """User does not have permission."""
    
    def __init__(self, detail: str = "Access denied"):
        super().__init__(status_code=403, detail=detail, code="FORBIDDEN")


class AdminRequiredException(ForbiddenException):
    """Admin access required."""
    
    def __init__(self):
        super().__init__(detail="Admin access required")
        self.code = "ADMIN_REQUIRED"


class MembershipRequiredException(ForbiddenException):
    """Membership (Starter/Pro) required."""
    
    def __init__(self, feature: str = None):
        detail = f"Membership required to access {feature}" if feature else "Membership required"
        super().__init__(detail=detail)
        self.code = "MEMBERSHIP_REQUIRED"


class TierRequiredException(ForbiddenException):
    """Specific tier required."""
    
    def __init__(self, required_tier: str):
        super().__init__(detail=f"{required_tier.title()} membership required")
        self.code = "TIER_REQUIRED"


# ==========================================
# Resource Errors
# ==========================================

class NotFoundException(AppException):
    """Resource not found."""
    
    def __init__(self, resource: str = "Resource", resource_id: str = None):
        detail = f"{resource} not found"
        if resource_id:
            detail = f"{resource} '{resource_id}' not found"
        super().__init__(status_code=404, detail=detail, code="NOT_FOUND")


class ProjectNotFoundException(NotFoundException):
    """Project not found."""
    
    def __init__(self, project_id: str = None):
        super().__init__(resource="Project", resource_id=project_id)


class ListingNotFoundException(NotFoundException):
    """Marketplace listing not found."""
    
    def __init__(self, listing_id: str = None):
        super().__init__(resource="Listing", resource_id=listing_id)


class UserNotFoundException(NotFoundException):
    """User not found."""
    
    def __init__(self, user_id: str = None):
        super().__init__(resource="User", resource_id=user_id)


# ==========================================
# Business Logic Errors
# ==========================================

class InsufficientCreditsException(AppException):
    """User does not have enough credits."""
    
    def __init__(self, required: int = None, available: int = None):
        if required and available is not None:
            detail = f"Insufficient credits. Need {required}, have {available}"
        else:
            detail = "Insufficient credits"
        super().__init__(status_code=402, detail=detail, code="INSUFFICIENT_CREDITS")


class AlreadyPurchasedException(AppException):
    """Item already purchased."""
    
    def __init__(self, listing_id: str = None):
        super().__init__(
            status_code=200, 
            detail="Item already owned",
            code="ALREADY_PURCHASED"
        )


class InvalidOperationException(AppException):
    """Invalid operation for current state."""
    
    def __init__(self, detail: str = "Invalid operation"):
        super().__init__(status_code=400, detail=detail, code="INVALID_OPERATION")


class ListingNotApprovedException(InvalidOperationException):
    """Listing is not approved for public access."""
    
    def __init__(self):
        super().__init__(detail="Listing is not approved")
        self.code = "LISTING_NOT_APPROVED"


class ListingNotPublicException(InvalidOperationException):
    """Listing is not public."""
    
    def __init__(self):
        super().__init__(detail="Listing is not public")
        self.code = "LISTING_NOT_PUBLIC"


class CannotEditPendingException(InvalidOperationException):
    """Cannot edit listing while pending review."""
    
    def __init__(self):
        super().__init__(detail="Cannot edit listing while pending review")
        self.code = "CANNOT_EDIT_PENDING"


# ==========================================
# Content Policy Errors
# ==========================================

class ContentPolicyViolationException(AppException):
    """Content violates policy (NSFW, etc.)."""
    
    def __init__(self, detail: str = "Content violates our content policy"):
        super().__init__(status_code=400, detail=detail, code="CONTENT_VIOLATION")


# ==========================================
# Validation Errors
# ==========================================

class ValidationException(AppException):
    """Request validation failed."""
    
    def __init__(self, detail: str, field: str = None):
        if field:
            detail = f"{field}: {detail}"
        super().__init__(status_code=400, detail=detail, code="VALIDATION_ERROR")


class InvalidTiersException(ValidationException):
    """Invalid allowed_tiers value."""
    
    def __init__(self):
        super().__init__(
            detail="Must be ['free'], ['starter','pro'], or ['pro']",
            field="allowed_tiers"
        )


class PriceLimitException(ValidationException):
    """Price exceeds limit."""
    
    def __init__(self, max_price: int):
        super().__init__(
            detail=f"Price must be between 0 and {max_price}",
            field="price_credits"
        )


# ==========================================
# Rate Limiting
# ==========================================

class RateLimitException(AppException):
    """Rate limit exceeded."""
    
    def __init__(self, retry_after: int = None):
        headers = {"Retry-After": str(retry_after)} if retry_after else None
        super().__init__(
            status_code=429, 
            detail="Rate limit exceeded. Please try again later.",
            code="RATE_LIMIT_EXCEEDED",
            headers=headers
        )

