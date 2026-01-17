"""
Staging Environment Test Configuration

Fixtures for testing against the actual staging API.
Requires TEST_USER_TOKEN environment variable.

@module tests.integration.staging.conftest
"""

import os
import pytest
import httpx
from typing import Generator, Optional


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


# ==========================================
# Configuration
# ==========================================

STAGING_BASE_URL = "https://decodables-staging.up.railway.app"
API_V2_PREFIX = "/api/v2"


def get_test_token() -> Optional[str]:
    """
    Get test user JWT token.

    Priority:
    1. TEST_USER_TOKEN environment variable (if set)
    2. Auto-generate using Clerk API (requires active session)

    For auto-generation, the test user must have logged in to staging
    at least once (to have an active session).
    """
    # First check environment variable
    token = os.getenv("TEST_USER_TOKEN")
    if token:
        return token

    # Try to auto-generate token using Clerk API
    try:
        from .get_test_token import get_test_token as generate_token
        token = generate_token()
        if token:
            return token
    except ImportError:
        pass  # Script not available
    except Exception as e:
        import sys
        print(f"Warning: Failed to auto-generate token: {e}", file=sys.stderr)

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
