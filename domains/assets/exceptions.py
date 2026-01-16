"""
Assets Domain Exceptions - Business-specific errors for asset operations.

@module domains.assets.exceptions
@version 1.0.0

These exceptions are raised by AssetsService and should be caught
by the API layer and converted to appropriate HTTP responses.
"""

from core.exceptions import AppException, ErrorCode


class AssetException(AppException):
    """Base exception for assets domain."""
    pass


# ==========================================
# Validation Exceptions (400 Bad Request)
# ==========================================

class InvalidUrlException(AssetException):
    """URL validation failed (too long, invalid format, etc.)."""
    status_code = 400
    default_code = ErrorCode.BAD_REQUEST
    default_message = "Invalid URL"

    def __init__(self, reason: str = None, **kwargs):
        message = reason or "Invalid URL format"
        super().__init__(message=message, **kwargs)


class SsrfException(AssetException):
    """URL points to internal/private network (SSRF attempt)."""
    status_code = 400
    default_code = ErrorCode.BAD_REQUEST
    default_message = "URL points to internal network"


class UrlNotAccessibleException(AssetException):
    """URL cannot be accessed or is not an image."""
    status_code = 400
    default_code = ErrorCode.BAD_REQUEST
    default_message = "URL is not accessible"

    def __init__(self, reason: str = None, status_code_http: int = None, **kwargs):
        if status_code_http:
            message = f"URL not accessible: {status_code_http}"
        else:
            message = reason or "Failed to access URL"
        super().__init__(message=message, **kwargs)


class InvalidFileTypeException(AssetException):
    """File type is not allowed."""
    status_code = 400
    default_code = ErrorCode.UPLOAD_INVALID_TYPE
    default_message = "Invalid file type"

    def __init__(self, content_type: str = None, allowed_types: list = None, **kwargs):
        if content_type:
            message = f"Unsupported file type: {content_type}"
        else:
            message = "Invalid file type"
        if allowed_types:
            message = f"{message}. Allowed: {', '.join(allowed_types)}"
        super().__init__(message=message, **kwargs)


class FileTooLargeException(AssetException):
    """File size exceeds the limit."""
    status_code = 400
    default_code = ErrorCode.UPLOAD_FILE_TOO_LARGE
    default_message = "File too large"

    def __init__(self, max_size_mb: int = 5, **kwargs):
        message = f"File too large. Maximum size is {max_size_mb}MB"
        super().__init__(message=message, **kwargs)


class NotImageException(AssetException):
    """URL does not point to an image."""
    status_code = 400
    default_code = ErrorCode.BAD_REQUEST
    default_message = "URL does not point to an image"


# ==========================================
# Permission Exceptions (403 Forbidden)
# ==========================================

class ProTierRequiredException(AssetException):
    """Operation requires Pro tier subscription."""
    status_code = 403
    default_code = ErrorCode.AUTH_FORBIDDEN
    default_message = "Personal asset upload requires Pro plan"


# ==========================================
# Not Found Exceptions (404)
# ==========================================

class AssetNotFoundException(AssetException):
    """Asset not found or not owned by user."""
    status_code = 404
    default_code = ErrorCode.RESOURCE_NOT_FOUND
    default_message = "Asset not found"

    def __init__(self, asset_id: str = None, in_trash: bool = False, **kwargs):
        if in_trash:
            message = "Asset not found in trash"
        elif asset_id:
            message = f"Asset {asset_id} not found or not owned by user"
        else:
            message = "Asset not found or not owned by user"
        super().__init__(message=message, context={"asset_id": asset_id}, **kwargs)


# ==========================================
# Server Exceptions (500)
# ==========================================

class StorageNotConfiguredException(AssetException):
    """Storage service is not configured."""
    status_code = 500
    default_code = ErrorCode.SERVICE_UNAVAILABLE
    default_message = "Storage service not configured"


class UploadFailedException(AssetException):
    """File upload to storage failed."""
    status_code = 500
    default_code = ErrorCode.UPLOAD_FAILED
    default_message = "Failed to upload file"

    def __init__(self, reason: str = None, **kwargs):
        message = f"Failed to upload file: {reason}" if reason else "Failed to upload file"
        super().__init__(message=message, **kwargs)
