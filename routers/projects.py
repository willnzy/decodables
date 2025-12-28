"""
Projects Router
Handles project-related API endpoints

@module routers/projects
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from dependencies import get_current_user
from db_service import (
    get_user_projects, get_project_detail, create_project as db_create_project,
    save_project, soft_delete_project, get_marketplace_item,
    can_access_resource, record_listing_usage, supabase
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
def list_projects(page: int = 1, limit: int = 20, user: dict = Depends(get_current_user)):
    """
    Get user's projects with pagination.
    
    Returns:
        Projects list with pagination info
    """
    items = get_user_projects(user["id"], page, limit)
    return {"items": items, "total": len(items), "page": page}


@router.post("")
def create_project(req: ProjectCreate, user: dict = Depends(get_current_user)):
    """
    Create a new project.
    
    Returns:
        Created project
    """
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
    
    - Save Project does NOT charge credits
    - Validates access to referenced listings
    - Records listing usage for usage_count
    
    Returns:
        Updated project with locked_elements info
    """
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

