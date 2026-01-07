"""
Validation Exceptions - Generic validation errors.

@module core.exceptions.validation
@version 1.0.0
"""

from typing import Optional, Dict, Any, List
from .base import AppException, ErrorCode


class ValidationException(AppException):
    """422: Request validation failed."""
    status_code = 422
    default_code = ErrorCode.VALIDATION_ERROR
    default_message = "Validation error"

    def __init__(
        self,
        errors: Optional[List[Dict]] = None,
        message: Optional[str] = None,
        **kwargs
    ):
        msg = message or "Request validation failed"
        super().__init__(
            message=msg,
            details={"errors": errors} if errors else None,
            **kwargs
        )


class FileTooLargeException(AppException):
    """413: Uploaded file exceeds size limit."""
    status_code = 413
    default_code = ErrorCode.UPLOAD_FILE_TOO_LARGE
    default_message = "File is too large"

    def __init__(
        self,
        file_size: Optional[int] = None,
        max_size: Optional[int] = None,
        **kwargs
    ):
        message = "File is too large"
        if max_size:
            max_mb = max_size / (1024 * 1024)
            message = f"File exceeds the maximum size of {max_mb:.1f}MB"
        super().__init__(
            message=message,
            context={"file_size": file_size, "max_size": max_size},
            details={"max_size_bytes": max_size},
            **kwargs
        )


class InvalidFileTypeException(AppException):
    """400: Uploaded file type is not supported."""
    status_code = 400
    default_code = ErrorCode.UPLOAD_INVALID_TYPE
    default_message = "File type not supported"

    def __init__(
        self,
        file_type: Optional[str] = None,
        allowed_types: Optional[List[str]] = None,
        **kwargs
    ):
        message = "File type not supported"
        if allowed_types:
            message = f"File type not supported. Allowed: {', '.join(allowed_types)}"
        super().__init__(
            message=message,
            context={"file_type": file_type, "allowed_types": allowed_types},
            details={"allowed_types": allowed_types},
            **kwargs
        )
