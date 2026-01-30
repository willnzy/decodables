"""
Creation Domain Exceptions.

@module domains.creation.exceptions
@version 1.0.0
"""

from core.exceptions import AppException, ErrorCode


class CreationException(AppException):
    """Base exception for creation domain."""
    pass


class ProjectNotFoundException(CreationException):
    """Raised when a project is not found."""
    status_code = 404
    default_code = ErrorCode.RESOURCE_NOT_FOUND
    default_message = "Project not found"

    def __init__(self, project_id: str = None, **kwargs):
        message = "Project not found"
        if project_id:
            message = f"Project not found: {project_id}"

        super().__init__(
            message=message,
            context={"project_id": project_id},
            **kwargs
        )


class ProjectAccessDeniedException(CreationException):
    """Raised when user doesn't have access to a project."""
    status_code = 403
    default_code = ErrorCode.AUTH_FORBIDDEN
    default_message = "Project access denied"

    def __init__(self, project_id: str = None, user_id: str = None, **kwargs):
        message = "Project access denied"
        if project_id and user_id:
            message = f"Access denied to project {project_id} for user {user_id}"

        super().__init__(
            message=message,
            context={"project_id": project_id, "user_id": user_id},
            **kwargs
        )


class InvalidProjectDataException(CreationException):
    """Raised when project data is invalid."""
    status_code = 400
    default_code = ErrorCode.VALIDATION_ERROR
    default_message = "Invalid project data"

    def __init__(self, field: str = None, reason: str = None, **kwargs):
        message = "Invalid project data"
        if field and reason:
            message = f"Invalid project data for field '{field}': {reason}"

        super().__init__(
            message=message,
            context={"field": field, "reason": reason},
            **kwargs
        )


class AssetNotFoundException(CreationException):
    """Raised when an asset is not found."""
    status_code = 404
    default_code = ErrorCode.RESOURCE_NOT_FOUND
    default_message = "Asset not found"

    def __init__(self, asset_id: str = None, **kwargs):
        message = "Asset not found"
        if asset_id:
            message = f"Asset not found: {asset_id}"

        super().__init__(
            message=message,
            context={"asset_id": asset_id},
            **kwargs
        )


class ProjectLimitExceededException(CreationException):
    """Raised when user exceeds project limit."""
    status_code = 403
    default_code = ErrorCode.AUTH_FORBIDDEN
    default_message = "Project limit exceeded"

    def __init__(self, user_id: str = None, limit: int = None, **kwargs):
        message = "Project limit exceeded"
        if user_id and limit:
            message = f"User {user_id} has reached the project limit of {limit}"

        super().__init__(
            message=message,
            context={"user_id": user_id, "limit": limit},
            **kwargs
        )


class CanvasOperationException(CreationException):
    """Raised when a canvas operation fails."""
    status_code = 400
    default_code = ErrorCode.BAD_REQUEST
    default_message = "Canvas operation failed"

    def __init__(
        self,
        project_id: str = None,
        operation: str = None,
        reason: str = None,
        **kwargs
    ):
        message = "Canvas operation failed"
        if operation and project_id:
            message = f"Canvas operation '{operation}' failed for project {project_id}"
            if reason:
                message += f": {reason}"

        super().__init__(
            message=message,
            context={
                "project_id": project_id,
                "operation": operation,
                "reason": reason,
            },
            **kwargs
        )


class PageNotFoundException(CreationException):
    """
    WS-4 (1B#28): Raised when a page is not found in a project.
    Replaces ValueError in aggregate methods.
    """
    status_code = 404
    default_code = ErrorCode.RESOURCE_NOT_FOUND
    default_message = "Page not found"

    def __init__(self, page_id: str, project_id: str = None, **kwargs):
        message = f"Page {page_id} not found"
        if project_id:
            message += f" in project {project_id}"

        super().__init__(
            message=message,
            context={"page_id": page_id, "project_id": project_id},
            **kwargs
        )
