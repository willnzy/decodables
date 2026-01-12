"""
Admin Articles Router - Article management API.

@module api.admin.articles
@version 1.0.0

Admin endpoints for full CRUD operations on articles.
Requires admin authentication.

Endpoints:
- GET /articles - List all articles (including drafts)
- GET /articles/{id} - Get article by ID
- POST /articles - Create article
- PUT /articles/{id} - Update article
- DELETE /articles/{id} - Delete article
- POST /articles/{id}/publish - Publish article
- POST /articles/{id}/unpublish - Unpublish article (set to draft)
"""

import logging
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Depends, Query, Path
from pydantic import BaseModel, Field, field_validator

from domains.articles.entities import ArticleCategory
from domains.articles.service import ArticleService
from infrastructure.rate_limiter import limiter
from core.database import get_async_db_client
from infrastructure.repositories.article_repository import SupabaseArticleRepository
from dependencies import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/articles", tags=["admin-articles"])


# ==========================================
# Request Models
# ==========================================

class CreateArticleRequest(BaseModel):
    """Request model for creating an article."""
    title: str = Field(..., min_length=1, max_length=500, description="Article title")
    content: str = Field(..., min_length=1, description="Markdown content")
    category: str = Field(..., description="Article category (manual, news, changelog)")
    slug: Optional[str] = Field(None, max_length=200, description="Custom slug (auto-generated if not provided)")
    summary: Optional[str] = Field(None, max_length=1000, description="Article summary")
    tags: Optional[List[str]] = Field(None, max_length=20, description="Article tags")
    cover_image: Optional[str] = Field(None, max_length=500, description="Cover image URL")
    is_published: bool = Field(False, description="Publish immediately")
    sort_order: int = Field(0, ge=0, description="Sort order weight")

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Validate category is valid."""
        valid = [c.value for c in ArticleCategory]
        if v not in valid:
            raise ValueError(f"Invalid category. Must be one of: {', '.join(valid)}")
        return v


class UpdateArticleRequest(BaseModel):
    """Request model for updating an article."""
    title: Optional[str] = Field(None, min_length=1, max_length=500, description="Article title")
    content: Optional[str] = Field(None, min_length=1, description="Markdown content")
    category: Optional[str] = Field(None, description="Article category")
    slug: Optional[str] = Field(None, max_length=200, description="Custom slug")
    summary: Optional[str] = Field(None, max_length=1000, description="Article summary")
    tags: Optional[List[str]] = Field(None, max_length=20, description="Article tags")
    cover_image: Optional[str] = Field(None, max_length=500, description="Cover image URL")
    sort_order: Optional[int] = Field(None, ge=0, description="Sort order weight")

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        """Validate category is valid if provided."""
        if v is None:
            return v
        valid = [c.value for c in ArticleCategory]
        if v not in valid:
            raise ValueError(f"Invalid category. Must be one of: {', '.join(valid)}")
        return v


# ==========================================
# Response Models
# ==========================================

class ArticleResponse(BaseModel):
    """Full article response."""
    id: str = Field(..., description="Article UUID")
    slug: str = Field(..., description="URL-friendly slug")
    title: str = Field(..., description="Article title")
    content: str = Field(..., description="Markdown content")
    summary: Optional[str] = Field(None, description="Article summary")
    category: str = Field(..., description="Article category")
    tags: List[str] = Field(default_factory=list, description="Article tags")
    cover_image: Optional[str] = Field(None, description="Cover image URL")
    is_published: bool = Field(..., description="Publication status")
    published_at: Optional[str] = Field(None, description="Publication timestamp")
    author_id: Optional[str] = Field(None, description="Author user ID")
    sort_order: int = Field(0, description="Sort order weight")
    view_count: int = Field(0, description="View count")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class ArticleSummaryResponse(BaseModel):
    """Article summary for list views."""
    id: str = Field(..., description="Article UUID")
    slug: str = Field(..., description="URL-friendly slug")
    title: str = Field(..., description="Article title")
    summary: Optional[str] = Field(None, description="Article summary")
    category: str = Field(..., description="Article category")
    tags: List[str] = Field(default_factory=list, description="Article tags")
    is_published: bool = Field(..., description="Publication status")
    published_at: Optional[str] = Field(None, description="Publication timestamp")
    view_count: int = Field(0, description="View count")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class ArticlesListResponse(BaseModel):
    """Response for article list endpoint."""
    articles: List[ArticleSummaryResponse]
    total: int = Field(..., description="Total count")
    offset: int = Field(0, description="Current offset")
    limit: int = Field(20, description="Current limit")


class ArticleCreateResponse(BaseModel):
    """Response for article creation."""
    success: bool
    message: str
    article: ArticleResponse


class ArticleUpdateResponse(BaseModel):
    """Response for article update."""
    success: bool
    message: str
    article: ArticleResponse


class ArticleDeleteResponse(BaseModel):
    """Response for article deletion."""
    success: bool
    message: str


class ArticlePublishResponse(BaseModel):
    """Response for publish/unpublish operations."""
    success: bool
    message: str
    article: ArticleResponse


# ==========================================
# Helper Functions
# ==========================================

def _get_article_service() -> ArticleService:
    """Get ArticleService instance with injected repository."""
    db = await get_async_db_client()
    repo = SupabaseArticleRepository(db)
    return ArticleService(repo)


def _article_to_response(article) -> ArticleResponse:
    """Convert Article entity to response model."""
    return ArticleResponse(
        id=str(article.id),
        slug=article.slug,
        title=article.title,
        content=article.content,
        summary=article.summary,
        category=article.category.value if hasattr(article.category, 'value') else article.category,
        tags=article.tags,
        cover_image=article.cover_image,
        is_published=article.is_published,
        published_at=article.published_at.isoformat() if article.published_at else None,
        author_id=article.author_id,
        sort_order=article.sort_order,
        view_count=article.view_count,
        created_at=article.created_at.isoformat() if article.created_at else None,
        updated_at=article.updated_at.isoformat() if article.updated_at else None,
    )


def _article_to_summary(article) -> ArticleSummaryResponse:
    """Convert ArticleSummary entity to response model."""
    return ArticleSummaryResponse(
        id=str(article.id),
        slug=article.slug,
        title=article.title,
        summary=article.summary,
        category=article.category.value if hasattr(article.category, 'value') else article.category,
        tags=article.tags,
        is_published=article.is_published,
        published_at=article.published_at.isoformat() if article.published_at else None,
        view_count=article.view_count,
        created_at=article.created_at.isoformat() if article.created_at else None,
        updated_at=article.updated_at.isoformat() if article.updated_at else None,
    )


# ==========================================
# List & Read Endpoints
# ==========================================

@router.get("", response_model=ArticlesListResponse)
@limiter.limit("30/minute")
async def list_articles(
    request: Request,
    category: Optional[str] = Query(None, description="Filter by category"),
    include_drafts: bool = Query(True, description="Include unpublished articles"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    admin: dict = Depends(require_admin),
):
    """
    List all articles (including drafts).

    Admin endpoint to view all articles regardless of publication status.

    Args:
        category: Optional category filter (manual, news, changelog)
        include_drafts: Include unpublished articles (default: True)
        offset: Pagination offset (default: 0)
        limit: Results per page (default: 20, max: 100)

    Returns:
        ArticlesListResponse with articles and pagination info

    Example:
        GET /api/v2/admin/articles?category=manual&include_drafts=true
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

        service = _get_article_service()
        logger.info(f"[Admin {admin.get('id')}] List articles (category={category}, drafts={include_drafts})")

        articles = await service.admin_list_articles(
            category=category,
            include_drafts=include_drafts,
            offset=offset,
            limit=limit,
        )
        total = await service.admin_get_count(
            category=category,
            published_only=not include_drafts,
        )

        return ArticlesListResponse(
            articles=[_article_to_summary(a) for a in articles],
            total=total,
            offset=offset,
            limit=limit,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] List articles failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve articles")


@router.get("/{article_id}", response_model=ArticleResponse)
@limiter.limit("30/minute")
async def get_article(
    request: Request,
    article_id: str = Path(..., description="Article UUID"),
    admin: dict = Depends(require_admin),
):
    """
    Get article by ID.

    Admin endpoint to view any article (including drafts).

    Args:
        article_id: Article UUID

    Returns:
        ArticleResponse with full article content

    Raises:
        404: Article not found

    Example:
        GET /api/v2/admin/articles/550e8400-e29b-41d4-a716-446655440000
    """
    try:
        # Validate UUID format
        try:
            uuid = UUID(article_id)
        except ValueError:
            raise HTTPException(400, "Invalid article ID format")

        service = _get_article_service()
        logger.info(f"[Admin {admin.get('id')}] Get article: {article_id}")

        article = await service.admin_get_article(uuid)

        if not article:
            raise HTTPException(404, f"Article '{article_id}' not found")

        return _article_to_response(article)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Get article failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve article")


# ==========================================
# Create & Update Endpoints
# ==========================================

@router.post("", response_model=ArticleCreateResponse)
@limiter.limit("10/minute")
async def create_article(
    request: Request,
    data: CreateArticleRequest,
    admin: dict = Depends(require_admin),
):
    """
    Create a new article.

    Creates a new article with the provided content. Article can be saved
    as draft (default) or published immediately.

    Args:
        data: CreateArticleRequest with article content

    Returns:
        ArticleCreateResponse with created article

    Example:
        POST /api/v2/admin/articles
        {
            "title": "How to Add Images",
            "content": "# How to Add Images\\n\\n...",
            "category": "manual",
            "summary": "Learn how to upload images",
            "tags": ["images", "tutorial"],
            "is_published": true
        }
    """
    try:
        service = _get_article_service()
        logger.info(f"[Admin {admin.get('id')}] Create article: {data.title}")

        article = await service.create_article(
            title=data.title,
            content=data.content,
            category=data.category,
            slug=data.slug,
            summary=data.summary,
            tags=data.tags,
            cover_image=data.cover_image,
            author_id=admin.get("id"),
            is_published=data.is_published,
            sort_order=data.sort_order,
        )

        # Log to audit trail
        try:
            from infrastructure.repositories.admin_repository import SupabaseAdminUsersRepository
            admin_repo = SupabaseAdminUsersRepository(await get_async_db_client())
            await admin_repo.admin_log_operation(
                admin_id=admin["id"],
                operation_type="article_create",
                target_type="article",
                target_id=str(article.id),
                details=f"Created article: {data.title}",
                metadata={
                    "category": data.category,
                    "is_published": data.is_published,
                },
                source="api",
            )
        except Exception as e:
            logger.warning(f"Failed to log article creation: {e}")

        logger.info(f"[Admin {admin.get('id')}] Article created: {article.id}")

        return ArticleCreateResponse(
            success=True,
            message="Article created successfully",
            article=_article_to_response(article),
        )

    except ValueError as e:
        raise HTTPException(400, str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Create article failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to create article")


@router.put("/{article_id}", response_model=ArticleUpdateResponse)
@limiter.limit("10/minute")
async def update_article(
    request: Request,
    article_id: str = Path(..., description="Article UUID"),
    data: UpdateArticleRequest = ...,
    admin: dict = Depends(require_admin),
):
    """
    Update an existing article.

    Updates article fields. Only provided fields will be updated.
    Cannot change publication status via this endpoint - use publish/unpublish.

    Args:
        article_id: Article UUID
        data: UpdateArticleRequest with fields to update

    Returns:
        ArticleUpdateResponse with updated article

    Raises:
        404: Article not found
        400: Invalid data (e.g., slug already exists)

    Example:
        PUT /api/v2/admin/articles/550e8400-e29b-41d4-a716-446655440000
        {
            "title": "Updated Title",
            "summary": "Updated summary"
        }
    """
    try:
        # Validate UUID format
        try:
            uuid = UUID(article_id)
        except ValueError:
            raise HTTPException(400, "Invalid article ID format")

        service = _get_article_service()
        logger.info(f"[Admin {admin.get('id')}] Update article: {article_id}")

        article = await service.update_article(
            article_id=uuid,
            title=data.title,
            content=data.content,
            category=data.category,
            slug=data.slug,
            summary=data.summary,
            tags=data.tags,
            cover_image=data.cover_image,
            sort_order=data.sort_order,
        )

        if not article:
            raise HTTPException(404, f"Article '{article_id}' not found")

        # Log to audit trail
        try:
            from infrastructure.repositories.admin_repository import SupabaseAdminUsersRepository
            admin_repo = SupabaseAdminUsersRepository(await get_async_db_client())
            await admin_repo.admin_log_operation(
                admin_id=admin["id"],
                operation_type="article_update",
                target_type="article",
                target_id=article_id,
                details=f"Updated article: {article.title}",
                metadata={
                    "updated_fields": [k for k, v in data.model_dump().items() if v is not None],
                },
                source="api",
            )
        except Exception as e:
            logger.warning(f"Failed to log article update: {e}")

        logger.info(f"[Admin {admin.get('id')}] Article updated: {article_id}")

        return ArticleUpdateResponse(
            success=True,
            message="Article updated successfully",
            article=_article_to_response(article),
        )

    except ValueError as e:
        raise HTTPException(400, str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Update article failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to update article")


# ==========================================
# Delete Endpoint
# ==========================================

@router.delete("/{article_id}", response_model=ArticleDeleteResponse)
@limiter.limit("10/minute")
async def delete_article(
    request: Request,
    article_id: str = Path(..., description="Article UUID"),
    admin: dict = Depends(require_admin),
):
    """
    Delete an article.

    Permanently deletes an article. This action cannot be undone.

    Args:
        article_id: Article UUID

    Returns:
        ArticleDeleteResponse

    Raises:
        404: Article not found

    Example:
        DELETE /api/v2/admin/articles/550e8400-e29b-41d4-a716-446655440000
    """
    try:
        # Validate UUID format
        try:
            uuid = UUID(article_id)
        except ValueError:
            raise HTTPException(400, "Invalid article ID format")

        service = _get_article_service()
        logger.info(f"[Admin {admin.get('id')}] Delete article: {article_id}")

        # Get article info before deletion for logging
        article = await service.admin_get_article(uuid)
        if not article:
            raise HTTPException(404, f"Article '{article_id}' not found")

        deleted = await service.delete_article(uuid)

        if not deleted:
            raise HTTPException(500, "Failed to delete article")

        # Log to audit trail
        try:
            from infrastructure.repositories.admin_repository import SupabaseAdminUsersRepository
            admin_repo = SupabaseAdminUsersRepository(await get_async_db_client())
            await admin_repo.admin_log_operation(
                admin_id=admin["id"],
                operation_type="article_delete",
                target_type="article",
                target_id=article_id,
                details=f"Deleted article: {article.title}",
                metadata={
                    "category": article.category.value if hasattr(article.category, 'value') else article.category,
                    "was_published": article.is_published,
                },
                source="api",
            )
        except Exception as e:
            logger.warning(f"Failed to log article deletion: {e}")

        logger.info(f"[Admin {admin.get('id')}] Article deleted: {article_id}")

        return ArticleDeleteResponse(
            success=True,
            message="Article deleted successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Delete article failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to delete article")


# ==========================================
# Publish/Unpublish Endpoints
# ==========================================

@router.post("/{article_id}/publish", response_model=ArticlePublishResponse)
@limiter.limit("10/minute")
async def publish_article(
    request: Request,
    article_id: str = Path(..., description="Article UUID"),
    admin: dict = Depends(require_admin),
):
    """
    Publish an article.

    Sets the article as published and records the publication timestamp.

    Args:
        article_id: Article UUID

    Returns:
        ArticlePublishResponse with updated article

    Raises:
        404: Article not found

    Example:
        POST /api/v2/admin/articles/550e8400-e29b-41d4-a716-446655440000/publish
    """
    try:
        # Validate UUID format
        try:
            uuid = UUID(article_id)
        except ValueError:
            raise HTTPException(400, "Invalid article ID format")

        service = _get_article_service()
        logger.info(f"[Admin {admin.get('id')}] Publish article: {article_id}")

        article = await service.publish_article(uuid)

        if not article:
            raise HTTPException(404, f"Article '{article_id}' not found")

        # Log to audit trail
        try:
            from infrastructure.repositories.admin_repository import SupabaseAdminUsersRepository
            admin_repo = SupabaseAdminUsersRepository(await get_async_db_client())
            await admin_repo.admin_log_operation(
                admin_id=admin["id"],
                operation_type="article_publish",
                target_type="article",
                target_id=article_id,
                details=f"Published article: {article.title}",
                source="api",
            )
        except Exception as e:
            logger.warning(f"Failed to log article publish: {e}")

        logger.info(f"[Admin {admin.get('id')}] Article published: {article_id}")

        return ArticlePublishResponse(
            success=True,
            message="Article published successfully",
            article=_article_to_response(article),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Publish article failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to publish article")


@router.post("/{article_id}/unpublish", response_model=ArticlePublishResponse)
@limiter.limit("10/minute")
async def unpublish_article(
    request: Request,
    article_id: str = Path(..., description="Article UUID"),
    admin: dict = Depends(require_admin),
):
    """
    Unpublish an article (set to draft).

    Sets the article as unpublished (draft) and clears the publication timestamp.

    Args:
        article_id: Article UUID

    Returns:
        ArticlePublishResponse with updated article

    Raises:
        404: Article not found

    Example:
        POST /api/v2/admin/articles/550e8400-e29b-41d4-a716-446655440000/unpublish
    """
    try:
        # Validate UUID format
        try:
            uuid = UUID(article_id)
        except ValueError:
            raise HTTPException(400, "Invalid article ID format")

        service = _get_article_service()
        logger.info(f"[Admin {admin.get('id')}] Unpublish article: {article_id}")

        article = await service.unpublish_article(uuid)

        if not article:
            raise HTTPException(404, f"Article '{article_id}' not found")

        # Log to audit trail
        try:
            from infrastructure.repositories.admin_repository import SupabaseAdminUsersRepository
            admin_repo = SupabaseAdminUsersRepository(await get_async_db_client())
            await admin_repo.admin_log_operation(
                admin_id=admin["id"],
                operation_type="article_unpublish",
                target_type="article",
                target_id=article_id,
                details=f"Unpublished article: {article.title}",
                source="api",
            )
        except Exception as e:
            logger.warning(f"Failed to log article unpublish: {e}")

        logger.info(f"[Admin {admin.get('id')}] Article unpublished: {article_id}")

        return ArticlePublishResponse(
            success=True,
            message="Article unpublished successfully",
            article=_article_to_response(article),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Unpublish article failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to unpublish article")
