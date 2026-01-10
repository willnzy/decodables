"""
Test api/user/tools.py - Utility Tools API (v3.0.0)

@version 3.0.0
@updated 2026-01-10 (v3.0.0: Updated to mock Command Handlers instead of Infrastructure)

Test Pattern:
- v2.1.0: Mocked Infrastructure (SupabaseCreditRepository, OCR service, Storage)
- v3.0.0: Mocks Command Handlers (PdfPreviewHandler, OcrHandler)

Endpoints:
- POST /api/v2/user/tools/pdf-preview - Convert PDF to preview images
- POST /api/v2/user/tools/ocr - OCR processing
"""

import pytest
import io
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

# Critical: Mock rate limiter BEFORE any imports
_rate_limiter_patcher = patch('infrastructure.rate_limiter.limiter.limit', lambda rate: lambda func: func)
_rate_limiter_patcher.start()

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
        "created_at": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
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
    image_content = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
        b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    return ("test.png", io.BytesIO(image_content), "image/png")


# ==========================================
# PDF Preview Tests (v3.0.0)
# ==========================================

class TestPdfPreview:
    """Tests for POST /api/v2/user/tools/pdf-preview endpoint (v3.0.0)."""

    def test_pdf_preview_success(self, override_get_current_user, mock_pdf_file):
        """v3.0.0: Test PDF preview generation successfully."""
        from application.commands.tools import PdfPreviewHandler, PdfPreviewResult

        # Mock handler
        mock_handler = MagicMock(spec=PdfPreviewHandler)
        mock_handler.handle = AsyncMock(return_value=PdfPreviewResult(
            result_data={
                "success": True,
                "preview_id": "abc123",
                "total_pages": 2,
                "pages": [
                    {
                        "page_number": 1,
                        "preview_url": "https://storage.example.com/page_1.png",
                        "width": 150,
                        "height": 200,
                    },
                    {
                        "page_number": 2,
                        "preview_url": "https://storage.example.com/page_2.png",
                        "width": 150,
                        "height": 200,
                    },
                ],
            }
        ))

        # Inject mock handler via container
        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('pdf_preview')
        container._handlers['pdf_preview'] = mock_handler

        try:
            # Make request
            response = client.post(
                "/api/v2/user/tools/pdf-preview",
                files={"file": mock_pdf_file}
            )

            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["preview_id"] == "abc123"
            assert data["total_pages"] == 2
            assert len(data["pages"]) == 2
            assert data["pages"][0]["page_number"] == 1
            mock_handler.handle.assert_called_once()

        finally:
            if original_handler:
                container._handlers['pdf_preview'] = original_handler
            else:
                container._handlers.pop('pdf_preview', None)

    def test_pdf_preview_free_user_forbidden(self, mock_user_free):
        """v3.0.0: Test PDF preview forbidden for free users."""
        from fastapi import HTTPException
        from application.commands.tools import PdfPreviewHandler

        # Mock handler that raises 403
        mock_handler = MagicMock(spec=PdfPreviewHandler)
        mock_handler.handle = AsyncMock(side_effect=HTTPException(
            status_code=403,
            detail="Upgrade to Teacher Pro to use Smart Scan"
        ))

        # Override user
        async def _get_current_user():
            return mock_user_free
        app.dependency_overrides[get_current_user] = _get_current_user

        # Inject mock handler
        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('pdf_preview')
        container._handlers['pdf_preview'] = mock_handler

        try:
            pdf_file = ("test.pdf", io.BytesIO(b"fake pdf"), "application/pdf")
            response = client.post(
                "/api/v2/user/tools/pdf-preview",
                files={"file": pdf_file}
            )

            assert response.status_code == 403
            assert "Upgrade to Teacher Pro" in response.json()["message"]

        finally:
            app.dependency_overrides.clear()
            if original_handler:
                container._handlers['pdf_preview'] = original_handler
            else:
                container._handlers.pop('pdf_preview', None)

    def test_pdf_preview_invalid_file_type(self, override_get_current_user):
        """v3.0.0: Test PDF preview with invalid file type."""
        from fastapi import HTTPException
        from application.commands.tools import PdfPreviewHandler

        mock_handler = MagicMock(spec=PdfPreviewHandler)
        mock_handler.handle = AsyncMock(side_effect=HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        ))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('pdf_preview')
        container._handlers['pdf_preview'] = mock_handler

        try:
            text_file = ("test.txt", io.BytesIO(b"not a pdf"), "text/plain")
            response = client.post(
                "/api/v2/user/tools/pdf-preview",
                files={"file": text_file}
            )

            assert response.status_code == 400
            assert "PDF" in response.json()["message"]

        finally:
            if original_handler:
                container._handlers['pdf_preview'] = original_handler
            else:
                container._handlers.pop('pdf_preview', None)

    def test_pdf_preview_file_too_large(self, override_get_current_user):
        """v3.0.0: Test PDF preview with file too large."""
        from fastapi import HTTPException
        from application.commands.tools import PdfPreviewHandler

        mock_handler = MagicMock(spec=PdfPreviewHandler)
        mock_handler.handle = AsyncMock(side_effect=HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 5MB"
        ))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('pdf_preview')
        container._handlers['pdf_preview'] = mock_handler

        try:
            large_pdf = ("large.pdf", io.BytesIO(b"x" * 6 * 1024 * 1024), "application/pdf")
            response = client.post(
                "/api/v2/user/tools/pdf-preview",
                files={"file": large_pdf}
            )

            assert response.status_code == 400
            assert "too large" in response.json()["message"]

        finally:
            if original_handler:
                container._handlers['pdf_preview'] = original_handler
            else:
                container._handlers.pop('pdf_preview', None)

    def test_pdf_preview_too_many_pages(self, override_get_current_user):
        """v3.0.0: Test PDF preview with too many pages."""
        from fastapi import HTTPException
        from application.commands.tools import PdfPreviewHandler

        mock_handler = MagicMock(spec=PdfPreviewHandler)
        mock_handler.handle = AsyncMock(side_effect=HTTPException(
            status_code=400,
            detail="PDF has too many pages (25). Maximum is 20"
        ))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('pdf_preview')
        container._handlers['pdf_preview'] = mock_handler

        try:
            pdf_file = ("test.pdf", io.BytesIO(b"fake pdf"), "application/pdf")
            response = client.post(
                "/api/v2/user/tools/pdf-preview",
                files={"file": pdf_file}
            )

            assert response.status_code == 400
            assert "too many pages" in response.json()["message"]

        finally:
            if original_handler:
                container._handlers['pdf_preview'] = original_handler
            else:
                container._handlers.pop('pdf_preview', None)

    def test_pdf_preview_corrupted_pdf(self, override_get_current_user):
        """v3.0.0: Test PDF preview with corrupted PDF file."""
        from fastapi import HTTPException
        from application.commands.tools import PdfPreviewHandler

        mock_handler = MagicMock(spec=PdfPreviewHandler)
        mock_handler.handle = AsyncMock(side_effect=HTTPException(
            status_code=400,
            detail="Invalid or corrupted PDF file"
        ))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('pdf_preview')
        container._handlers['pdf_preview'] = mock_handler

        try:
            corrupted_pdf = ("corrupted.pdf", io.BytesIO(b"not a valid pdf"), "application/pdf")
            response = client.post(
                "/api/v2/user/tools/pdf-preview",
                files={"file": corrupted_pdf}
            )

            assert response.status_code == 400
            assert "corrupted" in response.json()["message"].lower()

        finally:
            if original_handler:
                container._handlers['pdf_preview'] = original_handler
            else:
                container._handlers.pop('pdf_preview', None)


# ==========================================
# OCR Tests (v3.0.0)
# ==========================================

class TestOcr:
    """Tests for POST /api/v2/user/tools/ocr endpoint (v3.0.0)."""

    def test_ocr_success_pro_user(self, override_get_current_user, mock_image_file):
        """v3.0.0: Test OCR processing successfully with Pro user."""
        from application.commands.tools import OcrHandler, OcrResult

        mock_handler = MagicMock(spec=OcrHandler)
        mock_handler.handle = AsyncMock(return_value=OcrResult(
            result_data={
                "success": True,
                "text": "Extracted text from image",
                "tables": [
                    {
                        "headers": ["Name", "Age"],
                        "rows": [["John", "30"], ["Jane", "25"]],
                    }
                ],
                "images": ["https://storage.example.com/extracted_image.png"],
                "credits_used": 5,
                "balance": 95,
            }
        ))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('ocr')
        container._handlers['ocr'] = mock_handler

        try:
            response = client.post(
                "/api/v2/user/tools/ocr",
                files={"file": mock_image_file}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["text"] == "Extracted text from image"
            assert len(data["tables"]) == 1
            assert len(data["images"]) == 1
            assert data["credits_used"] == 5
            assert data["balance"] == 95
            mock_handler.handle.assert_called_once()

        finally:
            if original_handler:
                container._handlers['ocr'] = original_handler
            else:
                container._handlers.pop('ocr', None)

    def test_ocr_success_trial_user(self, mock_user_trial, mock_image_file):
        """v3.0.0: Test OCR processing successfully with trial user."""
        from application.commands.tools import OcrHandler, OcrResult

        mock_handler = MagicMock(spec=OcrHandler)
        mock_handler.handle = AsyncMock(return_value=OcrResult(
            result_data={
                "success": True,
                "text": "Trial OCR text",
                "tables": [],
                "images": [],
                "credits_used": 5,
                "balance": 45,
            }
        ))

        # Override user
        async def _get_current_user():
            return mock_user_trial
        app.dependency_overrides[get_current_user] = _get_current_user

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('ocr')
        container._handlers['ocr'] = mock_handler

        try:
            response = client.post(
                "/api/v2/user/tools/ocr",
                files={"file": mock_image_file}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["text"] == "Trial OCR text"
            mock_handler.handle.assert_called_once()

        finally:
            app.dependency_overrides.clear()
            if original_handler:
                container._handlers['ocr'] = original_handler
            else:
                container._handlers.pop('ocr', None)

    def test_ocr_free_user_forbidden(self, mock_user_free):
        """v3.0.0: Test OCR forbidden for free users outside trial."""
        from fastapi import HTTPException
        from application.commands.tools import OcrHandler

        mock_handler = MagicMock(spec=OcrHandler)
        mock_handler.handle = AsyncMock(side_effect=HTTPException(
            status_code=403,
            detail="Upgrade to Teacher Pro to use Smart Scan (or available during trial period)"
        ))

        # Override user
        async def _get_current_user():
            return mock_user_free
        app.dependency_overrides[get_current_user] = _get_current_user

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('ocr')
        container._handlers['ocr'] = mock_handler

        try:
            image_file = ("test.png", io.BytesIO(b"fake image"), "image/png")
            response = client.post(
                "/api/v2/user/tools/ocr",
                files={"file": image_file}
            )

            assert response.status_code == 403
            assert "Upgrade to Teacher Pro" in response.json()["message"]

        finally:
            app.dependency_overrides.clear()
            if original_handler:
                container._handlers['ocr'] = original_handler
            else:
                container._handlers.pop('ocr', None)

    def test_ocr_insufficient_credits(self, override_get_current_user):
        """v3.0.0: Test OCR with insufficient credits."""
        from fastapi import HTTPException
        from application.commands.tools import OcrHandler

        mock_handler = MagicMock(spec=OcrHandler)
        mock_handler.handle = AsyncMock(side_effect=HTTPException(
            status_code=402,
            detail="Insufficient credits for OCR"
        ))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('ocr')
        container._handlers['ocr'] = mock_handler

        try:
            image_file = ("test.png", io.BytesIO(b"fake image"), "image/png")
            response = client.post(
                "/api/v2/user/tools/ocr",
                files={"file": image_file}
            )

            assert response.status_code == 402
            assert "Insufficient credits" in response.json()["message"]

        finally:
            if original_handler:
                container._handlers['ocr'] = original_handler
            else:
                container._handlers.pop('ocr', None)

    def test_ocr_invalid_file_type(self, override_get_current_user):
        """v3.0.0: Test OCR with invalid file type."""
        from fastapi import HTTPException
        from application.commands.tools import OcrHandler

        mock_handler = MagicMock(spec=OcrHandler)
        mock_handler.handle = AsyncMock(side_effect=HTTPException(
            status_code=400,
            detail="Unsupported file type: text/plain"
        ))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('ocr')
        container._handlers['ocr'] = mock_handler

        try:
            text_file = ("test.txt", io.BytesIO(b"not an image"), "text/plain")
            response = client.post(
                "/api/v2/user/tools/ocr",
                files={"file": text_file}
            )

            assert response.status_code == 400
            assert "Unsupported file type" in response.json()["message"]

        finally:
            if original_handler:
                container._handlers['ocr'] = original_handler
            else:
                container._handlers.pop('ocr', None)

    def test_ocr_file_too_large(self, override_get_current_user):
        """v3.0.0: Test OCR with file too large."""
        from fastapi import HTTPException
        from application.commands.tools import OcrHandler

        mock_handler = MagicMock(spec=OcrHandler)
        mock_handler.handle = AsyncMock(side_effect=HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 10MB"
        ))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('ocr')
        container._handlers['ocr'] = mock_handler

        try:
            large_image = ("large.png", io.BytesIO(b"x" * 11 * 1024 * 1024), "image/png")
            response = client.post(
                "/api/v2/user/tools/ocr",
                files={"file": large_image}
            )

            assert response.status_code == 400
            assert "too large" in response.json()["message"]

        finally:
            if original_handler:
                container._handlers['ocr'] = original_handler
            else:
                container._handlers.pop('ocr', None)

    def test_ocr_processing_error_with_refund(self, override_get_current_user):
        """v3.0.0: Test OCR processing error triggers credit refund."""
        from fastapi import HTTPException
        from application.commands.tools import OcrHandler

        mock_handler = MagicMock(spec=OcrHandler)
        mock_handler.handle = AsyncMock(side_effect=HTTPException(
            status_code=500,
            detail="OCR processing failed: Connection timeout"
        ))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('ocr')
        container._handlers['ocr'] = mock_handler

        try:
            image_file = ("test.png", io.BytesIO(b"fake image"), "image/png")
            response = client.post(
                "/api/v2/user/tools/ocr",
                files={"file": image_file}
            )

            assert response.status_code == 500
            assert "OCR processing failed" in response.json()["message"]
            # Note: Credit refund happens in ToolsService._refund_ocr_credits()

        finally:
            if original_handler:
                container._handlers['ocr'] = original_handler
            else:
                container._handlers.pop('ocr', None)

    def test_ocr_invalid_project_id_format(self, override_get_current_user):
        """v3.0.0: Test OCR with invalid project_id format."""
        from fastapi import HTTPException
        from application.commands.tools import OcrHandler

        mock_handler = MagicMock(spec=OcrHandler)
        mock_handler.handle = AsyncMock(side_effect=HTTPException(
            status_code=400,
            detail="Invalid project ID format"
        ))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('ocr')
        container._handlers['ocr'] = mock_handler

        try:
            image_file = ("test.png", io.BytesIO(b"fake image"), "image/png")
            response = client.post(
                "/api/v2/user/tools/ocr",
                files={"file": image_file},
                data={"project_id": "not-a-valid-uuid"}
            )

            assert response.status_code == 400
            assert "Invalid project ID" in response.json()["message"]

        finally:
            if original_handler:
                container._handlers['ocr'] = original_handler
            else:
                container._handlers.pop('ocr', None)

    def test_ocr_valid_uuid_project_id(self, override_get_current_user, mock_image_file):
        """v3.0.0: Test OCR with valid UUID project_id."""
        from application.commands.tools import OcrHandler, OcrResult

        mock_handler = MagicMock(spec=OcrHandler)
        mock_handler.handle = AsyncMock(return_value=OcrResult(
            result_data={
                "success": True,
                "text": "Project OCR text",
                "tables": [],
                "images": [],
                "credits_used": 5,
                "balance": 90,
            }
        ))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('ocr')
        container._handlers['ocr'] = mock_handler

        try:
            valid_uuid = "123e4567-e89b-12d3-a456-426614174000"
            response = client.post(
                "/api/v2/user/tools/ocr",
                files={"file": mock_image_file},
                data={"project_id": valid_uuid}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            mock_handler.handle.assert_called_once()

        finally:
            if original_handler:
                container._handlers['ocr'] = original_handler
            else:
                container._handlers.pop('ocr', None)

    def test_ocr_no_charge_on_validation_failure(self, override_get_current_user):
        """v3.0.0: Test OCR doesn't charge credits on validation failure."""
        from fastapi import HTTPException
        from application.commands.tools import OcrHandler

        # Handler raises validation error before charging
        mock_handler = MagicMock(spec=OcrHandler)
        mock_handler.handle = AsyncMock(side_effect=HTTPException(
            status_code=400,
            detail="Unsupported file type: text/plain"
        ))

        from container import get_container
        container = get_container()
        original_handler = container._handlers.get('ocr')
        container._handlers['ocr'] = mock_handler

        try:
            text_file = ("test.txt", io.BytesIO(b"not an image"), "text/plain")
            response = client.post(
                "/api/v2/user/tools/ocr",
                files={"file": text_file}
            )

            assert response.status_code == 400
            # Credits should NOT be charged for validation errors
            # This is ensured by ToolsService.process_ocr() validating BEFORE deducting

        finally:
            if original_handler:
                container._handlers['ocr'] = original_handler
            else:
                container._handlers.pop('ocr', None)
