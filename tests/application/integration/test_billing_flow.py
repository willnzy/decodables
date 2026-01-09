"""
Billing Application Layer Integration Tests.

Tests complete flow: CommandBus → Handler → BillingService → Repository

@module tests.application.integration.test_billing_flow
@version 1.0.0
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timezone

from application.handlers import CommandBus, QueryBus
from application.commands.billing import (
    DeductCreditsCommand,
    DeductCreditsHandler,
    AddCreditsCommand,
    AddCreditsHandler,
    GrantSignupBonusCommand,
    GrantSignupBonusHandler,
)
from application.queries.billing import (
    GetUserCreditsQuery,
    GetUserCreditsHandler,
    GetTransactionHistoryQuery,
    GetTransactionHistoryHandler,
)
from domains.billing import (
    BillingService,
    UserCredits,
    CreditBucket,
    TransactionType,
    Credits,
)
from domains.billing.aggregates.user_credits import CreditTransaction


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def mock_billing_repository():
    """Mock billing repository."""
    repo = Mock()
    repo.get_by_user_id = AsyncMock()
    repo.save = AsyncMock()
    repo.deduct_atomic = AsyncMock()
    repo.add_atomic = AsyncMock()
    repo.get_transaction_history = AsyncMock()
    repo.get_transaction_count = AsyncMock()
    return repo


@pytest.fixture
def billing_service(mock_billing_repository):
    """Create BillingService with mock repository."""
    return BillingService(repository=mock_billing_repository)


@pytest.fixture
def command_bus(billing_service):
    """Create CommandBus with billing handlers registered."""
    bus = CommandBus()
    bus.register(DeductCreditsCommand, DeductCreditsHandler(billing_service))
    bus.register(AddCreditsCommand, AddCreditsHandler(billing_service))
    bus.register(GrantSignupBonusCommand, GrantSignupBonusHandler(billing_service))
    return bus


@pytest.fixture
def query_bus(billing_service):
    """Create QueryBus with billing handlers registered."""
    bus = QueryBus()
    bus.register(GetUserCreditsQuery, GetUserCreditsHandler(billing_service))
    bus.register(GetTransactionHistoryQuery, GetTransactionHistoryHandler(billing_service))
    return bus


# ==========================================
# Command Tests
# ==========================================

class TestDeductCreditsFlow:
    """Test complete credit deduction flow."""

    @pytest.mark.asyncio
    async def test_deduct_credits_via_command_bus(self, command_bus, mock_billing_repository):
        """Test deducting credits through command bus."""
        # Arrange
        user_credits = UserCredits.create(
            user_id="user_123",
            monthly=100,
            permanent=50,
            tier="pro",
        )

        transaction = CreditTransaction(
            amount=-5,
            bucket=CreditBucket.MONTHLY,
            tx_type=TransactionType.GENERATION,
            description="AI image generation",
            balance_after=Credits(monthly=95, permanent=50),
            created_at=datetime.now(timezone.utc),
        )

        mock_billing_repository.deduct_atomic.return_value = transaction
        mock_billing_repository.get_by_user_id.return_value = user_credits

        # Act
        command = DeductCreditsCommand(
            user_id="user_123",
            amount=5,
            operation="image_generation",
        )
        result = await command_bus.execute(command)

        # Assert
        assert result.success is True
        assert result.transaction is not None
        assert result.transaction.amount == -5
        assert result.remaining_credits == 150
        mock_billing_repository.deduct_atomic.assert_called_once()

    @pytest.mark.asyncio
    async def test_deduct_credits_insufficient_balance(self, command_bus, mock_billing_repository):
        """Test deduction fails when insufficient balance."""
        # Arrange
        from domains.billing.exceptions import InsufficientCreditsException
        mock_billing_repository.deduct_atomic.side_effect = InsufficientCreditsException(
            required=100,
            available=50
        )

        # Act
        command = DeductCreditsCommand(
            user_id="user_456",
            amount=100,
            operation="image_generation",
        )
        result = await command_bus.execute(command)

        # Assert
        assert result.success is False
        assert "Insufficient credits" in result.error


class TestAddCreditsFlow:
    """Test complete credit addition flow."""

    @pytest.mark.asyncio
    async def test_add_credits_via_command_bus(self, command_bus, mock_billing_repository):
        """Test adding credits through command bus."""
        # Arrange
        user_credits = UserCredits.create(
            user_id="user_123",
            monthly=0,
            permanent=150,  # 50 + 100
            tier="pro",
        )

        transaction = CreditTransaction(
            amount=100,
            bucket=CreditBucket.PERMANENT,
            tx_type=TransactionType.TOPUP_PURCHASE,
            description="Credit purchase",
            balance_after=Credits(monthly=0, permanent=150),
            created_at=datetime.now(timezone.utc),
        )

        mock_billing_repository.add_atomic.return_value = transaction
        mock_billing_repository.get_by_user_id.return_value = user_credits

        # Act
        command = AddCreditsCommand(
            user_id="user_123",
            amount=100,
            bucket=CreditBucket.PERMANENT,
            tx_type=TransactionType.TOPUP_PURCHASE,
            description="Credit purchase",
        )
        result = await command_bus.execute(command)

        # Assert
        assert result.success is True
        assert result.transaction.amount == 100
        assert result.new_balance == 150


class TestGrantSignupBonusFlow:
    """Test signup bonus grant flow."""

    @pytest.mark.asyncio
    async def test_grant_signup_bonus_via_command_bus(self, command_bus, mock_billing_repository):
        """Test granting signup bonus through command bus."""
        # Arrange
        transaction = CreditTransaction(
            amount=50,
            bucket=CreditBucket.PERMANENT,
            tx_type=TransactionType.TOPUP_PURCHASE,  # Use existing enum value
            description="Signup bonus",
            balance_after=Credits(monthly=0, permanent=50),
            created_at=datetime.now(timezone.utc),
        )

        mock_billing_repository.add_atomic.return_value = transaction

        # Act
        command = GrantSignupBonusCommand(user_id="new_user_001")
        result = await command_bus.execute(command)

        # Assert
        assert result.success is True
        assert result.credits_granted == 50


# ==========================================
# Query Tests
# ==========================================

class TestGetUserCreditsFlow:
    """Test querying user credits."""

    @pytest.mark.asyncio
    async def test_get_user_credits_via_query_bus(self, query_bus, mock_billing_repository):
        """Test getting user credits through query bus."""
        # Arrange
        user_credits = UserCredits.create(
            user_id="user_123",
            monthly=500,
            permanent=50,
            tier="starter",
        )

        mock_billing_repository.get_by_user_id.return_value = user_credits

        # Act
        query = GetUserCreditsQuery(user_id="user_123")
        result = await query_bus.execute(query)

        # Assert
        assert result.success is True
        assert result.monthly_credits == 500
        assert result.permanent_credits == 50
        assert result.total_credits == 550
        assert result.tier == "starter"

    @pytest.mark.asyncio
    async def test_get_user_credits_not_found(self, query_bus, mock_billing_repository):
        """Test querying non-existent user returns zero balance."""
        # Arrange
        mock_billing_repository.get_by_user_id.return_value = None

        # Act
        query = GetUserCreditsQuery(user_id="nonexistent")
        result = await query_bus.execute(query)

        # Assert
        assert result.success is True
        assert result.total_credits == 0
        assert result.tier == "free"


class TestGetTransactionHistoryFlow:
    """Test querying transaction history."""

    @pytest.mark.asyncio
    async def test_get_transaction_history_via_query_bus(self, query_bus, mock_billing_repository):
        """Test getting transaction history through query bus."""
        # Arrange
        transactions = [
            CreditTransaction(
                amount=-5,
                bucket=CreditBucket.MONTHLY,
                tx_type=TransactionType.GENERATION,
                description="AI generation",
                balance_after=Credits(monthly=95, permanent=0),
                created_at=datetime.now(timezone.utc),
            ),
            CreditTransaction(
                amount=100,
                bucket=CreditBucket.PERMANENT,
                tx_type=TransactionType.TOPUP_PURCHASE,
                description="Credit purchase",
                balance_after=Credits(monthly=0, permanent=100),
                created_at=datetime.now(timezone.utc),
            ),
        ]

        mock_billing_repository.get_transaction_history.return_value = transactions
        mock_billing_repository.get_transaction_count.return_value = 2

        # Act
        query = GetTransactionHistoryQuery(user_id="user_123", limit=10)
        result = await query_bus.execute(query)

        # Assert
        assert result.success is True
        assert len(result.transactions) == 2
        assert result.total_count == 2


# ==========================================
# End-to-End Flow Tests
# ==========================================

class TestBillingE2EFlow:
    """Test end-to-end billing flows."""

    @pytest.mark.asyncio
    async def test_complete_purchase_and_generation_flow(
        self, command_bus, query_bus, mock_billing_repository
    ):
        """
        Test complete flow:
        1. Check initial balance
        2. Purchase credits
        3. Check new balance
        4. Use credits for generation
        5. Check final balance
        """
        # Step 1: Initial balance
        initial_credits = UserCredits.create(
            user_id="user_123",
            monthly=0,
            permanent=0,
            tier="free",
        )
        mock_billing_repository.get_by_user_id.return_value = initial_credits

        query = GetUserCreditsQuery(user_id="user_123")
        result = await query_bus.execute(query)
        assert result.total_credits == 0

        # Step 2: Purchase credits
        purchase_tx = CreditTransaction(
            amount=100,
            bucket=CreditBucket.PERMANENT,
            tx_type=TransactionType.TOPUP_PURCHASE,
            description="Purchase",
            balance_after=Credits(monthly=0, permanent=100),
            created_at=datetime.now(timezone.utc),
        )
        mock_billing_repository.add_atomic.return_value = purchase_tx

        after_purchase = UserCredits.create(
            user_id="user_123",
            monthly=0,
            permanent=100,
            tier="free",
        )
        mock_billing_repository.get_by_user_id.return_value = after_purchase

        purchase_cmd = AddCreditsCommand(
            user_id="user_123",
            amount=100,
            bucket=CreditBucket.PERMANENT,
            tx_type=TransactionType.TOPUP_PURCHASE,
        )
        purchase_result = await command_bus.execute(purchase_cmd)
        assert purchase_result.new_balance == 100

        # Step 3: Use credits
        deduct_tx = CreditTransaction(
            amount=-5,
            bucket=CreditBucket.PERMANENT,
            tx_type=TransactionType.GENERATION,
            description="Generation",
            balance_after=Credits(monthly=0, permanent=95),
            created_at=datetime.now(timezone.utc),
        )
        mock_billing_repository.deduct_atomic.return_value = deduct_tx

        after_deduct = UserCredits.create(
            user_id="user_123",
            monthly=0,
            permanent=95,
            tier="free",
        )
        mock_billing_repository.get_by_user_id.return_value = after_deduct

        deduct_cmd = DeductCreditsCommand(
            user_id="user_123",
            amount=5,
            operation="image_generation",
        )
        deduct_result = await command_bus.execute(deduct_cmd)
        assert deduct_result.remaining_credits == 95

        # Step 4: Final balance check
        final_query = GetUserCreditsQuery(user_id="user_123")
        final_result = await query_bus.execute(final_query)
        assert final_result.total_credits == 95
