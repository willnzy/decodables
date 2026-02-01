"""
Resources API - System resources (stickers, backgrounds, templates) (v3.1).

@module api.user.resources
@version 3.1.0

Changes:
- v3.1.0: API Consolidation Phase 5
  - REMOVED: GET /stickers (use GET /?type=sticker instead)
  - REMOVED: GET /backgrounds (use GET /?type=background instead)
  - REMOVED: GET /templates (use GET /?type=template instead)
- v3.0.0: DDD architecture upgrade - CQRS Query pattern
  - Migrated from Inline Handler to Container pattern
  - All 7 Query Handlers now registered in Container
  - Removed Depends(get_content_service) from endpoints
  - Added Result objects for Stickers/Backgrounds/Templates
  - Improved architecture consistency with other v3 modules
- v2.1.0: Security improvements
  - RES-MEDIUM-1: Added rate limiting to all endpoints
  - RES-MEDIUM-2: Added UUID validation for resource_id
  - RES-MEDIUM-3: Added resource_type whitelist validation
  - RES-LOW-1: Added search parameter length limit
  - RES-LOW-2: Added category whitelist validation

Endpoints:
- GET /api/v2/user/resources - List system resources (use type param to filter)
- GET /api/v2/user/resources/types - Get resource types
- GET /api/v2/user/resources/categories/{type} - Get categories for type
- GET /api/v2/user/resources/{id} - Get single resource
"""

import logging
import re
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from dependencies import get_current_user, optional_user
from infrastructure.rate_limiter import limiter
from domains.content import ResourceType
from container import get_container
from application.queries.content import (
    GetResourcesQuery,
    GetResourceByIdQuery,
    GetCategoriesQuery,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resources", tags=["user-resources-v3"])

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
    allowed_tiers: List[str] = ["t1"]
    is_locked: bool = False

    class Config:
        extra = "allow"


class ResourcesListResponse(BaseModel):
    """Resources list response."""
    items: List[Dict[str, Any]]
    total: int
    offset: int
    limit: int
    has_more: bool = False


class PaginatedResourcesResponse(BaseModel):
    """Paginated resources response (P2-002). WS-16: page→offset."""
    items: List[Dict[str, Any]]
    total: int
    offset: int
    limit: int


class SingleResourceResponse(BaseModel):
    """Single resource response (P2-002)."""
    # Allow arbitrary fields since resource structure varies
    class Config:
        extra = "allow"


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
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=200),
    include_locked: bool = Query(True, description="Include locked resources"),
    user: dict = Depends(optional_user),
) -> ResourcesListResponse:
    """
    List system resources with optional filtering.

    Returns resources with access status based on user's tier.

    v3.0.0: Now uses GetResourcesHandler (Container pattern).
    v2.1.0: Added rate limiting and parameter validation.
    WS-16: Migrated page→offset for DDD consistency.
    """
    # v2.1.0: RES-MEDIUM-3 - Validate resource type if provided
    if type and type not in VALID_RESOURCE_TYPES:
        type = None  # Silently ignore invalid type

    # v2.1.0: RES-LOW-2 - Validate category if provided
    if category and category not in VALID_CATEGORIES:
        category = None  # Silently ignore invalid category

    user_tier = (user.tier or "t1") if user else "t1"

    container = get_container()
    handler = await container.get_resources_handler()

    query = GetResourcesQuery(
        user_tier=user_tier,
        resource_type=type,
        category=category,
        allowed_tiers_filter=tier,
        offset=offset,
        limit=limit,
        include_locked=include_locked,
    )

    result = await handler.handle(query)

    return ResourcesListResponse(
        items=result.items,
        total=result.total,
        offset=result.offset,
        limit=result.limit,
        has_more=result.total > offset + limit,
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
) -> CategoriesResponse:
    """
    Get available categories for a resource type.

    v3.0.0: Now uses GetCategoriesHandler (Container pattern).
    v2.1.0: Added rate limiting and type validation.
    """
    # v2.1.0: RES-MEDIUM-3 - Validate resource type
    if resource_type not in VALID_RESOURCE_TYPES:
        return CategoriesResponse(categories=[])  # Return empty for invalid type

    container = get_container()
    handler = await container.get_categories_handler()

    query = GetCategoriesQuery(resource_type=resource_type)
    result = await handler.handle(query)

    return CategoriesResponse(categories=result.categories)


@router.get("/{resource_id}")
@limiter.limit("60/minute")  # v2.1.0: RES-MEDIUM-1
async def get_resource(
    request: Request,  # v2.1.0: Required for rate limiter
    resource_id: str,
    user: dict = Depends(optional_user),
) -> ResourceItem:  # P2-002: Return Pydantic model instead of Dict[str, Any]
    """
    Get a single resource by ID.

    v3.0.0: Now uses GetResourceByIdHandler (Container pattern).
    v2.1.0: Added rate limiting and ID validation.
    """
    # v2.1.0: RES-MEDIUM-2 - Validate resource_id format
    if not UUID_PATTERN.match(resource_id):
        raise HTTPException(400, "Invalid resource ID format")

    user_tier = (user.tier or "t1") if user else "t1"

    container = get_container()
    handler = await container.get_resource_by_id_handler()

    query = GetResourceByIdQuery(
        resource_id=resource_id,
        user_tier=user_tier,
    )

    result = await handler.handle(query)

    if not result.resource:
        raise HTTPException(404, "Resource not found")

    # P2-002: Return Pydantic model instead of raw dict
    return ResourceItem(**result.resource)
