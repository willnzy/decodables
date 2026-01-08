"""
Tests for Export API (v2)

Endpoints tested:
- GET /api/v2/user/export/projects/{project_id}/pdf
- GET /api/v2/user/export/projects/{project_id}/preview
- POST /api/v2/user/export/zip (deprecated)
- GET /api/v2/user/export/projects/{project_id}/zip

@module tests.api.user.test_export
@version 2.0.0
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from io import BytesIO

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
def mock_pro_user():
    """Mock pro tier user."""
    return {
        "id": "user_123",
        "email": "user@example.com",
        "tier": "pro",
    }


@pytest.fixture
def override_get_current_user(mock_free_user):
    """Override get_current_user dependency."""
    async def _get_current_user():
        return mock_free_user

    app.dependency_overrides[get_current_user] = _get_current_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def override_pro_user(mock_pro_user):
    """Override get_current_user with pro user."""
    async def _get_current_user():
        return mock_pro_user

    app.dependency_overrides[get_current_user] = _get_current_user
    yield
    app.dependency_overrides.clear()


# ==========================================
# Test Cases
# ==========================================

class TestExportProjectPDF:
    """Test GET /export/projects/{project_id}/pdf endpoint."""

    @patch('api.user.export.log_activity')
    @patch('api.user.export.create_foldable_book')
    @patch('api.user.export.SupabaseProjectRepository')
    def test_export_pdf_success(self, mock_repo_class, mock_create_pdf, mock_log, override_get_current_user):
        """Should export project as PDF."""
        mock_project = {
            "id": "proj_1",
            "title": "My Project",
            "canvas_data": {
                "pages": [
                    {"previewImage": "https://example.com/img1.png", "prompt": "Page 1"},
                    {"previewImage": "https://example.com/img2.png", "prompt": "Page 2"},
                ],
                "paperSize": "Letter",
            }
        }

        mock_repo = MagicMock()
        mock_repo.get_project_detail = AsyncMock(return_value=mock_project)
        mock_repo_class.return_value = mock_repo

        # Mock PDF creation
        mock_create_pdf.side_effect = lambda urls, texts, buf, paper_type: buf.write(b"PDF content")

        response = client.get("/api/v2/user/export/projects/proj_1/pdf")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert b"PDF content" in response.content

    @patch('api.user.export.SupabaseProjectRepository')
    def test_export_pdf_project_not_found(self, mock_repo_class, override_get_current_user):
        """Should return 404 for non-existent project."""
        mock_repo = MagicMock()
        mock_repo.get_project_detail = AsyncMock(return_value=None)
        mock_repo_class.return_value = mock_repo

        response = client.get("/api/v2/user/export/projects/proj_nonexistent/pdf")

        assert response.status_code == 404

    def test_export_pdf_requires_auth(self):
        """Should require authentication."""
        response = client.get("/api/v2/user/export/projects/proj_1/pdf")

        assert response.status_code == 401


class TestExportProjectPreview:
    """Test GET /export/projects/{project_id}/preview endpoint."""

    @pytest.mark.skip(reason="Requires PyMuPDF (fitz) which may not be installed in test environment")
    @patch('api.user.export.log_activity')
    @patch('api.user.export.create_foldable_book')
    @patch('api.user.export.SupabaseProjectRepository')
    def test_export_preview_success(self, mock_repo_class, mock_create_pdf, mock_log, override_get_current_user):
        """Should export preview image."""
        pass

    @pytest.mark.skip(reason="Requires PyMuPDF (fitz) which may not be installed in test environment")
    @patch('api.user.export.SupabaseProjectRepository')
    def test_export_preview_project_not_found(self, mock_repo_class, override_get_current_user):
        """Should return 404 for non-existent project."""
        pass


class TestExportZIPDeprecated:
    """Test POST /export/zip endpoint (deprecated)."""

    @patch('api.user.export.log_activity')
    @patch('api.user.export.create_assets_zip')
    def test_export_zip_requires_pro(self, mock_create_zip, mock_log, override_get_current_user):
        """Should require Pro tier for ZIP export."""
        response = client.post(
            "/api/v2/user/export/zip",
            json={"image_urls": ["https://example.com/img1.png"]}
        )

        assert response.status_code == 403
        # Check detail exists - may be "detail" or "message"
        data = response.json()
        assert "Pro" in (data.get("detail", "") + data.get("message", ""))

    @patch('api.user.export.log_activity')
    @patch('api.user.export.create_assets_zip')
    def test_export_zip_success_for_pro(self, mock_create_zip, mock_log, override_pro_user):
        """Should export ZIP for Pro users."""
        mock_create_zip.side_effect = lambda urls, buf: buf.write(b"ZIP content")

        response = client.post(
            "/api/v2/user/export/zip",
            json={"image_urls": ["https://example.com/img1.png", "https://example.com/img2.png"]}
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert b"ZIP content" in response.content

    def test_export_zip_requires_auth(self):
        """Should require authentication."""
        response = client.post(
            "/api/v2/user/export/zip",
            json={"image_urls": ["https://example.com/img1.png"]}
        )

        assert response.status_code == 401


class TestExportProjectZIP:
    """Test GET /export/projects/{project_id}/zip endpoint."""

    @patch('api.user.export.log_activity')
    @patch('api.user.export.create_assets_zip')
    @patch('api.user.export.SupabaseProjectRepository')
    def test_export_project_zip_requires_pro(self, mock_repo_class, mock_create_zip, mock_log, override_get_current_user):
        """Should require Pro tier for ZIP export."""
        response = client.get("/api/v2/user/export/projects/proj_1/zip")

        assert response.status_code == 403
        # Check detail exists - may be "detail" or "message"
        data = response.json()
        assert "Pro" in (data.get("detail", "") + data.get("message", ""))

    @patch('api.user.export.log_activity')
    @patch('api.user.export.create_assets_zip')
    @patch('api.user.export.SupabaseProjectRepository')
    def test_export_project_zip_success(self, mock_repo_class, mock_create_zip, mock_log, override_pro_user):
        """Should export project as ZIP for Pro users."""
        mock_project = {
            "id": "proj_1",
            "title": "My Project",
            "canvas_data": {
                "pages": [
                    {"previewImage": "https://example.com/img1.png"},
                    {"previewImage": "https://example.com/img2.png"},
                ],
            }
        }

        mock_repo = MagicMock()
        mock_repo.get_project_detail = AsyncMock(return_value=mock_project)
        mock_repo_class.return_value = mock_repo

        mock_create_zip.side_effect = lambda urls, buf: buf.write(b"ZIP content")

        response = client.get("/api/v2/user/export/projects/proj_1/zip")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert b"ZIP content" in response.content

    @patch('api.user.export.SupabaseProjectRepository')
    def test_export_project_zip_not_found(self, mock_repo_class, override_pro_user):
        """Should return 404 for non-existent project."""
        mock_repo = MagicMock()
        mock_repo.get_project_detail = AsyncMock(return_value=None)
        mock_repo_class.return_value = mock_repo

        response = client.get("/api/v2/user/export/projects/proj_nonexistent/zip")

        assert response.status_code == 404

    def test_export_project_zip_requires_auth(self):
        """Should require authentication."""
        response = client.get("/api/v2/user/export/projects/proj_1/zip")

        assert response.status_code == 401
