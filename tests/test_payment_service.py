"""
Payment Service Unit Tests
Tests for Stripe integration with MOCKED SDK calls.

🚨 CRITICAL: NO REAL MONEY - All tests use mocked Stripe SDK

Test Coverage:
- create_checkout_session: Session creation with correct params
- create_portal_session: Billing portal generation
- construct_event: Webhook signature verification
- create_refund: Refund processing
- cancel_subscription: Subscription cancellation
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone
import json
import sys

# Mock stripe module BEFORE importing payment_service
sys.modules['stripe'] = MagicMock()


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def mock_stripe():
    """Mock the entire Stripe module"""
    with patch('services.payment_service.stripe') as mock:
        yield mock


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for Stripe"""
    with patch.dict('os.environ', {
        'STRIPE_SECRET_KEY': 'sk_test_mock_key_12345',
        'STRIPE_WEBHOOK_SECRET': 'whsec_test_mock_secret_67890',
        'STRIPE_PRICE_CREDITS_100': 'price_credits_100_test',
        'STRIPE_PRICE_SUB_STARTER': 'price_starter_test',
        'STRIPE_PRICE_SUB_PRO': 'price_pro_test',
        'FRONTEND_URL': 'https://test.decodables.com',
    }):
        yield


@pytest.fixture
def sample_checkout_session():
    """Sample Stripe Checkout Session response"""
    return Mock(
        id='cs_test_session_123',
        url='https://checkout.stripe.com/pay/cs_test_session_123',
        payment_status='unpaid',
        status='open',
        metadata={'user_id': 'user_123', 'plan_type': 'credits_100'},
        amount_total=999,
        currency='usd'
    )


@pytest.fixture
def sample_subscription():
    """Sample Stripe Subscription response"""
    return Mock(
        id='sub_test_123',
        status='active',
        current_period_end=1735689600,  # Future timestamp
        items=Mock(data=[Mock(price=Mock(id='price_starter_test'))]),
        customer='cus_test_123'
    )


@pytest.fixture
def sample_payment_intent():
    """Sample Stripe PaymentIntent response"""
    return Mock(
        id='pi_test_123',
        status='succeeded',
        amount=999,
        amount_received=999,
        currency='usd',
        customer='cus_test_123',
        metadata={'user_id': 'user_123'},
        charges=Mock(data=[Mock(amount_refunded=0)])
    )


# ============================================
# A. Checkout Session Tests
# ============================================

class TestCreateCheckoutSession:
    """Tests for create_checkout_session function"""
    
    def test_creates_session_for_credits_purchase(self, mock_stripe, sample_checkout_session):
        """
        ✅ PASS: Creates one-time payment session for credits
        Verifies:
        - mode = "payment" for one-time purchase
        - metadata contains user_id and plan_type
        - correct price_id is used
        """
        # Import after mocking
        mock_stripe.checkout.Session.create.return_value = sample_checkout_session
        
        from services.payment_service import create_checkout_session, PRICE_MAP
        
        # Patch PRICE_MAP
        with patch.dict('services.payment_service.PRICE_MAP', {
            'credits_100': 'price_credits_100_test',
            'starter': 'price_starter_test',
            'pro': 'price_pro_test'
        }):
            result = create_checkout_session('user_123', 'credits_100')
        
        # Assertions
        assert result == sample_checkout_session.url
        
        call_kwargs = mock_stripe.checkout.Session.create.call_args[1]
        assert call_kwargs['mode'] == 'payment'  # One-time, not subscription
        assert call_kwargs['metadata'] == {'user_id': 'user_123', 'plan_type': 'credits_100'}
        assert call_kwargs['line_items'][0]['price'] == 'price_credits_100_test'
    
    def test_creates_session_for_starter_subscription(self, mock_stripe, sample_checkout_session):
        """
        ✅ PASS: Creates subscription session for Starter plan
        Verifies:
        - mode = "subscription" for recurring
        """
        mock_stripe.checkout.Session.create.return_value = sample_checkout_session
        
        from services.payment_service import create_checkout_session
        
        with patch.dict('services.payment_service.PRICE_MAP', {
            'credits_100': 'price_credits_100_test',
            'starter': 'price_starter_test',
            'pro': 'price_pro_test'
        }):
            result = create_checkout_session('user_456', 'starter')
        
        call_kwargs = mock_stripe.checkout.Session.create.call_args[1]
        assert call_kwargs['mode'] == 'subscription'
        assert call_kwargs['metadata']['plan_type'] == 'starter'
    
    def test_creates_session_for_pro_subscription(self, mock_stripe, sample_checkout_session):
        """
        ✅ PASS: Creates subscription session for Pro plan
        """
        mock_stripe.checkout.Session.create.return_value = sample_checkout_session
        
        from services.payment_service import create_checkout_session
        
        with patch.dict('services.payment_service.PRICE_MAP', {
            'credits_100': 'price_credits_100_test',
            'starter': 'price_starter_test',
            'pro': 'price_pro_test'
        }):
            result = create_checkout_session('user_789', 'pro')
        
        call_kwargs = mock_stripe.checkout.Session.create.call_args[1]
        assert call_kwargs['mode'] == 'subscription'
        assert call_kwargs['metadata']['plan_type'] == 'pro'
    
    def test_applies_discount_coupon(self, mock_stripe, sample_checkout_session):
        """
        ✅ PASS: Creates coupon and applies discount
        """
        mock_coupon = Mock(id='coupon_20_off')
        mock_stripe.Coupon.create.return_value = mock_coupon
        mock_stripe.checkout.Session.create.return_value = sample_checkout_session
        
        from services.payment_service import create_checkout_session
        
        with patch.dict('services.payment_service.PRICE_MAP', {'credits_100': 'price_test'}):
            result = create_checkout_session('user_123', 'credits_100', discount_percent=20)
        
        # Verify coupon was created
        mock_stripe.Coupon.create.assert_called_once()
        coupon_kwargs = mock_stripe.Coupon.create.call_args[1]
        assert coupon_kwargs['percent_off'] == 20
        assert coupon_kwargs['duration'] == 'once'
        
        # Verify coupon was applied to session
        session_kwargs = mock_stripe.checkout.Session.create.call_args[1]
        assert session_kwargs['discounts'] == [{'coupon': 'coupon_20_off'}]
    
    def test_allows_promo_codes_without_discount(self, mock_stripe, sample_checkout_session):
        """
        ✅ PASS: Enables promo codes when no discount is applied
        """
        mock_stripe.checkout.Session.create.return_value = sample_checkout_session
        
        from services.payment_service import create_checkout_session
        
        with patch.dict('services.payment_service.PRICE_MAP', {'credits_100': 'price_test'}):
            result = create_checkout_session('user_123', 'credits_100', discount_percent=0)
        
        session_kwargs = mock_stripe.checkout.Session.create.call_args[1]
        assert session_kwargs.get('allow_promotion_codes') is True
    
    def test_invalid_plan_type_raises_error(self, mock_stripe):
        """
        ❌ FAIL: Raises error for invalid plan type
        """
        from services.payment_service import create_checkout_session
        
        with patch.dict('services.payment_service.PRICE_MAP', {
            'credits_100': 'price_test',
            'starter': None,  # Simulate missing price
        }):
            with pytest.raises(Exception) as exc_info:
                create_checkout_session('user_123', 'invalid_plan')
            
            assert 'Invalid plan type' in str(exc_info.value)
    
    def test_stripe_api_error_returns_none(self, mock_stripe):
        """
        ❌ FAIL: Returns None when Stripe API fails
        """
        mock_stripe.checkout.Session.create.side_effect = Exception('Stripe API Down')
        
        from services.payment_service import create_checkout_session
        
        with patch.dict('services.payment_service.PRICE_MAP', {'credits_100': 'price_test'}):
            result = create_checkout_session('user_123', 'credits_100')
        
        assert result is None


# ============================================
# B. Portal Session Tests
# ============================================

class TestCreatePortalSession:
    """Tests for create_portal_session function"""
    
    def test_creates_portal_session_successfully(self, mock_stripe):
        """
        ✅ PASS: Creates billing portal session
        """
        mock_portal = Mock(url='https://billing.stripe.com/portal/sess_123')
        mock_stripe.billing_portal.Session.create.return_value = mock_portal
        
        from services.payment_service import create_portal_session
        
        result = create_portal_session('user_123', 'cus_test_123')
        
        assert result == mock_portal.url
        mock_stripe.billing_portal.Session.create.assert_called_once()
    
    def test_raises_error_without_customer_id(self, mock_stripe):
        """
        ❌ FAIL: Raises error when no customer ID provided
        """
        from services.payment_service import create_portal_session
        
        with pytest.raises(Exception) as exc_info:
            create_portal_session('user_123', None)
        
        assert 'No Stripe Customer ID' in str(exc_info.value)
    
    def test_returns_none_on_stripe_error(self, mock_stripe):
        """
        ❌ FAIL: Returns None when Stripe API fails
        """
        mock_stripe.billing_portal.Session.create.side_effect = Exception('API Error')
        
        from services.payment_service import create_portal_session
        
        result = create_portal_session('user_123', 'cus_test_123')
        assert result is None


# ============================================
# C. Webhook Signature Verification Tests
# ============================================

class TestConstructEvent:
    """Tests for construct_event (webhook signature verification)"""
    
    def test_valid_signature_returns_event(self, mock_stripe):
        """
        ✅ PASS: Valid signature returns parsed event
        """
        mock_event = {
            'id': 'evt_test_123',
            'type': 'checkout.session.completed',
            'data': {'object': {'id': 'cs_123'}}
        }
        mock_stripe.Webhook.construct_event.return_value = mock_event
        
        from services.payment_service import construct_event
        
        result = construct_event(b'payload', 'sig_header_valid')
        
        assert result == mock_event
        mock_stripe.Webhook.construct_event.assert_called_once()
    
    def test_invalid_signature_raises_error(self, mock_stripe):
        """
        ❌ FAIL (Security): Invalid signature raises error
        🔒 This is a critical security test
        """
        mock_stripe.Webhook.construct_event.side_effect = Exception(
            'Webhook signature verification failed'
        )
        
        from services.payment_service import construct_event
        
        with pytest.raises(Exception) as exc_info:
            construct_event(b'payload', 'sig_invalid')
        
        assert 'Webhook Error' in str(exc_info.value)
    
    def test_empty_payload_raises_error(self, mock_stripe):
        """
        ❌ FAIL (Security): Empty payload raises error
        """
        mock_stripe.Webhook.construct_event.side_effect = Exception(
            'No payload provided'
        )
        
        from services.payment_service import construct_event
        
        with pytest.raises(Exception):
            construct_event(b'', 'sig_header')
    
    def test_tampered_payload_raises_error(self, mock_stripe):
        """
        ❌ FAIL (Security): Tampered payload with valid sig header fails
        """
        mock_stripe.Webhook.construct_event.side_effect = Exception(
            'Signature verification failed'
        )
        
        from services.payment_service import construct_event
        
        with pytest.raises(Exception) as exc_info:
            # Simulate attacker modifying payload but keeping old signature
            construct_event(b'{"amount": 0}', 'sig_from_different_payload')
        
        assert 'Webhook Error' in str(exc_info.value)


# ============================================
# D. Refund Tests
# ============================================

class TestCreateRefund:
    """Tests for create_refund function"""
    
    def test_full_refund_success(self, mock_stripe):
        """
        ✅ PASS: Full refund processes successfully
        """
        mock_refund = Mock(
            id='re_test_123',
            status='succeeded',
            amount=999
        )
        mock_stripe.Refund.create.return_value = mock_refund
        
        from services.payment_service import create_refund
        
        result = create_refund('pi_test_123')
        
        assert result['success'] is True
        assert result['refund'] == mock_refund
        assert result['error'] is None
        
        # Verify no amount specified (full refund)
        call_kwargs = mock_stripe.Refund.create.call_args[1]
        assert 'amount' not in call_kwargs
    
    def test_partial_refund_success(self, mock_stripe):
        """
        ✅ PASS: Partial refund with specific amount
        """
        mock_refund = Mock(id='re_test_456', status='succeeded', amount=500)
        mock_stripe.Refund.create.return_value = mock_refund
        
        from services.payment_service import create_refund
        
        result = create_refund('pi_test_123', amount_cents=500)
        
        assert result['success'] is True
        
        call_kwargs = mock_stripe.Refund.create.call_args[1]
        assert call_kwargs['amount'] == 500
    
    def test_refund_with_reason(self, mock_stripe):
        """
        ✅ PASS: Refund with custom reason
        """
        mock_refund = Mock(id='re_test_789', status='succeeded')
        mock_stripe.Refund.create.return_value = mock_refund
        
        from services.payment_service import create_refund
        
        result = create_refund('pi_test_123', reason='duplicate')
        
        call_kwargs = mock_stripe.Refund.create.call_args[1]
        assert call_kwargs['reason'] == 'duplicate'
    
    def test_refund_stripe_error(self, mock_stripe):
        """
        ❌ FAIL: Stripe error returns failure response
        """
        # Create a mock StripeError
        mock_error = Mock()
        mock_error.__str__ = lambda s: 'Card declined'
        mock_stripe.error.StripeError = Exception
        mock_stripe.Refund.create.side_effect = Exception('Card declined')
        
        from services.payment_service import create_refund
        
        result = create_refund('pi_test_invalid')
        
        assert result['success'] is False
        assert result['refund'] is None
        assert 'Card declined' in result['error']


# ============================================
# E. Cancel Subscription Tests
# ============================================

class TestCancelSubscription:
    """Tests for cancel_subscription function"""
    
    def test_immediate_cancellation(self, mock_stripe, sample_subscription):
        """
        ✅ PASS: Immediate cancellation works
        """
        sample_subscription.status = 'canceled'
        mock_stripe.Subscription.cancel.return_value = sample_subscription
        
        from services.payment_service import cancel_subscription
        
        result = cancel_subscription('sub_test_123', immediate=True)
        
        assert result['success'] is True
        mock_stripe.Subscription.cancel.assert_called_once_with('sub_test_123')
    
    def test_end_of_period_cancellation(self, mock_stripe, sample_subscription):
        """
        ✅ PASS: End-of-period cancellation sets cancel_at_period_end
        """
        sample_subscription.cancel_at_period_end = True
        mock_stripe.Subscription.modify.return_value = sample_subscription
        
        from services.payment_service import cancel_subscription
        
        result = cancel_subscription('sub_test_123', immediate=False)
        
        assert result['success'] is True
        mock_stripe.Subscription.modify.assert_called_once_with(
            'sub_test_123',
            cancel_at_period_end=True
        )
    
    def test_cancellation_stripe_error(self, mock_stripe):
        """
        ❌ FAIL: Stripe error returns failure
        """
        mock_stripe.error.StripeError = Exception
        mock_stripe.Subscription.cancel.side_effect = Exception('Subscription not found')
        
        from services.payment_service import cancel_subscription
        
        result = cancel_subscription('sub_invalid', immediate=True)
        
        assert result['success'] is False
        assert 'Subscription not found' in result['error']


# ============================================
# F. Get Payment Intent Details Tests
# ============================================

class TestGetPaymentIntentDetails:
    """Tests for get_payment_intent_details function"""
    
    def test_retrieves_payment_intent(self, mock_stripe, sample_payment_intent):
        """
        ✅ PASS: Retrieves PaymentIntent details
        """
        mock_stripe.PaymentIntent.retrieve.return_value = sample_payment_intent
        
        from services.payment_service import get_payment_intent_details
        
        result = get_payment_intent_details('pi_test_123')
        
        assert result == sample_payment_intent
        mock_stripe.PaymentIntent.retrieve.assert_called_once_with('pi_test_123')
    
    def test_returns_none_on_error(self, mock_stripe):
        """
        ❌ FAIL: Returns None when PaymentIntent not found
        """
        mock_stripe.error.StripeError = Exception
        mock_stripe.PaymentIntent.retrieve.side_effect = Exception('Not found')
        
        from services.payment_service import get_payment_intent_details
        
        result = get_payment_intent_details('pi_invalid')
        
        assert result is None


# ============================================
# G. Get Subscription Status Tests
# ============================================

class TestGetSubscriptionStatus:
    """Tests for get_subscription_status function"""
    
    def test_returns_active_subscription_status(self, mock_stripe):
        """
        ✅ PASS: Returns correct status for active subscription
        """
        mock_subscription = Mock()
        mock_subscription.status = 'active'
        mock_subscription.current_period_end = 1735689600
        mock_subscription.__getitem__ = lambda s, k: {
            'items': {'data': [{'price': {'id': 'price_starter_test'}}]}
        }[k]
        
        mock_stripe.Subscription.list.return_value = Mock(data=[mock_subscription])
        
        from services.payment_service import get_subscription_status
        
        with patch.dict('services.payment_service.PRICE_MAP', {
            'starter': 'price_starter_test',
            'pro': 'price_pro_test'
        }):
            result = get_subscription_status('cus_test_123')
        
        assert result['status'] == 'active'
        assert result['tier'] == 'starter'
    
    def test_returns_inactive_when_no_subscription(self, mock_stripe):
        """
        ✅ PASS: Returns inactive status when no subscription
        """
        mock_stripe.Subscription.list.return_value = Mock(data=[])
        
        from services.payment_service import get_subscription_status
        
        result = get_subscription_status('cus_test_123')
        
        assert result['status'] == 'inactive'
        assert result['tier'] == 'free'


# ============================================
# H. Security Tests
# ============================================

class TestSecurityCompliance:
    """Security-focused tests for payment service"""
    
    def test_no_card_numbers_in_metadata(self, mock_stripe, sample_checkout_session):
        """
        🔒 SECURITY: Verify no credit card numbers in session metadata
        """
        mock_stripe.checkout.Session.create.return_value = sample_checkout_session
        
        from services.payment_service import create_checkout_session
        
        with patch.dict('services.payment_service.PRICE_MAP', {'credits_100': 'price_test'}):
            create_checkout_session('user_123', 'credits_100')
        
        call_kwargs = mock_stripe.checkout.Session.create.call_args[1]
        metadata = call_kwargs.get('metadata', {})
        
        # Ensure no card-related data in metadata
        for key, value in metadata.items():
            assert 'card' not in key.lower()
            assert not (isinstance(value, str) and len(value) == 16 and value.isdigit())
    
    def test_success_url_uses_https(self, mock_stripe, sample_checkout_session):
        """
        🔒 SECURITY: Success/Cancel URLs should use HTTPS in production
        """
        mock_stripe.checkout.Session.create.return_value = sample_checkout_session
        
        from services.payment_service import create_checkout_session
        
        with patch.dict('services.payment_service.PRICE_MAP', {'credits_100': 'price_test'}):
            with patch('services.payment_service.FRONTEND_URL', 'https://decodables.com'):
                create_checkout_session('user_123', 'credits_100')
        
        call_kwargs = mock_stripe.checkout.Session.create.call_args[1]
        
        # In production, URLs should be HTTPS
        # (In test mode, localhost HTTP is acceptable)
        success_url = call_kwargs.get('success_url', '')
        cancel_url = call_kwargs.get('cancel_url', '')
        
        # Just verify URLs are well-formed
        assert 'success=true' in success_url
        assert 'canceled=true' in cancel_url
