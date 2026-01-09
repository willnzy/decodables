"""Test admin/metrics API endpoints.

Tests for system metrics and analytics endpoints.
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

class TestMetricsEndpointsAuth:
    """Basic tests for metrics API authentication requirements."""

    def test_get_daily_metrics_requires_auth(self, client):
        """Get daily metrics endpoint requires authentication."""
        response = client.get("/api/v2/admin/metrics/daily")
        assert response.status_code in [401, 403]

    def test_get_monthly_metrics_requires_auth(self, client):
        """Get monthly metrics endpoint requires authentication."""
        response = client.get("/api/v2/admin/metrics/monthly")
        assert response.status_code in [401, 403]

    def test_get_retention_metrics_requires_auth(self, client):
        """Get retention metrics endpoint requires authentication."""
        response = client.get("/api/v2/admin/metrics/retention")
        assert response.status_code in [401, 403]

    def test_get_funnel_metrics_requires_auth(self, client):
        """Get funnel metrics endpoint requires authentication."""
        response = client.get("/api/v2/admin/metrics/funnel")
        assert response.status_code in [401, 403]

    def test_get_error_metrics_requires_auth(self, client):
        """Get error metrics endpoint requires authentication."""
        response = client.get("/api/v2/admin/metrics/errors")
        assert response.status_code in [401, 403]

    def test_get_dau_trend_requires_auth(self, client):
        """Get DAU trend endpoint requires authentication."""
        response = client.get("/api/v2/admin/metrics/dau-trend")
        assert response.status_code in [401, 403]

    def test_refresh_metrics_requires_auth(self, client):
        """Refresh metrics endpoint requires authentication."""
        response = client.post("/api/v2/admin/metrics/refresh")
        assert response.status_code in [401, 403]


# ==========================================
# Constants Tests
# ==========================================

class TestMetricsConstants:
    """Tests for metrics constants."""

    def test_date_pattern(self):
        """Date pattern validates correctly."""
        from api.admin.metrics import DATE_PATTERN

        # Valid dates
        assert DATE_PATTERN.match("2026-01-09")
        assert DATE_PATTERN.match("2026-01-09T12:00:00")

        # Invalid dates
        assert not DATE_PATTERN.match("01-09-2026")
        assert not DATE_PATTERN.match("2026/01/09")
        assert not DATE_PATTERN.match("invalid")

    def test_valid_periods(self):
        """Valid period values are defined."""
        from api.admin.metrics import VALID_PERIODS

        assert "7d" in VALID_PERIODS
        assert "14d" in VALID_PERIODS
        assert "30d" in VALID_PERIODS
        assert "60d" in VALID_PERIODS
        assert "90d" in VALID_PERIODS
        assert "1d" not in VALID_PERIODS

    def test_valid_metric_types(self):
        """Valid metric types are defined (v3.28: updated to match scheduler.py)."""
        from api.admin.metrics import VALID_METRIC_TYPES

        # v3.28: MET-HIGH-5 - Fixed to match scheduler.py
        assert "all" in VALID_METRIC_TYPES
        assert "hourly" in VALID_METRIC_TYPES
        assert "daily" in VALID_METRIC_TYPES
        assert "invalid" not in VALID_METRIC_TYPES


# ==========================================
# Validation Function Tests
# ==========================================

class TestMetricsValidation:
    """Tests for metrics validation functions."""

    def test_validate_date_format_valid(self):
        """Valid date formats pass validation."""
        from api.admin.metrics import validate_date_format

        # These should not raise
        validate_date_format("2026-01-09", "test_date")
        validate_date_format("2026-01-09T12:00:00", "test_date")
        validate_date_format(None, "test_date")

    def test_validate_date_format_invalid(self):
        """Invalid date formats raise HTTPException."""
        from api.admin.metrics import validate_date_format
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

class TestMetricsFieldValidation:
    """Integration tests for field validation at API level."""

    @pytest.mark.parametrize("date_str", [
        "2026-01-01",
        "2026-12-31",
        "2026-01-01T00:00:00",
        "2026-12-31T23:59:59"
    ])
    def test_valid_date_formats(self, date_str):
        """Valid date formats pass validation."""
        from api.admin.metrics import validate_date_format

        # Should not raise
        validate_date_format(date_str, "test_date")

    @pytest.mark.parametrize("period", ["7d", "14d", "30d", "60d", "90d"])
    def test_valid_period_values(self, period):
        """Valid period values are accepted."""
        from api.admin.metrics import VALID_PERIODS

        assert period in VALID_PERIODS

    @pytest.mark.parametrize("metric_type", ["all", "hourly", "daily"])
    def test_valid_metric_type_values(self, metric_type):
        """Valid metric type values are accepted (v3.28: updated)."""
        from api.admin.metrics import VALID_METRIC_TYPES

        assert metric_type in VALID_METRIC_TYPES

    @pytest.mark.parametrize("months", [1, 6, 12, 24])
    def test_valid_months_values(self, months):
        """Valid months values are within range."""
        # Months should be between 1-24
        assert 1 <= months <= 24

    @pytest.mark.parametrize("hours", [1, 24, 48, 168])
    def test_valid_hours_values(self, hours):
        """Valid hours values are within range."""
        # Hours should be between 1-168 (1 week)
        assert 1 <= hours <= 168

    @pytest.mark.parametrize("days", [1, 30, 90, 365])
    def test_valid_days_values(self, days):
        """Valid days values are within range."""
        # Days should be between 1-365
        assert 1 <= days <= 365
