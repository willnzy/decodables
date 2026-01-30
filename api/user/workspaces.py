"""
Workspaces Router - Workspace management endpoints (v3.33)

@module api.user.workspaces
@version 2.0.0 (Phase 2: Multi-workspace support)

Endpoints:
- GET  /api/v2/user/workspaces - List user's workspaces
- POST /api/v2/user/workspaces - Create a new workspace (Phase 2)
- GET  /api/v2/user/workspaces/current - Get current default workspace
- GET  /api/v2/user/workspaces/{workspace_id} - Get workspace by ID
- PATCH /api/v2/user/workspaces/{workspace_id} - Update workspace
- DELETE /api/v2/user/workspaces/{workspace_id} - Delete workspace
"""

from typing import Optional, List

from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel, Field

from domains.identity.aggregates.user_profile import UserProfile
from infrastructure.logging.activity_logger import log_activity_async
from infrastructure.rate_limiter import limiter
from dependencies import get_current_user
from container import get_container
from core.utils.validation import validate_uuid

router = APIRouter(prefix="/workspaces", tags=["user-workspaces-v1"])


# ==========================================
# Constants (WS4: UUID validation centralized to core.utils.validation)
# ==========================================


# ==========================================
# Request/Response Models
# ==========================================

class CreateWorkspaceRequest(BaseModel):
    """Request model for creating a workspace."""
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)


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

    Returns all workspaces owned by the user (default + team).

    Returns:
        WorkspaceListResponse with items and total count
    """
    container = get_container()
    workspace_service = await container.get_workspace_service()

    workspaces = await workspace_service.list_user_workspaces(user.user_id)

    return {
        "items": [ws.to_dict() for ws in workspaces],
        "total": len(workspaces)
    }


@router.post("")
@limiter.limit("10/minute")
async def create_workspace(
    request: Request,
    data: CreateWorkspaceRequest,
    user: UserProfile = Depends(get_current_user)
):
    """
    Create a new team workspace (Phase 2).

    Tier-based quota:
    - Free/Starter: 1 workspace (cannot create additional)
    - Pro: up to 10 workspaces

    Args:
        data: CreateWorkspaceRequest (name, description)

    Returns:
        Created workspace details

    Raises:
        400: Validation error or quota exceeded
    """
    container = get_container()
    workspace_service = await container.get_workspace_service()

    # Get user tier
    user_tier = getattr(user, "tier", "t1") or "t1"

    try:
        workspace = await workspace_service.create_workspace(
            user_id=user.user_id,
            name=data.name,
            description=data.description,
            user_tier=user_tier,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    await log_activity_async(
        user_id=user.user_id,
        action="workspace_created",
        metadata={
            "workspace_id": workspace.id,
            "name": workspace.name,
            "is_personal": workspace.is_personal,
        }
    )

    return workspace.to_dict()


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

    try:
        updated = await workspace_service.update_workspace(
            workspace_id=workspace_id,
            user_id=user.user_id,
            name=data.name,
            description=data.description,
        )
    except PermissionError as e:
        raise HTTPException(403, str(e))

    if not updated:
        raise HTTPException(404, "Workspace not found")

    await log_activity_async(
        user_id=user.user_id,
        action="workspace_updated",
        metadata={
            "workspace_id": workspace_id,
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

    try:
        success = await workspace_service.delete_workspace(
            workspace_id=workspace_id,
            user_id=user.user_id,
        )
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(404, error_msg)
        raise HTTPException(400, error_msg)

    await log_activity_async(
        user_id=user.user_id,
        action="workspace_deleted",
        metadata={"workspace_id": workspace_id}
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

    try:
        stats = await workspace_service.get_workspace_stats(
            workspace_id=workspace_id,
            user_id=user.user_id,
        )
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(404, str(e))

    # Add tag count from tag service
    tag_service = await container.get_tag_service()
    tags = await tag_service.list_tags(workspace_id)
    stats["tag_count"] = len(tags)

    return stats
