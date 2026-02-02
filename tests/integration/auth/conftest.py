"""
Integration test fixtures for Auth API.

Uses FastAPI test client with dependency overrides
for auth_service and token_service.
"""

import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from domains.auth.aggregates.auth_user import AuthUser
from domains.auth.aggregates.session import Session
from domains.auth.password_service import PasswordService
from domains.auth.service import AuthService
from domains.auth.token_service import TokenService
from domains.auth.value_objects import DeviceInfo

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_JWT_SECRET = "integration_test_secret_key_that_is_long_enough_43"
TEST_USER_ID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
TEST_EMAIL = "integration@test.com"
TEST_PASSWORD = "IntegrationP@ss1"
TEST_PASSWORD_HASH = "$argon2id$v=19$m=65536,t=3,p=4$test_salt$test_hash"


# ---------------------------------------------------------------------------
# Real services for integration
# ---------------------------------------------------------------------------

@pytest.fixture
def int_password_service() -> PasswordService:
    return PasswordService()


@pytest.fixture
def int_token_service() -> TokenService:
    return TokenService(jwt_secret=TEST_JWT_SECRET)


@pytest.fixture
def int_auth_token(int_token_service: TokenService) -> str:
    """A valid access token for authenticated endpoints."""
    return int_token_service.create_access_token(
        user_id=TEST_USER_ID,
        email=TEST_EMAIL,
        role="user",
        tier="t1",
    )


# ---------------------------------------------------------------------------
# Mock repositories
# ---------------------------------------------------------------------------

@pytest.fixture
def int_mock_auth_user_repo():
    repo = AsyncMock()
    # Query methods
    repo.get_by_id = AsyncMock(return_value=None)
    repo.get_by_email = AsyncMock(return_value=None)
    repo.get_restorable_by_email = AsyncMock(return_value=None)
    # Registration (3-step OTP)
    repo.create_pending = AsyncMock()
    repo.complete_registration = AsyncMock()
    # OTP methods
    repo.update_otp = AsyncMock()
    repo.update_otp_attempts = AsyncMock()
    repo.clear_otp = AsyncMock()
    # Password & account
    repo.update_password = AsyncMock()
    repo.update_email_verified = AsyncMock()
    repo.update_login_attempt = AsyncMock()
    repo.record_login = AsyncMock()
    repo.delete = AsyncMock()
    # Account restore
    repo.restore_account = AsyncMock()
    return repo


@pytest.fixture
def int_mock_session_repo():
    repo = AsyncMock()
    repo.get_by_token_hash = AsyncMock(return_value=None)
    repo.get_active_by_user = AsyncMock(return_value=[])
    repo.count_active_by_user = AsyncMock(return_value=0)
    repo.create = AsyncMock()
    repo.revoke = AsyncMock()
    repo.revoke_family = AsyncMock()
    repo.revoke_all_by_user = AsyncMock()
    repo.revoke_oldest_by_user = AsyncMock()
    repo.update_last_used = AsyncMock()
    return repo


@pytest.fixture
def int_mock_email_service():
    service = MagicMock()
    service.send_otp_email = AsyncMock(return_value=True)
    return service


# ---------------------------------------------------------------------------
# AuthService with mock repos but real password/token services
# ---------------------------------------------------------------------------

@pytest.fixture
def int_auth_service(
    int_mock_auth_user_repo,
    int_mock_session_repo,
    int_password_service,
    int_token_service,
    int_mock_email_service,
) -> AuthService:
    return AuthService(
        auth_user_repository=int_mock_auth_user_repo,
        session_repository=int_mock_session_repo,
        password_service=int_password_service,
        token_service=int_token_service,
        email_service=int_mock_email_service,
    )


# ---------------------------------------------------------------------------
# FastAPI test app with dependency overrides
# ---------------------------------------------------------------------------

@pytest.fixture
def int_app(int_auth_service, int_token_service):
    """Create a FastAPI app with auth router and overridden dependencies."""
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address

    from core.exceptions.base import AppException
    import infrastructure.rate_limiter as rl_module

    # Replace the global limiter with an in-memory one (no Redis needed)
    original_limiter = rl_module.limiter
    test_limiter = Limiter(key_func=get_remote_address, enabled=False)
    rl_module.limiter = test_limiter

    app = FastAPI()
    app.state.limiter = test_limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Register AppException handler (mirrors app.py)
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.default_code,
                "message": str(exc),
            },
        )

    # Import and include the auth router
    from api.auth.router import router, get_auth_service, get_current_auth_user_id, get_token_service

    # Patch the router's limiter reference
    import api.auth.router as auth_router_module
    auth_router_module.limiter = test_limiter

    app.include_router(router)

    # Override auth service dependency
    async def override_auth_service():
        return int_auth_service

    app.dependency_overrides[get_auth_service] = override_auth_service

    # Override current user dependency for protected endpoints
    async def override_current_user():
        return TEST_USER_ID

    app.dependency_overrides[get_current_auth_user_id] = override_current_user

    # Override token service dependency
    async def override_token_service():
        return int_token_service

    app.dependency_overrides[get_token_service] = override_token_service

    yield app

    # Restore original limiter
    rl_module.limiter = original_limiter
    auth_router_module.limiter = original_limiter


@pytest_asyncio.fixture
async def client(int_app) -> AsyncClient:
    """Async test client for the FastAPI app."""
    transport = ASGITransport(app=int_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_client(int_app, int_auth_token) -> AsyncClient:
    """Authenticated async test client."""
    transport = ASGITransport(app=int_app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {int_auth_token}"},
    ) as ac:
        yield ac
