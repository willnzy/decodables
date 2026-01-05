"""
AI Model Canary Release
AI 模型灰度发布

Provides deterministic traffic splitting for testing new AI models
before full rollout.

Features:
- Hash-based user bucketing (deterministic)
- Tier-based targeting
- Configurable traffic percentage
"""

import hashlib
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

from ..config_service import get_config

logger = logging.getLogger(__name__)


@dataclass
class CanaryConfig:
    """Canary release configuration"""
    enabled: bool
    canary_provider: str
    canary_model: str
    traffic_percent: int  # 0-100
    target_tiers: list  # ["pro", "starter", ...]


def get_canary_config() -> Dict:
    """
    Get full canary configuration from system_configs.
    
    Returns:
        Canary config dict
    """
    return get_config("ai_model.canary") or {
        "enabled": False,
        "text_reasoning": None,
        "image_generation": None,
    }


def _get_user_bucket(user_id: str, model_type: str) -> int:
    """
    Get deterministic bucket (0-99) for a user.
    
    Uses MD5 hash to ensure same user always gets same bucket.
    
    Args:
        user_id: User identifier
        model_type: "text_reasoning" or "image_generation"
        
    Returns:
        Bucket number 0-99
    """
    # Create hash input
    hash_input = f"{user_id}:{model_type}"
    hash_value = hashlib.md5(hash_input.encode()).hexdigest()
    
    # Convert first 8 chars of hex to int, then mod 100
    bucket = int(hash_value[:8], 16) % 100
    
    return bucket


def should_use_canary(
    user_id: str,
    model_type: str,
    tier: str = "free"
) -> Tuple[bool, Optional[Dict]]:
    """
    Determine if a user should use the canary model.
    
    Uses deterministic hashing to ensure consistent experience
    for the same user across requests.
    
    Args:
        user_id: User identifier (user code or visitor ID)
        model_type: "text_reasoning" or "image_generation"
        tier: User tier ("free", "starter", "pro")
        
    Returns:
        Tuple of (should_use_canary, canary_config_dict or None)
        
    Example:
        >>> use_canary, config = should_use_canary("user123", "text_reasoning", "pro")
        >>> if use_canary:
        ...     provider = config["provider"]
        ...     model = config["model"]
    """
    # Get canary config
    canary_config = get_canary_config()
    
    # Check if canary is globally enabled
    if not canary_config.get("enabled", False):
        return False, None
    
    # Get model-specific canary config
    model_canary = canary_config.get(model_type)
    if not model_canary:
        return False, None
    
    # Check tier targeting
    target_tiers = model_canary.get("target_tiers", [])
    if target_tiers and tier not in target_tiers:
        # User's tier is not in target list
        return False, None
    
    # Get traffic percentage
    traffic_percent = model_canary.get("traffic_percent", 0)
    if traffic_percent <= 0:
        return False, None
    
    # Determine user bucket
    user_bucket = _get_user_bucket(user_id, model_type)
    
    # Check if user is in canary group
    if user_bucket < traffic_percent:
        logger.debug(
            f"[Canary] User {user_id[:8]}... in canary group "
            f"(bucket={user_bucket}, threshold={traffic_percent})"
        )
        return True, {
            "provider": model_canary.get("canary_provider"),
            "model": model_canary.get("canary_model"),
        }
    
    return False, None


def get_canary_stats() -> Dict:
    """
    Get canary release statistics (for admin dashboard).
    
    Returns:
        Dict with canary status and configuration
    """
    canary_config = get_canary_config()
    
    return {
        "enabled": canary_config.get("enabled", False),
        "text_reasoning": {
            "active": canary_config.get("text_reasoning") is not None,
            "config": canary_config.get("text_reasoning"),
        },
        "image_generation": {
            "active": canary_config.get("image_generation") is not None,
            "config": canary_config.get("image_generation"),
        },
    }


# ==========================================
# Admin Functions
# ==========================================

def update_canary_config(
    enabled: bool,
    text_reasoning: Optional[Dict] = None,
    image_generation: Optional[Dict] = None,
    updated_by: str = None
) -> bool:
    """
    Update canary release configuration.
    
    Args:
        enabled: Global enable/disable
        text_reasoning: Text model canary config
        image_generation: Image model canary config
        updated_by: Admin user ID
        
    Returns:
        True if successful
        
    Example config:
        text_reasoning = {
            "canary_provider": "qwen",
            "canary_model": "qwen-plus",
            "traffic_percent": 10,
            "target_tiers": ["pro"]
        }
    """
    from ..config_service import set_config
    
    config = {
        "enabled": enabled,
    }
    
    if text_reasoning:
        config["text_reasoning"] = {
            "canary_provider": text_reasoning.get("canary_provider"),
            "canary_model": text_reasoning.get("canary_model"),
            "traffic_percent": text_reasoning.get("traffic_percent", 0),
            "target_tiers": text_reasoning.get("target_tiers", []),
        }
    
    if image_generation:
        config["image_generation"] = {
            "canary_provider": image_generation.get("canary_provider"),
            "canary_model": image_generation.get("canary_model"),
            "traffic_percent": image_generation.get("traffic_percent", 0),
            "target_tiers": image_generation.get("target_tiers", []),
        }
    
    return set_config("ai_model.canary", config, updated_by)


def disable_canary(updated_by: str = None) -> bool:
    """
    Quickly disable all canary releases.
    
    Returns:
        True if successful
    """
    from ..config_service import set_config
    
    # Keep existing config but disable
    config = get_canary_config()
    config["enabled"] = False
    
    return set_config("ai_model.canary", config, updated_by)
