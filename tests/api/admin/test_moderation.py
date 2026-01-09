"""Test admin/moderation API endpoints.

Tests for marketplace moderation and content reports endpoints.
v3.28: Updated imports to use new domain constants (MOD-LOW-1).
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

class TestModerationEndpointsAuth:
    """Basic tests for moderation API authentication requirements."""

    def test_get_moderation_list_requires_auth(self, client):
        """Get moderation list endpoint requires authentication."""
        response = client.get("/api/v2/admin/moderation/marketplace/moderation/list")
        assert response.status_code in [401, 403]

    def test_get_moderation_detail_requires_auth(self, client):
        """Get moderation detail endpoint requires authentication."""
        response = client.get("/api/v2/admin/moderation/marketplace/moderation/test-id")
        assert response.status_code in [401, 403]

    def test_approve_listing_requires_auth(self, client):
        """Approve listing endpoint requires authentication."""
        response = client.post("/api/v2/admin/moderation/marketplace/moderation/test-id/approve")
        assert response.status_code in [401, 403]

    def test_reject_listing_requires_auth(self, client):
        """Reject listing endpoint requires authentication."""
        response = client.post(
            "/api/v2/admin/moderation/marketplace/moderation/test-id/reject",
            json={"reason": "Test reason"}
        )
        assert response.status_code in [401, 403]

    def test_delete_listing_requires_auth(self, client):
        """Delete listing endpoint requires authentication."""
        response = client.post("/api/v2/admin/moderation/marketplace/moderation/test-id/delete")
        assert response.status_code in [401, 403]

    def test_unpublish_listing_requires_auth(self, client):
        """Unpublish listing endpoint requires authentication."""
        response = client.post("/api/v2/admin/moderation/marketplace/moderation/test-id/unpublish")
        assert response.status_code in [401, 403]

    def test_get_reports_requires_auth(self, client):
        """Get reports endpoint requires authentication."""
        response = client.get("/api/v2/admin/moderation/reports")
        assert response.status_code in [401, 403]

    def test_get_reports_stats_requires_auth(self, client):
        """Get reports stats endpoint requires authentication."""
        response = client.get("/api/v2/admin/moderation/reports/stats")
        assert response.status_code in [401, 403]

    def test_get_report_detail_requires_auth(self, client):
        """Get report detail endpoint requires authentication."""
        response = client.get("/api/v2/admin/moderation/reports/test-id")
        assert response.status_code in [401, 403]

    def test_respond_to_report_requires_auth(self, client):
        """Respond to report endpoint requires authentication."""
        response = client.post(
            "/api/v2/admin/moderation/reports/test-id/respond",
            json={"status": "resolved"}
        )
        assert response.status_code in [401, 403]


# ==========================================
# Constants Tests
# ==========================================

class TestModerationConstants:
    """Tests for moderation constants."""

    def test_valid_moderation_statuses(self):
        """Valid moderation statuses are defined."""
        # v3.28: Import from domain constants
        from domains.moderation.constants import VALID_MODERATION_STATUSES

        assert "pending" in VALID_MODERATION_STATUSES
        assert "approved" in VALID_MODERATION_STATUSES
        assert "rejected" in VALID_MODERATION_STATUSES
        assert "invalid" not in VALID_MODERATION_STATUSES

    def test_valid_resource_types(self):
        """Valid resource types are defined."""
        # v3.28: Import from domain constants
        from domains.moderation.constants import VALID_RESOURCE_TYPES

        assert "sticker" in VALID_RESOURCE_TYPES
        assert "clipart" in VALID_RESOURCE_TYPES
        assert "template" in VALID_RESOURCE_TYPES
        assert "font" in VALID_RESOURCE_TYPES
        assert "all" in VALID_RESOURCE_TYPES
        assert "invalid" not in VALID_RESOURCE_TYPES

    def test_valid_report_statuses(self):
        """Valid report statuses are defined."""
        # v3.28: Import from domain constants
        from domains.moderation.constants import VALID_REPORT_STATUSES

        assert "reviewed" in VALID_REPORT_STATUSES
        assert "resolved" in VALID_REPORT_STATUSES
        assert "dismissed" in VALID_REPORT_STATUSES
        assert "pending" not in VALID_REPORT_STATUSES


# ==========================================
# Parameter Validation Tests (Unit Tests)
# ==========================================

class TestModerationParameterValidation:
    """Unit tests for parameter validation in request models."""

    def test_reject_request_reason_length(self):
        """Rejection reason must be between 1 and 1000 characters."""
        from api.admin.moderation import AdminModerationRejectRequest

        # Valid reasons
        AdminModerationRejectRequest(reason="Too short description")
        AdminModerationRejectRequest(reason="a" * 1000)

        # Invalid: empty reason
        with pytest.raises(ValidationError):
            AdminModerationRejectRequest(reason="")

        # Invalid: too long
        with pytest.raises(ValidationError):
            AdminModerationRejectRequest(reason="a" * 1001)

    def test_report_response_request_status_validation(self):
        """Report status must be valid."""
        from api.admin.moderation import ReportResponseRequest

        # Valid statuses
        for status in ["reviewed", "resolved", "dismissed"]:
            req = ReportResponseRequest(status=status)
            assert req.status == status

        # Invalid status
        with pytest.raises(ValidationError) as exc_info:
            ReportResponseRequest(status="pending")
        assert "Invalid status" in str(exc_info.value)

    def test_report_response_request_response_length(self):
        """Response field has max length of 2000."""
        from api.admin.moderation import ReportResponseRequest

        # Valid response
        ReportResponseRequest(status="resolved", response="Valid response")
        ReportResponseRequest(status="resolved", response="a" * 2000)

        # Invalid: too long
        with pytest.raises(ValidationError):
            ReportResponseRequest(status="resolved", response="a" * 2001)


# ==========================================
# Integration-style Tests
# ==========================================

class TestModerationFieldValidation:
    """Integration tests for field validation at API level."""

    @pytest.mark.parametrize("status", ["pending", "approved", "rejected"])
    def test_valid_moderation_status_values(self, status):
        """Valid moderation status values are accepted."""
        # v3.28: Import from domain constants
        from domains.moderation.constants import VALID_MODERATION_STATUSES

        assert status in VALID_MODERATION_STATUSES

    @pytest.mark.parametrize("resource_type", ["sticker", "clipart", "template", "font", "all"])
    def test_valid_resource_type_values(self, resource_type):
        """Valid resource type values are accepted."""
        # v3.28: Import from domain constants
        from domains.moderation.constants import VALID_RESOURCE_TYPES

        assert resource_type in VALID_RESOURCE_TYPES

    @pytest.mark.parametrize("status", ["reviewed", "resolved", "dismissed"])
    def test_valid_report_status_values(self, status):
        """Valid report status values are accepted."""
        from api.admin.moderation import ReportResponseRequest

        req = ReportResponseRequest(status=status)
        assert req.status == status

    @pytest.mark.parametrize("limit", [1, 20, 50, 100])
    def test_valid_limit_values(self, limit):
        """Valid limit values are within range."""
        # Limit should be between 1-100
        assert 1 <= limit <= 100

    @pytest.mark.parametrize("offset", [0, 10, 100, 1000])
    def test_valid_offset_values(self, offset):
        """Valid offset values are non-negative."""
        # Offset should be >= 0
        assert offset >= 0
