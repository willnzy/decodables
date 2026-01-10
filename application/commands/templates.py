"""
Templates Commands - Write operations for user prompt templates.

@module application.commands.templates
@version 1.0.0
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional

from domains.templates.templates_service import TemplatesService


# ==========================================
# Asset Templates Commands
# ==========================================

# Command 1: Create Asset Template
# ==========================================

@dataclass
class CreateAssetTemplateCommand:
    """Command to create asset prompt template."""
    user_id: str
    template_data: Dict[str, Any]


@dataclass
class CreateAssetTemplateResult:
    """Result of create asset template command."""
    template: Dict[str, Any]


class CreateAssetTemplateHandler:
    """Handler for CreateAssetTemplateCommand."""

    def __init__(self, service: TemplatesService):
        self._service = service

    async def handle(self, command: CreateAssetTemplateCommand) -> CreateAssetTemplateResult:
        """Execute create command."""
        template = await self._service.create_asset_template(
            command.user_id,
            command.template_data
        )
        return CreateAssetTemplateResult(template=template)


# Command 2: Update Asset Template
# ==========================================

@dataclass
class UpdateAssetTemplateCommand:
    """Command to update asset prompt template."""
    template_id: str
    user_id: str
    updates: Dict[str, Any]


@dataclass
class UpdateAssetTemplateResult:
    """Result of update asset template command."""
    template: Dict[str, Any]


class UpdateAssetTemplateHandler:
    """Handler for UpdateAssetTemplateCommand."""

    def __init__(self, service: TemplatesService):
        self._service = service

    async def handle(self, command: UpdateAssetTemplateCommand) -> UpdateAssetTemplateResult:
        """Execute update command."""
        template = await self._service.update_asset_template(
            command.template_id,
            command.user_id,
            command.updates
        )
        return UpdateAssetTemplateResult(template=template)


# Command 3: Delete Asset Template
# ==========================================

@dataclass
class DeleteAssetTemplateCommand:
    """Command to delete asset prompt template."""
    template_id: str
    user_id: str


@dataclass
class DeleteAssetTemplateResult:
    """Result of delete asset template command."""
    success: bool


class DeleteAssetTemplateHandler:
    """Handler for DeleteAssetTemplateCommand."""

    def __init__(self, service: TemplatesService):
        self._service = service

    async def handle(self, command: DeleteAssetTemplateCommand) -> DeleteAssetTemplateResult:
        """Execute delete command."""
        success = await self._service.delete_asset_template(
            command.template_id,
            command.user_id
        )
        return DeleteAssetTemplateResult(success=success)


# Command 4: Use Asset Template
# ==========================================

@dataclass
class UseAssetTemplateCommand:
    """Command to mark asset template as used."""
    template_id: str
    user_id: str


@dataclass
class UseAssetTemplateResult:
    """Result of use asset template command."""
    new_use_count: int


class UseAssetTemplateHandler:
    """Handler for UseAssetTemplateCommand."""

    def __init__(self, service: TemplatesService):
        self._service = service

    async def handle(self, command: UseAssetTemplateCommand) -> UseAssetTemplateResult:
        """Execute use command."""
        new_count = await self._service.use_asset_template(
            command.template_id,
            command.user_id
        )
        return UseAssetTemplateResult(new_use_count=new_count)


# ==========================================
# Page Templates Commands
# ==========================================

# Command 5: Create Page Template
# ==========================================

@dataclass
class CreatePageTemplateCommand:
    """Command to create page prompt template."""
    user_id: str
    template_data: Dict[str, Any]


@dataclass
class CreatePageTemplateResult:
    """Result of create page template command."""
    template: Dict[str, Any]


class CreatePageTemplateHandler:
    """Handler for CreatePageTemplateCommand."""

    def __init__(self, service: TemplatesService):
        self._service = service

    async def handle(self, command: CreatePageTemplateCommand) -> CreatePageTemplateResult:
        """Execute create command."""
        template = await self._service.create_page_template(
            command.user_id,
            command.template_data
        )
        return CreatePageTemplateResult(template=template)


# Command 6: Update Page Template
# ==========================================

@dataclass
class UpdatePageTemplateCommand:
    """Command to update page prompt template."""
    template_id: str
    user_id: str
    updates: Dict[str, Any]


@dataclass
class UpdatePageTemplateResult:
    """Result of update page template command."""
    template: Dict[str, Any]


class UpdatePageTemplateHandler:
    """Handler for UpdatePageTemplateCommand."""

    def __init__(self, service: TemplatesService):
        self._service = service

    async def handle(self, command: UpdatePageTemplateCommand) -> UpdatePageTemplateResult:
        """Execute update command."""
        template = await self._service.update_page_template(
            command.template_id,
            command.user_id,
            command.updates
        )
        return UpdatePageTemplateResult(template=template)


# Command 7: Delete Page Template
# ==========================================

@dataclass
class DeletePageTemplateCommand:
    """Command to delete page prompt template."""
    template_id: str
    user_id: str


@dataclass
class DeletePageTemplateResult:
    """Result of delete page template command."""
    success: bool


class DeletePageTemplateHandler:
    """Handler for DeletePageTemplateCommand."""

    def __init__(self, service: TemplatesService):
        self._service = service

    async def handle(self, command: DeletePageTemplateCommand) -> DeletePageTemplateResult:
        """Execute delete command."""
        success = await self._service.delete_page_template(
            command.template_id,
            command.user_id
        )
        return DeletePageTemplateResult(success=success)


# Command 8: Use Page Template
# ==========================================

@dataclass
class UsePageTemplateCommand:
    """Command to mark page template as used."""
    template_id: str
    user_id: str


@dataclass
class UsePageTemplateResult:
    """Result of use page template command."""
    new_use_count: int


class UsePageTemplateHandler:
    """Handler for UsePageTemplateCommand."""

    def __init__(self, service: TemplatesService):
        self._service = service

    async def handle(self, command: UsePageTemplateCommand) -> UsePageTemplateResult:
        """Execute use command."""
        new_count = await self._service.use_page_template(
            command.template_id,
            command.user_id
        )
        return UsePageTemplateResult(new_use_count=new_count)
