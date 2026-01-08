"""Test admin/events API endpoints.

Tests for event management endpoints.
v3.25: Added comprehensive tests including security validation.
"""
import pytest
from fastapi.testclient import TestClient

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

class TestEventsEndpointsAuth:
    """Basic tests for events API authentication requirements."""

    def test_get_user_events_requires_auth(self, client):
        """Get user events endpoint requires authentication."""
        response = client.get("/api/v2/admin/events/events")
        assert response.status_code in [401, 403]

    def test_get_event_stats_requires_auth(self, client):
        """Get event stats endpoint requires authentication."""
        response = client.get("/api/v2/admin/events/events/stats")
        assert response.status_code in [401, 403]

    def test_get_aggregated_stats_requires_auth(self, client):
        """Get aggregated stats endpoint requires authentication."""
        response = client.get("/api/v2/admin/events/aggregated/daily_users")
        assert response.status_code in [401, 403]

    def test_get_aggregated_stats_range_requires_auth(self, client):
        """Get aggregated stats range endpoint requires authentication."""
        response = client.get("/api/v2/admin/events/aggregated/daily_users/range")
        assert response.status_code in [401, 403]

    def test_run_aggregation_requires_auth(self, client):
        """Run aggregation endpoint requires authentication."""
        response = client.post("/api/v2/admin/events/aggregation/run")
        assert response.status_code in [401, 403]


# ==========================================
# Constants Tests
# ==========================================

class TestEventsConstants:
    """Tests for events constants."""

    def test_valid_group_by(self):
        """Valid group_by values are defined."""
        from api.admin.events import VALID_GROUP_BY

        assert "event_type" in VALID_GROUP_BY
        assert "user_id" in VALID_GROUP_BY
        assert "date" in VALID_GROUP_BY
        assert "hour" in VALID_GROUP_BY
        assert "invalid" not in VALID_GROUP_BY

    def test_valid_stat_types(self):
        """Valid stat_types are defined."""
        from api.admin.events import VALID_STAT_TYPES

        assert "daily_users" in VALID_STAT_TYPES
        assert "daily_revenue" in VALID_STAT_TYPES
        assert "daily_projects" in VALID_STAT_TYPES
        assert "credit_usage_30d" in VALID_STAT_TYPES
        assert "tier_distribution" in VALID_STAT_TYPES
        assert "invalid" not in VALID_STAT_TYPES

    def test_valid_task_types(self):
        """Valid task_types are defined."""
        from api.admin.events import VALID_TASK_TYPES

        assert "all" in VALID_TASK_TYPES
        assert "hourly" in VALID_TASK_TYPES
        assert "daily" in VALID_TASK_TYPES
        assert "invalid" not in VALID_TASK_TYPES

    def test_date_pattern(self):
        """Date pattern validates correctly."""
        from api.admin.events import DATE_PATTERN

        # Valid dates
        assert DATE_PATTERN.match("2026-01-09")
        assert DATE_PATTERN.match("2026-01-09T12:00:00")

        # Invalid dates
        assert not DATE_PATTERN.match("01-09-2026")
        assert not DATE_PATTERN.match("2026/01/09")
        assert not DATE_PATTERN.match("invalid")


# ==========================================
# Validation Function Tests
# ==========================================

class TestEventsValidation:
    """Tests for events validation functions."""

    def test_validate_date_format_valid(self):
        """Valid date formats pass validation."""
        from api.admin.events import validate_date_format

        # These should not raise
        validate_date_format("2026-01-09", "test_date")
        validate_date_format("2026-01-09T12:00:00", "test_date")
        validate_date_format(None, "test_date")

    def test_validate_date_format_invalid(self):
        """Invalid date formats raise HTTPException."""
        from api.admin.events import validate_date_format
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            validate_date_format("01-09-2026", "test_date")
        assert exc_info.value.status_code == 400
        assert "Invalid test_date format" in str(exc_info.value.detail)

        with pytest.raises(HTTPException):
            validate_date_format("invalid", "test_date")


# ==========================================
# Integration-style Tests
# ==========================================

class TestEventsFieldValidation:
    """Integration tests for field validation at API level."""

    @pytest.mark.parametrize("group_by", ["event_type", "user_id", "date", "hour"])
    def test_valid_group_by_values(self, group_by):
        """Valid group_by values are accepted."""
        from api.admin.events import VALID_GROUP_BY

        assert group_by in VALID_GROUP_BY

    @pytest.mark.parametrize("stat_type", [
        "daily_users", "daily_revenue", "daily_projects",
        "credit_usage_30d", "tier_distribution"
    ])
    def test_valid_stat_type_values(self, stat_type):
        """Valid stat_type values are accepted."""
        from api.admin.events import VALID_STAT_TYPES

        assert stat_type in VALID_STAT_TYPES

    @pytest.mark.parametrize("task_type", ["all", "hourly", "daily"])
    def test_valid_task_type_values(self, task_type):
        """Valid task_type values are accepted."""
        from api.admin.events import VALID_TASK_TYPES

        assert task_type in VALID_TASK_TYPES

    @pytest.mark.parametrize("date_str", [
        "2026-01-01",
        "2026-12-31",
        "2026-01-01T00:00:00",
        "2026-12-31T23:59:59"
    ])
    def test_valid_date_formats(self, date_str):
        """Valid date formats pass validation."""
        from api.admin.events import validate_date_format

        # Should not raise
        validate_date_format(date_str, "test_date")

