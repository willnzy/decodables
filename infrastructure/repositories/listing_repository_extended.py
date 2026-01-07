"""
Listing Repository Extended - Additional methods for services/db migration.

@module infrastructure.repositories.listing_repository_extended
@version 1.0.0

Extends SupabaseListingRepository with additional methods needed for
backward compatibility with services/db/marketplace.py functions.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from core.database import DatabaseClient, retry_on_network_error

logger = logging.getLogger(__name__)


class SupabaseListingRepositoryExtended:
    """
    Extended listing repository with additional methods for marketplace_listings table.

    This repository works directly with the "marketplace_listings" and
    "marketplace_purchases" tables and provides all methods needed to replace
    services/db/marketplace.py functions.
    """

    def __init__(self, client: DatabaseClient):
        """
        Initialize repository with database client.

        Args:
            client: Supabase database client
        """
        self.client = client

    @retry_on_network_error()
    async def get_marketplace_listings(
        self,
        featured: bool = False,
        resource_type: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
        sort: str = "latest",
        tier_filter: Optional[str] = None,
        price_filter: Optional[str] = None,
        mine: bool = False,
        user_id: Optional[str] = None,
        user_tier: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get marketplace listings with filtering and sorting.

        Business Rules:
        - Public list: moderation_status='approved' AND is_public=true AND is_deleted=false
        - mine=true: Returns all statuses for owner

        Args:
            featured: Whether to show featured listings
            resource_type: Filter by resource type
            page: Page number
            limit: Items per page
            sort: Sort method (latest/popular/best_selling)
            tier_filter: Tier filter (all/free/starter/pro)
            price_filter: Price filter (all/free/paid)
            mine: Show own listings
            user_id: User ID for mine mode
            user_tier: User tier (for compatibility)

        Returns:
            List of listing dicts
        """
        start = (page - 1) * limit
        end = start + limit - 1

        # Explicitly specify seller relationship
        query = self.client.table("marketplace_listings").select(
            "*, profiles!marketplace_listings_seller_id_fkey(username, avatar_url)"
        )

        if mine and user_id:
            # Seller views own listings (all statuses)
            query = query.eq("seller_id", user_id).eq("is_deleted", False)
        else:
            # Public list: Must be approved + public + not deleted
            query = query.eq("is_public", True).eq("is_deleted", False).eq(
                "moderation_status", "approved"
            )

        # Resource type filter
        if resource_type:
            query = query.eq("resource_type", resource_type)

        # Tier filter
        if tier_filter and tier_filter != "all":
            query = query.contains("allowed_tiers", [tier_filter])

        # Price filter
        if price_filter == "free":
            query = query.eq("price_credits", 0)
        elif price_filter == "paid":
            query = query.gt("price_credits", 0)

        # Sorting
        if featured or sort == "best_selling":
            query = query.order("sales_count", desc=True)
        elif sort == "popular":
            query = query.order("usage_count", desc=True)
        else:  # latest
            query = query.order("created_at", desc=True)

        result = query.range(start, end).execute()
        return result.data or []

    @retry_on_network_error()
    async def get_marketplace_item(
        self,
        listing_id: str,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get single listing detail.

        Business Rules:
        - Public access: Only approved + public + not deleted
        - Seller access: Own listing in any status

        Args:
            listing_id: Listing ID
            user_id: User ID for access check

        Returns:
            Listing dict or None
        """
        res = self.client.table("marketplace_listings").select(
            "*, profiles!marketplace_listings_seller_id_fkey(username, avatar_url)"
        ).eq("id", listing_id).single().execute()

        if not res.data:
            return None

        listing = res.data

        # Check access permission
        is_seller = user_id and listing.get("seller_id") == user_id
        is_visible = self._is_public_visible(listing)

        if not is_seller and not is_visible:
            return None

        # Check if user has purchased
        if user_id:
            purchase = self.client.table("marketplace_purchases").select("id").eq(
                "buyer_id", user_id
            ).eq("listing_id", listing_id).execute()
            listing["is_purchased"] = bool(purchase.data)

        return listing

    def _is_public_visible(self, listing: Dict[str, Any]) -> bool:
        """Check if listing is publicly visible."""
        return (
            listing.get("is_public", False)
            and not listing.get("is_deleted", False)
            and listing.get("moderation_status") == "approved"
        )

    @retry_on_network_error()
    async def get_seller_listings(
        self,
        seller_id: str,
        page: int = 1,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get seller's own listings.

        Args:
            seller_id: Seller user ID
            page: Page number
            limit: Items per page

        Returns:
            List of listing dicts
        """
        start = (page - 1) * limit
        end = start + limit - 1

        result = self.client.table("marketplace_listings").select("*").eq(
            "seller_id", seller_id
        ).eq("is_deleted", False).order("created_at", desc=True).range(start, end).execute()

        return result.data or []

    @retry_on_network_error()
    async def create_listing(
        self,
        seller_id: str,
        title: str,
        description: str,
        thumbnail_url: str,
        resource_url: str,
        resource_type: str,
        price_credits: int,
        allowed_tiers: Optional[list] = None,
        submit_for_review: bool = True,
        resource_id: Optional[str] = None,
        version: str = "1.0",
        changelog: str = "",
        timezone_str: str = "UTC"
    ) -> Optional[Dict[str, Any]]:
        """
        Create or update listing.

        If a listing already exists for this resource, update it with new version.

        Args:
            seller_id: Seller user ID
            title: Listing title
            description: Description
            thumbnail_url: Thumbnail URL
            resource_url: Resource URL
            resource_type: Resource type (asset/project)
            price_credits: Price in credits
            allowed_tiers: Allowed tiers list
            submit_for_review: Submit for review immediately
            resource_id: Resource ID
            version: Version number
            changelog: Version changelog
            timezone_str: Timezone

        Returns:
            Created/updated listing dict
        """
        # Check if listing already exists for this resource
        existing_query = self.client.table("marketplace_listings").select("*").eq(
            "seller_id", seller_id
        ).eq("is_deleted", False)

        # Try to find by resource_id first, then by resource_url
        if resource_id:
            existing_query = existing_query.eq("resource_id", resource_id)
        else:
            existing_query = existing_query.eq("resource_url", resource_url)

        existing_res = existing_query.execute()
        existing_listing = existing_res.data[0] if existing_res.data else None

        if existing_listing:
            # Update existing listing with new version
            current_history = existing_listing.get("version_history") or []

            # Add new version to history
            new_entry = {
                "version": version,
                "changelog": changelog,
                "published_at": datetime.now(timezone.utc).isoformat(),
            }
            current_history.append(new_entry)

            update_data = {
                "title": title,
                "description": description,
                "thumbnail_url": thumbnail_url,
                "price_credits": price_credits,
                "allowed_tiers": allowed_tiers or ["free"],
                "version": version,
                "changelog": changelog,
                "version_history": current_history,
                "moderation_status": "pending" if submit_for_review else "draft",
                "moderation_note": None,
                "is_public": True,
            }

            res = self.client.table("marketplace_listings").update(update_data).eq(
                "id", existing_listing["id"]
            ).execute()
            return res.data[0] if res.data else None

        # Create new listing
        version_history = [
            {
                "version": version,
                "changelog": changelog,
                "published_at": datetime.now(timezone.utc).isoformat(),
            }
        ]

        data = {
            "seller_id": seller_id,
            "title": title,
            "description": description,
            "thumbnail_url": thumbnail_url,
            "resource_url": resource_url,
            "resource_id": resource_id,
            "resource_type": resource_type,
            "price_credits": price_credits,
            "allowed_tiers": allowed_tiers or ["free"],
            "is_public": True,
            "is_deleted": False,
            "sales_count": 0,
            "usage_count": 0,
            "moderation_status": "pending" if submit_for_review else "draft",
            "moderation_note": None,
            "moderated_by": None,
            "moderated_at": None,
            "version": version,
            "changelog": changelog,
            "version_history": version_history,
            "timezone": timezone_str,
        }
        res = self.client.table("marketplace_listings").insert(data).execute()
        return res.data[0] if res.data else None

    @retry_on_network_error()
    async def submit_listing_for_review(
        self,
        listing_id: str,
        seller_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Submit listing for review.

        Args:
            listing_id: Listing ID
            seller_id: Seller ID for ownership check

        Returns:
            Updated listing dict
        """
        query = self.client.table("marketplace_listings").update({
            "moderation_status": "pending",
            "is_public": True,
            "submitted_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", listing_id)

        if seller_id:
            query = query.eq("seller_id", seller_id)

        result = query.execute()
        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def unpublish_listing(
        self,
        listing_id: str,
        seller_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Unpublish listing.

        Sets is_public=false while preserving purchases and usage_count.

        Args:
            listing_id: Listing ID
            seller_id: Seller ID for ownership check

        Returns:
            Updated listing dict
        """
        result = self.client.table("marketplace_listings").update({
            "is_public": False
        }).eq("id", listing_id).eq("seller_id", seller_id).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def update_listing(
        self,
        listing_id: str,
        seller_id: str,
        updates: dict
    ) -> Optional[Dict[str, Any]]:
        """
        Update listing.

        Args:
            listing_id: Listing ID
            seller_id: Seller ID for ownership check
            updates: Update dict

        Returns:
            Updated listing dict
        """
        result = self.client.table("marketplace_listings").update(updates).eq(
            "id", listing_id
        ).eq("seller_id", seller_id).execute()

        return result.data[0] if result.data else None

    async def check_user_purchase(
        self,
        user_id: str,
        listing_id: str
    ) -> bool:
        """
        Check if user has purchased listing.

        Args:
            user_id: User ID
            listing_id: Listing ID

        Returns:
            True if purchased
        """
        result = self.client.table("marketplace_purchases").select("id").eq(
            "buyer_id", user_id
        ).eq("listing_id", listing_id).execute()
        return bool(result.data)

    @retry_on_network_error()
    async def execute_purchase(
        self,
        buyer_id: str,
        listing_id: str,
        tz: str = "UTC"
    ) -> dict:
        """
        Execute marketplace purchase using atomic RPC.

        Business Rule: Uses atomic RPC to ensure credit deduction and purchase recording.

        Args:
            buyer_id: Buyer user ID
            listing_id: Listing ID
            tz: Timezone

        Returns:
            Result dict with success status
        """
        try:
            result = self.client.rpc("execute_marketplace_purchase", {
                "p_buyer_id": buyer_id,
                "p_listing_id": listing_id,
                "p_timezone": tz
            }).execute()

            if result.data:
                return {"success": True, "data": result.data}
            return {"success": False, "error": "RPC returned no data"}
        except Exception as e:
            error_str = str(e)
            if "INSUFFICIENT" in error_str:
                return {"success": False, "error": "INSUFFICIENT_CREDITS"}
            if "ALREADY_PURCHASED" in error_str:
                return {"success": False, "error": "ALREADY_PURCHASED"}
            logger.error(f"execute_purchase failed: {e}")
            return {"success": False, "error": error_str}

    @retry_on_network_error()
    async def get_user_purchases(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get user's purchases.

        Args:
            user_id: User ID
            page: Page number
            limit: Items per page

        Returns:
            List of purchase dicts with listing info
        """
        offset = (page - 1) * limit
        result = self.client.table("marketplace_purchases").select(
            "*, marketplace_listings(id, title, resource_type, thumbnail_url)"
        ).eq("buyer_id", user_id).order("purchased_at", desc=True).range(
            offset, offset + limit - 1
        ).execute()

        return result.data or []

    @retry_on_network_error()
    async def get_seller_stats(
        self,
        seller_id: str
    ) -> Dict[str, Any]:
        """
        Get seller statistics.

        Args:
            seller_id: Seller user ID

        Returns:
            Dict with total_listings, total_sales, total_usage, total_revenue, total_earned_credits
        """
        listings = self.client.table("marketplace_listings").select(
            "id, price_credits, sales_count, usage_count"
        ).eq("seller_id", seller_id).eq("is_deleted", False).execute()

        data = listings.data or []
        total_sales = sum(l.get("sales_count", 0) for l in data)
        total_usage = sum(l.get("usage_count", 0) for l in data)
        total_revenue = sum(l.get("price_credits", 0) * l.get("sales_count", 0) for l in data)

        return {
            "total_listings": len(data),
            "total_sales": total_sales,
            "total_usage": total_usage,
            "total_revenue": total_revenue,
            "total_earned_credits": int(total_revenue * 0.9),  # 90% seller revenue
        }

    @retry_on_network_error()
    async def record_listing_usage(
        self,
        listing_id: str,
        used_by_user_id: str,
        project_id: str
    ) -> bool:
        """
        Record listing usage.

        Args:
            listing_id: Listing ID
            used_by_user_id: User who used the listing
            project_id: Project ID where used

        Returns:
            True if successful
        """
        try:
            self.client.table("listing_usages").insert({
                "listing_id": listing_id,
                "used_by_user_id": used_by_user_id,
                "project_id": project_id,
            }).execute()
            return True
        except:
            return False

    @retry_on_network_error()
    async def get_leaderboard(
        self,
        period: str = "monthly",
        board_type: str = "all",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get marketplace leaderboard.

        Returns top listings with usage_count and rank (approved + public + not deleted only).

        Args:
            period: Period (currently unused, for future use)
            board_type: Board type (all/asset/project)
            limit: Number of items

        Returns:
            List of listing dicts with rank
        """
        query = self.client.table("marketplace_listings").select(
            "id, title, thumbnail_url, usage_count, sales_count, resource_type, seller_id, "
            "profiles!marketplace_listings_seller_id_fkey(username, avatar_url)"
        ).eq("is_public", True).eq("is_deleted", False).eq("moderation_status", "approved")

        # Filter by type
        if board_type and board_type != "all":
            query = query.eq("resource_type", board_type)

        # Sort by usage_count
        query = query.order("usage_count", desc=True).limit(limit)

        result = query.execute()
        items = result.data or []

        # Add rank
        for i, item in enumerate(items):
            item["rank"] = i + 1

        return items
