"""
Config Repository Interface - Abstract interface for config data access.

@module domains.platform.config_repository
@version 1.0.0
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any


class ConfigRepository(ABC):
    """
    Abstract interface for system configuration data access.

    This interface defines the contract for accessing system configuration data.
    Implementations should handle database operations, caching, and error handling.
    """

    @abstractmethod
    async def get_by_key(
        self,
        key: str,
        default_value: Optional[str] = None
    ) -> Optional[str]:
        """
        Get system configuration value by key.

        Args:
            key: Configuration key
            default_value: Default value if not found

        Returns:
            Configuration value or default_value
        """
        pass

    @abstractmethod
    async def get_all(
        self,
        group: Optional[str] = None,
        include_inactive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get all system configurations.

        Args:
            group: Filter by config group
            include_inactive: Include inactive configs

        Returns:
            List of configuration records
        """
        pass

    @abstractmethod
    async def get_by_group(self, group: str) -> Dict[str, Any]:
        """
        Get configs by group as dict.

        Args:
            group: Config group name

        Returns:
            Dict of key-value pairs
        """
        pass

    @abstractmethod
    async def update(
        self,
        key: str,
        value: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
        admin_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update system config.

        Args:
            key: Config key
            value: New value
            description: New description
            is_active: Active status
            admin_id: Admin user ID

        Returns:
            Updated config record
        """
        pass

    @abstractmethod
    def invalidate_cache(self, key: Optional[str] = None):
        """
        Invalidate config cache.

        Args:
            key: Specific key to invalidate, or None for all
        """
        pass
