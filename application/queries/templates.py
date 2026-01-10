"""
Templates Queries - Read-only operations for user prompt templates.

@module application.queries.templates
@version 1.0.0
"""

from dataclasses import dataclass
from typing import List, Dict, Any

from domains.templates.templates_service import TemplatesService


# ==========================================
# Query 1: List Asset Templates
# ==========================================

@dataclass
class ListAssetTemplatesQuery:
    """Query to list asset prompt templates."""
    user_id: str


@dataclass
class ListAssetTemplatesResult:
    """Result of list asset templates query."""
    templates: List[Dict[str, Any]]


class ListAssetTemplatesHandler:
    """Handler for ListAssetTemplatesQuery."""

    def __init__(self, service: TemplatesService):
        self._service = service

    async def handle(self, query: ListAssetTemplatesQuery) -> ListAssetTemplatesResult:
        """Execute list query."""
        templates = await self._service.list_asset_templates(query.user_id)
        return ListAssetTemplatesResult(templates=templates)


# ==========================================
# Query 2: List Page Templates
# ==========================================

@dataclass
class ListPageTemplatesQuery:
    """Query to list page prompt templates."""
    user_id: str


@dataclass
class ListPageTemplatesResult:
    """Result of list page templates query."""
    templates: List[Dict[str, Any]]


class ListPageTemplatesHandler:
    """Handler for ListPageTemplatesQuery."""

    def __init__(self, service: TemplatesService):
        self._service = service

    async def handle(self, query: ListPageTemplatesQuery) -> ListPageTemplatesResult:
        """Execute list query."""
        templates = await self._service.list_page_templates(query.user_id)
        return ListPageTemplatesResult(templates=templates)
