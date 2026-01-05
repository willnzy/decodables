"""
Logs Router - Error logging endpoints

@module routers.logs
@version 3.24

Endpoints:
- POST /api/logs/error - Log single error
- POST /api/logs/errors - Log batch errors
"""

import logging
from typing import Optional
from fastapi import APIRouter, Header

from services.db_service import supabase
from schemas import ErrorLogRequest, ErrorLogBatchRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/logs", tags=["logs"])


def _extract_user_id_from_token(authorization: Optional[str]) -> Optional[str]:
    """Extract user_id from JWT token without verification (for logging purposes)."""
    if authorization and authorization.startswith("Bearer "):
        try:
            import jwt
            token = authorization.split(" ")[1]
            decoded = jwt.decode(token, options={"verify_signature": False})
            return decoded.get("sub")
        except Exception:
            pass
    return None


@router.post("/error")
async def log_error(request: ErrorLogRequest, authorization: Optional[str] = Header(None)):
    """
    Receive and store a single error log from frontend.
    Does not require authentication - errors should be logged even for unauthenticated users.
    """
    try:
        user_id = _extract_user_id_from_token(authorization)
        
        # Insert error log
        error_data = {
            "error_id": request.error_id,
            "error_type": request.error_type,
            "error_code": request.error_code,
            "message": request.message[:2000] if request.message else None,
            "status_code": request.status_code,
            "endpoint": request.endpoint[:500] if request.endpoint else None,
            "method": request.method,
            "user_id": user_id,
            "user_code": request.user_code,
            "session_id": request.session_id,
            "page_url": request.page_url[:2000] if request.page_url else None,
            "user_agent": request.user_agent[:500] if request.user_agent else None,
            "stack_trace": request.stack_trace[:5000] if request.stack_trace else None,
            "context": request.context or {},
            "client_timestamp": request.client_timestamp,
        }
        
        supabase.table("error_logs").insert(error_data).execute()
        
        # Also log to console for immediate visibility
        logger.info(f"[ErrorLog] {request.error_type} - {request.message[:100] if request.message else 'No message'}")
        
        return {"status": "ok"}
    except Exception as e:
        # Don't fail on logging errors
        logger.warning(f"[ErrorLog] Failed to store error: {e}")
        return {"status": "ok", "warning": "Error may not have been stored"}


@router.post("/errors")
async def log_errors_batch(request: ErrorLogBatchRequest, authorization: Optional[str] = Header(None)):
    """
    Receive and store batch error logs from frontend.
    """
    try:
        user_id = _extract_user_id_from_token(authorization)
        
        # Insert all errors
        error_records = []
        for err in request.errors:
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
        
        return {"status": "ok", "errors_received": len(error_records)}
    except Exception as e:
        logger.warning(f"[ErrorLog] Failed to store batch errors: {e}")
        return {"status": "ok", "warning": "Some errors may not have been stored"}
