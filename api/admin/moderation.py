"""
Admin Moderation Router - Marketplace moderation and content reports

@module api.admin.moderation
@version 3.25

Changes:
- v3.25: Security improvements
  - MOD-MEDIUM-1: Added rate limiting to all endpoints
  - MOD-MEDIUM-2: Migrated from page to offset pagination
  - MOD-MEDIUM-3: Added moderation status enum validation
  - MOD-MEDIUM-4: Added resource type enum validation
  - MOD-MEDIUM-5: Added limit range validation (1-100)
  - MOD-MEDIUM-6: Added report status validation via field_validator
  - MOD-LOW-1: Added field length limits (reason, response)
  - MOD-LOW-2: Limited error message exposure

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

from core.database import get_database_client
from infrastructure.repositories import (
    SupabaseAdminModerationRepository,
    SupabaseAdminUsersRepository,
    SupabaseAdminStatsRepository,
)
from infrastructure.rate_limiter import limiter
from dependencies import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/moderation", tags=["admin-moderation-v2"])


# ==========================================
# Constants (v3.25)
# ==========================================

# v3.25: MOD-MEDIUM-3 - Valid moderation statuses
VALID_MODERATION_STATUSES = {"pending", "approved", "rejected"}

# v3.25: MOD-MEDIUM-4 - Valid resource types
VALID_RESOURCE_TYPES = {"sticker", "clipart", "template", "font", "all"}

# v3.25: MOD-MEDIUM-6 - Valid report statuses
VALID_REPORT_STATUSES = {"reviewed", "resolved", "dismissed"}


# ==========================================
# Request Models (v3.25: Added field validations)
# ==========================================

class AdminModerationRejectRequest(BaseModel):
    # v3.25: MOD-LOW-1 - Added field length limit
    reason: str = Field(..., min_length=1, max_length=1000)


class ReportResponseRequest(BaseModel):
    # v3.25: MOD-MEDIUM-6 - Added status validation
    status: str = Field(..., max_length=50)
    # v3.25: MOD-LOW-1 - Added field length limit
    response: Optional[str] = Field(None, max_length=2000)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in VALID_REPORT_STATUSES:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(VALID_REPORT_STATUSES)}")
        return v


# ==========================================
# Marketplace Moderation Endpoints (v3.25: Added rate limiting)
# ==========================================

@router.get("/marketplace/moderation/list")
@limiter.limit("30/minute")
async def adm_moderation_list(
    request: Request,
    # v3.25: MOD-MEDIUM-3 - Added status enum validation
    status: Optional[str] = Query(None, max_length=50),
    # v3.25: MOD-MEDIUM-4 - Added resource type enum validation
    resource_type: Optional[str] = Query(None, max_length=50, alias="type"),
    # v3.25: MOD-MEDIUM-2 - Migrated from page to offset pagination
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    # v3.25: MOD-MEDIUM-5 - Added limit range validation
    limit: int = Query(20, ge=1, le=100, description="Max items per page"),
    admin: dict = Depends(require_admin)
):
    """Retrieve moderation list (PRD §16)."""
    # v3.25: Validate status if provided
    if status is not None and status not in VALID_MODERATION_STATUSES:
        raise HTTPException(400, f"Invalid status. Must be one of: {', '.join(VALID_MODERATION_STATUSES)}")

    # v3.25: Validate resource_type if provided
    if resource_type is not None and resource_type not in VALID_RESOURCE_TYPES:
        raise HTTPException(400, f"Invalid type. Must be one of: {', '.join(VALID_RESOURCE_TYPES)}")

    db_client = get_database_client()
    moderation_repo = SupabaseAdminModerationRepository(db_client)
    items = await moderation_repo.admin_get_moderation_list(
        status=status,
        resource_type=resource_type,
        offset=offset,
        limit=limit
    )
    return {"items": items, "total": len(items), "offset": offset, "limit": limit}


@router.get("/marketplace/moderation/{listing_id}")
@limiter.limit("30/minute")
async def adm_moderation_detail(
    request: Request,
    listing_id: str,
    admin: dict = Depends(require_admin)
):
    """Retrieve moderation detail (PRD §16)."""
    db_client = get_database_client()
    moderation_repo = SupabaseAdminModerationRepository(db_client)
    item = await moderation_repo.admin_get_moderation_detail(listing_id)
    if not item:
        raise HTTPException(404, "Listing not found")
    return item


@router.post("/marketplace/moderation/{listing_id}/approve")
@limiter.limit("30/minute")
async def adm_moderation_approve(
    request: Request,
    listing_id: str,
    admin: dict = Depends(require_admin)
):
    """Approve listing (PRD §16)."""
    db_client = get_database_client()
    moderation_repo = SupabaseAdminModerationRepository(db_client)
    stats_repo = SupabaseAdminStatsRepository(db_client)
    admin_users_repo = SupabaseAdminUsersRepository(db_client)

    result = await moderation_repo.admin_approve_listing(listing_id, admin["id"])
    if not result:
        raise HTTPException(404, "Listing not found")

    await stats_repo.log_user_event(admin["id"], "admin_moderation_approve", {"listing_id": listing_id})

    await admin_users_repo.admin_log_operation(
        admin_id=admin["id"],
        operation_type="listing_approve",
        target_user_id=result.get("seller_id"),
        details=f"Approved listing: {result.get('title', listing_id)[:50]}",
        reason=None
    )
    return {"status": "approved", "listing_id": listing_id}


@router.post("/marketplace/moderation/{listing_id}/reject")
@limiter.limit("30/minute")
async def adm_moderation_reject(
    request: Request,
    listing_id: str,
    req: AdminModerationRejectRequest,
    admin: dict = Depends(require_admin)
):
    """Reject listing (PRD §16)."""
    db_client = get_database_client()
    moderation_repo = SupabaseAdminModerationRepository(db_client)
    stats_repo = SupabaseAdminStatsRepository(db_client)
    admin_users_repo = SupabaseAdminUsersRepository(db_client)

    try:
        result = await moderation_repo.admin_reject_listing(listing_id, admin["id"], req.reason)
    except Exception as e:
        # v3.25: MOD-LOW-2 - Limited error message exposure
        logger.error(f"Failed to reject listing {listing_id}: {e}")
        raise HTTPException(400, "Failed to reject listing")

    if not result:
        raise HTTPException(404, "Listing not found")

    await stats_repo.log_user_event(admin["id"], "admin_moderation_reject", {
        "listing_id": listing_id,
        "reason": req.reason
    })

    await admin_users_repo.admin_log_operation(
        admin_id=admin["id"],
        operation_type="listing_reject",
        target_user_id=result.get("seller_id"),
        details=f"Rejected listing: {result.get('title', listing_id)[:50]}",
        reason=req.reason
    )
    return {"status": "rejected", "listing_id": listing_id, "reason": req.reason}


@router.post("/marketplace/moderation/{listing_id}/delete")
@limiter.limit("30/minute")
async def adm_moderation_delete(
    request: Request,
    listing_id: str,
    admin: dict = Depends(require_admin)
):
    """Soft-delete listing (PRD §16)."""
    db_client = get_database_client()
    moderation_repo = SupabaseAdminModerationRepository(db_client)
    stats_repo = SupabaseAdminStatsRepository(db_client)

    result = await moderation_repo.admin_delete_listing(listing_id)
    if not result:
        raise HTTPException(404, "Listing not found")

    await stats_repo.log_user_event(admin["id"], "admin_moderation_delete", {"listing_id": listing_id})
    return {"status": "deleted", "listing_id": listing_id}


@router.post("/marketplace/moderation/{listing_id}/unpublish")
@limiter.limit("30/minute")
async def adm_moderation_unpublish(
    request: Request,
    listing_id: str,
    admin: dict = Depends(require_admin)
):
    """Force-unpublish a listing (PRD §16)."""
    db_client = get_database_client()
    moderation_repo = SupabaseAdminModerationRepository(db_client)
    stats_repo = SupabaseAdminStatsRepository(db_client)

    result = await moderation_repo.admin_unpublish_listing(listing_id)
    if not result:
        raise HTTPException(404, "Listing not found")

    await stats_repo.log_user_event(admin["id"], "admin_moderation_unpublish", {"listing_id": listing_id})
    return {"status": "unpublished", "listing_id": listing_id}


# ==========================================
# Content Reports Endpoints (v3.25: Added rate limiting)
# ==========================================

@router.get("/reports")
@limiter.limit("30/minute")
async def adm_get_reports(
    request: Request,
    status: Optional[str] = Query(None, max_length=50),
    # v3.25: MOD-MEDIUM-2 - Migrated from page to offset pagination
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(20, ge=1, le=100, description="Max items per page"),
    admin: dict = Depends(require_admin)
):
    """Get all content reports with optional status filtering."""
    db_client = get_database_client()
    moderation_repo = SupabaseAdminModerationRepository(db_client)
    reports = await moderation_repo.admin_get_reports(status=status, offset=offset, limit=limit)
    total = await moderation_repo.admin_get_reports_count(status=status)
    return {"items": reports, "total": total, "offset": offset, "limit": limit, "has_more": offset + limit < total}


@router.get("/reports/stats")
@limiter.limit("30/minute")
async def adm_get_reports_stats(
    request: Request,
    admin: dict = Depends(require_admin)
):
    """Get reports statistics by status."""
    db_client = get_database_client()
    moderation_repo = SupabaseAdminModerationRepository(db_client)
    return {
        "pending": await moderation_repo.admin_get_reports_count("pending"),
        "reviewed": await moderation_repo.admin_get_reports_count("reviewed"),
        "resolved": await moderation_repo.admin_get_reports_count("resolved"),
        "dismissed": await moderation_repo.admin_get_reports_count("dismissed"),
        "total": await moderation_repo.admin_get_reports_count()
    }


@router.get("/reports/{report_id}")
@limiter.limit("30/minute")
async def adm_get_report_detail(
    request: Request,
    report_id: str,
    admin: dict = Depends(require_admin)
):
    """Get detailed information about a specific report."""
    db_client = get_database_client()
    moderation_repo = SupabaseAdminModerationRepository(db_client)
    report = await moderation_repo.admin_get_report_detail(report_id)
    if not report:
        raise HTTPException(404, "Report not found")
    return report


@router.post("/reports/{report_id}/respond")
@limiter.limit("30/minute")
async def adm_respond_to_report(
    request: Request,
    report_id: str,
    req: ReportResponseRequest,
    admin: dict = Depends(require_admin)
):
    """Respond to a content report."""
    # Note: Status validation is now done in ReportResponseRequest via field_validator

    try:
        db_client = get_database_client()
        moderation_repo = SupabaseAdminModerationRepository(db_client)
        stats_repo = SupabaseAdminStatsRepository(db_client)
        admin_users_repo = SupabaseAdminUsersRepository(db_client)

        result = await moderation_repo.admin_respond_to_report(
            report_id=report_id,
            admin_id=admin["id"],
            new_status=req.status,
            admin_response=req.response
        )

        if not result:
            raise HTTPException(404, "Report not found")

        await stats_repo.log_user_event(admin["id"], "admin_report_respond", {
            "report_id": report_id,
            "status": req.status
        })

        await admin_users_repo.admin_log_operation(
            admin_id=admin["id"],
            operation_type="report_respond",
            target_user_id=result.get("reporter_id"),
            details=f"Report #{report_id[:8]}... → {req.status}",
            reason=req.response
        )

        return {"status": req.status, "report_id": report_id}

    except HTTPException:
        raise
    except Exception as e:
        # v3.25: MOD-LOW-2 - Limited error message exposure
        logger.error(f"Failed to respond to report: {e}")
        raise HTTPException(500, "Failed to respond to report")
