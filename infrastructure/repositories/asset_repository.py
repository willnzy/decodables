"""
Asset Repository - Asset management operations.

@module infrastructure.repositories.asset_repository
@version 2.0.0 (AsyncClient migration)

Changes in v2.0:
- Migrated all methods to use AsyncClient with await
- All .execute() calls now properly awaited

Provides all asset CRUD operations.
Inherits from BaseRepository for soft/hard delete support.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from core.database import retry_on_network_error
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class SupabaseAssetRepository(BaseRepository[Dict[str, Any]]):
    """
    Asset repository for assets table operations.

    Provides all methods needed for asset management.
    Inherits soft/hard delete operations from BaseRepository.

    Note: Uses Dict[str, Any] as entity type since there's no Asset domain entity.
    """

    @property
    def table_name(self) -> str:
        """Table name for assets."""
        return "assets"

    def _map_to_entity(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map database row to entity (passthrough for Dict).

        Since there's no Asset domain entity, we return the row as-is.
        """
        return row

    def _map_to_row(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map entity to database row (passthrough for Dict).

        Since there's no Asset domain entity, we return the entity as-is.
        """
        return entity

    @retry_on_network_error()
    async def save_asset(
        self,
        user_id: str,
        url: str,
        source: str,
        project_id: Optional[str] = None,
        prompt: Optional[str] = None,
        tz: str = "UTC",
        asset_type: str = "image",
        workspace_id: Optional[str] = None,
        folder_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Save new asset.

        Args:
            user_id: User ID
            url: Asset URL
            source: Asset source (upload, ai, system, marketplace)
            project_id: Optional project ID
            prompt: Optional prompt used to generate
            tz: Timezone
            asset_type: Asset type (image, video, audio, document). Defaults to 'image'.
            workspace_id: Optional workspace ID (v3.46: set at upload time)
            folder_id: Optional folder ID (v3.46: set at upload time)

        Returns:
            Created asset dict
        """
        insert_data = {
            "user_id": user_id,
            "url": url,
            "type": asset_type,  # Required NOT NULL field
            "source": source,
            "project_id": project_id,
            "prompt": prompt,
            "timezone": tz,
        }
        if workspace_id:
            insert_data["workspace_id"] = workspace_id
        if folder_id:
            insert_data["folder_id"] = folder_id

        result = await self.client.table("assets").insert(insert_data).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def get_assets(
        self,
        user_id: str,
        project_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get user assets (legacy, no pagination).

        Args:
            user_id: User ID
            project_id: Optional project ID filter

        Returns:
            List of asset dicts
        """
        query = self.client.table("assets").select("*").eq("user_id", user_id)

        if project_id:
            query = query.eq("project_id", project_id)

        result = await query.order("created_at", desc=True).execute()
        return result.data or []

    @retry_on_network_error()
    async def get_assets_paginated(
        self,
        user_id: str,
        project_id: Optional[str] = None,
        offset: int = 0,
        limit: int = 50
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Get user assets with pagination.

        Args:
            user_id: User ID
            project_id: Optional project ID filter
            offset: Number of items to skip
            limit: Max items to return

        Returns:
            Tuple of (list of asset dicts, total count)
        """
        # Build base query for non-deleted assets
        base_query = self.client.table("assets").select("*", count="exact").eq("user_id", user_id).is_("is_deleted", False)

        if project_id:
            base_query = base_query.eq("project_id", project_id)

        # Execute with pagination
        result = await base_query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()

        items = result.data or []
        total = result.count or 0

        return items, total

    @retry_on_network_error()
    async def delete_asset(self, asset_id: str, user_id: str) -> bool:
        """
        Soft delete an asset (mark as deleted).

        Uses BaseRepository.soft_delete() for soft deletion.
        For hard delete (physical removal), use hard_delete() method.

        Args:
            asset_id: Asset ID (UUID)
            user_id: User ID (for ownership check)

        Returns:
            True if deleted successfully
        """
        return await self.soft_delete(asset_id, user_id)

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
            result = await self.client.table("assets").select("*").eq(
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
        result = await self.client.table("assets").update({
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
        result = await self.client.table("assets").delete().eq(
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
        get_result = await self.client.table("assets").select("usage_count").eq(
            "id", asset_id
        ).eq("user_id", user_id).single().execute()

        if not get_result.data:
            return None

        current_count = get_result.data.get("usage_count", 0)
        new_count = current_count + 1

        # Update usage count
        update_result = await self.client.table("assets").update({
            "usage_count": new_count
        }).eq("id", asset_id).eq("user_id", user_id).execute()

        return update_result.data[0] if update_result.data else None

    # Legacy method removed - use list_deleted_recoverable() from BaseRepository instead
    # This automatically filters expired records and returns Entity + total count

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
        result = await self.client.table("assets").update({
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
        result = await self.client.table("assets").select("*").eq("user_id", user_id).execute()
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
            user_id: User ID (maps to seller_id in marketplace_listings)

        Returns:
            Seller stats dict with total_listings, total_sales, total_revenue, listings
        """
        # Note: marketplace_listings uses seller_id (not user_id) and price_credits (not price)
        result = await self.client.table("marketplace_listings").select(
            "id, title, price_credits, sales_count, created_at"
        ).eq("seller_id", user_id).eq("is_deleted", False).execute()

        listings_data = result.data or []
        total_sales = sum(l.get("sales_count", 0) for l in listings_data)
        total_revenue = sum(l.get("price_credits", 0) * l.get("sales_count", 0) for l in listings_data)

        return {
            "total_listings": len(listings_data),
            "total_sales": total_sales,
            "total_revenue": float(total_revenue),
            "listings": listings_data
        }

    @retry_on_network_error()
    async def get_dashboard_assets(
        self,
        user_id: str,
        workspace_id: Optional[str] = None,
        view_type: str = "all",
        offset: int = 0,
        limit: int = 15,
        search: Optional[str] = None,
        folder_id: Optional[str] = "NOT_SET",
    ) -> Dict[str, Any]:
        """
        Get assets for dashboard with view type filtering.

        v3.45: Added workspace_id filter for data isolation.

        Args:
            user_id: User ID
            workspace_id: Workspace ID for data isolation (optional for backward compat)
            view_type: "all", "bought", or "selling"
            offset: Number of records to skip
            limit: Items per page
            search: Search query (searches in name field)

        Returns:
            Dict with items, total, offset, limit, has_more, and counts for tabs
        """
        select_fields = "id, url, type, name, category, source, usage_count, prompt, description, metadata, is_purchased, source_listing_id, origin_owner_id, folder_id, is_starred, created_at, updated_at"

        # Handle "selling" view - query via marketplace_listings
        if view_type == "selling":
            # Get asset IDs from marketplace_listings where resource_type='asset'
            listings_result = await self.client.table("marketplace_listings").select(
                "resource_id"
            ).eq("seller_id", user_id).eq("resource_type", "asset").eq("is_deleted", False).execute()

            selling_asset_ids = [
                str(l["resource_id"]) for l in (listings_result.data or [])
                if l.get("resource_id")
            ]

            if not selling_asset_ids:
                items = []
                total = 0
            else:
                # Query assets by IDs
                query = self.client.table("assets").select(select_fields).in_(
                    "id", selling_asset_ids
                ).eq("is_deleted", False)

                # v3.45: Workspace isolation
                if workspace_id:
                    query = query.eq("workspace_id", workspace_id)

                # Apply folder filter
                if folder_id != "NOT_SET":
                    if folder_id is None:
                        query = query.is_("folder_id", "null")
                    else:
                        query = query.eq("folder_id", folder_id)

                if search and search.strip():
                    query = query.ilike("name", f"%{search.strip()}%")

                result = await query.order("created_at", desc=True).order("id", desc=True).range(offset, offset + limit - 1).execute()
                items = result.data or []

                # Count with same filters
                count_query = self.client.table("assets").select("id", count="exact").in_(
                    "id", selling_asset_ids
                ).eq("is_deleted", False)
                if workspace_id:
                    count_query = count_query.eq("workspace_id", workspace_id)
                if folder_id != "NOT_SET":
                    if folder_id is None:
                        count_query = count_query.is_("folder_id", "null")
                    else:
                        count_query = count_query.eq("folder_id", folder_id)
                if search and search.strip():
                    count_query = count_query.ilike("name", f"%{search.strip()}%")
                count_result = await count_query.execute()
                total = count_result.count or len(items)
        else:
            # Build base query for "all" and "bought" views
            query = self.client.table("assets").select(select_fields).eq(
                "user_id", user_id
            ).eq("is_deleted", False)

            # v3.45: Workspace isolation
            if workspace_id:
                query = query.eq("workspace_id", workspace_id)

            # Apply view type filter
            if view_type == "bought":
                query = query.eq("is_purchased", True)

            # Apply folder filter
            if folder_id != "NOT_SET":
                if folder_id is None:
                    query = query.is_("folder_id", "null")
                else:
                    query = query.eq("folder_id", folder_id)

            # Apply search filter
            if search and search.strip():
                query = query.ilike("name", f"%{search.strip()}%")

            # Execute query
            result = await query.order("created_at", desc=True).order("id", desc=True).range(offset, offset + limit - 1).execute()
            items = result.data or []

            # Get total count with same filters
            count_query = self.client.table("assets").select("id", count="exact").eq(
                "user_id", user_id
            ).eq("is_deleted", False)

            if workspace_id:
                count_query = count_query.eq("workspace_id", workspace_id)

            if view_type == "bought":
                count_query = count_query.eq("is_purchased", True)

            if folder_id != "NOT_SET":
                if folder_id is None:
                    count_query = count_query.is_("folder_id", "null")
                else:
                    count_query = count_query.eq("folder_id", folder_id)

            if search and search.strip():
                count_query = count_query.ilike("name", f"%{search.strip()}%")

            count_result = await count_query.execute()
            total = count_result.count or len(items)

        # Get counts for all view types (for tab badges)
        # All assets count
        all_count_query = self.client.table("assets").select("id", count="exact").eq(
            "user_id", user_id
        ).eq("is_deleted", False)
        if workspace_id:
            all_count_query = all_count_query.eq("workspace_id", workspace_id)
        all_count_result = await all_count_query.execute()
        all_count = all_count_result.count or 0

        # Bought assets count
        bought_count_query = self.client.table("assets").select("id", count="exact").eq(
            "user_id", user_id
        ).eq("is_deleted", False).eq("is_purchased", True)
        if workspace_id:
            bought_count_query = bought_count_query.eq("workspace_id", workspace_id)
        bought_count_result = await bought_count_query.execute()
        bought_count = bought_count_result.count or 0

        # Selling assets count (approved listings)
        selling_listings_result = await self.client.table("marketplace_listings").select(
            "resource_id", count="exact"
        ).eq("seller_id", user_id).eq("resource_type", "asset").eq(
            "is_deleted", False
        ).eq("moderation_status", "approved").execute()
        selling_count = selling_listings_result.count or 0

        counts = {
            "all": all_count,
            "bought": bought_count,
            "selling": selling_count,
        }

        return {
            "items": items,
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": offset + len(items) < total,
            "counts": counts,
        }

    # ==========================================
    # v3.33 Phase 2.6: Folder Organization and Starring
    # ==========================================

    @retry_on_network_error()
    async def move_to_folder(
        self,
        asset_id: str,
        user_id: str,
        folder_id: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Move asset to a folder (or root if folder_id is None).

        Args:
            asset_id: Asset ID
            user_id: User ID (for ownership check)
            folder_id: Target folder ID (None = move to root)

        Returns:
            Updated asset dict or None if not found/unauthorized
        """
        result = await self.client.table("assets").update({
            "folder_id": folder_id,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", asset_id).eq("user_id", user_id).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def toggle_star(
        self,
        asset_id: str,
        user_id: str,
        is_starred: bool
    ) -> Optional[Dict[str, Any]]:
        """
        Toggle asset starred status.

        Args:
            asset_id: Asset ID
            user_id: User ID (for ownership check)
            is_starred: New starred status

        Returns:
            Updated asset dict or None if not found/unauthorized
        """
        result = await self.client.table("assets").update({
            "is_starred": is_starred,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", asset_id).eq("user_id", user_id).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def get_by_folder(
        self,
        user_id: str,
        folder_id: Optional[str],
        offset: int = 0,
        limit: int = 50,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get assets in a specific folder.

        Args:
            user_id: User ID
            folder_id: Folder ID (None = root/unfiled)
            offset: Number of records to skip
            limit: Number of records to return
            search: Optional search query

        Returns:
            List of asset dicts
        """
        query = self.client.table("assets").select("*").eq(
            "user_id", user_id
        ).eq("is_deleted", False)

        if folder_id is None:
            query = query.is_("folder_id", "null")
        else:
            query = query.eq("folder_id", folder_id)

        if search and search.strip():
            query = query.ilike("name", f"%{search.strip()}%")

        result = await query.order("is_starred", desc=True).order(
            "created_at", desc=True
        ).range(offset, offset + limit - 1).execute()

        return result.data or []

    @retry_on_network_error()
    async def get_starred(
        self,
        user_id: str,
        offset: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get starred assets.

        Args:
            user_id: User ID
            offset: Number of records to skip
            limit: Number of records to return

        Returns:
            List of starred asset dicts
        """
        result = await self.client.table("assets").select("*").eq(
            "user_id", user_id
        ).eq("is_deleted", False).eq("is_starred", True).order(
            "created_at", desc=True
        ).range(offset, offset + limit - 1).execute()

        return result.data or []
