"""
User Repository
Database operations for users/profiles

@module repositories/user_repository
"""

from typing import Optional, List, Dict, Any
from .base import BaseRepository


class UserRepository(BaseRepository):
    """
    Repository for user/profile operations.
    """
    
    def __init__(self, supabase):
        super().__init__(supabase, "profiles")
    
    def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Find user by email.
        
        Args:
            email: User email
        
        Returns:
            User dict or None
        """
        result = self.supabase.table(self.table_name).select(
            "*"
        ).eq("email", email).single().execute()
        return result.data if result.data else None
    
    def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search users by email or username.
        
        Args:
            query: Search query
            limit: Max results
        
        Returns:
            Matching users
        """
        result = self.supabase.table(self.table_name).select(
            "*"
        ).or_(
            f"email.ilike.%{query}%,username.ilike.%{query}%"
        ).limit(limit).execute()
        return result.data or []
    
    def get_credit_transactions(
        self, 
        user_id: str, 
        page: int = 1, 
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get user's credit transactions.
        
        Args:
            user_id: User ID
            page: Page number
            limit: Items per page
        
        Returns:
            List of transactions
        """
        offset = (page - 1) * limit
        result = self.supabase.table("credit_transactions").select(
            "*"
        ).eq("user_id", user_id).order(
            "created_at", desc=True
        ).range(offset, offset + limit - 1).execute()
        return result.data or []
    
    def get_notifications(
        self, 
        user_id: str, 
        unread_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get user's notifications.
        
        Args:
            user_id: User ID
            unread_only: Filter unread only
        
        Returns:
            List of notifications
        """
        query = self.supabase.table("notifications").select(
            "*"
        ).or_(
            f"user_id.eq.{user_id},user_id.is.null"
        )
        
        if unread_only:
            query = query.eq("is_read", False)
        
        result = query.order("created_at", desc=True).execute()
        return result.data or []
    
    def mark_notification_read(
        self, 
        notification_id: str, 
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Mark notification as read.
        
        Args:
            notification_id: Notification ID
            user_id: User ID (for verification)
        
        Returns:
            Updated notification or None
        """
        result = self.supabase.table("notifications").update({
            "is_read": True
        }).eq("id", notification_id).execute()
        return result.data[0] if result.data else None
    
    def get_purchases(
        self, 
        user_id: str, 
        page: int = 1, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get user's marketplace purchases.
        
        Args:
            user_id: User ID
            page: Page number
            limit: Items per page
        
        Returns:
            List of purchases with listing details
        """
        offset = (page - 1) * limit
        result = self.supabase.table("user_purchases").select(
            "*, marketplace_listings(id, title, thumbnail_url, resource_type, resource_url, resource_id)"
        ).eq("user_id", user_id).order(
            "purchased_at", desc=True
        ).range(offset, offset + limit - 1).execute()
        return result.data or []
    
    def upsert_profile(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create or update user profile.
        
        Args:
            user_id: User ID
            data: Profile data
        
        Returns:
            Upserted profile
        """
        data["id"] = user_id
        result = self.supabase.table(self.table_name).upsert(data).execute()
        return result.data[0] if result.data else None
    
    def update_credits(
        self, 
        user_id: str, 
        credits_monthly: int, 
        credits_permanent: int
    ) -> Optional[Dict[str, Any]]:
        """
        Update user's credit balances.
        
        Args:
            user_id: User ID
            credits_monthly: New monthly balance
            credits_permanent: New permanent balance
        
        Returns:
            Updated profile or None
        """
        result = self.supabase.table(self.table_name).update({
            "credits_monthly": credits_monthly,
            "credits_permanent": credits_permanent
        }).eq("id", user_id).execute()
        return result.data[0] if result.data else None

