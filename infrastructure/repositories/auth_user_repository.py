"""
AuthUser Repository — Supabase implementation.

Implements IAuthUserRepository for the auth domain.
Uses AsyncClient for all database operations.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from uuid import UUID

from core.database import retry_on_network_error_async
from domains.auth.aggregates.auth_user import AuthUser
from domains.auth.repository import IAuthUserRepository

logger = logging.getLogger(__name__)


class SupabaseAuthUserRepository(IAuthUserRepository):
    """
    Supabase implementation of IAuthUserRepository.

    Operates on the auth_users table. Uses RPC for atomic
    creation with profiles table.
    """

    TABLE = "auth_users"

    def __init__(self, client: Any) -> None:
        """
        Initialize with AsyncClient.

        Args:
            client: Supabase AsyncClient instance.
        """
        if client is None:
            raise ValueError("AsyncClient is required")
        self._client = client

    # -------------------------------------------------------------------
    # Mapping
    # -------------------------------------------------------------------

    @staticmethod
    def _map_to_entity(row: Dict[str, Any]) -> AuthUser:
        """Map database row to AuthUser aggregate."""
        return AuthUser(
            id=UUID(row["id"]) if isinstance(row["id"], str) else row["id"],
            email=row["email"],
            password_hash=row["password_hash"],
            email_verified=row.get("email_verified", False),
            email_verified_at=_parse_datetime(row.get("email_verified_at")),
            email_verification_token=row.get("email_verification_token"),
            email_verification_expires_at=_parse_datetime(
                row.get("email_verification_expires_at")
            ),
            password_reset_token=row.get("password_reset_token"),
            password_reset_expires_at=_parse_datetime(
                row.get("password_reset_expires_at")
            ),
            password_changed_at=_parse_datetime(row.get("password_changed_at")),
            failed_login_attempts=row.get("failed_login_attempts", 0),
            locked_until=_parse_datetime(row.get("locked_until")),
            last_login_at=_parse_datetime(row.get("last_login_at")),
            last_login_ip=row.get("last_login_ip"),
            is_active=row.get("is_active", True),
            created_at=_parse_datetime(row.get("created_at")) or datetime.now(timezone.utc),
            updated_at=_parse_datetime(row.get("updated_at")) or datetime.now(timezone.utc),
        )

    # -------------------------------------------------------------------
    # Query Methods
    # -------------------------------------------------------------------

    @retry_on_network_error_async()
    async def get_by_id(self, user_id: UUID) -> Optional[AuthUser]:
        """Get auth user by ID."""
        result = await (
            self._client.table(self.TABLE)
            .select("*")
            .eq("id", str(user_id))
            .maybe_single()
            .execute()
        )
        if not result.data:
            return None
        return self._map_to_entity(result.data)

    @retry_on_network_error_async()
    async def get_by_email(self, email: str) -> Optional[AuthUser]:
        """Get auth user by email (normalized to lowercase)."""
        result = await (
            self._client.table(self.TABLE)
            .select("*")
            .eq("email", email.strip().lower())
            .maybe_single()
            .execute()
        )
        if not result.data:
            return None
        return self._map_to_entity(result.data)

    # -------------------------------------------------------------------
    # Command Methods
    # -------------------------------------------------------------------

    @retry_on_network_error_async()
    async def create(
        self,
        auth_user: AuthUser,
        display_name: Optional[str] = None,
        signup_bonus: int = 0,
    ) -> Tuple[AuthUser, bool]:
        """
        Create auth user + profile atomically via RPC.

        Returns (AuthUser, was_created).
        """
        try:
            result = await self._client.rpc(
                "create_auth_user_with_profile",
                {
                    "p_email": auth_user.email,
                    "p_password_hash": auth_user.password_hash,
                    "p_display_name": display_name,
                    "p_signup_bonus": signup_bonus,
                },
            ).execute()

            if not result.data or len(result.data) == 0:
                raise RuntimeError("RPC create_auth_user_with_profile returned no data")

            row = result.data[0]
            auth_user_data = row["auth_user"]
            was_created = row["was_created"]

            # Parse the JSONB result into an AuthUser
            entity = AuthUser(
                id=UUID(auth_user_data["id"]),
                email=auth_user_data["email"],
                password_hash=auth_user_data["password_hash"],
                email_verified=auth_user_data.get("email_verified", False),
                is_active=auth_user_data.get("is_active", True),
                created_at=_parse_datetime(auth_user_data.get("created_at"))
                or datetime.now(timezone.utc),
                updated_at=_parse_datetime(auth_user_data.get("updated_at"))
                or datetime.now(timezone.utc),
            )

            return entity, was_created

        except Exception as e:
            error_msg = str(e)
            # Handle unique_violation for email (RPC should handle this,
            # but add defensive fallback)
            if "unique_violation" in error_msg or "already exists" in error_msg.lower():
                existing = await self.get_by_email(auth_user.email)
                if existing:
                    return existing, False
            raise

    @retry_on_network_error_async()
    async def update_password(
        self,
        user_id: UUID,
        password_hash: str,
    ) -> None:
        """Update user's password hash."""
        await (
            self._client.table(self.TABLE)
            .update({
                "password_hash": password_hash,
                "password_changed_at": datetime.now(timezone.utc).isoformat(),
                "password_reset_token": None,
                "password_reset_expires_at": None,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", str(user_id))
            .execute()
        )

    @retry_on_network_error_async()
    async def update_email_verified(
        self,
        user_id: UUID,
        verified: bool,
    ) -> None:
        """Update email verification status."""
        data: Dict[str, Any] = {
            "email_verified": verified,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if verified:
            data["email_verified_at"] = datetime.now(timezone.utc).isoformat()
            data["email_verification_token"] = None
            data["email_verification_expires_at"] = None

        await (
            self._client.table(self.TABLE)
            .update(data)
            .eq("id", str(user_id))
            .execute()
        )

    @retry_on_network_error_async()
    async def update_login_attempt(
        self,
        user_id: UUID,
        failed_attempts: int,
        locked_until: Optional[datetime],
    ) -> None:
        """Update failed login attempt count and lockout state."""
        await (
            self._client.table(self.TABLE)
            .update({
                "failed_login_attempts": failed_attempts,
                "locked_until": locked_until.isoformat() if locked_until else None,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", str(user_id))
            .execute()
        )

    @retry_on_network_error_async()
    async def set_verification_token(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> None:
        """Set email verification token."""
        await (
            self._client.table(self.TABLE)
            .update({
                "email_verification_token": token_hash,
                "email_verification_expires_at": expires_at.isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", str(user_id))
            .execute()
        )

    @retry_on_network_error_async()
    async def set_password_reset_token(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> None:
        """Set password reset token."""
        await (
            self._client.table(self.TABLE)
            .update({
                "password_reset_token": token_hash,
                "password_reset_expires_at": expires_at.isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", str(user_id))
            .execute()
        )

    @retry_on_network_error_async()
    async def clear_verification_token(self, user_id: UUID) -> None:
        """Clear email verification token."""
        await (
            self._client.table(self.TABLE)
            .update({
                "email_verification_token": None,
                "email_verification_expires_at": None,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", str(user_id))
            .execute()
        )

    @retry_on_network_error_async()
    async def clear_password_reset_token(self, user_id: UUID) -> None:
        """Clear password reset token."""
        await (
            self._client.table(self.TABLE)
            .update({
                "password_reset_token": None,
                "password_reset_expires_at": None,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", str(user_id))
            .execute()
        )

    @retry_on_network_error_async()
    async def record_login(
        self,
        user_id: UUID,
        ip_address: Optional[str],
        timestamp: datetime,
    ) -> None:
        """Record successful login."""
        await (
            self._client.table(self.TABLE)
            .update({
                "last_login_at": timestamp.isoformat(),
                "last_login_ip": ip_address,
                "failed_login_attempts": 0,
                "locked_until": None,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", str(user_id))
            .execute()
        )

    @retry_on_network_error_async()
    async def delete(self, user_id: UUID) -> None:
        """Hard delete auth user (cascades to sessions)."""
        await (
            self._client.table(self.TABLE)
            .delete()
            .eq("id", str(user_id))
            .execute()
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_datetime(value: Any) -> Optional[datetime]:
    """Parse ISO datetime string from Supabase to datetime object."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        # Supabase returns ISO format, sometimes with Z suffix
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
