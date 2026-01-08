"""
Listing Repository Implementation - Supabase data access for marketplace domain.

@module infrastructure.repositories.listing_repository
@version 1.0.0

Implements IListingRepository using Supabase PostgreSQL.
"""

from typing import Optional, List
from datetime import datetime, timedelta
import logging

from domains.marketplace.repository import IListingRepository
from domains.marketplace.aggregates.listing import Listing
from domains.marketplace.value_objects import (
    ListingStatus,
    ResourceType,
    AssetCategory,
    ListingSource,
    PriceType,
    ListingMetadata,
    ListingStats,
    ListingSortOrder,
    PriceFilter,
)
from domains.marketplace.exceptions import ListingNotFoundException
from core.database import get_supabase_client

logger = logging.getLogger(__name__)


class SupabaseListingRepository(IListingRepository):
    """
    Supabase implementation of listing repository.
    """

    def __init__(self, client=None):
        """Initialize repository with Supabase client."""
        self._client = client

    @property
    def client(self):
        """Lazy load Supabase client."""
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    async def get_by_id(self, listing_id: str) -> Optional[Listing]:
        """Get listing by ID."""
        try:
            result = self.client.table("marketplace_listings").select("*").eq(
                "listing_id", listing_id
            ).single().execute()

            if not result.data:
                return None

            return self._map_to_listing(result.data)

        except Exception as e:
            logger.error(f"Failed to get listing {listing_id}: {e}")
            return None

    async def save(self, listing: Listing) -> Listing:
        """Persist listing (upsert)."""
        try:
            data = self._map_to_row(listing)
            self.client.table("marketplace_listings").upsert(
                data, on_conflict="listing_id"
            ).execute()

            return listing

        except Exception as e:
            logger.error(f"Failed to save listing {listing.listing_id}: {e}")
            raise

    async def create(self, listing: Listing) -> Listing:
        """Create a new listing."""
        try:
            data = self._map_to_row(listing)
            self.client.table("marketplace_listings").insert(data).execute()

            return listing

        except Exception as e:
            logger.error(f"Failed to create listing {listing.listing_id}: {e}")
            raise

    async def update(self, listing: Listing) -> Listing:
        """Update existing listing."""
        try:
            data = self._map_to_row(listing)
            data["updated_at"] = datetime.utcnow().isoformat()

            result = self.client.table("marketplace_listings").update(data).eq(
                "listing_id", listing.listing_id
            ).select("*").single().execute()

            if not result.data:
                raise ListingNotFoundException(listing.listing_id)

            return listing

        except ListingNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Failed to update listing {listing.listing_id}: {e}")
            raise

    async def delete(self, listing_id: str) -> bool:
        """Delete a listing."""
        try:
            result = self.client.table("marketplace_listings").delete().eq(
                "listing_id", listing_id
            ).execute()

            return len(result.data) > 0 if result.data else False

        except Exception as e:
            logger.error(f"Failed to delete listing {listing_id}: {e}")
            return False

    async def get_by_seller(
        self,
        seller_id: str,
        status: Optional[ListingStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Listing]:
        """Get listings by seller."""
        try:
            query = self.client.table("marketplace_listings").select("*").eq(
                "seller_id", seller_id
            ).order("updated_at", desc=True).range(offset, offset + limit - 1)

            if status:
                query = query.eq("status", status.value)

            result = query.execute()

            return [self._map_to_listing(row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to get listings for seller {seller_id}: {e}")
            return []

    async def get_published(
        self,
        category: Optional[AssetCategory] = None,
        price_type: Optional[PriceType] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Listing]:
        """Get published listings."""
        try:
            query = self.client.table("marketplace_listings").select("*").eq(
                "status", ListingStatus.PUBLISHED.value
            ).order("published_at", desc=True).range(offset, offset + limit - 1)

            if category:
                query = query.eq("category", category.value)
            if price_type:
                query = query.eq("price_type", price_type.value)
            if tags:
                query = query.contains("tags", tags)

            result = query.execute()

            return [self._map_to_listing(row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to get published listings: {e}")
            return []

    async def get_featured(self, limit: int = 10) -> List[Listing]:
        """Get featured listings."""
        try:
            result = self.client.table("marketplace_listings").select("*").eq(
                "status", ListingStatus.PUBLISHED.value
            ).eq("is_featured", True).order(
                "published_at", desc=True
            ).limit(limit).execute()

            return [self._map_to_listing(row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to get featured listings: {e}")
            return []

    async def get_pending_review(self, limit: int = 50) -> List[Listing]:
        """Get listings pending review."""
        try:
            result = self.client.table("marketplace_listings").select("*").eq(
                "status", ListingStatus.PENDING_REVIEW.value
            ).order("created_at").limit(limit).execute()

            return [self._map_to_listing(row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to get pending listings: {e}")
            return []

    async def search(
        self,
        query: str,
        category: Optional[AssetCategory] = None,
        price_type: Optional[PriceType] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Listing]:
        """Search listings."""
        try:
            db_query = self.client.table("marketplace_listings").select("*").eq(
                "status", ListingStatus.PUBLISHED.value
            ).or_(f"title.ilike.%{query}%,description.ilike.%{query}%").order(
                "view_count", desc=True
            ).range(offset, offset + limit - 1)

            if category:
                db_query = db_query.eq("category", category.value)
            if price_type:
                db_query = db_query.eq("price_type", price_type.value)

            result = db_query.execute()

            return [self._map_to_listing(row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to search listings: {e}")
            return []

    async def search_with_filters(
        self,
        query: str = "",
        category: Optional[AssetCategory] = None,
        price_filter: Optional[PriceFilter] = None,
        sort_by: ListingSortOrder = ListingSortOrder.LATEST,
        tier_filter: Optional[str] = None,
        featured: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[Listing], int]:
        """
        Search listings with advanced filtering and sorting.

        Reuses logic from get_marketplace_listings but returns Listing objects.
        """
        try:
            # Build base query for published, public, non-deleted listings
            db_query = self.client.table("marketplace_listings").select(
                "*", count="exact"
            ).eq("is_public", True).eq("is_deleted", False).eq(
                "moderation_status", "approved"
            )

            # Text search filter
            if query:
                db_query = db_query.or_(
                    f"title.ilike.%{query}%,description.ilike.%{query}%"
                )

            # Category filter (resource_type in DB)
            if category:
                db_query = db_query.eq("resource_type", category.value)

            # Tier filter
            if tier_filter and tier_filter != "all":
                db_query = db_query.contains("allowed_tiers", [tier_filter])

            # Price filter
            if price_filter:
                if price_filter == PriceFilter.FREE:
                    db_query = db_query.eq("price_credits", 0)
                elif price_filter == PriceFilter.PAID:
                    db_query = db_query.gt("price_credits", 0)
                # PriceFilter.ALL - no filter needed

            # Sorting
            if featured or sort_by == ListingSortOrder.BEST_SELLING:
                db_query = db_query.order("sales_count", desc=True)
            elif sort_by == ListingSortOrder.POPULAR:
                db_query = db_query.order("usage_count", desc=True)
            elif sort_by == ListingSortOrder.PRICE_ASC:
                db_query = db_query.order("price_credits", desc=False)
            elif sort_by == ListingSortOrder.PRICE_DESC:
                db_query = db_query.order("price_credits", desc=True)
            else:  # LATEST (default)
                db_query = db_query.order("created_at", desc=True)

            # Pagination
            db_query = db_query.range(offset, offset + limit - 1)

            result = db_query.execute()

            # Get total count from response
            total_count = result.count if result.count is not None else len(result.data)

            # Map to Listing objects
            listings = [self._map_to_listing(row) for row in result.data]

            return listings, total_count

        except Exception as e:
            logger.error(f"Failed to search listings with filters: {e}")
            return [], 0

    async def get_popular(
        self,
        category: Optional[AssetCategory] = None,
        days: int = 30,
        limit: int = 50
    ) -> List[Listing]:
        """Get popular listings."""
        try:
            since = (datetime.utcnow() - timedelta(days=days)).isoformat()

            query = self.client.table("marketplace_listings").select("*").eq(
                "status", ListingStatus.PUBLISHED.value
            ).gte("published_at", since).order(
                "download_count", desc=True
            ).limit(limit)

            if category:
                query = query.eq("category", category.value)

            result = query.execute()

            return [self._map_to_listing(row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to get popular listings: {e}")
            return []

    async def record_purchase(
        self,
        listing_id: str,
        buyer_id: str,
        credit_amount: int = 0
    ) -> bool:
        """Record a purchase."""
        try:
            # Insert purchase record
            self.client.table("marketplace_purchases").insert({
                "listing_id": listing_id,
                "buyer_id": buyer_id,
                "credit_amount": credit_amount,
                "purchased_at": datetime.utcnow().isoformat(),
            }).execute()

            # Increment purchase count
            self.client.rpc("increment_listing_stat", {
                "p_listing_id": listing_id,
                "p_stat": "purchase_count",
            }).execute()

            return True

        except Exception as e:
            logger.error(f"Failed to record purchase for listing {listing_id}: {e}")
            return False

    async def has_purchased(
        self,
        listing_id: str,
        user_id: str
    ) -> bool:
        """Check if user has purchased listing."""
        try:
            result = self.client.table("marketplace_purchases").select(
                "id"
            ).eq("listing_id", listing_id).eq("buyer_id", user_id).single().execute()

            return result.data is not None

        except Exception:
            return False

    async def get_user_purchases(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Listing]:
        """Get listings purchased by user."""
        try:
            # Get purchase records
            purchases = self.client.table("marketplace_purchases").select(
                "listing_id"
            ).eq("buyer_id", user_id).order(
                "purchased_at", desc=True
            ).range(offset, offset + limit - 1).execute()

            if not purchases.data:
                return []

            listing_ids = [p["listing_id"] for p in purchases.data]

            # Get listings
            result = self.client.table("marketplace_listings").select("*").in_(
                "listing_id", listing_ids
            ).execute()

            return [self._map_to_listing(row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to get purchases for user {user_id}: {e}")
            return []

    def _map_to_listing(self, row: dict) -> Listing:
        """Map database row to Listing."""
        metadata = ListingMetadata(
            title=row.get("title", "Untitled"),
            description=row.get("description"),
            tags=row.get("tags", []),
            preview_url=row.get("preview_url", ""),
            thumbnail_url=row.get("thumbnail_url"),
            file_url=row.get("file_url", ""),
            file_size=row.get("file_size", 0),
            file_format=row.get("file_format", ""),
            dimensions=row.get("dimensions"),
            license_type=row.get("license_type", "standard"),
        )

        stats = ListingStats(
            view_count=row.get("view_count", 0),
            download_count=row.get("download_count", 0),
            like_count=row.get("like_count", 0),
            purchase_count=row.get("purchase_count", 0),
            rating_average=row.get("rating_average", 0.0),
            rating_count=row.get("rating_count", 0),
        )

        # Parse resource_type with fallback
        resource_type_str = row.get("resource_type", "asset")
        try:
            resource_type = ResourceType(resource_type_str)
        except ValueError:
            resource_type = ResourceType.ASSET

        # Parse category with fallback
        category_str = row.get("category", "element")
        try:
            category = AssetCategory(category_str)
        except ValueError:
            category = AssetCategory.ELEMENT

        # Parse source with fallback
        source_str = row.get("source", "user")
        try:
            source = ListingSource(source_str)
        except ValueError:
            source = ListingSource.USER

        # Parse allowed_tiers
        allowed_tiers = row.get("allowed_tiers", ["free", "starter", "pro"])
        if isinstance(allowed_tiers, str):
            allowed_tiers = [allowed_tiers]

        return Listing(
            listing_id=row["listing_id"],
            seller_id=row["seller_id"],
            resource_type=resource_type,
            category=category,
            metadata=metadata,
            source=source,
            price_type=PriceType(row.get("price_type", "free")),
            credit_price=row.get("credit_price", 0),
            allowed_tiers=allowed_tiers,
            status=ListingStatus(row.get("status", "draft")),
            stats=stats,
            is_featured=row.get("is_featured", False),
            rejection_reason=row.get("rejection_reason"),
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
                if row.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00"))
                if row.get("updated_at") else datetime.utcnow(),
            published_at=datetime.fromisoformat(row["published_at"].replace("Z", "+00:00"))
                if row.get("published_at") else None,
        )

    def _map_to_row(self, listing: Listing) -> dict:
        """Map Listing to database row."""
        return {
            "listing_id": listing.listing_id,
            "seller_id": listing.seller_id,
            "resource_type": listing.resource_type.value,
            "category": listing.category.value,
            "source": listing.source.value,
            "title": listing.metadata.title,
            "description": listing.metadata.description,
            "tags": listing.metadata.tags,
            "preview_url": listing.metadata.preview_url,
            "thumbnail_url": listing.metadata.thumbnail_url,
            "file_url": listing.metadata.file_url,
            "file_size": listing.metadata.file_size,
            "file_format": listing.metadata.file_format,
            "dimensions": listing.metadata.dimensions,
            "license_type": listing.metadata.license_type,
            "price_type": listing.price_type.value,
            "credit_price": listing.credit_price,
            "allowed_tiers": listing.allowed_tiers,
            "status": listing.status.value,
            "is_featured": listing.is_featured,
            "rejection_reason": listing.rejection_reason,
            "view_count": listing.stats.view_count,
            "download_count": listing.stats.download_count,
            "like_count": listing.stats.like_count,
            "purchase_count": listing.stats.purchase_count,
            "published_at": listing.published_at.isoformat() if listing.published_at else None,
        }

    # ==========================================
    # Extended Methods (from listing_repository_extended)
    # ==========================================

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
    ) -> List[dict]:
        """
        Get marketplace listings with filtering and sorting.

        Business Rules:
        - Public list: moderation_status='approved' AND is_public=true AND is_deleted=false
        - mine=true: Returns all statuses for owner
        """
        start = (page - 1) * limit
        end = start + limit - 1

        query = self.client.table("marketplace_listings").select(
            "*, profiles!marketplace_listings_seller_id_fkey(username, avatar_url)"
        )

        if mine and user_id:
            query = query.eq("seller_id", user_id).eq("is_deleted", False)
        else:
            query = query.eq("is_public", True).eq("is_deleted", False).eq(
                "moderation_status", "approved"
            )

        if resource_type:
            query = query.eq("resource_type", resource_type)

        if tier_filter and tier_filter != "all":
            query = query.contains("allowed_tiers", [tier_filter])

        if price_filter == "free":
            query = query.eq("price_credits", 0)
        elif price_filter == "paid":
            query = query.gt("price_credits", 0)

        if featured or sort == "best_selling":
            query = query.order("sales_count", desc=True)
        elif sort == "popular":
            query = query.order("usage_count", desc=True)
        else:
            query = query.order("created_at", desc=True)

        result = query.range(start, end).execute()
        return result.data or []

    async def get_marketplace_item(
        self,
        listing_id: str,
        user_id: Optional[str] = None
    ) -> Optional[dict]:
        """Get single listing detail with access control."""
        res = self.client.table("marketplace_listings").select(
            "*, profiles!marketplace_listings_seller_id_fkey(username, avatar_url)"
        ).eq("id", listing_id).single().execute()

        if not res.data:
            return None

        listing = res.data
        is_seller = user_id and listing.get("seller_id") == user_id
        is_visible = (
            listing.get("is_public", False)
            and not listing.get("is_deleted", False)
            and listing.get("moderation_status") == "approved"
        )

        if not is_seller and not is_visible:
            return None

        if user_id:
            purchase = self.client.table("marketplace_purchases").select("id").eq(
                "buyer_id", user_id
            ).eq("listing_id", listing_id).execute()
            listing["is_purchased"] = bool(purchase.data)

        return listing

    async def get_seller_listings(
        self,
        seller_id: str,
        page: int = 1,
        limit: int = 20
    ) -> List[dict]:
        """Get seller's own listings."""
        start = (page - 1) * limit
        end = start + limit - 1

        result = self.client.table("marketplace_listings").select("*").eq(
            "seller_id", seller_id
        ).eq("is_deleted", False).order("created_at", desc=True).range(start, end).execute()

        return result.data or []

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
    ) -> Optional[dict]:
        """Create or update listing."""
        existing_query = self.client.table("marketplace_listings").select("*").eq(
            "seller_id", seller_id
        ).eq("is_deleted", False)

        if resource_id:
            existing_query = existing_query.eq("resource_id", resource_id)
        else:
            existing_query = existing_query.eq("resource_url", resource_url)

        existing_res = existing_query.execute()
        existing_listing = existing_res.data[0] if existing_res.data else None

        if existing_listing:
            current_history = existing_listing.get("version_history") or []
            new_entry = {
                "version": version,
                "changelog": changelog,
                "published_at": datetime.utcnow().isoformat(),
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

        version_history = [
            {
                "version": version,
                "changelog": changelog,
                "published_at": datetime.utcnow().isoformat(),
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

    async def submit_listing_for_review(
        self,
        listing_id: str,
        seller_id: Optional[str] = None
    ) -> Optional[dict]:
        """Submit listing for review."""
        query = self.client.table("marketplace_listings").update({
            "moderation_status": "pending",
            "is_public": True,
            "submitted_at": datetime.utcnow().isoformat()
        }).eq("id", listing_id)

        if seller_id:
            query = query.eq("seller_id", seller_id)

        result = query.execute()
        return result.data[0] if result.data else None

    async def unpublish_listing(
        self,
        listing_id: str,
        seller_id: str
    ) -> Optional[dict]:
        """Unpublish listing."""
        result = self.client.table("marketplace_listings").update({
            "is_public": False
        }).eq("id", listing_id).eq("seller_id", seller_id).execute()

        return result.data[0] if result.data else None

    async def update_listing(
        self,
        listing_id: str,
        seller_id: str,
        updates: dict
    ) -> Optional[dict]:
        """Update listing."""
        result = self.client.table("marketplace_listings").update(updates).eq(
            "id", listing_id
        ).eq("seller_id", seller_id).execute()

        return result.data[0] if result.data else None

    async def check_user_purchase(
        self,
        user_id: str,
        listing_id: str
    ) -> bool:
        """Check if user has purchased listing."""
        result = self.client.table("marketplace_purchases").select("id").eq(
            "buyer_id", user_id
        ).eq("listing_id", listing_id).execute()
        return bool(result.data)

    async def execute_purchase(
        self,
        buyer_id: str,
        listing_id: str,
        tz: str = "UTC"
    ) -> dict:
        """Execute marketplace purchase using atomic RPC."""
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

    async def get_seller_stats(
        self,
        seller_id: str
    ) -> dict:
        """Get seller statistics."""
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
            "total_earned_credits": int(total_revenue * 0.9),
        }

    async def record_listing_usage(
        self,
        listing_id: str,
        used_by_user_id: str,
        project_id: str
    ) -> bool:
        """Record listing usage."""
        try:
            self.client.table("listing_usages").insert({
                "listing_id": listing_id,
                "used_by_user_id": used_by_user_id,
                "project_id": project_id,
            }).execute()
            return True
        except:
            return False

    async def get_leaderboard(
        self,
        period: str = "monthly",
        board_type: str = "all",
        limit: int = 10
    ) -> List[dict]:
        """Get marketplace leaderboard."""
        query = self.client.table("marketplace_listings").select(
            "id, title, thumbnail_url, usage_count, sales_count, resource_type, seller_id, "
            "profiles!marketplace_listings_seller_id_fkey(username, avatar_url)"
        ).eq("is_public", True).eq("is_deleted", False).eq("moderation_status", "approved")

        if board_type and board_type != "all":
            query = query.eq("resource_type", board_type)

        query = query.order("usage_count", desc=True).limit(limit)

        result = query.execute()
        items = result.data or []

        for i, item in enumerate(items):
            item["rank"] = i + 1

        return items

    async def get_seller_info(self, seller_id: str) -> Optional[dict]:
        """Get seller profile info."""
        try:
            result = self.client.table("profiles").select(
                "username, avatar_url"
            ).eq("id", seller_id).single().execute()

            if not result.data:
                return None

            return {
                "username": result.data.get("username"),
                "avatar_url": result.data.get("avatar_url"),
            }

        except Exception as e:
            logger.error(f"Failed to get seller info for {seller_id}: {e}")
            return None

    async def get_listing_detail(
        self,
        listing_id: str,
        user_id: Optional[str] = None
    ) -> Optional[tuple[Listing, bool, Optional[dict]]]:
        """
        Get listing detail with access control, purchase status and seller info.

        Combines access control logic from get_marketplace_item with DDD mapping.
        """
        try:
            # Query listing with seller profile join
            result = self.client.table("marketplace_listings").select(
                "*, profiles!marketplace_listings_seller_id_fkey(username, avatar_url)"
            ).eq("listing_id", listing_id).single().execute()

            if not result.data:
                return None

            row = result.data

            # Access control check
            is_seller = user_id and row.get("seller_id") == user_id
            is_visible = (
                row.get("is_public", False)
                and not row.get("is_deleted", False)
                and row.get("moderation_status") == "approved"
            )

            # Seller can always see; others need visibility
            if not is_seller and not is_visible:
                return None

            # Map to Listing aggregate
            listing = self._map_to_listing(row)

            # Check purchase status
            is_purchased = False
            if user_id:
                is_purchased = await self.has_purchased(listing_id, user_id)

            # Extract seller info from joined profile
            profile_data = row.get("profiles") or {}
            seller_info = {
                "username": profile_data.get("username"),
                "avatar_url": profile_data.get("avatar_url"),
            } if profile_data else None

            return listing, is_purchased, seller_info

        except Exception as e:
            logger.error(f"Failed to get listing detail {listing_id}: {e}")
            return None
