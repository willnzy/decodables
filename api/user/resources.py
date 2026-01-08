"""
Resources API - System resources (stickers, backgrounds, templates) (v2).

@module api.user.resources
@version 2.1.0

Changes:
- v2.1.0: Security improvements
  - RES-MEDIUM-1: Added rate limiting to all endpoints
  - RES-MEDIUM-2: Added UUID validation for resource_id
  - RES-MEDIUM-3: Added resource_type whitelist validation
  - RES-LOW-1: Added search parameter length limit
  - RES-LOW-2: Added category whitelist validation

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
import re
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from dependencies import get_current_user, optional_user
from infrastructure.rate_limiter import limiter
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
# Constants (v2.1.0)
# ==========================================

# v2.1.0: RES-MEDIUM-2 - UUID validation pattern for resource_id
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE
)

# v2.1.0: RES-MEDIUM-3 - Valid resource types (from enum)
VALID_RESOURCE_TYPES = {rt.value for rt in ResourceType}

# v2.1.0: RES-LOW-2 - Valid category values
VALID_CATEGORIES = {
    "story", "educational", "seasonal", "blank",  # Project
    "animals", "nature", "people", "food", "objects", "emotions", "education", "holiday",  # Sticker
    "pattern",  # Background
    "popular", "new", "ai_generated", "user_upload",  # General
}

# v2.1.0: RES-LOW-1 - Max search query length
MAX_SEARCH_LENGTH = 100


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
@limiter.limit("60/minute")  # v2.1.0: RES-MEDIUM-1
async def list_resources(
    request: Request,  # v2.1.0: Required for rate limiter
    type: Optional[str] = Query(None, description="Resource type", max_length=50),
    category: Optional[str] = Query(None, description="Category filter", max_length=50),
    tier: Optional[str] = Query(None, description="Tier filter", max_length=20),
    search: Optional[str] = Query(None, description="Search in name/tags", max_length=MAX_SEARCH_LENGTH),
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(50, ge=1, le=200),
    include_locked: bool = Query(True, description="Include locked resources"),
    user: dict = Depends(optional_user),
    content_service: ContentService = Depends(get_content_service),
) -> ResourcesListResponse:
    """
    List system resources with optional filtering.

    Returns resources with access status based on user's tier.

    v2.1.0: Added rate limiting and parameter validation.
    """
    # v2.1.0: RES-MEDIUM-3 - Validate resource type if provided
    if type and type not in VALID_RESOURCE_TYPES:
        type = None  # Silently ignore invalid type

    # v2.1.0: RES-LOW-2 - Validate category if provided
    if category and category not in VALID_CATEGORIES:
        category = None  # Silently ignore invalid category

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
@limiter.limit("60/minute")  # v2.1.0: RES-MEDIUM-1
async def get_resource_types(request: Request) -> ResourceTypesResponse:
    """
    Get all available resource types.

    v2.1.0: Added rate limiting.
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
@limiter.limit("60/minute")  # v2.1.0: RES-MEDIUM-1
async def get_categories(
    request: Request,  # v2.1.0: Required for rate limiter
    resource_type: str,
    content_service: ContentService = Depends(get_content_service),
) -> CategoriesResponse:
    """
    Get available categories for a resource type.

    v2.1.0: Added rate limiting and type validation.
    """
    # v2.1.0: RES-MEDIUM-3 - Validate resource type
    if resource_type not in VALID_RESOURCE_TYPES:
        return CategoriesResponse(categories=[])  # Return empty for invalid type

    query = GetCategoriesQuery(resource_type=resource_type)
    handler = GetCategoriesHandler(content_service)
    result = await handler.handle(query)

    return CategoriesResponse(categories=result.categories)


@router.get("/stickers")
@limiter.limit("60/minute")  # v2.1.0: RES-MEDIUM-1
async def get_stickers(
    request: Request,  # v2.1.0: Required for rate limiter
    category: Optional[str] = Query(None, max_length=50),
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(100, ge=1, le=500),
    user: dict = Depends(optional_user),
    content_service: ContentService = Depends(get_content_service),
) -> Dict[str, Any]:
    """
    Get stickers for the editor.

    Convenience endpoint that filters by sticker type.

    v2.1.0: Added rate limiting and parameter validation.
    """
    # v2.1.0: RES-LOW-2 - Validate category
    if category and category not in VALID_CATEGORIES:
        category = None

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
@limiter.limit("60/minute")  # v2.1.0: RES-MEDIUM-1
async def get_backgrounds(
    request: Request,  # v2.1.0: Required for rate limiter
    category: Optional[str] = Query(None, max_length=50),
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(optional_user),
    content_service: ContentService = Depends(get_content_service),
) -> Dict[str, Any]:
    """
    Get background images.

    Convenience endpoint that filters by background type.

    v2.1.0: Added rate limiting and parameter validation.
    """
    # v2.1.0: RES-LOW-2 - Validate category
    if category and category not in VALID_CATEGORIES:
        category = None

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
@limiter.limit("60/minute")  # v2.1.0: RES-MEDIUM-1
async def get_templates(
    request: Request,  # v2.1.0: Required for rate limiter
    category: Optional[str] = Query(None, max_length=50),
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(optional_user),
    content_service: ContentService = Depends(get_content_service),
) -> Dict[str, Any]:
    """
    Get project templates.

    Convenience endpoint that filters by template/project type.

    v2.1.0: Added rate limiting and parameter validation.
    """
    # v2.1.0: RES-LOW-2 - Validate category
    if category and category not in VALID_CATEGORIES:
        category = None

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
@limiter.limit("60/minute")  # v2.1.0: RES-MEDIUM-1
async def get_resource(
    request: Request,  # v2.1.0: Required for rate limiter
    resource_id: str,
    user: dict = Depends(optional_user),
    content_service: ContentService = Depends(get_content_service),
) -> Dict[str, Any]:
    """
    Get a single resource by ID.

    v2.1.0: Added rate limiting and ID validation.
    """
    # v2.1.0: RES-MEDIUM-2 - Validate resource_id format
    if not UUID_PATTERN.match(resource_id):
        raise HTTPException(400, "Invalid resource ID format")

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
