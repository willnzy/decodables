"""
Tests for AuthService — Core authentication orchestration.

Covers:
- Registration (success, duplicate email, disposable email, weak password)
- Login (success, wrong credentials, lockout, disabled account)
- Token refresh (rotation, reuse detection, grace period, expired)
- Logout (single, all devices)
- Email verification
- Password reset and change
- Session management (list, revoke, limit enforcement)
- Account deletion
"""

import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from domains.auth.aggregates.auth_user import AuthUser
from domains.auth.aggregates.session import Session
from domains.auth.exceptions import (
    AccountDisabledException,
    AccountLockedException,
    DisposableEmailException,
    EmailAlreadyExistsException,
    InvalidCredentialsException,
    InvalidVerificationTokenException,
    TokenExpiredException,
    TokenReuseDetectedException,
    TokenRevokedException,
    WeakPasswordException,
)
from domains.auth.service import AuthService
from domains.auth.value_objects import DeviceInfo

from .conftest import TEST_EMAIL, TEST_PASSWORD, TEST_USER_ID


# ===========================================================================
# Registration
# ===========================================================================

class TestRegister:

    @pytest.mark.asyncio
    async def test_register_success(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        mock_session_repo,
        mock_email_service,
    ):
        """Successful registration returns tokens and user info."""
        # Mock: create returns (user, True) meaning new user created
        created_user = AuthUser.create_new(
            email=TEST_EMAIL,
            password_hash="hashed",
            user_id=TEST_USER_ID,
        )
        mock_auth_user_repo.create.return_value = (created_user, True)
        mock_session_repo.create.return_value = None

        result = await auth_service.register(
            email=TEST_EMAIL,
            password=TEST_PASSWORD,
        )

        assert "access_token" in result
        assert "refresh_token" in result
        assert result["token_type"] == "bearer"
        assert result["user"]["email"] == TEST_EMAIL
        mock_auth_user_repo.create.assert_awaited_once()
        mock_email_service.send_verification_email.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_register_duplicate_email_raises(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
    ):
        """Registering with existing email raises EmailAlreadyExistsException."""
        mock_auth_user_repo.create.return_value = (
            AuthUser.create_new(email=TEST_EMAIL, password_hash="h"),
            False,  # Not created — email exists
        )

        with pytest.raises(EmailAlreadyExistsException):
            await auth_service.register(
                email=TEST_EMAIL,
                password=TEST_PASSWORD,
            )

    @pytest.mark.asyncio
    async def test_register_weak_password_raises(self, auth_service: AuthService):
        """Weak password should raise before hitting repository."""
        with pytest.raises(WeakPasswordException):
            await auth_service.register(
                email="new@example.com",
                password="weak",  # Too short, missing uppercase, etc.
            )

    @pytest.mark.asyncio
    async def test_register_disposable_email_raises(self, auth_service: AuthService):
        """Disposable email domain should be rejected."""
        with pytest.raises(DisposableEmailException):
            await auth_service.register(
                email="test@mailinator.com",
                password=TEST_PASSWORD,
            )

    @pytest.mark.asyncio
    async def test_register_invalid_email_raises(self, auth_service: AuthService):
        """Invalid email format should raise ValueError."""
        with pytest.raises(ValueError):
            await auth_service.register(
                email="not-an-email",
                password=TEST_PASSWORD,
            )

    @pytest.mark.asyncio
    async def test_register_with_device_info(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        mock_session_repo,
        test_device_info: DeviceInfo,
    ):
        """Registration with device info passes it to session creation."""
        created_user = AuthUser.create_new(
            email=TEST_EMAIL, password_hash="h", user_id=TEST_USER_ID,
        )
        mock_auth_user_repo.create.return_value = (created_user, True)

        result = await auth_service.register(
            email=TEST_EMAIL,
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
        token_hash = test_session.refresh_token_hash
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
# Email Verification
# ===========================================================================

class TestVerifyEmail:

    @pytest.mark.asyncio
    async def test_verify_email_success(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        token_service,
    ):
        """Valid verification token marks email as verified."""
        plaintext, token_hash = token_service.create_secure_token()
        auth_user = AuthUser(
            id=TEST_USER_ID,
            email=TEST_EMAIL,
            password_hash="hashed",
            email_verified=False,
            email_verification_token=token_hash,
            email_verification_expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        mock_auth_user_repo.get_by_email.return_value = auth_user

        result = await auth_service.verify_email(token=plaintext, email=TEST_EMAIL)

        assert result is True
        mock_auth_user_repo.update_email_verified.assert_awaited_once_with(
            user_id=TEST_USER_ID,
            verified=True,
        )

    @pytest.mark.asyncio
    async def test_verify_email_already_verified(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        verified_auth_user: AuthUser,
    ):
        """Already verified email returns True without update."""
        mock_auth_user_repo.get_by_email.return_value = verified_auth_user

        result = await auth_service.verify_email(token="any-token", email=TEST_EMAIL)
        assert result is True
        mock_auth_user_repo.update_email_verified.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_verify_email_wrong_token_raises(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
    ):
        """Wrong verification token raises InvalidVerificationTokenException."""
        auth_user = AuthUser(
            id=TEST_USER_ID,
            email=TEST_EMAIL,
            password_hash="hashed",
            email_verified=False,
            email_verification_token="stored_hash",
            email_verification_expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        mock_auth_user_repo.get_by_email.return_value = auth_user

        with pytest.raises(InvalidVerificationTokenException):
            await auth_service.verify_email(token="wrong-token", email=TEST_EMAIL)

    @pytest.mark.asyncio
    async def test_verify_email_expired_token_raises(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        token_service,
    ):
        """Expired verification token raises."""
        plaintext, token_hash = token_service.create_secure_token()
        auth_user = AuthUser(
            id=TEST_USER_ID,
            email=TEST_EMAIL,
            password_hash="hashed",
            email_verified=False,
            email_verification_token=token_hash,
            email_verification_expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        mock_auth_user_repo.get_by_email.return_value = auth_user

        with pytest.raises(InvalidVerificationTokenException):
            await auth_service.verify_email(token=plaintext, email=TEST_EMAIL)

    @pytest.mark.asyncio
    async def test_verify_email_unknown_email_raises(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
    ):
        """Unknown email raises InvalidVerificationTokenException."""
        mock_auth_user_repo.get_by_email.return_value = None

        with pytest.raises(InvalidVerificationTokenException):
            await auth_service.verify_email(token="any", email="unknown@example.com")


# ===========================================================================
# Password Reset
# ===========================================================================

class TestPasswordReset:

    @pytest.mark.asyncio
    async def test_request_password_reset_sends_email(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        mock_email_service,
        test_auth_user: AuthUser,
    ):
        """Request password reset for existing user sends email."""
        mock_auth_user_repo.get_by_email.return_value = test_auth_user

        await auth_service.request_password_reset(email=TEST_EMAIL)

        mock_auth_user_repo.set_password_reset_token.assert_awaited_once()
        mock_email_service.send_password_reset_email.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_request_password_reset_unknown_email_silent(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        mock_email_service,
    ):
        """Unknown email should NOT raise (prevent email enumeration)."""
        mock_auth_user_repo.get_by_email.return_value = None

        await auth_service.request_password_reset(email="unknown@example.com")

        mock_email_service.send_password_reset_email.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_reset_password_success(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        mock_session_repo,
        token_service,
    ):
        """Valid reset token updates password and revokes all sessions."""
        plaintext, token_hash = token_service.create_secure_token()
        auth_user = AuthUser(
            id=TEST_USER_ID,
            email=TEST_EMAIL,
            password_hash="old_hash",
            password_reset_token=token_hash,
            password_reset_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        mock_auth_user_repo.get_by_email.return_value = auth_user

        new_password = "NewStrong1Pass"
        await auth_service.reset_password(
            token=plaintext,
            email=TEST_EMAIL,
            new_password=new_password,
        )

        mock_auth_user_repo.update_password.assert_awaited_once()
        mock_session_repo.revoke_all_by_user.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_reset_password_weak_new_password_raises(
        self,
        auth_service: AuthService,
    ):
        """Weak new password raises before token verification."""
        with pytest.raises(WeakPasswordException):
            await auth_service.reset_password(
                token="any", email=TEST_EMAIL, new_password="weak",
            )

    @pytest.mark.asyncio
    async def test_reset_password_invalid_token_raises(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
    ):
        """Wrong reset token raises InvalidVerificationTokenException."""
        auth_user = AuthUser(
            id=TEST_USER_ID,
            email=TEST_EMAIL,
            password_hash="old",
            password_reset_token="stored_hash",
            password_reset_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        mock_auth_user_repo.get_by_email.return_value = auth_user

        with pytest.raises(InvalidVerificationTokenException):
            await auth_service.reset_password(
                token="wrong-token", email=TEST_EMAIL, new_password="NewStrong1",
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
        from domains.auth.exceptions import SessionNotFoundException

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
        password_service,
    ):
        """Delete account verifies password then deletes."""
        real_hash = password_service.hash_password(TEST_PASSWORD)
        auth_user = AuthUser(
            id=TEST_USER_ID, email=TEST_EMAIL, password_hash=real_hash,
        )
        mock_auth_user_repo.get_by_id.return_value = auth_user

        await auth_service.delete_account(
            user_id=TEST_USER_ID,
            password=TEST_PASSWORD,
        )

        mock_session_repo.revoke_all_by_user.assert_awaited_once()
        mock_auth_user_repo.delete.assert_awaited_once_with(TEST_USER_ID)

    @pytest.mark.asyncio
    async def test_delete_account_wrong_password_raises(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
        password_service,
    ):
        """Wrong password prevents deletion."""
        real_hash = password_service.hash_password(TEST_PASSWORD)
        auth_user = AuthUser(
            id=TEST_USER_ID, email=TEST_EMAIL, password_hash=real_hash,
        )
        mock_auth_user_repo.get_by_id.return_value = auth_user

        with pytest.raises(InvalidCredentialsException):
            await auth_service.delete_account(
                user_id=TEST_USER_ID,
                password="WrongPassword1",
            )

        mock_auth_user_repo.delete.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_account_unknown_user_raises(
        self,
        auth_service: AuthService,
        mock_auth_user_repo,
    ):
        """Non-existent user raises InvalidCredentialsException."""
        mock_auth_user_repo.get_by_id.return_value = None

        with pytest.raises(InvalidCredentialsException):
            await auth_service.delete_account(
                user_id=TEST_USER_ID,
                password=TEST_PASSWORD,
            )
