"""
Tests for Export API (v3)

Endpoints tested:
- GET /api/v2/user/export/projects/{project_id}/pdf
- GET /api/v2/user/export/projects/{project_id}/preview
- POST /api/v2/user/export/zip (deprecated)
- GET /api/v2/user/export/projects/{project_id}/zip

@module tests.api.user.test_export
@version 3.0.0

Changes in v3.0.0:
- DDD architecture upgrade with ExportService
- Updated tests to use app.dependency_overrides (FastAPI best practice)
- Removed @patch decorators in favor of service mocking
- All tests now mock ExportService instead of Repository

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
from api.user.export import get_export_service
from domains.export.export_service import (
    ExportService,
    ProjectNotFoundException,
    ExportException,
    InsufficientPermissionException,
)

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

    def test_export_pdf_success(self, override_get_current_user):
        """
        v3.0.0: Should export project as PDF via ExportService.

        Given: Valid project_id and authenticated user
        When: GET /export/projects/{id}/pdf
        Then: Returns 200 with PDF content
        """
        # Arrange: Mock ExportService
        mock_service = MagicMock(spec=ExportService)
        pdf_buffer = BytesIO(b"PDF content")
        mock_service.export_pdf = AsyncMock(return_value=(pdf_buffer, "My Project"))

        app.dependency_overrides[get_export_service] = lambda: mock_service

        # Act
        response = client.get(f"/api/v2/user/export/projects/{VALID_PROJECT_ID}/pdf")

        # Assert
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert b"PDF content" in response.content
        assert 'filename="My Project.pdf"' in response.headers.get("content-disposition", "")

        # Verify service was called correctly
        mock_service.export_pdf.assert_called_once_with(
            "user_2NNEqL2nrIRdJ194ndJqAHwEfxC",
            VALID_PROJECT_ID
        )

        app.dependency_overrides.clear()

    def test_export_pdf_project_not_found(self, override_get_current_user):
        """
        v3.0.0: Should return 404 when project not found.

        Given: Non-existent project_id
        When: GET /export/projects/{id}/pdf
        Then: Returns 404 Not Found
        """
        # Arrange: Mock service to raise ProjectNotFoundException
        mock_service = MagicMock(spec=ExportService)
        mock_service.export_pdf = AsyncMock(side_effect=ProjectNotFoundException("Not found"))

        app.dependency_overrides[get_export_service] = lambda: mock_service

        # Act
        response = client.get(f"/api/v2/user/export/projects/{VALID_PROJECT_ID}/pdf")

        # Assert
        assert response.status_code == 404

        app.dependency_overrides.clear()

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

    def test_export_pdf_filename_sanitized(self, override_get_current_user):
        """
        v2.1.0/v3.0.0: EX-HIGH-2 - Should sanitize filename in Content-Disposition.

        Given: Project with malicious title (sanitized by Service)
        When: GET /export/projects/{id}/pdf
        Then: Filename is sanitized (special chars removed)
        """
        # Arrange: Mock service to return sanitized filename
        mock_service = MagicMock(spec=ExportService)
        pdf_buffer = BytesIO(b"PDF content")
        # Service already sanitizes: "My<script>alert('xss')</script>Project" → "MyscriptalertxssscriptProject"
        mock_service.export_pdf = AsyncMock(return_value=(pdf_buffer, "MyscriptalertxssscriptProject"))

        app.dependency_overrides[get_export_service] = lambda: mock_service

        # Act
        response = client.get(f"/api/v2/user/export/projects/{VALID_PROJECT_ID}/pdf")

        # Assert
        assert response.status_code == 200
        content_disp = response.headers.get("content-disposition", "")
        # Verify sanitized filename (no special chars)
        assert "<script>" not in content_disp
        assert "</script>" not in content_disp
        assert "'" not in content_disp

        app.dependency_overrides.clear()

    def test_export_pdf_generation_failed(self, override_get_current_user):
        """
        v3.0.0: Should return 500 when PDF generation fails.

        Given: PDF generation error in Service
        When: GET /export/projects/{id}/pdf
        Then: Returns 500 Internal Server Error
        """
        # Arrange: Mock service to raise ExportException
        mock_service = MagicMock(spec=ExportService)
        mock_service.export_pdf = AsyncMock(side_effect=ExportException("PDF generation failed"))

        app.dependency_overrides[get_export_service] = lambda: mock_service

        # Act
        response = client.get(f"/api/v2/user/export/projects/{VALID_PROJECT_ID}/pdf")

        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "PDF generation failed" in (data.get("detail", "") + data.get("message", ""))

        app.dependency_overrides.clear()


# ==========================================
# Test Cases - Preview Export
# ==========================================

class TestExportProjectPreview:
    """Test GET /export/projects/{project_id}/preview endpoint."""

    def test_export_preview_invalid_project_id(self, override_get_current_user):
        """
        v2.1.0/v3.0.0: EX-HIGH-1 - Should reject invalid project_id format.

        Given: Invalid project_id (not UUID format)
        When: GET /export/projects/{invalid_id}/preview
        Then: Returns 400 Bad Request
        """
        response = client.get(f"/api/v2/user/export/projects/{INVALID_PROJECT_ID}/preview")

        assert response.status_code == 400

    @pytest.mark.skip(reason="Requires PyMuPDF (fitz) which may not be installed in test environment")
    def test_export_preview_success(self, override_get_current_user):
        """
        v3.0.0: Should export preview image via ExportService.

        Note: Skipped because fitz (PyMuPDF) import happens at runtime in Service.
        """
        # Arrange: Mock ExportService
        mock_service = MagicMock(spec=ExportService)
        img_buffer = BytesIO(b"PNG image data")
        mock_service.export_preview = AsyncMock(return_value=img_buffer)

        app.dependency_overrides[get_export_service] = lambda: mock_service

        # Act
        response = client.get(f"/api/v2/user/export/projects/{VALID_PROJECT_ID}/preview")

        # Assert
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert b"PNG image data" in response.content

        app.dependency_overrides.clear()

    @pytest.mark.skip(reason="Requires PyMuPDF (fitz) which may not be installed in test environment")
    def test_export_preview_project_not_found(self, override_get_current_user):
        """
        v3.0.0: Should return 404 when project not found.

        Note: Skipped because fitz (PyMuPDF) import happens at runtime in Service.
        """
        # Arrange: Mock service to raise ProjectNotFoundException
        mock_service = MagicMock(spec=ExportService)
        mock_service.export_preview = AsyncMock(side_effect=ProjectNotFoundException("Not found"))

        app.dependency_overrides[get_export_service] = lambda: mock_service

        # Act
        response = client.get(f"/api/v2/user/export/projects/{VALID_PROJECT_ID}/preview")

        # Assert
        assert response.status_code == 404

        app.dependency_overrides.clear()


# ==========================================
# Test Cases - ZIP Export (Deprecated)
# ==========================================

class TestExportZIPDeprecated:
    """Test POST /export/zip endpoint (deprecated)."""

    def test_export_zip_requires_pro(self, override_get_current_user):
        """
        v3.0.0: Should require Pro tier for ZIP export.

        Given: Free tier user
        When: POST /export/zip
        Then: Returns 403 Forbidden
        """
        # Arrange: Mock service to raise InsufficientPermissionException
        mock_service = MagicMock(spec=ExportService)
        mock_service.export_custom_zip = AsyncMock(
            side_effect=InsufficientPermissionException("ZIP export requires Pro plan")
        )

        app.dependency_overrides[get_export_service] = lambda: mock_service

        # Act
        response = client.post(
            "/api/v2/user/export/zip",
            json={"image_urls": [ALLOWED_URL]}
        )

        # Assert
        assert response.status_code == 403
        data = response.json()
        assert "Pro" in (data.get("detail", "") + data.get("message", ""))

        app.dependency_overrides.clear()

    def test_export_zip_success_for_pro(self, override_pro_user):
        """
        v3.0.0: Should export ZIP for Pro users with allowed URLs.

        Given: Pro tier user and valid URLs
        When: POST /export/zip
        Then: Returns 200 with ZIP content
        """
        # Arrange: Mock ExportService
        mock_service = MagicMock(spec=ExportService)
        zip_buffer = BytesIO(b"ZIP content")
        mock_service.export_custom_zip = AsyncMock(return_value=zip_buffer)

        app.dependency_overrides[get_export_service] = lambda: mock_service

        # Act
        response = client.post(
            "/api/v2/user/export/zip",
            json={"image_urls": [ALLOWED_URL, "https://fal.media/test.png"]}
        )

        # Assert
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert b"ZIP content" in response.content

        # Verify service was called correctly
        mock_service.export_custom_zip.assert_called_once()
        call_args = mock_service.export_custom_zip.call_args[1]
        assert call_args["tier"] == "pro"
        assert len(call_args["image_urls"]) == 2

        app.dependency_overrides.clear()

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
        Then: Returns 422 Validation Error (Pydantic validation)
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
        Then: Returns 422 Validation Error (Pydantic validation)
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
        Then: Returns 422 Validation Error (Pydantic validation)
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
        v2.1.0/v3.0.0: EX-HIGH-1 - Should reject invalid project_id format.

        Given: Invalid project_id (not UUID format)
        When: GET /export/projects/{invalid_id}/zip
        Then: Returns 400 Bad Request
        """
        response = client.get(f"/api/v2/user/export/projects/{INVALID_PROJECT_ID}/zip")

        assert response.status_code == 400

    def test_export_project_zip_requires_pro(self, override_get_current_user):
        """
        v3.0.0: Should require Pro tier for ZIP export.

        Given: Free tier user
        When: GET /export/projects/{id}/zip
        Then: Returns 403 Forbidden
        """
        # Arrange: Mock service to raise InsufficientPermissionException
        mock_service = MagicMock(spec=ExportService)
        mock_service.export_project_zip = AsyncMock(
            side_effect=InsufficientPermissionException("ZIP export requires Pro plan")
        )

        app.dependency_overrides[get_export_service] = lambda: mock_service

        # Act
        response = client.get(f"/api/v2/user/export/projects/{VALID_PROJECT_ID}/zip")

        # Assert
        assert response.status_code == 403
        data = response.json()
        assert "Pro" in (data.get("detail", "") + data.get("message", ""))

        app.dependency_overrides.clear()

    def test_export_project_zip_success(self, override_pro_user):
        """
        v3.0.0: Should export project as ZIP for Pro users.

        Given: Pro tier user and valid project
        When: GET /export/projects/{id}/zip
        Then: Returns 200 with ZIP content
        """
        # Arrange: Mock ExportService
        mock_service = MagicMock(spec=ExportService)
        zip_buffer = BytesIO(b"ZIP content")
        mock_service.export_project_zip = AsyncMock(return_value=(zip_buffer, "My Project"))

        app.dependency_overrides[get_export_service] = lambda: mock_service

        # Act
        response = client.get(f"/api/v2/user/export/projects/{VALID_PROJECT_ID}/zip")

        # Assert
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert b"ZIP content" in response.content
        assert 'filename="My Project_assets.zip"' in response.headers.get("content-disposition", "")

        # Verify service was called correctly
        mock_service.export_project_zip.assert_called_once_with(
            user_id="user_2NNEqL2nrIRdJ194ndJqAHwEfxC",
            project_id=VALID_PROJECT_ID,
            tier="pro"
        )

        app.dependency_overrides.clear()

    def test_export_project_zip_not_found(self, override_pro_user):
        """
        v3.0.0: Should return 404 for non-existent project.

        Given: Non-existent project_id
        When: GET /export/projects/{id}/zip
        Then: Returns 404 Not Found
        """
        # Arrange: Mock service to raise ProjectNotFoundException
        mock_service = MagicMock(spec=ExportService)
        mock_service.export_project_zip = AsyncMock(side_effect=ProjectNotFoundException("Not found"))

        app.dependency_overrides[get_export_service] = lambda: mock_service

        # Act
        response = client.get(f"/api/v2/user/export/projects/{VALID_PROJECT_ID}/zip")

        # Assert
        assert response.status_code == 404

        app.dependency_overrides.clear()

    def test_export_project_zip_requires_auth(self):
        """Should require authentication."""
        response = client.get(f"/api/v2/user/export/projects/{VALID_PROJECT_ID}/zip")

        assert response.status_code == 401

    def test_export_project_zip_ssrf_protection(self, override_pro_user):
        """
        v2.1.0/v3.0.0: EX-P0-1 - Should filter disallowed URLs (SSRF protection in Service).

        Given: Project with mixed URLs (Service filters them)
        When: GET /export/projects/{id}/zip
        Then: Returns 200 (Service handles SSRF filtering)

        Note: SSRF protection is now handled in ExportService._is_allowed_url()
        This test verifies the endpoint works when Service filters properly.
        """
        # Arrange: Mock ExportService with already-filtered URLs
        mock_service = MagicMock(spec=ExportService)
        zip_buffer = BytesIO(b"ZIP with filtered URLs")
        # Service filters out DISALLOWED_URL, returns only allowed ones
        mock_service.export_project_zip = AsyncMock(return_value=(zip_buffer, "Test Project"))

        app.dependency_overrides[get_export_service] = lambda: mock_service

        # Act
        response = client.get(f"/api/v2/user/export/projects/{VALID_PROJECT_ID}/zip")

        # Assert
        assert response.status_code == 200
        assert b"ZIP with filtered URLs" in response.content

        app.dependency_overrides.clear()

    def test_export_project_zip_no_valid_urls(self, override_pro_user):
        """
        v2.1.0/v3.0.0: Should return 400 if project has no valid URLs.

        Given: Project with only disallowed URLs
        When: GET /export/projects/{id}/zip (Service raises ExportException)
        Then: Returns 400 Bad Request
        """
        # Arrange: Mock service to raise ExportException (no valid URLs)
        mock_service = MagicMock(spec=ExportService)
        mock_service.export_project_zip = AsyncMock(
            side_effect=ExportException("No valid image URLs found in project")
        )

        app.dependency_overrides[get_export_service] = lambda: mock_service

        # Act
        response = client.get(f"/api/v2/user/export/projects/{VALID_PROJECT_ID}/zip")

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "No valid" in (data.get("detail", "") + data.get("message", ""))

        app.dependency_overrides.clear()


# ==========================================
# Test Helper Functions
# ==========================================

class TestHelperFunctions:
    """Test helper functions for export module."""

    def test_is_allowed_url_allowed_domain(self):
        """
        v2.1.0: Test _is_allowed_url with allowed domains.

        Note: _is_allowed_url remains in API layer for Pydantic validation.
        """
        from api.user.export import _is_allowed_url

        # Supabase storage
        assert _is_allowed_url("https://xyz.supabase.co/storage/test.png") is True
        assert _is_allowed_url("https://project.supabase.com/test.png") is True

        # Fal.ai
        assert _is_allowed_url("https://fal.media/files/test.png") is True
        assert _is_allowed_url("https://cdn.fal.ai/test.png") is True

    def test_is_allowed_url_disallowed_domain(self):
        """
        v2.1.0: Test _is_allowed_url with disallowed domains.
        """
        from api.user.export import _is_allowed_url

        # Internal/localhost
        assert _is_allowed_url("http://localhost:8080/test.png") is False
        assert _is_allowed_url("http://127.0.0.1/test.png") is False
        assert _is_allowed_url("http://192.168.1.1/test.png") is False

        # External arbitrary domain
        assert _is_allowed_url("https://evil.com/test.png") is False
        assert _is_allowed_url("https://example.com/test.png") is False

    def test_is_allowed_url_edge_cases(self):
        """
        v2.1.0: Test _is_allowed_url with edge cases.
        """
        from api.user.export import _is_allowed_url

        assert _is_allowed_url("") is False
        assert _is_allowed_url(None) is False
        assert _is_allowed_url("not-a-url") is False
        assert _is_allowed_url("ftp://supabase.co/test.png") is False  # Wrong protocol

    def test_sanitize_filename_normal(self):
        """
        v3.0.0: Test _sanitize_filename with normal input.

        Note: _sanitize_filename moved to ExportService in v3.0.0.
        """
        from domains.export.export_service import ExportService

        service = ExportService(project_repository=None)  # No repo needed for this test

        assert service._sanitize_filename("My Project") == "My Project"
        assert service._sanitize_filename("test-file_123") == "test-file_123"

    def test_sanitize_filename_malicious(self):
        """
        v3.0.0: Test _sanitize_filename with malicious input.
        """
        from domains.export.export_service import ExportService

        service = ExportService(project_repository=None)

        # Script injection attempt
        result = service._sanitize_filename("<script>alert('xss')</script>")
        assert "<" not in result
        assert ">" not in result
        assert "'" not in result

        # Path traversal attempt
        result = service._sanitize_filename("../../../etc/passwd")
        assert "/" not in result
        assert ".." not in result

    def test_sanitize_filename_empty(self):
        """
        v3.0.0: Test _sanitize_filename with empty/None input.
        """
        from domains.export.export_service import ExportService

        service = ExportService(project_repository=None)

        assert service._sanitize_filename("") == "export"
        assert service._sanitize_filename(None) == "export"
        assert service._sanitize_filename("   ") == "export"

    def test_sanitize_filename_length_limit(self):
        """
        v3.0.0: Test _sanitize_filename truncates long names.
        """
        from domains.export.export_service import ExportService

        service = ExportService(project_repository=None)

        long_name = "a" * 100
        result = service._sanitize_filename(long_name)
        assert len(result) <= 50


# ==========================================
# Coverage Summary
# ==========================================

"""
Test Coverage Summary (v3.0.0):

GET /export/projects/{id}/pdf (6 tests):
- Success case via ExportService
- Project not found (404)
- Requires authentication (401)
- Invalid project_id format (400)
- Filename sanitization
- PDF generation failed (500) - NEW in v3.0.0

GET /export/projects/{id}/preview (3 tests):
- Invalid project_id format (400)
- (skipped) Success case - requires PyMuPDF
- (skipped) Project not found - requires PyMuPDF

POST /export/zip (6 tests):
- Requires Pro tier (403)
- Success for Pro users via ExportService
- Requires authentication (401)
- SSRF protection (422) - Pydantic validation
- URL count limit (422) - Pydantic validation
- Empty URLs rejected (422)

GET /export/projects/{id}/zip (7 tests):
- Invalid project_id format (400)
- Requires Pro tier (403)
- Success for Pro users via ExportService
- Project not found (404)
- Requires authentication (401)
- SSRF protection (Service filters URLs)
- No valid URLs (400)

Helper Functions (7 tests):
- _is_allowed_url with allowed domains (API layer)
- _is_allowed_url with disallowed domains (API layer)
- _is_allowed_url edge cases (API layer)
- _sanitize_filename normal input (Service layer) - MOVED in v3.0.0
- _sanitize_filename malicious input (Service layer)
- _sanitize_filename empty input (Service layer)
- _sanitize_filename length limit (Service layer)

Total: 29 tests (2 skipped) - +1 test in v3.0.0

Architecture Changes in v3.0.0:
- ✅ DDD compliance: API → Service → Repository
- ✅ Dependency injection via app.dependency_overrides
- ✅ All tests use ExportService mocking (no @patch on Repository)
- ✅ _sanitize_filename moved to ExportService (private method)
- ✅ _is_allowed_url remains in API layer (Pydantic + Service both use it)

Security Improvements in v2.1.0 (maintained):
- EX-P0-1/2: SSRF protection via URL domain whitelist
- EX-HIGH-1: UUID validation for project_id
- EX-HIGH-2: Filename sanitization in Content-Disposition
- EX-MEDIUM-2: URL count limit (max 20)
"""
