"""
Resources Router
API endpoints for system resources (projects, stickers, assets)

@module routers/resources
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel

from dependencies import get_current_user, require_admin, optional_user
from services import get_resource_service, ResourceType, ResourceCategory


router = APIRouter(prefix="/api/resources", tags=["resources"])


# ==========================================
# Request/Response Models
# ==========================================

class ResourceCreateRequest(BaseModel):
    """Request model for creating a resource"""
    type: str
    url: str
    category: Optional[str] = None
    name: Optional[str] = None
    tags: Optional[List[str]] = None
    allowed_tiers: Optional[List[str]] = ["free"]
    metadata: Optional[dict] = None


class ResourceUpdateRequest(BaseModel):
    """Request model for updating a resource"""
    category: Optional[str] = None
    name: Optional[str] = None
    tags: Optional[List[str]] = None
    allowed_tiers: Optional[List[str]] = None
    metadata: Optional[dict] = None


class BulkImportRequest(BaseModel):
    """Request model for bulk import"""
    resources: List[ResourceCreateRequest]


# ==========================================
# Public Endpoints
# ==========================================

@router.get("")
async def list_resources(
    type: Optional[str] = Query(None, description="Resource type (project, sticker, image, etc.)"),
    category: Optional[str] = Query(None, description="Category filter"),
    tier: Optional[str] = Query(None, description="Tier filter (free, starter, pro)"),
    search: Optional[str] = Query(None, description="Search in name/tags"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    include_locked: bool = Query(True, description="Include resources user cannot access"),
    user: dict = Depends(optional_user)
):
    """
    List system resources with optional filtering.
    Returns resources with access status based on user's tier.
    """
    resource_service = get_resource_service()
    
    return resource_service.get_resources(
        user=user,
        resource_type=type,
        category=category,
        allowed_tiers_filter=tier,
        search=search,
        page=page,
        limit=limit,
        include_locked=include_locked
    )


@router.get("/types")
async def get_resource_types():
    """
    Get all available resource types.
    """
    return {
        "types": [
            {
                "id": rt.value,
                "name": rt.value.replace("_", " ").title(),
            }
            for rt in ResourceType
        ]
    }


@router.get("/categories/{resource_type}")
async def get_categories(resource_type: str):
    """
    Get available categories for a resource type.
    """
    resource_service = get_resource_service()
    categories = resource_service.get_categories(resource_type)
    
    return {"categories": categories}


@router.get("/stickers")
async def get_stickers(
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    user: dict = Depends(optional_user)
):
    """
    Get stickers for the editor.
    Convenience endpoint that filters by sticker type.
    """
    resource_service = get_resource_service()
    
    return resource_service.get_stickers(
        user=user,
        category=category,
        page=page,
        limit=limit
    )


@router.get("/projects")
async def get_projects(
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(optional_user)
):
    """
    Get marketplace projects.
    Convenience endpoint that filters by project type.
    """
    resource_service = get_resource_service()
    
    return resource_service.get_projects(
        user=user,
        category=category,
        page=page,
        limit=limit
    )


@router.get("/backgrounds")
async def get_backgrounds(
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(optional_user)
):
    """
    Get background images.
    Convenience endpoint that filters by background type.
    """
    resource_service = get_resource_service()
    
    return resource_service.get_backgrounds(
        user=user,
        category=category,
        page=page,
        limit=limit
    )


@router.get("/{resource_id}")
async def get_resource(
    resource_id: str,
    user: dict = Depends(optional_user)
):
    """
    Get a single resource by ID.
    """
    resource_service = get_resource_service()
    resource = resource_service.get_resource_by_id(resource_id, user)
    
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    return resource


# ==========================================
# Admin Endpoints
# ==========================================

@router.get("/admin/stats")
async def get_resource_stats(
    admin: dict = Depends(require_admin)
):
    """
    Get resource statistics (admin only).
    """
    resource_service = get_resource_service()
    return resource_service.get_resource_stats()


@router.post("/admin")
async def create_resource(
    request: ResourceCreateRequest,
    admin: dict = Depends(require_admin)
):
    """
    Create a new system resource (admin only).
    """
    resource_service = get_resource_service()
    
    # Validate type
    try:
        ResourceType(request.type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid resource type. Valid types: {[t.value for t in ResourceType]}"
        )
    
    resource = resource_service.create_resource(
        resource_type=request.type,
        url=request.url,
        category=request.category,
        name=request.name,
        tags=request.tags,
        allowed_tiers=request.allowed_tiers,
        metadata=request.metadata,
    )
    
    return resource


@router.put("/admin/{resource_id}")
async def update_resource(
    resource_id: str,
    request: ResourceUpdateRequest,
    admin: dict = Depends(require_admin)
):
    """
    Update a system resource (admin only).
    """
    resource_service = get_resource_service()
    
    updates = request.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    resource = resource_service.update_resource(resource_id, updates)
    
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    return resource


@router.delete("/admin/{resource_id}")
async def delete_resource(
    resource_id: str,
    admin: dict = Depends(require_admin)
):
    """
    Delete a system resource (admin only).
    """
    resource_service = get_resource_service()
    success = resource_service.delete_resource(resource_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    return {"success": True}


@router.post("/admin/bulk-import")
async def bulk_import_resources(
    request: BulkImportRequest,
    admin: dict = Depends(require_admin)
):
    """
    Bulk import resources (admin only).
    """
    resource_service = get_resource_service()
    
    resources = [r.model_dump() for r in request.resources]
    result = resource_service.bulk_import_resources(resources)
    
    return result

