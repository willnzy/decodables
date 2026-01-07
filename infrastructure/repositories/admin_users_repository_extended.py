"""
Admin Users Repository Extended - Admin user management operations.

@module infrastructure.repositories.admin_users_repository_extended
@version 1.0.0
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from core.database import retry_on_network_error

logger = logging.getLogger(__name__)


class SupabaseAdminUsersRepositoryExtended:
    """Extended repository for admin user management operations."""

    def __init__(self, client):
        self.client = client

    @retry_on_network_error()
    async def get_full_user_audit(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get complete user audit information."""
        profile = self.client.table("profiles").select("*").eq("id", user_id).execute()
        if not profile.data:
            return None
        
        projects = self.client.table("projects").select("id, title, created_at").eq("user_id", user_id).execute()
        transactions = self.client.table("credit_transactions").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(50).execute()
        purchases = self.client.table("marketplace_purchases").select("*").eq("buyer_id", user_id).execute()
        
        return {
            "profile": profile.data[0],
            "projects": projects.data or [],
            "transactions": transactions.data or [],
            "purchases": purchases.data or [],
        }

    @retry_on_network_error()
    async def admin_adjust_credits(self, user_id: str, amount: int, bucket: str, reason: str) -> Optional[Dict[str, Any]]:
        """Admin adjust user credits."""
        profile = self.client.table("profiles").select("credits_monthly, credits_permanent").eq("id", user_id).execute()
        
        if not profile.data:
            return None
        
        current = profile.data[0]
        
        if bucket == "monthly":
            new_value = max(0, current.get("credits_monthly", 0) + amount)
            update = {"credits_monthly": new_value}
        else:
            new_value = max(0, current.get("credits_permanent", 0) + amount)
            update = {"credits_permanent": new_value}
        
        self.client.table("profiles").update(update).eq("id", user_id).execute()
        
        # Log transaction
        self.client.table("credit_transactions").insert({
            "user_id": user_id,
            "amount": abs(amount),
            "bucket": bucket,
            "type": "admin_add" if amount > 0 else "admin_deduct",
            "description": reason,
        }).execute()
        
        return {"success": True, "new_value": new_value}

    @retry_on_network_error()
    async def admin_get_user_projects(self, user_id: str, page: int = 1, limit: int = 20, include_deleted: bool = True) -> List[Dict[str, Any]]:
        """Admin get user's projects."""
        offset = (page - 1) * limit
        query = self.client.table("projects").select("*").eq("user_id", user_id)
        
        if not include_deleted:
            query = query.eq("is_deleted", False)
        
        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        return result.data or []

    @retry_on_network_error()
    async def admin_log_operation(self, admin_id: str, operation_type: str, target_user_id: Optional[str] = None,
                            details: Optional[str] = None, reason: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Log admin operation."""
        result = self.client.table("admin_operations").insert({
            "admin_id": admin_id,
            "operation_type": operation_type,
            "target_user_id": target_user_id,
            "details": details,
            "reason": reason,
        }).execute()
        
        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def admin_get_operation_logs(self, page: int = 1, limit: int = 50, operation_type: Optional[str] = None,
                                 admin_id: Optional[str] = None, target_user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get admin operation logs."""
        offset = (page - 1) * limit
        query = self.client.table("admin_operations").select("*", count="exact")
        
        if operation_type:
            query = query.eq("operation_type", operation_type)
        if admin_id:
            query = query.eq("admin_id", admin_id)
        if target_user_id:
            query = query.eq("target_user_id", target_user_id)
        
        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        
        return {"items": result.data or [], "total": result.count or 0}
