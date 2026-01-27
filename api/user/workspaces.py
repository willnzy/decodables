"""
Workspaces Router - Workspace management endpoints (v3.33)

@module api.user.workspaces
@version 1.0.0 (created for v3.33 Workspace + Tag Phase 1)

Endpoints:
- GET /api/v2/user/workspaces - List user's workspaces
- GET /api/v2/user/workspaces/current - Get current default workspace
- GET /api/v2/user/workspaces/{workspace_id} - Get workspace by ID
- PATCH /api/v2/user/workspaces/{workspace_id} - Update workspace
- DELETE /api/v2/user/workspaces/{workspace_id} - Delete workspace (Phase 2+)

Phase 1 Scope:
- Users have exactly one default Personal Workspace
- Workspace is auto-created on registration
- Basic CRUD operations supported
- No team/collaboration features yet (Phase 2)
"""

import re
from typing import Optional, List

from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel, Field

from domains.identity.aggregates.user_profile import UserProfile
from infrastructure.logging.activity_logger import log_activity_async
from infrastructure.rate_limiter import limiter
from dependencies import get_current_user
from container import get_container

router = APIRouter(prefix="/workspaces", tags=["user-workspaces-v1"])


# ==========================================
# Constants
# ==========================================

UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE
)


def validate_uuid(value: str, field_name: str = "ID") -> None:
    """Validate that a value is a valid UUID format."""
    if not UUID_PATTERN.match(value):
        raise HTTPException(400, f"Invalid {field_name} format")


# ==========================================
# Request/Response Models
# ==========================================

class UpdateWorkspaceRequest(BaseModel):
    """Request model for updating a workspace."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)


class WorkspaceResponse(BaseModel):
    """Response model for a workspace."""
    id: str
    name: str
    description: Optional[str] = None
    owner_id: str
    is_default: bool
    is_personal: bool
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class WorkspaceListResponse(BaseModel):
    """Response model for workspace list."""
    items: List[WorkspaceResponse]
    total: int


# ==========================================
# Workspace Endpoints
# ==========================================

@router.get("")
@limiter.limit("60/minute")
async def list_workspaces(
    request: Request,
    user: UserProfile = Depends(get_current_user)
):
    """
    List user's workspaces.

    Phase 1: Returns the user's single default workspace.
    Phase 2+: Will return all workspaces user has access to.

    Returns:
        WorkspaceListResponse with items and total count
    """
    container = get_container()
    workspace_service = await container.get_workspace_service()

    # Phase 1: Get or create default workspace
    workspace = await workspace_service.get_or_create_default(user.user_id)

    return {
        "items": [workspace.to_dict()],
        "total": 1
    }


@router.get("/current")
@limiter.limit("60/minute")
async def get_current_workspace(
    request: Request,
    user: UserProfile = Depends(get_current_user)
):
    """
    Get user's current (default) workspace.

    Phase 1: Always returns the user's single default workspace.
    Phase 2+: May support workspace switching.

    Returns:
        Workspace details
    """
    container = get_container()
    workspace_service = await container.get_workspace_service()

    workspace = await workspace_service.get_or_create_default(user.user_id)

    return workspace.to_dict()


@router.get("/{workspace_id}")
@limiter.limit("60/minute")
async def get_workspace(
    request: Request,
    workspace_id: str,
    user: UserProfile = Depends(get_current_user)
):
    """
    Get workspace by ID.

    Args:
        workspace_id: Workspace UUID

    Returns:
        Workspace details

    Raises:
        404: Workspace not found
        403: Not authorized to access workspace
    """
    validate_uuid(workspace_id, "workspace_id")

    container = get_container()
    workspace_service = await container.get_workspace_service()

    workspace = await workspace_service.get_by_id(workspace_id)
    if not workspace:
        raise HTTPException(404, "Workspace not found")

    # Verify ownership
    if workspace.owner_id != user.user_id:
        raise HTTPException(403, "Not authorized to access this workspace")

    return workspace.to_dict()


@router.patch("/{workspace_id}")
@limiter.limit("30/minute")
async def update_workspace(
    request: Request,
    workspace_id: str,
    data: UpdateWorkspaceRequest,
    user: UserProfile = Depends(get_current_user)
):
    """
    Update workspace details.

    Phase 1: Only name and description can be updated.

    Args:
        workspace_id: Workspace UUID
        data: Update data (name, description)

    Returns:
        Updated workspace details

    Raises:
        404: Workspace not found
        403: Not authorized to modify workspace
        400: Invalid request data
    """
    validate_uuid(workspace_id, "workspace_id")

    # Check if any update data provided
    if data.name is None and data.description is None:
        raise HTTPException(400, "No update data provided")

    container = get_container()
    workspace_service = await container.get_workspace_service()

    # Get workspace
    workspace = await workspace_service.get_by_id(workspace_id)
    if not workspace:
        raise HTTPException(404, "Workspace not found")

    # Verify ownership
    if workspace.owner_id != user.user_id:
        raise HTTPException(403, "Not authorized to modify this workspace")

    # Update workspace via repository
    from infrastructure.repositories.workspace_repository import SupabaseWorkspaceRepository
    from core.database import get_async_db_client

    db = await get_async_db_client()
    workspace_repo = SupabaseWorkspaceRepository(db)

    update_data = {}
    if data.name is not None:
        update_data["name"] = data.name
    if data.description is not None:
        update_data["description"] = data.description

    updated = await workspace_repo.update_partial(workspace_id, update_data)

    await log_activity_async(
        user_id=user.user_id,
        action="workspace_updated",
        metadata={
            "workspace_id": workspace_id,
            "updates": list(update_data.keys())
        }
    )

    return updated.to_dict()


@router.delete("/{workspace_id}")
@limiter.limit("10/minute")
async def delete_workspace(
    request: Request,
    workspace_id: str,
    user: UserProfile = Depends(get_current_user)
):
    """
    Delete a workspace.

    Phase 1: Cannot delete the default workspace.
    Phase 2+: Will support deleting non-default workspaces.

    Args:
        workspace_id: Workspace UUID

    Returns:
        Success message

    Raises:
        404: Workspace not found
        403: Not authorized to delete workspace
        400: Cannot delete default workspace
    """
    validate_uuid(workspace_id, "workspace_id")

    container = get_container()
    workspace_service = await container.get_workspace_service()

    workspace = await workspace_service.get_by_id(workspace_id)
    if not workspace:
        raise HTTPException(404, "Workspace not found")

    # Verify ownership
    if workspace.owner_id != user.user_id:
        raise HTTPException(403, "Not authorized to delete this workspace")

    # Phase 1: Cannot delete default workspace
    if workspace.is_default:
        raise HTTPException(400, "Cannot delete default workspace")

    # Delete via repository
    from infrastructure.repositories.workspace_repository import SupabaseWorkspaceRepository
    from core.database import get_async_db_client

    db = await get_async_db_client()
    workspace_repo = SupabaseWorkspaceRepository(db)
    await workspace_repo.delete(workspace_id)

    await log_activity_async(
        user_id=user.user_id,
        action="workspace_deleted",
        metadata={"workspace_id": workspace_id, "name": workspace.name}
    )

    return {"success": True, "message": "Workspace deleted"}


@router.get("/{workspace_id}/stats")
@limiter.limit("30/minute")
async def get_workspace_stats(
    request: Request,
    workspace_id: str,
    user: UserProfile = Depends(get_current_user)
):
    """
    Get workspace statistics.

    Returns counts for:
    - Total tags
    - Total projects
    - Total assets

    Args:
        workspace_id: Workspace UUID

    Returns:
        Workspace statistics

    Raises:
        404: Workspace not found
        403: Not authorized to access workspace
    """
    validate_uuid(workspace_id, "workspace_id")

    container = get_container()
    workspace_service = await container.get_workspace_service()

    workspace = await workspace_service.get_by_id(workspace_id)
    if not workspace:
        raise HTTPException(404, "Workspace not found")

    # Verify ownership
    if workspace.owner_id != user.user_id:
        raise HTTPException(403, "Not authorized to access this workspace")

    # Get tag count
    tag_service = await container.get_tag_service()
    tags = await tag_service.list_tags(workspace_id)

    # TODO: Add project and asset counts when those services are integrated
    # For now, return placeholder values that will be filled in later

    return {
        "workspace_id": workspace_id,
        "tag_count": len(tags),
        "project_count": 0,  # TODO: Integrate with projects service
        "asset_count": 0,    # TODO: Integrate with assets service
    }
