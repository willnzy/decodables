"""
Billing Domain Service - Orchestrates credit operations within the domain.

@module domains.billing.service
@version 1.0.0

This service handles domain logic that doesn't naturally belong to aggregates.
It coordinates operations but delegates persistence to the repository.
"""

from typing import Optional, List
from datetime import datetime
import logging

from .aggregates.user_credits import UserCredits, CreditTransaction
from .repository import ICreditRepository
from .value_objects import Credits, CreditBucket, TransactionType
from .exceptions import (
    InsufficientCreditsException,
    InvalidAmountException,
    CreditOperationFailedException,
)

logger = logging.getLogger(__name__)


class BillingService:
    """
    Domain service for billing operations.

    This service:
    - Validates business rules
    - Coordinates credit operations
    - Calculates costs for different operations
    """

    # Emergency fallback costs (only used if database is completely unavailable)
    # ⚠️ WARNING: These are EMERGENCY fallbacks only!
    # Primary source: system_configs table in database
    EMERGENCY_FALLBACK_COSTS = {
        "image_generation": 5,
        "text_generation": 0,  # Currently free
        "smart_scan": 10,
        "ocr": 10,  # Same as smart_scan (no distinction)
    }

    # Monthly allowances by tier (fallback)
    TIER_ALLOWANCES = {
        "t1": 0,
        "t2": 500,
        "t3": 1000,
    }

    # Signup bonus (fallback)
    SIGNUP_BONUS = 50

    def __init__(self, repository: ICreditRepository, config_service: 'ConfigService' = None):
        """
        Initialize billing service with repository and config service.

        Args:
            repository: Credit repository implementation
            config_service: Optional ConfigService instance for dynamic configuration (async)
        """
        self._repository = repository
        self._config_service = config_service

    async def get_user_credits(self, user_id: str) -> Optional[UserCredits]:
        """
        Get user's current credit status.

        Args:
            user_id: User ID

        Returns:
            UserCredits aggregate or None
        """
        return await self._repository.get_by_user_id(user_id)

    async def check_can_afford(self, user_id: str, amount: int) -> bool:
        """
        Check if user can afford an operation.

        Args:
            user_id: User ID
            amount: Required credits

        Returns:
            True if user has enough credits
        """
        user_credits = await self._repository.get_by_user_id(user_id)
        if not user_credits:
            return False
        return user_credits.can_afford(amount)

    async def check_can_afford_operation(
        self,
        user_id: str,
        operation: str
    ) -> bool:
        """
        Check if user can afford a specific operation.

        Args:
            user_id: User ID
            operation: Operation name (e.g., "image_generation")

        Returns:
            True if user has enough credits
        """
        cost = await self.get_operation_cost(operation)
        return await self.check_can_afford(user_id, cost)

    async def get_operation_cost(self, operation: str) -> int:
        """
        Get the cost for a specific operation.

        Priority:
        1. Database system_configs (primary source)
        2. Emergency fallback (if database unavailable)

        Args:
            operation: Operation name

        Returns:
            Credit cost as integer

        Raises:
            ValueError: If operation is unknown
        """
        # Try to get from database config first
        if self._config_service:
            try:
                config_key = f"credits.cost.{operation}"
                config_value = await self._config_service.get_config(config_key, use_cache=True)

                if config_value is not None:
                    # Handle different value formats
                    if isinstance(config_value, dict):
                        return int(config_value.get('amount', config_value.get('value', 0)))
                    return int(config_value)
                else:
                    logger.error(
                        f"[CRITICAL] Credit cost for '{operation}' not found in database!",
                        extra={"operation": operation, "config_key": config_key}
                    )
            except Exception as e:
                logger.error(
                    f"[CRITICAL] Failed to load credit cost from database: {e}",
                    extra={"operation": operation, "error": str(e)}
                )

        # Use emergency fallback
        logger.warning(
            f"Using EMERGENCY fallback cost for '{operation}'. "
            f"Database config should be added to system_configs table!",
            extra={"operation": operation}
        )

        if operation not in self.EMERGENCY_FALLBACK_COSTS:
            raise ValueError(f"Unknown operation: {operation}")

        return self.EMERGENCY_FALLBACK_COSTS[operation]

    async def deduct_for_operation(
        self,
        user_id: str,
        operation: str,
        description: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> CreditTransaction:
        """
        Deduct credits for a specific AI operation.

        Uses atomic database operation to ensure consistency.

        Args:
            user_id: User ID
            operation: Operation name
            description: Optional description
            idempotency_key: Optional idempotency key

        Returns:
            CreditTransaction record

        Raises:
            InsufficientCreditsException: If not enough credits
            ValueError: If operation is unknown
        """
        cost = await self.get_operation_cost(operation)
        tx_type = self._operation_to_tx_type(operation)

        return await self._repository.deduct_atomic(
            user_id=user_id,
            amount=cost,
            tx_type=tx_type,
            description=description or f"{operation} operation",
            idempotency_key=idempotency_key,
        )

    async def deduct_credits(
        self,
        user_id: str,
        amount: int,
        tx_type: TransactionType,
        description: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> CreditTransaction:
        """
        Deduct arbitrary credits from user.

        Args:
            user_id: User ID
            amount: Amount to deduct
            tx_type: Transaction type
            description: Optional description
            idempotency_key: Optional idempotency key

        Returns:
            CreditTransaction record
        """
        if amount <= 0:
            raise InvalidAmountException(amount, "Deduction amount must be positive")

        return await self._repository.deduct_atomic(
            user_id=user_id,
            amount=amount,
            tx_type=tx_type,
            description=description,
            idempotency_key=idempotency_key,
        )

    async def add_credits(
        self,
        user_id: str,
        amount: int,
        bucket: CreditBucket,
        tx_type: TransactionType,
        description: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> CreditTransaction:
        """
        Add credits to user's balance.

        Args:
            user_id: User ID
            amount: Amount to add
            bucket: Which bucket to add to
            tx_type: Transaction type
            description: Optional description
            idempotency_key: Optional idempotency key

        Returns:
            CreditTransaction record
        """
        if amount <= 0:
            raise InvalidAmountException(amount, "Addition amount must be positive")

        return await self._repository.add_atomic(
            user_id=user_id,
            amount=amount,
            bucket=bucket,
            tx_type=tx_type,
            description=description,
            idempotency_key=idempotency_key,
        )

    async def grant_signup_bonus(
        self,
        user_id: str,
        idempotency_key: Optional[str] = None
    ) -> CreditTransaction:
        """
        Grant signup bonus to new user.

        Args:
            user_id: User ID
            idempotency_key: Optional idempotency key (recommend: user_id)

        Returns:
            CreditTransaction record
        """
        return await self.add_credits(
            user_id=user_id,
            amount=self.SIGNUP_BONUS,
            bucket=CreditBucket.PERMANENT,
            tx_type=TransactionType.SIGNUP_BONUS,
            description="Welcome bonus for new users",
            idempotency_key=idempotency_key or f"signup_bonus_{user_id}",
        )

    async def process_subscription_renewal(
        self,
        user_id: str,
        tier: str
    ) -> UserCredits:
        """
        Process monthly subscription renewal.

        Resets monthly credits based on tier.

        Args:
            user_id: User ID
            tier: Subscription tier

        Returns:
            Updated UserCredits aggregate
        """
        allowance = self.TIER_ALLOWANCES.get(tier, 0)
        return await self._repository.reset_monthly_credits(user_id, allowance)

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
        Get user's transaction history.

        Args:
            user_id: User ID
            limit: Maximum records
            offset: Records to skip
            tx_type: Filter by type
            start_date: Filter start
            end_date: Filter end

        Returns:
            List of transactions
        """
        return await self._repository.get_transaction_history(
            user_id=user_id,
            limit=limit,
            offset=offset,
            tx_type=tx_type,
            start_date=start_date,
            end_date=end_date,
        )

    async def get_transaction_count(
        self,
        user_id: str,
        tx_type: Optional[TransactionType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> int:
        """
        Get total count of transactions for pagination.

        Args:
            user_id: User ID
            tx_type: Filter by type
            start_date: Filter start
            end_date: Filter end

        Returns:
            Total count of matching transactions
        """
        return await self._repository.get_transaction_count(
            user_id=user_id,
            tx_type=tx_type,
            start_date=start_date,
            end_date=end_date,
        )

    def _operation_to_tx_type(self, operation: str) -> TransactionType:
        """Map operation name to transaction type."""
        mapping = {
            "image_generation": TransactionType.AI_GENERATION,
            "text_generation": TransactionType.AI_GENERATION,
            "smart_scan": TransactionType.SMART_SCAN,
            "ocr": TransactionType.SMART_SCAN,
        }
        return mapping.get(operation, TransactionType.AI_GENERATION)
