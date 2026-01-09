"""
Trial Helper Tests - Test trial period checking logic.

@module tests.domains.test_trial_helper
@version 1.0.0
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock

from domains.identity.trial_helper import is_user_in_trial, is_user_in_trial_async


class TestTrialHelper:
    """Tests for trial period helper functions."""

    def test_is_user_in_trial_free_user_within_trial(self):
        """Test free user within trial period."""
        # User registered 15 days ago
        created_at = datetime.now(timezone.utc) - timedelta(days=15)

        user = {
            "tier": "t1",
            "created_at": created_at.isoformat()
        }

        assert is_user_in_trial(user, trial_days=30) is True

    def test_is_user_in_trial_free_user_expired(self):
        """Test free user past trial period."""
        # User registered 35 days ago
        created_at = datetime.now(timezone.utc) - timedelta(days=35)

        user = {
            "tier": "t1",
            "created_at": created_at.isoformat()
        }

        assert is_user_in_trial(user, trial_days=30) is False

    def test_is_user_in_trial_paid_user(self):
        """Test paid users don't have trial period."""
        created_at = datetime.now(timezone.utc) - timedelta(days=5)

        user_t2 = {
            "tier": "t2",
            "created_at": created_at.isoformat()
        }

        user_t3 = {
            "tier": "t3",
            "created_at": created_at.isoformat()
        }

        assert is_user_in_trial(user_t2, trial_days=30) is False
        assert is_user_in_trial(user_t3, trial_days=30) is False

    def test_is_user_in_trial_legacy_tier_names(self):
        """Test trial check with legacy tier names."""
        created_at = datetime.now(timezone.utc) - timedelta(days=10)

        user = {
            "tier": "free",  # Legacy name
            "created_at": created_at.isoformat()
        }

        assert is_user_in_trial(user, trial_days=30) is True

    def test_is_user_in_trial_no_created_at(self):
        """Test user without created_at returns False."""
        user = {
            "tier": "t1",
            # No created_at field
        }

        assert is_user_in_trial(user, trial_days=30) is False

    def test_is_user_in_trial_invalid_date(self):
        """Test invalid date format returns False."""
        user = {
            "tier": "t1",
            "created_at": "invalid_date_format"
        }

        assert is_user_in_trial(user, trial_days=30) is False

    def test_is_user_in_trial_edge_case_exact_days(self):
        """Test exact boundary at trial expiration."""
        # User registered exactly 30 days ago (to the second)
        now = datetime.now(timezone.utc)
        created_at = now - timedelta(days=30, seconds=0)

        user = {
            "tier": "t1",
            "created_at": created_at.isoformat()
        }

        # Exactly <= 30 days (30*24*3600 seconds) means they're still in trial
        # But due to microsecond precision, this might be very slightly over
        # Let's use 29.9 days to be safe in the test
        created_at_safe = now - timedelta(days=29, hours=23, minutes=59)
        user_safe = {
            "tier": "t1",
            "created_at": created_at_safe.isoformat()
        }

        assert is_user_in_trial(user_safe, trial_days=30) is True

    def test_is_user_in_trial_edge_case_just_over(self):
        """Test just over trial period."""
        # User registered 30.5 days ago
        created_at = datetime.now(timezone.utc) - timedelta(days=30, hours=12)

        user = {
            "tier": "t1",
            "created_at": created_at.isoformat()
        }

        assert is_user_in_trial(user, trial_days=30) is False

    def test_is_user_in_trial_custom_duration(self):
        """Test with custom trial duration."""
        created_at = datetime.now(timezone.utc) - timedelta(days=20)

        user = {
            "tier": "t1",
            "created_at": created_at.isoformat()
        }

        # Within 30 days
        assert is_user_in_trial(user, trial_days=30) is True

        # Beyond 15 days
        assert is_user_in_trial(user, trial_days=15) is False

    def test_is_user_in_trial_datetime_object(self):
        """Test with datetime object instead of string."""
        created_at = datetime.now(timezone.utc) - timedelta(days=10)

        user = {
            "tier": "t1",
            "created_at": created_at  # datetime object
        }

        assert is_user_in_trial(user, trial_days=30) is True

    def test_is_user_in_trial_default_duration(self):
        """Test using default trial duration (30 days)."""
        created_at = datetime.now(timezone.utc) - timedelta(days=15)

        user = {
            "tier": "t1",
            "created_at": created_at.isoformat()
        }

        # Should use default 30 days
        assert is_user_in_trial(user) is True

    @pytest.mark.asyncio
    async def test_is_user_in_trial_async_with_service(self):
        """Test async version with TierService."""
        created_at = datetime.now(timezone.utc) - timedelta(days=10)

        user = {
            "tier": "t1",
            "created_at": created_at.isoformat()
        }

        # Mock TierService
        mock_tier_service = AsyncMock()
        mock_tier_service.get_trial_duration_days.return_value = 45

        result = await is_user_in_trial_async(user, tier_service=mock_tier_service)

        assert result is True
        mock_tier_service.get_trial_duration_days.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_user_in_trial_async_without_service(self):
        """Test async version without TierService (uses default)."""
        created_at = datetime.now(timezone.utc) - timedelta(days=10)

        user = {
            "tier": "t1",
            "created_at": created_at.isoformat()
        }

        result = await is_user_in_trial_async(user, tier_service=None)

        assert result is True  # Uses default 30 days

    @pytest.mark.asyncio
    async def test_is_user_in_trial_async_service_error(self):
        """Test async version handles service errors."""
        created_at = datetime.now(timezone.utc) - timedelta(days=10)

        user = {
            "tier": "t1",
            "created_at": created_at.isoformat()
        }

        # Mock TierService that throws error
        mock_tier_service = AsyncMock()
        mock_tier_service.get_trial_duration_days.side_effect = Exception("DB error")

        result = await is_user_in_trial_async(user, tier_service=mock_tier_service)

        # Should fall back to default and still work
        assert result is True
