"""
Tier Service - Manages tier configuration and display names.

@module domains.identity.tier_service
@version 1.0.0

This service handles tier display names that are stored in system_configs.
Display names can be changed by admins without modifying code.
"""

import logging
from typing import Dict, Optional

from .constants import (
    TIER_T1,
    TIER_T2,
    TIER_T3,
    VALID_TIERS,
    TIER_LABELS,
    DEFAULT_TIER_DISPLAY_NAMES,
)
from infrastructure.repositories.config_repository import SupabaseConfigRepository

logger = logging.getLogger(__name__)


class TierService:
    """
    Service for managing tier configurations.

    Responsibilities:
    - Fetch tier display names from system_configs
    - Provide fallback to default values
    - Cache tier names for performance
    - Allow admin to update tier display names
    """

    def __init__(self, config_repo: SupabaseConfigRepository):
        """
        Initialize TierService with config repository.

        Args:
            config_repo: Configuration repository for accessing system_configs
        """
        self.config_repo = config_repo
        self._cache: Dict[str, str] = {}

    async def get_tier_display_name(self, tier: str) -> str:
        """
        Get configurable display name for a tier.

        This fetches the display name from system_configs table.
        Admins can change these names without code changes.

        Args:
            tier: Tier system code ('t1', 't2', or 't3')

        Returns:
            Display name (e.g., 'Free Plan', 'Starter Plan', 'Pro Plan')
            Falls back to default if not found in config.

        Example:
            >>> tier_service = TierService(config_repo)
            >>> await tier_service.get_tier_display_name("t1")
            'Free Plan'
        """
        if tier not in VALID_TIERS:
            logger.warning(f"Invalid tier code: {tier}")
            return tier.upper()

        # Check cache first
        if tier in self._cache:
            return self._cache[tier]

        # Fetch from database
        config_key = f"tier.{tier}.display_name"
        try:
            display_name = await self.config_repo.get_by_key(
                config_key,
                default_value=DEFAULT_TIER_DISPLAY_NAMES.get(tier, tier.upper())
            )

            # Cache the result
            self._cache[tier] = display_name
            return display_name

        except Exception as e:
            logger.error(f"Failed to fetch tier display name for {tier}: {e}")
            # Return default value on error
            return DEFAULT_TIER_DISPLAY_NAMES.get(tier, tier.upper())

    def get_tier_label(self, tier: str) -> str:
        """
        Get fixed descriptive label for a tier.

        These labels are fixed and never change:
        - t1 → "First Tier"
        - t2 → "Second Tier"
        - t3 → "Third Tier"

        Used in documentation, logs, and internal references.

        Args:
            tier: Tier system code ('t1', 't2', or 't3')

        Returns:
            Fixed tier label
        """
        return TIER_LABELS.get(tier, tier.upper())

    async def update_tier_display_name(self, tier: str, display_name: str) -> bool:
        """
        Update tier display name (Admin operation).

        This updates the display name in system_configs and clears the cache.

        Args:
            tier: Tier system code ('t1', 't2', or 't3')
            display_name: New display name to set

        Returns:
            True if successful, False otherwise

        Raises:
            ValueError: If tier is invalid
        """
        if tier not in VALID_TIERS:
            raise ValueError(f"Invalid tier: {tier}")

        config_key = f"tier.{tier}.display_name"

        try:
            # Update in database
            await self.config_repo.upsert(
                key=config_key,
                value=display_name,
                value_type="text",
                config_group="tier",
                description=f"{self.get_tier_label(tier)} 显示名称 (可配置)",
                is_active=True,
                is_editable=True
            )

            # Clear cache for this tier
            self._cache.pop(tier, None)

            logger.info(f"Updated tier display name: {tier} → '{display_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to update tier display name for {tier}: {e}")
            return False

    async def get_all_tier_configs(self) -> list[dict]:
        """
        Get all tier configurations with display names.

        Returns:
            List of tier configs with system codes, labels, and display names

        Example:
            [
                {
                    "tier": "t1",
                    "tier_label": "First Tier",
                    "display_name": "Free Plan"
                },
                ...
            ]
        """
        configs = []

        for tier in sorted(VALID_TIERS):
            display_name = await self.get_tier_display_name(tier)
            configs.append({
                "tier": tier,
                "tier_label": self.get_tier_label(tier),
                "display_name": display_name,
            })

        return configs

    def clear_cache(self):
        """Clear the tier display name cache."""
        self._cache.clear()
        logger.debug("Tier display name cache cleared")
