"""
Projects API - Project management endpoints.

@module api.user.projects
@version 1.2.0 (Container DI Migration)

Changes:
- v1.2.0: Container DI Migration
  - Migrated audit logging to use Container's admin_audit_service
  - Removed direct get_async_db_client() calls
  - Removed direct infrastructure.repositories imports
  - Architecture: API → Container → Service → Repository
- v1.1.0: API Consolidation Phase 3
  - REMOVED: GET /api/v2/user/projects/seller-stats (use /seller/stats?include=projects)
- v1.0.0: Initial version
- v3.31: 添加重试机制处理 Supabase 临时故障

Endpoints:
- GET /api/v2/user/projects - List user projects
- GET /api/v2/user/projects/dashboard - Dashboard view
- GET /api/v2/user/projects/deleted - List deleted projects
- GET /api/v2/user/projects/starred - List starred projects (v3.33)
- GET /api/v2/user/projects/folder/{folder_id} - List projects in folder (v3.33)
- POST /api/v2/user/projects - Create project
- GET /api/v2/user/projects/{id} - Get project details
- PUT /api/v2/user/projects/{id} - Update project
- DELETE /api/v2/user/projects/{id} - Delete project
- POST /api/v2/user/projects/{id}/restore - Restore deleted project
- POST /api/v2/user/projects/{id}/duplicate - Duplicate project
- POST /api/v2/user/projects/{id}/move - Move project to folder (v3.33)
- POST /api/v2/user/projects/{id}/star - Toggle star status (v3.33)
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from domains.identity.aggregates.user_profile import UserProfile
from dependencies import get_current_user, get_current_user_with_workspace, UserWithWorkspace
from container import get_container
from infrastructure.rate_limiter import limiter

# v3.31: 重试配置
MAX_RETRIES = 2
RETRY_DELAY = 1.0  # 秒

from application.commands.creation import (
    CreateProjectCommand,
    UpdateProjectCommand,
    DeleteProjectCommand,
    RestoreProjectCommand,
)
from application.queries.creation import (
    GetProjectQuery,
    GetUserProjectsQuery,
    GetDashboardProjectsQuery,
)
from domains.creation.exceptions import (
    ProjectNotFoundException,
    ProjectAccessDeniedException,
    ProjectLimitExceededException,
    InvalidProjectDataException,
)
from core.utils.validation import (
    validate_canvas_data,
    validate_thumbnail_url,
    validate_title,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["user-projects-v2"])


# ==========================================
# Request/Response Models
# ==========================================

class ProjectCreateRequest(BaseModel):
    """
    Request to create a project.

    v1.1.0: Added idempotency_key for safe retry support.
    """
    title: Optional[str] = Field(None, max_length=200)  # P2-030: DoS protection
    canvas_data: Optional[Dict[str, Any]] = None  # JSON size limited at DB layer
    # v1.1.0: Idempotency key - client-generated UUID for safe retries
    # If provided, server returns existing project if already created with this key
    idempotency_key: Optional[str] = Field(None, max_length=64, pattern=r'^[a-zA-Z0-9\-_]+$')


class ProjectUpdateRequest(BaseModel):
    """Request to update a project."""
    canvas_data: Optional[Dict[str, Any]] = None  # JSON size limited at DB layer
    thumbnail_url: Optional[str] = Field(None, max_length=500)  # P2-030: DoS protection
    title: Optional[str] = Field(None, max_length=200)  # P2-030: DoS protection
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
    """
    Project list response (DDD compliant).

    P1-002 fix: Migrated from page-based to offset-based pagination.
    """
    items: List[Dict[str, Any]]
    total: int
    offset: int
    limit: int


class ProjectDeleteResponse(BaseModel):
    """Project delete response."""
    status: str
    stage: int = 1


class ProjectRestoreResponse(BaseModel):
    """Project restore response."""
    status: str
    project: Optional[Dict[str, Any]] = None


class ViewTypeCounts(BaseModel):
    """Counts for each view type tab."""
    all: int = 0
    bought: int = 0
    selling: int = 0


class DashboardProjectsResponse(BaseModel):
    """Dashboard projects response (P2-002)."""
    items: List[Dict[str, Any]]
    total: int
    offset: int
    limit: int
    view: str
    counts: Optional[ViewTypeCounts] = None

    class Config:
        extra = "allow"


class ProjectUpdateResponse(BaseModel):
    """Project update response (P2-002)."""
    status: str
    locked_elements: List[str] = []
    usage_recorded: List[str] = []


# ==========================================
# Endpoints
# ==========================================

@router.get("")
async def list_projects(
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(6, ge=1, le=100, description="Number of records to return (1-100)"),
    search: Optional[str] = None,
    include_canvas_data: bool = True,
    ctx: UserWithWorkspace = Depends(get_current_user_with_workspace),
) -> ProjectListResponse:
    """
    Get user's projects with pagination.

    P1-002 fix: Migrated from page-based to offset-based pagination (DDD compliant).
    v3.33: Now uses UserWithWorkspace for automatic workspace creation.

    Args:
        offset: Number of records to skip (default: 0)
        limit: Number of records to return (default: 6, max: 100)
        search: Search query to filter by title
        include_canvas_data: Whether to include canvas_data

    Returns:
        ProjectListResponse with items, total, offset, limit
    """
    container = get_container()
    handler = await container.get_user_projects_handler()

    query = GetUserProjectsQuery(
        user_id=ctx.user_id,
        limit=limit,
        offset=offset,
    )

    result = await handler.handle(query)

    if not result.success:
        logger.error(f"Failed to get projects for user {ctx.user_id}: {result.error}")
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
        offset=offset,
        limit=limit,
    )


@router.get("/dashboard")
async def dashboard_projects(
    view: str = Query("all", pattern="^(all|bought|selling)$"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of records to return (1-100)"),
    search: Optional[str] = None,
    include_canvas: bool = True,
    ctx: UserWithWorkspace = Depends(get_current_user_with_workspace),
) -> DashboardProjectsResponse:
    """
    Get projects for dashboard with view type filtering.

    P1-002 fix: Migrated from page-based to offset-based pagination (DDD compliant).
    P2-002 fix: Return Pydantic model instead of Dict[str, Any].
    v3.31: 添加重试机制处理 Supabase 临时故障 (502/503)
    v3.33: Now uses UserWithWorkspace for automatic workspace creation.

    Args:
        view: View type - "all" (default), "bought", or "selling"
        offset: Number of records to skip (default: 0)
        limit: Number of records to return (default: 20, max: 100)
        search: Search query
        include_canvas: Whether to include canvas_data

    Returns:
        DashboardProjectsResponse with projects list and view info
    """
    container = get_container()
    handler = await container.get_dashboard_projects_handler()

    query = GetDashboardProjectsQuery(
        user_id=ctx.user_id,
        view_type=view,
        offset=offset,
        limit=limit,
        search=search,
        include_canvas_data=include_canvas,
    )

    # v3.31: 添加重试机制处理 Supabase 临时故障
    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        result = await handler.handle(query)

        if result.success:
            # P2-002: Return Pydantic model with counts for tab badges
            counts_data = result.data.get("counts")
            counts = ViewTypeCounts(**counts_data) if counts_data else None
            return DashboardProjectsResponse(
                items=result.data.get("items", []),
                total=result.data.get("total", 0),
                offset=result.data.get("offset", offset),
                limit=result.data.get("limit", limit),
                view=view,
                counts=counts,
            )

        # 检查是否为可重试的错误 (502, 503, 网络错误)
        error_str = str(result.error).lower() if result.error else ""
        is_retryable = any([
            "502" in error_str,
            "503" in error_str,
            "bad gateway" in error_str,
            "service unavailable" in error_str,
            "cloudflare" in error_str,
            "internal server error" in error_str,
        ])

        if is_retryable and attempt < MAX_RETRIES:
            logger.warning(
                f"Retrying dashboard_projects (attempt {attempt + 1}/{MAX_RETRIES}) "
                f"for user {ctx.user_id}: {result.error}"
            )
            await asyncio.sleep(RETRY_DELAY * (attempt + 1))  # 指数退避
            last_error = result.error
            continue
        else:
            last_error = result.error
            break

    logger.error(f"Failed to get dashboard projects for user {ctx.user_id}: {last_error}")
    raise HTTPException(500, "Failed to get dashboard projects")


@router.get("/deleted")
async def list_deleted_projects(
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of records to return (1-100)"),
    ctx: UserWithWorkspace = Depends(get_current_user_with_workspace),
) -> ProjectListResponse:
    """
    Retrieve the user's deleted projects.

    P1-002 fix: Migrated to offset-based pagination.
    P2-002 fix: Return Pydantic model instead of Dict[str, Any].
    P2-003 fix: Fixed bug using 'page' instead of 'offset' in response.
    v3.33: Now uses UserWithWorkspace for automatic workspace creation.

    Returns:
        ProjectListResponse with deleted projects that can be restored
    """
    container = get_container()
    creation_service = await container.get_creation_service()

    # Note: get_user_deleted_projects returns tuple (items, total)
    items, total = await creation_service.get_user_deleted_projects(
        user_id=ctx.user_id,
        limit=limit,
        offset=offset,
    )

    # P2-002: Return Pydantic model
    # P2-003: Fixed bug - use 'offset' instead of 'page'
    return ProjectListResponse(
        items=items,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post("")
@limiter.limit("20/minute")
async def create_project(
    request: Request,
    req: ProjectCreateRequest,
    ctx: UserWithWorkspace = Depends(get_current_user_with_workspace),
) -> ProjectResponse:
    """
    Create a new project.

    Checks project limit based on tier:
    - Free: 1 project
    - Starter: 20 projects
    - Pro: 200 projects

    P2-002 fix: Return Pydantic model instead of Dict[str, Any].
    v3.33: Now uses UserWithWorkspace for automatic workspace creation.

    Returns:
        ProjectResponse with created project details
    """
    # Validate title
    is_valid, error = validate_title(req.title)
    if not is_valid:
        raise HTTPException(400, f"Invalid title: {error}")

    # Validate canvas_data for XSS/injection
    is_valid, error = validate_canvas_data(req.canvas_data)
    if not is_valid:
        raise HTTPException(400, f"Invalid canvas data: {error}")

    container = get_container()
    handler = await container.get_create_project_handler()

    # UserProfile.tier is UserTier enum, get string value
    tier = (ctx.user.tier.value if ctx.user.tier else "t1").lower()

    command = CreateProjectCommand(
        user_id=ctx.user_id,
        title=req.title or "Untitled",
        canvas_data=req.canvas_data,
        tier=tier,
        idempotency_key=req.idempotency_key,  # v1.1.0: Idempotency support
    )

    result = await handler.handle(command)

    if not result.success:
        if isinstance(result.exception, ProjectLimitExceededException):
            raise HTTPException(403, result.error)
        if isinstance(result.exception, InvalidProjectDataException):
            raise HTTPException(400, result.error)
        raise HTTPException(400, result.error or "Failed to create project")

    # P2-002: Return Pydantic model
    return ProjectResponse(**result.project_dict)


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    ctx: UserWithWorkspace = Depends(get_current_user_with_workspace),
) -> ProjectResponse:
    """
    Get single project details.

    Only owner can access the project.

    P2-002 fix: Return Pydantic model instead of Dict[str, Any].
    v3.33: Now uses UserWithWorkspace for automatic workspace creation.

    Returns:
        ProjectResponse with project details
    """
    container = get_container()
    handler = await container.get_project_handler()

    query = GetProjectQuery(
        project_id=project_id,
        user_id=ctx.user_id,
    )

    result = await handler.handle(query)

    if not result.success:
        if isinstance(result.exception, ProjectNotFoundException):
            raise HTTPException(404, "Project not found")
        if isinstance(result.exception, ProjectAccessDeniedException):
            raise HTTPException(403, "Access denied")
        raise HTTPException(400, result.error or "Failed to get project")

    # P2-002: Return Pydantic model
    return ProjectResponse(**result.project_dict)


@router.put("/{project_id}")
async def update_project(
    project_id: str,
    req: ProjectUpdateRequest,
    ctx: UserWithWorkspace = Depends(get_current_user_with_workspace),
) -> ProjectUpdateResponse:
    """
    Update a project.

    Validates:
    - User is owner
    - Project is within tier limit
    - Free user trial period

    P2-002 fix: Return Pydantic model instead of Dict[str, Any].
    v3.33: Now uses UserWithWorkspace for automatic workspace creation.

    Returns:
        ProjectUpdateResponse with update status and locked_elements info
    """
    # Validate title if provided
    is_valid, error = validate_title(req.title)
    if not is_valid:
        raise HTTPException(400, f"Invalid title: {error}")

    # Validate canvas_data for XSS/injection
    is_valid, error = validate_canvas_data(req.canvas_data)
    if not is_valid:
        raise HTTPException(400, f"Invalid canvas data: {error}")

    # Validate thumbnail_url to prevent SSRF
    is_valid, error = validate_thumbnail_url(req.thumbnail_url)
    if not is_valid:
        raise HTTPException(400, f"Invalid thumbnail URL: {error}")

    container = get_container()
    handler = await container.get_update_project_handler()

    command = UpdateProjectCommand(
        project_id=project_id,
        user_id=ctx.user_id,
        title=req.title,
        canvas_data=req.canvas_data,
        thumbnail_url=req.thumbnail_url,
        user_tier=ctx.user.tier or "t1",  # P1-013: For locked elements check
    )

    result = await handler.handle(command)

    if not result.success:
        if isinstance(result.exception, ProjectNotFoundException):
            raise HTTPException(404, "Project not found")
        if isinstance(result.exception, (ProjectAccessDeniedException, ProjectLimitExceededException)):
            raise HTTPException(403, result.error)
        raise HTTPException(400, result.error or "Failed to update project")

    # P2-002: Return Pydantic model
    return ProjectUpdateResponse(
        status="saved",
        locked_elements=[],
        usage_recorded=[],
    )


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    permanent: bool = False,
    ctx: UserWithWorkspace = Depends(get_current_user_with_workspace),
) -> ProjectDeleteResponse:
    """
    Delete a project.

    v3.33: Now uses UserWithWorkspace for automatic workspace creation.

    Args:
        project_id: Project ID to delete
        permanent: If true, permanently hides from trash (stage 2)
                   If false, soft delete to trash (stage 1)

    Returns:
        Deletion status with stage info
    """
    container = get_container()
    handler = await container.get_delete_project_handler()

    command = DeleteProjectCommand(
        project_id=project_id,
        user_id=ctx.user_id,
        permanent=permanent,
    )

    result = await handler.handle(command)

    if not result.success:
        if isinstance(result.exception, ProjectNotFoundException):
            raise HTTPException(404, "Project not found")
        if isinstance(result.exception, ProjectAccessDeniedException):
            raise HTTPException(403, "Access denied")
        raise HTTPException(400, result.error or "Failed to delete project")

    # ✅ v1.2.0: Audit logging via Container (DI migration)
    try:
        admin_audit = await container.get_admin_audit_service()
        await admin_audit.admin_log_operation(
            admin_id=ctx.user_id,  # User deleting their own project
            operation_type="project_delete_permanent" if permanent else "project_delete_soft",
            target_type="project",
            target_id=project_id,
            details=f"Project deletion ({'permanent' if permanent else 'soft delete'})",
            source="api",
        )
    except Exception as e:
        logger.warning(f"Failed to log project deletion: {e}")
        # Don't fail the operation if logging fails

    status = "permanently_hidden" if permanent else "deleted"
    stage = 2 if permanent else 1

    return ProjectDeleteResponse(status=status, stage=stage)


@router.post("/{project_id}/restore")
async def restore_project(
    project_id: str,
    ctx: UserWithWorkspace = Depends(get_current_user_with_workspace),
) -> ProjectRestoreResponse:
    """
    Restore a deleted project from trash.

    v3.33: Now uses UserWithWorkspace for automatic workspace creation.

    Returns:
        Restored project details
    """
    container = get_container()
    handler = await container.get_restore_project_handler()

    command = RestoreProjectCommand(
        project_id=project_id,
        user_id=ctx.user_id,
    )

    result = await handler.handle(command)

    if not result.success:
        if isinstance(result.exception, ProjectNotFoundException):
            raise HTTPException(404, "Project not found")
        if isinstance(result.exception, ProjectAccessDeniedException):
            raise HTTPException(403, "Access denied")
        logger.error(f"Failed to restore project {project_id}: {result.error}")
        raise HTTPException(400, result.error or "Failed to restore project")

    # ✅ v1.2.0: Audit logging via Container (DI migration)
    try:
        admin_audit = await container.get_admin_audit_service()
        await admin_audit.admin_log_operation(
            admin_id=ctx.user_id,
            operation_type="project_restore",
            target_type="project",
            target_id=project_id,
            details="Project restored from soft delete",
            source="api",
        )
    except Exception as e:
        logger.warning(f"Failed to log project restoration: {e}")
        # Don't fail the operation if logging fails

    return ProjectRestoreResponse(
        status="ok",
        project=result.project_dict,
    )


@router.post("/{project_id}/duplicate")
@limiter.limit("10/minute")
async def duplicate_project(
    request: Request,
    project_id: str,
    ctx: UserWithWorkspace = Depends(get_current_user_with_workspace),
) -> ProjectResponse:
    """
    Duplicate a project.

    Creates a copy of the project with title + " (Copy)".

    P2-002 fix: Return Pydantic model instead of Dict[str, Any].
    v3.33: Now uses UserWithWorkspace for automatic workspace creation.

    Returns:
        ProjectResponse with new duplicated project
    """
    container = get_container()
    creation_service = await container.get_creation_service()

    # UserProfile.tier is UserTier enum, get string value
    tier = (ctx.user.tier.value if ctx.user.tier else "t1").lower()

    try:
        # Service returns Project directly, not a Result object
        project = await creation_service.duplicate_project(
            project_id=project_id,
            user_id=ctx.user_id,
            tier=tier,
        )

        # P2-002: Return Pydantic model
        return ProjectResponse(**project.to_dict())

    except ProjectLimitExceededException as e:
        raise HTTPException(403, str(e))
    except ProjectNotFoundException:
        raise HTTPException(404, "Project not found")
    except ProjectAccessDeniedException:
        raise HTTPException(403, "Access denied")
    except Exception as e:
        logger.error(f"Failed to duplicate project {project_id}: {e}")
        raise HTTPException(500, "Failed to duplicate project")


# ==========================================
# v3.33 Phase 2.6: Folder and Star Endpoints
# ==========================================

class MoveToFolderRequest(BaseModel):
    """Request to move project to a folder."""
    folder_id: Optional[str] = Field(None, description="Target folder ID (null = move to root)")


class ToggleStarRequest(BaseModel):
    """Request to toggle project star status."""
    is_starred: bool = Field(..., description="New starred status")


class ProjectMoveResponse(BaseModel):
    """Response for move operation."""
    success: bool
    folder_id: Optional[str] = None


class ProjectStarResponse(BaseModel):
    """Response for star operation."""
    success: bool
    is_starred: bool


@router.post("/{project_id}/move")
@limiter.limit("30/minute")
async def move_project_to_folder(
    request: Request,
    project_id: str,
    req: MoveToFolderRequest,
    ctx: UserWithWorkspace = Depends(get_current_user_with_workspace),
) -> ProjectMoveResponse:
    """
    Move project to a folder (or root if folder_id is null).

    v3.33 Phase 2.6: Folder organization support.

    Args:
        project_id: Project ID to move
        req: MoveToFolderRequest with target folder_id

    Returns:
        ProjectMoveResponse with success status
    """
    container = get_container()

    # Validate folder belongs to user's workspace (if not moving to root)
    if req.folder_id:
        folder_service = await container.get_folder_service()
        if not await folder_service.validate_folder_access(req.folder_id, ctx.workspace_id):
            raise HTTPException(404, "Folder not found")

    # Get project repository directly for this operation
    from core.database import get_async_db_client
    from infrastructure.repositories.project_repository import SupabaseProjectRepository

    db = await get_async_db_client()
    repo = SupabaseProjectRepository(db)

    result = await repo.move_to_folder(project_id, ctx.user_id, req.folder_id)

    if not result:
        raise HTTPException(404, "Project not found or access denied")

    return ProjectMoveResponse(success=True, folder_id=req.folder_id)


@router.post("/{project_id}/star")
@limiter.limit("60/minute")
async def toggle_project_star(
    request: Request,
    project_id: str,
    req: ToggleStarRequest,
    ctx: UserWithWorkspace = Depends(get_current_user_with_workspace),
) -> ProjectStarResponse:
    """
    Toggle project starred status.

    v3.33 Phase 2.6: Project starring support.

    Args:
        project_id: Project ID to star/unstar
        req: ToggleStarRequest with is_starred value

    Returns:
        ProjectStarResponse with new starred status
    """
    # Get project repository directly for this operation
    from core.database import get_async_db_client
    from infrastructure.repositories.project_repository import SupabaseProjectRepository

    db = await get_async_db_client()
    repo = SupabaseProjectRepository(db)

    result = await repo.toggle_star(project_id, ctx.user_id, req.is_starred)

    if not result:
        raise HTTPException(404, "Project not found or access denied")

    return ProjectStarResponse(success=True, is_starred=req.is_starred)


@router.get("/folder/{folder_id}")
async def list_projects_by_folder(
    folder_id: str,
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of records to return"),
    search: Optional[str] = None,
    ctx: UserWithWorkspace = Depends(get_current_user_with_workspace),
) -> ProjectListResponse:
    """
    Get projects in a specific folder.

    v3.33 Phase 2.6: Folder filtering support.
    Note: Use folder_id="root" to get unfiled projects.

    Args:
        folder_id: Folder ID (or "root" for unfiled)
        offset: Number of records to skip
        limit: Number of records to return
        search: Optional search query

    Returns:
        ProjectListResponse with projects in the folder
    """
    container = get_container()

    # Handle "root" as unfiled projects
    target_folder_id: Optional[str] = None if folder_id == "root" else folder_id

    # Validate folder belongs to user's workspace (if not root)
    if target_folder_id:
        folder_service = await container.get_folder_service()
        if not await folder_service.validate_folder_access(target_folder_id, ctx.workspace_id):
            raise HTTPException(404, "Folder not found")

    # Get project repository directly for this operation
    from core.database import get_async_db_client
    from infrastructure.repositories.project_repository import SupabaseProjectRepository

    db = await get_async_db_client()
    repo = SupabaseProjectRepository(db)

    items = await repo.get_by_folder(
        user_id=ctx.user_id,
        folder_id=target_folder_id,
        offset=offset,
        limit=limit,
        search=search,
    )

    return ProjectListResponse(
        items=items,
        total=len(items),  # Approximate; exact count would need separate query
        offset=offset,
        limit=limit,
    )


@router.get("/starred")
async def list_starred_projects(
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of records to return"),
    ctx: UserWithWorkspace = Depends(get_current_user_with_workspace),
) -> ProjectListResponse:
    """
    Get starred projects.

    v3.33 Phase 2.6: Starred projects view.

    Args:
        offset: Number of records to skip
        limit: Number of records to return

    Returns:
        ProjectListResponse with starred projects
    """
    # Get project repository directly for this operation
    from core.database import get_async_db_client
    from infrastructure.repositories.project_repository import SupabaseProjectRepository

    db = await get_async_db_client()
    repo = SupabaseProjectRepository(db)

    items = await repo.get_starred(
        user_id=ctx.user_id,
        offset=offset,
        limit=limit,
    )

    return ProjectListResponse(
        items=items,
        total=len(items),  # Approximate; exact count would need separate query
        offset=offset,
        limit=limit,
    )
