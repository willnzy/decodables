"""
TierService Tests - Tier configuration and display name management.

@module tests.domains.test_tier_service
@version 1.0.0

Tests cover:
- Getting tier display names from config
- Fallback to default values
- Updating tier display names
- Cache management
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from domains.identity.tier_service import TierService
from domains.identity.constants import TIER_T1, TIER_T2, TIER_T3


class TestTierService:
    """Tests for TierService."""

    @pytest.fixture
    def mock_config_repo(self):
        """Create mock config repository."""
        repo = MagicMock()
        repo.get_by_key = AsyncMock()
        repo.upsert = AsyncMock()
        repo.get_all = AsyncMock()
        return repo

    @pytest.fixture
    def tier_service(self, mock_config_repo):
        """Create tier service with mock repository."""
        return TierService(mock_config_repo)

    @pytest.mark.asyncio
    async def test_get_tier_display_name_from_config(self, tier_service, mock_config_repo):
        """Should return tier display name from config."""
        mock_config_repo.get_by_key.return_value = "Free Plan"

        result = await tier_service.get_tier_display_name(TIER_T1)

        assert result == "Free Plan"
        mock_config_repo.get_by_key.assert_called_once_with(
            "tier.t1.display_name",
            default_value="Free Plan"
        )

    @pytest.mark.asyncio
    async def test_get_tier_display_name_uses_cache(self, tier_service, mock_config_repo):
        """Should use cached value on second call."""
        mock_config_repo.get_by_key.return_value = "Starter Plan"

        # First call - fetches from config
        result1 = await tier_service.get_tier_display_name(TIER_T2)
        assert result1 == "Starter Plan"
        assert mock_config_repo.get_by_key.call_count == 1

        # Second call - uses cache
        result2 = await tier_service.get_tier_display_name(TIER_T2)
        assert result2 == "Starter Plan"
        assert mock_config_repo.get_by_key.call_count == 1  # Not called again

    @pytest.mark.asyncio
    async def test_get_tier_display_name_fallback_on_error(self, tier_service, mock_config_repo):
        """Should fallback to default value on error."""
        mock_config_repo.get_by_key.side_effect = Exception("Database error")

        result = await tier_service.get_tier_display_name(TIER_T3)

        # Should return default value
        assert result == "Pro Plan"

    @pytest.mark.asyncio
    async def test_get_tier_display_name_invalid_tier(self, tier_service, mock_config_repo):
        """Should handle invalid tier code gracefully."""
        result = await tier_service.get_tier_display_name("invalid")

        assert result == "INVALID"
        mock_config_repo.get_by_key.assert_not_called()

    def test_get_tier_label(self, tier_service):
        """Should return fixed tier labels."""
        assert tier_service.get_tier_label(TIER_T1) == "First Tier"
        assert tier_service.get_tier_label(TIER_T2) == "Second Tier"
        assert tier_service.get_tier_label(TIER_T3) == "Third Tier"

    def test_get_tier_label_invalid_tier(self, tier_service):
        """Should handle invalid tier code."""
        assert tier_service.get_tier_label("invalid") == "INVALID"

    @pytest.mark.asyncio
    async def test_update_tier_display_name_success(self, tier_service, mock_config_repo):
        """Should update tier display name and clear cache."""
        # Populate cache first
        mock_config_repo.get_by_key.return_value = "Old Name"
        await tier_service.get_tier_display_name(TIER_T2)
        assert TIER_T2 in tier_service._cache

        # Update display name
        result = await tier_service.update_tier_display_name(TIER_T2, "Growth Plan")

        assert result is True
        mock_config_repo.upsert.assert_called_once()

        # Verify cache was cleared
        assert TIER_T2 not in tier_service._cache

    @pytest.mark.asyncio
    async def test_update_tier_display_name_invalid_tier(self, tier_service, mock_config_repo):
        """Should raise ValueError for invalid tier."""
        with pytest.raises(ValueError, match="Invalid tier"):
            await tier_service.update_tier_display_name("invalid", "New Name")

        mock_config_repo.upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_tier_display_name_error(self, tier_service, mock_config_repo):
        """Should return False on update error."""
        mock_config_repo.upsert.side_effect = Exception("Database error")

        result = await tier_service.update_tier_display_name(TIER_T1, "New Name")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_all_tier_configs(self, tier_service, mock_config_repo):
        """Should return all tier configurations."""
        mock_config_repo.get_by_key.side_effect = [
            "Free Plan",    # t1
            "Starter Plan", # t2
            "Pro Plan",     # t3
        ]

        configs = await tier_service.get_all_tier_configs()

        assert len(configs) == 3
        assert configs[0] == {
            "tier": "t1",
            "tier_label": "First Tier",
            "display_name": "Free Plan",
        }
        assert configs[1] == {
            "tier": "t2",
            "tier_label": "Second Tier",
            "display_name": "Starter Plan",
        }
        assert configs[2] == {
            "tier": "t3",
            "tier_label": "Third Tier",
            "display_name": "Pro Plan",
        }

    def test_clear_cache(self, tier_service):
        """Should clear the tier display name cache."""
        # Populate cache
        tier_service._cache = {
            "t1": "Free Plan",
            "t2": "Starter Plan",
            "t3": "Pro Plan",
        }

        tier_service.clear_cache()

        assert len(tier_service._cache) == 0
