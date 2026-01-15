"""
Admin Static Pages Router - Static page management API.

@module api.admin.static_pages
@version 1.0.0

Admin endpoints for full CRUD operations on static pages.
Requires admin authentication.

Endpoints:
- GET /static-pages - List all static pages (including drafts)
- GET /static-pages/{id} - Get static page by ID
- POST /static-pages - Create static page
- PUT /static-pages/{id} - Update static page
- DELETE /static-pages/{id} - Delete static page
- POST /static-pages/{id}/publish - Publish static page
- POST /static-pages/{id}/unpublish - Unpublish static page (set to draft)
"""

import logging
from typing import Optional, List, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Depends, Query, Path
from pydantic import BaseModel, Field, field_validator

from domains.static_pages.entities import StaticPageType
from domains.static_pages.service import StaticPageService
from infrastructure.rate_limiter import limiter
from core.database import get_async_db_client
from infrastructure.repositories.static_page_repository import SupabaseStaticPageRepository
from dependencies import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/static-pages", tags=["admin-static-pages"])


# ==========================================
# Request Models
# ==========================================

class CreateStaticPageRequest(BaseModel):
    """Request model for creating a static page."""
    slug: str = Field(..., min_length=1, max_length=100, description="URL-friendly slug")
    title: str = Field(..., min_length=1, max_length=200, description="Page title")
    content: str = Field(..., min_length=1, description="Markdown content")
    page_type: str = Field(..., description="Page type (legal, company, guide, other)")
    subtitle: Optional[str] = Field(None, max_length=500, description="Page subtitle")
    icon: Optional[str] = Field(None, max_length=50, description="Lucide icon name")
    hero_gradient: Optional[str] = Field(None, max_length=100, description="CSS gradient classes")
    meta_title: Optional[str] = Field(None, max_length=200, description="SEO title")
    meta_description: Optional[str] = Field(None, max_length=500, description="SEO description")
    schema_data: Optional[dict] = Field(None, description="JSON-LD schema")
    extra_data: Optional[dict] = Field(None, description="Additional structured data")
    last_updated_display: Optional[str] = Field(None, max_length=50, description="Display date")
    sort_order: int = Field(0, ge=0, description="Sort order weight")

    @field_validator("page_type")
    @classmethod
    def validate_page_type(cls, v: str) -> str:
        """Validate page type is valid."""
        valid = [t.value for t in StaticPageType]
        if v not in valid:
            raise ValueError(f"Invalid page_type. Must be one of: {', '.join(valid)}")
        return v


class UpdateStaticPageRequest(BaseModel):
    """Request model for updating a static page."""
    slug: Optional[str] = Field(None, min_length=1, max_length=100, description="URL-friendly slug")
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="Page title")
    content: Optional[str] = Field(None, min_length=1, description="Markdown content")
    page_type: Optional[str] = Field(None, description="Page type")
    subtitle: Optional[str] = Field(None, max_length=500, description="Page subtitle")
    icon: Optional[str] = Field(None, max_length=50, description="Lucide icon name")
    hero_gradient: Optional[str] = Field(None, max_length=100, description="CSS gradient classes")
    meta_title: Optional[str] = Field(None, max_length=200, description="SEO title")
    meta_description: Optional[str] = Field(None, max_length=500, description="SEO description")
    schema_data: Optional[dict] = Field(None, description="JSON-LD schema")
    extra_data: Optional[dict] = Field(None, description="Additional structured data")
    last_updated_display: Optional[str] = Field(None, max_length=50, description="Display date")
    sort_order: Optional[int] = Field(None, ge=0, description="Sort order weight")

    @field_validator("page_type")
    @classmethod
    def validate_page_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate page type is valid if provided."""
        if v is None:
            return v
        valid = [t.value for t in StaticPageType]
        if v not in valid:
            raise ValueError(f"Invalid page_type. Must be one of: {', '.join(valid)}")
        return v


# ==========================================
# Response Models
# ==========================================

class StaticPageResponse(BaseModel):
    """Full static page response."""
    id: str = Field(..., description="Page UUID")
    slug: str = Field(..., description="URL-friendly slug")
    title: str = Field(..., description="Page title")
    subtitle: Optional[str] = Field(None, description="Page subtitle")
    content: str = Field(..., description="Markdown content")
    page_type: str = Field(..., description="Page type")
    icon: Optional[str] = Field(None, description="Lucide icon name")
    hero_gradient: Optional[str] = Field(None, description="CSS gradient classes")
    meta_title: Optional[str] = Field(None, description="SEO title")
    meta_description: Optional[str] = Field(None, description="SEO description")
    schema_data: Optional[dict] = Field(None, description="JSON-LD schema")
    extra_data: dict = Field(default_factory=dict, description="Additional data")
    is_published: bool = Field(..., description="Publication status")
    published_at: Optional[str] = Field(None, description="Publication timestamp")
    last_updated_display: Optional[str] = Field(None, description="Display date")
    sort_order: int = Field(0, description="Sort order weight")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class StaticPageSummaryResponse(BaseModel):
    """Static page summary for list views."""
    id: str = Field(..., description="Page UUID")
    slug: str = Field(..., description="URL-friendly slug")
    title: str = Field(..., description="Page title")
    subtitle: Optional[str] = Field(None, description="Page subtitle")
    page_type: str = Field(..., description="Page type")
    icon: Optional[str] = Field(None, description="Lucide icon name")
    is_published: bool = Field(..., description="Publication status")
    last_updated_display: Optional[str] = Field(None, description="Display date")
    sort_order: int = Field(0, description="Sort order weight")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class StaticPagesListResponse(BaseModel):
    """Response for static page list endpoint."""
    items: List[StaticPageSummaryResponse]
    total: int = Field(..., description="Total count")
    offset: int = Field(0, description="Current offset")
    limit: int = Field(20, description="Current limit")


class StaticPageCreateResponse(BaseModel):
    """Response for static page creation."""
    success: bool
    message: str
    page: StaticPageResponse


class StaticPageUpdateResponse(BaseModel):
    """Response for static page update."""
    success: bool
    message: str
    page: StaticPageResponse


class StaticPageDeleteResponse(BaseModel):
    """Response for static page deletion."""
    success: bool
    message: str


class StaticPagePublishResponse(BaseModel):
    """Response for publish/unpublish operations."""
    success: bool
    message: str
    page: StaticPageResponse


# ==========================================
# Helper Functions
# ==========================================

async def _get_static_page_service() -> StaticPageService:
    """Get StaticPageService instance with injected repository."""
    db = await get_async_db_client()
    repo = SupabaseStaticPageRepository(db)
    return StaticPageService(repo)


def _page_to_response(page) -> StaticPageResponse:
    """Convert StaticPage entity to response model."""
    return StaticPageResponse(
        id=str(page.id),
        slug=page.slug,
        title=page.title,
        subtitle=page.subtitle,
        content=page.content,
        page_type=page.page_type.value if hasattr(page.page_type, 'value') else page.page_type,
        icon=page.icon,
        hero_gradient=page.hero_gradient,
        meta_title=page.meta_title,
        meta_description=page.meta_description,
        schema_data=page.schema_data,
        extra_data=page.extra_data or {},
        is_published=page.is_published,
        published_at=page.published_at.isoformat() if page.published_at else None,
        last_updated_display=page.last_updated_display,
        sort_order=page.sort_order,
        created_at=page.created_at.isoformat() if page.created_at else None,
        updated_at=page.updated_at.isoformat() if page.updated_at else None,
    )


def _page_to_summary(page) -> StaticPageSummaryResponse:
    """Convert StaticPageSummary entity to response model."""
    return StaticPageSummaryResponse(
        id=str(page.id),
        slug=page.slug,
        title=page.title,
        subtitle=page.subtitle,
        page_type=page.page_type.value if hasattr(page.page_type, 'value') else page.page_type,
        icon=page.icon,
        is_published=page.is_published,
        last_updated_display=page.last_updated_display,
        sort_order=page.sort_order,
        created_at=page.created_at.isoformat() if page.created_at else None,
        updated_at=page.updated_at.isoformat() if page.updated_at else None,
    )


# ==========================================
# List & Read Endpoints
# ==========================================

@router.get("", response_model=StaticPagesListResponse)
@limiter.limit("30/minute")
async def list_static_pages(
    request: Request,
    page_type: Optional[str] = Query(None, description="Filter by page type"),
    include_drafts: bool = Query(True, description="Include unpublished pages"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Results per page"),
    admin: dict = Depends(require_admin),
):
    """
    List all static pages (including drafts).

    Admin endpoint to view all static pages regardless of publication status.

    Args:
        page_type: Optional type filter (legal, company, guide, other)
        include_drafts: Include unpublished pages (default: True)
        offset: Pagination offset (default: 0)
        limit: Results per page (default: 50, max: 100)

    Returns:
        StaticPagesListResponse with pages and pagination info

    Example:
        GET /api/v2/admin/static-pages?page_type=legal&include_drafts=true
    """
    try:
        # Validate page_type if provided
        parsed_type = None
        if page_type:
            try:
                parsed_type = StaticPageType(page_type)
            except ValueError:
                valid_types = [t.value for t in StaticPageType]
                raise HTTPException(
                    400,
                    f"Invalid page_type. Must be one of: {', '.join(valid_types)}"
                )

        service = await _get_static_page_service()
        logger.info(f"[Admin {admin.get('id')}] List static pages (type={page_type}, drafts={include_drafts})")

        pages = await service.admin_list_static_pages(
            page_type=parsed_type,
            include_drafts=include_drafts,
            offset=offset,
            limit=limit,
        )
        total = await service.admin_get_count(
            page_type=parsed_type,
            published_only=not include_drafts,
        )

        return StaticPagesListResponse(
            items=[_page_to_summary(p) for p in pages],
            total=total,
            offset=offset,
            limit=limit,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] List static pages failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve static pages")


@router.get("/{page_id}", response_model=StaticPageResponse)
@limiter.limit("30/minute")
async def get_static_page(
    request: Request,
    page_id: str = Path(..., description="Page UUID"),
    admin: dict = Depends(require_admin),
):
    """
    Get static page by ID.

    Admin endpoint to view any static page (including drafts).

    Args:
        page_id: Page UUID

    Returns:
        StaticPageResponse with full page content

    Raises:
        404: Page not found

    Example:
        GET /api/v2/admin/static-pages/123e4567-e89b-12d3-a456-426614174000
    """
    try:
        page_uuid = UUID(page_id)
    except ValueError:
        raise HTTPException(400, "Invalid page ID format")

    try:
        service = await _get_static_page_service()
        logger.info(f"[Admin {admin.get('id')}] Get static page {page_id}")

        page = await service.admin_get_static_page(page_uuid)

        if not page:
            raise HTTPException(404, f"Static page not found: {page_id}")

        return _page_to_response(page)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Get static page failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve static page")


# ==========================================
# Create & Update Endpoints
# ==========================================

@router.post("", response_model=StaticPageCreateResponse)
@limiter.limit("10/minute")
async def create_static_page(
    request: Request,
    data: CreateStaticPageRequest,
    admin: dict = Depends(require_admin),
):
    """
    Create a new static page.

    Admin endpoint to create a static page. Pages are created as drafts by default.

    Args:
        data: CreateStaticPageRequest with page details

    Returns:
        StaticPageCreateResponse with created page

    Raises:
        400: Invalid data or slug already exists

    Example:
        POST /api/v2/admin/static-pages
        {
            "slug": "privacy-policy",
            "title": "Privacy Policy",
            "content": "# Privacy Policy...",
            "page_type": "legal"
        }
    """
    try:
        service = await _get_static_page_service()
        logger.info(f"[Admin {admin.get('id')}] Create static page: {data.slug}")

        page = await service.create_static_page(
            slug=data.slug,
            title=data.title,
            content=data.content,
            page_type=StaticPageType(data.page_type),
            subtitle=data.subtitle,
            icon=data.icon,
            hero_gradient=data.hero_gradient,
            meta_title=data.meta_title,
            meta_description=data.meta_description,
            schema_data=data.schema_data,
            extra_data=data.extra_data,
            last_updated_display=data.last_updated_display,
            sort_order=data.sort_order,
        )

        return StaticPageCreateResponse(
            success=True,
            message=f"Static page '{data.title}' created successfully",
            page=_page_to_response(page),
        )

    except ValueError as e:
        raise HTTPException(400, str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Create static page failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to create static page")


@router.put("/{page_id}", response_model=StaticPageUpdateResponse)
@limiter.limit("30/minute")
async def update_static_page(
    request: Request,
    page_id: str = Path(..., description="Page UUID"),
    data: UpdateStaticPageRequest = ...,
    admin: dict = Depends(require_admin),
):
    """
    Update an existing static page.

    Admin endpoint to update static page content or metadata.

    Args:
        page_id: Page UUID
        data: UpdateStaticPageRequest with fields to update

    Returns:
        StaticPageUpdateResponse with updated page

    Raises:
        400: Invalid data or slug already exists
        404: Page not found

    Example:
        PUT /api/v2/admin/static-pages/123e4567-e89b-12d3-a456-426614174000
        {
            "title": "Updated Privacy Policy",
            "content": "# Updated content..."
        }
    """
    try:
        page_uuid = UUID(page_id)
    except ValueError:
        raise HTTPException(400, "Invalid page ID format")

    try:
        service = await _get_static_page_service()
        logger.info(f"[Admin {admin.get('id')}] Update static page: {page_id}")

        page = await service.update_static_page(
            page_id=page_uuid,
            slug=data.slug,
            title=data.title,
            content=data.content,
            page_type=StaticPageType(data.page_type) if data.page_type else None,
            subtitle=data.subtitle,
            icon=data.icon,
            hero_gradient=data.hero_gradient,
            meta_title=data.meta_title,
            meta_description=data.meta_description,
            schema_data=data.schema_data,
            extra_data=data.extra_data,
            last_updated_display=data.last_updated_display,
            sort_order=data.sort_order,
        )

        if not page:
            raise HTTPException(404, f"Static page not found: {page_id}")

        return StaticPageUpdateResponse(
            success=True,
            message="Static page updated successfully",
            page=_page_to_response(page),
        )

    except ValueError as e:
        raise HTTPException(400, str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Update static page failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to update static page")


@router.delete("/{page_id}", response_model=StaticPageDeleteResponse)
@limiter.limit("10/minute")
async def delete_static_page(
    request: Request,
    page_id: str = Path(..., description="Page UUID"),
    admin: dict = Depends(require_admin),
):
    """
    Delete a static page.

    Admin endpoint to permanently delete a static page.

    Args:
        page_id: Page UUID

    Returns:
        StaticPageDeleteResponse

    Raises:
        404: Page not found

    Example:
        DELETE /api/v2/admin/static-pages/123e4567-e89b-12d3-a456-426614174000
    """
    try:
        page_uuid = UUID(page_id)
    except ValueError:
        raise HTTPException(400, "Invalid page ID format")

    try:
        service = await _get_static_page_service()
        logger.info(f"[Admin {admin.get('id')}] Delete static page: {page_id}")

        success = await service.delete_static_page(page_uuid)

        if not success:
            raise HTTPException(404, f"Static page not found: {page_id}")

        return StaticPageDeleteResponse(
            success=True,
            message="Static page deleted successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Delete static page failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to delete static page")


# ==========================================
# Publish/Unpublish Endpoints
# ==========================================

@router.post("/{page_id}/publish", response_model=StaticPagePublishResponse)
@limiter.limit("10/minute")
async def publish_static_page(
    request: Request,
    page_id: str = Path(..., description="Page UUID"),
    admin: dict = Depends(require_admin),
):
    """
    Publish a static page.

    Admin endpoint to make a static page publicly visible.

    Args:
        page_id: Page UUID

    Returns:
        StaticPagePublishResponse with published page

    Raises:
        404: Page not found

    Example:
        POST /api/v2/admin/static-pages/123e4567-e89b-12d3-a456-426614174000/publish
    """
    try:
        page_uuid = UUID(page_id)
    except ValueError:
        raise HTTPException(400, "Invalid page ID format")

    try:
        service = await _get_static_page_service()
        logger.info(f"[Admin {admin.get('id')}] Publish static page: {page_id}")

        page = await service.publish_static_page(page_uuid)

        if not page:
            raise HTTPException(404, f"Static page not found: {page_id}")

        return StaticPagePublishResponse(
            success=True,
            message="Static page published successfully",
            page=_page_to_response(page),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Publish static page failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to publish static page")


@router.post("/{page_id}/unpublish", response_model=StaticPagePublishResponse)
@limiter.limit("10/minute")
async def unpublish_static_page(
    request: Request,
    page_id: str = Path(..., description="Page UUID"),
    admin: dict = Depends(require_admin),
):
    """
    Unpublish a static page (set to draft).

    Admin endpoint to hide a static page from public access.

    Args:
        page_id: Page UUID

    Returns:
        StaticPagePublishResponse with unpublished page

    Raises:
        404: Page not found

    Example:
        POST /api/v2/admin/static-pages/123e4567-e89b-12d3-a456-426614174000/unpublish
    """
    try:
        page_uuid = UUID(page_id)
    except ValueError:
        raise HTTPException(400, "Invalid page ID format")

    try:
        service = await _get_static_page_service()
        logger.info(f"[Admin {admin.get('id')}] Unpublish static page: {page_id}")

        page = await service.unpublish_static_page(page_uuid)

        if not page:
            raise HTTPException(404, f"Static page not found: {page_id}")

        return StaticPagePublishResponse(
            success=True,
            message="Static page unpublished successfully",
            page=_page_to_response(page),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Unpublish static page failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to unpublish static page")
