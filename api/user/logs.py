"""Logs API - Activity logs endpoint (v2).

@module api.user.logs
@version 2.0.0

Endpoints:
- POST /api/v2/user/logs/error - Log single error
- POST /api/v2/user/logs/errors - Log batch errors

Note: These endpoints don't require authentication so errors
can be logged even for unauthenticated users.
"""

import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Header
from pydantic import BaseModel, Field

from services.db_service import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/user/logs", tags=["user-logs-v2"])


# ==========================================
# Request/Response Models
# ==========================================

class ErrorLogRequest(BaseModel):
    """Single error log request."""
    error_id: str
    error_type: str
    error_code: Optional[str] = None
    message: Optional[str] = None
    status_code: Optional[int] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    user_code: Optional[str] = None
    session_id: Optional[str] = None
    page_url: Optional[str] = None
    user_agent: Optional[str] = None
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = {}
    client_timestamp: Optional[str] = None


class ErrorLogBatchRequest(BaseModel):
    """Batch error logs request."""
    errors: List[ErrorLogRequest]


class ErrorLogResponse(BaseModel):
    """Error log response."""
    status: str
    warning: Optional[str] = None
    errors_received: Optional[int] = None


# ==========================================
# Helper Functions
# ==========================================

def _extract_user_id_from_token(authorization: Optional[str]) -> Optional[str]:
    """Extract user_id from JWT token without verification (for logging)."""
    if authorization and authorization.startswith("Bearer "):
        try:
            import jwt
            token = authorization.split(" ")[1]
            decoded = jwt.decode(token, options={"verify_signature": False})
            return decoded.get("sub")
        except Exception:
            pass
    return None


# ==========================================
# Endpoints
# ==========================================

@router.post("/error")
async def log_error(
    req: ErrorLogRequest,
    authorization: Optional[str] = Header(None),
) -> ErrorLogResponse:
    """
    Receive and store a single error log from frontend.

    Does not require authentication - errors should be logged
    even for unauthenticated users.
    """
    try:
        user_id = _extract_user_id_from_token(authorization)

        error_data = {
            "error_id": req.error_id,
            "error_type": req.error_type,
            "error_code": req.error_code,
            "message": req.message[:2000] if req.message else None,
            "status_code": req.status_code,
            "endpoint": req.endpoint[:500] if req.endpoint else None,
            "method": req.method,
            "user_id": user_id,
            "user_code": req.user_code,
            "session_id": req.session_id,
            "page_url": req.page_url[:2000] if req.page_url else None,
            "user_agent": req.user_agent[:500] if req.user_agent else None,
            "stack_trace": req.stack_trace[:5000] if req.stack_trace else None,
            "context": req.context or {},
            "client_timestamp": req.client_timestamp,
        }

        supabase.table("error_logs").insert(error_data).execute()

        logger.info(f"[ErrorLog] {req.error_type} - {req.message[:100] if req.message else 'No message'}")

        return ErrorLogResponse(status="ok")
    except Exception as e:
        logger.warning(f"[ErrorLog] Failed to store error: {e}")
        return ErrorLogResponse(status="ok", warning="Error may not have been stored")


@router.post("/errors")
async def log_errors_batch(
    req: ErrorLogBatchRequest,
    authorization: Optional[str] = Header(None),
) -> ErrorLogResponse:
    """Receive and store batch error logs from frontend."""
    try:
        user_id = _extract_user_id_from_token(authorization)

        error_records = []
        for err in req.errors:
            error_records.append({
                "error_id": err.error_id,
                "error_type": err.error_type,
                "error_code": err.error_code,
                "message": err.message[:2000] if err.message else None,
                "status_code": err.status_code,
                "endpoint": err.endpoint[:500] if err.endpoint else None,
                "method": err.method,
                "user_id": user_id,
                "user_code": err.user_code,
                "session_id": err.session_id,
                "page_url": err.page_url[:2000] if err.page_url else None,
                "user_agent": err.user_agent[:500] if err.user_agent else None,
                "stack_trace": err.stack_trace[:5000] if err.stack_trace else None,
                "context": err.context or {},
                "client_timestamp": err.client_timestamp,
            })

        if error_records:
            supabase.table("error_logs").insert(error_records).execute()

        return ErrorLogResponse(status="ok", errors_received=len(error_records))
    except Exception as e:
        logger.warning(f"[ErrorLog] Failed to store batch errors: {e}")
        return ErrorLogResponse(status="ok", warning="Some errors may not have been stored")
