"""
Support Repository - Support ticket management operations.

@module infrastructure.repositories.support_repository
@version 1.0.0

Provides support ticket CRUD operations.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from core.database import get_supabase_client, retry_on_network_error

logger = logging.getLogger(__name__)


class SupabaseSupportRepository:
    """
    Support repository for support tickets table operations.
    """

    def __init__(self, client=None):
        """Initialize repository with database client."""
        self._client = client

    @property
    def client(self):
        """Lazy load Supabase client."""
        if self._client is None:
            self._client = get_supabase_client()
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
