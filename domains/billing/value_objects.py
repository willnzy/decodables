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
    """Credit transaction types."""
    # Deductions
    GENERATION = "generation"       # AI image generation
    OCR = "ocr"                     # Smart scan / OCR
    MARKET_PURCHASE = "market_purchase"  # Marketplace purchase

    # Additions
    SIGNUP_BONUS = "signup_bonus"   # Welcome bonus (50 permanent)
    SUB_GRANT = "sub_grant"         # Monthly subscription grant
    TOPUP_PURCHASE = "topup_purchase"  # Credit top-up purchase
    REFUND = "refund"               # Refund
    ADMIN_GRANT = "admin_grant"     # Admin manual grant
    MONTHLY_RESET = "monthly_reset"  # Monthly credit reset


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
    """Cost configuration for different operations."""
    GENERATION: int = 5   # AI image generation
    OCR: int = 10         # Smart scan / OCR
    TEXT_GEN: int = 1     # AI text generation

    @classmethod
    def get_cost(cls, operation: str) -> int:
        """Get cost for an operation."""
        costs = {
            "generation": cls.GENERATION,
            "ocr": cls.OCR,
            "text_gen": cls.TEXT_GEN,
        }
        return costs.get(operation, 0)
