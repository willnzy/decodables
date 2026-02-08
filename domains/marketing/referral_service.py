"""Referral Service (SVC-012 Phase 2).

Handles referral code generation, application, and eligibility checking.
Implements BR-010: both parties must be paying for referral rewards.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid

logger = logging.getLogger(__name__)


class ReferralService:
    """Manages referral program operations.

    Responsibilities:
    1. Generate unique referral codes for users
    2. Apply referral codes to new user signups
    3. Check referral eligibility (BR-010: both parties paying)
    4. Track referral relationships and reward status
    """

    def __init__(self, db_client=None, subscription_service=None):
        """Initialize with database and subscription service.

        Args:
            db_client: Database client for referral queries
            subscription_service: SubscriptionService for payment status checks
        """
        self._db = db_client
        self._subscription_service = subscription_service

    async def generate_referral_code(self, user_id: str) -> Dict[str, Any]:
        """Generate a unique referral code for a user.

        Args:
            user_id: The user who is referring

        Returns:
            Dictionary with generated referral code
        """
        referral_code = self._generate_unique_code()
        now = datetime.now(timezone.utc).isoformat()

        logger.info(
            "generate_referral_code",
            extra={
                "event": "marketing.referral_code_generated",
                "user_id": user_id,
                "code": referral_code,
            },
        )

        if self._db:
            await self._db.table("referral_codes").insert({
                "user_id": user_id,
                "code": referral_code,
                "created_at": now,
                "updated_at": now,
            }).execute()

        return {
            "user_id": user_id,
            "referral_code": referral_code,
            "created_at": now,
        }

    async def apply_referral(
        self, referred_user_id: str, referral_code: str
    ) -> Dict[str, Any]:
        """Apply a referral code to a new user signup.

        Implements BR-010: both parties must be paying for rewards.

        Args:
            referred_user_id: The user being referred (signup user)
            referral_code: The referral code from the referrer

        Returns:
            Dictionary with referral application result
        """
        # Find the referrer
        if not self._db:
            return {"applied": False, "reason": "Database unavailable"}

        try:
            result = await self._db.table("referral_codes").select("*").eq(
                "code", referral_code
            ).single().execute()

            if not result.data:
                return {"applied": False, "reason": "Invalid referral code"}

            referrer_user_id = result.data["user_id"]
            now = datetime.now(timezone.utc).isoformat()

            logger.info(
                "apply_referral",
                extra={
                    "event": "marketing.referral_applied",
                    "referrer_user_id": referrer_user_id,
                    "referred_user_id": referred_user_id,
                },
            )

            await self._db.table("referrals").insert({
                "referrer_user_id": referrer_user_id,
                "referred_user_id": referred_user_id,
                "referral_code": referral_code,
                "status": "pending",
                "created_at": now,
                "updated_at": now,
            }).execute()

            return {
                "applied": True,
                "referrer_user_id": referrer_user_id,
                "referred_user_id": referred_user_id,
                "status": "pending",
            }

        except Exception as e:
            logger.warning(
                "apply_referral failed",
                extra={
                    "event": "marketing.referral_apply_error",
                    "error": str(e),
                },
            )
            return {"applied": False, "reason": "Application error"}

    async def check_eligibility(self, user_id: str) -> Dict[str, Any]:
        """Check if a user is eligible for referral rewards.

        Implements BR-010: both parties must be paying for rewards.

        Args:
            user_id: The user to check

        Returns:
            Dictionary with eligibility status and reason
        """
        if not self._subscription_service:
            return {"eligible": False, "reason": "Service unavailable"}

        try:
            # Check if user has active paying subscription
            subscription = await self._subscription_service.get_subscription(
                user_id
            )

            if not subscription:
                return {"eligible": False, "reason": "No active subscription"}

            is_paying = subscription.get("status") in ["active", "trialing"]
            if not is_paying:
                return {"eligible": False, "reason": "User is not on paying tier"}

            logger.info(
                "check_eligibility",
                extra={
                    "event": "marketing.referral_eligibility_checked",
                    "user_id": user_id,
                    "eligible": True,
                },
            )

            return {
                "eligible": True,
                "user_id": user_id,
                "subscription_status": subscription.get("status"),
            }

        except Exception as e:
            logger.warning(
                "check_eligibility failed",
                extra={
                    "event": "marketing.eligibility_check_error",
                    "user_id": user_id,
                    "error": str(e),
                },
            )
            return {"eligible": False, "reason": "Eligibility check error"}

    def _generate_unique_code(self) -> str:
        """Generate a unique 8-character alphanumeric referral code.

        Returns:
            Unique referral code
        """
        # Use UUID4 shortened to 8 characters
        return str(uuid.uuid4()).replace("-", "")[:8].upper()
