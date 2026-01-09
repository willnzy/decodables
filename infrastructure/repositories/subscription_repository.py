"""
Subscription Repository - Data access layer for subscription-related operations

@module infrastructure.repositories.subscription_repository
@version 3.28

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

    def __init__(self, db_client):
        """
        Initialize with database client.

        Args:
            db_client: Supabase client instance
        """
        self.db = db_client
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
                "tier": user.get("tier", "free"),
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
        amount: float = 0.0,
        currency: str = "USD",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Record subscription change in payment history.

        Args:
            user_id: User ID
            change_type: Payment type (refund, sub_canceled, tier_downgrade, etc.)
            amount: Amount (negative for refunds)
            currency: Currency code
            metadata: Additional metadata

        Returns:
            True if successful
        """
        try:
            await self.payment_repo.create(
                user_id=user_id,
                amount=amount,
                currency=currency,
                payment_type=change_type,
                stripe_payment_id=None,  # Optional, can be in metadata
                metadata=metadata or {}
            )
            return True
        except Exception as e:
            logger.error(f"[SubscriptionRepo] Failed to record change for {user_id}: {e}")
            return False
