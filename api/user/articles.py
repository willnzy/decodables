"""
User Articles Router - Public articles API.

@module api.user.articles
@version 1.0.0

Public endpoints for reading articles (manual, news, changelog).
No authentication required.

Endpoints:
- GET /articles - List published articles
- GET /articles/categories - Get categories with counts
- GET /articles/search - Search published articles
- GET /articles/{slug} - Get article by slug
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Request, Query, Path, Depends
from pydantic import BaseModel, Field

from domains.articles.entities import ArticleCategory
from domains.articles.service import ArticleService
from infrastructure.rate_limiter import limiter
from container import get_container

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/articles", tags=["articles-public"])


# ==========================================
# Response Models
# ==========================================

class ArticleSummaryResponse(BaseModel):
    """Article summary for list views."""
    id: str = Field(..., description="Article UUID")
    slug: str = Field(..., description="URL-friendly slug")
    title: str = Field(..., description="Article title")
    summary: Optional[str] = Field(None, description="Article summary")
    category: str = Field(..., description="Article category")
    tags: List[str] = Field(default_factory=list, description="Article tags")
    cover_image: Optional[str] = Field(None, description="Cover image URL")
    published_at: Optional[str] = Field(None, description="Publication timestamp")
    view_count: int = Field(0, description="View count")


class ArticleDetailResponse(BaseModel):
    """Full article detail."""
    id: str = Field(..., description="Article UUID")
    slug: str = Field(..., description="URL-friendly slug")
    title: str = Field(..., description="Article title")
    content: str = Field(..., description="Markdown content")
    summary: Optional[str] = Field(None, description="Article summary")
    category: str = Field(..., description="Article category")
    tags: List[str] = Field(default_factory=list, description="Article tags")
    cover_image: Optional[str] = Field(None, description="Cover image URL")
    published_at: Optional[str] = Field(None, description="Publication timestamp")
    view_count: int = Field(0, description="View count")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class ArticlesListResponse(BaseModel):
    """Response for article list endpoint."""
    items: List[ArticleSummaryResponse]  # Changed from 'articles' to 'items' for frontend consistency
    total: int = Field(..., description="Total count (for pagination)")
    offset: int = Field(0, description="Current offset")
    limit: int = Field(20, description="Current limit")


class CategoryCountResponse(BaseModel):
    """Category with article count."""
    category: str = Field(..., description="Category name")
    display_name: str = Field(..., description="Human-readable name")
    count: int = Field(0, description="Published article count")


class CategoriesResponse(BaseModel):
    """Response for categories endpoint."""
    categories: List[CategoryCountResponse]


# ==========================================
# Dependencies
# ==========================================

async def get_article_service() -> ArticleService:
    """
    FastAPI dependency for ArticleService.
    
    v3.31: 使用 Container 单例模式（项目标准）
    - 通过 Container 获取服务实例
    - 实例缓存，避免重复创建
    - 与项目其他模块保持一致
    """
    try:
        container = get_container()
        return await container.get_article_service()
    except RuntimeError as e:
        logger.error(f"[Articles] Failed to get service: {e}")
        raise HTTPException(503, "Database service unavailable")


def _get_category_display_name(category: str) -> str:
    """Get human-readable category name."""
    names = {
        "manual": "Help & Documentation",
        "news": "News & Announcements",
        "changelog": "Changelog",
    }
    return names.get(category, category.title())


# ==========================================
# Endpoints
# ==========================================

@router.get("", response_model=ArticlesListResponse)
@limiter.limit("60/minute")
async def list_articles(
    request: Request,
    category: Optional[str] = Query(
        None,
        description="Filter by category (manual, news, changelog)"
    ),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    service: ArticleService = Depends(get_article_service),  # v3.31: 修复依赖注入
):
    """
    List published articles.

    Returns a paginated list of published articles, optionally filtered by category.
    Articles are sorted by sort_order (ascending) and published_at (descending).

    Args:
        category: Optional category filter (manual, news, changelog)
        offset: Pagination offset (default: 0)
        limit: Results per page (default: 20, max: 100)

    Returns:
        ArticlesListResponse with articles, total count, and pagination info

    Example:
        GET /api/v2/user/articles?category=manual&limit=10
    """
    try:
        # Validate category if provided
        if category:
            valid_categories = [c.value for c in ArticleCategory]
            if category not in valid_categories:
                raise HTTPException(
                    400,
                    f"Invalid category. Must be one of: {', '.join(valid_categories)}"
                )

        # Get articles and total count
        articles = await service.list_articles(
            category=category,
            offset=offset,
            limit=limit,
        )
        total = await service.get_article_count(category=category)

        return ArticlesListResponse(
            items=[
                ArticleSummaryResponse(
                    id=str(a.id),
                    slug=a.slug,
                    title=a.title,
                    summary=a.summary,
                    category=a.category.value if hasattr(a.category, 'value') else a.category,
                    tags=a.tags,
                    cover_image=a.cover_image,
                    published_at=a.published_at.isoformat() if a.published_at else None,
                    view_count=a.view_count,
                )
                for a in articles
            ],
            total=total,
            offset=offset,
            limit=limit,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Articles] List failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve articles")


@router.get("/categories", response_model=CategoriesResponse)
@limiter.limit("60/minute")
async def get_categories(
    request: Request,
    service: ArticleService = Depends(get_article_service),  # v3.31: 修复依赖注入
):
    """
    Get article categories with published counts.

    Returns all available categories with the number of published articles
    in each category.

    Returns:
        CategoriesResponse with category info

    Example:
        GET /api/v2/user/articles/categories

        Response:
        {
            "categories": [
                {"category": "manual", "display_name": "Help & Documentation", "count": 15},
                {"category": "news", "display_name": "News & Announcements", "count": 8},
                {"category": "changelog", "display_name": "Changelog", "count": 12}
            ]
        }
    """
    try:
        categories = await service.get_categories()

        return CategoriesResponse(
            categories=[
                CategoryCountResponse(
                    category=cat["category"],
                    display_name=_get_category_display_name(cat["category"]),
                    count=cat["count"],
                )
                for cat in categories
            ]
        )

    except Exception as e:
        logger.error(f"[Articles] Get categories failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve categories")


@router.get("/search", response_model=ArticlesListResponse)
@limiter.limit("30/minute")
async def search_articles(
    request: Request,
    q: str = Query(..., min_length=2, max_length=100, description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    service: ArticleService = Depends(get_article_service),  # v3.31: 修复依赖注入
):
    """
    Search published articles.

    Searches article titles, content, and tags for the given query.
    Only returns published articles.

    Args:
        q: Search query (2-100 characters)
        category: Optional category filter
        offset: Pagination offset (default: 0)
        limit: Results per page (default: 20, max: 100)

    Returns:
        ArticlesListResponse with matching articles

    Example:
        GET /api/v2/user/articles/search?q=getting+started&category=manual
    """
    try:
        # Validate category if provided
        if category:
            valid_categories = [c.value for c in ArticleCategory]
            if category not in valid_categories:
                raise HTTPException(
                    400,
                    f"Invalid category. Must be one of: {', '.join(valid_categories)}"
                )

        articles = await service.search_articles(
            query=q,
            category=category,
            offset=offset,
            limit=limit,
        )

        return ArticlesListResponse(
            items=[
                ArticleSummaryResponse(
                    id=str(a.id),
                    slug=a.slug,
                    title=a.title,
                    summary=a.summary,
                    category=a.category.value if hasattr(a.category, 'value') else a.category,
                    tags=a.tags,
                    cover_image=a.cover_image,
                    published_at=a.published_at.isoformat() if a.published_at else None,
                    view_count=a.view_count,
                )
                for a in articles
            ],
            total=len(articles),  # Note: Search doesn't return total count
            offset=offset,
            limit=limit,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Articles] Search failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to search articles")


@router.get("/featured", response_model=ArticlesListResponse)
@limiter.limit("60/minute")
async def get_featured_articles(
    request: Request,
    category: Optional[str] = Query(
        None,
        description="Filter by category (manual, news, changelog, faq, troubleshooting)"
    ),
    limit: int = Query(4, ge=1, le=20, description="Number of featured articles"),
    service: ArticleService = Depends(get_article_service),  # v3.31: 修复依赖注入
):
    """
    Get featured articles.

    Returns a list of featured (is_featured=true) published articles,
    optionally filtered by category.

    Args:
        category: Optional category filter
        limit: Maximum number of articles to return (default: 4, max: 20)

    Returns:
        ArticlesListResponse with featured articles

    Example:
        GET /api/v2/user/articles/featured?category=manual&limit=4
    """
    try:
        # Validate category if provided
        if category:
            valid_categories = [c.value for c in ArticleCategory]
            if category not in valid_categories:
                raise HTTPException(
                    400,
                    f"Invalid category. Must be one of: {', '.join(valid_categories)}"
                )

        # Get featured articles
        articles = await service.get_featured_articles(
            category=category,
            limit=limit,
        )

        return ArticlesListResponse(
            items=[
                ArticleSummaryResponse(
                    id=str(a.id),
                    slug=a.slug,
                    title=a.title,
                    summary=a.summary,
                    category=a.category.value if hasattr(a.category, 'value') else a.category,
                    tags=a.tags,
                    cover_image=a.cover_image,
                    published_at=a.published_at.isoformat() if a.published_at else None,
                    view_count=a.view_count,
                )
                for a in articles
            ],
            total=len(articles),
            offset=0,
            limit=limit,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Articles] Get featured failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve featured articles")


@router.get("/{slug}/related", response_model=List[ArticleSummaryResponse])
@limiter.limit("60/minute")
async def get_related_articles(
    request: Request,
    slug: str = Path(..., min_length=1, max_length=200, description="Article slug"),
    limit: int = Query(3, ge=1, le=10, description="Number of related articles"),
    service: ArticleService = Depends(get_article_service),  # v3.31: 修复依赖注入
):
    """
    Get related articles for a given article.

    Returns articles in the same category, excluding the current article.
    Ordered by published_at descending.

    Args:
        slug: Current article slug
        limit: Maximum number of articles to return (default: 3, max: 10)

    Returns:
        List of related ArticleSummaryResponse

    Example:
        GET /api/v2/user/articles/getting-started/related?limit=3
    """
    try:
        # Get current article to know its category
        current_article = await service.get_article(slug)
        if not current_article:
            raise HTTPException(404, f"Article '{slug}' not found")

        # Get articles in same category
        articles = await service.list_articles(
            category=current_article.category.value if hasattr(current_article.category, 'value') else current_article.category,
            offset=0,
            limit=limit + 10,  # Get more to filter out current article
        )

        # Filter out current article and limit results
        related = [a for a in articles if a.slug != slug][:limit]

        return [
            ArticleSummaryResponse(
                id=str(a.id),
                slug=a.slug,
                title=a.title,
                summary=a.summary,
                category=a.category.value if hasattr(a.category, 'value') else a.category,
                tags=a.tags,
                cover_image=a.cover_image,
                published_at=a.published_at.isoformat() if a.published_at else None,
                view_count=a.view_count,
            )
            for a in related
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Articles] Get related articles failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve related articles")


@router.get("/{slug}", response_model=ArticleDetailResponse)
@limiter.limit("60/minute")
async def get_article(
    request: Request,
    slug: str = Path(..., min_length=1, max_length=200, description="Article slug"),
    service: ArticleService = Depends(get_article_service),  # v3.31: 修复依赖注入
):
    """
    Get a single published article by slug.

    Returns the full article content for a published article.
    Also increments the view count.

    Args:
        slug: Article slug (URL-friendly identifier)

    Returns:
        ArticleDetailResponse with full article content

    Raises:
        404: Article not found or not published

    Example:
        GET /api/v2/user/articles/how-to-add-images
    """
    try:
        article = await service.get_article(slug)

        if not article:
            raise HTTPException(404, f"Article '{slug}' not found")

        return ArticleDetailResponse(
            id=str(article.id),
            slug=article.slug,
            title=article.title,
            content=article.content,
            summary=article.summary,
            category=article.category.value if hasattr(article.category, 'value') else article.category,
            tags=article.tags,
            cover_image=article.cover_image,
            published_at=article.published_at.isoformat() if article.published_at else None,
            view_count=article.view_count,
            created_at=article.created_at.isoformat() if article.created_at else None,
            updated_at=article.updated_at.isoformat() if article.updated_at else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Articles] Get article failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve article")
