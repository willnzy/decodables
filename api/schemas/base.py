"""
Base Schemas - Standard API response models.

@module api.schemas.base
@version 2.0.0

Changes:
- v2.0.0: API Consolidation Phase 0
  - PaginatedResponse: Uses offset instead of page (DDD compliance)
  - DataResponse: For single item endpoints
  - OperationResponse: For action endpoints
  - ErrorResponse: For standardized errors

Standard Response Models:
- PaginatedResponse[T]: For list endpoints with pagination
- DataResponse[T]: For single item endpoints
- OperationResponse: For action/mutation endpoints
- ErrorResponse: For standardized error responses
"""

from typing import Optional, List, Generic, TypeVar, Any, Dict
from pydantic import BaseModel, Field

T = TypeVar('T')


# ==========================================
# Standard Response Models
# ==========================================

class PaginatedResponse(BaseModel, Generic[T]):
    """
    Standard paginated list response.

    Example:
        GET /api/v2/user/projects?offset=20&limit=10

        Response:
        {
            "items": [...],
            "total": 100,
            "offset": 20,
            "limit": 10,
            "has_more": true
        }
    """
    items: List[T] = Field(..., description="List of items")
    total: int = Field(..., description="Total count of items")
    offset: int = Field(0, description="Number of items skipped")
    limit: int = Field(..., description="Maximum items per page")
    has_more: bool = Field(False, description="Whether more items exist")

    @classmethod
    def create(cls, items: List[T], total: int, offset: int, limit: int):
        """Factory method to create PaginatedResponse with has_more calculation."""
        return cls(
            items=items,
            total=total,
            offset=offset,
            limit=limit,
            has_more=total > offset + limit
        )


class DataResponse(BaseModel, Generic[T]):
    """
    Standard single item response.

    Example:
        GET /api/v2/user/projects/{id}

        Response:
        {
            "data": { "id": "...", "title": "..." },
            "meta": { "created_at": "...", "updated_at": "..." }
        }
    """
    data: T = Field(..., description="Response data")
    meta: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class OperationResponse(BaseModel):
    """
    Standard operation/action response.

    Example:
        DELETE /api/v2/user/projects/{id}

        Response:
        {
            "success": true,
            "message": "Project deleted successfully",
            "data": { "deleted_id": "..." }
        }
    """
    success: bool = Field(True, description="Whether operation succeeded")
    message: Optional[str] = Field(None, description="Human-readable message")
    data: Optional[Dict[str, Any]] = Field(None, description="Optional result data")


class ErrorDetail(BaseModel):
    """Error detail for validation errors."""
    field: Optional[str] = Field(None, description="Field that caused the error")
    reason: str = Field(..., description="Error reason")


class ErrorResponse(BaseModel):
    """
    Standard error response.

    Example:
        {
            "code": "VALIDATION_ERROR",
            "message": "Validation failed",
            "details": [
                { "field": "email", "reason": "Invalid format" }
            ]
        }
    """
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[List[ErrorDetail]] = Field(None, description="Detailed error info")


__all__ = [
    "PaginatedResponse",
    "DataResponse",
    "OperationResponse",
    "ErrorDetail",
    "ErrorResponse",
]
