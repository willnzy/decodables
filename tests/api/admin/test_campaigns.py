"""Test admin/campaigns API endpoints.

Tests for campaign management endpoints.
v3.25: Added comprehensive tests including security validation.
"""
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import app


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


# ==========================================
# Basic Endpoint Tests (Auth)
# ==========================================

class TestCampaignsEndpointsAuth:
    """Basic tests for campaign API authentication requirements."""

    def test_list_campaigns_requires_auth(self, client):
        """List campaigns endpoint requires authentication."""
        response = client.get("/api/v2/admin/campaigns")
        assert response.status_code in [401, 403]

    def test_get_campaign_requires_auth(self, client):
        """Get campaign endpoint requires authentication."""
        response = client.get("/api/v2/admin/campaigns/test-id")
        assert response.status_code in [401, 403]

    def test_create_campaign_requires_auth(self, client):
        """Create campaign endpoint requires authentication."""
        response = client.post(
            "/api/v2/admin/campaigns",
            json={
                "name": "Test Campaign",
                "type": "credits_gift",
                "config": {},
                "target_type": "all",
                "start_at": "2026-01-01T00:00:00Z"
            }
        )
        assert response.status_code in [401, 403]

    def test_update_campaign_requires_auth(self, client):
        """Update campaign endpoint requires authentication."""
        response = client.put(
            "/api/v2/admin/campaigns/test-id",
            json={"name": "Updated Name"}
        )
        assert response.status_code in [401, 403]

    def test_delete_campaign_requires_auth(self, client):
        """Delete campaign endpoint requires authentication."""
        response = client.delete("/api/v2/admin/campaigns/test-id")
        assert response.status_code in [401, 403]

    def test_activate_campaign_requires_auth(self, client):
        """Activate campaign endpoint requires authentication."""
        response = client.post("/api/v2/admin/campaigns/test-id/activate")
        assert response.status_code in [401, 403]

    def test_pause_campaign_requires_auth(self, client):
        """Pause campaign endpoint requires authentication."""
        response = client.post("/api/v2/admin/campaigns/test-id/pause")
        assert response.status_code in [401, 403]

    def test_get_campaign_stats_requires_auth(self, client):
        """Get campaign stats endpoint requires authentication."""
        response = client.get("/api/v2/admin/campaigns/test-id/stats")
        assert response.status_code in [401, 403]


# ==========================================
# Parameter Validation Tests (Unit Tests)
# ==========================================

class TestCampaignParameterValidation:
    """Unit tests for parameter validation in request models."""

    def test_create_request_name_length(self):
        """Name must be between 1 and 200 characters."""
        from api.admin.campaigns import CampaignCreateRequest

        # Valid names
        CampaignCreateRequest(
            name="Test Campaign",
            type="credits_gift",
            config={},
            target_type="all",
            start_at="2026-01-01"
        )

        CampaignCreateRequest(
            name="A" * 200,
            type="credits_gift",
            config={},
            target_type="all",
            start_at="2026-01-01"
        )

        # Invalid: empty name
        with pytest.raises(ValidationError):
            CampaignCreateRequest(
                name="",
                type="credits_gift",
                config={},
                target_type="all",
                start_at="2026-01-01"
            )

        # Invalid: too long
        with pytest.raises(ValidationError):
            CampaignCreateRequest(
                name="A" * 201,
                type="credits_gift",
                config={},
                target_type="all",
                start_at="2026-01-01"
            )

    def test_create_request_type_validation(self):
        """Type must be a valid campaign type."""
        from api.admin.campaigns import CampaignCreateRequest

        # Valid types
        for campaign_type in ["credits_gift", "credits_discount", "credits_bonus"]:
            CampaignCreateRequest(
                name="Test",
                type=campaign_type,
                config={},
                target_type="all",
                start_at="2026-01-01"
            )

        # Invalid type
        with pytest.raises(ValidationError):
            CampaignCreateRequest(
                name="Test",
                type="invalid_type",
                config={},
                target_type="all",
                start_at="2026-01-01"
            )

    def test_create_request_target_type_validation(self):
        """Target type must be a valid type."""
        from api.admin.campaigns import CampaignCreateRequest

        # Valid target types
        for target in ["all", "subscription", "users", "new_users", "inactive_users"]:
            CampaignCreateRequest(
                name="Test",
                type="credits_gift",
                config={},
                target_type=target,
                start_at="2026-01-01"
            )

        # Invalid target type
        with pytest.raises(ValidationError):
            CampaignCreateRequest(
                name="Test",
                type="credits_gift",
                config={},
                target_type="invalid_target",
                start_at="2026-01-01"
            )

    def test_create_request_usage_limit_range(self):
        """Usage limit must be between 1 and 1000000."""
        from api.admin.campaigns import CampaignCreateRequest

        # Valid limits
        CampaignCreateRequest(
            name="Test",
            type="credits_gift",
            config={},
            target_type="all",
            start_at="2026-01-01",
            usage_limit=1
        )

        CampaignCreateRequest(
            name="Test",
            type="credits_gift",
            config={},
            target_type="all",
            start_at="2026-01-01",
            usage_limit=1000000
        )

        # Invalid: zero
        with pytest.raises(ValidationError):
            CampaignCreateRequest(
                name="Test",
                type="credits_gift",
                config={},
                target_type="all",
                start_at="2026-01-01",
                usage_limit=0
            )

        # Invalid: too large
        with pytest.raises(ValidationError):
            CampaignCreateRequest(
                name="Test",
                type="credits_gift",
                config={},
                target_type="all",
                start_at="2026-01-01",
                usage_limit=1000001
            )

    def test_create_request_usage_per_user_range(self):
        """Usage per user must be between 1 and 100."""
        from api.admin.campaigns import CampaignCreateRequest

        # Valid
        CampaignCreateRequest(
            name="Test",
            type="credits_gift",
            config={},
            target_type="all",
            start_at="2026-01-01",
            usage_per_user=1
        )

        CampaignCreateRequest(
            name="Test",
            type="credits_gift",
            config={},
            target_type="all",
            start_at="2026-01-01",
            usage_per_user=100
        )

        # Invalid: zero
        with pytest.raises(ValidationError):
            CampaignCreateRequest(
                name="Test",
                type="credits_gift",
                config={},
                target_type="all",
                start_at="2026-01-01",
                usage_per_user=0
            )

        # Invalid: too large
        with pytest.raises(ValidationError):
            CampaignCreateRequest(
                name="Test",
                type="credits_gift",
                config={},
                target_type="all",
                start_at="2026-01-01",
                usage_per_user=101
            )

    def test_update_request_target_type_validation(self):
        """Update request target_type must be valid if provided."""
        from api.admin.campaigns import CampaignUpdateRequest

        # Valid target types
        for target in ["all", "subscription", "users", "new_users", "inactive_users"]:
            req = CampaignUpdateRequest(target_type=target)
            assert req.target_type == target

        # None is allowed
        req = CampaignUpdateRequest(target_type=None)
        assert req.target_type is None

        # Invalid target type
        with pytest.raises(ValidationError) as exc_info:
            CampaignUpdateRequest(target_type="invalid_target")
        assert "Invalid target_type" in str(exc_info.value)


# ==========================================
# Constants Tests
# ==========================================

class TestCampaignConstants:
    """Tests for campaign constants."""

    def test_valid_campaign_statuses(self):
        """Valid campaign statuses are defined."""
        from domains.marketing.campaigns.constants import VALID_CAMPAIGN_STATUSES

        assert "draft" in VALID_CAMPAIGN_STATUSES
        assert "active" in VALID_CAMPAIGN_STATUSES
        assert "paused" in VALID_CAMPAIGN_STATUSES
        assert "completed" in VALID_CAMPAIGN_STATUSES
        assert "deleted" in VALID_CAMPAIGN_STATUSES
        assert "invalid" not in VALID_CAMPAIGN_STATUSES

    def test_valid_campaign_types(self):
        """Valid campaign types are defined."""
        from domains.marketing.campaigns.constants import VALID_CAMPAIGN_TYPES

        assert "credits_gift" in VALID_CAMPAIGN_TYPES
        assert "credits_discount" in VALID_CAMPAIGN_TYPES
        assert "credits_bonus" in VALID_CAMPAIGN_TYPES
        assert "invalid" not in VALID_CAMPAIGN_TYPES

    def test_valid_target_types(self):
        """Valid target types are defined."""
        from domains.marketing.campaigns.constants import VALID_TARGET_TYPES

        assert "all" in VALID_TARGET_TYPES
        assert "subscription" in VALID_TARGET_TYPES
        assert "users" in VALID_TARGET_TYPES
        assert "new_users" in VALID_TARGET_TYPES
        assert "inactive_users" in VALID_TARGET_TYPES
        assert "invalid" not in VALID_TARGET_TYPES


# ==========================================
# Integration-style Tests
# ==========================================

class TestCampaignFieldValidation:
    """Integration tests for field validation at API level."""

    @pytest.mark.parametrize("campaign_type", ["credits_gift", "credits_discount", "credits_bonus"])
    def test_valid_campaign_types(self, campaign_type):
        """Valid campaign types are accepted."""
        from api.admin.campaigns import CampaignCreateRequest

        req = CampaignCreateRequest(
            name="Test",
            type=campaign_type,
            config={},
            target_type="all",
            start_at="2026-01-01"
        )
        assert req.type == campaign_type

    @pytest.mark.parametrize("target_type", ["all", "subscription", "users", "new_users", "inactive_users"])
    def test_valid_target_types(self, target_type):
        """Valid target types are accepted."""
        from api.admin.campaigns import CampaignCreateRequest

        req = CampaignCreateRequest(
            name="Test",
            type="credits_gift",
            config={},
            target_type=target_type,
            start_at="2026-01-01"
        )
        assert req.target_type == target_type

    @pytest.mark.parametrize("usage_limit", [1, 100, 1000, 10000, 1000000])
    def test_valid_usage_limits(self, usage_limit):
        """Valid usage limits are accepted."""
        from api.admin.campaigns import CampaignCreateRequest

        req = CampaignCreateRequest(
            name="Test",
            type="credits_gift",
            config={},
            target_type="all",
            start_at="2026-01-01",
            usage_limit=usage_limit
        )
        assert req.usage_limit == usage_limit

    @pytest.mark.parametrize("usage_per_user", [1, 5, 10, 50, 100])
    def test_valid_usage_per_user(self, usage_per_user):
        """Valid usage per user values are accepted."""
        from api.admin.campaigns import CampaignCreateRequest

        req = CampaignCreateRequest(
            name="Test",
            type="credits_gift",
            config={},
            target_type="all",
            start_at="2026-01-01",
            usage_per_user=usage_per_user
        )
        assert req.usage_per_user == usage_per_user

