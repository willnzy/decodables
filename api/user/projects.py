"""
Projects API - Project management endpoints.

@module api.user.projects
@version 1.0.0

Endpoints:
- GET /api/v2/user/projects - List user projects
- GET /api/v2/user/projects/dashboard - Dashboard view
- GET /api/v2/user/projects/deleted - List deleted projects
- GET /api/v2/user/projects/seller-stats - Seller statistics
- POST /api/v2/user/projects - Create project
- GET /api/v2/user/projects/{id} - Get project details
- PUT /api/v2/user/projects/{id} - Update project
- DELETE /api/v2/user/projects/{id} - Delete project
- POST /api/v2/user/projects/{id}/restore - Restore deleted project
- POST /api/v2/user/projects/{id}/duplicate - Duplicate project
"""

import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from dependencies import get_current_user
from container import get_container
from infrastructure.rate_limiter import limiter

from application.commands.creation import (
    CreateProjectCommand,
    UpdateProjectCommand,
    DeleteProjectCommand,
)
from application.queries.creation import (
    GetProjectQuery,
    GetUserProjectsQuery,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["user-projects-v2"])


# ==========================================
# Request/Response Models
# ==========================================

class ProjectCreateRequest(BaseModel):
    """Request to create a project."""
    title: Optional[str] = None
    canvas_data: Optional[Dict[str, Any]] = None


class ProjectUpdateRequest(BaseModel):
    """Request to update a project."""
    canvas_data: Optional[Dict[str, Any]] = None
    thumbnail_url: Optional[str] = None
    title: Optional[str] = None
    used_listing_ids: Optional[List[str]] = None


class ProjectResponse(BaseModel):
    """Single project response."""
    id: str
    user_id: str
    title: str
    thumbnail_url: Optional[str] = None
    canvas_data: Optional[Dict[str, Any]] = None
    status: str = "active"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        extra = "allow"


class ProjectListResponse(BaseModel):
    """Project list response."""
    items: List[Dict[str, Any]]
    total: int
    page: int


class ProjectDeleteResponse(BaseModel):
    """Project delete response."""
    status: str
    stage: int = 1


class ProjectRestoreResponse(BaseModel):
    """Project restore response."""
    status: str
    project: Optional[Dict[str, Any]] = None


# ==========================================
# Endpoints
# ==========================================

@router.get("")
async def list_projects(
    page: int = Query(1, ge=1),
    limit: int = Query(6, ge=1, le=100),
    search: Optional[str] = None,
    include_canvas_data: bool = True,
    user: dict = Depends(get_current_user),
) -> ProjectListResponse:
    """
    Get user's projects with pagination.

    Compatible with legacy /api/projects response format.

    Args:
        page: Page number (default: 1)
        limit: Items per page (default: 6)
        search: Search query to filter by title
        include_canvas_data: Whether to include canvas_data

    Returns:
        ProjectListResponse with items, total, page
    """
    container = get_container()
    handler = container.get_user_projects_handler

    offset = (page - 1) * limit

    query = GetUserProjectsQuery(
        user_id=user["id"],
        limit=limit,
        offset=offset,
    )

    result = await handler.handle(query)

    if not result.success:
        logger.error(f"Failed to get projects for user {user['id']}: {result.error}")
        raise HTTPException(500, "Failed to get projects")

    # Filter by search if provided
    items = result.projects_list
    if search:
        search_lower = search.lower()
        items = [p for p in items if search_lower in (p.get("title") or "").lower()]

    # Optionally exclude canvas_data for lighter response
    if not include_canvas_data:
        items = [{k: v for k, v in p.items() if k != "canvas_data"} for p in items]

    return ProjectListResponse(
        items=items,
        total=result.total_count,
        page=page,
    )


@router.get("/dashboard")
async def dashboard_projects(
    view: str = Query("all", pattern="^(all|bought|selling)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    include_canvas: bool = True,
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get projects for dashboard with view type filtering.

    Args:
        view: View type - "all" (default), "bought", or "selling"
        page: Page number
        limit: Items per page
        search: Search query
        include_canvas: Whether to include canvas_data

    Returns:
        Projects list with view info
    """
    from services.db_service import get_dashboard_projects

    result = get_dashboard_projects(
        user_id=user["id"],
        view_type=view,
        page=page,
        limit=limit,
        search=search,
        include_canvas_data=include_canvas,
    )

    return result


@router.get("/deleted")
async def list_deleted_projects(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Retrieve the user's deleted projects.

    Returns:
        List of deleted projects that can be restored
    """
    from services.db_service import get_user_deleted_projects

    return get_user_deleted_projects(user["id"], page, limit)


@router.get("/seller-stats")
async def get_project_seller_stats(
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get seller statistics for projects.

    Returns:
        Dict with total_selling, total_sales, unique_buyers, etc.
    """
    from services.db_service import get_seller_project_stats

    return get_seller_project_stats(user["id"])


@router.post("")
@limiter.limit("20/minute")
async def create_project(
    request: Request,
    req: ProjectCreateRequest,
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Create a new project.

    Checks project limit based on tier:
    - Free: 1 project
    - Starter: 20 projects
    - Pro: 200 projects

    Returns:
        Created project
    """
    container = get_container()
    handler = container.create_project_handler

    tier = (user.get("tier") or "free").lower()

    command = CreateProjectCommand(
        user_id=user["id"],
        title=req.title or "Untitled",
        canvas_data=req.canvas_data,
        tier=tier,
    )

    result = await handler.handle(command)

    if not result.success:
        if "limit" in (result.error or "").lower():
            raise HTTPException(403, result.error)
        raise HTTPException(400, result.error or "Failed to create project")

    return result.project_dict


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get single project details.

    Only owner can access the project.

    Returns:
        Project details
    """
    container = get_container()
    handler = container.get_project_handler

    query = GetProjectQuery(
        project_id=project_id,
        user_id=user["id"],
    )

    result = await handler.handle(query)

    if not result.success:
        if "not found" in (result.error or "").lower():
            raise HTTPException(404, "Project not found")
        if "access" in (result.error or "").lower():
            raise HTTPException(403, "Access denied")
        raise HTTPException(400, result.error or "Failed to get project")

    return result.project_dict


@router.put("/{project_id}")
async def update_project(
    project_id: str,
    req: ProjectUpdateRequest,
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Update a project.

    Validates:
    - User is owner
    - Project is within tier limit
    - Free user trial period

    Returns:
        Update status with locked_elements info
    """
    container = get_container()
    handler = container.update_project_handler

    command = UpdateProjectCommand(
        project_id=project_id,
        user_id=user["id"],
        title=req.title,
        canvas_data=req.canvas_data,
        thumbnail_url=req.thumbnail_url,
    )

    result = await handler.handle(command)

    if not result.success:
        if "not found" in (result.error or "").lower():
            raise HTTPException(404, "Project not found")
        if "access" in (result.error or "").lower() or "limit" in (result.error or "").lower():
            raise HTTPException(403, result.error)
        raise HTTPException(400, result.error or "Failed to update project")

    return {
        "status": "saved",
        "locked_elements": [],
        "usage_recorded": [],
    }


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    permanent: bool = False,
    user: dict = Depends(get_current_user),
) -> ProjectDeleteResponse:
    """
    Delete a project.

    Args:
        project_id: Project ID to delete
        permanent: If true, permanently hides from trash (stage 2)
                   If false, soft delete to trash (stage 1)

    Returns:
        Deletion status with stage info
    """
    container = get_container()
    handler = container.delete_project_handler

    command = DeleteProjectCommand(
        project_id=project_id,
        user_id=user["id"],
        permanent=permanent,
    )

    result = await handler.handle(command)

    if not result.success:
        if "not found" in (result.error or "").lower():
            raise HTTPException(404, "Project not found")
        raise HTTPException(400, result.error or "Failed to delete project")

    status = "permanently_hidden" if permanent else "deleted"
    stage = 2 if permanent else 1

    return ProjectDeleteResponse(status=status, stage=stage)


@router.post("/{project_id}/restore")
async def restore_project(
    project_id: str,
    user: dict = Depends(get_current_user),
) -> ProjectRestoreResponse:
    """
    Restore a deleted project from trash.

    Returns:
        Restored project details
    """
    container = get_container()
    creation_service = container.creation_service

    try:
        result = await creation_service.restore_project(
            project_id=project_id,
            user_id=user["id"],
        )

        if not result.success:
            if "not found" in (result.error or "").lower():
                raise HTTPException(404, "Project not found")
            raise HTTPException(400, result.error or "Failed to restore project")

        return ProjectRestoreResponse(
            status="ok",
            project=result.project.to_dict() if result.project else None,
        )

    except Exception as e:
        logger.error(f"Failed to restore project {project_id}: {e}")
        raise HTTPException(400, str(e))


@router.post("/{project_id}/duplicate")
@limiter.limit("10/minute")
async def duplicate_project(
    request: Request,
    project_id: str,
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Duplicate a project.

    Creates a copy of the project with title + " (Copy)".

    Returns:
        New duplicated project
    """
    container = get_container()
    creation_service = container.creation_service

    tier = (user.get("tier") or "free").lower()

    try:
        result = await creation_service.duplicate_project(
            project_id=project_id,
            user_id=user["id"],
            tier=tier,
        )

        if not result.success:
            if "limit" in (result.error or "").lower():
                raise HTTPException(403, result.error)
            if "not found" in (result.error or "").lower():
                raise HTTPException(404, "Project not found")
            raise HTTPException(400, result.error or "Failed to duplicate project")

        return result.project.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to duplicate project {project_id}: {e}")
        raise HTTPException(500, "Failed to duplicate project")
