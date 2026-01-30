"""
Credit Repository Implementation - Supabase data access for billing domain.

@module infrastructure.repositories.credit_repository
@version 2.0.0 (AsyncClient migration)

Changes in v2.0:
- Removed lazy loading (client parameter now mandatory)
- All methods use AsyncClient
- Removed get_supabase_client() import (sync client)

Changes in v1.0.1:
- Fixed bucket detection to use RPC 'bucket' field instead of non-existent 'from_monthly'
- Fixed balance fields to use 'balance_monthly'/'balance_permanent' (RPC return fields)

Implements ICreditRepository using Supabase PostgreSQL.
Uses atomic RPC functions for credit operations.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import logging

from domains.billing.repository import ICreditRepository
from domains.billing.aggregates.user_credits import UserCredits, CreditTransaction
from domains.billing.value_objects import Credits, CreditBucket, TransactionType
from domains.billing.exceptions import (
    InsufficientCreditsException,
    CreditOperationFailedException,
)
from core.database import retry_on_network_error

logger = logging.getLogger(__name__)


class SupabaseCreditRepository(ICreditRepository):
    """
    Supabase implementation of credit repository.

    v2.0: AsyncClient required (no lazy loading).

    Uses PostgreSQL RPC functions for atomic credit operations.
    """

    def __init__(self, client):
        """
        Initialize repository with AsyncClient.

        Args:
            client: AsyncClient instance (required)

        Raises:
            ValueError: If client is None
        """
        if client is None:
            raise ValueError("AsyncClient required for SupabaseCreditRepository")
        self._client = client

    @property
    def client(self):
        """Get AsyncClient instance."""
        return self._client

    async def get_by_user_id(self, user_id: str) -> Optional[UserCredits]:
        """Get user credits by user ID."""
        try:
            result = await self.client.table("profiles").select(
                "id, credits_monthly, credits_permanent, tier"
            ).eq("id", user_id).single().execute()

            if not result.data:
                return None

            data = result.data
            return UserCredits.create(
                user_id=data["id"],  # profiles.id is the user_id
                monthly=data.get("credits_monthly", 0),
                permanent=data.get("credits_permanent", 0),
                tier=data.get("tier", "t1"),
            )
        except Exception as e:
            logger.error(f"Failed to get credits for user {user_id}: {e}")
            return None

    async def save(self, user_credits: UserCredits) -> UserCredits:
        """Persist user credits and pending transactions."""
        try:
            # Update user credits in profiles table
            await self.client.table("profiles").update({
                "credits_monthly": user_credits.monthly_credits,
                "credits_permanent": user_credits.permanent_credits,
                "tier": user_credits.tier,
            }).eq("id", user_credits.user_id).execute()

            # v3.26: Batch save pending transactions (N+1 fix)
            if user_credits.pending_transactions:
                await self._save_transactions_batch(
                    user_credits.user_id,
                    user_credits.pending_transactions
                )

            user_credits.clear_pending_transactions()
            return user_credits

        except Exception as e:
            logger.error(f"Failed to save credits for user {user_credits.user_id}: {e}")
            raise CreditOperationFailedException(
                user_id=user_credits.user_id,
                operation="save",
                reason=str(e)
            )

    async def deduct_atomic(
        self,
        user_id: str,
        amount: int,
        tx_type: TransactionType,
        description: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> CreditTransaction:
        """Atomically deduct credits using database RPC."""
        # Check idempotency
        if idempotency_key:
            existing = await self.check_idempotency(idempotency_key)
            if existing:
                return existing

        try:
            # Call atomic deduction RPC
            rpc_params = {
                "p_user_id": user_id,
                "p_amount": amount,
                "p_type": tx_type.value,
                "p_description": description or f"{tx_type.value} operation",
            }
            if idempotency_key:
                rpc_params["p_idempotency_key"] = idempotency_key
            result = await self.client.rpc("deduct_credits_atomic", rpc_params).execute()

            if not result.data:
                raise CreditOperationFailedException(
                    user_id=user_id,
                    operation="deduct",
                    reason="RPC returned no data"
                )

            # B-NEW-6 FIX: Validate RPC return structure
            data = result.data
            if isinstance(data, list):
                if not data:  # Empty list
                    raise CreditOperationFailedException(
                        user_id=user_id,
                        operation="deduct",
                        reason="RPC returned empty list"
                    )
                data = data[0]
            elif not data:  # None or empty dict
                raise CreditOperationFailedException(
                    user_id=user_id,
                    operation="deduct",
                    reason="RPC returned no data"
                )

            # Check for RPC failure (success=False means insufficient credits or validation error)
            if not data.get("success"):
                error_msg = data.get("error_message", "")
                if "Insufficient credits" in error_msg:
                    available = data.get("balance_monthly", 0) + data.get("balance_permanent", 0)
                    raise InsufficientCreditsException(
                        required=amount,
                        available=available
                    )
                raise CreditOperationFailedException(
                    user_id=user_id,
                    operation="deduct",
                    reason=error_msg or "RPC returned failure"
                )

            # Determine bucket used - RPC returns 'bucket' field
            bucket_str = data.get("bucket", "permanent")
            bucket = CreditBucket.MONTHLY if bucket_str == "monthly" else CreditBucket.PERMANENT

            # Create transaction record
            # RPC returns: balance_monthly, balance_permanent (not monthly_after/permanent_after)
            tx = CreditTransaction(
                amount=-amount,
                bucket=bucket,
                tx_type=tx_type,
                description=description,
                balance_after=Credits(
                    monthly=data.get("balance_monthly", 0),
                    permanent=data.get("balance_permanent", 0)
                ),
                idempotency_key=idempotency_key,
            )

            # Save transaction record
            await self._save_transaction(user_id, tx)

            return tx

        except InsufficientCreditsException:
            raise
        except Exception as e:
            logger.error(f"Failed to deduct credits for user {user_id}: {e}")
            raise CreditOperationFailedException(
                user_id=user_id,
                operation="deduct",
                reason=str(e)
            )

    async def add_atomic(
        self,
        user_id: str,
        amount: int,
        bucket: CreditBucket,
        tx_type: TransactionType,
        description: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> CreditTransaction:
        """Atomically add credits using database RPC."""
        # Check idempotency
        if idempotency_key:
            existing = await self.check_idempotency(idempotency_key)
            if existing:
                return existing

        try:
            # Determine which column to update
            column = "credits_monthly" if bucket == CreditBucket.MONTHLY else "credits_permanent"

            # Call atomic addition RPC
            rpc_params = {
                "p_user_id": user_id,
                "p_amount": amount,
                "p_bucket": bucket.value,
                "p_type": tx_type.value,
                "p_description": description or f"{tx_type.value} operation",
            }
            if idempotency_key:
                rpc_params["p_idempotency_key"] = idempotency_key
            result = await self.client.rpc("add_credits_atomic", rpc_params).execute()

            if not result.data:
                raise CreditOperationFailedException(
                    user_id=user_id,
                    operation="add",
                    reason="RPC returned no data"
                )

            # B-NEW-6 FIX: Validate RPC return structure
            data = result.data
            if isinstance(data, list):
                if not data:  # Empty list
                    raise CreditOperationFailedException(
                        user_id=user_id,
                        operation="add",
                        reason="RPC returned empty list"
                    )
                data = data[0]
            elif not data:  # None or empty dict
                raise CreditOperationFailedException(
                    user_id=user_id,
                    operation="add",
                    reason="RPC returned no data"
                )

            # Check for RPC failure
            if not data.get("success"):
                error_msg = data.get("error_message", "")
                raise CreditOperationFailedException(
                    user_id=user_id,
                    operation="add",
                    reason=error_msg or "RPC returned failure"
                )

            # Create transaction record
            # RPC returns: balance_monthly, balance_permanent (not monthly_after/permanent_after)
            tx = CreditTransaction(
                amount=amount,
                bucket=bucket,
                tx_type=tx_type,
                description=description,
                balance_after=Credits(
                    monthly=data.get("balance_monthly", 0),
                    permanent=data.get("balance_permanent", 0)
                ),
                idempotency_key=idempotency_key,
            )

            # Save transaction record
            await self._save_transaction(user_id, tx)

            return tx

        except Exception as e:
            logger.error(f"Failed to add credits for user {user_id}: {e}")
            raise CreditOperationFailedException(
                user_id=user_id,
                operation="add",
                reason=str(e)
            )

    async def get_transaction_history(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        tx_type: Optional[TransactionType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[CreditTransaction]:
        """Get transaction history for a user."""
        try:
            query = self.client.table("credit_transactions").select("*").eq(
                "user_id", user_id
            ).order("created_at", desc=True).range(offset, offset + limit - 1)

            if tx_type:
                query = query.eq("tx_type", tx_type.value)
            if start_date:
                query = query.gte("created_at", start_date.isoformat())
            if end_date:
                query = query.lte("created_at", end_date.isoformat())

            result = await query.execute()

            return [self._map_to_transaction(row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to get transaction history for user {user_id}: {e}")
            return []

    async def get_transaction_count(
        self,
        user_id: str,
        tx_type: Optional[TransactionType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> int:
        """Get total count of transactions for a user (for pagination)."""
        try:
            # Use count query with same filters as get_transaction_history
            query = self.client.table("credit_transactions").select(
                "*", count="exact"
            ).eq("user_id", user_id)

            if tx_type:
                query = query.eq("tx_type", tx_type.value)
            if start_date:
                query = query.gte("created_at", start_date.isoformat())
            if end_date:
                query = query.lte("created_at", end_date.isoformat())

            result = await query.execute()

            # Supabase returns count in result.count when count="exact"
            return result.count if result.count is not None else 0

        except Exception as e:
            # B-NEW-3 FIX: Raise exception instead of returning 0
            logger.error(f"Failed to get transaction count for user {user_id}: {e}")
            raise CreditOperationFailedException(
                user_id=user_id,
                operation="count",
                reason=str(e)
            )

    async def check_idempotency(
        self,
        idempotency_key: str
    ) -> Optional[CreditTransaction]:
        """Check if a transaction with this idempotency key exists."""
        try:
            result = await self.client.table("credit_transactions").select("*").eq(
                "idempotency_key", idempotency_key
            ).single().execute()

            if result.data:
                return self._map_to_transaction(result.data)
            return None

        except Exception:
            return None

    async def reset_monthly_credits(
        self,
        user_id: str,
        new_amount: int
    ) -> UserCredits:
        """Reset monthly credits for a user."""
        try:
            # Update credits
            await self.client.table("profiles").update({
                "credits_monthly": new_amount
            }).eq("id", user_id).execute()

            # Fetch updated data
            result = await self.client.table("profiles").select(
                "id, credits_monthly, credits_permanent, tier"
            ).eq("id", user_id).single().execute()

            if not result.data:
                raise CreditOperationFailedException(
                    user_id=user_id,
                    operation="reset_monthly",
                    reason="User not found"
                )

            data = result.data
            return UserCredits.create(
                user_id=data["id"],
                monthly=data["credits_monthly"],
                permanent=data["credits_permanent"],
                tier=data.get("tier", "t1"),
            )

        except Exception as e:
            logger.error(f"Failed to reset monthly credits for user {user_id}: {e}")
            raise CreditOperationFailedException(
                operation="reset_monthly",
                reason=str(e)
            )

    async def _save_transaction(self, user_id: str, tx: CreditTransaction):
        """Save a transaction record."""
        try:
            await self.client.table("credit_transactions").insert({
                "user_id": user_id,
                "amount": tx.amount,
                "bucket": tx.bucket.value,
                "tx_type": tx.tx_type.value,
                "description": tx.description,
                "balance_monthly_after": tx.balance_after.monthly if tx.balance_after else None,
                "balance_permanent_after": tx.balance_after.permanent if tx.balance_after else None,
                "idempotency_key": tx.idempotency_key,
                "created_at": tx.created_at.isoformat(),
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to save transaction record: {e}")

    async def _save_transactions_batch(
        self,
        user_id: str,
        transactions: List[CreditTransaction]
    ):
        """
        Save multiple transaction records in a single batch (v3.26 - N+1 fix).

        Args:
            user_id: User ID
            transactions: List of transactions to save
        """
        if not transactions:
            return

        try:
            batch_data = [
                {
                    "user_id": user_id,
                    "amount": tx.amount,
                    "bucket": tx.bucket.value,
                    "tx_type": tx.tx_type.value,
                    "description": tx.description,
                    "balance_monthly_after": tx.balance_after.monthly if tx.balance_after else None,
                    "balance_permanent_after": tx.balance_after.permanent if tx.balance_after else None,
                    "idempotency_key": tx.idempotency_key,
                    "created_at": tx.created_at.isoformat(),
                }
                for tx in transactions
            ]

            await self.client.table("credit_transactions").insert(batch_data).execute()
        except Exception as e:
            logger.warning(f"Failed to batch save {len(transactions)} transaction records: {e}")

    def _map_to_transaction(self, row: dict) -> CreditTransaction:
        """Map database row to CreditTransaction."""
        return CreditTransaction(
            amount=row["amount"],
            bucket=CreditBucket(row["bucket"]),
            tx_type=TransactionType(row["tx_type"]),
            description=row.get("description"),
            balance_after=Credits(
                monthly=row.get("balance_monthly_after", 0),
                permanent=row.get("balance_permanent_after", 0)
            ) if row.get("balance_monthly_after") is not None else None,
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
            idempotency_key=row.get("idempotency_key"),
        )

    # Extended Methods

    async def log_transaction(
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
            await self.client.table("credit_transactions").insert({
                "user_id": user_id,
                "amount": amount,
                "bucket": bucket,
                "tx_type": tx_type,
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
            result = await self.client.rpc("deduct_credits_atomic", {
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
            result = await self.client.rpc("add_credits_atomic", {
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
            result = await self.client.rpc("add_credits_atomic", {
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
        result = await self.client.table("credit_transactions").select("*", count="exact").eq(
            "user_id", user_id
        ).order("created_at", desc=True).range(offset, offset + limit - 1).execute()

        return {"items": result.data or [], "total": result.count or 0}

    @retry_on_network_error()
    async def refresh_monthly_credits(self, user_id: str, amount: int) -> Optional[dict]:
        """
        Reset monthly credits to the specified amount.

        WS2: Changed from tier-based lookup to explicit amount parameter.
        The caller (webhook service / scheduler) gets the amount from TierService.

        Args:
            user_id: User ID
            amount: Monthly credits amount to set

        Returns:
            Dict with credits_monthly or None
        """
        if amount == 0:
            return None

        await self.client.table("profiles").update({
            "credits_monthly": amount,
            "credits_reset_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", user_id).execute()

        await self.log_transaction(
            user_id, amount, "monthly", "monthly_reset",
            "monthly credits refresh"
        )
        return {"credits_monthly": amount}

    async def check_and_reset_monthly_credits_if_needed(self, user_id: str):
        """
        Check and reset monthly credits if 30 days passed.

        Args:
            user_id: User ID
        """
        # Get profile
        from infrastructure.repositories.user_repository import SupabaseUserRepository
        user_repo = SupabaseUserRepository(self.client)
        profile = await user_repo.get_profile(user_id)

        if not profile:
            return

        tier = profile.get("tier", "t1")
        if tier not in ["t2", "t3"]:
            return

        # Get monthly credits amount from constants (fallback source)
        from domains.identity.constants import TIER_MONTHLY_CREDITS
        amount = TIER_MONTHLY_CREDITS.get(tier, 0)
        if amount <= 0:
            return

        reset_at = profile.get("credits_reset_at")
        if not reset_at:
            await self.refresh_monthly_credits(user_id, amount)
            return

        try:
            if isinstance(reset_at, str):
                reset_dt = datetime.fromisoformat(reset_at.replace("Z", "+00:00"))
            else:
                reset_dt = reset_at

            days_since = (datetime.now(timezone.utc) - reset_dt).days
            if days_since >= 30:
                await self.refresh_monthly_credits(user_id, amount)
        except Exception as e:
            logger.warning(f"Error checking credit reset: {e}")
