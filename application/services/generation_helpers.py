"""
Generation Helpers - Shared utilities for AI generation endpoints

@module services.generation_helpers
@version 3.27

Changes:
- v3.27: Migrated to async ConfigService (no sync methods)
- v3.26: GI-P0-003 - Enhanced safety check with Unicode normalization and regex patterns
         Added comprehensive blacklist with category-based detection
- v3.25: Use ConfigService for dynamic credit costs (no hardcoded values)
"""

import logging
import re
import unicodedata
from typing import Optional, List, Dict, Any

from shared.ai.prompt_enhancer import enhance_prompt_async, enhance_asset_prompt_async
from domains.platform.config_service import ConfigService
from infrastructure.repositories.config_repository import SupabaseConfigRepository
from core.database import get_async_db_client

logger = logging.getLogger(__name__)


# Global ConfigService instance (lazy initialized)
_config_service: Optional[ConfigService] = None


async def _get_config_service() -> ConfigService:
    """Get or create global ConfigService instance (async)."""
    global _config_service
    if _config_service is None:
        db_client = await get_async_db_client()
        config_repo = SupabaseConfigRepository(db_client)
        _config_service = ConfigService(config_repo)
    return _config_service


# ==========================================
# Content Safety - Enhanced Blacklist (v3.26)
# ==========================================

# Category-based blacklist for better organization and maintenance
BLACKLIST_CATEGORIES = {
    "explicit": [
        "nsfw", "nude", "naked", "sex", "porn", "xxx",
        "erotic", "hentai", "fetish", "bondage",
    ],
    "violence": [
        "gore", "mutilation", "torture", "dismember",
        "decapitat", "disembowel",
    ],
    "illegal": [
        "child abuse", "cp ", "csam", "pedophil",
        "underage", "minor sexual",
    ],
    "harmful": [
        "suicide method", "how to kill", "make bomb",
        "synthesize drug", "cook meth",
    ],
}

# Flatten for quick lookup
BLACKLIST_WORDS = []
for category_words in BLACKLIST_CATEGORIES.values():
    BLACKLIST_WORDS.extend(category_words)

# Regex patterns for more complex detection
BLACKLIST_PATTERNS = [
    r"n\s*s\s*f\s*w",  # Spaced out "nsfw"
    r"n\.s\.f\.w",      # Dotted "n.s.f.w"
    r"p\s*o\s*r\s*n",  # Spaced out "porn"
    r"s\s*e\s*x\s*u",  # Spaced out "sexu..."
]

# Compiled regex for performance
_BLACKLIST_REGEX = None


def _get_blacklist_regex() -> re.Pattern:
    """Get compiled blacklist regex (lazy initialization)."""
    global _BLACKLIST_REGEX
    if _BLACKLIST_REGEX is None:
        pattern = "|".join(BLACKLIST_PATTERNS)
        _BLACKLIST_REGEX = re.compile(pattern, re.IGNORECASE)
    return _BLACKLIST_REGEX

# Config keys for credit costs
CONFIG_KEY_IMAGE_GENERATION = "credits.cost.image_generation"
CONFIG_KEY_IMAGE_GENERATION_REF = "credits.cost.image_generation_reference"
CONFIG_KEY_TEXT_GENERATION = "credits.cost.text_generation"

# Emergency fallbacks (only used if database completely unavailable)
EMERGENCY_FALLBACK_COST = 5
EMERGENCY_FALLBACK_COST_REF = 7
EMERGENCY_FALLBACK_COST_TEXT = 0  # Currently free by design


def check_prompt_safety(prompts: List[str]) -> bool:
    """
    Check if prompts contain blacklisted content (v3.26 enhanced).

    Uses multi-layer detection:
    1. Unicode normalization (prevent homoglyph attacks)
    2. Direct blacklist word matching
    3. Regex pattern matching (spaced/dotted bypass attempts)

    Args:
        prompts: List of prompts to check

    Returns:
        True if unsafe content detected, False if safe
    """
    blacklist_regex = _get_blacklist_regex()

    for prompt in prompts:
        # Normalize Unicode to prevent homoglyph attacks (е→e, а→a, etc.)
        normalized = unicodedata.normalize("NFKC", prompt).lower()

        # Remove zero-width characters that could be used to bypass
        normalized = re.sub(r"[\u200b-\u200f\u2060\ufeff]", "", normalized)

        # Check direct blacklist words
        for word in BLACKLIST_WORDS:
            if word in normalized:
                logger.warning(f"Safety check failed: blacklist word '{word}' detected")
                return True

        # Check regex patterns (spaced/dotted bypass attempts)
        if blacklist_regex.search(normalized):
            logger.warning(f"Safety check failed: pattern match in prompt")
            return True

    return False


def get_model_for_tier(tier: str) -> str:
    """Get AI model based on user tier."""
    return "flux-dev" if tier == "t3" else "flux-schnell"


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


async def get_base_cost(has_reference: bool) -> int:
    """
    Get base cost for image generation from config (async).

    Priority:
    1. Database system_configs (primary)
    2. Emergency fallback (if database unavailable)
    """
    config_service = await _get_config_service()
    config_key = CONFIG_KEY_IMAGE_GENERATION_REF if has_reference else CONFIG_KEY_IMAGE_GENERATION
    fallback = EMERGENCY_FALLBACK_COST_REF if has_reference else EMERGENCY_FALLBACK_COST

    try:
        config_value = await config_service.get_config(config_key, use_cache=True)
        if config_value is not None:
            # Handle different value formats
            if isinstance(config_value, dict):
                return int(config_value.get('amount', config_value.get('value', fallback)))
            return int(config_value)
    except Exception as e:
        logger.warning(f"Failed to get cost config '{config_key}': {e}")

    logger.warning(f"Using EMERGENCY fallback cost for '{config_key}': {fallback}")
    return fallback


async def calculate_cost(num_prompts: int, has_reference: bool, num_images: int = 1) -> int:
    """Calculate credit cost for generation using config-driven costs (async)."""
    base_cost = await get_base_cost(has_reference)
    return num_prompts * base_cost * num_images


async def get_text_generation_cost() -> int:
    """
    Get cost for text generation from config (async).

    Priority:
    1. Database system_configs (primary)
    2. Emergency fallback (if database unavailable)

    Note: Currently configured as 0 (free), but can be changed via config.
    """
    config_service = await _get_config_service()
    try:
        config_value = await config_service.get_config(CONFIG_KEY_TEXT_GENERATION, use_cache=True)
        if config_value is not None:
            if isinstance(config_value, dict):
                return int(config_value.get('amount', config_value.get('value', EMERGENCY_FALLBACK_COST_TEXT)))
            return int(config_value)
    except Exception as e:
        logger.warning(f"Failed to get text generation cost config: {e}")

    return EMERGENCY_FALLBACK_COST_TEXT


async def enhance_prompts(
    prompts: List[str],
    theme: Optional[str] = None,
    character: Optional[str] = None,
    style: str = "cartoon",
    mode: str = "guided",
    creativity_level: float = 0.3,
    user_id: str = None,
    tier: str = "t1",
    who: Optional[str] = None,
    what: Optional[str] = None,
    where: Optional[str] = None,
    moods: Optional[List[str]] = None,
    enhance_enabled: bool = False
) -> Dict[str, Any]:
    """
    WS-13: Converted to async, calls async AI services directly.

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
            result = await enhance_prompt_async(
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
            result = await enhance_asset_prompt_async(
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
