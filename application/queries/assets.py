"""
Assets Queries - Read-only operations for user assets.

@module application.queries.assets
@version 1.0.0
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from domains.assets.assets_service import AssetsService


# ==========================================
# Query 1: Get User Assets
# ==========================================

@dataclass
class GetUserAssetsQuery:
    """Query to get user assets."""
    user_id: str
    project_id: Optional[str] = None


@dataclass
class GetUserAssetsResult:
    """Result of get user assets query."""
    assets: List[Dict[str, Any]]


class GetUserAssetsHandler:
    """Handler for GetUserAssetsQuery."""

    def __init__(self, service: AssetsService):
        self._service = service

    async def handle(self, query: GetUserAssetsQuery) -> GetUserAssetsResult:
        """Execute get user assets query."""
        assets = await self._service.get_user_assets(
            query.user_id,
            query.project_id
        )
        return GetUserAssetsResult(assets=assets)


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
    """Query to get soft-deleted assets."""
    user_id: str


@dataclass
class GetDeletedAssetsResult:
    """Result of get deleted assets query."""
    assets: List[Dict[str, Any]]


class GetDeletedAssetsHandler:
    """Handler for GetDeletedAssetsQuery."""

    def __init__(self, service: AssetsService):
        self._service = service

    async def handle(self, query: GetDeletedAssetsQuery) -> GetDeletedAssetsResult:
        """Execute get deleted assets query."""
        assets = await self._service.get_deleted_assets(query.user_id)
        return GetDeletedAssetsResult(assets=assets)
