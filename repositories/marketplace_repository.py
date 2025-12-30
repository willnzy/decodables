"""
Marketplace Repository
Database operations for marketplace listings

@module repositories/marketplace_repository
"""

from typing import Optional, List, Dict, Any
from .base import BaseRepository


class MarketplaceRepository(BaseRepository):
    """
    Repository for marketplace listing operations.
    """
    
    def __init__(self, supabase):
        super().__init__(supabase, "marketplace_listings")
    
    def find_public(
        self,
        resource_type: str = None,
        tier_filter: str = None,
        price_filter: str = None,
        sort: str = "latest",
        page: int = 1,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Find public listings (approved + public + not deleted).
        
        Args:
            resource_type: Filter by type (project/asset)
            tier_filter: Filter by allowed_tiers
            price_filter: 'free' or 'paid'
            sort: 'latest', 'popular', 'best_selling'
            page: Page number
            limit: Items per page
        
        Returns:
            List of listings
        """
        offset = (page - 1) * limit
        query = self.supabase.table(self.table_name).select(
            "*, profiles!seller_id(username, avatar_url)"
        ).eq("moderation_status", "approved").eq(
            "is_public", True
        ).eq("is_deleted", False)
        
        if resource_type:
            query = query.eq("resource_type", resource_type)
        
        if tier_filter == "free":
            query = query.contains("allowed_tiers", ["free"])
        elif tier_filter in ["starter", "pro"]:
            query = query.contains("allowed_tiers", [tier_filter])
        
        if price_filter == "free":
            query = query.eq("price_credits", 0)
        elif price_filter == "paid":
            query = query.gt("price_credits", 0)
        
        # Sorting
        if sort == "popular":
            query = query.order("usage_count", desc=True)
        elif sort == "best_selling":
            query = query.order("sales_count", desc=True)
        else:  # latest
            query = query.order("created_at", desc=True)
        
        query = query.range(offset, offset + limit - 1)
        result = query.execute()
        return result.data or []
    
    def find_by_seller(
        self,
        seller_id: str,
        page: int = 1,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Find listings by seller (all moderation states).
        
        Args:
            seller_id: Seller user ID
            page: Page number
            limit: Items per page
        
        Returns:
            List of listings
        """
        offset = (page - 1) * limit
        result = self.supabase.table(self.table_name).select(
            "*"
        ).eq("seller_id", seller_id).eq("is_deleted", False).order(
            "created_at", desc=True
        ).range(offset, offset + limit - 1).execute()
        return result.data or []
    
    def find_by_id_public_or_owner(
        self,
        listing_id: str,
        user_id: str = None,
        is_admin: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Find listing if accessible to user.
        
        Rules:
        - Admin: can see any listing
        - Seller: can see own listings
        - Others: only approved + public + not deleted
        
        Args:
            listing_id: Listing ID
            user_id: Current user ID
            is_admin: Whether user is admin
        
        Returns:
            Listing dict or None
        """
        result = self.supabase.table(self.table_name).select(
            "*, profiles!seller_id(username, avatar_url, email)"
        ).eq("id", listing_id).single().execute()
        
        if not result.data:
            return None
        
        listing = result.data
        
        # Admin can see anything
        if is_admin:
            return listing
        
        # Seller can see own listings
        if listing.get("seller_id") == user_id:
            return listing
        
        # Others: must be approved, public, not deleted
        if (listing.get("moderation_status") == "approved" and 
            listing.get("is_public") and 
            not listing.get("is_deleted")):
            return listing
        
        return None
    
    def create_listing(
        self,
        seller_id: str,
        title: str,
        description: str,
        thumbnail_url: str,
        resource_url: str,
        resource_type: str,
        price_credits: int,
        allowed_tiers: List[str]
    ) -> Dict[str, Any]:
        """
        Create new listing.
        
        Args:
            seller_id: Seller user ID
            title: Listing title
            description: Description
            thumbnail_url: Thumbnail URL
            resource_url: Resource URL
            resource_type: 'project' or 'asset'
            price_credits: Price in credits
            allowed_tiers: Access tiers
        
        Returns:
            Created listing
        """
        return self.create({
            "seller_id": seller_id,
            "title": title,
            "description": description,
            "thumbnail_url": thumbnail_url,
            "resource_url": resource_url,
            "resource_type": resource_type,
            "price_credits": price_credits,
            "allowed_tiers": allowed_tiers,
            "moderation_status": "draft",
            "is_public": False
        })
    
    def submit_for_review(self, listing_id: str) -> Optional[Dict[str, Any]]:
        """
        Submit listing for review.
        
        Args:
            listing_id: Listing ID
        
        Returns:
            Updated listing
        """
        return self.update(listing_id, {
            "moderation_status": "pending",
            "is_public": True  # Intent to be public
        })
    
    def approve(
        self,
        listing_id: str,
        moderator_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Approve listing.
        
        Args:
            listing_id: Listing ID
            moderator_id: Admin user ID
        
        Returns:
            Updated listing
        """
        return self.update(listing_id, {
            "moderation_status": "approved",
            "moderated_by": moderator_id,
            "moderated_at": "now()"
        })
    
    def reject(
        self,
        listing_id: str,
        moderator_id: str,
        reason: str
    ) -> Optional[Dict[str, Any]]:
        """
        Reject listing.
        
        Args:
            listing_id: Listing ID
            moderator_id: Admin user ID
            reason: Rejection reason
        
        Returns:
            Updated listing
        """
        return self.update(listing_id, {
            "moderation_status": "rejected",
            "moderation_note": reason,
            "moderated_by": moderator_id,
            "moderated_at": "now()"
        })
    
    def unpublish(
        self,
        listing_id: str,
        user_id: str = None
    ) -> bool:
        """
        Unpublish listing (set is_public=false).
        
        Args:
            listing_id: Listing ID
            user_id: Optional seller ID for ownership check
        
        Returns:
            True if updated
        """
        query = self.supabase.table(self.table_name).update({
            "is_public": False
        }).eq("id", listing_id)
        
        if user_id:
            query = query.eq("seller_id", user_id)
        
        result = query.execute()
        return len(result.data) > 0 if result.data else False
    
    def get_by_moderation_status(
        self,
        status: str = None,
        resource_type: str = None,
        page: int = 1,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get listings by moderation status (admin).
        
        Args:
            status: Filter by status (pending/approved/rejected/all)
            resource_type: Filter by type
            page: Page number
            limit: Items per page
        
        Returns:
            List of listings with seller info
        """
        offset = (page - 1) * limit
        query = self.supabase.table(self.table_name).select(
            "*, profiles!seller_id(username, email, avatar_url)"
        ).eq("is_deleted", False)
        
        if status and status != "all":
            query = query.eq("moderation_status", status)
        
        if resource_type:
            query = query.eq("resource_type", resource_type)
        
        query = query.order("created_at", desc=True)
        query = query.range(offset, offset + limit - 1)
        
        result = query.execute()
        return result.data or []
    
    def record_purchase(
        self,
        user_id: str,
        listing_id: str,
        price_paid: int
    ) -> Optional[Dict[str, Any]]:
        """
        Record a purchase.
        
        Args:
            user_id: Buyer user ID
            listing_id: Listing ID
            price_paid: Amount paid
        
        Returns:
            Created purchase record
        """
        result = self.supabase.table("user_purchases").insert({
            "user_id": user_id,
            "listing_id": listing_id,
            "price_paid": price_paid
        }).execute()
        return result.data[0] if result.data else None
    
    def check_purchase_exists(
        self,
        user_id: str,
        listing_id: str
    ) -> bool:
        """
        Check if user already purchased listing.
        
        Args:
            user_id: User ID
            listing_id: Listing ID
        
        Returns:
            True if already purchased
        """
        result = self.supabase.table("user_purchases").select(
            "id"
        ).eq("user_id", user_id).eq("listing_id", listing_id).execute()
        return len(result.data) > 0 if result.data else False

