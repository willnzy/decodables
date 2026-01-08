"""Test admin/ai API endpoints.

Tests for AI insights and report generation endpoints.
v3.25: Added comprehensive tests including security validation.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

from app import app


# ==========================================
# Test Constants
# ==========================================

VALID_DATE = "2024-01-15"
VALID_ISO_DATE = "2024-01-15T10:30:00"
INVALID_DATE = "not-a-date"
INVALID_DATE_2 = "15-01-2024"  # Wrong format

# Test users
ADMIN_USER = {"id": "admin-user-id", "email": "admin@test.com", "role": "admin"}


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def admin_headers():
    """Admin authorization headers."""
    return {"Authorization": "Bearer test_admin_token"}


# ==========================================
# Basic Endpoint Tests
# ==========================================

class TestAdminAiEndpoints:
    """Basic tests for admin AI API endpoints."""

    def test_insights_requires_auth(self, client):
        """Insights endpoint requires authentication."""
        response = client.get("/api/v2/admin/ai/insights")
        assert response.status_code in [401, 403]

    def test_recommendations_requires_auth(self, client):
        """Recommendations endpoint requires authentication."""
        response = client.get("/api/v2/admin/ai/recommendations")
        assert response.status_code in [401, 403]

    def test_behavior_analysis_requires_auth(self, client):
        """Behavior analysis endpoint requires authentication."""
        response = client.get("/api/v2/admin/ai/behavior-analysis")
        assert response.status_code in [401, 403]

    def test_generate_report_requires_auth(self, client):
        """Generate report endpoint requires authentication."""
        response = client.post("/api/v2/admin/ai/generate-report")
        assert response.status_code in [401, 403]

    def test_quick_insights_requires_auth(self, client):
        """Quick insights endpoint requires authentication."""
        response = client.get("/api/v2/admin/ai/quick-insights")
        assert response.status_code in [401, 403]


# ==========================================
# Parameter Validation Tests (Unit Tests)
# ==========================================

class TestAiParameterValidation:
    """Unit tests for parameter validation functions."""

    def test_date_pattern_valid_dates(self):
        """Valid date formats are accepted."""
        from api.admin.ai import DATE_PATTERN

        valid_dates = [
            "2024-01-15",
            "2024-12-31",
            "2024-01-15T10:30:00",
            "2024-01-15T23:59:59",
        ]

        for date in valid_dates:
            assert DATE_PATTERN.match(date) is not None, f"Date {date} should be valid"

    def test_date_pattern_invalid_dates(self):
        """Invalid date formats are rejected."""
        from api.admin.ai import DATE_PATTERN

        invalid_dates = [
            "invalid",
            "15-01-2024",
            "01/15/2024",
            "2024/01/15",
            "2024-1-15",
            "20240115",
        ]

        for date in invalid_dates:
            assert DATE_PATTERN.match(date) is None, f"Date {date} should be invalid"

    def test_valid_insight_types_set(self):
        """Valid insight types are defined."""
        from api.admin.ai import VALID_INSIGHT_TYPES

        assert "all" in VALID_INSIGHT_TYPES
        assert "growth" in VALID_INSIGHT_TYPES
        assert "engagement" in VALID_INSIGHT_TYPES
        assert "revenue" in VALID_INSIGHT_TYPES
        assert "invalid" not in VALID_INSIGHT_TYPES

    def test_valid_recommendation_areas_set(self):
        """Valid recommendation areas are defined."""
        from api.admin.ai import VALID_RECOMMENDATION_AREAS

        assert "all" in VALID_RECOMMENDATION_AREAS
        assert "growth" in VALID_RECOMMENDATION_AREAS
        assert "retention" in VALID_RECOMMENDATION_AREAS
        assert "monetization" in VALID_RECOMMENDATION_AREAS
        assert "invalid" not in VALID_RECOMMENDATION_AREAS

    def test_valid_report_types_set(self):
        """Valid report types are defined."""
        from api.admin.ai import VALID_REPORT_TYPES

        assert "comprehensive" in VALID_REPORT_TYPES
        assert "growth" in VALID_REPORT_TYPES
        assert "engagement" in VALID_REPORT_TYPES
        assert "revenue" in VALID_REPORT_TYPES
        assert "quick" in VALID_REPORT_TYPES
        assert "invalid" not in VALID_REPORT_TYPES

    def test_valid_time_ranges_set(self):
        """Valid time ranges are defined."""
        from api.admin.ai import VALID_TIME_RANGES

        assert "7d" in VALID_TIME_RANGES
        assert "30d" in VALID_TIME_RANGES
        assert "90d" in VALID_TIME_RANGES
        assert "365d" in VALID_TIME_RANGES
        assert "1y" not in VALID_TIME_RANGES


class TestValidateDateFormat:
    """Unit tests for validate_date_format function."""

    def test_validate_date_format_valid(self):
        """Valid dates pass validation."""
        from api.admin.ai import validate_date_format

        # Should not raise
        validate_date_format("2024-01-15", "test_date")
        validate_date_format("2024-01-15T10:30:00", "test_date")
        validate_date_format(None, "test_date")  # None is allowed

    def test_validate_date_format_invalid(self):
        """Invalid dates raise HTTPException."""
        from api.admin.ai import validate_date_format
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            validate_date_format("invalid", "test_date")
        assert exc_info.value.status_code == 400
        assert "test_date" in exc_info.value.detail

        with pytest.raises(HTTPException) as exc_info:
            validate_date_format("15-01-2024", "start_date")
        assert exc_info.value.status_code == 400
        assert "start_date" in exc_info.value.detail


# ==========================================
# Repository Method Tests
# ==========================================

class TestAdminGetAiInsights:
    """Tests for admin_get_ai_insights repository method."""

    @pytest.mark.asyncio
    async def test_returns_insights_list(self):
        """Returns list of insights."""
        from infrastructure.repositories.admin_repository import SupabaseAdminStatsRepository

        mock_client = MagicMock()
        # Mock profiles query
        mock_client.table.return_value.select.return_value.gte.return_value.execute.return_value = MagicMock(
            count=100
        )
        # Mock for neq query (paying users)
        mock_client.table.return_value.select.return_value.neq.return_value.eq.return_value.execute.return_value = MagicMock(
            count=10
        )
        # Mock for projects query
        mock_client.table.return_value.select.return_value.gte.return_value.eq.return_value.execute.return_value = MagicMock(
            count=50
        )

        repo = SupabaseAdminStatsRepository(mock_client)
        result = await repo.admin_get_ai_insights("all")

        assert isinstance(result, list)
        assert len(result) >= 1  # At least one insight

    @pytest.mark.asyncio
    async def test_filters_by_type(self):
        """Filters insights by type."""
        from infrastructure.repositories.admin_repository import SupabaseAdminStatsRepository

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.gte.return_value.execute.return_value = MagicMock(
            count=100
        )

        repo = SupabaseAdminStatsRepository(mock_client)
        result = await repo.admin_get_ai_insights("growth")

        assert isinstance(result, list)
        # Should only have growth category
        for insight in result:
            assert insight.get("category") == "growth"


class TestAdminGetAiRecommendations:
    """Tests for admin_get_ai_recommendations repository method."""

    @pytest.mark.asyncio
    async def test_returns_recommendations_list(self):
        """Returns list of recommendations."""
        from infrastructure.repositories.admin_repository import SupabaseAdminStatsRepository

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.gte.return_value.execute.return_value = MagicMock(
            count=10
        )
        mock_client.table.return_value.select.return_value.execute.return_value = MagicMock(
            count=100, data=[]
        )
        mock_client.table.return_value.select.return_value.neq.return_value.execute.return_value = MagicMock(
            count=5
        )

        repo = SupabaseAdminStatsRepository(mock_client)
        result = await repo.admin_get_ai_recommendations("all")

        assert isinstance(result, list)


class TestAdminGetBehaviorAnalysis:
    """Tests for admin_get_behavior_analysis repository method."""

    @pytest.mark.asyncio
    async def test_returns_behavior_data(self):
        """Returns behavior analysis data."""
        from infrastructure.repositories.admin_repository import SupabaseAdminStatsRepository

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(
            data=[
                {"event_type": "page_view", "created_at": "2024-01-15T10:30:00"}
            ]
        )
        mock_client.table.return_value.select.return_value.execute.return_value = MagicMock(
            data=[{"tier": "free"}, {"tier": "pro"}]
        )

        repo = SupabaseAdminStatsRepository(mock_client)
        result = await repo.admin_get_behavior_analysis()

        assert isinstance(result, dict)
        assert "patterns" in result
        assert "segments" in result
        assert "period" in result
