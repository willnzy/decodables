"""
Creation Domain - Projects and assets management.

This domain handles:
- Project creation and management
- Canvas and page management
- Asset generation and storage
- Project sharing and collaboration

@package domains.creation
@version 1.0.0

Note: This domain manages the core creative content of the platform.
"""

from .value_objects import (
    ProjectId,
    AssetId,
    ProjectStatus,
    AssetType,
    CanvasSize,
    ProjectMetadata,
)
from .aggregates.project import Project
from .exceptions import (
    ProjectNotFoundException,
    ProjectAccessDeniedException,
    ProjectLimitExceededException,
    InvalidProjectDataException,
    AssetNotFoundException,
)
from .repository import IProjectRepository
from .service import CreationService

__all__ = [
    # Value Objects
    'ProjectId',
    'AssetId',
    'ProjectStatus',
    'AssetType',
    'CanvasSize',
    'ProjectMetadata',
    # Aggregates
    'Project',
    # Exceptions
    'ProjectNotFoundException',
    'ProjectAccessDeniedException',
    'ProjectLimitExceededException',
    'InvalidProjectDataException',
    'AssetNotFoundException',
    # Repository
    'IProjectRepository',
    # Service
    'CreationService',
]
