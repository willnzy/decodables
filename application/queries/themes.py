"""Themes Queries - Read operations for holiday themes.

@module application.queries.themes
@version 1.0.0
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional, Dict, Any


# ==========================================
# Get Current Theme Query
# ==========================================

@dataclass
class GetCurrentThemeQuery:
    """Query to get currently active theme."""
    check_date: date


@dataclass
class GetCurrentThemeResult:
    """Result of current theme query."""
    theme: Optional[Dict[str, Any]] = None


class GetCurrentThemeHandler:
    """Handler for GetCurrentThemeQuery."""

    def __init__(self, themes_service):
        """
        Initialize with ThemesService.

        Args:
            themes_service: ThemesService instance
        """
        self._themes_service = themes_service

    async def handle(self, query: GetCurrentThemeQuery) -> GetCurrentThemeResult:
        """
        Execute query to get current active theme.

        Args:
            query: GetCurrentThemeQuery

        Returns:
            GetCurrentThemeResult with theme data
        """
        try:
            theme = await self._themes_service.get_current_active_theme(query.check_date)
            return GetCurrentThemeResult(theme=theme)

        except Exception:
            # Return empty result on error (non-critical feature)
            return GetCurrentThemeResult(theme=None)
