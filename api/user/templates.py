"""
Templates API - User prompt templates management (v3.0.0).

@module api.user.templates
@version 3.0.0

Changes:
- v3.0.0: DDD architecture upgrade - Full CQRS pattern
  - Created TemplatesService v1.0.0 with 10 business methods
  - Added 2 Query Handlers (ListAsset, ListPage)
  - Added 8 Command Handlers (Create/Update/Delete/Use × 2 types)
  - Eliminated direct Supabase calls from API layer
  - Moved all business logic to Service layer
  - Improved testability and maintainability

- v2.1.0: Security improvements (inherited)
  - TPL-MEDIUM-1: Added template_id UUID format validation
  - TPL-MEDIUM-2: Added max_length to custom text fields
  - TPL-MEDIUM-3: Added max_length to moods list
  - TPL-LOW-1/2: Added style and layout enum validation
  - TPL-LOW-3: Added negative_prompt max_length

Endpoints:
Asset Prompt Templates (5W1H):
- GET /api/v3/user/templates/asset - List templates
- POST /api/v3/user/templates/asset - Create template
- PUT /api/v3/user/templates/asset/{id} - Update template
- DELETE /api/v3/user/templates/asset/{id} - Delete template
- POST /api/v3/user/templates/asset/{id}/use - Mark as used

Page Prompt Templates (AI Design Page):
- GET /api/v3/user/templates/page - List templates
- POST /api/v3/user/templates/page - Create template
- PUT /api/v3/user/templates/page/{id} - Update template
- DELETE /api/v3/user/templates/page/{id} - Delete template
- POST /api/v3/user/templates/page/{id}/use - Mark as used
"""

import logging
import re
from typing import Optional, List, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from dependencies import get_current_user
from infrastructure.rate_limiter import limiter
from container import get_container
from application.queries.templates import (
    ListAssetTemplatesQuery,
    ListPageTemplatesQuery,
)
from application.commands.templates import (
    CreateAssetTemplateCommand,
    UpdateAssetTemplateCommand,
    DeleteAssetTemplateCommand,
    UseAssetTemplateCommand,
    CreatePageTemplateCommand,
    UpdatePageTemplateCommand,
    DeletePageTemplateCommand,
    UsePageTemplateCommand,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/templates", tags=["user-templates-v3"])

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
    negative_prompt: Optional[str] = Field(None, max_length=MAX_NEGATIVE_PROMPT_LENGTH)  # v2.1.0


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
    """
    Get user's saved asset prompt templates (5W1H).

    v3.0.0: Now uses ListAssetTemplatesHandler (Container pattern).
    """
    container = get_container()
    handler = container.list_asset_templates_handler

    query = ListAssetTemplatesQuery(user_id=user["id"])
    result = await handler.handle(query)

    return TemplateListResponse(templates=result.templates)


@router.post("/asset")
@limiter.limit("30/minute")
async def create_asset_template(
    request: Request,
    req: AssetTemplateCreate,
    user: dict = Depends(get_current_user),
) -> TemplateResponse:
    """
    Create a new asset prompt template.

    v3.0.0: Now uses CreateAssetTemplateHandler (Container pattern).
    Business logic (template limit check) moved to Service layer.
    """
    container = get_container()
    handler = container.create_asset_template_handler

    template_data = {
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

    command = CreateAssetTemplateCommand(
        user_id=user["id"],
        template_data=template_data
    )
    result = await handler.handle(command)

    return TemplateResponse(success=True, template=result.template)


@router.put("/asset/{template_id}")
@limiter.limit("30/minute")
async def update_asset_template(
    request: Request,
    template_id: str,
    req: AssetTemplateUpdate,
    user: dict = Depends(get_current_user),
) -> TemplateResponse:
    """
    Update an existing asset prompt template.

    v3.0.0: Now uses UpdateAssetTemplateHandler (Container pattern).
    """
    # v2.1.0: TPL-MEDIUM-1 - Validate template_id format
    validate_template_id(template_id)

    update_data = {k: v for k, v in req.model_dump().items() if v is not None}

    if not update_data:
        raise HTTPException(400, "No fields to update")

    container = get_container()
    handler = container.update_asset_template_handler

    command = UpdateAssetTemplateCommand(
        template_id=template_id,
        user_id=user["id"],
        updates=update_data
    )
    result = await handler.handle(command)

    return TemplateResponse(success=True, template=result.template)


@router.delete("/asset/{template_id}")
@limiter.limit("30/minute")
async def delete_asset_template(
    request: Request,
    template_id: str,
    user: dict = Depends(get_current_user),
) -> TemplateResponse:
    """
    Delete an asset prompt template.

    v3.0.0: Now uses DeleteAssetTemplateHandler (Container pattern).
    """
    # v2.1.0: TPL-MEDIUM-1 - Validate template_id format
    validate_template_id(template_id)

    container = get_container()
    handler = container.delete_asset_template_handler

    command = DeleteAssetTemplateCommand(
        template_id=template_id,
        user_id=user["id"]
    )
    result = await handler.handle(command)

    return TemplateResponse(success=result.success)


@router.post("/asset/{template_id}/use")
@limiter.limit("60/minute")
async def use_asset_template(
    request: Request,
    template_id: str,
    user: dict = Depends(get_current_user),
) -> TemplateUseResponse:
    """
    Mark an asset template as used (increments use_count).

    v3.0.0: Now uses UseAssetTemplateHandler (Container pattern).
    Business logic (use count increment) moved to Service layer.
    """
    # v2.1.0: TPL-MEDIUM-1 - Validate template_id format
    validate_template_id(template_id)

    container = get_container()
    handler = container.use_asset_template_handler

    command = UseAssetTemplateCommand(
        template_id=template_id,
        user_id=user["id"]
    )
    result = await handler.handle(command)

    return TemplateUseResponse(success=True, use_count=result.new_use_count)


# ==========================================
# Page Prompt Templates Endpoints
# ==========================================

@router.get("/page")
@limiter.limit("60/minute")
async def list_page_templates(
    request: Request,
    user: dict = Depends(get_current_user),
) -> TemplateListResponse:
    """
    Get user's saved page prompt templates.

    v3.0.0: Now uses ListPageTemplatesHandler (Container pattern).
    """
    container = get_container()
    handler = container.list_page_templates_handler

    query = ListPageTemplatesQuery(user_id=user["id"])
    result = await handler.handle(query)

    return TemplateListResponse(templates=result.templates)


@router.post("/page")
@limiter.limit("30/minute")
async def create_page_template(
    request: Request,
    req: PageTemplateCreate,
    user: dict = Depends(get_current_user),
) -> TemplateResponse:
    """
    Create a new page prompt template.

    v3.0.0: Now uses CreatePageTemplateHandler (Container pattern).
    Business logic (template limit check) moved to Service layer.
    """
    container = get_container()
    handler = container.create_page_template_handler

    template_data = {
        "name": req.name,
        "layout": req.layout,
        "story_theme": req.story_theme,
        "main_character": req.main_character,
        "style": req.style,
        "creativity_level": req.creativity_level,
        "negative_prompt": req.negative_prompt,
        "generation_mode": req.generation_mode,
    }

    command = CreatePageTemplateCommand(
        user_id=user["id"],
        template_data=template_data
    )
    result = await handler.handle(command)

    return TemplateResponse(success=True, template=result.template)


@router.put("/page/{template_id}")
@limiter.limit("30/minute")
async def update_page_template(
    request: Request,
    template_id: str,
    req: PageTemplateUpdate,
    user: dict = Depends(get_current_user),
) -> TemplateResponse:
    """
    Update an existing page prompt template.

    v3.0.0: Now uses UpdatePageTemplateHandler (Container pattern).
    """
    # v2.1.0: TPL-MEDIUM-1 - Validate template_id format
    validate_template_id(template_id)

    update_data = {k: v for k, v in req.model_dump().items() if v is not None}

    if not update_data:
        raise HTTPException(400, "No fields to update")

    container = get_container()
    handler = container.update_page_template_handler

    command = UpdatePageTemplateCommand(
        template_id=template_id,
        user_id=user["id"],
        updates=update_data
    )
    result = await handler.handle(command)

    return TemplateResponse(success=True, template=result.template)


@router.delete("/page/{template_id}")
@limiter.limit("30/minute")
async def delete_page_template(
    request: Request,
    template_id: str,
    user: dict = Depends(get_current_user),
) -> TemplateResponse:
    """
    Delete a page prompt template.

    v3.0.0: Now uses DeletePageTemplateHandler (Container pattern).
    """
    # v2.1.0: TPL-MEDIUM-1 - Validate template_id format
    validate_template_id(template_id)

    container = get_container()
    handler = container.delete_page_template_handler

    command = DeletePageTemplateCommand(
        template_id=template_id,
        user_id=user["id"]
    )
    result = await handler.handle(command)

    return TemplateResponse(success=result.success)


@router.post("/page/{template_id}/use")
@limiter.limit("60/minute")
async def use_page_template(
    request: Request,
    template_id: str,
    user: dict = Depends(get_current_user),
) -> TemplateUseResponse:
    """
    Mark a page template as used (increments use_count).

    v3.0.0: Now uses UsePageTemplateHandler (Container pattern).
    Business logic (use count increment) moved to Service layer.
    """
    # v2.1.0: TPL-MEDIUM-1 - Validate template_id format
    validate_template_id(template_id)

    container = get_container()
    handler = container.use_page_template_handler

    command = UsePageTemplateCommand(
        template_id=template_id,
        user_id=user["id"]
    )
    result = await handler.handle(command)

    return TemplateUseResponse(success=True, use_count=result.new_use_count)
