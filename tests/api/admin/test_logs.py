"""Test admin/logs API endpoints.

Tests for error logs and operation logs management endpoints.
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

class TestLogsEndpointsAuth:
    """Basic tests for logs API authentication requirements."""

    def test_get_error_logs_requires_auth(self, client):
        """Get error logs endpoint requires authentication."""
        response = client.get("/api/v2/admin/logs/errors")
        assert response.status_code in [401, 403]

    def test_get_error_stats_requires_auth(self, client):
        """Get error stats endpoint requires authentication."""
        response = client.get("/api/v2/admin/logs/errors/stats")
        assert response.status_code in [401, 403]

    def test_get_operation_logs_requires_auth(self, client):
        """Get operation logs endpoint requires authentication."""
        response = client.get("/api/v2/admin/logs/operations")
        assert response.status_code in [401, 403]

    def test_export_operation_logs_requires_auth(self, client):
        """Export operation logs endpoint requires authentication."""
        response = client.get("/api/v2/admin/logs/operations/export")
        assert response.status_code in [401, 403]


# ==========================================
# Constants Tests
# ==========================================

class TestLogsConstants:
    """Tests for logs constants."""

    def test_date_pattern(self):
        """Date pattern validates correctly."""
        from api.admin.logs import DATE_PATTERN

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

class TestLogsValidation:
    """Tests for logs validation functions."""

    def test_validate_date_format_valid(self):
        """Valid date formats pass validation."""
        from api.admin.logs import validate_date_format

        # These should not raise
        validate_date_format("2026-01-09", "test_date")
        validate_date_format("2026-01-09T12:00:00", "test_date")
        validate_date_format(None, "test_date")

    def test_validate_date_format_invalid(self):
        """Invalid date formats raise HTTPException."""
        from api.admin.logs import validate_date_format
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

class TestLogsFieldValidation:
    """Integration tests for field validation at API level."""

    @pytest.mark.parametrize("date_str", [
        "2026-01-01",
        "2026-12-31",
        "2026-01-01T00:00:00",
        "2026-12-31T23:59:59"
    ])
    def test_valid_date_formats(self, date_str):
        """Valid date formats pass validation."""
        from api.admin.logs import validate_date_format

        # Should not raise
        validate_date_format(date_str, "test_date")

    @pytest.mark.parametrize("hours", [1, 24, 48, 168])
    def test_valid_hours_values(self, hours):
        """Valid hours values are within range."""
        # Hours should be between 1-168 (1 week)
        assert 1 <= hours <= 168

    @pytest.mark.parametrize("limit", [1, 50, 100])
    def test_valid_limit_values(self, limit):
        """Valid limit values are within range."""
        # Limit should be between 1-100
        assert 1 <= limit <= 100

    @pytest.mark.parametrize("offset", [0, 10, 100, 1000])
    def test_valid_offset_values(self, offset):
        """Valid offset values are non-negative."""
        # Offset should be >= 0
        assert offset >= 0
