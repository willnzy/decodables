"""Export API - PDF, preview, and ZIP export endpoints (v2).

@module api.user.export
@version 2.0.0

Endpoints:
- GET /api/v2/user/export/projects/{project_id}/pdf - Generate PDF
- GET /api/v2/user/export/projects/{project_id}/preview - Generate preview image
- POST /api/v2/user/export/zip - Export ZIP with provided URLs
- GET /api/v2/user/export/projects/{project_id}/zip - Export project as ZIP
"""

import logging
from io import BytesIO
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from dependencies import get_current_user
from shared.ai.zine_generator import create_foldable_book, create_assets_zip
from infrastructure.rate_limiter import limiter
from infrastructure.repositories.project_repository_extended import SupabaseProjectRepositoryExtended
from infrastructure.logging.activity_logger import log_activity
from core.database import get_database_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/user/export", tags=["user-export-v2"])


# ==========================================
# Request Models
# ==========================================

class ZipExportRequest(BaseModel):
    """ZIP export request."""
    image_urls: List[str]
    project_id: Optional[str] = None


# ==========================================
# Helper Functions
# ==========================================

def _extract_project_data(canvas_data) -> tuple[list, list, str]:
    """Extract pages data and paper size from canvas_data."""
    if isinstance(canvas_data, list):
        pages = canvas_data
        paper_size = "US_LETTER"
    else:
        pages = canvas_data.get("pages", [])
        paper_size_raw = canvas_data.get("paperSize", "Letter")
        paper_size = "A4" if paper_size_raw == "A4" else "US_LETTER"

    image_urls = []
    texts = []
    for page in pages:
        if isinstance(page, dict):
            image_urls.append(page.get("previewImage", "") or "")
            texts.append(page.get("prompt", "") or "")
        else:
            image_urls.append("")
            texts.append("")

    # Pad to 8 pages
    while len(image_urls) < 8:
        image_urls.append("")
        texts.append("")

    return image_urls, texts, paper_size


# ==========================================
# PDF Export Endpoints
# ==========================================

@router.get("/projects/{project_id}/pdf")
@limiter.limit("10/minute")
async def export_project_pdf(
    request: Request,
    project_id: str,
    user: dict = Depends(get_current_user),
):
    """
    Generate a PDF from stored project data.

    PDF export is always free per PRD v3.0.
    """
    project_repo = SupabaseProjectRepositoryExtended(get_database_client())
    proj = await project_repo.get_project_detail(project_id, user["id"])
    if not proj:
        raise HTTPException(404, "Project not found")

    canvas_data = proj.get("canvas_data", {})
    image_urls, texts, paper_size = _extract_project_data(canvas_data)

    buf = BytesIO()
    create_foldable_book(image_urls, texts, buf, paper_type=paper_size)
    buf.seek(0)

    title = proj.get("title", "project").replace(" ", "_")
    log_activity(user["id"], "download_pdf", {"project_id": project_id})

    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={title}.pdf"},
    )


@router.get("/projects/{project_id}/preview")
@limiter.limit("20/minute")
async def export_project_preview(
    request: Request,
    project_id: str,
    user: dict = Depends(get_current_user),
):
    """Generate a PNG preview of the project PDF."""
    import fitz

    project_repo = SupabaseProjectRepositoryExtended(get_database_client())
    proj = await project_repo.get_project_detail(project_id, user["id"])
    if not proj:
        raise HTTPException(404, "Project not found")

    canvas_data = proj.get("canvas_data", {})
    image_urls, texts, paper_size = _extract_project_data(canvas_data)

    pdf_buffer = BytesIO()
    create_foldable_book(image_urls, texts, pdf_buffer, paper_type=paper_size)
    pdf_buffer.seek(0)

    try:
        pdf_doc = fitz.open(stream=pdf_buffer.read(), filetype="pdf")
        page = pdf_doc[0]

        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)

        img_buffer = BytesIO(pix.tobytes("png"))
        pdf_doc.close()

        log_activity(user["id"], "preview_pdf", {"project_id": project_id})

        return StreamingResponse(
            img_buffer,
            media_type="image/png",
            headers={"Cache-Control": "no-store"},
        )
    except Exception as e:
        logger.error(f"PDF to image conversion error: {e}")
        raise HTTPException(500, "Failed to generate preview")


# ==========================================
# ZIP Export Endpoints
# ==========================================

@router.post("/zip", deprecated=True)
@limiter.limit("5/minute")
async def export_zip(
    request: Request,
    req: ZipExportRequest,
    user: dict = Depends(get_current_user),
):
    """
    Export images as ZIP archive.

    **DEPRECATED**: Use `GET /projects/{project_id}/zip` instead.
    This endpoint will be removed in v3.0.

    Requires Pro plan.
    """
    user_tier = (user.get("tier") or "").lower()
    if user_tier != "pro":
        raise HTTPException(403, "ZIP export requires Pro plan.")

    buf = BytesIO()
    create_assets_zip(req.image_urls, buf)
    buf.seek(0)

    log_activity(user["id"], "export_zip", {"project_id": req.project_id})

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=assets.zip"},
    )


@router.get("/projects/{project_id}/zip")
@limiter.limit("5/minute")
async def export_project_zip(
    request: Request,
    project_id: str,
    user: dict = Depends(get_current_user),
):
    """
    Export project assets as ZIP archive.

    Requires Pro plan.
    """
    user_tier = (user.get("tier") or "").lower()
    if user_tier != "pro":
        raise HTTPException(403, "ZIP export requires Pro plan.")

    project_repo = SupabaseProjectRepositoryExtended(get_database_client())
    proj = await project_repo.get_project_detail(project_id, user["id"])
    if not proj:
        raise HTTPException(404, "Project not found")

    canvas_data = proj.get("canvas_data", {})
    image_urls, _, _ = _extract_project_data(canvas_data)

    # Filter valid URLs
    valid_urls = [url for url in image_urls if url and url.startswith("http")]

    buf = BytesIO()
    create_assets_zip(valid_urls, buf)
    buf.seek(0)

    title = proj.get("title", "project").replace(" ", "_")
    log_activity(user["id"], "export_zip", {"project_id": project_id})

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={title}_assets.zip"},
    )
