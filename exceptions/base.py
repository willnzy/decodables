"""
Base Exceptions - Core exception classes and error codes

@module exceptions.base
@version 3.24
"""

from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel


class ErrorCode(str, Enum):
    """Semantic error codes organized by module."""
    
    # === Generic Errors ===
    SERVER_ERROR = "server_error"
    VALIDATION_ERROR = "validation_error"
    TOO_MANY_REQUESTS = "too_many_requests"
    BAD_REQUEST = "bad_request"
    
    # === Authentication Errors ===
    AUTH_UNAUTHORIZED = "auth_unauthorized"
    AUTH_FORBIDDEN = "auth_forbidden"
    AUTH_TOKEN_EXPIRED = "auth_token_expired"
    AUTH_TOKEN_INVALID = "auth_token_invalid"
    AUTH_ADMIN_REQUIRED = "auth_admin_required"
    AUTH_MEMBERSHIP_REQUIRED = "auth_membership_required"
    AUTH_TIER_REQUIRED = "auth_tier_required"
    
    # === Resource Errors ===
    RESOURCE_NOT_FOUND = "resource_not_found"
    RESOURCE_ALREADY_EXISTS = "resource_already_exists"
    RESOURCE_CONFLICT = "resource_conflict"
    RESOURCE_DELETED = "resource_deleted"
    
    # === Billing/Credits Errors ===
    BILLING_INSUFFICIENT_CREDITS = "billing_insufficient_credits"
    BILLING_PAYMENT_FAILED = "billing_payment_failed"
    BILLING_SUBSCRIPTION_REQUIRED = "billing_subscription_required"
    BILLING_ALREADY_PURCHASED = "billing_already_purchased"
    
    # === AI Generation Errors ===
    AI_GENERATION_FAILED = "ai_generation_failed"
    AI_PROVIDER_TIMEOUT = "ai_provider_timeout"
    AI_PROVIDER_ERROR = "ai_provider_error"
    AI_CONTENT_POLICY = "ai_content_policy"
    AI_QUOTA_EXCEEDED = "ai_quota_exceeded"
    
    # === Marketplace Errors ===
    MARKETPLACE_NOT_APPROVED = "marketplace_not_approved"
    MARKETPLACE_NOT_PUBLIC = "marketplace_not_public"
    MARKETPLACE_CANNOT_EDIT = "marketplace_cannot_edit"
    MARKETPLACE_SELF_PURCHASE = "marketplace_self_purchase"
    
    # === Project Errors ===
    PROJECT_NOT_FOUND = "project_not_found"
    PROJECT_ACCESS_DENIED = "project_access_denied"
    PROJECT_LIMIT_REACHED = "project_limit_reached"
    
    # === Asset/Upload Errors ===
    UPLOAD_FILE_TOO_LARGE = "upload_file_too_large"
    UPLOAD_INVALID_TYPE = "upload_invalid_type"
    UPLOAD_FAILED = "upload_failed"
    
    # === Export Errors ===
    EXPORT_FAILED = "export_failed"
    EXPORT_INVALID_DATA = "export_invalid_data"


class ErrorResponse(BaseModel):
    """Standard error response format."""
    code: str
    message: str
    request_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "resource_not_found",
                "message": "Project not found",
                "request_id": "550e8400-e29b-41d4-a716-446655440000",
                "details": None
            }
        }


class AppException(Exception):
    """Base exception class for all application errors."""
    
    status_code: int = 500
    default_code: ErrorCode = ErrorCode.SERVER_ERROR
    default_message: str = "An unexpected error occurred"
    
    def __init__(
        self,
        status_code: Optional[int] = None,
        code: Optional[ErrorCode] = None,
        message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        self.status_code = status_code or self.__class__.status_code
        self.code = code or self.__class__.default_code
        self.message = message or self.__class__.default_message
        self.context = context or {}
        self.details = details
        self.headers = headers or {}  # Compatible with FastAPI HTTPException
        super().__init__(self.message)
    
    def to_response(self, request_id: Optional[str] = None) -> ErrorResponse:
        """Convert exception to error response."""
        return ErrorResponse(
            code=self.code.value if isinstance(self.code, ErrorCode) else str(self.code),
            message=self.message,
            request_id=request_id,
            details=self.details
        )
    
    def __repr__(self):
        return f"{self.__class__.__name__}(code={self.code}, message={self.message})"
