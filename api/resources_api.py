"""
Resources API - System resources (stickers, backgrounds, templates).

@module api.resources_api
@version 1.0.0

Endpoints:
- GET /api/v2/resources - List system resources
- GET /api/v2/resources/types - Get resource types
- GET /api/v2/resources/categories/{type} - Get categories for type
- GET /api/v2/resources/stickers - Get stickers
- GET /api/v2/resources/backgrounds - Get backgrounds
- GET /api/v2/resources/{id} - Get single resource
"""

import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from dependencies import get_current_user, optional_user
from services import get_resource_service, ResourceType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/resources", tags=["resources-v2"])


# ==========================================
# Response Models
# ==========================================

class ResourceTypeInfo(BaseModel):
    """Resource type info."""
    id: str
    name: str


class ResourceTypesResponse(BaseModel):
    """Resource types response."""
    types: List[ResourceTypeInfo]


class CategoryInfo(BaseModel):
    """Category info."""
    id: str
    name: str
    count: Optional[int] = None


class CategoriesResponse(BaseModel):
    """Categories response."""
    categories: List[Dict[str, Any]]


class ResourceItem(BaseModel):
    """Resource item."""
    id: str
    type: str
    url: str
    name: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    allowed_tiers: List[str] = ["free"]
    is_locked: bool = False

    class Config:
        extra = "allow"


class ResourcesListResponse(BaseModel):
    """Resources list response."""
    items: List[Dict[str, Any]]
    total: int
    page: int
    has_more: bool = False


# ==========================================
# Endpoints
# ==========================================

@router.get("", response_model=ResourcesListResponse)
async def list_resources(
    type: Optional[str] = Query(None, description="Resource type"),
    category: Optional[str] = Query(None, description="Category filter"),
    tier: Optional[str] = Query(None, description="Tier filter"),
    search: Optional[str] = Query(None, description="Search in name/tags"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    include_locked: bool = Query(True, description="Include locked resources"),
    user: dict = Depends(optional_user),
) -> ResourcesListResponse:
    """
    List system resources with optional filtering.

    Returns resources with access status based on user's tier.
    """
    resource_service = get_resource_service()

    result = resource_service.get_resources(
        user=user,
        resource_type=type,
        category=category,
        allowed_tiers_filter=tier,
        search=search,
        page=page,
        limit=limit,
        include_locked=include_locked,
    )

    items = result.get("items", [])
    total = result.get("total", len(items))

    return ResourcesListResponse(
        items=items,
        total=total,
        page=page,
        has_more=total > page * limit,
    )


@router.get("/types", response_model=ResourceTypesResponse)
async def get_resource_types() -> ResourceTypesResponse:
    """
    Get all available resource types.
    """
    types = [
        ResourceTypeInfo(
            id=rt.value,
            name=rt.value.replace("_", " ").title(),
        )
        for rt in ResourceType
    ]

    return ResourceTypesResponse(types=types)


@router.get("/categories/{resource_type}", response_model=CategoriesResponse)
async def get_categories(resource_type: str) -> CategoriesResponse:
    """
    Get available categories for a resource type.
    """
    resource_service = get_resource_service()
    categories = resource_service.get_categories(resource_type)

    return CategoriesResponse(categories=categories)


@router.get("/stickers")
async def get_stickers(
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    user: dict = Depends(optional_user),
) -> Dict[str, Any]:
    """
    Get stickers for the editor.

    Convenience endpoint that filters by sticker type.
    """
    resource_service = get_resource_service()

    return resource_service.get_stickers(
        user=user,
        category=category,
        page=page,
        limit=limit,
    )


@router.get("/backgrounds")
async def get_backgrounds(
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(optional_user),
) -> Dict[str, Any]:
    """
    Get background images.

    Convenience endpoint that filters by background type.
    """
    resource_service = get_resource_service()

    return resource_service.get_backgrounds(
        user=user,
        category=category,
        page=page,
        limit=limit,
    )


@router.get("/templates")
async def get_templates(
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(optional_user),
) -> Dict[str, Any]:
    """
    Get project templates.

    Convenience endpoint that filters by template/project type.
    """
    resource_service = get_resource_service()

    return resource_service.get_projects(
        user=user,
        category=category,
        page=page,
        limit=limit,
    )


@router.get("/{resource_id}")
async def get_resource(
    resource_id: str,
    user: dict = Depends(optional_user),
) -> Dict[str, Any]:
    """
    Get a single resource by ID.
    """
    resource_service = get_resource_service()
    resource = resource_service.get_resource_by_id(resource_id, user)

    if not resource:
        raise HTTPException(404, "Resource not found")

    return resource
