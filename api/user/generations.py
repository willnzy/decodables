"""Generations API - Generation history endpoints (v2).

@module api.user.generations
@version 2.1.0

Changes:
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
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel

from dependencies import get_current_user
from infrastructure.rate_limiter import limiter
from infrastructure.logging.activity_logger import log_activity

from core.database import get_supabase_client
supabase = get_supabase_client()

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
) -> GenerationHistoryResponse:
    """
    Get user's image generation history.

    Returns paginated list of generated images with metadata.
    Supports filtering by favorites.
    """
    query = supabase.table("user_generations") \
        .select("*") \
        .eq("user_id", user["id"]) \
        .order("created_at", desc=True)

    if favorites_only:
        query = query.eq("is_favorited", True)

    result = query.range(offset, offset + limit - 1).execute()

    # Get total count
    count_query = supabase.table("user_generations") \
        .select("id", count="exact") \
        .eq("user_id", user["id"])
    if favorites_only:
        count_query = count_query.eq("is_favorited", True)
    count_result = count_query.execute()

    return GenerationHistoryResponse(
        generations=result.data or [],
        total=count_result.count if count_result.count else len(result.data or []),
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
) -> FavoriteResponse:
    """
    Update generation properties (favorite status, etc.).

    **Recommended**: Use PATCH for partial resource updates.
    """
    # v2.1.0: GEN-P0-1 - Validate generation_id format
    if not UUID_PATTERN.match(generation_id):
        raise HTTPException(400, "Invalid generation ID format")

    result = supabase.table("user_generations") \
        .update({"is_favorited": req.is_favorited}) \
        .eq("id", generation_id) \
        .eq("user_id", user["id"]) \
        .execute()

    if not result.data:
        raise HTTPException(404, "Generation not found")

    return FavoriteResponse(success=True, is_favorited=req.is_favorited)


@router.post("/{generation_id}/favorite", deprecated=True)
@limiter.limit("60/minute")
async def toggle_favorite(
    request: Request,
    generation_id: str,
    req: FavoriteRequest,
    user: dict = Depends(get_current_user),
) -> FavoriteResponse:
    """
    Toggle favorite status of a generated image.

    **DEPRECATED**: Use `PATCH /{generation_id}` instead.
    This endpoint will be removed in v3.0.
    """
    # v2.1.0: GEN-P0-1 - Validate generation_id format
    if not UUID_PATTERN.match(generation_id):
        raise HTTPException(400, "Invalid generation ID format")

    result = supabase.table("user_generations") \
        .update({"is_favorited": req.is_favorited}) \
        .eq("id", generation_id) \
        .eq("user_id", user["id"]) \
        .execute()

    if not result.data:
        raise HTTPException(404, "Generation not found")

    return FavoriteResponse(success=True, is_favorited=req.is_favorited)


@router.delete("/batch", deprecated=True)
@limiter.limit("10/minute")
async def clear_generation_history(
    request: Request,
    keep_favorites: bool = True,
    user: dict = Depends(get_current_user),
) -> BatchDeleteResponse:
    """
    Clear all generation history, optionally keeping favorites.

    **DEPRECATED**: Use `POST /batch-delete` instead.
    This endpoint will be removed in v3.0.

    **IMPORTANT**: This route must come BEFORE /{generation_id}
    otherwise "batch" will be matched as a generation_id.
    """
    query = supabase.table("user_generations") \
        .delete() \
        .eq("user_id", user["id"])

    if keep_favorites:
        query = query.eq("is_favorited", False)

    result = query.execute()
    deleted_count = len(result.data) if result.data else 0

    # v2.1.0: GEN-MEDIUM-2 - Add audit logging
    log_activity(user["id"], "batch_delete_generations", {
        "keep_favorites": keep_favorites,
        "deleted_count": deleted_count,
    })

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
) -> DeleteResponse:
    """Delete a generated image from history."""
    # v2.1.0: GEN-P0-1 - Validate generation_id format
    if not UUID_PATTERN.match(generation_id):
        raise HTTPException(400, "Invalid generation ID format")

    result = supabase.table("user_generations") \
        .delete() \
        .eq("id", generation_id) \
        .eq("user_id", user["id"]) \
        .execute()

    # v2.1.0: GEN-MEDIUM-1 - Check if record was actually deleted
    if not result.data:
        raise HTTPException(404, "Generation not found")

    # v2.1.0: GEN-MEDIUM-2 - Add audit logging
    log_activity(user["id"], "delete_generation", {"generation_id": generation_id})

    return DeleteResponse(success=True, deleted=generation_id)


@router.post("/batch-delete")
@limiter.limit("10/minute")
async def batch_delete_generations(
    request: Request,
    keep_favorites: bool = True,
    user: dict = Depends(get_current_user),
) -> BatchDeleteResponse:
    """
    Clear all generation history, optionally keeping favorites.

    **Recommended**: Use POST for batch operations.
    """
    query = supabase.table("user_generations") \
        .delete() \
        .eq("user_id", user["id"])

    if keep_favorites:
        query = query.eq("is_favorited", False)

    result = query.execute()
    deleted_count = len(result.data or [])

    # v2.1.0: GEN-MEDIUM-2 - Add audit logging
    log_activity(user["id"], "batch_delete_generations", {
        "keep_favorites": keep_favorites,
        "deleted_count": deleted_count,
    })

    return BatchDeleteResponse(
        success=True,
        deleted_count=deleted_count,
    )
