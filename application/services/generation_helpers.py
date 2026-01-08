"""
Generation Helpers - Shared utilities for AI generation endpoints

@module services.generation_helpers
@version 3.25

Changes:
- v3.25: Use ConfigService for dynamic credit costs (no hardcoded values)
"""

import logging
from typing import Optional, List, Dict, Any

from shared.ai.prompt_enhancer import enhance_prompt, enhance_asset_prompt
from domains.platform.config_service import get_config

logger = logging.getLogger(__name__)


BLACKLIST_WORDS = ["nsfw", "nude", "sex"]

# Config keys for credit costs
CONFIG_KEY_IMAGE_GENERATION = "credits.cost.image_generation"
CONFIG_KEY_IMAGE_GENERATION_REF = "credits.cost.image_generation_reference"
CONFIG_KEY_TEXT_GENERATION = "credits.cost.text_generation"

# Emergency fallbacks (only used if database completely unavailable)
EMERGENCY_FALLBACK_COST = 5
EMERGENCY_FALLBACK_COST_REF = 7
EMERGENCY_FALLBACK_COST_TEXT = 0  # Currently free by design


def check_prompt_safety(prompts: List[str]) -> bool:
    """Check if prompts contain blacklisted words."""
    return any(w in p.lower() for p in prompts for w in BLACKLIST_WORDS)


def get_model_for_tier(tier: str) -> str:
    """Get AI model based on user tier."""
    return "flux-dev" if tier == "pro" else "flux-schnell"


def validate_generation_mode(mode: Optional[str]) -> str:
    """Validate and normalize generation mode."""
    if mode not in ["guided", "flexible"]:
        return "guided"
    return mode


def validate_creativity_level(level: Optional[float]) -> float:
    """Validate and clamp creativity level."""
    if level is None:
        return 0.3
    return max(0.0, min(1.0, level))


def get_base_cost(has_reference: bool) -> int:
    """
    Get base cost for image generation from config.

    Priority:
    1. Database system_configs (primary)
    2. Emergency fallback (if database unavailable)
    """
    config_key = CONFIG_KEY_IMAGE_GENERATION_REF if has_reference else CONFIG_KEY_IMAGE_GENERATION
    fallback = EMERGENCY_FALLBACK_COST_REF if has_reference else EMERGENCY_FALLBACK_COST

    try:
        config_value = get_config(config_key, use_cache=True)
        if config_value is not None:
            # Handle different value formats
            if isinstance(config_value, dict):
                return int(config_value.get('amount', config_value.get('value', fallback)))
            return int(config_value)
    except Exception as e:
        logger.warning(f"Failed to get cost config '{config_key}': {e}")

    logger.warning(f"Using EMERGENCY fallback cost for '{config_key}': {fallback}")
    return fallback


def calculate_cost(num_prompts: int, has_reference: bool, num_images: int = 1) -> int:
    """Calculate credit cost for generation using config-driven costs."""
    base_cost = get_base_cost(has_reference)
    return num_prompts * base_cost * num_images


def get_text_generation_cost() -> int:
    """
    Get cost for text generation from config.

    Priority:
    1. Database system_configs (primary)
    2. Emergency fallback (if database unavailable)

    Note: Currently configured as 0 (free), but can be changed via config.
    """
    try:
        config_value = get_config(CONFIG_KEY_TEXT_GENERATION, use_cache=True)
        if config_value is not None:
            if isinstance(config_value, dict):
                return int(config_value.get('amount', config_value.get('value', EMERGENCY_FALLBACK_COST_TEXT)))
            return int(config_value)
    except Exception as e:
        logger.warning(f"Failed to get text generation cost config: {e}")

    return EMERGENCY_FALLBACK_COST_TEXT


def enhance_prompts(
    prompts: List[str],
    theme: Optional[str] = None,
    character: Optional[str] = None,
    style: str = "cartoon",
    mode: str = "guided",
    creativity_level: float = 0.3,
    user_id: str = None,
    tier: str = "free",
    who: Optional[str] = None,
    what: Optional[str] = None,
    where: Optional[str] = None,
    moods: Optional[List[str]] = None,
    enhance_enabled: bool = False
) -> Dict[str, Any]:
    """
    Enhance prompts using AI enhancement.
    
    Returns:
        Dict with:
        - prompts: List of (possibly enhanced) prompts
        - enhanced: Whether enhancement was applied
        - result: Enhancement result (if applied)
    """
    # Try theme-based enhancement first
    if theme:
        try:
            result = enhance_prompt(
                theme=theme,
                character=character,
                style=style,
                mode=mode,
                creativity_level=creativity_level,
                user_id=user_id,
                tier=tier
            )
            return {
                "prompts": [result["enhanced_prompt"]],
                "enhanced": True,
                "result": result
            }
        except Exception as e:
            logger.warning(f"Prompt enhancement failed: {e}")
    
    # Try 5W1H enhancement
    if who and enhance_enabled:
        try:
            result = enhance_asset_prompt(
                who=who,
                what=what,
                where=where,
                style=style,
                moods=moods,
                mode=mode,
                creativity_level=creativity_level,
                user_id=user_id,
                tier=tier
            )
            return {
                "prompts": [result["enhanced_prompt"]],
                "enhanced": True,
                "result": result
            }
        except Exception as e:
            logger.warning(f"5W1H enhancement failed: {e}")
    
    return {"prompts": prompts, "enhanced": False, "result": None}


def build_generation_record(
    user_id: str,
    image_url: str,
    original_prompt: Optional[str],
    enhanced_prompt: Optional[str],
    negative_prompt: Optional[str],
    style: Optional[str],
    moods: Optional[List[str]],
    aspect_ratio: str,
    generation_mode: str,
    creativity_level: float,
    who: Optional[str],
    what: Optional[str],
    where: Optional[str],
    has_reference: bool,
    reference_strength: Optional[float],
    batch_id: str,
    batch_index: int,
    credits_used: int,
    model_used: str,
    generation_time_ms: int,
    timezone: Optional[str]
) -> Dict[str, Any]:
    """Build record for user_generations table."""
    return {
        "user_id": user_id,
        "image_url": image_url,
        "original_prompt": original_prompt,
        "enhanced_prompt": enhanced_prompt,
        "negative_prompt": negative_prompt,
        "style": style,
        "moods": moods,
        "aspect_ratio": aspect_ratio,
        "generation_mode": generation_mode,
        "creativity_level": creativity_level,
        "who_param": who,
        "what_param": what,
        "where_param": where,
        "has_reference": has_reference,
        "reference_strength": reference_strength,
        "batch_id": batch_id,
        "batch_index": batch_index,
        "credits_used": credits_used,
        "model_used": model_used,
        "generation_time_ms": generation_time_ms,
        "timezone": timezone,
    }
