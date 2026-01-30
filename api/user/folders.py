"""
Folders Router - Folder management endpoints (v3.33)

@module api.user.folders
@version 1.0.0 (created for v3.33 Workspace + Tag Phase 2.6)

Endpoints:
- GET /api/v2/user/folders?type=project - Get user's folders
- POST /api/v2/user/folders - Create a folder
- PATCH /api/v2/user/folders/{folder_id} - Update a folder
- DELETE /api/v2/user/folders/{folder_id} - Delete a folder
- POST /api/v2/user/folders/reorder - Reorder folders
"""

import re
from typing import Optional, List

from fastapi import APIRouter, Request, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from domains.folder.entities import FolderColor, FolderType
from infrastructure.logging.activity_logger import log_activity_async
from infrastructure.rate_limiter import limiter
from dependencies import get_current_user_with_workspace, UserWithWorkspace
from container import get_container

router = APIRouter(prefix="/folders", tags=["user-folders-v1"])


# ==========================================
# Constants
# ==========================================

UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE
)

VALID_COLORS = {"slate", "red", "orange", "amber", "emerald", "cyan", "blue", "violet"}
VALID_TYPES = {"project", "asset"}


def validate_uuid(value: str, field_name: str = "ID") -> None:
    """Validate that a value is a valid UUID format."""
    if not UUID_PATTERN.match(value):
        raise HTTPException(400, f"Invalid {field_name} format")


# ==========================================
# Request/Response Models
# ==========================================

class CreateFolderRequest(BaseModel):
    folder_type: str = Field(..., pattern=r"^(project|asset)$")
    name: str = Field(..., min_length=1, max_length=100)
    color: Optional[str] = Field(
        default="slate",
        pattern=r"^(slate|red|orange|amber|emerald|cyan|blue|violet)$"
    )


class UpdateFolderRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    color: Optional[str] = Field(
        default=None,
        pattern=r"^(slate|red|orange|amber|emerald|cyan|blue|violet)$"
    )


class ReorderFoldersRequest(BaseModel):
    folder_type: str = Field(..., pattern=r"^(project|asset)$")
    folder_ids: List[str] = Field(..., min_length=1)


class FolderPreviewItemResponse(BaseModel):
    id: str
    thumbnailUrl: Optional[str] = None


class FolderResponse(BaseModel):
    id: str
    workspace_id: str
    folder_type: str
    name: str
    color: str
    sort_order: int
    item_count: int = 0
    # v3.34: Counts for Bought/Selling tab filtering
    bought_count: int = 0
    selling_count: int = 0
    # v3.37: Preview items for folder thumbnail grid
    preview_items: List[FolderPreviewItemResponse] = []


class FolderListResponse(BaseModel):
    items: List[FolderResponse]
    total: int


# ==========================================
# Folder CRUD Endpoints
# ==========================================

@router.get("")
@limiter.limit("60/minute")
async def list_folders(
    request: Request,
    folder_type: str = Query(..., pattern=r"^(project|asset)$"),
    ctx: UserWithWorkspace = Depends(get_current_user_with_workspace)
):
    """
    Get user's folders.

    Query Parameters:
        - folder_type: "project" or "asset" (required)

    Returns:
        FolderListResponse with items, total, and per-folder counts:
        - item_count: total items in folder
        - bought_count: items with is_purchased=True
        - selling_count: items with active marketplace listings

    v3.34: Now includes bought_count and selling_count for Bought/Selling tab filtering.
    """
    container = get_container()
    folder_service = await container.get_folder_service()

    ft = FolderType.from_str(folder_type)
    # v3.34: Use list_folders_with_counts to include bought/selling counts
    folders = await folder_service.list_folders_with_counts(
        ctx.workspace_id,
        ft,
        ctx.user_id,
    )

    return {
        "items": [folder.to_dict() for folder in folders],
        "total": len(folders)
    }


@router.post("")
@limiter.limit("30/minute")
async def create_folder(
    request: Request,
    data: CreateFolderRequest,
    ctx: UserWithWorkspace = Depends(get_current_user_with_workspace)
):
    """
    Create a new folder.

    Returns:
        Created folder
    """
    container = get_container()
    folder_service = await container.get_folder_service()

    try:
        ft = FolderType.from_str(data.folder_type)
        fc = FolderColor.from_str(data.color) if data.color else FolderColor.SLATE

        folder = await folder_service.create_folder(
            workspace_id=ctx.workspace_id,
            folder_type=ft,
            name=data.name,
            created_by=ctx.user_id,
            color=fc,
        )

        await log_activity_async(
            user_id=ctx.user_id,
            action="folder_created",
            metadata={"folder_id": folder.id, "name": folder.name, "type": data.folder_type}
        )

        return folder.to_dict()

    except ValueError as e:
        raise HTTPException(400, str(e))


@router.patch("/{folder_id}")
@limiter.limit("30/minute")
async def update_folder(
    request: Request,
    folder_id: str,
    data: UpdateFolderRequest,
    ctx: UserWithWorkspace = Depends(get_current_user_with_workspace)
):
    """
    Update an existing folder.

    Returns:
        Updated folder
    """
    validate_uuid(folder_id, "folder_id")

    container = get_container()
    folder_service = await container.get_folder_service()

    # Verify ownership via workspace
    if not await folder_service.validate_folder_access(folder_id, ctx.workspace_id):
        raise HTTPException(404, "Folder not found")

    try:
        color = FolderColor.from_str(data.color) if data.color else None

        updated = await folder_service.update_folder(
            folder_id=folder_id,
            name=data.name,
            color=color,
            workspace_id=ctx.workspace_id,
        )

        if not updated:
            raise HTTPException(404, "Folder not found")

        return updated.to_dict()

    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/{folder_id}")
@limiter.limit("30/minute")
async def delete_folder(
    request: Request,
    folder_id: str,
    ctx: UserWithWorkspace = Depends(get_current_user_with_workspace)
):
    """
    Delete a folder.

    Note: Items in the folder will be moved to root (no folder).

    Returns:
        Success message
    """
    validate_uuid(folder_id, "folder_id")

    container = get_container()
    folder_service = await container.get_folder_service()

    # Verify ownership via workspace
    if not await folder_service.validate_folder_access(folder_id, ctx.workspace_id):
        raise HTTPException(404, "Folder not found")

    # Get folder name for logging before deletion
    folder = await folder_service.get_folder(folder_id)
    folder_name = folder.name if folder else "unknown"

    success = await folder_service.delete_folder(folder_id, workspace_id=ctx.workspace_id)

    if not success:
        raise HTTPException(500, "Failed to delete folder")

    await log_activity_async(
        user_id=ctx.user_id,
        action="folder_deleted",
        metadata={"folder_id": folder_id, "name": folder_name}
    )

    return {"success": True, "message": "Folder deleted"}


@router.post("/reorder")
@limiter.limit("30/minute")
async def reorder_folders(
    request: Request,
    data: ReorderFoldersRequest,
    ctx: UserWithWorkspace = Depends(get_current_user_with_workspace)
):
    """
    Reorder folders within a workspace.

    Returns:
        Success message
    """
    # Validate all folder IDs
    for folder_id in data.folder_ids:
        validate_uuid(folder_id, "folder_id")

    container = get_container()
    folder_service = await container.get_folder_service()

    # Verify all folders belong to user's workspace
    for folder_id in data.folder_ids:
        if not await folder_service.validate_folder_access(folder_id, ctx.workspace_id):
            raise HTTPException(400, f"Folder {folder_id} not found or not accessible")

    ft = FolderType.from_str(data.folder_type)

    success = await folder_service.reorder_folders(
        workspace_id=ctx.workspace_id,
        folder_type=ft,
        folder_ids=data.folder_ids,
    )

    if not success:
        raise HTTPException(500, "Failed to reorder folders")

    return {"success": True, "message": "Folders reordered"}
