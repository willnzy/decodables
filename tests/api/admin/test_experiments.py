"""Test admin/experiments API endpoints.

Tests for A/B testing experiment management endpoints.
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

class TestExperimentsEndpointsAuth:
    """Basic tests for experiments API authentication requirements."""

    def test_list_experiments_requires_auth(self, client):
        """List experiments endpoint requires authentication."""
        response = client.get("/api/v2/admin/experiments")
        assert response.status_code in [401, 403]

    def test_create_experiment_requires_auth(self, client):
        """Create experiment endpoint requires authentication."""
        response = client.post(
            "/api/v2/admin/experiments",
            json={
                "experiment_key": "test_exp",
                "name": "Test Experiment",
                "variants": [{"key": "control", "name": "Control", "weight": 50}, {"key": "variant", "name": "Variant", "weight": 50}]
            }
        )
        assert response.status_code in [401, 403]

    def test_get_experiment_requires_auth(self, client):
        """Get experiment endpoint requires authentication."""
        response = client.get("/api/v2/admin/experiments/test_exp")
        assert response.status_code in [401, 403]

    def test_update_experiment_requires_auth(self, client):
        """Update experiment endpoint requires authentication."""
        response = client.put(
            "/api/v2/admin/experiments/test_exp",
            json={"name": "Updated Name"}
        )
        assert response.status_code in [401, 403]

    def test_update_status_requires_auth(self, client):
        """Update status endpoint requires authentication."""
        response = client.put(
            "/api/v2/admin/experiments/test_exp/status",
            json={"status": "running"}
        )
        assert response.status_code in [401, 403]

    def test_delete_experiment_requires_auth(self, client):
        """Delete experiment endpoint requires authentication."""
        response = client.delete("/api/v2/admin/experiments/test_exp")
        assert response.status_code in [401, 403]

    def test_get_results_requires_auth(self, client):
        """Get results endpoint requires authentication."""
        response = client.get("/api/v2/admin/experiments/test_exp/results")
        assert response.status_code in [401, 403]

    def test_trigger_aggregation_requires_auth(self, client):
        """Trigger aggregation endpoint requires authentication."""
        response = client.post("/api/v2/admin/experiments/test_exp/aggregate")
        assert response.status_code in [401, 403]

    def test_trigger_all_aggregation_requires_auth(self, client):
        """Trigger all aggregation endpoint requires authentication."""
        response = client.post("/api/v2/admin/experiments/aggregate-all")
        assert response.status_code in [401, 403]

    def test_clear_cache_requires_auth(self, client):
        """Clear cache endpoint requires authentication."""
        response = client.post("/api/v2/admin/experiments/cache/clear")
        assert response.status_code in [401, 403]

    def test_ai_analysis_requires_auth(self, client):
        """AI analysis endpoint requires authentication."""
        response = client.post("/api/v2/admin/experiments/test_exp/ai-analysis")
        assert response.status_code in [401, 403]

    def test_quick_recommendation_requires_auth(self, client):
        """Quick recommendation endpoint requires authentication."""
        response = client.get("/api/v2/admin/experiments/test_exp/quick-recommendation")
        assert response.status_code in [401, 403]

    def test_get_trend_requires_auth(self, client):
        """Get trend endpoint requires authentication."""
        response = client.get("/api/v2/admin/experiments/test_exp/trend")
        assert response.status_code in [401, 403]

    def test_get_hourly_trend_requires_auth(self, client):
        """Get hourly trend endpoint requires authentication."""
        response = client.get("/api/v2/admin/experiments/test_exp/hourly-trend")
        assert response.status_code in [401, 403]


# ==========================================
# Parameter Validation Tests (Unit Tests)
# ==========================================

class TestExperimentsParameterValidation:
    """Unit tests for parameter validation in request models."""

    def test_create_request_experiment_type_validation(self):
        """Experiment type must be valid."""
        from api.admin.experiments import ExperimentCreateRequest, VariantConfig

        variants = [
            VariantConfig(key="control", name="Control", weight=50),
            VariantConfig(key="variant", name="Variant", weight=50)
        ]

        # Valid types
        for exp_type in ["ab", "multivariate", "feature_flag"]:
            ExperimentCreateRequest(
                experiment_key="test",
                name="Test",
                experiment_type=exp_type,
                variants=variants
            )

        # Invalid type
        with pytest.raises(ValidationError) as exc_info:
            ExperimentCreateRequest(
                experiment_key="test",
                name="Test",
                experiment_type="invalid",
                variants=variants
            )
        assert "Invalid experiment_type" in str(exc_info.value)

    def test_create_request_key_length(self):
        """Experiment key must be 2-100 characters."""
        from api.admin.experiments import ExperimentCreateRequest, VariantConfig

        variants = [
            VariantConfig(key="control", name="Control", weight=50),
            VariantConfig(key="variant", name="Variant", weight=50)
        ]

        # Valid keys
        ExperimentCreateRequest(experiment_key="ab", name="Test", variants=variants)
        ExperimentCreateRequest(experiment_key="a" * 100, name="Test", variants=variants)

        # Invalid: too short
        with pytest.raises(ValidationError):
            ExperimentCreateRequest(experiment_key="a", name="Test", variants=variants)

        # Invalid: too long
        with pytest.raises(ValidationError):
            ExperimentCreateRequest(experiment_key="a" * 101, name="Test", variants=variants)

    def test_status_update_request_validation(self):
        """Status must be valid."""
        from api.admin.experiments import StatusUpdateRequest

        # Valid statuses
        for status in ["draft", "running", "paused", "completed"]:
            req = StatusUpdateRequest(status=status)
            assert req.status == status

        # Invalid status
        with pytest.raises(ValidationError) as exc_info:
            StatusUpdateRequest(status="invalid")
        assert "Invalid status" in str(exc_info.value)

    def test_variant_config_weight_range(self):
        """Variant weight must be 0-100."""
        from api.admin.experiments import VariantConfig

        # Valid weights
        VariantConfig(key="test", name="Test", weight=0)
        VariantConfig(key="test", name="Test", weight=50)
        VariantConfig(key="test", name="Test", weight=100)

        # Invalid: negative
        with pytest.raises(ValidationError):
            VariantConfig(key="test", name="Test", weight=-1)

        # Invalid: too high
        with pytest.raises(ValidationError):
            VariantConfig(key="test", name="Test", weight=101)


# ==========================================
# Constants Tests
# ==========================================

class TestExperimentsConstants:
    """Tests for experiments constants."""

    def test_valid_experiment_statuses(self):
        """Valid experiment statuses are defined."""
        from api.admin.experiments import VALID_EXPERIMENT_STATUSES

        assert "draft" in VALID_EXPERIMENT_STATUSES
        assert "running" in VALID_EXPERIMENT_STATUSES
        assert "paused" in VALID_EXPERIMENT_STATUSES
        assert "completed" in VALID_EXPERIMENT_STATUSES
        assert "invalid" not in VALID_EXPERIMENT_STATUSES

    def test_valid_experiment_types(self):
        """Valid experiment types are defined."""
        from api.admin.experiments import VALID_EXPERIMENT_TYPES

        assert "ab" in VALID_EXPERIMENT_TYPES
        assert "multivariate" in VALID_EXPERIMENT_TYPES
        assert "feature_flag" in VALID_EXPERIMENT_TYPES
        assert "invalid" not in VALID_EXPERIMENT_TYPES

    def test_date_pattern(self):
        """Date pattern validates correctly."""
        from api.admin.experiments import DATE_PATTERN

        # Valid dates
        assert DATE_PATTERN.match("2026-01-09")
        assert DATE_PATTERN.match("2026-01-09T12:00:00")

        # Invalid dates
        assert not DATE_PATTERN.match("01-09-2026")
        assert not DATE_PATTERN.match("invalid")


# ==========================================
# Validation Function Tests
# ==========================================

class TestExperimentsValidation:
    """Tests for experiments validation functions."""

    def test_validate_date_format_valid(self):
        """Valid date formats pass validation."""
        from api.admin.experiments import validate_date_format

        # These should not raise
        validate_date_format("2026-01-09", "test_date")
        validate_date_format("2026-01-09T12:00:00", "test_date")
        validate_date_format(None, "test_date")

    def test_validate_date_format_invalid(self):
        """Invalid date formats raise HTTPException."""
        from api.admin.experiments import validate_date_format
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            validate_date_format("01-09-2026", "test_date")
        assert exc_info.value.status_code == 400


# ==========================================
# Integration-style Tests
# ==========================================

class TestExperimentsFieldValidation:
    """Integration tests for field validation at API level."""

    @pytest.mark.parametrize("status", ["draft", "running", "paused", "completed"])
    def test_valid_status_values(self, status):
        """Valid status values are accepted."""
        from api.admin.experiments import StatusUpdateRequest

        req = StatusUpdateRequest(status=status)
        assert req.status == status

    @pytest.mark.parametrize("exp_type", ["ab", "multivariate", "feature_flag"])
    def test_valid_experiment_types(self, exp_type):
        """Valid experiment types are accepted."""
        from api.admin.experiments import ExperimentCreateRequest, VariantConfig

        variants = [
            VariantConfig(key="control", name="Control", weight=50),
            VariantConfig(key="variant", name="Variant", weight=50)
        ]

        req = ExperimentCreateRequest(
            experiment_key="test",
            name="Test",
            experiment_type=exp_type,
            variants=variants
        )
        assert req.experiment_type == exp_type

    @pytest.mark.parametrize("weight", [0, 25, 50, 75, 100])
    def test_valid_weight_values(self, weight):
        """Valid weight values are accepted."""
        from api.admin.experiments import VariantConfig

        config = VariantConfig(key="test", name="Test", weight=weight)
        assert config.weight == weight

