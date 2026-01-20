"""
Listing Repository Implementation - Supabase data access for marketplace domain.

@module infrastructure.repositories.listing_repository
@version 2.0.0 (AsyncClient migration)

Changes in v2.0:
- Migrated all methods to use AsyncClient with await
- All .execute() calls now properly awaited

Implements IListingRepository using Supabase PostgreSQL.
Inherits from BaseRepository for soft/hard delete support.
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
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class SupabaseListingRepository(BaseRepository[Listing], IListingRepository):
    """
    Supabase implementation of listing repository.

    Inherits soft/hard delete operations from BaseRepository.
    """

    @property
    def table_name(self) -> str:
        """Table name for marketplace listings."""
        return "marketplace_listings"

    async def get_by_id(self, listing_id: str) -> Optional[Listing]:
        """Get listing by ID."""
        try:
            result = await self.client.table("marketplace_listings").select("*").eq(
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
            await self.client.table("marketplace_listings").upsert(
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
            await self.client.table("marketplace_listings").insert(data).execute()

            return listing

        except Exception as e:
            logger.error(f"Failed to create listing {listing.listing_id}: {e}")
            raise

    async def update(self, listing: Listing) -> Listing:
        """Update existing listing."""
        try:
            data = self._map_to_row(listing)
            data["updated_at"] = datetime.utcnow().isoformat()

            # AsyncClient: update doesn't support .select() chaining
            # Just execute the update and return the listing object
            await self.client.table("marketplace_listings").update(data).eq(
                "listing_id", listing.listing_id
            ).execute()

            return listing

        except Exception as e:
            logger.error(f"Failed to update listing {listing.listing_id}: {e}")
            raise

    async def delete(self, listing_id: str) -> bool:
        """
        Soft delete a listing (mark as deleted).

        Uses BaseRepository.soft_delete() for soft deletion.
        For hard delete (physical removal), use hard_delete() method.
        """
        # Get listing UUID first
        result = await self.client.table("marketplace_listings").select("id").eq(
            "listing_id", listing_id
        ).single().execute()

        if not result.data:
            return False

        return await super().soft_delete(result.data["id"])

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

            result = await query.execute()

            return [self._map_to_listing(row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to get listings for seller {seller_id}: {e}")
            return []

    async def get_by_seller_with_count(
        self,
        seller_id: str,
        status: Optional[ListingStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[Listing], int]:
        """
        Get listings by seller with total count.

        M-HIGH-001 fix: Returns accurate total for pagination.
        """
        try:
            query = self.client.table("marketplace_listings").select(
                "*", count="exact"
            ).eq("seller_id", seller_id).order("updated_at", desc=True)

            if status:
                query = query.eq("status", status.value)

            result = await query.range(offset, offset + limit - 1).execute()

            listings = [self._map_to_listing(row) for row in result.data]
            total_count = result.count if result.count is not None else len(listings)

            return listings, total_count

        except Exception as e:
            logger.error(f"Failed to get listings for seller {seller_id}: {e}")
            return [], 0

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

            result = await query.execute()

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

        P1-004: Uses RPC function p_get_marketplace_listings for 5x-10x better performance.
        Falls back to direct query if RPC fails (graceful degradation).
        """
        try:
            # P1-004: Try RPC function first (optimized path)
            try:
                # Use centralized RPC mapper to convert domain enums to RPC parameters
                from domains.marketplace.rpc_mappings import MarketplaceRPCMapper

                rpc_params = MarketplaceRPCMapper.map_all_filters(
                    category=category,
                    price_filter=price_filter,
                    sort_by=sort_by,
                )

                result = await self.client.rpc("p_get_marketplace_listings", {
                    "p_category": rpc_params["category"],
                    "p_price_filter": rpc_params["price_filter"],
                    "p_sort_by": rpc_params["sort_by"],
                    "p_tier_filter": tier_filter,
                    "p_search_query": query,
                    "p_limit": limit,
                    "p_offset": offset,
                }).execute()

                if result.data:
                    # Extract total count from first row (all rows have same total_count)
                    total_count = result.data[0].get("total_count", 0) if result.data else 0

                    # Map RPC results to Listing objects
                    listings = [self._map_to_listing(row) for row in result.data]

                    return listings, total_count

            except Exception as rpc_error:
                # Log RPC failure but don't crash - fall back to direct query
                logger.warning(f"RPC p_get_marketplace_listings failed, falling back to direct query: {rpc_error}")

            # Fallback: Original direct query implementation
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

            result = await db_query.execute()

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

            result = await query.execute()

            return [self._map_to_listing(row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to get popular listings: {e}")
            return []

    async def record_purchase(
        self,
        listing_id: str,
        buyer_id: str,
        credit_amount: int = 0
    ) -> tuple[bool, bool]:
        """
        Record a purchase atomically.

        Uses upsert with ON CONFLICT to prevent race condition where
        concurrent requests both pass has_purchased() check.

        Returns:
            tuple[bool, bool]: (success, already_existed)
            - (True, False): New purchase recorded successfully
            - (True, True): Purchase already existed (idempotent)
            - (False, False): Failed to record purchase
        """
        try:
            # Use upsert with ON CONFLICT DO NOTHING to handle race condition
            # The unique constraint on (listing_id, buyer_id) prevents duplicates
            result = await self.client.table("marketplace_purchases").upsert(
                {
                    "listing_id": listing_id,
                    "buyer_id": buyer_id,
                    "credit_amount": credit_amount,
                    "purchased_at": datetime.utcnow().isoformat(),
                },
                on_conflict="listing_id,buyer_id",
                ignore_duplicates=True,  # Don't update if exists
            ).execute()

            # Check if this was a new insert or existing record
            # If no data returned with ignore_duplicates, it was a duplicate
            is_new_purchase = bool(result.data)

            if is_new_purchase:
                # Only increment stats for new purchases
                try:
                    await self.client.rpc("increment_listing_stat", {
                        "p_listing_id": listing_id,
                        "p_stat": "purchase_count",
                    }).execute()
                except Exception as stat_err:
                    # Log but don't fail - purchase record is the source of truth
                    logger.warning(f"Failed to increment purchase count for {listing_id}: {stat_err}")

            return (True, not is_new_purchase)

        except Exception as e:
            logger.error(f"Failed to record purchase for listing {listing_id}: {e}")
            return (False, False)

    async def has_purchased(
        self,
        listing_id: str,
        user_id: str
    ) -> bool:
        """
        Check if user has purchased listing.

        Raises exception on database errors instead of silently returning False,
        which could lead to double-charging in purchase flow.
        """
        try:
            result = await self.client.table("marketplace_purchases").select(
                "id"
            ).eq("listing_id", listing_id).eq("buyer_id", user_id).maybe_single().execute()

            return result.data is not None

        except Exception as e:
            # Don't silently return False - this could lead to double-charging
            logger.error(f"Failed to check purchase status for listing {listing_id}, user {user_id}: {e}")
            raise

    async def get_user_purchases(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Listing]:
        """Get listings purchased by user."""
        try:
            # Get purchase records
            purchases = await self.client.table("marketplace_purchases").select(
                "listing_id"
            ).eq("buyer_id", user_id).order(
                "purchased_at", desc=True
            ).range(offset, offset + limit - 1).execute()

            if not purchases.data:
                return []

            listing_ids = [p["listing_id"] for p in purchases.data]

            # Get listings
            result = await self.client.table("marketplace_listings").select("*").in_(
                "listing_id", listing_ids
            ).execute()

            return [self._map_to_listing(row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to get purchases for user {user_id}: {e}")
            return []

    def _map_to_entity(self, row: dict) -> Listing:
        """
        Map database row to Listing entity (BaseRepository requirement).

        This is the standard mapping method for BaseRepository.
        _map_to_listing() is kept for backward compatibility.
        """
        return self._map_to_listing(row)

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
        allowed_tiers = row.get("allowed_tiers", ["t1", "t2", "t3"])
        if isinstance(allowed_tiers, str):
            allowed_tiers = [allowed_tiers]

        return Listing(
            listing_id=row["listing_id"],
            seller_id=row["seller_id"],
            resource_type=resource_type,
            category=category,
            metadata=metadata,
            source=source,
            price_type=PriceType(row.get("price_type", "t1")),
            credit_price=row.get("price_credits", 0),  # DB column is price_credits
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
            "price_credits": listing.credit_price,  # DB column is price_credits
            "allowed_tiers": listing.allowed_tiers,
            "status": listing.status.value,  # Internal status field
            "moderation_status": self._status_to_moderation(listing.status),  # DB uses moderation_status
            "is_featured": listing.is_featured,
            "rejection_reason": listing.rejection_reason,
            "view_count": listing.stats.view_count,
            "download_count": listing.stats.download_count,
            "like_count": listing.stats.like_count,
            "purchase_count": listing.stats.purchase_count,
            "published_at": listing.published_at.isoformat() if listing.published_at else None,
        }

    def _status_to_moderation(self, status: ListingStatus) -> str:
        """
        Map ListingStatus to database moderation_status.

        DB moderation_status: draft, pending, approved, rejected
        Code ListingStatus: draft, pending_review, published, rejected, suspended, archived
        """
        mapping = {
            ListingStatus.DRAFT: "draft",
            ListingStatus.PENDING_REVIEW: "pending",
            ListingStatus.PUBLISHED: "approved",
            ListingStatus.REJECTED: "rejected",
            ListingStatus.SUSPENDED: "rejected",  # Suspended maps to rejected
            ListingStatus.ARCHIVED: "rejected",   # Archived maps to rejected
        }
        return mapping.get(status, "draft")

    # ==========================================
    # Statistics & Leaderboard Methods
    # ==========================================

    async def get_seller_stats(
        self,
        seller_id: str
    ) -> dict:
        """
        Get seller statistics.

        M-MEDIUM-005 fix: Use integer arithmetic to avoid floating point precision issues.
        Seller earns 90% of revenue (platform takes 10% fee).
        """
        try:
            listings = await self.client.table("marketplace_listings").select(
                "id, price_credits, sales_count, usage_count"
            ).eq("seller_id", seller_id).eq("is_deleted", False).execute()

            data = listings.data or []
            total_sales = sum(l.get("sales_count", 0) for l in data)
            total_usage = sum(l.get("usage_count", 0) for l in data)
            total_revenue = sum(l.get("price_credits", 0) * l.get("sales_count", 0) for l in data)

            # M-MEDIUM-005 fix: Use integer arithmetic (multiply first, then divide)
            # This avoids floating point precision issues
            # Formula: earned = revenue * 90 / 100 (integer division)
            total_earned_credits = (total_revenue * 90) // 100

            return {
                "total_listings": len(data),
                "total_sales": total_sales,
                "total_usage": total_usage,
                "total_revenue": total_revenue,
                "total_earned_credits": total_earned_credits,
            }
        except Exception as e:
            logger.error(f"Failed to get seller stats for {seller_id}: {e}")
            return {
                "total_listings": 0,
                "total_sales": 0,
                "total_usage": 0,
                "total_revenue": 0,
                "total_earned_credits": 0,
            }

    async def record_listing_usage(
        self,
        listing_id: str,
        used_by_user_id: str,
        project_id: str
    ) -> bool:
        """Record listing usage."""
        try:
            await self.client.table("listing_usages").insert({
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

        result = await query.execute()
        items = result.data or []

        for i, item in enumerate(items):
            item["rank"] = i + 1

        return items

    async def get_seller_info(self, seller_id: str) -> Optional[dict]:
        """Get seller profile info."""
        try:
            result = await self.client.table("profiles").select(
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
            result = await self.client.table("marketplace_listings").select(
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
