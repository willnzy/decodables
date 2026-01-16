"""
Admin Logs API - Error logs and operation logs for admins.

@module api.admin.logs
@version 3.29 (Container-based DI)

Changes in v3.29:
- LOG-ARCH-1: Migrated to Container-based dependency injection
- LOG-ARCH-2: Created AdminLogsService for business logic
- LOG-ARCH-3: Removed direct repository imports from API layer
- Architecture: API → Container → Service → Repository (Strict DIP)

Changes in v3.26:
- LOG-CRITICAL-1: Created ErrorLogsRepository (DDD compliance)
- LOG-CRITICAL-2: Migrated GET /errors/stats to Repository
- LOG-HIGH-1: Added .limit(100000) to prevent OOM
- LOG-HIGH-2: Added Pydantic Response Models
- LOG-HIGH-3: All Repository methods have @retry_on_network_error
- LOG-MEDIUM-1: Increased export limit from 10000 to 100000
- LOG-MEDIUM-2: Unified error handling (HTTPException)
- LOG-LOW-1: Added audit logging for sensitive operations

Endpoints:
- GET /logs/errors - Get error logs with filtering
- GET /logs/errors/stats - Get error statistics
- GET /logs/operations - Get admin operation logs
- GET /logs/operations/export - Export operation logs as CSV
- GET /logs/audit - Get comprehensive audit logs
"""

import csv
import logging
import re
from io import StringIO
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, Request, Query
from fastapi.responses import StreamingResponse

from dependencies import require_admin
from infrastructure.rate_limiter import limiter

# v3.29: Container-based DI
# WHY: API layer should not know about concrete repository implementations
from container import get_container

from .logs_models import (
    ErrorLogsResponse,
    ErrorStatsResponse,
    OperationLogsResponse,
    AuditLogsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/logs", tags=["admin-logs-v2"])


# ==========================================
# Dependency Injection (v3.29: Container-based)
# ==========================================

async def get_admin_logs_service():
    """
    Get AdminLogsService from Container.

    WHY Container-based DI?
    1. Decouples API layer from infrastructure implementations
    2. Enables easy testing with mock services
    3. Centralizes dependency management
    4. Supports future provider switches
    """
    container = get_container()
    return await container.get_admin_logs_service()


# ==========================================
# Constants
# ==========================================

# Date format pattern
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2})?")


# ==========================================
# Validation Functions
# ==========================================

def validate_date_format(date_str: Optional[str], field_name: str) -> None:
    """Validate date format (YYYY-MM-DD or ISO format)."""
    if date_str is not None and not DATE_PATTERN.match(date_str):
        raise HTTPException(400, f"Invalid {field_name} format. Use YYYY-MM-DD or ISO format")


# ==========================================
# Error Logs Endpoints
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
    admin: dict = Depends(require_admin),
    service=Depends(get_admin_logs_service),
):
    """
    Fetch error logs with filtering and pagination.

    v3.29: Refactored to use AdminLogsService via Container.
    """
    # Validate date formats
    validate_date_format(start_date, "start_date")
    validate_date_format(end_date, "end_date")

    try:
        logger.info(f"[Admin {admin.get('id')}] Queried error logs (offset={offset}, limit={limit})")

        result = await service.get_error_logs(
            error_level=error_level,
            start_date=start_date,
            end_date=end_date,
            offset=offset,
            limit=limit
        )
        return result
    except Exception as e:
        logger.error(f"[Admin] Get error logs failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve error logs")


@router.get("/errors/stats", response_model=ErrorStatsResponse)
@limiter.limit("30/minute")
async def get_error_stats(
    request: Request,
    hours: int = Query(24, ge=1, le=168, description="Time range in hours (1-168)"),
    admin: dict = Depends(require_admin),
    service=Depends(get_admin_logs_service),
):
    """
    Get error statistics for the specified time period.

    v3.29: Refactored to use AdminLogsService via Container.
    """
    try:
        logger.info(f"[Admin {admin.get('id')}] Queried error stats (hours={hours})")

        stats = await service.get_error_stats(hours=hours)
        return stats
    except Exception as e:
        logger.error(f"[Admin] Get error stats failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve error statistics")


# ==========================================
# Operation Logs Endpoints
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
    admin: dict = Depends(require_admin),
    service=Depends(get_admin_logs_service),
):
    """
    Fetch administrator operation logs.

    v3.29: Refactored to use AdminLogsService via Container.
    """
    # Validate date formats
    validate_date_format(start_date, "start_date")
    validate_date_format(end_date, "end_date")

    try:
        logger.info(f"[Admin {admin.get('id')}] Queried operation logs (offset={offset}, limit={limit})")

        return await service.get_operation_logs(
            offset=offset,
            limit=limit,
            operation_type=operation_type,
            admin_id=admin_id,
            target_user_id=target_user_id,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        logger.error(f"[Admin] Get operation logs failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve operation logs")


@router.get("/operations/export")
@limiter.limit("10/minute")
async def export_operation_logs(
    request: Request,
    operation_type: Optional[str] = Query(None, max_length=50),
    start_date: Optional[str] = Query(None, max_length=30),
    end_date: Optional[str] = Query(None, max_length=30),
    admin: dict = Depends(require_admin),
    service=Depends(get_admin_logs_service),
):
    """
    Export operation logs as CSV.

    v3.29: Refactored to use AdminLogsService via Container.
    """
    # Validate date formats
    validate_date_format(start_date, "start_date")
    validate_date_format(end_date, "end_date")

    try:
        logger.info(f"[Admin {admin.get('id')}] Exported operation logs (operation_type={operation_type})")

        logs = await service.export_operation_logs(
            operation_type=operation_type,
            start_date=start_date,
            end_date=end_date,
        )

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Time", "Operation", "Admin", "Target User", "Details", "Reason"])

        for log in logs:
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
        logger.error(f"[Admin] Export operation logs failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to export operation logs")


# ==========================================
# Unified Audit Logs Endpoint
# ==========================================

@router.get("/audit", response_model=AuditLogsResponse)
@limiter.limit("30/minute")
async def get_audit_logs(
    request: Request,
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Page size (max 100)"),
    operation_type: Optional[str] = Query(None, description="Filter by operation type"),
    admin_id: Optional[str] = Query(None, description="Filter by admin ID"),
    target_user_id: Optional[str] = Query(None, description="Filter by affected user"),
    target_type: Optional[str] = Query(None, description="Filter by target type"),
    target_id: Optional[str] = Query(None, description="Filter by specific resource ID"),
    source: Optional[str] = Query(None, description="Filter by source"),
    start_date: Optional[str] = Query(None, max_length=30, description="Filter from date"),
    end_date: Optional[str] = Query(None, max_length=30, description="Filter to date"),
    admin: dict = Depends(require_admin),
    service=Depends(get_admin_logs_service),
):
    """
    Get comprehensive audit logs with advanced filtering.

    v3.29: Refactored to use AdminLogsService via Container.
    """
    # Validate date formats
    validate_date_format(start_date, "start_date")
    validate_date_format(end_date, "end_date")

    try:
        logger.info(
            f"[Admin {admin.get('id')}] Queried audit logs "
            f"(operation_type={operation_type}, source={source}, offset={offset})"
        )

        result = await service.get_audit_logs(
            offset=offset,
            limit=limit,
            operation_type=operation_type,
            admin_id=admin_id,
            target_user_id=target_user_id,
            target_type=target_type,
            target_id=target_id,
            source=source,
            start_date=start_date,
            end_date=end_date,
        )

        return AuditLogsResponse(
            logs=result["logs"],
            total=result["total"],
            offset=result["offset"],
            limit=result["limit"],
            has_more=result["has_more"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[Admin {admin.get('id')}] Get audit logs failed: "
            f"{type(e).__name__} - {e}"
        )
        raise HTTPException(500, "Failed to retrieve audit logs")
