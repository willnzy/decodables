"""
Credit Repository Extended - Additional methods for services/db migration.

@module infrastructure.repositories.credit_repository_extended
@version 1.0.0

Extends SupabaseCreditRepository with additional methods needed for
backward compatibility with services/db/users.py credit functions.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from core.database import DatabaseClient, retry_on_network_error

logger = logging.getLogger(__name__)


class SupabaseCreditRepositoryExtended:
    """
    Extended credit repository with additional methods for profiles table.

    This repository works directly with the "profiles" and "credit_transactions"
    tables and provides all credit methods needed to replace services/db/users.py.
    """

    def __init__(self, client: DatabaseClient):
        """
        Initialize repository with database client.

        Args:
            client: Supabase database client
        """
        self.client = client

    def log_transaction(
        self,
        user_id: str,
        amount: int,
        bucket: str,
        tx_type: str,
        description: str,
        tz: str = "UTC"
    ):
        """
        Log credit transaction (fire-and-forget).

        Args:
            user_id: User ID
            amount: Amount of credits
            bucket: Bucket (monthly or permanent)
            tx_type: Transaction type
            description: Description
            tz: Timezone
        """
        try:
            self.client.table("credit_transactions").insert({
                "user_id": user_id,
                "amount": amount,
                "bucket": bucket,
                "type": tx_type,
                "description": description,
                "timezone": tz,
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to log credit transaction: {e}")

    @retry_on_network_error()
    async def deduct_credits(
        self,
        user_id: str,
        amount: int,
        tx_type: str,
        description: str,
        tz: str = "UTC"
    ) -> dict:
        """
        Deduct credits using atomic RPC function.

        Business Rule: Deduct from monthly first, then permanent.

        Args:
            user_id: User ID
            amount: Amount to deduct
            tx_type: Transaction type
            description: Description
            tz: Timezone

        Returns:
            Result dict with success status and balances
        """
        try:
            result = self.client.rpc("deduct_credits_atomic", {
                "p_user_id": user_id,
                "p_amount": amount,
                "p_type": tx_type,
                "p_description": description,
                "p_timezone": tz
            }).execute()

            if result.data:
                return {
                    "success": True,
                    "balance_monthly": result.data.get("balance_monthly", 0),
                    "balance_permanent": result.data.get("balance_permanent", 0),
                    "total": result.data.get("total_balance", 0),
                    "deducted_from": result.data.get("deducted_from", "unknown")
                }
            return {"success": False, "error": "RPC returned no data"}
        except Exception as e:
            error_str = str(e)
            if "INSUFFICIENT" in error_str:
                return {"success": False, "error": "INSUFFICIENT_CREDITS"}
            logger.error(f"credit_deduct failed: {e}")
            return {"success": False, "error": error_str}

    @retry_on_network_error()
    async def add_credits_permanent(
        self,
        user_id: str,
        amount: int,
        description: str,
        tx_type: str = "topup_purchase",
        tz: str = "UTC"
    ) -> Optional[dict]:
        """
        Add permanent credits using atomic RPC.

        Args:
            user_id: User ID
            amount: Amount to add
            description: Description
            tx_type: Transaction type
            tz: Timezone

        Returns:
            RPC result or None
        """
        try:
            result = self.client.rpc("add_credits_atomic", {
                "p_user_id": user_id,
                "p_amount": amount,
                "p_bucket": "permanent",
                "p_type": tx_type,
                "p_description": description,
                "p_timezone": tz
            }).execute()
            return result.data if result.data else None
        except Exception as e:
            logger.error(f"add_credits_permanent failed: {e}")
            return None

    @retry_on_network_error()
    async def add_credits_monthly(
        self,
        user_id: str,
        amount: int,
        description: str,
        tx_type: str = "sub_grant",
        tz: str = "UTC"
    ) -> Optional[dict]:
        """
        Add monthly credits using atomic RPC.

        Args:
            user_id: User ID
            amount: Amount to add
            description: Description
            tx_type: Transaction type
            tz: Timezone

        Returns:
            RPC result or None
        """
        try:
            result = self.client.rpc("add_credits_atomic", {
                "p_user_id": user_id,
                "p_amount": amount,
                "p_bucket": "monthly",
                "p_type": tx_type,
                "p_description": description,
                "p_timezone": tz
            }).execute()
            return result.data if result.data else None
        except Exception as e:
            logger.error(f"add_credits_monthly failed: {e}")
            return None

    async def add_credits(
        self,
        user_id: str,
        amount: int,
        description: str,
        tx_type: str = "purchase",
        tz: str = "UTC"
    ) -> Optional[dict]:
        """
        Add credits (defaults to permanent).

        Args:
            user_id: User ID
            amount: Amount to add
            description: Description
            tx_type: Transaction type
            tz: Timezone

        Returns:
            RPC result or None
        """
        return await self.add_credits_permanent(user_id, amount, description, tx_type, tz)

    @retry_on_network_error()
    async def get_credit_history(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get credit transaction history.

        Args:
            user_id: User ID
            page: Page number
            limit: Items per page

        Returns:
            Dict with items and total count
        """
        offset = (page - 1) * limit
        result = self.client.table("credit_transactions").select("*", count="exact").eq(
            "user_id", user_id
        ).order("created_at", desc=True).range(offset, offset + limit - 1).execute()

        return {"items": result.data or [], "total": result.count or 0}

    @retry_on_network_error()
    async def refresh_monthly_credits(self, user_id: str, tier: str) -> Optional[dict]:
        """
        Reset monthly credits based on tier.

        Business Rule:
        - starter: 500 credits/month
        - pro: 1000 credits/month
        - free: 0 credits/month

        Args:
            user_id: User ID
            tier: User tier

        Returns:
            Dict with credits_monthly or None
        """
        tier_credits = {"starter": 500, "pro": 1000}
        amount = tier_credits.get(tier, 0)

        if amount == 0:
            return None

        self.client.table("profiles").update({
            "credits_monthly": amount,
            "credits_reset_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", user_id).execute()

        self.log_transaction(
            user_id, amount, "monthly", "monthly_reset",
            f"{tier} monthly refresh"
        )
        return {"credits_monthly": amount}

    async def check_and_reset_monthly_credits_if_needed(self, user_id: str):
        """
        Check and reset monthly credits if 30 days passed.

        Args:
            user_id: User ID
        """
        # Get profile
        from infrastructure.repositories.user_repository_extended import SupabaseUserRepositoryExtended
        user_repo = SupabaseUserRepositoryExtended(self.client)
        profile = await user_repo.get_profile(user_id)

        if not profile:
            return

        tier = profile.get("tier", "free")
        if tier not in ["starter", "pro"]:
            return

        reset_at = profile.get("credits_reset_at")
        if not reset_at:
            await self.refresh_monthly_credits(user_id, tier)
            return

        try:
            if isinstance(reset_at, str):
                reset_dt = datetime.fromisoformat(reset_at.replace("Z", "+00:00"))
            else:
                reset_dt = reset_at

            days_since = (datetime.now(timezone.utc) - reset_dt).days
            if days_since >= 30:
                await self.refresh_monthly_credits(user_id, tier)
        except Exception as e:
            logger.warning(f"Error checking credit reset: {e}")
