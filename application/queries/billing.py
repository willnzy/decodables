"""
Billing Queries - Credit read operations.

@module application.queries.billing
@version 1.0.0
"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime

from domains.billing import BillingService, TransactionType
from domains.billing.aggregates.user_credits import CreditTransaction


@dataclass
class GetUserCreditsQuery:
    """Query to get user's credit balance."""
    user_id: str


@dataclass
class GetUserCreditsResult:
    """Result of credit balance query."""
    success: bool
    monthly_credits: int = 0
    permanent_credits: int = 0
    total_credits: int = 0
    tier: str = "free"
    error: Optional[str] = None


class GetUserCreditsHandler:
    """Handler for GetUserCreditsQuery."""

    def __init__(self, billing_service: BillingService):
        self._billing_service = billing_service

    async def handle(self, query: GetUserCreditsQuery) -> GetUserCreditsResult:
        """Execute credit balance query."""
        try:
            user_credits = await self._billing_service.get_user_credits(query.user_id)

            if not user_credits:
                return GetUserCreditsResult(
                    success=True,
                    monthly_credits=0,
                    permanent_credits=0,
                    total_credits=0,
                    tier="free",
                )

            return GetUserCreditsResult(
                success=True,
                monthly_credits=user_credits.monthly_credits,
                permanent_credits=user_credits.permanent_credits,
                total_credits=user_credits.total_credits,
                tier=user_credits.tier,
            )

        except Exception as e:
            return GetUserCreditsResult(
                success=False,
                error=str(e),
            )


@dataclass
class GetTransactionHistoryQuery:
    """Query to get user's transaction history."""
    user_id: str
    limit: int = 50
    offset: int = 0
    tx_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


@dataclass
class GetTransactionHistoryResult:
    """Result of transaction history query."""
    success: bool
    transactions: List[CreditTransaction] = None
    total_count: int = 0
    error: Optional[str] = None

    def __post_init__(self):
        if self.transactions is None:
            self.transactions = []


class GetTransactionHistoryHandler:
    """Handler for GetTransactionHistoryQuery."""

    def __init__(self, billing_service: BillingService):
        self._billing_service = billing_service

    async def handle(self, query: GetTransactionHistoryQuery) -> GetTransactionHistoryResult:
        """Execute transaction history query."""
        try:
            tx_type = TransactionType(query.tx_type) if query.tx_type else None

            # Execute list and count queries
            transactions = await self._billing_service.get_transaction_history(
                user_id=query.user_id,
                limit=query.limit,
                offset=query.offset,
                tx_type=tx_type,
                start_date=query.start_date,
                end_date=query.end_date,
            )

            # Get total count for pagination (with same filters, without limit/offset)
            total_count = await self._billing_service.get_transaction_count(
                user_id=query.user_id,
                tx_type=tx_type,
                start_date=query.start_date,
                end_date=query.end_date,
            )

            return GetTransactionHistoryResult(
                success=True,
                transactions=transactions,
                total_count=total_count,
            )

        except Exception as e:
            return GetTransactionHistoryResult(
                success=False,
                error=str(e),
            )


@dataclass
class CheckCanAffordQuery:
    """Query to check if user can afford an operation."""
    user_id: str
    amount: int = 0
    operation: Optional[str] = None  # e.g., "image_generation"


@dataclass
class CheckCanAffordResult:
    """Result of affordability check."""
    success: bool
    can_afford: bool = False
    current_balance: int = 0
    required_amount: int = 0
    error: Optional[str] = None


class CheckCanAffordHandler:
    """Handler for CheckCanAffordQuery."""

    def __init__(self, billing_service: BillingService):
        self._billing_service = billing_service

    async def handle(self, query: CheckCanAffordQuery) -> CheckCanAffordResult:
        """Execute affordability check."""
        try:
            # Determine amount
            if query.operation:
                can_afford = await self._billing_service.check_can_afford_operation(
                    query.user_id,
                    query.operation
                )
                cost = self._billing_service.get_operation_cost(query.operation)
                required = cost.amount
            else:
                can_afford = await self._billing_service.check_can_afford(
                    query.user_id,
                    query.amount
                )
                required = query.amount

            # Get current balance
            user_credits = await self._billing_service.get_user_credits(query.user_id)
            balance = user_credits.total_credits if user_credits else 0

            return CheckCanAffordResult(
                success=True,
                can_afford=can_afford,
                current_balance=balance,
                required_amount=required,
            )

        except Exception as e:
            return CheckCanAffordResult(
                success=False,
                error=str(e),
            )
