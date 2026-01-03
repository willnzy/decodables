"""
Pytest configuration and fixtures for API tests

This conftest.py provides:
- Mock user fixtures for all tier levels
- Database mock fixtures
- External API mock fixtures (Stripe, FAL, OpenAI)
- Test client factory
- Common test utilities
"""
import pytest
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import json

# Set test environment
os.environ.setdefault('TESTING', 'true')
os.environ.setdefault('STRIPE_SECRET_KEY', 'sk_test_mock')
os.environ.setdefault('STRIPE_WEBHOOK_SECRET', 'whsec_test_mock')

# ============================================
# Test Client Factory
# ============================================

def get_test_client():
    """Lazy import TestClient and app to avoid import errors"""
    from fastapi.testclient import TestClient
    try:
        from app import app
        return TestClient(app)
    except ImportError as e:
        pytest.skip(f"Cannot import app: {e}")

# ============================================
# Mock User Data for Different Tiers
# ============================================

MOCK_FREE_USER = {
    "id": "user_free_123",
    "email": "free@test.com",
    "tier": "free",
    "subscription_status": "inactive",
    "credits_monthly": 0,
    "credits_permanent": 50,
    "created_at": datetime.now(timezone.utc).isoformat(),
    "user_code": "FREE001",
    "timezone": "UTC",
    "stripe_customer_id": None,
}

MOCK_FREE_USER_EXPIRED = {
    "id": "user_free_expired_123",
    "email": "free_expired@test.com",
    "tier": "free",
    "subscription_status": "inactive",
    "credits_monthly": 0,
    "credits_permanent": 50,
    "created_at": (datetime.now(timezone.utc) - timedelta(days=8)).isoformat(),
    "user_code": "FREE002",
    "timezone": "UTC",
    "stripe_customer_id": None,
}

MOCK_FREE_USER_NO_CREDITS = {
    "id": "user_free_nocredits_123",
    "email": "nocredits@test.com",
    "tier": "free",
    "subscription_status": "inactive",
    "credits_monthly": 0,
    "credits_permanent": 0,
    "created_at": datetime.now(timezone.utc).isoformat(),
    "user_code": "FREE003",
    "timezone": "UTC",
    "stripe_customer_id": None,
}

MOCK_STARTER_USER = {
    "id": "user_starter_123",
    "email": "starter@test.com",
    "tier": "starter",
    "subscription_status": "active",
    "credits_monthly": 500,
    "credits_permanent": 0,
    "created_at": datetime.now(timezone.utc).isoformat(),
    "user_code": "START001",
    "timezone": "America/New_York",
    "stripe_customer_id": "cus_starter_123",
    "stripe_subscription_id": "sub_starter_123",
}

MOCK_PRO_USER = {
    "id": "user_pro_123",
    "email": "pro@test.com",
    "tier": "pro",
    "subscription_status": "active",
    "credits_monthly": 1000,
    "credits_permanent": 200,
    "created_at": datetime.now(timezone.utc).isoformat(),
    "user_code": "PRO001",
    "timezone": "Asia/Shanghai",
    "stripe_customer_id": "cus_pro_123",
    "stripe_subscription_id": "sub_pro_123",
}

MOCK_ADMIN_USER = {
    "id": "user_admin_123",
    "email": "admin@test.com",
    "tier": "pro",
    "subscription_status": "active",
    "credits_monthly": 9999,
    "credits_permanent": 9999,
    "created_at": datetime.now(timezone.utc).isoformat(),
    "user_code": "ADMIN001",
    "timezone": "UTC",
    "is_admin": True,
    "stripe_customer_id": "cus_admin_123",
}


# ============================================
# Client Fixtures
# ============================================

@pytest.fixture
def client():
    """Create a test client"""
    return get_test_client()


# ============================================
# User Mock Fixtures
# ============================================

@pytest.fixture
def mock_get_current_user_free():
    """Mock get_current_user for Free tier"""
    def _mock_user():
        return MOCK_FREE_USER.copy()
    return _mock_user


@pytest.fixture
def mock_get_current_user_free_expired():
    """Mock get_current_user for expired Free tier"""
    def _mock_user():
        return MOCK_FREE_USER_EXPIRED.copy()
    return _mock_user


@pytest.fixture
def mock_get_current_user_free_no_credits():
    """Mock get_current_user for Free tier with no credits"""
    def _mock_user():
        return MOCK_FREE_USER_NO_CREDITS.copy()
    return _mock_user


@pytest.fixture
def mock_get_current_user_starter():
    """Mock get_current_user for Starter tier"""
    def _mock_user():
        return MOCK_STARTER_USER.copy()
    return _mock_user


@pytest.fixture
def mock_get_current_user_pro():
    """Mock get_current_user for Pro tier"""
    def _mock_user():
        return MOCK_PRO_USER.copy()
    return _mock_user


@pytest.fixture
def mock_get_current_user_admin():
    """Mock get_current_user for Admin user"""
    def _mock_user():
        return MOCK_ADMIN_USER.copy()
    return _mock_user


# ============================================
# Database Mock Fixtures
# ============================================

@pytest.fixture
def mock_supabase():
    """Mock Supabase client with chainable methods"""
    mock_client = MagicMock()
    
    # Create chainable mock
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    
    # Make all methods return self for chaining
    for method in ['select', 'insert', 'update', 'delete', 'eq', 'neq', 
                   'gt', 'gte', 'lt', 'lte', 'like', 'ilike', 'is_', 
                   'in_', 'not_', 'or_', 'order', 'limit', 'range']:
        getattr(mock_table, method).return_value = mock_table
    
    # Default execute returns empty
    mock_table.execute.return_value = Mock(data=[], count=0)
    
    return mock_client


@pytest.fixture
def mock_db_service():
    """Mock db_service functions"""
    with patch('db_service.supabase') as mock_supabase:
        yield mock_supabase


# ============================================
# External API Mock Fixtures
# ============================================

@pytest.fixture
def mock_stripe():
    """Mock Stripe API calls"""
    with patch('stripe.checkout.Session') as mock_session, \
         patch('stripe.billing_portal.Session') as mock_portal, \
         patch('stripe.Refund') as mock_refund, \
         patch('stripe.Subscription') as mock_subscription, \
         patch('stripe.PaymentIntent') as mock_payment_intent, \
         patch('stripe.Webhook') as mock_webhook:
        
        # Checkout session mock
        mock_session.create.return_value = Mock(
            id='cs_test_123',
            url='https://checkout.stripe.com/test'
        )
        
        # Portal session mock
        mock_portal.create.return_value = Mock(
            url='https://billing.stripe.com/test'
        )
        
        # Refund mock
        mock_refund.create.return_value = Mock(
            id='re_test_123',
            amount=1000,
            status='succeeded'
        )
        
        # Subscription mock
        mock_subscription.modify.return_value = Mock(
            id='sub_test_123',
            status='active'
        )
        mock_subscription.delete.return_value = Mock(
            id='sub_test_123',
            status='canceled'
        )
        
        # PaymentIntent mock
        mock_payment_intent.retrieve.return_value = Mock(
            id='pi_test_123',
            amount=1000,
            status='succeeded'
        )
        
        yield {
            'session': mock_session,
            'portal': mock_portal,
            'refund': mock_refund,
            'subscription': mock_subscription,
            'payment_intent': mock_payment_intent,
            'webhook': mock_webhook,
        }


@pytest.fixture
def mock_fal_ai():
    """Mock FAL.ai image generation"""
    with patch('fal_client.submit') as mock_submit:
        mock_result = Mock()
        mock_result.get.return_value = {
            'images': [{'url': 'https://cdn.fal.ai/test_image.png'}]
        }
        mock_submit.return_value = mock_result
        yield mock_submit


@pytest.fixture
def mock_openai():
    """Mock OpenAI API calls"""
    with patch('openai.ChatCompletion.create') as mock_chat:
        mock_chat.return_value = Mock(
            choices=[Mock(message=Mock(content='Test response'))]
        )
        yield mock_chat


# ============================================
# Test Data Factories
# ============================================

@pytest.fixture
def project_factory():
    """Factory for creating test project data"""
    def _create_project(
        project_id='proj_test_123',
        user_id='user_test_123',
        title='Test Project',
        **kwargs
    ):
        return {
            'id': project_id,
            'user_id': user_id,
            'title': title,
            'canvas_data': kwargs.get('canvas_data', {'pages': []}),
            'thumbnail_url': kwargs.get('thumbnail_url', 'https://cdn.../thumb.png'),
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'deleted': False,
            **kwargs
        }
    return _create_project


@pytest.fixture
def asset_factory():
    """Factory for creating test asset data"""
    def _create_asset(
        asset_id='asset_test_123',
        user_id='user_test_123',
        **kwargs
    ):
        return {
            'id': asset_id,
            'user_id': user_id,
            'url': kwargs.get('url', 'https://cdn.../asset.png'),
            'type': kwargs.get('type', 'uploaded'),
            'description': kwargs.get('description', ''),
            'created_at': datetime.now(timezone.utc).isoformat(),
            'deleted': False,
            **kwargs
        }
    return _create_asset


@pytest.fixture
def listing_factory():
    """Factory for creating marketplace listing data"""
    def _create_listing(
        listing_id='listing_test_123',
        seller_id='user_test_123',
        **kwargs
    ):
        return {
            'id': listing_id,
            'seller_id': seller_id,
            'title': kwargs.get('title', 'Test Listing'),
            'description': kwargs.get('description', 'Test description'),
            'price_credits': kwargs.get('price_credits', 50),
            'resource_type': kwargs.get('resource_type', 'project'),
            'status': kwargs.get('status', 'approved'),
            'is_public': True,
            'created_at': datetime.now(timezone.utc).isoformat(),
            **kwargs
        }
    return _create_listing


# ============================================
# Webhook Test Helpers
# ============================================

@pytest.fixture
def stripe_webhook_payload():
    """Create Stripe webhook test payloads"""
    def _create_payload(event_type, data=None):
        return {
            'id': f'evt_test_{event_type}',
            'type': event_type,
            'created': int(datetime.now(timezone.utc).timestamp()),
            'data': {
                'object': data or {}
            }
        }
    return _create_payload


@pytest.fixture
def stripe_signature():
    """Create mock Stripe webhook signature"""
    def _create_signature(payload, secret='whsec_test_mock'):
        import hmac
        import hashlib
        timestamp = str(int(datetime.now(timezone.utc).timestamp()))
        payload_str = json.dumps(payload) if isinstance(payload, dict) else payload
        signed_payload = f'{timestamp}.{payload_str}'
        signature = hmac.new(
            secret.encode('utf-8'),
            signed_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return f't={timestamp},v1={signature}'
    return _create_signature


# ============================================
# Test Markers
# ============================================

def pytest_configure(config):
    """Configure custom markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )
    config.addinivalue_line(
        "markers", "payment: marks tests related to payment processing"
    )
    config.addinivalue_line(
        "markers", "auth: marks tests related to authentication"
    )

