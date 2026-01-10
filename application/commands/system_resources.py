"""
SystemResources Commands - Write operations for Admin System Resources.

@module application.commands.system_resources
@version 1.0.0
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from fastapi import UploadFile

from domains.content.system_resources_service import SystemResourcesService


# ==========================================
# Command 1: Create System Resource
# ==========================================

@dataclass
class CreateSystemResourceCommand:
    """Command to create a system resource with file upload."""
    file: UploadFile
    type: str
    category: Optional[str]
    name: Optional[str]
    description: Optional[str]
    tags: Optional[str]  # Comma-separated
    allowed_tiers: Optional[str]  # Comma-separated
    sort_order: int
    admin_id: str


@dataclass
class CreateSystemResourceResult:
    """Result of create command."""
    result_data: Dict[str, Any]


class CreateSystemResourceHandler:
    """Handler for CreateSystemResourceCommand."""

    def __init__(self, service: SystemResourcesService):
        self._service = service

    async def handle(self, command: CreateSystemResourceCommand) -> CreateSystemResourceResult:
        """Execute create command."""
        resource_data = {
            "type": command.type,
            "category": command.category,
            "name": command.name,
            "description": command.description,
            "tags": command.tags,
            "allowed_tiers": command.allowed_tiers,
            "sort_order": command.sort_order,
        }

        result = await self._service.create_resource(
            file=command.file,
            resource_data=resource_data,
            admin_id=command.admin_id,
        )

        return CreateSystemResourceResult(result_data=result)


# ==========================================
# Command 2: Update System Resource
# ==========================================

@dataclass
class UpdateSystemResourceCommand:
    """Command to update system resource metadata."""
    resource_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    allowed_tiers: Optional[List[str]] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    metadata: Optional[dict] = None
    admin_id: str = None


@dataclass
class UpdateSystemResourceResult:
    """Result of update command."""
    result_data: Dict[str, Any]


class UpdateSystemResourceHandler:
    """Handler for UpdateSystemResourceCommand."""

    def __init__(self, service: SystemResourcesService):
        self._service = service

    async def handle(self, command: UpdateSystemResourceCommand) -> UpdateSystemResourceResult:
        """Execute update command."""
        # Build updates dict from command
        updates = {}
        if command.name is not None:
            updates["name"] = command.name
        if command.description is not None:
            updates["description"] = command.description
        if command.category is not None:
            updates["category"] = command.category
        if command.tags is not None:
            updates["tags"] = command.tags
        if command.allowed_tiers is not None:
            updates["allowed_tiers"] = command.allowed_tiers
        if command.sort_order is not None:
            updates["sort_order"] = command.sort_order
        if command.is_active is not None:
            updates["is_active"] = command.is_active
        if command.metadata is not None:
            updates["metadata"] = command.metadata

        result = await self._service.update_resource(
            resource_id=command.resource_id,
            updates=updates,
            admin_id=command.admin_id,
        )

        return UpdateSystemResourceResult(result_data=result)


# ==========================================
# Command 3: Replace Resource File
# ==========================================

@dataclass
class ReplaceResourceFileCommand:
    """Command to replace resource file."""
    resource_id: str
    file: UploadFile
    admin_id: str


@dataclass
class ReplaceResourceFileResult:
    """Result of replace file command."""
    result_data: Dict[str, Any]


class ReplaceResourceFileHandler:
    """Handler for ReplaceResourceFileCommand."""

    def __init__(self, service: SystemResourcesService):
        self._service = service

    async def handle(self, command: ReplaceResourceFileCommand) -> ReplaceResourceFileResult:
        """Execute replace file command."""
        result = await self._service.replace_file(
            resource_id=command.resource_id,
            new_file=command.file,
            admin_id=command.admin_id,
        )

        return ReplaceResourceFileResult(result_data=result)


# ==========================================
# Command 4: Delete System Resource
# ==========================================

@dataclass
class DeleteSystemResourceCommand:
    """Command to delete (soft delete) a system resource."""
    resource_id: str
    admin_id: str


@dataclass
class DeleteSystemResourceResult:
    """Result of delete command."""
    result_data: Dict[str, str]


class DeleteSystemResourceHandler:
    """Handler for DeleteSystemResourceCommand."""

    def __init__(self, service: SystemResourcesService):
        self._service = service

    async def handle(self, command: DeleteSystemResourceCommand) -> DeleteSystemResourceResult:
        """Execute delete command."""
        result = await self._service.delete_resource(
            resource_id=command.resource_id,
            admin_id=command.admin_id,
        )

        return DeleteSystemResourceResult(result_data=result)


# ==========================================
# Command 5: Batch Operation
# ==========================================

@dataclass
class BatchOperationCommand:
    """Command to perform batch operations."""
    operation: str  # "activate" | "deactivate" | "delete"
    resource_ids: List[str]
    admin_id: str


@dataclass
class BatchOperationResult:
    """Result of batch operation command."""
    result_data: Dict[str, str]


class BatchOperationHandler:
    """Handler for BatchOperationCommand."""

    def __init__(self, service: SystemResourcesService):
        self._service = service

    async def handle(self, command: BatchOperationCommand) -> BatchOperationResult:
        """Execute batch operation command."""
        result = await self._service.batch_operation(
            operation=command.operation,
            resource_ids=command.resource_ids,
            admin_id=command.admin_id,
        )

        return BatchOperationResult(result_data=result)
