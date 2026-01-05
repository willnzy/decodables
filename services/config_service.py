"""
System Configuration Service
系统配置服务

Provides:
- Dynamic rate limit configuration
- System-wide config management
- Cache with Redis (memory fallback)
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List

from supabase import create_client, Client

from .cache import cache_service

logger = logging.getLogger(__name__)

# Supabase client
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")  # Service role key

# Ensure URL has trailing slash to avoid SDK warning
if SUPABASE_URL and not SUPABASE_URL.endswith('/'):
    SUPABASE_URL = SUPABASE_URL + '/'

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# Default rate limit configs (fallback when DB unavailable)
DEFAULT_RATE_LIMITS = {
    # Payment operations
    "rate_limit.payment.checkout": {"limit": 5, "window": "minute", "enabled": True},
    "rate_limit.payment.portal": {"limit": 10, "window": "minute", "enabled": True},
    "rate_limit.marketplace.purchase": {"limit": 10, "window": "minute", "enabled": True},
    
    # AI operations
    "rate_limit.generate.story": {"limit": 20, "window": "minute", "enabled": True},
    "rate_limit.generate.images": {"limit": 10, "window": "minute", "enabled": True},
    "rate_limit.tools.ocr": {"limit": 10, "window": "minute", "enabled": True},
    
    # Export operations
    "rate_limit.export.pdf": {"limit": 10, "window": "minute", "enabled": True},
    "rate_limit.export.zip": {"limit": 5, "window": "minute", "enabled": True},
    "rate_limit.export.preview": {"limit": 20, "window": "minute", "enabled": True},
    
    # Project operations
    "rate_limit.projects.create": {"limit": 20, "window": "minute", "enabled": True},
    "rate_limit.assets.upload": {"limit": 20, "window": "minute", "enabled": True},
    "rate_limit.marketplace.publish": {"limit": 10, "window": "minute", "enabled": True},
    
    # Support operations
    "rate_limit.support.email": {"limit": 3, "window": "minute", "enabled": True},
    "rate_limit.contact.form": {"limit": 3, "window": "minute", "enabled": True},
    "rate_limit.feedback.submit": {"limit": 3, "window": "minute", "enabled": True},
    
    # Admin operations
    "rate_limit.admin.credits": {"limit": 30, "window": "minute", "enabled": True},
    "rate_limit.admin.tier": {"limit": 30, "window": "minute", "enabled": True},
    "rate_limit.admin.refund": {"limit": 10, "window": "minute", "enabled": True},
    "rate_limit.admin.subscription": {"limit": 10, "window": "minute", "enabled": True},
    "rate_limit.admin.broadcast": {"limit": 5, "window": "minute", "enabled": True},
    
    # High-frequency operations
    "rate_limit.admin.search": {"limit": 60, "window": "minute", "enabled": True},
    "rate_limit.marketplace.list": {"limit": 60, "window": "minute", "enabled": True},
    "rate_limit.analytics.events": {"limit": 60, "window": "minute", "enabled": True},
    
    # Global settings
    "rate_limit.global.default": {"limit": 100, "window": "minute", "enabled": True},
    "rate_limit.global.enabled": {"enabled": True},
}


def get_config(config_key: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
    """
    Get config value by key.
    
    Args:
        config_key: Config key (e.g., "rate_limit.payment.checkout")
        use_cache: Whether to use cache
        
    Returns:
        Config value dict or None
    """
    # Check cache first
    if use_cache:
        cached = cache_service.get_config(config_key)
        if cached is not None:
            return cached
    
    # Query database
    if supabase:
        try:
            result = supabase.table("system_configs")\
                .select("value, is_active")\
                .eq("key", config_key)\
                .single()\
                .execute()
            
            if result.data and result.data.get("is_active"):
                raw_value = result.data["value"]
                try:
                    config_value = json.loads(raw_value) if raw_value else None
                except (json.JSONDecodeError, TypeError):
                    config_value = raw_value
                
                # Cache the result
                if config_value is not None:
                    cache_service.set_config(config_key, config_value)
                
                return config_value
        except Exception as e:
            logger.warning(f"[ConfigService] Error fetching config {config_key}: {e}")
    
    # Return default
    return DEFAULT_RATE_LIMITS.get(config_key)


def set_config(config_key: str, config_value: Dict[str, Any], updated_by: str = None) -> bool:
    """
    Set config value.
    
    Args:
        config_key: Config key
        config_value: Config value dict
        updated_by: User ID who made the update
        
    Returns:
        True if successful
    """
    if not supabase:
        logger.error("[ConfigService] Supabase not configured")
        return False
    
    try:
        result = supabase.table("system_configs")\
            .update({
                "value": json.dumps(config_value) if isinstance(config_value, dict) else str(config_value),
                "updated_by": updated_by
            })\
            .eq("key", config_key)\
            .execute()
        
        # Invalidate cache
        cache_service.invalidate_config_cache(config_key)
        
        return True
    except Exception as e:
        logger.error(f"[ConfigService] Error setting config {config_key}: {e}")
        return False


def get_all_configs(category: str = None) -> List[Dict[str, Any]]:
    """
    Get all configs, optionally filtered by category.
    
    Args:
        category: Optional category filter (e.g., "rate_limit")
        
    Returns:
        List of config dicts
    """
    if not supabase:
        # Return defaults
        configs = []
        for key, value in DEFAULT_RATE_LIMITS.items():
            if category is None or key.startswith(f"{category}."):
                configs.append({
                    "key": key,
                    "value": json.dumps(value),
                    "config_group": key.split(".")[0] + "." + key.split(".")[1] if "." in key else "general",
                    "is_active": True
                })
        return configs
    
    try:
        query = supabase.table("system_configs").select("*")
        if category:
            query = query.eq("config_group", category)
        
        result = query.order("key").execute()
        return result.data or []
    except Exception as e:
        logger.error(f"[ConfigService] Error fetching configs: {e}")
        return []


def get_rate_limit_string(config_key: str) -> str:
    """
    Get rate limit string for slowapi.
    
    Args:
        config_key: Config key
        
    Returns:
        Rate limit string (e.g., "10/minute")
    """
    config = get_config(config_key)
    if not config or not config.get("enabled", True):
        # Disabled - return very high limit
        return "10000/minute"
    
    limit = config.get("limit", 100)
    window = config.get("window", "minute")
    
    return f"{limit}/{window}"


def is_rate_limit_enabled(config_key: str = None) -> bool:
    """
    Check if rate limiting is enabled.
    
    Args:
        config_key: Optional specific config key to check
        
    Returns:
        True if rate limiting is enabled
    """
    # Check global setting
    global_config = get_config("rate_limit.global.enabled")
    if global_config and not global_config.get("enabled", True):
        return False
    
    # Check specific key
    if config_key:
        config = get_config(config_key)
        if config and not config.get("enabled", True):
            return False
    
    return True


def clear_config_cache():
    """Clear all config cache."""
    cache_service.invalidate_config_cache()
    logger.info("[ConfigService] Config cache cleared")


def batch_update_configs(updates: List[Dict[str, Any]], updated_by: str = None) -> Dict[str, bool]:
    """
    Batch update multiple configs.
    
    Args:
        updates: List of {"config_key": "...", "config_value": {...}}
        updated_by: User ID
        
    Returns:
        Dict of {config_key: success_bool}
    """
    results = {}
    for update in updates:
        config_key = update.get("config_key")
        config_value = update.get("config_value")
        if config_key and config_value is not None:
            results[config_key] = set_config(config_key, config_value, updated_by)
    
    return results


# Rate limit presets
RATE_LIMIT_PRESETS = {
    "strict": {
        "description": "严格模式 - 适合高风险时期",
        "multiplier": 0.5
    },
    "normal": {
        "description": "正常模式 - 默认配置",
        "multiplier": 1.0
    },
    "relaxed": {
        "description": "宽松模式 - 适合促销活动",
        "multiplier": 2.0
    },
    "disabled": {
        "description": "禁用模式 - 完全关闭限流",
        "enabled": False
    }
}


def apply_rate_limit_preset(preset_name: str, updated_by: str = None) -> bool:
    """
    Apply a rate limit preset.
    
    Args:
        preset_name: Preset name ("strict", "normal", "relaxed", "disabled")
        updated_by: User ID
        
    Returns:
        True if successful
    """
    preset = RATE_LIMIT_PRESETS.get(preset_name)
    if not preset:
        return False
    
    if preset.get("enabled") is False:
        # Disable all rate limiting
        return set_config("rate_limit.global.enabled", {"enabled": False}, updated_by)
    
    # Enable rate limiting
    set_config("rate_limit.global.enabled", {"enabled": True}, updated_by)
    
    multiplier = preset.get("multiplier", 1.0)
    if multiplier == 1.0:
        # Reset to defaults
        for key, value in DEFAULT_RATE_LIMITS.items():
            if key.startswith("rate_limit.") and key != "rate_limit.global.enabled":
                set_config(key, value, updated_by)
    else:
        # Apply multiplier
        configs = get_all_configs("rate_limit")
        for config in configs:
            key = config["key"]
            if key != "rate_limit.global.enabled" and key != "rate_limit.global.default":
                raw_value = config["value"]
                try:
                    value = json.loads(raw_value) if isinstance(raw_value, str) else raw_value
                except (json.JSONDecodeError, TypeError):
                    value = raw_value
                if isinstance(value, dict) and "limit" in value:
                    new_limit = max(1, int(value["limit"] * multiplier))
                    set_config(key, {**value, "limit": new_limit}, updated_by)
    
    # Clear cache
    clear_config_cache()
    return True
