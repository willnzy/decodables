"""
Marketplace Service
Handles marketplace business logic

@module services/marketplace_service
"""

from typing import Optional, Dict, Any, List
from .credit_service import CreditService
from .access_control import AccessControl
from config import SELLER_REVENUE_PERCENT


class MarketplaceService:
    """
    Service for managing marketplace operations.
    
    Key operations:
    - Purchase (with 90/10 split)
    - Publish (with moderation)
    - Usage tracking
    """
    
    def __init__(self, supabase):
        self.supabase = supabase
        self.credit_service = CreditService(supabase)
        self.access_control = AccessControl()
    
    def execute_purchase(
        self, 
        listing_id: str, 
        buyer_id: str
    ) -> Dict[str, Any]:
        """
        Execute a marketplace purchase.
        
        Flow:
        1. Validate listing (approved, public, not deleted)
        2. Check buyer access (allowed_tiers)
        3. Check if already purchased (dedup)
        4. Deduct from buyer (monthly first, then permanent)
        5. Add to seller (90% to permanent)
        6. Record purchase
        
        Args:
            listing_id: Listing ID
            buyer_id: Buyer user ID
        
        Returns:
            Result dict with success status
        """
        # Get listing
        listing = self.supabase.table("marketplace_listings").select(
            "*"
        ).eq("id", listing_id).single().execute()
        
        if not listing.data:
            return {"success": False, "status": 404, "error": "Listing not found"}
        
        listing = listing.data
        
        # Validate listing status
        if listing.get("moderation_status") != "approved":
            return {"success": False, "status": 400, "error": "Listing is not approved"}
        if not listing.get("is_public", False):
            return {"success": False, "status": 400, "error": "Listing is not public"}
        if listing.get("is_deleted", False):
            return {"success": False, "status": 400, "error": "Listing has been deleted"}
        
        # Get buyer profile
        buyer = self.supabase.table("profiles").select(
            "*"
        ).eq("id", buyer_id).single().execute()
        
        if not buyer.data:
            return {"success": False, "status": 404, "error": "Buyer not found"}
        
        buyer = buyer.data
        
        # Check tier access
        allowed_tiers = listing.get("allowed_tiers", ["free"])
        if not self.access_control.can_access_resource(buyer, allowed_tiers):
            return {"success": False, "status": 403, "error": f"Requires {'/'.join(allowed_tiers)} membership"}
        
        # PRD v3.2: Starter can only purchase Assets, Pro can purchase Assets + Templates
        resource_type = listing.get("resource_type", "asset")
        buyer_tier = buyer.get("tier", "free")
        if resource_type == "project" and buyer_tier != "pro":
            return {"success": False, "status": 403, "error": "Only Pro members can purchase templates. Upgrade to Pro to access templates."}
        
        # Check if already purchased
        existing = self.supabase.table("user_purchases").select(
            "id"
        ).eq("user_id", buyer_id).eq("listing_id", listing_id).execute()
        
        if existing.data and len(existing.data) > 0:
            return {"success": True, "already_owned": True, "message": "Already purchased"}
        
        price = listing.get("price_credits", 0)
        seller_id = listing.get("seller_id")
        
        # If free, just record purchase
        if price == 0:
            self.supabase.table("user_purchases").insert({
                "user_id": buyer_id,
                "listing_id": listing_id,
                "price_paid": 0
            }).execute()
            
            # Increment sales count (use update instead of RPC for compatibility)
            self.supabase.table("marketplace_listings").update({
                "sales_count": listing.get("sales_count", 0) + 1
            }).eq("id", listing_id).execute()
            
            return {"success": True, "price_paid": 0, "message": "Free item acquired"}
        
        # Check buyer has enough credits
        if not self.credit_service.has_enough(buyer_id, price):
            return {"success": False, "status": 402, "error": "Insufficient credits"}
        
        # Deduct from buyer
        success, msg = self.credit_service.deduct(
            buyer_id, price, "market_purchase", 
            f"Purchased: {listing.get('title', 'Listing')}"
        )
        
        if not success:
            return {"success": False, "status": 400, "error": msg}
        
        # Calculate seller revenue (90%)
        seller_revenue = int(price * SELLER_REVENUE_PERCENT / 100)
        
        # Add to seller (if not official listing)
        if seller_id:
            self.credit_service.add(
                seller_id, seller_revenue, "permanent",
                "market_sale", f"Sale: {listing.get('title', 'Listing')}"
            )
        
        # Record purchase
        self.supabase.table("user_purchases").insert({
            "user_id": buyer_id,
            "listing_id": listing_id,
            "price_paid": price
        }).execute()
        
        # Increment sales count
        self.supabase.table("marketplace_listings").update({
            "sales_count": listing.get("sales_count", 0) + 1
        }).eq("id", listing_id).execute()
        
        return {
            "success": True,
            "price_paid": price,
            "seller_revenue": seller_revenue,
            "message": "Purchase successful"
        }
    
    def record_usage(
        self, 
        listing_id: str, 
        user_id: str, 
        project_id: str
    ) -> bool:
        """
        Record listing usage (for usage_count).
        
        Deduplication: (listing_id, user_id, project_id) must be unique.
        
        Args:
            listing_id: Listing ID
            user_id: User who applied the listing
            project_id: Project where it was applied
        
        Returns:
            True if new usage recorded, False if already exists
        """
        try:
            # Try to insert (will fail if exists due to unique constraint)
            self.supabase.table("listing_usage").insert({
                "listing_id": listing_id,
                "used_by_user_id": user_id,
                "project_id": project_id
            }).execute()
            
            # Increment usage_count
            listing = self.supabase.table("marketplace_listings").select(
                "usage_count"
            ).eq("id", listing_id).single().execute()
            
            if listing.data:
                self.supabase.table("marketplace_listings").update({
                    "usage_count": (listing.data.get("usage_count", 0) or 0) + 1
                }).eq("id", listing_id).execute()
            
            return True
        except Exception:
            # Already exists or other error
            return False
    
    def get_seller_stats(self, seller_id: str) -> Dict[str, Any]:
        """
        Get seller statistics.
        
        Returns:
            Stats including total_earned, listings_count, total_sales
        """
        # Get listings
        listings = self.supabase.table("marketplace_listings").select(
            "id, sales_count, usage_count"
        ).eq("seller_id", seller_id).eq("is_deleted", False).execute()
        
        listings_data = listings.data or []
        
        # Get total earned from credit transactions
        transactions = self.supabase.table("credit_transactions").select(
            "amount"
        ).eq("user_id", seller_id).eq("type", "market_sale").execute()
        
        total_earned = sum(tx.get("amount", 0) for tx in (transactions.data or []))
        total_sales = sum(l.get("sales_count", 0) for l in listings_data)
        total_usage = sum(l.get("usage_count", 0) or 0 for l in listings_data)
        
        return {
            "total_earned_credits": total_earned,
            "listings_count": len(listings_data),
            "total_sales": total_sales,
            "total_usage": total_usage
        }
    
    def get_leaderboard(
        self, 
        period: str = "monthly",
        resource_type: str = "all",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get leaderboard by usage_count.
        
        Only includes approved + public + not deleted listings.
        
        Args:
            period: 'monthly' or 'all_time' (currently same)
            resource_type: 'all', 'project', or 'asset'
            limit: Number of items to return
        
        Returns:
            List of top listings with rank
        """
        query = self.supabase.table("marketplace_listings").select(
            "id, title, thumbnail_url, resource_type, usage_count, seller_id"
        ).eq("moderation_status", "approved").eq("is_public", True).eq("is_deleted", False)
        
        if resource_type != "all":
            query = query.eq("resource_type", resource_type)
        
        query = query.order("usage_count", desc=True).limit(limit)
        
        result = query.execute()
        
        # Add rank
        items = []
        for i, item in enumerate(result.data or []):
            item["rank"] = i + 1
            items.append(item)
        
        return items

