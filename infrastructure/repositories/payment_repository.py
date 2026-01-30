"""
Payment Repository Implementation - Payment records data access.

@module infrastructure.repositories.payment_repository
@version 2.0.0 (AsyncClient migration)

Changes in v2.0:
- Migrated all methods to use AsyncClient with await
- All .execute() calls now properly awaited
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

from core.database import DatabaseClient, retry_on_network_error

logger = logging.getLogger(__name__)


class SupabasePaymentRepository:
    """Supabase implementation of payment repository."""

    def __init__(self, client: DatabaseClient):
        """
        Initialize repository with database client.

        Args:
            client: Supabase database client
        """
        self.client = client

    @retry_on_network_error()
    async def create(
        self,
        user_id: str,
        amount_usd: float,
        currency: str,
        payment_type: str,
        stripe_payment_intent_id: Optional[str] = None,
        metadata: Optional[dict] = None,
        timezone_str: str = "UTC",
        payment_method: str = "card",
        status: str = "succeeded",
    ) -> Optional[Dict[str, Any]]:
        """
        Log payment record.

        Args:
            user_id: User ID
            amount_usd: Payment amount in USD
            currency: Currency code
            payment_type: Payment type
            stripe_payment_intent_id: Stripe payment intent ID
            metadata: Additional metadata
            timezone_str: User timezone
            payment_method: Payment method (default: card)
            status: Payment status (default: succeeded)

        Returns:
            Created payment record
        """
        result = await self.client.table("payment_records").insert({
            "user_id": user_id,
            "amount_usd": amount_usd,
            "currency": currency,
            "payment_type": payment_type,
            "stripe_payment_intent_id": stripe_payment_intent_id,
            "payment_method": payment_method,
            "metadata": metadata or {},
            "timezone": timezone_str,
            "status": status,
        }).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def get_by_user(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get user payment records.

        Args:
            user_id: User ID
            page: Page number
            limit: Items per page

        Returns:
            List of payment records
        """
        offset = (page - 1) * limit
        result = await self.client.table("payment_records").select("*").eq(
            "user_id", user_id
        ).order("created_at", desc=True).range(
            offset, offset + limit - 1
        ).execute()

        return result.data or []

    @retry_on_network_error()
    async def get_all_paginated(
        self,
        page: int = 1,
        limit: int = 50,
        user_id: Optional[str] = None,
        payment_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Admin get all payment records with pagination.

        Args:
            page: Page number
            limit: Items per page
            user_id: Filter by user ID
            payment_type: Filter by payment type

        Returns:
            Dict with items and total count
        """
        offset = (page - 1) * limit
        query = self.client.table("payment_records").select(
            "*, profiles(email, username)", count="exact"
        )

        if user_id:
            query = query.eq("user_id", user_id)
        if payment_type:
            query = query.eq("payment_type", payment_type)

        result = await query.order("created_at", desc=True).range(
            offset, offset + limit - 1
        ).execute()

        return {
            "items": result.data or [],
            "total": result.count or 0
        }

    @retry_on_network_error()
    async def get_by_stripe_id(
        self,
        stripe_payment_intent_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get payment by Stripe payment intent ID.

        Args:
            stripe_payment_intent_id: Stripe payment intent ID

        Returns:
            Payment record or None
        """
        result = await self.client.table("payment_records").select("*").eq(
            "stripe_payment_intent_id", stripe_payment_intent_id
        ).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def update_status(
        self,
        payment_id: str,
        status: str,
        metadata: Optional[dict] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update payment status.

        Args:
            payment_id: Payment ID
            status: New status
            metadata: Optional metadata to merge

        Returns:
            Updated payment record
        """
        update_data = {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        if metadata:
            update_data["metadata"] = metadata

        result = await self.client.table("payment_records").update(update_data).eq(
            "id", payment_id
        ).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def get_revenue_stats(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        group_by: str = "day"
    ) -> Dict[str, Any]:
        """
        Get revenue statistics.

        Args:
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            group_by: Grouping method (day, week, month)

        Returns:
            Revenue statistics dict
        """
        if not start_date:
            start_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        if not end_date:
            end_date = datetime.now(timezone.utc).isoformat()

        result = await self.client.table("payment_records").select(
            "amount_usd, created_at, payment_type"
        ).gte("created_at", start_date).lte(
            "created_at", end_date
        ).eq("status", "succeeded").execute()

        payments = result.data or []

        # Calculate totals
        total = sum(p.get("amount_usd", 0) for p in payments)

        # Group by type
        by_type = {}
        for p in payments:
            pt = p.get("payment_type", "unknown")
            by_type[pt] = by_type.get(pt, 0) + p.get("amount_usd", 0)

        # Group by date
        by_date = {}
        for p in payments:
            date_str = p.get("created_at", "")[:10]
            by_date[date_str] = by_date.get(date_str, 0) + p.get("amount_usd", 0)

        return {
            "total": total,
            "by_type": by_type,
            "by_date": [{"date": k, "amount_usd": v} for k, v in sorted(by_date.items())],
            "transaction_count": len(payments),
        }
