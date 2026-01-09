"""Export API - PDF, preview, and ZIP export endpoints.

@module api.user.export
@version 3.0.0

Changes:
- v3.0.0: DDD architecture upgrade
  - Created ExportService with complete business logic
  - Added dependency injection (get_export_service)
  - Migrated to DDD: API → Service → Repository
  - Reduced API layer from 352 to ~200 lines (-43%)
  - All business logic moved to ExportService
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
from typing import List, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from dependencies import get_current_user
from infrastructure.rate_limiter import limiter
from infrastructure.repositories.project_repository import SupabaseProjectRepository
from core.database import get_database_client
from domains.export import ExportService
from domains.export.export_service import (
    ProjectNotFoundException,
    ExportException,
    InsufficientPermissionException,
)

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


# ==========================================
# Dependency Injection
# ==========================================

def get_export_service() -> ExportService:
    """Dependency injection factory for ExportService."""
    db = get_database_client()
    project_repo = SupabaseProjectRepository(db)
    return ExportService(project_repository=project_repo)


# ==========================================
# PDF Export Endpoint
# ==========================================

@router.get("/projects/{project_id}/pdf")
@limiter.limit("10/minute")
async def export_project_pdf(
    request: Request,
    project_id: str,
    user: dict = Depends(get_current_user),
    export_service: ExportService = Depends(get_export_service),  # v3.0.0: DI
):
    """
    Generate a PDF from stored project data.

    PDF export is always free per PRD v3.0.

    Security:
    - UUID validation for project_id
    - Project ownership verification via Service
    - Filename sanitization

    Returns:
        StreamingResponse: PDF file (application/pdf)
    """
    # v2.1.0: EX-HIGH-1 - Validate project_id format
    if not UUID_PATTERN.match(project_id):
        raise HTTPException(400, "Invalid project ID format")

    # v3.0.0: Export PDF via Service (DDD compliant)
    try:
        buf, title = await export_service.export_pdf(user["id"], project_id)
    except ProjectNotFoundException:
        raise HTTPException(404, "Project not found")
    except ExportException as e:
        logger.error(f"PDF export failed for user {user['id'][:8]}...: {e}")
        raise HTTPException(500, "PDF generation failed")

    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{title}.pdf"'},
    )


# ==========================================
# Preview Export Endpoint
# ==========================================

@router.get("/projects/{project_id}/preview")
@limiter.limit("20/minute")
async def export_project_preview(
    request: Request,
    project_id: str,
    user: dict = Depends(get_current_user),
    export_service: ExportService = Depends(get_export_service),  # v3.0.0: DI
):
    """
    Generate a PNG preview of the project PDF.

    Security:
    - UUID validation for project_id
    - Project ownership verification via Service

    Returns:
        StreamingResponse: PNG image (image/png)
    """
    # v2.1.0: EX-HIGH-1 - Validate project_id format
    if not UUID_PATTERN.match(project_id):
        raise HTTPException(400, "Invalid project ID format")

    # v3.0.0: Export preview via Service (DDD compliant)
    try:
        img_buffer = await export_service.export_preview(user["id"], project_id)
    except ProjectNotFoundException:
        raise HTTPException(404, "Project not found")
    except ExportException:
        raise HTTPException(500, "Failed to generate preview")

    return StreamingResponse(
        img_buffer,
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )


# ==========================================
# ZIP Export Endpoints
# ==========================================

@router.post("/zip", deprecated=True)
@limiter.limit("5/minute")
async def export_zip(
    request: Request,
    req: ZipExportRequest,
    user: dict = Depends(get_current_user),
    export_service: ExportService = Depends(get_export_service),  # v3.0.0: DI
):
    """
    Export images as ZIP archive.

    **DEPRECATED**: Use `GET /projects/{project_id}/zip` instead.
    This endpoint will be removed in v4.0.

    Requires Pro plan.

    v2.1.0: Added SSRF protection via URL domain whitelist validation.

    Security:
    - Tier verification (Pro required)
    - URL validation via Pydantic (SSRF protection)
    - URL count limit (max 20)

    Returns:
        StreamingResponse: ZIP file (application/zip)
    """
    # v3.0.0: Export custom ZIP via Service (DDD compliant)
    try:
        buf = await export_service.export_custom_zip(
            user_id=user["id"],
            image_urls=req.image_urls,
            tier=(user.get("tier") or "").lower(),
            project_id=req.project_id,
        )
    except InsufficientPermissionException:
        raise HTTPException(403, "ZIP export requires Pro plan.")
    except ExportException as e:
        logger.error(f"Custom ZIP export failed: {e}")
        raise HTTPException(500, "ZIP generation failed")

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
    export_service: ExportService = Depends(get_export_service),  # v3.0.0: DI
):
    """
    Export project assets as ZIP archive.

    Requires Pro plan.

    v2.1.0: Added UUID validation and SSRF protection.

    Security:
    - UUID validation for project_id
    - Tier verification (Pro required)
    - Project ownership verification via Service
    - SSRF protection (URL filtering in Service)
    - Filename sanitization

    Returns:
        StreamingResponse: ZIP file (application/zip)
    """
    # v2.1.0: EX-HIGH-1 - Validate project_id format
    if not UUID_PATTERN.match(project_id):
        raise HTTPException(400, "Invalid project ID format")

    # v3.0.0: Export project ZIP via Service (DDD compliant)
    try:
        buf, title = await export_service.export_project_zip(
            user_id=user["id"],
            project_id=project_id,
            tier=(user.get("tier") or "").lower(),
        )
    except InsufficientPermissionException:
        raise HTTPException(403, "ZIP export requires Pro plan.")
    except ProjectNotFoundException:
        raise HTTPException(404, "Project not found")
    except ExportException as e:
        # ExportException includes "No valid URLs" case
        if "No valid" in str(e):
            raise HTTPException(400, str(e))
        logger.error(f"Project ZIP export failed: {e}")
        raise HTTPException(500, "ZIP generation failed")

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{title}_assets.zip"'},
    )
