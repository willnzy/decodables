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
    """
    user_id: str
    balance: Credits
    tier: str = "free"
    pending_transactions: List[CreditTransaction] = field(default_factory=list)

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
            InvalidAmountException: If amount <= 0
            InsufficientCreditsException: If not enough credits
        """
        if amount <= 0:
            raise InvalidAmountException(amount, "Deduction amount must be positive")

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
            InvalidAmountException: If amount <= 0
        """
        if amount <= 0:
            raise InvalidAmountException(amount, "Addition amount must be positive")

        # Calculate new balance
        new_balance = self.balance.add(amount, bucket)
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

    def reset_monthly(self, new_amount: int, tx_type: TransactionType = TransactionType.MONTHLY_RESET):
        """
        Reset monthly credits to new amount.

        Used for subscription renewal.

        Args:
            new_amount: New monthly credit amount
            tx_type: Transaction type
        """
        old_monthly = self.balance.monthly
        new_balance = self.balance.reset_monthly(new_amount)
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
