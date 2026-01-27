"""
Tags Router - Tag management endpoints (v3.33)

@module api.user.tags
@version 1.0.0 (created for v3.33 Workspace + Tag Phase 1)

Endpoints:
- GET /api/v2/user/tags - Get user's tags
- POST /api/v2/user/tags - Create a tag
- PATCH /api/v2/user/tags/{tag_id} - Update a tag
- DELETE /api/v2/user/tags/{tag_id} - Delete a tag
- GET /api/v2/user/tags/presets - Get tag group presets

Project Tags:
- GET /api/v2/user/projects/{project_id}/tags - Get project tags
- POST /api/v2/user/projects/{project_id}/tags - Add tags to project
- PUT /api/v2/user/projects/{project_id}/tags - Set project tags (replace)
- DELETE /api/v2/user/projects/{project_id}/tags/{tag_id} - Remove tag from project

Asset Tags:
- GET /api/v2/user/assets/{asset_id}/tags - Get asset tags
- POST /api/v2/user/assets/{asset_id}/tags - Add tags to asset
- PUT /api/v2/user/assets/{asset_id}/tags - Set asset tags (replace)
- DELETE /api/v2/user/assets/{asset_id}/tags/{tag_id} - Remove tag from asset
"""

import re
from typing import Optional, List

from fastapi import APIRouter, Request, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from domains.identity.aggregates.user_profile import UserProfile
from domains.tag.entities import TagColor
from infrastructure.logging.activity_logger import log_activity
from infrastructure.rate_limiter import limiter
from dependencies import get_current_user, get_current_user_with_workspace, UserWithWorkspace
from container import get_container

router = APIRouter(prefix="/tags", tags=["user-tags-v1"])

# Also create routers for project and asset tags
project_tags_router = APIRouter(tags=["user-project-tags-v1"])
asset_tags_router = APIRouter(tags=["user-asset-tags-v1"])


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

class CreateTagRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    color: str = Field(default="gray", pattern=r"^(gray|red|orange|yellow|green|blue|purple|pink)$")
    group_name: Optional[str] = Field(default=None, max_length=50)
    icon: Optional[str] = Field(default=None, max_length=10)


class UpdateTagRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    color: Optional[str] = Field(default=None, pattern=r"^(gray|red|orange|yellow|green|blue|purple|pink)$")
    group_name: Optional[str] = Field(default=None, max_length=50)
    icon: Optional[str] = Field(default=None, max_length=10)


class AddTagsRequest(BaseModel):
    tag_ids: List[str] = Field(..., min_length=1)


class SetTagsRequest(BaseModel):
    tag_ids: List[str] = Field(default_factory=list)


class TagResponse(BaseModel):
    id: str
    name: str
    color: str
    icon: Optional[str] = None
    group_name: Optional[str] = None
    sort_order: int = 0
    usage_count: int = 0


class TagListResponse(BaseModel):
    items: List[TagResponse]
    total: int


class TagGroupPresetResponse(BaseModel):
    id: str
    group_name: str
    display_name: str
    description: Optional[str]
    icon: Optional[str]
    preset_tags: List[dict]
    is_default: bool


# ==========================================
# Tag CRUD Endpoints
# ==========================================

@router.get("")
@limiter.limit("60/minute")
async def list_tags(
    request: Request,
    group_name: Optional[str] = None,
    ctx: UserWithWorkspace = Depends(get_current_user_with_workspace)
):
    """
    Get user's tags.

    v3.33: Now uses UserWithWorkspace for automatic workspace creation.

    Query Parameters:
        - group_name: Optional filter by group

    Returns:
        TagListResponse with items and total
    """
    container = get_container()
    tag_service = await container.get_tag_service()

    # Get tags using workspace_id from context
    tags = await tag_service.list_tags(ctx.workspace_id, group_name)

    return {
        "items": [tag.to_dict() for tag in tags],
        "total": len(tags)
    }


@router.get("/by-group")
@limiter.limit("60/minute")
async def list_tags_by_group(
    request: Request,
    ctx: UserWithWorkspace = Depends(get_current_user_with_workspace)
):
    """
    Get tags organized by group.

    v3.33: Now uses UserWithWorkspace for automatic workspace creation.

    Returns:
        Dict mapping group_name to list of tags
    """
    container = get_container()
    tag_service = await container.get_tag_service()

    groups = await tag_service.get_tags_by_group(ctx.workspace_id)

    return {
        group: [tag.to_dict() for tag in tags]
        for group, tags in groups.items()
    }


@router.post("")
@limiter.limit("30/minute")
async def create_tag(
    request: Request,
    data: CreateTagRequest,
    ctx: UserWithWorkspace = Depends(get_current_user_with_workspace)
):
    """
    Create a new tag.

    v3.33: Now uses UserWithWorkspace for automatic workspace creation.

    Returns:
        Created tag
    """
    container = get_container()
    tag_service = await container.get_tag_service()

    try:
        tag = await tag_service.create_tag(
            workspace_id=ctx.workspace_id,
            name=data.name,
            color=TagColor.from_str(data.color),
            created_by=ctx.user_id,
            group_name=data.group_name,
            icon=data.icon,
        )

        log_activity(
            user_id=ctx.user_id,
            action="tag_created",
            details={"tag_id": tag.id, "name": tag.name}
        )

        return tag.to_dict()

    except ValueError as e:
        raise HTTPException(400, str(e))


@router.patch("/{tag_id}")
@limiter.limit("30/minute")
async def update_tag(
    request: Request,
    tag_id: str,
    data: UpdateTagRequest,
    ctx: UserWithWorkspace = Depends(get_current_user_with_workspace)
):
    """
    Update an existing tag.

    v3.33: Now uses UserWithWorkspace for automatic workspace creation.

    Returns:
        Updated tag
    """
    validate_uuid(tag_id, "tag_id")

    container = get_container()
    workspace_service = await container.get_workspace_service()
    tag_service = await container.get_tag_service()

    # Verify ownership
    tag = await tag_service.get_tag(tag_id)
    if not tag:
        raise HTTPException(404, "Tag not found")

    # Check that user owns the workspace
    is_owner = await workspace_service.validate_ownership(tag.workspace_id, ctx.user_id)
    if not is_owner:
        raise HTTPException(403, "Not authorized to modify this tag")

    try:
        updated = await tag_service.update_tag(
            tag_id=tag_id,
            name=data.name,
            color=TagColor.from_str(data.color) if data.color else None,
            icon=data.icon,
            group_name=data.group_name,
        )

        return updated.to_dict()

    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/{tag_id}")
@limiter.limit("30/minute")
async def delete_tag(
    request: Request,
    tag_id: str,
    ctx: UserWithWorkspace = Depends(get_current_user_with_workspace)
):
    """
    Delete a tag.

    v3.33: Now uses UserWithWorkspace for automatic workspace creation.

    Returns:
        Success message
    """
    validate_uuid(tag_id, "tag_id")

    container = get_container()
    workspace_service = await container.get_workspace_service()
    tag_service = await container.get_tag_service()

    # Verify ownership
    tag = await tag_service.get_tag(tag_id)
    if not tag:
        raise HTTPException(404, "Tag not found")

    is_owner = await workspace_service.validate_ownership(tag.workspace_id, ctx.user_id)
    if not is_owner:
        raise HTTPException(403, "Not authorized to delete this tag")

    await tag_service.delete_tag(tag_id)

    log_activity(
        user_id=ctx.user_id,
        action="tag_deleted",
        details={"tag_id": tag_id, "name": tag.name}
    )

    return {"success": True, "message": "Tag deleted"}


@router.get("/presets")
@limiter.limit("60/minute")
async def list_presets(
    request: Request,
    ctx: UserWithWorkspace = Depends(get_current_user_with_workspace)
):
    """
    Get available tag group presets.

    v3.33: Now uses UserWithWorkspace for automatic workspace creation.

    Returns:
        List of tag group presets
    """
    container = get_container()
    tag_service = await container.get_tag_service()

    presets = await tag_service.get_all_presets()

    return {
        "items": [preset.to_dict() for preset in presets]
    }


# ==========================================
# Project Tag Endpoints
# ==========================================

@project_tags_router.get("/projects/{project_id}/tags")
@limiter.limit("60/minute")
async def get_project_tags(
    request: Request,
    project_id: str,
    ctx: UserWithWorkspace = Depends(get_current_user_with_workspace)
):
    """
    Get tags for a project.

    v3.33: Now uses UserWithWorkspace for automatic workspace creation.

    Returns:
        List of tags
    """
    validate_uuid(project_id, "project_id")

    container = get_container()
    project_tag_service = await container.get_project_tag_service()

    tags = await project_tag_service.get_project_tags(project_id)

    return {
        "items": [tag.to_dict() for tag in tags]
    }


@project_tags_router.post("/projects/{project_id}/tags")
@limiter.limit("30/minute")
async def add_project_tags(
    request: Request,
    project_id: str,
    data: AddTagsRequest,
    ctx: UserWithWorkspace = Depends(get_current_user_with_workspace)
):
    """
    Add tags to a project.

    v3.33: Now uses UserWithWorkspace for automatic workspace creation.

    Returns:
        Updated list of project tags
    """
    validate_uuid(project_id, "project_id")
    for tag_id in data.tag_ids:
        validate_uuid(tag_id, "tag_id")

    container = get_container()
    project_tag_service = await container.get_project_tag_service()

    try:
        tags = await project_tag_service.add_tags(
            project_id=project_id,
            tag_ids=data.tag_ids,
            user_id=ctx.user_id
        )

        return {
            "items": [tag.to_dict() for tag in tags]
        }

    except ValueError as e:
        raise HTTPException(400, str(e))


@project_tags_router.put("/projects/{project_id}/tags")
@limiter.limit("30/minute")
async def set_project_tags(
    request: Request,
    project_id: str,
    data: SetTagsRequest,
    ctx: UserWithWorkspace = Depends(get_current_user_with_workspace)
):
    """
    Set project tags (replace all existing).

    v3.33: Now uses UserWithWorkspace for automatic workspace creation.

    Returns:
        Updated list of project tags
    """
    validate_uuid(project_id, "project_id")
    for tag_id in data.tag_ids:
        validate_uuid(tag_id, "tag_id")

    container = get_container()
    project_tag_service = await container.get_project_tag_service()

    try:
        tags = await project_tag_service.set_tags(
            project_id=project_id,
            tag_ids=data.tag_ids,
            user_id=ctx.user_id
        )

        return {
            "items": [tag.to_dict() for tag in tags]
        }

    except ValueError as e:
        raise HTTPException(400, str(e))


@project_tags_router.delete("/projects/{project_id}/tags/{tag_id}")
@limiter.limit("30/minute")
async def remove_project_tag(
    request: Request,
    project_id: str,
    tag_id: str,
    ctx: UserWithWorkspace = Depends(get_current_user_with_workspace)
):
    """
    Remove a tag from a project.

    v3.33: Now uses UserWithWorkspace for automatic workspace creation.

    Returns:
        Success message
    """
    validate_uuid(project_id, "project_id")
    validate_uuid(tag_id, "tag_id")

    container = get_container()
    project_tag_service = await container.get_project_tag_service()

    await project_tag_service.remove_tag(project_id, tag_id)

    return {"success": True, "message": "Tag removed from project"}


# ==========================================
# Asset Tag Endpoints
# ==========================================

@asset_tags_router.get("/assets/{asset_id}/tags")
@limiter.limit("60/minute")
async def get_asset_tags(
    request: Request,
    asset_id: str,
    ctx: UserWithWorkspace = Depends(get_current_user_with_workspace)
):
    """
    Get tags for an asset.

    v3.33: Now uses UserWithWorkspace for automatic workspace creation.

    Returns:
        List of tags
    """
    validate_uuid(asset_id, "asset_id")

    container = get_container()
    asset_tag_service = await container.get_asset_tag_service()

    tags = await asset_tag_service.get_asset_tags(asset_id)

    return {
        "items": [tag.to_dict() for tag in tags]
    }


@asset_tags_router.post("/assets/{asset_id}/tags")
@limiter.limit("30/minute")
async def add_asset_tags(
    request: Request,
    asset_id: str,
    data: AddTagsRequest,
    ctx: UserWithWorkspace = Depends(get_current_user_with_workspace)
):
    """
    Add tags to an asset.

    v3.33: Now uses UserWithWorkspace for automatic workspace creation.

    Returns:
        Updated list of asset tags
    """
    validate_uuid(asset_id, "asset_id")
    for tag_id in data.tag_ids:
        validate_uuid(tag_id, "tag_id")

    container = get_container()
    asset_tag_service = await container.get_asset_tag_service()

    try:
        tags = await asset_tag_service.add_tags(
            asset_id=asset_id,
            tag_ids=data.tag_ids,
            user_id=ctx.user_id,
            source="manual"
        )

        return {
            "items": [tag.to_dict() for tag in tags]
        }

    except ValueError as e:
        raise HTTPException(400, str(e))


@asset_tags_router.put("/assets/{asset_id}/tags")
@limiter.limit("30/minute")
async def set_asset_tags(
    request: Request,
    asset_id: str,
    data: SetTagsRequest,
    ctx: UserWithWorkspace = Depends(get_current_user_with_workspace)
):
    """
    Set asset tags (replace all existing).

    v3.33: Now uses UserWithWorkspace for automatic workspace creation.

    Returns:
        Updated list of asset tags
    """
    validate_uuid(asset_id, "asset_id")
    for tag_id in data.tag_ids:
        validate_uuid(tag_id, "tag_id")

    container = get_container()
    asset_tag_service = await container.get_asset_tag_service()

    try:
        tags = await asset_tag_service.set_tags(
            asset_id=asset_id,
            tag_ids=data.tag_ids,
            user_id=ctx.user_id,
            source="manual"
        )

        return {
            "items": [tag.to_dict() for tag in tags]
        }

    except ValueError as e:
        raise HTTPException(400, str(e))


@asset_tags_router.delete("/assets/{asset_id}/tags/{tag_id}")
@limiter.limit("30/minute")
async def remove_asset_tag(
    request: Request,
    asset_id: str,
    tag_id: str,
    ctx: UserWithWorkspace = Depends(get_current_user_with_workspace)
):
    """
    Remove a tag from an asset.

    v3.33: Now uses UserWithWorkspace for automatic workspace creation.

    Returns:
        Success message
    """
    validate_uuid(asset_id, "asset_id")
    validate_uuid(tag_id, "tag_id")

    container = get_container()
    asset_tag_service = await container.get_asset_tag_service()

    await asset_tag_service.remove_tag(asset_id, tag_id)

    return {"success": True, "message": "Tag removed from asset"}
