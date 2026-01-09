"""Themes Repository Interface.

@module domains.themes.repository
@version 1.0.0
"""

from typing import Protocol, List, Dict, Any


class ThemesRepository(Protocol):
    """Repository interface for holiday themes operations."""

    async def list_active_themes(self) -> List[Dict[str, Any]]:
        """
        Get all active themes ordered by priority (descending).

        Returns:
            List of active theme dictionaries, each containing:
            - id: Theme unique identifier
            - name: Theme display name
            - is_active: Whether theme is enabled
            - priority: Theme priority (higher = more important)
            - date_rule: Date activation rules
            - theme_config: Theme configuration (colors, badges, etc.)
        """
        ...
