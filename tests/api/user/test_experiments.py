"""
Tests for Experiments API (v2)

Endpoints tested:
- POST /api/v2/user/experiments/{key}/assign
- POST /api/v2/user/experiments/{key}/exposure
- POST /api/v2/user/experiments/{key}/conversion
- GET /api/v2/user/experiments/user/{identifier}

@module tests.api.user.test_experiments
@version 2.1.0

Changes in v2.1.0:
- Updated request models to match Service layer signatures
- assign: user_properties instead of identifier_type/context
- conversion: metric_key instead of variant_key/conversion_type
- exposure: added context parameter
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# Module-level rate limiter bypass BEFORE app import
_rate_limiter_patcher = patch('infrastructure.rate_limiter.limiter.limit', lambda rate: lambda func: func)
_rate_limiter_patcher.start()

from fastapi.testclient import TestClient
from app import app
from dependencies import get_current_user

client = TestClient(app)


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def mock_free_user():
    """Mock free tier user."""
    return {
        "id": "user_123",
        "email": "user@example.com",
        "tier": "free",
    }


@pytest.fixture
def override_get_current_user(mock_free_user):
    """Override get_current_user dependency."""
    async def _get_current_user():
        return mock_free_user

    app.dependency_overrides[get_current_user] = _get_current_user
    yield
    app.dependency_overrides.clear()


# ==========================================
# Test Cases: POST /experiments/{key}/assign
# ==========================================

class TestAssignVariant:
    """Test POST /experiments/{key}/assign endpoint."""

    @patch('domains.platform.experiments.assign_variant')
    def test_assign_variant_success(self, mock_assign):
        """Should assign variant successfully."""
        mock_assign.return_value = "variant_a"

        response = client.post(
            "/api/v2/user/experiments/test_experiment/assign",
            json={
                "user_identifier": "user_123",
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["assigned"] is True
        assert data["variant"] == "variant_a"
        assert data["experiment_key"] == "test_experiment"

        mock_assign.assert_called_once_with(
            experiment_key="test_experiment",
            user_identifier="user_123",
            user_properties=None,
        )

    @patch('domains.platform.experiments.assign_variant')
    def test_assign_variant_not_eligible(self, mock_assign):
        """Should return not assigned when not eligible."""
        mock_assign.return_value = None

        response = client.post(
            "/api/v2/user/experiments/test_experiment/assign",
            json={
                "user_identifier": "user_123",
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["assigned"] is False
        assert data["variant"] is None
        assert "Not eligible" in data["reason"]

    @patch('domains.platform.experiments.assign_variant')
    def test_assign_variant_with_user_properties(self, mock_assign):
        """Should pass user_properties to assignment for targeting."""
        mock_assign.return_value = "variant_b"

        response = client.post(
            "/api/v2/user/experiments/test_experiment/assign",
            json={
                "user_identifier": "user_123",
                "user_properties": {"tier": "pro", "country": "US"}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["assigned"] is True
        assert data["variant"] == "variant_b"

        mock_assign.assert_called_once()
        call_kwargs = mock_assign.call_args.kwargs
        assert call_kwargs["user_properties"] == {"tier": "pro", "country": "US"}

    def test_assign_variant_invalid_payload(self):
        """Should return 422 for invalid payload."""
        response = client.post(
            "/api/v2/user/experiments/test_experiment/assign",
            json={}  # Missing required fields
        )

        assert response.status_code == 422


# ==========================================
# Test Cases: POST /experiments/{key}/exposure
# ==========================================

class TestTrackExposure:
    """Test POST /experiments/{key}/exposure endpoint."""

    @patch('domains.platform.experiments.track_exposure')
    def test_track_exposure_success(self, mock_track):
        """Should track exposure successfully."""
        mock_track.return_value = True

        response = client.post(
            "/api/v2/user/experiments/test_experiment/exposure",
            json={
                "user_identifier": "user_123",
                "variant_key": "variant_a",
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        mock_track.assert_called_once_with(
            experiment_key="test_experiment",
            user_identifier="user_123",
            variant_key="variant_a",
            context=None,
        )

    @patch('domains.platform.experiments.track_exposure')
    def test_track_exposure_with_context(self, mock_track):
        """Should pass context to exposure tracking."""
        mock_track.return_value = True

        response = client.post(
            "/api/v2/user/experiments/test_experiment/exposure",
            json={
                "user_identifier": "user_123",
                "variant_key": "variant_a",
                "context": {"page": "home", "device": "mobile"}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        call_kwargs = mock_track.call_args.kwargs
        assert call_kwargs["context"] == {"page": "home", "device": "mobile"}

    @patch('domains.platform.experiments.track_exposure')
    def test_track_exposure_failure(self, mock_track):
        """Should return false when tracking fails."""
        mock_track.return_value = False

        response = client.post(
            "/api/v2/user/experiments/test_experiment/exposure",
            json={
                "user_identifier": "user_123",
                "variant_key": "variant_a",
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False


# ==========================================
# Test Cases: POST /experiments/{key}/conversion
# ==========================================

class TestTrackConversion:
    """Test POST /experiments/{key}/conversion endpoint."""

    @patch('domains.platform.experiments.track_conversion')
    def test_track_conversion_success(self, mock_track):
        """Should track conversion successfully."""
        mock_track.return_value = True

        response = client.post(
            "/api/v2/user/experiments/test_experiment/conversion",
            json={
                "user_identifier": "user_123",
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        mock_track.assert_called_once_with(
            experiment_key="test_experiment",
            user_identifier="user_123",
            metric_key="primary",  # Default value
            value=1.0,             # Default value
            metadata=None,
        )

    @patch('domains.platform.experiments.track_conversion')
    def test_track_conversion_with_metric_and_value(self, mock_track):
        """Should track conversion with custom metric and value."""
        mock_track.return_value = True

        response = client.post(
            "/api/v2/user/experiments/test_experiment/conversion",
            json={
                "user_identifier": "user_123",
                "metric_key": "revenue",
                "value": 29.99,
                "metadata": {"order_id": "ord_123"}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        call_kwargs = mock_track.call_args.kwargs
        assert call_kwargs["metric_key"] == "revenue"
        assert call_kwargs["value"] == 29.99
        assert call_kwargs["metadata"]["order_id"] == "ord_123"

    @patch('domains.platform.experiments.track_conversion')
    def test_track_conversion_failure(self, mock_track):
        """Should return false when user has no assignment."""
        mock_track.return_value = False

        response = client.post(
            "/api/v2/user/experiments/test_experiment/conversion",
            json={
                "user_identifier": "user_without_assignment",
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False


# ==========================================
# Test Cases: GET /experiments/user/{identifier}
# ==========================================

class TestGetUserExperiments:
    """Test GET /experiments/user/{identifier} endpoint."""

    @patch('domains.platform.experiments.get_user_experiments')
    def test_get_user_experiments_success(self, mock_get):
        """Should get user experiments."""
        mock_get.return_value = [
            {"experiment_key": "exp1", "variant_key": "variant_a", "created_at": "2026-01-08T00:00:00Z"},
            {"experiment_key": "exp2", "variant_key": "control", "created_at": "2026-01-07T00:00:00Z"},
        ]

        response = client.get("/api/v2/user/experiments/user/user_123")

        assert response.status_code == 200
        data = response.json()
        assert len(data["experiments"]) == 2
        assert data["experiments"][0]["experiment_key"] == "exp1"
        assert data["experiments"][1]["variant_key"] == "control"

        mock_get.assert_called_once_with("user_123")

    @patch('domains.platform.experiments.get_user_experiments')
    def test_get_user_experiments_empty(self, mock_get):
        """Should return empty list for user with no experiments."""
        mock_get.return_value = []

        response = client.get("/api/v2/user/experiments/user/user_123")

        assert response.status_code == 200
        data = response.json()
        assert data["experiments"] == []


# ==========================================
# Summary
# ==========================================
# Total tests: 12
# Coverage:
# - POST /experiments/{key}/assign: 4 tests
# - POST /experiments/{key}/exposure: 3 tests
# - POST /experiments/{key}/conversion: 3 tests
# - GET /experiments/user/{identifier}: 2 tests
# ==========================================
