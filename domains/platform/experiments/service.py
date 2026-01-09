"""
Experiment Service - Domain service for A/B testing experiments.

@module domains.platform.experiments.service
@version 1.0.0

This is the DDD-compliant service that uses ExperimentRepository.
Replaces the module-function approach in crud.py with class-based service.
"""

import logging
from typing import Optional, List, Dict, Any, Tuple

from infrastructure.repositories.experiment_repository import SupabaseExperimentRepository

logger = logging.getLogger(__name__)


class ExperimentService:
    """
    Domain service for experiment management.

    Responsibilities:
    - Experiment CRUD operations
    - Experiment lifecycle management (status updates)
    - Active experiment queries
    """

    def __init__(self, experiment_repo: SupabaseExperimentRepository):
        """
        Initialize service with repository.

        Args:
            experiment_repo: Experiment repository instance
        """
        self._repo = experiment_repo

    async def list_experiments(
        self,
        status: Optional[str] = None,
        experiment_type: Optional[str] = None,
        offset: int = 0,
        limit: int = 20
    ) -> Tuple[List[Dict], int]:
        """
        List experiments with filters.

        Args:
            status: Filter by experiment status
            experiment_type: Filter by experiment type
            offset: Number of items to skip (DDD standard pagination)
            limit: Maximum number of items to return

        Returns:
            Tuple of (experiments list, total count)
        """
        try:
            experiments, total = await self._repo.list_experiments(
                status=status,
                experiment_type=experiment_type,
                offset=offset,
                limit=limit
            )
            return (experiments, total)
        except Exception as e:
            logger.error(f"[ExperimentService] Failed to list: {e}")
            return ([], 0)

    async def get_experiment(self, experiment_key: str) -> Optional[Dict]:
        """
        Get experiment by key.

        Args:
            experiment_key: Experiment identifier

        Returns:
            Experiment dict or None
        """
        try:
            experiment = await self._repo.get_by_key(experiment_key)
            return experiment
        except Exception as e:
            logger.error(f"[ExperimentService] Failed to get {experiment_key}: {e}")
            return None

    async def get_experiment_by_id(self, experiment_id: str) -> Optional[Dict]:
        """
        Get experiment by ID.

        Args:
            experiment_id: Experiment UUID

        Returns:
            Experiment dict or None
        """
        try:
            result = await self._repo.get_by_id(experiment_id)
            if result:
                # Convert Experiment aggregate to dict
                return result.__dict__ if hasattr(result, '__dict__') else result
            return None
        except Exception as e:
            logger.error(f"[ExperimentService] Failed to get by ID {experiment_id}: {e}")
            return None

    async def get_active_experiments(self) -> List[Dict]:
        """
        Get all active (running) experiments.

        Returns:
            List of active experiments
        """
        try:
            experiments, _ = await self._repo.list_experiments(
                status="running",
                offset=0,
                limit=10000  # Get all active experiments
            )
            return experiments
        except Exception as e:
            logger.error(f"[ExperimentService] Failed to get active experiments: {e}")
            return []

    async def create_experiment(
        self,
        experiment_key: str,
        name: str,
        description: str,
        experiment_type: str,
        variants: List[Dict],
        targeting: Optional[Dict] = None,
        metrics: Optional[List[Dict]] = None,
        status: str = "draft"
    ) -> Optional[Dict]:
        """
        Create new experiment.

        Args:
            experiment_key: Unique experiment identifier
            name: Human-readable name
            description: Experiment description
            experiment_type: Type (ab, multivariate, feature_flag)
            variants: List of variant configurations
            targeting: Targeting rules
            metrics: List of metrics to track
            status: Initial status (default: draft)

        Returns:
            Created experiment dict or None
        """
        try:
            # Build experiment data
            experiment_data = {
                "experiment_key": experiment_key,
                "name": name,
                "description": description,
                "experiment_type": experiment_type,
                "variants": variants,
                "targeting": targeting,
                "metrics": metrics,
                "status": status
            }

            result = await self._repo.create(experiment_data)
            return result
        except Exception as e:
            logger.error(f"[ExperimentService] Failed to create {experiment_key}: {e}")
            return None

    async def update_experiment(
        self,
        experiment_key: str,
        **kwargs
    ) -> Optional[Dict]:
        """
        Update experiment.

        Args:
            experiment_key: Experiment identifier
            **kwargs: Fields to update

        Returns:
            Updated experiment dict or None
        """
        try:
            result = await self._repo.update(experiment_key, kwargs)
            return result
        except Exception as e:
            logger.error(f"[ExperimentService] Failed to update {experiment_key}: {e}")
            return None

    async def update_experiment_status(
        self,
        experiment_key: str,
        status: str
    ) -> Optional[Dict]:
        """
        Update experiment status.

        Args:
            experiment_key: Experiment identifier
            status: New status (draft, running, paused, completed)

        Returns:
            Updated experiment dict or None
        """
        try:
            result = await self._repo.update_status(experiment_key, status)
            return result
        except Exception as e:
            logger.error(f"[ExperimentService] Failed to update status {experiment_key}: {e}")
            return None

    async def delete_experiment(self, experiment_key: str) -> bool:
        """
        Delete experiment.

        Args:
            experiment_key: Experiment identifier

        Returns:
            True if deleted successfully
        """
        try:
            result = await self._repo.delete(experiment_key)
            return result
        except Exception as e:
            logger.error(f"[ExperimentService] Failed to delete {experiment_key}: {e}")
            return False
