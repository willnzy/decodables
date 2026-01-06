"""
Templates Router - User prompt templates management

@module routers.templates
@version 3.24

Endpoints:
Asset Prompt Templates (5W1H):
- GET /api/asset-prompt/templates - List templates
- POST /api/asset-prompt/templates - Create template
- PUT /api/asset-prompt/templates/{id} - Update template
- DELETE /api/asset-prompt/templates/{id} - Delete template
- POST /api/asset-prompt/templates/{id}/use - Mark as used

Page Prompt Templates (AI Design Page):
- GET /api/page-prompt/templates - List templates
- POST /api/page-prompt/templates - Create template
- PUT /api/page-prompt/templates/{id} - Update template
- DELETE /api/page-prompt/templates/{id} - Delete template
- POST /api/page-prompt/templates/{id}/use - Mark as used
"""

import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel

from services.db_service import supabase
from services.rate_limiter import limiter
from dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["templates"])


# ==========================================
# Request Models - Asset Prompt Templates
# ==========================================

class AssetPromptTemplateCreate(BaseModel):
    """Create request for asset prompt template (5W1H naming convention)."""
    name: str
    description: Optional[str] = None
    who_type: Optional[str] = None
    who_custom: Optional[str] = None
    what_type: Optional[str] = None
    what_custom: Optional[str] = None
    where_type: Optional[str] = None
    where_custom: Optional[str] = None
    style: Optional[str] = "cartoon"
    moods: Optional[List[str]] = ["warm"]
    aspect_ratio: Optional[str] = "square"
    creativity_level: Optional[float] = 0.3
    negative_prompt: Optional[str] = None


class AssetPromptTemplateUpdate(BaseModel):
    """Update request for asset prompt template (5W1H naming convention)."""
    name: Optional[str] = None
    description: Optional[str] = None
    who_type: Optional[str] = None
    who_custom: Optional[str] = None
    what_type: Optional[str] = None
    what_custom: Optional[str] = None
    where_type: Optional[str] = None
    where_custom: Optional[str] = None
    style: Optional[str] = None
    moods: Optional[List[str]] = None
    aspect_ratio: Optional[str] = None
    creativity_level: Optional[float] = None
    negative_prompt: Optional[str] = None


# ==========================================
# Request Models - Page Prompt Templates
# ==========================================

class PagePromptTemplateCreate(BaseModel):
    """Create request for page prompt template."""
    name: str
    layout: Optional[str] = "image_top"
    story_theme: Optional[str] = None
    main_character: Optional[str] = None
    style: Optional[str] = "cartoon"
    creativity_level: Optional[float] = 0.3
    negative_prompt: Optional[str] = None
    generation_mode: Optional[str] = "guided"


class PagePromptTemplateUpdate(BaseModel):
    """Update request for page prompt template."""
    name: Optional[str] = None
    layout: Optional[str] = None
    story_theme: Optional[str] = None
    main_character: Optional[str] = None
    style: Optional[str] = None
    creativity_level: Optional[float] = None
    negative_prompt: Optional[str] = None
    generation_mode: Optional[str] = None


# ==========================================
# Asset Prompt Templates Endpoints
# ==========================================

@router.get("/api/asset-prompt/templates")
@limiter.limit("60/minute")
async def get_asset_prompt_templates(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """Get user's saved asset prompt templates."""
    try:
        result = supabase.table("asset_prompt_templates") \
            .select("*") \
            .eq("user_id", user["id"]) \
            .order("use_count", desc=True) \
            .execute()
        
        return {"templates": result.data}
    except Exception as e:
        logger.error(f"Failed to fetch asset prompt templates: {e}")
        raise HTTPException(500, f"Failed to fetch templates: {str(e)}")


@router.post("/api/asset-prompt/templates")
@limiter.limit("30/minute")
async def create_asset_prompt_template(
    request: Request,
    req: AssetPromptTemplateCreate,
    user: dict = Depends(get_current_user)
):
    """Create a new asset prompt template."""
    try:
        # Check template limit (max 20 per user)
        count_result = supabase.table("asset_prompt_templates") \
            .select("id", count="exact") \
            .eq("user_id", user["id"]) \
            .execute()
        
        if count_result.count and count_result.count >= 20:
            raise HTTPException(400, "Maximum 20 templates allowed. Please delete some first.")
        
        template_data = {
            "user_id": user["id"],
            "name": req.name,
            "description": req.description,
            "who_type": req.who_type,
            "who_custom": req.who_custom,
            "what_type": req.what_type,
            "what_custom": req.what_custom,
            "where_type": req.where_type,
            "where_custom": req.where_custom,
            "style": req.style,
            "moods": req.moods,
            "aspect_ratio": req.aspect_ratio,
            "creativity_level": req.creativity_level,
            "negative_prompt": req.negative_prompt,
        }
        
        result = supabase.table("asset_prompt_templates") \
            .insert(template_data) \
            .execute()
        
        return {"success": True, "template": result.data[0] if result.data else None}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create asset prompt template: {e}")
        raise HTTPException(500, f"Failed to create template: {str(e)}")


@router.put("/api/asset-prompt/templates/{template_id}")
@limiter.limit("30/minute")
async def update_asset_prompt_template(
    request: Request,
    template_id: str,
    req: AssetPromptTemplateUpdate,
    user: dict = Depends(get_current_user)
):
    """Update an existing asset prompt template."""
    try:
        # Build update data, excluding None values
        update_data = {k: v for k, v in req.dict().items() if v is not None}
        
        if not update_data:
            raise HTTPException(400, "No fields to update")
        
        result = supabase.table("asset_prompt_templates") \
            .update(update_data) \
            .eq("id", template_id) \
            .eq("user_id", user["id"]) \
            .execute()
        
        if not result.data:
            raise HTTPException(404, "Template not found")
        
        return {"success": True, "template": result.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update asset prompt template: {e}")
        raise HTTPException(500, f"Failed to update template: {str(e)}")


@router.delete("/api/asset-prompt/templates/{template_id}")
@limiter.limit("30/minute")
async def delete_asset_prompt_template(
    request: Request,
    template_id: str,
    user: dict = Depends(get_current_user)
):
    """Delete an asset prompt template."""
    try:
        result = supabase.table("asset_prompt_templates") \
            .delete() \
            .eq("id", template_id) \
            .eq("user_id", user["id"]) \
            .execute()
        
        return {"success": True, "deleted": template_id}
    except Exception as e:
        logger.error(f"Failed to delete asset prompt template: {e}")
        raise HTTPException(500, f"Failed to delete template: {str(e)}")


@router.post("/api/asset-prompt/templates/{template_id}/use")
@limiter.limit("60/minute")
async def use_asset_prompt_template(
    request: Request,
    template_id: str,
    user: dict = Depends(get_current_user)
):
    """Mark an asset prompt template as used (increments use_count)."""
    try:
        # First get current count
        get_result = supabase.table("asset_prompt_templates") \
            .select("use_count") \
            .eq("id", template_id) \
            .eq("user_id", user["id"]) \
            .single() \
            .execute()
        
        if not get_result.data:
            raise HTTPException(404, "Template not found")
        
        current_count = get_result.data.get("use_count", 0)
        
        # Update count and last_used_at
        result = supabase.table("asset_prompt_templates") \
            .update({
                "use_count": current_count + 1,
                "last_used_at": datetime.utcnow().isoformat()
            }) \
            .eq("id", template_id) \
            .eq("user_id", user["id"]) \
            .execute()
        
        return {"success": True, "use_count": current_count + 1}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update asset prompt template usage: {e}")
        raise HTTPException(500, f"Failed to update: {str(e)}")


# ==========================================
# Page Prompt Templates Endpoints
# ==========================================

@router.get("/api/page-prompt/templates")
@limiter.limit("60/minute")
async def get_page_prompt_templates(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """Get user's saved page prompt templates."""
    try:
        result = supabase.table("page_prompt_templates") \
            .select("*") \
            .eq("user_id", user["id"]) \
            .order("use_count", desc=True) \
            .execute()
        
        return {"templates": result.data}
    except Exception as e:
        logger.error(f"Failed to fetch page prompt templates: {e}")
        raise HTTPException(500, f"Failed to fetch templates: {str(e)}")


@router.post("/api/page-prompt/templates")
@limiter.limit("30/minute")
async def create_page_prompt_template(
    request: Request,
    req: PagePromptTemplateCreate,
    user: dict = Depends(get_current_user)
):
    """Create a new page prompt template."""
    try:
        # Check template limit (max 20 per user)
        count_result = supabase.table("page_prompt_templates") \
            .select("id", count="exact") \
            .eq("user_id", user["id"]) \
            .execute()
        
        if count_result.count and count_result.count >= 20:
            raise HTTPException(400, "Maximum 20 templates allowed. Please delete some first.")
        
        template_data = {
            "user_id": user["id"],
            "name": req.name,
            "layout": req.layout,
            "story_theme": req.story_theme,
            "main_character": req.main_character,
            "style": req.style,
            "creativity_level": req.creativity_level,
            "negative_prompt": req.negative_prompt,
            "generation_mode": req.generation_mode,
        }
        
        result = supabase.table("page_prompt_templates") \
            .insert(template_data) \
            .execute()
        
        return {"success": True, "template": result.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create page prompt template: {e}")
        raise HTTPException(500, f"Failed to create template: {str(e)}")


@router.put("/api/page-prompt/templates/{template_id}")
@limiter.limit("30/minute")
async def update_page_prompt_template(
    request: Request,
    template_id: str,
    req: PagePromptTemplateUpdate,
    user: dict = Depends(get_current_user)
):
    """Update an existing page prompt template."""
    try:
        # Build update data, excluding None values
        update_data = {k: v for k, v in req.dict().items() if v is not None}
        
        if not update_data:
            raise HTTPException(400, "No fields to update")
        
        result = supabase.table("page_prompt_templates") \
            .update(update_data) \
            .eq("id", template_id) \
            .eq("user_id", user["id"]) \
            .execute()
        
        if not result.data:
            raise HTTPException(404, "Template not found")
        
        return {"success": True, "template": result.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update page prompt template: {e}")
        raise HTTPException(500, f"Failed to update template: {str(e)}")


@router.delete("/api/page-prompt/templates/{template_id}")
@limiter.limit("30/minute")
async def delete_page_prompt_template(
    request: Request,
    template_id: str,
    user: dict = Depends(get_current_user)
):
    """Delete a page prompt template."""
    try:
        result = supabase.table("page_prompt_templates") \
            .delete() \
            .eq("id", template_id) \
            .eq("user_id", user["id"]) \
            .execute()
        
        return {"success": True, "deleted": template_id}
    except Exception as e:
        logger.error(f"Failed to delete page prompt template: {e}")
        raise HTTPException(500, f"Failed to delete template: {str(e)}")


@router.post("/api/page-prompt/templates/{template_id}/use")
@limiter.limit("60/minute")
async def use_page_prompt_template(
    request: Request,
    template_id: str,
    user: dict = Depends(get_current_user)
):
    """Mark a page prompt template as used (increments use_count)."""
    try:
        # First get current count
        get_result = supabase.table("page_prompt_templates") \
            .select("use_count") \
            .eq("id", template_id) \
            .eq("user_id", user["id"]) \
            .single() \
            .execute()
        
        if not get_result.data:
            raise HTTPException(404, "Template not found")
        
        current_count = get_result.data.get("use_count", 0)
        
        # Update count and last_used_at
        result = supabase.table("page_prompt_templates") \
            .update({
                "use_count": current_count + 1,
                "last_used_at": datetime.utcnow().isoformat()
            }) \
            .eq("id", template_id) \
            .eq("user_id", user["id"]) \
            .execute()
        
        return {"success": True, "use_count": current_count + 1}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update page prompt template usage: {e}")
        raise HTTPException(500, f"Failed to update: {str(e)}")
