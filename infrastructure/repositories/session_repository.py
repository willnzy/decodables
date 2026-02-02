"""
Session Repository — Supabase implementation.

Implements ISessionRepository for the auth domain.
Manages refresh token sessions with rotation and reuse detection.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from core.database import retry_on_network_error_async
from domains.auth.aggregates.session import Session
from domains.auth.repository import ISessionRepository

logger = logging.getLogger(__name__)


class SupabaseSessionRepository(ISessionRepository):
    """
    Supabase implementation of ISessionRepository.

    Operates on the auth_sessions table.
    """

    TABLE = "auth_sessions"

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
    def _map_to_entity(row: Dict[str, Any]) -> Session:
        """Map database row to Session entity."""
        return Session(
            id=UUID(row["id"]) if isinstance(row["id"], str) else row["id"],
            user_id=UUID(row["user_id"]) if isinstance(row["user_id"], str) else row["user_id"],
            family_id=UUID(row["family_id"]) if isinstance(row["family_id"], str) else row["family_id"],
            refresh_token_hash=row["refresh_token_hash"],
            user_agent=row.get("user_agent"),
            ip_address=row.get("ip_address"),
            device_name=row.get("device_name"),
            is_revoked=row.get("is_revoked", False),
            revoked_at=_parse_datetime(row.get("revoked_at")),
            revoke_reason=row.get("revoke_reason"),
            expires_at=_parse_datetime(row.get("expires_at")) or datetime.now(timezone.utc),
            last_used_at=_parse_datetime(row.get("last_used_at")),
            created_at=_parse_datetime(row.get("created_at")) or datetime.now(timezone.utc),
        )

    @staticmethod
    def _map_to_row(session: Session) -> Dict[str, Any]:
        """Map Session entity to database row for insert."""
        return {
            "id": str(session.id),
            "user_id": str(session.user_id),
            "family_id": str(session.family_id),
            "refresh_token_hash": session.refresh_token_hash,
            "user_agent": session.user_agent,
            "ip_address": session.ip_address,
            "device_name": session.device_name,
            "is_revoked": session.is_revoked,
            "revoked_at": session.revoked_at.isoformat() if session.revoked_at else None,
            "revoke_reason": session.revoke_reason,
            "expires_at": session.expires_at.isoformat(),
            "last_used_at": session.last_used_at.isoformat() if session.last_used_at else None,
            "created_at": session.created_at.isoformat(),
        }

    # -------------------------------------------------------------------
    # Query Methods
    # -------------------------------------------------------------------

    @retry_on_network_error_async()
    async def get_by_token_hash(self, token_hash: str) -> Optional[Session]:
        """Get session by refresh token hash."""
        result = await (
            self._client.table(self.TABLE)
            .select("*")
            .eq("refresh_token_hash", token_hash)
            .maybe_single()
            .execute()
        )
        if not result.data:
            return None
        return self._map_to_entity(result.data)

    @retry_on_network_error_async()
    async def get_active_by_user(self, user_id: UUID) -> List[Session]:
        """Get all active sessions for a user, ordered by last_used_at desc."""
        now = datetime.now(timezone.utc).isoformat()
        result = await (
            self._client.table(self.TABLE)
            .select("*")
            .eq("user_id", str(user_id))
            .eq("is_revoked", False)
            .gt("expires_at", now)
            .order("last_used_at", desc=True)
            .execute()
        )
        return [self._map_to_entity(row) for row in (result.data or [])]

    @retry_on_network_error_async()
    async def count_active_by_user(self, user_id: UUID) -> int:
        """Count active sessions for a user."""
        now = datetime.now(timezone.utc).isoformat()
        result = await (
            self._client.table(self.TABLE)
            .select("id", count="exact")
            .eq("user_id", str(user_id))
            .eq("is_revoked", False)
            .gt("expires_at", now)
            .execute()
        )
        return result.count or 0

    # -------------------------------------------------------------------
    # Command Methods
    # -------------------------------------------------------------------

    @retry_on_network_error_async()
    async def create(self, session: Session) -> Session:
        """Create a new session."""
        data = self._map_to_row(session)
        result = await (
            self._client.table(self.TABLE)
            .insert(data)
            .execute()
        )
        if not result.data:
            raise RuntimeError("Failed to create session — no data returned")
        return self._map_to_entity(result.data[0])

    @retry_on_network_error_async()
    async def revoke(self, session_id: UUID, reason: str) -> None:
        """Revoke a specific session."""
        now = datetime.now(timezone.utc).isoformat()
        await (
            self._client.table(self.TABLE)
            .update({
                "is_revoked": True,
                "revoked_at": now,
                "revoke_reason": reason,
            })
            .eq("id", str(session_id))
            .execute()
        )

    @retry_on_network_error_async()
    async def revoke_family(self, family_id: UUID, reason: str) -> None:
        """Revoke all sessions in a token family (reuse detection)."""
        now = datetime.now(timezone.utc).isoformat()
        await (
            self._client.table(self.TABLE)
            .update({
                "is_revoked": True,
                "revoked_at": now,
                "revoke_reason": reason,
            })
            .eq("family_id", str(family_id))
            .eq("is_revoked", False)
            .execute()
        )

    @retry_on_network_error_async()
    async def revoke_all_by_user(self, user_id: UUID, reason: str) -> None:
        """Revoke all active sessions for a user."""
        now = datetime.now(timezone.utc).isoformat()
        await (
            self._client.table(self.TABLE)
            .update({
                "is_revoked": True,
                "revoked_at": now,
                "revoke_reason": reason,
            })
            .eq("user_id", str(user_id))
            .eq("is_revoked", False)
            .execute()
        )

    @retry_on_network_error_async()
    async def revoke_oldest_by_user(self, user_id: UUID, reason: str) -> None:
        """
        Revoke the oldest active session for a user.

        Used when concurrent session limit is exceeded.
        Selects the session with the earliest last_used_at.
        """
        now_str = datetime.now(timezone.utc).isoformat()

        # Find the oldest active session
        result = await (
            self._client.table(self.TABLE)
            .select("id")
            .eq("user_id", str(user_id))
            .eq("is_revoked", False)
            .gt("expires_at", now_str)
            .order("last_used_at", desc=False)
            .limit(1)
            .execute()
        )

        if result.data and len(result.data) > 0:
            oldest_id = result.data[0]["id"]
            await (
                self._client.table(self.TABLE)
                .update({
                    "is_revoked": True,
                    "revoked_at": now_str,
                    "revoke_reason": reason,
                })
                .eq("id", oldest_id)
                .execute()
            )

    @retry_on_network_error_async()
    async def update_last_used(self, session_id: UUID) -> None:
        """Update session's last_used_at timestamp."""
        await (
            self._client.table(self.TABLE)
            .update({
                "last_used_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", str(session_id))
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
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
