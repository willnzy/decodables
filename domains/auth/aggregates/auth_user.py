"""
AuthUser Aggregate Root.

Encapsulates authentication credentials and account state.
This is separate from UserProfile (identity domain) — AuthUser owns
credentials, lockout state, and email verification status.

Uses unified OTP (One-Time Password) model for:
- Registration (3-step: email → OTP → password)
- Password reset (forgot password)
- Account deletion verification
- Password change verification
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

from ..constants import (
    MAX_FAILED_LOGIN_ATTEMPTS,
    LOCKOUT_DURATION_MINUTES,
    OTP_MAX_ATTEMPTS,
    VALID_OTP_PURPOSES,
)


@dataclass
class AuthUser:
    """
    Aggregate root for authentication credentials.

    Encapsulates:
    - Email + password hash (credentials)
    - Email verification state
    - Unified OTP state (code hash, purpose, expiry, attempts)
    - Account lockout state (failed attempts + lock timer)
    - Login tracking (last login time/IP)
    - Account active/inactive state
    """

    id: UUID
    email: str
    password_hash: Optional[str]  # None for pending users (step 1 of registration)

    # Email verification
    email_verified: bool = False
    email_verified_at: Optional[datetime] = None

    # Unified OTP fields
    otp_code_hash: Optional[str] = None
    otp_purpose: Optional[str] = None
    otp_expires_at: Optional[datetime] = None
    otp_attempts: int = 0

    # Password tracking
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
    def create_pending(
        cls,
        email: str,
        otp_code_hash: str,
        otp_purpose: str,
        otp_expires_at: datetime,
        user_id: Optional[UUID] = None,
    ) -> AuthUser:
        """
        Create a pending AuthUser for registration step 1 (send OTP).

        Pending users have no password_hash yet. They must complete
        OTP verification + password setup to become fully registered.

        Args:
            email: Normalized email address (lowercase).
            otp_code_hash: SHA-256 hash of the OTP code.
            otp_purpose: OTP purpose (e.g., "register").
            otp_expires_at: OTP expiration time.
            user_id: Optional pre-generated UUID.

        Returns:
            New pending AuthUser instance (password_hash=None).
        """
        now = datetime.now(timezone.utc)
        return cls(
            id=user_id or uuid4(),
            email=email.strip().lower(),
            password_hash=None,
            email_verified=False,
            otp_code_hash=otp_code_hash,
            otp_purpose=otp_purpose,
            otp_expires_at=otp_expires_at,
            otp_attempts=0,
            failed_login_attempts=0,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

    @classmethod
    def create_registered(
        cls,
        email: str,
        password_hash: str,
        user_id: Optional[UUID] = None,
    ) -> AuthUser:
        """
        Create a fully registered AuthUser (email verified, password set).

        Used after completing the 3-step registration flow.

        Args:
            email: Normalized email address (lowercase).
            password_hash: Argon2id hashed password.
            user_id: Optional pre-generated UUID (for shared ID with profiles).

        Returns:
            New registered AuthUser instance.
        """
        now = datetime.now(timezone.utc)
        return cls(
            id=user_id or uuid4(),
            email=email.strip().lower(),
            password_hash=password_hash,
            email_verified=True,
            email_verified_at=now,
            failed_login_attempts=0,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

    # -----------------------------------------------------------------------
    # Properties
    # -----------------------------------------------------------------------

    @property
    def is_pending(self) -> bool:
        """Check if user is in pending state (no password set yet)."""
        return self.password_hash is None

    @property
    def is_registered(self) -> bool:
        """Check if user has completed registration (password set)."""
        return self.password_hash is not None

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
    # OTP (One-Time Password) Logic
    # -----------------------------------------------------------------------

    def set_otp(
        self,
        otp_code_hash: str,
        purpose: str,
        expires_at: datetime,
    ) -> None:
        """
        Set a new OTP code.

        Replaces any existing OTP. Resets attempt counter.

        Args:
            otp_code_hash: SHA-256 hash of the OTP code.
            purpose: OTP purpose (must be in VALID_OTP_PURPOSES).
            expires_at: OTP expiration time.

        Raises:
            ValueError: If purpose is not valid.
        """
        if purpose not in VALID_OTP_PURPOSES:
            raise ValueError(f"Invalid OTP purpose: {purpose}")

        self.otp_code_hash = otp_code_hash
        self.otp_purpose = purpose
        self.otp_expires_at = expires_at
        self.otp_attempts = 0
        self.updated_at = datetime.now(timezone.utc)

    def clear_otp(self) -> None:
        """Clear OTP fields after successful verification or expiry."""
        self.otp_code_hash = None
        self.otp_purpose = None
        self.otp_expires_at = None
        self.otp_attempts = 0
        self.updated_at = datetime.now(timezone.utc)

    @property
    def is_otp_valid(self) -> bool:
        """Check if current OTP is still valid (exists and not expired)."""
        if self.otp_code_hash is None:
            return False
        if self.otp_expires_at is None:
            return False
        return datetime.now(timezone.utc) < self.otp_expires_at

    @property
    def is_otp_max_attempts_reached(self) -> bool:
        """Check if OTP max attempts has been reached."""
        return self.otp_attempts >= OTP_MAX_ATTEMPTS

    def increment_otp_attempts(self) -> None:
        """Increment OTP verification attempt counter."""
        self.otp_attempts += 1
        self.updated_at = datetime.now(timezone.utc)

    # -----------------------------------------------------------------------
    # Password Management
    # -----------------------------------------------------------------------

    def update_password(self, new_password_hash: str) -> None:
        """
        Update password hash.

        Args:
            new_password_hash: New argon2id hash.
        """
        now = datetime.now(timezone.utc)
        self.password_hash = new_password_hash
        self.password_changed_at = now
        self.updated_at = now

    def complete_registration(self, password_hash: str) -> None:
        """
        Complete registration by setting password and marking email verified.

        Called after successful OTP verification in step 3 of registration.

        Args:
            password_hash: Argon2id hashed password.
        """
        now = datetime.now(timezone.utc)
        self.password_hash = password_hash
        self.email_verified = True
        self.email_verified_at = now
        self.otp_code_hash = None
        self.otp_purpose = None
        self.otp_expires_at = None
        self.otp_attempts = 0
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
            "is_pending": self.is_pending,
            "last_login_at": (
                self.last_login_at.isoformat() if self.last_login_at else None
            ),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
