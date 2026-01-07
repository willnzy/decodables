"""
Admin Logs API - Error logs and operation logs for admins.

@module api.admin.logs
@version 2.0.0

Endpoints:
- GET /logs/errors - Get error logs with filtering
- GET /logs/errors/stats - Get error statistics
- GET /logs/operations - Get admin operation logs
- GET /logs/operations/export - Export operation logs as CSV
"""

import csv
import logging
from io import StringIO
from typing import Optional
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from dependencies import require_admin
from services.db_service import (
    supabase,
    admin_get_operation_logs,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/logs", tags=["admin-logs-v2"])


# ==========================================
# Error Logs Endpoints
# ==========================================

@router.get("/errors")
def get_error_logs(
    page: int = 1,
    limit: int = 50,
    error_type: Optional[str] = None,
    status_code: Optional[int] = None,
    user_code: Optional[str] = None,
    request_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    """Fetch error logs with filtering and pagination."""
    try:
        limit = min(limit, 100)
        offset = (page - 1) * limit

        query = supabase.table("error_logs").select("*", count="exact")

        if error_type:
            query = query.eq("error_type", error_type)
        if status_code:
            query = query.eq("status_code", status_code)
        if user_code:
            query = query.ilike("user_code", f"%{user_code}%")
        if request_id:
            query = query.ilike("request_id", f"%{request_id}%")
        if start_date:
            query = query.gte("created_at", start_date)
        if end_date:
            query = query.lte("created_at", end_date)
        if search:
            query = query.or_(f"message.ilike.%{search}%,endpoint.ilike.%{search}%")

        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()

        total = result.count or 0
        total_pages = (total + limit - 1) // limit if total > 0 else 1
        logs = result.data or []

        # Enrich logs with user_code from profiles if missing
        user_ids_without_code = [
            log["user_id"] for log in logs
            if log.get("user_id") and not log.get("user_code")
        ]

        if user_ids_without_code:
            profiles_result = supabase.table("profiles").select("id, user_code").in_("id", list(set(user_ids_without_code))).execute()
            user_code_map = {p["id"]: p.get("user_code") for p in (profiles_result.data or [])}

            for log in logs:
                if log.get("user_id") and not log.get("user_code"):
                    log["user_code"] = user_code_map.get(log["user_id"])

        return {
            "logs": logs,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
        }
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[Admin] Error fetching error logs: {error_msg}")
        if "relation" in error_msg.lower() and "does not exist" in error_msg.lower():
            return {
                "logs": [],
                "total": 0,
                "page": page,
                "limit": limit,
                "total_pages": 1,
                "warning": "Error logs table not created. Please run the migration."
            }
        raise HTTPException(500, f"Failed to fetch error logs: {error_msg}")


@router.get("/errors/stats")
def get_error_stats(
    hours: int = 24,
    admin: dict = Depends(require_admin)
):
    """Get error statistics for the specified time period."""
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

        errors = supabase.table("error_logs").select(
            "error_type, status_code, endpoint"
        ).gte("created_at", cutoff).execute()

        by_type = {}
        by_status = {}
        by_endpoint = {}

        for err in (errors.data or []):
            t = err.get("error_type", "UNKNOWN")
            by_type[t] = by_type.get(t, 0) + 1

            s = err.get("status_code") or 0
            by_status[s] = by_status.get(s, 0) + 1

            e = err.get("endpoint")
            if e:
                e = e.split("?")[0]
                by_endpoint[e] = by_endpoint.get(e, 0) + 1

        top_endpoints = sorted(by_endpoint.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "hours": hours,
            "total": len(errors.data or []),
            "by_type": by_type,
            "by_status": by_status,
            "top_endpoints": dict(top_endpoints),
        }
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[Admin] Error fetching error stats: {error_msg}")
        if "relation" in error_msg.lower() and "does not exist" in error_msg.lower():
            return {
                "hours": hours,
                "total": 0,
                "by_type": {},
                "by_status": {},
                "top_endpoints": {},
                "warning": "Error logs table not created. Please run the migration."
            }
        raise HTTPException(500, f"Failed to fetch error stats: {error_msg}")


# ==========================================
# Operation Logs Endpoints
# ==========================================

@router.get("/operations")
def get_operation_logs(
    operation_type: Optional[str] = None,
    admin_id: Optional[str] = None,
    target_user_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    admin: dict = Depends(require_admin)
):
    """Fetch administrator operation logs."""
    return admin_get_operation_logs(
        operation_type=operation_type,
        admin_id=admin_id,
        target_user_id=target_user_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        limit=limit
    )


@router.get("/operations/export")
def export_operation_logs(
    operation_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    """Export operation logs as CSV."""
    result = admin_get_operation_logs(
        operation_type=operation_type,
        start_date=start_date,
        end_date=end_date,
        page=1,
        limit=10000
    )

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Time", "Operation", "Admin", "Target User", "Target Email", "Details", "Reason"])

    for log in result.get("logs", []):
        writer.writerow([
            log.get("created_at"),
            log.get("operation_type"),
            log.get("admin_email"),
            log.get("target_user_code"),
            log.get("target_user_email"),
            log.get("details"),
            log.get("reason")
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=operation-logs.csv"}
    )
