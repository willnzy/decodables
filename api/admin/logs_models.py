"""
Logs Management API Models - Request/Response schemas.

@module api.admin.logs_models
@version 1.0.0
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ==========================================
# Error Logs Models
# ==========================================

class ErrorLogEntry(BaseModel):
    """Single error log entry."""
    id: Optional[str] = Field(None, description="Log entry ID")
    level: str = Field(..., description="Error level (error, warning, critical)")
    error_type: Optional[str] = Field(None, description="Error type/category")
    message: Optional[str] = Field(None, description="Error message")
    stack_trace: Optional[str] = Field(None, description="Stack trace")
    user_id: Optional[str] = Field(None, description="User ID if applicable")
    endpoint: Optional[str] = Field(None, description="API endpoint where error occurred")
    request_id: Optional[str] = Field(None, description="Request ID for tracing")
    created_at: str = Field(..., description="Error timestamp (ISO format)")


class ErrorLogsResponse(BaseModel):
    """Response for GET /logs/errors."""
    logs: List[ErrorLogEntry] = Field(..., description="List of error logs")
    total: int = Field(..., description="Total number of logs matching filters")
    offset: int = Field(..., description="Current pagination offset")
    limit: int = Field(..., description="Pagination limit")
    has_more: bool = Field(..., description="Whether more logs are available")


class ErrorStatsByLevel(BaseModel):
    """Error count by level."""
    pass  # Dynamic keys (error, warning, critical, etc.)


class ErrorStatsByType(BaseModel):
    """Error count by type."""
    pass  # Dynamic keys


class ErrorTrendEntry(BaseModel):
    """Single trend data point."""
    hour: str = Field(..., description="Hour timestamp (YYYY-MM-DDTHH)")
    count: int = Field(..., description="Error count in that hour")


class ErrorStatsResponse(BaseModel):
    """Response for GET /logs/errors/stats."""
    total_errors: int = Field(..., description="Total error count in period")
    by_level: Dict[str, int] = Field(..., description="Error distribution by level")
    by_type: Dict[str, int] = Field(..., description="Error distribution by type")
    by_hour: Dict[str, int] = Field(..., description="Error distribution by hour")
    trend: List[ErrorTrendEntry] = Field(..., description="Time series trend data")


# ==========================================
# Operation Logs Models
# ==========================================

class OperationLogEntry(BaseModel):
    """Single operation log entry."""
    id: Optional[str] = Field(None, description="Log entry ID")
    admin_id: str = Field(..., description="Admin user ID who performed operation")
    operation_type: str = Field(..., description="Type of operation performed")
    target_user_id: Optional[str] = Field(None, description="Target user ID if applicable")
    details: Optional[str] = Field(None, description="Operation details")
    reason: Optional[str] = Field(None, description="Reason for operation")
    created_at: str = Field(..., description="Operation timestamp (ISO format)")


class OperationLogsResponse(BaseModel):
    """Response for GET /logs/operations."""
    logs: List[OperationLogEntry] = Field(..., description="List of operation logs")
    total: int = Field(..., description="Total number of logs matching filters")
    offset: int = Field(..., description="Current pagination offset")
    limit: int = Field(..., description="Pagination limit")
    has_more: bool = Field(..., description="Whether more logs are available")


# ==========================================
# Audit Logs Models (Task 9 - Phase 5)
# ==========================================

class AuditLogEntry(BaseModel):
    """Single audit log entry with enhanced fields."""
    id: Optional[str] = Field(None, description="Log entry ID")
    admin_id: str = Field(..., description="Admin user ID who performed operation (or 'system_webhook')")
    operation_type: str = Field(..., description="Type of operation performed")
    target_user_id: Optional[str] = Field(None, description="Target user ID if applicable")
    target_type: Optional[str] = Field(None, description="Resource type: project, config, feature_flag, etc.")
    target_id: Optional[str] = Field(None, description="Specific resource identifier")
    details: Optional[str] = Field(None, description="Operation details")
    reason: Optional[str] = Field(None, description="Reason for operation")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional context (before/after values, etc.)")
    source: Optional[str] = Field(None, description="Action source: api, webhook, stripe, auth")
    created_at: str = Field(..., description="Operation timestamp (ISO format)")


class AuditLogsResponse(BaseModel):
    """Response for GET /logs/audit."""
    logs: List[AuditLogEntry] = Field(..., description="List of audit logs")
    total: int = Field(..., description="Total number of logs matching filters")
    offset: int = Field(..., description="Current pagination offset")
    limit: int = Field(..., description="Pagination limit")
    has_more: bool = Field(..., description="Whether more logs are available")
