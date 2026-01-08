"""
Generation Schemas - AI generation related models

@module schemas.generation
"""

from typing import Optional, List
from pydantic import BaseModel


class StoryGenRequest(BaseModel):
    """Story generation request."""
    topic: str
    style: Optional[str] = "Children's book illustration"


class ImageGenRequest(BaseModel):
    """Image generation request."""
    project_id: Optional[str] = None  # Optional - may be None when generating from Dashboard
    prompts: List[str]
    reference_image: Optional[str] = None  # Base64 encoded image or URL
    reference_strength: Optional[float] = 0.7  # 0.0-1.0, higher = more similar to reference
    image_size: Optional[str] = "landscape_4_3"  # Image aspect ratio
    # AI Design Page enhancement parameters (theme-based)
    theme: Optional[str] = None  # Page theme for prompt enhancement
    character: Optional[str] = None  # Character description
    style: Optional[str] = None  # Art style: cartoon, watercolor, sketch, fantasy, realistic, flat, scifi
    generation_mode: Optional[str] = "guided"  # "guided" (accurate) or "flexible" (creative)
    creativity_level: Optional[float] = 0.3  # 0.0-1.0, 0=precise, 1=creative
    # 5W1H Asset Generation parameters
    who: Optional[str] = None  # Main character description
    what: Optional[str] = None  # Action/activity
    where: Optional[str] = None  # Setting/scene
    moods: Optional[List[str]] = None  # Mood tags
    enhance_prompt: Optional[bool] = False  # Whether to use LLM enhancement
    # Negative prompt support
    negative_prompt: Optional[str] = None  # Elements to avoid
    # Batch generation support
    num_images: Optional[int] = 1  # Number of variations (1-4)


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
