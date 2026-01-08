"""
Admin Logs API - Error logs and operation logs for admins.

@module api.admin.logs
@version 3.25

Changes:
- v3.25: Security improvements
  - LOG-MEDIUM-1: Added rate limiting to all endpoints
  - LOG-MEDIUM-2: Migrated from page to offset pagination
  - LOG-MEDIUM-3: Added hours range validation (1-168)
  - LOG-MEDIUM-4: Added date format validation
  - LOG-MEDIUM-5: Added limit range validation (1-100)
  - LOG-LOW-1: Limited error message exposure

Endpoints:
- GET /logs/errors - Get error logs with filtering
- GET /logs/errors/stats - Get error statistics
- GET /logs/operations - Get admin operation logs
- GET /logs/operations/export - Export operation logs as CSV
"""

import csv
import logging
import re
from io import StringIO
from typing import Optional
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Depends, Request, Query
from fastapi.responses import StreamingResponse

from dependencies import require_admin
from core.database import get_database_client, get_supabase_client
from infrastructure.repositories import SupabaseAdminUsersRepository
from infrastructure.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/logs", tags=["admin-logs-v2"])


# ==========================================
# Constants (v3.25)
# ==========================================

# v3.25: LOG-MEDIUM-4 - Date format pattern
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2})?")


# ==========================================
# Validation Functions (v3.25)
# ==========================================

def validate_date_format(date_str: Optional[str], field_name: str) -> None:
    """Validate date format (YYYY-MM-DD or ISO format)."""
    if date_str is not None and not DATE_PATTERN.match(date_str):
        raise HTTPException(400, f"Invalid {field_name} format. Use YYYY-MM-DD or ISO format")


# ==========================================
# Error Logs Endpoints (v3.25: Added rate limiting and validation)
# ==========================================

@router.get("/errors")
@limiter.limit("30/minute")
async def get_error_logs(
    request: Request,
    # v3.25: LOG-MEDIUM-2 - Migrated from page to offset pagination
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    # v3.25: LOG-MEDIUM-5 - Added limit range validation
    limit: int = Query(50, ge=1, le=100, description="Max items per page"),
    error_type: Optional[str] = Query(None, max_length=100),
    status_code: Optional[int] = Query(None, ge=100, le=599),
    user_code: Optional[str] = Query(None, max_length=50),
    request_id: Optional[str] = Query(None, max_length=100),
    start_date: Optional[str] = Query(None, max_length=30),
    end_date: Optional[str] = Query(None, max_length=30),
    search: Optional[str] = Query(None, max_length=200),
    admin: dict = Depends(require_admin)
):
    """Fetch error logs with filtering and pagination."""
    # v3.25: LOG-MEDIUM-4 - Validate date formats
    validate_date_format(start_date, "start_date")
    validate_date_format(end_date, "end_date")

    try:
        query = get_supabase_client().table("error_logs").select("*", count="exact")

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
        logs = result.data or []

        # Enrich logs with user_code from profiles if missing
        user_ids_without_code = [
            log["user_id"] for log in logs
            if log.get("user_id") and not log.get("user_code")
        ]

        if user_ids_without_code:
            profiles_result = get_supabase_client().table("profiles").select("id, user_code").in_("id", list(set(user_ids_without_code))).execute()
            user_code_map = {p["id"]: p.get("user_code") for p in (profiles_result.data or [])}

            for log in logs:
                if log.get("user_id") and not log.get("user_code"):
                    log["user_code"] = user_code_map.get(log["user_id"])

        return {
            "logs": logs,
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": offset + limit < total,
        }
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[Admin] Error fetching error logs: {error_msg}")
        if "relation" in error_msg.lower() and "does not exist" in error_msg.lower():
            return {
                "logs": [],
                "total": 0,
                "offset": offset,
                "limit": limit,
                "has_more": False,
                "warning": "Error logs table not created. Please run the migration."
            }
        # v3.25: LOG-LOW-1 - Limit error message exposure
        raise HTTPException(500, "Failed to fetch error logs")


@router.get("/errors/stats")
@limiter.limit("30/minute")
async def get_error_stats(
    request: Request,
    # v3.25: LOG-MEDIUM-3 - Added hours range validation
    hours: int = Query(24, ge=1, le=168, description="Time range in hours (1-168)"),
    admin: dict = Depends(require_admin)
):
    """Get error statistics for the specified time period."""
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

        errors = get_supabase_client().table("error_logs").select(
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
        # v3.25: LOG-LOW-1 - Limit error message exposure
        raise HTTPException(500, "Failed to fetch error stats")


# ==========================================
# Operation Logs Endpoints (v3.25: Added rate limiting and validation)
# ==========================================

@router.get("/operations")
@limiter.limit("30/minute")
async def get_operation_logs(
    request: Request,
    operation_type: Optional[str] = Query(None, max_length=100),
    admin_id: Optional[str] = Query(None, max_length=100),
    target_user_id: Optional[str] = Query(None, max_length=100),
    start_date: Optional[str] = Query(None, max_length=30),
    end_date: Optional[str] = Query(None, max_length=30),
    # v3.25: LOG-MEDIUM-2 - Migrated from page to offset pagination
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(50, ge=1, le=100, description="Max items per page"),
    admin: dict = Depends(require_admin)
):
    """Fetch administrator operation logs."""
    # v3.25: LOG-MEDIUM-4 - Validate date formats
    validate_date_format(start_date, "start_date")
    validate_date_format(end_date, "end_date")

    db_client = get_database_client()
    admin_users_repo = SupabaseAdminUsersRepository(db_client)
    return await admin_users_repo.admin_get_operation_logs(
        operation_type=operation_type,
        admin_id=admin_id,
        target_user_id=target_user_id,
        start_date=start_date,
        end_date=end_date,
        offset=offset,
        limit=limit
    )


@router.get("/operations/export")
@limiter.limit("10/minute")
async def export_operation_logs(
    request: Request,
    operation_type: Optional[str] = Query(None, max_length=100),
    start_date: Optional[str] = Query(None, max_length=30),
    end_date: Optional[str] = Query(None, max_length=30),
    admin: dict = Depends(require_admin)
):
    """Export operation logs as CSV."""
    # v3.25: LOG-MEDIUM-4 - Validate date formats
    validate_date_format(start_date, "start_date")
    validate_date_format(end_date, "end_date")

    db_client = get_database_client()
    admin_users_repo = SupabaseAdminUsersRepository(db_client)
    result = await admin_users_repo.admin_get_operation_logs(
        operation_type=operation_type,
        start_date=start_date,
        end_date=end_date,
        offset=0,
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
