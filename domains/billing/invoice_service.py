"""Invoice Service (SVC-009 Phase 2).

Handles invoice generation, retrieval, and lifecycle management.
Integrates with billing events and subscription changes.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class InvoiceService:
    """Manages invoice operations and retrieval.

    Responsibilities:
    1. Generate invoices for subscription charges or one-time purchases
    2. Retrieve user's invoice history
    3. Fetch specific invoice details
    4. Update invoice status (paid, pending, failed)
    """

    def __init__(self, db_client=None, stripe_client=None):
        """Initialize with database and optional Stripe client.

        Args:
            db_client: Database client for invoice queries
            stripe_client: Optional Stripe API client for sync operations
        """
        self._db = db_client
        self._stripe = stripe_client

    async def generate_invoice(
        self,
        user_id: str,
        amount_cents: int,
        description: str = "",
        invoice_type: str = "subscription",
    ) -> Dict[str, Any]:
        """Generate a new invoice.

        Args:
            user_id: The user's ID
            amount_cents: Invoice amount in cents
            description: Invoice description
            invoice_type: Type of invoice (subscription, one-time, refund, etc.)

        Returns:
            Dictionary with invoice details and ID
        """
        invoice_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        logger.info(
            "generate_invoice",
            extra={
                "event": "billing.invoice_generated",
                "user_id": user_id,
                "invoice_id": invoice_id,
                "amount_cents": amount_cents,
                "type": invoice_type,
            },
        )

        if self._db:
            await self._db.table("invoices").insert({
                "id": invoice_id,
                "user_id": user_id,
                "amount_cents": amount_cents,
                "description": description,
                "invoice_type": invoice_type,
                "status": "pending",
                "created_at": now,
                "updated_at": now,
            }).execute()

        return {
            "invoice_id": invoice_id,
            "user_id": user_id,
            "amount_cents": amount_cents,
            "status": "pending",
            "created_at": now,
        }

    async def get_user_invoices(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Retrieve paginated invoice history for a user.

        Args:
            user_id: The user's ID
            limit: Max invoices to return
            offset: Pagination offset

        Returns:
            List of invoice records
        """
        if not self._db:
            return []

        try:
            result = await self._db.table("invoices").select("*").eq(
                "user_id", user_id
            ).order("created_at", desc=True).range(offset, offset + limit - 1).execute()
            return result.data or []
        except Exception as e:
            logger.warning(
                "get_user_invoices failed",
                extra={
                    "event": "billing.invoice_list_error",
                    "user_id": user_id,
                    "error": str(e),
                },
            )
            return []

    async def get_invoice_by_id(
        self, invoice_id: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch a specific invoice by ID (with ownership check).

        Args:
            invoice_id: The invoice's ID
            user_id: The user's ID (for authorization)

        Returns:
            Invoice record or None if not found
        """
        if not self._db:
            return None

        try:
            result = await self._db.table("invoices").select("*").eq(
                "id", invoice_id
            ).eq("user_id", user_id).single().execute()
            return result.data if result.data else None
        except Exception as e:
            logger.warning(
                "get_invoice_by_id failed",
                extra={
                    "event": "billing.invoice_fetch_error",
                    "invoice_id": invoice_id,
                    "error": str(e),
                },
            )
            return None

    async def update_invoice_status(
        self, invoice_id: str, status: str
    ) -> Dict[str, Any]:
        """Update invoice status (paid, failed, etc.).

        Args:
            invoice_id: The invoice's ID
            status: New status value

        Returns:
            Updated invoice record
        """
        now = datetime.now(timezone.utc).isoformat()

        logger.info(
            "update_invoice_status",
            extra={
                "event": "billing.invoice_status_updated",
                "invoice_id": invoice_id,
                "new_status": status,
            },
        )

        if self._db:
            await self._db.table("invoices").update({
                "status": status,
                "updated_at": now,
            }).eq("id", invoice_id).execute()

        return {"invoice_id": invoice_id, "status": status, "updated_at": now}
