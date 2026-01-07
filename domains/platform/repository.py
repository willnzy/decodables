"""
Platform Repository Interfaces - Abstract data access for platform domain.

@module domains.platform.repository
@version 1.0.0

This defines the repository interfaces (ports) for platform operations.
Concrete implementations live in infrastructure/repositories/.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from .aggregates.feature_flag import FeatureFlag
from .aggregates.experiment import Experiment
from .value_objects import FlagStatus, ExperimentStatus


class IFeatureFlagRepository(ABC):
    """
    Repository interface for feature flag operations.
    """

    @abstractmethod
    async def get_by_key(self, key: str) -> Optional[FeatureFlag]:
        """
        Get feature flag by key.

        Args:
            key: Feature flag key

        Returns:
            FeatureFlag or None if not found
        """
        pass

    @abstractmethod
    async def save(self, flag: FeatureFlag) -> FeatureFlag:
        """
        Persist feature flag.

        Args:
            flag: FeatureFlag to save

        Returns:
            Saved FeatureFlag
        """
        pass

    @abstractmethod
    async def create(self, flag: FeatureFlag) -> FeatureFlag:
        """
        Create a new feature flag.

        Args:
            flag: FeatureFlag to create

        Returns:
            Created FeatureFlag
        """
        pass

    @abstractmethod
    async def update(self, flag: FeatureFlag) -> FeatureFlag:
        """
        Update existing feature flag.

        Args:
            flag: FeatureFlag to update

        Returns:
            Updated FeatureFlag
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete a feature flag.

        Args:
            key: Flag key to delete

        Returns:
            True if deleted
        """
        pass

    @abstractmethod
    async def get_all(
        self,
        status: Optional[FlagStatus] = None,
        tags: Optional[List[str]] = None
    ) -> List[FeatureFlag]:
        """
        Get all feature flags.

        Args:
            status: Filter by status
            tags: Filter by tags

        Returns:
            List of FeatureFlags
        """
        pass

    @abstractmethod
    async def get_active(self) -> List[FeatureFlag]:
        """
        Get all active feature flags.

        Returns:
            List of active FeatureFlags
        """
        pass


class IExperimentRepository(ABC):
    """
    Repository interface for experiment operations.
    """

    @abstractmethod
    async def get_by_id(self, experiment_id: str) -> Optional[Experiment]:
        """
        Get experiment by ID.

        Args:
            experiment_id: Experiment ID

        Returns:
            Experiment or None if not found
        """
        pass

    @abstractmethod
    async def save(self, experiment: Experiment) -> Experiment:
        """
        Persist experiment.

        Args:
            experiment: Experiment to save

        Returns:
            Saved Experiment
        """
        pass

    @abstractmethod
    async def create(self, experiment: Experiment) -> Experiment:
        """
        Create a new experiment.

        Args:
            experiment: Experiment to create

        Returns:
            Created Experiment
        """
        pass

    @abstractmethod
    async def update(self, experiment: Experiment) -> Experiment:
        """
        Update existing experiment.

        Args:
            experiment: Experiment to update

        Returns:
            Updated Experiment
        """
        pass

    @abstractmethod
    async def delete(self, experiment_id: str) -> bool:
        """
        Delete an experiment.

        Args:
            experiment_id: Experiment ID to delete

        Returns:
            True if deleted
        """
        pass

    @abstractmethod
    async def get_all(
        self,
        status: Optional[ExperimentStatus] = None
    ) -> List[Experiment]:
        """
        Get all experiments.

        Args:
            status: Filter by status

        Returns:
            List of Experiments
        """
        pass

    @abstractmethod
    async def get_running(self) -> List[Experiment]:
        """
        Get all running experiments.

        Returns:
            List of running Experiments
        """
        pass

    @abstractmethod
    async def record_assignment(
        self,
        experiment_id: str,
        user_id: str,
        variant_id: str
    ) -> bool:
        """
        Record a user's variant assignment.

        Args:
            experiment_id: Experiment ID
            user_id: User ID
            variant_id: Assigned variant ID

        Returns:
            True if recorded
        """
        pass

    @abstractmethod
    async def get_user_assignment(
        self,
        experiment_id: str,
        user_id: str
    ) -> Optional[str]:
        """
        Get user's assigned variant.

        Args:
            experiment_id: Experiment ID
            user_id: User ID

        Returns:
            Variant ID or None
        """
        pass
