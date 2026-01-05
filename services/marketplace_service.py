"""
Marketplace Service
Handles marketplace business logic

@module services/marketplace_service

Atomic Operations (v3.22):
- Uses PostgreSQL RPC function for atomic purchase operations
- All credit operations (buyer deduct, seller add) in single transaction
- Idempotency support for duplicate request handling
"""

import logging
from typing import Optional, Dict, Any, List
from .credit_service import CreditService, DEFAULT_TIMEZONE
from .access_control import AccessControl
from config import SELLER_REVENUE_PERCENT

logger = logging.getLogger(__name__)


class MarketplaceService:
    """
    Service for managing marketplace operations.
    
    Key operations:
    - Purchase (with 90/10 split) - now atomic via RPC
    - Publish (with moderation)
    - Usage tracking
    
    v3.22: Purchase operations use atomic RPC for data consistency
    """
    
    def __init__(self, supabase):
        self.supabase = supabase
        self.credit_service = CreditService(supabase)
        self.access_control = AccessControl()
    
    def execute_purchase(
        self, 
        listing_id: str, 
        buyer_id: str,
        timezone: str = DEFAULT_TIMEZONE,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a marketplace purchase using atomic RPC.
        
        v3.22: All operations in single database transaction:
        1. Validate listing (approved, public, not deleted)
        2. Check if already purchased (dedup)
        3. Deduct from buyer (monthly first, then permanent)
        4. Add to seller (90% to permanent)
        5. Record purchase
        6. Update sales count
        
        Note: Tier access validation is done BEFORE calling RPC
        (RPC handles the atomic credit operations)
        
        Args:
            listing_id: Listing ID
            buyer_id: Buyer user ID
            timezone: IANA timezone for transaction snapshot (e.g., 'Asia/Shanghai')
            idempotency_key: Optional key to prevent duplicate purchases
        
        Returns:
            Result dict with success status
        """
        # Pre-validation: Get listing and buyer for tier access check
        # (This is done outside RPC to keep RPC focused on atomic operations)
        listing = self.supabase.table("marketplace_listings").select(
            "*"
        ).eq("id", listing_id).single().execute()
        
        if not listing.data:
            return {"success": False, "status": 404, "error": "Listing not found"}
        
        listing_data = listing.data
        
        # Get buyer profile for tier check
        buyer = self.supabase.table("profiles").select(
            "*"
        ).eq("id", buyer_id).single().execute()
        
        if not buyer.data:
            return {"success": False, "status": 404, "error": "Buyer not found"}
        
        buyer_data = buyer.data
        
        # Check tier access (business logic not in RPC)
        allowed_tiers = listing_data.get("allowed_tiers", ["free"])
        if not self.access_control.can_access_resource(buyer_data, allowed_tiers):
            return {"success": False, "status": 403, "error": f"Requires {'/'.join(allowed_tiers)} membership"}
        
        # PRD v3.2: Starter can only purchase Assets, Pro can purchase Assets + Projects
        resource_type = listing_data.get("resource_type", "asset")
        buyer_tier = buyer_data.get("tier", "free")
        if resource_type == "project" and buyer_tier != "pro":
            return {
                "success": False, 
                "status": 403, 
                "error": "Only Pro members can purchase projects. Upgrade to Pro to access projects."
            }
        
        # Execute atomic purchase via RPC
        try:
            result = self.supabase.rpc("execute_marketplace_purchase", {
                "p_listing_id": listing_id,
                "p_buyer_id": buyer_id,
                "p_timezone": timezone,
                "p_idempotency_key": idempotency_key
            }).execute()
            
            data = result.data
            
            if not data:
                logger.error(f"[Marketplace] RPC returned no data for purchase {listing_id}")
                return {"success": False, "status": 500, "error": "Database error"}
            
            # Map RPC response to service response format
            if data.get("success"):
                response = {
                    "success": True,
                    "price_paid": data.get("price_paid", 0),
                    "seller_revenue": data.get("seller_revenue", 0),
                    "message": data.get("message", "Purchase successful")
                }
                
                if data.get("already_owned"):
                    response["already_owned"] = True
                    
                if data.get("idempotent"):
                    response["idempotent"] = True
                    logger.info(f"[Marketplace] Idempotent purchase for {buyer_id}: {idempotency_key}")
                
                return response
            else:
                status = data.get("status", 400)
                error = data.get("error", "Purchase failed")
                return {"success": False, "status": status, "error": error}
                
        except Exception as e:
            logger.error(f"[Marketplace] Purchase exception for {listing_id}: {e}")
            return {"success": False, "status": 500, "error": str(e)}
    
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
            self.supabase.table("listing_usages").insert({
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
