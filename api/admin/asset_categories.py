"""
Admin API for Asset Category Management.

@module api.admin.asset_categories
@version 1.2.0 (Complete Container DI Migration)

Provides 7 endpoints for category CRUD and hierarchy operations:

Changes in v1.2.0:
- Fixed parking lot item: get_category_resources now uses Container pattern
- Added get_system_resource_repository() via Container
- Removed all direct get_async_db_client() calls
- Architecture: API → Container → Repository

Changes in v1.1.0:
- Migrated to Container-based dependency injection
- Removed direct get_async_db_client() calls in DI
- Added get_category_handlers() using Container pattern
- Architecture: API → Container → Service → Repository
- GET /api/v2/admin/categories - List all categories
- GET /api/v2/admin/categories/tree - Get category tree
- POST /api/v2/admin/categories - Create category
- PATCH /api/v2/admin/categories/{slug} - Update category
- PUT /api/v2/admin/categories/{slug}/move - Move category
- DELETE /api/v2/admin/categories/{slug} - Delete category
- GET /api/v2/admin/categories/{slug}/resources - Get category resources
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Path, Body, Depends
from pydantic import BaseModel, Field

from container import get_container
from domains.content.category_service import CategoryService
from application.queries.categories import (
    CategoryQueryHandlers,
    GetCategoryTreeQuery,
    ListCategoriesQuery,
    GetCategoryQuery
)
from application.commands.categories import (
    CategoryCommandHandlers,
    CreateCategoryCommand,
    UpdateCategoryCommand,
    MoveCategoryCommand,
    DeleteCategoryCommand
)


# =============================================================================
# Request/Response Models
# =============================================================================

class CreateCategoryRequest(BaseModel):
    """Request model for creating a category."""
    slug: str = Field(..., min_length=1, max_length=50, pattern=r'^[a-z0-9\-_]+$')
    name: str = Field(..., min_length=1, max_length=100)
    asset_type: str = Field(..., pattern=r'^(text|image|shape|table|sticker|icon|frame)$')
    parent_slug: Optional[str] = None
    name_i18n: Optional[Dict[str, str]] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    min_tier: str = Field(default="t1", pattern=r'^(t1|t2|t3)$')
    is_visible: bool = True
    is_featured: bool = False
    display_order: int = 0
    metadata: Optional[Dict[str, Any]] = None


class UpdateCategoryRequest(BaseModel):
    """Request model for updating a category."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    name_i18n: Optional[Dict[str, str]] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    asset_type: Optional[str] = Field(None, pattern=r'^(text|image|shape|table|sticker|icon|frame)$')
    min_tier: Optional[str] = Field(None, pattern=r'^(t1|t2|t3)$')
    is_visible: Optional[bool] = None
    is_featured: Optional[bool] = None
    display_order: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class MoveCategoryRequest(BaseModel):
    """Request model for moving a category."""
    new_parent_slug: Optional[str] = Field(
        None,
        description="New parent category slug. Use null to move to root."
    )


class DeleteCategoryRequest(BaseModel):
    """Request model for deleting a category."""
    cascade: bool = Field(
        default=False,
        description="If true, delete all descendant categories"
    )


class CategoryResponse(BaseModel):
    """Response model for a category."""
    id: str
    parent_id: Optional[str]
    path: str
    level: int
    slug: str
    name: str
    name_i18n: Dict[str, str]
    description: Optional[str]
    icon: Optional[str]
    asset_type: str
    is_visible: bool
    is_featured: bool
    display_order: int
    min_tier: str
    visible_from: Optional[str]
    visible_until: Optional[str]
    asset_count: int
    usage_count: int
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str


# =============================================================================
# Router and Dependencies
# =============================================================================

router = APIRouter(prefix="/asset-categories", tags=["admin-categories"])


async def get_category_handlers():
    """
    Dependency to get category query and command handlers via Container.

    WHY Container-based DI?
    - Centralized service instantiation
    - Testable (mock injection)
    - Follows DIP (Dependency Inversion Principle)
    """
    container = get_container()
    service = await container.get_category_service()
    query_handlers = CategoryQueryHandlers(service)
    command_handlers = CategoryCommandHandlers(service)
    return query_handlers, command_handlers


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/", response_model=List[CategoryResponse])
async def list_categories(
    asset_type: Optional[str] = Query(None, pattern=r'^(text|image|shape|table|sticker|icon|frame)$'),
    parent_id: Optional[str] = Query(None),
    is_visible: Optional[bool] = Query(None),
    min_tier: Optional[str] = Query(None, pattern=r'^(t1|t2|t3)$'),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """
    List all categories with optional filtering.

    Args:
        asset_type: Filter by asset type
        parent_id: Filter by parent category
        is_visible: Filter by visibility status
        min_tier: Filter by minimum tier requirement
        limit: Maximum results (1-500)
        offset: Results to skip

    Returns:
        List of categories
    """
    query_handlers, _ = await get_category_handlers()

    query = ListCategoriesQuery(
        asset_type=asset_type,
        parent_id=parent_id,
        is_visible=is_visible,
        min_tier=min_tier,
        limit=limit,
        offset=offset
    )

    categories = await query_handlers.handle_list_categories(query)
    return categories


@router.get("/tree", response_model=List[CategoryResponse])
async def get_category_tree(
    asset_type: Optional[str] = Query(None, pattern=r'^(text|image|shape|table|sticker|icon|frame)$'),
    include_hidden: bool = Query(False)
):
    """
    Get category tree in hierarchical order.

    Categories are ordered by LTREE path for tree structure.

    Args:
        asset_type: Filter by asset type
        include_hidden: Include is_visible=False categories

    Returns:
        List of categories in tree order
    """
    query_handlers, _ = await get_category_handlers()

    query = GetCategoryTreeQuery(
        asset_type=asset_type,
        include_hidden=include_hidden
    )

    categories = await query_handlers.handle_get_category_tree(query)
    return categories


@router.post("/", response_model=CategoryResponse, status_code=201)
async def create_category(
    request: CreateCategoryRequest = Body(...)
):
    """
    Create a new category.

    Path and level are automatically calculated based on parent.

    Args:
        request: CreateCategoryRequest

    Returns:
        Created category

    Raises:
        400: If validation fails (invalid data, slug exists, max level exceeded)
        404: If parent category not found
    """
    _, command_handlers = await get_category_handlers()

    command = CreateCategoryCommand(
        slug=request.slug,
        name=request.name,
        asset_type=request.asset_type,
        parent_slug=request.parent_slug,
        name_i18n=request.name_i18n,
        description=request.description,
        icon=request.icon,
        min_tier=request.min_tier,
        is_visible=request.is_visible,
        is_featured=request.is_featured,
        display_order=request.display_order,
        metadata=request.metadata
    )

    try:
        category = await command_handlers.handle_create_category(command)
        return category
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create category: {str(e)}")


@router.patch("/{slug}", response_model=CategoryResponse)
async def update_category(
    slug: str = Path(..., min_length=1, max_length=50),
    request: UpdateCategoryRequest = Body(...)
):
    """
    Update category metadata.

    Note: Use PUT /categories/{slug}/move to change parent/hierarchy.

    Args:
        slug: Category slug
        request: UpdateCategoryRequest

    Returns:
        Updated category

    Raises:
        400: If trying to update protected fields
        404: If category not found
    """
    query_handlers, command_handlers = await get_category_handlers()

    # Get category by slug
    get_query = GetCategoryQuery(slug=slug)
    category = await query_handlers.handle_get_category(get_query)
    if not category:
        raise HTTPException(status_code=404, detail=f"Category not found: {slug}")

    # Build updates dict (only include non-None fields)
    updates = {}
    if request.name is not None:
        updates["name"] = request.name
    if request.name_i18n is not None:
        updates["name_i18n"] = request.name_i18n
    if request.description is not None:
        updates["description"] = request.description
    if request.icon is not None:
        updates["icon"] = request.icon
    if request.asset_type is not None:
        updates["asset_type"] = request.asset_type
    if request.min_tier is not None:
        updates["min_tier"] = request.min_tier
    if request.is_visible is not None:
        updates["is_visible"] = request.is_visible
    if request.is_featured is not None:
        updates["is_featured"] = request.is_featured
    if request.display_order is not None:
        updates["display_order"] = request.display_order
    if request.metadata is not None:
        updates["metadata"] = request.metadata

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    command = UpdateCategoryCommand(
        category_id=category["id"],
        updates=updates
    )

    try:
        updated_category = await command_handlers.handle_update_category(command)
        return updated_category
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update category: {str(e)}")


@router.put("/{slug}/move", response_model=CategoryResponse)
async def move_category(
    slug: str = Path(..., min_length=1, max_length=50),
    request: MoveCategoryRequest = Body(...)
):
    """
    Move a category to a new parent.

    Automatically updates path, level, and all descendant categories.

    Args:
        slug: Category slug to move
        request: MoveCategoryRequest

    Returns:
        Updated category

    Raises:
        400: If would create circular reference or exceed max level
        404: If category or new parent not found
    """
    _, command_handlers = await get_category_handlers()

    command = MoveCategoryCommand(
        category_slug=slug,
        new_parent_slug=request.new_parent_slug
    )

    try:
        updated_category = await command_handlers.handle_move_category(command)
        return updated_category
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to move category: {str(e)}")


@router.delete("/{slug}")
async def delete_category(
    slug: str = Path(..., min_length=1, max_length=50),
    cascade: bool = Query(
        False,
        description="If true, delete all descendant categories"
    )
):
    """
    Delete a category (soft delete with 30-day recovery).

    Args:
        slug: Category slug
        cascade: If true, delete all descendants; if false, fail if has children

    Returns:
        Success message

    Raises:
        400: If cascade=False and category has children
        404: If category not found
    """
    query_handlers, command_handlers = await get_category_handlers()

    # Get category by slug
    get_query = GetCategoryQuery(slug=slug)
    category = await query_handlers.handle_get_category(get_query)
    if not category:
        raise HTTPException(status_code=404, detail=f"Category not found: {slug}")

    command = DeleteCategoryCommand(
        category_id=category["id"],
        cascade=cascade
    )

    try:
        await command_handlers.handle_delete_category(command)
        return {"message": "Category deleted successfully", "slug": slug}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete category: {str(e)}")


@router.get("/{slug}/resources")
async def get_category_resources(
    slug: str = Path(..., min_length=1, max_length=50),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """
    Get system resources associated with a category.

    Args:
        slug: Category slug
        limit: Maximum results (1-200)
        offset: Results to skip

    Returns:
        List of system resources in this category

    Raises:
        404: If category not found
    """
    query_handlers, _ = await get_category_handlers()

    # Get category by slug
    get_query = GetCategoryQuery(slug=slug)
    category = await query_handlers.handle_get_category(get_query)
    if not category:
        raise HTTPException(status_code=404, detail=f"Category not found: {slug}")

    # v1.2.0: Query system_resources via Container (parking lot fix)
    container = get_container()
    resource_repo = await container.get_system_resource_repository()
    resources = await resource_repo.get_by_category_id(
        category_id=category["id"],
        limit=limit,
        offset=offset,
    )

    return {
        "category_slug": slug,
        "category_name": category["name"],
        "total_resources": category.get("asset_count", 0),
        "resources": resources
    }
