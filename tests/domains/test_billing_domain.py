"""
Billing Domain Tests - UserCredits aggregate and credit logic.

@module tests.domains.test_billing_domain
@version 1.0.0

Tests cover:
- UserCredits aggregate creation and operations
- Credit deduction priority (monthly first, then permanent)
- Transaction recording
- Edge cases (zero balance, negative amounts)
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock

from domains.billing import (
    UserCredits,
    CreditTransaction,
    CreditType,
    TransactionType,
    OperationCost,
    InsufficientCreditsError,
    InvalidCreditOperationError,
)


class TestUserCreditsAggregate:
    """Tests for UserCredits aggregate."""

    def test_create_user_credits(self):
        """Test creating UserCredits aggregate."""
        credits = UserCredits(
            user_id="user_123",
            monthly_credits=500,
            permanent_credits=100,
            tier="starter",
        )

        assert credits.user_id == "user_123"
        assert credits.monthly_credits == 500
        assert credits.permanent_credits == 100
        assert credits.tier == "starter"
        assert credits.total_credits == 600

    def test_create_with_defaults(self):
        """Test creating UserCredits with default values."""
        credits = UserCredits(user_id="user_456")

        assert credits.monthly_credits == 0
        assert credits.permanent_credits == 0
        assert credits.tier == "free"
        assert credits.total_credits == 0

    def test_can_afford_true(self):
        """Test can_afford returns True when balance sufficient."""
        credits = UserCredits(
            user_id="user_123",
            monthly_credits=100,
            permanent_credits=50,
        )

        assert credits.can_afford(100) is True
        assert credits.can_afford(150) is True
        assert credits.can_afford(1) is True

    def test_can_afford_false(self):
        """Test can_afford returns False when balance insufficient."""
        credits = UserCredits(
            user_id="user_123",
            monthly_credits=50,
            permanent_credits=30,
        )

        assert credits.can_afford(81) is False
        assert credits.can_afford(100) is False
        assert credits.can_afford(1000) is False

    def test_can_afford_zero(self):
        """Test can_afford for zero amount."""
        credits = UserCredits(user_id="user_123")
        assert credits.can_afford(0) is True

    def test_deduct_from_monthly_first(self):
        """Test credit deduction uses monthly credits first."""
        credits = UserCredits(
            user_id="user_123",
            monthly_credits=100,
            permanent_credits=50,
        )

        tx = credits.deduct(30, "image_generation", "Test deduction")

        # Monthly should be reduced, permanent unchanged
        assert credits.monthly_credits == 70
        assert credits.permanent_credits == 50
        assert tx.amount == -30
        assert tx.credit_type == CreditType.MONTHLY

    def test_deduct_from_permanent_when_monthly_depleted(self):
        """Test deduction uses permanent when monthly is zero."""
        credits = UserCredits(
            user_id="user_123",
            monthly_credits=0,
            permanent_credits=100,
        )

        tx = credits.deduct(25, "image_generation", "Test deduction")

        assert credits.monthly_credits == 0
        assert credits.permanent_credits == 75
        assert tx.credit_type == CreditType.PERMANENT

    def test_deduct_mixed_sources(self):
        """Test deduction that spans both credit types."""
        credits = UserCredits(
            user_id="user_123",
            monthly_credits=30,
            permanent_credits=100,
        )

        # Deduct 50: should use 30 monthly + 20 permanent
        tx = credits.deduct(50, "smart_scan", "Mixed deduction")

        assert credits.monthly_credits == 0
        assert credits.permanent_credits == 80
        # Primary transaction type should be monthly (first source)
        assert tx.amount == -50

    def test_deduct_insufficient_raises_error(self):
        """Test deduction with insufficient balance raises error."""
        credits = UserCredits(
            user_id="user_123",
            monthly_credits=10,
            permanent_credits=10,
        )

        with pytest.raises(InsufficientCreditsError) as exc_info:
            credits.deduct(50, "operation", "Should fail")

        assert "Insufficient credits" in str(exc_info.value)

    def test_deduct_negative_amount_raises_error(self):
        """Test deduction with negative amount raises error."""
        credits = UserCredits(
            user_id="user_123",
            monthly_credits=100,
        )

        with pytest.raises(InvalidCreditOperationError):
            credits.deduct(-10, "operation", "Negative amount")

    def test_add_monthly_credits(self):
        """Test adding monthly credits."""
        credits = UserCredits(
            user_id="user_123",
            monthly_credits=100,
        )

        tx = credits.add_monthly(500, "subscription_renewal")

        assert credits.monthly_credits == 600
        assert tx.amount == 500
        assert tx.credit_type == CreditType.MONTHLY

    def test_add_permanent_credits(self):
        """Test adding permanent credits."""
        credits = UserCredits(
            user_id="user_123",
            permanent_credits=50,
        )

        tx = credits.add_permanent(100, "purchase")

        assert credits.permanent_credits == 150
        assert tx.amount == 100
        assert tx.credit_type == CreditType.PERMANENT

    def test_reset_monthly_credits(self):
        """Test resetting monthly credits (subscription renewal)."""
        credits = UserCredits(
            user_id="user_123",
            monthly_credits=50,
            tier="starter",
        )

        tx = credits.reset_monthly(500)  # Starter gets 500

        assert credits.monthly_credits == 500
        assert tx.tx_type == TransactionType.MONTHLY_RESET

    def test_to_dict(self):
        """Test serializing UserCredits to dict."""
        credits = UserCredits(
            user_id="user_123",
            monthly_credits=500,
            permanent_credits=100,
            tier="pro",
        )

        data = credits.to_dict()

        assert data["user_id"] == "user_123"
        assert data["monthly_credits"] == 500
        assert data["permanent_credits"] == 100
        assert data["total_credits"] == 600
        assert data["tier"] == "pro"

    def test_from_dict(self):
        """Test creating UserCredits from dict."""
        data = {
            "user_id": "user_789",
            "credits_monthly": 300,
            "credits_permanent": 75,
            "tier": "starter",
        }

        credits = UserCredits.from_dict(data)

        assert credits.user_id == "user_789"
        assert credits.monthly_credits == 300
        assert credits.permanent_credits == 75
        assert credits.tier == "starter"


class TestCreditTransaction:
    """Tests for CreditTransaction value object."""

    def test_create_transaction(self):
        """Test creating a credit transaction."""
        tx = CreditTransaction(
            id="tx_001",
            user_id="user_123",
            amount=-5,
            balance_after=95,
            tx_type=TransactionType.DEDUCTION,
            credit_type=CreditType.MONTHLY,
            operation="image_generation",
            description="Generated 1 image",
        )

        assert tx.id == "tx_001"
        assert tx.amount == -5
        assert tx.is_deduction is True
        assert tx.is_addition is False

    def test_transaction_types(self):
        """Test different transaction types."""
        deduction = CreditTransaction(
            id="tx_001",
            user_id="user_123",
            amount=-10,
            balance_after=90,
            tx_type=TransactionType.DEDUCTION,
        )

        addition = CreditTransaction(
            id="tx_002",
            user_id="user_123",
            amount=100,
            balance_after=190,
            tx_type=TransactionType.PURCHASE,
        )

        assert deduction.is_deduction is True
        assert addition.is_addition is True


class TestOperationCost:
    """Tests for OperationCost value object."""

    def test_create_operation_cost(self):
        """Test creating operation cost."""
        cost = OperationCost(
            operation="image_generation",
            amount=5,
            description="AI image generation",
        )

        assert cost.operation == "image_generation"
        assert cost.amount == 5
        assert cost.description == "AI image generation"

    def test_default_costs(self):
        """Test default operation costs are correct."""
        # These should match the business rules
        image_gen = OperationCost.for_operation("image_generation")
        text_gen = OperationCost.for_operation("text_generation")
        smart_scan = OperationCost.for_operation("smart_scan")

        assert image_gen.amount == 5
        assert text_gen.amount == 1
        assert smart_scan.amount == 10

    def test_unknown_operation(self):
        """Test unknown operation returns zero cost."""
        cost = OperationCost.for_operation("unknown_operation")
        assert cost.amount == 0


class TestBillingService:
    """Tests for BillingService (with mocked repository)."""

    @pytest.fixture
    def mock_repository(self):
        """Create mock credit repository."""
        repo = MagicMock()
        repo.get_by_user_id = AsyncMock()
        repo.save = AsyncMock()
        repo.add_transaction = AsyncMock()
        repo.get_transactions = AsyncMock(return_value=[])
        return repo

    @pytest.fixture
    def billing_service(self, mock_repository):
        """Create billing service with mock repository."""
        from domains.billing import BillingService
        return BillingService(mock_repository)

    @pytest.mark.asyncio
    async def test_get_user_credits(self, billing_service, mock_repository):
        """Test getting user credits."""
        mock_repository.get_by_user_id.return_value = UserCredits(
            user_id="user_123",
            monthly_credits=500,
            permanent_credits=100,
        )

        credits = await billing_service.get_user_credits("user_123")

        assert credits.total_credits == 600
        mock_repository.get_by_user_id.assert_called_once_with("user_123")

    @pytest.mark.asyncio
    async def test_deduct_credits_success(self, billing_service, mock_repository):
        """Test successful credit deduction."""
        mock_repository.get_by_user_id.return_value = UserCredits(
            user_id="user_123",
            monthly_credits=100,
            permanent_credits=50,
        )

        result = await billing_service.deduct_credits(
            user_id="user_123",
            amount=30,
            operation="image_generation",
        )

        assert result.success is True
        assert result.amount_deducted == 30
        mock_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_deduct_credits_insufficient(self, billing_service, mock_repository):
        """Test credit deduction with insufficient balance."""
        mock_repository.get_by_user_id.return_value = UserCredits(
            user_id="user_123",
            monthly_credits=10,
            permanent_credits=5,
        )

        result = await billing_service.deduct_credits(
            user_id="user_123",
            amount=100,
            operation="image_generation",
        )

        assert result.success is False
        assert "insufficient" in result.error.lower()
        mock_repository.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_can_afford(self, billing_service, mock_repository):
        """Test affordability check."""
        mock_repository.get_by_user_id.return_value = UserCredits(
            user_id="user_123",
            monthly_credits=50,
            permanent_credits=50,
        )

        assert await billing_service.check_can_afford("user_123", 100) is True
        assert await billing_service.check_can_afford("user_123", 101) is False

    @pytest.mark.asyncio
    async def test_grant_signup_bonus(self, billing_service, mock_repository):
        """Test granting signup bonus credits."""
        mock_repository.get_by_user_id.return_value = None  # New user

        result = await billing_service.grant_signup_bonus("new_user_123")

        assert result.success is True
        assert result.amount_added == 50  # Signup bonus
        mock_repository.save.assert_called_once()
