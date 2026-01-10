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

    @retry_on_network_error()
    async def soft_delete_asset(self, asset_id: str, user_id: str) -> bool:
        """
        Soft delete an asset (mark as deleted).

        Args:
            asset_id: Asset ID
            user_id: User ID (for ownership check)

        Returns:
            True if deleted
        """
        result = self.client.table("assets").update({
            "is_deleted": True
        }).eq("id", asset_id).eq("user_id", user_id).execute()

        return len(result.data) > 0 if result.data else False

    @retry_on_network_error()
    async def permanently_hide_asset(self, asset_id: str, user_id: str) -> bool:
        """
        Permanently hide an asset (hard delete from user perspective).

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
    async def increment_asset_usage(self, asset_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Increment usage count for an asset.

        Args:
            asset_id: Asset ID
            user_id: User ID (for ownership check)

        Returns:
            Updated asset dict with new usage_count
        """
        # Get current asset
        get_result = self.client.table("assets").select("usage_count").eq(
            "id", asset_id
        ).eq("user_id", user_id).single().execute()

        if not get_result.data:
            return None

        current_count = get_result.data.get("usage_count", 0)
        new_count = current_count + 1

        # Update usage count
        update_result = self.client.table("assets").update({
            "usage_count": new_count
        }).eq("id", asset_id).eq("user_id", user_id).execute()

        return update_result.data[0] if update_result.data else None

    @retry_on_network_error()
    async def get_deleted_assets(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get soft-deleted assets (trash).

        Args:
            user_id: User ID

        Returns:
            List of deleted asset dicts
        """
        result = self.client.table("assets").select("*").eq(
            "user_id", user_id
        ).eq("is_deleted", True).order("created_at", desc=True).execute()

        return result.data or []

    @retry_on_network_error()
    async def restore_asset(self, asset_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Restore a soft-deleted asset.

        Args:
            asset_id: Asset ID
            user_id: User ID (for ownership check)

        Returns:
            Restored asset dict
        """
        result = self.client.table("assets").update({
            "is_deleted": False
        }).eq("id", asset_id).eq("user_id", user_id).eq("is_deleted", True).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def get_dashboard_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get asset dashboard statistics.

        Args:
            user_id: User ID

        Returns:
            Dashboard stats dict with total_assets, total_usage, by_source, recent
        """
        result = self.client.table("assets").select("*").eq("user_id", user_id).execute()
        assets_data = result.data or []

        total_assets = len(assets_data)
        total_usage = sum(a.get("usage_count", 0) for a in assets_data)

        # Aggregate by source
        by_source = {}
        for asset in assets_data:
            src = asset.get("source", "unknown")
            by_source[src] = by_source.get(src, 0) + 1

        # Get recent 10
        recent = sorted(
            assets_data,
            key=lambda x: x.get("created_at", ""),
            reverse=True
        )[:10]

        return {
            "total_assets": total_assets,
            "total_usage": total_usage,
            "by_source": by_source,
            "recent": recent
        }

    @retry_on_network_error()
    async def get_seller_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get seller marketplace statistics.

        Args:
            user_id: User ID

        Returns:
            Seller stats dict with total_listings, total_sales, total_revenue, listings
        """
        result = self.client.table("marketplace_listings").select(
            "id, title, price, sales_count, created_at"
        ).eq("user_id", user_id).eq("is_deleted", False).execute()

        listings_data = result.data or []
        total_sales = sum(l.get("sales_count", 0) for l in listings_data)
        total_revenue = sum(l.get("price", 0) * l.get("sales_count", 0) for l in listings_data)

        return {
            "total_listings": len(listings_data),
            "total_sales": total_sales,
            "total_revenue": total_revenue,
            "listings": listings_data
        }
