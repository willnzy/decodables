"""
Projects Router
Handles project-related API endpoints

@module routers/projects

Endpoints:
- GET /api/projects - List user projects
- GET /api/projects/deleted - List deleted projects
- GET /api/projects/dashboard - Dashboard view
- GET /api/projects/seller-stats - Seller statistics
- POST /api/projects - Create project
- GET /api/projects/{project_id} - Get project details
- PUT /api/projects/{project_id} - Update project
- DELETE /api/projects/{project_id} - Delete project
- POST /api/projects/{project_id}/restore - Restore deleted project
- POST /api/projects/{project_id}/duplicate - Duplicate project
"""

from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from pydantic import BaseModel
from dependencies import get_current_user
from services.db_service import (
    get_user_projects, get_project_detail, create_project as db_create_project,
    save_project, soft_delete_project, get_marketplace_item,
    can_access_resource, record_listing_usage, count_user_projects, supabase,
    get_dashboard_projects, get_seller_project_stats, permanently_hide_project,
    get_user_deleted_projects, user_restore_project, duplicate_project, log_activity
)
from services.rate_limiter import limiter
from timezone_utils import get_request_timezone

router = APIRouter(prefix="/api/projects", tags=["projects"])


# Request Models
class ProjectCreate(BaseModel):
    title: Optional[str] = None
    canvas_data: Optional[dict] = None


class ProjectUpdate(BaseModel):
    canvas_data: Optional[dict] = None
    thumbnail_url: Optional[str] = None
    title: Optional[str] = None
    used_listing_ids: Optional[List[str]] = None


# Routes
@router.get("")
def list_projects(page: int = 1, limit: int = 20, search: str = None, user: dict = Depends(get_current_user)):
    """
    Get user's projects with pagination (PRD v3.2).
    
    Args:
        page: Page number (default: 1)
        limit: Items per page (default: 20)
        search: Search query to filter projects by title (optional)
    
    Returns:
        Projects list with pagination info
        Note: Projects exceeding tier limit may be read-only
    """
    print(f"[API] list_projects called: page={page}, limit={limit}, search={search}, user_id={user['id']}")
    
    items = get_user_projects(user["id"], page, limit, search)
    print(f"[API] get_user_projects returned {len(items) if items else 0} items")
    
    # Calculate total count using COUNT query (accurate for all cases)
    total_count = count_user_projects(user["id"], search)
    print(f"[API] count_user_projects returned total: {total_count}")
    
    result = {
        "items": items, 
        "total": total_count,  # Return accurate total count
        "page": page
    }
    print(f"[API] Returning result: {len(items) if items else 0} items, total: {total_count}, page: {page}")
    return result


@router.get("/dashboard")
def dashboard_projects(
    view: str = Query("all", regex="^(all|bought|selling)$"),
    page: int = 1, 
    limit: int = 20, 
    search: str = None,
    include_canvas: bool = True,
    user: dict = Depends(get_current_user)
):
    """
    Get projects for dashboard with view type filtering (PRD v3.3).
    
    Args:
        view: View type - "all" (default), "bought", or "selling"
        page: Page number (default: 1)
        limit: Items per page (default: 20)
        search: Search query to filter projects by title (optional)
        include_canvas: Whether to include canvas_data (default: true)
    
    Returns:
        Projects list with:
        - items: Array of projects with marketplace_listing info
        - total: Total count for current view
        - page: Current page
        - view_type: Current view type
        
    View Types:
        - all: Shows all projects (created + bought + selling)
        - bought: Only purchased projects (read-only)
        - selling: Only projects with active marketplace listings
    """
    print(f"[API] dashboard_projects: view={view}, page={page}, search={search}")
    
    result = get_dashboard_projects(
        user_id=user["id"],
        view_type=view,
        page=page,
        limit=limit,
        search=search,
        include_canvas_data=include_canvas
    )
    
    return result


@router.get("/deleted")
def list_deleted_projects(
    page: int = 1,
    limit: int = 20,
    user: dict = Depends(get_current_user)
):
    """
    Retrieve the user's deleted projects.
    
    Args:
        page: Page number (default: 1)
        limit: Items per page (default: 20)
    
    Returns:
        List of deleted projects that can be restored
    """
    return get_user_deleted_projects(user["id"], page, limit)


@router.get("/seller-stats")
def get_project_seller_stats(user: dict = Depends(get_current_user)):
    """
    Get seller statistics for projects (PRD v3.3).
    
    Returns:
        Dict with:
        - total_selling: Number of active project listings
        - total_sales: Total number of sales across all listings
        - unique_buyers: Total unique buyers
        - total_revenue: Total credits earned from sales
        - total_usage: Total usage count across all listings
    """
    return get_seller_project_stats(user["id"])


@router.post("")
def create_project(request: Request, req: ProjectCreate, user: dict = Depends(get_current_user)):
    """
    Create a new project (PRD v3.2).
    
    - Checks project limit based on tier:
      - Free: 1 project
      - Starter: 20 projects
      - Pro: 200 projects
    
    Returns:
        Created project
    
    Raises:
        HTTPException: 403 if project limit reached
    """
    # Get current project count (use COUNT query for accuracy)
    current_count = count_user_projects(user["id"])
    
    # Get max projects for tier (PRD v3.2)
    # Normalize tier to lowercase to handle case variations
    tier_limits = {
        "free": 1,
        "starter": 20,
        "pro": 200
    }
    user_tier = (user.get("tier") or "free").lower()
    max_projects = tier_limits.get(user_tier, 1)
    
    if current_count >= max_projects:
        raise HTTPException(
            403,
            f"You have reached the maximum number of projects ({max_projects}). "
            f"Please upgrade to create more projects."
        )
    
    # v3.9: Get timezone from request for snapshot
    tz = get_request_timezone(request, user_id=user.get("id"))
    return db_create_project(user["id"], req.title, req.canvas_data, timezone=tz)


@router.get("/{project_id}")
def get_project(project_id: str, user: dict = Depends(get_current_user)):
    """
    Get single project details.
    
    Raises:
        HTTPException: 404 if project not found
    
    Returns:
        Project details
    """
    project = get_project_detail(project_id, user["id"])
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.put("/{project_id}")
def update_project(project_id: str, req: ProjectUpdate, user: dict = Depends(get_current_user)):
    """
    Save/update project (PRD v3.2).
    
    - Free  7：7，
    - ：，
    - Save Project does NOT charge credits
    - Validates access to referenced listings
    - Records listing usage for usage_count
    
    Returns:
        Updated project with locked_elements info
    
    Raises:
        HTTPException: 403 if Free user trial expired or project limit exceeded
    """
    # Check Free user 7-day trial period (PRD v3.2)
    # Normalize tier to lowercase for consistent comparison
    user_tier = (user.get("tier") or "").lower()
    if user_tier == "free":
        created_at = user.get("created_at")
        if created_at:
            try:
                # Parse created_at (handle both ISO format and string)
                if isinstance(created_at, str):
                    # Remove 'Z' and add timezone if needed
                    created_at_str = created_at.replace('Z', '+00:00')
                    registration_date = datetime.fromisoformat(created_at_str)
                else:
                    registration_date = created_at
                
                # Ensure timezone-aware
                if registration_date.tzinfo is None:
                    registration_date = registration_date.replace(tzinfo=timezone.utc)
                
                now = datetime.now(timezone.utc)
                days_since_registration = (now - registration_date).total_seconds() / (24 * 3600)
                
                if days_since_registration > 7:
                    raise HTTPException(
                        403,
                        "Your 7-day trial period has expired. Please upgrade to continue editing projects."
                    )
            except (ValueError, TypeError) as e:
                # If date parsing fails, log but don't block (graceful degradation)
                print(f"Warning: Failed to parse created_at for user {user['id']}: {e}")
    
    # Check project limit for downgraded users (PRD v3.2)
    tier_limits = {
        "free": 1,
        "starter": 20,
        "pro": 200
    }
    # Normalize tier to lowercase to handle case variations
    user_tier = (user.get("tier") or "free").lower()
    max_projects = tier_limits.get(user_tier, 1)
    
    # Use COUNT query for accurate count
    current_count = count_user_projects(user["id"])
    
    # If user has more projects than allowed, check if this project is within limit
    if current_count > max_projects:
        # Get all projects for sorting (only if needed for limit check)
        existing_projects = get_user_projects(user["id"], page=1, limit=1000)
        # Get project creation order (by created_at)
        # Projects without created_at are treated as oldest (use empty string which sorts first)
        # This ensures they are included in allowed projects (safer default)
        sorted_projects = sorted(
            existing_projects,
            key=lambda p: p.get("created_at", "") or ""
        )
        allowed_projects = sorted_projects[:max_projects]
        allowed_project_ids = {p["id"] for p in allowed_projects}
        
        if project_id not in allowed_project_ids:
            raise HTTPException(
                403,
                f"You have exceeded the project limit for your current plan ({max_projects}). "
                f"This project is read-only. Please upgrade to edit it."
            )
    
    locked_elements = []
    new_usage_recorded = []
    
    # Validate listing access if new listings are referenced
    if req.used_listing_ids:
        for listing_id in req.used_listing_ids:
            listing = get_marketplace_item(listing_id, user["id"])
            
            if listing:
                allowed_tiers = listing.get("allowed_tiers", ["free"])
                if not can_access_resource(user, allowed_tiers):
                    locked_elements.append({
                        "listing_id": listing_id,
                        "title": listing.get("title", "Unknown"),
                        "reason": "Upgrade required to access this resource"
                    })
                else:
                    # Record usage (deduplicated)
                    is_new = record_listing_usage(listing_id, user["id"], project_id)
                    if is_new:
                        new_usage_recorded.append(listing_id)
    
    # Save project
    save_project(project_id, user["id"], req.canvas_data, req.thumbnail_url, req.title)
    
    # Update locked elements flag
    if locked_elements:
        supabase.table("projects").update({
            "contains_locked_elements": True
        }).eq("id", project_id).execute()
    
    return {
        "status": "saved",
        "locked_elements": locked_elements,
        "new_usage_recorded": new_usage_recorded
    }


@router.delete("/{project_id}")
def delete_project(project_id: str, permanent: bool = False, user: dict = Depends(get_current_user)):
    """
    Delete a project (PRD v3.3).
    
    Args:
        project_id: Project ID to delete
        permanent: If true, permanently hides from trash (stage 2 delete)
                   If false, soft delete to trash (stage 1 delete)
    
    Stage 1 (permanent=false):
        - Sets is_deleted=true, deleted_at=now()
        - Project appears in trash for 30 days
        - Can be restored
    
    Stage 2 (permanent=true):
        - Sets is_hidden_from_trash=true
        - Project no longer visible to user
        - Data retained in database
    
    Raises:
        HTTPException: 404 if project not found
    
    Returns:
        Deletion status with stage info
    """
    if permanent:
        # Stage 2: Permanently hide from trash
        try:
            result = permanently_hide_project(project_id, user["id"])
            if not result:
                raise HTTPException(404, "Project not found or not in trash")
            return {"status": "permanently_hidden", "stage": 2}
        except Exception as e:
            raise HTTPException(404, str(e))
    else:
        # Stage 1: Soft delete to trash
        result = soft_delete_project(project_id, user["id"])
        if not result:
            raise HTTPException(404, "Project not found")
        return {"status": "deleted", "stage": 1}


@router.post("/{project_id}/restore")
def restore_project(project_id: str, user: dict = Depends(get_current_user)):
    """
    Restore a deleted project (PRD v3.3).
    
    Allows a user to restore their own deleted project from trash.
    
    Args:
        project_id: Project ID to restore
    
    Returns:
        Restored project details
    
    Raises:
        HTTPException: 404 if project not found
        HTTPException: 400 if restore fails
    """
    try:
        project = user_restore_project(project_id, user["id"])
        if project:
            log_activity(user["id"], "restore_project", {"project_id": project_id})
            return {"status": "ok", "project": project}
        else:
            raise HTTPException(status_code=404, detail="Project not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/duplicate")
@limiter.limit("10/minute")
def duplicate_project_endpoint(request: Request, project_id: str, user: dict = Depends(get_current_user)):
    """
    Duplicate/Copy a project (PRD v3.2).
    
    - Own projects: Creates copy with title + " copied"
    - Purchased projects: Creates copy with same title, preserves source info
    
    Args:
        project_id: Project ID to duplicate
    
    Returns:
        New duplicated project
    
    Raises:
        HTTPException: 400 if duplication fails
        HTTPException: 500 if copy fails
    """
    try:
        # v3.9: Get timezone from request for snapshot
        tz = get_request_timezone(request, user_id=user.get("id"))
        new_project = duplicate_project(project_id, user["id"], timezone=tz)
        if new_project:
            log_activity(user["id"], "duplicate_project", {"source_project_id": project_id, "new_project_id": new_project["id"]})
            return new_project
        else:
            raise HTTPException(500, "Failed to copy project")
    except Exception as e:
        error_msg = str(e)
        raise HTTPException(400, error_msg)

