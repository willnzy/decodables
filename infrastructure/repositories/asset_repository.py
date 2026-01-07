"""
Asset Repository - Asset management operations.

@module infrastructure.repositories.asset_repository
@version 1.0.0

Provides all asset CRUD operations.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from core.database import get_supabase_client, retry_on_network_error

logger = logging.getLogger(__name__)


class SupabaseAssetRepository:
    """
    Asset repository for assets table operations.

    Provides all methods needed for asset management.
    """

    def __init__(self, client=None):
        """
        Initialize repository with database client.

        Args:
            client: Supabase database client
        """
        self._client = client

    @property
    def client(self):
        """Lazy load Supabase client."""
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    @retry_on_network_error()
    async def save_asset(
        self,
        user_id: str,
        url: str,
        asset_type: str,
        project_id: Optional[str] = None,
        prompt: Optional[str] = None,
        tz: str = "UTC"
    ) -> Optional[Dict[str, Any]]:
        """
        Save new asset.

        Args:
            user_id: User ID
            url: Asset URL
            asset_type: Asset type/source
            project_id: Optional project ID
            prompt: Optional prompt used to generate
            tz: Timezone

        Returns:
            Created asset dict
        """
        result = self.client.table("assets").insert({
            "user_id": user_id,
            "url": url,
            "source": asset_type,
            "project_id": project_id,
            "prompt": prompt,
            "timezone": tz,
        }).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def get_assets(
        self,
        user_id: str,
        project_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get user assets.

        Args:
            user_id: User ID
            project_id: Optional project ID filter

        Returns:
            List of asset dicts
        """
        query = self.client.table("assets").select("*").eq("user_id", user_id)

        if project_id:
            query = query.eq("project_id", project_id)

        result = query.order("created_at", desc=True).execute()
        return result.data or []

    @retry_on_network_error()
    async def delete_asset(self, asset_id: str, user_id: str) -> bool:
        """
        Delete an asset.

        Args:
            asset_id: Asset ID
            user_id: User ID (for ownership check)

        Returns:
            True if deleted
        """
        result = self.client.table("assets").delete().eq(
            "id", asset_id
        ).eq("user_id", user_id).execute()

        return len(result.data) > 0 if result.data else False
