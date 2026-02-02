"""
Session Entity.

Represents a user's authentication session (refresh token).
Supports token rotation with family-based reuse detection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

from ..constants import (
    REFRESH_TOKEN_EXPIRE_DAYS,
    TOKEN_ROTATION_GRACE_PERIOD_SECONDS,
    VALID_REVOKE_REASONS,
)


@dataclass
class Session:
    """
    Authentication session tied to a refresh token.

    Sessions share a family_id when rotated (old → new).
    This enables reuse detection: if a revoked token in the same family
    is presented again, all family sessions are revoked (potential theft).
    """

    id: UUID
    user_id: UUID
    family_id: UUID
    refresh_token_hash: str

    # Device identification
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    device_name: Optional[str] = None

    # Revocation state
    is_revoked: bool = False
    revoked_at: Optional[datetime] = None
    revoke_reason: Optional[str] = None

    # Expiration
    expires_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
        + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    last_used_at: Optional[datetime] = None

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # -----------------------------------------------------------------------
    # Factory Methods
    # -----------------------------------------------------------------------

    @classmethod
    def create_new(
        cls,
        user_id: UUID,
        refresh_token_hash: str,
        family_id: Optional[UUID] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        device_name: Optional[str] = None,
    ) -> Session:
        """
        Create a new session for a user.

        Args:
            user_id: The authenticated user's ID.
            refresh_token_hash: SHA-256 hash of the refresh token.
            family_id: Token family ID (new UUID for fresh login,
                       inherited from parent for rotation).
            user_agent: Client User-Agent header.
            ip_address: Client IP address.
            device_name: Human-readable device name.

        Returns:
            New Session instance.
        """
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid4(),
            user_id=user_id,
            family_id=family_id or uuid4(),
            refresh_token_hash=refresh_token_hash,
            user_agent=user_agent,
            ip_address=ip_address,
            device_name=device_name,
            is_revoked=False,
            expires_at=now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
            last_used_at=now,
            created_at=now,
        )

    @classmethod
    def create_rotated(
        cls,
        parent: Session,
        new_refresh_token_hash: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        device_name: Optional[str] = None,
    ) -> Session:
        """
        Create a new session by rotating from a parent session.

        Inherits the parent's family_id for reuse detection.

        Args:
            parent: The parent session being rotated.
            new_refresh_token_hash: SHA-256 hash of the new refresh token.
            user_agent: Client User-Agent (may differ from parent).
            ip_address: Client IP address.
            device_name: Human-readable device name.

        Returns:
            New Session instance sharing the parent's family_id.
        """
        return cls.create_new(
            user_id=parent.user_id,
            refresh_token_hash=new_refresh_token_hash,
            family_id=parent.family_id,
            user_agent=user_agent or parent.user_agent,
            ip_address=ip_address or parent.ip_address,
            device_name=device_name or parent.device_name,
        )

    # -----------------------------------------------------------------------
    # State Checks
    # -----------------------------------------------------------------------

    @property
    def is_expired(self) -> bool:
        """Check if session has expired."""
        return datetime.now(timezone.utc) >= self.expires_at

    @property
    def is_active(self) -> bool:
        """Check if session is active (not revoked and not expired)."""
        return not self.is_revoked and not self.is_expired

    @property
    def is_within_grace_period(self) -> bool:
        """
        Check if a revoked session is within the concurrent grace period.

        During token rotation, the old token is revoked. If a concurrent request
        arrives using the old token within 2 seconds, it's treated as a legitimate
        concurrent request rather than a reuse attack.
        """
        if not self.is_revoked or self.revoked_at is None:
            return False
        elapsed = (datetime.now(timezone.utc) - self.revoked_at).total_seconds()
        return elapsed < TOKEN_ROTATION_GRACE_PERIOD_SECONDS

    # -----------------------------------------------------------------------
    # Mutations
    # -----------------------------------------------------------------------

    def revoke(self, reason: str) -> None:
        """
        Revoke this session.

        Args:
            reason: Revocation reason (must be a valid reason).

        Raises:
            ValueError: If reason is not a recognized revocation reason.
        """
        if reason not in VALID_REVOKE_REASONS and reason != "session_limit_exceeded":
            raise ValueError(
                f"Invalid revoke reason: {reason}. "
                f"Valid reasons: {', '.join(sorted(VALID_REVOKE_REASONS))}"
            )

        self.is_revoked = True
        self.revoked_at = datetime.now(timezone.utc)
        self.revoke_reason = reason

    def touch(self) -> None:
        """Update last_used_at timestamp."""
        self.last_used_at = datetime.now(timezone.utc)

    # -----------------------------------------------------------------------
    # Serialization
    # -----------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses (session list for user)."""
        return {
            "id": str(self.id),
            "device_name": self.device_name,
            "ip_address": self.ip_address,
            "is_current": False,  # Set by caller based on request context
            "last_used_at": (
                self.last_used_at.isoformat() if self.last_used_at else None
            ),
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }
