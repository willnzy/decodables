"""
General Exceptions - Common framework-level errors.

@module core.exceptions.general
@version 1.0.0
"""

from typing import Optional
from .base import AppException, ErrorCode


class RateLimitException(AppException):
    """429: Rate limit exceeded."""
    status_code = 429
    default_code = ErrorCode.TOO_MANY_REQUESTS
    default_message = "Too many requests. Please try again later."

    def __init__(
        self,
        retry_after: Optional[int] = None,
        limit: Optional[str] = None,
        **kwargs
    ):
        message = "Too many requests. Please try again later."
        if retry_after:
            message = f"Rate limit exceeded. Try again in {retry_after} seconds."
        headers = {"Retry-After": str(retry_after)} if retry_after else {}
        super().__init__(
            message=message,
            context={"retry_after": retry_after, "limit": limit},
            details={"retry_after": retry_after},
            headers=headers,
            **kwargs
        )


class InternalServerException(AppException):
    """500: Unexpected internal error."""
    status_code = 500
    default_code = ErrorCode.SERVER_ERROR
    default_message = "An unexpected error occurred"

    def __init__(self, error: Optional[Exception] = None, **kwargs):
        message = "An unexpected error occurred. Please try again later."
        super().__init__(
            message=message,
            context={"original_error": str(error) if error else None},
            **kwargs
        )


class InvalidOperationException(AppException):
    """400: Operation is not valid in current state."""
    status_code = 400
    default_code = ErrorCode.BAD_REQUEST
    default_message = "Invalid operation"

    def __init__(
        self,
        operation: Optional[str] = None,
        reason: Optional[str] = None,
        **kwargs
    ):
        message = "This operation is not allowed"
        if operation and reason:
            message = f"Cannot {operation}: {reason}"
        elif reason:
            message = reason
        super().__init__(
            message=message,
            context={"operation": operation, "reason": reason},
            **kwargs
        )
