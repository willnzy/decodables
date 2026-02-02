"""
Tests for AuthService — Core authentication orchestration.

Covers:
- Registration 3-step OTP (send OTP, verify OTP, complete registration)
- Login (success, wrong credentials, lockout, disabled account)
- Token refresh (rotation, reuse detection, grace period, expired)
- Logout (single, all devices)
- Password reset via OTP (send, verify, reset)
- Password change
- Authenticated OTP (change-password, delete-account)
- Session management (list, revoke, limit enforcement)
- Account deletion (after OTP verification, no password)
"""

import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from domains.auth.aggregates.auth_user import AuthUser
from domains.auth.aggregates.session import Session
from domains.auth.constants import (
    OTP_EXPIRE_MINUTES,
    OTP_MAX_ATTEMPTS,
    OTP_PURPOSE_CHANGE_PASSWORD,
    OTP_PURPOSE_DELETE_ACCOUNT,
    OTP_PURPOSE_FORGOT_PASSWORD,
    OTP_PURPOSE_REGISTER,
)
from domains.auth.exceptions import (
    AccountDisabledException,
    AccountLockedException,
    DisposableEmailException,
    EmailAlreadyExistsException,
    InvalidCredentialsException,
    OtpCooldownException,
    OtpExpiredException,
    OtpInvalidException,
    OtpMaxAttemptsException,
    SessionNotFoundException,
    TokenExpiredException,
    TokenReuseDetectedException,
    TokenRevokedException,
    WeakPasswordException,
)
from domains.auth.service import AuthService
from domains.auth.value_objects import DeviceInfo

from .conftest import TEST_EMAIL, TEST_PASSWORD, TEST_USER_ID


# ===========================================================================
# Registration — 3-Step OTP
# ===========================================================================

class TestSendRegistrationOtp:
    """Step 1: Send OTP for registration."""

    @pytest.mark.asyncio
    async def test_send_otp_success_new_user(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        mock_email_service,
        token_service,
    ):
        """First-time email creates pending user and sends OTP email."""
        pending_user = AuthUser.create_pending(
            email=TEST_EMAIL,
            otp_code_hash="hashed_otp",
            otp_purpose=OTP_PURPOSE_REGISTER,
            otp_expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            user_id=TEST_USER_ID,
        )
        mock_auth_user_repo.create_pending.return_value = (pending_user, True)
        mock_auth_user_repo.get_restorable_by_email.return_value = None

        result = await auth_service.send_registration_otp(email=TEST_EMAIL)

        assert result["email"] == TEST_EMAIL
        assert "user_id" in result
        assert result["has_restorable_account"] is False
        mock_auth_user_repo.create_pending.assert_awaited_once()
        mock_email_service.send_otp_email.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_otp_duplicate_registered_email_raises(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
    ):
        """Registered email raises EmailAlreadyExistsException."""
        registered_user = AuthUser.create_registered(
            email=TEST_EMAIL, password_hash="hashed", user_id=TEST_USER_ID,
        )
        mock_auth_user_repo.get_restorable_by_email.return_value = None
        mock_auth_user_repo.create_pending.return_value = (registered_user, False)

        with pytest.raises(EmailAlreadyExistsException):
            await auth_service.send_registration_otp(email=TEST_EMAIL)

    @pytest.mark.asyncio
    async def test_send_otp_disposable_email_raises(
        self,
        auth_service: AuthService,
    ):
        """Disposable email domain is rejected."""
        with pytest.raises(DisposableEmailException):
            await auth_service.send_registration_otp(email="test@mailinator.com")

    @pytest.mark.asyncio
    async def test_send_otp_invalid_email_raises(
        self,
        auth_service: AuthService,
    ):
        """Invalid email format raises ValueError."""
        with pytest.raises(ValueError):
            await auth_service.send_registration_otp(email="not-an-email")

    @pytest.mark.asyncio
    async def test_send_otp_resend_within_cooldown_raises(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
    ):
        """Resending OTP within cooldown window raises OtpCooldownException."""
        # Pending user with valid OTP set recently (within cooldown)
        pending_user = AuthUser.create_pending(
            email=TEST_EMAIL,
            otp_code_hash="existing_hash",
            otp_purpose=OTP_PURPOSE_REGISTER,
            otp_expires_at=datetime.now(timezone.utc) + timedelta(minutes=9, seconds=50),
            user_id=TEST_USER_ID,
        )
        mock_auth_user_repo.get_restorable_by_email.return_value = None
        mock_auth_user_repo.create_pending.return_value = (pending_user, False)

        with pytest.raises(OtpCooldownException):
            await auth_service.send_registration_otp(email=TEST_EMAIL)

    @pytest.mark.asyncio
    async def test_send_otp_resend_after_cooldown_succeeds(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        mock_email_service,
    ):
        """Resending OTP after cooldown expires updates OTP and sends email."""
        # Pending user with OTP set 2 minutes ago (past cooldown)
        pending_user = AuthUser.create_pending(
            email=TEST_EMAIL,
            otp_code_hash="old_hash",
            otp_purpose=OTP_PURPOSE_REGISTER,
            otp_expires_at=datetime.now(timezone.utc) + timedelta(minutes=8),
            user_id=TEST_USER_ID,
        )
        mock_auth_user_repo.get_restorable_by_email.return_value = None
        mock_auth_user_repo.create_pending.return_value = (pending_user, False)
        mock_auth_user_repo.get_by_id.return_value = pending_user

        result = await auth_service.send_registration_otp(email=TEST_EMAIL)

        assert result["email"] == TEST_EMAIL
        mock_auth_user_repo.update_otp.assert_awaited_once()
        mock_email_service.send_otp_email.assert_awaited_once()


class TestVerifyRegistrationOtp:
    """Step 2: Verify the OTP code."""

    @pytest.mark.asyncio
    async def test_verify_otp_success(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        token_service,
    ):
        """Correct OTP code returns user_id and otp_verified=True."""
        otp_code, otp_hash = token_service.generate_otp()
        pending_user = AuthUser.create_pending(
            email=TEST_EMAIL,
            otp_code_hash=otp_hash,
            otp_purpose=OTP_PURPOSE_REGISTER,
            otp_expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            user_id=TEST_USER_ID,
        )
        mock_auth_user_repo.get_by_email.return_value = pending_user

        result = await auth_service.verify_registration_otp(
            email=TEST_EMAIL, otp_code=otp_code,
        )

        assert result["otp_verified"] is True
        assert result["user_id"] == str(TEST_USER_ID)

    @pytest.mark.asyncio
    async def test_verify_otp_wrong_code_raises(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        token_service,
    ):
        """Wrong OTP code raises OtpInvalidException and increments attempts."""
        otp_code, otp_hash = token_service.generate_otp()
        pending_user = AuthUser.create_pending(
            email=TEST_EMAIL,
            otp_code_hash=otp_hash,
            otp_purpose=OTP_PURPOSE_REGISTER,
            otp_expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            user_id=TEST_USER_ID,
        )
        mock_auth_user_repo.get_by_email.return_value = pending_user

        with pytest.raises(OtpInvalidException):
            await auth_service.verify_registration_otp(
                email=TEST_EMAIL, otp_code="000000",
            )

        mock_auth_user_repo.update_otp_attempts.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_verify_otp_expired_raises(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        token_service,
    ):
        """Expired OTP raises OtpExpiredException."""
        otp_code, otp_hash = token_service.generate_otp()
        pending_user = AuthUser.create_pending(
            email=TEST_EMAIL,
            otp_code_hash=otp_hash,
            otp_purpose=OTP_PURPOSE_REGISTER,
            otp_expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            user_id=TEST_USER_ID,
        )
        mock_auth_user_repo.get_by_email.return_value = pending_user

        with pytest.raises(OtpExpiredException):
            await auth_service.verify_registration_otp(
                email=TEST_EMAIL, otp_code=otp_code,
            )

    @pytest.mark.asyncio
    async def test_verify_otp_max_attempts_raises(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        token_service,
    ):
        """Max attempts reached raises OtpMaxAttemptsException."""
        otp_code, otp_hash = token_service.generate_otp()
        pending_user = AuthUser.create_pending(
            email=TEST_EMAIL,
            otp_code_hash=otp_hash,
            otp_purpose=OTP_PURPOSE_REGISTER,
            otp_expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            user_id=TEST_USER_ID,
        )
        pending_user.otp_attempts = OTP_MAX_ATTEMPTS  # Already at max
        mock_auth_user_repo.get_by_email.return_value = pending_user

        with pytest.raises(OtpMaxAttemptsException):
            await auth_service.verify_registration_otp(
                email=TEST_EMAIL, otp_code=otp_code,
            )

    @pytest.mark.asyncio
    async def test_verify_otp_unknown_email_raises(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
    ):
        """Unknown email raises OtpInvalidException."""
        mock_auth_user_repo.get_by_email.return_value = None

        with pytest.raises(OtpInvalidException):
            await auth_service.verify_registration_otp(
                email="unknown@example.com", otp_code="123456",
            )

    @pytest.mark.asyncio
    async def test_verify_otp_registered_user_raises(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
    ):
        """Already registered user raises OtpInvalidException."""
        registered_user = AuthUser.create_registered(
            email=TEST_EMAIL, password_hash="hashed", user_id=TEST_USER_ID,
        )
        mock_auth_user_repo.get_by_email.return_value = registered_user

        with pytest.raises(OtpInvalidException):
            await auth_service.verify_registration_otp(
                email=TEST_EMAIL, otp_code="123456",
            )


class TestCompleteRegistration:
    """Step 3: Set password and complete registration."""

    @pytest.mark.asyncio
    async def test_complete_registration_success(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        mock_session_repo,
        token_service,
    ):
        """Valid completion returns tokens and user info."""
        pending_user = AuthUser.create_pending(
            email=TEST_EMAIL,
            otp_code_hash="verified_hash",
            otp_purpose=OTP_PURPOSE_REGISTER,
            otp_expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            user_id=TEST_USER_ID,
        )
        completed_user = AuthUser.create_registered(
            email=TEST_EMAIL, password_hash="hashed", user_id=TEST_USER_ID,
        )
        mock_auth_user_repo.get_by_id.return_value = pending_user
        mock_auth_user_repo.complete_registration.return_value = completed_user

        result = await auth_service.complete_registration(
            user_id=str(TEST_USER_ID),
            password=TEST_PASSWORD,
        )

        assert "access_token" in result
        assert "refresh_token" in result
        assert result["token_type"] == "bearer"
        assert result["user"]["email"] == TEST_EMAIL
        mock_auth_user_repo.complete_registration.assert_awaited_once()
        mock_session_repo.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_complete_registration_weak_password_raises(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
    ):
        """Weak password raises WeakPasswordException."""
        pending_user = AuthUser.create_pending(
            email=TEST_EMAIL,
            otp_code_hash="verified_hash",
            otp_purpose=OTP_PURPOSE_REGISTER,
            otp_expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            user_id=TEST_USER_ID,
        )
        mock_auth_user_repo.get_by_id.return_value = pending_user

        with pytest.raises(WeakPasswordException):
            await auth_service.complete_registration(
                user_id=str(TEST_USER_ID),
                password="weak",
            )

    @pytest.mark.asyncio
    async def test_complete_registration_already_registered_raises(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
    ):
        """Already registered user raises OtpInvalidException."""
        registered_user = AuthUser.create_registered(
            email=TEST_EMAIL, password_hash="hashed", user_id=TEST_USER_ID,
        )
        mock_auth_user_repo.get_by_id.return_value = registered_user

        with pytest.raises(OtpInvalidException):
            await auth_service.complete_registration(
                user_id=str(TEST_USER_ID),
                password=TEST_PASSWORD,
            )

    @pytest.mark.asyncio
    async def test_complete_registration_unknown_user_raises(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
    ):
        """Non-existent user raises OtpInvalidException."""
        mock_auth_user_repo.get_by_id.return_value = None

        with pytest.raises(OtpInvalidException):
            await auth_service.complete_registration(
                user_id=str(TEST_USER_ID),
                password=TEST_PASSWORD,
            )

    @pytest.mark.asyncio
    async def test_complete_registration_with_device_info(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        mock_session_repo,
        test_device_info: DeviceInfo,
    ):
        """Device info is passed through to session creation."""
        pending_user = AuthUser.create_pending(
            email=TEST_EMAIL,
            otp_code_hash="verified_hash",
            otp_purpose=OTP_PURPOSE_REGISTER,
            otp_expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            user_id=TEST_USER_ID,
        )
        completed_user = AuthUser.create_registered(
            email=TEST_EMAIL, password_hash="hashed", user_id=TEST_USER_ID,
        )
        mock_auth_user_repo.get_by_id.return_value = pending_user
        mock_auth_user_repo.complete_registration.return_value = completed_user

        result = await auth_service.complete_registration(
            user_id=str(TEST_USER_ID),
            password=TEST_PASSWORD,
            device_info=test_device_info,
        )

        assert "access_token" in result
        mock_session_repo.create.assert_awaited_once()


# ===========================================================================
# Login
# ===========================================================================

class TestLogin:

    @pytest.mark.asyncio
    async def test_login_success(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        mock_session_repo,
        password_service,
    ):
        """Successful login with correct credentials."""
        real_hash = password_service.hash_password(TEST_PASSWORD)
        auth_user = AuthUser(
            id=TEST_USER_ID,
            email=TEST_EMAIL,
            password_hash=real_hash,
            is_active=True,
        )
        mock_auth_user_repo.get_by_email.return_value = auth_user
        mock_session_repo.count_active_by_user.return_value = 0

        result = await auth_service.login(
            email=TEST_EMAIL,
            password=TEST_PASSWORD,
        )

        assert "access_token" in result
        assert "refresh_token" in result
        mock_auth_user_repo.record_login.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_login_wrong_email_raises(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
    ):
        """Non-existent email raises InvalidCredentialsException."""
        mock_auth_user_repo.get_by_email.return_value = None

        with pytest.raises(InvalidCredentialsException):
            await auth_service.login(
                email="unknown@example.com",
                password=TEST_PASSWORD,
            )

    @pytest.mark.asyncio
    async def test_login_wrong_password_raises(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        password_service,
    ):
        """Wrong password raises InvalidCredentialsException and records failure."""
        real_hash = password_service.hash_password(TEST_PASSWORD)
        auth_user = AuthUser(
            id=TEST_USER_ID,
            email=TEST_EMAIL,
            password_hash=real_hash,
            is_active=True,
        )
        mock_auth_user_repo.get_by_email.return_value = auth_user

        with pytest.raises(InvalidCredentialsException):
            await auth_service.login(
                email=TEST_EMAIL,
                password="WrongPassword1",
            )

        # Should record the failed attempt
        mock_auth_user_repo.update_login_attempt.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_login_locked_account_raises(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        locked_auth_user: AuthUser,
    ):
        """Locked account raises AccountLockedException."""
        mock_auth_user_repo.get_by_email.return_value = locked_auth_user

        with pytest.raises(AccountLockedException):
            await auth_service.login(
                email=TEST_EMAIL,
                password=TEST_PASSWORD,
            )

    @pytest.mark.asyncio
    async def test_login_disabled_account_raises(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        disabled_auth_user: AuthUser,
    ):
        """Disabled account raises AccountDisabledException."""
        mock_auth_user_repo.get_by_email.return_value = disabled_auth_user

        with pytest.raises(AccountDisabledException):
            await auth_service.login(
                email=TEST_EMAIL,
                password=TEST_PASSWORD,
            )

    @pytest.mark.asyncio
    async def test_login_pending_user_raises(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        pending_auth_user: AuthUser,
    ):
        """Pending user (no password set) cannot login."""
        mock_auth_user_repo.get_by_email.return_value = pending_auth_user

        with pytest.raises(InvalidCredentialsException):
            await auth_service.login(
                email=TEST_EMAIL,
                password=TEST_PASSWORD,
            )

    @pytest.mark.asyncio
    async def test_login_enforces_session_limit(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        mock_session_repo,
        password_service,
    ):
        """Login should enforce max session limit when exceeded."""
        real_hash = password_service.hash_password(TEST_PASSWORD)
        auth_user = AuthUser(
            id=TEST_USER_ID, email=TEST_EMAIL,
            password_hash=real_hash, is_active=True,
        )
        mock_auth_user_repo.get_by_email.return_value = auth_user
        # 10 active sessions = at limit
        mock_session_repo.count_active_by_user.return_value = 10

        result = await auth_service.login(email=TEST_EMAIL, password=TEST_PASSWORD)

        assert "access_token" in result
        mock_session_repo.revoke_oldest_by_user.assert_awaited_once()


# ===========================================================================
# Token Refresh
# ===========================================================================

class TestRefreshToken:

    @pytest.mark.asyncio
    async def test_refresh_with_rotation(
        self,
        auth_service: AuthService,
        mock_session_repo,
        mock_auth_user_repo,
        test_session: Session,
        test_auth_user: AuthUser,
    ):
        """Refresh with rotation revokes old session and creates new one."""
        mock_session_repo.get_by_token_hash.return_value = test_session
        mock_auth_user_repo.get_by_id.return_value = test_auth_user

        result = await auth_service.refresh_token(
            refresh_token="test-refresh-token",
            rotate=True,
        )

        assert "access_token" in result
        assert "refresh_token" in result
        mock_session_repo.revoke.assert_awaited_once()
        mock_session_repo.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_refresh_without_rotation(
        self,
        auth_service: AuthService,
        mock_session_repo,
        mock_auth_user_repo,
        test_session: Session,
        test_auth_user: AuthUser,
    ):
        """Refresh without rotation just issues new access token."""
        mock_session_repo.get_by_token_hash.return_value = test_session
        mock_auth_user_repo.get_by_id.return_value = test_auth_user

        result = await auth_service.refresh_token(
            refresh_token="test-refresh-token",
            rotate=False,
        )

        assert "access_token" in result
        # No rotation: no revoke, no create
        mock_session_repo.revoke.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_refresh_revoked_token_raises(
        self,
        auth_service: AuthService,
        mock_session_repo,
    ):
        """Revoked token (not within grace period) triggers reuse detection."""
        session = Session.create_new(
            user_id=TEST_USER_ID,
            refresh_token_hash=hashlib.sha256(b"old-token").hexdigest(),
        )
        # Revoke and push revoked_at far back (past grace period)
        session.is_revoked = True
        session.revoked_at = datetime.now(timezone.utc) - timedelta(seconds=10)
        session.revoke_reason = "rotation"

        mock_session_repo.get_by_token_hash.return_value = session

        with pytest.raises(TokenReuseDetectedException):
            await auth_service.refresh_token(refresh_token="old-token")

        # Should revoke entire family
        mock_session_repo.revoke_family.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_refresh_expired_token_raises(
        self,
        auth_service: AuthService,
        mock_session_repo,
        expired_session: Session,
    ):
        """Expired session raises TokenExpiredException."""
        mock_session_repo.get_by_token_hash.return_value = expired_session

        with pytest.raises(TokenExpiredException):
            await auth_service.refresh_token(refresh_token="expired-token")

    @pytest.mark.asyncio
    async def test_refresh_unknown_token_raises(
        self,
        auth_service: AuthService,
        mock_session_repo,
    ):
        """Unknown refresh token raises TokenRevokedException."""
        mock_session_repo.get_by_token_hash.return_value = None

        with pytest.raises(TokenRevokedException):
            await auth_service.refresh_token(refresh_token="unknown-token")


# ===========================================================================
# Logout
# ===========================================================================

class TestLogout:

    @pytest.mark.asyncio
    async def test_logout_revokes_session(
        self,
        auth_service: AuthService,
        mock_session_repo,
        test_session: Session,
    ):
        """Logout revokes the matching session."""
        mock_session_repo.get_by_token_hash.return_value = test_session

        await auth_service.logout(refresh_token="test-refresh-token")

        mock_session_repo.revoke.assert_awaited_once_with(
            session_id=test_session.id,
            reason="logout",
        )

    @pytest.mark.asyncio
    async def test_logout_unknown_token_no_error(
        self,
        auth_service: AuthService,
        mock_session_repo,
    ):
        """Logout with unknown token should not raise."""
        mock_session_repo.get_by_token_hash.return_value = None
        await auth_service.logout(refresh_token="unknown-token")
        mock_session_repo.revoke.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_logout_all(
        self,
        auth_service: AuthService,
        mock_session_repo,
    ):
        """Logout all revokes all user sessions."""
        await auth_service.logout_all(user_id=TEST_USER_ID)
        mock_session_repo.revoke_all_by_user.assert_awaited_once_with(
            user_id=TEST_USER_ID,
            reason="logout",
        )


# ===========================================================================
# Password Reset via OTP
# ===========================================================================

class TestPasswordResetOtp:

    @pytest.mark.asyncio
    async def test_send_reset_otp_for_existing_user(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        mock_email_service,
        verified_auth_user: AuthUser,
    ):
        """Send OTP for existing user sends email and returns generic message."""
        mock_auth_user_repo.get_by_email.return_value = verified_auth_user

        result = await auth_service.send_password_reset_otp(email=TEST_EMAIL)

        assert "message" in result
        mock_auth_user_repo.update_otp.assert_awaited_once()
        mock_email_service.send_otp_email.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_reset_otp_unknown_email_silent(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        mock_email_service,
    ):
        """Unknown email returns generic message (no email sent, no error)."""
        mock_auth_user_repo.get_by_email.return_value = None

        result = await auth_service.send_password_reset_otp(
            email="unknown@example.com",
        )

        assert "message" in result
        mock_email_service.send_otp_email.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_send_reset_otp_pending_user_silent(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        mock_email_service,
        pending_auth_user: AuthUser,
    ):
        """Pending user (not registered) returns generic message silently."""
        mock_auth_user_repo.get_by_email.return_value = pending_auth_user

        result = await auth_service.send_password_reset_otp(email=TEST_EMAIL)

        assert "message" in result
        mock_email_service.send_otp_email.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_verify_reset_otp_success(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        token_service,
    ):
        """Correct OTP verifies and returns user_id."""
        otp_code, otp_hash = token_service.generate_otp()
        auth_user = AuthUser(
            id=TEST_USER_ID,
            email=TEST_EMAIL,
            password_hash="hashed",
            email_verified=True,
            otp_code_hash=otp_hash,
            otp_purpose=OTP_PURPOSE_FORGOT_PASSWORD,
            otp_expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            otp_attempts=0,
        )
        mock_auth_user_repo.get_by_email.return_value = auth_user

        result = await auth_service.verify_password_reset_otp(
            email=TEST_EMAIL, otp_code=otp_code,
        )

        assert result["otp_verified"] is True
        assert result["user_id"] == str(TEST_USER_ID)

    @pytest.mark.asyncio
    async def test_verify_reset_otp_wrong_code_raises(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        token_service,
    ):
        """Wrong OTP code raises OtpInvalidException."""
        otp_code, otp_hash = token_service.generate_otp()
        auth_user = AuthUser(
            id=TEST_USER_ID,
            email=TEST_EMAIL,
            password_hash="hashed",
            otp_code_hash=otp_hash,
            otp_purpose=OTP_PURPOSE_FORGOT_PASSWORD,
            otp_expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            otp_attempts=0,
        )
        mock_auth_user_repo.get_by_email.return_value = auth_user

        with pytest.raises(OtpInvalidException):
            await auth_service.verify_password_reset_otp(
                email=TEST_EMAIL, otp_code="000000",
            )

        mock_auth_user_repo.update_otp_attempts.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_verify_reset_otp_expired_raises(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        token_service,
    ):
        """Expired OTP raises OtpExpiredException."""
        otp_code, otp_hash = token_service.generate_otp()
        auth_user = AuthUser(
            id=TEST_USER_ID,
            email=TEST_EMAIL,
            password_hash="hashed",
            otp_code_hash=otp_hash,
            otp_purpose=OTP_PURPOSE_FORGOT_PASSWORD,
            otp_expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            otp_attempts=0,
        )
        mock_auth_user_repo.get_by_email.return_value = auth_user

        with pytest.raises(OtpExpiredException):
            await auth_service.verify_password_reset_otp(
                email=TEST_EMAIL, otp_code=otp_code,
            )

    @pytest.mark.asyncio
    async def test_reset_password_success(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        mock_session_repo,
    ):
        """Valid reset updates password and revokes all sessions."""
        auth_user = AuthUser(
            id=TEST_USER_ID,
            email=TEST_EMAIL,
            password_hash="old_hash",
        )
        mock_auth_user_repo.get_by_id.return_value = auth_user

        await auth_service.reset_password(
            user_id=str(TEST_USER_ID),
            new_password="NewStrong1Pass",
        )

        mock_auth_user_repo.update_password.assert_awaited_once()
        mock_session_repo.revoke_all_by_user.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_reset_password_weak_raises(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
    ):
        """Weak new password raises before hitting repository."""
        auth_user = AuthUser(
            id=TEST_USER_ID, email=TEST_EMAIL, password_hash="old",
        )
        mock_auth_user_repo.get_by_id.return_value = auth_user

        with pytest.raises(WeakPasswordException):
            await auth_service.reset_password(
                user_id=str(TEST_USER_ID), new_password="weak",
            )

    @pytest.mark.asyncio
    async def test_reset_password_unknown_user_raises(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
    ):
        """Non-existent user raises InvalidCredentialsException."""
        mock_auth_user_repo.get_by_id.return_value = None

        with pytest.raises(InvalidCredentialsException):
            await auth_service.reset_password(
                user_id=str(TEST_USER_ID), new_password="NewStrong1Pass",
            )


# ===========================================================================
# Change Password
# ===========================================================================

class TestChangePassword:

    @pytest.mark.asyncio
    async def test_change_password_success(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        mock_session_repo,
        password_service,
    ):
        """Change password with correct current password succeeds."""
        current_hash = password_service.hash_password(TEST_PASSWORD)
        auth_user = AuthUser(
            id=TEST_USER_ID,
            email=TEST_EMAIL,
            password_hash=current_hash,
        )
        mock_auth_user_repo.get_by_id.return_value = auth_user

        await auth_service.change_password(
            user_id=TEST_USER_ID,
            current_password=TEST_PASSWORD,
            new_password="NewStrong1Pass",
        )

        mock_auth_user_repo.update_password.assert_awaited_once()
        mock_session_repo.revoke_all_by_user.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_change_password_wrong_current_raises(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        password_service,
    ):
        """Wrong current password raises InvalidCredentialsException."""
        current_hash = password_service.hash_password(TEST_PASSWORD)
        auth_user = AuthUser(
            id=TEST_USER_ID,
            email=TEST_EMAIL,
            password_hash=current_hash,
        )
        mock_auth_user_repo.get_by_id.return_value = auth_user

        with pytest.raises(InvalidCredentialsException):
            await auth_service.change_password(
                user_id=TEST_USER_ID,
                current_password="WrongPass1",
                new_password="NewStrong1Pass",
            )

    @pytest.mark.asyncio
    async def test_change_password_weak_new_raises(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        password_service,
    ):
        """Weak new password raises WeakPasswordException."""
        current_hash = password_service.hash_password(TEST_PASSWORD)
        auth_user = AuthUser(
            id=TEST_USER_ID,
            email=TEST_EMAIL,
            password_hash=current_hash,
        )
        mock_auth_user_repo.get_by_id.return_value = auth_user

        with pytest.raises(WeakPasswordException):
            await auth_service.change_password(
                user_id=TEST_USER_ID,
                current_password=TEST_PASSWORD,
                new_password="weak",
            )

    @pytest.mark.asyncio
    async def test_change_password_no_revoke_option(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        mock_session_repo,
        password_service,
    ):
        """Can opt out of revoking other sessions."""
        current_hash = password_service.hash_password(TEST_PASSWORD)
        auth_user = AuthUser(
            id=TEST_USER_ID, email=TEST_EMAIL, password_hash=current_hash,
        )
        mock_auth_user_repo.get_by_id.return_value = auth_user

        await auth_service.change_password(
            user_id=TEST_USER_ID,
            current_password=TEST_PASSWORD,
            new_password="NewStrong1Pass",
            revoke_other_sessions=False,
        )

        mock_session_repo.revoke_all_by_user.assert_not_awaited()


# ===========================================================================
# Authenticated OTP (change-password / delete-account)
# ===========================================================================

class TestAuthenticatedOtp:

    @pytest.mark.asyncio
    async def test_send_change_password_otp(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        mock_email_service,
        verified_auth_user: AuthUser,
    ):
        """Send change-password OTP stores OTP and sends email."""
        mock_auth_user_repo.get_by_id.return_value = verified_auth_user

        await auth_service.send_change_password_otp(user_id=TEST_USER_ID)

        mock_auth_user_repo.update_otp.assert_awaited_once()
        mock_email_service.send_otp_email.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_delete_account_otp(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        mock_email_service,
        verified_auth_user: AuthUser,
    ):
        """Send delete-account OTP stores OTP and sends email."""
        mock_auth_user_repo.get_by_id.return_value = verified_auth_user

        await auth_service.send_delete_account_otp(user_id=TEST_USER_ID)

        mock_auth_user_repo.update_otp.assert_awaited_once()
        mock_email_service.send_otp_email.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_otp_pending_user_raises(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        pending_auth_user: AuthUser,
    ):
        """Pending user cannot request authenticated OTP."""
        mock_auth_user_repo.get_by_id.return_value = pending_auth_user

        with pytest.raises(InvalidCredentialsException):
            await auth_service.send_change_password_otp(user_id=TEST_USER_ID)

    @pytest.mark.asyncio
    async def test_send_otp_cooldown_raises(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
    ):
        """OTP sent within cooldown raises OtpCooldownException."""
        auth_user = AuthUser(
            id=TEST_USER_ID,
            email=TEST_EMAIL,
            password_hash="hashed",
            otp_code_hash="existing_hash",
            otp_purpose=OTP_PURPOSE_CHANGE_PASSWORD,
            # Set 10 seconds ago (within 60s cooldown)
            otp_expires_at=datetime.now(timezone.utc) + timedelta(minutes=9, seconds=50),
            otp_attempts=0,
        )
        mock_auth_user_repo.get_by_id.return_value = auth_user

        with pytest.raises(OtpCooldownException):
            await auth_service.send_change_password_otp(user_id=TEST_USER_ID)

    @pytest.mark.asyncio
    async def test_verify_authenticated_otp_success(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        token_service,
    ):
        """Correct OTP verifies and clears OTP fields."""
        otp_code, otp_hash = token_service.generate_otp()
        auth_user = AuthUser(
            id=TEST_USER_ID,
            email=TEST_EMAIL,
            password_hash="hashed",
            otp_code_hash=otp_hash,
            otp_purpose=OTP_PURPOSE_CHANGE_PASSWORD,
            otp_expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            otp_attempts=0,
        )
        mock_auth_user_repo.get_by_id.return_value = auth_user

        result = await auth_service.verify_authenticated_otp(
            user_id=TEST_USER_ID,
            otp_code=otp_code,
            expected_purpose=OTP_PURPOSE_CHANGE_PASSWORD,
        )

        assert result["otp_verified"] is True
        mock_auth_user_repo.clear_otp.assert_awaited_once_with(TEST_USER_ID)

    @pytest.mark.asyncio
    async def test_verify_authenticated_otp_wrong_purpose_raises(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        token_service,
    ):
        """Wrong OTP purpose raises OtpInvalidException."""
        otp_code, otp_hash = token_service.generate_otp()
        auth_user = AuthUser(
            id=TEST_USER_ID,
            email=TEST_EMAIL,
            password_hash="hashed",
            otp_code_hash=otp_hash,
            otp_purpose=OTP_PURPOSE_DELETE_ACCOUNT,  # Different purpose
            otp_expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            otp_attempts=0,
        )
        mock_auth_user_repo.get_by_id.return_value = auth_user

        with pytest.raises(OtpInvalidException):
            await auth_service.verify_authenticated_otp(
                user_id=TEST_USER_ID,
                otp_code=otp_code,
                expected_purpose=OTP_PURPOSE_CHANGE_PASSWORD,
            )

    @pytest.mark.asyncio
    async def test_verify_authenticated_otp_wrong_code_increments(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        token_service,
    ):
        """Wrong OTP code increments attempts and raises."""
        otp_code, otp_hash = token_service.generate_otp()
        auth_user = AuthUser(
            id=TEST_USER_ID,
            email=TEST_EMAIL,
            password_hash="hashed",
            otp_code_hash=otp_hash,
            otp_purpose=OTP_PURPOSE_CHANGE_PASSWORD,
            otp_expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            otp_attempts=0,
        )
        mock_auth_user_repo.get_by_id.return_value = auth_user

        with pytest.raises(OtpInvalidException):
            await auth_service.verify_authenticated_otp(
                user_id=TEST_USER_ID,
                otp_code="000000",
                expected_purpose=OTP_PURPOSE_CHANGE_PASSWORD,
            )

        mock_auth_user_repo.update_otp_attempts.assert_awaited_once()


# ===========================================================================
# Session Management
# ===========================================================================

class TestSessionManagement:

    @pytest.mark.asyncio
    async def test_get_sessions(
        self,
        auth_service: AuthService,
        mock_session_repo,
    ):
        """Get sessions returns list of session dicts."""
        sessions = [
            Session.create_new(user_id=TEST_USER_ID, refresh_token_hash="h1"),
            Session.create_new(user_id=TEST_USER_ID, refresh_token_hash="h2"),
        ]
        mock_session_repo.get_active_by_user.return_value = sessions

        result = await auth_service.get_sessions(user_id=TEST_USER_ID)

        assert len(result) == 2
        assert "id" in result[0]
        assert "device_name" in result[0]

    @pytest.mark.asyncio
    async def test_revoke_session_success(
        self,
        auth_service: AuthService,
        mock_session_repo,
    ):
        """Revoke a specific session owned by the user."""
        session_id = uuid4()
        session = Session.create_new(
            user_id=TEST_USER_ID, refresh_token_hash="h",
        )
        session.id = session_id
        mock_session_repo.get_active_by_user.return_value = [session]

        await auth_service.revoke_session(
            user_id=TEST_USER_ID,
            session_id=session_id,
        )

        mock_session_repo.revoke.assert_awaited_once_with(
            session_id=session_id,
            reason="logout",
        )

    @pytest.mark.asyncio
    async def test_revoke_session_not_found_raises(
        self,
        auth_service: AuthService,
        mock_session_repo,
    ):
        """Revoking a non-existent session raises SessionNotFoundException."""
        mock_session_repo.get_active_by_user.return_value = []

        with pytest.raises(SessionNotFoundException):
            await auth_service.revoke_session(
                user_id=TEST_USER_ID,
                session_id=uuid4(),
            )


# ===========================================================================
# Account Deletion
# ===========================================================================

class TestDeleteAccount:

    @pytest.mark.asyncio
    async def test_delete_account_success(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        mock_session_repo,
    ):
        """Delete account (after OTP verification) revokes sessions and deletes."""
        auth_user = AuthUser(
            id=TEST_USER_ID, email=TEST_EMAIL, password_hash="hashed",
        )
        mock_auth_user_repo.get_by_id.return_value = auth_user

        await auth_service.delete_account(user_id=TEST_USER_ID)

        mock_session_repo.revoke_all_by_user.assert_awaited_once()
        mock_auth_user_repo.delete.assert_awaited_once_with(TEST_USER_ID)

    @pytest.mark.asyncio
    async def test_delete_account_unknown_user_raises(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
    ):
        """Non-existent user raises InvalidCredentialsException."""
        mock_auth_user_repo.get_by_id.return_value = None

        with pytest.raises(InvalidCredentialsException):
            await auth_service.delete_account(user_id=TEST_USER_ID)
