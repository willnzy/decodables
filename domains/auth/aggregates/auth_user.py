"""
AuthUser Aggregate Root.

Encapsulates authentication credentials and account state.
This is separate from UserProfile (identity domain) — AuthUser owns
credentials, lockout state, and email verification status.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

from ..constants import (
    MAX_FAILED_LOGIN_ATTEMPTS,
    LOCKOUT_DURATION_MINUTES,
)


@dataclass
class AuthUser:
    """
    Aggregate root for authentication credentials.

    Encapsulates:
    - Email + password hash (credentials)
    - Email verification state
    - Account lockout state (failed attempts + lock timer)
    - Login tracking (last login time/IP)
    - Account active/inactive state
    """

    id: UUID
    email: str
    password_hash: str

    # Email verification
    email_verified: bool = False
    email_verified_at: Optional[datetime] = None
    email_verification_token: Optional[str] = None
    email_verification_expires_at: Optional[datetime] = None

    # Password reset
    password_reset_token: Optional[str] = None
    password_reset_expires_at: Optional[datetime] = None
    password_changed_at: Optional[datetime] = None

    # Lockout state
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None

    # Login tracking
    last_login_at: Optional[datetime] = None
    last_login_ip: Optional[str] = None

    # Account state
    is_active: bool = True

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # -----------------------------------------------------------------------
    # Factory Methods
    # -----------------------------------------------------------------------

    @classmethod
    def create_new(
        cls,
        email: str,
        password_hash: str,
        user_id: Optional[UUID] = None,
    ) -> AuthUser:
        """
        Create a new AuthUser for registration.

        Args:
            email: Normalized email address (lowercase).
            password_hash: Argon2id hashed password.
            user_id: Optional pre-generated UUID (for shared ID with profiles).

        Returns:
            New AuthUser instance.
        """
        now = datetime.now(timezone.utc)
        return cls(
            id=user_id or uuid4(),
            email=email.strip().lower(),
            password_hash=password_hash,
            email_verified=False,
            failed_login_attempts=0,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

    # -----------------------------------------------------------------------
    # Lockout Logic
    # -----------------------------------------------------------------------

    @property
    def is_locked(self) -> bool:
        """Check if account is currently locked."""
        if self.locked_until is None:
            return False
        return datetime.now(timezone.utc) < self.locked_until

    @property
    def lockout_remaining_seconds(self) -> int:
        """Seconds remaining until lockout expires. Returns 0 if not locked."""
        if not self.is_locked or self.locked_until is None:
            return 0
        remaining = (self.locked_until - datetime.now(timezone.utc)).total_seconds()
        return max(0, int(remaining))

    def record_failed_login(self) -> None:
        """
        Record a failed login attempt.

        If threshold is reached, lock the account.
        Does NOT increment during lockout period (prevents lock extension attacks).
        """
        if self.is_locked:
            return

        self.failed_login_attempts += 1
        self.updated_at = datetime.now(timezone.utc)

        if self.failed_login_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
            self.locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=LOCKOUT_DURATION_MINUTES
            )

    def record_successful_login(self, ip_address: Optional[str] = None) -> None:
        """
        Record a successful login. Resets lockout state.

        Args:
            ip_address: Client IP address.
        """
        now = datetime.now(timezone.utc)
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login_at = now
        self.last_login_ip = ip_address
        self.updated_at = now

    # -----------------------------------------------------------------------
    # Email Verification
    # -----------------------------------------------------------------------

    def set_verification_token(
        self,
        token_hash: str,
        expires_at: datetime,
    ) -> None:
        """
        Set email verification token (SHA-256 hash).

        Args:
            token_hash: SHA-256 hash of the verification token.
            expires_at: Token expiration time.
        """
        self.email_verification_token = token_hash
        self.email_verification_expires_at = expires_at
        self.updated_at = datetime.now(timezone.utc)

    def verify_email(self) -> None:
        """Mark email as verified and clear verification token."""
        now = datetime.now(timezone.utc)
        self.email_verified = True
        self.email_verified_at = now
        self.email_verification_token = None
        self.email_verification_expires_at = None
        self.updated_at = now

    @property
    def is_verification_token_valid(self) -> bool:
        """Check if current verification token is still valid (not expired)."""
        if self.email_verification_token is None:
            return False
        if self.email_verification_expires_at is None:
            return False
        return datetime.now(timezone.utc) < self.email_verification_expires_at

    # -----------------------------------------------------------------------
    # Password Reset
    # -----------------------------------------------------------------------

    def set_password_reset_token(
        self,
        token_hash: str,
        expires_at: datetime,
    ) -> None:
        """
        Set password reset token (SHA-256 hash).

        Args:
            token_hash: SHA-256 hash of the reset token.
            expires_at: Token expiration time.
        """
        self.password_reset_token = token_hash
        self.password_reset_expires_at = expires_at
        self.updated_at = datetime.now(timezone.utc)

    def clear_password_reset_token(self) -> None:
        """Clear password reset token after successful reset."""
        self.password_reset_token = None
        self.password_reset_expires_at = None
        self.updated_at = datetime.now(timezone.utc)

    @property
    def is_reset_token_valid(self) -> bool:
        """Check if current password reset token is still valid."""
        if self.password_reset_token is None:
            return False
        if self.password_reset_expires_at is None:
            return False
        return datetime.now(timezone.utc) < self.password_reset_expires_at

    def update_password(self, new_password_hash: str) -> None:
        """
        Update password hash.

        Args:
            new_password_hash: New argon2id hash.
        """
        now = datetime.now(timezone.utc)
        self.password_hash = new_password_hash
        self.password_changed_at = now
        self.password_reset_token = None
        self.password_reset_expires_at = None
        self.updated_at = now

    # -----------------------------------------------------------------------
    # Account State
    # -----------------------------------------------------------------------

    def deactivate(self) -> None:
        """Deactivate the account (soft disable)."""
        self.is_active = False
        self.updated_at = datetime.now(timezone.utc)

    def activate(self) -> None:
        """Reactivate the account."""
        self.is_active = True
        self.updated_at = datetime.now(timezone.utc)

    # -----------------------------------------------------------------------
    # Serialization
    # -----------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses (excludes sensitive fields)."""
        return {
            "id": str(self.id),
            "email": self.email,
            "email_verified": self.email_verified,
            "email_verified_at": (
                self.email_verified_at.isoformat() if self.email_verified_at else None
            ),
            "is_active": self.is_active,
            "last_login_at": (
                self.last_login_at.isoformat() if self.last_login_at else None
            ),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
