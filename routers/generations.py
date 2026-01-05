"""
Generations Router - User generation history management

@module routers.generations
@version 3.24

Endpoints:
- GET /api/generations/history - Get generation history
- POST /api/generations/favorite - Toggle favorite
- DELETE /api/generations/{generation_id} - Delete single generation
- DELETE /api/generations/batch - Clear history (batch delete)
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel

from services.db_service import supabase
from services.rate_limiter import limiter
from dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/generations", tags=["generations"])


# ==========================================
# Request Models
# ==========================================

class FavoriteRequest(BaseModel):
    generation_id: str
    is_favorited: bool


# ==========================================
# Generation History Endpoints
# ==========================================

@router.get("/history")
@limiter.limit("60/minute")
async def get_generation_history(
    request: Request,
    limit: int = 20,
    offset: int = 0,
    favorites_only: bool = False,
    user: dict = Depends(get_current_user)
):
    """
    Get user's image generation history.
    
    Returns paginated list of generated images with metadata.
    Supports filtering by favorites.
    """
    try:
        # Clamp limit
        limit = max(1, min(100, limit))
        
        query = supabase.table("user_generations") \
            .select("*") \
            .eq("user_id", user["id"]) \
            .order("created_at", desc=True)
        
        if favorites_only:
            query = query.eq("is_favorited", True)
        
        result = query.range(offset, offset + limit - 1).execute()
        
        # Get total count for pagination
        count_query = supabase.table("user_generations") \
            .select("id", count="exact") \
            .eq("user_id", user["id"])
        if favorites_only:
            count_query = count_query.eq("is_favorited", True)
        count_result = count_query.execute()
        
        return {
            "generations": result.data,
            "total": count_result.count if count_result.count else len(result.data),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Failed to fetch generation history: {e}")
        raise HTTPException(500, f"Failed to fetch history: {str(e)}")


@router.post("/favorite")
@limiter.limit("60/minute")
async def toggle_favorite(
    request: Request,
    req: FavoriteRequest,
    user: dict = Depends(get_current_user)
):
    """Toggle favorite status of a generated image."""
    try:
        result = supabase.table("user_generations") \
            .update({"is_favorited": req.is_favorited}) \
            .eq("id", req.generation_id) \
            .eq("user_id", user["id"]) \
            .execute()
        
        if not result.data:
            raise HTTPException(404, "Generation not found")
        
        return {"success": True, "is_favorited": req.is_favorited}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to toggle favorite: {e}")
        raise HTTPException(500, f"Failed to update: {str(e)}")


@router.delete("/{generation_id}")
@limiter.limit("30/minute")
async def delete_generation(
    request: Request,
    generation_id: str,
    user: dict = Depends(get_current_user)
):
    """Delete a generated image from history."""
    try:
        result = supabase.table("user_generations") \
            .delete() \
            .eq("id", generation_id) \
            .eq("user_id", user["id"]) \
            .execute()
        
        return {"success": True, "deleted": generation_id}
    except Exception as e:
        logger.error(f"Failed to delete generation: {e}")
        raise HTTPException(500, f"Failed to delete: {str(e)}")


@router.delete("/batch")
@limiter.limit("10/minute")
async def clear_generation_history(
    request: Request,
    keep_favorites: bool = True,
    user: dict = Depends(get_current_user)
):
    """Clear all generation history, optionally keeping favorites."""
    try:
        query = supabase.table("user_generations") \
            .delete() \
            .eq("user_id", user["id"])
        
        if keep_favorites:
            query = query.eq("is_favorited", False)
        
        result = query.execute()
        
        return {"success": True, "deleted_count": len(result.data) if result.data else 0}
    except Exception as e:
        logger.error(f"Failed to clear history: {e}")
        raise HTTPException(500, f"Failed to clear: {str(e)}")
