"""
Identity Domain Tests - UserProfile aggregate and tier logic.

@module tests.domains.test_identity_domain
@version 1.0.0

Tests cover:
- UserProfile aggregate creation and operations
- User tier management
- Feature access control by tier
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock

from domains.identity import (
    UserProfile,
    UserTier,
    OnboardingStep,
    UserPreferences,
    UserNotFoundException,
    InvalidUserDataException,
)


class TestUserTier:
    """Tests for UserTier enum."""

    def test_tier_values(self):
        """Test tier enum values."""
        assert UserTier.FREE.value == "free"
        assert UserTier.STARTER.value == "starter"
        assert UserTier.PRO.value == "pro"

    def test_tier_from_string(self):
        """Test creating tier from string."""
        assert UserTier("free") == UserTier.FREE
        assert UserTier("starter") == UserTier.STARTER
        assert UserTier("pro") == UserTier.PRO

    def test_tier_comparison(self):
        """Test tier comparison methods."""
        free = UserTier.FREE
        starter = UserTier.STARTER
        pro = UserTier.PRO

        # Free < Starter < Pro
        assert free.level < starter.level
        assert starter.level < pro.level
        assert free.level < pro.level


class TestFeatureAccess:
    """Tests for FeatureAccess configuration."""

    def test_marketplace_publish_access(self):
        """Test marketplace publish feature access."""
        access = FeatureAccess.for_feature("marketplace_publish")

        assert UserTier.FREE not in access.allowed_tiers
        assert UserTier.STARTER in access.allowed_tiers
        assert UserTier.PRO in access.allowed_tiers

    def test_sticker_library_access(self):
        """Test sticker library feature access."""
        access = FeatureAccess.for_feature("sticker_library")

        assert UserTier.FREE not in access.allowed_tiers
        assert UserTier.STARTER in access.allowed_tiers
        assert UserTier.PRO in access.allowed_tiers

    def test_commercial_license_access(self):
        """Test commercial license feature access."""
        access = FeatureAccess.for_feature("commercial_license")

        assert UserTier.FREE not in access.allowed_tiers
        assert UserTier.STARTER not in access.allowed_tiers
        assert UserTier.PRO in access.allowed_tiers

    def test_basic_features_all_tiers(self):
        """Test basic features available to all tiers."""
        access = FeatureAccess.for_feature("project_create")

        assert UserTier.FREE in access.allowed_tiers
        assert UserTier.STARTER in access.allowed_tiers
        assert UserTier.PRO in access.allowed_tiers


class TestUserProfileAggregate:
    """Tests for UserProfile aggregate."""

    def test_create_user_profile(self):
        """Test creating UserProfile aggregate."""
        now = datetime.now(timezone.utc)
        profile = UserProfile(
            user_id="user_123",
            email="test@example.com",
            tier=UserTier.STARTER,
            created_at=now,
        )

        assert profile.user_id == "user_123"
        assert profile.email == "test@example.com"
        assert profile.tier == UserTier.STARTER
        assert profile.is_member is True

    def test_create_with_defaults(self):
        """Test creating UserProfile with default values."""
        profile = UserProfile(
            user_id="user_456",
            email="free@example.com",
        )

        assert profile.tier == UserTier.FREE
        assert profile.is_member is False
        assert profile.role == "user"

    def test_is_member_property(self):
        """Test is_member property for different tiers."""
        free = UserProfile(user_id="1", email="a@b.com", tier=UserTier.FREE)
        starter = UserProfile(user_id="2", email="b@b.com", tier=UserTier.STARTER)
        pro = UserProfile(user_id="3", email="c@b.com", tier=UserTier.PRO)

        assert free.is_member is False
        assert starter.is_member is True
        assert pro.is_member is True

    def test_is_admin_property(self):
        """Test is_admin property."""
        user = UserProfile(user_id="1", email="user@b.com", role="user")
        admin = UserProfile(user_id="2", email="admin@b.com", role="admin")

        assert user.is_admin is False
        assert admin.is_admin is True

    def test_has_feature_access(self):
        """Test feature access check."""
        free_user = UserProfile(user_id="1", email="a@b.com", tier=UserTier.FREE)
        pro_user = UserProfile(user_id="2", email="b@b.com", tier=UserTier.PRO)

        # Free user cannot publish to marketplace
        assert free_user.has_feature_access("marketplace_publish") is False

        # Pro user can publish to marketplace
        assert pro_user.has_feature_access("marketplace_publish") is True

    def test_upgrade_tier(self):
        """Test upgrading user tier."""
        profile = UserProfile(
            user_id="user_123",
            email="test@example.com",
            tier=UserTier.FREE,
        )

        profile.upgrade_tier(UserTier.STARTER)

        assert profile.tier == UserTier.STARTER
        assert profile.is_member is True

    def test_downgrade_tier(self):
        """Test downgrading user tier."""
        profile = UserProfile(
            user_id="user_123",
            email="test@example.com",
            tier=UserTier.PRO,
        )

        profile.downgrade_tier(UserTier.FREE)

        assert profile.tier == UserTier.FREE
        assert profile.is_member is False

    def test_project_limit_by_tier(self):
        """Test project limits by tier."""
        free = UserProfile(user_id="1", email="a@b.com", tier=UserTier.FREE)
        starter = UserProfile(user_id="2", email="b@b.com", tier=UserTier.STARTER)
        pro = UserProfile(user_id="3", email="c@b.com", tier=UserTier.PRO)

        assert free.project_limit == 1
        assert starter.project_limit == 20
        assert pro.project_limit == 200

    def test_trial_period(self):
        """Test trial period calculation."""
        # User created 15 days ago
        created = datetime.now(timezone.utc) - timedelta(days=15)
        profile = UserProfile(
            user_id="user_123",
            email="test@example.com",
            tier=UserTier.FREE,
            created_at=created,
        )

        assert profile.is_in_trial is True
        assert profile.trial_days_remaining == 15

    def test_trial_expired(self):
        """Test trial expired state."""
        # User created 35 days ago (trial is 30 days)
        created = datetime.now(timezone.utc) - timedelta(days=35)
        profile = UserProfile(
            user_id="user_123",
            email="test@example.com",
            tier=UserTier.FREE,
            created_at=created,
        )

        assert profile.is_in_trial is False
        assert profile.trial_days_remaining == 0

    def test_paid_users_no_trial(self):
        """Test paid users don't have trial limitations."""
        created = datetime.now(timezone.utc) - timedelta(days=100)
        profile = UserProfile(
            user_id="user_123",
            email="test@example.com",
            tier=UserTier.PRO,
            created_at=created,
        )

        # Paid users are not subject to trial
        assert profile.is_in_trial is True  # Always "in trial" for paid users

    def test_to_dict(self):
        """Test serializing UserProfile to dict."""
        profile = UserProfile(
            user_id="user_123",
            email="test@example.com",
            tier=UserTier.STARTER,
            display_name="Test User",
        )

        data = profile.to_dict()

        assert data["user_id"] == "user_123"
        assert data["email"] == "test@example.com"
        assert data["tier"] == "starter"
        assert data["display_name"] == "Test User"
        assert data["is_member"] is True

    def test_from_dict(self):
        """Test creating UserProfile from dict."""
        data = {
            "id": "user_789",
            "email": "from_dict@example.com",
            "tier": "pro",
            "display_name": "Dict User",
            "role": "admin",
        }

        profile = UserProfile.from_dict(data)

        assert profile.user_id == "user_789"
        assert profile.email == "from_dict@example.com"
        assert profile.tier == UserTier.PRO
        assert profile.is_admin is True


class TestIdentityService:
    """Tests for IdentityService (with mocked repository)."""

    @pytest.fixture
    def mock_repository(self):
        """Create mock user repository."""
        repo = MagicMock()
        repo.get_by_id = AsyncMock()
        repo.get_by_email = AsyncMock()
        repo.save = AsyncMock()
        repo.update_tier = AsyncMock()
        return repo

    @pytest.fixture
    def identity_service(self, mock_repository):
        """Create identity service with mock repository."""
        from domains.identity import IdentityService
        return IdentityService(mock_repository)

    @pytest.mark.asyncio
    async def test_get_user(self, identity_service, mock_repository):
        """Test getting user by ID."""
        mock_repository.get_by_id.return_value = UserProfile(
            user_id="user_123",
            email="test@example.com",
            tier=UserTier.STARTER,
        )

        user = await identity_service.get_user("user_123")

        assert user.email == "test@example.com"
        mock_repository.get_by_id.assert_called_once_with("user_123")

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, identity_service, mock_repository):
        """Test getting non-existent user."""
        mock_repository.get_by_id.return_value = None

        user = await identity_service.get_user("nonexistent")

        assert user is None

    @pytest.mark.asyncio
    async def test_create_user(self, identity_service, mock_repository):
        """Test creating new user."""
        mock_repository.get_by_email.return_value = None

        result = await identity_service.create_user(
            user_id="new_user",
            email="new@example.com",
        )

        assert result.success is True
        mock_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_feature_access(self, identity_service, mock_repository):
        """Test checking feature access."""
        mock_repository.get_by_id.return_value = UserProfile(
            user_id="user_123",
            email="test@example.com",
            tier=UserTier.FREE,
        )

        # Free user cannot publish to marketplace
        has_access = await identity_service.check_feature_access(
            "user_123",
            "marketplace_publish"
        )

        assert has_access is False

    @pytest.mark.asyncio
    async def test_upgrade_user_tier(self, identity_service, mock_repository):
        """Test upgrading user tier."""
        mock_repository.get_by_id.return_value = UserProfile(
            user_id="user_123",
            email="test@example.com",
            tier=UserTier.FREE,
        )

        result = await identity_service.update_tier("user_123", UserTier.PRO)

        assert result.success is True
        mock_repository.save.assert_called_once()
