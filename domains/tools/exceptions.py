"""
Tools Domain Exceptions.

@module domains.tools.exceptions
@version 1.0.0

Domain-specific exceptions for tools operations.
API layer catches these and converts to HTTPException.
"""

from core.exceptions import AppException, ErrorCode


class ToolsException(AppException):
    """Base exception for tools domain."""
    pass


# ==========================================
# Validation Exceptions
# ==========================================

class InvalidProjectIdException(ToolsException):
    """Invalid project ID format."""
    status_code = 400
    default_code = ErrorCode.BAD_REQUEST
    default_message = "Invalid project ID format"


class InvalidFileTypeException(ToolsException):
    """File type not supported."""
    status_code = 400
    default_code = ErrorCode.BAD_REQUEST
    default_message = "Unsupported file type"

    def __init__(self, content_type: str = None, **kwargs):
        if content_type:
            message = f"Unsupported file type: {content_type}"
        else:
            message = self.default_message
        super().__init__(message=message, **kwargs)


class FileTooLargeException(ToolsException):
    """File exceeds size limit."""
    status_code = 400
    default_code = ErrorCode.UPLOAD_FILE_TOO_LARGE
    default_message = "File too large"

    def __init__(self, max_size_mb: int = None, **kwargs):
        if max_size_mb:
            message = f"File too large. Maximum size is {max_size_mb}MB"
        else:
            message = self.default_message
        super().__init__(message=message, **kwargs)


class InvalidPdfException(ToolsException):
    """Invalid or corrupted PDF file."""
    status_code = 400
    default_code = ErrorCode.BAD_REQUEST
    default_message = "Invalid or corrupted PDF file"


class TooManyPagesException(ToolsException):
    """PDF has too many pages."""
    status_code = 400
    default_code = ErrorCode.BAD_REQUEST
    default_message = "PDF has too many pages"

    def __init__(self, page_count: int = None, max_pages: int = None, **kwargs):
        if page_count and max_pages:
            message = f"PDF has too many pages ({page_count}). Maximum is {max_pages}"
        else:
            message = self.default_message
        super().__init__(message=message, **kwargs)


class OnlyPdfSupportedException(ToolsException):
    """Only PDF files are supported."""
    status_code = 400
    default_code = ErrorCode.BAD_REQUEST
    default_message = "Only PDF files are supported"


# ==========================================
# Permission Exceptions
# ==========================================

class SmartScanPermissionDeniedException(ToolsException):
    """User does not have permission for Smart Scan."""
    status_code = 403
    default_code = ErrorCode.AUTH_FORBIDDEN
    default_message = "Upgrade to Teacher Pro to use Smart Scan"


class SmartScanTrialDeniedException(ToolsException):
    """User does not have permission for Smart Scan (trial context)."""
    status_code = 403
    default_code = ErrorCode.AUTH_FORBIDDEN
    default_message = "Upgrade to Teacher Pro to use Smart Scan (or available during trial period)"


# ==========================================
# Credit Exceptions
# ==========================================

class InsufficientCreditsException(ToolsException):
    """Insufficient credits for operation."""
    status_code = 402
    default_code = ErrorCode.CREDITS_INSUFFICIENT
    default_message = "Insufficient credits for OCR"


# ==========================================
# Processing Exceptions
# ==========================================

class PdfProcessingFailedException(ToolsException):
    """PDF processing failed."""
    status_code = 500
    default_code = ErrorCode.SERVICE_UNAVAILABLE
    default_message = "Failed to process PDF"

    def __init__(self, reason: str = None, **kwargs):
        if reason:
            message = f"Failed to process PDF: {reason}"
        else:
            message = self.default_message
        super().__init__(message=message, **kwargs)


class OcrProcessingFailedException(ToolsException):
    """OCR processing failed."""
    status_code = 500
    default_code = ErrorCode.SERVICE_UNAVAILABLE
    default_message = "OCR processing failed"

    def __init__(self, reason: str = None, **kwargs):
        if reason:
            message = f"OCR processing failed: {reason}"
        else:
            message = self.default_message
        super().__init__(message=message, **kwargs)
