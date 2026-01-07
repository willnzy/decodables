"""
Pagination Utilities - Common pagination helpers.

@module core.utils.pagination
@version 1.0.0
"""

from dataclasses import dataclass
from typing import Generic, TypeVar, List, Optional, Any

T = TypeVar('T')


@dataclass
class PaginationParams:
    """
    Pagination parameters.

    Attributes:
        page: Current page number (1-indexed)
        limit: Items per page
        offset: Calculated offset for database queries
    """
    page: int = 1
    limit: int = 20

    def __post_init__(self):
        # Ensure valid values
        self.page = max(1, self.page)
        self.limit = max(1, min(100, self.limit))  # Cap at 100

    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.limit

    @classmethod
    def from_query(cls, page: int = 1, limit: int = 20) -> 'PaginationParams':
        """Create from query parameters."""
        return cls(page=page, limit=limit)


@dataclass
class PaginatedResponse(Generic[T]):
    """
    Paginated response wrapper.

    Attributes:
        items: List of items for current page
        total: Total number of items across all pages
        page: Current page number
        limit: Items per page
        pages: Total number of pages
        has_next: Whether there is a next page
        has_prev: Whether there is a previous page
    """
    items: List[T]
    total: int
    page: int
    limit: int

    @property
    def pages(self) -> int:
        """Calculate total number of pages."""
        if self.total == 0:
            return 0
        return (self.total + self.limit - 1) // self.limit

    @property
    def has_next(self) -> bool:
        """Check if there is a next page."""
        return self.page < self.pages

    @property
    def has_prev(self) -> bool:
        """Check if there is a previous page."""
        return self.page > 1

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON response."""
        return {
            "items": self.items,
            "total": self.total,
            "page": self.page,
            "limit": self.limit,
            "pages": self.pages,
            "has_next": self.has_next,
            "has_prev": self.has_prev,
        }


def paginate(
    items: List[T],
    total: int,
    params: PaginationParams
) -> PaginatedResponse[T]:
    """
    Create paginated response from items.

    Args:
        items: Items for current page
        total: Total item count
        params: Pagination parameters

    Returns:
        PaginatedResponse
    """
    return PaginatedResponse(
        items=items,
        total=total,
        page=params.page,
        limit=params.limit,
    )


def paginate_list(
    all_items: List[T],
    params: PaginationParams
) -> PaginatedResponse[T]:
    """
    Paginate an in-memory list.

    Use this for small lists. For large datasets, use database pagination.

    Args:
        all_items: Complete list of items
        params: Pagination parameters

    Returns:
        PaginatedResponse with sliced items
    """
    total = len(all_items)
    start = params.offset
    end = start + params.limit
    items = all_items[start:end]

    return PaginatedResponse(
        items=items,
        total=total,
        page=params.page,
        limit=params.limit,
    )
