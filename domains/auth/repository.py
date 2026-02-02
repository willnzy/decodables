"""
Auth Repository Interfaces.

Defines the data access contracts (ports) for the auth domain.
Infrastructure layer provides concrete implementations.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Tuple
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

    # -------------------------------------------------------------------
    # Command Methods
    # -------------------------------------------------------------------

    @abstractmethod
    async def create(
        self,
        auth_user: AuthUser,
        display_name: Optional[str] = None,
        signup_bonus: int = 0,
    ) -> Tuple[AuthUser, bool]:
        """
        Create auth user and associated profile atomically.

        Uses RPC create_auth_user_with_profile() to ensure auth_users
        and profiles are created in the same transaction with a shared UUID.

        Args:
            auth_user: AuthUser aggregate to create.
            display_name: Optional display name for the profile.
            signup_bonus: Signup bonus credits (default 0).

        Returns:
            Tuple of (AuthUser, was_created).
            was_created=False means email already exists.
        """
        pass

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
    async def set_verification_token(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> None:
        """
        Set email verification token.

        Args:
            user_id: User's UUID.
            token_hash: SHA-256 hash of the verification token.
            expires_at: Token expiration time.
        """
        pass

    @abstractmethod
    async def set_password_reset_token(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> None:
        """
        Set password reset token.

        Args:
            user_id: User's UUID.
            token_hash: SHA-256 hash of the reset token.
            expires_at: Token expiration time.
        """
        pass

    @abstractmethod
    async def clear_verification_token(self, user_id: UUID) -> None:
        """Clear email verification token after successful verification."""
        pass

    @abstractmethod
    async def clear_password_reset_token(self, user_id: UUID) -> None:
        """Clear password reset token after successful reset."""
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
