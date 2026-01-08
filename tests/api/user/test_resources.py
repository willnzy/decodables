"""
Tests for Resources API (v2)

Endpoints tested:
- GET /api/v2/user/resources
- GET /api/v2/user/resources/types
- GET /api/v2/user/resources/categories/{type}
- GET /api/v2/user/resources/stickers
- GET /api/v2/user/resources/backgrounds
- GET /api/v2/user/resources/templates
- GET /api/v2/user/resources/{id}

@module tests.api.user.test_resources
@version 2.0.0
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# Module-level rate limiter bypass BEFORE app import
_rate_limiter_patcher = patch('infrastructure.rate_limiter.limiter.limit', lambda rate: lambda func: func)
_rate_limiter_patcher.start()

from fastapi.testclient import TestClient
from app import app
from dependencies import optional_user

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
def override_optional_user(mock_free_user):
    """Override optional_user dependency."""
    async def _optional_user():
        return mock_free_user

    app.dependency_overrides[optional_user] = _optional_user
    yield
    app.dependency_overrides.clear()


#==========================================
# Test Cases
# ==========================================

class TestListResources:
    """Test GET /resources endpoint."""

    @patch('api.user.resources.GetResourcesHandler')
    @patch('api.user.resources.get_content_service')
    def test_list_resources_success(self, mock_service, mock_handler_class, override_optional_user):
        """Should list resources."""
        mock_result = MagicMock()
        mock_result.items = [
            {"id": "res_1", "type": "sticker", "url": "https://example.com/sticker1.png", "is_locked": False},
            {"id": "res_2", "type": "background", "url": "https://example.com/bg1.png", "is_locked": True},
        ]
        mock_result.total = 2
        mock_result.page = 1

        mock_handler = MagicMock()
        mock_handler.handle = AsyncMock(return_value=mock_result)
        mock_handler_class.return_value = mock_handler

        response = client.get("/api/v2/user/resources")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 2
        assert data["page"] == 1

    @patch('api.user.resources.GetResourcesHandler')
    @patch('api.user.resources.get_content_service')
    def test_list_resources_with_filters(self, mock_service, mock_handler_class, override_optional_user):
        """Should filter resources by type and category."""
        mock_result = MagicMock()
        mock_result.items = [{"id": "res_1", "type": "sticker", "category": "animals"}]
        mock_result.total = 1
        mock_result.page = 1

        mock_handler = MagicMock()
        mock_handler.handle = AsyncMock(return_value=mock_result)
        mock_handler_class.return_value = mock_handler

        response = client.get("/api/v2/user/resources?type=sticker&category=animals")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1


class TestGetResourceTypes:
    """Test GET /resources/types endpoint."""

    def test_get_resource_types(self):
        """Should return all resource types."""
        response = client.get("/api/v2/user/resources/types")

        assert response.status_code == 200
        data = response.json()
        assert "types" in data
        assert isinstance(data["types"], list)
        assert len(data["types"]) > 0


class TestGetCategories:
    """Test GET /resources/categories/{type} endpoint."""

    @patch('api.user.resources.GetCategoriesHandler')
    @patch('api.user.resources.get_content_service')
    def test_get_categories(self, mock_service, mock_handler_class):
        """Should get categories for resource type."""
        mock_result = MagicMock()
        mock_result.categories = [
            {"id": "cat_1", "name": "Animals"},
            {"id": "cat_2", "name": "Nature"},
        ]

        mock_handler = MagicMock()
        mock_handler.handle = AsyncMock(return_value=mock_result)
        mock_handler_class.return_value = mock_handler

        response = client.get("/api/v2/user/resources/categories/sticker")

        assert response.status_code == 200
        data = response.json()
        assert len(data["categories"]) == 2


class TestGetStickers:
    """Test GET /resources/stickers endpoint."""

    @patch('api.user.resources.GetStickersHandler')
    @patch('api.user.resources.get_content_service')
    def test_get_stickers(self, mock_service, mock_handler_class, override_optional_user):
        """Should get stickers."""
        mock_result = {"items": [{"id": "sticker_1", "type": "sticker"}], "total": 1}

        mock_handler = MagicMock()
        mock_handler.handle = AsyncMock(return_value=mock_result)
        mock_handler_class.return_value = mock_handler

        response = client.get("/api/v2/user/resources/stickers")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1


class TestGetBackgrounds:
    """Test GET /resources/backgrounds endpoint."""

    @patch('api.user.resources.GetBackgroundsHandler')
    @patch('api.user.resources.get_content_service')
    def test_get_backgrounds(self, mock_service, mock_handler_class, override_optional_user):
        """Should get backgrounds."""
        mock_result = {"items": [{"id": "bg_1", "type": "background"}], "total": 1}

        mock_handler = MagicMock()
        mock_handler.handle = AsyncMock(return_value=mock_result)
        mock_handler_class.return_value = mock_handler

        response = client.get("/api/v2/user/resources/backgrounds")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1


class TestGetTemplates:
    """Test GET /resources/templates endpoint."""

    @patch('api.user.resources.GetProjectTemplatesHandler')
    @patch('api.user.resources.get_content_service')
    def test_get_templates(self, mock_service, mock_handler_class, override_optional_user):
        """Should get project templates."""
        mock_result = {"items": [{"id": "tpl_1", "type": "template"}], "total": 1}

        mock_handler = MagicMock()
        mock_handler.handle = AsyncMock(return_value=mock_result)
        mock_handler_class.return_value = mock_handler

        response = client.get("/api/v2/user/resources/templates")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1


class TestGetResourceById:
    """Test GET /resources/{id} endpoint."""

    @patch('api.user.resources.GetResourceByIdHandler')
    @patch('api.user.resources.get_content_service')
    def test_get_resource_by_id(self, mock_service, mock_handler_class, override_optional_user):
        """Should get resource by ID."""
        mock_result = MagicMock()
        mock_result.resource = {"id": "res_1", "type": "sticker", "url": "https://example.com/sticker.png"}

        mock_handler = MagicMock()
        mock_handler.handle = AsyncMock(return_value=mock_result)
        mock_handler_class.return_value = mock_handler

        response = client.get("/api/v2/user/resources/res_1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "res_1"

    @patch('api.user.resources.GetResourceByIdHandler')
    @patch('api.user.resources.get_content_service')
    def test_get_resource_not_found(self, mock_service, mock_handler_class, override_optional_user):
        """Should return 404 for non-existent resource."""
        mock_result = MagicMock()
        mock_result.resource = None

        mock_handler = MagicMock()
        mock_handler.handle = AsyncMock(return_value=mock_result)
        mock_handler_class.return_value = mock_handler

        response = client.get("/api/v2/user/resources/res_nonexistent")

        assert response.status_code == 404
