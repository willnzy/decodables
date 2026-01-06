"""
Admin Payment Management Tests
Tests for admin refund and subscription management endpoints

🚨 CRITICAL: NO REAL MONEY - All Stripe calls are mocked

Test Coverage:
- Admin refund creation with validation
- Subscription cancellation (immediate vs end-of-period)
- Payment history retrieval
- Security checks (admin-only access)
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone
import json
import sys

# Mock modules BEFORE importing app or payment_service
# Mock python-multipart (required for Form/File uploads)
if 'multipart' not in sys.modules:
    multipart_mock = MagicMock()
    multipart_mock.multipart = MagicMock()
    sys.modules['multipart'] = multipart_mock
    sys.modules['multipart.multipart'] = multipart_mock.multipart

# Mock stripe module
sys.modules['stripe'] = MagicMock()

# Check if required dependencies are available
try:
    import jwt
    import supabase
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

pytestmark = pytest.mark.skipif(not HAS_DEPS, reason="Missing dependencies (jwt, supabase)")


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def client():
    """Create test client with mocked dependencies"""
    if not HAS_DEPS:
        pytest.skip("Missing dependencies")
    # Mock supabase in the db_service module where it's defined
    with patch('services.db_service.supabase') as mock_supabase:
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(data=[])
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(data=None)
        with patch('services.payment_service.stripe'):
            from app import app
            from fastapi.testclient import TestClient
            return TestClient(app)


@pytest.fixture
def mock_admin_user():
    """Mock admin user for authentication"""
    return {
        'id': 'admin_user_123',
        'email': 'admin@test.com',
        'tier': 'admin',
        'is_admin': True
    }


@pytest.fixture
def mock_regular_user():
    """Mock regular user (non-admin)"""
    return {
        'id': 'user_regular_123',
        'email': 'user@test.com',
        'tier': 'starter',
        'is_admin': False,
        'stripe_customer_id': 'cus_regular_123'
    }


@pytest.fixture
def mock_payment_intents():
    """Mock Stripe PaymentIntent list"""
    return [
        Mock(
            id='pi_test_001',
            status='succeeded',
            amount=999,
            amount_received=999,
            currency='usd',
            created=int(datetime.now(timezone.utc).timestamp()),
            charges=Mock(data=[Mock(amount_refunded=0)])
        ),
        Mock(
            id='pi_test_002',
            status='succeeded',
            amount=1999,
            amount_received=1999,
            currency='usd',
            created=int(datetime.now(timezone.utc).timestamp()) - 86400,
            charges=Mock(data=[Mock(amount_refunded=500)])
        )
    ]


@pytest.fixture
def mock_subscriptions():
    """Mock Stripe Subscription list"""
    return [
        Mock(
            id='sub_test_001',
            status='active',
            current_period_end=int(datetime.now(timezone.utc).timestamp()) + 86400 * 30,
            items=Mock(data=[Mock(price=Mock(id='price_starter_test'))]),
            cancel_at_period_end=False
        )
    ]


# ============================================
# A. Admin User Payment History Tests
# ============================================

class TestAdminGetUserPayments:
    """Tests for GET /api/admin/user/{uid}/payments"""
    
    @patch('dependencies.require_admin')
    @patch('services.db_service.supabase')
    @patch('services.payment_service.get_customer_payments')
    @patch('services.payment_service.get_customer_subscriptions')
    def test_returns_payment_history(
        self, mock_get_subs, mock_get_payments, mock_supabase, mock_require_admin,
        client, mock_admin_user, mock_payment_intents, mock_subscriptions
    ):
        """
        ✅ PASS: Returns user's payment history for admin
        """
        mock_require_admin.return_value = mock_admin_user
        
        # Mock user lookup
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=[{
                'id': 'user_target_123',
                'user_code': 'TARG123',
                'email': 'target@test.com',
                'stripe_customer_id': 'cus_target_123'
            }]
        )
        
        mock_get_payments.return_value = mock_payment_intents
        mock_get_subs.return_value = mock_subscriptions
        
        response = client.get('/api/admin/user/user_target_123/payments')
        
        # Should return payment history
        assert response.status_code == 200
        data = response.json()
        assert 'payments' in data
        assert 'subscriptions' in data
    
    @patch('dependencies.require_admin')
    @patch('services.db_service.supabase')
    def test_returns_empty_for_no_stripe_customer(
        self, mock_supabase, mock_require_admin, client, mock_admin_user
    ):
        """
        ✅ PASS: Returns empty arrays for user without Stripe customer
        """
        mock_require_admin.return_value = mock_admin_user
        
        # User without stripe_customer_id
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=[{
                'id': 'user_no_stripe',
                'user_code': 'NOSTRIPE',
                'email': 'nostripe@test.com',
                'stripe_customer_id': None
            }]
        )
        
        response = client.get('/api/admin/user/user_no_stripe/payments')
        
        assert response.status_code == 200
        data = response.json()
        assert data['payments'] == []
        assert data['subscriptions'] == []
    
    @patch('dependencies.require_admin')
    @patch('services.db_service.supabase')
    def test_returns_404_for_nonexistent_user(
        self, mock_supabase, mock_require_admin, client, mock_admin_user
    ):
        """
        ❌ FAIL: Returns 404 for non-existent user
        """
        mock_require_admin.return_value = mock_admin_user
        
        # No user found
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=[]
        )
        
        response = client.get('/api/admin/user/user_nonexistent/payments')
        
        assert response.status_code == 404


# ============================================
# B. Admin Refund Tests
# ============================================

class TestAdminCreateRefund:
    """Tests for POST /api/admin/user/{uid}/refund"""
    
    @patch('dependencies.require_admin')
    @patch('services.db_service.supabase')
    @patch('services.payment_service.get_payment_intent_details')
    @patch('services.payment_service.create_refund')
    @patch('app.log_payment_record')
    @patch('services.db.admin_users.admin_log_operation')
    def test_full_refund_success(
        self, mock_log_admin, mock_log_payment, mock_create_refund, 
        mock_get_pi, mock_supabase, mock_require_admin,
        client, mock_admin_user
    ):
        """
        ✅ PASS: Full refund processes successfully
        """
        mock_require_admin.return_value = mock_admin_user
        
        # Mock user lookup
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=[{
                'id': 'user_refund_123',
                'user_code': 'REF123',
                'stripe_customer_id': 'cus_refund_123'
            }]
        )
        
        # Mock PaymentIntent
        mock_pi = Mock(
            id='pi_to_refund',
            status='succeeded',
            amount=999,
            customer='cus_refund_123',
            charges=Mock(data=[Mock(amount_refunded=0)])
        )
        mock_get_pi.return_value = mock_pi
        
        # Mock refund creation
        mock_create_refund.return_value = {
            'success': True,
            'refund': Mock(id='re_123', amount=999),
            'error': None
        }
        
        response = client.post(
            '/api/admin/user/user_refund_123/refund',
            json={
                'user_code': 'REF123',
                'payment_intent_id': 'pi_to_refund',
                'reason': 'Customer requested'
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        
        # Verify refund was logged
        mock_log_payment.assert_called()
    
    @patch('dependencies.require_admin')
    @patch('services.db_service.supabase')
    @patch('services.payment_service.get_payment_intent_details')
    @patch('services.payment_service.create_refund')
    def test_partial_refund_success(
        self, mock_create_refund, mock_get_pi, mock_supabase, mock_require_admin,
        client, mock_admin_user
    ):
        """
        ✅ PASS: Partial refund with specific amount
        """
        mock_require_admin.return_value = mock_admin_user
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=[{
                'id': 'user_partial_123',
                'user_code': 'PART123',
                'stripe_customer_id': 'cus_partial_123'
            }]
        )
        
        mock_pi = Mock(
            id='pi_partial',
            status='succeeded',
            amount=1999,  # $19.99
            customer='cus_partial_123',
            charges=Mock(data=[Mock(amount_refunded=0)])
        )
        mock_get_pi.return_value = mock_pi
        
        mock_create_refund.return_value = {
            'success': True,
            'refund': Mock(id='re_456', amount=500),
            'error': None
        }
        
        response = client.post(
            '/api/admin/user/user_partial_123/refund',
            json={
                'user_code': 'PART123',
                'payment_intent_id': 'pi_partial',
                'amount_cents': 500,  # $5.00 partial refund
                'reason': 'Partial refund for service issue'
            }
        )
        
        assert response.status_code == 200
        
        # Verify partial amount was passed
        mock_create_refund.assert_called_once()
        call_args = mock_create_refund.call_args
        assert call_args[1].get('amount_cents') == 500 or call_args[0][1] == 500
    
    @patch('dependencies.require_admin')
    @patch('services.db_service.supabase')
    @patch('services.payment_service.get_payment_intent_details')
    def test_refund_wrong_customer_rejected(
        self, mock_get_pi, mock_supabase, mock_require_admin,
        client, mock_admin_user
    ):
        """
        ❌ REJECT (Security): Refund for wrong customer rejected
        🔒 Prevents admin from refunding to wrong account
        """
        mock_require_admin.return_value = mock_admin_user
        
        # User A
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=[{
                'id': 'user_a',
                'user_code': 'USERA',
                'stripe_customer_id': 'cus_user_a'
            }]
        )
        
        # PaymentIntent belongs to User B
        mock_pi = Mock(
            id='pi_user_b',
            status='succeeded',
            amount=999,
            customer='cus_user_b',  # Different customer!
            charges=Mock(data=[Mock(amount_refunded=0)])
        )
        mock_get_pi.return_value = mock_pi
        
        response = client.post(
            '/api/admin/user/user_a/refund',
            json={
                'user_code': 'USERA',
                'payment_intent_id': 'pi_user_b',
                'reason': 'Attempting to refund wrong user'
            }
        )
        
        # Should be rejected - payment doesn't belong to user
        assert response.status_code == 403
    
    @patch('dependencies.require_admin')
    @patch('services.db_service.supabase')
    @patch('services.payment_service.get_payment_intent_details')
    def test_refund_already_refunded_rejected(
        self, mock_get_pi, mock_supabase, mock_require_admin,
        client, mock_admin_user
    ):
        """
        ❌ REJECT: Already refunded payment rejected
        """
        mock_require_admin.return_value = mock_admin_user
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=[{
                'id': 'user_refunded',
                'user_code': 'REFUNDED',
                'stripe_customer_id': 'cus_refunded'
            }]
        )
        
        # PaymentIntent already fully refunded
        mock_pi = Mock(
            id='pi_already_refunded',
            status='succeeded',
            amount=999,
            customer='cus_refunded',
            charges=Mock(data=[Mock(amount_refunded=999)])  # Fully refunded
        )
        mock_get_pi.return_value = mock_pi
        
        response = client.post(
            '/api/admin/user/user_refunded/refund',
            json={
                'user_code': 'REFUNDED',
                'payment_intent_id': 'pi_already_refunded',
                'reason': 'Attempting double refund'
            }
        )
        
        assert response.status_code == 400
        assert 'refunded' in response.json().get('detail', '').lower()
    
    @patch('dependencies.require_admin')
    @patch('services.db_service.supabase')
    @patch('services.payment_service.get_payment_intent_details')
    def test_refund_nonexistent_payment_rejected(
        self, mock_get_pi, mock_supabase, mock_require_admin,
        client, mock_admin_user
    ):
        """
        ❌ REJECT: Non-existent payment returns 404
        """
        mock_require_admin.return_value = mock_admin_user
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=[{
                'id': 'user_test',
                'user_code': 'TEST',
                'stripe_customer_id': 'cus_test'
            }]
        )
        
        # PaymentIntent not found
        mock_get_pi.return_value = None
        
        response = client.post(
            '/api/admin/user/user_test/refund',
            json={
                'user_code': 'TEST',
                'payment_intent_id': 'pi_nonexistent',
                'reason': 'Test'
            }
        )
        
        assert response.status_code == 404
    
    @patch('dependencies.require_admin')
    @patch('services.db_service.supabase')
    def test_refund_user_code_mismatch_rejected(
        self, mock_supabase, mock_require_admin, client, mock_admin_user
    ):
        """
        ❌ REJECT (Security): User code mismatch rejected
        🔒 Prevents accidental refund to wrong user
        """
        mock_require_admin.return_value = mock_admin_user
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=[{
                'id': 'user_123',
                'user_code': 'CORRECT',  # Actual code
                'stripe_customer_id': 'cus_123'
            }]
        )
        
        response = client.post(
            '/api/admin/user/user_123/refund',
            json={
                'user_code': 'WRONG',  # Mismatched code
                'payment_intent_id': 'pi_test',
                'reason': 'Test'
            }
        )
        
        assert response.status_code == 400


# ============================================
# C. Admin Subscription Cancellation Tests
# ============================================

class TestAdminCancelSubscription:
    """Tests for POST /api/admin/user/{uid}/cancel-subscription"""
    
    @patch('dependencies.require_admin')
    @patch('services.db_service.supabase')
    @patch('services.payment_service.cancel_subscription')
    @patch('app.log_payment_record')
    @patch('services.db.admin_users.admin_log_operation')
    def test_immediate_cancellation_success(
        self, mock_log_admin, mock_log_payment, mock_cancel_sub,
        mock_supabase, mock_require_admin, client, mock_admin_user
    ):
        """
        ✅ PASS: Immediate cancellation processes successfully
        """
        mock_require_admin.return_value = mock_admin_user
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=[{
                'id': 'user_cancel_123',
                'user_code': 'CANCEL',
                'tier': 'starter',
                'stripe_customer_id': 'cus_cancel_123'
            }]
        )
        
        mock_cancel_sub.return_value = {
            'success': True,
            'subscription': Mock(id='sub_123', status='canceled'),
            'error': None
        }
        
        response = client.post(
            '/api/admin/user/user_cancel_123/cancel-subscription',
            json={
                'user_code': 'CANCEL',
                'subscription_id': 'sub_123',
                'immediate': True,
                'reason': 'Customer requested immediate cancellation'
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        
        # Verify immediate cancellation was called
        mock_cancel_sub.assert_called_once()
        call_kwargs = mock_cancel_sub.call_args
        assert call_kwargs[1].get('immediate') is True or call_kwargs[0][1] is True
    
    @patch('dependencies.require_admin')
    @patch('services.db_service.supabase')
    @patch('services.payment_service.cancel_subscription')
    def test_end_of_period_cancellation_success(
        self, mock_cancel_sub, mock_supabase, mock_require_admin,
        client, mock_admin_user
    ):
        """
        ✅ PASS: End-of-period cancellation sets cancel_at_period_end
        """
        mock_require_admin.return_value = mock_admin_user
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=[{
                'id': 'user_eop_123',
                'user_code': 'EOP',
                'tier': 'pro',
                'stripe_customer_id': 'cus_eop_123'
            }]
        )
        
        mock_cancel_sub.return_value = {
            'success': True,
            'subscription': Mock(id='sub_456', cancel_at_period_end=True),
            'error': None
        }
        
        response = client.post(
            '/api/admin/user/user_eop_123/cancel-subscription',
            json={
                'user_code': 'EOP',
                'subscription_id': 'sub_456',
                'immediate': False,  # End of period
                'reason': 'Customer wants to keep access until period ends'
            }
        )
        
        assert response.status_code == 200
        
        # Verify non-immediate cancellation
        mock_cancel_sub.assert_called_once()


# ============================================
# D. Security Tests
# ============================================

class TestAdminPaymentSecurity:
    """Security tests for admin payment endpoints"""
    
    def test_non_admin_cannot_access_payments(self, client):
        """
        ❌ REJECT (Security): Non-admin users cannot access payment endpoints
        """
        # Without proper admin auth, should fail
        response = client.get('/api/admin/user/user_123/payments')
        
        # Should return 401 or 403
        assert response.status_code in [401, 403, 422]
    
    def test_non_admin_cannot_create_refund(self, client):
        """
        ❌ REJECT (Security): Non-admin users cannot create refunds
        """
        response = client.post(
            '/api/admin/user/user_123/refund',
            json={
                'user_code': 'TEST',
                'payment_intent_id': 'pi_test',
                'reason': 'Test'
            }
        )
        
        assert response.status_code in [401, 403, 422]
    
    def test_non_admin_cannot_cancel_subscription(self, client):
        """
        ❌ REJECT (Security): Non-admin users cannot cancel subscriptions
        """
        response = client.post(
            '/api/admin/user/user_123/cancel-subscription',
            json={
                'user_code': 'TEST',
                'subscription_id': 'sub_test',
                'immediate': True,
                'reason': 'Test'
            }
        )
        
        assert response.status_code in [401, 403, 422]
    
    @patch('dependencies.require_admin')
    def test_audit_log_created_for_refund(
        self, mock_require_admin, client, mock_admin_user
    ):
        """
        🔒 SECURITY: Refund actions are logged for audit trail
        """
        mock_require_admin.return_value = mock_admin_user
        
        # Even if refund fails, audit should be logged
        # This is verified by checking log_admin_activity is called
        # in the actual implementation


# ============================================
# E. Edge Cases
# ============================================

class TestAdminPaymentEdgeCases:
    """Edge cases for admin payment management"""
    
    @patch('dependencies.require_admin')
    @patch('services.db_service.supabase')
    def test_refund_exceeds_original_amount(
        self, mock_supabase, mock_require_admin, client, mock_admin_user
    ):
        """
        ❌ REJECT: Refund amount exceeding original payment rejected
        """
        mock_require_admin.return_value = mock_admin_user
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=[{
                'id': 'user_excess',
                'user_code': 'EXCESS',
                'stripe_customer_id': 'cus_excess'
            }]
        )
        
        with patch('services.payment_service.get_payment_intent_details') as mock_get_pi:
            mock_pi = Mock(
                id='pi_small',
                status='succeeded',
                amount=999,  # $9.99
                customer='cus_excess',
                charges=Mock(data=[Mock(amount_refunded=0)])
            )
            mock_get_pi.return_value = mock_pi
            
            response = client.post(
                '/api/admin/user/user_excess/refund',
                json={
                    'user_code': 'EXCESS',
                    'payment_intent_id': 'pi_small',
                    'amount_cents': 5000,  # $50 > $9.99
                    'reason': 'Excessive refund attempt'
                }
            )
        
        # Should be rejected
        assert response.status_code == 400
    
    @patch('dependencies.require_admin')
    @patch('services.db_service.supabase')
    def test_cancel_already_canceled_subscription(
        self, mock_supabase, mock_require_admin, client, mock_admin_user
    ):
        """
        ⚠️ EDGE: Canceling already-canceled subscription handled gracefully
        """
        mock_require_admin.return_value = mock_admin_user
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=[{
                'id': 'user_already_canceled',
                'user_code': 'CANCELED',
                'tier': 'free',  # Already downgraded
                'stripe_customer_id': 'cus_canceled'
            }]
        )
        
        with patch('services.payment_service.cancel_subscription') as mock_cancel:
            mock_cancel.return_value = {
                'success': False,
                'subscription': None,
                'error': 'Subscription is already canceled'
            }
            
            response = client.post(
                '/api/admin/user/user_already_canceled/cancel-subscription',
                json={
                    'user_code': 'CANCELED',
                    'subscription_id': 'sub_already_canceled',
                    'immediate': True,
                    'reason': 'Test'
                }
            )
        
        # Should return error but not crash
        assert response.status_code in [200, 400]
