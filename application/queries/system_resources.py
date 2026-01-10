"""
SystemResources Queries - Read-only operations for Admin System Resources.

@module application.queries.system_resources
@version 1.0.0
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from domains.content.system_resources_service import SystemResourcesService


# ==========================================
# Query 1: List System Resources
# ==========================================

@dataclass
class ListSystemResourcesQuery:
    """Query to list system resources with filters."""
    resource_type: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None
    search: Optional[str] = None
    page: int = 1
    limit: int = 50


@dataclass
class ListSystemResourcesResult:
    """Result of list system resources query."""
    items: List[Dict[str, Any]]
    total: int
    page: int
    limit: int
    has_more: bool


class ListSystemResourcesHandler:
    """Handler for ListSystemResourcesQuery."""

    def __init__(self, service: SystemResourcesService):
        self._service = service

    async def handle(self, query: ListSystemResourcesQuery) -> ListSystemResourcesResult:
        """Execute list query."""
        offset = (query.page - 1) * query.limit

        items, total = await self._service.list_resources(
            resource_type=query.resource_type,
            category=query.category,
            is_active=query.is_active,
            search=query.search,
            limit=query.limit,
            offset=offset,
        )

        return ListSystemResourcesResult(
            items=items,
            total=total,
            page=query.page,
            limit=query.limit,
            has_more=total > offset + query.limit,
        )


# ==========================================
# Query 2: Get System Resource by ID
# ==========================================

@dataclass
class GetSystemResourceQuery:
    """Query to get single system resource."""
    resource_id: str


@dataclass
class GetSystemResourceResult:
    """Result of get system resource query."""
    resource: Optional[Dict[str, Any]]


class GetSystemResourceHandler:
    """Handler for GetSystemResourceQuery."""

    def __init__(self, service: SystemResourcesService):
        self._service = service

    async def handle(self, query: GetSystemResourceQuery) -> GetSystemResourceResult:
        """Execute get query."""
        resource = await self._service.get_resource(query.resource_id)
        return GetSystemResourceResult(resource=resource)


# ==========================================
# Query 3: Get Resource Stats
# ==========================================

@dataclass
class GetResourceStatsQuery:
    """Query to get resource statistics."""
    pass


@dataclass
class GetResourceStatsResult:
    """Result of stats query."""
    stats: Dict[str, Any]


class GetResourceStatsHandler:
    """Handler for GetResourceStatsQuery."""

    def __init__(self, service: SystemResourcesService):
        self._service = service

    async def handle(self, query: GetResourceStatsQuery) -> GetResourceStatsResult:
        """Execute stats query."""
        stats = await self._service.get_stats()
        return GetResourceStatsResult(stats=stats)


# ==========================================
# Query 4: Get Audit Log
# ==========================================

@dataclass
class GetAuditLogQuery:
    """Query to get audit log for a resource."""
    resource_id: str
    limit: int = 50


@dataclass
class GetAuditLogResult:
    """Result of audit log query."""
    audit_log: List[Dict[str, Any]]


class GetAuditLogHandler:
    """Handler for GetAuditLogQuery."""

    def __init__(self, service: SystemResourcesService):
        self._service = service

    async def handle(self, query: GetAuditLogQuery) -> GetAuditLogResult:
        """Execute audit log query."""
        audit_log = await self._service.get_audit_log(
            query.resource_id,
            query.limit
        )
        return GetAuditLogResult(audit_log=audit_log)
