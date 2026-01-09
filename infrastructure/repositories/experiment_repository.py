"""
Experiment Repository Implementation - Supabase data access for platform domain.

@module infrastructure.repositories.experiment_repository
@version 2.0.0 (v3.28)

Implements IExperimentRepository using Supabase PostgreSQL.

Changes in v3.28:
- Added @retry_on_network_error_async to all async methods (EXP-HIGH-1)
- Added OOM protection with .limit(10000) to all queries (EXP-HIGH-2)
- Added list_experiments() method returning tuple (EXP-CRITICAL-1)
- Added get_trend_data() and get_hourly_trend_data() methods (EXP-CRITICAL-1)
- Added get_by_key() method for key-based lookups
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import logging
import json

from domains.platform.repository import IExperimentRepository
from domains.platform.aggregates.experiment import Experiment
from domains.platform.value_objects import (
    ExperimentStatus,
    ExperimentVariant,
    TargetingRule,
    TargetType,
)
from core.database import get_supabase_client
from core.database.retry import retry_on_network_error_async

logger = logging.getLogger(__name__)


class SupabaseExperimentRepository(IExperimentRepository):
    """
    Supabase implementation of experiment repository.
    """

    def __init__(self, client=None):
        """Initialize repository with Supabase client."""
        self._client = client

    @property
    def client(self):
        """Lazy load Supabase client."""
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    @retry_on_network_error_async(max_retries=3, delay=1.0)
    async def get_by_id(self, experiment_id: str) -> Optional[Experiment]:
        """Get experiment by ID."""
        try:
            result = self.client.table("experiments").select("*").eq(
                "experiment_id", experiment_id
            ).limit(1).single().execute()

            if not result.data:
                return None

            return self._map_to_experiment(result.data)

        except Exception as e:
            logger.error(f"Failed to get experiment {experiment_id}: {e}")
            return None

    @retry_on_network_error_async(max_retries=3, delay=1.0)
    async def save(self, experiment: Experiment) -> Experiment:
        """Persist experiment (upsert)."""
        try:
            data = self._map_to_row(experiment)
            self.client.table("experiments").upsert(
                data, on_conflict="experiment_id"
            ).execute()

            return experiment

        except Exception as e:
            logger.error(f"Failed to save experiment {experiment.experiment_id}: {e}")
            raise

    @retry_on_network_error_async(max_retries=3, delay=1.0)
    async def create(self, experiment: Experiment) -> Experiment:
        """Create a new experiment."""
        try:
            data = self._map_to_row(experiment)
            self.client.table("experiments").insert(data).execute()

            return experiment

        except Exception as e:
            logger.error(f"Failed to create experiment {experiment.experiment_id}: {e}")
            raise

    @retry_on_network_error_async(max_retries=3, delay=1.0)
    async def update(self, experiment: Experiment) -> Experiment:
        """Update existing experiment."""
        try:
            data = self._map_to_row(experiment)
            data["updated_at"] = datetime.utcnow().isoformat()

            self.client.table("experiments").update(data).eq(
                "experiment_id", experiment.experiment_id
            ).execute()

            return experiment

        except Exception as e:
            logger.error(f"Failed to update experiment {experiment.experiment_id}: {e}")
            raise

    @retry_on_network_error_async(max_retries=3, delay=1.0)
    async def delete(self, experiment_id: str) -> bool:
        """Delete an experiment."""
        try:
            # Delete assignments first (limit for safety)
            self.client.table("experiment_assignments").delete().eq(
                "experiment_id", experiment_id
            ).limit(10000).execute()

            # Delete experiment
            result = self.client.table("experiments").delete().eq(
                "experiment_id", experiment_id
            ).limit(1).execute()

            return len(result.data) > 0 if result.data else False

        except Exception as e:
            logger.error(f"Failed to delete experiment {experiment_id}: {e}")
            return False

    @retry_on_network_error_async(max_retries=3, delay=1.0)
    async def get_all(
        self,
        status: Optional[ExperimentStatus] = None
    ) -> List[Experiment]:
        """Get all experiments (with OOM protection)."""
        try:
            query = self.client.table("experiments").select("*").order(
                "created_at", desc=True
            )

            if status:
                query = query.eq("status", status.value)

            result = query.limit(10000).execute()  # OOM protection

            return [self._map_to_experiment(row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to get experiments: {e}")
            return []

    @retry_on_network_error_async(max_retries=3, delay=1.0)
    async def get_running(self) -> List[Experiment]:
        """Get all running experiments (with OOM protection)."""
        try:
            result = self.client.table("experiments").select("*").eq(
                "status", ExperimentStatus.RUNNING.value
            ).limit(1000).execute()  # OOM protection (fewer running experiments expected)

            return [self._map_to_experiment(row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to get running experiments: {e}")
            return []

    @retry_on_network_error_async(max_retries=3, delay=1.0)
    async def record_assignment(
        self,
        experiment_id: str,
        user_id: str,
        variant_id: str
    ) -> bool:
        """Record a user's variant assignment."""
        try:
            self.client.table("experiment_assignments").upsert({
                "experiment_id": experiment_id,
                "user_id": user_id,
                "variant_id": variant_id,
                "assigned_at": datetime.utcnow().isoformat(),
            }, on_conflict="experiment_id,user_id").execute()

            return True

        except Exception as e:
            logger.error(f"Failed to record assignment: {e}")
            return False

    @retry_on_network_error_async(max_retries=3, delay=1.0)
    async def get_user_assignment(
        self,
        experiment_id: str,
        user_id: str
    ) -> Optional[str]:
        """Get user's assigned variant."""
        try:
            result = self.client.table("experiment_assignments").select(
                "variant_id"
            ).eq("experiment_id", experiment_id).eq(
                "user_id", user_id
            ).limit(1).single().execute()

            if result.data:
                return result.data["variant_id"]
            return None

        except Exception:
            return None

    def _map_to_experiment(self, row: dict) -> Experiment:
        """Map database row to Experiment."""
        # Parse variants
        variants = []
        variants_data = row.get("variants", [])
        if isinstance(variants_data, str):
            variants_data = json.loads(variants_data)

        for v_data in variants_data:
            variant = ExperimentVariant(
                variant_id=v_data["variant_id"],
                name=v_data["name"],
                weight=v_data.get("weight", 50),
                config=v_data.get("config", {}),
            )
            variants.append(variant)

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
            )
            targeting_rules.append(rule)

        return Experiment(
            experiment_id=row["experiment_id"],
            name=row["name"],
            description=row.get("description"),
            status=ExperimentStatus(row.get("status", "draft")),
            variants=variants,
            targeting_rules=targeting_rules,
            start_date=datetime.fromisoformat(row["start_date"].replace("Z", "+00:00"))
                if row.get("start_date") else None,
            end_date=datetime.fromisoformat(row["end_date"].replace("Z", "+00:00"))
                if row.get("end_date") else None,
            created_by=row.get("created_by"),
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
                if row.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00"))
                if row.get("updated_at") else datetime.utcnow(),
        )

    def _map_to_row(self, experiment: Experiment) -> dict:
        """Map Experiment to database row."""
        return {
            "experiment_id": experiment.experiment_id,
            "name": experiment.name,
            "description": experiment.description,
            "status": experiment.status.value,
            "variants": json.dumps([v.to_dict() for v in experiment.variants]),
            "targeting_rules": json.dumps([r.to_dict() for r in experiment.targeting_rules]),
            "start_date": experiment.start_date.isoformat() if experiment.start_date else None,
            "end_date": experiment.end_date.isoformat() if experiment.end_date else None,
            "created_by": experiment.created_by,
        }

    # ==========================================
    # New Methods (v3.28) - For DDD Migration
    # ==========================================

    @retry_on_network_error_async(max_retries=3, delay=1.0)
    async def get_by_key(self, experiment_key: str) -> Optional[Dict]:
        """
        Get experiment by experiment_key (not ID).

        v3.28: Added to support API layer migration (EXP-CRITICAL-1).
        Returns dict (not Aggregate) for compatibility with current API.
        """
        try:
            result = self.client.table("experiments").select("*").eq(
                "experiment_key", experiment_key
            ).limit(1).single().execute()

            if not result.data:
                return None

            return result.data

        except Exception as e:
            logger.error(f"Failed to get experiment by key {experiment_key}: {e}")
            return None

    @retry_on_network_error_async(max_retries=3, delay=1.0)
    async def list_experiments(
        self,
        status: Optional[str] = None,
        experiment_type: Optional[str] = None,
        offset: int = 0,
        limit: int = 20
    ) -> Tuple[List[Dict], int]:
        """
        List experiments with filters and pagination.

        v3.28: Added to replace domains/platform/experiments/crud.py (EXP-CRITICAL-1).
        Returns (experiments, total) tuple to match API expectations.

        Args:
            status: Filter by status (draft/running/paused/completed)
            experiment_type: Filter by type
            offset: Pagination offset
            limit: Page size

        Returns:
            Tuple of (experiments list, total count)
        """
        try:
            query = self.client.table("experiments").select("*", count="exact")

            if status:
                query = query.eq("status", status)
            if experiment_type:
                query = query.eq("experiment_type", experiment_type)

            result = query.order("created_at", desc=True)\
                .range(offset, offset + limit - 1)\
                .limit(10000)\
                .execute()

            items = result.data or []
            total = result.count or 0

            return (items, total)

        except Exception as e:
            logger.error(f"[ExperimentRepo] Failed to list experiments: {e}")
            return ([], 0)

    @retry_on_network_error_async(max_retries=3, delay=1.0)
    async def get_trend_data(
        self,
        experiment_id: str,
        start_date: str,
        days: int
    ) -> List[Dict]:
        """
        Get daily trend data for experiment.

        v3.28: Added to support trend endpoints (EXP-CRITICAL-1).
        Retrieves aggregated results from experiment_results table.

        Args:
            experiment_id: Experiment ID
            start_date: Start date (YYYY-MM-DD)
            days: Number of days

        Returns:
            List of daily result records
        """
        try:
            result = self.client.table("experiment_results").select("*")\
                .eq("experiment_id", experiment_id)\
                .gte("date", start_date)\
                .order("date")\
                .limit(10000)\
                .execute()

            return result.data or []

        except Exception as e:
            logger.error(f"[ExperimentRepo] Failed to get trend data for {experiment_id}: {e}")
            return []

    @retry_on_network_error_async(max_retries=3, delay=1.0)
    async def get_hourly_trend_data(
        self,
        experiment_id: str,
        start_date: str,
        hours: int
    ) -> List[Dict]:
        """
        Get hourly trend data for experiment.

        v3.28: Added to support hourly trend endpoints (EXP-CRITICAL-1).
        Retrieves hourly aggregated results from experiment_results table.

        Args:
            experiment_id: Experiment ID
            start_date: Start date (YYYY-MM-DD)
            hours: Number of hours

        Returns:
            List of hourly result records
        """
        try:
            result = self.client.table("experiment_results").select("*")\
                .eq("experiment_id", experiment_id)\
                .gte("date", start_date)\
                .order("date").order("hour")\
                .limit(10000)\
                .execute()

            return result.data or []

        except Exception as e:
            logger.error(f"[ExperimentRepo] Failed to get hourly trend data for {experiment_id}: {e}")
            return []
