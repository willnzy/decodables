"""
AuthService — Core authentication orchestration service.

Coordinates all authentication operations:
- 3-step OTP registration (send OTP → verify OTP → set password)
- Login with lockout protection
- Token refresh with rotation and reuse detection
- Logout (single / all devices)
- Password reset via OTP
- Password change
- Multi-device session management
- Account deletion (soft-delete with restore window)
- Account restoration
"""

from __future__ import annotations

import hmac
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from starlette.concurrency import run_in_threadpool

from .aggregates.auth_user import AuthUser
from .aggregates.session import Session
from .constants import (
    MAX_ACTIVE_SESSIONS,
    OTP_COOLDOWN_SECONDS,
    OTP_EXPIRE_MINUTES,
    OTP_PURPOSE_CHANGE_PASSWORD,
    OTP_PURPOSE_DELETE_ACCOUNT,
    OTP_PURPOSE_FORGOT_PASSWORD,
    OTP_PURPOSE_REGISTER,
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
from .password_service import PasswordService
from .repository import IAuthUserRepository, ISessionRepository
from .token_service import TokenService
from .value_objects import DeviceInfo, Email

# Import identity repository for role/tier lookup
from domains.identity.repository import IUserRepository

logger = logging.getLogger(__name__)


def _mask_email(email: str) -> str:
    """Mask email for log output: u***@example.com"""
    if "@" not in email:
        return "***"
    local, domain = email.rsplit("@", 1)
    return f"{local[0]}***@{domain}" if local else f"***@{domain}"


# Disposable email domain blacklist (common ones)
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
    - 3-step OTP registration (email → OTP → password)
    - Login with lockout protection
    - Token refresh with rotation and reuse detection
    - Logout (single / all devices)
    - Password reset via OTP
    - Password change
    - Multi-device session management
    - Account deletion + restoration
    """

    def __init__(
        self,
        auth_user_repository: IAuthUserRepository,
        session_repository: ISessionRepository,
        password_service: PasswordService,
        token_service: TokenService,
        email_service: EmailService,
        user_repository: Optional[IUserRepository] = None,
    ) -> None:
        self._auth_user_repo = auth_user_repository
        self._session_repo = session_repository
        self._password_svc = password_service
        self._token_svc = token_service
        self._email_svc = email_service
        self._user_repo = user_repository

    # ===================================================================
    # Internal Helpers
    # ===================================================================

    async def _get_user_role_tier(self, user_id: UUID) -> tuple[str, str]:
        """
        Look up the real role and tier from the user profile.

        Falls back to safe defaults ("user", "t1") if the profile
        repository is not injected or the profile is not found.
        """
        if self._user_repo is not None:
            profile = await self._user_repo.get_by_id(str(user_id))
            if profile is not None:
                role = profile.role.value if hasattr(profile.role, "value") else str(profile.role)
                tier = profile.tier.value if hasattr(profile.tier, "value") else str(profile.tier)
                return role, tier
        return "user", "t1"

    # ===================================================================
    # Registration — Step 1: Send OTP
    # ===================================================================

    async def send_registration_otp(
        self,
        email: str,
    ) -> Dict[str, Any]:
        """
        Registration step 1: Validate email and send OTP code.

        Flow:
        1. Validate email format + disposable check
        2. Check for restorable soft-deleted account
        3. Generate OTP + create pending auth_user via RPC
        4. Send OTP email

        Args:
            email: User's email address.

        Returns:
            Dict with user_id (for step 2) and has_restorable_account flag.

        Raises:
            DisposableEmailException: Disposable email detected.
            EmailAlreadyExistsException: Email already registered.
            AccountRestorableException: Soft-deleted account can be restored.
            OtpCooldownException: OTP sent too recently.
        """
        # 1. Validate email
        validated_email = Email(email)
        self._check_disposable_email(validated_email.domain)

        # 2. Check for restorable account
        has_restorable = False
        restorable = await self._auth_user_repo.get_restorable_by_email(
            validated_email.value
        )
        if restorable:
            has_restorable = True

        # 3. Generate OTP
        otp_code, otp_hash = self._token_svc.generate_otp()
        otp_expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=OTP_EXPIRE_MINUTES
        )

        # 4. Create pending user via RPC
        pending_user = AuthUser.create_pending(
            email=validated_email.value,
            otp_code_hash=otp_hash,
            otp_purpose=OTP_PURPOSE_REGISTER,
            otp_expires_at=otp_expires_at,
        )

        created_user, was_created = await self._auth_user_repo.create_pending(
            auth_user=pending_user,
        )

        if not was_created:
            # Email already fully registered
            if created_user.is_registered:
                raise EmailAlreadyExistsException()

            # Pending user exists — check cooldown then update OTP
            if created_user.is_otp_valid:
                # Check cooldown: if OTP was set recently, don't resend
                if created_user.otp_expires_at:
                    otp_set_at = created_user.otp_expires_at - timedelta(
                        minutes=OTP_EXPIRE_MINUTES
                    )
                    elapsed = (datetime.now(timezone.utc) - otp_set_at).total_seconds()
                    if elapsed < OTP_COOLDOWN_SECONDS:
                        remaining = int(OTP_COOLDOWN_SECONDS - elapsed)
                        raise OtpCooldownException(retry_after_seconds=remaining)

            # Resend: generate new OTP and update
            otp_code, otp_hash = self._token_svc.generate_otp()
            otp_expires_at = datetime.now(timezone.utc) + timedelta(
                minutes=OTP_EXPIRE_MINUTES
            )
            await self._auth_user_repo.update_otp(
                user_id=created_user.id,
                otp_code_hash=otp_hash,
                otp_purpose=OTP_PURPOSE_REGISTER,
                otp_expires_at=otp_expires_at,
            )
            created_user = await self._auth_user_repo.get_by_id(created_user.id)
            if created_user is None:
                raise RuntimeError("Pending user disappeared after OTP update")

        # 5. Send OTP email (non-blocking, don't fail registration)
        try:
            await self._email_svc.send_otp_email(
                to_email=validated_email.value,
                otp_code=otp_code,
                purpose=OTP_PURPOSE_REGISTER,
            )
        except Exception:
            logger.exception(f"Failed to send OTP email to {_mask_email(validated_email.value)}")

        return {
            "user_id": str(created_user.id),
            "email": validated_email.value,
            "otp_expires_in_seconds": OTP_EXPIRE_MINUTES * 60,
            "has_restorable_account": has_restorable,
        }

    # ===================================================================
    # Registration — Step 2: Verify OTP
    # ===================================================================

    async def verify_registration_otp(
        self,
        email: str,
        otp_code: str,
    ) -> Dict[str, Any]:
        """
        Registration step 2: Verify the OTP code.

        Args:
            email: User's email address (used to look up the pending user).
            otp_code: 6-digit OTP code from email.

        Returns:
            Dict with user_id (for step 3) confirming OTP is valid.

        Raises:
            OtpExpiredException: OTP has expired.
            OtpMaxAttemptsException: Too many failed attempts.
            OtpInvalidException: Wrong OTP code.
        """
        normalized = email.strip().lower()
        auth_user = await self._auth_user_repo.get_by_email(normalized)
        if auth_user is None:
            raise OtpInvalidException(remaining_attempts=0)

        # Must be pending user with register purpose
        if auth_user.is_registered:
            raise OtpInvalidException(remaining_attempts=0)

        if auth_user.otp_purpose != OTP_PURPOSE_REGISTER:
            raise OtpInvalidException(remaining_attempts=0)

        # Check expiry
        if not auth_user.is_otp_valid:
            raise OtpExpiredException()

        # Check max attempts
        if auth_user.is_otp_max_attempts_reached:
            raise OtpMaxAttemptsException()

        # Verify OTP code
        input_hash = self._token_svc.hash_otp(otp_code)
        if not hmac.compare_digest(input_hash, auth_user.otp_code_hash or ""):
            # Increment attempts
            auth_user.increment_otp_attempts()
            await self._auth_user_repo.update_otp_attempts(
                user_id=auth_user.id,
                otp_attempts=auth_user.otp_attempts,
            )

            if auth_user.is_otp_max_attempts_reached:
                raise OtpMaxAttemptsException()

            from .constants import OTP_MAX_ATTEMPTS
            remaining = OTP_MAX_ATTEMPTS - auth_user.otp_attempts
            raise OtpInvalidException(remaining_attempts=remaining)

        # OTP verified — don't clear yet, step 3 will clear via RPC
        return {
            "user_id": str(auth_user.id),
            "email": auth_user.email,
            "otp_verified": True,
        }

    # ===================================================================
    # Registration — Step 3: Complete Registration
    # ===================================================================

    async def complete_registration(
        self,
        user_id: str,
        password: str,
        display_name: Optional[str] = None,
        device_info: Optional[DeviceInfo] = None,
        signup_bonus: int = 0,
    ) -> Dict[str, Any]:
        """
        Registration step 3: Set password and create profile.

        Flow:
        1. Validate password strength
        2. Hash password (argon2id)
        3. Complete registration via RPC (set password + create profile)
        4. Create session + return tokens

        Args:
            user_id: User ID from step 2.
            password: Plaintext password.
            display_name: Optional display name.
            device_info: Client device information.
            signup_bonus: Signup bonus credits.

        Returns:
            Dict with access_token, refresh_token, user info.

        Raises:
            WeakPasswordException: Password doesn't meet requirements.
            OtpInvalidException: User not in valid pending state.
        """
        uid = UUID(user_id)

        # Verify user is still in pending state with verified OTP
        auth_user = await self._auth_user_repo.get_by_id(uid)
        if auth_user is None or auth_user.is_registered:
            raise OtpInvalidException(remaining_attempts=0)

        # 1. Validate password strength
        strength = self._password_svc.validate_strength(password)
        if not strength.is_valid:
            raise WeakPasswordException(errors=list(strength.errors))

        # 2. Hash password (CPU-bound, run in threadpool)
        password_hash = await run_in_threadpool(
            self._password_svc.hash_password, password
        )

        # 3. Complete registration via RPC
        completed_user = await self._auth_user_repo.complete_registration(
            user_id=uid,
            password_hash=password_hash,
            display_name=display_name,
            signup_bonus=signup_bonus,
        )

        # 4. Create session + tokens
        return await self._create_session_and_tokens(
            user=completed_user,
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

        # Pending users cannot login
        if auth_user.is_pending:
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

            role, tier = await self._get_user_role_tier(auth_user.id)
            access_token = self._token_svc.create_access_token(
                user_id=auth_user.id,
                email=auth_user.email,
                role=role,
                tier=tier,
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
    # Authenticated OTP (change-password / delete-account)
    # ===================================================================

    async def send_change_password_otp(self, user_id: UUID) -> None:
        """
        Send OTP for password change verification.

        Args:
            user_id: Authenticated user's UUID.

        Raises:
            OtpCooldownException: OTP sent too recently.
        """
        await self._send_authenticated_otp(user_id, OTP_PURPOSE_CHANGE_PASSWORD)

    async def send_delete_account_otp(self, user_id: UUID) -> None:
        """
        Send OTP for account deletion verification.

        Args:
            user_id: Authenticated user's UUID.

        Raises:
            OtpCooldownException: OTP sent too recently.
        """
        await self._send_authenticated_otp(user_id, OTP_PURPOSE_DELETE_ACCOUNT)

    async def _send_authenticated_otp(
        self, user_id: UUID, purpose: str
    ) -> None:
        """
        Internal: Send OTP for an authenticated user.

        Shared logic for change-password and delete-account OTP.
        """
        auth_user = await self._auth_user_repo.get_by_id(user_id)
        if auth_user is None or auth_user.is_pending:
            raise InvalidCredentialsException()

        # Check cooldown
        if auth_user.is_otp_valid and auth_user.otp_expires_at:
            otp_set_at = auth_user.otp_expires_at - timedelta(
                minutes=OTP_EXPIRE_MINUTES
            )
            elapsed = (datetime.now(timezone.utc) - otp_set_at).total_seconds()
            if elapsed < OTP_COOLDOWN_SECONDS:
                remaining = int(OTP_COOLDOWN_SECONDS - elapsed)
                raise OtpCooldownException(retry_after_seconds=remaining)

        # Generate and store OTP
        otp_code, otp_hash = self._token_svc.generate_otp()
        otp_expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=OTP_EXPIRE_MINUTES
        )

        await self._auth_user_repo.update_otp(
            user_id=auth_user.id,
            otp_code_hash=otp_hash,
            otp_purpose=purpose,
            otp_expires_at=otp_expires_at,
        )

        # Send email
        try:
            await self._email_svc.send_otp_email(
                to_email=auth_user.email,
                otp_code=otp_code,
                purpose=purpose,
            )
        except Exception:
            logger.exception(
                f"Failed to send {purpose} OTP to {_mask_email(auth_user.email)}"
            )

    async def verify_authenticated_otp(
        self,
        user_id: UUID,
        otp_code: str,
        expected_purpose: str,
    ) -> Dict[str, Any]:
        """
        Verify OTP for an authenticated user (change-password / delete-account).

        Args:
            user_id: Authenticated user's UUID.
            otp_code: 6-digit OTP code.
            expected_purpose: Expected OTP purpose.

        Returns:
            Dict with user_id and otp_verified=True.

        Raises:
            OtpExpiredException: OTP has expired.
            OtpMaxAttemptsException: Too many failed attempts.
            OtpInvalidException: Wrong OTP code.
        """
        auth_user = await self._auth_user_repo.get_by_id(user_id)
        if auth_user is None:
            raise OtpInvalidException(remaining_attempts=0)

        if auth_user.otp_purpose != expected_purpose:
            raise OtpInvalidException(remaining_attempts=0)

        if not auth_user.is_otp_valid:
            raise OtpExpiredException()

        if auth_user.is_otp_max_attempts_reached:
            raise OtpMaxAttemptsException()

        input_hash = self._token_svc.hash_otp(otp_code)
        if not hmac.compare_digest(input_hash, auth_user.otp_code_hash or ""):
            auth_user.increment_otp_attempts()
            await self._auth_user_repo.update_otp_attempts(
                user_id=auth_user.id,
                otp_attempts=auth_user.otp_attempts,
            )

            if auth_user.is_otp_max_attempts_reached:
                raise OtpMaxAttemptsException()

            from .constants import OTP_MAX_ATTEMPTS
            remaining = OTP_MAX_ATTEMPTS - auth_user.otp_attempts
            raise OtpInvalidException(remaining_attempts=remaining)

        # Clear OTP after successful verification
        await self._auth_user_repo.clear_otp(user_id)

        return {
            "user_id": str(user_id),
            "otp_verified": True,
        }

    # ===================================================================
    # Password Reset via OTP
    # ===================================================================

    async def send_password_reset_otp(self, email: str) -> Dict[str, Any]:
        """
        Send OTP for password reset.

        Always returns success-like response to prevent email enumeration.

        Args:
            email: Email address to send OTP to.

        Returns:
            Dict with generic success message (doesn't reveal if email exists).
        """
        normalized_email = email.strip().lower()
        auth_user = await self._auth_user_repo.get_by_email(normalized_email)

        # Always return "success" to prevent enumeration
        generic_response = {
            "message": "If an account exists with this email, a verification code has been sent.",
        }

        if auth_user is None or auth_user.is_pending:
            logger.info(f"Password reset requested for unknown/pending email: {_mask_email(normalized_email)}")
            return generic_response

        # Check cooldown
        if auth_user.is_otp_valid and auth_user.otp_expires_at:
            otp_set_at = auth_user.otp_expires_at - timedelta(minutes=OTP_EXPIRE_MINUTES)
            elapsed = (datetime.now(timezone.utc) - otp_set_at).total_seconds()
            if elapsed < OTP_COOLDOWN_SECONDS:
                # Don't reveal cooldown to prevent enumeration
                return generic_response

        # Generate and store OTP
        otp_code, otp_hash = self._token_svc.generate_otp()
        otp_expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=OTP_EXPIRE_MINUTES
        )

        await self._auth_user_repo.update_otp(
            user_id=auth_user.id,
            otp_code_hash=otp_hash,
            otp_purpose=OTP_PURPOSE_FORGOT_PASSWORD,
            otp_expires_at=otp_expires_at,
        )

        # Send email
        try:
            await self._email_svc.send_otp_email(
                to_email=auth_user.email,
                otp_code=otp_code,
                purpose=OTP_PURPOSE_FORGOT_PASSWORD,
            )
        except Exception:
            logger.exception(f"Failed to send password reset OTP to {_mask_email(auth_user.email)}")

        return generic_response

    async def verify_password_reset_otp(
        self,
        email: str,
        otp_code: str,
    ) -> Dict[str, Any]:
        """
        Verify OTP for password reset.

        Args:
            email: User's email.
            otp_code: 6-digit OTP code.

        Returns:
            Dict with user_id for the reset step.

        Raises:
            OtpExpiredException: OTP has expired.
            OtpMaxAttemptsException: Too many failed attempts.
            OtpInvalidException: Wrong OTP code.
        """
        normalized = email.strip().lower()
        auth_user = await self._auth_user_repo.get_by_email(normalized)
        if auth_user is None:
            raise OtpInvalidException(remaining_attempts=0)

        if auth_user.otp_purpose != OTP_PURPOSE_FORGOT_PASSWORD:
            raise OtpInvalidException(remaining_attempts=0)

        if not auth_user.is_otp_valid:
            raise OtpExpiredException()

        if auth_user.is_otp_max_attempts_reached:
            raise OtpMaxAttemptsException()

        input_hash = self._token_svc.hash_otp(otp_code)
        if not hmac.compare_digest(input_hash, auth_user.otp_code_hash or ""):
            auth_user.increment_otp_attempts()
            await self._auth_user_repo.update_otp_attempts(
                user_id=auth_user.id,
                otp_attempts=auth_user.otp_attempts,
            )

            if auth_user.is_otp_max_attempts_reached:
                raise OtpMaxAttemptsException()

            from .constants import OTP_MAX_ATTEMPTS
            remaining = OTP_MAX_ATTEMPTS - auth_user.otp_attempts
            raise OtpInvalidException(remaining_attempts=remaining)

        # Clear OTP after successful verification (prevents reuse)
        await self._auth_user_repo.clear_otp(auth_user.id)

        return {
            "user_id": str(auth_user.id),
            "email": auth_user.email,
            "otp_verified": True,
        }

    async def reset_password(
        self,
        user_id: str,
        new_password: str,
    ) -> None:
        """
        Reset password after OTP verification.

        Args:
            user_id: User's UUID (from verify step).
            new_password: New plaintext password.

        Raises:
            WeakPasswordException: New password doesn't meet requirements.
            InvalidCredentialsException: User not found.
        """
        uid = UUID(user_id)
        auth_user = await self._auth_user_repo.get_by_id(uid)
        if auth_user is None:
            raise InvalidCredentialsException()

        # Validate password strength
        strength = self._password_svc.validate_strength(new_password)
        if not strength.is_valid:
            raise WeakPasswordException(errors=list(strength.errors))

        # Hash new password
        new_hash = await run_in_threadpool(
            self._password_svc.hash_password, new_password
        )

        # Update password (also clears OTP)
        await self._auth_user_repo.update_password(
            user_id=uid,
            password_hash=new_hash,
        )

        # Revoke all sessions (security: force re-login)
        await self._session_repo.revoke_all_by_user(
            user_id=uid,
            reason=REVOKE_REASON_SECURITY,
        )

    # ===================================================================
    # Password Change (authenticated)
    # ===================================================================

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
        if auth_user is None or auth_user.password_hash is None:
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
    ) -> None:
        """
        Delete user account (after OTP verification).

        Flow:
        1. Revoke all sessions
        2. Hard delete auth_users (cascades to sessions)

        Note: OTP verification is handled by the router layer before calling this.
        Profile soft-delete, email_hash, and Stripe cancellation
        should be handled by the application layer before calling this.

        Args:
            user_id: User's UUID.
        """
        auth_user = await self._auth_user_repo.get_by_id(user_id)
        if auth_user is None:
            raise InvalidCredentialsException()

        # Revoke all sessions
        await self._session_repo.revoke_all_by_user(
            user_id=user_id,
            reason="account_deleted",
        )

        # Hard delete auth_users (cascades to auth_sessions)
        await self._auth_user_repo.delete(user_id)

        logger.info(f"Account deleted for user {user_id}")

    # ===================================================================
    # Account Restoration
    # ===================================================================

    async def get_pending_user_email(self, user_id: UUID) -> Optional[str]:
        """
        Get the email of a pending (pre-registration) user.

        Used by the router to look up email for the restore flow.

        Args:
            user_id: User's UUID from register_token.

        Returns:
            Email string if user is pending, None otherwise.
        """
        auth_user = await self._auth_user_repo.get_by_id(user_id)
        if auth_user is None or auth_user.is_registered:
            return None
        return auth_user.email

    async def check_restorable_account(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Check if email has a restorable soft-deleted account.

        Args:
            email: Email to check.

        Returns:
            Dict with restore info if restorable, None otherwise.
        """
        return await self._auth_user_repo.get_restorable_by_email(email)

    async def restore_account(
        self,
        email: str,
        password: str,
        device_info: Optional[DeviceInfo] = None,
    ) -> Dict[str, Any]:
        """
        Restore a soft-deleted account.

        Flow:
        1. Validate password strength
        2. Hash password
        3. Restore via RPC (reuse old profile UUID)
        4. Create session + tokens

        Args:
            email: User's email.
            password: New password.
            device_info: Client device info.

        Returns:
            Dict with access_token, refresh_token, user info.

        Raises:
            WeakPasswordException: Password doesn't meet requirements.
        """
        # Validate password
        strength = self._password_svc.validate_strength(password)
        if not strength.is_valid:
            raise WeakPasswordException(errors=list(strength.errors))

        # Hash password
        password_hash = await run_in_threadpool(
            self._password_svc.hash_password, password
        )

        # Restore via RPC
        restored_user = await self._auth_user_repo.restore_account(
            email=email,
            password_hash=password_hash,
        )

        # Create session + tokens
        return await self._create_session_and_tokens(
            user=restored_user,
            device_info=device_info,
        )

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

        # Create access token with real role/tier from profile
        role, tier = await self._get_user_role_tier(user.id)
        access_token = self._token_svc.create_access_token(
            user_id=user.id,
            email=user.email,
            role=role,
            tier=tier,
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

        role, tier = await self._get_user_role_tier(auth_user.id)
        access_token = self._token_svc.create_access_token(
            user_id=auth_user.id,
            email=auth_user.email,
            role=role,
            tier=tier,
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
        }

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
