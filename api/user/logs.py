"""Logs API - Error logs endpoint (v3).

@module api.user.logs
@version 3.1.0

Changes:
- v3.1.0: Added request_id field for backend tracing

- v3.0.0: DDD architecture upgrade - CQRS pattern
  - Created LoggingService with error logging business logic
  - Added 2 Command Handlers (CreateErrorLog, CreateErrorLogBatch)
  - Eliminated direct Supabase calls from API layer
  - Improved testability and maintainability

- v2.1.0: Security improvements
  - LOG-P0-1: Added rate limiting (30/minute for single, 10/minute for batch)
  - LOG-P0-2: Added batch size limit (max 50 errors per request)
  - LOG-HIGH-1: Added error_id format validation (max 100 chars, alphanumeric)
  - LOG-HIGH-2: Added context size limit (max 10KB serialized)
  - LOG-MEDIUM-1: Added error_type max_length
  - LOG-MEDIUM-2: Added method whitelist validation

Endpoints:
- POST /api/v2/user/logs/error - Log single error
- POST /api/v2/user/logs/errors - Log batch errors

Note: These endpoints don't require authentication so errors
can be logged even for unauthenticated users.
"""

import json
import logging
import jwt
import re
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Header, Request
from pydantic import BaseModel, Field, field_validator
from infrastructure.rate_limiter import limiter
from container import get_container
from application.commands.logging import CreateErrorLogCommand, CreateErrorLogBatchCommand

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/logs", tags=["user-logs-v3"])

# v2.1.0: LOG-HIGH-1 - Error ID validation pattern (alphanumeric, underscore, hyphen)
ERROR_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]{1,100}$")

# v2.1.0: LOG-MEDIUM-2 - Valid HTTP methods
VALID_HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}

# v2.1.0: LOG-HIGH-2 - Max context size (10KB)
MAX_CONTEXT_SIZE = 10 * 1024


# ==========================================
# Request/Response Models
# ==========================================

class ErrorLogRequest(BaseModel):
    """
    Single error log request.

    v2.1.0: Added validation for security:
    - LOG-HIGH-1: error_id format validation
    - LOG-MEDIUM-1: error_type max_length
    - LOG-MEDIUM-2: method whitelist
    - LOG-HIGH-2: context size limit
    """
    # v2.1.0: LOG-HIGH-1 - Validate error_id format
    error_id: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_\-]+$")
    # v2.1.0: LOG-MEDIUM-1 - Limit error_type length
    error_type: str = Field(..., min_length=1, max_length=50)
    error_code: Optional[str] = Field(None, max_length=50)
    message: Optional[str] = Field(None, max_length=5000)
    status_code: Optional[int] = Field(None, ge=100, le=599)
    endpoint: Optional[str] = Field(None, max_length=1000)
    method: Optional[str] = Field(None, max_length=10)
    # v3.1.0: Added request_id for backend tracing
    request_id: Optional[str] = Field(None, max_length=100)
    user_code: Optional[str] = Field(None, max_length=50)
    session_id: Optional[str] = Field(None, max_length=100)
    page_url: Optional[str] = Field(None, max_length=2000)
    user_agent: Optional[str] = Field(None, max_length=500)
    stack_trace: Optional[str] = Field(None, max_length=10000)
    context: Dict[str, Any] = Field(default_factory=dict)
    client_timestamp: Optional[str] = Field(None, max_length=50)

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: Optional[str]) -> Optional[str]:
        """Validate HTTP method is valid."""
        if v is None:
            return v
        v_upper = v.upper()
        if v_upper not in VALID_HTTP_METHODS:
            return None  # Silently ignore invalid methods
        return v_upper

    @field_validator("context")
    @classmethod
    def validate_context_size(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate context size is within limits."""
        if not v:
            return {}
        try:
            serialized = json.dumps(v)
            if len(serialized) > MAX_CONTEXT_SIZE:
                # Truncate by returning only error info
                return {"_truncated": True, "_original_size": len(serialized)}
        except Exception:
            return {"_error": "context_serialization_failed"}
        return v


class ErrorLogBatchRequest(BaseModel):
    """
    Batch error logs request.

    v2.1.0: LOG-P0-2 - Added batch size limit (max 50 errors).
    """
    # v2.1.0: LOG-P0-2 - Limit batch size to prevent DoS
    errors: List[ErrorLogRequest] = Field(..., max_length=50)


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
@limiter.limit("30/minute")
async def log_error(
    request: Request,  # v2.1.0: Required for rate limiter
    req: ErrorLogRequest,
    authorization: Optional[str] = Header(None),
) -> ErrorLogResponse:
    """
    Receive and store a single error log from frontend.

    v3.0.0: Now uses CreateErrorLogHandler (CQRS pattern).

    Does not require authentication - errors should be logged
    even for unauthenticated users.

    v2.1.0: Added rate limiting (30/minute) to prevent abuse.
    """
    container = get_container()
    handler = await container.get_create_error_log_handler()

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

    command = CreateErrorLogCommand(error_data=error_data)
    result = await handler.handle(command)

    if not result.success:
        logger.warning(f"[ErrorLog] Failed to store error: {result.error}")
        return ErrorLogResponse(status="ok", warning="Error may not have been stored")

    return ErrorLogResponse(status="ok")


@router.post("/errors")
@limiter.limit("10/minute")
async def log_errors_batch(
    request: Request,  # v2.1.0: Required for rate limiter
    req: ErrorLogBatchRequest,
    authorization: Optional[str] = Header(None),
) -> ErrorLogResponse:
    """
    Receive and store batch error logs from frontend.

    v3.0.0: Now uses CreateErrorLogBatchHandler (CQRS pattern).

    v2.1.0: Added rate limiting (10/minute) and batch size limit (50).
    """
    container = get_container()
    handler = await container.get_create_error_log_batch_handler()

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

    command = CreateErrorLogBatchCommand(errors=error_records)
    result = await handler.handle(command)

    if not result.success:
        logger.warning(f"[ErrorLog] Failed to store batch errors: {result.error}")
        return ErrorLogResponse(status="ok", warning="Some errors may not have been stored")

    return ErrorLogResponse(status="ok", errors_received=result.count)
