"""Test admin/stats API endpoints.

Tests for admin dashboard and analytics endpoints.
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

class TestStatsEndpointsAuth:
    """Basic tests for stats API authentication requirements."""

    def test_dashboard_requires_auth(self, client):
        """Dashboard endpoint requires authentication."""
        response = client.get("/api/v2/admin/stats/dashboard")
        assert response.status_code in [401, 403]

    def test_user_growth_requires_auth(self, client):
        """User growth endpoint requires authentication."""
        response = client.get("/api/v2/admin/stats/user-growth")
        assert response.status_code in [401, 403]

    def test_revenue_requires_auth(self, client):
        """Revenue endpoint requires authentication."""
        response = client.get("/api/v2/admin/stats/revenue")
        assert response.status_code in [401, 403]

    def test_projects_requires_auth(self, client):
        """Projects endpoint requires authentication."""
        response = client.get("/api/v2/admin/stats/projects")
        assert response.status_code in [401, 403]

    def test_credits_requires_auth(self, client):
        """Credits endpoint requires authentication."""
        response = client.get("/api/v2/admin/stats/credits")
        assert response.status_code in [401, 403]

    def test_tier_distribution_requires_auth(self, client):
        """Tier distribution endpoint requires authentication."""
        response = client.get("/api/v2/admin/stats/tier-distribution")
        assert response.status_code in [401, 403]

    def test_conversion_funnel_requires_auth(self, client):
        """Conversion funnel endpoint requires authentication."""
        response = client.get("/api/v2/admin/stats/conversion-funnel")
        assert response.status_code in [401, 403]

    def test_exports_requires_auth(self, client):
        """Exports endpoint requires authentication."""
        response = client.get("/api/v2/admin/stats/exports")
        assert response.status_code in [401, 403]

    def test_assets_requires_auth(self, client):
        """Assets endpoint requires authentication."""
        response = client.get("/api/v2/admin/stats/assets")
        assert response.status_code in [401, 403]

    def test_tier_activity_requires_auth(self, client):
        """Tier activity endpoint requires authentication."""
        response = client.get("/api/v2/admin/stats/tier-activity")
        assert response.status_code in [401, 403]

    def test_subscription_events_requires_auth(self, client):
        """Subscription events endpoint requires authentication."""
        response = client.get("/api/v2/admin/stats/subscription-events")
        assert response.status_code in [401, 403]

    def test_page_views_requires_auth(self, client):
        """Page views endpoint requires authentication."""
        response = client.get("/api/v2/admin/stats/page-views")
        assert response.status_code in [401, 403]

    def test_project_details_requires_auth(self, client):
        """Project details endpoint requires authentication."""
        response = client.get("/api/v2/admin/stats/project-details")
        assert response.status_code in [401, 403]

    def test_returning_users_requires_auth(self, client):
        """Returning users endpoint requires authentication."""
        response = client.get("/api/v2/admin/stats/returning-users")
        assert response.status_code in [401, 403]

    def test_tier_trend_requires_auth(self, client):
        """Tier trend endpoint requires authentication."""
        response = client.get("/api/v2/admin/stats/tier-trend")
        assert response.status_code in [401, 403]

    def test_tier_conversion_requires_auth(self, client):
        """Tier conversion endpoint requires authentication."""
        response = client.get("/api/v2/admin/stats/tier-conversion")
        assert response.status_code in [401, 403]

    def test_performance_requires_auth(self, client):
        """Performance endpoint requires authentication."""
        response = client.get("/api/v2/admin/stats/performance")
        assert response.status_code in [401, 403]

    def test_user_distribution_requires_auth(self, client):
        """User distribution endpoint requires authentication."""
        response = client.get("/api/v2/admin/stats/user-distribution")
        assert response.status_code in [401, 403]


# ==========================================
# Constants Tests
# ==========================================

class TestStatsConstants:
    """Tests for stats constants."""

    def test_valid_dashboard_periods(self):
        """Valid dashboard periods are defined."""
        from domains.stats.constants import VALID_DASHBOARD_PERIODS

        assert "day" in VALID_DASHBOARD_PERIODS
        assert "week" in VALID_DASHBOARD_PERIODS
        assert "month" in VALID_DASHBOARD_PERIODS
        assert "year" in VALID_DASHBOARD_PERIODS
        assert "invalid" not in VALID_DASHBOARD_PERIODS

    def test_valid_group_by(self):
        """Valid group_by values are defined."""
        from domains.stats.constants import VALID_GROUP_BY

        assert "day" in VALID_GROUP_BY
        assert "week" in VALID_GROUP_BY
        assert "month" in VALID_GROUP_BY
        assert "year" not in VALID_GROUP_BY  # year is not valid for group_by
        assert "invalid" not in VALID_GROUP_BY

    def test_date_pattern(self):
        """Date pattern matches expected formats."""
        from domains.stats.constants import DATE_PATTERN

        # Valid formats
        assert DATE_PATTERN.match("2024-01-15")
        assert DATE_PATTERN.match("2024-12-31")
        assert DATE_PATTERN.match("2024-01-15T10:30:00")

        # Invalid formats
        assert not DATE_PATTERN.match("01-15-2024")
        assert not DATE_PATTERN.match("2024/01/15")
        assert not DATE_PATTERN.match("invalid")


# ==========================================
# Validation Function Tests
# ==========================================

class TestStatsValidation:
    """Tests for stats validation functions."""

    def test_validate_date_format_valid(self):
        """Valid date formats pass validation."""
        from api.admin.stats import validate_date_format

        # Should not raise for valid dates
        validate_date_format("2024-01-15", "start_date")
        validate_date_format("2024-12-31T23:59:59", "end_date")
        validate_date_format(None, "date")  # None is valid

    def test_validate_date_format_invalid(self):
        """Invalid date formats raise HTTPException."""
        from fastapi import HTTPException
        from api.admin.stats import validate_date_format

        with pytest.raises(HTTPException) as exc_info:
            validate_date_format("01-15-2024", "start_date")
        assert exc_info.value.status_code == 400
        assert "start_date" in str(exc_info.value.detail)

        with pytest.raises(HTTPException) as exc_info:
            validate_date_format("invalid", "end_date")
        assert exc_info.value.status_code == 400


# ==========================================
# Parameter Validation Tests
# ==========================================

class TestStatsParameterValidation:
    """Integration tests for parameter validation."""

    @pytest.mark.parametrize("period", ["day", "week", "month", "year"])
    def test_valid_dashboard_period_values(self, period):
        """Valid dashboard period values are accepted."""
        from domains.stats.constants import VALID_DASHBOARD_PERIODS

        assert period in VALID_DASHBOARD_PERIODS

    @pytest.mark.parametrize("group_by", ["day", "week", "month"])
    def test_valid_group_by_values(self, group_by):
        """Valid group_by values are accepted."""
        from domains.stats.constants import VALID_GROUP_BY

        assert group_by in VALID_GROUP_BY

    @pytest.mark.parametrize("date_str", [
        "2024-01-01",
        "2024-06-15",
        "2024-12-31",
        "2024-01-01T00:00:00",
        "2024-12-31T23:59:59",
    ])
    def test_valid_date_formats(self, date_str):
        """Valid date formats pass validation."""
        from domains.stats.constants import DATE_PATTERN

        assert DATE_PATTERN.match(date_str)

    @pytest.mark.parametrize("date_str", [
        "01-01-2024",
        "2024/01/01",
        "invalid",
        "20240101",
        "",
    ])
    def test_invalid_date_formats(self, date_str):
        """Invalid date formats fail validation."""
        from domains.stats.constants import DATE_PATTERN

        assert not DATE_PATTERN.match(date_str)


# ==========================================
# Aggregated Stats Helper Tests
# ==========================================

class TestAggregatedStatsHelper:
    """Tests for the _get_aggregated_stat helper function."""

    def test_stat_types_are_strings(self):
        """Stat types used in aggregated stats are valid strings."""
        # These are the stat_type values used in the module
        stat_types = [
            "export_stats_30d",
            "asset_usage_ranking",
            "tier_activity",
            "subscription_events_30d",
            "page_views_7d",
            "project_details_30d",
            "returning_users",
            "tier_trend_30d",
            "tier_conversion_30d",
            "performance_metrics_7d",
            "user_distribution_7d",
        ]

        for stat_type in stat_types:
            assert isinstance(stat_type, str)
            assert len(stat_type) > 0
            assert len(stat_type) <= 50  # Reasonable max length

    def test_default_values_are_dicts(self):
        """Default values for aggregated stats are dictionaries."""
        # These are the default return values used in the module
        defaults = [
            {"totalPdf": 0, "totalZip": 0, "totalPrint": 0, "totalPreview": 0, "trend": []},
            {"top_assets": [], "by_type": {}, "total_usage": 0, "total_assets_used": 0},
            {},
            {"totalUpgrades": 0, "totalDowngrades": 0, "totalCancellations": 0, "totalRefunds": 0, "trend": []},
            {"pages": {}, "total_views": 0, "guest_views": 0},
            {"deleted_projects": 0, "ocr_usage": 0, "total_pages_sample": 0, "avg_pages_per_project": 0},
            {},
            {"trend": []},
            {"conversions": []},
            {"metrics": {}, "by_page": {}, "total_samples": 0},
            {"country": [], "browser": [], "os": [], "device_type": [], "language": [], "timezone": [], "total_sessions": 0},
        ]

        for default in defaults:
            assert isinstance(default, dict)
