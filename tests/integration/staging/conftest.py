"""
Staging Environment Test Configuration

Fixtures for testing against the actual staging API.
Supports both regular user and admin user testing.

Token 获取方式 (优先级):
1. 环境变量: TEST_USER_TOKEN / TEST_ADMIN_TOKEN
2. 自动生成: test_jwt_generator (需要 Railway 配置 TEST_JWT_PUBLIC_KEY)
3. Clerk API: CLERK_SECRET_KEY + SESSION_ID (需要用户登录)

@module tests.integration.staging.conftest
@version 3.0.0 (added auto token generation without Clerk login)
"""

import os
import pytest
import httpx
from typing import Generator, Optional

from .test_users import TestUsers, TokenEnvVars
from .test_jwt_generator import (
    get_free_token as generate_free_token,
    get_starter_token as generate_starter_token,
    get_pro_token as generate_pro_token,
    get_admin_token as generate_admin_token,
    TEST_USERS,
)


# ==========================================
# Custom Markers
# ==========================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "p0: Priority 0 - Critical tests")
    config.addinivalue_line("markers", "p1: Priority 1 - High priority tests")
    config.addinivalue_line("markers", "p2: Priority 2 - Medium priority tests")
    config.addinivalue_line("markers", "p3: Priority 3 - Low priority tests")
    config.addinivalue_line("markers", "security: Security related tests")
    config.addinivalue_line("markers", "performance: Performance related tests")
    config.addinivalue_line("markers", "admin: Requires admin privileges")


# ==========================================
# Configuration
# ==========================================

STAGING_BASE_URL = "https://decodables-staging.up.railway.app"
API_V2_PREFIX = "/api/v2"
CLERK_API_BASE = "https://api.clerk.com/v1"


def _get_token_from_clerk(session_id: str, clerk_secret: str) -> Optional[str]:
    """
    Get JWT token from Clerk API using session ID.

    Args:
        session_id: Clerk session ID (e.g., "sess_xxx")
        clerk_secret: Clerk secret key (e.g., "sk_test_xxx")

    Returns:
        JWT token or None if failed
    """
    try:
        response = httpx.post(
            f"{CLERK_API_BASE}/sessions/{session_id}/tokens",
            headers={
                "Authorization": f"Bearer {clerk_secret}",
                "Content-Type": "application/json",
            },
            json={},
            timeout=10.0,
        )
        if response.status_code == 200:
            return response.json().get("jwt")
    except Exception as e:
        import sys
        print(f"Warning: Failed to get token from Clerk: {e}", file=sys.stderr)
    return None


def get_test_token() -> Optional[str]:
    """
    Get test user JWT token.

    Priority:
    1. TEST_USER_TOKEN environment variable (if set)
    2. Auto-generate using test_jwt_generator (no Clerk login needed!)
    3. Clerk API (requires active session - fallback)

    For option 2, Railway Staging must have TEST_JWT_PUBLIC_KEY configured.
    """
    # First check environment variable
    token = os.getenv(TokenEnvVars.USER_TOKEN)
    if token:
        return token

    # Auto-generate using test_jwt_generator (preferred - no Clerk login needed)
    # This works when Railway has TEST_JWT_PUBLIC_KEY configured
    try:
        return generate_free_token()
    except Exception as e:
        import sys
        print(f"Note: Using auto-generated test token (free tier)", file=sys.stderr)

    # Fallback: Try Clerk API (requires user to have logged in)
    try:
        from .get_test_token import get_test_token as clerk_generate_token
        token = clerk_generate_token()
        if token:
            return token
    except ImportError:
        pass
    except Exception as e:
        import sys
        print(f"Warning: Clerk token generation failed: {e}", file=sys.stderr)

    return None


def get_admin_token() -> Optional[str]:
    """
    Get admin user JWT token.

    Priority:
    1. TEST_ADMIN_TOKEN environment variable
    2. Auto-generate using test_jwt_generator (no Clerk login needed!)
    3. Clerk API with TEST_ADMIN_SESSION_ID (fallback)

    Returns:
        Admin JWT token or None
    """
    # First check environment variable
    token = os.getenv(TokenEnvVars.ADMIN_TOKEN)
    if token:
        return token

    # Auto-generate using test_jwt_generator (preferred)
    try:
        return generate_admin_token()
    except Exception:
        pass

    # Fallback: Try Clerk API
    clerk_secret = os.getenv(TokenEnvVars.CLERK_SECRET_KEY)
    session_id = os.getenv(TokenEnvVars.ADMIN_SESSION_ID)

    if clerk_secret and session_id:
        return _get_token_from_clerk(session_id, clerk_secret)

    if clerk_secret and TestUsers.ADMIN.get("clerk_session_id"):
        return _get_token_from_clerk(TestUsers.ADMIN["clerk_session_id"], clerk_secret)

    return None


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture(scope="session")
def staging_base_url() -> str:
    """Staging API base URL."""
    return STAGING_BASE_URL


@pytest.fixture(scope="session")
def api_v2_url(staging_base_url) -> str:
    """Full API v2 URL."""
    return f"{staging_base_url}{API_V2_PREFIX}"


@pytest.fixture(scope="module")
def test_token() -> str:
    """
    Get test user token.

    Uses module scope to refresh token for each test module,
    avoiding token expiration issues (Clerk tokens expire in 60s).

    Raises pytest.skip if token not configured.
    """
    token = get_test_token()
    if not token:
        pytest.skip(
            "TEST_USER_TOKEN not set and auto-generation failed. "
            "Please ensure you have logged in to staging frontend.\n"
            "Or set: export TEST_USER_TOKEN='eyJhbG...'"
        )
    return token


@pytest.fixture(scope="module")
def auth_headers(test_token) -> dict:
    """Authorization headers for authenticated requests."""
    return {
        "Authorization": f"Bearer {test_token}",
        "Content-Type": "application/json",
    }


@pytest.fixture(scope="session")
def sync_client() -> Generator[httpx.Client, None, None]:
    """
    Synchronous HTTP client for staging API.

    Uses session scope for connection reuse.
    """
    with httpx.Client(timeout=30.0) as client:
        yield client


@pytest.fixture(scope="module")
def auth_client(test_token, staging_base_url) -> Generator[httpx.Client, None, None]:
    """
    Authenticated synchronous HTTP client.

    Pre-configured with Authorization header and base URL.
    Uses module scope to refresh token per module (Clerk tokens expire in 60s).
    """
    headers = {
        "Authorization": f"Bearer {test_token}",
        "Content-Type": "application/json",
    }
    with httpx.Client(
        base_url=staging_base_url,
        timeout=30.0,
        headers=headers,
    ) as client:
        yield client


@pytest.fixture(scope="session")
def anon_client(staging_base_url) -> Generator[httpx.Client, None, None]:
    """
    Anonymous (unauthenticated) HTTP client.

    For testing endpoints without authentication.
    """
    headers = {
        "Content-Type": "application/json",
    }
    with httpx.Client(
        base_url=staging_base_url,
        timeout=30.0,
        headers=headers,
    ) as client:
        yield client


# ==========================================
# Admin Fixtures
# ==========================================

@pytest.fixture(scope="module")
def admin_token() -> str:
    """
    Get admin user token.

    Uses module scope to refresh token for each test module.
    Raises pytest.skip if admin token not configured.

    Admin user: willnzy@gmail.com (user_38J7ztkfxMPma40Q5FQ2ryO80eg)
    """
    token = get_admin_token()
    if not token:
        pytest.skip(
            "Admin token not configured. Set one of:\n"
            "  - TEST_ADMIN_TOKEN environment variable\n"
            "  - CLERK_SECRET_KEY + TEST_ADMIN_SESSION_ID"
        )
    return token


@pytest.fixture(scope="module")
def admin_client(admin_token, staging_base_url) -> Generator[httpx.Client, None, None]:
    """
    Authenticated admin HTTP client.

    Pre-configured with admin Authorization header and base URL.
    Uses module scope to refresh token per module.
    """
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json",
    }
    with httpx.Client(
        base_url=staging_base_url,
        timeout=30.0,
        headers=headers,
    ) as client:
        yield client


@pytest.fixture(scope="module")
def admin_user_info() -> dict:
    """
    Get admin user static information.

    Returns configured admin user details from test_users.py.
    """
    return TestUsers.ADMIN.copy()


# ==========================================
# Tier-specific Fixtures (t2 Starter, t3 Pro)
# ==========================================

def get_starter_token() -> Optional[str]:
    """Get Starter (t2) user JWT token."""
    token = os.getenv(TokenEnvVars.STARTER_TOKEN)
    if token:
        return token

    # Auto-generate using test_jwt_generator (preferred)
    try:
        return generate_starter_token()
    except Exception:
        pass

    # Fallback: Clerk API
    clerk_secret = os.getenv(TokenEnvVars.CLERK_SECRET_KEY)
    session_id = os.getenv(TokenEnvVars.STARTER_SESSION_ID)

    if clerk_secret and session_id:
        return _get_token_from_clerk(session_id, clerk_secret)

    return None


def get_pro_token() -> Optional[str]:
    """Get Pro (t3) user JWT token."""
    token = os.getenv(TokenEnvVars.PRO_TOKEN)
    if token:
        return token

    # Auto-generate using test_jwt_generator (preferred)
    try:
        return generate_pro_token()
    except Exception:
        pass

    # Fallback: Clerk API
    clerk_secret = os.getenv(TokenEnvVars.CLERK_SECRET_KEY)
    session_id = os.getenv(TokenEnvVars.PRO_SESSION_ID)

    if clerk_secret and session_id:
        return _get_token_from_clerk(session_id, clerk_secret)

    return None


@pytest.fixture(scope="module")
def starter_token() -> str:
    """
    Get Starter (t2) user token.

    Raises pytest.skip if not configured.
    """
    token = get_starter_token()
    if not token:
        pytest.skip(
            "Starter (t2) token not configured. Set:\n"
            "  - TEST_STARTER_TOKEN environment variable\n"
            "  - Or CLERK_SECRET_KEY + TEST_STARTER_SESSION_ID"
        )
    return token


@pytest.fixture(scope="module")
def pro_token() -> str:
    """
    Get Pro (t3) user token.

    Raises pytest.skip if not configured.
    """
    token = get_pro_token()
    if not token:
        pytest.skip(
            "Pro (t3) token not configured. Set:\n"
            "  - TEST_PRO_TOKEN environment variable\n"
            "  - Or CLERK_SECRET_KEY + TEST_PRO_SESSION_ID"
        )
    return token


@pytest.fixture(scope="module")
def starter_client(starter_token, staging_base_url) -> Generator[httpx.Client, None, None]:
    """
    Authenticated Starter (t2) tier HTTP client.

    For testing features available to paid Starter users.
    """
    headers = {
        "Authorization": f"Bearer {starter_token}",
        "Content-Type": "application/json",
    }
    with httpx.Client(
        base_url=staging_base_url,
        timeout=30.0,
        headers=headers,
    ) as client:
        yield client


@pytest.fixture(scope="module")
def pro_client(pro_token, staging_base_url) -> Generator[httpx.Client, None, None]:
    """
    Authenticated Pro (t3) tier HTTP client.

    For testing features available to Pro users.
    """
    headers = {
        "Authorization": f"Bearer {pro_token}",
        "Content-Type": "application/json",
    }
    with httpx.Client(
        base_url=staging_base_url,
        timeout=30.0,
        headers=headers,
    ) as client:
        yield client


@pytest.fixture
async def async_client(staging_base_url) -> httpx.AsyncClient:
    """
    Asynchronous HTTP client for staging API.

    For async test functions.
    """
    async with httpx.AsyncClient(
        base_url=staging_base_url,
        timeout=30.0,
    ) as client:
        yield client


@pytest.fixture(scope="module")
async def async_auth_client(test_token, staging_base_url) -> httpx.AsyncClient:
    """
    Authenticated asynchronous HTTP client.
    Uses module scope to refresh token per module.
    """
    headers = {
        "Authorization": f"Bearer {test_token}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(
        base_url=staging_base_url,
        timeout=30.0,
        headers=headers,
    ) as client:
        yield client


# ==========================================
# Helper Functions
# ==========================================

def assert_success_response(response: httpx.Response, expected_status: int = 200):
    """Assert response is successful with expected status."""
    assert response.status_code == expected_status, (
        f"Expected {expected_status}, got {response.status_code}. "
        f"Response: {response.text[:500]}"
    )


def assert_json_response(response: httpx.Response) -> dict:
    """Assert response is valid JSON and return data."""
    assert response.headers.get("content-type", "").startswith("application/json"), (
        f"Expected JSON response, got {response.headers.get('content-type')}"
    )
    return response.json()


def assert_error_response(
    response: httpx.Response,
    expected_status: int,
    expected_detail: Optional[str] = None,
):
    """Assert response is an error with expected status and optional detail."""
    assert response.status_code == expected_status, (
        f"Expected {expected_status}, got {response.status_code}. "
        f"Response: {response.text[:500]}"
    )
    if expected_detail:
        data = response.json()
        assert expected_detail in str(data.get("detail", "")), (
            f"Expected detail containing '{expected_detail}', got {data}"
        )
