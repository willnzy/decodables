"""
Subscription Service - Subscription management business logic

@module domains.subscriptions.subscription_service
@version 3.29 (DDD Exception Compliance)

Changes:
- v3.29: DDD-compliant exceptions
  - Removed all HTTPException (replaced with domain exceptions)
  - API layer now responsible for HTTP status code mapping
- v3.28: Created to extract business logic from API layer

Business Logic:
- Refund processing with safety checks
- Subscription cancellation (immediate or scheduled)
- Subscription downgrade (t3→t2, Any→t1)
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from domains.subscriptions.exceptions import (
    UserNotFoundException,
    UserCodeMissingException,
    UserCodeMismatchException,
    UserEmailMismatchException,
    NoStripeCustomerException,
    PaymentNotFoundException,
    PaymentOwnershipException,
    PaymentStatusException,
    AlreadyRefundedException,
    InvalidRefundAmountException,
    RefundFailedException,
    SubscriptionNotFoundException,
    SubscriptionOwnershipException,
    SubscriptionStatusException,
    AlreadyCancelScheduledException,
    SubscriptionCancelFailedException,
    SubscriptionModifyFailedException,
    NoActiveSubscriptionException,
    InvalidTierException,
    InvalidDowngradePathException,
    PriceIdNotConfiguredException,
)

from domains.billing.payment_service import (
    get_customer_subscriptions,
    cancel_subscription,
    create_refund,
    get_payment_intent_details,
    get_subscription_details,
    get_tier_from_price_id,
    modify_subscription,
)
from domains.identity.constants import (
    TIER_T1,
    TIER_T2,
    TIER_T3,
    TIER_LEVELS,
    normalize_tier,
)
from infrastructure.repositories import (
    SupabaseUserRepository,
    SupabasePaymentRepository,
    SupabaseAdminUsersRepository,
)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domains.identity.tier_service import TierService

logger = logging.getLogger(__name__)


# ==========================================
# Monthly credits fallback (use TierService for actual values)
# ==========================================
TIER_MONTHLY_CREDITS_FALLBACK = {
    TIER_T1: 0,
    TIER_T2: 100,  # Aligned with database: tier.t2.monthly_credits
    TIER_T3: 200,  # Aligned with database: tier.t3.monthly_credits
}


class SubscriptionService:
    """
    Subscription management service.

    v3.28: Created to extract business logic from API layer (SUB-MEDIUM-1/2/3).
    v3.32: Use TierService for monthly credits configuration.
    """

    def __init__(
        self,
        users_repo: SupabaseUserRepository,
        payment_repo: SupabasePaymentRepository,
        admin_repo: SupabaseAdminUsersRepository,
        tier_service: "TierService" = None,
    ):
        self.users_repo = users_repo
        self.payment_repo = payment_repo
        self.admin_repo = admin_repo
        self._tier_service = tier_service

    async def _get_monthly_credits(self, tier: str) -> int:
        """Get monthly credits for tier from TierService or fallback."""
        if self._tier_service:
            try:
                return await self._tier_service.get_monthly_credits(tier)
            except Exception as e:
                logger.warning(f"Failed to get monthly credits from TierService: {e}")
        return TIER_MONTHLY_CREDITS_FALLBACK.get(tier, 0)

    # ==========================================
    # Validation Helpers (SUB-MEDIUM-8: Extract common logic)
    # ==========================================

    async def _verify_user_identity(
        self,
        user_id: str,
        user_code: str,
        user_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify user identity using user_code (and optionally email).

        Returns user profile if verification successful.

        Raises:
            UserNotFoundException: If user not found
            UserCodeMissingException: If user has no user code
            UserCodeMismatchException: If user code does not match
            UserEmailMismatchException: If email does not match
        """
        user = await self.users_repo.get_profile(user_id)
        if not user:
            raise UserNotFoundException()

        stored_user_code = user.get("user_code")
        if not stored_user_code:
            raise UserCodeMissingException()
        if stored_user_code != user_code:
            raise UserCodeMismatchException()

        if user_email is not None:
            if user.get("email") != user_email:
                raise UserEmailMismatchException()

        return user

    # ==========================================
    # Refund Operations (SUB-MEDIUM-1)
    # ==========================================

    async def process_refund(
        self,
        user_id: str,
        user_code: str,
        payment_intent_id: str,
        amount_cents: Optional[int],
        reason: str,
        admin_id: str
    ) -> Dict[str, Any]:
        """
        Process a refund with safety checks.

        Args:
            user_id: User ID
            user_code: User code for verification
            payment_intent_id: Stripe Payment Intent ID
            amount_cents: Refund amount in cents (None = full refund)
            reason: Admin reason for refund
            admin_id: Admin performing operation

        Returns:
            Dict with status, refund_id, amount, currency

        Raises:
            UserNotFoundException: If user not found
            NoStripeCustomerException: If user has no Stripe customer ID
            PaymentNotFoundException: If payment not found
            PaymentOwnershipException: If payment does not belong to user
            PaymentStatusException: If payment status does not allow refund
            AlreadyRefundedException: If payment already fully refunded
            InvalidRefundAmountException: If refund amount is invalid
            RefundFailedException: If refund operation fails
        """
        # Verify user identity
        user = await self._verify_user_identity(user_id, user_code)

        customer_id = user.get("stripe_customer_id")
        if not customer_id:
            raise NoStripeCustomerException()

        # Fetch PaymentIntent details
        pi = get_payment_intent_details(payment_intent_id)
        if not pi:
            raise PaymentNotFoundException()

        if pi.customer != customer_id:
            raise PaymentOwnershipException()

        if pi.status != 'succeeded':
            raise PaymentStatusException(status=pi.status)

        refundable_amount = pi.amount_received if hasattr(pi, 'amount_received') else pi.amount

        if refundable_amount <= 0:
            raise AlreadyRefundedException()

        if amount_cents is not None:
            if amount_cents <= 0:
                raise InvalidRefundAmountException(amount=amount_cents)
            if amount_cents > refundable_amount:
                raise InvalidRefundAmountException(amount=amount_cents, refundable=refundable_amount)

        # Execute refund with metadata for webhook processing (P0-010 fix)
        result = create_refund(
            payment_intent_id,
            amount_cents=amount_cents,
            reason="requested_by_customer",
            metadata={
                "user_id": user_id,
                "admin_id": admin_id,
                "refund_reason": reason
            }
        )

        if not result["success"]:
            logger.error(f"[Admin] Refund failed for PI {payment_intent_id}: {result['error']}")
            raise RefundFailedException()

        refund = result["refund"]
        refund_amount = refund.amount
        currency = refund.currency.upper()

        # P0-010: Database record will be created by charge.refunded webhook handler
        # This ensures transactional safety - DB only updated after Stripe confirms refund
        logger.info(
            f"[Admin] Refund initiated successfully: "
            f"refund_id={refund.id}, amount=${refund_amount/100:.2f} {currency}, "
            f"user_id={user_id}, admin_id={admin_id}"
        )
        logger.info(
            f"[Admin] Refund will be recorded in database via charge.refunded webhook. "
            f"Check webhook events in Stripe Dashboard if record doesn't appear within 1 minute."
        )

        return {
            "status": "refunded",
            "refund_id": refund.id,
            "amount": refund_amount,
            "currency": currency,
            "message": "Refund initiated. Database record will be created when Stripe confirms the refund via webhook."
        }

    # ==========================================
    # Subscription Cancellation (SUB-MEDIUM-2)
    # ==========================================

    async def cancel_user_subscription(
        self,
        user_id: str,
        user_code: str,
        subscription_id: str,
        immediate: bool,
        reason: str,
        admin_id: str
    ) -> Dict[str, Any]:
        """
        Cancel a user's subscription.

        Args:
            user_id: User ID
            user_code: User code for verification
            subscription_id: Stripe Subscription ID
            immediate: True = cancel now, False = cancel at period end
            reason: Admin reason for cancellation
            admin_id: Admin performing operation

        Returns:
            Dict with status, subscription_id, cancel info

        Raises:
            UserNotFoundException: If user not found
            NoStripeCustomerException: If user has no Stripe customer ID
            SubscriptionNotFoundException: If subscription not found
            SubscriptionOwnershipException: If subscription does not belong to user
            SubscriptionStatusException: If subscription status does not allow cancel
            AlreadyCancelScheduledException: If already scheduled for cancel
            SubscriptionCancelFailedException: If cancel operation fails
        """
        # Verify user identity
        user = await self._verify_user_identity(user_id, user_code)

        customer_id = user.get("stripe_customer_id")
        if not customer_id:
            raise NoStripeCustomerException()

        # Get subscription details
        subscription_detail = get_subscription_details(subscription_id)
        if not subscription_detail:
            logger.error(f"[Admin] Subscription retrieve failed for {subscription_id}")
            raise SubscriptionNotFoundException()

        if subscription_detail.customer != customer_id:
            raise SubscriptionOwnershipException()

        if subscription_detail.status not in ['active', 'trialing', 'past_due']:
            raise SubscriptionStatusException(status=subscription_detail.status, operation="cancel")

        if not immediate and subscription_detail.cancel_at_period_end:
            raise AlreadyCancelScheduledException()

        # Cancel subscription via Stripe
        result = cancel_subscription(subscription_id, immediate=immediate)

        if not result["success"]:
            logger.error(f"[Admin] Cancel subscription failed for {subscription_id}: {result['error']}")
            raise SubscriptionCancelFailedException()

        subscription = result["subscription"]

        # Determine plan name
        plan_name = self._extract_plan_name(subscription_detail)

        # Update database
        if immediate:
            await self.users_repo.update_subscription_tier(user_id, TIER_T1, subscription_status="canceled")
            await self.payment_repo.create(
                user_id=user_id,
                amount_usd=0,
                currency="USD",
                payment_type="sub_canceled",
                metadata={
                    "plan_name": plan_name,
                    "subscription_id": subscription_id,
                    "reason": reason,
                    "admin_id": admin_id
                }
            )
        else:
            await self.payment_repo.create(
                user_id=user_id,
                amount_usd=0,
                currency="USD",
                payment_type="sub_cancel_scheduled",
                metadata={
                    "plan_name": plan_name,
                    "subscription_id": subscription_id,
                    "period_end": str(subscription.current_period_end),
                    "reason": reason,
                    "admin_id": admin_id
                }
            )

        # Log admin operation
        await self.admin_repo.admin_log_operation(
            admin_id=admin_id,
            operation_type="subscription_cancel",
            target_user_id=user_id,
            details=f"{plan_name} ({'immediate' if immediate else 'at period end'})",
            reason=reason
        )

        return {
            "status": "canceled" if immediate else "cancel_scheduled",
            "subscription_id": subscription.id,
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "current_period_end": subscription.current_period_end
        }

    # ==========================================
    # Subscription Downgrade (SUB-MEDIUM-3/7)
    # ==========================================

    async def downgrade_user_subscription(
        self,
        user_id: str,
        user_code: str,
        user_email: str,
        target_tier: str,
        immediate: bool,
        reason: str,
        admin_id: str
    ) -> Dict[str, Any]:
        """
        Downgrade a user's subscription.

        Supports:
        - t3 → t2 (modify subscription)
        - t3/t2 → t1 (cancel subscription)

        Args:
            user_id: User ID
            user_code: User code for verification
            user_email: User email for verification
            target_tier: Target tier ('t1' or 't2')
            immediate: True = apply now, False = apply at period end
            reason: Admin reason for downgrade
            admin_id: Admin performing operation

        Returns:
            Dict with status, from_tier, to_tier, subscription_id

        Raises:
            UserNotFoundException: If user not found
            InvalidTierException: If tier is invalid
            InvalidDowngradePathException: If downgrade path is invalid
        """
        # Verify user identity (including email)
        user = await self._verify_user_identity(user_id, user_code, user_email)

        current_tier = user.get("tier", "t1")
        target_tier = target_tier.lower()

        # P0-012 fix: Validate target tier is valid
        if target_tier not in TIER_LEVELS:
            raise InvalidTierException(tier=target_tier, valid_tiers=list(TIER_LEVELS.keys()))

        # P0-012 fix: Validate current tier is valid
        if current_tier not in TIER_LEVELS:
            raise InvalidTierException(tier=current_tier)

        # Validate downgrade direction
        if TIER_LEVELS.get(target_tier, -1) >= TIER_LEVELS.get(current_tier, 0):
            raise InvalidDowngradePathException(from_tier=current_tier, to_tier=target_tier)

        customer_id = user.get("stripe_customer_id")

        # Route to appropriate handler
        if target_tier == "t1":
            return await self._downgrade_to_free(
                user_id, customer_id, current_tier, immediate, reason, admin_id
            )
        elif current_tier == "t3" and target_tier == "t2":
            return await self._downgrade_t3_to_t2(
                user_id, customer_id, current_tier, immediate, reason, admin_id
            )
        else:
            raise InvalidDowngradePathException(from_tier=current_tier, to_tier=target_tier)

    async def _downgrade_to_free(
        self,
        user_id: str,
        customer_id: Optional[str],
        current_tier: str,
        immediate: bool,
        reason: str,
        admin_id: str
    ) -> Dict[str, Any]:
        """Handle downgrade to Free tier."""

        # Case 1: No Stripe customer (already free or never subscribed)
        if not customer_id:
            await self.users_repo.update_subscription_tier(user_id, "t1", subscription_status="inactive")
            monthly_credits = await self._get_monthly_credits("t1")
            await self.users_repo.update_monthly_credits(user_id, monthly_credits)

            await self.payment_repo.create(
                user_id=user_id,
                amount_usd=0,
                currency="USD",
                payment_type="tier_downgrade",
                metadata={
                    "from_tier": current_tier,
                    "to_tier": "t1",
                    "immediate": immediate,
                    "reason": reason,
                    "admin_id": admin_id
                }
            )
            return {"status": "downgraded", "from_tier": current_tier, "to_tier": "t1"}

        # Case 2: Has Stripe customer - check for active subscription
        subscriptions = get_customer_subscriptions(customer_id)
        active_sub = next((sub for sub in subscriptions if sub.status in ['active', 'trialing']), None)

        if not active_sub:
            # No active subscription - just update tier
            await self.users_repo.update_subscription_tier(user_id, "t1", subscription_status="inactive")
            monthly_credits = await self._get_monthly_credits("t1")
            await self.users_repo.update_monthly_credits(user_id, monthly_credits)

            await self.payment_repo.create(
                user_id=user_id,
                amount_usd=0,
                currency="USD",
                payment_type="tier_downgrade",
                metadata={
                    "from_tier": current_tier,
                    "to_tier": "t1",
                    "reason": reason,
                    "admin_id": admin_id
                }
            )
            return {"status": "downgraded", "from_tier": current_tier, "to_tier": "t1"}

        # Case 3: Has active subscription - cancel it
        if immediate:
            result = cancel_subscription(active_sub.id, immediate=True)
            if not result["success"]:
                logger.error(f"[Admin] Failed to cancel subscription {active_sub.id}: {result['error']}")
                raise SubscriptionCancelFailedException()

            await self.users_repo.update_subscription_tier(user_id, "t1", subscription_status="canceled")
            monthly_credits = await self._get_monthly_credits("t1")
            await self.users_repo.update_monthly_credits(user_id, monthly_credits)

            await self.payment_repo.create(
                user_id=user_id,
                amount_usd=0,
                currency="USD",
                payment_type="tier_downgrade",
                metadata={
                    "from_tier": current_tier,
                    "to_tier": "t1",
                    "immediate": True,
                    "subscription_id": active_sub.id,
                    "reason": reason,
                    "admin_id": admin_id
                }
            )
        else:
            result = cancel_subscription(active_sub.id, immediate=False)
            if not result["success"]:
                logger.error(f"[Admin] Failed to schedule cancellation for {active_sub.id}: {result['error']}")
                raise SubscriptionCancelFailedException()

            await self.payment_repo.create(
                user_id=user_id,
                amount_usd=0,
                currency="USD",
                payment_type="tier_downgrade_scheduled",
                metadata={
                    "from_tier": current_tier,
                    "to_tier": "t1",
                    "period_end": str(result['subscription'].current_period_end),
                    "subscription_id": active_sub.id,
                    "reason": reason,
                    "admin_id": admin_id
                }
            )

        return {
            "status": "downgraded" if immediate else "downgrade_scheduled",
            "from_tier": current_tier,
            "to_tier": "t1",
            "subscription_id": active_sub.id
        }

    async def _downgrade_t3_to_t2(
        self,
        user_id: str,
        customer_id: Optional[str],
        current_tier: str,
        immediate: bool,
        reason: str,
        admin_id: str
    ) -> Dict[str, Any]:
        """Handle downgrade from t3 to t2."""
        if not customer_id:
            raise NoStripeCustomerException()

        subscriptions = get_customer_subscriptions(customer_id)
        active_sub = next((sub for sub in subscriptions if sub.status in ['active', 'trialing']), None)

        if not active_sub:
            raise NoActiveSubscriptionException()

        # Stripe Price ID for t2 plan (environment variable)
        t2_price_id = os.environ.get("STRIPE_T2_MONTHLY_PRICE_ID") or os.environ.get("STRIPE_STARTER_MONTHLY_PRICE_ID")
        if not t2_price_id:
            raise PriceIdNotConfiguredException(tier="t2")

        # Modify subscription to t2 plan
        updated_sub = modify_subscription(
            active_sub.id,
            items=[{
                "id": active_sub.items.data[0].id,
                "price": t2_price_id
            }],
            proration_behavior='create_prorations' if immediate else 'none',
            billing_cycle_anchor='unchanged' if not immediate else 'now'
        )

        if not updated_sub:
            logger.error(f"[Admin] Subscription downgrade failed for {active_sub.id}")
            raise SubscriptionModifyFailedException()

        # Update database
        if immediate:
            await self.users_repo.update_subscription_tier(user_id, "t2", subscription_status="active")
            monthly_credits = await self._get_monthly_credits("t2")
            await self.users_repo.update_monthly_credits(user_id, monthly_credits)

            await self.payment_repo.create(
                user_id=user_id,
                amount_usd=0,
                currency="USD",
                payment_type="tier_downgrade",
                metadata={
                    "from_tier": "t3",
                    "to_tier": "t2",
                    "immediate": True,
                    "subscription_id": active_sub.id,
                    "reason": reason,
                    "admin_id": admin_id
                }
            )
        else:
            await self.payment_repo.create(
                user_id=user_id,
                amount_usd=0,
                currency="USD",
                payment_type="tier_downgrade_scheduled",
                metadata={
                    "from_tier": "t3",
                    "to_tier": "t2",
                    "next_billing": str(updated_sub.current_period_end),
                    "subscription_id": active_sub.id,
                    "reason": reason,
                    "admin_id": admin_id
                }
            )

        # Log admin operation
        await self.admin_repo.admin_log_operation(
            admin_id=admin_id,
            operation_type="subscription_downgrade",
            target_user_id=user_id,
            details=f"t3 → t2 ({'immediate' if immediate else 'at period end'})",
            reason=reason
        )

        return {
            "status": "downgraded" if immediate else "downgrade_scheduled",
            "from_tier": "t3",
            "to_tier": "t2",
            "subscription_id": active_sub.id
        }

    # ==========================================
    # Helper Methods
    # ==========================================

    def _extract_plan_name(self, subscription_detail) -> str:
        """Extract plan tier from subscription details.

        Returns tier code (t2/t3) based on Stripe Price ID.
        Uses PRICE_MAP-based lookup via get_tier_from_price_id.
        """
        if not subscription_detail.items.data:
            return "Unknown"

        price_id = subscription_detail.items.data[0].price.id
        tier = get_tier_from_price_id(price_id)
        return tier if tier in ["t2", "t3"] else "Unknown"
