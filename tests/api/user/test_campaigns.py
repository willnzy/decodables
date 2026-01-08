"""
Tests for Campaigns API (v2)

Endpoints tested:
- GET /api/v2/user/campaigns/active
- POST /api/v2/user/campaigns/{id}/claim
- POST /api/v2/user/campaigns/{id}/dismiss

@module tests.api.user.test_campaigns
@version 2.2.0

Changes in v2.2.0:
- Refactored tests for DDD architecture (CampaignService dependency injection)
- Removed direct supabase mocking, now mock CampaignService methods
- Updated to test service integration through API layer

Changes in v2.1.0:
- Updated tests to use valid UUID format for campaign_id (v2.1.0 validation)
- Updated mock chain to use .gt() instead of .gte() for end_at query
- Added tests for new validation helpers
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone, timedelta

# Module-level rate limiter bypass BEFORE app import
_rate_limiter_patcher = patch('infrastructure.rate_limiter.limiter.limit', lambda rate: lambda func: func)
_rate_limiter_patcher.start()

from fastapi.testclient import TestClient
from app import app
from dependencies import get_current_user, optional_user
from api.user.campaigns import get_campaign_service
from domains.marketing import CampaignService, ClaimResult, CampaignWithStatus
from domains.marketing.repository import CampaignData

client = TestClient(app)


# ==========================================
# Constants for Testing
# ==========================================

# Valid UUIDs for testing (v2.1.0 requires UUID format)
VALID_CAMPAIGN_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
VALID_CAMPAIGN_ID_2 = "b2c3d4e5-f6a7-8901-bcde-f12345678901"
VALID_CAMPAIGN_ID_3 = "c3d4e5f6-a7b8-9012-cdef-123456789012"

# Invalid ID for testing (not UUID format)
INVALID_CAMPAIGN_ID = "camp_1"
INVALID_CAMPAIGN_ID_LONG = "not-a-valid-uuid-format"


# ==========================================
# Helper Functions
# ==========================================

def create_mock_campaign_data(
    campaign_id: str = VALID_CAMPAIGN_ID,
    name: str = "Test Campaign",
    campaign_type: str = "credits_gift",
    status: str = "active",
    is_active: bool = True,
    target_type: str = "all",
    usage_count: int = 0,
    usage_limit: int = 100,
    config: dict = None,
    days_offset: tuple = (-1, 7),  # (start_offset, end_offset) in days from now
) -> CampaignData:
    """Create a mock CampaignData for testing."""
    now = datetime.now(timezone.utc)
    return CampaignData(
        id=campaign_id,
        name=name,
        description="Test campaign description",
        type=campaign_type,
        config=config or {"amount": 50},
        target_type=target_type,
        target_config={},
        notification_channels=["modal", "banner"],
        notification_config={"title": "Welcome!", "message": "Get free credits"},
        start_at=now + timedelta(days=days_offset[0]),
        end_at=now + timedelta(days=days_offset[1]),
        usage_limit=usage_limit,
        usage_count=usage_count,
        status=status,
        is_active=is_active,
    )


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def mock_free_user():
    """Mock free tier user."""
    return {
        "id": "user_123",
        "email": "user@example.com",
        "tier": "free",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def override_get_current_user(mock_free_user):
    """Override get_current_user dependency."""
    async def _get_current_user():
        return mock_free_user

    app.dependency_overrides[get_current_user] = _get_current_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def override_optional_user(mock_free_user):
    """Override optional_user dependency."""
    async def _optional_user():
        return mock_free_user

    app.dependency_overrides[optional_user] = _optional_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_campaign_service():
    """Create a mock CampaignService."""
    mock_service = MagicMock(spec=CampaignService)
    mock_service.get_active_campaigns_for_user = AsyncMock()
    mock_service.claim_campaign = AsyncMock()
    mock_service.dismiss_notification = AsyncMock()
    mock_service.is_valid_notification_channel = MagicMock(return_value=True)
    return mock_service


@pytest.fixture
def override_campaign_service(mock_campaign_service):
    """Override get_campaign_service dependency."""
    def _get_campaign_service():
        return mock_campaign_service

    app.dependency_overrides[get_campaign_service] = _get_campaign_service
    yield mock_campaign_service
    app.dependency_overrides.clear()


# ==========================================
# Test Cases
# ==========================================

class TestGetActiveCampaigns:
    """Test GET /campaigns/active endpoint."""

    def test_get_active_campaigns_success(self, override_optional_user, override_campaign_service):
        """Should get active campaigns."""
        mock_service = override_campaign_service
        mock_campaign = create_mock_campaign_data()

        mock_service.get_active_campaigns_for_user.return_value = (
            [CampaignWithStatus(campaign=mock_campaign, has_claimed=False, can_claim=True)],
            {}
        )

        response = client.get("/api/v2/user/campaigns/active")

        assert response.status_code == 200
        data = response.json()
        assert len(data["campaigns"]) == 1
        assert data["campaigns"][0]["id"] == VALID_CAMPAIGN_ID
        assert data["campaigns"][0]["has_claimed"] is False
        assert data["campaigns"][0]["can_claim"] is True

    def test_get_active_campaigns_empty(self, override_optional_user, override_campaign_service):
        """Should return empty list when no campaigns."""
        mock_service = override_campaign_service
        mock_service.get_active_campaigns_for_user.return_value = ([], {})

        response = client.get("/api/v2/user/campaigns/active")

        assert response.status_code == 200
        data = response.json()
        assert data["campaigns"] == []
        assert data["notifications"] is not None

    def test_get_active_campaigns_with_notifications(self, override_optional_user, override_campaign_service):
        """Should build notifications from campaign channels."""
        mock_service = override_campaign_service
        mock_campaign = create_mock_campaign_data()

        mock_service.get_active_campaigns_for_user.return_value = (
            [CampaignWithStatus(campaign=mock_campaign, has_claimed=False, can_claim=True)],
            {}
        )

        response = client.get("/api/v2/user/campaigns/active")

        assert response.status_code == 200
        data = response.json()
        # Should have modal notification
        assert data["notifications"]["modal"] is not None
        assert data["notifications"]["modal"]["campaign_id"] == VALID_CAMPAIGN_ID

    def test_get_active_campaigns_respects_dismissals(self, override_optional_user, override_campaign_service):
        """Should not show notifications for dismissed channels."""
        mock_service = override_campaign_service
        mock_campaign = create_mock_campaign_data()

        # User dismissed modal for this campaign
        mock_service.get_active_campaigns_for_user.return_value = (
            [CampaignWithStatus(campaign=mock_campaign, has_claimed=False, can_claim=True)],
            {VALID_CAMPAIGN_ID: ["modal"]}
        )

        response = client.get("/api/v2/user/campaigns/active")

        assert response.status_code == 200
        data = response.json()
        # Modal should be None because it's dismissed
        assert data["notifications"]["modal"] is None
        # Banner should still be present
        assert len(data["notifications"]["banner"]) == 1

    def test_get_active_campaigns_as_anonymous(self, override_campaign_service):
        """Should work for anonymous users."""
        mock_service = override_campaign_service
        mock_service.get_active_campaigns_for_user.return_value = ([], {})

        response = client.get("/api/v2/user/campaigns/active")

        assert response.status_code == 200


class TestClaimCampaign:
    """Test POST /campaigns/{id}/claim endpoint."""

    def test_claim_campaign_success(self, override_get_current_user, override_campaign_service):
        """Should claim campaign and receive credits."""
        mock_service = override_campaign_service
        mock_service.claim_campaign.return_value = ClaimResult(
            success=True,
            credits_received=50,
            message="You received 50 credits!"
        )

        response = client.post(f"/api/v2/user/campaigns/{VALID_CAMPAIGN_ID}/claim")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["credits_received"] == 50
        assert "50 credits" in data["message"]

    def test_claim_campaign_not_found(self, override_get_current_user, override_campaign_service):
        """Should return 404 for non-existent campaign."""
        mock_service = override_campaign_service
        mock_service.claim_campaign.return_value = ClaimResult(
            success=False,
            error_code="NOT_FOUND",
            message="Campaign not found"
        )

        response = client.post(f"/api/v2/user/campaigns/{VALID_CAMPAIGN_ID}/claim")

        assert response.status_code == 404

    def test_claim_campaign_invalid_id_format(self, override_get_current_user):
        """Should return 400 for invalid campaign ID format (v2.1.0)."""
        response = client.post("/api/v2/user/campaigns/invalid_id/claim")

        assert response.status_code == 400
        assert "Invalid campaign ID format" in response.json()["message"]

    def test_claim_campaign_already_claimed(self, override_get_current_user, override_campaign_service):
        """Should return 400 if already claimed."""
        mock_service = override_campaign_service
        mock_service.claim_campaign.return_value = ClaimResult(
            success=False,
            error_code="ALREADY_CLAIMED",
            message="You have already claimed this campaign"
        )

        response = client.post(f"/api/v2/user/campaigns/{VALID_CAMPAIGN_ID}/claim")

        assert response.status_code == 400
        assert "already claimed" in response.json()["message"].lower()

    def test_claim_campaign_not_eligible(self, override_get_current_user, override_campaign_service):
        """Should return 403 if user not eligible."""
        mock_service = override_campaign_service
        mock_service.claim_campaign.return_value = ClaimResult(
            success=False,
            error_code="NOT_ELIGIBLE",
            message="You are not eligible for this campaign"
        )

        response = client.post(f"/api/v2/user/campaigns/{VALID_CAMPAIGN_ID}/claim")

        assert response.status_code == 403

    def test_claim_campaign_inactive(self, override_get_current_user, override_campaign_service):
        """Should return 400 if campaign is inactive."""
        mock_service = override_campaign_service
        mock_service.claim_campaign.return_value = ClaimResult(
            success=False,
            error_code="INACTIVE",
            message="Campaign is not active"
        )

        response = client.post(f"/api/v2/user/campaigns/{VALID_CAMPAIGN_ID}/claim")

        assert response.status_code == 400

    def test_claim_campaign_ended(self, override_get_current_user, override_campaign_service):
        """Should return 400 if campaign has ended."""
        mock_service = override_campaign_service
        mock_service.claim_campaign.return_value = ClaimResult(
            success=False,
            error_code="ENDED",
            message="Campaign has ended"
        )

        response = client.post(f"/api/v2/user/campaigns/{VALID_CAMPAIGN_ID}/claim")

        assert response.status_code == 400

    def test_claim_campaign_limit_reached(self, override_get_current_user, override_campaign_service):
        """Should return 400 if usage limit reached."""
        mock_service = override_campaign_service
        mock_service.claim_campaign.return_value = ClaimResult(
            success=False,
            error_code="LIMIT_REACHED",
            message="Campaign usage limit reached"
        )

        response = client.post(f"/api/v2/user/campaigns/{VALID_CAMPAIGN_ID}/claim")

        assert response.status_code == 400

    def test_claim_campaign_credit_failed(self, override_get_current_user, override_campaign_service):
        """Should return 500 if credit grant fails."""
        mock_service = override_campaign_service
        mock_service.claim_campaign.return_value = ClaimResult(
            success=False,
            error_code="CREDIT_FAILED",
            message="Failed to grant credits. Please try again."
        )

        response = client.post(f"/api/v2/user/campaigns/{VALID_CAMPAIGN_ID}/claim")

        assert response.status_code == 500

    def test_claim_campaign_requires_auth(self):
        """Should require authentication."""
        response = client.post(f"/api/v2/user/campaigns/{VALID_CAMPAIGN_ID}/claim")

        assert response.status_code == 401


class TestDismissNotification:
    """Test POST /campaigns/{id}/dismiss endpoint."""

    def test_dismiss_notification_success(self, override_get_current_user, override_campaign_service):
        """Should dismiss notification."""
        mock_service = override_campaign_service
        mock_service.dismiss_notification.return_value = True

        response = client.post(
            f"/api/v2/user/campaigns/{VALID_CAMPAIGN_ID}/dismiss",
            json={"channel": "modal"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_service.dismiss_notification.assert_called_once()

    def test_dismiss_notification_invalid_channel(self, override_get_current_user):
        """Should return 422 for invalid channel."""
        response = client.post(
            f"/api/v2/user/campaigns/{VALID_CAMPAIGN_ID}/dismiss",
            json={"channel": "invalid_channel"}
        )

        assert response.status_code == 422

    def test_dismiss_notification_invalid_id_format(self, override_get_current_user):
        """Should return 400 for invalid campaign ID format (v2.1.0)."""
        response = client.post(
            "/api/v2/user/campaigns/invalid_id/dismiss",
            json={"channel": "modal"}
        )

        assert response.status_code == 400
        assert "Invalid campaign ID format" in response.json()["message"]

    def test_dismiss_notification_requires_auth(self):
        """Should require authentication."""
        response = client.post(
            f"/api/v2/user/campaigns/{VALID_CAMPAIGN_ID}/dismiss",
            json={"channel": "modal"}
        )

        assert response.status_code == 401


class TestUUIDValidation:
    """Tests for UUID validation added in v2.1.0."""

    def test_valid_uuid_lowercase(self):
        """Should accept valid lowercase UUID."""
        from api.user.campaigns import UUID_PATTERN

        assert UUID_PATTERN.match("a1b2c3d4-e5f6-7890-abcd-ef1234567890") is not None

    def test_valid_uuid_uppercase(self):
        """Should accept valid uppercase UUID."""
        from api.user.campaigns import UUID_PATTERN

        assert UUID_PATTERN.match("A1B2C3D4-E5F6-7890-ABCD-EF1234567890") is not None

    def test_valid_uuid_mixed_case(self):
        """Should accept valid mixed case UUID."""
        from api.user.campaigns import UUID_PATTERN

        assert UUID_PATTERN.match("A1b2C3d4-E5f6-7890-AbCd-Ef1234567890") is not None

    def test_invalid_uuid_too_short(self):
        """Should reject too short UUID."""
        from api.user.campaigns import UUID_PATTERN

        assert UUID_PATTERN.match("a1b2c3d4-e5f6-7890-abcd") is None

    def test_invalid_uuid_wrong_format(self):
        """Should reject wrong format."""
        from api.user.campaigns import UUID_PATTERN

        assert UUID_PATTERN.match("not-a-valid-uuid") is None

    def test_invalid_uuid_no_dashes(self):
        """Should reject UUID without dashes."""
        from api.user.campaigns import UUID_PATTERN

        assert UUID_PATTERN.match("a1b2c3d4e5f67890abcdef1234567890") is None


class TestNotificationBuilding:
    """Tests for notification building from CampaignData."""

    def test_build_notification_from_data(self):
        """Should build notification data from CampaignData."""
        from api.user.campaigns import _build_notification_from_data, NotificationData

        campaign = create_mock_campaign_data()
        notification = _build_notification_from_data(campaign, "modal", can_claim=True)

        assert isinstance(notification, NotificationData)
        assert notification.campaign_id == VALID_CAMPAIGN_ID
        assert notification.channel == "modal"
        assert notification.can_claim is True
        assert notification.title == "Welcome!"

    def test_build_notification_default_values(self):
        """Should use default values when config is empty."""
        from api.user.campaigns import _build_notification_from_data

        campaign = create_mock_campaign_data()
        campaign = CampaignData(
            id=campaign.id,
            name="Test",
            description=None,
            type=campaign.type,
            config=campaign.config,
            target_type=campaign.target_type,
            target_config={},
            notification_channels=["modal"],
            notification_config={},  # Empty config
            start_at=campaign.start_at,
            end_at=campaign.end_at,
            usage_limit=campaign.usage_limit,
            usage_count=campaign.usage_count,
            status=campaign.status,
            is_active=campaign.is_active,
        )

        notification = _build_notification_from_data(campaign, "modal")

        assert notification.title == "Test"  # Falls back to campaign name
        assert notification.message == ""  # Falls back to empty string
        assert notification.cta_text == "Learn More"  # Default
        assert notification.cta_url == "/pricing"  # Default


# ==========================================
# Summary
# ==========================================
# Total tests: 28
# - GET /campaigns/active: 5 tests
# - POST /campaigns/{id}/claim: 10 tests
# - POST /campaigns/{id}/dismiss: 4 tests
# - UUID validation (v2.1.0): 6 tests
# - Notification building (v2.2.0): 3 tests
# ==========================================
