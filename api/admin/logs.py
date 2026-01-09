"""
Admin Logs API - Error logs and operation logs for admins.

@module api.admin.logs
@version 3.26

Changes:
- v3.26: DDD architecture refactor + enhancements (2026-01-09)
  - LOG-CRITICAL-1: Created ErrorLogsRepository (DDD compliance)
  - LOG-CRITICAL-2: Migrated GET /errors/stats to Repository
  - LOG-HIGH-1: Added .limit(100000) to prevent OOM
  - LOG-HIGH-2: Added Pydantic Response Models
  - LOG-HIGH-3: All Repository methods have @retry_on_network_error
  - LOG-MEDIUM-1: Increased export limit from 10000 to 100000
  - LOG-MEDIUM-2: Unified error handling (HTTPException)
  - LOG-LOW-1: Added audit logging for sensitive operations

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
from core.database import get_database_client
from infrastructure.repositories import SupabaseAdminUsersRepository, SupabaseErrorLogsRepository
from infrastructure.rate_limiter import limiter
from .logs_models import (
    ErrorLogsResponse,
    ErrorStatsResponse,
    OperationLogsResponse,
)

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

@router.get("/errors", response_model=ErrorLogsResponse)
@limiter.limit("30/minute")
async def get_error_logs(
    request: Request,
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(50, ge=1, le=100, description="Max items per page"),
    error_level: Optional[str] = Query(None, max_length=20, description="Filter by error level"),
    start_date: Optional[str] = Query(None, max_length=30),
    end_date: Optional[str] = Query(None, max_length=30),
    admin: dict = Depends(require_admin)
):
    """Fetch error logs with filtering and pagination."""
    # v3.25: LOG-MEDIUM-4 - Validate date formats
    validate_date_format(start_date, "start_date")
    validate_date_format(end_date, "end_date")

    try:
        # v3.26: LOG-CRITICAL-1 - Use ErrorLogsRepository (DDD compliance)
        db_client = get_database_client()
        error_logs_repo = SupabaseErrorLogsRepository(db_client)

        # v3.26: LOG-LOW-1 - Add audit logging
        logger.info(f"[Admin {admin.get('id')}] Queried error logs (offset={offset}, limit={limit})")

        result = await error_logs_repo.get_error_logs(
            error_level=error_level,
            start_date=start_date,
            end_date=end_date,
            offset=offset,
            limit=limit
        )
        return result
    except Exception as e:
        # v3.26: LOG-MEDIUM-2 - Unified error handling
        logger.error(f"[Admin] Get error logs failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve error logs")


@router.get("/errors/stats", response_model=ErrorStatsResponse)
@limiter.limit("30/minute")
async def get_error_stats(
    request: Request,
    hours: int = Query(24, ge=1, le=168, description="Time range in hours (1-168)"),
    admin: dict = Depends(require_admin)
):
    """Get error statistics for the specified time period."""
    try:
        # v3.26: LOG-CRITICAL-2 - Use ErrorLogsRepository (DDD compliance)
        db_client = get_database_client()
        error_logs_repo = SupabaseErrorLogsRepository(db_client)

        # v3.26: LOG-LOW-1 - Add audit logging
        logger.info(f"[Admin {admin.get('id')}] Queried error stats (hours={hours})")

        stats = await error_logs_repo.get_error_stats(hours=hours)
        return stats
    except Exception as e:
        # v3.26: LOG-MEDIUM-2 - Unified error handling
        logger.error(f"[Admin] Get error stats failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve error statistics")


# ==========================================
# Operation Logs Endpoints (v3.25: Added rate limiting and validation)
# ==========================================

@router.get("/operations", response_model=OperationLogsResponse)
@limiter.limit("30/minute")
async def get_operation_logs(
    request: Request,
    operation_type: Optional[str] = Query(None, max_length=50),
    admin_id: Optional[str] = Query(None),
    target_user_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None, max_length=30),
    end_date: Optional[str] = Query(None, max_length=30),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(50, ge=1, le=100, description="Max items per page"),
    admin: dict = Depends(require_admin)
):
    """Fetch administrator operation logs."""
    # v3.25: LOG-MEDIUM-4 - Validate date formats
    validate_date_format(start_date, "start_date")
    validate_date_format(end_date, "end_date")

    try:
        db_client = get_database_client()
        admin_users_repo = SupabaseAdminUsersRepository(db_client)

        # v3.26: LOG-LOW-1 - Add audit logging
        logger.info(f"[Admin {admin.get('id')}] Queried operation logs (offset={offset}, limit={limit})")

        return await admin_users_repo.admin_get_operation_logs(
            offset=offset,
            limit=limit,
            operation_type=operation_type,
            admin_id=admin_id,
            target_user_id=target_user_id,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        # v3.26: LOG-MEDIUM-2 - Unified error handling
        logger.error(f"[Admin] Get operation logs failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve operation logs")


@router.get("/operations/export")
@limiter.limit("10/minute")
async def export_operation_logs(
    request: Request,
    operation_type: Optional[str] = Query(None, max_length=50),
    start_date: Optional[str] = Query(None, max_length=30),
    end_date: Optional[str] = Query(None, max_length=30),
    admin: dict = Depends(require_admin)
):
    """Export operation logs as CSV."""
    # v3.25: LOG-MEDIUM-4 - Validate date formats
    validate_date_format(start_date, "start_date")
    validate_date_format(end_date, "end_date")

    try:
        db_client = get_database_client()
        admin_users_repo = SupabaseAdminUsersRepository(db_client)

        # v3.26: LOG-LOW-1 - Add audit logging
        logger.info(f"[Admin {admin.get('id')}] Exported operation logs (operation_type={operation_type})")

        # v3.26: LOG-MEDIUM-1 - Increased limit from 10000 to 100000
        result = await admin_users_repo.admin_get_operation_logs(
            offset=0,
            limit=100000,
            operation_type=operation_type,
            admin_id=None,
            target_user_id=None,
            start_date=start_date,
            end_date=end_date
        )

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Time", "Operation", "Admin", "Target User", "Details", "Reason"])

        for log in result.get("logs", []):
            writer.writerow([
                log.get("created_at"),
                log.get("operation_type"),
                log.get("admin_id"),
                log.get("target_user_id"),
                log.get("details"),
                log.get("reason")
            ])

        output.seek(0)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=operation_logs_{timestamp}.csv"}
        )
    except Exception as e:
        # v3.26: LOG-MEDIUM-2 - Unified error handling
        logger.error(f"[Admin] Export operation logs failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to export operation logs")
