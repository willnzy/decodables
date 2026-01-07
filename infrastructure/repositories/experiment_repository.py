"""
Experiment Repository Implementation - Supabase data access for platform domain.

@module infrastructure.repositories.experiment_repository
@version 1.0.0

Implements IExperimentRepository using Supabase PostgreSQL.
"""

from typing import Optional, List
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

    async def get_by_id(self, experiment_id: str) -> Optional[Experiment]:
        """Get experiment by ID."""
        try:
            result = self.client.table("experiments").select("*").eq(
                "experiment_id", experiment_id
            ).single().execute()

            if not result.data:
                return None

            return self._map_to_experiment(result.data)

        except Exception as e:
            logger.error(f"Failed to get experiment {experiment_id}: {e}")
            return None

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

    async def create(self, experiment: Experiment) -> Experiment:
        """Create a new experiment."""
        try:
            data = self._map_to_row(experiment)
            self.client.table("experiments").insert(data).execute()

            return experiment

        except Exception as e:
            logger.error(f"Failed to create experiment {experiment.experiment_id}: {e}")
            raise

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

    async def delete(self, experiment_id: str) -> bool:
        """Delete an experiment."""
        try:
            # Delete assignments first
            self.client.table("experiment_assignments").delete().eq(
                "experiment_id", experiment_id
            ).execute()

            # Delete experiment
            result = self.client.table("experiments").delete().eq(
                "experiment_id", experiment_id
            ).execute()

            return len(result.data) > 0 if result.data else False

        except Exception as e:
            logger.error(f"Failed to delete experiment {experiment_id}: {e}")
            return False

    async def get_all(
        self,
        status: Optional[ExperimentStatus] = None
    ) -> List[Experiment]:
        """Get all experiments."""
        try:
            query = self.client.table("experiments").select("*").order(
                "created_at", desc=True
            )

            if status:
                query = query.eq("status", status.value)

            result = query.execute()

            return [self._map_to_experiment(row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to get experiments: {e}")
            return []

    async def get_running(self) -> List[Experiment]:
        """Get all running experiments."""
        try:
            result = self.client.table("experiments").select("*").eq(
                "status", ExperimentStatus.RUNNING.value
            ).execute()

            return [self._map_to_experiment(row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to get running experiments: {e}")
            return []

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
            ).single().execute()

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
