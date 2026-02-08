"""
Billing Domain Service - Orchestrates credit operations within the domain.

@module domains.billing.service
@version 2.0.0

This service handles domain logic that doesn't naturally belong to aggregates.
It coordinates operations but delegates persistence to the repository.

All credit configurations (costs, allowances, signup bonus) are now fetched from
TierService (system_configs) instead of hardcoded values.
"""

from typing import Optional, List, TYPE_CHECKING
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

if TYPE_CHECKING:
    from domains.identity.tier_service import TierService

logger = logging.getLogger(__name__)


class BillingService:
    """
    Domain service for billing operations.

    This service:
    - Validates business rules
    - Coordinates credit operations
    - Calculates costs for different operations (from TierService configuration)
    """

    def __init__(
        self,
        repository: ICreditRepository,
        tier_service: "TierService" = None
    ):
        """
        Initialize billing service with repository and tier service.

        Args:
            repository: Credit repository implementation
            tier_service: TierService for fetching credit configurations
        """
        self._repository = repository
        self._tier_service = tier_service

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

        Uses TierService to fetch from system_configs, with emergency fallback.

        Args:
            operation: Operation name (image_generation, page_generation, ocr, smart_scan, text_generation)

        Returns:
            Credit cost as integer
        """
        if self._tier_service:
            return await self._tier_service.get_operation_cost(operation)

        # Emergency fallback if tier_service not available
        fallback_costs = {
            "image_generation": 5,
            "page_generation": 5,
            "ocr": 5,
            "smart_scan": 5,
            "text_generation": 0,
        }
        logger.warning(f"Using fallback cost for '{operation}' - tier_service not available")
        return fallback_costs.get(operation, 5)

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

        Bonus amount is fetched from TierService (system_configs).

        Args:
            user_id: User ID
            idempotency_key: Optional idempotency key (recommend: user_id)

        Returns:
            CreditTransaction record
        """
        # Get signup bonus from configuration
        if self._tier_service:
            bonus_amount = await self._tier_service.get_signup_bonus()
        else:
            bonus_amount = 100  # Default fallback

        return await self.add_credits(
            user_id=user_id,
            amount=bonus_amount,
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

        Monthly credit allowance is fetched from TierService (system_configs).

        Args:
            user_id: User ID
            tier: Subscription tier

        Returns:
            Updated UserCredits aggregate
        """
        # Get monthly credits from configuration
        if self._tier_service:
            allowance = await self._tier_service.get_monthly_credits(tier)
        else:
            # Emergency fallback
            from domains.identity.tier_service import EMERGENCY_TIER_CONFIGS
            allowance = EMERGENCY_TIER_CONFIGS.get(tier, {}).get("monthly_credits", 0)

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
        """Map operation name to transaction type.

        Phase 2: All consumption operations map to CREDIT_CONSUME.
        The specific feature name is recorded in the description field.
        """
        # All operations are now CREDIT_CONSUME — feature name is in description
        return TransactionType.CREDIT_CONSUME
