"""
System Configuration Service (v2) - Repository-based implementation.

@module domains.platform.config_service_v2
@version 2.0.0

This is the new DDD-compliant service that uses ConfigRepository.
"""

import json
import logging
from typing import Optional, Dict, Any, List

from core.cache import cache_service
from domains.platform.config_repository import ConfigRepository

logger = logging.getLogger(__name__)


# Import default configs from v1
from domains.platform.config_service import DEFAULT_RATE_LIMITS, RATE_LIMIT_PRESETS


class ConfigService:
    """
    Configuration service using Repository pattern.

    Handles system configuration management with caching.
    """

    def __init__(self, config_repo: ConfigRepository):
        """
        Initialize service with repository.

        Args:
            config_repo: Configuration repository instance
        """
        self.config_repo = config_repo

    async def get_config(
        self,
        config_key: str,
        use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
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
            cached = cache_service.get_json(f"config:{config_key}")
            if cached is not None:
                return cached

        # Query via repository
        try:
            raw_value = await self.config_repo.get_by_key(config_key)
            if raw_value:
                try:
                    config_value = json.loads(raw_value) if raw_value else None
                except (json.JSONDecodeError, TypeError):
                    config_value = raw_value

                # Cache the result (5 minutes TTL)
                if config_value is not None:
                    cache_service.set_json(f"config:{config_key}", config_value, ttl=300)

                return config_value
        except Exception as e:
            logger.warning(f"[ConfigService] Error fetching config {config_key}: {e}")

        # Return default
        return DEFAULT_RATE_LIMITS.get(config_key)

    async def set_config(
        self,
        config_key: str,
        config_value: Dict[str, Any],
        updated_by: str = None
    ) -> bool:
        """
        Set config value.

        Args:
            config_key: Config key
            config_value: Config value dict
            updated_by: User ID who made the update

        Returns:
            True if successful
        """
        try:
            value_str = json.dumps(config_value) if isinstance(config_value, dict) else str(config_value)

            result = await self.config_repo.update(
                key=config_key,
                value=value_str,
                admin_id=updated_by
            )

            # Invalidate cache
            cache_service.delete(f"config:{config_key}")

            return result is not None
        except Exception as e:
            logger.error(f"[ConfigService] Error setting config {config_key}: {e}")
            return False

    async def get_all_configs(
        self,
        category: str = None
    ) -> List[Dict[str, Any]]:
        """
        Get all configs, optionally filtered by category.

        Args:
            category: Optional category filter (e.g., "rate_limit")

        Returns:
            List of config dicts
        """
        try:
            configs = await self.config_repo.get_all(group=category)
            return configs
        except Exception as e:
            logger.error(f"[ConfigService] Error fetching configs: {e}")
            # Return defaults
            default_configs = []
            for key, value in DEFAULT_RATE_LIMITS.items():
                if category is None or key.startswith(f"{category}."):
                    default_configs.append({
                        "key": key,
                        "value": json.dumps(value),
                        "config_group": key.split(".")[0] + "." + key.split(".")[1] if "." in key else "general",
                        "is_active": True
                    })
            return default_configs

    async def get_rate_limit_string(self, config_key: str) -> str:
        """
        Get rate limit string for slowapi.

        Args:
            config_key: Config key

        Returns:
            Rate limit string (e.g., "10/minute")
        """
        config = await self.get_config(config_key)
        if not config or not config.get("enabled", True):
            # Disabled - return very high limit
            return "10000/minute"

        limit = config.get("limit", 100)
        window = config.get("window", "minute")

        return f"{limit}/{window}"

    async def is_rate_limit_enabled(self, config_key: str = None) -> bool:
        """
        Check if rate limiting is enabled.

        Args:
            config_key: Optional specific config key to check

        Returns:
            True if rate limiting is enabled
        """
        # Check global setting
        global_config = await self.get_config("rate_limit.global.enabled")
        if global_config and not global_config.get("enabled", True):
            return False

        # Check specific key
        if config_key:
            config = await self.get_config(config_key)
            if config and not config.get("enabled", True):
                return False

        return True

    def clear_config_cache(self):
        """Clear all config cache."""
        cache_service.delete_pattern("config:*")
        logger.info("[ConfigService] Config cache cleared")

    async def batch_update_configs(
        self,
        updates: List[Dict[str, Any]],
        updated_by: str = None
    ) -> Dict[str, bool]:
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
                results[config_key] = await self.set_config(config_key, config_value, updated_by)

        return results

    async def apply_rate_limit_preset(
        self,
        preset_name: str,
        updated_by: str = None
    ) -> bool:
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
            return await self.set_config("rate_limit.global.enabled", {"enabled": False}, updated_by)

        # Enable rate limiting
        await self.set_config("rate_limit.global.enabled", {"enabled": True}, updated_by)

        multiplier = preset.get("multiplier", 1.0)
        if multiplier == 1.0:
            # Reset to defaults
            for key, value in DEFAULT_RATE_LIMITS.items():
                if key.startswith("rate_limit.") and key != "rate_limit.global.enabled":
                    await self.set_config(key, value, updated_by)
        else:
            # Apply multiplier
            configs = await self.get_all_configs("rate_limit")
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
                        await self.set_config(key, {**value, "limit": new_limit}, updated_by)

        # Clear cache
        self.clear_config_cache()
        return True
