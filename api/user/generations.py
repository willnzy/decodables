"""Generations API - Generation history endpoints (v3).

@module api.user.generations
@version 3.0.0

Changes:
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
- PATCH /api/v2/user/generations/{id} - Update generation
- POST /api/v2/user/generations/{id}/favorite - Toggle favorite (deprecated)
- DELETE /api/v2/user/generations/{id} - Delete single generation
- POST /api/v2/user/generations/batch-delete - Clear history
- DELETE /api/v2/user/generations/batch - Clear history (deprecated)
"""

import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from typing import List, Dict, Any

from dependencies import get_current_user
from infrastructure.rate_limiter import limiter
from core.database import get_database_client
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

def get_generation_history_service() -> GenerationHistoryService:
    """Dependency injection factory for GenerationHistoryService."""
    db = get_database_client()
    return GenerationHistoryService(db_client=db)


# ==========================================
# Endpoints
# ==========================================

@router.get("/history")
@limiter.limit("60/minute")
async def get_generation_history(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    favorites_only: bool = False,
    user: dict = Depends(get_current_user),
    history_service: GenerationHistoryService = Depends(get_generation_history_service),  # v3.0.0: DI
) -> GenerationHistoryResponse:
    """
    Get user's image generation history.

    Returns paginated list of generated images with metadata.
    Supports filtering by favorites.

    Security:
    - User ownership enforced by Service
    - Pagination limits (1-100)

    Returns:
        GenerationHistoryResponse: Paginated generation history
    """
    # v3.0.0: Get history via Service (DDD compliant)
    try:
        generations, total = await history_service.get_history(
            user["id"], limit, offset, favorites_only
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
    user: dict = Depends(get_current_user),
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
            user["id"],
            generation_id,
            {"is_favorited": req.is_favorited}
        )
    except GenerationNotFoundException:
        raise HTTPException(404, "Generation not found")
    except Exception as e:
        logger.error(f"Update generation failed: {e}")
        raise HTTPException(500, "Failed to update generation")

    return FavoriteResponse(success=True, is_favorited=req.is_favorited)


@router.post("/{generation_id}/favorite", deprecated=True)
@limiter.limit("60/minute")
async def toggle_favorite(
    request: Request,
    generation_id: str,
    req: FavoriteRequest,
    user: dict = Depends(get_current_user),
    history_service: GenerationHistoryService = Depends(get_generation_history_service),  # v3.0.0: DI
) -> FavoriteResponse:
    """
    Toggle favorite status of a generated image.

    **DEPRECATED**: Use `PATCH /{generation_id}` instead.
    This endpoint will be removed in v4.0.

    Security:
    - UUID validation for generation_id
    - User ownership verified by Service
    """
    # v2.1.0: GEN-P0-1 - Validate generation_id format
    if not UUID_PATTERN.match(generation_id):
        raise HTTPException(400, "Invalid generation ID format")

    # v3.0.0: Call Service (same logic as PATCH)
    try:
        await history_service.update_generation(
            user["id"],
            generation_id,
            {"is_favorited": req.is_favorited}
        )
    except GenerationNotFoundException:
        raise HTTPException(404, "Generation not found")
    except Exception as e:
        logger.error(f"Toggle favorite failed: {e}")
        raise HTTPException(500, "Failed to toggle favorite")

    return FavoriteResponse(success=True, is_favorited=req.is_favorited)


@router.delete("/batch", deprecated=True)
@limiter.limit("10/minute")
async def clear_generation_history(
    request: Request,
    keep_favorites: bool = True,
    user: dict = Depends(get_current_user),
    history_service: GenerationHistoryService = Depends(get_generation_history_service),  # v3.0.0: DI
) -> BatchDeleteResponse:
    """
    Clear all generation history, optionally keeping favorites.

    **DEPRECATED**: Use `POST /batch-delete` instead.
    This endpoint will be removed in v4.0.

    **IMPORTANT**: This route must come BEFORE /{generation_id}
    otherwise "batch" will be matched as a generation_id.

    Security:
    - User ownership enforced by Service
    - Audit logging in Service
    """
    # v3.0.0: Batch delete via Service (DDD compliant)
    try:
        deleted_count = await history_service.batch_delete(user["id"], keep_favorites)
    except Exception as e:
        logger.error(f"Batch delete failed: {e}")
        raise HTTPException(500, "Failed to clear history")

    return BatchDeleteResponse(
        success=True,
        deleted_count=deleted_count,
    )


@router.delete("/{generation_id}")
@limiter.limit("30/minute")
async def delete_generation(
    request: Request,
    generation_id: str,
    user: dict = Depends(get_current_user),
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
        deleted_id = await history_service.delete_generation(user["id"], generation_id)
    except GenerationNotFoundException:
        raise HTTPException(404, "Generation not found")
    except Exception as e:
        logger.error(f"Delete generation failed: {e}")
        raise HTTPException(500, "Failed to delete generation")

    return DeleteResponse(success=True, deleted=deleted_id)


@router.post("/batch-delete")
@limiter.limit("10/minute")
async def batch_delete_generations(
    request: Request,
    keep_favorites: bool = True,
    user: dict = Depends(get_current_user),
    history_service: GenerationHistoryService = Depends(get_generation_history_service),  # v3.0.0: DI
) -> BatchDeleteResponse:
    """
    Clear all generation history, optionally keeping favorites.

    **Recommended**: Use POST for batch operations.

    Security:
    - User ownership enforced by Service
    - Audit logging in Service
    """
    # v3.0.0: Batch delete via Service (DDD compliant)
    try:
        deleted_count = await history_service.batch_delete(user["id"], keep_favorites)
    except Exception as e:
        logger.error(f"Batch delete failed: {e}")
        raise HTTPException(500, "Failed to clear history")

    return BatchDeleteResponse(
        success=True,
        deleted_count=deleted_count,
    )
