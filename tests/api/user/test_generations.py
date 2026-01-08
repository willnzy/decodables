"""
Tests for Generations API (v2)

Endpoints tested:
- GET /api/v2/user/generations/history
- PATCH /api/v2/user/generations/{id}
- POST /api/v2/user/generations/{id}/favorite (deprecated)
- DELETE /api/v2/user/generations/{id}
- POST /api/v2/user/generations/batch-delete
- DELETE /api/v2/user/generations/batch (deprecated)

@module tests.api.user.test_generations
@version 2.1.0

Changes in v2.1.0:
- Added tests for UUID validation (GEN-P0-1)
- Added tests for delete 404 response (GEN-MEDIUM-1)
- Updated test constants to use valid UUID format
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# Module-level rate limiter bypass BEFORE app import
_rate_limiter_patcher = patch('infrastructure.rate_limiter.limiter.limit', lambda rate: lambda func: func)
_rate_limiter_patcher.start()

# Mock supabase at module level to prevent connection attempts
_supabase_patcher = patch('api.user.generations.supabase', MagicMock())
_supabase_patcher.start()

from fastapi.testclient import TestClient
from app import app
from dependencies import get_current_user

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

    @patch('api.user.generations.supabase')
    def test_get_history_success(self, mock_supabase, override_get_current_user):
        """Should get generation history."""
        # Mock query chain
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "gen1", "prompt": "test prompt", "is_favorited": False},
            {"id": "gen2", "prompt": "another prompt", "is_favorited": True},
        ]

        mock_count_result = MagicMock()
        mock_count_result.count = 2

        # Chain mocking
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_eq = MagicMock()
        mock_order = MagicMock()
        mock_range = MagicMock()

        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq
        mock_eq.order.return_value = mock_order
        mock_order.range.return_value = mock_range
        mock_range.execute.return_value = mock_result

        # Mock count query
        mock_select.eq.return_value.execute.return_value = mock_count_result

        response = client.get("/api/v2/user/generations/history")

        assert response.status_code == 200
        data = response.json()
        assert len(data["generations"]) == 2
        assert data["total"] == 2
        assert data["limit"] == 20
        assert data["offset"] == 0

    @patch('api.user.generations.supabase')
    def test_get_history_with_pagination(self, mock_supabase, override_get_current_user):
        """Should support pagination."""
        mock_result = MagicMock()
        mock_result.data = []
        mock_count_result = MagicMock()
        mock_count_result.count = 0

        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_eq = MagicMock()
        mock_order = MagicMock()
        mock_range = MagicMock()

        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq
        mock_eq.order.return_value = mock_order
        mock_order.range.return_value = mock_range
        mock_range.execute.return_value = mock_result
        mock_select.eq.return_value.execute.return_value = mock_count_result

        response = client.get("/api/v2/user/generations/history?limit=10&offset=20")

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 20

    @patch('api.user.generations.supabase')
    def test_get_history_favorites_only(self, mock_supabase, override_get_current_user):
        """Should filter by favorites."""
        mock_result = MagicMock()
        mock_result.data = [{"id": "gen1", "is_favorited": True}]
        mock_count_result = MagicMock()
        mock_count_result.count = 1

        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_eq = MagicMock()
        mock_order = MagicMock()
        mock_range = MagicMock()

        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq
        mock_eq.order.return_value = mock_order
        mock_eq.eq.return_value = mock_order  # Second eq for favorites_only
        mock_order.range.return_value = mock_range
        mock_range.execute.return_value = mock_result
        mock_select.eq.return_value.eq.return_value.execute.return_value = mock_count_result

        response = client.get("/api/v2/user/generations/history?favorites_only=true")

        assert response.status_code == 200

    def test_get_history_requires_auth(self):
        """Should require authentication."""
        response = client.get("/api/v2/user/generations/history")

        assert response.status_code == 401


class TestUpdateGeneration:
    """Test PATCH /generations/{id} endpoint."""

    @patch('api.user.generations.supabase')
    def test_update_generation_success(self, mock_supabase, override_get_current_user):
        """Should update generation favorite status."""
        mock_result = MagicMock()
        mock_result.data = [{"id": VALID_GENERATION_ID, "is_favorited": True}]

        mock_table = MagicMock()
        mock_update = MagicMock()
        mock_eq1 = MagicMock()
        mock_eq2 = MagicMock()

        mock_supabase.table.return_value = mock_table
        mock_table.update.return_value = mock_update
        mock_update.eq.return_value = mock_eq1
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value = mock_result

        response = client.patch(
            f"/api/v2/user/generations/{VALID_GENERATION_ID}",
            json={"is_favorited": True}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["is_favorited"] is True

    @patch('api.user.generations.supabase')
    def test_update_generation_not_found(self, mock_supabase, override_get_current_user):
        """Should return 404 for non-existent generation."""
        mock_result = MagicMock()
        mock_result.data = []

        mock_table = MagicMock()
        mock_update = MagicMock()
        mock_eq1 = MagicMock()
        mock_eq2 = MagicMock()

        mock_supabase.table.return_value = mock_table
        mock_table.update.return_value = mock_update
        mock_update.eq.return_value = mock_eq1
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value = mock_result

        response = client.patch(
            f"/api/v2/user/generations/{VALID_GENERATION_ID}",
            json={"is_favorited": True}
        )

        assert response.status_code == 404

    def test_update_generation_invalid_id(self, override_get_current_user):
        """
        v2.1.0: GEN-P0-1 - Should reject invalid generation_id format.

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

    @patch('api.user.generations.supabase')
    def test_toggle_favorite_deprecated(self, mock_supabase, override_get_current_user):
        """Should still work but is deprecated."""
        mock_result = MagicMock()
        mock_result.data = [{"id": VALID_GENERATION_ID, "is_favorited": True}]

        mock_table = MagicMock()
        mock_update = MagicMock()
        mock_eq1 = MagicMock()
        mock_eq2 = MagicMock()

        mock_supabase.table.return_value = mock_table
        mock_table.update.return_value = mock_update
        mock_update.eq.return_value = mock_eq1
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value = mock_result

        response = client.post(
            f"/api/v2/user/generations/{VALID_GENERATION_ID}/favorite",
            json={"is_favorited": True}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_toggle_favorite_invalid_id(self, override_get_current_user):
        """
        v2.1.0: GEN-P0-1 - Should reject invalid generation_id format.
        """
        response = client.post(
            f"/api/v2/user/generations/{INVALID_GENERATION_ID}/favorite",
            json={"is_favorited": True}
        )

        assert response.status_code == 400


class TestDeleteGeneration:
    """Test DELETE /generations/{id} endpoint."""

    @patch('api.user.generations.log_activity')
    @patch('api.user.generations.supabase')
    def test_delete_generation_success(self, mock_supabase, mock_log, override_get_current_user):
        """Should delete generation."""
        mock_result = MagicMock()
        mock_result.data = [{"id": VALID_GENERATION_ID}]  # v2.1.0: Return data to indicate deletion

        mock_table = MagicMock()
        mock_delete = MagicMock()
        mock_eq1 = MagicMock()
        mock_eq2 = MagicMock()

        mock_supabase.table.return_value = mock_table
        mock_table.delete.return_value = mock_delete
        mock_delete.eq.return_value = mock_eq1
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value = mock_result

        response = client.delete(f"/api/v2/user/generations/{VALID_GENERATION_ID}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["deleted"] == VALID_GENERATION_ID

    def test_delete_generation_invalid_id(self, override_get_current_user):
        """
        v2.1.0: GEN-P0-1 - Should reject invalid generation_id format.
        """
        response = client.delete(f"/api/v2/user/generations/{INVALID_GENERATION_ID}")

        assert response.status_code == 400

    @patch('api.user.generations.supabase')
    def test_delete_generation_not_found(self, mock_supabase, override_get_current_user):
        """
        v2.1.0: GEN-MEDIUM-1 - Should return 404 if generation not found.
        """
        mock_result = MagicMock()
        mock_result.data = []  # No data = not found

        mock_table = MagicMock()
        mock_delete = MagicMock()
        mock_eq1 = MagicMock()
        mock_eq2 = MagicMock()

        mock_supabase.table.return_value = mock_table
        mock_table.delete.return_value = mock_delete
        mock_delete.eq.return_value = mock_eq1
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value = mock_result

        response = client.delete(f"/api/v2/user/generations/{VALID_GENERATION_ID}")

        assert response.status_code == 404


class TestBatchDelete:
    """Test POST /generations/batch-delete endpoint."""

    @patch('api.user.generations.log_activity')
    @patch('api.user.generations.supabase')
    def test_batch_delete_keep_favorites(self, mock_supabase, mock_log, override_get_current_user):
        """Should delete all except favorites."""
        mock_result = MagicMock()
        mock_result.data = [{"id": "gen1"}, {"id": "gen2"}]

        mock_table = MagicMock()
        mock_delete = MagicMock()
        mock_eq1 = MagicMock()
        mock_eq2 = MagicMock()

        mock_supabase.table.return_value = mock_table
        mock_table.delete.return_value = mock_delete
        mock_delete.eq.return_value = mock_eq1
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value = mock_result

        response = client.post("/api/v2/user/generations/batch-delete?keep_favorites=true")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["deleted_count"] == 2

    @patch('api.user.generations.log_activity')
    @patch('api.user.generations.supabase')
    def test_batch_delete_all(self, mock_supabase, mock_log, override_get_current_user):
        """Should delete all generations."""
        mock_result = MagicMock()
        mock_result.data = [{"id": "gen1"}, {"id": "gen2"}, {"id": "gen3"}]

        mock_table = MagicMock()
        mock_delete = MagicMock()
        mock_eq = MagicMock()

        mock_supabase.table.return_value = mock_table
        mock_table.delete.return_value = mock_delete
        mock_delete.eq.return_value = mock_eq
        mock_eq.execute.return_value = mock_result

        response = client.post("/api/v2/user/generations/batch-delete?keep_favorites=false")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["deleted_count"] == 3


class TestBatchDeleteDeprecated:
    """Test DELETE /generations/batch endpoint (deprecated).

    **BUG FIXED**: Route ordering issue fixed!
    DELETE /batch now comes BEFORE DELETE /{generation_id}, so it correctly matches.
    """

    @patch('api.user.generations.log_activity')
    @patch('api.user.generations.supabase')
    def test_batch_delete_deprecated_now_fixed(self, mock_supabase, mock_log, override_get_current_user):
        """BUG FIXED: DELETE /batch now correctly matches and returns BatchDeleteResponse."""
        mock_result = MagicMock()
        mock_result.data = [{"id": "gen_1"}, {"id": "gen_2"}]

        mock_table = MagicMock()
        mock_delete = MagicMock()
        mock_eq1 = MagicMock()
        mock_eq2 = MagicMock()

        mock_supabase.table.return_value = mock_table
        mock_table.delete.return_value = mock_delete
        mock_delete.eq.return_value = mock_eq1
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value = mock_result

        response = client.delete("/api/v2/user/generations/batch?keep_favorites=true")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # FIXED: Now returns correct BatchDeleteResponse with deleted_count
        assert data["deleted_count"] == 2
