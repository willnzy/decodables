"""
Admin Moderation Router - Marketplace moderation and content reports

@module api.admin.moderation
@version 3.28 (DDD Compliant)

Changes:
- v3.28: Complete DDD Architecture Migration (MOD-CRITICAL-1)
  - All business logic moved to domains/moderation/service.py
  - API layer only handles HTTP concerns (auth, validation, responses)
  - Fixed total calculation bug (MOD-HIGH-1)
  - Added OOM protection to Repository (MOD-HIGH-2)
  - Added update protection to Repository (MOD-HIGH-3)
  - Optimized query performance (MOD-HIGH-4, MOD-MEDIUM-2)
  - Unified method signatures (MOD-MEDIUM-3)
  - Achieved 100% DDD architecture compliance
- v3.25: Security improvements
  - Added rate limiting to all endpoints
  - Migrated from page to offset pagination
  - Added status/type enum validation
  - Added field length limits
  - Limited error message exposure

Endpoints:
- GET /api/admin/marketplace/moderation/list - Get moderation list
- GET /api/admin/marketplace/moderation/{listing_id} - Get moderation detail
- POST /api/admin/marketplace/moderation/{listing_id}/approve - Approve listing
- POST /api/admin/marketplace/moderation/{listing_id}/reject - Reject listing
- POST /api/admin/marketplace/moderation/{listing_id}/delete - Delete listing
- POST /api/admin/marketplace/moderation/{listing_id}/unpublish - Unpublish listing
- GET /api/admin/reports - Get content reports
- GET /api/admin/reports/stats - Get report statistics
- GET /api/admin/reports/{report_id} - Get report detail
- POST /api/admin/reports/{report_id}/respond - Respond to report
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request, Query
from pydantic import BaseModel, Field, field_validator

# v3.28: Import Service layer instead of Repository
from core.validators import validate_uuid
from domains import moderation as moderation_service
from domains.moderation.constants import (
    VALID_MODERATION_STATUSES,
    VALID_RESOURCE_TYPES,
    VALID_REPORT_STATUSES,
)
from infrastructure.rate_limiter import limiter
from dependencies import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/moderation", tags=["admin-moderation-v2"])


# ==========================================
# Request Models
# ==========================================

class AdminModerationRejectRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=1000)


class ReportResponseRequest(BaseModel):
    status: str = Field(..., max_length=50)
    response: Optional[str] = Field(None, max_length=2000)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in VALID_REPORT_STATUSES:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(VALID_REPORT_STATUSES)}")
        return v


# ==========================================
# Marketplace Moderation Endpoints
# ==========================================

@router.get("/marketplace/moderation/list")
@limiter.limit("30/minute")
async def adm_moderation_list(
    request: Request,
    status: Optional[str] = Query(None, max_length=50),
    resource_type: Optional[str] = Query(None, max_length=50, alias="type"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(20, ge=1, le=100, description="Max items per page"),
    admin: dict = Depends(require_admin)
):
    """Retrieve moderation list (PRD §16)."""
    # Validate status if provided
    if status is not None and status not in VALID_MODERATION_STATUSES:
        raise HTTPException(400, f"Invalid status. Must be one of: {', '.join(VALID_MODERATION_STATUSES)}")

    # Validate resource_type if provided
    if resource_type is not None and resource_type not in VALID_RESOURCE_TYPES:
        raise HTTPException(400, f"Invalid type. Must be one of: {', '.join(VALID_RESOURCE_TYPES)}")

    try:
        # v3.28: Call Service layer (DDD compliant)
        items, total = await moderation_service.get_moderation_list(
            status=status,
            resource_type=resource_type,
            offset=offset,
            limit=limit
        )
        return {"items": items, "total": total, "offset": offset, "limit": limit}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] List moderation queue failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to list moderation queue")


@router.get("/marketplace/moderation/{listing_id}")
@limiter.limit("30/minute")
async def adm_moderation_detail(
    request: Request,
    listing_id: str,
    admin: dict = Depends(require_admin)
):
    """Retrieve moderation detail (PRD §16)."""
    try:
        listing_id = validate_uuid(listing_id, "listing_id")  # WS-08
        item = await moderation_service.get_moderation_detail(listing_id)
        if not item:
            raise HTTPException(404, "Listing not found")
        return item

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Get moderation detail failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to get moderation detail")


@router.post("/marketplace/moderation/{listing_id}/approve")
@limiter.limit("30/minute")
async def adm_moderation_approve(
    request: Request,
    listing_id: str,
    admin: dict = Depends(require_admin)
):
    """Approve listing (PRD §16)."""
    try:
        listing_id = validate_uuid(listing_id, "listing_id")  # WS-08
        result = await moderation_service.approve_listing(listing_id, admin["id"])
        if not result:
            raise HTTPException(404, "Listing not found")

        return {"status": "approved", "listing_id": listing_id}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Approve listing failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to approve listing")


@router.post("/marketplace/moderation/{listing_id}/reject")
@limiter.limit("30/minute")
async def adm_moderation_reject(
    request: Request,
    listing_id: str,
    req: AdminModerationRejectRequest,
    admin: dict = Depends(require_admin)
):
    """Reject listing (PRD §16)."""
    try:
        listing_id = validate_uuid(listing_id, "listing_id")  # WS-08
        result = await moderation_service.reject_listing(listing_id, admin["id"], req.reason)
        if not result:
            raise HTTPException(404, "Listing not found")

        return {"status": "rejected", "listing_id": listing_id, "reason": req.reason}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Reject listing failed: {type(e).__name__} - {e}")
        raise HTTPException(400, "Failed to reject listing")


@router.post("/marketplace/moderation/{listing_id}/delete")
@limiter.limit("30/minute")
async def adm_moderation_delete(
    request: Request,
    listing_id: str,
    admin: dict = Depends(require_admin)
):
    """Soft-delete listing (PRD §16)."""
    try:
        listing_id = validate_uuid(listing_id, "listing_id")  # WS-08
        result = await moderation_service.delete_listing(listing_id, admin["id"])
        if not result:
            raise HTTPException(404, "Listing not found")

        return {"status": "deleted", "listing_id": listing_id}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Delete listing failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to delete listing")


@router.post("/marketplace/moderation/{listing_id}/unpublish")
@limiter.limit("30/minute")
async def adm_moderation_unpublish(
    request: Request,
    listing_id: str,
    admin: dict = Depends(require_admin)
):
    """Force-unpublish a listing (PRD §16)."""
    try:
        listing_id = validate_uuid(listing_id, "listing_id")  # WS-08
        result = await moderation_service.unpublish_listing(listing_id, admin["id"])
        if not result:
            raise HTTPException(404, "Listing not found")

        return {"status": "unpublished", "listing_id": listing_id}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Unpublish listing failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to unpublish listing")


# ==========================================
# Content Reports Endpoints
# ==========================================

@router.get("/reports")
@limiter.limit("30/minute")
async def adm_get_reports(
    request: Request,
    status: Optional[str] = Query(None, max_length=50),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(20, ge=1, le=100, description="Max items per page"),
    admin: dict = Depends(require_admin)
):
    """Get all content reports with optional status filtering."""
    try:
        # v3.28: Call Service layer (DDD compliant)
        # v3.28: MOD-HIGH-4 Fix - Single query returns both items and total
        reports, total, has_more = await moderation_service.get_reports(
            status=status,
            offset=offset,
            limit=limit
        )
        return {
            "items": reports,
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": has_more
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Get reports failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to get reports")


@router.get("/reports/stats")
@limiter.limit("30/minute")
async def adm_get_reports_stats(
    request: Request,
    admin: dict = Depends(require_admin)
):
    """Get reports statistics by status."""
    try:
        # v3.28: Call Service layer (DDD compliant)
        # v3.28: MOD-MEDIUM-2 Fix - Single query with in-memory aggregation
        stats = await moderation_service.get_reports_stats()
        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Get reports stats failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to get reports statistics")


@router.get("/reports/{report_id}")
@limiter.limit("30/minute")
async def adm_get_report_detail(
    request: Request,
    report_id: str,
    admin: dict = Depends(require_admin)
):
    """Get detailed information about a specific report."""
    try:
        report_id = validate_uuid(report_id, "report_id")  # WS-08
        report = await moderation_service.get_report_detail(report_id)
        if not report:
            raise HTTPException(404, "Report not found")
        return report

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Get report detail failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to get report detail")


@router.post("/reports/{report_id}/respond")
@limiter.limit("30/minute")
async def adm_respond_to_report(
    request: Request,
    report_id: str,
    req: ReportResponseRequest,
    admin: dict = Depends(require_admin)
):
    """Respond to a content report."""
    try:
        report_id = validate_uuid(report_id, "report_id")  # WS-08
        result = await moderation_service.respond_to_report(
            report_id=report_id,
            admin_id=admin["id"],
            new_status=req.status,
            admin_response=req.response
        )

        if not result:
            raise HTTPException(404, "Report not found")

        return {"status": req.status, "report_id": report_id}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Respond to report failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to respond to report")
