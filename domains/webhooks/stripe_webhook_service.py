"""
Stripe Webhook Service

Handles Stripe payment webhook events.

@version 2.1.0 (Phase 5 Part C - True Atomicity)

Architecture: API → StripeWebhookService → Repositories/RPC

v2.1.0 Changes:
- Credits purchase now uses atomic RPC (process_credit_purchase)
- Payment record + credits addition in single transaction
- Eliminates half-failure state in credit purchases

v2.0.0 Changes:
- Migrated to AsyncClient for all database operations
- Removed get_supabase_client() usage
- All direct DB calls now use self.db_client (AsyncClient)
"""

import logging
from typing import Dict, Any, Optional

from infrastructure.repositories import (
    SupabaseUserRepository,
    SupabaseCreditRepository,
    SupabasePaymentRepository,
)
from domains.billing.payment_service import (
    construct_event,
    get_tier_from_price_id,
    get_credits_amount,
)
from infrastructure.monitoring.analytics_tracker import AnalyticsEvents, track_payment

logger = logging.getLogger(__name__)


class StripeWebhookService:
    """
    Stripe Webhook Service - Handles Stripe payment events.

    This service processes Stripe webhook events for payments,
    subscriptions, and credits purchases.

    Architecture: API → StripeWebhookService → Repositories

    v2.0.0: Migrated to AsyncClient
    v1.0.0: Created for DDD compliance
    """

    def __init__(
        self,
        user_repo: SupabaseUserRepository,
        credit_repo: SupabaseCreditRepository,
        payment_repo: SupabasePaymentRepository,
        db_client = None,  # AsyncClient for direct database operations
        tier_service = None,  # WS2: TierService for dynamic credits configuration
        activity_log_repo = None,  # WS2: ActivityLogRepository for unified activity logging
        subscription_repo = None,  # WS3: SubscriptionRepository for atomic RPC calls
    ):
        """
        Initialize Stripe Webhook Service.

        Args:
            user_repo: User repository for subscription tier updates
            credit_repo: Credit repository for credits operations
            payment_repo: Payment repository for payment records
            db_client: AsyncClient for direct database operations (activity logs, RPC calls)
            tier_service: TierService for dynamic tier/credits configuration
            activity_log_repo: ActivityLogRepository for activity logging
            subscription_repo: SubscriptionRepository for atomic subscription RPC calls
        """
        self.user_repo = user_repo
        self.credit_repo = credit_repo
        self.payment_repo = payment_repo
        self.db_client = db_client or user_repo.client  # Use repo's client if not provided
        self.tier_service = tier_service
        self.activity_log_repo = activity_log_repo
        self.subscription_repo = subscription_repo

    def verify_signature(self, payload: bytes, sig_header: str) -> Dict[str, Any]:
        """
        Verify Stripe webhook signature.

        Args:
            payload: Raw request body
            sig_header: Stripe-Signature header value

        Returns:
            Verified event dictionary

        Raises:
            Exception: If signature verification fails
        """
        return construct_event(payload, sig_header)

    async def is_duplicate_event(self, event_id: str, event_type: str, event: Dict[str, Any]) -> bool:
        """
        Check if webhook event already processed (idempotency).

        Uses PostgreSQL RPC for atomic check-and-insert.

        Args:
            event_id: Stripe event ID
            event_type: Stripe event type
            event: Full event payload (for logging)

        Returns:
            True if event already processed, False otherwise

        Raises:
            Exception: If idempotency check fails for critical events
        """
        try:
            result = await self.db_client.rpc("check_webhook_idempotency", {
                "p_event_id": event_id,
                "p_event_type": event_type,
                "p_payload": event
            }).execute()

            # RPC returns JSONB — handle list or dict
            check_data = result.data[0] if isinstance(result.data, list) else result.data
            if check_data and check_data.get("idempotent"):
                logger.info(f"[Webhook] Duplicate event ignored: {event_id} ({event_type})")
                return True
            return False
        except Exception as e:
            # Fail-safe: reject critical events if idempotency check fails
            critical_events = ['checkout.session.completed', 'invoice.payment_succeeded']
            if event_type in critical_events:
                logger.error(f"[Webhook] CRITICAL: Idempotency check failed for {event_type}, rejecting: {e}")
                raise
            else:
                logger.warning(f"[Webhook] Idempotency check failed for {event_id}: {e}")
                return False

    async def update_webhook_result(self, event_id: str, result: Dict[str, Any]) -> None:
        """
        Update webhook processing result in database.

        Best-effort operation, failures are logged but not raised.

        Args:
            event_id: Stripe event ID
            result: Processing result dictionary
        """
        try:
            self.db_client.rpc("update_webhook_result", {
                "p_event_id": event_id,
                "p_result": result
            }).execute()
        except Exception as e:
            logger.warning(f"[Webhook] Failed to update result for {event_id}: {e}")

    async def handle_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route and handle Stripe webhook event.

        Args:
            event: Verified Stripe webhook event

        Returns:
            Dict with status and optional action/error details
        """
        event_type = event.get("type")

        # Validate event structure
        if not event.get("id"):
            logger.error(f"[Webhook] Received Stripe event without id")
            return {"status": "error", "error": "missing_event_id"}
        if not event_type:
            logger.error(f"[Webhook] Received Stripe event without type: {event['id']}")
            return {"status": "error", "error": "missing_event_type"}

        # Route to appropriate handler
        if event_type == "checkout.session.completed":
            return await self._handle_checkout_completed(event)
        elif event_type == "invoice.payment_succeeded":
            return await self._handle_invoice_payment(event)
        elif event_type in ["customer.subscription.deleted", "customer.subscription.updated"]:
            return await self._handle_subscription_change(event)
        elif event_type == "charge.refunded":
            # P0-010 fix: Process refunds via webhook for transaction safety
            return await self._handle_charge_refunded(event)

        return {"status": "ok"}

    async def _handle_checkout_completed(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle checkout.session.completed event.

        Processes:
        1. Subscription purchases (t2, t3)
        2. Credits purchases (credits_100, credits_500, credits_2000)

        Transaction order (v2.4.0):
        1. Payment record FIRST (audit trail)
        2. Credits/tier update (actual benefit)
        3. Activity logging and analytics (non-critical)

        Args:
            event: Stripe checkout.session.completed event

        Returns:
            Dict with status, action, and relevant IDs
        """
        session = event["data"]["object"]
        session_id = session.get("id", "unknown")

        # Validate metadata
        metadata = session.get("metadata", {})
        if not metadata:
            logger.error(f"[Webhook] checkout.session.completed missing metadata: session={session_id}")
            return {"status": "error", "error": "missing_metadata", "session_id": session_id}

        uid = metadata.get("user_id")
        plan = metadata.get("plan_type")

        if not uid or not plan:
            logger.error(f"[Webhook] checkout.session.completed incomplete metadata: uid={uid}, plan={plan}, session={session_id}")
            return {"status": "error", "error": "incomplete_metadata", "session_id": session_id}

        amount_total = session.get("amount_total", 0)  # Amount in cents
        currency = session.get("currency", "usd").upper()

        # Validate amount
        if amount_total <= 0:
            logger.error(f"[Webhook] Invalid amount for checkout {session_id}: {amount_total}")
            return {"status": "error", "error": "invalid_amount", "session_id": session_id}

        # Handle credits purchase (credits_100, credits_500, credits_2000)
        credits_amount = get_credits_amount(plan)
        if credits_amount > 0:
            return await self._process_credits_purchase(uid, credits_amount, amount_total, currency, session_id)

        # Handle subscription purchase (t2, t3)
        elif plan in ["t2", "t3"]:
            return await self._process_subscription_start(uid, plan, amount_total, currency, session, session_id)

        return {"status": "ok"}

    async def _process_credits_purchase(
        self,
        uid: str,
        credits_amount: int,
        amount_total: int,
        currency: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Process credits purchase using atomic RPC.

        v2.1.0: Phase 5 Part C - True Atomicity
        - Uses process_credit_purchase RPC for atomic operation
        - Payment record + credits addition in single transaction
        - Eliminates half-failure state

        Args:
            uid: User ID
            credits_amount: Number of credits to add
            amount_total: Payment amount in cents
            currency: Payment currency
            session_id: Stripe session ID

        Returns:
            Dict with status and action details
        """
        # ============================================
        # ATOMIC OPERATION: Payment + Credits + Transaction
        # All three operations in a single database transaction
        # ============================================
        try:
            result = await self.db_client.rpc("process_credit_purchase", {
                "p_user_id": uid,
                "p_credits_amount": credits_amount,
                "p_payment_amount": amount_total,
                "p_currency": currency,
                "p_session_id": session_id,
                "p_idempotency_key": f"credit_purchase_{session_id}",
            }).execute()

            # Validate RPC response
            if not result.data:
                logger.error(f"[Webhook] RPC process_credit_purchase returned no data for user {uid}")
                return {"status": "error", "error": "rpc_no_data", "session_id": session_id}

            # Handle list response (PostgreSQL returns array)
            data = result.data[0] if isinstance(result.data, list) else result.data

            if not data.get("success"):
                error_msg = data.get("error_message", "Unknown error")
                logger.error(f"[Webhook] RPC process_credit_purchase failed for user {uid}: {error_msg}")
                return {"status": "error", "error": error_msg, "session_id": session_id}

            payment_id = data.get("payment_id")
            balance_permanent = data.get("balance_permanent", 0)

            logger.info(
                f"[Webhook] Credits purchase completed atomically: "
                f"user={uid[:8]}..., credits={credits_amount}, "
                f"payment_id={payment_id}, new_balance={balance_permanent}"
            )

        except Exception as e:
            logger.error(f"[Webhook] Atomic credit purchase failed for user {uid}: {e}")
            return {"status": "error", "error": "atomic_operation_failed", "session_id": session_id}

        # ============================================
        # NON-CRITICAL: Analytics & Logging (best-effort)
        # These can fail without affecting the core transaction
        # ============================================

        # Log activity (non-critical)
        if self.activity_log_repo:
            await self.activity_log_repo.log_activity(
                user_id=uid,
                action="credits_purchase",
                metadata={
                    "amount": credits_amount,
                    "payment": amount_total,
                    "session_id": session_id,
                    "payment_id": str(payment_id) if payment_id else None,
                },
            )

        # Track analytics (non-critical)
        try:
            track_payment(
                uid,
                AnalyticsEvents.CREDITS_PURCHASED,
                amount_total,
                currency,
                extra_properties={"credits_amount": credits_amount}
            )
        except Exception as e:
            logger.warning(f"Failed to track analytics: {e}")

        # Log webhook operation to audit trail (non-critical)
        try:
            from infrastructure.logging.activity_logger import log_webhook_operation
            await log_webhook_operation(
                operation_type="webhook_credits_purchase",
                source="stripe",
                target_user_id=uid,
                details=f"Credits purchased: {credits_amount} credits for ${amount_total/100:.2f}",
                metadata={
                    "session_id": session_id,
                    "credits_amount": credits_amount,
                    "amount_paid": amount_total,
                    "currency": currency,
                    "payment_id": str(payment_id) if payment_id else None,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to log webhook operation: {e}")

        return {"status": "ok", "action": "credits_added", "user_id": uid, "credits": credits_amount}

    async def _process_subscription_start(
        self,
        uid: str,
        plan: str,
        amount_total: int,
        currency: str,
        session: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """
        Process subscription start (first payment).

        v2.4.0: W-P0-2 fix - Uses atomic RPC for transaction consistency

        Args:
            uid: User ID
            plan: Plan type (t2, t3)
            amount_total: Payment amount in cents
            currency: Payment currency
            session: Full session object
            session_id: Stripe session ID

        Returns:
            Dict with status and action details
        """
        # Validate customer_id
        stripe_customer_id = session.get("customer")
        if not stripe_customer_id:
            logger.error(f"[Webhook] Missing customer_id in checkout session for user {uid}")
            return {"status": "error", "error": "missing_customer_id", "user_id": uid}

        # WS2: Get monthly credits from TierService (was hardcoded 500/1000)
        if self.tier_service:
            amt = await self.tier_service.get_monthly_credits(plan)
        else:
            # Emergency fallback (should never happen with proper DI)
            from domains.identity.constants import TIER_MONTHLY_CREDITS
            amt = TIER_MONTHLY_CREDITS.get(plan, 0)

        # WS3: Atomic subscription start via Repository → RPC
        try:
            rpc_result = await self.subscription_repo.start_subscription(
                user_id=uid,
                plan=plan,
                stripe_customer_id=stripe_customer_id,
                credits_amount=amt,
                payment_amount=amount_total,
                currency=currency,
                session_id=session_id,
            )

            if rpc_result.get("already_processed"):
                logger.info(f"[Webhook] Subscription start already processed for user {uid} (idempotent)")

        except Exception as e:
            logger.error(f"[Webhook] Atomic subscription start failed for user {uid}: {e}")
            return {"status": "error", "error": "subscription_start_failed", "user_id": uid}

        # Log activity (non-critical)
        if self.activity_log_repo:
            await self.activity_log_repo.log_activity(
                user_id=uid,
                action="subscription_started",
                metadata={"plan": plan, "payment": amount_total, "session_id": session_id},
            )

        # Track analytics (non-critical)
        try:
            track_payment(uid, AnalyticsEvents.CHECKOUT_COMPLETED, amount_total, currency, plan=plan)
        except Exception as e:
            logger.warning(f"Failed to track analytics: {e}")

        # ✅ Phase 4 - Task 9: Log webhook operation to audit trail
        try:
            from infrastructure.logging.activity_logger import log_webhook_operation
            await log_webhook_operation(
                operation_type="webhook_subscription_create",
                source="stripe",
                target_user_id=uid,
                details=f"Subscription created: {plan} plan for ${amount_total/100:.2f}/month",
                metadata={
                    "session_id": session_id,
                    "stripe_customer_id": stripe_customer_id,
                    "plan": plan,
                    "amount_total": amount_total,
                    "currency": currency,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to log webhook operation: {e}")

        return {"status": "ok", "action": "subscription_started", "user_id": uid, "plan": plan}

    async def _handle_invoice_payment(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle invoice.payment_succeeded event (subscription renewal).

        v2.4.0: W-HIGH-2/3 fix - Proper transaction handling:
        1. Validate customer and user first
        2. Record payment before refreshing credits
        3. Handle subscription status properly

        Args:
            event: Stripe invoice.payment_succeeded event

        Returns:
            Dict with status and action details
        """
        invoice = event["data"]["object"]
        invoice_id = invoice.get("id", "unknown")
        customer_id = invoice.get("customer")
        amount_paid = invoice.get("amount_paid", 0)
        currency = invoice.get("currency", "usd").upper()
        billing_reason = invoice.get("billing_reason", "")

        # Validate customer_id
        if not customer_id:
            logger.error(f"[Webhook] invoice.payment_succeeded missing customer_id: invoice={invoice_id}")
            return {"status": "error", "error": "missing_customer_id", "invoice_id": invoice_id}

        # Look up user by stripe_customer_id
        user_res = self.db_client.table("profiles").select("id, tier, subscription_status")\
            .eq("stripe_customer_id", customer_id).execute()

        if not user_res.data:
            logger.warning(f"[Webhook] No user found for customer {customer_id}: invoice={invoice_id}")
            return {"status": "error", "error": "user_not_found", "customer_id": customer_id}

        user = user_res.data[0]
        uid = user["id"]
        tier = user.get("tier", "t1")
        current_status = user.get("subscription_status", "inactive")

        # Handle subscription renewal (monthly refresh)
        if tier in ["t2", "t3"] and billing_reason == "subscription_cycle":
            return await self._process_subscription_renewal(
                uid, tier, current_status, amount_paid, currency, invoice_id
            )

        # Handle subscription_create billing reason (first subscription confirmation)
        if billing_reason == "subscription_create" and tier in ["t2", "t3"]:
            if current_status != "active":
                try:
                    self.db_client.table("profiles").update({
                        "subscription_status": "active"
                    }).eq("id", uid).execute()
                    logger.info(f"[Webhook] Confirmed subscription active for user {uid}")
                except Exception as e:
                    logger.warning(f"[Webhook] Failed to confirm subscription status for user {uid}: {e}")

        return {"status": "ok"}

    async def _process_subscription_renewal(
        self,
        uid: str,
        tier: str,
        current_status: str,
        amount_paid: int,
        currency: str,
        invoice_id: str
    ) -> Dict[str, Any]:
        """
        Process subscription renewal.

        v2.4.0: W-HIGH-2 fix - Payment record FIRST (audit trail)

        Args:
            uid: User ID
            tier: Current tier (t2, t3)
            current_status: Current subscription status
            amount_paid: Payment amount in cents
            currency: Payment currency
            invoice_id: Stripe invoice ID

        Returns:
            Dict with status and action details
        """
        # WS3: Get monthly credits from TierService
        if self.tier_service:
            monthly_credits = await self.tier_service.get_monthly_credits(tier)
        else:
            from domains.identity.constants import TIER_MONTHLY_CREDITS
            monthly_credits = TIER_MONTHLY_CREDITS.get(tier, 0)

        # WS3: Atomic renewal via Repository → RPC (payment + status + credits in one transaction)
        try:
            rpc_result = await self.subscription_repo.renew_subscription(
                user_id=uid,
                tier=tier,
                amount_usd=amount_paid,
                currency=currency,
                invoice_id=invoice_id,
                monthly_credits=monthly_credits,
            )

            if rpc_result.get("already_processed"):
                logger.info(f"[Webhook] Subscription renewal already processed for user {uid} (idempotent)")

        except Exception as e:
            logger.error(f"[Webhook] Atomic subscription renewal failed for user {uid}: {e}")
            return {
                "status": "error",
                "error": "subscription_renewal_failed",
                "invoice_id": invoice_id,
                "user_id": uid
            }

        # Step 4: Log activity (non-critical)
        if self.activity_log_repo:
            await self.activity_log_repo.log_activity(
                user_id=uid,
                action="monthly_credits_refreshed",
                metadata={"tier": tier, "payment": amount_paid, "invoice_id": invoice_id},
            )

        # ✅ Phase 4 - Task 9: Log webhook operation to audit trail
        try:
            from infrastructure.logging.activity_logger import log_webhook_operation
            await log_webhook_operation(
                operation_type="webhook_invoice_paid",
                source="stripe",
                target_user_id=uid,
                details=f"Subscription renewed: {tier} plan for ${amount_paid/100:.2f}",
                metadata={
                    "invoice_id": invoice_id,
                    "tier": tier,
                    "amount_paid": amount_paid,
                    "currency": currency,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to log webhook operation: {e}")

        return {"status": "ok", "action": "credits_refreshed", "user_id": uid}

    async def _handle_subscription_change(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle customer.subscription.deleted/updated events.

        v2.4.0: W-MEDIUM-* fix - Improved error handling and logging:
        1. Better status handling for edge cases
        2. Structured logging with context
        3. Graceful degradation on failures

        Args:
            event: Stripe subscription change event

        Returns:
            Dict with status and action details
        """
        subscription = event["data"]["object"]
        subscription_id = subscription.get("id", "unknown")
        customer_id = subscription.get("customer")
        status = subscription.get("status")
        event_type = event.get("type", "unknown")

        # Validate customer_id
        if not customer_id:
            logger.warning(f"[Webhook] subscription change missing customer_id: sub={subscription_id}, event={event_type}")
            return {"status": "error", "error": "missing_customer_id", "subscription_id": subscription_id}

        # Log all subscription changes for audit
        logger.info(f"[Webhook] Processing subscription change: sub={subscription_id}, status={status}, event={event_type}")

        # Look up user
        user_res = self.db_client.table("profiles").select("id, tier")\
            .eq("stripe_customer_id", customer_id).execute()

        if not user_res.data:
            logger.warning(f"[Webhook] No user found for customer {customer_id}: sub={subscription_id}")
            return {"status": "error", "error": "user_not_found", "customer_id": customer_id}

        uid = user_res.data[0]["id"]
        current_tier = user_res.data[0].get("tier", "t1")

        # Handle termination statuses
        termination_statuses = ["canceled", "unpaid", "past_due", "incomplete_expired"]
        if status in termination_statuses:
            return await self._process_subscription_termination(uid, current_tier, status, subscription_id)

        # Handle active status (reactivation or plan change)
        elif status == "active":
            return await self._process_subscription_reactivation(
                uid, current_tier, customer_id, subscription, subscription_id
            )

        # Handle incomplete/trialing statuses
        elif status in ["incomplete", "trialing"]:
            logger.info(f"[Webhook] Subscription in {status} state for user {uid}, no action needed")
            return {"status": "ok", "action": "no_action", "reason": f"subscription_{status}"}

        # Unknown status
        logger.warning(f"[Webhook] Unhandled subscription status '{status}' for user {uid}")
        return {"status": "ok", "action": "no_action", "reason": f"unhandled_status_{status}"}

    async def _process_subscription_termination(
        self,
        uid: str,
        current_tier: str,
        status: str,
        subscription_id: str
    ) -> Dict[str, Any]:
        """
        Process subscription termination (cancel, unpaid, etc).

        Args:
            uid: User ID
            current_tier: Current tier before downgrade
            status: Termination status
            subscription_id: Stripe subscription ID

        Returns:
            Dict with status and action details
        """
        # Downgrade to free
        try:
            await self.user_repo.update_subscription_tier(uid, "t1", subscription_status="inactive")
            logger.info(f"[Webhook] Downgraded user {uid} to free tier (was {current_tier}), reason: {status}")
        except Exception as e:
            logger.error(f"[Webhook] Failed to downgrade user {uid}: {e}")
            return {"status": "error", "error": "tier_update_failed", "user_id": uid}

        # Log activity (non-critical)
        if self.activity_log_repo:
            await self.activity_log_repo.log_activity(
                user_id=uid,
                action="subscription_ended",
                metadata={
                    "reason": status,
                    "previous_tier": current_tier,
                    "subscription_id": subscription_id
                },
            )

        # ✅ Phase 4 - Task 9: Log webhook operation to audit trail
        try:
            from infrastructure.logging.activity_logger import log_webhook_operation
            await log_webhook_operation(
                operation_type="webhook_subscription_cancel",
                source="stripe",
                target_user_id=uid,
                details=f"Subscription cancelled: {current_tier} → t1 (reason: {status})",
                metadata={
                    "subscription_id": subscription_id,
                    "previous_tier": current_tier,
                    "cancellation_reason": status,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to log webhook operation: {e}")

        return {"status": "ok", "action": "subscription_ended", "user_id": uid, "previous_tier": current_tier}

    async def _process_subscription_reactivation(
        self,
        uid: str,
        current_tier: str,
        customer_id: str,
        subscription: Dict[str, Any],
        subscription_id: str
    ) -> Dict[str, Any]:
        """
        Process subscription reactivation or plan change.

        Args:
            uid: User ID
            current_tier: Current tier
            customer_id: Stripe customer ID
            subscription: Full subscription object
            subscription_id: Stripe subscription ID

        Returns:
            Dict with status and action details
        """
        # Get price_id and map to tier
        price_id = subscription.get("items", {}).get("data", [{}])[0].get("price", {}).get("id", "")
        new_tier = get_tier_from_price_id(price_id)

        # Handle unknown price_id
        if new_tier == "t1":
            logger.warning(f"[Webhook] Unknown price_id '{price_id}' for user {uid}, keeping current tier {current_tier}")
            # Don't downgrade to free for unknown price - could be a new plan not yet configured
            new_tier = current_tier if current_tier in ["t2", "t3"] else "t1"

        # Update tier
        try:
            await self.user_repo.update_subscription_tier(
                uid, new_tier,
                stripe_customer_id=customer_id,
                subscription_status="active"
            )
            logger.info(f"[Webhook] Updated user {uid} subscription: {current_tier} -> {new_tier}")
        except Exception as e:
            logger.error(f"[Webhook] Failed to update subscription for user {uid}: {e}")
            return {"status": "error", "error": "tier_update_failed", "user_id": uid}

        # Log activity if tier changed
        if new_tier != current_tier:
            if self.activity_log_repo:
                await self.activity_log_repo.log_activity(
                    user_id=uid,
                    action="subscription_changed",
                    metadata={
                        "previous_tier": current_tier,
                        "new_tier": new_tier,
                        "subscription_id": subscription_id
                    },
                )

            # ✅ Phase 4 - Task 9: Log webhook operation to audit trail
            try:
                from infrastructure.logging.activity_logger import log_webhook_operation
                await log_webhook_operation(
                    operation_type="webhook_subscription_update",
                    source="stripe",
                    target_user_id=uid,
                    details=f"Subscription updated: {current_tier} → {new_tier}",
                    metadata={
                        "subscription_id": subscription_id,
                        "previous_tier": current_tier,
                        "new_tier": new_tier,
                        "price_id": price_id,
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to log webhook operation: {e}")

        return {"status": "ok", "action": "subscription_reactivated", "user_id": uid, "tier": new_tier}

    async def _handle_charge_refunded(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle charge.refunded webhook event.

        P0-010 fix: Process refunds via webhook for transaction safety.
        This ensures refund is only recorded in database after Stripe confirms it.

        Event structure:
        {
            "id": "evt_xxx",
            "type": "charge.refunded",
            "data": {
                "object": {
                    "id": "ch_xxx",
                    "payment_intent": "pi_xxx",
                    "amount_refunded": 2000,  # cents
                    "currency": "usd",
                    "refunds": {
                        "data": [{
                            "id": "re_xxx",
                            "amount": 2000,
                            "reason": "requested_by_customer",
                            "status": "succeeded",
                            "created": 1234567890
                        }]
                    },
                    "metadata": {
                        "user_id": "user_xxx",
                        "admin_id": "user_admin_xxx",  # Who initiated refund
                        "refund_reason": "Customer request"
                    }
                }
            }
        }

        Args:
            event: Stripe charge.refunded webhook event

        Returns:
            Dict with status and processing details
        """
        charge = event["data"]["object"]
        charge_id = charge.get("id", "unknown")
        payment_intent_id = charge.get("payment_intent", "unknown")

        # Extract refund data
        refunds = charge.get("refunds", {}).get("data", [])
        if not refunds:
            logger.error(f"[Webhook] charge.refunded event has no refunds data: charge={charge_id}")
            return {"status": "error", "error": "no_refunds_data"}

        # Process the latest refund (Stripe sends charge.refunded for each refund)
        refund = refunds[0]
        refund_id = refund.get("id", "unknown")
        amount_refunded = refund.get("amount", 0)  # cents
        currency = charge.get("currency", "usd")
        refund_reason = refund.get("reason", "unknown")
        refund_status = refund.get("status", "unknown")

        # Get metadata
        metadata = charge.get("metadata", {})
        user_id = metadata.get("user_id")
        admin_id = metadata.get("admin_id")
        custom_reason = metadata.get("refund_reason", refund_reason)

        logger.info(
            f"[Webhook] Processing charge.refunded: "
            f"refund_id={refund_id}, charge={charge_id}, pi={payment_intent_id}, "
            f"amount=${amount_refunded/100:.2f} {currency}, user={user_id}"
        )

        # Validate refund status
        if refund_status != "succeeded":
            logger.warning(f"[Webhook] Refund {refund_id} not succeeded (status={refund_status}), skipping database update")
            return {"status": "ok", "action": "refund_not_succeeded", "refund_id": refund_id, "refund_status": refund_status}

        # Validate user_id
        if not user_id:
            logger.error(f"[Webhook] charge.refunded missing user_id in metadata: refund={refund_id}")
            return {"status": "error", "error": "missing_user_id", "refund_id": refund_id}

        # Check if refund already recorded (idempotency)
        try:
            existing = self.payment_repo.get_by_payment_intent_and_type(payment_intent_id, "refund")
            if existing and any(r.get("metadata", {}).get("stripe_refund_id") == refund_id for r in existing):
                logger.info(f"[Webhook] Refund {refund_id} already recorded, skipping")
                return {"status": "ok", "action": "already_recorded", "refund_id": refund_id}
        except Exception as e:
            logger.warning(f"[Webhook] Failed to check existing refund: {e}")

        # Record refund in payment_records table
        try:
            refund_record = await self.payment_repo.create(
                user_id=user_id,
                stripe_payment_intent_id=payment_intent_id,
                amount_usd=amount_refunded / 100,  # Convert cents to dollars
                currency=currency,
                status="refunded",
                payment_type="refund",
                metadata={
                    "stripe_refund_id": refund_id,
                    "stripe_charge_id": charge_id,
                    "refund_reason": custom_reason,
                    "refund_status": refund_status,
                    "admin_id": admin_id,
                    "refunded_at": refund.get("created")
                }
            )

            if not refund_record:
                raise Exception("Payment record creation returned None")

            logger.info(f"[Webhook] Recorded refund {refund_id} in payment_records: record_id={refund_record.get('id')}")

        except Exception as e:
            logger.critical(
                f"🔴 CRITICAL: Stripe refund webhook processing failed!\n"
                f"Refund ID: {refund_id}\n"
                f"Payment Intent: {payment_intent_id}\n"
                f"User ID: {user_id}\n"
                f"Amount: ${amount_refunded/100:.2f} {currency}\n"
                f"Admin ID: {admin_id}\n"
                f"Reason: {custom_reason}\n"
                f"Database Error: {e}\n"
                f"⚠️  MANUAL ACTION REQUIRED: Record this refund in payment_records table!"
            )
            return {"status": "error", "error": "database_failure", "refund_id": refund_id, "details": str(e)}

        # Log admin operation if admin_id exists
        if admin_id:
            try:
                from infrastructure.repositories.admin_repository import AdminRepository
                admin_repo = AdminRepository(self.db_client)
                await admin_repo.admin_log_operation(
                    admin_id=admin_id,
                    operation_type="refund_processed",
                    description=f"Processed Stripe refund ${amount_refunded/100:.2f} for user {user_id}",
                    metadata={
                        "refund_id": refund_id,
                        "payment_intent_id": payment_intent_id,
                        "amount": amount_refunded / 100,
                        "currency": currency,
                        "reason": custom_reason,
                        "user_id": user_id
                    }
                )
            except Exception as e:
                logger.warning(f"[Webhook] Failed to log admin operation: {e}")

        # ✅ Phase 4 - Task 9: Log webhook operation to audit trail
        try:
            from infrastructure.logging.activity_logger import log_webhook_operation
            await log_webhook_operation(
                operation_type="webhook_refund_process",
                source="stripe",
                target_user_id=user_id,
                details=f"Refund processed: ${amount_refunded/100:.2f} {currency.upper()} (reason: {custom_reason})",
                metadata={
                    "refund_id": refund_id,
                    "payment_intent_id": payment_intent_id,
                    "charge_id": charge_id,
                    "amount": amount_refunded / 100,
                    "currency": currency,
                    "refund_reason": custom_reason,
                    "refund_status": refund_status,
                    "admin_id": admin_id,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to log webhook operation: {e}")

        return {
            "status": "ok",
            "action": "refund_processed",
            "refund_id": refund_id,
            "payment_intent_id": payment_intent_id,
            "user_id": user_id,
            "amount": amount_refunded / 100,
            "currency": currency
        }
