"""
User Static Pages Router - Public static pages API.

@module api.user.static_pages
@version 1.0.0

Public endpoints for reading static pages (legal, company, guide).
No authentication required.

Endpoints:
- GET /static-pages - List published static pages
- GET /static-pages/{slug} - Get static page by slug
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Request, Query, Path, Depends
from pydantic import BaseModel, Field

from domains.static_pages.entities import StaticPageType
from domains.static_pages.service import StaticPageService
from infrastructure.rate_limiter import limiter
from container import get_container

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/static-pages", tags=["static-pages-public"])


# ==========================================
# Response Models
# ==========================================

class StaticPageSummaryResponse(BaseModel):
    """Static page summary for list views."""
    id: str = Field(..., description="Page UUID")
    slug: str = Field(..., description="URL-friendly slug")
    title: str = Field(..., description="Page title")
    subtitle: Optional[str] = Field(None, description="Page subtitle")
    page_type: str = Field(..., description="Page type (legal, company, guide, other)")
    icon: Optional[str] = Field(None, description="Lucide icon name")
    is_published: bool = Field(..., description="Publication status")
    last_updated_display: Optional[str] = Field(None, description="Display date")
    sort_order: int = Field(0, description="Sort order")


class StaticPageDetailResponse(BaseModel):
    """Full static page detail."""
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
    last_updated_display: Optional[str] = Field(None, description="Display date")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class StaticPagesListResponse(BaseModel):
    """Response for static pages list endpoint."""
    items: List[StaticPageSummaryResponse]
    total: int = Field(..., description="Total count (for pagination)")
    offset: int = Field(0, description="Current offset")
    limit: int = Field(20, description="Current limit")


# ==========================================
# Dependencies
# ==========================================

async def get_static_page_service() -> StaticPageService:
    """
    FastAPI dependency for StaticPageService.

    Uses Container singleton pattern (project standard).
    """
    try:
        container = get_container()
        return await container.get_static_page_service()
    except RuntimeError as e:
        logger.error(f"[StaticPages] Failed to get service: {e}")
        raise HTTPException(503, "Database service unavailable")


# ==========================================
# Endpoints
# ==========================================

@router.get("", response_model=StaticPagesListResponse)
@limiter.limit("60/minute")
async def list_static_pages(
    request: Request,
    page_type: Optional[str] = Query(
        None,
        description="Filter by page type (legal, company, guide, other)"
    ),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    service: StaticPageService = Depends(get_static_page_service),
):
    """
    List published static pages.

    Returns a paginated list of published static pages, optionally filtered by type.
    Pages are sorted by sort_order (ascending) and title (ascending).

    Args:
        page_type: Optional type filter (legal, company, guide, other)
        offset: Pagination offset (default: 0)
        limit: Results per page (default: 20, max: 100)

    Returns:
        StaticPagesListResponse with pages, total count, and pagination info

    Example:
        GET /api/v2/user/static-pages?page_type=legal&limit=10
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

        # Get pages and total count
        pages = await service.list_static_pages(
            page_type=parsed_type,
            offset=offset,
            limit=limit,
        )
        total = await service.get_static_page_count(page_type=parsed_type)

        return StaticPagesListResponse(
            items=[
                StaticPageSummaryResponse(
                    id=str(p.id),
                    slug=p.slug,
                    title=p.title,
                    subtitle=p.subtitle,
                    page_type=p.page_type.value if hasattr(p.page_type, 'value') else p.page_type,
                    icon=p.icon,
                    is_published=p.is_published,
                    last_updated_display=p.last_updated_display,
                    sort_order=p.sort_order,
                )
                for p in pages
            ],
            total=total,
            offset=offset,
            limit=limit,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[StaticPages] List failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve static pages")


@router.get("/{slug}", response_model=StaticPageDetailResponse)
@limiter.limit("60/minute")
async def get_static_page(
    request: Request,
    slug: str = Path(..., description="Page slug"),
    service: StaticPageService = Depends(get_static_page_service),
):
    """
    Get a static page by slug.

    Returns the full content of a published static page.

    Args:
        slug: URL-friendly page identifier

    Returns:
        StaticPageDetailResponse with full page content

    Raises:
        404: Page not found or not published

    Example:
        GET /api/v2/user/static-pages/privacy-policy
    """
    try:
        page = await service.get_static_page(slug)

        if not page:
            raise HTTPException(404, f"Static page not found: {slug}")

        return StaticPageDetailResponse(
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
            extra_data=page.extra_data,
            is_published=page.is_published,
            last_updated_display=page.last_updated_display,
            created_at=page.created_at.isoformat() if page.created_at else None,
            updated_at=page.updated_at.isoformat() if page.updated_at else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[StaticPages] Get page failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve static page")
