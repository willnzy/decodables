"""
Templates Domain Exceptions.

@module domains.templates.exceptions
@version 1.0.0

Domain-specific exceptions for template operations.
API layer catches these and converts to HTTPException.
"""

from core.exceptions import AppException, ErrorCode


class TemplateException(AppException):
    """Base exception for templates domain."""
    pass


class TemplateNotFoundException(TemplateException):
    """Template not found."""
    status_code = 404
    default_code = ErrorCode.RESOURCE_NOT_FOUND
    default_message = "Template not found"


class TemplateLimitExceededException(TemplateException):
    """Template limit exceeded."""
    status_code = 400
    default_code = ErrorCode.BAD_REQUEST
    default_message = "Template limit exceeded"

    def __init__(self, max_templates: int = None, **kwargs):
        if max_templates:
            message = f"Maximum {max_templates} templates allowed. Delete some first."
        else:
            message = self.default_message
        super().__init__(message=message, **kwargs)
