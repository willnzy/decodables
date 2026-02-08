"""Refund Service (SVC-010 Phase 2).

Handles refund processing, status tracking, and prorated refund calculations.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class RefundService:
    """Manages refund operations and calculations.

    Responsibilities:
    1. Process refunds for subscriptions or one-time purchases
    2. Track refund status and timeline
    3. Calculate prorated refund amounts based on usage
    4. Update refund status during payment processing
    """

    def __init__(self, db_client=None, stripe_client=None):
        """Initialize with database and optional Stripe client.

        Args:
            db_client: Database client for refund queries
            stripe_client: Optional Stripe API client for processing
        """
        self._db = db_client
        self._stripe = stripe_client

    async def process_refund(
        self,
        invoice_id: str,
        user_id: str,
        amount_cents: int,
        reason: str = "",
    ) -> Dict[str, Any]:
        """Process a refund for an invoice.

        Args:
            invoice_id: The invoice being refunded
            user_id: The user's ID
            amount_cents: Refund amount in cents
            reason: Reason for refund

        Returns:
            Dictionary with refund details
        """
        refund_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        logger.info(
            "process_refund",
            extra={
                "event": "billing.refund_processed",
                "user_id": user_id,
                "invoice_id": invoice_id,
                "refund_id": refund_id,
                "amount_cents": amount_cents,
            },
        )

        if self._db:
            await self._db.table("refunds").insert({
                "id": refund_id,
                "user_id": user_id,
                "invoice_id": invoice_id,
                "amount_cents": amount_cents,
                "reason": reason if reason else None,
                "status": "pending",
                "created_at": now,
                "updated_at": now,
            }).execute()

        return {
            "refund_id": refund_id,
            "user_id": user_id,
            "invoice_id": invoice_id,
            "amount_cents": amount_cents,
            "status": "pending",
            "created_at": now,
        }

    async def get_refund_status(self, refund_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a refund.

        Args:
            refund_id: The refund's ID

        Returns:
            Refund record or None if not found
        """
        if not self._db:
            return None

        try:
            result = await self._db.table("refunds").select("*").eq(
                "id", refund_id
            ).single().execute()
            return result.data if result.data else None
        except Exception as e:
            logger.warning(
                "get_refund_status failed",
                extra={
                    "event": "billing.refund_status_error",
                    "refund_id": refund_id,
                    "error": str(e),
                },
            )
            return None

    async def calculate_prorated_refund(
        self,
        total_amount_cents: int,
        billing_period_days: int,
        days_used: int,
    ) -> Dict[str, Any]:
        """Calculate prorated refund amount based on usage.

        Refund = total_amount * (remaining_days / billing_period_days)

        Args:
            total_amount_cents: Total charge in cents
            billing_period_days: Length of billing cycle (typically 30)
            days_used: Days the subscription was active

        Returns:
            Dictionary with refund calculation details
        """
        remaining_days = max(0, billing_period_days - days_used)
        refund_amount = (total_amount_cents * remaining_days) // billing_period_days

        logger.info(
            "calculate_prorated_refund",
            extra={
                "event": "billing.refund_calculated",
                "total_amount_cents": total_amount_cents,
                "billing_period_days": billing_period_days,
                "days_used": days_used,
                "refund_amount_cents": refund_amount,
            },
        )

        return {
            "total_amount_cents": total_amount_cents,
            "days_used": days_used,
            "remaining_days": remaining_days,
            "refund_amount_cents": refund_amount,
            "refund_percentage": (refund_amount / total_amount_cents * 100) if total_amount_cents > 0 else 0,
        }

    async def update_refund_status(
        self, refund_id: str, status: str
    ) -> Dict[str, Any]:
        """Update refund status (completed, failed, etc.).

        Args:
            refund_id: The refund's ID
            status: New status value

        Returns:
            Updated refund record
        """
        now = datetime.now(timezone.utc).isoformat()

        logger.info(
            "update_refund_status",
            extra={
                "event": "billing.refund_status_updated",
                "refund_id": refund_id,
                "new_status": status,
            },
        )

        if self._db:
            await self._db.table("refunds").update({
                "status": status,
                "updated_at": now,
            }).eq("id", refund_id).execute()

        return {"refund_id": refund_id, "status": status, "updated_at": now}
