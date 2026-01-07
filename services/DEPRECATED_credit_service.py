"""
⚠️ DEPRECATED - DO NOT USE ⚠️

This file has been DEPRECATED and replaced by the v2 architecture.

Migration Path:
===============

❌ OLD (services/credit_service.py):
```python
from services.credit_service import CreditService

credit_service = CreditService(supabase)
success, message = credit_service.deduct(user_id, amount, "generation")
```

✅ NEW (domains/billing + infrastructure):
```python
from domains.billing.service import BillingService
from domains.billing.value_objects import TransactionType
from infrastructure.repositories.credit_repository import SupabaseCreditRepository

# Initialize
repo = SupabaseCreditRepository()
billing_service = BillingService(repo)

# Deduct credits
transaction = await billing_service.deduct_credits(
    user_id=user_id,
    amount=amount,
    tx_type=TransactionType.GENERATION,
    description="AI image generation"
)
```

Function Mapping:
=================

| Old Method | New Location | Notes |
|------------|--------------|-------|
| `get_balance(user_id)` | `repo.get_by_user_id(user_id).total_credits` | Returns UserCredits aggregate |
| `get_total(user_id)` | `repo.get_by_user_id(user_id).total_credits` | Property on UserCredits |
| `has_enough(user_id, amount)` | `billing_service.check_can_afford(user_id, amount)` | |
| `deduct(...)` | `billing_service.deduct_credits(...)` | Returns CreditTransaction |
| `deduct_with_details(...)` | `billing_service.deduct_credits(...)`  | CreditTransaction has all details |
| `add(...)` | `billing_service.add_credits(...)` | |
| `reset_monthly(...)` | `repo.reset_monthly_credits(...)` | |
| `get_generation_cost()` | `billing_service.get_operation_cost("image_generation")` | |
| `get_ocr_cost()` | `billing_service.get_operation_cost("ocr")` | |

Architecture Benefits:
======================

✅ **Business Rules in Domain**: Monthly-first deduction logic in UserCredits aggregate
✅ **Atomic Operations**: PostgreSQL RPC functions ensure consistency
✅ **Testability**: Domain logic separated from infrastructure
✅ **Type Safety**: Strongly typed value objects (Credits, TransactionType)
✅ **Maintainability**: Clear separation of concerns

Migration Date: 2026-01-07
Replaced by: domains/billing/service.py + infrastructure/repositories/credit_repository.py

For questions, see:
- docs/BACKEND_ARCHITECTURE_GUIDE.md
- docs/SERVICES_MIGRATION_PLAN.md
- docs/CREDIT_SERVICE_MIGRATION_ANALYSIS.md
"""

# Keep the original file below for reference in tests
# It will be completely removed in Phase 7.1.6

import logging
from typing import Optional, Tuple, Literal, Dict, Any
from config import CREDITS_PER_IMAGE, CREDITS_PER_OCR

logger = logging.getLogger(__name__)

# Default timezone for transactions
DEFAULT_TIMEZONE = "UTC"


class CreditService:
    """
    ⚠️ DEPRECATED - Use domains.billing.service.BillingService instead

    Service for managing user credits.

    Credit Types (PRD v3.2):
    - Monthly Credits: Reset monthly, no rollover
    - Permanent Credits: Never expire

    Deduction Priority: Monthly first, then Permanent

    Atomic Operations (v3.22):
    - All credit operations use PostgreSQL RPC for atomicity
    - Row locking prevents concurrent modification issues
    """

    def __init__(self, supabase):
        self.supabase = supabase
        logger.warning(
            "⚠️ CreditService is DEPRECATED. "
            "Use domains.billing.service.BillingService instead. "
            "See services/DEPRECATED_credit_service.py for migration guide."
        )

    def get_balance(self, user_id: str) -> Tuple[int, int]:
        """
        ⚠️ DEPRECATED - Use:
        user_credits = await repo.get_by_user_id(user_id)
        return (user_credits.monthly_credits, user_credits.permanent_credits)
        """
        result = self.supabase.table("profiles").select(
            "credits_monthly, credits_permanent"
        ).eq("id", user_id).single().execute()

        if result.data:
            return (
                result.data.get("credits_monthly", 0),
                result.data.get("credits_permanent", 0)
            )
        return (0, 0)

    def get_total(self, user_id: str) -> int:
        """
        ⚠️ DEPRECATED - Use:
        user_credits = await repo.get_by_user_id(user_id)
        return user_credits.total_credits
        """
        monthly, permanent = self.get_balance(user_id)
        return monthly + permanent

    def has_enough(self, user_id: str, required: int) -> bool:
        """
        ⚠️ DEPRECATED - Use:
        await billing_service.check_can_afford(user_id, required)
        """
        return self.get_total(user_id) >= required

    def deduct(
        self,
        user_id: str,
        amount: int,
        tx_type: str,
        description: Optional[str] = None,
        timezone: str = DEFAULT_TIMEZONE,
        idempotency_key: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        ⚠️ DEPRECATED - Use:
        transaction = await billing_service.deduct_credits(
            user_id=user_id,
            amount=amount,
            tx_type=TransactionType.GENERATION,
            description=description,
            idempotency_key=idempotency_key
        )
        """
        if amount <= 0:
            return (True, "No credits needed")

        try:
            result = self.supabase.rpc("deduct_credits_atomic", {
                "p_user_id": user_id,
                "p_amount": amount,
                "p_tx_type": tx_type,
                "p_description": description,
                "p_timezone": timezone,
                "p_idempotency_key": idempotency_key
            }).execute()

            data = result.data

            if not data:
                logger.error(f"[CreditService] RPC returned no data for user {user_id}")
                return (False, "Database error: no response")

            if data.get("success"):
                if data.get("idempotent"):
                    logger.info(f"[CreditService] Idempotent deduction for {user_id}: {idempotency_key}")
                return (True, f"Deducted {amount} credits")
            else:
                error = data.get("error", "Unknown error")
                error_code = data.get("error_code", "")
                logger.warning(f"[CreditService] Deduction failed for {user_id}: {error} ({error_code})")
                return (False, error)

        except Exception as e:
            logger.error(f"[CreditService] Deduction exception for {user_id}: {e}")
            return (False, str(e))

    def deduct_with_details(
        self,
        user_id: str,
        amount: int,
        tx_type: str,
        description: Optional[str] = None,
        timezone: str = DEFAULT_TIMEZONE,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        ⚠️ DEPRECATED - Use:
        transaction = await billing_service.deduct_credits(...)
        # CreditTransaction object contains all details
        """
        if amount <= 0:
            monthly, permanent = self.get_balance(user_id)
            return {
                "success": True,
                "message": "No credits needed",
                "balance_monthly": monthly,
                "balance_permanent": permanent
            }

        try:
            result = self.supabase.rpc("deduct_credits_atomic", {
                "p_user_id": user_id,
                "p_amount": amount,
                "p_tx_type": tx_type,
                "p_description": description,
                "p_timezone": timezone,
                "p_idempotency_key": idempotency_key
            }).execute()

            data = result.data or {}
            return {
                "success": data.get("success", False),
                "balance_monthly": data.get("balance_monthly", 0),
                "balance_permanent": data.get("balance_permanent", 0),
                "deducted": data.get("deducted", 0),
                "bucket": data.get("bucket", ""),
                "error": data.get("error"),
                "error_code": data.get("error_code"),
                "idempotent": data.get("idempotent", False)
            }
        except Exception as e:
            logger.error(f"[CreditService] Deduction exception for {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": "EXCEPTION"
            }

    def add(
        self,
        user_id: str,
        amount: int,
        bucket: Literal["monthly", "permanent"],
        tx_type: str,
        description: Optional[str] = None,
        timezone: str = DEFAULT_TIMEZONE,
        idempotency_key: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        ⚠️ DEPRECATED - Use:
        transaction = await billing_service.add_credits(
            user_id=user_id,
            amount=amount,
            bucket=CreditBucket.MONTHLY,  # or PERMANENT
            tx_type=TransactionType.PURCHASE,
            description=description,
            idempotency_key=idempotency_key
        )
        """
        if amount <= 0:
            return (False, "Amount must be positive")

        try:
            result = self.supabase.rpc("add_credits_atomic", {
                "p_user_id": user_id,
                "p_amount": amount,
                "p_bucket": bucket,
                "p_tx_type": tx_type,
                "p_description": description,
                "p_timezone": timezone,
                "p_idempotency_key": idempotency_key
            }).execute()

            data = result.data

            if not data:
                logger.error(f"[CreditService] Add RPC returned no data for user {user_id}")
                return (False, "Database error: no response")

            if data.get("success"):
                if data.get("idempotent"):
                    logger.info(f"[CreditService] Idempotent add for {user_id}: {idempotency_key}")
                return (True, f"Added {amount} credits to {bucket}")
            else:
                error = data.get("error", "Unknown error")
                logger.warning(f"[CreditService] Add failed for {user_id}: {error}")
                return (False, error)

        except Exception as e:
            logger.error(f"[CreditService] Add exception for {user_id}: {e}")
            return (False, str(e))

    def reset_monthly(
        self,
        user_id: str,
        amount: int,
        timezone: str = DEFAULT_TIMEZONE
    ) -> Tuple[bool, str]:
        """
        ⚠️ DEPRECATED - Use:
        updated_credits = await repo.reset_monthly_credits(user_id, amount)
        """
        monthly, permanent = self.get_balance(user_id)

        try:
            # Use direct update for reset (this is a replace, not add)
            # Calculate the net change for transaction logging
            net_change = amount - monthly

            # Update monthly to new amount
            self.supabase.table("profiles").update({
                "credits_monthly": amount
            }).eq("id", user_id).execute()

            # Record transaction with timezone snapshot
            self.supabase.table("credit_transactions").insert({
                "user_id": user_id,
                "amount": net_change,
                "bucket": "monthly",
                "balance_monthly_after": amount,
                "balance_permanent_after": permanent,
                "type": "sub_grant",
                "description": "Monthly credits reset",
                "timezone": timezone
            }).execute()

            return (True, f"Monthly credits reset to {amount}")
        except Exception as e:
            logger.error(f"[CreditService] Reset exception for {user_id}: {e}")
            return (False, str(e))

    @staticmethod
    def get_generation_cost() -> int:
        """
        ⚠️ DEPRECATED - Use:
        cost = billing_service.get_operation_cost("image_generation")
        """
        return CREDITS_PER_IMAGE

    @staticmethod
    def get_ocr_cost() -> int:
        """
        ⚠️ DEPRECATED - Use:
        cost = billing_service.get_operation_cost("ocr")
        """
        return CREDITS_PER_OCR
