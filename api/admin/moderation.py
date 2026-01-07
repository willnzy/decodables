"""
Admin Moderation Router - Marketplace moderation and content reports

@module api.admin.moderation
@version 3.24

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

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from infrastructure.db_compat import (
    admin_get_moderation_list,
    admin_get_moderation_detail,
    admin_approve_listing,
    admin_reject_listing,
    admin_delete_listing,
    admin_unpublish_listing,
    admin_log_operation,
    log_activity,
    admin_get_reports,
    admin_get_reports_count,
    admin_get_report_detail,
    admin_respond_to_report,
)
from dependencies import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/moderation", tags=["admin-moderation-v2"])


# ==========================================
# Request Models
# ==========================================

class AdminModerationRejectRequest(BaseModel):
    reason: str


class ReportResponseRequest(BaseModel):
    status: str  # 'reviewed' | 'resolved' | 'dismissed'
    response: Optional[str] = None


# ==========================================
# Marketplace Moderation Endpoints
# ==========================================

@router.get("/marketplace/moderation/list")
def adm_moderation_list(
    status: Optional[str] = None,
    type: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    admin: dict = Depends(require_admin)
):
    """Retrieve moderation list (PRD §16)."""
    items = admin_get_moderation_list(
        status=status,
        resource_type=type,
        page=page,
        limit=limit
    )
    return {"items": items, "total": len(items), "page": page}


@router.get("/marketplace/moderation/{listing_id}")
def adm_moderation_detail(listing_id: str, admin: dict = Depends(require_admin)):
    """Retrieve moderation detail (PRD §16)."""
    item = admin_get_moderation_detail(listing_id)
    if not item:
        raise HTTPException(404, "Listing not found")
    return item


@router.post("/marketplace/moderation/{listing_id}/approve")
def adm_moderation_approve(listing_id: str, admin: dict = Depends(require_admin)):
    """Approve listing (PRD §16)."""
    result = admin_approve_listing(listing_id, admin["id"])
    if not result:
        raise HTTPException(404, "Listing not found")
    
    log_activity(admin["id"], "admin_moderation_approve", {"listing_id": listing_id})
    
    admin_log_operation(
        admin_id=admin["id"],
        operation_type="listing_approve",
        target_user_id=result.get("seller_id"),
        details=f"Approved listing: {result.get('title', listing_id)[:50]}",
        reason=None
    )
    return {"status": "approved", "listing_id": listing_id}


@router.post("/marketplace/moderation/{listing_id}/reject")
def adm_moderation_reject(
    listing_id: str, 
    req: AdminModerationRejectRequest,
    admin: dict = Depends(require_admin)
):
    """Reject listing (PRD §16)."""
    try:
        result = admin_reject_listing(listing_id, admin["id"], req.reason)
    except Exception as e:
        raise HTTPException(400, str(e))
    
    if not result:
        raise HTTPException(404, "Listing not found")
    
    log_activity(admin["id"], "admin_moderation_reject", {
        "listing_id": listing_id,
        "reason": req.reason
    })
    
    admin_log_operation(
        admin_id=admin["id"],
        operation_type="listing_reject",
        target_user_id=result.get("seller_id"),
        details=f"Rejected listing: {result.get('title', listing_id)[:50]}",
        reason=req.reason
    )
    return {"status": "rejected", "listing_id": listing_id, "reason": req.reason}


@router.post("/marketplace/moderation/{listing_id}/delete")
def adm_moderation_delete(listing_id: str, admin: dict = Depends(require_admin)):
    """Soft-delete listing (PRD §16)."""
    result = admin_delete_listing(listing_id)
    if not result:
        raise HTTPException(404, "Listing not found")
    
    log_activity(admin["id"], "admin_moderation_delete", {"listing_id": listing_id})
    return {"status": "deleted", "listing_id": listing_id}


@router.post("/marketplace/moderation/{listing_id}/unpublish")
def adm_moderation_unpublish(listing_id: str, admin: dict = Depends(require_admin)):
    """Force-unpublish a listing (PRD §16)."""
    result = admin_unpublish_listing(listing_id)
    if not result:
        raise HTTPException(404, "Listing not found")
    
    log_activity(admin["id"], "admin_moderation_unpublish", {"listing_id": listing_id})
    return {"status": "unpublished", "listing_id": listing_id}


# ==========================================
# Content Reports Endpoints
# ==========================================

@router.get("/reports")
def adm_get_reports(
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    admin: dict = Depends(require_admin)
):
    """Get all content reports with optional status filtering."""
    reports = admin_get_reports(status=status, page=page, limit=limit)
    total = admin_get_reports_count(status=status)
    return {"items": reports, "total": total, "page": page}


@router.get("/reports/stats")
def adm_get_reports_stats(admin: dict = Depends(require_admin)):
    """Get reports statistics by status."""
    return {
        "pending": admin_get_reports_count("pending"),
        "reviewed": admin_get_reports_count("reviewed"),
        "resolved": admin_get_reports_count("resolved"),
        "dismissed": admin_get_reports_count("dismissed"),
        "total": admin_get_reports_count()
    }


@router.get("/reports/{report_id}")
def adm_get_report_detail(report_id: str, admin: dict = Depends(require_admin)):
    """Get detailed information about a specific report."""
    report = admin_get_report_detail(report_id)
    if not report:
        raise HTTPException(404, "Report not found")
    return report


@router.post("/reports/{report_id}/respond")
def adm_respond_to_report(
    report_id: str,
    req: ReportResponseRequest,
    admin: dict = Depends(require_admin)
):
    """Respond to a content report."""
    if req.status not in ['reviewed', 'resolved', 'dismissed']:
        raise HTTPException(400, "Invalid status. Must be 'reviewed', 'resolved', or 'dismissed'")
    
    try:
        result = admin_respond_to_report(
            report_id=report_id,
            admin_id=admin["id"],
            new_status=req.status,
            admin_response=req.response
        )
        
        if not result:
            raise HTTPException(404, "Report not found")
        
        log_activity(admin["id"], "admin_report_respond", {
            "report_id": report_id,
            "status": req.status
        })
        
        admin_log_operation(
            admin_id=admin["id"],
            operation_type="report_respond",
            target_user_id=result.get("reporter_id"),
            details=f"Report #{report_id[:8]}... → {req.status}",
            reason=req.response
        )
        
        return {"status": req.status, "report_id": report_id}
        
    except Exception as e:
        logger.error(f"Failed to respond to report: {e}")
        raise HTTPException(500, str(e))
