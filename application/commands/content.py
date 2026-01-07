"""
Content Commands - Content management operations.

@module application.commands.content
@version 1.0.0
"""

from dataclasses import dataclass
from typing import Optional, List

from domains.content import (
    ContentService,
    SystemResource,
    ResourceType,
    ResourceCategory,
)


@dataclass
class CreateResourceCommand:
    """Command to create a system resource (admin only)."""
    resource_type: str
    url: str
    category: Optional[str] = None
    allowed_tiers: Optional[List[str]] = None
    name: Optional[str] = None
    tags: Optional[List[str]] = None


@dataclass
class CreateResourceResult:
    """Result of resource creation."""
    success: bool
    resource_id: Optional[str] = None
    error: Optional[str] = None


class CreateResourceHandler:
    """Handler for CreateResourceCommand."""

    def __init__(self, content_service: ContentService):
        self._content_service = content_service

    async def handle(self, command: CreateResourceCommand) -> CreateResourceResult:
        """Execute resource creation."""
        try:
            resource_type = ResourceType(command.resource_type)
            category = ResourceCategory(command.category) if command.category else None

            resource = await self._content_service.create_resource(
                resource_type=resource_type,
                url=command.url,
                category=category,
                allowed_tiers=command.allowed_tiers,
                name=command.name,
                tags=command.tags,
            )

            return CreateResourceResult(
                success=True,
                resource_id=resource.resource_id,
            )

        except Exception as e:
            return CreateResourceResult(
                success=False,
                error=str(e),
            )


@dataclass
class UpdateResourceCommand:
    """Command to update a system resource (admin only)."""
    resource_id: str
    name: Optional[str] = None
    tags: Optional[List[str]] = None
    allowed_tiers: Optional[List[str]] = None


@dataclass
class UpdateResourceResult:
    """Result of resource update."""
    success: bool
    error: Optional[str] = None


class UpdateResourceHandler:
    """Handler for UpdateResourceCommand."""

    def __init__(self, content_service: ContentService):
        self._content_service = content_service

    async def handle(self, command: UpdateResourceCommand) -> UpdateResourceResult:
        """Execute resource update."""
        try:
            await self._content_service.update_resource(
                resource_id=command.resource_id,
                name=command.name,
                tags=command.tags,
                allowed_tiers=command.allowed_tiers,
            )

            return UpdateResourceResult(success=True)

        except Exception as e:
            return UpdateResourceResult(
                success=False,
                error=str(e),
            )


@dataclass
class DeleteResourceCommand:
    """Command to delete a system resource (admin only)."""
    resource_id: str


@dataclass
class DeleteResourceResult:
    """Result of resource deletion."""
    success: bool
    error: Optional[str] = None


class DeleteResourceHandler:
    """Handler for DeleteResourceCommand."""

    def __init__(self, content_service: ContentService):
        self._content_service = content_service

    async def handle(self, command: DeleteResourceCommand) -> DeleteResourceResult:
        """Execute resource deletion."""
        try:
            deleted = await self._content_service.delete_resource(command.resource_id)

            return DeleteResourceResult(success=deleted)

        except Exception as e:
            return DeleteResourceResult(
                success=False,
                error=str(e),
            )
