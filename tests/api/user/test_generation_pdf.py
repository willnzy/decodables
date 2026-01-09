"""
Test generation_pdf API endpoints.

@version 3.0.0

Tests for POST /api/v2/user/generate/pdf/pdf endpoint:
- v3.0.0: Complete rewrite using app.dependency_overrides (FastAPI best practice)
          Mock PdfGenerationService instead of individual components
          Added integration tests for API endpoints
- v2.0.0: Security validations (GP-P0-1/2, GP-HIGH-1/2, GP-MEDIUM-1)
"""

import pytest
from io import BytesIO
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient

# Rate limiter bypass BEFORE app import
@patch("infrastructure.rate_limiter.limiter.enabled", False)
def noop_decorator(*args, **kwargs):
    return lambda f: f
patch("infrastructure.rate_limiter.limiter.limit", noop_decorator).start()

from app import app
from dependencies import get_current_user
from api.user.generation_pdf import get_pdf_service
from domains.generation.pdf_service import (
    ProjectNotFoundException,
    PdfGenerationException,
)

from api.schemas.user.generation import (
    is_allowed_url,
    ALLOWED_URL_DOMAINS,
    UUID_PATTERN,
)


# ==========================================
# Test Fixtures
# ==========================================

client = TestClient(app)

@pytest.fixture
def mock_free_user():
    """Mock free tier user."""
    return {
        "id": "user_123abc",
        "email": "test@example.com",
        "tier": "free",
    }

@pytest.fixture
def override_free_user(mock_free_user):
    """Override get_current_user dependency with free user."""
    app.dependency_overrides[get_current_user] = lambda: mock_free_user
    yield
    app.dependency_overrides.clear()


# ==========================================
# Test Constants
# ==========================================

VALID_PROJECT_ID = "12345678-1234-1234-1234-123456789abc"
INVALID_PROJECT_ID = "not-a-valid-uuid"
VALID_HASH = "abc123_def-456"
INVALID_HASH = "hash<script>alert(1)</script>"

ALLOWED_URL = "https://xyz.supabase.co/storage/v1/object/public/test.png"
DISALLOWED_URL = "http://localhost:8080/internal/secret"
INTERNAL_URL = "http://169.254.169.254/latest/meta-data/"


# ==========================================
# Test: is_allowed_url Helper
# ==========================================

class TestIsAllowedUrl:
    """Tests for SSRF protection helper function."""

    def test_allowed_supabase_url(self):
        """Supabase URLs should be allowed."""
        assert is_allowed_url("https://xyz.supabase.co/storage/test.png") is True
        assert is_allowed_url("https://project.supabase.com/file.jpg") is True

    def test_allowed_fal_url(self):
        """Fal.ai URLs should be allowed."""
        assert is_allowed_url("https://fal.media/files/image.png") is True
        assert is_allowed_url("https://cdn.fal.ai/output.jpg") is True

    def test_allowed_s3_url(self):
        """AWS S3 URLs should be allowed."""
        assert is_allowed_url("https://bucket.s3.amazonaws.com/file.png") is True

    def test_disallowed_localhost(self):
        """Localhost URLs should be blocked."""
        assert is_allowed_url("http://localhost:8080/secret") is False
        assert is_allowed_url("http://127.0.0.1/admin") is False

    def test_disallowed_internal_ip(self):
        """Internal IP ranges should be blocked."""
        assert is_allowed_url("http://192.168.1.1/config") is False
        assert is_allowed_url("http://10.0.0.1/internal") is False

    def test_disallowed_cloud_metadata(self):
        """Cloud metadata endpoints should be blocked."""
        assert is_allowed_url("http://169.254.169.254/latest/meta-data/") is False

    def test_disallowed_arbitrary_domain(self):
        """Arbitrary domains should be blocked."""
        assert is_allowed_url("https://evil.com/malware.exe") is False
        assert is_allowed_url("https://attacker.net/payload") is False

    def test_empty_url(self):
        """Empty URLs should return False."""
        assert is_allowed_url("") is False
        assert is_allowed_url(None) is False

    def test_non_http_url(self):
        """Non-HTTP URLs should be blocked."""
        assert is_allowed_url("file:///etc/passwd") is False
        assert is_allowed_url("ftp://server/file") is False

    def test_malformed_url(self):
        """Malformed URLs should be handled gracefully."""
        assert is_allowed_url("not-a-url") is False
        assert is_allowed_url("://missing-scheme") is False


# ==========================================
# Test: PdfGenRequest Validation
# ==========================================

from api.schemas.user.generation import PdfGenRequest

class TestPdfGenRequestValidation:
    """Tests for PdfGenRequest schema validation."""

    def test_valid_request(self):
        """Valid request should pass validation."""
        req = PdfGenRequest(
            project_id=VALID_PROJECT_ID,
            current_hash="abc123",
            image_urls=[ALLOWED_URL, ""],
            texts=["Page 1", "Page 2"],
        )
        assert req.project_id == VALID_PROJECT_ID
        assert len(req.image_urls) == 2

    def test_invalid_project_id_rejected(self):
        """Invalid project_id format should be rejected."""
        with pytest.raises(ValueError) as exc:
            PdfGenRequest(
                project_id=INVALID_PROJECT_ID,
                current_hash="abc123",
                image_urls=[ALLOWED_URL],
                texts=["Test"],
            )
        assert "pattern" in str(exc.value).lower() or "string" in str(exc.value).lower()

    def test_invalid_hash_rejected(self):
        """Invalid hash format should be rejected."""
        with pytest.raises(ValueError) as exc:
            PdfGenRequest(
                project_id=VALID_PROJECT_ID,
                current_hash=INVALID_HASH,
                image_urls=[ALLOWED_URL],
                texts=["Test"],
            )
        assert "pattern" in str(exc.value).lower() or "string" in str(exc.value).lower()

    def test_disallowed_url_rejected(self):
        """Disallowed URLs should be rejected (SSRF protection)."""
        with pytest.raises(ValueError) as exc:
            PdfGenRequest(
                project_id=VALID_PROJECT_ID,
                current_hash="abc123",
                image_urls=[DISALLOWED_URL],
                texts=["Test"],
            )
        assert "domain not allowed" in str(exc.value).lower()

    def test_internal_url_rejected(self):
        """Internal/metadata URLs should be rejected."""
        with pytest.raises(ValueError) as exc:
            PdfGenRequest(
                project_id=VALID_PROJECT_ID,
                current_hash="abc123",
                image_urls=[INTERNAL_URL],
                texts=["Test"],
            )
        assert "domain not allowed" in str(exc.value).lower()

    def test_empty_urls_allowed(self):
        """Empty URL strings (blank pages) should be allowed."""
        req = PdfGenRequest(
            project_id=VALID_PROJECT_ID,
            current_hash="abc123",
            image_urls=["", "", ALLOWED_URL],
            texts=["", "", "Page 3"],
        )
        assert req.image_urls[0] == ""
        assert req.image_urls[2] == ALLOWED_URL

    def test_too_many_urls_rejected(self):
        """More than 20 URLs should be rejected."""
        urls = [ALLOWED_URL] * 25
        with pytest.raises(ValueError) as exc:
            PdfGenRequest(
                project_id=VALID_PROJECT_ID,
                current_hash="abc123",
                image_urls=urls,
                texts=[""] * 25,
            )
        # max_length validation error

    def test_long_text_truncated(self):
        """Overly long texts should be truncated to 2000 chars."""
        long_text = "x" * 3000
        req = PdfGenRequest(
            project_id=VALID_PROJECT_ID,
            current_hash="abc123",
            image_urls=[ALLOWED_URL],
            texts=[long_text],
        )
        assert len(req.texts[0]) == 2000

    def test_hash_max_length(self):
        """Hash exceeding max length should be rejected."""
        long_hash = "a" * 200
        with pytest.raises(ValueError):
            PdfGenRequest(
                project_id=VALID_PROJECT_ID,
                current_hash=long_hash,
                image_urls=[ALLOWED_URL],
                texts=["Test"],
            )


# ==========================================
# Test: UUID Pattern
# ==========================================

class TestUuidPattern:
    """Tests for UUID validation pattern."""

    def test_valid_uuid_lowercase(self):
        """Lowercase UUID should match."""
        assert UUID_PATTERN.match("12345678-1234-1234-1234-123456789abc")

    def test_valid_uuid_uppercase(self):
        """Uppercase UUID should match."""
        assert UUID_PATTERN.match("12345678-1234-1234-1234-123456789ABC")

    def test_valid_uuid_mixed_case(self):
        """Mixed case UUID should match."""
        # Note: UUID only uses hex chars (0-9, a-f/A-F), not g or h
        assert UUID_PATTERN.match("12345678-AbCd-1234-EfAb-123456789abc")

    def test_invalid_uuid_short(self):
        """Short UUID should not match."""
        assert not UUID_PATTERN.match("12345678-1234-1234-1234")

    def test_invalid_uuid_no_dashes(self):
        """UUID without dashes should not match."""
        assert not UUID_PATTERN.match("12345678123412341234123456789abc")

    def test_invalid_uuid_special_chars(self):
        """UUID with special chars should not match."""
        assert not UUID_PATTERN.match("12345678-1234-1234-1234-12345678<>ab")


# ==========================================
# Test: ALLOWED_URL_DOMAINS
# ==========================================

class TestAllowedDomains:
    """Tests for allowed domain whitelist."""

    def test_expected_domains_present(self):
        """All expected storage domains should be in whitelist."""
        expected = {"supabase.co", "supabase.com", "fal.media", "fal.ai"}
        assert expected.issubset(ALLOWED_URL_DOMAINS)

    def test_dangerous_domains_not_present(self):
        """Dangerous domains should not be in whitelist."""
        dangerous = {"localhost", "127.0.0.1", "169.254.169.254"}
        assert dangerous.isdisjoint(ALLOWED_URL_DOMAINS)


# ==========================================
# Test: POST /api/v2/user/generate/pdf/pdf (Integration)
# ==========================================

class TestGenPdf:
    """Tests for POST /api/v2/user/generate/pdf/pdf endpoint (v3.0.0 - DI-based)."""

    def test_gen_pdf_success(
        self,
        mock_free_user,
        override_free_user,
    ):
        """
        Test: Successful PDF generation.

        Given: Valid request with project ownership
        When: POST /api/v2/user/generate/pdf/pdf
        Then: Returns PDF file with 200 status
        """
        # Arrange - Mock PdfGenerationService
        mock_service = MagicMock()
        fake_pdf = BytesIO(b"%PDF-1.4\nfake pdf content")
        mock_service.generate_pdf = AsyncMock(return_value=fake_pdf)

        # Override DI (FastAPI best practice)
        app.dependency_overrides[get_pdf_service] = lambda: mock_service

        # Act
        response = client.post(
            "/api/v2/user/generate/pdf/pdf",
            json={
                "project_id": VALID_PROJECT_ID,
                "current_hash": "abc123",
                "image_urls": [ALLOWED_URL, ""],
                "texts": ["Page 1", "Page 2"],
            },
        )

        # Assert
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "attachment" in response.headers["content-disposition"]
        assert "zine.pdf" in response.headers["content-disposition"]

        # Verify Service was called
        mock_service.generate_pdf.assert_called_once()
        call_kwargs = mock_service.generate_pdf.call_args.kwargs
        assert call_kwargs["user_id"] == mock_free_user["id"]
        assert call_kwargs["project_id"] == VALID_PROJECT_ID
        assert call_kwargs["current_hash"] == "abc123"
        assert call_kwargs["image_urls"] == [ALLOWED_URL, ""]
        assert call_kwargs["texts"] == ["Page 1", "Page 2"]

        # Cleanup
        app.dependency_overrides.clear()

    def test_gen_pdf_project_not_found(
        self,
        override_free_user,
    ):
        """
        Test: Returns 404 for non-existent or unauthorized project.

        Given: Project not found or user lacks permission
        When: POST /api/v2/user/generate/pdf/pdf
        Then: Returns 404 Not Found
        """
        # Arrange
        mock_service = MagicMock()
        mock_service.generate_pdf = AsyncMock(
            side_effect=ProjectNotFoundException(VALID_PROJECT_ID)
        )

        app.dependency_overrides[get_pdf_service] = lambda: mock_service

        # Act
        response = client.post(
            "/api/v2/user/generate/pdf/pdf",
            json={
                "project_id": VALID_PROJECT_ID,
                "current_hash": "abc123",
                "image_urls": [ALLOWED_URL],
                "texts": ["Test"],
            },
        )

        # Assert
        assert response.status_code == 404
        data = response.json()
        error_msg = data.get("detail", "") or data.get("message", "")
        assert "not found" in error_msg.lower() or "access denied" in error_msg.lower()

        app.dependency_overrides.clear()

    def test_gen_pdf_generation_failure(
        self,
        override_free_user,
    ):
        """
        Test: Returns 500 on PDF generation error.

        Given: PDF generation fails (invalid image format, network error, etc.)
        When: POST /api/v2/user/generate/pdf/pdf
        Then: Returns 500 Internal Server Error with friendly message
        """
        # Arrange
        mock_service = MagicMock()
        mock_service.generate_pdf = AsyncMock(
            side_effect=PdfGenerationException("Invalid image format")
        )

        app.dependency_overrides[get_pdf_service] = lambda: mock_service

        # Act
        response = client.post(
            "/api/v2/user/generate/pdf/pdf",
            json={
                "project_id": VALID_PROJECT_ID,
                "current_hash": "abc123",
                "image_urls": [ALLOWED_URL],
                "texts": ["Test"],
            },
        )

        # Assert
        assert response.status_code == 500
        data = response.json()
        error_msg = data.get("detail", "") or data.get("message", "")
        assert "failed" in error_msg.lower()

        app.dependency_overrides.clear()

    def test_gen_pdf_unauthorized(self):
        """
        Test: Returns 401 without authentication.

        Given: No authentication token
        When: POST /api/v2/user/generate/pdf/pdf
        Then: Returns 401 Unauthorized
        """
        # Act - No authentication override
        response = client.post(
            "/api/v2/user/generate/pdf/pdf",
            json={
                "project_id": VALID_PROJECT_ID,
                "current_hash": "abc123",
                "image_urls": [ALLOWED_URL],
                "texts": ["Test"],
            },
        )

        # Assert
        assert response.status_code == 401

    def test_gen_pdf_invalid_project_id(
        self,
        override_free_user,
    ):
        """
        Test: Returns 422 for invalid project_id format.

        Given: project_id not matching UUID pattern
        When: POST /api/v2/user/generate/pdf/pdf
        Then: Returns 422 Unprocessable Entity (schema validation)
        """
        # Act
        response = client.post(
            "/api/v2/user/generate/pdf/pdf",
            json={
                "project_id": INVALID_PROJECT_ID,  # Not a UUID
                "current_hash": "abc123",
                "image_urls": [ALLOWED_URL],
                "texts": ["Test"],
            },
        )

        # Assert
        assert response.status_code == 422

    def test_gen_pdf_disallowed_url(
        self,
        override_free_user,
    ):
        """
        Test: Returns 422 for disallowed URL (SSRF protection).

        Given: image_urls contains non-whitelisted domain
        When: POST /api/v2/user/generate/pdf/pdf
        Then: Returns 422 Unprocessable Entity (schema validation)
        """
        # Act
        response = client.post(
            "/api/v2/user/generate/pdf/pdf",
            json={
                "project_id": VALID_PROJECT_ID,
                "current_hash": "abc123",
                "image_urls": [DISALLOWED_URL],  # Not in whitelist
                "texts": ["Test"],
            },
        )

        # Assert
        assert response.status_code == 422
        data = response.json()
        error_detail = str(data)
        assert "domain not allowed" in error_detail.lower()

    def test_gen_pdf_empty_urls_allowed(
        self,
        mock_free_user,
        override_free_user,
    ):
        """
        Test: Empty URLs (blank pages) are allowed.

        Given: image_urls contains empty strings
        When: POST /api/v2/user/generate/pdf/pdf
        Then: Succeeds with 200 status
        """
        # Arrange
        mock_service = MagicMock()
        fake_pdf = BytesIO(b"%PDF-1.4\nfake")
        mock_service.generate_pdf = AsyncMock(return_value=fake_pdf)

        app.dependency_overrides[get_pdf_service] = lambda: mock_service

        # Act
        response = client.post(
            "/api/v2/user/generate/pdf/pdf",
            json={
                "project_id": VALID_PROJECT_ID,
                "current_hash": "abc123",
                "image_urls": ["", "", ALLOWED_URL],  # Blank pages
                "texts": ["", "", "Page 3"],
            },
        )

        # Assert
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"

        # Verify blank pages passed to Service
        call_kwargs = mock_service.generate_pdf.call_args.kwargs
        assert call_kwargs["image_urls"] == ["", "", ALLOWED_URL]

        app.dependency_overrides.clear()
