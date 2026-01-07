"""Tools API - Utility tools endpoints (v2).

@module api.user.tools
@version 2.0.0

Endpoints:
- POST /api/v2/user/tools/pdf-preview - Convert PDF to preview images
- POST /api/v2/user/tools/ocr - OCR processing
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from pydantic import BaseModel

from dependencies import get_current_user
from infrastructure.rate_limiter import limiter
from infrastructure.repositories.credit_repository import SupabaseCreditRepository
from infrastructure.repositories.asset_repository import SupabaseAssetRepository
from infrastructure.logging.activity_logger import log_activity
from core.database import get_database_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/user/tools", tags=["user-tools-v2"])


# ==========================================
# Response Models
# ==========================================

class PagePreview(BaseModel):
    """Single page preview."""
    page_number: int
    preview_url: Optional[str] = None
    width: int
    height: int


class PdfPreviewResponse(BaseModel):
    """PDF preview response."""
    success: bool
    preview_id: str
    total_pages: int
    pages: List[PagePreview]


class OcrResponse(BaseModel):
    """OCR response."""
    success: bool
    text: str
    tables: List[Dict[str, Any]]
    images: List[str]
    credits_used: int
    balance: int


# ==========================================
# Endpoints
# ==========================================

@router.post("/pdf-preview")
@limiter.limit("10/minute")
async def pdf_preview(
    request: Request,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
) -> PdfPreviewResponse:
    """
    Convert PDF to page preview images.

    Pro only feature. Returns thumbnail URLs for each page.
    """
    import fitz
    from shared.ai.image_generator import supabase as storage_supabase, BUCKET_NAME

    if user.get("tier", "free").lower() != "pro":
        raise HTTPException(403, "Upgrade to Teacher Pro to use Smart Scan")

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")

    try:
        contents = await file.read()

        if len(contents) > 5 * 1024 * 1024:
            raise HTTPException(400, "File too large. Maximum size is 5MB")

        pdf_doc = fitz.open(stream=contents, filetype="pdf")
        total_pages = len(pdf_doc)

        if total_pages > 20:
            raise HTTPException(400, f"PDF has too many pages ({total_pages}). Maximum is 20")

        pages = []
        preview_id = uuid.uuid4().hex[:8]

        for page_num in range(total_pages):
            page = pdf_doc[page_num]
            mat = fitz.Matrix(150 / 72, 150 / 72)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")

            filename = f"{user['id']}/previews/{preview_id}/page_{page_num + 1}.png"

            preview_url = None
            if storage_supabase:
                try:
                    storage_supabase.storage.from_(BUCKET_NAME).upload(
                        path=filename,
                        file=img_bytes,
                        file_options={"content-type": "image/png"},
                    )
                    preview_url = storage_supabase.storage.from_(BUCKET_NAME).get_public_url(filename)
                except Exception as e:
                    logger.warning(f"Failed to upload preview: {e}")

            pages.append(PagePreview(
                page_number=page_num + 1,
                preview_url=preview_url,
                width=pix.width,
                height=pix.height,
            ))

        pdf_doc.close()

        return PdfPreviewResponse(
            success=True,
            preview_id=preview_id,
            total_pages=total_pages,
            pages=pages,
        )

    except fitz.FileDataError:
        raise HTTPException(400, "Invalid or corrupted PDF file")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF Preview Error: {e}")
        raise HTTPException(500, f"Failed to process PDF: {str(e)}")


@router.post("/ocr")
@limiter.limit("10/minute")
async def ocr_tool(
    request: Request,
    file: UploadFile = File(...),
    project_id: Optional[str] = Form(None),
    user: dict = Depends(get_current_user),
) -> OcrResponse:
    """
    Advanced OCR endpoint - detects tables, text, and images.

    Pro or trial users only. Costs 5 credits.
    """
    from shared.ai.ocr_service import process_ocr
    from domains.shared.access_control import AccessControl
    from timezone_utils import get_request_timezone
    from config import TRIAL_DAYS

    # Check if user is in trial period
    is_trial = False
    user_tier = (user.get("tier") or "free").lower()
    if user_tier == "free":
        created_at = user.get("created_at")
        if created_at:
            try:
                if isinstance(created_at, str):
                    created_at_str = created_at.replace("Z", "+00:00")
                    registration_date = datetime.fromisoformat(created_at_str)
                else:
                    registration_date = created_at
                if registration_date.tzinfo is None:
                    registration_date = registration_date.replace(tzinfo=timezone.utc)
                days_since = (datetime.now(timezone.utc) - registration_date).total_seconds() / (24 * 3600)
                is_trial = days_since <= TRIAL_DAYS
            except (ValueError, TypeError):
                pass

    # Check OCR permission
    if not AccessControl.can_use_ocr(user, is_trial=is_trial):
        raise HTTPException(403, "Upgrade to Teacher Pro to use Smart Scan (or available during trial period)")

    OCR_COST = 5
    credit_repo = SupabaseCreditRepository(get_database_client())
    result = await credit_repo.deduct_credits(user["id"], OCR_COST, "ocr", "OCR processing")
    if not result.get("success", True):
        if "INSUFFICIENT" in str(result.get("error", "")):
            raise HTTPException(402, "Insufficient credits for OCR")

    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp", "application/pdf"]
    if file.content_type not in allowed_types:
        raise HTTPException(400, f"Unsupported file type: {file.content_type}")

    contents = await file.read()

    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(400, "File too large. Maximum size is 10MB")

    try:
        ocr_result = await process_ocr(contents, file.content_type, file.filename)

        log_activity(user["id"], "ocr_process", {
            "filename": file.filename,
            "project_id": project_id,
        })

        if ocr_result.get("images"):
            tz = get_request_timezone(request, user_id=user.get("id"))
            asset_repo = SupabaseAssetRepository(get_database_client())
            for img_url in ocr_result["images"]:
                await asset_repo.save_asset(user["id"], img_url, "ocr_extracted", project_id, timezone=tz)

        return OcrResponse(
            success=True,
            text=ocr_result.get("text", ""),
            tables=ocr_result.get("tables", []),
            images=ocr_result.get("images", []),
            credits_used=OCR_COST,
            balance=result.get("total", 0),
        )

    except Exception as e:
        logger.error(f"OCR Error: {e}")
        raise HTTPException(500, f"OCR processing failed: {str(e)}")
