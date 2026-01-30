"""
Assets Queries - Read-only operations for user assets.

@module application.queries.assets
@version 1.1.0

Changes:
- v1.1.0: Added GetDashboardAssetsQuery/Handler for dashboard view filtering
- v1.0.0: Initial implementation
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from domains.assets.assets_service import AssetsService


# ==========================================
# Query 1: Get User Assets
# ==========================================

@dataclass
class GetUserAssetsQuery:
    """Query to get user assets with pagination."""
    user_id: str
    project_id: Optional[str] = None
    offset: int = 0
    limit: int = 50


@dataclass
class GetUserAssetsResult:
    """Result of get user assets query."""
    items: List[Dict[str, Any]]
    total: int
    offset: int
    limit: int
    has_more: bool


class GetUserAssetsHandler:
    """Handler for GetUserAssetsQuery."""

    def __init__(self, service: AssetsService):
        self._service = service

    async def handle(self, query: GetUserAssetsQuery) -> GetUserAssetsResult:
        """Execute get user assets query with pagination."""
        result = await self._service.get_user_assets_paginated(
            query.user_id,
            query.project_id,
            offset=query.offset,
            limit=query.limit
        )
        return GetUserAssetsResult(
            items=result["items"],
            total=result["total"],
            offset=query.offset,
            limit=query.limit,
            has_more=result["has_more"]
        )


# ==========================================
# Query 2: Check URL Validity
# ==========================================

@dataclass
class CheckURLQuery:
    """Query to check URL validity."""
    url: str


@dataclass
class CheckURLResult:
    """Result of check URL query."""
    result: Dict[str, Any]


class CheckURLHandler:
    """Handler for CheckURLQuery."""

    def __init__(self, service: AssetsService):
        self._service = service

    async def handle(self, query: CheckURLQuery) -> CheckURLResult:
        """Execute check URL query."""
        result = await self._service.check_url_validity(query.url)
        return CheckURLResult(result=result)


# ==========================================
# Query 3: Get Dashboard Stats
# ==========================================

@dataclass
class GetDashboardStatsQuery:
    """Query to get asset dashboard statistics."""
    user_id: str


@dataclass
class GetDashboardStatsResult:
    """Result of get dashboard stats query."""
    stats: Dict[str, Any]


class GetDashboardStatsHandler:
    """Handler for GetDashboardStatsQuery."""

    def __init__(self, service: AssetsService):
        self._service = service

    async def handle(self, query: GetDashboardStatsQuery) -> GetDashboardStatsResult:
        """Execute get dashboard stats query."""
        stats = await self._service.get_dashboard_stats(query.user_id)
        return GetDashboardStatsResult(stats=stats)


# ==========================================
# Query 4: Get Seller Stats
# ==========================================

@dataclass
class GetSellerStatsQuery:
    """Query to get seller marketplace statistics."""
    user_id: str


@dataclass
class GetSellerStatsResult:
    """Result of get seller stats query."""
    stats: Dict[str, Any]


class GetSellerStatsHandler:
    """Handler for GetSellerStatsQuery."""

    def __init__(self, service: AssetsService):
        self._service = service

    async def handle(self, query: GetSellerStatsQuery) -> GetSellerStatsResult:
        """Execute get seller stats query."""
        stats = await self._service.get_seller_stats(query.user_id)
        return GetSellerStatsResult(stats=stats)


# ==========================================
# Query 5: Get Deleted Assets
# ==========================================

@dataclass
class GetDeletedAssetsQuery:
    """Query to get soft-deleted assets with pagination."""
    user_id: str
    offset: int = 0
    limit: int = 50


@dataclass
class GetDeletedAssetsResult:
    """Result of get deleted assets query."""
    items: List[Dict[str, Any]]
    total: int
    offset: int
    limit: int
    has_more: bool


class GetDeletedAssetsHandler:
    """Handler for GetDeletedAssetsQuery."""

    def __init__(self, service: AssetsService):
        self._service = service

    async def handle(self, query: GetDeletedAssetsQuery) -> GetDeletedAssetsResult:
        """Execute get deleted assets query with pagination."""
        result = await self._service.get_deleted_assets_paginated(
            query.user_id,
            offset=query.offset,
            limit=query.limit
        )
        return GetDeletedAssetsResult(
            items=result["items"],
            total=result["total"],
            offset=query.offset,
            limit=query.limit,
            has_more=result["has_more"]
        )


# ==========================================
# Query 6: Get Dashboard Assets
# ==========================================

@dataclass
class GetDashboardAssetsQuery:
    """
    Query to get dashboard assets with view type filtering.

    Supports cross-domain data (marketplace listings for selling view).
    v3.45: Added workspace_id for data isolation.
    """
    user_id: str
    workspace_id: Optional[str] = None
    view_type: str = "all"  # "all", "bought", "selling"
    offset: int = 0
    limit: int = 15
    search: Optional[str] = None
    folder_id: Optional[str] = "NOT_SET"  # "NOT_SET" = no filter, None = root only, str = specific folder


@dataclass
class GetDashboardAssetsResult:
    """Result of dashboard assets query."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class GetDashboardAssetsHandler:
    """
    Handler for GetDashboardAssetsQuery.

    Uses AssetsService for DDD-compliant data access.
    """

    def __init__(self, assets_service: AssetsService):
        self._assets_service = assets_service

    async def handle(self, query: GetDashboardAssetsQuery) -> GetDashboardAssetsResult:
        """Execute dashboard assets query."""
        try:
            result = await self._assets_service.get_dashboard_assets(
                user_id=query.user_id,
                workspace_id=query.workspace_id,
                view_type=query.view_type,
                offset=query.offset,
                limit=query.limit,
                search=query.search,
                folder_id=query.folder_id,
            )

            return GetDashboardAssetsResult(
                success=True,
                data=result,
            )

        except Exception as e:
            return GetDashboardAssetsResult(
                success=False,
                error=str(e),
            )
