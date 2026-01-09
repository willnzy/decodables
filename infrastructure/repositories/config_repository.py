"""
Config Repository Implementation - System configuration data access.

@module infrastructure.repositories.config_repository
@version 1.1.0
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from core.database import DatabaseClient, retry_on_network_error
from domains.platform.config_repository import ConfigRepository

logger = logging.getLogger(__name__)


class SupabaseConfigRepository(ConfigRepository):
    """
    Supabase implementation of configuration repository.

    Provides data access for system_configs table.
    Caching is handled at Domain Service layer.
    """

    def __init__(self, client: DatabaseClient):
        """
        Initialize repository with database client.

        Args:
            client: Supabase database client
        """
        self.client = client

    @retry_on_network_error()
    async def get_by_key(self, key: str, default_value: Optional[str] = None) -> Optional[str]:
        """
        Get system configuration value by key.

        Args:
            key: Configuration key
            default_value: Default value if not found

        Returns:
            Configuration value or default_value
        """
        result = self.client.table("system_configs").select("value").eq(
            "key", key
        ).eq("is_active", True).execute()

        if result.data:
            return result.data[0].get("value")

        return default_value

    @retry_on_network_error()
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
        query = self.client.table("system_configs").select("*")

        if group:
            query = query.eq("config_group", group)
        if not include_inactive:
            query = query.eq("is_active", True)

        # Add limit to prevent OOM (CFG-HIGH-2)
        result = query.order("config_group").order("key").limit(10000).execute()
        return result.data or []

    @retry_on_network_error()
    async def get_by_group(self, group: str) -> Dict[str, Any]:
        """
        Get configs by group as dict.

        Args:
            group: Config group name

        Returns:
            Dict of key-value pairs
        """
        result = self.client.table("system_configs").select("key, value").eq(
            "config_group", group
        ).eq("is_active", True).execute()

        return {row["key"]: row["value"] for row in (result.data or [])}

    @retry_on_network_error()
    async def get_paginated(
        self,
        group: Optional[str] = None,
        offset: int = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get system configs with pagination (admin).

        Args:
            group: Filter by group
            offset: Number of records to skip
            limit: Items per page

        Returns:
            Dict with items and total count
        """
        query = self.client.table("system_configs").select("*", count="exact")

        if group:
            query = query.eq("config_group", group)

        result = query.order("config_group").order("key").range(
            offset, offset + limit - 1
        ).execute()

        return {
            "items": result.data or [],
            "total": result.count or 0
        }

    @retry_on_network_error()
    async def get_groups(self) -> List[str]:
        """
        Get distinct config groups with OOM protection.

        SYS-MEDIUM-3: Added .limit(10000) for OOM protection.

        Returns:
            List of group names
        """
        result = self.client.table("system_configs").select("config_group").limit(10000).execute()
        groups = set(
            row.get("config_group")
            for row in (result.data or [])
            if row.get("config_group")
        )
        return sorted(list(groups))

    @retry_on_network_error()
    async def create(
        self,
        key: str,
        value: str,
        group: str,
        description: Optional[str] = None,
        value_type: str = "string",
        admin_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create system config.

        Args:
            key: Config key
            value: Config value
            group: Config group
            description: Optional description
            value_type: Value type (string, int, bool, json)
            admin_id: Admin user ID

        Returns:
            Created config record
        """
        result = self.client.table("system_configs").insert({
            "key": key,
            "value": value,
            "config_group": group,
            "description": description,
            "value_type": value_type,
            "is_active": True,
            "created_by": admin_id,
        }).execute()

        # CFG-LOW-2 FIX: Cache invalidation handled by Domain Service layer
        # self._invalidate_cache(key)  # Removed - no-op in this layer

        return result.data[0] if result.data else None

    @retry_on_network_error()
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
        update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}

        if value is not None:
            update_data["value"] = value
        if description is not None:
            update_data["description"] = description
        if is_active is not None:
            update_data["is_active"] = is_active
        if admin_id:
            update_data["updated_by"] = admin_id

        result = self.client.table("system_configs").update(update_data).eq(
            "key", key
        ).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def delete(self, key: str, admin_id: Optional[str] = None) -> bool:
        """
        Delete system config.

        Args:
            key: Config key
            admin_id: Admin user ID (for audit)

        Returns:
            True if deleted successfully
        """
        # Log audit if admin_id provided
        if admin_id:
            await self._log_audit(key, "delete", None, None, admin_id)

        result = self.client.table("system_configs").delete().eq("key", key).execute()

        return len(result.data) > 0 if result.data else False

    @retry_on_network_error()
    async def get_audit_logs(
        self,
        config_key: Optional[str] = None,
        offset: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get config audit logs.

        Args:
            config_key: Filter by config key
            offset: Number of records to skip
            limit: Items per page

        Returns:
            List of audit log records
        """
        query = self.client.table("config_audit_logs").select("*")

        if config_key:
            query = query.eq("config_key", config_key)

        result = query.order("created_at", desc=True).range(
            offset, offset + limit - 1
        ).execute()

        return result.data or []

    async def _log_audit(
        self,
        key: str,
        action: str,
        old_value: Any,
        new_value: Any,
        admin_id: str
    ):
        """
        Log config audit.

        Args:
            key: Config key
            action: Action performed
            old_value: Previous value
            new_value: New value
            admin_id: Admin user ID
        """
        try:
            self.client.table("config_audit_logs").insert({
                "config_key": key,
                "action": action,
                "old_value": str(old_value) if old_value else None,
                "new_value": str(new_value) if new_value else None,
                "admin_id": admin_id,
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to log config audit: {e}")

    def invalidate_cache(self, key: Optional[str] = None):
        """
        Invalidate cache (no-op, caching handled by Domain Service).

        Args:
            key: Specific key to invalidate, or None for all
        """
        # Caching is handled at Domain Service layer
        pass
