"""
Subscription Repository - Data access layer for subscription-related operations

@module infrastructure.repositories.subscription_repository
@version 3.29 (AsyncClient migration)

Changes in v3.29:
- Confirmed AsyncClient compatibility (delegates to other async repositories)
- No direct database operations (uses UserRepository and PaymentRepository)

Note: Subscription data primarily lives in Stripe. This repository provides
convenience methods for subscription-related operations on local data.
"""

import logging
from typing import Optional, Dict, Any, Protocol
from abc import ABC, abstractmethod


logger = logging.getLogger(__name__)


class SubscriptionRepository(Protocol):
    """
    Interface for subscription repository operations.

    v3.28: Created for SUB-MEDIUM-5 (missing repository).
    """

    async def get_user_subscription_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user's subscription-related information from local database.

        Returns:
            Dict with tier, subscription_status, stripe_customer_id, credits
        """
        ...

    async def update_tier_and_credits(
        self,
        user_id: str,
        tier: str,
        subscription_status: str,
        monthly_credits: int
    ) -> bool:
        """
        Update user's tier and monthly credits atomically.

        Returns:
            True if successful
        """
        ...

    async def record_subscription_change(
        self,
        user_id: str,
        change_type: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Record subscription change in payment history.

        Args:
            change_type: 'refund', 'sub_canceled', 'tier_downgrade', etc.
            metadata: Additional information about the change
        """
        ...


class SupabaseSubscriptionRepository:
    """
    Supabase implementation of SubscriptionRepository.

    v3.28: Wraps existing UserRepository and PaymentRepository for subscription operations.
    """

    def __init__(self, db_client, user_repo=None, payment_repo=None):
        """
        Initialize with database client and optional repository dependencies.

        Args:
            db_client: Supabase client instance
            user_repo: UserRepository instance (injected by Container)
            payment_repo: PaymentRepository instance (injected by Container)
        """
        self.db = db_client
        if user_repo and payment_repo:
            self.users_repo = user_repo
            self.payment_repo = payment_repo
        else:
            # Fallback: create repositories directly (for backward compatibility)
            from infrastructure.repositories import (
                SupabaseUserRepository,
                SupabasePaymentRepository
            )
            self.users_repo = SupabaseUserRepository(db_client)
            self.payment_repo = SupabasePaymentRepository(db_client)

    async def get_user_subscription_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user's subscription-related information.

        Returns:
            Dict with subscription fields or None if user not found
        """
        try:
            user = await self.users_repo.get_profile(user_id)
            if not user:
                return None

            return {
                "tier": user.get("tier", "t1"),
                "subscription_status": user.get("subscription_status"),
                "stripe_customer_id": user.get("stripe_customer_id"),
                "credits_monthly": user.get("credits_monthly", 0),
                "credits_permanent": user.get("credits_permanent", 0),
                "user_code": user.get("user_code"),
                "email": user.get("email"),
            }
        except Exception as e:
            logger.error(f"[SubscriptionRepo] Failed to get subscription info for {user_id}: {e}")
            return None

    async def update_tier_and_credits(
        self,
        user_id: str,
        tier: str,
        subscription_status: str,
        monthly_credits: int
    ) -> bool:
        """
        Update user's tier and monthly credits.

        Returns:
            True if successful
        """
        try:
            # Update tier and subscription status
            await self.users_repo.update_subscription_tier(
                user_id,
                tier,
                subscription_status=subscription_status
            )

            # Update monthly credits
            await self.users_repo.update_monthly_credits(user_id, monthly_credits)

            return True
        except Exception as e:
            logger.error(f"[SubscriptionRepo] Failed to update tier for {user_id}: {e}")
            return False

    async def record_subscription_change(
        self,
        user_id: str,
        change_type: str,
        amount_usd: float = 0.0,
        currency: str = "USD",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Record subscription change in payment history.

        Args:
            user_id: User ID
            change_type: Payment type (refund, sub_canceled, tier_downgrade, etc.)
            amount_usd: Amount in USD
            currency: Currency code
            metadata: Additional metadata

        Returns:
            True if successful
        """
        try:
            await self.payment_repo.create(
                user_id=user_id,
                amount_usd=amount_usd,
                currency=currency,
                payment_type=change_type,
                stripe_payment_intent_id=None,
                metadata=metadata or {}
            )
            return True
        except Exception as e:
            logger.error(f"[SubscriptionRepo] Failed to record change for {user_id}: {e}")
            return False

    async def start_subscription(
        self,
        user_id: str,
        plan: str,
        stripe_customer_id: str,
        credits_amount: int,
        payment_amount: int,
        currency: str,
        session_id: str,
    ) -> Dict[str, Any]:
        """
        Atomically process first subscription via RPC.

        Executes in single transaction: tier update + payment record + credit grant.

        Args:
            user_id: User ID
            plan: Tier code ('t2', 't3')
            stripe_customer_id: Stripe customer ID
            credits_amount: Monthly credits to grant (from TierService)
            payment_amount: Amount in cents
            currency: Currency code
            session_id: Stripe checkout session ID (idempotency key)

        Returns:
            RPC result dict with 'success', 'tier', 'credits_monthly', etc.

        Raises:
            Exception on RPC failure
        """
        result = await self.db.rpc("process_subscription_start", {
            "p_user_id": user_id,
            "p_plan": plan,
            "p_stripe_customer_id": stripe_customer_id,
            "p_credits_amount": credits_amount,
            "p_payment_amount": payment_amount,
            "p_currency": currency,
            "p_session_id": session_id,
        }).execute()

        if not result.data:
            raise Exception("RPC process_subscription_start returned no data")

        data = result.data if isinstance(result.data, dict) else result.data[0] if result.data else {}
        if not data.get("success"):
            raise Exception(f"RPC failed: {data.get('error', 'Unknown error')}")

        return data

    async def renew_subscription(
        self,
        user_id: str,
        tier: str,
        amount_usd: int,
        currency: str,
        invoice_id: str,
        monthly_credits: int,
    ) -> Dict[str, Any]:
        """
        Atomically process subscription renewal via RPC.

        Executes in single transaction: payment record + status update + credit reset.

        Args:
            user_id: User ID
            tier: Current tier code ('t2', 't3')
            amount_usd: Amount in cents
            currency: Currency code
            invoice_id: Stripe invoice ID
            monthly_credits: Monthly credits to reset to (from TierService)

        Returns:
            RPC result dict with 'success', 'credits_monthly', etc.

        Raises:
            Exception on RPC failure
        """
        idempotency_key = f"renewal_{invoice_id}"

        result = await self.db.rpc("process_subscription_renewal", {
            "p_user_id": user_id,
            "p_tier": tier,
            "p_amount_usd": amount_usd,
            "p_currency": currency,
            "p_invoice_id": invoice_id,
            "p_monthly_credits": monthly_credits,
            "p_idempotency_key": idempotency_key,
        }).execute()

        if not result.data:
            raise Exception("RPC process_subscription_renewal returned no data")

        data = result.data if isinstance(result.data, dict) else result.data[0] if result.data else {}
        if not data.get("success"):
            raise Exception(f"RPC failed: {data.get('error', 'Unknown error')}")

        return data
