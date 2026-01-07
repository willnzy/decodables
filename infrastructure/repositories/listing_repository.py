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
    AssetCategory,
    PriceType,
    ListingMetadata,
    ListingStats,
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

        return Listing(
            listing_id=row["listing_id"],
            seller_id=row["seller_id"],
            category=AssetCategory(row.get("category", "element")),
            metadata=metadata,
            price_type=PriceType(row.get("price_type", "free")),
            credit_price=row.get("credit_price", 0),
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
            "category": listing.category.value,
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
            "status": listing.status.value,
            "is_featured": listing.is_featured,
            "rejection_reason": listing.rejection_reason,
            "view_count": listing.stats.view_count,
            "download_count": listing.stats.download_count,
            "like_count": listing.stats.like_count,
            "purchase_count": listing.stats.purchase_count,
            "published_at": listing.published_at.isoformat() if listing.published_at else None,
        }
