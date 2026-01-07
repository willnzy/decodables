"""
Base Exceptions - Core exception classes and error codes.

@module core.exceptions.base
@version 1.0.0
"""

from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel


class ErrorCode(str, Enum):
    """Semantic error codes organized by category."""

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

    # === Resource Errors ===
    RESOURCE_NOT_FOUND = "resource_not_found"
    RESOURCE_ALREADY_EXISTS = "resource_already_exists"
    RESOURCE_CONFLICT = "resource_conflict"
    RESOURCE_DELETED = "resource_deleted"

    # === Upload Errors ===
    UPLOAD_FILE_TOO_LARGE = "upload_file_too_large"
    UPLOAD_INVALID_TYPE = "upload_invalid_type"
    UPLOAD_FAILED = "upload_failed"


class ErrorResponse(BaseModel):
    """Standard error response format for API."""
    code: str
    message: str
    request_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "code": "resource_not_found",
                "message": "Resource not found",
                "request_id": "550e8400-e29b-41d4-a716-446655440000",
                "details": None
            }
        }


class AppException(Exception):
    """
    Base exception class for all application errors.

    All custom exceptions should inherit from this class.
    Provides consistent error response formatting.
    """

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
        self.headers = headers or {}
        super().__init__(self.message)

    def to_response(self, request_id: Optional[str] = None) -> ErrorResponse:
        """Convert exception to API error response."""
        return ErrorResponse(
            code=self.code.value if isinstance(self.code, ErrorCode) else str(self.code),
            message=self.message,
            request_id=request_id,
            details=self.details
        )

    def __repr__(self):
        return f"{self.__class__.__name__}(code={self.code}, message={self.message})"
