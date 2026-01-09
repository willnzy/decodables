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

    @retry_on_network_error()
    async def get_user_asset_usage(
        self,
        user_id: str,
        limit: int = 1000,
        top_n: int = 10
    ) -> Dict[str, Any]:
        """
        Get aggregated asset usage statistics for a user (Admin).

        Queries assets table and returns aggregated statistics by type, category,
        and most used assets.

        Args:
            user_id: User ID
            limit: Maximum number of assets to query (default: 1000, prevents OOM)
            top_n: Number of most used assets to return (default: 10)

        Returns:
            Dict with aggregated statistics:
            {
                "total_assets": int,
                "by_type": Dict[str, int],
                "by_category": Dict[str, int],
                "most_used": List[Dict[str, Any]]
            }
        """
        from collections import Counter

        try:
            # Query assets with limit to prevent OOM
            result = self.client.table("assets").select("*").eq(
                "user_id", user_id
            ).limit(limit).execute()

            assets = result.data or []

            # Aggregate by type
            by_type = Counter()
            for asset in assets:
                asset_type = asset.get("type", "unknown")
                by_type[asset_type] += 1

            # Aggregate by category
            by_category = Counter()
            for asset in assets:
                category = asset.get("category", "uncategorized")
                by_category[category] += 1

            # Find most used assets (by usage_count)
            assets_with_usage = [
                {
                    "id": a.get("id"),
                    "name": a.get("name"),
                    "type": a.get("type"),
                    "category": a.get("category"),
                    "usage_count": a.get("usage_count", 0)
                }
                for a in assets
                if a.get("usage_count", 0) > 0
            ]

            # Sort by usage_count descending and take top N
            most_used = sorted(
                assets_with_usage,
                key=lambda x: x["usage_count"],
                reverse=True
            )[:top_n]

            return {
                "total_assets": len(assets),
                "by_type": dict(by_type),
                "by_category": dict(by_category),
                "most_used": most_used,
                "queried_limit": limit,
                "is_truncated": len(assets) >= limit
            }

        except Exception as e:
            logger.error(f"Failed to get asset usage for user {user_id}: {e}")
            raise
