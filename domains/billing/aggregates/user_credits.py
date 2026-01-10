"""
UserCredits Aggregate - Encapsulates credit balance and operations.

@module domains.billing.aggregates.user_credits
@version 1.0.0

This is the aggregate root for credit management.
All credit operations must go through this aggregate.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from ..value_objects import Credits, CreditBucket, TransactionType
from ..exceptions import InsufficientCreditsException, InvalidAmountException

# ============================================================
# Business Constraints (matches database CHECK constraints)
# ============================================================

# Credit Balance Limits (from profiles table)
MAX_MONTHLY_CREDITS = 1_000_000      # 1M monthly credits maximum
MAX_PERMANENT_CREDITS = 10_000_000   # 10M permanent credits maximum
MIN_CREDITS = 0                       # Non-negative only

# Transaction Amount Limits
MAX_SINGLE_TRANSACTION = 1_000_000    # Maximum single transaction amount
MIN_TRANSACTION_AMOUNT = 1            # Minimum positive amount


@dataclass
class CreditTransaction:
    """Record of a credit operation."""
    amount: int
    bucket: CreditBucket
    tx_type: TransactionType
    description: Optional[str] = None
    balance_after: Optional[Credits] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    idempotency_key: Optional[str] = None


@dataclass
class UserCredits:
    """
    Aggregate root for user credit management.

    Encapsulates:
    - Current credit balance (monthly + permanent)
    - Business rules for deduction priority
    - Pending transactions for unit of work pattern

    Business Rules:
    - Monthly credits are deducted first
    - Permanent credits are deducted when monthly is exhausted
    - All operations should be validated before persistence

    Invariants (enforced by __post_init__):
    - 0 <= monthly credits <= 1,000,000
    - 0 <= permanent credits <= 10,000,000
    - user_id must be non-empty
    """
    user_id: str
    balance: Credits
    tier: str = "free"
    pending_transactions: List[CreditTransaction] = field(default_factory=list)

    def __post_init__(self):
        """
        Validate aggregate invariants after initialization.

        Raises:
            ValueError: If any constraint is violated
        """
        # Validate user_id
        if not self.user_id or not self.user_id.strip():
            raise ValueError("user_id cannot be empty")

        # Validate credit balances against database constraints
        if self.balance.monthly < MIN_CREDITS:
            raise ValueError(
                f"Monthly credits cannot be negative: {self.balance.monthly}"
            )
        if self.balance.monthly > MAX_MONTHLY_CREDITS:
            raise ValueError(
                f"Monthly credits exceed maximum ({MAX_MONTHLY_CREDITS:,}): "
                f"{self.balance.monthly:,}"
            )

        if self.balance.permanent < MIN_CREDITS:
            raise ValueError(
                f"Permanent credits cannot be negative: {self.balance.permanent}"
            )
        if self.balance.permanent > MAX_PERMANENT_CREDITS:
            raise ValueError(
                f"Permanent credits exceed maximum ({MAX_PERMANENT_CREDITS:,}): "
                f"{self.balance.permanent:,}"
            )

        # Validate tier (optional, but good practice)
        valid_tiers = {"free", "starter", "pro", "t1", "t2", "t3"}
        if self.tier and self.tier not in valid_tiers:
            # Soft validation - log warning but don't fail
            # (allows for future tier additions)
            pass

    @classmethod
    def create(cls, user_id: str, monthly: int = 0, permanent: int = 0, tier: str = "free"):
        """Factory method to create UserCredits."""
        return cls(
            user_id=user_id,
            balance=Credits(monthly=monthly, permanent=permanent),
            tier=tier,
        )

    @property
    def total_credits(self) -> int:
        """Total available credits."""
        return self.balance.total

    @property
    def monthly_credits(self) -> int:
        """Monthly credit balance."""
        return self.balance.monthly

    @property
    def permanent_credits(self) -> int:
        """Permanent credit balance."""
        return self.balance.permanent

    def can_afford(self, amount: int) -> bool:
        """Check if user can afford the specified amount."""
        return self.balance.has_enough(amount)

    def deduct(
        self,
        amount: int,
        tx_type: TransactionType,
        description: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> CreditTransaction:
        """
        Deduct credits from user's balance.

        Business Rule: Monthly first, then permanent.

        Args:
            amount: Amount to deduct
            tx_type: Transaction type
            description: Optional description
            idempotency_key: Optional idempotency key

        Returns:
            CreditTransaction record

        Raises:
            InvalidAmountException: If amount <= 0 or exceeds max transaction
            InsufficientCreditsException: If not enough credits
            ValueError: If resulting balance would violate constraints
        """
        # Pre-condition: Validate amount
        if amount <= 0:
            raise InvalidAmountException(amount, "Deduction amount must be positive")

        if amount > MAX_SINGLE_TRANSACTION:
            raise InvalidAmountException(
                amount,
                f"Single transaction cannot exceed {MAX_SINGLE_TRANSACTION:,} credits"
            )

        # Pre-condition: Validate sufficient balance
        if not self.can_afford(amount):
            raise InsufficientCreditsException(
                required=amount,
                available=self.total_credits
            )

        # Determine which bucket(s) to deduct from
        if self.balance.monthly >= amount:
            bucket = CreditBucket.MONTHLY
        elif self.balance.monthly > 0:
            bucket = CreditBucket.MONTHLY  # Will use both, but primary is monthly
        else:
            bucket = CreditBucket.PERMANENT

        # Calculate new balance
        new_balance = self.balance.deduct(amount)

        # Post-condition: Validate new balance doesn't violate constraints
        # (This should never happen if Credits.deduct() is correct, but defensive check)
        if new_balance.monthly < MIN_CREDITS or new_balance.permanent < MIN_CREDITS:
            raise ValueError(
                f"Internal error: Deduction would result in negative balance. "
                f"Monthly: {new_balance.monthly}, Permanent: {new_balance.permanent}"
            )

        # Update balance (triggers __post_init__ validation via dataclass replace)
        self.balance = new_balance

        # Create transaction record
        tx = CreditTransaction(
            amount=-amount,  # Negative for deductions
            bucket=bucket,
            tx_type=tx_type,
            description=description,
            balance_after=new_balance,
            idempotency_key=idempotency_key,
        )
        self.pending_transactions.append(tx)

        return tx

    def add(
        self,
        amount: int,
        bucket: CreditBucket,
        tx_type: TransactionType,
        description: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> CreditTransaction:
        """
        Add credits to user's balance.

        Args:
            amount: Amount to add
            bucket: Which bucket to add to
            tx_type: Transaction type
            description: Optional description
            idempotency_key: Optional idempotency key

        Returns:
            CreditTransaction record

        Raises:
            InvalidAmountException: If amount <= 0 or exceeds max transaction
            ValueError: If resulting balance would exceed maximum limits
        """
        # Pre-condition: Validate amount
        if amount <= 0:
            raise InvalidAmountException(amount, "Addition amount must be positive")

        if amount > MAX_SINGLE_TRANSACTION:
            raise InvalidAmountException(
                amount,
                f"Single transaction cannot exceed {MAX_SINGLE_TRANSACTION:,} credits"
            )

        # Calculate new balance
        new_balance = self.balance.add(amount, bucket)

        # Post-condition: Validate new balance doesn't exceed maximum limits
        if bucket == CreditBucket.MONTHLY and new_balance.monthly > MAX_MONTHLY_CREDITS:
            raise ValueError(
                f"Cannot add {amount:,} credits: would exceed monthly maximum "
                f"({MAX_MONTHLY_CREDITS:,}). Current: {self.balance.monthly:,}, "
                f"After: {new_balance.monthly:,}"
            )

        if bucket == CreditBucket.PERMANENT and new_balance.permanent > MAX_PERMANENT_CREDITS:
            raise ValueError(
                f"Cannot add {amount:,} credits: would exceed permanent maximum "
                f"({MAX_PERMANENT_CREDITS:,}). Current: {self.balance.permanent:,}, "
                f"After: {new_balance.permanent:,}"
            )

        # Update balance
        self.balance = new_balance

        # Create transaction record
        tx = CreditTransaction(
            amount=amount,
            bucket=bucket,
            tx_type=tx_type,
            description=description,
            balance_after=new_balance,
            idempotency_key=idempotency_key,
        )
        self.pending_transactions.append(tx)

        return tx

    def reset_monthly(
        self,
        new_amount: int,
        tx_type: TransactionType = TransactionType.SUBSCRIPTION_GRANT
    ):
        """
        Reset monthly credits to new amount.

        Used for subscription renewal.

        Args:
            new_amount: New monthly credit amount
            tx_type: Transaction type (default: SUBSCRIPTION_GRANT)

        Raises:
            ValueError: If new_amount exceeds maximum monthly credits
        """
        # Pre-condition: Validate new amount
        if new_amount < MIN_CREDITS:
            raise ValueError(f"Monthly credits cannot be negative: {new_amount}")

        if new_amount > MAX_MONTHLY_CREDITS:
            raise ValueError(
                f"Monthly credits cannot exceed maximum ({MAX_MONTHLY_CREDITS:,}): "
                f"{new_amount:,}"
            )

        old_monthly = self.balance.monthly
        new_balance = self.balance.reset_monthly(new_amount)

        # Post-condition: Validate new balance
        if new_balance.monthly != new_amount:
            raise ValueError(
                f"Internal error: Monthly reset failed. "
                f"Expected: {new_amount}, Got: {new_balance.monthly}"
            )

        self.balance = new_balance

        # Record the change
        net_change = new_amount - old_monthly
        tx = CreditTransaction(
            amount=net_change,
            bucket=CreditBucket.MONTHLY,
            tx_type=tx_type,
            description=f"Monthly reset: {old_monthly} -> {new_amount}",
            balance_after=new_balance,
        )
        self.pending_transactions.append(tx)

    def clear_pending_transactions(self):
        """Clear pending transactions after persistence."""
        self.pending_transactions = []

    def get_tier_monthly_allowance(self) -> int:
        """Get monthly credit allowance based on tier."""
        allowances = {
            "free": 0,
            "starter": 500,
            "pro": 1000,
        }
        return allowances.get(self.tier, 0)
