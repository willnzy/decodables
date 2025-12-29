"""
Projects Router
Handles project-related API endpoints

@module routers/projects
"""

from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from dependencies import get_current_user
from db_service import (
    get_user_projects, get_project_detail, create_project as db_create_project,
    save_project, soft_delete_project, get_marketplace_item,
    can_access_resource, record_listing_usage, count_user_projects, supabase
)

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


@router.post("")
def create_project(req: ProjectCreate, user: dict = Depends(get_current_user)):
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
    
    return db_create_project(user["id"], req.title, req.canvas_data)


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
    
    - Free 用户 7天游玩期检查：如果注册超过7天，阻止编辑
    - 项目数量限制检查：如果降级后超过限制，阻止编辑
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
def delete_project(project_id: str, user: dict = Depends(get_current_user)):
    """
    Soft delete a project.
    
    Raises:
        HTTPException: 404 if project not found
    
    Returns:
        Deletion status
    """
    result = soft_delete_project(project_id, user["id"])
    if not result:
        raise HTTPException(404, "Project not found")
    return {"status": "deleted"}

