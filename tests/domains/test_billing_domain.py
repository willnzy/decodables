"""
Billing Domain Tests - UserCredits aggregate and credit logic.

@module tests.domains.test_billing_domain
@version 2.0.0

Tests cover:
- Credits value object (immutable operations)
- UserCredits aggregate creation and operations
- Credit deduction priority (monthly first, then permanent)
- Transaction recording
- Edge cases (zero balance, negative amounts)
- BillingService (with mocked repository)
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock

from domains.billing import (
    UserCredits,
    CreditTransaction,
    Credits,
    CreditBucket,
    TransactionType,
    InsufficientCreditsException,
    InvalidAmountException,
    BillingService,
)


# ==========================================
# Credits Value Object Tests
# ==========================================

class TestCreditsValueObject:
    """Tests for Credits immutable value object."""

    def test_create_credits(self):
        """Test creating Credits value object."""
        credits = Credits(monthly=500, permanent=100)

        assert credits.monthly == 500
        assert credits.permanent == 100
        assert credits.total == 600

    def test_create_credits_defaults(self):
        """Test creating Credits with default values."""
        credits = Credits()

        assert credits.monthly == 0
        assert credits.permanent == 0
        assert credits.total == 0

    def test_credits_negative_raises_error(self):
        """Test that negative credits raise ValueError."""
        with pytest.raises(ValueError):
            Credits(monthly=-10, permanent=0)

        with pytest.raises(ValueError):
            Credits(monthly=0, permanent=-10)

    def test_has_enough_true(self):
        """Test has_enough returns True when sufficient."""
        credits = Credits(monthly=100, permanent=50)

        assert credits.has_enough(100) is True
        assert credits.has_enough(150) is True
        assert credits.has_enough(0) is True

    def test_has_enough_false(self):
        """Test has_enough returns False when insufficient."""
        credits = Credits(monthly=50, permanent=30)

        assert credits.has_enough(81) is False
        assert credits.has_enough(100) is False

    def test_deduct_from_monthly_only(self):
        """Test deduction when monthly has enough."""
        credits = Credits(monthly=100, permanent=50)
        new_credits = credits.deduct(30)

        # Immutable - original unchanged
        assert credits.monthly == 100

        # New object has deducted amount
        assert new_credits.monthly == 70
        assert new_credits.permanent == 50

    def test_deduct_from_both_buckets(self):
        """Test deduction spanning both buckets."""
        credits = Credits(monthly=30, permanent=100)
        new_credits = credits.deduct(50)

        # Should use all monthly (30) + some permanent (20)
        assert new_credits.monthly == 0
        assert new_credits.permanent == 80

    def test_deduct_from_permanent_only(self):
        """Test deduction when monthly is zero."""
        credits = Credits(monthly=0, permanent=100)
        new_credits = credits.deduct(25)

        assert new_credits.monthly == 0
        assert new_credits.permanent == 75

    def test_deduct_insufficient_raises_error(self):
        """Test deduction with insufficient balance raises error."""
        credits = Credits(monthly=10, permanent=10)

        with pytest.raises(ValueError) as exc_info:
            credits.deduct(50)

        assert "Insufficient" in str(exc_info.value)

    def test_deduct_zero_returns_same(self):
        """Test deducting zero returns equivalent credits."""
        credits = Credits(monthly=100, permanent=50)
        new_credits = credits.deduct(0)

        assert new_credits.monthly == 100
        assert new_credits.permanent == 50

    def test_add_to_monthly(self):
        """Test adding to monthly bucket."""
        credits = Credits(monthly=100, permanent=50)
        new_credits = credits.add(500, CreditBucket.MONTHLY)

        assert new_credits.monthly == 600
        assert new_credits.permanent == 50

    def test_add_to_permanent(self):
        """Test adding to permanent bucket."""
        credits = Credits(monthly=100, permanent=50)
        new_credits = credits.add(100, CreditBucket.PERMANENT)

        assert new_credits.monthly == 100
        assert new_credits.permanent == 150

    def test_add_zero_returns_same(self):
        """Test adding zero returns equivalent credits."""
        credits = Credits(monthly=100, permanent=50)
        new_credits = credits.add(0, CreditBucket.MONTHLY)

        assert new_credits.monthly == 100
        assert new_credits.permanent == 50

    def test_reset_monthly(self):
        """Test resetting monthly credits."""
        credits = Credits(monthly=50, permanent=100)
        new_credits = credits.reset_monthly(500)

        assert new_credits.monthly == 500
        assert new_credits.permanent == 100


# ==========================================
# UserCredits Aggregate Tests
# ==========================================

class TestUserCreditsAggregate:
    """Tests for UserCredits aggregate root."""

    def test_create_user_credits(self):
        """Test creating UserCredits aggregate via factory."""
        user_credits = UserCredits.create(
            user_id="user_123",
            monthly=500,
            permanent=100,
            tier="starter",
        )

        assert user_credits.user_id == "user_123"
        assert user_credits.monthly_credits == 500
        assert user_credits.permanent_credits == 100
        assert user_credits.total_credits == 600
        assert user_credits.tier == "starter"

    def test_create_with_defaults(self):
        """Test creating UserCredits with default values."""
        user_credits = UserCredits.create(user_id="user_456")

        assert user_credits.monthly_credits == 0
        assert user_credits.permanent_credits == 0
        assert user_credits.tier == "free"
        assert user_credits.total_credits == 0

    def test_can_afford_true(self):
        """Test can_afford returns True when balance sufficient."""
        user_credits = UserCredits.create(
            user_id="user_123",
            monthly=100,
            permanent=50,
        )

        assert user_credits.can_afford(100) is True
        assert user_credits.can_afford(150) is True
        assert user_credits.can_afford(1) is True

    def test_can_afford_false(self):
        """Test can_afford returns False when balance insufficient."""
        user_credits = UserCredits.create(
            user_id="user_123",
            monthly=50,
            permanent=30,
        )

        assert user_credits.can_afford(81) is False
        assert user_credits.can_afford(100) is False

    def test_deduct_from_monthly_first(self):
        """
        Test: Credit deduction uses monthly credits first.

        Business Rule: 先扣月度积分 -> 再扣永久积分
        """
        user_credits = UserCredits.create(
            user_id="user_123",
            monthly=100,
            permanent=50,
        )

        tx = user_credits.deduct(30, TransactionType.GENERATION, "Test deduction")

        # Monthly should be reduced, permanent unchanged
        assert user_credits.monthly_credits == 70
        assert user_credits.permanent_credits == 50
        assert tx.amount == -30
        assert tx.bucket == CreditBucket.MONTHLY

    def test_deduct_from_permanent_when_monthly_depleted(self):
        """Test deduction uses permanent when monthly is zero."""
        user_credits = UserCredits.create(
            user_id="user_123",
            monthly=0,
            permanent=100,
        )

        tx = user_credits.deduct(25, TransactionType.GENERATION, "Test deduction")

        assert user_credits.monthly_credits == 0
        assert user_credits.permanent_credits == 75
        assert tx.bucket == CreditBucket.PERMANENT

    def test_deduct_mixed_sources(self):
        """Test deduction that spans both credit types."""
        user_credits = UserCredits.create(
            user_id="user_123",
            monthly=30,
            permanent=100,
        )

        # Deduct 50: should use 30 monthly + 20 permanent
        tx = user_credits.deduct(50, TransactionType.OCR, "Mixed deduction")

        assert user_credits.monthly_credits == 0
        assert user_credits.permanent_credits == 80
        assert tx.amount == -50

    def test_deduct_insufficient_raises_error(self):
        """Test deduction with insufficient balance raises InsufficientCreditsException."""
        user_credits = UserCredits.create(
            user_id="user_123",
            monthly=10,
            permanent=10,
        )

        with pytest.raises(InsufficientCreditsException) as exc_info:
            user_credits.deduct(50, TransactionType.GENERATION, "Should fail")

        # Check exception contains useful info
        assert exc_info.value.required == 50
        assert exc_info.value.available == 20

    def test_deduct_negative_amount_raises_error(self):
        """Test deduction with negative amount raises InvalidAmountException."""
        user_credits = UserCredits.create(
            user_id="user_123",
            monthly=100,
        )

        with pytest.raises(InvalidAmountException):
            user_credits.deduct(-10, TransactionType.GENERATION, "Negative amount")

    def test_deduct_zero_raises_error(self):
        """Test deduction with zero amount raises InvalidAmountException."""
        user_credits = UserCredits.create(
            user_id="user_123",
            monthly=100,
        )

        with pytest.raises(InvalidAmountException):
            user_credits.deduct(0, TransactionType.GENERATION, "Zero amount")

    def test_add_credits_monthly(self):
        """Test adding monthly credits."""
        user_credits = UserCredits.create(
            user_id="user_123",
            monthly=100,
        )

        tx = user_credits.add(
            amount=500,
            bucket=CreditBucket.MONTHLY,
            tx_type=TransactionType.SUB_GRANT,
            description="subscription_renewal"
        )

        assert user_credits.monthly_credits == 600
        assert tx.amount == 500
        assert tx.bucket == CreditBucket.MONTHLY

    def test_add_credits_permanent(self):
        """Test adding permanent credits."""
        user_credits = UserCredits.create(
            user_id="user_123",
            permanent=50,
        )

        tx = user_credits.add(
            amount=100,
            bucket=CreditBucket.PERMANENT,
            tx_type=TransactionType.TOPUP_PURCHASE,
            description="purchase"
        )

        assert user_credits.permanent_credits == 150
        assert tx.amount == 100
        assert tx.bucket == CreditBucket.PERMANENT

    def test_add_negative_raises_error(self):
        """Test adding negative amount raises InvalidAmountException."""
        user_credits = UserCredits.create(user_id="user_123", monthly=100)

        with pytest.raises(InvalidAmountException):
            user_credits.add(-10, CreditBucket.MONTHLY, TransactionType.ADMIN_GRANT)

    def test_reset_monthly_credits(self):
        """Test resetting monthly credits (subscription renewal)."""
        user_credits = UserCredits.create(
            user_id="user_123",
            monthly=50,
            tier="starter",
        )

        user_credits.reset_monthly(500)  # Starter gets 500

        assert user_credits.monthly_credits == 500

    def test_pending_transactions_tracked(self):
        """Test that transactions are tracked in pending list."""
        user_credits = UserCredits.create(
            user_id="user_123",
            monthly=100,
            permanent=50,
        )

        user_credits.deduct(10, TransactionType.GENERATION)
        user_credits.add(20, CreditBucket.PERMANENT, TransactionType.ADMIN_GRANT)

        assert len(user_credits.pending_transactions) == 2

    def test_clear_pending_transactions(self):
        """Test clearing pending transactions after save."""
        user_credits = UserCredits.create(
            user_id="user_123",
            monthly=100,
        )

        user_credits.deduct(10, TransactionType.GENERATION)
        assert len(user_credits.pending_transactions) == 1

        user_credits.clear_pending_transactions()
        assert len(user_credits.pending_transactions) == 0

    def test_get_tier_monthly_allowance(self):
        """Test getting monthly allowance by tier."""
        free_user = UserCredits.create(user_id="u1", tier="free")
        starter_user = UserCredits.create(user_id="u2", tier="starter")
        pro_user = UserCredits.create(user_id="u3", tier="pro")

        assert free_user.get_tier_monthly_allowance() == 0
        assert starter_user.get_tier_monthly_allowance() == 500
        assert pro_user.get_tier_monthly_allowance() == 1000


# ==========================================
# CreditTransaction Tests
# ==========================================

class TestCreditTransaction:
    """Tests for CreditTransaction entity."""

    def test_create_deduction_transaction(self):
        """Test creating a deduction transaction."""
        tx = CreditTransaction(
            amount=-5,
            bucket=CreditBucket.MONTHLY,
            tx_type=TransactionType.GENERATION,
            description="Generated 1 image",
            balance_after=Credits(monthly=95, permanent=50),
        )

        assert tx.amount == -5
        assert tx.bucket == CreditBucket.MONTHLY
        assert tx.tx_type == TransactionType.GENERATION
        assert tx.balance_after.total == 145

    def test_create_addition_transaction(self):
        """Test creating an addition transaction."""
        tx = CreditTransaction(
            amount=100,
            bucket=CreditBucket.PERMANENT,
            tx_type=TransactionType.TOPUP_PURCHASE,
            description="Credit purchase",
        )

        assert tx.amount == 100
        assert tx.bucket == CreditBucket.PERMANENT
        assert tx.tx_type == TransactionType.TOPUP_PURCHASE

    def test_transaction_has_timestamp(self):
        """Test transaction has created_at timestamp."""
        tx = CreditTransaction(
            amount=-10,
            bucket=CreditBucket.MONTHLY,
            tx_type=TransactionType.GENERATION,
        )

        assert tx.created_at is not None
        assert isinstance(tx.created_at, datetime)

    def test_transaction_with_idempotency_key(self):
        """Test transaction with idempotency key."""
        tx = CreditTransaction(
            amount=-5,
            bucket=CreditBucket.MONTHLY,
            tx_type=TransactionType.GENERATION,
            idempotency_key="unique_key_123",
        )

        assert tx.idempotency_key == "unique_key_123"


# ==========================================
# TransactionType Enum Tests
# ==========================================

class TestTransactionType:
    """Tests for TransactionType enum."""

    def test_deduction_types(self):
        """Test deduction transaction types."""
        assert TransactionType.GENERATION.value == "generation"
        assert TransactionType.OCR.value == "ocr"
        assert TransactionType.MARKET_PURCHASE.value == "market_purchase"

    def test_addition_types(self):
        """Test addition transaction types."""
        assert TransactionType.SIGNUP_BONUS.value == "signup_bonus"
        assert TransactionType.SUB_GRANT.value == "sub_grant"
        assert TransactionType.TOPUP_PURCHASE.value == "topup_purchase"
        assert TransactionType.REFUND.value == "refund"
        assert TransactionType.ADMIN_GRANT.value == "admin_grant"


# ==========================================
# BillingService Tests (with mocked repository)
# ==========================================

class TestBillingService:
    """Tests for BillingService domain service."""

    @pytest.fixture
    def mock_repository(self):
        """Create mock credit repository."""
        repo = MagicMock()
        repo.get_by_user_id = AsyncMock()
        repo.save = AsyncMock()
        repo.deduct_atomic = AsyncMock()
        repo.add_atomic = AsyncMock()
        repo.get_transaction_history = AsyncMock(return_value=[])
        repo.get_transaction_count = AsyncMock(return_value=0)
        repo.reset_monthly_credits = AsyncMock()
        return repo

    @pytest.fixture
    def billing_service(self, mock_repository):
        """Create billing service with mock repository."""
        return BillingService(repository=mock_repository)

    @pytest.mark.asyncio
    async def test_get_user_credits(self, billing_service, mock_repository):
        """Test getting user credits."""
        mock_repository.get_by_user_id.return_value = UserCredits.create(
            user_id="user_123",
            monthly=500,
            permanent=100,
        )

        credits = await billing_service.get_user_credits("user_123")

        assert credits.total_credits == 600
        mock_repository.get_by_user_id.assert_called_once_with("user_123")

    @pytest.mark.asyncio
    async def test_get_user_credits_not_found(self, billing_service, mock_repository):
        """Test getting credits for non-existent user."""
        mock_repository.get_by_user_id.return_value = None

        credits = await billing_service.get_user_credits("nonexistent")

        assert credits is None

    @pytest.mark.asyncio
    async def test_check_can_afford_true(self, billing_service, mock_repository):
        """Test affordability check - sufficient."""
        mock_repository.get_by_user_id.return_value = UserCredits.create(
            user_id="user_123",
            monthly=50,
            permanent=50,
        )

        result = await billing_service.check_can_afford("user_123", 100)

        assert result is True

    @pytest.mark.asyncio
    async def test_check_can_afford_false(self, billing_service, mock_repository):
        """Test affordability check - insufficient."""
        mock_repository.get_by_user_id.return_value = UserCredits.create(
            user_id="user_123",
            monthly=50,
            permanent=50,
        )

        result = await billing_service.check_can_afford("user_123", 101)

        assert result is False

    @pytest.mark.asyncio
    async def test_check_can_afford_user_not_found(self, billing_service, mock_repository):
        """Test affordability check for non-existent user."""
        mock_repository.get_by_user_id.return_value = None

        result = await billing_service.check_can_afford("nonexistent", 10)

        assert result is False

    @pytest.mark.asyncio
    async def test_get_operation_cost_known(self, billing_service):
        """Test getting cost for known operations."""
        # Uses emergency fallback since no config_service
        assert await billing_service.get_operation_cost("image_generation") == 5
        assert await billing_service.get_operation_cost("text_generation") == 0
        assert await billing_service.get_operation_cost("smart_scan") == 10

    @pytest.mark.asyncio
    async def test_get_operation_cost_unknown_raises(self, billing_service):
        """Test getting cost for unknown operation raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            await billing_service.get_operation_cost("unknown_operation")

        assert "Unknown operation" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_deduct_for_operation(self, billing_service, mock_repository):
        """Test deducting credits for a specific operation."""
        mock_tx = CreditTransaction(
            amount=-5,
            bucket=CreditBucket.MONTHLY,
            tx_type=TransactionType.GENERATION,
        )
        mock_repository.deduct_atomic.return_value = mock_tx

        result = await billing_service.deduct_for_operation(
            user_id="user_123",
            operation="image_generation",
            description="Test image",
        )

        assert result.amount == -5
        mock_repository.deduct_atomic.assert_called_once()
        call_args = mock_repository.deduct_atomic.call_args
        assert call_args.kwargs["user_id"] == "user_123"
        assert call_args.kwargs["amount"] == 5  # image_generation cost

    @pytest.mark.asyncio
    async def test_grant_signup_bonus(self, billing_service, mock_repository):
        """
        Test granting signup bonus credits.

        Business Rule: 新用户注册赠送 50 永久积分
        """
        mock_tx = CreditTransaction(
            amount=50,
            bucket=CreditBucket.PERMANENT,
            tx_type=TransactionType.SIGNUP_BONUS,
        )
        mock_repository.add_atomic.return_value = mock_tx

        result = await billing_service.grant_signup_bonus("new_user_123")

        assert result.amount == 50
        assert result.bucket == CreditBucket.PERMANENT
        mock_repository.add_atomic.assert_called_once()
        call_args = mock_repository.add_atomic.call_args
        assert call_args.kwargs["amount"] == 50

    @pytest.mark.asyncio
    async def test_process_subscription_renewal(self, billing_service, mock_repository):
        """
        Test processing subscription renewal.

        Business Rules:
        - Starter: 500 credits/month
        - Pro: 1000 credits/month
        """
        mock_repository.reset_monthly_credits.return_value = UserCredits.create(
            user_id="user_123",
            monthly=500,
            tier="starter",
        )

        result = await billing_service.process_subscription_renewal("user_123", "starter")

        assert result.monthly_credits == 500
        mock_repository.reset_monthly_credits.assert_called_once_with("user_123", 500)

    @pytest.mark.asyncio
    async def test_get_transaction_history(self, billing_service, mock_repository):
        """Test getting transaction history."""
        mock_repository.get_transaction_history.return_value = [
            CreditTransaction(
                amount=-5,
                bucket=CreditBucket.MONTHLY,
                tx_type=TransactionType.GENERATION,
            ),
        ]

        result = await billing_service.get_transaction_history("user_123", limit=10)

        assert len(result) == 1
        mock_repository.get_transaction_history.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_transaction_count(self, billing_service, mock_repository):
        """Test getting transaction count for pagination."""
        mock_repository.get_transaction_count.return_value = 150

        result = await billing_service.get_transaction_count("user_123")

        assert result == 150
        mock_repository.get_transaction_count.assert_called_once()
        call_args = mock_repository.get_transaction_count.call_args
        assert call_args.kwargs["user_id"] == "user_123"

    @pytest.mark.asyncio
    async def test_get_transaction_count_with_filters(self, billing_service, mock_repository):
        """Test getting transaction count with filters."""
        mock_repository.get_transaction_count.return_value = 25

        result = await billing_service.get_transaction_count(
            user_id="user_123",
            tx_type=TransactionType.GENERATION,
        )

        assert result == 25
        mock_repository.get_transaction_count.assert_called_once()
        call_args = mock_repository.get_transaction_count.call_args
        assert call_args.kwargs["tx_type"] == TransactionType.GENERATION


# ==========================================
# Integration-style Tests (Business Rules)
# ==========================================

class TestBillingBusinessRules:
    """Tests verifying business rules are correctly implemented."""

    def test_deduction_priority_monthly_first(self):
        """
        Business Rule: 先扣月度积分 -> 再扣永久积分

        Given: User has 100 monthly + 50 permanent
        When: Deduct 80 credits
        Then: Monthly becomes 20, permanent stays 50
        """
        user_credits = UserCredits.create(
            user_id="test_user",
            monthly=100,
            permanent=50,
        )

        user_credits.deduct(80, TransactionType.GENERATION)

        assert user_credits.monthly_credits == 20
        assert user_credits.permanent_credits == 50

    def test_deduction_uses_both_when_needed(self):
        """
        Business Rule: Monthly exhausted, then use permanent

        Given: User has 30 monthly + 100 permanent
        When: Deduct 50 credits
        Then: Monthly becomes 0, permanent becomes 80
        """
        user_credits = UserCredits.create(
            user_id="test_user",
            monthly=30,
            permanent=100,
        )

        user_credits.deduct(50, TransactionType.GENERATION)

        assert user_credits.monthly_credits == 0
        assert user_credits.permanent_credits == 80

    def test_tier_allowances(self):
        """
        Business Rule: Tier monthly allowances
        - Free: 0
        - Starter: 500
        - Pro: 1000
        """
        service = BillingService(repository=MagicMock())

        assert service.TIER_ALLOWANCES["free"] == 0
        assert service.TIER_ALLOWANCES["starter"] == 500
        assert service.TIER_ALLOWANCES["pro"] == 1000

    def test_signup_bonus(self):
        """
        Business Rule: 新用户注册赠送 50 永久积分
        """
        service = BillingService(repository=MagicMock())

        assert service.SIGNUP_BONUS == 50

    @pytest.mark.asyncio
    async def test_operation_costs(self):
        """
        Business Rule: AI operation costs
        - Image generation: 5 credits
        - Text generation: 0 credits (free)
        - Smart scan: 10 credits
        """
        service = BillingService(repository=MagicMock())

        assert await service.get_operation_cost("image_generation") == 5
        assert await service.get_operation_cost("text_generation") == 0
        assert await service.get_operation_cost("smart_scan") == 10
