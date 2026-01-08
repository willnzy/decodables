"""
Templates API - User prompt templates management (v2).

@module api.user.templates
@version 2.1.0

Changes:
- v2.1.0: Security improvements
  - TPL-MEDIUM-1: Added template_id UUID format validation
  - TPL-MEDIUM-2: Added max_length to custom text fields
  - TPL-MEDIUM-3: Added max_length to moods list
  - TPL-LOW-1/2: Added style and layout enum validation
  - TPL-LOW-3: Added negative_prompt max_length

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
import re
from datetime import datetime, timezone
from typing import Optional, List, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from dependencies import get_current_user
from infrastructure.rate_limiter import limiter

from core.database import get_supabase_client
supabase = get_supabase_client()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/templates", tags=["user-templates-v2"])

MAX_TEMPLATES_PER_USER = 20

# ==========================================
# Constants (v2.1.0)
# ==========================================

# v2.1.0: TPL-MEDIUM-1 - UUID validation pattern
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE
)

# v2.1.0: TPL-LOW-1 - Valid style options
VALID_STYLES = Literal["cartoon", "realistic", "watercolor", "sketch", "flat", "3d"]

# v2.1.0: TPL-LOW-2 - Valid layout options
VALID_LAYOUTS = Literal["image_top", "image_bottom", "image_left", "image_right", "full_image"]

# v2.1.0: TPL-MEDIUM-3 - Max moods list size
MAX_MOODS = 10

# v2.1.0: TPL-MEDIUM-2 - Max custom text length
MAX_CUSTOM_TEXT_LENGTH = 500

# v2.1.0: TPL-LOW-3 - Max negative prompt length
MAX_NEGATIVE_PROMPT_LENGTH = 1000


def validate_template_id(template_id: str) -> None:
    """v2.1.0: TPL-MEDIUM-1 - Validate template_id is UUID format."""
    if not UUID_PATTERN.match(template_id):
        raise HTTPException(400, "Invalid template ID format")


# ==========================================
# Request/Response Models
# ==========================================

class AssetTemplateCreate(BaseModel):
    """Create request for asset prompt template (5W1H)."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    who_type: Optional[str] = Field(None, max_length=50)  # v2.1.0: TPL-MEDIUM-2
    who_custom: Optional[str] = Field(None, max_length=MAX_CUSTOM_TEXT_LENGTH)  # v2.1.0
    what_type: Optional[str] = Field(None, max_length=50)  # v2.1.0
    what_custom: Optional[str] = Field(None, max_length=MAX_CUSTOM_TEXT_LENGTH)  # v2.1.0
    where_type: Optional[str] = Field(None, max_length=50)  # v2.1.0
    where_custom: Optional[str] = Field(None, max_length=MAX_CUSTOM_TEXT_LENGTH)  # v2.1.0
    style: str = Field("cartoon", max_length=50)  # v2.1.0: Allow flexibility but limit length
    moods: List[str] = Field(default=["warm"], max_length=MAX_MOODS)  # v2.1.0: TPL-MEDIUM-3
    aspect_ratio: str = Field("square", max_length=20)  # v2.1.0
    creativity_level: float = Field(0.3, ge=0.0, le=1.0)
    negative_prompt: Optional[str] = Field(None, max_length=MAX_NEGATIVE_PROMPT_LENGTH)  # v2.1.0: TPL-LOW-3

    # v2.1.0: Validate individual mood strings
    @field_validator('moods')
    @classmethod
    def validate_moods(cls, v):
        if v:
            for mood in v:
                if len(mood) > 50:
                    raise ValueError("Each mood must be 50 characters or less")
        return v


class AssetTemplateUpdate(BaseModel):
    """Update request for asset prompt template."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    who_type: Optional[str] = Field(None, max_length=50)  # v2.1.0
    who_custom: Optional[str] = Field(None, max_length=MAX_CUSTOM_TEXT_LENGTH)  # v2.1.0
    what_type: Optional[str] = Field(None, max_length=50)  # v2.1.0
    what_custom: Optional[str] = Field(None, max_length=MAX_CUSTOM_TEXT_LENGTH)  # v2.1.0
    where_type: Optional[str] = Field(None, max_length=50)  # v2.1.0
    where_custom: Optional[str] = Field(None, max_length=MAX_CUSTOM_TEXT_LENGTH)  # v2.1.0
    style: Optional[str] = Field(None, max_length=50)  # v2.1.0
    moods: Optional[List[str]] = Field(None, max_length=MAX_MOODS)  # v2.1.0
    aspect_ratio: Optional[str] = Field(None, max_length=20)  # v2.1.0
    creativity_level: Optional[float] = Field(None, ge=0.0, le=1.0)
    negative_prompt: Optional[str] = Field(None, max_length=MAX_NEGATIVE_PROMPT_LENGTH)  # v2.1.0

    # v2.1.0: Validate individual mood strings
    @field_validator('moods')
    @classmethod
    def validate_moods(cls, v):
        if v:
            for mood in v:
                if len(mood) > 50:
                    raise ValueError("Each mood must be 50 characters or less")
        return v


class PageTemplateCreate(BaseModel):
    """Create request for page prompt template."""
    name: str = Field(..., min_length=1, max_length=100)
    layout: str = Field("image_top", max_length=50)  # v2.1.0
    story_theme: Optional[str] = Field(None, max_length=MAX_CUSTOM_TEXT_LENGTH)  # v2.1.0
    main_character: Optional[str] = Field(None, max_length=MAX_CUSTOM_TEXT_LENGTH)  # v2.1.0
    style: str = Field("cartoon", max_length=50)  # v2.1.0
    creativity_level: float = Field(0.3, ge=0.0, le=1.0)
    negative_prompt: Optional[str] = Field(None, max_length=MAX_NEGATIVE_PROMPT_LENGTH)  # v2.1.0
    generation_mode: str = Field("guided", pattern="^(guided|flexible)$")


class PageTemplateUpdate(BaseModel):
    """Update request for page prompt template."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    layout: Optional[str] = Field(None, max_length=50)  # v2.1.0
    story_theme: Optional[str] = Field(None, max_length=MAX_CUSTOM_TEXT_LENGTH)  # v2.1.0
    main_character: Optional[str] = Field(None, max_length=MAX_CUSTOM_TEXT_LENGTH)  # v2.1.0
    style: Optional[str] = Field(None, max_length=50)  # v2.1.0
    creativity_level: Optional[float] = Field(None, ge=0.0, le=1.0)
    negative_prompt: Optional[str] = Field(None, max_length=MAX_NEGATIVE_PROMPT_LENGTH)  # v2.1.0
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
    # v2.1.0: TPL-MEDIUM-1 - Validate template_id format
    validate_template_id(template_id)

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
    # v2.1.0: TPL-MEDIUM-1 - Validate template_id format
    validate_template_id(template_id)

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
    # v2.1.0: TPL-MEDIUM-1 - Validate template_id format
    validate_template_id(template_id)

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
    # v2.1.0: TPL-MEDIUM-1 - Validate template_id format
    validate_template_id(template_id)

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
    # v2.1.0: TPL-MEDIUM-1 - Validate template_id format
    validate_template_id(template_id)

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
    # v2.1.0: TPL-MEDIUM-1 - Validate template_id format
    validate_template_id(template_id)

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
