"""
Asset Repository Extended - Additional methods for services/db migration.

@module infrastructure.repositories.asset_repository_extended
@version 1.0.0

Provides all asset CRUD operations needed to replace services/db/assets.py.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from core.database import retry_on_network_error

logger = logging.getLogger(__name__)


class SupabaseAssetRepositoryExtended:
    """
    Extended asset repository for assets table operations.

    Provides all methods needed to replace services/db/assets.py functions.
    """

    def __init__(self, client):
        """
        Initialize repository with database client.

        Args:
            client: Supabase database client
        """
        self.client = client

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
        query = self.client.table("assets").select("*").eq(
            "user_id", user_id
        ).eq("is_deleted", False)

        if project_id:
            query = query.eq("project_id", project_id)

        result = query.order("created_at", desc=True).execute()
        return result.data or []

    @retry_on_network_error()
    async def soft_delete_asset(
        self,
        asset_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Soft delete asset.

        Args:
            asset_id: Asset ID
            user_id: User ID (for ownership check)

        Returns:
            Updated asset dict
        """
        result = self.client.table("assets").update({
            "is_deleted": True,
            "deleted_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", asset_id).eq("user_id", user_id).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def permanently_hide_asset(
        self,
        asset_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Permanently hide asset (stage 2 delete).

        Args:
            asset_id: Asset ID
            user_id: User ID (for ownership check)

        Returns:
            Updated asset dict
        """
        result = self.client.table("assets").update({
            "is_permanently_deleted": True
        }).eq("id", asset_id).eq("user_id", user_id).eq("is_deleted", True).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def restore_asset(
        self,
        asset_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Restore soft-deleted asset.

        Args:
            asset_id: Asset ID
            user_id: User ID (for ownership check)

        Returns:
            Updated asset dict
        """
        result = self.client.table("assets").update({
            "is_deleted": False,
            "deleted_at": None
        }).eq("id", asset_id).eq("user_id", user_id).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def get_deleted_assets(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get user's deleted assets.

        Args:
            user_id: User ID
            page: Page number
            limit: Items per page

        Returns:
            List of deleted asset dicts
        """
        offset = (page - 1) * limit
        result = self.client.table("assets").select(
            "id, url, source, deleted_at"
        ).eq("user_id", user_id).eq("is_deleted", True).eq(
            "is_permanently_deleted", False
        ).order("deleted_at", desc=True).range(offset, offset + limit - 1).execute()

        return result.data or []

    @retry_on_network_error()
    async def increment_asset_usage(
        self,
        asset_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Increment asset usage count.

        Args:
            asset_id: Asset ID
            user_id: User ID

        Returns:
            Updated asset dict
        """
        # Get current count
        asset = self.client.table("assets").select("usage_count").eq("id", asset_id).execute()
        if not asset.data:
            return None

        current = asset.data[0].get("usage_count", 0)

        result = self.client.table("assets").update({
            "usage_count": current + 1
        }).eq("id", asset_id).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def get_dashboard_assets(
        self,
        user_id: str,
        view: str = "all",
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get assets for dashboard.

        Args:
            user_id: User ID
            view: View type (currently unused, for future expansion)
            page: Page number
            limit: Items per page

        Returns:
            Dict with items and total count
        """
        offset = (page - 1) * limit

        query = self.client.table("assets").select("*", count="exact").eq(
            "user_id", user_id
        ).eq("is_deleted", False)

        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()

        return {"items": result.data or [], "total": result.count or 0}

    @retry_on_network_error()
    async def get_seller_asset_stats(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get seller statistics for assets.

        Args:
            user_id: User ID

        Returns:
            Dict with total_listings, total_sales, total_revenue
        """
        listings = self.client.table("marketplace_listings").select(
            "id, price, sales_count"
        ).eq("user_id", user_id).neq("resource_type", "project").execute()

        data = listings.data or []
        total_sales = sum(l.get("sales_count", 0) for l in data)
        total_revenue = sum(l.get("price", 0) * l.get("sales_count", 0) for l in data)

        return {
            "total_listings": len(data),
            "total_sales": total_sales,
            "total_revenue": total_revenue
        }

    async def get_system_resources(
        self,
        resource_type: str = "sticker",
        user_tier: str = "free"
    ) -> List[Dict[str, Any]]:
        """
        Get system resources by type.

        Args:
            resource_type: Resource type (sticker, etc.)
            user_tier: User tier (for future filtering)

        Returns:
            List of system resource dicts
        """
        result = self.client.table("system_resources").select("*").eq(
            "resource_type", resource_type
        ).eq("is_active", True).order("sort_order").execute()

        return result.data or []
