"""
Billing Handler Tests - Command and Query handlers for billing.

@module tests.application.test_billing_handlers
@version 1.0.0

Tests cover:
- DeductCreditsHandler
- AddCreditsHandler
- GetUserCreditsHandler
- GetTransactionHistoryHandler
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, timezone

from domains.billing import (
    UserCredits,
    CreditTransaction,
    Credits,
    CreditBucket,
    TransactionType,
    BillingService,
)


class TestDeductCreditsHandler:
    """Tests for DeductCreditsHandler."""

    @pytest.fixture
    def mock_billing_service(self):
        """Create mock billing service."""
        service = MagicMock(spec=BillingService)
        service.deduct_credits = AsyncMock()
        service.get_user_credits = AsyncMock()
        return service

    @pytest.fixture
    def handler(self, mock_billing_service):
        """Create handler with mock service."""
        from application.commands.billing import DeductCreditsHandler
        return DeductCreditsHandler(mock_billing_service)

    @pytest.mark.asyncio
    async def test_deduct_credits_success(self, handler, mock_billing_service):
        """Test successful credit deduction."""
        from application.commands.billing import DeductCreditsCommand

        # Mock the transaction object
        mock_tx = MagicMock(spec=CreditTransaction)
        mock_tx.amount = -5
        mock_billing_service.deduct_for_operation.return_value = mock_tx

        # Mock the user credits
        mock_user_credits = MagicMock(spec=UserCredits)
        mock_user_credits.total_credits = 95
        mock_billing_service.get_user_credits.return_value = mock_user_credits

        command = DeductCreditsCommand(
            user_id="user_123",
            amount=5,
            operation="image_generation",
            description="Generated 1 image",
        )

        result = await handler.handle(command)

        assert result.success is True
        assert result.remaining_credits == 95
        assert result.transaction == mock_tx
        mock_billing_service.deduct_for_operation.assert_called_once()

    @pytest.mark.asyncio
    async def test_deduct_credits_insufficient(self, handler, mock_billing_service):
        """Test deduction with insufficient credits."""
        from application.commands.billing import DeductCreditsCommand
        from domains.billing.exceptions import InsufficientCreditsException

        mock_billing_service.deduct_for_operation.side_effect = InsufficientCreditsException(
            required=100,
            available=50
        )

        command = DeductCreditsCommand(
            user_id="user_123",
            amount=100,
            operation="image_generation",
        )

        result = await handler.handle(command)

        assert result.success is False
        assert "insufficient" in result.error.lower()


class TestAddCreditsHandler:
    """Tests for AddCreditsHandler."""

    @pytest.fixture
    def mock_billing_service(self):
        """Create mock billing service."""
        service = MagicMock(spec=BillingService)
        service.add_credits = AsyncMock()
        return service

    @pytest.fixture
    def handler(self, mock_billing_service):
        """Create handler with mock service."""
        from application.commands.billing import AddCreditsHandler
        return AddCreditsHandler(mock_billing_service)

    @pytest.mark.asyncio
    async def test_add_monthly_credits(self, handler, mock_billing_service):
        """Test adding monthly credits."""
        from application.commands.billing import AddCreditsCommand

        # Mock the transaction object
        mock_tx = MagicMock(spec=CreditTransaction)
        mock_tx.amount = 500
        mock_billing_service.add_credits.return_value = mock_tx

        # Mock the user credits
        mock_user_credits = MagicMock(spec=UserCredits)
        mock_user_credits.total_credits = 500
        mock_billing_service.get_user_credits.return_value = mock_user_credits

        command = AddCreditsCommand(
            user_id="user_123",
            amount=500,
            bucket=CreditBucket.MONTHLY,
            tx_type=TransactionType.SUBSCRIPTION_GRANT,
            description="subscription_renewal",
        )

        result = await handler.handle(command)

        assert result.success is True
        assert result.new_balance == 500
        assert result.transaction == mock_tx

    @pytest.mark.asyncio
    async def test_add_permanent_credits(self, handler, mock_billing_service):
        """Test adding permanent credits."""
        from application.commands.billing import AddCreditsCommand

        # Mock the transaction object
        mock_tx = MagicMock(spec=CreditTransaction)
        mock_tx.amount = 100
        mock_billing_service.add_credits.return_value = mock_tx

        # Mock the user credits
        mock_user_credits = MagicMock(spec=UserCredits)
        mock_user_credits.total_credits = 100
        mock_billing_service.get_user_credits.return_value = mock_user_credits

        command = AddCreditsCommand(
            user_id="user_123",
            amount=100,
            bucket=CreditBucket.PERMANENT,
            tx_type=TransactionType.PURCHASE,
            description="purchase",
        )

        result = await handler.handle(command)

        assert result.success is True
        assert result.new_balance == 100
        assert result.transaction == mock_tx


class TestGrantSignupBonusHandler:
    """Tests for GrantSignupBonusHandler."""

    @pytest.fixture
    def mock_billing_service(self):
        """Create mock billing service."""
        service = MagicMock(spec=BillingService)
        service.grant_signup_bonus = AsyncMock()
        return service

    @pytest.fixture
    def handler(self, mock_billing_service):
        """Create handler with mock service."""
        from application.commands.billing import GrantSignupBonusHandler
        return GrantSignupBonusHandler(mock_billing_service)

    @pytest.mark.asyncio
    async def test_grant_signup_bonus(self, handler, mock_billing_service):
        """Test granting signup bonus."""
        from application.commands.billing import GrantSignupBonusCommand

        # Mock the transaction object
        mock_tx = MagicMock(spec=CreditTransaction)
        mock_tx.amount = 50
        mock_billing_service.grant_signup_bonus.return_value = mock_tx

        command = GrantSignupBonusCommand(user_id="new_user_123")

        result = await handler.handle(command)

        assert result.success is True
        assert result.credits_granted == 50  # Signup bonus is 50


class TestGetUserCreditsHandler:
    """Tests for GetUserCreditsHandler."""

    @pytest.fixture
    def mock_billing_service(self):
        """Create mock billing service."""
        service = MagicMock(spec=BillingService)
        service.get_user_credits = AsyncMock()
        return service

    @pytest.fixture
    def handler(self, mock_billing_service):
        """Create handler with mock service."""
        from application.queries.billing import GetUserCreditsHandler
        return GetUserCreditsHandler(mock_billing_service)

    @pytest.mark.asyncio
    async def test_get_user_credits(self, handler, mock_billing_service):
        """Test getting user credits."""
        from application.queries.billing import GetUserCreditsQuery

        mock_billing_service.get_user_credits.return_value = UserCredits.create(
            user_id="user_123",
            monthly=500,
            permanent=100,
            tier="t2",
        )

        query = GetUserCreditsQuery(user_id="user_123")
        result = await handler.handle(query)

        assert result.success is True
        assert result.monthly_credits == 500
        assert result.permanent_credits == 100
        assert result.total_credits == 600
        assert result.tier == "t2"

    @pytest.mark.asyncio
    async def test_get_user_credits_new_user(self, handler, mock_billing_service):
        """Test getting credits for new user (no records)."""
        from application.queries.billing import GetUserCreditsQuery

        mock_billing_service.get_user_credits.return_value = None

        query = GetUserCreditsQuery(user_id="new_user")
        result = await handler.handle(query)

        assert result.success is True
        assert result.total_credits == 0
        assert result.tier == "t1"


class TestGetTransactionHistoryHandler:
    """Tests for GetTransactionHistoryHandler."""

    @pytest.fixture
    def mock_billing_service(self):
        """Create mock billing service."""
        service = MagicMock(spec=BillingService)
        service.get_transaction_history = AsyncMock()
        service.get_transaction_count = AsyncMock()
        return service

    @pytest.fixture
    def handler(self, mock_billing_service):
        """Create handler with mock service."""
        from application.queries.billing import GetTransactionHistoryHandler
        return GetTransactionHistoryHandler(mock_billing_service)

    @pytest.mark.asyncio
    async def test_get_transaction_history(self, handler, mock_billing_service):
        """Test getting transaction history."""
        from application.queries.billing import GetTransactionHistoryQuery

        mock_billing_service.get_transaction_history.return_value = [
            CreditTransaction(
                amount=-5,
                bucket=CreditBucket.MONTHLY,
                tx_type=TransactionType.AI_GENERATION,
                description="image_generation",
                balance_after=Credits(monthly=95, permanent=0),
                created_at=datetime.now(timezone.utc),
            ),
            CreditTransaction(
                amount=500,
                bucket=CreditBucket.MONTHLY,
                tx_type=TransactionType.SUBSCRIPTION_GRANT,
                description="Monthly subscription grant",
                balance_after=Credits(monthly=500, permanent=0),
                created_at=datetime.now(timezone.utc),
            ),
        ]
        mock_billing_service.get_transaction_count.return_value = 2

        query = GetTransactionHistoryQuery(
            user_id="user_123",
            limit=50,
            offset=0,
        )
        result = await handler.handle(query)

        assert result.success is True
        assert len(result.transactions) == 2
        assert result.total_count == 2

    @pytest.mark.asyncio
    async def test_get_transaction_history_empty(self, handler, mock_billing_service):
        """Test getting empty transaction history."""
        from application.queries.billing import GetTransactionHistoryQuery

        mock_billing_service.get_transaction_history.return_value = []
        mock_billing_service.get_transaction_count.return_value = 0

        query = GetTransactionHistoryQuery(user_id="new_user")
        result = await handler.handle(query)

        assert result.success is True
        assert len(result.transactions) == 0
        assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_get_transaction_history_filtered(self, handler, mock_billing_service):
        """Test getting filtered transaction history."""
        from application.queries.billing import GetTransactionHistoryQuery

        mock_billing_service.get_transaction_history.return_value = [
            CreditTransaction(
                amount=-5,
                bucket=CreditBucket.MONTHLY,
                tx_type=TransactionType.AI_GENERATION,
                description="image_generation",
                balance_after=Credits(monthly=95, permanent=0),
                created_at=datetime.now(timezone.utc),
            ),
        ]
        mock_billing_service.get_transaction_count.return_value = 1

        query = GetTransactionHistoryQuery(
            user_id="user_123",
            tx_type="ai_generation",  # Use valid TransactionType value
            limit=10,
        )
        result = await handler.handle(query)

        assert result.success is True
        assert len(result.transactions) == 1
        assert result.total_count == 1
        mock_billing_service.get_transaction_history.assert_called_once()
