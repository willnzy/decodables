"""
Auth Repository Interfaces.

Defines the data access contracts (ports) for the auth domain.
Infrastructure layer provides concrete implementations.

Uses unified OTP model — no separate verification/reset token methods.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from .aggregates.auth_user import AuthUser
from .aggregates.session import Session


class IAuthUserRepository(ABC):
    """
    Repository interface for AuthUser aggregate operations.

    All methods are async to support non-blocking I/O.
    """

    # -------------------------------------------------------------------
    # Query Methods
    # -------------------------------------------------------------------

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[AuthUser]:
        """
        Get auth user by ID.

        Args:
            user_id: User's UUID.

        Returns:
            AuthUser or None if not found.
        """
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[AuthUser]:
        """
        Get auth user by email address.

        Email is normalized to lowercase before lookup.

        Args:
            email: User's email address.

        Returns:
            AuthUser or None if not found.
        """
        pass

    @abstractmethod
    async def get_restorable_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Check if a soft-deleted profile exists that can be restored.

        Looks for profiles with is_deleted=true and recovery_expires_at > now.

        Args:
            email: User's email address.

        Returns:
            Dict with profile info (id, email, recovery_expires_at) or None.
        """
        pass

    # -------------------------------------------------------------------
    # Command Methods — Registration (3-step OTP)
    # -------------------------------------------------------------------

    @abstractmethod
    async def create_pending(
        self,
        auth_user: AuthUser,
    ) -> Tuple[AuthUser, bool]:
        """
        Create a pending auth user (step 1 of registration).

        Uses RPC create_pending_auth_user() to atomically create/update
        a pending user with OTP fields.

        Args:
            auth_user: Pending AuthUser aggregate (no password_hash).

        Returns:
            Tuple of (AuthUser, was_created).
            was_created=False means email already registered (has password).
        """
        pass

    @abstractmethod
    async def complete_registration(
        self,
        user_id: UUID,
        email: str,
        password_hash: str,
        display_name: Optional[str] = None,
        signup_bonus: int = 0,
    ) -> AuthUser:
        """
        Complete registration (step 3 of registration).

        Uses RPC create_auth_user_with_profile() to atomically set password,
        mark email verified, and create the associated profile.

        Args:
            user_id: Pending user's UUID from step 1.
            email: User's email (used for profile creation and default display name).
            password_hash: Argon2id hashed password.
            display_name: Optional display name for the profile.
            signup_bonus: Signup bonus credits (default 0).

        Returns:
            Completed AuthUser.
        """
        pass

    # -------------------------------------------------------------------
    # Command Methods — OTP
    # -------------------------------------------------------------------

    @abstractmethod
    async def update_otp(
        self,
        user_id: UUID,
        otp_code_hash: str,
        otp_purpose: str,
        otp_expires_at: datetime,
    ) -> None:
        """
        Update OTP fields for a user.

        Args:
            user_id: User's UUID.
            otp_code_hash: SHA-256 hash of the OTP code.
            otp_purpose: OTP purpose string.
            otp_expires_at: OTP expiration time.
        """
        pass

    @abstractmethod
    async def update_otp_attempts(
        self,
        user_id: UUID,
        otp_attempts: int,
    ) -> None:
        """
        Update OTP attempt count.

        Args:
            user_id: User's UUID.
            otp_attempts: New attempt count.
        """
        pass

    @abstractmethod
    async def clear_otp(self, user_id: UUID) -> None:
        """Clear all OTP fields after successful verification."""
        pass

    # -------------------------------------------------------------------
    # Command Methods — Password & Account
    # -------------------------------------------------------------------

    @abstractmethod
    async def update_password(
        self,
        user_id: UUID,
        password_hash: str,
    ) -> None:
        """
        Update user's password hash.

        Args:
            user_id: User's UUID.
            password_hash: New argon2id password hash.
        """
        pass

    @abstractmethod
    async def update_email_verified(
        self,
        user_id: UUID,
        verified: bool,
    ) -> None:
        """
        Update email verification status.

        Args:
            user_id: User's UUID.
            verified: Whether email is verified.
        """
        pass

    @abstractmethod
    async def update_login_attempt(
        self,
        user_id: UUID,
        failed_attempts: int,
        locked_until: Optional[datetime],
    ) -> None:
        """
        Update failed login attempt count and lockout state.

        Args:
            user_id: User's UUID.
            failed_attempts: Current failed attempt count.
            locked_until: Lockout expiry time (None to clear).
        """
        pass

    @abstractmethod
    async def record_login(
        self,
        user_id: UUID,
        ip_address: Optional[str],
        timestamp: datetime,
    ) -> None:
        """
        Record successful login (update last_login_at, last_login_ip, reset failures).

        Args:
            user_id: User's UUID.
            ip_address: Client IP address.
            timestamp: Login timestamp.
        """
        pass

    @abstractmethod
    async def delete(self, user_id: UUID) -> None:
        """
        Hard delete auth user record.

        This cascades to auth_sessions via ON DELETE CASCADE.

        Args:
            user_id: User's UUID.
        """
        pass

    # -------------------------------------------------------------------
    # Command Methods — Account Restore
    # -------------------------------------------------------------------

    @abstractmethod
    async def restore_account(
        self,
        email: str,
        password_hash: str,
    ) -> AuthUser:
        """
        Restore a soft-deleted account within the restore window.

        Uses RPC restore_auth_user_with_profile() to atomically:
        - Create new auth_users record reusing the old profile UUID
        - Restore the soft-deleted profile (is_deleted=false)

        Args:
            email: User's email address.
            password_hash: Argon2id hashed password.

        Returns:
            Restored AuthUser.
        """
        pass


class ISessionRepository(ABC):
    """
    Repository interface for Session entity operations.

    Manages refresh token sessions with rotation and reuse detection.
    """

    # -------------------------------------------------------------------
    # Query Methods
    # -------------------------------------------------------------------

    @abstractmethod
    async def get_by_token_hash(
        self,
        token_hash: str,
    ) -> Optional[Session]:
        """
        Get session by refresh token hash.

        Args:
            token_hash: SHA-256 hash of the refresh token.

        Returns:
            Session or None if not found.
        """
        pass

    @abstractmethod
    async def get_active_by_user(
        self,
        user_id: UUID,
    ) -> List[Session]:
        """
        Get all active (non-revoked, non-expired) sessions for a user.

        Args:
            user_id: User's UUID.

        Returns:
            List of active Session entities, ordered by last_used_at desc.
        """
        pass

    @abstractmethod
    async def count_active_by_user(self, user_id: UUID) -> int:
        """
        Count active sessions for a user.

        Args:
            user_id: User's UUID.

        Returns:
            Number of active sessions.
        """
        pass

    # -------------------------------------------------------------------
    # Command Methods
    # -------------------------------------------------------------------

    @abstractmethod
    async def create(self, session: Session) -> Session:
        """
        Create a new session.

        Args:
            session: Session entity to create.

        Returns:
            Created Session.
        """
        pass

    @abstractmethod
    async def revoke(
        self,
        session_id: UUID,
        reason: str,
    ) -> None:
        """
        Revoke a specific session.

        Args:
            session_id: Session UUID.
            reason: Revocation reason.
        """
        pass

    @abstractmethod
    async def revoke_family(
        self,
        family_id: UUID,
        reason: str,
    ) -> None:
        """
        Revoke all sessions in a token family.

        Used for reuse detection: if a rotated token is reused,
        the entire family is revoked as a security measure.

        Args:
            family_id: Token family UUID.
            reason: Revocation reason.
        """
        pass

    @abstractmethod
    async def revoke_all_by_user(
        self,
        user_id: UUID,
        reason: str,
    ) -> None:
        """
        Revoke all sessions for a user (logout from all devices).

        Args:
            user_id: User's UUID.
            reason: Revocation reason.
        """
        pass

    @abstractmethod
    async def revoke_oldest_by_user(
        self,
        user_id: UUID,
        reason: str,
    ) -> None:
        """
        Revoke the oldest active session for a user.

        Used when concurrent session limit is exceeded.

        Args:
            user_id: User's UUID.
            reason: Revocation reason.
        """
        pass

    @abstractmethod
    async def update_last_used(self, session_id: UUID) -> None:
        """
        Update session's last_used_at timestamp.

        Args:
            session_id: Session UUID.
        """
        pass
