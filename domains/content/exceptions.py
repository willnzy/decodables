"""
Content Domain Exceptions.

@module domains.content.exceptions
@version 1.1.0 (DDD Exception Compliance)

Changes:
- v1.1.0: Added exceptions for system resources service
  - InvalidFileTypeException, FileTooLargeException, UploadFailedException
  - InvalidOperationException
- v1.0.0: Initial implementation
"""

from core.exceptions import AppException, ErrorCode


class ContentDomainException(AppException):
    """Base exception for content domain."""
    pass


class ResourceNotFoundException(ContentDomainException):
    """Resource not found."""

    def __init__(self, resource_id: str):
        self.resource_id = resource_id
        super().__init__(f"Resource not found: {resource_id}")


class ResourceAccessDeniedException(ContentDomainException):
    """User does not have access to resource."""

    def __init__(self, resource_id: str, user_tier: str, required_tiers: list):
        self.resource_id = resource_id
        self.user_tier = user_tier
        self.required_tiers = required_tiers
        super().__init__(
            f"Access denied to resource {resource_id}. "
            f"User tier: {user_tier}, required: {required_tiers}"
        )


class InvalidResourceDataException(ContentDomainException):
    """Invalid resource data."""

    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(f"Invalid {field}: {message}")


class InvalidResourceTypeException(ContentDomainException):
    """Invalid resource type."""

    def __init__(self, resource_type: str):
        self.resource_type = resource_type
        super().__init__(f"Invalid resource type: {resource_type}")


class InvalidCategoryException(ContentDomainException):
    """Invalid category for resource type."""

    def __init__(self, category: str, resource_type: str):
        self.category = category
        self.resource_type = resource_type
        super().__init__(
            message=f"Invalid category '{category}' for resource type '{resource_type}'"
        )


# ==========================================
# System Resources Exceptions
# ==========================================

class SystemResourceNotFoundException(ContentDomainException):
    """System resource not found."""
    status_code = 404
    default_code = ErrorCode.RESOURCE_NOT_FOUND
    default_message = "Resource not found"

    def __init__(self, resource_id: str = None, **kwargs):
        message = f"Resource {resource_id} not found" if resource_id else "Resource not found"
        super().__init__(message=message, context={"resource_id": resource_id}, **kwargs)


class InvalidResourceTypeException(ContentDomainException):
    """Invalid resource type."""
    status_code = 400
    default_code = ErrorCode.BAD_REQUEST

    def __init__(self, resource_type: str, allowed_types: list = None, **kwargs):
        if allowed_types:
            message = f"Invalid type '{resource_type}'. Allowed: {allowed_types}"
        else:
            message = f"Invalid resource type: {resource_type}"
        super().__init__(message=message, **kwargs)


class InvalidFileTypeException(ContentDomainException):
    """File type is not allowed."""
    status_code = 400
    default_code = ErrorCode.UPLOAD_INVALID_TYPE
    default_message = "Invalid file type"

    def __init__(self, content_type: str = None, allowed_types: list = None, **kwargs):
        if allowed_types:
            message = f"Invalid file type. Allowed: {allowed_types}"
        elif content_type:
            message = f"Invalid file type: {content_type}"
        else:
            message = "Invalid file type"
        super().__init__(message=message, **kwargs)


class FileTooLargeException(ContentDomainException):
    """File size exceeds the limit."""
    status_code = 400
    default_code = ErrorCode.UPLOAD_FILE_TOO_LARGE
    default_message = "File too large"

    def __init__(self, max_size_mb: int = None, **kwargs):
        if max_size_mb:
            message = f"File too large. Maximum: {max_size_mb}MB"
        else:
            message = "File too large"
        super().__init__(message=message, **kwargs)


class UploadFailedException(ContentDomainException):
    """File upload failed."""
    status_code = 500
    default_code = ErrorCode.UPLOAD_FAILED
    default_message = "Failed to upload file"

    def __init__(self, reason: str = None, **kwargs):
        message = f"Failed to upload file: {reason}" if reason else "Failed to upload file"
        super().__init__(message=message, **kwargs)


class InvalidOperationException(ContentDomainException):
    """Unknown or invalid operation."""
    status_code = 400
    default_code = ErrorCode.BAD_REQUEST
    default_message = "Invalid operation"

    def __init__(self, operation: str = None, **kwargs):
        message = f"Unknown action: {operation}" if operation else "Invalid operation"
        super().__init__(message=message, **kwargs)
