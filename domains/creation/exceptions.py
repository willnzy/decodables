"""
Creation Domain Exceptions.

@module domains.creation.exceptions
@version 1.0.0
"""

from core.exceptions import DomainException


class CreationException(DomainException):
    """Base exception for creation domain."""

    def __init__(self, message: str, code: str = "CREATION_ERROR"):
        super().__init__(message, code)


class ProjectNotFoundException(CreationException):
    """Raised when a project is not found."""

    def __init__(self, project_id: str):
        super().__init__(
            message=f"Project not found: {project_id}",
            code="PROJECT_NOT_FOUND"
        )
        self.project_id = project_id
        self.status_code = 404


class ProjectAccessDeniedException(CreationException):
    """Raised when user doesn't have access to a project."""

    def __init__(self, project_id: str, user_id: str):
        super().__init__(
            message=f"Access denied to project {project_id} for user {user_id}",
            code="PROJECT_ACCESS_DENIED"
        )
        self.project_id = project_id
        self.user_id = user_id
        self.status_code = 403


class InvalidProjectDataException(CreationException):
    """Raised when project data is invalid."""

    def __init__(self, field: str, reason: str):
        super().__init__(
            message=f"Invalid project data for field '{field}': {reason}",
            code="INVALID_PROJECT_DATA"
        )
        self.field = field
        self.reason = reason
        self.status_code = 400


class AssetNotFoundException(CreationException):
    """Raised when an asset is not found."""

    def __init__(self, asset_id: str):
        super().__init__(
            message=f"Asset not found: {asset_id}",
            code="ASSET_NOT_FOUND"
        )
        self.asset_id = asset_id
        self.status_code = 404


class ProjectLimitExceededException(CreationException):
    """Raised when user exceeds project limit."""

    def __init__(self, user_id: str, limit: int):
        super().__init__(
            message=f"User {user_id} has reached the project limit of {limit}",
            code="PROJECT_LIMIT_EXCEEDED"
        )
        self.user_id = user_id
        self.limit = limit
        self.status_code = 403


class CanvasOperationException(CreationException):
    """Raised when a canvas operation fails."""

    def __init__(self, project_id: str, operation: str, reason: str):
        super().__init__(
            message=f"Canvas operation '{operation}' failed for project {project_id}: {reason}",
            code="CANVAS_OPERATION_FAILED"
        )
        self.project_id = project_id
        self.operation = operation
        self.reason = reason
        self.status_code = 400
