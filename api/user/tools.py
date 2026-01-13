"""Tools API - Utility tools endpoints (v3).

@module api.user.tools
@version 3.0.0

Changes:
- v3.0.0: DDD architecture upgrade - CQRS Command pattern
  - Created ToolsService with PDF preview and OCR business logic
  - Added PdfPreviewHandler (Command Handler)
  - Added OcrHandler (Command Handler)
  - Eliminated direct infrastructure calls from API layer
  - Moved all validation and business logic to Service layer
  - Improved testability and maintainability

- v2.1.0: Security improvements
  - TL-MEDIUM-1: Added project_id UUID format validation
  - TL-LOW-1: Moved credit deduction after all validations
  - TL-LOW-2: Added credit refund on OCR processing failure

Endpoints:
- POST /api/v2/user/tools/pdf-preview - Convert PDF to preview images
- POST /api/v2/user/tools/ocr - OCR processing
"""

import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, Request, UploadFile, File, Form
from pydantic import BaseModel

from domains.identity.aggregates.user_profile import UserProfile
from dependencies import get_current_user
from container import get_container
from application.commands.tools import PdfPreviewCommand, OcrCommand
from infrastructure.rate_limiter import limiter
from infrastructure.logging.activity_logger import log_activity
from core.utils.timezone import get_request_timezone
from core.middleware import validate_file_size  # P3-005: File upload size validation
from domains.identity import is_user_in_trial
from config import TRIAL_DAYS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tools", tags=["user-tools-v3"])


# ==========================================
# Constants (v3.0.0)
# ==========================================

# OCR cost in credits
OCR_COST = 5


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
    file: UploadFile = Depends(validate_file_size),  # P3-005: File size validation (10MB limit)
    user: UserProfile = Depends(get_current_user),
) -> PdfPreviewResponse:
    """
    Convert PDF to page preview images.

    v3.0.0: Now uses PdfPreviewHandler (CQRS Command pattern).
    P3-005: Added 10MB file size limit via validate_file_size dependency.

    Pro only feature. Returns thumbnail URLs for each page.
    """
    container = get_container()
    handler = await container.pdf_preview_handler()

    command = PdfPreviewCommand(
        file=file,
        user=user,
    )

    result = await handler.handle(command)

    return PdfPreviewResponse(**result.result_data)


@router.post("/ocr")
@limiter.limit("10/minute")
async def ocr_tool(
    request: Request,
    file: UploadFile = Depends(validate_file_size),  # P3-005: File size validation (10MB limit)
    project_id: Optional[str] = Form(None),
    user: UserProfile = Depends(get_current_user),
) -> OcrResponse:
    """
    Advanced OCR endpoint - detects tables, text, and images.

    v3.0.0: Now uses OcrHandler (CQRS Command pattern).

    Pro or trial users only. Costs 5 credits.
    """
    # Check if user is in trial period
    is_trial = is_user_in_trial(user, trial_days=TRIAL_DAYS)

    # Get timezone for asset storage
    timezone = get_request_timezone(request, user_id=user.user_id)

    container = get_container()
    handler = await container.ocr_handler()

    command = OcrCommand(
        file=file,
        project_id=project_id,
        user=user,
        timezone=timezone,
        is_trial=is_trial,
    )

    result = await handler.handle(command)

    # Log activity
    log_activity(user.user_id, "ocr_process", {
        "filename": file.filename,
        "project_id": project_id,
    })

    return OcrResponse(**result.result_data)
