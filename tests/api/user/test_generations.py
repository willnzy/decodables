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
@version 2.0.0
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
        mock_result.data = [{"id": "gen1", "is_favorited": True}]

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
            "/api/v2/user/generations/gen1",
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
            "/api/v2/user/generations/gen_nonexistent",
            json={"is_favorited": True}
        )

        assert response.status_code == 404


class TestToggleFavoriteDeprecated:
    """Test POST /generations/{id}/favorite endpoint (deprecated)."""

    @patch('api.user.generations.supabase')
    def test_toggle_favorite_deprecated(self, mock_supabase, override_get_current_user):
        """Should still work but is deprecated."""
        mock_result = MagicMock()
        mock_result.data = [{"id": "gen1", "is_favorited": True}]

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
            "/api/v2/user/generations/gen1/favorite",
            json={"is_favorited": True}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestDeleteGeneration:
    """Test DELETE /generations/{id} endpoint."""

    @patch('api.user.generations.supabase')
    def test_delete_generation_success(self, mock_supabase, override_get_current_user):
        """Should delete generation."""
        mock_result = MagicMock()

        mock_table = MagicMock()
        mock_delete = MagicMock()
        mock_eq1 = MagicMock()
        mock_eq2 = MagicMock()

        mock_supabase.table.return_value = mock_table
        mock_table.delete.return_value = mock_delete
        mock_delete.eq.return_value = mock_eq1
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value = mock_result

        response = client.delete("/api/v2/user/generations/gen1")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["deleted"] == "gen1"


class TestBatchDelete:
    """Test POST /generations/batch-delete endpoint."""

    @patch('api.user.generations.supabase')
    def test_batch_delete_keep_favorites(self, mock_supabase, override_get_current_user):
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

    @patch('api.user.generations.supabase')
    def test_batch_delete_all(self, mock_supabase, override_get_current_user):
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

    **KNOWN API BUG #6**: Route ordering issue!
    DELETE /batch comes AFTER DELETE /{generation_id}, so FastAPI matches "batch" as generation_id.
    This endpoint is currently broken and returns DeleteResponse instead of BatchDeleteResponse.
    """

    @patch('api.user.generations.supabase')
    def test_batch_delete_deprecated_broken(self, mock_supabase, override_get_current_user):
        """KNOWN BUG: DELETE /batch is being matched as DELETE /{generation_id}."""
        mock_result = MagicMock()

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
        # BUG: Returns DeleteResponse (deleted="batch") instead of BatchDeleteResponse
        assert data["deleted"] == "batch"  # Wrong response model!
