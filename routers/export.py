"""
Export Router - PDF, preview, and ZIP export endpoints

@module routers.export
@version 3.24

Endpoints:
- GET /api/projects/{project_id}/pdf - Generate PDF
- GET /api/projects/{project_id}/preview - Generate preview image
- POST /api/export/zip - Export ZIP
- GET /api/projects/{project_id}/zip - Get project ZIP
"""

import logging
from io import BytesIO
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services.db_service import get_project_detail, log_activity
from services.rate_limiter import limiter
from services.ai.zine_generator import create_foldable_book, create_assets_zip
from dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["export"])


# ==========================================
# Request Models
# ==========================================

class PdfGenRequest(BaseModel):
    image_urls: List[str]
    texts: List[str] = []
    project_id: Optional[str] = None


# ==========================================
# Helper Functions
# ==========================================

def _extract_project_data(canvas_data):
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
# Export Endpoints
# ==========================================

@router.get("/api/projects/{project_id}/pdf")
@limiter.limit("10/minute")
def get_project_pdf(
    request: Request, 
    project_id: str, 
    user: dict = Depends(get_current_user)
):
    """Generate a PDF from stored project data (always free)."""
    proj = get_project_detail(project_id, user["id"])
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
        headers={"Content-Disposition": f"attachment; filename={title}.pdf"}
    )


@router.get("/api/projects/{project_id}/preview")
@limiter.limit("20/minute")
def preview_project_as_image(
    request: Request, 
    project_id: str, 
    user: dict = Depends(get_current_user)
):
    """Generate a PNG preview of the PDF."""
    import fitz
    
    proj = get_project_detail(project_id, user["id"])
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
            headers={"Cache-Control": "no-store"}
        )
    except Exception as e:
        logger.error(f"PDF to image conversion error: {e}")
        raise HTTPException(500, "Failed to generate preview")


@router.post("/api/export/zip")
@limiter.limit("5/minute")
def dl_zip(
    request: Request, 
    req: PdfGenRequest, 
    user: dict = Depends(get_current_user)
):
    """Export a ZIP (Pro only)."""
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
        headers={"Content-Disposition": "attachment; filename=assets.zip"}
    )


@router.get("/api/projects/{project_id}/zip")
@limiter.limit("5/minute")
def get_project_zip(
    request: Request,
    project_id: str,
    user: dict = Depends(get_current_user)
):
    """Get project assets as ZIP (Pro only)."""
    user_tier = (user.get("tier") or "").lower()
    if user_tier != "pro":
        raise HTTPException(403, "ZIP export requires Pro plan.")
    
    proj = get_project_detail(project_id, user["id"])
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
        headers={"Content-Disposition": f"attachment; filename={title}_assets.zip"}
    )
