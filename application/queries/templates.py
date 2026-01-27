"""
Templates Queries - Read-only operations for user prompt templates.

@module application.queries.templates
@version 1.1.0 (Unified naming)

Changes:
- v1.1.0: Updated service method calls to new naming convention
  - list_asset_templates → list_user_asset_prompt_templates
  - list_page_templates → list_user_page_prompt_templates
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
        templates = await self._service.list_user_asset_prompt_templates(query.user_id)
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
        templates = await self._service.list_user_page_prompt_templates(query.user_id)
        return ListPageTemplatesResult(templates=templates)
