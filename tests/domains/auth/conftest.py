"""
Auth Domain Test Fixtures.

Provides reusable fixtures for testing auth services, aggregates,
and value objects. All database operations are mocked.
"""

import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from domains.auth.aggregates.auth_user import AuthUser
from domains.auth.aggregates.session import Session
from domains.auth.email_service import EmailService
from domains.auth.password_service import PasswordService
from domains.auth.service import AuthService
from domains.auth.token_service import TokenService
from domains.auth.value_objects import DeviceInfo

# ---------------------------------------------------------------------------
# Constants for testing
# ---------------------------------------------------------------------------

TEST_JWT_SECRET = "a" * 43  # Minimum length secret for testing
TEST_JWT_SECRET_OLD = "b" * 43
TEST_USER_ID = UUID("12345678-1234-1234-1234-123456789abc")
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "StrongP@ss1"
TEST_PASSWORD_HASH = "$argon2id$v=19$m=65536,t=3,p=4$fake_salt$fake_hash"
TEST_IP = "192.168.1.1"
TEST_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120.0"


# ---------------------------------------------------------------------------
# Service Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def password_service() -> PasswordService:
    """Real PasswordService (no external dependencies)."""
    return PasswordService()


@pytest.fixture
def token_service() -> TokenService:
    """Real TokenService with test secret."""
    return TokenService(
        jwt_secret=TEST_JWT_SECRET,
        jwt_secret_old=TEST_JWT_SECRET_OLD,
    )


@pytest.fixture
def token_service_single_key() -> TokenService:
    """TokenService with only current key (no dual-key rotation)."""
    return TokenService(jwt_secret=TEST_JWT_SECRET)


@pytest.fixture
def mock_email_service() -> EmailService:
    """Mock EmailService to avoid actual email sending."""
    service = MagicMock(spec=EmailService)
    service.send_verification_email = AsyncMock(return_value=True)
    service.send_password_reset_email = AsyncMock(return_value=True)
    return service


# ---------------------------------------------------------------------------
# Repository Mock Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_auth_user_repo():
    """Mock IAuthUserRepository."""
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.get_by_email = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.update_password = AsyncMock()
    repo.update_email_verified = AsyncMock()
    repo.update_login_attempt = AsyncMock()
    repo.set_verification_token = AsyncMock()
    repo.set_password_reset_token = AsyncMock()
    repo.clear_verification_token = AsyncMock()
    repo.clear_password_reset_token = AsyncMock()
    repo.record_login = AsyncMock()
    repo.delete = AsyncMock()
    return repo


@pytest.fixture
def mock_session_repo():
    """Mock ISessionRepository."""
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


# ---------------------------------------------------------------------------
# AuthService Fixture (fully assembled with mocks)
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_service(
    mock_auth_user_repo,
    mock_session_repo,
    password_service,
    token_service,
    mock_email_service,
) -> AuthService:
    """AuthService with real password/token services and mocked repos/email."""
    return AuthService(
        auth_user_repository=mock_auth_user_repo,
        session_repository=mock_session_repo,
        password_service=password_service,
        token_service=token_service,
        email_service=mock_email_service,
    )


# ---------------------------------------------------------------------------
# Domain Entity Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_auth_user() -> AuthUser:
    """A standard test AuthUser (active, unverified, no lockout)."""
    return AuthUser(
        id=TEST_USER_ID,
        email=TEST_EMAIL,
        password_hash=TEST_PASSWORD_HASH,
        email_verified=False,
        failed_login_attempts=0,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def verified_auth_user() -> AuthUser:
    """An AuthUser with verified email."""
    now = datetime.now(timezone.utc)
    return AuthUser(
        id=TEST_USER_ID,
        email=TEST_EMAIL,
        password_hash=TEST_PASSWORD_HASH,
        email_verified=True,
        email_verified_at=now - timedelta(days=1),
        failed_login_attempts=0,
        is_active=True,
        created_at=now - timedelta(days=7),
        updated_at=now,
    )


@pytest.fixture
def locked_auth_user() -> AuthUser:
    """An AuthUser with a locked account (too many failed attempts)."""
    return AuthUser(
        id=TEST_USER_ID,
        email=TEST_EMAIL,
        password_hash=TEST_PASSWORD_HASH,
        email_verified=True,
        failed_login_attempts=5,
        locked_until=datetime.now(timezone.utc) + timedelta(minutes=30),
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def disabled_auth_user() -> AuthUser:
    """An AuthUser with a disabled account."""
    return AuthUser(
        id=TEST_USER_ID,
        email=TEST_EMAIL,
        password_hash=TEST_PASSWORD_HASH,
        email_verified=True,
        failed_login_attempts=0,
        is_active=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def test_session() -> Session:
    """A standard active test Session."""
    return Session.create_new(
        user_id=TEST_USER_ID,
        refresh_token_hash=hashlib.sha256(b"test-refresh-token").hexdigest(),
    )


@pytest.fixture
def revoked_session() -> Session:
    """A revoked Session within grace period."""
    session = Session.create_new(
        user_id=TEST_USER_ID,
        refresh_token_hash=hashlib.sha256(b"old-refresh-token").hexdigest(),
    )
    session.revoke("rotation")
    return session


@pytest.fixture
def expired_session() -> Session:
    """An expired Session."""
    session = Session.create_new(
        user_id=TEST_USER_ID,
        refresh_token_hash=hashlib.sha256(b"expired-refresh-token").hexdigest(),
    )
    # Force expiration by setting expires_at to the past
    session.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    return session


@pytest.fixture
def test_device_info() -> DeviceInfo:
    """Standard test device info."""
    return DeviceInfo.from_request(
        user_agent=TEST_USER_AGENT,
        ip_address=TEST_IP,
    )
