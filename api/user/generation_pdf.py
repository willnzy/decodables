"""
PDF Generation Router - PDF export endpoint

@module api.user.generation_pdf
@version 3.26

Changes:
- v3.26: GP-CRITICAL-1 fix - Added PdfGenerationService with DI
         - Created domains/generation/pdf_service.py
         - Migrated to DDD architecture: API → Service → Repository
         - Reduced API layer from 59 to 40 lines (-32%)
         - All business logic moved to PdfGenerationService
- v3.25: Security improvements
  - GP-P0-1/2: Added SSRF protection via PdfGenRequest validation
  - GP-HIGH-1: Added UUID validation for project_id
  - GP-HIGH-2: Added text length validation
  - GP-MEDIUM-1: Added hash format validation
  - GP-LOW-1: Sanitized user_id in activity logs

Endpoints:
- POST /api/v2/user/generate/pdf/pdf - PDF generation
"""

import logging
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse

from domains.identity.aggregates.user_profile import UserProfile
from core.database.dependencies import get_async_db
from infrastructure.repositories.project_repository import SupabaseProjectRepository
from infrastructure.rate_limiter import limiter
from domains.generation import PdfGenerationService
from domains.generation.pdf_service import (
    ProjectNotFoundException,
    PdfGenerationException,
)
from dependencies import get_current_user
from api.schemas.user.generation import PdfGenRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generate/pdf", tags=["generation-pdf-v2"])


# ==========================================
# Dependency Injection
# ==========================================

async def get_pdf_service(db = Depends(get_async_db)) -> PdfGenerationService:
    """Dependency injection factory for PdfGenerationService (AsyncClient)."""
    project_repo = SupabaseProjectRepository(db)
    return PdfGenerationService(project_repository=project_repo)


# ==========================================
# PDF Generation
# ==========================================

@router.post("/pdf")
@limiter.limit("10/minute")
async def gen_pdf(
    request: Request,
    req: PdfGenRequest,
    user: UserProfile = Depends(get_current_user),
    pdf_service: PdfGenerationService = Depends(get_pdf_service),  # v3.26: DI
):
    """
    Generate a PDF (always free per PRD v3.0).

    Creates an 8-page foldable zine (booklet) from images and texts.
    Format: Single A4 sheet that can be folded into a mini-book.

    Security:
    - SSRF protection via PdfGenRequest validation
    - Project ownership verification via Service
    - UUID validation for project_id
    - Text length limits (max 2000 chars/page)

    Returns:
        StreamingResponse: PDF file (application/pdf)
    """
    # v3.26: Generate PDF via Service (DDD compliant)
    try:
        buf = await pdf_service.generate_pdf(
            user_id=user.user_id,
            project_id=req.project_id,
            current_hash=req.current_hash,
            image_urls=req.image_urls,
            texts=req.texts,
        )
    except ProjectNotFoundException:
        # v3.26: GP-HIGH-3 fix - Explicit 404 for missing/unauthorized projects
        raise HTTPException(404, "Project not found or access denied")
    except PdfGenerationException as e:
        # v3.26: GP-HIGH-3 fix - User-friendly error for PDF generation failures
        logger.error(f"PDF generation failed for user {user['id']}: {e}")
        raise HTTPException(500, f"PDF generation failed: {str(e)}")

    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=zine.pdf"}
    )
