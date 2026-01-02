"""
Unified Error Handling System (v3.12)
=====================================

This module provides a comprehensive error handling framework with:
- Semantic error codes (MODULE_ERROR_TYPE format)
- Structured error responses
- Request ID tracking for debugging
- Context preservation for logging (without exposing to clients)

Error Response Format:
{
    "code": "resource_not_found",
    "message": "Project not found",
    "request_id": "abc-123-xyz",
    "details": { ... }  // Optional validation details
}

Usage:
    from exceptions import (
        AppException, ErrorCode,
        NotFoundException, InsufficientCreditsException
    )
    
    # Raise with automatic error code
    raise NotFoundException("Project", project_id="proj_123")
    
    # Raise with custom context for logging
    raise AppException(
        status_code=500,
        code=ErrorCode.AI_PROVIDER_ERROR,
        message="AI generation failed",
        context={"provider": "fal.ai", "model": "flux", "raw_error": str(e)}
    )
"""

from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel


# ==========================================
# Error Codes Enumeration
# ==========================================

class ErrorCode(str, Enum):
    """
    Semantic error codes organized by module.
    Format: MODULE_ERROR_TYPE (lowercase, snake_case)
    
    These codes are exposed to frontend for programmatic handling.
    """
    
    # === Generic Errors ===
    SERVER_ERROR = "server_error"                    # 500: Unhandled exception
    VALIDATION_ERROR = "validation_error"            # 422: Request validation failed
    TOO_MANY_REQUESTS = "too_many_requests"          # 429: Rate limit exceeded
    BAD_REQUEST = "bad_request"                      # 400: Malformed request
    
    # === Authentication Errors ===
    AUTH_UNAUTHORIZED = "auth_unauthorized"          # 401: Not authenticated
    AUTH_FORBIDDEN = "auth_forbidden"                # 403: Not authorized
    AUTH_TOKEN_EXPIRED = "auth_token_expired"        # 401: Token has expired
    AUTH_TOKEN_INVALID = "auth_token_invalid"        # 401: Invalid token
    AUTH_ADMIN_REQUIRED = "auth_admin_required"      # 403: Admin access required
    AUTH_MEMBERSHIP_REQUIRED = "auth_membership_required"  # 403: Paid plan required
    AUTH_TIER_REQUIRED = "auth_tier_required"        # 403: Specific tier required
    
    # === Resource Errors ===
    RESOURCE_NOT_FOUND = "resource_not_found"        # 404: Generic not found
    RESOURCE_ALREADY_EXISTS = "resource_already_exists"  # 409: Duplicate entry
    RESOURCE_CONFLICT = "resource_conflict"          # 409: State conflict
    RESOURCE_DELETED = "resource_deleted"            # 410: Resource was deleted
    
    # === Billing/Credits Errors ===
    BILLING_INSUFFICIENT_CREDITS = "billing_insufficient_credits"  # 402: Not enough credits
    BILLING_PAYMENT_FAILED = "billing_payment_failed"  # 402: Payment processing failed
    BILLING_SUBSCRIPTION_REQUIRED = "billing_subscription_required"  # 402: Active subscription needed
    BILLING_ALREADY_PURCHASED = "billing_already_purchased"  # 200: Item already owned
    
    # === AI Generation Errors ===
    AI_GENERATION_FAILED = "ai_generation_failed"    # 500: AI failed to generate
    AI_PROVIDER_TIMEOUT = "ai_provider_timeout"      # 504: AI provider timed out
    AI_PROVIDER_ERROR = "ai_provider_error"          # 502: AI provider returned error
    AI_CONTENT_POLICY = "ai_content_policy"          # 400: Content policy violation
    AI_QUOTA_EXCEEDED = "ai_quota_exceeded"          # 429: AI usage quota exceeded
    
    # === Marketplace Errors ===
    MARKETPLACE_NOT_APPROVED = "marketplace_not_approved"  # 400: Listing not approved
    MARKETPLACE_NOT_PUBLIC = "marketplace_not_public"  # 400: Listing not public
    MARKETPLACE_CANNOT_EDIT = "marketplace_cannot_edit"  # 400: Cannot edit in current state
    MARKETPLACE_SELF_PURCHASE = "marketplace_self_purchase"  # 400: Cannot buy own item
    
    # === Project Errors ===
    PROJECT_NOT_FOUND = "project_not_found"          # 404: Project doesn't exist
    PROJECT_ACCESS_DENIED = "project_access_denied"  # 403: Not owner/purchaser
    PROJECT_LIMIT_REACHED = "project_limit_reached"  # 403: Free tier limit
    
    # === Asset/Upload Errors ===
    UPLOAD_FILE_TOO_LARGE = "upload_file_too_large"  # 413: File exceeds size limit
    UPLOAD_INVALID_TYPE = "upload_invalid_type"      # 400: Unsupported file type
    UPLOAD_FAILED = "upload_failed"                  # 500: Upload to storage failed
    
    # === Export Errors ===
    EXPORT_FAILED = "export_failed"                  # 500: PDF/ZIP generation failed
    EXPORT_INVALID_DATA = "export_invalid_data"      # 400: Invalid canvas data


# ==========================================
# Error Response Schema
# ==========================================

class ErrorResponse(BaseModel):
    """
    Standard error response format.
    This is what gets sent to the client.
    """
    code: str                           # Error code from ErrorCode enum
    message: str                        # Human-readable message (localization-ready)
    request_id: Optional[str] = None    # UUID for tracing in logs
    details: Optional[Dict[str, Any]] = None  # Extra info (validation errors, etc.)
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "resource_not_found",
                "message": "Project not found",
                "request_id": "550e8400-e29b-41d4-a716-446655440000",
                "details": None
            }
        }


# ==========================================
# Base Application Exception
# ==========================================

class AppException(Exception):
    """
    Base exception class for all application errors.
    
    Attributes:
        status_code: HTTP status code to return
        code: Semantic error code (from ErrorCode enum)
        message: Human-readable message for the client
        context: Additional data for logging (NOT exposed to client)
        details: Optional details to include in response (validation errors, etc.)
    
    Example:
        raise AppException(
            status_code=500,
            code=ErrorCode.AI_PROVIDER_ERROR,
            message="Failed to generate image",
            context={"provider": "fal.ai", "raw_error": str(e)}  # For logs only
        )
    """
    
    def __init__(
        self,
        status_code: int,
        code: str | ErrorCode,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.status_code = status_code
        self.code = code.value if isinstance(code, ErrorCode) else code
        self.message = message
        self.context = context or {}  # For logging, not exposed to client
        self.details = details        # Exposed to client (e.g., validation errors)
        self.headers = headers        # Optional response headers
        super().__init__(message)
    
    def to_response(self, request_id: Optional[str] = None) -> ErrorResponse:
        """Convert to ErrorResponse for JSON serialization."""
        return ErrorResponse(
            code=self.code,
            message=self.message,
            request_id=request_id,
            details=self.details
        )
    
    def to_log_dict(self, request_id: Optional[str] = None) -> Dict[str, Any]:
        """Convert to dict for structured logging (includes context)."""
        return {
            "error_code": self.code,
            "message": self.message,
            "status_code": self.status_code,
            "request_id": request_id,
            "context": self.context,
            "details": self.details,
        }


# ==========================================
# Authentication & Authorization Errors
# ==========================================

class UnauthorizedException(AppException):
    """User is not authenticated (401)."""
    
    def __init__(self, message: str = "Authentication required", context: Dict = None):
        super().__init__(
            status_code=401,
            code=ErrorCode.AUTH_UNAUTHORIZED,
            message=message,
            context=context
        )


class TokenExpiredException(AppException):
    """Authentication token has expired (401)."""
    
    def __init__(self, context: Dict = None):
        super().__init__(
            status_code=401,
            code=ErrorCode.AUTH_TOKEN_EXPIRED,
            message="Your session has expired. Please sign in again.",
            context=context
        )


class TokenInvalidException(AppException):
    """Authentication token is invalid (401)."""
    
    def __init__(self, context: Dict = None):
        super().__init__(
            status_code=401,
            code=ErrorCode.AUTH_TOKEN_INVALID,
            message="Invalid authentication token",
            context=context
        )


class ForbiddenException(AppException):
    """User does not have permission (403)."""
    
    def __init__(self, message: str = "Access denied", context: Dict = None):
        super().__init__(
            status_code=403,
            code=ErrorCode.AUTH_FORBIDDEN,
            message=message,
            context=context
        )


class AdminRequiredException(AppException):
    """Admin access required (403)."""
    
    def __init__(self, context: Dict = None):
        super().__init__(
            status_code=403,
            code=ErrorCode.AUTH_ADMIN_REQUIRED,
            message="Administrator access required",
            context=context
        )


class MembershipRequiredException(AppException):
    """Paid membership required (403)."""
    
    def __init__(self, feature: str = None, context: Dict = None):
        message = f"Upgrade to access {feature}" if feature else "Membership required"
        super().__init__(
            status_code=403,
            code=ErrorCode.AUTH_MEMBERSHIP_REQUIRED,
            message=message,
            context=context
        )


class TierRequiredException(AppException):
    """Specific tier required (403)."""
    
    def __init__(self, required_tier: str, context: Dict = None):
        super().__init__(
            status_code=403,
            code=ErrorCode.AUTH_TIER_REQUIRED,
            message=f"Upgrade to {required_tier.title()} to access this feature",
            context={"required_tier": required_tier, **(context or {})}
        )


# ==========================================
# Resource Errors
# ==========================================

class NotFoundException(AppException):
    """Resource not found (404)."""
    
    def __init__(
        self, 
        resource: str = "Resource", 
        resource_id: str = None,
        context: Dict = None
    ):
        message = f"{resource} not found"
        ctx = {"resource_type": resource, **(context or {})}
        if resource_id:
            ctx["resource_id"] = resource_id
        super().__init__(
            status_code=404,
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message=message,
            context=ctx
        )


class ProjectNotFoundException(AppException):
    """Project not found (404)."""
    
    def __init__(self, project_id: str = None, context: Dict = None):
        super().__init__(
            status_code=404,
            code=ErrorCode.PROJECT_NOT_FOUND,
            message="Project not found",
            context={"project_id": project_id, **(context or {})}
        )


class ListingNotFoundException(NotFoundException):
    """Marketplace listing not found (404)."""
    
    def __init__(self, listing_id: str = None, context: Dict = None):
        super().__init__(
            resource="Listing",
            resource_id=listing_id,
            context=context
        )


class UserNotFoundException(NotFoundException):
    """User not found (404)."""
    
    def __init__(self, user_id: str = None, context: Dict = None):
        super().__init__(
            resource="User",
            resource_id=user_id,
            context=context
        )


class ResourceAlreadyExistsException(AppException):
    """Resource already exists (409)."""
    
    def __init__(self, resource: str = "Resource", context: Dict = None):
        super().__init__(
            status_code=409,
            code=ErrorCode.RESOURCE_ALREADY_EXISTS,
            message=f"{resource} already exists",
            context=context
        )


# ==========================================
# Billing/Credits Errors
# ==========================================

class InsufficientCreditsException(AppException):
    """Not enough credits (402)."""
    
    def __init__(
        self, 
        required: int = None, 
        available: int = None,
        context: Dict = None
    ):
        if required is not None and available is not None:
            message = f"Insufficient credits. Need {required}, have {available}"
            ctx = {"required": required, "available": available, **(context or {})}
        else:
            message = "Insufficient credits"
            ctx = context
        super().__init__(
            status_code=402,
            code=ErrorCode.BILLING_INSUFFICIENT_CREDITS,
            message=message,
            context=ctx
        )


class PaymentFailedException(AppException):
    """Payment processing failed (402)."""
    
    def __init__(self, message: str = "Payment failed", context: Dict = None):
        super().__init__(
            status_code=402,
            code=ErrorCode.BILLING_PAYMENT_FAILED,
            message=message,
            context=context
        )


class AlreadyPurchasedException(AppException):
    """Item already owned (200 - not really an error)."""
    
    def __init__(self, listing_id: str = None, context: Dict = None):
        super().__init__(
            status_code=200,  # Not an error, just informational
            code=ErrorCode.BILLING_ALREADY_PURCHASED,
            message="You already own this item",
            context={"listing_id": listing_id, **(context or {})}
        )


# ==========================================
# AI Generation Errors
# ==========================================

class AIGenerationException(AppException):
    """AI generation failed (500)."""
    
    def __init__(self, message: str = "AI generation failed", context: Dict = None):
        super().__init__(
            status_code=500,
            code=ErrorCode.AI_GENERATION_FAILED,
            message=message,
            context=context
        )


class AIProviderTimeoutException(AppException):
    """AI provider timed out (504)."""
    
    def __init__(self, provider: str = "AI provider", context: Dict = None):
        super().__init__(
            status_code=504,
            code=ErrorCode.AI_PROVIDER_TIMEOUT,
            message=f"{provider} is taking too long. Please try again.",
            context={"provider": provider, **(context or {})}
        )


class AIProviderErrorException(AppException):
    """AI provider returned an error (502)."""
    
    def __init__(self, provider: str = "AI provider", context: Dict = None):
        super().__init__(
            status_code=502,
            code=ErrorCode.AI_PROVIDER_ERROR,
            message=f"{provider} encountered an error. Please try again.",
            context={"provider": provider, **(context or {})}
        )


class ContentPolicyViolationException(AppException):
    """Content violates policy (400)."""
    
    def __init__(self, message: str = "Content violates our content policy", context: Dict = None):
        super().__init__(
            status_code=400,
            code=ErrorCode.AI_CONTENT_POLICY,
            message=message,
            context=context
        )


# ==========================================
# Marketplace Errors
# ==========================================

class ListingNotApprovedException(AppException):
    """Listing is not approved (400)."""
    
    def __init__(self, context: Dict = None):
        super().__init__(
            status_code=400,
            code=ErrorCode.MARKETPLACE_NOT_APPROVED,
            message="This listing is not yet approved",
            context=context
        )


class ListingNotPublicException(AppException):
    """Listing is not public (400)."""
    
    def __init__(self, context: Dict = None):
        super().__init__(
            status_code=400,
            code=ErrorCode.MARKETPLACE_NOT_PUBLIC,
            message="This listing is not available",
            context=context
        )


class CannotEditPendingException(AppException):
    """Cannot edit listing while pending review (400)."""
    
    def __init__(self, context: Dict = None):
        super().__init__(
            status_code=400,
            code=ErrorCode.MARKETPLACE_CANNOT_EDIT,
            message="Cannot edit listing while pending review",
            context=context
        )


class SelfPurchaseException(AppException):
    """Cannot purchase own item (400)."""
    
    def __init__(self, context: Dict = None):
        super().__init__(
            status_code=400,
            code=ErrorCode.MARKETPLACE_SELF_PURCHASE,
            message="You cannot purchase your own item",
            context=context
        )


# ==========================================
# Validation Errors
# ==========================================

class ValidationException(AppException):
    """Request validation failed (400/422)."""
    
    def __init__(
        self, 
        message: str = "Validation failed",
        field: str = None,
        details: Dict = None,
        context: Dict = None
    ):
        if field:
            message = f"{field}: {message}"
        super().__init__(
            status_code=422,
            code=ErrorCode.VALIDATION_ERROR,
            message=message,
            details=details,
            context=context
        )


class InvalidTiersException(ValidationException):
    """Invalid allowed_tiers value (422)."""
    
    def __init__(self):
        super().__init__(
            message="Must be ['free'], ['starter','pro'], or ['pro']",
            field="allowed_tiers"
        )


class PriceLimitException(ValidationException):
    """Price exceeds limit (422)."""
    
    def __init__(self, max_price: int):
        super().__init__(
            message=f"Price must be between 0 and {max_price}",
            field="price_credits"
        )


# ==========================================
# Upload Errors
# ==========================================

class FileTooLargeException(AppException):
    """File exceeds size limit (413)."""
    
    def __init__(self, max_size_mb: int = 5, context: Dict = None):
        super().__init__(
            status_code=413,
            code=ErrorCode.UPLOAD_FILE_TOO_LARGE,
            message=f"File size exceeds the maximum limit of {max_size_mb}MB",
            context=context
        )


class InvalidFileTypeException(AppException):
    """Unsupported file type (400)."""
    
    def __init__(self, allowed_types: list = None, context: Dict = None):
        message = "Unsupported file type"
        if allowed_types:
            message += f". Allowed: {', '.join(allowed_types)}"
        super().__init__(
            status_code=400,
            code=ErrorCode.UPLOAD_INVALID_TYPE,
            message=message,
            context=context
        )


# ==========================================
# Rate Limiting
# ==========================================

class RateLimitException(AppException):
    """Rate limit exceeded (429)."""
    
    def __init__(self, retry_after: int = None, context: Dict = None):
        headers = {"Retry-After": str(retry_after)} if retry_after else None
        super().__init__(
            status_code=429,
            code=ErrorCode.TOO_MANY_REQUESTS,
            message="Too many requests. Please try again later.",
            context=context,
            headers=headers
        )


# ==========================================
# Export Errors
# ==========================================

class ExportFailedException(AppException):
    """Export (PDF/ZIP) generation failed (500)."""
    
    def __init__(self, format: str = "export", context: Dict = None):
        super().__init__(
            status_code=500,
            code=ErrorCode.EXPORT_FAILED,
            message=f"Failed to generate {format}. Please try again.",
            context=context
        )


# ==========================================
# Server Errors
# ==========================================

class InternalServerException(AppException):
    """Generic server error (500)."""
    
    def __init__(self, context: Dict = None):
        super().__init__(
            status_code=500,
            code=ErrorCode.SERVER_ERROR,
            message="Internal server error. Please try again later.",
            context=context
        )


class InvalidOperationException(AppException):
    """Invalid operation for current state (400)."""
    
    def __init__(self, message: str = "Invalid operation", context: Dict = None):
        super().__init__(
            status_code=400,
            code=ErrorCode.BAD_REQUEST,
            message=message,
            context=context
        )
