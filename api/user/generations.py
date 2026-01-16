"""Generations API - Generation history endpoints (v3).

@module api.user.generations
@version 3.2.0 (Container DI Migration)

Changes:
- v3.2.0: Container DI Migration
  - Migrated to Container-based dependency injection
  - Removed direct get_async_db_client() calls
  - Migrated audit logging to use Container's admin_audit_service
  - Architecture: API → Container → Service → Repository
- v3.1.0: Deprecated endpoints cleanup
  - REMOVED: POST /{id}/favorite (use PATCH /{id} instead)
  - REMOVED: DELETE /batch (use POST /batch-delete instead)
- v3.0.0: DDD architecture upgrade
  - Created GenerationHistoryService with complete business logic
  - Added dependency injection (get_generation_history_service)
  - Migrated to DDD: API → Service → Database
  - Reduced API layer from 284 to ~200 lines (-30%)
  - All business logic moved to GenerationHistoryService
- v2.1.0: Security improvements
  - GEN-P0-1: Added UUID validation for generation_id
  - GEN-MEDIUM-1: Delete now returns 404 if record not found
  - GEN-MEDIUM-2: Added audit logging for delete operations
  - GEN-LOW-1: Sanitized user_id in logs

Endpoints:
- GET /api/v2/user/generations/history - Get generation history
- PATCH /api/v2/user/generations/{id} - Update generation (favorite, etc.)
- DELETE /api/v2/user/generations/{id} - Delete single generation
- POST /api/v2/user/generations/batch-delete - Batch delete history
"""

import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from typing import List, Dict, Any

from domains.identity.aggregates.user_profile import UserProfile
from dependencies import get_current_user
from infrastructure.rate_limiter import limiter
from container import get_container
from domains.generation import GenerationHistoryService
from domains.generation.history_service import GenerationNotFoundException

logger = logging.getLogger(__name__)

# v2.1.0: GEN-P0-1 - UUID validation pattern
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE
)

router = APIRouter(prefix="/generations", tags=["user-generations-v2"])


# ==========================================
# Request/Response Models
# ==========================================

class FavoriteRequest(BaseModel):
    """Toggle favorite request."""
    is_favorited: bool


class GenerationHistoryResponse(BaseModel):
    """Generation history response."""
    generations: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int


class FavoriteResponse(BaseModel):
    """Favorite response."""
    success: bool
    is_favorited: bool


class DeleteResponse(BaseModel):
    """Delete response."""
    success: bool
    deleted: str


class BatchDeleteResponse(BaseModel):
    """Batch delete response."""
    success: bool
    deleted_count: int


# ==========================================
# Dependency Injection
# ==========================================

async def get_generation_history_service() -> GenerationHistoryService:
    """
    Dependency injection factory for GenerationHistoryService via Container.

    WHY Container-based DI?
    - Centralized service instantiation
    - Testable (mock injection)
    - Follows DIP (Dependency Inversion Principle)
    """
    container = get_container()
    return await container.get_generation_history_service()


# ==========================================
# Endpoints
# ==========================================

@router.get("/history")
@limiter.limit("60/minute")
async def get_generation_history(
    request: Request,
    limit: int = Query(20, ge=1, le=100, description="Maximum number of generations to return (1-100, default: 20)"),
    offset: int = Query(0, ge=0, description="Number of generations to skip for pagination"),
    favorites_only: bool = Query(False, description="If true, only return favorited generations"),
    user: UserProfile = Depends(get_current_user),
    history_service: GenerationHistoryService = Depends(get_generation_history_service),  # v3.0.0: DI
) -> GenerationHistoryResponse:
    """
    Get user's AI image generation history with optional favorites filter.

    Retrieves a chronological list of all AI-generated images created by the user,
    including prompts, image URLs, creation timestamps, and favorite status.
    Useful for browsing past generations, reusing prompts, and managing favorites.

    v3.0.0: Refactored to use GenerationHistoryService (DDD architecture).
    v2.1.0: Added pagination limits and UUID validation (GEN-P0-1).

    Args:
        limit: Maximum generations to return (default: 20, max: 100)
            Pagination support for large generation histories
        offset: Skip first N generations (default: 0)
            Used with limit for pagination
        favorites_only: Filter to show only favorited generations (default: false)
            Useful for "Saved" or "Favorites" views

    Returns:
        GenerationHistoryResponse containing:
            - generations: List of generation objects including:
                - id: Generation UUID
                - image_urls: List of generated image URLs (1-8 images)
                - prompt: Original text prompt used
                - style: Generation style (e.g., "illustration", "realistic")
                - is_favorited: Whether user marked this as favorite
                - created_at: Generation timestamp
                - metadata: Additional generation parameters (JSON)
            - total: Total number of generations (respecting favorites_only filter)
            - limit: Limit applied
            - offset: Offset applied
            - has_more: Whether more generations exist (for pagination)

    Raises:
        400: Invalid limit/offset values
        401: Unauthorized (not authenticated)
        429: Rate limit exceeded (max 60 requests per minute)
        500: Database error or service unavailable

    Security:
        - Authentication required
        - User can only access their own generations
        - Rate limit: 60 requests per minute
        - Pagination enforced (max 100 per request)
        - User ownership verified by Service layer

    Example:
        GET /api/v2/user/generations/history?limit=10&favorites_only=true

        Response:
        {
            "generations": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "image_urls": [
                        "https://storage.example.com/gen_abc123_1.png",
                        "https://storage.example.com/gen_abc123_2.png"
                    ],
                    "prompt": "A playful cat reading a book",
                    "style": "illustration",
                    "is_favorited": true,
                    "created_at": "2026-01-10T15:30:00Z",
                    "metadata": {"pages": 2, "tier": "t2"}
                }
            ],
            "total": 1,
            "limit": 10,
            "offset": 0,
            "has_more": false
        }
    """
    # v3.0.0: Get history via Service (DDD compliant)
    try:
        generations, total = await history_service.get_history(
            user.user_id, limit, offset, favorites_only
        )
    except Exception as e:
        logger.error(f"Get history failed for user {user['id'][:8]}...: {e}")
        raise HTTPException(500, "Failed to fetch generation history")

    return GenerationHistoryResponse(
        generations=generations,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.patch("/{generation_id}")
@limiter.limit("60/minute")
async def update_generation(
    request: Request,
    generation_id: str,
    req: FavoriteRequest,
    user: UserProfile = Depends(get_current_user),
    history_service: GenerationHistoryService = Depends(get_generation_history_service),  # v3.0.0: DI
) -> FavoriteResponse:
    """
    Update generation properties (favorite status, etc.).

    **Recommended**: Use PATCH for partial resource updates.

    Security:
    - UUID validation for generation_id
    - User ownership verified by Service
    """
    # v2.1.0: GEN-P0-1 - Validate generation_id format
    if not UUID_PATTERN.match(generation_id):
        raise HTTPException(400, "Invalid generation ID format")

    # v3.0.0: Update via Service (DDD compliant)
    try:
        await history_service.update_generation(
            user.user_id,
            generation_id,
            {"is_favorited": req.is_favorited}
        )
    except GenerationNotFoundException:
        raise HTTPException(404, "Generation not found")
    except Exception as e:
        logger.error(f"Update generation failed: {e}")
        raise HTTPException(500, "Failed to update generation")

    return FavoriteResponse(success=True, is_favorited=req.is_favorited)


@router.delete("/{generation_id}")
@limiter.limit("30/minute")
async def delete_generation(
    request: Request,
    generation_id: str,
    user: UserProfile = Depends(get_current_user),
    history_service: GenerationHistoryService = Depends(get_generation_history_service),  # v3.0.0: DI
) -> DeleteResponse:
    """
    Delete a generated image from history.

    Security:
    - UUID validation for generation_id
    - User ownership verified by Service
    - Audit logging in Service
    """
    # v2.1.0: GEN-P0-1 - Validate generation_id format
    if not UUID_PATTERN.match(generation_id):
        raise HTTPException(400, "Invalid generation ID format")

    # v3.0.0: Delete via Service (DDD compliant)
    try:
        deleted_id = await history_service.delete_generation(user.user_id, generation_id)
    except GenerationNotFoundException:
        raise HTTPException(404, "Generation not found")
    except Exception as e:
        logger.error(f"Delete generation failed: {e}")
        raise HTTPException(500, "Failed to delete generation")

    # ✅ v3.2.0: Audit logging via Container (DI migration)
    try:
        container = get_container()
        admin_audit = await container.get_admin_audit_service()
        await admin_audit.admin_log_operation(
            admin_id=user.user_id,
            operation_type="generation_delete",
            target_type="generation",
            target_id=generation_id,
            details="Generation deleted",
            source="api",
        )
    except Exception as e:
        logger.warning(f"Failed to log generation deletion: {e}")

    return DeleteResponse(success=True, deleted=deleted_id)


@router.post("/batch-delete")
@limiter.limit("10/minute")
async def batch_delete_generations(
    request: Request,
    keep_favorites: bool = Query(True, description="If true, preserve favorited generations (default: true)"),
    user: UserProfile = Depends(get_current_user),
    history_service: GenerationHistoryService = Depends(get_generation_history_service),  # v3.0.0: DI
) -> BatchDeleteResponse:
    """
    Batch delete all generation history with optional favorite preservation.

    Allows users to clear their generation history in bulk, useful for privacy,
    storage management, or starting fresh. Supports preserving favorited generations
    to avoid accidental deletion of important work.

    **Recommended**: Use POST for batch operations (not DELETE).

    v3.0.0: Refactored to use GenerationHistoryService (DDD architecture).

    Args:
        keep_favorites: Whether to preserve favorited generations (default: true)
            - true: Only delete non-favorited generations (safe mode)
            - false: Delete ALL generations including favorites (caution!)

    Returns:
        BatchDeleteResponse containing:
            - success: true if operation completed
            - deleted_count: Number of generations deleted
                Does not include preserved favorites
            - message: Optional confirmation message

    Raises:
        400: Invalid request parameters
        401: Unauthorized (not authenticated)
        429: Rate limit exceeded (max 10 requests per minute)
        500: Database error or service unavailable

    Security:
        - Authentication required
        - User can only delete their own generations
        - Rate limit: 10 requests per minute (prevent abuse)
        - User ownership verified by Service layer
        - Audit logging enabled for accountability

    Behavior:
        - Soft delete (marks as deleted, doesn't remove from DB immediately)
        - Preserves favorites by default (keep_favorites=true)
        - Returns count of deleted items
        - Irreversible operation (no undo)

    Example 1 (safe delete - keep favorites):
        POST /api/v2/user/generations/batch-delete?keep_favorites=true

        Response:
        {
            "success": true,
            "deleted_count": 42,
            "message": "Deleted 42 generations. 5 favorites preserved."
        }

    Example 2 (full delete - including favorites):
        POST /api/v2/user/generations/batch-delete?keep_favorites=false

        Response:
        {
            "success": true,
            "deleted_count": 47,
            "message": "Deleted all 47 generations including favorites."
        }
    """
    # v3.0.0: Batch delete via Service (DDD compliant)
    try:
        deleted_count = await history_service.batch_delete(user.user_id, keep_favorites)
    except Exception as e:
        logger.error(f"Batch delete failed: {e}")
        raise HTTPException(500, "Failed to clear history")

    # ✅ v3.2.0: Audit logging via Container (DI migration)
    try:
        container = get_container()
        admin_audit = await container.get_admin_audit_service()
        await admin_audit.admin_log_operation(
            admin_id=user.user_id,
            operation_type="generation_batch_delete",
            target_type="generation",
            details=f"Batch deleted {deleted_count} generations (keep_favorites={keep_favorites})",
            metadata={
                "deleted_count": deleted_count,
                "keep_favorites": keep_favorites,
            },
            source="api",
        )
    except Exception as e:
        logger.warning(f"Failed to log batch deletion: {e}")

    return BatchDeleteResponse(
        success=True,
        deleted_count=deleted_count,
    )
