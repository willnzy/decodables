"""
Content Domain - System resources and content library.

This domain handles:
- System resource management (stickers, backgrounds, templates)
- Resource categorization and discovery
- Tier-based access control for resources
- Resource metadata management

@package domains.content
@version 1.0.0

Note: This domain manages official platform content provided to users.
"""

from .value_objects import (
    ResourceId,
    ResourceType,
    ResourceCategory,
    ResourceMetadata,
    AccessControl,
    TYPE_CATEGORIES,
)
from .aggregates.system_resource import SystemResource
from .exceptions import (
    ContentDomainException,
    ResourceNotFoundException,
    ResourceAccessDeniedException,
    InvalidResourceDataException,
    InvalidResourceTypeException,
    InvalidCategoryException,
)
from .repository import ISystemResourceRepository
from .service import ContentService

__all__ = [
    # Value Objects
    'ResourceId',
    'ResourceType',
    'ResourceCategory',
    'ResourceMetadata',
    'AccessControl',
    'TYPE_CATEGORIES',
    # Aggregates
    'SystemResource',
    # Exceptions
    'ContentDomainException',
    'ResourceNotFoundException',
    'ResourceAccessDeniedException',
    'InvalidResourceDataException',
    'InvalidResourceTypeException',
    'InvalidCategoryException',
    # Repository
    'ISystemResourceRepository',
    # Service
    'ContentService',
]
