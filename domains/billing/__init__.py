"""
Billing Domain - Credit management and transactions.

This domain handles:
- User credit balances (monthly + permanent)
- Credit deduction with priority rules
- Credit addition and top-ups
- Transaction history

@package domains.billing
@version 1.0.0

Business Rules:
- Deduction Priority: Monthly credits first, then Permanent
- Monthly Credits: Reset on subscription cycle, no rollover
- Permanent Credits: Never expire
- All operations must be atomic (use PostgreSQL RPC)
"""

from .value_objects import Credits, CreditBucket, TransactionType
from .aggregates.user_credits import UserCredits
from .exceptions import (
    InsufficientCreditsException,
    InvalidAmountException,
    CreditOperationFailedException,
)
from .repository import ICreditRepository
from .service import BillingService

__all__ = [
    # Value Objects
    'Credits',
    'CreditBucket',
    'TransactionType',
    # Aggregates
    'UserCredits',
    # Exceptions
    'InsufficientCreditsException',
    'InvalidAmountException',
    'CreditOperationFailedException',
    # Repository
    'ICreditRepository',
    # Service
    'BillingService',
]
