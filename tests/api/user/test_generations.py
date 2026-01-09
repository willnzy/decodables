"""
Tests for Generations API (v3)

Endpoints tested:
- GET /api/v2/user/generations/history
- PATCH /api/v2/user/generations/{id}
- POST /api/v2/user/generations/{id}/favorite (deprecated)
- DELETE /api/v2/user/generations/{id}
- POST /api/v2/user/generations/batch-delete
- DELETE /api/v2/user/generations/batch (deprecated)

@module tests.api.user.test_generations
@version 3.0.0

Changes in v3.0.0:
- DDD architecture upgrade with GenerationHistoryService
- Updated tests to use app.dependency_overrides (FastAPI best practice)
- Removed @patch decorators in favor of service mocking
- All tests now mock GenerationHistoryService instead of Supabase

Changes in v2.1.0:
- Added tests for UUID validation (GEN-P0-1)
- Added tests for delete 404 response (GEN-MEDIUM-1)
- Updated test constants to use valid UUID format
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

# Module-level rate limiter bypass BEFORE app import
_rate_limiter_patcher = patch('infrastructure.rate_limiter.limiter.limit', lambda rate: lambda func: func)
_rate_limiter_patcher.start()

from fastapi.testclient import TestClient
from app import app
from dependencies import get_current_user
from api.user.generations import get_generation_history_service
from domains.generation import GenerationHistoryService
from domains.generation.history_service import GenerationNotFoundException

client = TestClient(app)


# ==========================================
# Test Constants
# ==========================================

# v2.1.0: Valid UUID format for generation_id
VALID_GENERATION_ID = "12345678-1234-1234-1234-123456789abc"
INVALID_GENERATION_ID = "not-a-valid-uuid"


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
# Test Cases
# ==========================================

class TestGetGenerationHistory:
    """Test GET /generations/history endpoint."""

    def test_get_history_success(self, override_get_current_user):
        """
        v3.0.0: Should get generation history via GenerationHistoryService.

        Given: Valid authenticated user
        When: GET /generations/history
        Then: Returns 200 with paginated history
        """
        # Arrange: Mock GenerationHistoryService
        mock_service = MagicMock(spec=GenerationHistoryService)
        mock_service.get_history = AsyncMock(return_value=(
            [
                {"id": "gen1", "prompt": "test prompt", "is_favorited": False},
                {"id": "gen2", "prompt": "another prompt", "is_favorited": True},
            ],
            2
        ))

        app.dependency_overrides[get_generation_history_service] = lambda: mock_service

        # Act
        response = client.get("/api/v2/user/generations/history")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["generations"]) == 2
        assert data["total"] == 2
        assert data["limit"] == 20
        assert data["offset"] == 0

        # Verify service was called correctly
        mock_service.get_history.assert_called_once_with(
            "user_123", 20, 0, False
        )

        app.dependency_overrides.clear()

    def test_get_history_with_pagination(self, override_get_current_user):
        """
        v3.0.0: Should support pagination via Service.

        Given: Pagination parameters
        When: GET /generations/history?limit=10&offset=20
        Then: Returns paginated results
        """
        # Arrange: Mock empty result
        mock_service = MagicMock(spec=GenerationHistoryService)
        mock_service.get_history = AsyncMock(return_value=([], 0))

        app.dependency_overrides[get_generation_history_service] = lambda: mock_service

        # Act
        response = client.get("/api/v2/user/generations/history?limit=10&offset=20")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 20

        # Verify service was called with correct params
        mock_service.get_history.assert_called_once_with(
            "user_123", 10, 20, False
        )

        app.dependency_overrides.clear()

    def test_get_history_favorites_only(self, override_get_current_user):
        """
        v3.0.0: Should filter by favorites via Service.

        Given: favorites_only=true parameter
        When: GET /generations/history?favorites_only=true
        Then: Service is called with favorites_only=True
        """
        # Arrange: Mock favorited results
        mock_service = MagicMock(spec=GenerationHistoryService)
        mock_service.get_history = AsyncMock(return_value=(
            [{"id": "gen1", "is_favorited": True}],
            1
        ))

        app.dependency_overrides[get_generation_history_service] = lambda: mock_service

        # Act
        response = client.get("/api/v2/user/generations/history?favorites_only=true")

        # Assert
        assert response.status_code == 200

        # Verify service was called with favorites_only=True
        mock_service.get_history.assert_called_once_with(
            "user_123", 20, 0, True
        )

        app.dependency_overrides.clear()

    def test_get_history_requires_auth(self):
        """Should require authentication."""
        response = client.get("/api/v2/user/generations/history")

        assert response.status_code == 401


class TestUpdateGeneration:
    """Test PATCH /generations/{id} endpoint."""

    def test_update_generation_success(self, override_get_current_user):
        """
        v3.0.0: Should update generation via GenerationHistoryService.

        Given: Valid generation_id and update data
        When: PATCH /generations/{id}
        Then: Returns 200 with updated status
        """
        # Arrange: Mock successful update
        mock_service = MagicMock(spec=GenerationHistoryService)
        mock_service.update_generation = AsyncMock(return_value={
            "id": VALID_GENERATION_ID,
            "is_favorited": True
        })

        app.dependency_overrides[get_generation_history_service] = lambda: mock_service

        # Act
        response = client.patch(
            f"/api/v2/user/generations/{VALID_GENERATION_ID}",
            json={"is_favorited": True}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["is_favorited"] is True

        # Verify service was called correctly
        mock_service.update_generation.assert_called_once_with(
            "user_123",
            VALID_GENERATION_ID,
            {"is_favorited": True}
        )

        app.dependency_overrides.clear()

    def test_update_generation_not_found(self, override_get_current_user):
        """
        v3.0.0: Should return 404 when Service raises GenerationNotFoundException.

        Given: Non-existent generation_id
        When: PATCH /generations/{id}
        Then: Returns 404 Not Found
        """
        # Arrange: Mock service to raise GenerationNotFoundException
        mock_service = MagicMock(spec=GenerationHistoryService)
        mock_service.update_generation = AsyncMock(side_effect=GenerationNotFoundException("Not found"))

        app.dependency_overrides[get_generation_history_service] = lambda: mock_service

        # Act
        response = client.patch(
            f"/api/v2/user/generations/{VALID_GENERATION_ID}",
            json={"is_favorited": True}
        )

        # Assert
        assert response.status_code == 404

        app.dependency_overrides.clear()

    def test_update_generation_invalid_id(self, override_get_current_user):
        """
        v2.1.0/v3.0.0: GEN-P0-1 - Should reject invalid generation_id format.

        Given: Invalid generation_id (not UUID format)
        When: PATCH /generations/{invalid_id}
        Then: Returns 400 Bad Request
        """
        response = client.patch(
            f"/api/v2/user/generations/{INVALID_GENERATION_ID}",
            json={"is_favorited": True}
        )

        assert response.status_code == 400


class TestToggleFavoriteDeprecated:
    """Test POST /generations/{id}/favorite endpoint (deprecated)."""

    def test_toggle_favorite_deprecated(self, override_get_current_user):
        """
        v3.0.0: Should still work but is deprecated (calls same Service method).

        Given: Valid generation_id
        When: POST /generations/{id}/favorite
        Then: Returns 200 (but endpoint is deprecated)
        """
        # Arrange: Mock successful update
        mock_service = MagicMock(spec=GenerationHistoryService)
        mock_service.update_generation = AsyncMock(return_value={
            "id": VALID_GENERATION_ID,
            "is_favorited": True
        })

        app.dependency_overrides[get_generation_history_service] = lambda: mock_service

        # Act
        response = client.post(
            f"/api/v2/user/generations/{VALID_GENERATION_ID}/favorite",
            json={"is_favorited": True}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify service was called (same as PATCH)
        mock_service.update_generation.assert_called_once_with(
            "user_123",
            VALID_GENERATION_ID,
            {"is_favorited": True}
        )

        app.dependency_overrides.clear()

    def test_toggle_favorite_invalid_id(self, override_get_current_user):
        """
        v2.1.0/v3.0.0: GEN-P0-1 - Should reject invalid generation_id format.
        """
        response = client.post(
            f"/api/v2/user/generations/{INVALID_GENERATION_ID}/favorite",
            json={"is_favorited": True}
        )

        assert response.status_code == 400


class TestDeleteGeneration:
    """Test DELETE /generations/{id} endpoint."""

    def test_delete_generation_success(self, override_get_current_user):
        """
        v3.0.0: Should delete generation via GenerationHistoryService.

        Given: Valid generation_id
        When: DELETE /generations/{id}
        Then: Returns 200 with deleted ID
        """
        # Arrange: Mock successful delete
        mock_service = MagicMock(spec=GenerationHistoryService)
        mock_service.delete_generation = AsyncMock(return_value=VALID_GENERATION_ID)

        app.dependency_overrides[get_generation_history_service] = lambda: mock_service

        # Act
        response = client.delete(f"/api/v2/user/generations/{VALID_GENERATION_ID}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["deleted"] == VALID_GENERATION_ID

        # Verify service was called correctly
        mock_service.delete_generation.assert_called_once_with(
            "user_123",
            VALID_GENERATION_ID
        )

        app.dependency_overrides.clear()

    def test_delete_generation_invalid_id(self, override_get_current_user):
        """
        v2.1.0/v3.0.0: GEN-P0-1 - Should reject invalid generation_id format.
        """
        response = client.delete(f"/api/v2/user/generations/{INVALID_GENERATION_ID}")

        assert response.status_code == 400

    def test_delete_generation_not_found(self, override_get_current_user):
        """
        v2.1.0/v3.0.0: GEN-MEDIUM-1 - Should return 404 when Service raises GenerationNotFoundException.

        Given: Non-existent generation_id
        When: DELETE /generations/{id}
        Then: Returns 404 Not Found
        """
        # Arrange: Mock service to raise GenerationNotFoundException
        mock_service = MagicMock(spec=GenerationHistoryService)
        mock_service.delete_generation = AsyncMock(side_effect=GenerationNotFoundException("Not found"))

        app.dependency_overrides[get_generation_history_service] = lambda: mock_service

        # Act
        response = client.delete(f"/api/v2/user/generations/{VALID_GENERATION_ID}")

        # Assert
        assert response.status_code == 404

        app.dependency_overrides.clear()


class TestBatchDelete:
    """Test POST /generations/batch-delete endpoint."""

    def test_batch_delete_keep_favorites(self, override_get_current_user):
        """
        v3.0.0: Should delete all except favorites via Service.

        Given: keep_favorites=true parameter
        When: POST /generations/batch-delete
        Then: Returns 200 with deleted count
        """
        # Arrange: Mock successful batch delete
        mock_service = MagicMock(spec=GenerationHistoryService)
        mock_service.batch_delete = AsyncMock(return_value=2)

        app.dependency_overrides[get_generation_history_service] = lambda: mock_service

        # Act
        response = client.post("/api/v2/user/generations/batch-delete?keep_favorites=true")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["deleted_count"] == 2

        # Verify service was called correctly
        mock_service.batch_delete.assert_called_once_with(
            "user_123", True
        )

        app.dependency_overrides.clear()

    def test_batch_delete_all(self, override_get_current_user):
        """
        v3.0.0: Should delete all generations via Service.

        Given: keep_favorites=false parameter
        When: POST /generations/batch-delete
        Then: Returns 200 with total deleted count
        """
        # Arrange: Mock successful batch delete (all)
        mock_service = MagicMock(spec=GenerationHistoryService)
        mock_service.batch_delete = AsyncMock(return_value=3)

        app.dependency_overrides[get_generation_history_service] = lambda: mock_service

        # Act
        response = client.post("/api/v2/user/generations/batch-delete?keep_favorites=false")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["deleted_count"] == 3

        # Verify service was called correctly
        mock_service.batch_delete.assert_called_once_with(
            "user_123", False
        )

        app.dependency_overrides.clear()


class TestBatchDeleteDeprecated:
    """Test DELETE /generations/batch endpoint (deprecated).

    **BUG FIXED**: Route ordering issue fixed!
    DELETE /batch now comes BEFORE DELETE /{generation_id}, so it correctly matches.
    """

    def test_batch_delete_deprecated_now_fixed(self, override_get_current_user):
        """
        v3.0.0: BUG FIXED - DELETE /batch now correctly matches and calls Service.

        Given: Deprecated DELETE /batch endpoint
        When: DELETE /generations/batch?keep_favorites=true
        Then: Returns 200 with BatchDeleteResponse (via Service)
        """
        # Arrange: Mock successful batch delete
        mock_service = MagicMock(spec=GenerationHistoryService)
        mock_service.batch_delete = AsyncMock(return_value=2)

        app.dependency_overrides[get_generation_history_service] = lambda: mock_service

        # Act
        response = client.delete("/api/v2/user/generations/batch?keep_favorites=true")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # FIXED: Now returns correct BatchDeleteResponse with deleted_count
        assert data["deleted_count"] == 2

        # Verify service was called correctly
        mock_service.batch_delete.assert_called_once_with(
            "user_123", True
        )

        app.dependency_overrides.clear()


# ==========================================
# Coverage Summary
# ==========================================

"""
Test Coverage Summary (v3.0.0):

GET /generations/history (4 tests):
- Success case via GenerationHistoryService
- Pagination support
- Favorites filtering
- Requires authentication (401)

PATCH /generations/{id} (3 tests):
- Success case via Service
- Generation not found (404)
- Invalid generation_id format (400)

POST /generations/{id}/favorite (2 tests - deprecated):
- Success case (calls same Service method as PATCH)
- Invalid generation_id format (400)

DELETE /generations/{id} (3 tests):
- Success case via Service
- Invalid generation_id format (400)
- Generation not found (404)

POST /generations/batch-delete (2 tests):
- Delete all except favorites via Service
- Delete all generations via Service

DELETE /generations/batch (1 test - deprecated):
- BUG FIXED: Now correctly matches and calls Service

Total: 15 tests (same as v2.1.0)

Architecture Changes in v3.0.0:
- ✅ DDD compliance: API → GenerationHistoryService → Database
- ✅ Dependency injection via app.dependency_overrides
- ✅ All tests use GenerationHistoryService mocking (no @patch on Supabase)
- ✅ Custom exception handling (GenerationNotFoundException)
- ✅ All security features maintained (UUID validation, audit logging)

Security Improvements in v2.1.0 (maintained):
- GEN-P0-1: UUID validation for generation_id
- GEN-MEDIUM-1: Delete returns 404 if not found
- GEN-MEDIUM-2: Audit logging in Service layer
"""
