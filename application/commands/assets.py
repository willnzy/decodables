"""
Assets Commands - Write operations for user assets.

@module application.commands.assets
@version 1.0.0
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from fastapi import UploadFile

from domains.assets.assets_service import AssetsService


# ==========================================
# Command 1: Upload Asset
# ==========================================

@dataclass
class UploadAssetCommand:
    """Command to upload asset."""
    user_id: str
    user_tier: str
    file: UploadFile
    project_id: Optional[str]
    timezone: str = "UTC"


@dataclass
class UploadAssetResult:
    """Result of upload asset command."""
    result: Dict[str, Any]


class UploadAssetHandler:
    """Handler for UploadAssetCommand."""

    def __init__(self, service: AssetsService):
        self._service = service

    async def handle(self, command: UploadAssetCommand) -> UploadAssetResult:
        """Execute upload asset command."""
        result = await self._service.upload_asset(
            command.user_id,
            command.user_tier,
            command.file,
            command.project_id,
            command.timezone
        )
        return UploadAssetResult(result=result)


# ==========================================
# Command 2: Add Asset From URL
# ==========================================

@dataclass
class AddAssetFromURLCommand:
    """Command to add asset from external URL."""
    user_id: str
    url: str
    project_id: Optional[str]
    timezone: str = "UTC"


@dataclass
class AddAssetFromURLResult:
    """Result of add asset from URL command."""
    result: Dict[str, Any]


class AddAssetFromURLHandler:
    """Handler for AddAssetFromURLCommand."""

    def __init__(self, service: AssetsService):
        self._service = service

    async def handle(self, command: AddAssetFromURLCommand) -> AddAssetFromURLResult:
        """Execute add asset from URL command."""
        result = await self._service.add_asset_from_url(
            command.user_id,
            command.url,
            command.project_id,
            command.timezone
        )
        return AddAssetFromURLResult(result=result)


# ==========================================
# Command 3: Delete Asset
# ==========================================

@dataclass
class DeleteAssetCommand:
    """Command to delete asset."""
    asset_id: str
    user_id: str
    permanent: bool = False


@dataclass
class DeleteAssetResult:
    """Result of delete asset command."""
    result: Dict[str, str]


class DeleteAssetHandler:
    """Handler for DeleteAssetCommand."""

    def __init__(self, service: AssetsService):
        self._service = service

    async def handle(self, command: DeleteAssetCommand) -> DeleteAssetResult:
        """Execute delete asset command."""
        result = await self._service.delete_asset(
            command.asset_id,
            command.user_id,
            command.permanent
        )
        return DeleteAssetResult(result=result)


# ==========================================
# Command 4: Increment Asset Usage
# ==========================================

@dataclass
class IncrementAssetUsageCommand:
    """Command to increment asset usage count."""
    asset_id: str
    user_id: str


@dataclass
class IncrementAssetUsageResult:
    """Result of increment asset usage command."""
    usage_count: int


class IncrementAssetUsageHandler:
    """Handler for IncrementAssetUsageCommand."""

    def __init__(self, service: AssetsService):
        self._service = service

    async def handle(self, command: IncrementAssetUsageCommand) -> IncrementAssetUsageResult:
        """Execute increment asset usage command."""
        usage_count = await self._service.increment_asset_usage(
            command.asset_id,
            command.user_id
        )
        return IncrementAssetUsageResult(usage_count=usage_count)


# ==========================================
# Command 5: Restore Asset
# ==========================================

@dataclass
class RestoreAssetCommand:
    """Command to restore soft-deleted asset."""
    asset_id: str
    user_id: str


@dataclass
class RestoreAssetResult:
    """Result of restore asset command."""
    asset: Dict[str, Any]


class RestoreAssetHandler:
    """Handler for RestoreAssetCommand."""

    def __init__(self, service: AssetsService):
        self._service = service

    async def handle(self, command: RestoreAssetCommand) -> RestoreAssetResult:
        """Execute restore asset command."""
        asset = await self._service.restore_asset(
            command.asset_id,
            command.user_id
        )
        return RestoreAssetResult(asset=asset)
