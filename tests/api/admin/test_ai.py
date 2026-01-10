"""Test admin/ai API endpoints.

Tests for AI insights and report generation endpoints.
v3.28: Complete rewrite with FastAPI dependency override + rate limiter mocking.
v3.25: Added comprehensive tests including security validation.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

# CRITICAL: Mock modules BEFORE importing app
# This prevents Redis/import errors in test environment
import sys

# Mock rate limiter
if 'infrastructure.rate_limiter' not in sys.modules:
    limiter_mock = MagicMock()
    limiter_mock.limit = lambda x: lambda func: func  # No-op decorator
    sys.modules['infrastructure.rate_limiter'] = MagicMock(limiter=limiter_mock)

# Mock ai_reports module (doesn't exist yet, but endpoints try to import it)
if 'application.services.ai_reports' not in sys.modules:
    ai_reports_mock = MagicMock()
    ai_reports_mock.generate_ai_business_report = MagicMock(return_value={"report": "test"})
    ai_reports_mock.get_quick_insights = MagicMock(return_value=[])
    sys.modules['application.services.ai_reports'] = ai_reports_mock

from app import app
from dependencies import require_admin


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
def mock_limiter():
    """Mock rate limiter to avoid Redis connection."""
    with patch('infrastructure.rate_limiter.limiter') as mock:
        # Make limit() return a pass-through decorator
        mock.limit.return_value = lambda func: func
        yield mock


@pytest.fixture
def client(mock_limiter):
    """Create test client with mocked rate limiter."""
    return TestClient(app)


@pytest.fixture
def override_require_admin():
    """Override admin authentication for testing."""
    async def mock_admin():
        return ADMIN_USER

    app.dependency_overrides[require_admin] = mock_admin
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def admin_headers():
    """Admin authorization headers (for reference, not actually used with override)."""
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
        assert "invalid" not in VALID_TIME_RANGES


class TestValidateDateFormat:
    """Unit tests for validate_date_format function."""

    def test_validate_date_format_valid(self):
        """Valid dates pass validation."""
        from api.admin.ai import validate_date_format

        validate_date_format("2024-01-15", "start_date")
        validate_date_format("2024-01-15T10:30:00", "end_date")
        validate_date_format(None, "start_date")  # None should be allowed

    def test_validate_date_format_invalid(self):
        """Invalid dates raise HTTPException."""
        from api.admin.ai import validate_date_format
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            validate_date_format("invalid", "start_date")
        assert exc_info.value.status_code == 400


# ==========================================
# Integration Tests with Mocked Domain Services
# ==========================================

class TestAdminGetAiInsights:
    """Integration tests for GET /ai/insights endpoint."""

    @patch('api.admin.ai.get_ai_insights')
    def test_returns_insights_list(self, mock_get_insights, client, override_require_admin):
        """Successfully returns insights list."""
        mock_get_insights.return_value = [
            {"category": "growth", "insight": "User growth increased"},
            {"category": "engagement", "insight": "Engagement stable"}
        ]

        response = client.get("/api/v2/admin/ai/insights")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        mock_get_insights.assert_called_once_with("all")

    @patch('api.admin.ai.get_ai_insights')
    def test_filters_by_type(self, mock_get_insights, client, override_require_admin):
        """Filters insights by specified type."""
        mock_get_insights.return_value = [{"category": "growth", "insight": "Growth data"}]

        response = client.get("/api/v2/admin/ai/insights?type=growth")

        assert response.status_code == 200
        mock_get_insights.assert_called_once_with("growth")


class TestAdminGetAiRecommendations:
    """Integration tests for GET /ai/recommendations endpoint."""

    @patch('api.admin.ai.get_ai_recommendations')
    def test_returns_recommendations_list(self, mock_get_recs, client, override_require_admin):
        """Successfully returns recommendations list."""
        mock_get_recs.return_value = [
            {"area": "growth", "recommendation": "Focus on user acquisition"}
        ]

        response = client.get("/api/v2/admin/ai/recommendations")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        mock_get_recs.assert_called_once_with("all")


class TestAdminGetBehaviorAnalysis:
    """Integration tests for GET /ai/behavior-analysis endpoint."""

    @patch('api.admin.ai.get_behavior_analysis')
    def test_returns_behavior_data(self, mock_get_behavior, client, override_require_admin):
        """Successfully returns behavior analysis data."""
        mock_get_behavior.return_value = {
            "analysis": "User behavior patterns",
            "trends": []
        }

        response = client.get("/api/v2/admin/ai/behavior-analysis")

        assert response.status_code == 200
        data = response.json()
        assert "analysis" in data
        mock_get_behavior.assert_called_once()


# ==========================================
# Success Tests with Full Mock
# ==========================================

class TestInsightsSuccess:
    """Success tests for insights endpoint."""

    @patch('api.admin.ai.get_ai_insights')
    def test_insights_success_all_type(self, mock_insights, client, override_require_admin):
        """Insights endpoint works with type=all."""
        mock_insights.return_value = [
            {"category": "growth", "insight": "Growth positive"},
            {"category": "revenue", "insight": "Revenue increasing"}
        ]

        response = client.get("/api/v2/admin/ai/insights?type=all")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        mock_insights.assert_called_once_with("all")

    @patch('api.admin.ai.get_ai_insights')
    def test_insights_success_growth_type(self, mock_insights, client, override_require_admin):
        """Insights endpoint works with type=growth."""
        mock_insights.return_value = [{"category": "growth", "insight": "Growth data"}]

        response = client.get("/api/v2/admin/ai/insights?type=growth")

        assert response.status_code == 200
        mock_insights.assert_called_once_with("growth")


class TestRecommendationsSuccess:
    """Success tests for recommendations endpoint."""

    @patch('api.admin.ai.get_ai_recommendations')
    def test_recommendations_success_all_area(self, mock_recs, client, override_require_admin):
        """Recommendations endpoint works with area=all."""
        mock_recs.return_value = [
            {"area": "growth", "recommendation": "Increase marketing"},
            {"area": "retention", "recommendation": "Improve onboarding"}
        ]

        response = client.get("/api/v2/admin/ai/recommendations?area=all")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        mock_recs.assert_called_once_with("all")

    @patch('api.admin.ai.get_ai_recommendations')
    def test_recommendations_success_retention_area(self, mock_recs, client, override_require_admin):
        """Recommendations endpoint works with area=retention."""
        mock_recs.return_value = [{"area": "retention", "recommendation": "Improve retention"}]

        response = client.get("/api/v2/admin/ai/recommendations?area=retention")

        assert response.status_code == 200
        mock_recs.assert_called_once_with("retention")


class TestBehaviorAnalysisSuccess:
    """Success tests for behavior analysis endpoint."""

    @patch('api.admin.ai.get_behavior_analysis')
    def test_behavior_analysis_success_with_dates(self, mock_behavior, client, override_require_admin):
        """Behavior analysis works with date range."""
        mock_behavior.return_value = {"patterns": [], "summary": "Analysis complete"}

        response = client.get(
            "/api/v2/admin/ai/behavior-analysis"
            "?start_date=2024-01-01&end_date=2024-01-31"
        )

        assert response.status_code == 200
        mock_behavior.assert_called_once()


class TestGenerateReportSuccess:
    """Success tests for generate report endpoint."""

    @patch('application.services.ai_reports.generate_ai_business_report')
    def test_generate_report_success_comprehensive(self, mock_report, client, override_require_admin):
        """Generate report works for comprehensive type."""
        mock_report.return_value = {
            "executive_summary": "Test summary",
            "key_insights": [],
            "report_type": "comprehensive"
        }

        response = client.post(
            "/api/v2/admin/ai/generate-report?report_type=comprehensive&time_range=30d"
        )

        assert response.status_code == 200
        data = response.json()
        assert "executive_summary" in data


class TestQuickInsightsSuccess:
    """Success tests for quick insights endpoint."""

    @patch('application.services.ai_reports.get_quick_insights')
    def test_quick_insights_success(self, mock_insights, client, override_require_admin):
        """Quick insights endpoint returns data."""
        mock_insights.return_value = [{"title": "Quick insight", "priority": "high"}]

        response = client.get("/api/v2/admin/ai/quick-insights")

        assert response.status_code == 200
        data = response.json()
        assert "insights" in data
        assert len(data["insights"]) > 0


# ==========================================
# Parameter Validation Tests
# ==========================================

class TestInsightsParameterValidation:
    """Parameter validation for insights endpoint."""

    def test_insights_rejects_invalid_type(self, client, override_require_admin):
        """Insights endpoint rejects invalid type parameter."""
        response = client.get("/api/v2/admin/ai/insights?type=invalid")

        assert response.status_code == 400
        data = response.json()
        assert "message" in data or "detail" in data


class TestRecommendationsParameterValidation:
    """Parameter validation for recommendations endpoint."""

    def test_recommendations_rejects_invalid_area(self, client, override_require_admin):
        """Recommendations endpoint rejects invalid area parameter."""
        response = client.get("/api/v2/admin/ai/recommendations?area=invalid")

        assert response.status_code == 400
        data = response.json()
        assert "message" in data or "detail" in data


class TestBehaviorAnalysisParameterValidation:
    """Parameter validation for behavior analysis endpoint."""

    def test_behavior_analysis_rejects_invalid_date_format(self, client, override_require_admin):
        """Behavior analysis rejects invalid date format."""
        response = client.get("/api/v2/admin/ai/behavior-analysis?start_date=invalid")

        assert response.status_code == 400
        data = response.json()
        assert "message" in data or "detail" in data


class TestGenerateReportParameterValidation:
    """Parameter validation for generate report endpoint."""

    def test_generate_report_rejects_invalid_report_type(self, client, override_require_admin):
        """Generate report rejects invalid report_type."""
        response = client.post(
            "/api/v2/admin/ai/generate-report?report_type=invalid&time_range=30d"
        )

        assert response.status_code == 400
        data = response.json()
        assert "message" in data or "detail" in data

    def test_generate_report_rejects_invalid_time_range(self, client, override_require_admin):
        """Generate report rejects invalid time_range."""
        response = client.post(
            "/api/v2/admin/ai/generate-report?report_type=comprehensive&time_range=invalid"
        )

        assert response.status_code == 400
        data = response.json()
        assert "message" in data or "detail" in data


# ==========================================
# Exception Handling Tests
# ==========================================

class TestInsightsExceptionHandling:
    """Exception handling for insights endpoint."""

    @patch('api.admin.ai.get_ai_insights')
    def test_insights_handles_database_error(self, mock_insights, client, override_require_admin):
        """Insights endpoint handles database errors gracefully."""
        mock_insights.side_effect = Exception("Database connection failed")

        response = client.get("/api/v2/admin/ai/insights")

        assert response.status_code == 500
        data = response.json()
        assert "message" in data or "detail" in data


class TestRecommendationsExceptionHandling:
    """Exception handling for recommendations endpoint."""

    @patch('api.admin.ai.get_ai_recommendations')
    def test_recommendations_handles_database_error(self, mock_recs, client, override_require_admin):
        """Recommendations endpoint handles database errors gracefully."""
        mock_recs.side_effect = Exception("Database error")

        response = client.get("/api/v2/admin/ai/recommendations")

        assert response.status_code == 500
        data = response.json()
        assert "message" in data or "detail" in data


class TestBehaviorAnalysisExceptionHandling:
    """Exception handling for behavior analysis endpoint."""

    @patch('api.admin.ai.get_behavior_analysis')
    def test_behavior_analysis_handles_database_error(self, mock_behavior, client, override_require_admin):
        """Behavior analysis handles database errors gracefully."""
        mock_behavior.side_effect = Exception("Database error")

        response = client.get("/api/v2/admin/ai/behavior-analysis")

        assert response.status_code == 500
        data = response.json()
        assert "message" in data or "detail" in data


class TestGenerateReportExceptionHandling:
    """Exception handling for generate report endpoint."""

    @patch('application.services.ai_reports.generate_ai_business_report')
    def test_generate_report_handles_openai_error(self, mock_report, client, override_require_admin):
        """Generate report handles OpenAI API errors gracefully."""
        mock_report.side_effect = Exception("OpenAI API timeout")

        response = client.post(
            "/api/v2/admin/ai/generate-report?report_type=comprehensive&time_range=30d"
        )

        assert response.status_code == 500
        data = response.json()
        assert "message" in data or "detail" in data


# ==========================================
# Boundary Cases
# ==========================================

class TestBehaviorAnalysisBoundaryCases:
    """Boundary case tests for behavior analysis endpoint."""

    @patch('api.admin.ai.get_behavior_analysis')
    def test_behavior_analysis_same_start_end_date(self, mock_behavior, client, override_require_admin):
        """Behavior analysis handles same start and end date."""
        mock_behavior.return_value = {"data": "single day"}

        response = client.get(
            "/api/v2/admin/ai/behavior-analysis"
            "?start_date=2024-01-15&end_date=2024-01-15"
        )

        assert response.status_code == 200

    @patch('api.admin.ai.get_behavior_analysis')
    def test_behavior_analysis_future_dates(self, mock_behavior, client, override_require_admin):
        """Behavior analysis handles future dates."""
        mock_behavior.return_value = {"data": "future"}

        response = client.get(
            "/api/v2/admin/ai/behavior-analysis"
            "?start_date=2025-01-01&end_date=2025-12-31"
        )

        # Should work (service may return empty data)
        assert response.status_code in [200, 400]


class TestInsightsBoundaryCases:
    """Boundary case tests for insights endpoint."""

    @patch('api.admin.ai.get_ai_insights')
    def test_insights_all_valid_types(self, mock_insights, client, override_require_admin):
        """Insights endpoint accepts all valid types."""
        mock_insights.return_value = []

        for insight_type in ["all", "growth", "engagement", "revenue"]:
            response = client.get(f"/api/v2/admin/ai/insights?type={insight_type}")
            assert response.status_code == 200


class TestRecommendationsBoundaryCases:
    """Boundary case tests for recommendations endpoint."""

    @patch('api.admin.ai.get_ai_recommendations')
    def test_recommendations_all_valid_areas(self, mock_recs, client, override_require_admin):
        """Recommendations endpoint accepts all valid areas."""
        mock_recs.return_value = []

        for area in ["all", "growth", "retention", "monetization"]:
            response = client.get(f"/api/v2/admin/ai/recommendations?area={area}")
            assert response.status_code == 200
