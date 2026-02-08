"""
Refund Repository Implementation (REPO-007 Phase 5+)

@module infrastructure.repositories.refund_repository
@version 1.0.0

Provides data access for refund records using Supabase.
Queries the payment_records table filtered for refund type payment records.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from core.database import retry_on_network_error

logger = logging.getLogger(__name__)


class SupabaseRefundRepository:
    """Supabase implementation of refund repository."""

    def __init__(self, client):
        """
        Initialize repository with AsyncClient.

        Args:
            client: AsyncClient instance
        """
        self.client = client

    @retry_on_network_error()
    async def get_by_id(self, refund_id: str) -> Optional[Dict[str, Any]]:
        """
        Get refund by ID.

        Args:
            refund_id: Refund ID from payment_records table

        Returns:
            Refund record or None
        """
        try:
            result = await self.client.table("payment_records").select("*").eq(
                "id", refund_id
            ).eq(
                "payment_type", "refund"
            ).single().execute()

            return result.data if result.data else None

        except Exception as e:
            logger.error(f"Failed to get refund {refund_id}: {e}")
            return None

    @retry_on_network_error()
    async def get_by_user(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get refunds for a user.

        Args:
            user_id: User ID
            limit: Max records
            offset: Pagination offset

        Returns:
            List of refund records
        """
        try:
            result = await self.client.table("payment_records").select("*").eq(
                "user_id", user_id
            ).eq(
                "payment_type", "refund"
            ).order("created_at", desc=True).range(offset, offset + limit - 1).execute()

            return result.data or []

        except Exception as e:
            logger.error(f"Failed to get refunds for user {user_id}: {e}")
            return []

    @retry_on_network_error()
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new refund record.

        Args:
            data: Refund data dict (user_id, amount_usd, currency, stripe_refund_id, etc)

        Returns:
            Created refund record
        """
        try:
            # Ensure required fields
            if "payment_type" not in data:
                data["payment_type"] = "refund"
            if "created_at" not in data:
                data["created_at"] = datetime.now(timezone.utc).isoformat()
            if "status" not in data:
                data["status"] = "succeeded"

            result = await self.client.table("payment_records").insert(data).execute()

            return result.data[0] if result.data else {}

        except Exception as e:
            logger.error(f"Failed to create refund: {e}")
            return {}

    @retry_on_network_error()
    async def get_by_stripe_refund_id(
        self,
        stripe_refund_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get refund by Stripe refund ID (for idempotency).

        Args:
            stripe_refund_id: Stripe refund ID

        Returns:
            Refund record or None
        """
        try:
            result = await self.client.table("payment_records").select("*").eq(
                "stripe_refund_id", stripe_refund_id
            ).eq(
                "payment_type", "refund"
            ).single().execute()

            return result.data if result.data else None

        except Exception as e:
            logger.error(f"Failed to get refund by stripe_refund_id {stripe_refund_id}: {e}")
            return None

    @retry_on_network_error()
    async def get_by_original_payment_id(
        self,
        payment_intent_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all refunds for an original payment by payment intent ID.

        Args:
            payment_intent_id: Original Stripe payment intent ID
            limit: Max records
            offset: Pagination offset

        Returns:
            List of refund records for this payment
        """
        try:
            result = await self.client.table("payment_records").select("*").eq(
                "stripe_payment_intent_id", payment_intent_id
            ).eq(
                "payment_type", "refund"
            ).order("created_at", desc=True).range(offset, offset + limit - 1).execute()

            return result.data or []

        except Exception as e:
            logger.error(f"Failed to get refunds for payment {payment_intent_id}: {e}")
            return []

    @retry_on_network_error()
    async def get_by_status(
        self,
        status: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get refunds filtered by status.

        Args:
            status: Refund status (succeeded, failed, pending, etc)
            limit: Max records
            offset: Pagination offset

        Returns:
            List of refund records with given status
        """
        try:
            result = await self.client.table("payment_records").select("*").eq(
                "payment_type", "refund"
            ).eq(
                "status", status
            ).order("created_at", desc=True).range(offset, offset + limit - 1).execute()

            return result.data or []

        except Exception as e:
            logger.error(f"Failed to get refunds by status {status}: {e}")
            return []

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
        Get refunds within a date range.

        Args:
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            user_id: Optional filter by user
            limit: Max records
            offset: Pagination offset

        Returns:
            List of refund records in date range
        """
        try:
            query = self.client.table("payment_records").select("*").gte(
                "created_at", start_date
            ).lte(
                "created_at", end_date
            ).eq(
                "payment_type", "refund"
            )

            if user_id:
                query = query.eq("user_id", user_id)

            result = await query.order("created_at", desc=True).range(
                offset, offset + limit - 1
            ).execute()

            return result.data or []

        except Exception as e:
            logger.error(f"Failed to get refunds in date range: {e}")
            return []

    @retry_on_network_error()
    async def get_total_refunded_for_user(self, user_id: str) -> float:
        """
        Get total refunded amount for a user.

        Args:
            user_id: User ID

        Returns:
            Total refunded amount in USD
        """
        try:
            result = await self.client.table("payment_records").select(
                "amount_usd"
            ).eq(
                "user_id", user_id
            ).eq(
                "payment_type", "refund"
            ).eq(
                "status", "succeeded"
            ).execute()

            refunds = result.data or []
            return sum(r.get("amount_usd", 0) for r in refunds)

        except Exception as e:
            logger.error(f"Failed to get total refunded for user {user_id}: {e}")
            return 0.0

    @retry_on_network_error()
    async def update_status(
        self,
        refund_id: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update refund status.

        Args:
            refund_id: Refund ID
            status: New status
            metadata: Optional metadata to merge

        Returns:
            Updated refund record
        """
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            if metadata:
                update_data["metadata"] = metadata

            result = await self.client.table("payment_records").update(update_data).eq(
                "id", refund_id
            ).execute()

            return result.data[0] if result.data else None

        except Exception as e:
            logger.error(f"Failed to update refund {refund_id} status: {e}")
            return None
