"""
Resources API - System resources (stickers, backgrounds, templates) (v2).

@module api.user.resources
@version 2.0.0

Endpoints:
- GET /api/v2/user/resources - List system resources
- GET /api/v2/user/resources/types - Get resource types
- GET /api/v2/user/resources/categories/{type} - Get categories for type
- GET /api/v2/user/resources/stickers - Get stickers
- GET /api/v2/user/resources/backgrounds - Get backgrounds
- GET /api/v2/user/resources/templates - Get project templates
- GET /api/v2/user/resources/{id} - Get single resource
"""

import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from dependencies import get_current_user, optional_user
from domains.content import ResourceType, ContentService
from infrastructure.repositories import SupabaseSystemResourceRepository
from application.queries.content import (
    GetResourcesQuery,
    GetResourcesHandler,
    GetResourceByIdQuery,
    GetResourceByIdHandler,
    GetStickersQuery,
    GetStickersHandler,
    GetBackgroundsQuery,
    GetBackgroundsHandler,
    GetProjectTemplatesQuery,
    GetProjectTemplatesHandler,
    GetCategoriesQuery,
    GetCategoriesHandler,
)
from core.database import get_database_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resources", tags=["user-resources-v2"])


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
# Dependency Injection
# ==========================================

def get_content_service() -> ContentService:
    """Get content service instance."""
    db_client = get_database_client()
    repository = SupabaseSystemResourceRepository(db_client)
    return ContentService(repository)


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
    content_service: ContentService = Depends(get_content_service),
) -> ResourcesListResponse:
    """
    List system resources with optional filtering.

    Returns resources with access status based on user's tier.
    """
    user_tier = user.get("tier", "free") if user else "free"

    query = GetResourcesQuery(
        user_tier=user_tier,
        resource_type=type,
        category=category,
        allowed_tiers_filter=tier,
        page=page,
        limit=limit,
        include_locked=include_locked,
    )

    handler = GetResourcesHandler(content_service)
    result = await handler.handle(query)

    return ResourcesListResponse(
        items=result.items,
        total=result.total,
        page=result.page,
        has_more=result.total > page * limit,
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
async def get_categories(
    resource_type: str,
    content_service: ContentService = Depends(get_content_service),
) -> CategoriesResponse:
    """
    Get available categories for a resource type.
    """
    query = GetCategoriesQuery(resource_type=resource_type)
    handler = GetCategoriesHandler(content_service)
    result = await handler.handle(query)

    return CategoriesResponse(categories=result.categories)


@router.get("/stickers")
async def get_stickers(
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    user: dict = Depends(optional_user),
    content_service: ContentService = Depends(get_content_service),
) -> Dict[str, Any]:
    """
    Get stickers for the editor.

    Convenience endpoint that filters by sticker type.
    """
    user_tier = user.get("tier", "free") if user else "free"

    query = GetStickersQuery(
        user_tier=user_tier,
        category=category,
        page=page,
        limit=limit,
    )

    handler = GetStickersHandler(content_service)
    return await handler.handle(query)


@router.get("/backgrounds")
async def get_backgrounds(
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(optional_user),
    content_service: ContentService = Depends(get_content_service),
) -> Dict[str, Any]:
    """
    Get background images.

    Convenience endpoint that filters by background type.
    """
    user_tier = user.get("tier", "free") if user else "free"

    query = GetBackgroundsQuery(
        user_tier=user_tier,
        category=category,
        page=page,
        limit=limit,
    )

    handler = GetBackgroundsHandler(content_service)
    return await handler.handle(query)


@router.get("/templates")
async def get_templates(
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(optional_user),
    content_service: ContentService = Depends(get_content_service),
) -> Dict[str, Any]:
    """
    Get project templates.

    Convenience endpoint that filters by template/project type.
    """
    user_tier = user.get("tier", "free") if user else "free"

    query = GetProjectTemplatesQuery(
        user_tier=user_tier,
        category=category,
        page=page,
        limit=limit,
    )

    handler = GetProjectTemplatesHandler(content_service)
    return await handler.handle(query)


@router.get("/{resource_id}")
async def get_resource(
    resource_id: str,
    user: dict = Depends(optional_user),
    content_service: ContentService = Depends(get_content_service),
) -> Dict[str, Any]:
    """
    Get a single resource by ID.
    """
    user_tier = user.get("tier", "free") if user else "free"

    query = GetResourceByIdQuery(
        resource_id=resource_id,
        user_tier=user_tier,
    )

    handler = GetResourceByIdHandler(content_service)
    result = await handler.handle(query)

    if not result.resource:
        raise HTTPException(404, "Resource not found")

    return result.resource
