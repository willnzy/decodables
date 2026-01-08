"""
Test api/user/tools.py - Utility Tools API

Endpoints:
- POST /api/v2/user/tools/pdf-preview - Convert PDF to preview images
- POST /api/v2/user/tools/ocr - OCR processing

Created: 2026-01-07
Updated: 2026-01-08 (Complete rewrite with proper mocking of external dependencies)
"""

import pytest
import io
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock, Mock
from fastapi.testclient import TestClient

# Critical: Mock external dependencies BEFORE any imports
# 1. Rate limiter bypass
_rate_limiter_patcher = patch('infrastructure.rate_limiter.limiter.limit', lambda rate: lambda func: func)
_rate_limiter_patcher.start()

# 2. Mock fitz (PyMuPDF) - must be done before api.user.tools import
import sys

# Create fitz mock with FileDataError exception class
_fitz_mock = Mock()
# FileDataError must inherit from Exception to be catchable
_fitz_mock.FileDataError = type('FileDataError', (Exception,), {})
sys.modules['fitz'] = _fitz_mock

# 3. Mock OCR service - must be done before api.user.tools import
mock_ocr_module = Mock()
mock_ocr_module.process_ocr = AsyncMock()
sys.modules['shared.ai.ocr_service'] = mock_ocr_module

from app import app
from dependencies import get_current_user

client = TestClient(app)


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def mock_user_pro():
    """Mock Pro user."""
    return {
        "id": "user_123",
        "email": "test@example.com",
        "tier": "pro",
        "created_at": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
    }


@pytest.fixture
def mock_user_free():
    """Mock Free user."""
    return {
        "id": "user_456",
        "email": "free@example.com",
        "tier": "free",
        "created_at": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
    }


@pytest.fixture
def mock_user_trial():
    """Mock Free user in trial period."""
    return {
        "id": "user_789",
        "email": "trial@example.com",
        "tier": "free",
        "created_at": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),  # Within 7-day trial
    }


@pytest.fixture
def override_get_current_user(mock_user_pro):
    """Override authentication dependency."""
    async def _get_current_user():
        return mock_user_pro
    app.dependency_overrides[get_current_user] = _get_current_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_pdf_file():
    """Create a mock PDF file."""
    pdf_content = b"%PDF-1.4\ntest content\n%%EOF"
    return ("test.pdf", io.BytesIO(pdf_content), "application/pdf")


@pytest.fixture
def mock_image_file():
    """Create a mock image file for OCR."""
    # 1x1 PNG image
    png_content = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01'
        b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    return ("test.png", io.BytesIO(png_content), "image/png")


# ==========================================
# Tests - POST /api/v2/user/tools/pdf-preview
# ==========================================

class TestPdfPreview:
    """Test POST /api/v2/user/tools/pdf-preview endpoint."""

    @patch('shared.ai.image_generator.supabase')
    def test_pdf_preview_success(self, mock_storage, override_get_current_user, mock_pdf_file):
        """Test successful PDF preview generation."""
        # Get the mocked fitz module from sys.modules
        import sys
        fitz_module = sys.modules['fitz']

        # Mock PyMuPDF document
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 2
        mock_doc.close = MagicMock()
        mock_page = MagicMock()
        mock_pix = MagicMock()
        mock_pix.width = 800
        mock_pix.height = 600
        mock_pix.tobytes.return_value = b'fake_png_data'
        mock_page.get_pixmap.return_value = mock_pix
        mock_doc.__getitem__.return_value = mock_page
        fitz_module.open.return_value = mock_doc

        # Mock storage
        mock_storage.storage.from_.return_value.upload.return_value = None
        mock_storage.storage.from_.return_value.get_public_url.return_value = "https://cdn.example.com/preview.png"

        filename, content, content_type = mock_pdf_file
        response = client.post(
            "/api/v2/user/tools/pdf-preview",
            files={"file": (filename, content, content_type)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["total_pages"] == 2
        assert len(data["pages"]) == 2
        assert data["pages"][0]["page_number"] == 1
        assert data["pages"][0]["width"] == 800
        assert data["pages"][0]["height"] == 600

    def test_pdf_preview_free_user_forbidden(self, mock_user_free):
        """Test PDF preview requires Pro tier."""
        async def _get_free_user():
            return mock_user_free
        app.dependency_overrides[get_current_user] = _get_free_user

        pdf_content = b"%PDF-1.4\ntest"
        response = client.post(
            "/api/v2/user/tools/pdf-preview",
            files={"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")},
        )
        app.dependency_overrides.clear()

        assert response.status_code == 403
        data = response.json()
        assert "Upgrade to Teacher Pro" in data["message"]

    def test_pdf_preview_invalid_file_type(self, override_get_current_user):
        """Test PDF preview rejects non-PDF files."""
        response = client.post(
            "/api/v2/user/tools/pdf-preview",
            files={"file": ("test.txt", io.BytesIO(b"not a pdf"), "text/plain")},
        )

        assert response.status_code == 400
        data = response.json()
        assert "Only PDF files" in data["message"]

    def test_pdf_preview_file_too_large(self, override_get_current_user):
        """Test PDF preview rejects files over 5MB."""
        # Create content over 5MB
        large_content = b"x" * (6 * 1024 * 1024)
        response = client.post(
            "/api/v2/user/tools/pdf-preview",
            files={"file": ("large.pdf", io.BytesIO(large_content), "application/pdf")},
        )

        assert response.status_code == 400
        data = response.json()
        assert "too large" in data["message"].lower()

    def test_pdf_preview_too_many_pages(self, override_get_current_user):
        """Test PDF preview rejects files with over 20 pages."""
        import sys
        fitz_module = sys.modules['fitz']

        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 25  # 25 pages
        fitz_module.open.return_value = mock_doc

        pdf_content = b"%PDF-1.4\ntest"
        response = client.post(
            "/api/v2/user/tools/pdf-preview",
            files={"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")},
        )

        assert response.status_code == 400
        data = response.json()
        assert "too many pages" in data["message"].lower()
        assert "25" in data["message"]

    def test_pdf_preview_corrupted_pdf(self, override_get_current_user):
        """Test PDF preview handles corrupted PDF files."""
        import sys
        fitz_module = sys.modules['fitz']

        # Use the FileDataError already defined in fitz_module
        fitz_module.open.side_effect = fitz_module.FileDataError("Invalid PDF")

        pdf_content = b"corrupted pdf data"
        response = client.post(
            "/api/v2/user/tools/pdf-preview",
            files={"file": ("bad.pdf", io.BytesIO(pdf_content), "application/pdf")},
        )

        assert response.status_code == 400
        data = response.json()
        assert "Invalid or corrupted PDF" in data["message"]


# ==========================================
# Tests - POST /api/v2/user/tools/ocr
# ==========================================

class TestOcrTool:
    """Test POST /api/v2/user/tools/ocr endpoint."""

    @patch('api.user.tools.SupabaseAssetRepository')
    @patch('api.user.tools.SupabaseCreditRepository')
    def test_ocr_success_pro_user(
        self,
        mock_credit_repo_class,
        mock_asset_repo_class,
        override_get_current_user,
        mock_image_file,
    ):
        """Test successful OCR processing for Pro user."""
        # Get mocked OCR service from sys.modules
        import sys
        ocr_module = sys.modules['shared.ai.ocr_service']

        # Mock credit deduction
        mock_credit_repo = AsyncMock()
        mock_credit_repo.deduct_credits.return_value = {"success": True, "total": 95}
        mock_credit_repo_class.return_value = mock_credit_repo

        # Mock OCR result
        ocr_module.process_ocr.return_value = {
            "text": "Extracted text from image",
            "tables": [{"row": 1, "col": 1, "text": "Cell 1"}],
            "images": ["https://cdn.example.com/extracted1.png"],
        }

        # Mock asset repository
        mock_asset_repo = AsyncMock()
        mock_asset_repo.save_asset.return_value = None
        mock_asset_repo_class.return_value = mock_asset_repo

        filename, content, content_type = mock_image_file
        # v2.1.0: project_id must be valid UUID format
        response = client.post(
            "/api/v2/user/tools/ocr",
            files={"file": (filename, content, content_type)},
            data={"project_id": "12345678-1234-1234-1234-123456789abc"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["text"] == "Extracted text from image"
        assert data["credits_used"] == 5
        assert data["balance"] == 95
        assert len(data["tables"]) == 1
        assert len(data["images"]) == 1

        # Verify credit deduction
        mock_credit_repo.deduct_credits.assert_called_once_with(
            "user_123", 5, "ocr", "OCR processing"
        )

    @patch('config.TRIAL_DAYS', 7)
    @patch('api.user.tools.SupabaseAssetRepository')
    @patch('api.user.tools.SupabaseCreditRepository')
    def test_ocr_success_trial_user(
        self,
        mock_credit_repo_class,
        mock_asset_repo_class,
        mock_user_trial,
        mock_image_file,
    ):
        """Test successful OCR processing for trial user."""
        # Get mocked OCR service
        import sys
        ocr_module = sys.modules['shared.ai.ocr_service']

        async def _get_trial_user():
            return mock_user_trial
        app.dependency_overrides[get_current_user] = _get_trial_user

        # Mock credit deduction
        mock_credit_repo = AsyncMock()
        mock_credit_repo.deduct_credits.return_value = {"success": True, "total": 45}
        mock_credit_repo_class.return_value = mock_credit_repo

        # Mock OCR result
        ocr_module.process_ocr.return_value = {
            "text": "Trial OCR text",
            "tables": [],
            "images": [],
        }

        # Mock asset repository
        mock_asset_repo = AsyncMock()
        mock_asset_repo_class.return_value = mock_asset_repo

        filename, content, content_type = mock_image_file
        response = client.post(
            "/api/v2/user/tools/ocr",
            files={"file": (filename, content, content_type)},
        )
        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["credits_used"] == 5

    def test_ocr_free_user_forbidden(self, mock_user_free):
        """Test OCR requires Pro tier or trial period."""
        async def _get_free_user():
            return mock_user_free
        app.dependency_overrides[get_current_user] = _get_free_user

        response = client.post(
            "/api/v2/user/tools/ocr",
            files={"file": ("test.png", io.BytesIO(b"fake"), "image/png")},
        )
        app.dependency_overrides.clear()

        assert response.status_code == 403
        data = response.json()
        assert "Upgrade to Teacher Pro" in data["message"]

    @patch('api.user.tools.SupabaseCreditRepository')
    def test_ocr_insufficient_credits(self, mock_credit_repo_class, override_get_current_user):
        """Test OCR handles insufficient credits."""
        mock_credit_repo = AsyncMock()
        mock_credit_repo.deduct_credits.return_value = {
            "success": False,
            "error": "INSUFFICIENT CREDITS"
        }
        mock_credit_repo_class.return_value = mock_credit_repo

        response = client.post(
            "/api/v2/user/tools/ocr",
            files={"file": ("test.png", io.BytesIO(b"fake"), "image/png")},
        )

        assert response.status_code == 402
        data = response.json()
        assert "Insufficient credits" in data["message"]

    def test_ocr_invalid_file_type(self, override_get_current_user):
        """Test OCR rejects unsupported file types."""
        response = client.post(
            "/api/v2/user/tools/ocr",
            files={"file": ("test.txt", io.BytesIO(b"text file"), "text/plain")},
        )

        assert response.status_code == 400
        data = response.json()
        assert "Unsupported file type" in data["message"]

    def test_ocr_file_too_large(self, override_get_current_user):
        """Test OCR rejects files over 10MB."""
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB
        response = client.post(
            "/api/v2/user/tools/ocr",
            files={"file": ("large.png", io.BytesIO(large_content), "image/png")},
        )

        assert response.status_code == 400
        data = response.json()
        assert "too large" in data["message"].lower()

    @patch('api.user.tools.SupabaseCreditRepository')
    def test_ocr_processing_error(
        self,
        mock_credit_repo_class,
        override_get_current_user,
        mock_image_file,
    ):
        """Test OCR handles processing errors."""
        # Get mocked OCR service
        import sys
        ocr_module = sys.modules['shared.ai.ocr_service']

        # Mock credit deduction success
        mock_credit_repo = AsyncMock()
        mock_credit_repo.deduct_credits.return_value = {"success": True, "total": 95}
        mock_credit_repo_class.return_value = mock_credit_repo

        # Mock OCR failure
        ocr_module.process_ocr.side_effect = Exception("OCR service unavailable")

        filename, content, content_type = mock_image_file
        response = client.post(
            "/api/v2/user/tools/ocr",
            files={"file": (filename, content, content_type)},
        )

        assert response.status_code == 500
        data = response.json()
        assert "OCR processing failed" in data["message"]


# ==========================================
# Tests - Security Validations (v2.1.0)
# ==========================================

class TestSecurityValidations:
    """Test security validation improvements in v2.1.0."""

    def test_ocr_invalid_project_id_format(self, override_get_current_user):
        """Test OCR rejects invalid project_id format (TL-MEDIUM-1)."""
        response = client.post(
            "/api/v2/user/tools/ocr",
            files={"file": ("test.png", io.BytesIO(b"fake"), "image/png")},
            data={"project_id": "not-a-valid-uuid"},
        )

        assert response.status_code == 400
        data = response.json()
        assert "Invalid project ID format" in data["message"]

    @patch('api.user.tools.SupabaseCreditRepository')
    def test_ocr_valid_uuid_project_id(
        self,
        mock_credit_repo_class,
        override_get_current_user,
    ):
        """Test OCR accepts valid UUID project_id."""
        import sys
        ocr_module = sys.modules['shared.ai.ocr_service']

        # Reset any previous side_effect
        ocr_module.process_ocr.side_effect = None

        mock_credit_repo = AsyncMock()
        mock_credit_repo.deduct_credits.return_value = {"success": True, "total": 95}
        mock_credit_repo_class.return_value = mock_credit_repo

        ocr_module.process_ocr.return_value = {
            "text": "Test",
            "tables": [],
            "images": [],
        }

        # Valid UUID format
        valid_uuid = "12345678-1234-1234-1234-123456789abc"
        response = client.post(
            "/api/v2/user/tools/ocr",
            files={"file": ("test.png", io.BytesIO(b"fake"), "image/png")},
            data={"project_id": valid_uuid},
        )

        assert response.status_code == 200

    @patch('api.user.tools.SupabaseCreditRepository')
    def test_ocr_no_charge_on_validation_failure(
        self,
        mock_credit_repo_class,
        override_get_current_user,
    ):
        """Test that credits are NOT charged when file validation fails (TL-LOW-1)."""
        mock_credit_repo = AsyncMock()
        mock_credit_repo_class.return_value = mock_credit_repo

        # Send unsupported file type
        response = client.post(
            "/api/v2/user/tools/ocr",
            files={"file": ("test.exe", io.BytesIO(b"fake"), "application/x-executable")},
        )

        assert response.status_code == 400
        # Credit deduction should NOT be called
        mock_credit_repo.deduct_credits.assert_not_called()

    @patch('api.user.tools.SupabaseCreditRepository')
    def test_ocr_refund_on_processing_failure(
        self,
        mock_credit_repo_class,
        override_get_current_user,
        mock_image_file,
    ):
        """Test that credits are refunded when OCR processing fails (TL-LOW-2)."""
        import sys
        ocr_module = sys.modules['shared.ai.ocr_service']

        mock_credit_repo = AsyncMock()
        mock_credit_repo.deduct_credits.return_value = {"success": True, "total": 95}
        mock_credit_repo.add_credits.return_value = {"success": True}
        mock_credit_repo_class.return_value = mock_credit_repo

        # Mock OCR failure
        ocr_module.process_ocr.side_effect = Exception("Service unavailable")

        filename, content, content_type = mock_image_file
        response = client.post(
            "/api/v2/user/tools/ocr",
            files={"file": (filename, content, content_type)},
        )

        assert response.status_code == 500
        # Verify refund was called
        mock_credit_repo.add_credits.assert_called_once()
        call_args = mock_credit_repo.add_credits.call_args
        assert call_args[0][0] == "user_123"  # user_id
        assert call_args[0][1] == 5  # OCR_COST
        assert call_args[0][3] == "refund"  # transaction_type
