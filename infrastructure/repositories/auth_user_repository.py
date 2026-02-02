"""
AuthUser Repository — Supabase implementation.

Implements IAuthUserRepository for the auth domain.
Uses AsyncClient for all database operations.
Uses unified OTP model with RPC functions for atomic operations.
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
    creation/restore with profiles table.
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
            password_hash=row.get("password_hash"),  # None for pending users
            email_verified=row.get("email_verified", False),
            email_verified_at=_parse_datetime(row.get("email_verified_at")),
            otp_code_hash=row.get("otp_code_hash"),
            otp_purpose=row.get("otp_purpose"),
            otp_expires_at=_parse_datetime(row.get("otp_expires_at")),
            otp_attempts=row.get("otp_attempts", 0),
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
            .limit(1)
            .execute()
        )
        if result is None or not result.data:
            return None
        return self._map_to_entity(result.data[0])

    @retry_on_network_error_async()
    async def get_by_email(self, email: str) -> Optional[AuthUser]:
        """Get auth user by email (normalized to lowercase)."""
        result = await (
            self._client.table(self.TABLE)
            .select("*")
            .eq("email", email.strip().lower())
            .limit(1)
            .execute()
        )
        if result is None or not result.data:
            return None
        return self._map_to_entity(result.data[0])

    @retry_on_network_error_async()
    async def get_restorable_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Check if a soft-deleted profile exists that can be restored.

        Queries profiles table for is_deleted=true and recovery_expires_at > now.
        Uses limit(1) instead of maybe_single() to avoid supabase-py bug
        where maybe_single() can return None or raise on 0-row results.
        """
        normalized = email.strip().lower()
        now = datetime.now(timezone.utc).isoformat()
        result = await (
            self._client.table("profiles")
            .select("id, email, recovery_expires_at")
            .eq("email", normalized)
            .eq("is_deleted", True)
            .gt("recovery_expires_at", now)
            .limit(1)
            .execute()
        )
        if result is None or not result.data:
            return None
        return result.data[0]

    # -------------------------------------------------------------------
    # Command Methods — Registration (3-step OTP)
    # -------------------------------------------------------------------

    @retry_on_network_error_async()
    async def create_pending(
        self,
        auth_user: AuthUser,
    ) -> Tuple[AuthUser, bool]:
        """
        Create a pending auth user via RPC create_pending_auth_user().

        Returns (AuthUser, was_created).
        was_created=False means email already registered (has password).
        """
        try:
            result = await self._client.rpc(
                "create_pending_auth_user",
                {
                    "p_email": auth_user.email,
                    "p_otp_code_hash": auth_user.otp_code_hash,
                    "p_otp_purpose": auth_user.otp_purpose,
                    "p_otp_expires_at": auth_user.otp_expires_at.isoformat()
                    if auth_user.otp_expires_at
                    else None,
                },
            ).execute()

            if result is None or not result.data or len(result.data) == 0:
                raise RuntimeError("RPC create_pending_auth_user returned no data")

            row = result.data[0]

            # RPC returns NULL for user_id when email already registered
            if row.get("user_id") is None:
                # Already registered user — return existing
                existing = await self.get_by_email(auth_user.email)
                if existing:
                    return existing, False
                raise RuntimeError("RPC returned null user_id but no existing user found")

            # Success — create entity from RPC result
            entity = AuthUser(
                id=UUID(row["user_id"]),
                email=auth_user.email,
                password_hash=None,
                email_verified=False,
                otp_code_hash=auth_user.otp_code_hash,
                otp_purpose=auth_user.otp_purpose,
                otp_expires_at=auth_user.otp_expires_at,
                otp_attempts=0,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            return entity, True

        except Exception as e:
            error_msg = str(e)
            if "unique_violation" in error_msg or "already exists" in error_msg.lower():
                existing = await self.get_by_email(auth_user.email)
                if existing:
                    return existing, False
            raise

    @retry_on_network_error_async()
    async def complete_registration(
        self,
        user_id: UUID,
        password_hash: str,
        display_name: Optional[str] = None,
        signup_bonus: int = 0,
    ) -> AuthUser:
        """
        Complete registration via RPC create_auth_user_with_profile().

        Sets password, marks email verified, creates profile atomically.
        """
        result = await self._client.rpc(
            "create_auth_user_with_profile",
            {
                "p_user_id": str(user_id),
                "p_password_hash": password_hash,
                "p_display_name": display_name,
                "p_signup_bonus": signup_bonus,
            },
        ).execute()

        if result is None or not result.data or len(result.data) == 0:
            raise RuntimeError("RPC create_auth_user_with_profile returned no data")

        row = result.data[0]
        auth_user_data = row["auth_user"]

        return AuthUser(
            id=UUID(auth_user_data["id"]),
            email=auth_user_data["email"],
            password_hash=auth_user_data.get("password_hash"),
            email_verified=auth_user_data.get("email_verified", True),
            email_verified_at=_parse_datetime(auth_user_data.get("email_verified_at")),
            is_active=auth_user_data.get("is_active", True),
            created_at=_parse_datetime(auth_user_data.get("created_at"))
            or datetime.now(timezone.utc),
            updated_at=_parse_datetime(auth_user_data.get("updated_at"))
            or datetime.now(timezone.utc),
        )

    # -------------------------------------------------------------------
    # Command Methods — OTP
    # -------------------------------------------------------------------

    @retry_on_network_error_async()
    async def update_otp(
        self,
        user_id: UUID,
        otp_code_hash: str,
        otp_purpose: str,
        otp_expires_at: datetime,
    ) -> None:
        """Update OTP fields for a user."""
        await (
            self._client.table(self.TABLE)
            .update({
                "otp_code_hash": otp_code_hash,
                "otp_purpose": otp_purpose,
                "otp_expires_at": otp_expires_at.isoformat(),
                "otp_attempts": 0,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", str(user_id))
            .execute()
        )

    @retry_on_network_error_async()
    async def update_otp_attempts(
        self,
        user_id: UUID,
        otp_attempts: int,
    ) -> None:
        """Update OTP attempt count."""
        await (
            self._client.table(self.TABLE)
            .update({
                "otp_attempts": otp_attempts,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", str(user_id))
            .execute()
        )

    @retry_on_network_error_async()
    async def clear_otp(self, user_id: UUID) -> None:
        """Clear all OTP fields after successful verification."""
        await (
            self._client.table(self.TABLE)
            .update({
                "otp_code_hash": None,
                "otp_purpose": None,
                "otp_expires_at": None,
                "otp_attempts": 0,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", str(user_id))
            .execute()
        )

    # -------------------------------------------------------------------
    # Command Methods — Password & Account
    # -------------------------------------------------------------------

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
                "otp_code_hash": None,
                "otp_purpose": None,
                "otp_expires_at": None,
                "otp_attempts": 0,
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

    # -------------------------------------------------------------------
    # Command Methods — Account Restore
    # -------------------------------------------------------------------

    @retry_on_network_error_async()
    async def restore_account(
        self,
        email: str,
        password_hash: str,
    ) -> AuthUser:
        """
        Restore a soft-deleted account via RPC restore_auth_user_with_profile().

        Reuses the old profile UUID, creates new auth_users record,
        and restores the profile (is_deleted=false).
        """
        normalized = email.strip().lower()
        result = await self._client.rpc(
            "restore_auth_user_with_profile",
            {
                "p_email": normalized,
                "p_password_hash": password_hash,
            },
        ).execute()

        if result is None or not result.data or len(result.data) == 0:
            raise RuntimeError("RPC restore_auth_user_with_profile returned no data")

        row = result.data[0]
        auth_user_data = row["auth_user"]

        return AuthUser(
            id=UUID(auth_user_data["id"]),
            email=auth_user_data["email"],
            password_hash=auth_user_data.get("password_hash"),
            email_verified=auth_user_data.get("email_verified", True),
            email_verified_at=_parse_datetime(auth_user_data.get("email_verified_at")),
            is_active=auth_user_data.get("is_active", True),
            created_at=_parse_datetime(auth_user_data.get("created_at"))
            or datetime.now(timezone.utc),
            updated_at=_parse_datetime(auth_user_data.get("updated_at"))
            or datetime.now(timezone.utc),
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
