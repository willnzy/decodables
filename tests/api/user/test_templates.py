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
Updated: 2026-01-09
- v2.1.0: Updated tests for UUID template_id validation
- Added security validation tests
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
# Test Constants (v2.1.0)
# ==========================================

# v2.1.0: Use valid UUID format for template_id
VALID_ASSET_TEMPLATE_ID = "12345678-1234-1234-1234-123456789abc"
VALID_PAGE_TEMPLATE_ID = "87654321-4321-4321-4321-cba987654321"
NONEXISTENT_TEMPLATE_ID = "00000000-0000-0000-0000-000000000000"  # Valid UUID but doesn't exist
INVALID_TEMPLATE_ID = "not-a-valid-uuid"


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
        "id": VALID_ASSET_TEMPLATE_ID,  # v2.1.0: Use valid UUID
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
        "id": VALID_PAGE_TEMPLATE_ID,  # v2.1.0: Use valid UUID
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
        assert data["templates"][0]["id"] == VALID_ASSET_TEMPLATE_ID
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
        assert data["template"]["id"] == VALID_ASSET_TEMPLATE_ID

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
        response = client.put(f"/api/v2/user/templates/asset/{VALID_ASSET_TEMPLATE_ID}", json=payload)

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
        response = client.put(f"/api/v2/user/templates/asset/{NONEXISTENT_TEMPLATE_ID}", json=payload)

        assert response.status_code == 404
        assert "Template not found" in response.json()["message"]

    @patch('api.user.templates.supabase')
    def test_update_asset_template_no_fields(self, mock_supabase, override_get_current_user):
        """Test updating with no fields provided."""
        response = client.put(f"/api/v2/user/templates/asset/{VALID_ASSET_TEMPLATE_ID}", json={})

        assert response.status_code == 400
        assert "No fields to update" in response.json()["message"]

    @patch('api.user.templates.supabase')
    def test_delete_asset_template_success(self, mock_supabase, override_get_current_user):
        """Test deleting an asset template."""
        mock_supabase.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()

        response = client.delete(f"/api/v2/user/templates/asset/{VALID_ASSET_TEMPLATE_ID}")

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

        response = client.post(f"/api/v2/user/templates/asset/{VALID_ASSET_TEMPLATE_ID}/use")

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

        response = client.post(f"/api/v2/user/templates/asset/{NONEXISTENT_TEMPLATE_ID}/use")

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
        assert data["templates"][0]["id"] == VALID_PAGE_TEMPLATE_ID
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
        assert data["template"]["id"] == VALID_PAGE_TEMPLATE_ID

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
        response = client.put(f"/api/v2/user/templates/page/{VALID_PAGE_TEMPLATE_ID}", json=payload)

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
        response = client.put(f"/api/v2/user/templates/page/{NONEXISTENT_TEMPLATE_ID}", json=payload)

        assert response.status_code == 404
        assert "Template not found" in response.json()["message"]

    @patch('api.user.templates.supabase')
    def test_delete_page_template_success(self, mock_supabase, override_get_current_user):
        """Test deleting a page template."""
        mock_supabase.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()

        response = client.delete(f"/api/v2/user/templates/page/{VALID_PAGE_TEMPLATE_ID}")

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

        response = client.post(f"/api/v2/user/templates/page/{VALID_PAGE_TEMPLATE_ID}/use")

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

        response = client.post(f"/api/v2/user/templates/page/{NONEXISTENT_TEMPLATE_ID}/use")

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


# ==========================================
# Tests - Security Validations (v2.1.0)
# ==========================================

class TestSecurityValidations:
    """Test security validations added in v2.1.0."""

    def test_update_asset_template_invalid_id(self, override_get_current_user):
        """v2.1.0: TPL-MEDIUM-1 - Reject invalid template_id format."""
        response = client.put(
            f"/api/v2/user/templates/asset/{INVALID_TEMPLATE_ID}",
            json={"name": "Test"}
        )
        assert response.status_code == 400
        assert "Invalid template ID format" in response.text

    def test_delete_asset_template_invalid_id(self, override_get_current_user):
        """v2.1.0: TPL-MEDIUM-1 - Reject invalid template_id format on delete."""
        response = client.delete(f"/api/v2/user/templates/asset/{INVALID_TEMPLATE_ID}")
        assert response.status_code == 400
        assert "Invalid template ID format" in response.text

    def test_use_asset_template_invalid_id(self, override_get_current_user):
        """v2.1.0: TPL-MEDIUM-1 - Reject invalid template_id format on use."""
        response = client.post(f"/api/v2/user/templates/asset/{INVALID_TEMPLATE_ID}/use")
        assert response.status_code == 400
        assert "Invalid template ID format" in response.text

    def test_update_page_template_invalid_id(self, override_get_current_user):
        """v2.1.0: TPL-MEDIUM-1 - Reject invalid template_id format."""
        response = client.put(
            f"/api/v2/user/templates/page/{INVALID_TEMPLATE_ID}",
            json={"layout": "image_top"}
        )
        assert response.status_code == 400
        assert "Invalid template ID format" in response.text

    def test_delete_page_template_invalid_id(self, override_get_current_user):
        """v2.1.0: TPL-MEDIUM-1 - Reject invalid template_id format on delete."""
        response = client.delete(f"/api/v2/user/templates/page/{INVALID_TEMPLATE_ID}")
        assert response.status_code == 400
        assert "Invalid template ID format" in response.text

    def test_use_page_template_invalid_id(self, override_get_current_user):
        """v2.1.0: TPL-MEDIUM-1 - Reject invalid template_id format on use."""
        response = client.post(f"/api/v2/user/templates/page/{INVALID_TEMPLATE_ID}/use")
        assert response.status_code == 400
        assert "Invalid template ID format" in response.text

    def test_create_asset_template_moods_too_many(self, override_get_current_user):
        """v2.1.0: TPL-MEDIUM-3 - Reject too many moods."""
        payload = {
            "name": "Test Template",
            "moods": ["mood" + str(i) for i in range(15)],  # More than MAX_MOODS (10)
        }
        response = client.post("/api/v2/user/templates/asset", json=payload)
        assert response.status_code == 422  # Pydantic validation

    def test_create_asset_template_custom_text_too_long(self, override_get_current_user):
        """v2.1.0: TPL-MEDIUM-2 - Reject too long custom text."""
        payload = {
            "name": "Test Template",
            "who_custom": "x" * 600,  # More than MAX_CUSTOM_TEXT_LENGTH (500)
        }
        response = client.post("/api/v2/user/templates/asset", json=payload)
        assert response.status_code == 422  # Pydantic validation

    def test_create_asset_template_negative_prompt_too_long(self, override_get_current_user):
        """v2.1.0: TPL-LOW-3 - Reject too long negative prompt."""
        payload = {
            "name": "Test Template",
            "negative_prompt": "x" * 1100,  # More than MAX_NEGATIVE_PROMPT_LENGTH (1000)
        }
        response = client.post("/api/v2/user/templates/asset", json=payload)
        assert response.status_code == 422  # Pydantic validation
