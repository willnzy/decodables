"""
Generation Schemas - AI generation related models

@module schemas.generation
@version 1.2.0

Changes in v1.2.0:
- GI-P0-001: Added Field constraints to ImageGenRequest for security
- Added max_length to all string fields
- Added value range validation (num_images, creativity_level, reference_strength)

Changes in v1.1.0:
- GS-P0-2: Added length limits to StoryGenRequest (topic, style)
- GI-P0-1: Added min_length validation to ImageGenRequest prompts
"""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class StoryGenRequest(BaseModel):
    """Story generation request."""
    # v1.1.0: GS-P0-2 fix - add length limits to prevent abuse
    topic: str = Field(..., min_length=1, max_length=500)
    style: Optional[str] = Field("Children's book illustration", max_length=200)


class ImageGenRequest(BaseModel):
    """
    Image generation request.

    v1.2.0: Added comprehensive Field constraints for security.
    """
    # v1.2.0: Added Field constraints with max lengths
    project_id: Optional[str] = Field(None, max_length=100)
    prompts: List[str] = Field(..., min_length=1, max_length=10)  # 1-10 prompts
    reference_image: Optional[str] = Field(None, max_length=5_000_000)  # ~5MB base64 or URL
    reference_strength: Optional[float] = Field(0.7, ge=0.0, le=1.0)
    image_size: Optional[str] = Field("landscape_4_3", max_length=50)
    # AI Design Page enhancement parameters (theme-based)
    theme: Optional[str] = Field(None, max_length=200)
    character: Optional[str] = Field(None, max_length=500)
    style: Optional[str] = Field(None, max_length=50)
    generation_mode: Optional[str] = Field("guided", max_length=20)
    creativity_level: Optional[float] = Field(0.3, ge=0.0, le=1.0)
    # 5W1H Asset Generation parameters
    who: Optional[str] = Field(None, max_length=500)
    what: Optional[str] = Field(None, max_length=500)
    where: Optional[str] = Field(None, max_length=500)
    moods: Optional[List[str]] = Field(None, max_length=10)  # Max 10 moods
    enhance_prompt: Optional[bool] = False
    # Negative prompt support
    negative_prompt: Optional[str] = Field(None, max_length=1000)
    # Batch generation support
    num_images: Optional[int] = Field(1, ge=1, le=4)  # 1-4 images per prompt

    @field_validator("prompts")
    @classmethod
    def validate_prompts_content(cls, v: List[str]) -> List[str]:
        """Validate each prompt has content and reasonable length."""
        if not v:
            raise ValueError("At least one prompt is required")
        for i, prompt in enumerate(v):
            if not prompt or not prompt.strip():
                raise ValueError(f"Prompt {i + 1} cannot be empty")
            if len(prompt) > 2000:
                raise ValueError(f"Prompt {i + 1} exceeds maximum length of 2000 characters")
        return v

    @field_validator("moods")
    @classmethod
    def validate_moods(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate mood tags."""
        if v is None:
            return v
        # Filter empty strings and limit length
        return [m.strip()[:50] for m in v if m and m.strip()][:10]


class PdfGenRequest(BaseModel):
    """PDF generation request."""
    project_id: str
    current_hash: str
    image_urls: List[str]
    texts: List[str]


class InspirationRequest(BaseModel):
    """AI inspiration generation request."""
    category: Optional[str] = None  # 'character', 'scene', 'story', 'all'
    style: Optional[str] = None  # Art style preference


class GenerationHistoryQuery(BaseModel):
    """Query parameters for generation history."""
    limit: Optional[int] = 20
    offset: Optional[int] = 0
    favorites_only: Optional[bool] = False


class FavoriteRequest(BaseModel):
    """Toggle favorite request."""
    generation_id: str
    is_favorited: bool


class AssetPromptTemplateCreate(BaseModel):
    """Create request for asset prompt template (5W1H naming convention)."""
    name: str
    description: Optional[str] = None
    who_type: Optional[str] = None      # Character type
    who_custom: Optional[str] = None    # Custom character
    what_type: Optional[str] = None     # Action type
    what_custom: Optional[str] = None   # Custom action
    where_type: Optional[str] = None    # Setting type
    where_custom: Optional[str] = None  # Custom setting
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


# Backward compatibility aliases
TemplateCreate = AssetPromptTemplateCreate
TemplateUpdate = AssetPromptTemplateUpdate
PageDesignTemplateCreate = PagePromptTemplateCreate
