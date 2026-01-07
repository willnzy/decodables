"""
Admin Moderation Repository Extended - Content moderation operations.

@module infrastructure.repositories.admin_moderation_repository_extended
@version 1.0.0
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from core.database import retry_on_network_error

logger = logging.getLogger(__name__)


class SupabaseAdminModerationRepositoryExtended:
    """Extended repository for admin content moderation operations."""

    def __init__(self, client):
        self.client = client

    @retry_on_network_error()
    async def admin_get_moderation_list(self, status: str = "pending", page: int = 1, limit: int = 20) -> List[Dict[str, Any]]:
        """Get moderation queue."""
        offset = (page - 1) * limit
        query = self.client.table("marketplace_listings").select(
            "*, profiles(username, email)"
        ).eq("is_deleted", False)
        
        if status:
            query = query.eq("moderation_status", status)
        
        result = query.order("submitted_at", desc=True).range(offset, offset + limit - 1).execute()
        return result.data or []

    @retry_on_network_error()
    async def admin_get_moderation_detail(self, listing_id: str) -> Optional[Dict[str, Any]]:
        """Get listing detail for moderation."""
        result = self.client.table("marketplace_listings").select(
            "*, profiles(username, email, tier)"
        ).eq("id", listing_id).execute()
        
        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def admin_approve_listing(self, listing_id: str, admin_id: str) -> Optional[Dict[str, Any]]:
        """Approve listing."""
        result = self.client.table("marketplace_listings").update({
            "moderation_status": "approved",
            "is_public": True,
            "moderated_at": datetime.now(timezone.utc).isoformat(),
            "moderated_by": admin_id,
        }).eq("id", listing_id).execute()
        
        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def admin_reject_listing(self, listing_id: str, admin_id: str, reason: str) -> Optional[Dict[str, Any]]:
        """Reject listing."""
        result = self.client.table("marketplace_listings").update({
            "moderation_status": "rejected",
            "is_public": False,
            "rejection_reason": reason,
            "moderated_at": datetime.now(timezone.utc).isoformat(),
            "moderated_by": admin_id,
        }).eq("id", listing_id).execute()
        
        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def admin_delete_listing(self, listing_id: str) -> Optional[Dict[str, Any]]:
        """Delete listing."""
        result = self.client.table("marketplace_listings").update({
            "is_deleted": True,
            "deleted_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", listing_id).execute()
        
        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def admin_unpublish_listing(self, listing_id: str) -> Optional[Dict[str, Any]]:
        """Unpublish listing."""
        result = self.client.table("marketplace_listings").update({
            "is_public": False,
        }).eq("id", listing_id).execute()
        
        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def admin_get_reports(self, status: Optional[str] = None, page: int = 1, limit: int = 20) -> List[Dict[str, Any]]:
        """Get content reports."""
        offset = (page - 1) * limit
        query = self.client.table("reports").select(
            "*, profiles!reporter_id(username), marketplace_listings(title)"
        )
        
        if status:
            query = query.eq("status", status)
        
        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        return result.data or []

    @retry_on_network_error()
    async def admin_get_reports_count(self, status: Optional[str] = None) -> int:
        """Get reports count."""
        query = self.client.table("reports").select("id", count="exact")
        
        if status:
            query = query.eq("status", status)
        
        result = query.execute()
        return result.count or 0

    @retry_on_network_error()
    async def admin_respond_to_report(self, report_id: str, admin_id: str, action: str, response: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Respond to report."""
        result = self.client.table("reports").update({
            "status": action,
            "admin_response": response,
            "responded_by": admin_id,
            "responded_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", report_id).execute()
        
        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def admin_get_report_detail(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get report detail."""
        result = self.client.table("reports").select(
            "*, profiles!reporter_id(username, email), marketplace_listings(*)"
        ).eq("id", report_id).execute()
        
        return result.data[0] if result.data else None
