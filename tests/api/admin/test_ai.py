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
        mock_client.table.return_value.select.return_value.gte.return_value.lte.return_value.limit.return_value.execute.return_value = MagicMock(
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


# ==========================================
# Success Scenario Tests (Integration)
# ==========================================

class TestInsightsSuccess:
    """Test successful insights retrieval scenarios."""

    @patch('api.admin.ai.get_database_client')
    @patch('api.admin.ai.require_admin')
    def test_insights_success_all_type(self, mock_admin, mock_db, client):
        """Successfully retrieve all insights with admin auth."""
        mock_admin.return_value = ADMIN_USER

        mock_repo = MagicMock()
        mock_repo.admin_get_ai_insights = AsyncMock(return_value=[
            {"category": "growth", "title": "User Growth", "metric_value": 100}
        ])

        with patch('api.admin.ai.SupabaseAdminStatsRepository', return_value=mock_repo):
            response = client.get(
                "/api/v2/admin/ai/insights?type=all",
                headers={"Authorization": "Bearer admin_token"}
            )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    @patch('api.admin.ai.get_database_client')
    @patch('api.admin.ai.require_admin')
    def test_insights_success_growth_type(self, mock_admin, mock_db, client):
        """Successfully retrieve growth insights."""
        mock_admin.return_value = ADMIN_USER

        mock_repo = MagicMock()
        mock_repo.admin_get_ai_insights = AsyncMock(return_value=[
            {"category": "growth", "title": "User Growth", "metric_value": 100}
        ])

        with patch('api.admin.ai.SupabaseAdminStatsRepository', return_value=mock_repo):
            response = client.get(
                "/api/v2/admin/ai/insights?type=growth",
                headers={"Authorization": "Bearer admin_token"}
            )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestRecommendationsSuccess:
    """Test successful recommendations retrieval scenarios."""

    @patch('api.admin.ai.get_database_client')
    @patch('api.admin.ai.require_admin')
    def test_recommendations_success_all_area(self, mock_admin, mock_db, client):
        """Successfully retrieve all recommendations."""
        mock_admin.return_value = ADMIN_USER

        mock_repo = MagicMock()
        mock_repo.admin_get_ai_recommendations = AsyncMock(return_value=[
            {"area": "growth", "priority": "high", "title": "Improve signups"}
        ])

        with patch('api.admin.ai.SupabaseAdminStatsRepository', return_value=mock_repo):
            response = client.get(
                "/api/v2/admin/ai/recommendations?area=all",
                headers={"Authorization": "Bearer admin_token"}
            )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @patch('api.admin.ai.get_database_client')
    @patch('api.admin.ai.require_admin')
    def test_recommendations_success_retention_area(self, mock_admin, mock_db, client):
        """Successfully retrieve retention recommendations."""
        mock_admin.return_value = ADMIN_USER

        mock_repo = MagicMock()
        mock_repo.admin_get_ai_recommendations = AsyncMock(return_value=[
            {"area": "retention", "priority": "medium", "title": "Add onboarding"}
        ])

        with patch('api.admin.ai.SupabaseAdminStatsRepository', return_value=mock_repo):
            response = client.get(
                "/api/v2/admin/ai/recommendations?area=retention",
                headers={"Authorization": "Bearer admin_token"}
            )

        assert response.status_code == 200


class TestBehaviorAnalysisSuccess:
    """Test successful behavior analysis scenarios."""

    @patch('api.admin.ai.get_database_client')
    @patch('api.admin.ai.require_admin')
    def test_behavior_analysis_success_with_dates(self, mock_admin, mock_db, client):
        """Successfully retrieve behavior analysis with date range."""
        mock_admin.return_value = ADMIN_USER

        mock_repo = MagicMock()
        mock_repo.admin_get_behavior_analysis = AsyncMock(return_value={
            "patterns": {"event_distribution": {}, "peak_activity_hour": 12},
            "segments": {"by_tier": {"free": 100}, "total_users": 100},
            "period": {"start": "2024-01-01", "end": "2024-01-31"}
        })

        with patch('api.admin.ai.SupabaseAdminStatsRepository', return_value=mock_repo):
            response = client.get(
                "/api/v2/admin/ai/behavior-analysis?start_date=2024-01-01&end_date=2024-01-31",
                headers={"Authorization": "Bearer admin_token"}
            )

        assert response.status_code == 200
        data = response.json()
        assert "patterns" in data
        assert "segments" in data
        assert "period" in data


class TestGenerateReportSuccess:
    """Test successful report generation scenarios."""

    @patch('api.admin.ai.require_admin')
    @patch('application.services.ai_reports.generate_ai_business_report')
    def test_generate_report_success_comprehensive(self, mock_generate, mock_admin, client):
        """Successfully generate comprehensive report."""
        mock_admin.return_value = ADMIN_USER
        mock_generate.return_value = {
            "executive_summary": "Business is growing",
            "key_insights": [],
            "report_type": "comprehensive",
            "time_range": "30d"
        }

        response = client.post(
            "/api/v2/admin/ai/generate-report?report_type=comprehensive&time_range=30d",
            headers={"Authorization": "Bearer admin_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "executive_summary" in data
        assert data["report_type"] == "comprehensive"
        assert data["time_range"] == "30d"


class TestQuickInsightsSuccess:
    """Test successful quick insights retrieval."""

    @patch('api.admin.ai.require_admin')
    @patch('application.services.ai_reports.get_quick_insights')
    def test_quick_insights_success(self, mock_get, mock_admin, client):
        """Successfully retrieve quick insights."""
        mock_admin.return_value = ADMIN_USER
        mock_get.return_value = [
            {"title": "Growth up", "priority": "high"}
        ]

        response = client.get(
            "/api/v2/admin/ai/quick-insights",
            headers={"Authorization": "Bearer admin_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "insights" in data
        assert isinstance(data["insights"], list)


# ==========================================
# Parameter Validation Tests (Integration)
# ==========================================

class TestInsightsParameterValidation:
    """Test insights endpoint parameter validation."""

    @patch('api.admin.ai.require_admin')
    def test_insights_rejects_invalid_type(self, mock_admin, client):
        """Invalid type parameter returns 400."""
        mock_admin.return_value = ADMIN_USER

        response = client.get(
            "/api/v2/admin/ai/insights?type=invalid",
            headers={"Authorization": "Bearer admin_token"}
        )

        assert response.status_code == 400
        assert "Invalid type" in response.json()["detail"]


class TestRecommendationsParameterValidation:
    """Test recommendations endpoint parameter validation."""

    @patch('api.admin.ai.require_admin')
    def test_recommendations_rejects_invalid_area(self, mock_admin, client):
        """Invalid area parameter returns 400."""
        mock_admin.return_value = ADMIN_USER

        response = client.get(
            "/api/v2/admin/ai/recommendations?area=invalid",
            headers={"Authorization": "Bearer admin_token"}
        )

        assert response.status_code == 400
        assert "Invalid area" in response.json()["detail"]


class TestBehaviorAnalysisParameterValidation:
    """Test behavior analysis endpoint parameter validation."""

    @patch('api.admin.ai.require_admin')
    def test_behavior_analysis_rejects_invalid_date_format(self, mock_admin, client):
        """Invalid date format returns 400."""
        mock_admin.return_value = ADMIN_USER

        response = client.get(
            "/api/v2/admin/ai/behavior-analysis?start_date=invalid",
            headers={"Authorization": "Bearer admin_token"}
        )

        assert response.status_code == 400
        assert "Invalid start_date" in response.json()["detail"]


class TestGenerateReportParameterValidation:
    """Test generate report endpoint parameter validation."""

    @patch('api.admin.ai.require_admin')
    def test_generate_report_rejects_invalid_report_type(self, mock_admin, client):
        """Invalid report_type returns 400."""
        mock_admin.return_value = ADMIN_USER

        response = client.post(
            "/api/v2/admin/ai/generate-report?report_type=invalid",
            headers={"Authorization": "Bearer admin_token"}
        )

        assert response.status_code == 400
        assert "Invalid report_type" in response.json()["detail"]

    @patch('api.admin.ai.require_admin')
    def test_generate_report_rejects_invalid_time_range(self, mock_admin, client):
        """Invalid time_range returns 400."""
        mock_admin.return_value = ADMIN_USER

        response = client.post(
            "/api/v2/admin/ai/generate-report?time_range=invalid",
            headers={"Authorization": "Bearer admin_token"}
        )

        assert response.status_code == 400
        assert "Invalid time_range" in response.json()["detail"]


# ==========================================
# Exception Handling Tests
# ==========================================

class TestInsightsExceptionHandling:
    """Test insights endpoint exception handling."""

    @patch('api.admin.ai.get_database_client')
    @patch('api.admin.ai.require_admin')
    def test_insights_handles_database_error(self, mock_admin, mock_db, client):
        """Database error returns 500 with generic message."""
        mock_admin.return_value = ADMIN_USER
        mock_db.side_effect = Exception("Database connection failed")

        response = client.get(
            "/api/v2/admin/ai/insights",
            headers={"Authorization": "Bearer admin_token"}
        )

        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to fetch AI insights"


class TestRecommendationsExceptionHandling:
    """Test recommendations endpoint exception handling."""

    @patch('api.admin.ai.get_database_client')
    @patch('api.admin.ai.require_admin')
    def test_recommendations_handles_database_error(self, mock_admin, mock_db, client):
        """Database error returns 500 with generic message."""
        mock_admin.return_value = ADMIN_USER
        mock_db.side_effect = Exception("Database connection failed")

        response = client.get(
            "/api/v2/admin/ai/recommendations",
            headers={"Authorization": "Bearer admin_token"}
        )

        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to fetch AI recommendations"


class TestBehaviorAnalysisExceptionHandling:
    """Test behavior analysis endpoint exception handling."""

    @patch('api.admin.ai.get_database_client')
    @patch('api.admin.ai.require_admin')
    def test_behavior_analysis_handles_database_error(self, mock_admin, mock_db, client):
        """Database error returns 500 with generic message."""
        mock_admin.return_value = ADMIN_USER
        mock_db.side_effect = Exception("Database connection failed")

        response = client.get(
            "/api/v2/admin/ai/behavior-analysis",
            headers={"Authorization": "Bearer admin_token"}
        )

        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to fetch behavior analysis"


class TestGenerateReportExceptionHandling:
    """Test generate report exception handling."""

    @patch('api.admin.ai.require_admin')
    @patch('application.services.ai_reports.generate_ai_business_report')
    def test_generate_report_handles_openai_error(self, mock_generate, mock_admin, client):
        """OpenAI error returns 500 with generic message."""
        mock_admin.return_value = ADMIN_USER
        mock_generate.side_effect = Exception("OpenAI API error")

        response = client.post(
            "/api/v2/admin/ai/generate-report",
            headers={"Authorization": "Bearer admin_token"}
        )

        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to generate AI report"


# ==========================================
# Boundary Case Tests
# ==========================================

class TestBehaviorAnalysisBoundaryCases:
    """Test behavior analysis boundary cases."""

    @patch('api.admin.ai.get_database_client')
    @patch('api.admin.ai.require_admin')
    def test_behavior_analysis_same_start_end_date(self, mock_admin, mock_db, client):
        """Same start and end date is valid."""
        mock_admin.return_value = ADMIN_USER

        mock_repo = MagicMock()
        mock_repo.admin_get_behavior_analysis = AsyncMock(return_value={
            "patterns": {}, "segments": {}, "period": {}
        })

        with patch('api.admin.ai.SupabaseAdminStatsRepository', return_value=mock_repo):
            response = client.get(
                "/api/v2/admin/ai/behavior-analysis?start_date=2024-01-15&end_date=2024-01-15",
                headers={"Authorization": "Bearer admin_token"}
            )

        assert response.status_code == 200

    @patch('api.admin.ai.require_admin')
    def test_behavior_analysis_future_dates(self, mock_admin, client):
        """Future dates are accepted (no validation against current date)."""
        mock_admin.return_value = ADMIN_USER

        # This should be accepted as date format is valid
        response = client.get(
            "/api/v2/admin/ai/behavior-analysis?start_date=2030-01-01&end_date=2030-12-31",
            headers={"Authorization": "Bearer admin_token"}
        )

        # Should pass format validation (actual logic validation is in Repository)
        assert response.status_code in [200, 500]  # Either succeeds or fails in repo


class TestInsightsBoundaryCases:
    """Test insights boundary cases."""

    @patch('api.admin.ai.get_database_client')
    @patch('api.admin.ai.require_admin')
    def test_insights_all_valid_types(self, mock_admin, mock_db, client):
        """Test all valid insight types."""
        mock_admin.return_value = ADMIN_USER

        mock_repo = MagicMock()
        mock_repo.admin_get_ai_insights = AsyncMock(return_value=[])

        valid_types = ["all", "growth", "engagement", "revenue"]

        with patch('api.admin.ai.SupabaseAdminStatsRepository', return_value=mock_repo):
            for type_val in valid_types:
                response = client.get(
                    f"/api/v2/admin/ai/insights?type={type_val}",
                    headers={"Authorization": "Bearer admin_token"}
                )
                assert response.status_code == 200, f"Type {type_val} should be valid"


class TestRecommendationsBoundaryCases:
    """Test recommendations boundary cases."""

    @patch('api.admin.ai.get_database_client')
    @patch('api.admin.ai.require_admin')
    def test_recommendations_all_valid_areas(self, mock_admin, mock_db, client):
        """Test all valid recommendation areas."""
        mock_admin.return_value = ADMIN_USER

        mock_repo = MagicMock()
        mock_repo.admin_get_ai_recommendations = AsyncMock(return_value=[])

        valid_areas = ["all", "growth", "retention", "monetization"]

        with patch('api.admin.ai.SupabaseAdminStatsRepository', return_value=mock_repo):
            for area_val in valid_areas:
                response = client.get(
                    f"/api/v2/admin/ai/recommendations?area={area_val}",
                    headers={"Authorization": "Bearer admin_token"}
                )
                assert response.status_code == 200, f"Area {area_val} should be valid"
