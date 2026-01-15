"""Export API - PDF, preview, and ZIP export endpoints.

@module api.user.export
@version 4.1.0

Changes:
- v4.1.0: Deprecated endpoints cleanup
  - REMOVED: POST /zip (use GET /projects/{id}/zip instead)
- v4.0.0: Async export implementation
  - Added async export endpoints: POST /projects/{id}/pdf/async and POST /projects/{id}/zip/async
  - Integrated with RQ task queue for background processing
  - Added TaskResponse model for async task responses
  - Old sync endpoints remain for backward compatibility
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
  - EX-MEDIUM-1/2: Added URL count limit and validation (removed in v4.1.0)
  - EX-LOW-1: Sanitized user_id in logs (only first 8 chars)

Endpoints:
- GET /api/v2/user/export/projects/{project_id}/pdf - Generate PDF (sync)
- POST /api/v2/user/export/projects/{project_id}/pdf/async - Generate PDF (async, recommended)
- GET /api/v2/user/export/projects/{project_id}/preview - Generate preview image
- GET /api/v2/user/export/projects/{project_id}/zip - Export project as ZIP (sync)
- POST /api/v2/user/export/projects/{project_id}/zip/async - Export project as ZIP (async, recommended)
"""

import logging
import re
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from domains.identity.aggregates.user_profile import UserProfile
from dependencies import get_current_user
from infrastructure.rate_limiter import limiter
from infrastructure.repositories.project_repository import SupabaseProjectRepository
from core.database.dependencies import get_async_db
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
# Response Models
# ==========================================

class TaskResponse(BaseModel):
    """Async export task response.

    v4.0.0: Response model for async export endpoints.
    """
    task_id: str = Field(..., description="Unique task identifier")
    status: str = Field(..., description="Task status (pending/queued/processing/completed/failed)")
    message: str = Field(..., description="Human-readable status message")
    estimated_time_seconds: int = Field(..., description="Estimated completion time in seconds")


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

async def get_export_service(db = Depends(get_async_db)) -> ExportService:
    """Dependency injection factory for ExportService (AsyncClient)."""
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
    user: UserProfile = Depends(get_current_user),
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
        buf, title = await export_service.export_pdf(user.user_id, project_id)
    except ProjectNotFoundException:
        raise HTTPException(404, "Project not found")
    except ExportException as e:
        logger.error(f"PDF export failed for user {user.user_id[:8]}...: {e}")
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
    user: UserProfile = Depends(get_current_user),
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
        img_buffer = await export_service.export_preview(user.user_id, project_id)
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

@router.get("/projects/{project_id}/zip")
@limiter.limit("5/minute")
async def export_project_zip(
    request: Request,
    project_id: str,
    user: UserProfile = Depends(get_current_user),
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
            user_id=user.user_id,
            project_id=project_id,
            tier=(user.tier.value if hasattr(user.tier, 'value') else user.tier or "").lower(),
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


# ==========================================
# Async Export Endpoints (v4.0.0)
# ==========================================

@router.post("/projects/{project_id}/pdf/async", response_model=TaskResponse)
@limiter.limit("10/minute")
async def export_project_pdf_async(
    request: Request,
    project_id: str,
    user: UserProfile = Depends(get_current_user),
):
    """
    Enqueue PDF export task for background processing.

    v4.0.0: Async export endpoint using RQ task queue.

    Workflow:
    1. Validate project ownership and UUID format
    2. Enqueue task to Redis Queue with tier-based priority
    3. Return task_id immediately (non-blocking)
    4. Client polls GET /api/v2/user/tasks/{task_id} for status
    5. Download from task.result.download_url when completed

    Security:
    - UUID validation for project_id
    - Idempotency via Redis (24h TTL)
    - Tier-based priority routing (t3→high, t2→default, t1→low)

    Returns:
        TaskResponse: Task ID and status (202 Accepted)
    """
    # v2.1.0: EX-HIGH-1 - Validate project_id format
    if not UUID_PATTERN.match(project_id):
        raise HTTPException(400, "Invalid project ID format")

    # Import task queue service
    from infrastructure.task_queue.queue_service import task_queue

    # Enqueue task with idempotency
    tier = (user.tier.value if hasattr(user.tier, 'value') else user.tier or "t1").lower()
    idempotency_key = f"export:pdf:{user.user_id}:{project_id}"

    task_id = task_queue.enqueue_export_task(
        user_id=user.user_id,
        project_id=project_id,
        export_type="pdf",
        tier=tier,
        idempotency_key=idempotency_key,
    )

    if not task_id:
        logger.error(f"Failed to enqueue PDF export for user {user.user_id[:8]}...")
        raise HTTPException(503, "Export service temporarily unavailable")

    logger.info(f"Enqueued PDF export task {task_id} for user {user.user_id[:8]}...")

    return TaskResponse(
        task_id=task_id,
        status="pending",
        message="PDF export task queued successfully",
        estimated_time_seconds=10,
    )


@router.post("/projects/{project_id}/zip/async", response_model=TaskResponse)
@limiter.limit("5/minute")
async def export_project_zip_async(
    request: Request,
    project_id: str,
    user: UserProfile = Depends(get_current_user),
):
    """
    Enqueue ZIP export task for background processing.

    v4.0.0: Async export endpoint using RQ task queue.

    Requires Pro plan (t3).

    Workflow:
    1. Validate tier (Pro required)
    2. Validate project ownership and UUID format
    3. Enqueue task to Redis Queue with high priority (Pro users)
    4. Return task_id immediately (non-blocking)
    5. Client polls GET /api/v2/user/tasks/{task_id} for status
    6. Download from task.result.download_url when completed

    Security:
    - Tier verification (Pro required)
    - UUID validation for project_id
    - Idempotency via Redis (24h TTL)
    - SSRF protection (URL filtering in background worker)

    Returns:
        TaskResponse: Task ID and status (202 Accepted)
    """
    # v2.1.0: EX-HIGH-1 - Validate project_id format
    if not UUID_PATTERN.match(project_id):
        raise HTTPException(400, "Invalid project ID format")

    # Verify Pro tier
    tier = (user.tier.value if hasattr(user.tier, 'value') else user.tier or "t1").lower()
    if tier != "t3":
        raise HTTPException(403, "ZIP export requires Pro plan")

    # Import task queue service
    from infrastructure.task_queue.queue_service import task_queue

    # Enqueue task with idempotency
    idempotency_key = f"export:zip:{user.user_id}:{project_id}"

    task_id = task_queue.enqueue_export_task(
        user_id=user.user_id,
        project_id=project_id,
        export_type="zip",
        tier=tier,
        idempotency_key=idempotency_key,
    )

    if not task_id:
        logger.error(f"Failed to enqueue ZIP export for user {user.user_id[:8]}...")
        raise HTTPException(503, "Export service temporarily unavailable")

    logger.info(f"Enqueued ZIP export task {task_id} for user {user.user_id[:8]}...")

    return TaskResponse(
        task_id=task_id,
        status="pending",
        message="ZIP export task queued successfully",
        estimated_time_seconds=30,
    )
