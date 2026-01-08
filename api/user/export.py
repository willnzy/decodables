"""Export API - PDF, preview, and ZIP export endpoints (v2).

@module api.user.export
@version 2.1.0

Changes:
- v2.1.0: Security improvements
  - EX-P0-1/2: Added SSRF protection with URL whitelist validation
  - EX-HIGH-1: Added UUID validation for project_id
  - EX-HIGH-2: Fixed filename injection in Content-Disposition headers
  - EX-MEDIUM-1/2: Added URL count limit and validation to ZipExportRequest
  - EX-LOW-1: Sanitized user_id in logs (only first 8 chars)

Endpoints:
- GET /api/v2/user/export/projects/{project_id}/pdf - Generate PDF
- GET /api/v2/user/export/projects/{project_id}/preview - Generate preview image
- POST /api/v2/user/export/zip - Export ZIP with provided URLs (deprecated)
- GET /api/v2/user/export/projects/{project_id}/zip - Export project as ZIP
"""

import logging
import re
from io import BytesIO
from typing import List, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from dependencies import get_current_user
from shared.ai.zine_generator import create_foldable_book, create_assets_zip
from infrastructure.rate_limiter import limiter
from infrastructure.repositories.project_repository import SupabaseProjectRepository
from infrastructure.logging.activity_logger import log_activity
from core.database import get_database_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/export", tags=["user-export-v2"])

# ==========================================
# Constants
# ==========================================

# v2.1.0: EX-HIGH-1 - UUID validation pattern
UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)

# v2.1.0: EX-P0-1/2 - SSRF Protection: Allowed URL domains whitelist
# Only allow URLs from our known storage providers
ALLOWED_URL_DOMAINS = {
    # Supabase storage
    "supabase.co",
    "supabase.com",
    # Fal.ai (AI image generation)
    "fal.media",
    "fal.ai",
    # Cloudflare R2 (if used)
    "r2.cloudflarestorage.com",
    # AWS S3 (if used)
    "s3.amazonaws.com",
}

# v2.1.0: EX-HIGH-2 - Safe filename pattern (alphanumeric, underscore, hyphen, space)
SAFE_FILENAME_PATTERN = re.compile(r"[^a-zA-Z0-9_\- ]")


# ==========================================
# Request Models
# ==========================================

class ZipExportRequest(BaseModel):
    """ZIP export request.

    v2.1.0: Added validation for SSRF protection and DoS prevention.
    """
    # v2.1.0: EX-MEDIUM-2 - Limit to max 20 URLs to prevent DoS
    image_urls: List[str] = Field(..., min_length=1, max_length=20)
    project_id: Optional[str] = Field(None, max_length=100)

    @field_validator("image_urls")
    @classmethod
    def validate_urls(cls, v: List[str]) -> List[str]:
        """Validate URLs are from allowed domains (SSRF protection)."""
        validated = []
        for url in v:
            if not url or not url.strip():
                continue
            if not _is_allowed_url(url):
                raise ValueError(f"URL domain not allowed: {url[:50]}...")
            validated.append(url)
        if not validated:
            raise ValueError("At least one valid URL is required")
        return validated


# ==========================================
# Helper Functions
# ==========================================

def _is_allowed_url(url: str) -> bool:
    """
    Check if URL is from an allowed domain (SSRF protection).

    v2.1.0: EX-P0-1/2 - Only allow URLs from trusted storage providers.
    """
    if not url or not url.startswith("http"):
        return False

    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()

        # Check if host matches any allowed domain (or subdomain)
        for allowed in ALLOWED_URL_DOMAINS:
            if host == allowed or host.endswith(f".{allowed}"):
                return True

        return False
    except Exception:
        return False


def _sanitize_filename(name: str) -> str:
    """
    Sanitize filename for Content-Disposition header.

    v2.1.0: EX-HIGH-2 - Prevent header injection via filename.
    """
    if not name:
        return "export"

    # Remove unsafe characters
    safe_name = SAFE_FILENAME_PATTERN.sub("", name)

    # Limit length and provide fallback
    safe_name = safe_name[:50].strip() or "export"

    return safe_name


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
    # v2.1.0: EX-HIGH-1 - Validate project_id format
    if not UUID_PATTERN.match(project_id):
        raise HTTPException(400, "Invalid project ID format")

    project_repo = SupabaseProjectRepository(get_database_client())
    proj = await project_repo.get_project_detail(project_id, user["id"])
    if not proj:
        raise HTTPException(404, "Project not found")

    canvas_data = proj.get("canvas_data", {})
    image_urls, texts, paper_size = _extract_project_data(canvas_data)

    buf = BytesIO()
    create_foldable_book(image_urls, texts, buf, paper_type=paper_size)
    buf.seek(0)

    # v2.1.0: EX-HIGH-2 - Sanitize filename to prevent header injection
    title = _sanitize_filename(proj.get("title", "project"))
    # v2.1.0: EX-LOW-1 - Sanitize user_id in activity log (only first 8 chars logged internally)
    log_activity(user["id"], "download_pdf", {"project_id": project_id})

    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{title}.pdf"'},
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

    # v2.1.0: EX-HIGH-1 - Validate project_id format
    if not UUID_PATTERN.match(project_id):
        raise HTTPException(400, "Invalid project ID format")

    project_repo = SupabaseProjectRepository(get_database_client())
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
        # v2.1.0: EX-LOW-1 - Don't expose internal error details
        logger.error(f"PDF to image conversion error for project {project_id[:8]}...: {type(e).__name__}")
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

    v2.1.0: Added SSRF protection via URL domain whitelist validation.
    """
    user_tier = (user.get("tier") or "").lower()
    if user_tier != "pro":
        raise HTTPException(403, "ZIP export requires Pro plan.")

    # v2.1.0: EX-P0-2 - URLs are already validated by ZipExportRequest.validate_urls()
    buf = BytesIO()
    create_assets_zip(req.image_urls, buf)
    buf.seek(0)

    log_activity(user["id"], "export_zip", {"project_id": req.project_id})

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="assets.zip"'},
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

    v2.1.0: Added UUID validation and SSRF protection.
    """
    # v2.1.0: EX-HIGH-1 - Validate project_id format
    if not UUID_PATTERN.match(project_id):
        raise HTTPException(400, "Invalid project ID format")

    user_tier = (user.get("tier") or "").lower()
    if user_tier != "pro":
        raise HTTPException(403, "ZIP export requires Pro plan.")

    project_repo = SupabaseProjectRepository(get_database_client())
    proj = await project_repo.get_project_detail(project_id, user["id"])
    if not proj:
        raise HTTPException(404, "Project not found")

    canvas_data = proj.get("canvas_data", {})
    image_urls, _, _ = _extract_project_data(canvas_data)

    # v2.1.0: EX-P0-1 - Filter only allowed URLs (SSRF protection)
    valid_urls = [url for url in image_urls if _is_allowed_url(url)]

    if not valid_urls:
        raise HTTPException(400, "No valid image URLs found in project")

    buf = BytesIO()
    create_assets_zip(valid_urls, buf)
    buf.seek(0)

    # v2.1.0: EX-HIGH-2 - Sanitize filename to prevent header injection
    title = _sanitize_filename(proj.get("title", "project"))
    log_activity(user["id"], "export_zip", {"project_id": project_id})

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{title}_assets.zip"'},
    )
