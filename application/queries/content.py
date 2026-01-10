"""
Content Queries - Read-only content operations.

@module application.queries.content
@version 1.0.0
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from domains.content import (
    ContentService,
    ResourceType,
    ResourceCategory,
)


@dataclass
class GetResourcesQuery:
    """Query to get system resources."""
    user_tier: str
    resource_type: Optional[str] = None
    category: Optional[str] = None
    allowed_tiers_filter: Optional[str] = None
    page: int = 1
    limit: int = 50
    include_locked: bool = True


@dataclass
class GetResourcesResult:
    """Result of resources query."""
    items: List[Dict[str, Any]]
    total: int
    page: int
    limit: int


class GetResourcesHandler:
    """Handler for GetResourcesQuery."""

    def __init__(self, content_service: ContentService):
        self._content_service = content_service

    async def handle(self, query: GetResourcesQuery) -> GetResourcesResult:
        """Execute resources query."""
        offset = (query.page - 1) * query.limit

        # Parse resource type
        resource_type = None
        if query.resource_type:
            try:
                resource_type = ResourceType(query.resource_type)
            except ValueError:
                pass

        # Parse category
        category = None
        if query.category:
            try:
                category = ResourceCategory(query.category)
            except ValueError:
                pass

        items = await self._content_service.get_resources_with_access(
            user_tier=query.user_tier,
            resource_type=resource_type,
            category=category,
            allowed_tiers_filter=query.allowed_tiers_filter,
            limit=query.limit,
            offset=offset,
            include_locked=query.include_locked,
        )

        return GetResourcesResult(
            items=items,
            total=len(items),
            page=query.page,
            limit=query.limit,
        )


@dataclass
class GetResourceByIdQuery:
    """Query to get single resource."""
    resource_id: str
    user_tier: str


@dataclass
class GetResourceByIdResult:
    """Result of resource query."""
    resource: Optional[Dict[str, Any]]


class GetResourceByIdHandler:
    """Handler for GetResourceByIdQuery."""

    def __init__(self, content_service: ContentService):
        self._content_service = content_service

    async def handle(self, query: GetResourceByIdQuery) -> GetResourceByIdResult:
        """Execute resource query."""
        resource = await self._content_service.get_resource(query.resource_id)

        if not resource:
            return GetResourceByIdResult(resource=None)

        is_accessible = resource.is_accessible_by(query.user_tier)

        return GetResourceByIdResult(
            resource={
                "id": resource.resource_id,
                "type": resource.resource_type.value,
                "url": resource.url,
                "category": resource.category.value if resource.category else None,
                "allowed_tiers": resource.access_control.allowed_tiers,
                "name": resource.display_name,
                "tags": resource.search_tags,
                "is_accessible": is_accessible,
                "is_locked": not is_accessible,
                "created_at": resource.created_at.isoformat() if resource.created_at else None,
            }
        )


@dataclass
class GetStickersQuery:
    """Query to get stickers."""
    user_tier: str
    category: Optional[str] = None
    page: int = 1
    limit: int = 100


@dataclass
class GetStickersResult:
    """Result of stickers query."""
    items: List[Dict[str, Any]]
    total: int
    page: int
    limit: int


class GetStickersHandler:
    """Handler for GetStickersQuery."""

    def __init__(self, content_service: ContentService):
        self._content_service = content_service

    async def handle(self, query: GetStickersQuery) -> GetStickersResult:
        """Execute stickers query."""
        offset = (query.page - 1) * query.limit

        category = None
        if query.category:
            try:
                category = ResourceCategory(query.category)
            except ValueError:
                pass

        result = await self._content_service.get_stickers(
            user_tier=query.user_tier,
            category=category,
            limit=query.limit,
            offset=offset,
        )

        return GetStickersResult(
            items=result.get("items", []),
            total=result.get("total", 0),
            page=query.page,
            limit=query.limit,
        )


@dataclass
class GetBackgroundsQuery:
    """Query to get backgrounds."""
    user_tier: str
    category: Optional[str] = None
    page: int = 1
    limit: int = 50


@dataclass
class GetBackgroundsResult:
    """Result of backgrounds query."""
    items: List[Dict[str, Any]]
    total: int
    page: int
    limit: int


class GetBackgroundsHandler:
    """Handler for GetBackgroundsQuery."""

    def __init__(self, content_service: ContentService):
        self._content_service = content_service

    async def handle(self, query: GetBackgroundsQuery) -> GetBackgroundsResult:
        """Execute backgrounds query."""
        offset = (query.page - 1) * query.limit

        category = None
        if query.category:
            try:
                category = ResourceCategory(query.category)
            except ValueError:
                pass

        result = await self._content_service.get_backgrounds(
            user_tier=query.user_tier,
            category=category,
            limit=query.limit,
            offset=offset,
        )

        return GetBackgroundsResult(
            items=result.get("items", []),
            total=result.get("total", 0),
            page=query.page,
            limit=query.limit,
        )


@dataclass
class GetProjectTemplatesQuery:
    """Query to get project templates."""
    user_tier: str
    category: Optional[str] = None
    page: int = 1
    limit: int = 20


@dataclass
class GetProjectTemplatesResult:
    """Result of project templates query."""
    items: List[Dict[str, Any]]
    total: int
    page: int
    limit: int


class GetProjectTemplatesHandler:
    """Handler for GetProjectTemplatesQuery."""

    def __init__(self, content_service: ContentService):
        self._content_service = content_service

    async def handle(self, query: GetProjectTemplatesQuery) -> GetProjectTemplatesResult:
        """Execute project templates query."""
        offset = (query.page - 1) * query.limit

        category = None
        if query.category:
            try:
                category = ResourceCategory(query.category)
            except ValueError:
                pass

        result = await self._content_service.get_projects(
            user_tier=query.user_tier,
            category=category,
            limit=query.limit,
            offset=offset,
        )

        return GetProjectTemplatesResult(
            items=result.get("items", []),
            total=result.get("total", 0),
            page=query.page,
            limit=query.limit,
        )


@dataclass
class GetCategoriesQuery:
    """Query to get categories for resource type."""
    resource_type: str


@dataclass
class GetCategoriesResult:
    """Result of categories query."""
    categories: List[Dict[str, str]]


class GetCategoriesHandler:
    """Handler for GetCategoriesQuery."""

    def __init__(self, content_service: ContentService):
        self._content_service = content_service

    async def handle(self, query: GetCategoriesQuery) -> GetCategoriesResult:
        """Execute categories query."""
        try:
            resource_type = ResourceType(query.resource_type)
            categories = self._content_service.get_categories_for_type(resource_type)
            return GetCategoriesResult(categories=categories)
        except ValueError:
            return GetCategoriesResult(categories=[])


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

    def __init__(self, content_service: ContentService):
        self._content_service = content_service

    async def handle(self, query: GetResourceStatsQuery) -> GetResourceStatsResult:
        """Execute stats query."""
        stats = await self._content_service.get_resource_stats()
        return GetResourceStatsResult(stats=stats)
