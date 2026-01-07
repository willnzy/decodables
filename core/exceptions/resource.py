"""
Resource Exceptions - Generic resource errors.

Business-specific resource errors (ProjectNotFound, ListingNotFound)
should go to domains/*/exceptions.py

@module core.exceptions.resource
@version 1.0.0
"""

from typing import Optional
from .base import AppException, ErrorCode


class NotFoundException(AppException):
    """404: Resource not found."""
    status_code = 404
    default_code = ErrorCode.RESOURCE_NOT_FOUND
    default_message = "Resource not found"

    def __init__(
        self,
        resource_type: str = "Resource",
        resource_id: Optional[str] = None,
        **kwargs
    ):
        message = f"{resource_type} not found"
        if resource_id:
            message = f"{resource_type} '{resource_id}' not found"
        super().__init__(
            message=message,
            context={"resource_type": resource_type, "resource_id": resource_id},
            **kwargs
        )


class ResourceAlreadyExistsException(AppException):
    """409: Resource already exists."""
    status_code = 409
    default_code = ErrorCode.RESOURCE_ALREADY_EXISTS
    default_message = "Resource already exists"

    def __init__(
        self,
        resource_type: str = "Resource",
        identifier: Optional[str] = None,
        **kwargs
    ):
        message = f"{resource_type} already exists"
        if identifier:
            message = f"{resource_type} '{identifier}' already exists"
        super().__init__(
            message=message,
            context={"resource_type": resource_type, "identifier": identifier},
            **kwargs
        )


class ResourceConflictException(AppException):
    """409: Resource conflict (concurrent modification, etc.)."""
    status_code = 409
    default_code = ErrorCode.RESOURCE_CONFLICT
    default_message = "Resource conflict"

    def __init__(self, reason: Optional[str] = None, **kwargs):
        message = reason or "A conflict occurred while processing this resource"
        super().__init__(message=message, **kwargs)
