"""
Credit Repository Interface - Abstract data access for billing domain.

@module domains.billing.repository
@version 1.0.0

This defines the repository interface (port) for credit operations.
Concrete implementations live in infrastructure/repositories/.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import datetime

from .aggregates.user_credits import UserCredits, CreditTransaction
from .value_objects import CreditBucket, TransactionType


class ICreditRepository(ABC):
    """
    Repository interface for credit operations.

    Follows the Repository pattern from DDD.
    Infrastructure layer provides the concrete implementation.
    """

    @abstractmethod
    async def get_by_user_id(self, user_id: str) -> Optional[UserCredits]:
        """
        Get user credits by user ID.

        Args:
            user_id: The user's unique identifier

        Returns:
            UserCredits aggregate or None if not found
        """
        pass

    @abstractmethod
    async def save(self, user_credits: UserCredits) -> UserCredits:
        """
        Persist user credits and pending transactions.

        This should:
        1. Update user credit balance
        2. Persist all pending transactions
        3. Clear pending transactions after successful save

        Args:
            user_credits: The UserCredits aggregate to save

        Returns:
            Updated UserCredits aggregate
        """
        pass

    @abstractmethod
    async def deduct_atomic(
        self,
        user_id: str,
        amount: int,
        tx_type: TransactionType,
        description: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> CreditTransaction:
        """
        Atomically deduct credits using database RPC.

        This is the preferred method for production use as it
        guarantees atomicity at the database level.

        Args:
            user_id: User ID
            amount: Amount to deduct
            tx_type: Transaction type
            description: Optional description
            idempotency_key: Optional idempotency key

        Returns:
            CreditTransaction record

        Raises:
            InsufficientCreditsException: If not enough credits
            CreditOperationFailedException: If operation fails
        """
        pass

    @abstractmethod
    async def add_atomic(
        self,
        user_id: str,
        amount: int,
        bucket: CreditBucket,
        tx_type: TransactionType,
        description: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> CreditTransaction:
        """
        Atomically add credits using database RPC.

        Args:
            user_id: User ID
            amount: Amount to add
            bucket: Which bucket to add to
            tx_type: Transaction type
            description: Optional description
            idempotency_key: Optional idempotency key

        Returns:
            CreditTransaction record

        Raises:
            CreditOperationFailedException: If operation fails
        """
        pass

    @abstractmethod
    async def get_transaction_history(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        tx_type: Optional[TransactionType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[CreditTransaction]:
        """
        Get transaction history for a user.

        Args:
            user_id: User ID
            limit: Maximum number of records
            offset: Number of records to skip
            tx_type: Filter by transaction type
            start_date: Filter by start date
            end_date: Filter by end date

        Returns:
            List of CreditTransaction records
        """
        pass

    @abstractmethod
    async def get_transaction_count(
        self,
        user_id: str,
        tx_type: Optional[TransactionType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> int:
        """
        Get total count of transactions for a user (for pagination).

        Args:
            user_id: User ID
            tx_type: Filter by transaction type
            start_date: Filter by start date
            end_date: Filter by end date

        Returns:
            Total count of matching transactions
        """
        pass

    @abstractmethod
    async def check_idempotency(
        self,
        idempotency_key: str
    ) -> Optional[CreditTransaction]:
        """
        Check if a transaction with this idempotency key exists.

        Args:
            idempotency_key: The idempotency key to check

        Returns:
            Existing transaction or None
        """
        pass

    @abstractmethod
    async def reset_monthly_credits(
        self,
        user_id: str,
        new_amount: int
    ) -> UserCredits:
        """
        Reset monthly credits for a user.

        Used during subscription renewal.

        Args:
            user_id: User ID
            new_amount: New monthly credit amount

        Returns:
            Updated UserCredits aggregate
        """
        pass
