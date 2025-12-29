"""
Pytest configuration and fixtures for API tests
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock

# Lazy import to avoid dependency issues
def get_test_client():
    """Lazy import TestClient and app"""
    from fastapi.testclient import TestClient
    from app import app
    return TestClient(app)

# Mock user data for different tiers
MOCK_FREE_USER = {
    "id": "user_free_123",
    "email": "free@test.com",
    "tier": "free",
    "subscription_status": "inactive",
    "credits_monthly": 0,
    "credits_permanent": 50,
    "created_at": datetime.now(timezone.utc).isoformat(),  # Just created
}

MOCK_FREE_USER_EXPIRED = {
    "id": "user_free_expired_123",
    "email": "free_expired@test.com",
    "tier": "free",
    "subscription_status": "inactive",
    "credits_monthly": 0,
    "credits_permanent": 50,
    "created_at": (datetime.now(timezone.utc) - timedelta(days=8)).isoformat(),  # 8 days ago
}

MOCK_STARTER_USER = {
    "id": "user_starter_123",
    "email": "starter@test.com",
    "tier": "starter",
    "subscription_status": "active",
    "credits_monthly": 500,
    "credits_permanent": 0,
    "created_at": datetime.now(timezone.utc).isoformat(),
}

MOCK_PRO_USER = {
    "id": "user_pro_123",
    "email": "pro@test.com",
    "tier": "pro",
    "subscription_status": "active",
    "credits_monthly": 1000,
    "credits_permanent": 0,
    "created_at": datetime.now(timezone.utc).isoformat(),
}


@pytest.fixture
def client():
    """Create a test client"""
    return get_test_client()


@pytest.fixture
def mock_get_current_user_free():
    """Mock get_current_user for Free tier"""
    def _mock_user():
        return MOCK_FREE_USER
    return _mock_user


@pytest.fixture
def mock_get_current_user_free_expired():
    """Mock get_current_user for expired Free tier"""
    def _mock_user():
        return MOCK_FREE_USER_EXPIRED
    return _mock_user


@pytest.fixture
def mock_get_current_user_starter():
    """Mock get_current_user for Starter tier"""
    def _mock_user():
        return MOCK_STARTER_USER
    return _mock_user


@pytest.fixture
def mock_get_current_user_pro():
    """Mock get_current_user for Pro tier"""
    def _mock_user():
        return MOCK_PRO_USER
    return _mock_user


@pytest.fixture
def mock_supabase():
    """Mock Supabase client"""
    mock_supabase = MagicMock()
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    return mock_supabase


@pytest.fixture
def mock_db_service():
    """Mock db_service functions"""
    with patch('db_service.supabase') as mock_supabase:
        yield mock_supabase

