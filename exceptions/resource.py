"""
Resource Exceptions

@module exceptions.resource
@version 3.24
"""

from typing import Optional
from .base import AppException, ErrorCode


class NotFoundException(AppException):
    """404: Resource not found."""
    status_code = 404
    default_code = ErrorCode.RESOURCE_NOT_FOUND
    default_message = "Resource not found"
    
    def __init__(self, resource_type: str = "Resource", resource_id: str = None, **kwargs):
        message = f"{resource_type} not found"
        if resource_id:
            message = f"{resource_type} '{resource_id}' not found"
        super().__init__(
            message=message,
            context={"resource_type": resource_type, "resource_id": resource_id},
            **kwargs
        )


class ProjectNotFoundException(NotFoundException):
    """404: Project not found."""
    default_code = ErrorCode.PROJECT_NOT_FOUND
    
    def __init__(self, project_id: str = None, **kwargs):
        super().__init__(
            resource_type="Project",
            resource_id=project_id,
            **kwargs
        )


class ListingNotFoundException(NotFoundException):
    """404: Marketplace listing not found."""
    
    def __init__(self, listing_id: str = None, **kwargs):
        super().__init__(
            resource_type="Listing",
            resource_id=listing_id,
            **kwargs
        )


class UserNotFoundException(NotFoundException):
    """404: User not found."""
    
    def __init__(self, user_id: str = None, **kwargs):
        super().__init__(
            resource_type="User",
            resource_id=user_id,
            **kwargs
        )


class ResourceAlreadyExistsException(AppException):
    """409: Resource already exists."""
    status_code = 409
    default_code = ErrorCode.RESOURCE_ALREADY_EXISTS
    default_message = "Resource already exists"
    
    def __init__(self, resource_type: str = "Resource", identifier: str = None, **kwargs):
        message = f"{resource_type} already exists"
        if identifier:
            message = f"{resource_type} '{identifier}' already exists"
        super().__init__(
            message=message,
            context={"resource_type": resource_type, "identifier": identifier},
            **kwargs
        )
