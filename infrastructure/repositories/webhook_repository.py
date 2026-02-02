"""
Webhook Events Repository

Repository for webhook event storage and retry management (P3-022).

@module infrastructure.repositories.webhook_repository
@version 2.0.0 (AsyncClient migration)

Changes in v2.0:
- Migrated all methods to use AsyncClient with await
- All .execute() calls now properly awaited

Architecture: Service → Repository → Database
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, timezone

from core.database.retry import retry_on_network_error

logger = logging.getLogger(__name__)


class SupabaseWebhookRepository:
    """
    Supabase implementation of Webhook Events Repository.

    Handles webhook event storage, status tracking, and retry management.

    v1.0.0: Created for P3-022 (Webhook Retry Logic)
    """

    def __init__(self, client):
        """Initialize repository with database client."""
        self.client = client

    # ==========================================
    # Stripe Webhook Events
    # ==========================================

    @retry_on_network_error()
    async def create_stripe_webhook_event(
        self,
        event_id: str,
        event_type: str,
        payload: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Create new Stripe webhook event record.

        Args:
            event_id: Stripe event ID (unique)
            event_type: Event type (e.g., 'checkout.session.completed')
            payload: Full webhook payload

        Returns:
            Created event record or None if failed

        Note:
            Uses INSERT ... ON CONFLICT to handle duplicate events (idempotency)
        """
        try:
            result = await self.client.table("stripe_webhook_events").insert({
                "event_id": event_id,
                "event_type": event_type,
                "payload": payload,
                "processed": False,
                "retry_count": 0,
            }, upsert=False).execute()  # Don't update if exists

            return result.data[0] if result.data else None
        except Exception as e:
            if "duplicate key" in str(e).lower():
                logger.info(f"Stripe webhook event {event_id} already exists (idempotent)")
                return None
            logger.error(f"Failed to create Stripe webhook event: {e}")
            raise

    @retry_on_network_error()
    async def update_stripe_webhook_status(
        self,
        event_id: str,
        processed: bool,
        error_message: Optional[str] = None,
        increment_retry: bool = False,
    ) -> bool:
        """
        Update Stripe webhook event processing status.

        Args:
            event_id: Stripe event ID
            processed: Whether processing succeeded
            error_message: Error message if failed
            increment_retry: Whether to increment retry count

        Returns:
            True if update succeeded, False otherwise
        """
        try:
            update_data = {
                "processed": processed,
                "processed_at": datetime.now(timezone.utc).isoformat() if processed else None,
                "error_message": error_message,
            }

            if increment_retry:
                # Fetch current retry_count and increment
                current = await self.client.table("stripe_webhook_events").select("retry_count").eq(
                    "event_id", event_id
                ).single().execute()

                current_count = current.data.get("retry_count", 0) if current.data else 0

                result = await self.client.table("stripe_webhook_events").update({
                    **update_data,
                    "retry_count": current_count + 1,
                }).eq("event_id", event_id).execute()
            else:
                result = await self.client.table("stripe_webhook_events").update(
                    update_data
                ).eq("event_id", event_id).execute()

            return bool(result.data)
        except Exception as e:
            logger.error(f"Failed to update Stripe webhook status: {e}")
            return False

    @retry_on_network_error()
    async def get_failed_stripe_webhooks(
        self,
        max_retry_count: int = 5,
        hours_since_created: int = 72,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get failed Stripe webhooks eligible for retry.

        Args:
            max_retry_count: Maximum retry count to include
            hours_since_created: Maximum age in hours
            limit: Maximum number to return

        Returns:
            List of failed webhook events
        """
        try:
            cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=hours_since_created)).isoformat()

            result = await self.client.table("stripe_webhook_events").select("*").eq(
                "processed", False
            ).lt("retry_count", max_retry_count).gte(
                "created_at", cutoff_time
            ).order("created_at", desc=False).limit(limit).execute()

            return result.data or []
        except Exception as e:
            logger.error(f"Failed to get failed Stripe webhooks: {e}")
            return []

