"""
Webhook Retry Service

Business logic for retrying failed webhook processing (P3-022).

@module domains.webhooks.webhook_retry_service
@version 1.0.0

Architecture: API → Service → Repository
"""

import logging
from typing import Dict, Any
from datetime import datetime, timezone, timedelta

from config import (
    WEBHOOK_MAX_RETRIES,
    WEBHOOK_RETRY_DELAYS,
    WEBHOOK_MAX_RETRY_AGE_HOURS,
    WEBHOOK_RETRY_BATCH_SIZE,
)
from infrastructure.repositories import (
    SupabaseWebhookRepository,
    SupabaseUserRepository,
    SupabaseCreditRepository,
    SupabasePaymentRepository,
)
from domains.webhooks.clerk_webhook_service import ClerkWebhookService
from domains.webhooks.stripe_webhook_service import StripeWebhookService

logger = logging.getLogger(__name__)


class WebhookRetryService:
    """
    Service for managing webhook retry logic.

    Responsibilities:
    - Fetch failed webhooks from database
    - Determine eligibility for retry
    - Reprocess events using webhook services
    - Update status and retry counts

    v1.0.0: Created for P3-022 (Webhook Retry Logic)
    """

    def __init__(
        self,
        webhook_repo: SupabaseWebhookRepository,
        clerk_service: ClerkWebhookService,
        stripe_service: StripeWebhookService,
    ):
        """Initialize retry service with repositories and webhook services."""
        self.webhook_repo = webhook_repo
        self.clerk_service = clerk_service
        self.stripe_service = stripe_service

    @staticmethod
    def get_retry_delay(retry_count: int) -> int:
        """
        Get retry delay in seconds for given retry count.

        Uses exponential backoff:
        - Retry 1: 1 minute
        - Retry 2: 5 minutes
        - Retry 3: 15 minutes
        - Retry 4: 1 hour
        - Retry 5: 2 hours

        Args:
            retry_count: Current retry attempt number (0-indexed)

        Returns:
            Delay in seconds before next retry
        """
        if retry_count >= len(WEBHOOK_RETRY_DELAYS):
            return WEBHOOK_RETRY_DELAYS[-1]
        return WEBHOOK_RETRY_DELAYS[retry_count]

    @staticmethod
    def should_retry(retry_count: int, hours_since_created: float) -> bool:
        """
        Determine if webhook should be retried.

        Args:
            retry_count: Number of times already retried
            hours_since_created: Hours since webhook was first created

        Returns:
            True if should retry, False otherwise
        """
        if retry_count >= WEBHOOK_MAX_RETRIES:
            return False

        if hours_since_created > WEBHOOK_MAX_RETRY_AGE_HOURS:
            return False

        return True

    async def retry_stripe_webhooks(self) -> Dict[str, int]:
        """
        Retry failed Stripe webhook events.

        Returns:
            Dict with counts: {processed, failed, skipped}
        """
        stats = {"processed": 0, "failed": 0, "skipped": 0}

        # Get failed events
        failed_events = await self.webhook_repo.get_failed_stripe_webhooks(
            max_retry_count=WEBHOOK_MAX_RETRIES,
            hours_since_created=WEBHOOK_MAX_RETRY_AGE_HOURS,
            limit=WEBHOOK_RETRY_BATCH_SIZE,
        )

        logger.info(f"[Webhook Retry] Found {len(failed_events)} failed Stripe webhooks")

        for event_record in failed_events:
            event_id = event_record["event_id"]
            retry_count = event_record["retry_count"]
            created_at = datetime.fromisoformat(event_record["created_at"].replace("Z", "+00:00"))
            hours_ago = (datetime.now(timezone.utc) - created_at).total_seconds() / 3600

            # Check eligibility
            if not self.should_retry(retry_count, hours_ago):
                stats["skipped"] += 1
                continue

            # Check if enough time has passed since last retry
            expected_delay = self.get_retry_delay(retry_count)
            seconds_since_created = (datetime.now(timezone.utc) - created_at).total_seconds()

            if seconds_since_created < expected_delay:
                stats["skipped"] += 1
                continue

            # Retry processing
            logger.info(
                f"[Webhook Retry] Retrying Stripe event {event_id} "
                f"(attempt {retry_count + 1}/{WEBHOOK_MAX_RETRIES})"
            )

            try:
                payload = event_record["payload"]
                await self.stripe_service.handle_event(payload)

                # Success
                await self.webhook_repo.update_stripe_webhook_status(
                    event_id=event_id,
                    processed=True,
                    error_message=None,
                    increment_retry=False,
                )
                stats["processed"] += 1
                logger.info(f"[Webhook Retry] ✅ Stripe event {event_id} reprocessed successfully")

            except Exception as e:
                # Failed
                error_msg = f"{type(e).__name__}: {str(e)}"
                await self.webhook_repo.update_stripe_webhook_status(
                    event_id=event_id,
                    processed=False,
                    error_message=error_msg,
                    increment_retry=True,
                )
                stats["failed"] += 1
                logger.error(f"[Webhook Retry] ❌ Stripe event {event_id} failed: {error_msg}")

        return stats

    async def retry_clerk_webhooks(self) -> Dict[str, int]:
        """
        Retry failed Clerk webhook events.

        Returns:
            Dict with counts: {processed, failed, skipped}
        """
        stats = {"processed": 0, "failed": 0, "skipped": 0}

        # Get failed events
        failed_events = await self.webhook_repo.get_failed_clerk_webhooks(
            max_retry_count=WEBHOOK_MAX_RETRIES,
            hours_since_created=WEBHOOK_MAX_RETRY_AGE_HOURS,
            limit=WEBHOOK_RETRY_BATCH_SIZE,
        )

        logger.info(f"[Webhook Retry] Found {len(failed_events)} failed Clerk webhooks")

        for event_record in failed_events:
            event_id = event_record["event_id"]
            retry_count = event_record["retry_count"]
            created_at = datetime.fromisoformat(event_record["created_at"].replace("Z", "+00:00"))
            hours_ago = (datetime.now(timezone.utc) - created_at).total_seconds() / 3600

            # Check eligibility
            if not self.should_retry(retry_count, hours_ago):
                stats["skipped"] += 1
                continue

            # Check if enough time has passed
            expected_delay = self.get_retry_delay(retry_count)
            seconds_since_created = (datetime.now(timezone.utc) - created_at).total_seconds()

            if seconds_since_created < expected_delay:
                stats["skipped"] += 1
                continue

            # Retry processing
            logger.info(
                f"[Webhook Retry] Retrying Clerk event {event_id} "
                f"(attempt {retry_count + 1}/{WEBHOOK_MAX_RETRIES})"
            )

            try:
                payload = event_record["payload"]
                await self.clerk_service.handle_event(payload)

                # Success
                await self.webhook_repo.update_clerk_webhook_status(
                    event_id=event_id,
                    processed=True,
                    error_message=None,
                    increment_retry=False,
                )
                stats["processed"] += 1
                logger.info(f"[Webhook Retry] ✅ Clerk event {event_id} reprocessed successfully")

            except Exception as e:
                # Failed
                error_msg = f"{type(e).__name__}: {str(e)}"
                await self.webhook_repo.update_clerk_webhook_status(
                    event_id=event_id,
                    processed=False,
                    error_message=error_msg,
                    increment_retry=True,
                )
                stats["failed"] += 1
                logger.error(f"[Webhook Retry] ❌ Clerk event {event_id} failed: {error_msg}")

        return stats

    async def retry_all_failed_webhooks(self) -> Dict[str, Any]:
        """
        Retry all failed webhooks (both Stripe and Clerk).

        Returns:
            Combined statistics
        """
        logger.info("[Webhook Retry] Starting retry task...")

        stripe_stats = await self.retry_stripe_webhooks()
        clerk_stats = await self.retry_clerk_webhooks()

        logger.info(
            f"[Webhook Retry] Stripe: {stripe_stats['processed']} OK, "
            f"{stripe_stats['failed']} failed, {stripe_stats['skipped']} skipped"
        )
        logger.info(
            f"[Webhook Retry] Clerk: {clerk_stats['processed']} OK, "
            f"{clerk_stats['failed']} failed, {clerk_stats['skipped']} skipped"
        )

        return {
            "stripe": stripe_stats,
            "clerk": clerk_stats,
            "total": {
                "processed": stripe_stats["processed"] + clerk_stats["processed"],
                "failed": stripe_stats["failed"] + clerk_stats["failed"],
                "skipped": stripe_stats["skipped"] + clerk_stats["skipped"],
            },
        }
