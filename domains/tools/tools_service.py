"""Tools Service - Business logic for utility tools (v3.0.0).

@module domains.tools.tools_service
@version 3.0.0

Changes:
- v3.0.0: DDD architecture upgrade - Service layer extraction
  - Migrated all business logic from API layer to Service
  - Added project_id validation
  - Added PDF preview generation logic
  - Added OCR processing logic with credit management
  - Improved separation of concerns
"""

import logging
import re
import uuid
from typing import Optional, List, Dict, Any

from fastapi import HTTPException, UploadFile

logger = logging.getLogger(__name__)


# ==========================================
# Constants (v3.0.0)
# ==========================================

# UUID validation pattern
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE
)

# OCR cost in credits
OCR_COST = 5

# Allowed file types for OCR
ALLOWED_OCR_TYPES = [
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "application/pdf",
]


# ==========================================
# Service Class
# ==========================================

class ToolsService:
    """Service for utility tools business logic (v3.0.0)."""

    def __init__(
        self,
        credit_repository,
        asset_repository,
        storage_client,
        ocr_processor,
        access_control,
    ):
        """
        Initialize ToolsService.

        Args:
            credit_repository: Credit operations repository
            asset_repository: Asset operations repository
            storage_client: Storage client (Supabase)
            ocr_processor: OCR processing service
            access_control: Access control service
        """
        self.credit_repository = credit_repository
        self.asset_repository = asset_repository
        self.storage = storage_client
        self.ocr_processor = ocr_processor
        self.access_control = access_control

    # ==========================================
    # Validation
    # ==========================================

    def validate_project_id(self, project_id: Optional[str]) -> None:
        """
        Validate optional project_id is UUID format.

        Args:
            project_id: Optional project UUID string

        Raises:
            HTTPException: 400 if project_id is invalid format
        """
        if project_id is not None and not UUID_PATTERN.match(project_id):
            raise HTTPException(400, "Invalid project ID format")

    # ==========================================
    # PDF Preview
    # ==========================================

    async def process_pdf_preview(
        self,
        file: UploadFile,
        user: dict,
    ) -> Dict[str, Any]:
        """
        Convert PDF to page preview images.

        Pro only feature. Returns thumbnail URLs for each page.

        Args:
            file: Uploaded PDF file
            user: User dict with id, tier

        Returns:
            Dict with success, preview_id, total_pages, pages

        Raises:
            HTTPException: 403 if not Pro, 400 if invalid file, 500 if processing fails
        """
        # Check tier access
        if user.get("tier", "free").lower() != "pro":
            raise HTTPException(403, "Upgrade to Teacher Pro to use Smart Scan")

        # Validate file type
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(400, "Only PDF files are supported")

        try:
            import fitz  # PyMuPDF

            # Read file
            contents = await file.read()

            # Check file size (5MB limit)
            if len(contents) > 5 * 1024 * 1024:
                raise HTTPException(400, "File too large. Maximum size is 5MB")

            # Open PDF
            pdf_doc = fitz.open(stream=contents, filetype="pdf")
            total_pages = len(pdf_doc)

            # Check page limit (20 pages)
            if total_pages > 20:
                raise HTTPException(
                    400,
                    f"PDF has too many pages ({total_pages}). Maximum is 20"
                )

            # Generate preview ID
            preview_id = uuid.uuid4().hex[:8]

            # Process each page
            pages = []
            for page_num in range(total_pages):
                page = pdf_doc[page_num]
                mat = fitz.Matrix(150 / 72, 150 / 72)  # 150 DPI
                pix = page.get_pixmap(matrix=mat)
                img_bytes = pix.tobytes("png")

                # Upload to storage
                filename = f"{user['id']}/previews/{preview_id}/page_{page_num + 1}.png"
                preview_url = await self._upload_preview_image(
                    filename,
                    img_bytes,
                )

                pages.append({
                    "page_number": page_num + 1,
                    "preview_url": preview_url,
                    "width": pix.width,
                    "height": pix.height,
                })

            pdf_doc.close()

            return {
                "success": True,
                "preview_id": preview_id,
                "total_pages": total_pages,
                "pages": pages,
            }

        except fitz.FileDataError:
            raise HTTPException(400, "Invalid or corrupted PDF file")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"PDF Preview Error: {e}")
            raise HTTPException(500, f"Failed to process PDF: {str(e)}")

    async def _upload_preview_image(
        self,
        filename: str,
        img_bytes: bytes,
    ) -> Optional[str]:
        """
        Upload preview image to storage.

        Args:
            filename: Storage path
            img_bytes: Image bytes

        Returns:
            Public URL or None if upload fails
        """
        try:
            from config import BUCKET_NAME

            self.storage.storage.from_(BUCKET_NAME).upload(
                path=filename,
                file=img_bytes,
                file_options={"content-type": "image/png"},
            )
            return self.storage.storage.from_(BUCKET_NAME).get_public_url(filename)
        except Exception as e:
            logger.warning(f"Failed to upload preview: {e}")
            return None

    # ==========================================
    # OCR Processing
    # ==========================================

    async def process_ocr(
        self,
        file: UploadFile,
        project_id: Optional[str],
        user: dict,
        timezone: str,
        is_trial: bool,
    ) -> Dict[str, Any]:
        """
        Advanced OCR endpoint - detects tables, text, and images.

        Pro or trial users only. Costs 5 credits.

        Args:
            file: Uploaded file (image or PDF)
            project_id: Optional project UUID
            user: User dict with id, tier
            timezone: User timezone
            is_trial: Whether user is in trial period

        Returns:
            Dict with success, text, tables, images, credits_used, balance

        Raises:
            HTTPException: 403 if no access, 400 if invalid file,
                          402 if insufficient credits, 500 if processing fails
        """
        # Validate project_id format
        self.validate_project_id(project_id)

        # Check OCR permission
        if not self.access_control.can_use_ocr(user, is_trial=is_trial):
            raise HTTPException(
                403,
                "Upgrade to Teacher Pro to use Smart Scan (or available during trial period)"
            )

        # Validate file type BEFORE charging credits
        if file.content_type not in ALLOWED_OCR_TYPES:
            raise HTTPException(
                400,
                f"Unsupported file type: {file.content_type}"
            )

        # Read file
        contents = await file.read()

        # Check file size (10MB limit)
        if len(contents) > 10 * 1024 * 1024:
            raise HTTPException(400, "File too large. Maximum size is 10MB")

        # Deduct credits after all validations pass
        result = await self.credit_repository.deduct_credits(
            user["id"],
            OCR_COST,
            "ocr",
            "OCR processing"
        )
        if not result.get("success", True):
            if "INSUFFICIENT" in str(result.get("error", "")):
                raise HTTPException(402, "Insufficient credits for OCR")

        try:
            # Process OCR
            ocr_result = await self.ocr_processor.process_ocr(
                contents,
                file.content_type,
                file.filename,
            )

            # Save extracted images as assets
            if ocr_result.get("images"):
                for img_url in ocr_result["images"]:
                    await self.asset_repository.save_asset(
                        user["id"],
                        img_url,
                        "ocr_extracted",
                        project_id,
                        tz=timezone,
                    )

            return {
                "success": True,
                "text": ocr_result.get("text", ""),
                "tables": ocr_result.get("tables", []),
                "images": ocr_result.get("images", []),
                "credits_used": OCR_COST,
                "balance": result.get("total", 0),
            }

        except Exception as e:
            # Refund credits on OCR processing failure
            await self._refund_ocr_credits(user["id"], e)
            logger.error(f"OCR Error: {e}")
            raise HTTPException(500, f"OCR processing failed: {str(e)}")

    async def _refund_ocr_credits(
        self,
        user_id: str,
        error: Exception,
    ) -> None:
        """
        Refund credits on OCR processing failure.

        Args:
            user_id: User ID
            error: Exception that caused the failure
        """
        try:
            await self.credit_repository.add_credits(
                user_id,
                OCR_COST,
                f"OCR failed: {str(error)[:50]}",
                "refund"
            )
            logger.info(f"Refunded {OCR_COST} credits for failed OCR: {user_id}")
        except Exception as refund_error:
            logger.error(f"Failed to refund credits: {refund_error}")
