"""
Campaign Repository Implementation - Supabase implementation of campaign data access.

@module infrastructure.repositories.campaign_repository
@version 1.0.0
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Set, Tuple

from domains.marketing.repository import ICampaignRepository, CampaignData

logger = logging.getLogger(__name__)


class SupabaseCampaignRepository(ICampaignRepository):
    """Supabase implementation of campaign repository."""

    def __init__(self, client):
        """
        Initialize repository with Supabase client.

        Args:
            client: Supabase client instance
        """
        self.client = client

    async def get_active_campaigns(self) -> List[CampaignData]:
        """Get all currently active campaigns within valid time range."""
        now = datetime.now(timezone.utc)

        result = self.client.table("campaigns").select("*").eq(
            "status", "active",
        ).eq("is_active", True).lte(
            "start_at", now.isoformat(),
        ).gte(
            "end_at", now.isoformat(),
        ).execute()

        return [self._to_campaign_data(c) for c in result.data] if result.data else []

    async def get_by_id(self, campaign_id: str) -> Optional[CampaignData]:
        """Get campaign by ID."""
        result = self.client.table("campaigns").select("*").eq(
            "id", campaign_id,
        ).execute()

        if not result.data:
            return None
        return self._to_campaign_data(result.data[0])

    async def get_user_campaign_status(
        self, campaign_ids: List[str], user_id: str
    ) -> Tuple[Set[str], Dict[str, List[str]]]:
        """Batch fetch user's claim and dismissal status for multiple campaigns."""
        claimed_campaigns: Set[str] = set()
        dismissed_map: Dict[str, List[str]] = {}

        if not campaign_ids:
            return claimed_campaigns, dismissed_map

        # Batch query claims
        try:
            claims_result = self.client.table("campaign_claims").select(
                "campaign_id"
            ).eq("user_id", user_id).in_("campaign_id", campaign_ids).execute()

            claimed_campaigns = {c["campaign_id"] for c in claims_result.data}
        except Exception as e:
            logger.warning(f"[CampaignRepo] Failed to batch fetch claims: {e}")

        # Batch query dismissals
        try:
            dismissals_result = self.client.table("campaign_dismissals").select(
                "campaign_id, channel"
            ).eq("user_id", user_id).in_("campaign_id", campaign_ids).execute()

            for d in dismissals_result.data:
                campaign_id = d["campaign_id"]
                if campaign_id not in dismissed_map:
                    dismissed_map[campaign_id] = []
                dismissed_map[campaign_id].append(d["channel"])
        except Exception as e:
            logger.warning(f"[CampaignRepo] Failed to batch fetch dismissals: {e}")

        return claimed_campaigns, dismissed_map

    async def record_claim(
        self, campaign_id: str, user_id: str, credits_received: int
    ) -> bool:
        """
        Record a campaign claim.

        Uses UNIQUE constraint to prevent race conditions.
        Returns False if claim already exists.
        """
        try:
            self.client.table("campaign_claims").insert({
                "campaign_id": campaign_id,
                "user_id": user_id,
                "credits_received": credits_received,
            }).execute()
            return True
        except Exception as e:
            if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                return False
            raise

    async def delete_claim(self, campaign_id: str, user_id: str) -> None:
        """Delete a campaign claim for rollback purposes."""
        self.client.table("campaign_claims").delete().eq(
            "campaign_id", campaign_id
        ).eq("user_id", user_id).execute()

    async def increment_usage_count(self, campaign_id: str) -> bool:
        """
        Atomically increment campaign usage count.

        Uses RPC function to ensure atomicity.
        Returns False if usage limit reached.
        """
        try:
            result = self.client.rpc("increment_campaign_usage", {
                "p_campaign_id": campaign_id,
            }).execute()

            if result.data and len(result.data) > 0:
                return result.data[0].get("success", False)
            return False
        except Exception as e:
            logger.warning(f"[CampaignRepo] Failed to increment usage_count: {e}")
            return False

    async def record_dismissal(
        self, campaign_id: str, user_id: str, channel: str
    ) -> None:
        """Record notification dismissal using upsert."""
        self.client.table("campaign_dismissals").upsert({
            "campaign_id": campaign_id,
            "user_id": user_id,
            "channel": channel,
            "dismissed_at": datetime.now(timezone.utc).isoformat(),
        }, on_conflict="campaign_id,user_id,channel").execute()

    def _to_campaign_data(self, row: dict) -> CampaignData:
        """Convert database row to CampaignData."""
        return CampaignData(
            id=row["id"],
            name=row["name"],
            description=row.get("description"),
            type=row["type"],
            config=row.get("config", {}),
            target_type=row.get("target_type", "all"),
            target_config=row.get("target_config", {}),
            notification_channels=row.get("notification_channels", ["banner"]),
            notification_config=row.get("notification_config", {}),
            start_at=datetime.fromisoformat(row["start_at"].replace("Z", "+00:00")),
            end_at=datetime.fromisoformat(row["end_at"].replace("Z", "+00:00")),
            usage_limit=row.get("usage_limit"),
            usage_count=row.get("usage_count", 0),
            status=row.get("status", "draft"),
            is_active=row.get("is_active", True),
        )
