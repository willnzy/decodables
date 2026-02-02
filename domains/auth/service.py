"""
AuthService — Core authentication orchestration service.

Coordinates all authentication operations: register, login, token refresh,
logout, email verification, password reset, session management, and
account deletion.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from starlette.concurrency import run_in_threadpool

from .aggregates.auth_user import AuthUser
from .aggregates.session import Session
from .constants import (
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS,
    MAX_ACTIVE_SESSIONS,
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS,
    REVOKE_REASON_LOGOUT,
    REVOKE_REASON_ROTATION,
    REVOKE_REASON_SECURITY,
    REVOKE_REASON_SESSION_LIMIT,
)
from .email_service import EmailService
from .exceptions import (
    AccountDisabledException,
    AccountLockedException,
    DisposableEmailException,
    EmailAlreadyExistsException,
    EmailNotVerifiedException,
    InvalidCredentialsException,
    InvalidVerificationTokenException,
    SessionNotFoundException,
    TokenExpiredException,
    TokenReuseDetectedException,
    TokenRevokedException,
    WeakPasswordException,
)
from .password_service import PasswordService
from .repository import IAuthUserRepository, ISessionRepository
from .token_service import TokenService
from .value_objects import DeviceInfo, Email, PasswordStrength

logger = logging.getLogger(__name__)

# Disposable email domain blacklist (common ones)
# For production, consider using the `disposable-email-domains` package
DISPOSABLE_EMAIL_DOMAINS: frozenset = frozenset({
    "mailinator.com", "tempmail.com", "guerrillamail.com", "throwaway.email",
    "yopmail.com", "sharklasers.com", "grr.la", "guerrillamailblock.com",
    "pokemail.net", "spam4.me", "trashmail.com", "trashmail.me",
    "dispostable.com", "maildrop.cc", "fakeinbox.com", "getnada.com",
    "tempail.com", "temp-mail.org", "minutemail.com", "emailondeck.com",
    "mohmal.com", "burnermail.io", "10minutemail.com", "harakirimail.com",
    "mailnesia.com", "tempr.email", "discard.email", "mailsac.com",
})


class AuthService:
    """
    Core authentication orchestration service.

    Coordinates:
    - User registration with atomic profile creation
    - Login with lockout protection
    - Token refresh with rotation and reuse detection
    - Logout (single / all devices)
    - Email verification
    - Password reset / change
    - Multi-device session management
    - Account deletion
    """

    def __init__(
        self,
        auth_user_repository: IAuthUserRepository,
        session_repository: ISessionRepository,
        password_service: PasswordService,
        token_service: TokenService,
        email_service: EmailService,
    ) -> None:
        self._auth_user_repo = auth_user_repository
        self._session_repo = session_repository
        self._password_svc = password_service
        self._token_svc = token_service
        self._email_svc = email_service

    # ===================================================================
    # Registration
    # ===================================================================

    async def register(
        self,
        email: str,
        password: str,
        display_name: Optional[str] = None,
        device_info: Optional[DeviceInfo] = None,
        signup_bonus: int = 0,
    ) -> Dict[str, Any]:
        """
        Register a new user.

        Flow:
        1. Validate email format + disposable check
        2. Validate password strength
        3. Hash password (argon2id)
        4. Atomic create: auth_users + profiles (via RPC)
        5. Send verification email
        6. Create session + return tokens

        Args:
            email: User's email address.
            password: Plaintext password.
            display_name: Optional display name.
            device_info: Client device information.
            signup_bonus: Signup bonus credits.

        Returns:
            Dict with access_token, refresh_token, user info.

        Raises:
            WeakPasswordException: Password doesn't meet requirements.
            DisposableEmailException: Disposable email detected.
            EmailAlreadyExistsException: Email already registered.
        """
        # 1. Validate email
        validated_email = Email(email)
        self._check_disposable_email(validated_email.domain)

        # 2. Validate password strength
        strength = self._password_svc.validate_strength(password)
        if not strength.is_valid:
            raise WeakPasswordException(errors=list(strength.errors))

        # 3. Hash password (CPU-bound, run in threadpool)
        password_hash = await run_in_threadpool(
            self._password_svc.hash_password, password
        )

        # 4. Atomic create via RPC
        auth_user = AuthUser.create_new(
            email=validated_email.value,
            password_hash=password_hash,
        )

        created_user, was_created = await self._auth_user_repo.create(
            auth_user=auth_user,
            display_name=display_name,
            signup_bonus=signup_bonus,
        )

        if not was_created:
            # Email already exists — per design, return generic success
            # to prevent email enumeration. Send "already registered" hint
            # to the existing email instead.
            logger.info(f"Registration attempt for existing email: {validated_email.value}")
            raise EmailAlreadyExistsException()

        # 5. Send verification email (non-blocking, don't fail registration)
        await self._send_verification_email(created_user)

        # 6. Create session + tokens
        return await self._create_session_and_tokens(
            user=created_user,
            device_info=device_info,
        )

    # ===================================================================
    # Login
    # ===================================================================

    async def login(
        self,
        email: str,
        password: str,
        device_info: Optional[DeviceInfo] = None,
    ) -> Dict[str, Any]:
        """
        Authenticate user with email and password.

        Flow:
        1. Lookup user by email
        2. Check account lockout
        3. Verify password
        4. Record login + create session
        5. Enforce session limit

        Args:
            email: User's email.
            password: Plaintext password.
            device_info: Client device information.

        Returns:
            Dict with access_token, refresh_token, user info.

        Raises:
            InvalidCredentialsException: Wrong email or password.
            AccountLockedException: Too many failed attempts.
            AccountDisabledException: Account has been disabled.
        """
        # 1. Lookup user
        normalized_email = email.strip().lower()
        auth_user = await self._auth_user_repo.get_by_email(normalized_email)
        if auth_user is None:
            raise InvalidCredentialsException()

        # 2. Check account state
        if not auth_user.is_active:
            raise AccountDisabledException()

        if auth_user.is_locked:
            raise AccountLockedException(
                retry_after_seconds=auth_user.lockout_remaining_seconds
            )

        # 3. Verify password (CPU-bound)
        is_valid = await run_in_threadpool(
            self._password_svc.verify_password,
            password,
            auth_user.password_hash,
        )

        if not is_valid:
            # Record failure
            auth_user.record_failed_login()
            await self._auth_user_repo.update_login_attempt(
                user_id=auth_user.id,
                failed_attempts=auth_user.failed_login_attempts,
                locked_until=auth_user.locked_until,
            )
            raise InvalidCredentialsException()

        # 4. Record successful login
        ip_address = device_info.ip_address if device_info else None
        now = datetime.now(timezone.utc)
        auth_user.record_successful_login(ip_address=ip_address)
        await self._auth_user_repo.record_login(
            user_id=auth_user.id,
            ip_address=ip_address,
            timestamp=now,
        )

        # 5. Enforce session limit
        await self._enforce_session_limit(auth_user.id)

        # 6. Create session + tokens
        return await self._create_session_and_tokens(
            user=auth_user,
            device_info=device_info,
        )

    # ===================================================================
    # Token Refresh
    # ===================================================================

    async def refresh_token(
        self,
        refresh_token: str,
        device_info: Optional[DeviceInfo] = None,
        rotate: bool = True,
    ) -> Dict[str, Any]:
        """
        Refresh access token using a refresh token.

        Supports token rotation with reuse detection.

        Args:
            refresh_token: Plaintext refresh token from client.
            device_info: Client device information.
            rotate: Whether to rotate the refresh token (default True).

        Returns:
            Dict with access_token and optionally new refresh_token.

        Raises:
            TokenExpiredException: Refresh token expired.
            TokenRevokedException: Token was revoked.
            TokenReuseDetectedException: Reuse attack detected.
        """
        # Hash the token for lookup
        token_hash = self._token_svc.hash_refresh_token(refresh_token)

        # Find session
        session = await self._session_repo.get_by_token_hash(token_hash)
        if session is None:
            raise TokenRevokedException()

        # Check expiration
        if session.is_expired:
            raise TokenExpiredException()

        # Check revocation
        if session.is_revoked:
            # Check grace period for concurrent requests
            if session.is_within_grace_period:
                # Concurrent request — allow it, but don't rotate
                return await self._issue_tokens_for_session(session, rotate=False)

            # Reuse detected — revoke entire family
            logger.warning(
                f"Token reuse detected for user {session.user_id}, "
                f"family {session.family_id}. Revoking all family sessions."
            )
            await self._session_repo.revoke_family(
                family_id=session.family_id,
                reason=REVOKE_REASON_SECURITY,
            )
            raise TokenReuseDetectedException()

        # Update last_used
        await self._session_repo.update_last_used(session.id)

        if rotate:
            # Revoke old session
            await self._session_repo.revoke(
                session_id=session.id,
                reason=REVOKE_REASON_ROTATION,
            )

            # Create new session in same family
            new_plain, new_hash = self._token_svc.create_refresh_token()
            new_session = Session.create_rotated(
                parent=session,
                new_refresh_token_hash=new_hash,
                user_agent=device_info.user_agent if device_info else None,
                ip_address=device_info.ip_address if device_info else None,
                device_name=device_info.device_name if device_info else None,
            )
            await self._session_repo.create(new_session)

            # Issue new tokens
            auth_user = await self._auth_user_repo.get_by_id(session.user_id)
            if auth_user is None:
                raise TokenRevokedException()

            access_token = self._token_svc.create_access_token(
                user_id=auth_user.id,
                email=auth_user.email,
                role="user",  # TODO: get from profile
                tier="t1",    # TODO: get from profile
            )
            return {
                "access_token": access_token,
                "refresh_token": new_plain,
                "token_type": "bearer",
            }
        else:
            return await self._issue_tokens_for_session(session, rotate=False)

    # ===================================================================
    # Logout
    # ===================================================================

    async def logout(self, refresh_token: str) -> None:
        """
        Logout current session.

        Args:
            refresh_token: Plaintext refresh token from client.
        """
        token_hash = self._token_svc.hash_refresh_token(refresh_token)
        session = await self._session_repo.get_by_token_hash(token_hash)
        if session and not session.is_revoked:
            await self._session_repo.revoke(
                session_id=session.id,
                reason=REVOKE_REASON_LOGOUT,
            )

    async def logout_all(self, user_id: UUID) -> None:
        """
        Logout from all devices.

        Args:
            user_id: User's UUID.
        """
        await self._session_repo.revoke_all_by_user(
            user_id=user_id,
            reason=REVOKE_REASON_LOGOUT,
        )

    # ===================================================================
    # Email Verification
    # ===================================================================

    async def verify_email(self, token: str, email: str) -> bool:
        """
        Verify user's email address.

        Args:
            token: Plaintext verification token from email link.
            email: Email address to verify.

        Returns:
            True if verification successful.

        Raises:
            InvalidVerificationTokenException: Invalid or expired token.
        """
        normalized_email = email.strip().lower()
        auth_user = await self._auth_user_repo.get_by_email(normalized_email)

        if auth_user is None:
            raise InvalidVerificationTokenException()

        if auth_user.email_verified:
            return True  # Already verified

        # Compare token hash
        token_hash = self._token_svc.hash_token(token)
        if auth_user.email_verification_token != token_hash:
            raise InvalidVerificationTokenException()

        if not auth_user.is_verification_token_valid:
            raise InvalidVerificationTokenException(
                message="Verification token has expired. Please request a new one."
            )

        # Mark verified
        await self._auth_user_repo.update_email_verified(
            user_id=auth_user.id,
            verified=True,
        )

        return True

    async def resend_verification_email(self, user_id: UUID) -> bool:
        """
        Resend email verification link.

        Args:
            user_id: User's UUID.

        Returns:
            True if email was sent.
        """
        auth_user = await self._auth_user_repo.get_by_id(user_id)
        if auth_user is None or auth_user.email_verified:
            return False

        return await self._send_verification_email(auth_user)

    # ===================================================================
    # Password Reset
    # ===================================================================

    async def request_password_reset(self, email: str) -> None:
        """
        Request password reset email.

        Always returns success to prevent email enumeration.

        Args:
            email: Email address to send reset link to.
        """
        normalized_email = email.strip().lower()
        auth_user = await self._auth_user_repo.get_by_email(normalized_email)

        if auth_user is None:
            # Don't reveal whether email exists — return silently
            logger.info(f"Password reset requested for unknown email: {normalized_email}")
            return

        # Generate reset token
        plaintext, token_hash = self._token_svc.create_secure_token()
        expires_at = datetime.now(timezone.utc) + timedelta(
            hours=PASSWORD_RESET_TOKEN_EXPIRE_HOURS
        )

        # Store hash
        await self._auth_user_repo.set_password_reset_token(
            user_id=auth_user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        # Send email
        await self._email_svc.send_password_reset_email(
            to_email=auth_user.email,
            token_plaintext=plaintext,
        )

    async def reset_password(
        self,
        token: str,
        email: str,
        new_password: str,
    ) -> None:
        """
        Reset password using a reset token.

        Args:
            token: Plaintext reset token from email link.
            email: Email address.
            new_password: New plaintext password.

        Raises:
            InvalidVerificationTokenException: Invalid or expired token.
            WeakPasswordException: New password doesn't meet requirements.
        """
        # Validate password strength
        strength = self._password_svc.validate_strength(new_password)
        if not strength.is_valid:
            raise WeakPasswordException(errors=list(strength.errors))

        normalized_email = email.strip().lower()
        auth_user = await self._auth_user_repo.get_by_email(normalized_email)

        if auth_user is None:
            raise InvalidVerificationTokenException()

        # Verify token
        token_hash = self._token_svc.hash_token(token)
        if auth_user.password_reset_token != token_hash:
            raise InvalidVerificationTokenException()

        if not auth_user.is_reset_token_valid:
            raise InvalidVerificationTokenException(
                message="Reset token has expired. Please request a new one."
            )

        # Hash new password
        new_hash = await run_in_threadpool(
            self._password_svc.hash_password, new_password
        )

        # Update password
        await self._auth_user_repo.update_password(
            user_id=auth_user.id,
            password_hash=new_hash,
        )

        # Revoke all sessions (security: force re-login)
        await self._session_repo.revoke_all_by_user(
            user_id=auth_user.id,
            reason=REVOKE_REASON_SECURITY,
        )

    async def change_password(
        self,
        user_id: UUID,
        current_password: str,
        new_password: str,
        revoke_other_sessions: bool = True,
    ) -> None:
        """
        Change password (requires current password verification).

        Args:
            user_id: User's UUID.
            current_password: Current plaintext password.
            new_password: New plaintext password.
            revoke_other_sessions: Whether to revoke other sessions.

        Raises:
            InvalidCredentialsException: Current password is wrong.
            WeakPasswordException: New password doesn't meet requirements.
        """
        auth_user = await self._auth_user_repo.get_by_id(user_id)
        if auth_user is None:
            raise InvalidCredentialsException()

        # Verify current password
        is_valid = await run_in_threadpool(
            self._password_svc.verify_password,
            current_password,
            auth_user.password_hash,
        )
        if not is_valid:
            raise InvalidCredentialsException(
                message="Current password is incorrect"
            )

        # Validate new password
        strength = self._password_svc.validate_strength(new_password)
        if not strength.is_valid:
            raise WeakPasswordException(errors=list(strength.errors))

        # Hash and update
        new_hash = await run_in_threadpool(
            self._password_svc.hash_password, new_password
        )
        await self._auth_user_repo.update_password(
            user_id=user_id,
            password_hash=new_hash,
        )

        # Optionally revoke other sessions
        if revoke_other_sessions:
            await self._session_repo.revoke_all_by_user(
                user_id=user_id,
                reason=REVOKE_REASON_SECURITY,
            )

    # ===================================================================
    # Session Management
    # ===================================================================

    async def get_sessions(self, user_id: UUID) -> List[Dict[str, Any]]:
        """
        Get all active sessions for a user (multi-device management).

        Args:
            user_id: User's UUID.

        Returns:
            List of session dicts for API response.
        """
        sessions = await self._session_repo.get_active_by_user(user_id)
        return [s.to_dict() for s in sessions]

    async def revoke_session(
        self,
        user_id: UUID,
        session_id: UUID,
    ) -> None:
        """
        Revoke a specific session (kick a device).

        Args:
            user_id: User's UUID (for ownership verification).
            session_id: Session to revoke.

        Raises:
            SessionNotFoundException: Session not found or doesn't belong to user.
        """
        sessions = await self._session_repo.get_active_by_user(user_id)
        target = next((s for s in sessions if s.id == session_id), None)

        if target is None:
            raise SessionNotFoundException()

        await self._session_repo.revoke(
            session_id=session_id,
            reason=REVOKE_REASON_LOGOUT,
        )

    # ===================================================================
    # Account Deletion
    # ===================================================================

    async def delete_account(
        self,
        user_id: UUID,
        password: str,
    ) -> None:
        """
        Delete user account permanently.

        Flow:
        1. Verify password
        2. Revoke all sessions
        3. Hard delete auth_users (cascades to sessions)

        Note: Profile soft-delete and Stripe cancellation should be
        handled by the application layer before calling this method.

        Args:
            user_id: User's UUID.
            password: Current password for verification.

        Raises:
            InvalidCredentialsException: Wrong password.
        """
        auth_user = await self._auth_user_repo.get_by_id(user_id)
        if auth_user is None:
            raise InvalidCredentialsException()

        # Verify password
        is_valid = await run_in_threadpool(
            self._password_svc.verify_password,
            password,
            auth_user.password_hash,
        )
        if not is_valid:
            raise InvalidCredentialsException(
                message="Password verification failed"
            )

        # Revoke all sessions
        await self._session_repo.revoke_all_by_user(
            user_id=user_id,
            reason="account_deleted",
        )

        # Hard delete auth_users (cascades to auth_sessions)
        await self._auth_user_repo.delete(user_id)

        logger.info(f"Account deleted for user {user_id}")

    # ===================================================================
    # Internal Helpers
    # ===================================================================

    async def _create_session_and_tokens(
        self,
        user: AuthUser,
        device_info: Optional[DeviceInfo] = None,
    ) -> Dict[str, Any]:
        """Create a new session and return access + refresh tokens."""
        # Generate refresh token
        refresh_plain, refresh_hash = self._token_svc.create_refresh_token()

        # Create session
        session = Session.create_new(
            user_id=user.id,
            refresh_token_hash=refresh_hash,
            user_agent=device_info.user_agent if device_info else None,
            ip_address=device_info.ip_address if device_info else None,
            device_name=device_info.device_name if device_info else None,
        )
        await self._session_repo.create(session)

        # Create access token
        access_token = self._token_svc.create_access_token(
            user_id=user.id,
            email=user.email,
            role="user",  # TODO: get from profile via join or lookup
            tier="t1",    # TODO: get from profile via join or lookup
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_plain,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "email_verified": user.email_verified,
            },
        }

    async def _issue_tokens_for_session(
        self,
        session: Session,
        rotate: bool = False,
    ) -> Dict[str, Any]:
        """Issue tokens for an existing session (no rotation)."""
        auth_user = await self._auth_user_repo.get_by_id(session.user_id)
        if auth_user is None:
            raise TokenRevokedException()

        access_token = self._token_svc.create_access_token(
            user_id=auth_user.id,
            email=auth_user.email,
            role="user",  # TODO: get from profile
            tier="t1",    # TODO: get from profile
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
        }

    async def _send_verification_email(self, auth_user: AuthUser) -> bool:
        """Generate verification token and send email."""
        try:
            plaintext, token_hash = self._token_svc.create_secure_token()
            expires_at = datetime.now(timezone.utc) + timedelta(
                hours=EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS
            )

            await self._auth_user_repo.set_verification_token(
                user_id=auth_user.id,
                token_hash=token_hash,
                expires_at=expires_at,
            )

            return await self._email_svc.send_verification_email(
                to_email=auth_user.email,
                token_plaintext=plaintext,
            )
        except Exception:
            logger.exception(
                f"Failed to send verification email to {auth_user.email}"
            )
            return False

    async def _enforce_session_limit(self, user_id: UUID) -> None:
        """Enforce maximum concurrent session limit."""
        count = await self._session_repo.count_active_by_user(user_id)
        if count >= MAX_ACTIVE_SESSIONS:
            await self._session_repo.revoke_oldest_by_user(
                user_id=user_id,
                reason=REVOKE_REASON_SESSION_LIMIT,
            )

    @staticmethod
    def _check_disposable_email(domain: str) -> None:
        """
        Check if email domain is a known disposable email provider.

        Raises:
            DisposableEmailException: If domain is in blacklist.
        """
        if domain.lower() in DISPOSABLE_EMAIL_DOMAINS:
            raise DisposableEmailException()
