"""
Billing Commands - Credit operations that change state.

@module application.commands.billing
@version 1.0.0
"""

from dataclasses import dataclass
from typing import Optional

from domains.billing import (
    BillingService,
    CreditBucket,
    TransactionType,
    UserCredits,
)
from domains.billing.aggregates.user_credits import CreditTransaction
from domains.billing.exceptions import (
    InsufficientCreditsException,
    CreditOperationFailedException,
    InvalidAmountException,
)


@dataclass
class DeductCreditsCommand:
    """
    Command to deduct credits from a user.

    Use cases:
    - AI image generation (5 credits)
    - AI text generation (1 credit)
    - Smart scan (10 credits)
    """
    user_id: str
    amount: int
    operation: Optional[str] = None  # e.g., "image_generation"
    tx_type: TransactionType = TransactionType.AI_GENERATION
    description: Optional[str] = None
    idempotency_key: Optional[str] = None


@dataclass
class DeductCreditsResult:
    """Result of credit deduction."""
    success: bool
    transaction: Optional[CreditTransaction] = None
    error: Optional[str] = None
    remaining_credits: int = 0


class DeductCreditsHandler:
    """Handler for DeductCreditsCommand."""

    def __init__(self, billing_service: BillingService):
        self._billing_service = billing_service

    async def handle(self, command: DeductCreditsCommand) -> DeductCreditsResult:
        """Execute credit deduction."""
        try:
            # Use operation-based deduction if specified
            if command.operation:
                tx = await self._billing_service.deduct_for_operation(
                    user_id=command.user_id,
                    operation=command.operation,
                    description=command.description,
                    idempotency_key=command.idempotency_key,
                )
            else:
                tx = await self._billing_service.deduct_credits(
                    user_id=command.user_id,
                    amount=command.amount,
                    tx_type=command.tx_type,
                    description=command.description,
                    idempotency_key=command.idempotency_key,
                )

            # Get remaining balance
            user_credits = await self._billing_service.get_user_credits(command.user_id)
            remaining = user_credits.total_credits if user_credits else 0

            return DeductCreditsResult(
                success=True,
                transaction=tx,
                remaining_credits=remaining,
            )

        except InsufficientCreditsException as e:
            # B-NEW-1 FIX: Expected business exception - insufficient credits
            return DeductCreditsResult(
                success=False,
                error="Insufficient credits",
            )
        except (CreditOperationFailedException, InvalidAmountException) as e:
            # B-NEW-1 FIX: Other business exceptions
            return DeductCreditsResult(
                success=False,
                error="Failed to deduct credits",
            )
        except Exception as e:
            # Unexpected system errors - log and return generic error
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"[Billing] Unexpected error in DeductCreditsHandler: {e}", exc_info=True)
            return DeductCreditsResult(
                success=False,
                error="System error",
            )


@dataclass
class AddCreditsCommand:
    """
    Command to add credits to a user.

    Use cases:
    - Credit purchase
    - Promotional credits
    - Refunds
    """
    user_id: str
    amount: int
    bucket: CreditBucket
    tx_type: TransactionType
    description: Optional[str] = None
    idempotency_key: Optional[str] = None


@dataclass
class AddCreditsResult:
    """Result of credit addition."""
    success: bool
    transaction: Optional[CreditTransaction] = None
    error: Optional[str] = None
    new_balance: int = 0


class AddCreditsHandler:
    """Handler for AddCreditsCommand."""

    def __init__(self, billing_service: BillingService):
        self._billing_service = billing_service

    async def handle(self, command: AddCreditsCommand) -> AddCreditsResult:
        """Execute credit addition."""
        try:
            tx = await self._billing_service.add_credits(
                user_id=command.user_id,
                amount=command.amount,
                bucket=command.bucket,
                tx_type=command.tx_type,
                description=command.description,
                idempotency_key=command.idempotency_key,
            )

            # Get new balance
            user_credits = await self._billing_service.get_user_credits(command.user_id)
            new_balance = user_credits.total_credits if user_credits else 0

            return AddCreditsResult(
                success=True,
                transaction=tx,
                new_balance=new_balance,
            )

        except (CreditOperationFailedException, InvalidAmountException) as e:
            # B-NEW-1 FIX: Catch specific business exceptions
            return AddCreditsResult(
                success=False,
                error="Failed to add credits",
            )
        except Exception as e:
            # Unexpected system errors - log and return generic error
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"[Billing] Unexpected error in AddCreditsHandler: {e}", exc_info=True)
            return AddCreditsResult(
                success=False,
                error="System error",
            )


@dataclass
class GrantSignupBonusCommand:
    """
    Command to grant signup bonus to new user.

    Grants signup bonus permanent credits to new users (configured in system_configs, default 100).
    """
    user_id: str


@dataclass
class GrantSignupBonusResult:
    """Result of signup bonus grant."""
    success: bool
    credits_granted: int = 0
    error: Optional[str] = None


class GrantSignupBonusHandler:
    """Handler for GrantSignupBonusCommand."""

    def __init__(self, billing_service: BillingService):
        self._billing_service = billing_service

    async def handle(self, command: GrantSignupBonusCommand) -> GrantSignupBonusResult:
        """Execute signup bonus grant."""
        try:
            tx = await self._billing_service.grant_signup_bonus(
                user_id=command.user_id,
                idempotency_key=f"signup_bonus_{command.user_id}",
            )

            return GrantSignupBonusResult(
                success=True,
                credits_granted=tx.amount,
            )

        except (CreditOperationFailedException, InvalidAmountException) as e:
            # B-NEW-1 FIX: Catch specific business exceptions
            return GrantSignupBonusResult(
                success=False,
                error="Failed to grant signup bonus",
            )
        except Exception as e:
            # Unexpected system errors - log and return generic error
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"[Billing] Unexpected error in GrantSignupBonusHandler: {e}", exc_info=True)
            return GrantSignupBonusResult(
                success=False,
                error="System error",
            )
