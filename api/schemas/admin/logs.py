"""
Log Schemas - Error logging models

@module schemas.logs
"""

from typing import Optional, List
from pydantic import BaseModel


class ErrorLogRequest(BaseModel):
    """Request model for error logging."""
    error_id: Optional[str] = None
    error_type: str  # API, NETWORK, JS_ERROR, UNHANDLED_REJECTION, REACT_ERROR, CORS, OTHER
    error_code: Optional[str] = None
    message: str
    status_code: Optional[int] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    page_url: Optional[str] = None
    user_agent: Optional[str] = None
    stack_trace: Optional[str] = None
    context: Optional[dict] = None
    client_timestamp: Optional[str] = None
    session_id: Optional[str] = None
    user_code: Optional[str] = None  # User code for easier identification


class ErrorLogBatchRequest(BaseModel):
    """Request model for batch error logging."""
    errors: List[ErrorLogRequest]
