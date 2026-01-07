"""
Platform Domain Service - Orchestrates platform operations.

@module domains.platform.service
@version 1.0.0

This service handles domain logic for feature flags and experiments.
"""

from typing import Optional, List, Dict, Any

from .aggregates.feature_flag import FeatureFlag
from .aggregates.experiment import Experiment
from .repository import IFeatureFlagRepository, IExperimentRepository
from .value_objects import (
    FlagStatus,
    ExperimentStatus,
    TargetingRule,
    TargetType,
    ExperimentVariant,
)
from .exceptions import (
    FeatureFlagNotFoundException,
    ExperimentNotFoundException,
    InvalidConfigurationException,
)


class PlatformService:
    """
    Domain service for platform operations.

    This service:
    - Manages feature flags
    - Manages A/B experiments
    - Handles flag evaluation
    - Handles experiment assignment
    """

    def __init__(
        self,
        flag_repository: IFeatureFlagRepository,
        experiment_repository: IExperimentRepository
    ):
        """
        Initialize platform service with repositories.

        Args:
            flag_repository: Feature flag repository
            experiment_repository: Experiment repository
        """
        self._flag_repo = flag_repository
        self._experiment_repo = experiment_repository

    # ========== Feature Flag Methods ==========

    async def get_flag(self, key: str) -> Optional[FeatureFlag]:
        """Get feature flag by key."""
        return await self._flag_repo.get_by_key(key)

    async def get_flag_or_raise(self, key: str) -> FeatureFlag:
        """Get feature flag or raise exception."""
        flag = await self._flag_repo.get_by_key(key)
        if not flag:
            raise FeatureFlagNotFoundException(key)
        return flag

    async def create_flag(
        self,
        key: str,
        name: str,
        description: Optional[str] = None,
        default_value: bool = False,
        created_by: Optional[str] = None
    ) -> FeatureFlag:
        """
        Create a new feature flag.

        Args:
            key: Unique flag key
            name: Human-readable name
            description: Optional description
            default_value: Default value
            created_by: Creator user ID

        Returns:
            Created FeatureFlag
        """
        # Check if key already exists
        existing = await self._flag_repo.get_by_key(key)
        if existing:
            raise InvalidConfigurationException("feature_flag", f"Key '{key}' already exists")

        flag = FeatureFlag.create_new(
            key=key,
            name=name,
            description=description,
            default_value=default_value,
            created_by=created_by,
        )

        return await self._flag_repo.create(flag)

    async def evaluate_flag(
        self,
        key: str,
        user_id: Optional[str] = None,
        user_tier: Optional[str] = None,
        default: bool = False
    ) -> bool:
        """
        Evaluate a feature flag for a user.

        Args:
            key: Flag key
            user_id: User ID
            user_tier: User's subscription tier
            default: Default value if flag not found

        Returns:
            True if feature is enabled
        """
        flag = await self._flag_repo.get_by_key(key)
        if not flag:
            return default

        return flag.evaluate(user_id=user_id, user_tier=user_tier)

    async def is_enabled(
        self,
        key: str,
        user_id: Optional[str] = None,
        user_tier: Optional[str] = None
    ) -> bool:
        """Alias for evaluate_flag with default=False."""
        return await self.evaluate_flag(key, user_id, user_tier, default=False)

    async def activate_flag(self, key: str) -> FeatureFlag:
        """Activate a feature flag."""
        flag = await self.get_flag_or_raise(key)
        flag.activate()
        return await self._flag_repo.update(flag)

    async def deprecate_flag(self, key: str) -> FeatureFlag:
        """Deprecate a feature flag."""
        flag = await self.get_flag_or_raise(key)
        flag.deprecate()
        return await self._flag_repo.update(flag)

    async def add_flag_targeting(
        self,
        key: str,
        rule_type: TargetType,
        **kwargs
    ) -> FeatureFlag:
        """
        Add targeting rule to flag.

        Args:
            key: Flag key
            rule_type: Type of targeting rule
            **kwargs: Rule-specific parameters

        Returns:
            Updated FeatureFlag
        """
        flag = await self.get_flag_or_raise(key)

        rule = TargetingRule(rule_type=rule_type, **kwargs)
        flag.add_targeting_rule(rule)

        return await self._flag_repo.update(flag)

    async def get_all_flags(
        self,
        status: Optional[FlagStatus] = None
    ) -> List[FeatureFlag]:
        """Get all feature flags."""
        return await self._flag_repo.get_all(status=status)

    # ========== Experiment Methods ==========

    async def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """Get experiment by ID."""
        return await self._experiment_repo.get_by_id(experiment_id)

    async def get_experiment_or_raise(self, experiment_id: str) -> Experiment:
        """Get experiment or raise exception."""
        experiment = await self._experiment_repo.get_by_id(experiment_id)
        if not experiment:
            raise ExperimentNotFoundException(experiment_id)
        return experiment

    async def create_experiment(
        self,
        name: str,
        description: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Experiment:
        """
        Create a new experiment.

        Args:
            name: Experiment name
            description: Optional description
            created_by: Creator user ID

        Returns:
            Created Experiment with default control/treatment variants
        """
        experiment = Experiment.create_new(
            name=name,
            description=description,
            created_by=created_by,
        )

        return await self._experiment_repo.create(experiment)

    async def assign_experiment(
        self,
        experiment_id: str,
        user_id: str,
        user_tier: Optional[str] = None
    ) -> Optional[ExperimentVariant]:
        """
        Assign user to experiment variant.

        Args:
            experiment_id: Experiment ID
            user_id: User ID
            user_tier: User's subscription tier

        Returns:
            Assigned variant or None
        """
        # Check for existing assignment
        existing = await self._experiment_repo.get_user_assignment(
            experiment_id, user_id
        )
        if existing:
            experiment = await self.get_experiment_or_raise(experiment_id)
            for variant in experiment.variants:
                if variant.variant_id == existing:
                    return variant
            return None

        experiment = await self.get_experiment_or_raise(experiment_id)
        variant = experiment.assign_variant(user_id, user_tier)

        if variant:
            await self._experiment_repo.record_assignment(
                experiment_id, user_id, variant.variant_id
            )

        return variant

    async def get_variant(
        self,
        experiment_id: str,
        user_id: str,
        user_tier: Optional[str] = None
    ) -> Optional[str]:
        """
        Get user's variant for an experiment.

        Args:
            experiment_id: Experiment ID
            user_id: User ID
            user_tier: User's subscription tier

        Returns:
            Variant ID or None
        """
        variant = await self.assign_experiment(experiment_id, user_id, user_tier)
        return variant.variant_id if variant else None

    async def start_experiment(self, experiment_id: str) -> Experiment:
        """Start an experiment."""
        experiment = await self.get_experiment_or_raise(experiment_id)
        experiment.start()
        return await self._experiment_repo.update(experiment)

    async def pause_experiment(self, experiment_id: str) -> Experiment:
        """Pause an experiment."""
        experiment = await self.get_experiment_or_raise(experiment_id)
        experiment.pause()
        return await self._experiment_repo.update(experiment)

    async def complete_experiment(self, experiment_id: str) -> Experiment:
        """Complete an experiment."""
        experiment = await self.get_experiment_or_raise(experiment_id)
        experiment.complete()
        return await self._experiment_repo.update(experiment)

    async def get_running_experiments(self) -> List[Experiment]:
        """Get all running experiments."""
        return await self._experiment_repo.get_running()

    # ========== Bulk Evaluation Methods ==========

    async def get_user_features(
        self,
        user_id: str,
        user_tier: str = "free"
    ) -> Dict[str, bool]:
        """
        Get all feature flag values for a user.

        Args:
            user_id: User ID
            user_tier: User's subscription tier

        Returns:
            Dictionary of flag_key -> enabled
        """
        flags = await self._flag_repo.get_active()
        return {
            flag.key: flag.evaluate(user_id=user_id, user_tier=user_tier)
            for flag in flags
        }

    async def get_user_experiments(
        self,
        user_id: str,
        user_tier: str = "free"
    ) -> Dict[str, Optional[str]]:
        """
        Get all experiment assignments for a user.

        Args:
            user_id: User ID
            user_tier: User's subscription tier

        Returns:
            Dictionary of experiment_id -> variant_id
        """
        experiments = await self._experiment_repo.get_running()
        result = {}

        for experiment in experiments:
            variant = await self.assign_experiment(
                experiment.experiment_id, user_id, user_tier
            )
            result[experiment.experiment_id] = variant.variant_id if variant else None

        return result
