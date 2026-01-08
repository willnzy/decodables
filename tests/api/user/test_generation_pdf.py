"""
Test generation_pdf API endpoints.

@version 2.0.0

Tests for POST /api/v2/user/generate/pdf/pdf endpoint with security validations:
- GP-P0-1/2: SSRF protection and URL count limits
- GP-HIGH-1: UUID validation for project_id
- GP-HIGH-2: Text length validation
- GP-MEDIUM-1: Hash format validation
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from io import BytesIO

from api.schemas.user.generation import (
    PdfGenRequest,
    is_allowed_url,
    ALLOWED_URL_DOMAINS,
    UUID_PATTERN,
)


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
