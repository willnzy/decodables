"""
Base Schemas - Generic response models

@module schemas.base
"""

from typing import Optional, List, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar('T')


class ApiResponse(BaseModel, Generic[T]):
    """Standard API response wrapper."""
    success: bool = True
    data: Optional[T] = None
    message: Optional[str] = None
    error: Optional[str] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response."""
    items: List[T]
    total: int
    page: int
    limit: int
    has_more: bool = False
    
    @classmethod
    def create(cls, items: List[T], total: int, page: int, limit: int):
        return cls(
            items=items,
            total=total,
            page=page,
            limit=limit,
            has_more=total > page * limit
        )
