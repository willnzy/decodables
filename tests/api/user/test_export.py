"""
Tests for Export API (v2)

Endpoints tested:
- GET /api/v2/user/export/projects/{project_id}/pdf
- GET /api/v2/user/export/projects/{project_id}/preview
- POST /api/v2/user/export/zip (deprecated)
- GET /api/v2/user/export/projects/{project_id}/zip

@module tests.api.user.test_export
@version 2.1.0

Changes in v2.1.0:
- Added tests for SSRF protection (URL domain whitelist)
- Added tests for UUID validation
- Added tests for filename sanitization
- Added tests for URL count limits
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

# Valid UUID for testing
VALID_PROJECT_ID = "12345678-1234-1234-1234-123456789abc"
INVALID_PROJECT_ID = "not-a-valid-uuid"

# Allowed URL for testing (from ALLOWED_URL_DOMAINS)
ALLOWED_URL = "https://xyz.supabase.co/storage/v1/object/public/test.png"
DISALLOWED_URL = "http://localhost:8080/internal/secret"


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def mock_free_user():
    """Mock free tier user."""
    return {
        "id": "user_2NNEqL2nrIRdJ194ndJqAHwEfxC",
        "email": "user@example.com",
        "tier": "free",
    }


@pytest.fixture
def mock_pro_user():
    """Mock pro tier user."""
    return {
        "id": "user_2NNEqL2nrIRdJ194ndJqAHwEfxC",
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
# Test Cases - PDF Export
# ==========================================

class TestExportProjectPDF:
    """Test GET /export/projects/{project_id}/pdf endpoint."""

    @patch('api.user.export.log_activity')
    @patch('api.user.export.create_foldable_book')
    @patch('api.user.export.SupabaseProjectRepository')
    def test_export_pdf_success(self, mock_repo_class, mock_create_pdf, mock_log, override_get_current_user):
        """Should export project as PDF."""
        mock_project = {
            "id": VALID_PROJECT_ID,
            "title": "My Project",
            "canvas_data": {
                "pages": [
                    {"previewImage": ALLOWED_URL, "prompt": "Page 1"},
                    {"previewImage": ALLOWED_URL, "prompt": "Page 2"},
                ],
                "paperSize": "Letter",
            }
        }

        mock_repo = MagicMock()
        mock_repo.get_project_detail = AsyncMock(return_value=mock_project)
        mock_repo_class.return_value = mock_repo

        # Mock PDF creation
        mock_create_pdf.side_effect = lambda urls, texts, buf, paper_type: buf.write(b"PDF content")

        response = client.get(f"/api/v2/user/export/projects/{VALID_PROJECT_ID}/pdf")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert b"PDF content" in response.content

    @patch('api.user.export.SupabaseProjectRepository')
    def test_export_pdf_project_not_found(self, mock_repo_class, override_get_current_user):
        """Should return 404 for non-existent project."""
        mock_repo = MagicMock()
        mock_repo.get_project_detail = AsyncMock(return_value=None)
        mock_repo_class.return_value = mock_repo

        response = client.get(f"/api/v2/user/export/projects/{VALID_PROJECT_ID}/pdf")

        assert response.status_code == 404

    def test_export_pdf_requires_auth(self):
        """Should require authentication."""
        response = client.get(f"/api/v2/user/export/projects/{VALID_PROJECT_ID}/pdf")

        assert response.status_code == 401

    def test_export_pdf_invalid_project_id(self, override_get_current_user):
        """
        v2.1.0: EX-HIGH-1 - Should reject invalid project_id format.

        Given: Invalid project_id (not UUID format)
        When: GET /export/projects/{invalid_id}/pdf
        Then: Returns 400 Bad Request
        """
        response = client.get(f"/api/v2/user/export/projects/{INVALID_PROJECT_ID}/pdf")

        assert response.status_code == 400
        data = response.json()
        assert "Invalid" in (data.get("detail", "") + data.get("message", ""))

    @patch('api.user.export.log_activity')
    @patch('api.user.export.create_foldable_book')
    @patch('api.user.export.SupabaseProjectRepository')
    def test_export_pdf_filename_sanitized(self, mock_repo_class, mock_create_pdf, mock_log, override_get_current_user):
        """
        v2.1.0: EX-HIGH-2 - Should sanitize filename in Content-Disposition.

        Given: Project with malicious title (contains special chars)
        When: GET /export/projects/{id}/pdf
        Then: Filename is sanitized (special chars removed)
        """
        mock_project = {
            "id": VALID_PROJECT_ID,
            "title": "My<script>alert('xss')</script>Project",  # Malicious title
            "canvas_data": {"pages": []},
        }

        mock_repo = MagicMock()
        mock_repo.get_project_detail = AsyncMock(return_value=mock_project)
        mock_repo_class.return_value = mock_repo
        mock_create_pdf.side_effect = lambda urls, texts, buf, paper_type: buf.write(b"PDF")

        response = client.get(f"/api/v2/user/export/projects/{VALID_PROJECT_ID}/pdf")

        assert response.status_code == 200
        # Check that special chars are removed from filename
        content_disp = response.headers.get("content-disposition", "")
        # Script tags should be removed (< and > are filtered)
        assert "<script>" not in content_disp
        assert "</script>" not in content_disp
        # Single quotes should be removed
        assert "'" not in content_disp


# ==========================================
# Test Cases - Preview Export
# ==========================================

class TestExportProjectPreview:
    """Test GET /export/projects/{project_id}/preview endpoint."""

    @pytest.mark.skip(reason="Requires PyMuPDF (fitz) which may not be installed in test environment")
    def test_export_preview_invalid_project_id(self, override_get_current_user):
        """
        v2.1.0: EX-HIGH-1 - Should reject invalid project_id format.

        Given: Invalid project_id (not UUID format)
        When: GET /export/projects/{invalid_id}/preview
        Then: Returns 400 Bad Request

        Note: Skipped because fitz import happens at function call time.
        """
        response = client.get(f"/api/v2/user/export/projects/{INVALID_PROJECT_ID}/preview")

        assert response.status_code == 400

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


# ==========================================
# Test Cases - ZIP Export (Deprecated)
# ==========================================

class TestExportZIPDeprecated:
    """Test POST /export/zip endpoint (deprecated)."""

    def test_export_zip_requires_pro(self, override_get_current_user):
        """Should require Pro tier for ZIP export."""
        response = client.post(
            "/api/v2/user/export/zip",
            json={"image_urls": [ALLOWED_URL]}
        )

        assert response.status_code == 403
        data = response.json()
        assert "Pro" in (data.get("detail", "") + data.get("message", ""))

    @patch('api.user.export.log_activity')
    @patch('api.user.export.create_assets_zip')
    def test_export_zip_success_for_pro(self, mock_create_zip, mock_log, override_pro_user):
        """Should export ZIP for Pro users with allowed URLs."""
        mock_create_zip.side_effect = lambda urls, buf: buf.write(b"ZIP content")

        response = client.post(
            "/api/v2/user/export/zip",
            json={"image_urls": [ALLOWED_URL, "https://fal.media/test.png"]}
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert b"ZIP content" in response.content

    def test_export_zip_requires_auth(self):
        """Should require authentication."""
        response = client.post(
            "/api/v2/user/export/zip",
            json={"image_urls": [ALLOWED_URL]}
        )

        assert response.status_code == 401

    def test_export_zip_ssrf_protection(self, override_pro_user):
        """
        v2.1.0: EX-P0-2 - Should reject URLs from disallowed domains (SSRF protection).

        Given: URL from localhost (internal network)
        When: POST /export/zip with disallowed URL
        Then: Returns 422 Validation Error
        """
        response = client.post(
            "/api/v2/user/export/zip",
            json={"image_urls": [DISALLOWED_URL]}
        )

        assert response.status_code == 422

    def test_export_zip_url_count_limit(self, override_pro_user):
        """
        v2.1.0: EX-MEDIUM-2 - Should limit number of URLs (DoS protection).

        Given: More than 20 URLs
        When: POST /export/zip
        Then: Returns 422 Validation Error
        """
        # Create 25 URLs (exceeds 20 limit)
        too_many_urls = [f"https://xyz.supabase.co/img{i}.png" for i in range(25)]

        response = client.post(
            "/api/v2/user/export/zip",
            json={"image_urls": too_many_urls}
        )

        assert response.status_code == 422

    def test_export_zip_empty_urls(self, override_pro_user):
        """
        v2.1.0: Should reject empty URL list.

        Given: Empty image_urls array
        When: POST /export/zip
        Then: Returns 422 Validation Error
        """
        response = client.post(
            "/api/v2/user/export/zip",
            json={"image_urls": []}
        )

        assert response.status_code == 422


# ==========================================
# Test Cases - Project ZIP Export
# ==========================================

class TestExportProjectZIP:
    """Test GET /export/projects/{project_id}/zip endpoint."""

    def test_export_project_zip_invalid_id(self, override_pro_user):
        """
        v2.1.0: EX-HIGH-1 - Should reject invalid project_id format.

        Given: Invalid project_id (not UUID format)
        When: GET /export/projects/{invalid_id}/zip
        Then: Returns 400 Bad Request
        """
        response = client.get(f"/api/v2/user/export/projects/{INVALID_PROJECT_ID}/zip")

        assert response.status_code == 400

    def test_export_project_zip_requires_pro(self, override_get_current_user):
        """Should require Pro tier for ZIP export."""
        response = client.get(f"/api/v2/user/export/projects/{VALID_PROJECT_ID}/zip")

        assert response.status_code == 403
        data = response.json()
        assert "Pro" in (data.get("detail", "") + data.get("message", ""))

    @patch('api.user.export.log_activity')
    @patch('api.user.export.create_assets_zip')
    @patch('api.user.export.SupabaseProjectRepository')
    def test_export_project_zip_success(self, mock_repo_class, mock_create_zip, mock_log, override_pro_user):
        """Should export project as ZIP for Pro users."""
        mock_project = {
            "id": VALID_PROJECT_ID,
            "title": "My Project",
            "canvas_data": {
                "pages": [
                    {"previewImage": ALLOWED_URL},
                    {"previewImage": "https://fal.media/test.png"},
                ],
            }
        }

        mock_repo = MagicMock()
        mock_repo.get_project_detail = AsyncMock(return_value=mock_project)
        mock_repo_class.return_value = mock_repo

        mock_create_zip.side_effect = lambda urls, buf: buf.write(b"ZIP content")

        response = client.get(f"/api/v2/user/export/projects/{VALID_PROJECT_ID}/zip")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert b"ZIP content" in response.content

    @patch('api.user.export.SupabaseProjectRepository')
    def test_export_project_zip_not_found(self, mock_repo_class, override_pro_user):
        """Should return 404 for non-existent project."""
        mock_repo = MagicMock()
        mock_repo.get_project_detail = AsyncMock(return_value=None)
        mock_repo_class.return_value = mock_repo

        response = client.get(f"/api/v2/user/export/projects/{VALID_PROJECT_ID}/zip")

        assert response.status_code == 404

    def test_export_project_zip_requires_auth(self):
        """Should require authentication."""
        response = client.get(f"/api/v2/user/export/projects/{VALID_PROJECT_ID}/zip")

        assert response.status_code == 401

    @patch('api.user.export.log_activity')
    @patch('api.user.export.create_assets_zip')
    @patch('api.user.export.SupabaseProjectRepository')
    def test_export_project_zip_ssrf_protection(self, mock_repo_class, mock_create_zip, mock_log, override_pro_user):
        """
        v2.1.0: EX-P0-1 - Should filter out disallowed URLs from project (SSRF protection).

        Given: Project with mixed URLs (allowed + disallowed)
        When: GET /export/projects/{id}/zip
        Then: Only allowed URLs are included in ZIP
        """
        mock_project = {
            "id": VALID_PROJECT_ID,
            "title": "Test Project",
            "canvas_data": {
                "pages": [
                    {"previewImage": ALLOWED_URL},  # Allowed
                    {"previewImage": DISALLOWED_URL},  # Should be filtered
                ],
            }
        }

        mock_repo = MagicMock()
        mock_repo.get_project_detail = AsyncMock(return_value=mock_project)
        mock_repo_class.return_value = mock_repo

        captured_urls = []
        def capture_urls(urls, buf):
            captured_urls.extend(urls)
            buf.write(b"ZIP")

        mock_create_zip.side_effect = capture_urls

        response = client.get(f"/api/v2/user/export/projects/{VALID_PROJECT_ID}/zip")

        assert response.status_code == 200
        # Verify only allowed URLs were passed to create_assets_zip
        assert ALLOWED_URL in captured_urls
        assert DISALLOWED_URL not in captured_urls

    @patch('api.user.export.SupabaseProjectRepository')
    def test_export_project_zip_no_valid_urls(self, mock_repo_class, override_pro_user):
        """
        v2.1.0: Should return 400 if project has no valid URLs.

        Given: Project with only disallowed URLs
        When: GET /export/projects/{id}/zip
        Then: Returns 400 Bad Request
        """
        mock_project = {
            "id": VALID_PROJECT_ID,
            "title": "Test Project",
            "canvas_data": {
                "pages": [
                    {"previewImage": DISALLOWED_URL},  # All URLs filtered
                    {"previewImage": "http://192.168.1.1/private.png"},  # Internal IP
                ],
            }
        }

        mock_repo = MagicMock()
        mock_repo.get_project_detail = AsyncMock(return_value=mock_project)
        mock_repo_class.return_value = mock_repo

        response = client.get(f"/api/v2/user/export/projects/{VALID_PROJECT_ID}/zip")

        assert response.status_code == 400


# ==========================================
# Test Helper Functions
# ==========================================

class TestHelperFunctions:
    """Test helper functions for export module."""

    def test_is_allowed_url_allowed_domain(self):
        """Test _is_allowed_url with allowed domains."""
        from api.user.export import _is_allowed_url

        # Supabase storage
        assert _is_allowed_url("https://xyz.supabase.co/storage/test.png") is True
        assert _is_allowed_url("https://project.supabase.com/test.png") is True

        # Fal.ai
        assert _is_allowed_url("https://fal.media/files/test.png") is True
        assert _is_allowed_url("https://cdn.fal.ai/test.png") is True

    def test_is_allowed_url_disallowed_domain(self):
        """Test _is_allowed_url with disallowed domains."""
        from api.user.export import _is_allowed_url

        # Internal/localhost
        assert _is_allowed_url("http://localhost:8080/test.png") is False
        assert _is_allowed_url("http://127.0.0.1/test.png") is False
        assert _is_allowed_url("http://192.168.1.1/test.png") is False

        # External arbitrary domain
        assert _is_allowed_url("https://evil.com/test.png") is False
        assert _is_allowed_url("https://example.com/test.png") is False

    def test_is_allowed_url_edge_cases(self):
        """Test _is_allowed_url with edge cases."""
        from api.user.export import _is_allowed_url

        assert _is_allowed_url("") is False
        assert _is_allowed_url(None) is False
        assert _is_allowed_url("not-a-url") is False
        assert _is_allowed_url("ftp://supabase.co/test.png") is False  # Wrong protocol

    def test_sanitize_filename_normal(self):
        """Test _sanitize_filename with normal input."""
        from api.user.export import _sanitize_filename

        assert _sanitize_filename("My Project") == "My Project"
        assert _sanitize_filename("test-file_123") == "test-file_123"

    def test_sanitize_filename_malicious(self):
        """Test _sanitize_filename with malicious input."""
        from api.user.export import _sanitize_filename

        # Script injection attempt
        result = _sanitize_filename("<script>alert('xss')</script>")
        assert "<" not in result
        assert ">" not in result
        assert "'" not in result

        # Path traversal attempt
        result = _sanitize_filename("../../../etc/passwd")
        assert "/" not in result
        assert ".." not in result

    def test_sanitize_filename_empty(self):
        """Test _sanitize_filename with empty/None input."""
        from api.user.export import _sanitize_filename

        assert _sanitize_filename("") == "export"
        assert _sanitize_filename(None) == "export"
        assert _sanitize_filename("   ") == "export"

    def test_sanitize_filename_length_limit(self):
        """Test _sanitize_filename truncates long names."""
        from api.user.export import _sanitize_filename

        long_name = "a" * 100
        result = _sanitize_filename(long_name)
        assert len(result) <= 50


# ==========================================
# Coverage Summary
# ==========================================

"""
Test Coverage Summary:

GET /export/projects/{id}/pdf (4 tests):
- Success case
- Project not found (404)
- Requires authentication (401)
- Invalid project_id format (400) - v2.1.0
- Filename sanitization - v2.1.0

GET /export/projects/{id}/preview (3 tests):
- Invalid project_id format (400) - v2.1.0
- (skipped) Success case - requires PyMuPDF
- (skipped) Project not found - requires PyMuPDF

POST /export/zip (6 tests):
- Requires Pro tier (403)
- Success for Pro users
- Requires authentication (401)
- SSRF protection (422) - v2.1.0
- URL count limit (422) - v2.1.0
- Empty URLs rejected (422) - v2.1.0

GET /export/projects/{id}/zip (6 tests):
- Invalid project_id format (400) - v2.1.0
- Requires Pro tier (403)
- Success for Pro users
- Project not found (404)
- Requires authentication (401)
- SSRF protection (filters disallowed URLs) - v2.1.0
- No valid URLs (400) - v2.1.0

Helper Functions (9 tests):
- _is_allowed_url with allowed domains
- _is_allowed_url with disallowed domains
- _is_allowed_url edge cases
- _sanitize_filename normal input
- _sanitize_filename malicious input
- _sanitize_filename empty input
- _sanitize_filename length limit

Total: 28 tests (2 skipped)

Security Improvements in v2.1.0:
- EX-P0-1/2: SSRF protection via URL domain whitelist
- EX-HIGH-1: UUID validation for project_id
- EX-HIGH-2: Filename sanitization in Content-Disposition
- EX-MEDIUM-2: URL count limit (max 20)
"""
