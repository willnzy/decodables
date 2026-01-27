"""
Templates Repository - Data access for user prompt templates.

@module infrastructure.repositories.templates_repository
@version 2.1.0 (Unified naming)

Changes in v2.1:
- Renamed tables: asset_prompt_templates → user_asset_prompt_templates
- Renamed tables: user_prompt_templates → user_page_prompt_templates
- Unified method naming convention

Changes in v2.0:
- Removed lazy loading (client parameter now mandatory)
- All methods use AsyncClient
- Removed get_supabase_client() import (sync client)

Purpose:
- Data access for user_asset_prompt_templates and user_page_prompt_templates tables
- Returns raw Dict data for template CRUD operations
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from core.database import DatabaseClient
from core.database.retry import retry_on_network_error


class SupabaseTemplatesRepository:
    """
    Supabase implementation for Templates data access.

    v2.1: Unified naming convention.
    v2.0: AsyncClient required (no lazy loading).

    Handles two tables:
    - user_asset_prompt_templates (5W1H templates for image/asset generation)
    - user_page_prompt_templates (templates for AI Design Page generation)
    """

    def __init__(self, db_client: DatabaseClient):
        """
        Initialize repository with AsyncClient.

        Args:
            db_client: AsyncClient instance (required)

        Raises:
            ValueError: If db_client is None
        """
        if db_client is None:
            raise ValueError("AsyncClient required for SupabaseTemplatesRepository")
        self._client = db_client

    @property
    def client(self):
        """Get AsyncClient instance."""
        return self._client

    # ==========================================
    # User Asset Prompt Templates (5W1H)
    # ==========================================

    @retry_on_network_error()
    async def list_user_asset_prompt_templates(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List all user asset prompt templates for a user, ordered by use_count.

        Args:
            user_id: User ID

        Returns:
            List of template dicts
        """
        result = await self.client.table("user_asset_prompt_templates") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("use_count", desc=True) \
            .execute()

        return result.data or []

    @retry_on_network_error()
    async def get_user_asset_prompt_template(
        self,
        template_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get single user asset prompt template by ID.

        Args:
            template_id: Template UUID
            user_id: User ID (ownership check)

        Returns:
            Template dict or None
        """
        result = await self.client.table("user_asset_prompt_templates") \
            .select("*") \
            .eq("id", template_id) \
            .eq("user_id", user_id) \
            .single() \
            .execute()

        return result.data if result.data else None

    @retry_on_network_error()
    async def create_user_asset_prompt_template(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new user asset prompt template.

        Args:
            data: Template data dict

        Returns:
            Created template dict

        Raises:
            Exception: If creation fails
        """
        result = await self.client.table("user_asset_prompt_templates") \
            .insert(data) \
            .execute()

        if not result.data:
            raise Exception("Failed to create user asset prompt template")

        return result.data[0]

    @retry_on_network_error()
    async def update_user_asset_prompt_template(
        self,
        template_id: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update user asset prompt template.

        Args:
            template_id: Template UUID
            user_id: User ID (ownership check)
            updates: Fields to update

        Returns:
            Updated template dict or None if not found
        """
        result = await self.client.table("user_asset_prompt_templates") \
            .update(updates) \
            .eq("id", template_id) \
            .eq("user_id", user_id) \
            .execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def delete_user_asset_prompt_template(
        self,
        template_id: str,
        user_id: str
    ) -> bool:
        """
        Delete user asset prompt template.

        Args:
            template_id: Template UUID
            user_id: User ID (ownership check)

        Returns:
            True if deleted
        """
        await self.client.table("user_asset_prompt_templates") \
            .delete() \
            .eq("id", template_id) \
            .eq("user_id", user_id) \
            .execute()

        return True

    @retry_on_network_error()
    async def count_user_asset_prompt_templates(self, user_id: str) -> int:
        """
        Count user asset prompt templates for a user.

        Args:
            user_id: User ID

        Returns:
            Template count
        """
        result = await self.client.table("user_asset_prompt_templates") \
            .select("id", count="exact") \
            .eq("user_id", user_id) \
            .execute()

        return result.count or 0

    # ==========================================
    # User Page Prompt Templates
    # ==========================================

    @retry_on_network_error()
    async def list_user_page_prompt_templates(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List all user page prompt templates for a user, ordered by updated_at.

        Args:
            user_id: User ID

        Returns:
            List of template dicts
        """
        result = await self.client.table("user_page_prompt_templates") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("updated_at", desc=True) \
            .execute()

        return result.data or []

    @retry_on_network_error()
    async def get_user_page_prompt_template(
        self,
        template_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get single user page prompt template by ID.

        Args:
            template_id: Template UUID
            user_id: User ID (ownership check)

        Returns:
            Template dict or None
        """
        result = await self.client.table("user_page_prompt_templates") \
            .select("*") \
            .eq("id", template_id) \
            .eq("user_id", user_id) \
            .single() \
            .execute()

        return result.data if result.data else None

    @retry_on_network_error()
    async def create_user_page_prompt_template(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new user page prompt template.

        Args:
            data: Template data dict

        Returns:
            Created template dict

        Raises:
            Exception: If creation fails
        """
        result = await self.client.table("user_page_prompt_templates") \
            .insert(data) \
            .execute()

        if not result.data:
            raise Exception("Failed to create user page prompt template")

        return result.data[0]

    @retry_on_network_error()
    async def update_user_page_prompt_template(
        self,
        template_id: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update user page prompt template.

        Args:
            template_id: Template UUID
            user_id: User ID (ownership check)
            updates: Fields to update

        Returns:
            Updated template dict or None if not found
        """
        result = await self.client.table("user_page_prompt_templates") \
            .update(updates) \
            .eq("id", template_id) \
            .eq("user_id", user_id) \
            .execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def delete_user_page_prompt_template(
        self,
        template_id: str,
        user_id: str
    ) -> bool:
        """
        Delete user page prompt template.

        Args:
            template_id: Template UUID
            user_id: User ID (ownership check)

        Returns:
            True if deleted
        """
        await self.client.table("user_page_prompt_templates") \
            .delete() \
            .eq("id", template_id) \
            .eq("user_id", user_id) \
            .execute()

        return True

    @retry_on_network_error()
    async def count_user_page_prompt_templates(self, user_id: str) -> int:
        """
        Count user page prompt templates for a user.

        Args:
            user_id: User ID

        Returns:
            Template count
        """
        result = await self.client.table("user_page_prompt_templates") \
            .select("id", count="exact") \
            .eq("user_id", user_id) \
            .execute()

        return result.count or 0
