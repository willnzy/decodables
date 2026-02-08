"""
Billing Value Objects - Immutable value types for billing domain.

@module domains.billing.value_objects
@version 1.0.0
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CreditBucket(str, Enum):
    """Credit bucket types."""
    MONTHLY = "monthly"
    PERMANENT = "permanent"


class TransactionType(str, Enum):
    """Credit transaction types — TARGET 19 values (Phase 2 ENUM-002).

    SYNC: Must stay in sync with 01_core_business.sql credit_transactions.transaction_type CHECK.
    Phase 1 DB CHECK allows 29 (lenient = 16 old ∪ 19 new); Phase 2 tightens to 19 only.
    See IMPLEMENTATION-SPEC.md §5 ENUM-002 for full specification.
    """
    # ═══ Additions (+amount) — 10 types ═══
    SUBSCRIPTION_GRANT = "subscription_grant"        # Monthly subscription grant (invoice.paid)
    CREDIT_PURCHASE = "credit_purchase"              # Credit top-up purchase (checkout.session.completed)
    BONUS_SIGNUP_GRANT = "bonus_signup_grant"         # Welcome bonus (permanent, one-time)
    BONUS_REFERRAL_GRANT = "bonus_referral_grant"     # Referral reward (permanent)
    BONUS_CAMPAIGN_GRANT = "bonus_campaign_grant"     # Campaign/promotion reward (permanent)
    COMPENSATION_GRANT = "compensation_grant"         # Support compensation (permanent)
    PROMOTION_GRANT = "promotion_grant"               # Promo code / channel promotion (permanent)
    MARKETPLACE_EARNING = "marketplace_earning"       # Seller revenue from marketplace sale (permanent)
    ADMIN_ADJUSTMENT = "admin_adjustment"             # Admin manual grant/adjustment (+/-)
    MANUAL_CORRECTION = "manual_correction"           # Reconciliation / data fix (+/-)

    # ═══ Deductions (-amount) — 6 types ═══
    CREDIT_CONSUME = "credit_consume"                # Feature usage (AI gen, smart scan, etc.)
    MARKETPLACE_PURCHASE = "marketplace_purchase"    # Buyer purchase from marketplace
    CREDITS_EXPIRED = "credits_expired"              # Credit expiration (unused monthly)
    MONTHLY_CREDITS_CLEARED = "monthly_credits_cleared"  # Monthly credits cleared on cancel/downgrade
    REFUND_REVERSAL = "refund_reversal"              # Refund clawback (charge.refunded)
    CHARGEBACK_REVERSAL = "chargeback_reversal"      # Bank dispute clawback (charge.dispute.created)

    # ═══ Reset/Adjustment (=) — 3 types ═══
    MONTHLY_RESET = "monthly_reset"                  # Monthly credits reset to tier quota
    SUBSCRIPTION_UPGRADE = "subscription_upgrade"    # Upgrade differential (+diff)
    SUBSCRIPTION_DOWNGRADE = "subscription_downgrade"  # Downgrade excess removal (-diff)

    # ═══ Legacy members (Phase 2 transitional, removed after all code migrated) ═══
    # Kept WITHOUT prefix so existing code (TransactionType.AI_GENERATION etc.) still works.
    # New code should use the TARGET names above. DB CHECK (lenient tx_type) allows both.
    PURCHASE = "purchase"                    # → use CREDIT_PURCHASE
    TOPUP_PURCHASE = "topup_purchase"        # → use CREDIT_PURCHASE
    SUB_GRANT = "sub_grant"                  # → use SUBSCRIPTION_GRANT
    SIGNUP_BONUS = "signup_bonus"             # → use BONUS_SIGNUP_GRANT
    REFERRAL_BONUS = "referral_bonus"         # → use BONUS_REFERRAL_GRANT
    CAMPAIGN_REWARD = "campaign_reward"       # → use BONUS_CAMPAIGN_GRANT
    AI_GENERATION = "ai_generation"           # → use CREDIT_CONSUME
    SMART_SCAN = "smart_scan"                 # → use CREDIT_CONSUME
    EXPIRATION = "expiration"                  # → use CREDITS_EXPIRED
    REFUND = "refund"                          # → use REFUND_REVERSAL


@dataclass(frozen=True)
class Credits:
    """
    Immutable value object representing credit amounts.

    Attributes:
        monthly: Monthly credits (reset on subscription cycle)
        permanent: Permanent credits (never expire)
    """
    monthly: int = 0
    permanent: int = 0

    def __post_init__(self):
        # Validate non-negative
        if self.monthly < 0 or self.permanent < 0:
            raise ValueError("Credit amounts cannot be negative")

    @property
    def total(self) -> int:
        """Total credits (monthly + permanent)."""
        return self.monthly + self.permanent

    def has_enough(self, required: int) -> bool:
        """Check if total credits >= required."""
        return self.total >= required

    def deduct(self, amount: int) -> 'Credits':
        """
        Calculate new balances after deduction.

        Business Rule: Deduct from monthly first, then permanent.

        Args:
            amount: Amount to deduct

        Returns:
            New Credits with updated balances

        Raises:
            ValueError: If insufficient credits
        """
        if amount <= 0:
            return self

        if not self.has_enough(amount):
            raise ValueError(f"Insufficient credits: need {amount}, have {self.total}")

        # Deduct from monthly first
        if self.monthly >= amount:
            return Credits(
                monthly=self.monthly - amount,
                permanent=self.permanent
            )

        # Deduct from both buckets
        remaining = amount - self.monthly
        return Credits(
            monthly=0,
            permanent=self.permanent - remaining
        )

    def add(self, amount: int, bucket: CreditBucket) -> 'Credits':
        """
        Calculate new balances after addition.

        Args:
            amount: Amount to add
            bucket: Which bucket to add to

        Returns:
            New Credits with updated balance
        """
        if amount <= 0:
            return self

        if bucket == CreditBucket.MONTHLY:
            return Credits(
                monthly=self.monthly + amount,
                permanent=self.permanent
            )
        else:
            return Credits(
                monthly=self.monthly,
                permanent=self.permanent + amount
            )

    def reset_monthly(self, new_amount: int) -> 'Credits':
        """
        Reset monthly credits to new amount.

        Args:
            new_amount: New monthly credit amount

        Returns:
            New Credits with reset monthly balance
        """
        return Credits(
            monthly=new_amount,
            permanent=self.permanent
        )


@dataclass(frozen=True)
class CreditCost:
    """Cost configuration for credit_consume operations.

    Phase 2: All consumption uses TransactionType.CREDIT_CONSUME;
    the specific feature is recorded in description field.
    """
    AI_GENERATE_ASSET: int = 5    # AI image generation
    AI_GENERATE_PAGE: int = 5     # AI page generation
    SMART_SCAN: int = 10          # Smart scan / OCR
    TEXT_GEN: int = 1             # AI text generation (future)

    @classmethod
    def get_cost(cls, operation: str) -> int:
        """
        Get cost for an operation.

        Args:
            operation: Feature name (e.g., "ai_generate_asset", "smart_scan")

        Returns:
            Cost in credits
        """
        costs = {
            "ai_generate_asset": cls.AI_GENERATE_ASSET,
            "ai_generate_page": cls.AI_GENERATE_PAGE,
            "smart_scan": cls.SMART_SCAN,
            "text_gen": cls.TEXT_GEN,
            # Legacy aliases (Phase 2 transitional)
            "ai_generation": cls.AI_GENERATE_ASSET,
            "image_generation": cls.AI_GENERATE_ASSET,
            "text_generation": cls.TEXT_GEN,
        }
        return costs.get(operation, 0)
