"""
PDF Generation Router - PDF export endpoint

@module api.user.generation_pdf
@version 3.25

Changes:
- v3.25: Security improvements
  - GP-P0-1/2: Added SSRF protection via PdfGenRequest validation
  - GP-HIGH-1: Added UUID validation for project_id
  - GP-HIGH-2: Added text length validation
  - GP-MEDIUM-1: Added hash format validation
  - GP-LOW-1: Sanitized user_id in activity logs

Endpoints:
- POST /api/v2/user/generate/pdf/pdf - PDF generation
"""

from io import BytesIO

from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse

from shared.ai.zine_generator import create_foldable_book
from infrastructure.rate_limiter import limiter
from infrastructure.repositories.project_repository import SupabaseProjectRepository
from infrastructure.logging.activity_logger import log_activity
from core.database import get_database_client
from dependencies import get_current_user
from api.schemas.user.generation import PdfGenRequest

router = APIRouter(prefix="/generate/pdf", tags=["generation-pdf-v2"])


# ==========================================
# PDF Generation
# ==========================================

@router.post("/pdf")
@limiter.limit("10/minute")
async def gen_pdf(request: Request, req: PdfGenRequest, user: dict = Depends(get_current_user)):
    """Generate a PDF (always free per PRD v3.0)."""
    project_repo = SupabaseProjectRepository(get_database_client())
    proj = await project_repo.get_project_detail(req.project_id, user["id"])
    if proj and req.current_hash != proj.get("last_downloaded_hash"):
        await project_repo.update_project_hash(req.project_id, req.current_hash)

    buf = BytesIO()
    create_foldable_book(req.image_urls, req.texts, buf)
    buf.seek(0)

    log_activity(user["id"], "download_pdf", {"project_id": req.project_id})

    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=zine.pdf"}
    )
