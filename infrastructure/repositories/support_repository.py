"""
Support Repository - Support ticket management operations.

@module infrastructure.repositories.support_repository
@version 2.0.0 (AsyncClient migration)

Changes in v2.0:
- Removed lazy loading (client parameter now mandatory)
- All methods use AsyncClient
- Removed get_supabase_client() import (sync client)

Provides support ticket CRUD operations.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from core.database import retry_on_network_error

logger = logging.getLogger(__name__)


class SupabaseSupportRepository:
    """
    Support repository for support tickets table operations.

    v2.0: AsyncClient required (no lazy loading).
    """

    def __init__(self, client):
        """
        Initialize repository with AsyncClient.

        Args:
            client: AsyncClient instance (required)

        Raises:
            ValueError: If client is None
        """
        if client is None:
            raise ValueError("AsyncClient required for SupabaseSupportRepository")
        self._client = client

    @property
    def client(self):
        """Get AsyncClient instance."""
        return self._client

    @retry_on_network_error()
    async def create_ticket(
        self,
        user_id: str,
        subject: str,
        message: str,
        priority: str = "medium",
        category: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Create a new support ticket."""
        result = self.client.table("support_tickets").insert({
            "user_id": user_id,
            "subject": subject,
            "message": message,
            "priority": priority,
            "category": category,
            "status": "open",
        }).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def get_user_tickets(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get user support tickets."""
        query = self.client.table("support_tickets").select("*").eq(
            "user_id", user_id
        )

        if status:
            query = query.eq("status", status)

        result = query.order("created_at", desc=True).limit(limit).execute()
        return result.data or []

    @retry_on_network_error()
    async def update_ticket_status(
        self,
        ticket_id: str,
        status: str,
        admin_note: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Update ticket status."""
        update_data = {"status": status}
        if admin_note:
            update_data["admin_note"] = admin_note

        result = self.client.table("support_tickets").update(update_data).eq(
            "id", ticket_id
        ).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def add_reply(
        self,
        ticket_id: str,
        user_id: str,
        message: str,
        is_admin: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Add a reply to a ticket."""
        result = self.client.table("support_replies").insert({
            "ticket_id": ticket_id,
            "user_id": user_id,
            "message": message,
            "is_admin_reply": is_admin,
        }).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def create_report(
        self,
        user_id: str,
        listing_id: str,
        reason: str
    ) -> Optional[Dict[str, Any]]:
        """
        Create a content report for a marketplace listing.

        Args:
            user_id: Reporter user ID
            listing_id: Listing being reported
            reason: Report reason

        Returns:
            Created report or None

        Raises:
            Exception: If user already reported this listing
        """
        # Check if user already reported this listing
        existing = self.client.table("v_marketplace_reports").select("id").eq(
            "reporter_id", user_id
        ).eq("listing_id", listing_id).execute()

        if existing.data:
            raise Exception("You have already reported this listing")

        result = self.client.table("v_marketplace_reports").insert({
            "reporter_id": user_id,
            "listing_id": listing_id,
            "reason": reason,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def get_user_reports(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get reports submitted by a user.

        Args:
            user_id: User ID
            page: Page number (1-indexed)
            limit: Items per page

        Returns:
            List of reports
        """
        start = (page - 1) * limit
        end = start + limit - 1

        result = self.client.table("v_marketplace_reports").select("*").eq(
            "reporter_id", user_id
        ).order("created_at", desc=True).range(start, end).execute()

        return result.data or []

    @retry_on_network_error()
    async def get_user_reports_with_count(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Get reports submitted by a user with total count.

        M-HIGH-002 fix: Returns accurate total for pagination.

        Args:
            user_id: User ID
            page: Page number (1-indexed)
            limit: Items per page

        Returns:
            Tuple of (List of reports, total_count)
        """
        start = (page - 1) * limit
        end = start + limit - 1

        result = self.client.table("v_marketplace_reports").select(
            "*", count="exact"
        ).eq("reporter_id", user_id).order(
            "created_at", desc=True
        ).range(start, end).execute()

        reports = result.data or []
        total_count = result.count if result.count is not None else len(reports)

        return reports, total_count
