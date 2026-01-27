"""
Unit tests for SubscriptionService.

@module tests.domains.subscriptions.test_subscription_service
@version 3.28

Tests for subscription business logic with mocked repositories.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from domains.subscriptions.subscription_service import SubscriptionService
from domains.subscriptions.exceptions import (
    UserNotFoundException,
    UserCodeMissingException,
    UserCodeMismatchException,
    UserEmailMismatchException,
    NoStripeCustomerException,
    PaymentNotFoundException,
    PaymentOwnershipException,
    PaymentStatusException,
    AlreadyRefundedException,
    InvalidRefundAmountException,
    RefundFailedException,
    SubscriptionNotFoundException,
    SubscriptionOwnershipException,
    SubscriptionStatusException,
    AlreadyCancelScheduledException,
    InvalidDowngradePathException,
    NoActiveSubscriptionException,
)


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def mock_users_repo():
    """Mock users repository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_payment_repo():
    """Mock payment repository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_admin_repo():
    """Mock admin repository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def service(mock_users_repo, mock_payment_repo, mock_admin_repo):
    """Create SubscriptionService with mocked dependencies."""
    return SubscriptionService(
        mock_users_repo,
        mock_payment_repo,
        mock_admin_repo
    )


# ==========================================
# _verify_user_identity Tests
# ==========================================

class TestVerifyUserIdentity:
    """Tests for user identity verification."""

    @pytest.mark.asyncio
    async def test_verify_user_identity_success(self, service, mock_users_repo):
        """Successful verification returns user profile."""
        mock_users_repo.get_profile.return_value = {
            "user_id": "user-123",
            "user_code": "ABC123",
            "email": "test@example.com",
            "tier": "t3"
        }

        result = await service._verify_user_identity("user-123", "ABC123")

        assert result["user_id"] == "user-123"
        assert result["user_code"] == "ABC123"
        mock_users_repo.get_profile.assert_awaited_once_with("user-123")

    @pytest.mark.asyncio
    async def test_verify_user_identity_user_not_found(self, service, mock_users_repo):
        """User not found raises UserNotFoundException."""
        mock_users_repo.get_profile.return_value = None

        with pytest.raises(UserNotFoundException):
            await service._verify_user_identity("user-123", "ABC123")

    @pytest.mark.asyncio
    async def test_verify_user_identity_no_user_code(self, service, mock_users_repo):
        """User without user_code raises UserCodeMissingException."""
        mock_users_repo.get_profile.return_value = {
            "user_id": "user-123",
            "user_code": None
        }

        with pytest.raises(UserCodeMissingException):
            await service._verify_user_identity("user-123", "ABC123")

    @pytest.mark.asyncio
    async def test_verify_user_identity_code_mismatch(self, service, mock_users_repo):
        """User code mismatch raises UserCodeMismatchException."""
        mock_users_repo.get_profile.return_value = {
            "user_id": "user-123",
            "user_code": "ABC123"
        }

        with pytest.raises(UserCodeMismatchException):
            await service._verify_user_identity("user-123", "WRONG")

    @pytest.mark.asyncio
    async def test_verify_user_identity_email_mismatch(self, service, mock_users_repo):
        """Email mismatch raises UserEmailMismatchException."""
        mock_users_repo.get_profile.return_value = {
            "user_id": "user-123",
            "user_code": "ABC123",
            "email": "test@example.com"
        }

        with pytest.raises(UserEmailMismatchException):
            await service._verify_user_identity("user-123", "ABC123", "wrong@example.com")


# ==========================================
# process_refund Tests
# ==========================================

class TestProcessRefund:
    """Tests for refund processing."""

    @pytest.mark.asyncio
    @patch('domains.subscriptions.subscription_service.get_payment_intent_details')
    @patch('domains.subscriptions.subscription_service.create_refund')
    async def test_process_refund_full_success(
        self,
        mock_create_refund,
        mock_get_pi,
        service,
        mock_users_repo,
        mock_payment_repo,
        mock_admin_repo
    ):
        """Full refund processes successfully."""
        # Mock user
        mock_users_repo.get_profile.return_value = {
            "user_id": "user-123",
            "user_code": "ABC123",
            "stripe_customer_id": "cus_test"
        }

        # Mock payment intent
        mock_pi = MagicMock()
        mock_pi.customer = "cus_test"
        mock_pi.status = "succeeded"
        mock_pi.amount = 1000
        mock_pi.amount_received = 1000
        mock_get_pi.return_value = mock_pi

        # Mock refund
        mock_refund = MagicMock()
        mock_refund.id = "re_test123"
        mock_refund.amount = 1000
        mock_refund.currency = "usd"
        mock_create_refund.return_value = {
            "success": True,
            "refund": mock_refund
        }

        result = await service.process_refund(
            user_id="user-123",
            user_code="ABC123",
            payment_intent_id="pi_test",
            amount_cents=None,  # Full refund
            reason="Customer request",
            admin_id="admin-1"
        )

        assert result["status"] == "refunded"
        assert result["refund_id"] == "re_test123"
        assert result["amount"] == 1000
        assert result["currency"] == "USD"

        # P0-010: Database record is created by webhook handler, not here
        # mock_payment_repo.create should NOT be called in process_refund
        # mock_admin_repo.admin_log_operation is also NOT called here
        # Both will be handled by the charge.refunded webhook handler

    @pytest.mark.asyncio
    @patch('domains.subscriptions.subscription_service.get_payment_intent_details')
    async def test_process_refund_no_stripe_customer(
        self,
        mock_get_pi,
        service,
        mock_users_repo
    ):
        """Refund fails if user has no Stripe customer ID."""
        mock_users_repo.get_profile.return_value = {
            "user_id": "user-123",
            "user_code": "ABC123",
            "stripe_customer_id": None
        }

        with pytest.raises(NoStripeCustomerException):
            await service.process_refund(
                user_id="user-123",
                user_code="ABC123",
                payment_intent_id="pi_test",
                amount_cents=None,
                reason="Test",
                admin_id="admin-1"
            )

    @pytest.mark.asyncio
    @patch('domains.subscriptions.subscription_service.get_payment_intent_details')
    async def test_process_refund_payment_not_found(
        self,
        mock_get_pi,
        service,
        mock_users_repo
    ):
        """Refund fails if payment not found."""
        mock_users_repo.get_profile.return_value = {
            "user_id": "user-123",
            "user_code": "ABC123",
            "stripe_customer_id": "cus_test"
        }
        mock_get_pi.return_value = None

        with pytest.raises(PaymentNotFoundException):
            await service.process_refund(
                user_id="user-123",
                user_code="ABC123",
                payment_intent_id="pi_test",
                amount_cents=None,
                reason="Test",
                admin_id="admin-1"
            )

    @pytest.mark.asyncio
    @patch('domains.subscriptions.subscription_service.get_payment_intent_details')
    async def test_process_refund_wrong_customer(
        self,
        mock_get_pi,
        service,
        mock_users_repo
    ):
        """Refund fails if payment belongs to different customer."""
        mock_users_repo.get_profile.return_value = {
            "user_id": "user-123",
            "user_code": "ABC123",
            "stripe_customer_id": "cus_test"
        }

        mock_pi = MagicMock()
        mock_pi.customer = "cus_other"
        mock_get_pi.return_value = mock_pi

        with pytest.raises(PaymentOwnershipException):
            await service.process_refund(
                user_id="user-123",
                user_code="ABC123",
                payment_intent_id="pi_test",
                amount_cents=None,
                reason="Test",
                admin_id="admin-1"
            )

    @pytest.mark.asyncio
    @patch('domains.subscriptions.subscription_service.get_payment_intent_details')
    async def test_process_refund_invalid_status(
        self,
        mock_get_pi,
        service,
        mock_users_repo
    ):
        """Refund fails if payment not succeeded."""
        mock_users_repo.get_profile.return_value = {
            "user_id": "user-123",
            "user_code": "ABC123",
            "stripe_customer_id": "cus_test"
        }

        mock_pi = MagicMock()
        mock_pi.customer = "cus_test"
        mock_pi.status = "pending"
        mock_get_pi.return_value = mock_pi

        with pytest.raises(PaymentStatusException):
            await service.process_refund(
                user_id="user-123",
                user_code="ABC123",
                payment_intent_id="pi_test",
                amount_cents=None,
                reason="Test",
                admin_id="admin-1"
            )


# ==========================================
# cancel_user_subscription Tests
# ==========================================

class TestCancelSubscription:
    """Tests for subscription cancellation."""

    @pytest.mark.asyncio
    @patch('domains.subscriptions.subscription_service.get_subscription_details')
    @patch('domains.subscriptions.subscription_service.cancel_subscription')
    async def test_cancel_immediate_success(
        self,
        mock_cancel,
        mock_get_sub,
        service,
        mock_users_repo,
        mock_payment_repo,
        mock_admin_repo
    ):
        """Immediate cancellation succeeds."""
        mock_users_repo.get_profile.return_value = {
            "user_id": "user-123",
            "user_code": "ABC123",
            "stripe_customer_id": "cus_test"
        }

        mock_sub = MagicMock()
        mock_sub.id = "sub_test"
        mock_sub.customer = "cus_test"
        mock_sub.status = "active"
        mock_sub.cancel_at_period_end = False
        mock_sub.items.data = [MagicMock(price=MagicMock(id="price_starter_monthly"))]
        mock_get_sub.return_value = mock_sub

        mock_canceled_sub = MagicMock()
        mock_canceled_sub.id = "sub_test"
        mock_canceled_sub.cancel_at_period_end = True
        mock_canceled_sub.current_period_end = 1234567890
        mock_cancel.return_value = {"success": True, "subscription": mock_canceled_sub}

        result = await service.cancel_user_subscription(
            user_id="user-123",
            user_code="ABC123",
            subscription_id="sub_test",
            immediate=True,
            reason="Test cancel",
            admin_id="admin-1"
        )

        assert result["status"] == "canceled"
        assert result["subscription_id"] == "sub_test"

        mock_users_repo.update_subscription_tier.assert_awaited_once_with(
            "user-123", "t1", subscription_status="canceled"
        )

    @pytest.mark.asyncio
    @patch('domains.subscriptions.subscription_service.get_subscription_details')
    async def test_cancel_subscription_not_found(
        self,
        mock_get_sub,
        service,
        mock_users_repo
    ):
        """Cancel fails if subscription not found."""
        mock_users_repo.get_profile.return_value = {
            "user_id": "user-123",
            "user_code": "ABC123",
            "stripe_customer_id": "cus_test"
        }
        mock_get_sub.return_value = None

        with pytest.raises(SubscriptionNotFoundException):
            await service.cancel_user_subscription(
                user_id="user-123",
                user_code="ABC123",
                subscription_id="sub_test",
                immediate=True,
                reason="Test",
                admin_id="admin-1"
            )


# ==========================================
# downgrade_user_subscription Tests
# ==========================================

class TestDowngradeSubscription:
    """Tests for subscription downgrade."""

    @pytest.mark.asyncio
    @patch('domains.subscriptions.subscription_service.get_customer_subscriptions')
    @patch('domains.subscriptions.subscription_service.cancel_subscription')
    async def test_downgrade_to_free_immediate_with_active_sub(
        self,
        mock_cancel,
        mock_get_subs,
        service,
        mock_users_repo,
        mock_payment_repo,
        mock_admin_repo
    ):
        """Downgrade to free (immediate) with active subscription."""
        mock_users_repo.get_profile.return_value = {
            "user_id": "user-123",
            "user_code": "ABC123",
            "email": "test@example.com",
            "tier": "t3",
            "stripe_customer_id": "cus_test"
        }

        mock_sub = MagicMock()
        mock_sub.id = "sub_test"
        mock_sub.status = "active"
        mock_get_subs.return_value = [mock_sub]

        mock_canceled = MagicMock()
        mock_canceled.id = "sub_test"
        mock_cancel.return_value = {"success": True, "subscription": mock_canceled}

        result = await service.downgrade_user_subscription(
            user_id="user-123",
            user_code="ABC123",
            user_email="test@example.com",
            target_tier="t1",
            immediate=True,
            reason="Test downgrade",
            admin_id="admin-1"
        )

        assert result["status"] == "downgraded"
        assert result["from_tier"] == "t3"
        assert result["to_tier"] == "t1"
        assert result["subscription_id"] == "sub_test"

        mock_users_repo.update_subscription_tier.assert_awaited_once()
        mock_users_repo.update_monthly_credits.assert_awaited_once_with("user-123", 0)

    @pytest.mark.asyncio
    @patch('domains.subscriptions.subscription_service.get_customer_subscriptions')
    @patch('domains.subscriptions.subscription_service.modify_subscription')
    async def test_downgrade_pro_to_starter(
        self,
        mock_modify,
        mock_get_subs,
        service,
        mock_users_repo,
        mock_payment_repo,
        mock_admin_repo
    ):
        """Downgrade from Pro to Starter."""
        mock_users_repo.get_profile.return_value = {
            "user_id": "user-123",
            "user_code": "ABC123",
            "email": "test@example.com",
            "tier": "t3",
            "stripe_customer_id": "cus_test"
        }

        mock_sub = MagicMock()
        mock_sub.id = "sub_test"
        mock_sub.status = "active"
        mock_sub.items.data = [MagicMock(id="si_test")]
        mock_get_subs.return_value = [mock_sub]

        mock_updated = MagicMock()
        mock_updated.id = "sub_test"
        mock_updated.current_period_end = 1234567890
        mock_modify.return_value = mock_updated

        with patch.dict('os.environ', {'STRIPE_STARTER_MONTHLY_PRICE_ID': 'price_starter'}):
            result = await service.downgrade_user_subscription(
                user_id="user-123",
                user_code="ABC123",
                user_email="test@example.com",
                target_tier="t2",
                immediate=True,
                reason="Test downgrade",
                admin_id="admin-1"
            )

        assert result["status"] == "downgraded"
        assert result["from_tier"] == "t3"
        assert result["to_tier"] == "t2"

        mock_users_repo.update_subscription_tier.assert_awaited_once_with(
            "user-123", "t2", subscription_status="active"
        )
        mock_users_repo.update_monthly_credits.assert_awaited_once_with("user-123", 100)  # Updated from 200 to 100

    @pytest.mark.asyncio
    async def test_downgrade_invalid_direction(self, service, mock_users_repo):
        """Cannot downgrade from lower to higher tier."""
        mock_users_repo.get_profile.return_value = {
            "user_id": "user-123",
            "user_code": "ABC123",
            "email": "test@example.com",
            "tier": "t2"
        }

        with pytest.raises(InvalidDowngradePathException):
            await service.downgrade_user_subscription(
                user_id="user-123",
                user_code="ABC123",
                user_email="test@example.com",
                target_tier="t3",
                immediate=True,
                reason="Test",
                admin_id="admin-1"
            )


# ==========================================
# Additional Refund Tests
# ==========================================

class TestProcessRefundAdditional:
    """Additional tests for refund edge cases."""

    @pytest.mark.asyncio
    @patch('domains.subscriptions.subscription_service.get_payment_intent_details')
    async def test_process_refund_already_fully_refunded(
        self,
        mock_get_pi,
        service,
        mock_users_repo
    ):
        """Refund fails if already fully refunded."""
        mock_users_repo.get_profile.return_value = {
            "user_id": "user-123",
            "user_code": "ABC123",
            "stripe_customer_id": "cus_test"
        }

        mock_pi = MagicMock()
        mock_pi.customer = "cus_test"
        mock_pi.status = "succeeded"
        mock_pi.amount_received = 0  # Already refunded
        mock_get_pi.return_value = mock_pi

        with pytest.raises(AlreadyRefundedException):
            await service.process_refund(
                user_id="user-123",
                user_code="ABC123",
                payment_intent_id="pi_test",
                amount_cents=None,
                reason="Test",
                admin_id="admin-1"
            )

    @pytest.mark.asyncio
    @patch('domains.subscriptions.subscription_service.get_payment_intent_details')
    async def test_process_refund_amount_exceeds_refundable(
        self,
        mock_get_pi,
        service,
        mock_users_repo
    ):
        """Partial refund fails if amount exceeds refundable."""
        mock_users_repo.get_profile.return_value = {
            "user_id": "user-123",
            "user_code": "ABC123",
            "stripe_customer_id": "cus_test"
        }

        mock_pi = MagicMock()
        mock_pi.customer = "cus_test"
        mock_pi.status = "succeeded"
        mock_pi.amount = 1000
        mock_pi.amount_received = 1000
        mock_get_pi.return_value = mock_pi

        with pytest.raises(InvalidRefundAmountException):
            await service.process_refund(
                user_id="user-123",
                user_code="ABC123",
                payment_intent_id="pi_test",
                amount_cents=2000,  # More than refundable
                reason="Test",
                admin_id="admin-1"
            )

    @pytest.mark.asyncio
    @patch('domains.subscriptions.subscription_service.get_payment_intent_details')
    @patch('domains.subscriptions.subscription_service.create_refund')
    async def test_process_refund_stripe_error(
        self,
        mock_create_refund,
        mock_get_pi,
        service,
        mock_users_repo
    ):
        """Refund fails if Stripe API returns error."""
        mock_users_repo.get_profile.return_value = {
            "user_id": "user-123",
            "user_code": "ABC123",
            "stripe_customer_id": "cus_test"
        }

        mock_pi = MagicMock()
        mock_pi.customer = "cus_test"
        mock_pi.status = "succeeded"
        mock_pi.amount = 1000
        mock_pi.amount_received = 1000
        mock_get_pi.return_value = mock_pi

        mock_create_refund.return_value = {"success": False, "error": "Stripe error"}

        with pytest.raises(RefundFailedException):
            await service.process_refund(
                user_id="user-123",
                user_code="ABC123",
                payment_intent_id="pi_test",
                amount_cents=None,
                reason="Test",
                admin_id="admin-1"
            )


# ==========================================
# Additional Cancel Tests
# ==========================================

class TestCancelSubscriptionAdditional:
    """Additional tests for cancellation edge cases."""

    @pytest.mark.asyncio
    @patch('domains.subscriptions.subscription_service.get_subscription_details')
    async def test_cancel_wrong_customer(
        self,
        mock_get_sub,
        service,
        mock_users_repo
    ):
        """Cancel fails if subscription belongs to different customer."""
        mock_users_repo.get_profile.return_value = {
            "user_id": "user-123",
            "user_code": "ABC123",
            "stripe_customer_id": "cus_test"
        }

        mock_sub = MagicMock()
        mock_sub.customer = "cus_other"
        mock_get_sub.return_value = mock_sub

        with pytest.raises(SubscriptionOwnershipException):
            await service.cancel_user_subscription(
                user_id="user-123",
                user_code="ABC123",
                subscription_id="sub_test",
                immediate=True,
                reason="Test",
                admin_id="admin-1"
            )

    @pytest.mark.asyncio
    @patch('domains.subscriptions.subscription_service.get_subscription_details')
    async def test_cancel_invalid_status(
        self,
        mock_get_sub,
        service,
        mock_users_repo
    ):
        """Cancel fails if subscription has invalid status."""
        mock_users_repo.get_profile.return_value = {
            "user_id": "user-123",
            "user_code": "ABC123",
            "stripe_customer_id": "cus_test"
        }

        mock_sub = MagicMock()
        mock_sub.customer = "cus_test"
        mock_sub.status = "canceled"  # Already canceled
        mock_get_sub.return_value = mock_sub

        with pytest.raises(SubscriptionStatusException):
            await service.cancel_user_subscription(
                user_id="user-123",
                user_code="ABC123",
                subscription_id="sub_test",
                immediate=True,
                reason="Test",
                admin_id="admin-1"
            )

    @pytest.mark.asyncio
    @patch('domains.subscriptions.subscription_service.get_subscription_details')
    async def test_cancel_already_scheduled(
        self,
        mock_get_sub,
        service,
        mock_users_repo
    ):
        """Cancel (scheduled) fails if already scheduled."""
        mock_users_repo.get_profile.return_value = {
            "user_id": "user-123",
            "user_code": "ABC123",
            "stripe_customer_id": "cus_test"
        }

        mock_sub = MagicMock()
        mock_sub.customer = "cus_test"
        mock_sub.status = "active"
        mock_sub.cancel_at_period_end = True  # Already scheduled
        mock_get_sub.return_value = mock_sub

        with pytest.raises(AlreadyCancelScheduledException):
            await service.cancel_user_subscription(
                user_id="user-123",
                user_code="ABC123",
                subscription_id="sub_test",
                immediate=False,
                reason="Test",
                admin_id="admin-1"
            )

    @pytest.mark.asyncio
    @patch('domains.subscriptions.subscription_service.get_subscription_details')
    @patch('domains.subscriptions.subscription_service.cancel_subscription')
    async def test_cancel_scheduled_success(
        self,
        mock_cancel,
        mock_get_sub,
        service,
        mock_users_repo,
        mock_payment_repo,
        mock_admin_repo
    ):
        """Scheduled cancellation succeeds."""
        mock_users_repo.get_profile.return_value = {
            "user_id": "user-123",
            "user_code": "ABC123",
            "stripe_customer_id": "cus_test"
        }

        mock_sub = MagicMock()
        mock_sub.id = "sub_test"
        mock_sub.customer = "cus_test"
        mock_sub.status = "active"
        mock_sub.cancel_at_period_end = False
        mock_sub.items.data = [MagicMock(price=MagicMock(id="price_pro_monthly"))]
        mock_get_sub.return_value = mock_sub

        mock_canceled_sub = MagicMock()
        mock_canceled_sub.id = "sub_test"
        mock_canceled_sub.cancel_at_period_end = True
        mock_canceled_sub.current_period_end = 1234567890
        mock_cancel.return_value = {"success": True, "subscription": mock_canceled_sub}

        result = await service.cancel_user_subscription(
            user_id="user-123",
            user_code="ABC123",
            subscription_id="sub_test",
            immediate=False,
            reason="Test cancel",
            admin_id="admin-1"
        )

        assert result["status"] == "cancel_scheduled"
        assert result["subscription_id"] == "sub_test"

        # Should NOT update tier immediately
        mock_users_repo.update_subscription_tier.assert_not_called()


# ==========================================
# Additional Downgrade Tests
# ==========================================

class TestDowngradeSubscriptionAdditional:
    """Additional tests for downgrade edge cases."""

    @pytest.mark.asyncio
    async def test_downgrade_to_free_no_customer_no_sub(
        self,
        service,
        mock_users_repo,
        mock_payment_repo
    ):
        """Downgrade to free when no Stripe customer (direct to free)."""
        mock_users_repo.get_profile.return_value = {
            "user_id": "user-123",
            "user_code": "ABC123",
            "email": "test@example.com",
            "tier": "t2",
            "stripe_customer_id": None
        }

        result = await service.downgrade_user_subscription(
            user_id="user-123",
            user_code="ABC123",
            user_email="test@example.com",
            target_tier="t1",
            immediate=True,
            reason="Test downgrade",
            admin_id="admin-1"
        )

        assert result["status"] == "downgraded"
        assert result["from_tier"] == "t2"
        assert result["to_tier"] == "t1"
        assert "subscription_id" not in result

        mock_users_repo.update_subscription_tier.assert_awaited_once()

    @pytest.mark.asyncio
    @patch('domains.subscriptions.subscription_service.get_customer_subscriptions')
    async def test_downgrade_to_free_no_active_sub(
        self,
        mock_get_subs,
        service,
        mock_users_repo,
        mock_payment_repo
    ):
        """Downgrade to free with customer but no active subscription."""
        mock_users_repo.get_profile.return_value = {
            "user_id": "user-123",
            "user_code": "ABC123",
            "email": "test@example.com",
            "tier": "t3",
            "stripe_customer_id": "cus_test"
        }

        mock_get_subs.return_value = []  # No active subscriptions

        result = await service.downgrade_user_subscription(
            user_id="user-123",
            user_code="ABC123",
            user_email="test@example.com",
            target_tier="t1",
            immediate=True,
            reason="Test downgrade",
            admin_id="admin-1"
        )

        assert result["status"] == "downgraded"
        assert result["from_tier"] == "t3"
        assert result["to_tier"] == "t1"

    @pytest.mark.asyncio
    @patch('domains.subscriptions.subscription_service.get_customer_subscriptions')
    @patch('domains.subscriptions.subscription_service.cancel_subscription')
    async def test_downgrade_to_free_scheduled(
        self,
        mock_cancel,
        mock_get_subs,
        service,
        mock_users_repo,
        mock_payment_repo
    ):
        """Downgrade to free (scheduled) succeeds."""
        mock_users_repo.get_profile.return_value = {
            "user_id": "user-123",
            "user_code": "ABC123",
            "email": "test@example.com",
            "tier": "t3",
            "stripe_customer_id": "cus_test"
        }

        mock_sub = MagicMock()
        mock_sub.id = "sub_test"
        mock_sub.status = "active"
        mock_get_subs.return_value = [mock_sub]

        mock_canceled = MagicMock()
        mock_canceled.current_period_end = 1234567890
        mock_cancel.return_value = {"success": True, "subscription": mock_canceled}

        result = await service.downgrade_user_subscription(
            user_id="user-123",
            user_code="ABC123",
            user_email="test@example.com",
            target_tier="t1",
            immediate=False,
            reason="Test downgrade",
            admin_id="admin-1"
        )

        assert result["status"] == "downgrade_scheduled"
        assert result["to_tier"] == "t1"

    @pytest.mark.asyncio
    @patch('domains.subscriptions.subscription_service.get_customer_subscriptions')
    async def test_downgrade_pro_to_starter_no_customer(
        self,
        mock_get_subs,
        service,
        mock_users_repo
    ):
        """Downgrade Pro→Starter fails if no Stripe customer."""
        mock_users_repo.get_profile.return_value = {
            "user_id": "user-123",
            "user_code": "ABC123",
            "email": "test@example.com",
            "tier": "t3",
            "stripe_customer_id": None
        }

        with pytest.raises(NoStripeCustomerException):
            await service.downgrade_user_subscription(
                user_id="user-123",
                user_code="ABC123",
                user_email="test@example.com",
                target_tier="t2",
                immediate=True,
                reason="Test",
                admin_id="admin-1"
            )

    @pytest.mark.asyncio
    @patch('domains.subscriptions.subscription_service.get_customer_subscriptions')
    async def test_downgrade_pro_to_starter_no_active_sub(
        self,
        mock_get_subs,
        service,
        mock_users_repo
    ):
        """Downgrade Pro→Starter fails if no active subscription."""
        mock_users_repo.get_profile.return_value = {
            "user_id": "user-123",
            "user_code": "ABC123",
            "email": "test@example.com",
            "tier": "t3",
            "stripe_customer_id": "cus_test"
        }

        mock_get_subs.return_value = []

        with pytest.raises(NoActiveSubscriptionException):
            await service.downgrade_user_subscription(
                user_id="user-123",
                user_code="ABC123",
                user_email="test@example.com",
                target_tier="t2",
                immediate=True,
                reason="Test",
                admin_id="admin-1"
            )

    @pytest.mark.asyncio
    @patch('domains.subscriptions.subscription_service.get_customer_subscriptions')
    @patch('domains.subscriptions.subscription_service.modify_subscription')
    async def test_downgrade_pro_to_starter_scheduled(
        self,
        mock_modify,
        mock_get_subs,
        service,
        mock_users_repo,
        mock_payment_repo,
        mock_admin_repo
    ):
        """Downgrade Pro→Starter (scheduled) succeeds."""
        mock_users_repo.get_profile.return_value = {
            "user_id": "user-123",
            "user_code": "ABC123",
            "email": "test@example.com",
            "tier": "t3",
            "stripe_customer_id": "cus_test"
        }

        mock_sub = MagicMock()
        mock_sub.id = "sub_test"
        mock_sub.status = "active"
        mock_sub.items.data = [MagicMock(id="si_test")]
        mock_get_subs.return_value = [mock_sub]

        mock_updated = MagicMock()
        mock_updated.id = "sub_test"
        mock_updated.current_period_end = 1234567890
        mock_modify.return_value = mock_updated

        with patch.dict('os.environ', {'STRIPE_STARTER_MONTHLY_PRICE_ID': 'price_starter'}):
            result = await service.downgrade_user_subscription(
                user_id="user-123",
                user_code="ABC123",
                user_email="test@example.com",
                target_tier="t2",
                immediate=False,
                reason="Test downgrade",
                admin_id="admin-1"
            )

        assert result["status"] == "downgrade_scheduled"
        assert result["to_tier"] == "t2"

        # Should NOT update tier immediately
        mock_users_repo.update_subscription_tier.assert_not_called()


# ==========================================
# Helper Method Tests
# ==========================================

class TestHelperMethods:
    """Tests for helper methods."""

    def test_extract_plan_name_starter(self, service):
        """Extract tier code for Starter (t2)."""
        mock_sub = MagicMock()
        mock_sub.items.data = [MagicMock(price=MagicMock(id="price_starter_monthly"))]

        result = service._extract_plan_name(mock_sub)
        assert result == "t2"

    def test_extract_plan_name_pro(self, service):
        """Extract tier code for Pro (t3)."""
        mock_sub = MagicMock()
        mock_sub.items.data = [MagicMock(price=MagicMock(id="price_pro_monthly"))]

        result = service._extract_plan_name(mock_sub)
        assert result == "t3"

    def test_extract_plan_name_unknown(self, service):
        """Extract plan name for unknown."""
        mock_sub = MagicMock()
        mock_sub.items.data = [MagicMock(price=MagicMock(id="price_custom"))]

        result = service._extract_plan_name(mock_sub)
        assert result == "Unknown"

    def test_extract_plan_name_no_items(self, service):
        """Extract plan name when no items."""
        mock_sub = MagicMock()
        mock_sub.items.data = []

        result = service._extract_plan_name(mock_sub)
        assert result == "Unknown"
