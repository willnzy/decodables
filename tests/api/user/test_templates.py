"""
Test api/user/templates.py - Prompt Templates API

Endpoints:
Asset Templates (5W1H):
- GET /api/v2/user/templates/asset - List templates
- POST /api/v2/user/templates/asset - Create template
- PUT /api/v2/user/templates/asset/{id} - Update template
- DELETE /api/v2/user/templates/asset/{id} - Delete template
- POST /api/v2/user/templates/asset/{id}/use - Mark as used

Page Templates (AI Design):
- GET /api/v2/user/templates/page - List templates
- POST /api/v2/user/templates/page - Create template
- PUT /api/v2/user/templates/page/{id} - Update template
- DELETE /api/v2/user/templates/page/{id} - Delete template
- POST /api/v2/user/templates/page/{id}/use - Mark as used

Created: 2026-01-07
Updated: 2026-01-08 (Complete rewrite with 20 comprehensive tests)
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Rate limiter bypass BEFORE app import
_rate_limiter_patcher = patch('infrastructure.rate_limiter.limiter.limit', lambda rate: lambda func: func)
_rate_limiter_patcher.start()

from app import app
from dependencies import get_current_user

client = TestClient(app)


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return {
        "id": "user_123",
        "email": "test@example.com",
        "tier": "pro",
    }


@pytest.fixture
def override_get_current_user(mock_user):
    """Override authentication dependency."""
    async def _get_current_user():
        return mock_user
    app.dependency_overrides[get_current_user] = _get_current_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_asset_template():
    """Mock asset prompt template."""
    return {
        "id": "template_asset_1",
        "user_id": "user_123",
        "name": "My 5W1H Template",
        "description": "Test template",
        "who_type": "character",
        "who_custom": "A friendly teacher",
        "what_type": "action",
        "what_custom": "reading a book",
        "where_type": "location",
        "where_custom": "in a classroom",
        "style": "cartoon",
        "moods": ["warm", "happy"],
        "aspect_ratio": "square",
        "creativity_level": 0.5,
        "negative_prompt": "dark, scary",
        "use_count": 5,
        "last_used_at": "2024-12-01T10:00:00Z",
        "created_at": "2024-11-01T10:00:00Z",
    }


@pytest.fixture
def mock_page_template():
    """Mock page prompt template."""
    return {
        "id": "template_page_1",
        "user_id": "user_123",
        "name": "Story Page Layout",
        "layout": "image_top",
        "story_theme": "adventure",
        "main_character": "brave explorer",
        "style": "cartoon",
        "creativity_level": 0.4,
        "negative_prompt": None,
        "generation_mode": "guided",
        "use_count": 3,
        "last_used_at": "2024-12-05T15:30:00Z",
        "created_at": "2024-10-15T12:00:00Z",
    }


# ==========================================
# Tests - Asset Templates
# ==========================================

class TestAssetTemplates:
    """Test asset prompt template endpoints."""

    @patch('api.user.templates.supabase')
    def test_list_asset_templates_success(self, mock_supabase, override_get_current_user, mock_asset_template):
        """Test listing asset templates."""
        mock_result = MagicMock()
        mock_result.data = [mock_asset_template]
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_result

        response = client.get("/api/v2/user/templates/asset")

        assert response.status_code == 200
        data = response.json()
        assert len(data["templates"]) == 1
        assert data["templates"][0]["id"] == "template_asset_1"
        assert data["templates"][0]["name"] == "My 5W1H Template"

    @patch('api.user.templates.supabase')
    def test_list_asset_templates_empty(self, mock_supabase, override_get_current_user):
        """Test listing when no templates exist."""
        mock_result = MagicMock()
        mock_result.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_result

        response = client.get("/api/v2/user/templates/asset")

        assert response.status_code == 200
        data = response.json()
        assert data["templates"] == []

    @patch('api.user.templates.supabase')
    def test_create_asset_template_success(self, mock_supabase, override_get_current_user, mock_asset_template):
        """Test creating a new asset template."""
        # Mock count check (under limit)
        mock_count_result = MagicMock()
        mock_count_result.count = 5

        # Mock insert result
        mock_insert_result = MagicMock()
        mock_insert_result.data = [mock_asset_template]

        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_count_result
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_insert_result

        payload = {
            "name": "My 5W1H Template",
            "description": "Test template",
            "who_type": "character",
            "who_custom": "A friendly teacher",
            "what_type": "action",
            "what_custom": "reading a book",
            "where_type": "location",
            "where_custom": "in a classroom",
            "style": "cartoon",
            "moods": ["warm", "happy"],
            "aspect_ratio": "square",
            "creativity_level": 0.5,
            "negative_prompt": "dark, scary",
        }

        response = client.post("/api/v2/user/templates/asset", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["template"]["id"] == "template_asset_1"

    @patch('api.user.templates.supabase')
    def test_create_asset_template_limit_exceeded(self, mock_supabase, override_get_current_user):
        """Test creating template when limit is exceeded."""
        # Mock count check (at limit)
        mock_count_result = MagicMock()
        mock_count_result.count = 20  # MAX_TEMPLATES_PER_USER
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_count_result

        payload = {
            "name": "New Template",
            "style": "cartoon",
            "moods": ["warm"],
            "aspect_ratio": "square",
        }

        response = client.post("/api/v2/user/templates/asset", json=payload)

        assert response.status_code == 400
        assert "Maximum 20 templates" in response.json()["message"]

    @patch('api.user.templates.supabase')
    def test_update_asset_template_success(self, mock_supabase, override_get_current_user, mock_asset_template):
        """Test updating an existing asset template."""
        updated_template = mock_asset_template.copy()
        updated_template["name"] = "Updated Template Name"

        mock_result = MagicMock()
        mock_result.data = [updated_template]
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_result

        payload = {"name": "Updated Template Name"}
        response = client.put("/api/v2/user/templates/asset/template_asset_1", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["template"]["name"] == "Updated Template Name"

    @patch('api.user.templates.supabase')
    def test_update_asset_template_not_found(self, mock_supabase, override_get_current_user):
        """Test updating non-existent template."""
        mock_result = MagicMock()
        mock_result.data = []
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_result

        payload = {"name": "Updated Name"}
        response = client.put("/api/v2/user/templates/asset/nonexistent", json=payload)

        assert response.status_code == 404
        assert "Template not found" in response.json()["message"]

    @patch('api.user.templates.supabase')
    def test_update_asset_template_no_fields(self, mock_supabase, override_get_current_user):
        """Test updating with no fields provided."""
        response = client.put("/api/v2/user/templates/asset/template_asset_1", json={})

        assert response.status_code == 400
        assert "No fields to update" in response.json()["message"]

    @patch('api.user.templates.supabase')
    def test_delete_asset_template_success(self, mock_supabase, override_get_current_user):
        """Test deleting an asset template."""
        mock_supabase.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()

        response = client.delete("/api/v2/user/templates/asset/template_asset_1")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @patch('api.user.templates.supabase')
    def test_use_asset_template_success(self, mock_supabase, override_get_current_user):
        """Test marking asset template as used."""
        # Mock get result
        mock_get_result = MagicMock()
        mock_get_result.data = {"use_count": 5}

        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_get_result
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()

        response = client.post("/api/v2/user/templates/asset/template_asset_1/use")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["use_count"] == 6  # 5 + 1

    @patch('api.user.templates.supabase')
    def test_use_asset_template_not_found(self, mock_supabase, override_get_current_user):
        """Test marking non-existent template as used."""
        mock_get_result = MagicMock()
        mock_get_result.data = None
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_get_result

        response = client.post("/api/v2/user/templates/asset/nonexistent/use")

        assert response.status_code == 404
        assert "Template not found" in response.json()["message"]


# ==========================================
# Tests - Page Templates
# ==========================================

class TestPageTemplates:
    """Test page prompt template endpoints."""

    @patch('api.user.templates.supabase')
    def test_list_page_templates_success(self, mock_supabase, override_get_current_user, mock_page_template):
        """Test listing page templates."""
        mock_result = MagicMock()
        mock_result.data = [mock_page_template]
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_result

        response = client.get("/api/v2/user/templates/page")

        assert response.status_code == 200
        data = response.json()
        assert len(data["templates"]) == 1
        assert data["templates"][0]["id"] == "template_page_1"
        assert data["templates"][0]["layout"] == "image_top"

    @patch('api.user.templates.supabase')
    def test_create_page_template_success(self, mock_supabase, override_get_current_user, mock_page_template):
        """Test creating a new page template."""
        mock_count_result = MagicMock()
        mock_count_result.count = 3

        mock_insert_result = MagicMock()
        mock_insert_result.data = [mock_page_template]

        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_count_result
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_insert_result

        payload = {
            "name": "Story Page Layout",
            "layout": "image_top",
            "story_theme": "adventure",
            "main_character": "brave explorer",
            "style": "cartoon",
            "creativity_level": 0.4,
            "generation_mode": "guided",
        }

        response = client.post("/api/v2/user/templates/page", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["template"]["id"] == "template_page_1"

    @patch('api.user.templates.supabase')
    def test_create_page_template_limit_exceeded(self, mock_supabase, override_get_current_user):
        """Test creating page template when limit is exceeded."""
        mock_count_result = MagicMock()
        mock_count_result.count = 20
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_count_result

        payload = {
            "name": "New Page Template",
            "layout": "image_top",
            "style": "cartoon",
        }

        response = client.post("/api/v2/user/templates/page", json=payload)

        assert response.status_code == 400
        assert "Maximum 20 templates" in response.json()["message"]

    @patch('api.user.templates.supabase')
    def test_update_page_template_success(self, mock_supabase, override_get_current_user, mock_page_template):
        """Test updating an existing page template."""
        updated_template = mock_page_template.copy()
        updated_template["layout"] = "image_bottom"

        mock_result = MagicMock()
        mock_result.data = [updated_template]
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_result

        payload = {"layout": "image_bottom"}
        response = client.put("/api/v2/user/templates/page/template_page_1", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["template"]["layout"] == "image_bottom"

    @patch('api.user.templates.supabase')
    def test_update_page_template_not_found(self, mock_supabase, override_get_current_user):
        """Test updating non-existent page template."""
        mock_result = MagicMock()
        mock_result.data = []
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_result

        payload = {"layout": "image_left"}
        response = client.put("/api/v2/user/templates/page/nonexistent", json=payload)

        assert response.status_code == 404
        assert "Template not found" in response.json()["message"]

    @patch('api.user.templates.supabase')
    def test_delete_page_template_success(self, mock_supabase, override_get_current_user):
        """Test deleting a page template."""
        mock_supabase.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()

        response = client.delete("/api/v2/user/templates/page/template_page_1")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @patch('api.user.templates.supabase')
    def test_use_page_template_success(self, mock_supabase, override_get_current_user):
        """Test marking page template as used."""
        mock_get_result = MagicMock()
        mock_get_result.data = {"use_count": 3}

        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_get_result
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()

        response = client.post("/api/v2/user/templates/page/template_page_1/use")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["use_count"] == 4  # 3 + 1

    @patch('api.user.templates.supabase')
    def test_use_page_template_not_found(self, mock_supabase, override_get_current_user):
        """Test marking non-existent page template as used."""
        mock_get_result = MagicMock()
        mock_get_result.data = None
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_get_result

        response = client.post("/api/v2/user/templates/page/nonexistent/use")

        assert response.status_code == 404
        assert "Template not found" in response.json()["message"]


# ==========================================
# Tests - Authentication
# ==========================================

class TestTemplateAuthentication:
    """Test authentication requirements."""

    def test_list_asset_templates_requires_auth(self):
        """Test listing asset templates requires authentication."""
        response = client.get("/api/v2/user/templates/asset")
        assert response.status_code == 401

    def test_list_page_templates_requires_auth(self):
        """Test listing page templates requires authentication."""
        response = client.get("/api/v2/user/templates/page")
        assert response.status_code == 401
