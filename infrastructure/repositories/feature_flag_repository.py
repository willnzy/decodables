"""
Feature Flag Repository Implementation - Supabase data access for platform domain.

@module infrastructure.repositories.feature_flag_repository
@version 2.0.0 (AsyncClient migration)

Changes in v2.0:
- Removed lazy loading (client parameter now mandatory)
- All methods use AsyncClient
- Removed get_supabase_client() import (sync client)

Implements IFeatureFlagRepository using Supabase PostgreSQL.
"""

from typing import Optional, List
from datetime import datetime, timezone
import logging
import json

from domains.platform.repository import IFeatureFlagRepository
from domains.platform.aggregates.feature_flag import FeatureFlag
from domains.platform.value_objects import (
    FlagStatus,
    TargetingRule,
    TargetType,
)

logger = logging.getLogger(__name__)


class SupabaseFeatureFlagRepository(IFeatureFlagRepository):
    """
    Supabase implementation of feature flag repository.

    v2.0: AsyncClient required (no lazy loading).
    """

    def __init__(self, client):
        """
        Initialize repository with AsyncClient.

        Args:
            client: AsyncClient instance (required)

        Raises:
            ValueError: If client is None
        """
        if client is None:
            raise ValueError("AsyncClient required for SupabaseFeatureFlagRepository")
        self._client = client

    @property
    def client(self):
        """Get AsyncClient instance."""
        return self._client

    async def get_by_key(self, key: str) -> Optional[FeatureFlag]:
        """Get feature flag by key."""
        try:
            result = await self.client.table("feature_flags").select(
                "*, rollout_percentage"
            ).eq(
                "key", key
            ).single().execute()

            if not result.data:
                return None

            return self._map_to_flag(result.data)

        except Exception as e:
            logger.error(f"Failed to get feature flag {key}: {e}")
            return None

    async def save(self, flag: FeatureFlag) -> FeatureFlag:
        """Persist feature flag (upsert)."""
        try:
            data = self._map_to_row(flag)
            await self.client.table("feature_flags").upsert(
                data, on_conflict="key"
            ).execute()

            return flag

        except Exception as e:
            logger.error(f"Failed to save feature flag {flag.key}: {e}")
            raise

    async def create(self, flag: FeatureFlag) -> FeatureFlag:
        """Create a new feature flag."""
        try:
            data = self._map_to_row(flag)
            result = await self.client.table("feature_flags").insert(data).execute()

            return flag

        except Exception as e:
            logger.error(f"Failed to create feature flag {flag.key}: {e}")
            raise

    async def update(self, flag: FeatureFlag) -> FeatureFlag:
        """Update existing feature flag."""
        try:
            data = self._map_to_row(flag)
            data["updated_at"] = datetime.now(timezone.utc).isoformat()

            await self.client.table("feature_flags").update(data).eq(
                "key", flag.key
            ).execute()

            return flag

        except Exception as e:
            logger.error(f"Failed to update feature flag {flag.key}: {e}")
            raise

    async def delete(self, key: str) -> bool:
        """Delete a feature flag."""
        try:
            result = await self.client.table("feature_flags").delete().eq(
                "key", key
            ).execute()

            return len(result.data) > 0 if result.data else False

        except Exception as e:
            logger.error(f"Failed to delete feature flag {key}: {e}")
            return False

    async def get_all(
        self,
        status: Optional[FlagStatus] = None,
        tags: Optional[List[str]] = None
    ) -> List[FeatureFlag]:
        """Get all feature flags."""
        try:
            query = self.client.table("feature_flags").select(
                "*, rollout_percentage"
            ).order("key")

            if status:
                query = query.eq("status", status.value)
            if tags:
                query = query.contains("tags", tags)

            result = await query.execute()

            return [self._map_to_flag(row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to get feature flags: {e}")
            return []

    async def get_active(self) -> List[FeatureFlag]:
        """Get all active feature flags."""
        try:
            result = await self.client.table("feature_flags").select(
                "*, rollout_percentage"
            ).in_(
                "status", [FlagStatus.ACTIVE.value, FlagStatus.DEPRECATED.value]
            ).order("key").execute()

            return [self._map_to_flag(row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to get active feature flags: {e}")
            return []

    def _map_to_flag(self, row: dict) -> FeatureFlag:
        """Map database row to FeatureFlag."""
        # Parse targeting rules
        targeting_rules = []
        rules_data = row.get("targeting_rules", [])
        if isinstance(rules_data, str):
            rules_data = json.loads(rules_data)

        for rule_data in rules_data:
            rule = TargetingRule(
                rule_type=TargetType(rule_data.get("rule_type", "all_users")),
                enabled=rule_data.get("enabled", True),
                user_ids=rule_data.get("user_ids", []),
                user_tiers=rule_data.get("user_tiers", []),
                percentage=rule_data.get("percentage", 0),
                start_date=datetime.fromisoformat(rule_data["start_date"])
                    if rule_data.get("start_date") else None,
                end_date=datetime.fromisoformat(rule_data["end_date"])
                    if rule_data.get("end_date") else None,
                custom_rules=rule_data.get("custom_rules", {}),
            )
            targeting_rules.append(rule)

        flag = FeatureFlag(
            key=row["key"],
            name=row.get("name", row["key"]),
            description=row.get("description"),
            status=FlagStatus(row.get("status", "draft")),
            default_value=row.get("default_value", False),
            targeting_rules=targeting_rules,
            tags=row.get("tags", []),
            created_by=row.get("created_by"),
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
                if row.get("created_at") else datetime.now(timezone.utc),
            updated_at=datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00"))
                if row.get("updated_at") else datetime.now(timezone.utc),
        )

        # REPO-002: Add rollout_percentage support
        if "rollout_percentage" in row:
            flag.rollout_percentage = row.get("rollout_percentage", 0)

        return flag

    def _map_to_row(self, flag: FeatureFlag) -> dict:
        """Map FeatureFlag to database row."""
        return {
            "key": flag.key,
            "name": flag.name,
            "description": flag.description,
            "status": flag.status.value,
            "default_value": flag.default_value,
            "targeting_rules": json.dumps([r.to_dict() for r in flag.targeting_rules]),
            "tags": flag.tags,
            "created_by": flag.created_by,
            "rollout_percentage": getattr(flag, "rollout_percentage", 0),
        }
