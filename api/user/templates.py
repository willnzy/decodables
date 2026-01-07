"""
Templates API - User prompt templates management (v2).

@module api.user.templates
@version 2.0.0

Endpoints:
Asset Prompt Templates (5W1H):
- GET /api/v2/user/templates/asset - List templates
- POST /api/v2/user/templates/asset - Create template
- PUT /api/v2/user/templates/asset/{id} - Update template
- DELETE /api/v2/user/templates/asset/{id} - Delete template
- POST /api/v2/user/templates/asset/{id}/use - Mark as used

Page Prompt Templates (AI Design Page):
- GET /api/v2/user/templates/page - List templates
- POST /api/v2/user/templates/page - Create template
- PUT /api/v2/user/templates/page/{id} - Update template
- DELETE /api/v2/user/templates/page/{id} - Delete template
- POST /api/v2/user/templates/page/{id}/use - Mark as used
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from dependencies import get_current_user
from services.db_service import supabase
from infrastructure.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/templates", tags=["user-templates-v2"])

MAX_TEMPLATES_PER_USER = 20


# ==========================================
# Request/Response Models
# ==========================================

class AssetTemplateCreate(BaseModel):
    """Create request for asset prompt template (5W1H)."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    who_type: Optional[str] = None
    who_custom: Optional[str] = None
    what_type: Optional[str] = None
    what_custom: Optional[str] = None
    where_type: Optional[str] = None
    where_custom: Optional[str] = None
    style: str = "cartoon"
    moods: List[str] = ["warm"]
    aspect_ratio: str = "square"
    creativity_level: float = Field(0.3, ge=0.0, le=1.0)
    negative_prompt: Optional[str] = None


class AssetTemplateUpdate(BaseModel):
    """Update request for asset prompt template."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    who_type: Optional[str] = None
    who_custom: Optional[str] = None
    what_type: Optional[str] = None
    what_custom: Optional[str] = None
    where_type: Optional[str] = None
    where_custom: Optional[str] = None
    style: Optional[str] = None
    moods: Optional[List[str]] = None
    aspect_ratio: Optional[str] = None
    creativity_level: Optional[float] = Field(None, ge=0.0, le=1.0)
    negative_prompt: Optional[str] = None


class PageTemplateCreate(BaseModel):
    """Create request for page prompt template."""
    name: str = Field(..., min_length=1, max_length=100)
    layout: str = "image_top"
    story_theme: Optional[str] = None
    main_character: Optional[str] = None
    style: str = "cartoon"
    creativity_level: float = Field(0.3, ge=0.0, le=1.0)
    negative_prompt: Optional[str] = None
    generation_mode: str = Field("guided", pattern="^(guided|flexible)$")


class PageTemplateUpdate(BaseModel):
    """Update request for page prompt template."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    layout: Optional[str] = None
    story_theme: Optional[str] = None
    main_character: Optional[str] = None
    style: Optional[str] = None
    creativity_level: Optional[float] = Field(None, ge=0.0, le=1.0)
    negative_prompt: Optional[str] = None
    generation_mode: Optional[str] = Field(None, pattern="^(guided|flexible)$")


class TemplateResponse(BaseModel):
    """Generic template response."""
    success: bool
    template: Optional[dict] = None


class TemplateListResponse(BaseModel):
    """Template list response."""
    templates: List[dict]


class TemplateUseResponse(BaseModel):
    """Template use response."""
    success: bool
    use_count: int


# ==========================================
# Asset Prompt Templates Endpoints
# ==========================================

@router.get("/asset")
@limiter.limit("60/minute")
async def list_asset_templates(
    request: Request,
    user: dict = Depends(get_current_user),
) -> TemplateListResponse:
    """Get user's saved asset prompt templates (5W1H)."""
    result = supabase.table("asset_prompt_templates") \
        .select("*") \
        .eq("user_id", user["id"]) \
        .order("use_count", desc=True) \
        .execute()

    return TemplateListResponse(templates=result.data or [])


@router.post("/asset")
@limiter.limit("30/minute")
async def create_asset_template(
    request: Request,
    req: AssetTemplateCreate,
    user: dict = Depends(get_current_user),
) -> TemplateResponse:
    """Create a new asset prompt template."""
    # Check template limit
    count_result = supabase.table("asset_prompt_templates") \
        .select("id", count="exact") \
        .eq("user_id", user["id"]) \
        .execute()

    if count_result.count and count_result.count >= MAX_TEMPLATES_PER_USER:
        raise HTTPException(
            400,
            f"Maximum {MAX_TEMPLATES_PER_USER} templates allowed. Delete some first.",
        )

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

    return TemplateResponse(
        success=True,
        template=result.data[0] if result.data else None,
    )


@router.put("/asset/{template_id}")
@limiter.limit("30/minute")
async def update_asset_template(
    request: Request,
    template_id: str,
    req: AssetTemplateUpdate,
    user: dict = Depends(get_current_user),
) -> TemplateResponse:
    """Update an existing asset prompt template."""
    update_data = {k: v for k, v in req.model_dump().items() if v is not None}

    if not update_data:
        raise HTTPException(400, "No fields to update")

    result = supabase.table("asset_prompt_templates") \
        .update(update_data) \
        .eq("id", template_id) \
        .eq("user_id", user["id"]) \
        .execute()

    if not result.data:
        raise HTTPException(404, "Template not found")

    return TemplateResponse(success=True, template=result.data[0])


@router.delete("/asset/{template_id}")
@limiter.limit("30/minute")
async def delete_asset_template(
    request: Request,
    template_id: str,
    user: dict = Depends(get_current_user),
) -> TemplateResponse:
    """Delete an asset prompt template."""
    supabase.table("asset_prompt_templates") \
        .delete() \
        .eq("id", template_id) \
        .eq("user_id", user["id"]) \
        .execute()

    return TemplateResponse(success=True)


@router.post("/asset/{template_id}/use")
@limiter.limit("60/minute")
async def use_asset_template(
    request: Request,
    template_id: str,
    user: dict = Depends(get_current_user),
) -> TemplateUseResponse:
    """Mark an asset prompt template as used (increments use_count)."""
    get_result = supabase.table("asset_prompt_templates") \
        .select("use_count") \
        .eq("id", template_id) \
        .eq("user_id", user["id"]) \
        .single() \
        .execute()

    if not get_result.data:
        raise HTTPException(404, "Template not found")

    current_count = get_result.data.get("use_count", 0)

    supabase.table("asset_prompt_templates") \
        .update({
            "use_count": current_count + 1,
            "last_used_at": datetime.now(timezone.utc).isoformat(),
        }) \
        .eq("id", template_id) \
        .eq("user_id", user["id"]) \
        .execute()

    return TemplateUseResponse(success=True, use_count=current_count + 1)


# ==========================================
# Page Prompt Templates Endpoints
# ==========================================

@router.get("/page")
@limiter.limit("60/minute")
async def list_page_templates(
    request: Request,
    user: dict = Depends(get_current_user),
) -> TemplateListResponse:
    """Get user's saved page prompt templates."""
    result = supabase.table("page_prompt_templates") \
        .select("*") \
        .eq("user_id", user["id"]) \
        .order("use_count", desc=True) \
        .execute()

    return TemplateListResponse(templates=result.data or [])


@router.post("/page")
@limiter.limit("30/minute")
async def create_page_template(
    request: Request,
    req: PageTemplateCreate,
    user: dict = Depends(get_current_user),
) -> TemplateResponse:
    """Create a new page prompt template."""
    count_result = supabase.table("page_prompt_templates") \
        .select("id", count="exact") \
        .eq("user_id", user["id"]) \
        .execute()

    if count_result.count and count_result.count >= MAX_TEMPLATES_PER_USER:
        raise HTTPException(
            400,
            f"Maximum {MAX_TEMPLATES_PER_USER} templates allowed. Delete some first.",
        )

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

    return TemplateResponse(
        success=True,
        template=result.data[0] if result.data else None,
    )


@router.put("/page/{template_id}")
@limiter.limit("30/minute")
async def update_page_template(
    request: Request,
    template_id: str,
    req: PageTemplateUpdate,
    user: dict = Depends(get_current_user),
) -> TemplateResponse:
    """Update an existing page prompt template."""
    update_data = {k: v for k, v in req.model_dump().items() if v is not None}

    if not update_data:
        raise HTTPException(400, "No fields to update")

    result = supabase.table("page_prompt_templates") \
        .update(update_data) \
        .eq("id", template_id) \
        .eq("user_id", user["id"]) \
        .execute()

    if not result.data:
        raise HTTPException(404, "Template not found")

    return TemplateResponse(success=True, template=result.data[0])


@router.delete("/page/{template_id}")
@limiter.limit("30/minute")
async def delete_page_template(
    request: Request,
    template_id: str,
    user: dict = Depends(get_current_user),
) -> TemplateResponse:
    """Delete a page prompt template."""
    supabase.table("page_prompt_templates") \
        .delete() \
        .eq("id", template_id) \
        .eq("user_id", user["id"]) \
        .execute()

    return TemplateResponse(success=True)


@router.post("/page/{template_id}/use")
@limiter.limit("60/minute")
async def use_page_template(
    request: Request,
    template_id: str,
    user: dict = Depends(get_current_user),
) -> TemplateUseResponse:
    """Mark a page prompt template as used (increments use_count)."""
    get_result = supabase.table("page_prompt_templates") \
        .select("use_count") \
        .eq("id", template_id) \
        .eq("user_id", user["id"]) \
        .single() \
        .execute()

    if not get_result.data:
        raise HTTPException(404, "Template not found")

    current_count = get_result.data.get("use_count", 0)

    supabase.table("page_prompt_templates") \
        .update({
            "use_count": current_count + 1,
            "last_used_at": datetime.now(timezone.utc).isoformat(),
        }) \
        .eq("id", template_id) \
        .eq("user_id", user["id"]) \
        .execute()

    return TemplateUseResponse(success=True, use_count=current_count + 1)
