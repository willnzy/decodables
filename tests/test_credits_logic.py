"""
Tests for Credits System Logic (PRD v3.2)
Tests the three key rules:
1. Monthly credits reset each month for Starter/Pro
2. Permanent credits never expire (from purchase/sale)
3. Deduct monthly credits first, then permanent credits

Refactored to use repository pattern and UserCredits aggregate.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

from domains.billing.aggregates.user_credits import UserCredits, CreditTransaction
from domains.billing.value_objects import Credits, CreditBucket, TransactionType
from domains.billing.exceptions import InsufficientCreditsException, InvalidAmountException
from infrastructure.repositories.credit_repository import SupabaseCreditRepository


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client for repository with AsyncMock for .execute()."""
    client = MagicMock()

    # Create query builder that returns itself for chaining (synchronous)
    mock_query = MagicMock()
    mock_query.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.update.return_value = mock_query
    mock_query.insert.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.single.return_value = mock_query
    mock_query.rpc.return_value = mock_query

    # Only .execute() should be async
    mock_query.execute = AsyncMock()

    # RPC and table methods
    client.table.return_value = mock_query
    client.rpc.return_value = mock_query

    return client


@pytest.fixture
def credit_repo(mock_supabase_client):
    """Credit repository with mocked client."""
    return SupabaseCreditRepository(client=mock_supabase_client)


# ==========================================
# Test Rule 1: Monthly Credits Reset
# ==========================================

class TestMonthlyCreditsReset:
    """Test Rule 1: Monthly credits reset each month"""

    @pytest.mark.asyncio
    async def test_refresh_monthly_credits_resets_monthly_only(self, credit_repo, mock_supabase_client):
        """Monthly credits reset, permanent credits preserved"""
        # Arrange: User has 100 monthly + 200 permanent
        user_id = "user_123"

        # Mock database response - AsyncMock returns a MagicMock with data attribute
        mock_query = mock_supabase_client.table.return_value
        mock_query.execute.return_value = MagicMock(
            data={
                "id": user_id,
                "credits_monthly": 500,  # Reset to tier allowance
                "credits_permanent": 200,  # Unchanged
                "tier": "starter"
            }
        )

        # Act: Reset monthly credits
        result = await credit_repo.reset_monthly_credits(user_id, 500)

        # Assert: Monthly reset to 500, permanent preserved
        assert result.user_id == user_id
        assert result.monthly_credits == 500
        assert result.permanent_credits == 200
        assert result.total_credits == 700

    @pytest.mark.asyncio
    async def test_check_reset_after_30_days(self, credit_repo, mock_supabase_client):
        """Monthly credits reset if credits_reset_at is over 30 days old"""
        # Arrange: User last reset 31 days ago
        user_id = "user_456"
        old_reset_time = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()

        # Mock user profile with old reset time
        with patch('infrastructure.repositories.user_repository.SupabaseUserRepository') as mock_user_repo_class:
            mock_user_repo = AsyncMock()
            mock_user_repo_class.return_value = mock_user_repo
            mock_user_repo.get_profile.return_value = {
                "id": user_id,
                "tier": "t3",
                "credits_reset_at": old_reset_time
            }

            # Mock credit refresh
            mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
                data={"credits_monthly": 1000}
            )

            # Act: Check and reset if needed
            await credit_repo.check_and_reset_monthly_credits_if_needed(user_id)

            # Assert: Credits were refreshed
            assert mock_supabase_client.table.return_value.update.called
            update_call = mock_supabase_client.table.return_value.update.call_args[0][0]
            assert update_call["credits_monthly"] == 1000

    @pytest.mark.asyncio
    async def test_no_reset_before_30_days(self, credit_repo, mock_supabase_client):
        """Monthly credits don't reset if credits_reset_at is less than 30 days old"""
        # Arrange: User last reset 15 days ago
        user_id = "user_789"
        recent_reset_time = (datetime.now(timezone.utc) - timedelta(days=15)).isoformat()

        # Mock user profile with recent reset time
        with patch('infrastructure.repositories.user_repository.SupabaseUserRepository') as mock_user_repo_class:
            mock_user_repo = AsyncMock()
            mock_user_repo_class.return_value = mock_user_repo
            mock_user_repo.get_profile.return_value = {
                "id": user_id,
                "tier": "starter",
                "credits_reset_at": recent_reset_time
            }

            # Act: Check and reset if needed
            await credit_repo.check_and_reset_monthly_credits_if_needed(user_id)

            # Assert: No credit update occurred
            assert not mock_supabase_client.table.return_value.update.called


# ==========================================
# Test Rule 2: Permanent Credits Never Expire
# ==========================================

class TestPermanentCreditsNeverExpire:
    """Test Rule 2: Permanent credits never expire"""

    @pytest.mark.asyncio
    async def test_add_permanent_credits(self, credit_repo, mock_supabase_client):
        """Adding permanent credits increases permanent balance"""
        # Arrange
        user_id = "user_abc"

        # Mock RPC response - use correct field names matching repository
        mock_supabase_client.rpc.return_value.execute.return_value = MagicMock(
            data={
                "success": True,
                "balance_monthly": 100,
                "balance_permanent": 350,  # 300 + 50
            }
        )

        # Act: Add 50 permanent credits
        tx = await credit_repo.add_atomic(
            user_id=user_id,
            amount=50,
            bucket=CreditBucket.PERMANENT,
            tx_type=TransactionType.PURCHASE,
            description="Credit purchase"
        )

        # Assert: Permanent credits increased
        assert tx.amount == 50
        assert tx.bucket == CreditBucket.PERMANENT
        assert tx.balance_after.permanent == 350
        assert tx.balance_after.monthly == 100

    @pytest.mark.asyncio
    async def test_permanent_credits_preserved_on_reset(self, credit_repo, mock_supabase_client):
        """Permanent credits are preserved when monthly resets"""
        # Arrange: User has 50 monthly + 300 permanent
        user_id = "user_xyz"

        # Mock reset response
        mock_supabase_client.table.return_value.update.return_value.eq.return_value.select.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "id": user_id,
                "credits_monthly": 1000,  # Reset to Pro allowance
                "credits_permanent": 300,  # Unchanged
                "tier": "pro"
            }
        )

        # Act: Reset monthly credits
        result = await credit_repo.reset_monthly_credits(user_id, 1000)

        # Assert: Permanent credits unchanged
        assert result.permanent_credits == 300
        assert result.monthly_credits == 1000


# ==========================================
# Test Rule 3: Deduction Priority
# ==========================================

class TestDeductionPriority:
    """Test Rule 3: Deduct monthly credits first, then permanent credits"""

    @pytest.mark.asyncio
    async def test_deduct_monthly_first(self, credit_repo, mock_supabase_client):
        """Deduct from monthly credits first when sufficient"""
        # Arrange: User has 500 monthly + 200 permanent
        user_id = "user_001"

        # Mock RPC response showing deduction from monthly
        # Repository uses 'bucket' field to determine deduction source
        mock_supabase_client.rpc.return_value.execute.return_value = MagicMock(
            data={
                "success": True,
                "bucket": "monthly",  # Indicates deducted from monthly
                "balance_monthly": 450,
                "balance_permanent": 200,
            }
        )

        # Act: Deduct 50 credits
        tx = await credit_repo.deduct_atomic(
            user_id=user_id,
            amount=50,
            tx_type=TransactionType.AI_GENERATION,
            description="AI generation"
        )

        # Assert: Deducted from monthly only
        assert tx.bucket == CreditBucket.MONTHLY
        assert tx.balance_after.monthly == 450
        assert tx.balance_after.permanent == 200

    @pytest.mark.asyncio
    async def test_deduct_monthly_then_permanent(self, credit_repo, mock_supabase_client):
        """Deduct from monthly first, then permanent when monthly insufficient"""
        # Arrange: User has 30 monthly + 200 permanent, needs 50
        user_id = "user_002"

        # Mock RPC response showing deduction from both (monthly exhausted)
        # When monthly is exhausted, bucket shows 'monthly' since deduction started there
        mock_supabase_client.rpc.return_value.execute.return_value = MagicMock(
            data={
                "success": True,
                "bucket": "monthly",  # Started from monthly
                "balance_monthly": 0,
                "balance_permanent": 180,
            }
        )

        # Act: Deduct 50 credits
        tx = await credit_repo.deduct_atomic(
            user_id=user_id,
            amount=50,
            tx_type=TransactionType.AI_GENERATION,
            description="AI generation"
        )

        # Assert: Monthly exhausted, permanent reduced
        assert tx.balance_after.monthly == 0
        assert tx.balance_after.permanent == 180

    @pytest.mark.asyncio
    async def test_deduct_all_from_permanent_when_monthly_zero(self, credit_repo, mock_supabase_client):
        """Deduct all from permanent when monthly credits are zero"""
        # Arrange: User has 0 monthly + 200 permanent
        user_id = "user_003"

        # Mock RPC response showing deduction from permanent only
        mock_supabase_client.rpc.return_value.execute.return_value = MagicMock(
            data={
                "success": True,
                "bucket": "permanent",  # Deducted from permanent
                "balance_monthly": 0,
                "balance_permanent": 150,
            }
        )

        # Act: Deduct 50 credits
        tx = await credit_repo.deduct_atomic(
            user_id=user_id,
            amount=50,
            tx_type=TransactionType.AI_GENERATION,
            description="AI generation"
        )

        # Assert: Deducted from permanent only
        assert tx.bucket == CreditBucket.PERMANENT
        assert tx.balance_after.monthly == 0
        assert tx.balance_after.permanent == 150

    @pytest.mark.asyncio
    async def test_insufficient_credits_error(self, credit_repo, mock_supabase_client):
        """Return error when total credits insufficient"""
        # Arrange: User has 30 total credits, needs 50
        user_id = "user_004"

        # Mock RPC response with error - must match repository's expected fields
        mock_supabase_client.rpc.return_value.execute.return_value = MagicMock(
            data={
                "success": False,
                "error_message": "Insufficient credits",
                "balance_monthly": 10,
                "balance_permanent": 20,
            }
        )

        # Act & Assert: Raises exception
        with pytest.raises(InsufficientCreditsException) as exc_info:
            await credit_repo.deduct_atomic(
                user_id=user_id,
                amount=50,
                tx_type=TransactionType.AI_GENERATION,
                description="AI generation"
            )

        # Exception stores values in context dict
        assert exc_info.value.context["required"] == 50
        assert exc_info.value.context["available"] == 30


# ==========================================
# Test Integration Scenarios
# ==========================================

class TestIntegrationScenarios:
    """Integration tests for real-world scenarios"""

    @pytest.mark.asyncio
    async def test_complete_cycle_scenario(self):
        """Complete credit usage cycle"""
        # Arrange: Create UserCredits aggregate for Starter user
        user_credits = UserCredits.create(
            user_id="user_cycle",
            monthly=500,  # Starter monthly allowance
            permanent=50,  # Signup bonus
            tier="t2"
        )

        # Scenario 1: Use 100 credits (from monthly)
        tx1 = user_credits.deduct(100, TransactionType.AI_GENERATION, "First generation")
        assert user_credits.monthly_credits == 400
        assert user_credits.permanent_credits == 50
        assert tx1.amount == -100
        assert tx1.bucket == CreditBucket.MONTHLY

        # Scenario 2: Use 350 credits (from monthly)
        tx2 = user_credits.deduct(350, TransactionType.AI_GENERATION, "Second generation")
        assert user_credits.monthly_credits == 50
        assert user_credits.permanent_credits == 50
        assert tx2.bucket == CreditBucket.MONTHLY

        # Scenario 3: Use 70 credits (50 from monthly + 20 from permanent)
        tx3 = user_credits.deduct(70, TransactionType.AI_GENERATION, "Third generation")
        assert user_credits.monthly_credits == 0
        assert user_credits.permanent_credits == 30
        assert tx3.bucket == CreditBucket.MONTHLY  # Started from monthly

        # Scenario 4: Purchase 100 permanent credits
        tx4 = user_credits.add(100, CreditBucket.PERMANENT, TransactionType.PURCHASE, "Credit purchase")
        assert user_credits.monthly_credits == 0
        assert user_credits.permanent_credits == 130
        assert tx4.amount == 100

        # Scenario 5: Monthly reset (Starter gets 500)
        user_credits.reset_monthly(500, TransactionType.SUBSCRIPTION_GRANT)
        assert user_credits.monthly_credits == 500
        assert user_credits.permanent_credits == 130  # Preserved!
        assert user_credits.total_credits == 630

        # Scenario 6: Try to use 700 credits (insufficient)
        with pytest.raises(InsufficientCreditsException):
            user_credits.deduct(700, TransactionType.AI_GENERATION, "Exceeds balance")

        # Assert: 5 successful transactions recorded
        assert len(user_credits.pending_transactions) == 5


# ==========================================
# Test Aggregate Business Rules
# ==========================================

class TestUserCreditsAggregate:
    """Test UserCredits aggregate business logic"""

    def test_deduction_priority_in_aggregate(self):
        """Test deduction priority rule in UserCredits aggregate"""
        # Arrange: 100 monthly + 200 permanent
        credits = UserCredits.create("user_rule", monthly=100, permanent=200, tier="t2")

        # Deduct 150 (should use all monthly + 50 permanent)
        credits.deduct(150, TransactionType.AI_GENERATION)

        assert credits.monthly_credits == 0
        assert credits.permanent_credits == 150

    def test_cannot_deduct_negative_amount(self):
        """Test that negative deductions are rejected"""
        credits = UserCredits.create("user_neg", monthly=100, permanent=100)

        with pytest.raises(InvalidAmountException):
            credits.deduct(-10, TransactionType.AI_GENERATION)

    def test_monthly_reset_preserves_permanent(self):
        """Test reset_monthly preserves permanent credits"""
        credits = UserCredits.create("user_reset", monthly=50, permanent=300, tier="t3")

        credits.reset_monthly(1000)

        assert credits.monthly_credits == 1000
        assert credits.permanent_credits == 300

    def test_tier_allowance_mapping(self):
        """Test tier monthly allowance calculation"""
        free_user = UserCredits.create("free", tier="t1")
        assert free_user.get_tier_monthly_allowance() == 0

        starter_user = UserCredits.create("starter", tier="t2")
        assert starter_user.get_tier_monthly_allowance() == 500

        pro_user = UserCredits.create("pro", tier="t3")
        assert pro_user.get_tier_monthly_allowance() == 1000
