"""
Invoice Repository Implementation (REPO-006 Phase 5+)

@module infrastructure.repositories.invoice_repository
@version 1.0.0

Provides data access for invoice records using Supabase.
Queries the payment_records table filtered for invoice types.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from core.database import retry_on_network_error

logger = logging.getLogger(__name__)


class SupabaseInvoiceRepository:
    """Supabase implementation of invoice repository."""

    def __init__(self, client):
        """
        Initialize repository with AsyncClient.

        Args:
            client: AsyncClient instance
        """
        self.client = client

    @retry_on_network_error()
    async def get_by_id(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """
        Get invoice by ID.

        Args:
            invoice_id: Invoice ID from payment_records table

        Returns:
            Invoice record or None
        """
        try:
            result = await self.client.table("payment_records").select("*").eq(
                "id", invoice_id
            ).single().execute()

            return result.data if result.data else None

        except Exception as e:
            logger.error(f"Failed to get invoice {invoice_id}: {e}")
            return None

    @retry_on_network_error()
    async def get_by_user(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get invoices for a user.

        Args:
            user_id: User ID
            limit: Max records
            offset: Pagination offset

        Returns:
            List of invoice records
        """
        try:
            result = await self.client.table("payment_records").select("*").eq(
                "user_id", user_id
            ).order("created_at", desc=True).range(offset, offset + limit - 1).execute()

            return result.data or []

        except Exception as e:
            logger.error(f"Failed to get invoices for user {user_id}: {e}")
            return []

    @retry_on_network_error()
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new invoice record.

        Args:
            data: Invoice data dict (user_id, amount_usd, currency, payment_type, etc)

        Returns:
            Created invoice record
        """
        try:
            # Ensure required fields
            if "created_at" not in data:
                data["created_at"] = datetime.now(timezone.utc).isoformat()
            if "status" not in data:
                data["status"] = "pending"

            result = await self.client.table("payment_records").insert(data).execute()

            return result.data[0] if result.data else {}

        except Exception as e:
            logger.error(f"Failed to create invoice: {e}")
            return {}

    @retry_on_network_error()
    async def get_by_status(
        self,
        status: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get invoices filtered by status.

        Args:
            status: Invoice status (pending, completed, failed, etc)
            limit: Max records
            offset: Pagination offset

        Returns:
            List of invoice records with given status
        """
        try:
            result = await self.client.table("payment_records").select("*").eq(
                "status", status
            ).order("created_at", desc=True).range(offset, offset + limit - 1).execute()

            return result.data or []

        except Exception as e:
            logger.error(f"Failed to get invoices by status {status}: {e}")
            return []

    @retry_on_network_error()
    async def update_status(
        self,
        invoice_id: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update invoice status.

        Args:
            invoice_id: Invoice ID
            status: New status
            metadata: Optional metadata to merge

        Returns:
            Updated invoice record
        """
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            if metadata:
                update_data["metadata"] = metadata

            result = await self.client.table("payment_records").update(update_data).eq(
                "id", invoice_id
            ).execute()

            return result.data[0] if result.data else None

        except Exception as e:
            logger.error(f"Failed to update invoice {invoice_id} status: {e}")
            return None

    @retry_on_network_error()
    async def get_by_date_range(
        self,
        start_date: str,
        end_date: str,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get invoices within a date range.

        Args:
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            user_id: Optional filter by user
            limit: Max records
            offset: Pagination offset

        Returns:
            List of invoice records in date range
        """
        try:
            query = self.client.table("payment_records").select("*").gte(
                "created_at", start_date
            ).lte(
                "created_at", end_date
            )

            if user_id:
                query = query.eq("user_id", user_id)

            result = await query.order("created_at", desc=True).range(
                offset, offset + limit - 1
            ).execute()

            return result.data or []

        except Exception as e:
            logger.error(f"Failed to get invoices in date range: {e}")
            return []
