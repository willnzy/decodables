"""Test admin/subscriptions API endpoints.

Tests for admin subscription management endpoints.
v3.25: Added comprehensive tests including security validation.
"""
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import app


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


# ==========================================
# Basic Endpoint Tests (Auth)
# ==========================================

class TestSubscriptionsEndpointsAuth:
    """Basic tests for subscriptions API authentication requirements."""

    def test_refund_requires_auth(self, client):
        """Refund endpoint requires authentication."""
        response = client.post(
            "/api/v2/admin/subscriptions/refund",
            json={
                "user_id": "test-user",
                "user_code": "ABC123",
                "payment_intent_id": "pi_test",
                "reason": "Test reason"
            }
        )
        assert response.status_code in [401, 403]

    def test_cancel_subscription_requires_auth(self, client):
        """Cancel subscription endpoint requires authentication."""
        response = client.post(
            "/api/v2/admin/subscriptions/subscription/cancel",
            json={
                "user_id": "test-user",
                "user_code": "ABC123",
                "subscription_id": "sub_test",
                "reason": "Test reason"
            }
        )
        assert response.status_code in [401, 403]

    def test_downgrade_subscription_requires_auth(self, client):
        """Downgrade subscription endpoint requires authentication."""
        response = client.post(
            "/api/v2/admin/subscriptions/subscription/downgrade",
            json={
                "user_id": "test-user",
                "user_code": "ABC123",
                "user_email": "test@example.com",
                "target_tier": "free",
                "reason": "Test reason"
            }
        )
        assert response.status_code in [401, 403]


# ==========================================
# Constants Tests
# ==========================================

class TestSubscriptionsConstants:
    """Tests for subscriptions constants."""

    def test_valid_target_tiers(self):
        """Valid target tiers are defined."""
        from api.admin.subscriptions import VALID_TARGET_TIERS

        assert "free" in VALID_TARGET_TIERS
        assert "starter" in VALID_TARGET_TIERS
        assert "pro" not in VALID_TARGET_TIERS  # Can't downgrade TO pro
        assert "invalid" not in VALID_TARGET_TIERS


# ==========================================
# Request Model Validation Tests
# ==========================================

class TestAdminRefundRequestValidation:
    """Tests for AdminRefundRequest model validation."""

    def test_valid_refund_request(self):
        """Valid refund request is accepted."""
        from api.admin.subscriptions import AdminRefundRequest

        req = AdminRefundRequest(
            user_id="user-123",
            user_code="ABC123",
            payment_intent_id="pi_test123",
            amount_cents=1000,
            reason="Customer requested refund"
        )
        assert req.user_id == "user-123"
        assert req.amount_cents == 1000

    def test_refund_full_refund_allowed(self):
        """Full refund (None amount) is allowed."""
        from api.admin.subscriptions import AdminRefundRequest

        req = AdminRefundRequest(
            user_id="user-123",
            user_code="ABC123",
            payment_intent_id="pi_test123",
            reason="Full refund"
        )
        assert req.amount_cents is None

    def test_refund_user_id_length_validation(self):
        """User ID must be between 1-100 characters."""
        from api.admin.subscriptions import AdminRefundRequest

        # Invalid: empty user_id
        with pytest.raises(ValidationError):
            AdminRefundRequest(
                user_id="",
                user_code="ABC123",
                payment_intent_id="pi_test",
                reason="Test"
            )

        # Invalid: too long
        with pytest.raises(ValidationError):
            AdminRefundRequest(
                user_id="a" * 101,
                user_code="ABC123",
                payment_intent_id="pi_test",
                reason="Test"
            )

    def test_refund_reason_length_validation(self):
        """Reason must be between 1-1000 characters."""
        from api.admin.subscriptions import AdminRefundRequest

        # Valid reason
        AdminRefundRequest(
            user_id="user-123",
            user_code="ABC123",
            payment_intent_id="pi_test",
            reason="a" * 1000
        )

        # Invalid: empty reason
        with pytest.raises(ValidationError):
            AdminRefundRequest(
                user_id="user-123",
                user_code="ABC123",
                payment_intent_id="pi_test",
                reason=""
            )

        # Invalid: too long
        with pytest.raises(ValidationError):
            AdminRefundRequest(
                user_id="user-123",
                user_code="ABC123",
                payment_intent_id="pi_test",
                reason="a" * 1001
            )

    def test_refund_amount_validation(self):
        """Amount cents must be positive and within limit."""
        from api.admin.subscriptions import AdminRefundRequest

        # Valid amounts
        AdminRefundRequest(
            user_id="user-123",
            user_code="ABC123",
            payment_intent_id="pi_test",
            amount_cents=1,
            reason="Test"
        )
        AdminRefundRequest(
            user_id="user-123",
            user_code="ABC123",
            payment_intent_id="pi_test",
            amount_cents=100000000,  # $1M
            reason="Test"
        )

        # Invalid: zero amount
        with pytest.raises(ValidationError):
            AdminRefundRequest(
                user_id="user-123",
                user_code="ABC123",
                payment_intent_id="pi_test",
                amount_cents=0,
                reason="Test"
            )

        # Invalid: negative amount
        with pytest.raises(ValidationError):
            AdminRefundRequest(
                user_id="user-123",
                user_code="ABC123",
                payment_intent_id="pi_test",
                amount_cents=-100,
                reason="Test"
            )


class TestAdminCancelSubscriptionRequestValidation:
    """Tests for AdminCancelSubscriptionRequest model validation."""

    def test_valid_cancel_request(self):
        """Valid cancel request is accepted."""
        from api.admin.subscriptions import AdminCancelSubscriptionRequest

        req = AdminCancelSubscriptionRequest(
            user_id="user-123",
            user_code="ABC123",
            subscription_id="sub_test123",
            immediate=True,
            reason="Customer requested cancellation"
        )
        assert req.user_id == "user-123"
        assert req.immediate is True

    def test_cancel_default_immediate(self):
        """Default immediate is False."""
        from api.admin.subscriptions import AdminCancelSubscriptionRequest

        req = AdminCancelSubscriptionRequest(
            user_id="user-123",
            user_code="ABC123",
            subscription_id="sub_test",
            reason="Test reason"
        )
        assert req.immediate is False

    def test_cancel_field_length_validation(self):
        """Field length limits are enforced."""
        from api.admin.subscriptions import AdminCancelSubscriptionRequest

        # Invalid: empty subscription_id
        with pytest.raises(ValidationError):
            AdminCancelSubscriptionRequest(
                user_id="user-123",
                user_code="ABC123",
                subscription_id="",
                reason="Test"
            )

        # Invalid: reason too long
        with pytest.raises(ValidationError):
            AdminCancelSubscriptionRequest(
                user_id="user-123",
                user_code="ABC123",
                subscription_id="sub_test",
                reason="a" * 1001
            )


class TestAdminDowngradeRequestValidation:
    """Tests for AdminDowngradeRequest model validation."""

    def test_valid_downgrade_request(self):
        """Valid downgrade request is accepted."""
        from api.admin.subscriptions import AdminDowngradeRequest

        req = AdminDowngradeRequest(
            user_id="user-123",
            user_code="ABC123",
            user_email="test@example.com",
            target_tier="free",
            immediate=False,
            reason="Customer requested downgrade"
        )
        assert req.user_id == "user-123"
        assert req.target_tier == "free"

    def test_downgrade_target_tier_validation(self):
        """Target tier must be valid."""
        from api.admin.subscriptions import AdminDowngradeRequest

        # Valid target tiers
        for tier in ["free", "starter", "FREE", "Starter"]:
            req = AdminDowngradeRequest(
                user_id="user-123",
                user_code="ABC123",
                user_email="test@example.com",
                target_tier=tier,
                reason="Test"
            )
            assert req.target_tier in ["free", "starter"]

        # Invalid target tier
        with pytest.raises(ValidationError) as exc_info:
            AdminDowngradeRequest(
                user_id="user-123",
                user_code="ABC123",
                user_email="test@example.com",
                target_tier="pro",
                reason="Test"
            )
        assert "Invalid target_tier" in str(exc_info.value)

    def test_downgrade_target_tier_normalized(self):
        """Target tier is normalized to lowercase."""
        from api.admin.subscriptions import AdminDowngradeRequest

        req = AdminDowngradeRequest(
            user_id="user-123",
            user_code="ABC123",
            user_email="test@example.com",
            target_tier="STARTER",
            reason="Test"
        )
        assert req.target_tier == "starter"

    def test_downgrade_email_length_validation(self):
        """Email must be within length limits."""
        from api.admin.subscriptions import AdminDowngradeRequest

        # Valid email
        AdminDowngradeRequest(
            user_id="user-123",
            user_code="ABC123",
            user_email="a" * 240 + "@example.com",  # 252 chars
            target_tier="free",
            reason="Test"
        )

        # Invalid: empty email
        with pytest.raises(ValidationError):
            AdminDowngradeRequest(
                user_id="user-123",
                user_code="ABC123",
                user_email="",
                target_tier="free",
                reason="Test"
            )


# ==========================================
# Parameter Validation Tests
# ==========================================

class TestSubscriptionsParameterValidation:
    """Integration tests for parameter validation."""

    @pytest.mark.parametrize("target_tier", ["free", "starter"])
    def test_valid_target_tier_values(self, target_tier):
        """Valid target tier values are accepted."""
        from api.admin.subscriptions import VALID_TARGET_TIERS

        assert target_tier in VALID_TARGET_TIERS

    @pytest.mark.parametrize("target_tier", ["pro", "enterprise", "invalid", ""])
    def test_invalid_target_tier_values(self, target_tier):
        """Invalid target tier values are rejected."""
        from api.admin.subscriptions import VALID_TARGET_TIERS

        assert target_tier not in VALID_TARGET_TIERS
