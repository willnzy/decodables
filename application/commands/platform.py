"""
Platform Commands - Feature flag and experiment operations.

@module application.commands.platform
@version 1.0.0
"""

from dataclasses import dataclass
from typing import Optional, List

from domains.platform import (
    PlatformService,
    FeatureFlag,
    Experiment,
    TargetType,
)


@dataclass
class CreateFeatureFlagCommand:
    """
    Command to create a new feature flag.
    """
    key: str
    name: str
    description: Optional[str] = None
    default_value: bool = False
    created_by: Optional[str] = None


@dataclass
class CreateFeatureFlagResult:
    """Result of feature flag creation."""
    success: bool
    flag: Optional[FeatureFlag] = None
    error: Optional[str] = None


class CreateFeatureFlagHandler:
    """Handler for CreateFeatureFlagCommand."""

    def __init__(self, platform_service: PlatformService):
        self._platform_service = platform_service

    async def handle(self, command: CreateFeatureFlagCommand) -> CreateFeatureFlagResult:
        """Execute feature flag creation."""
        try:
            flag = await self._platform_service.create_flag(
                key=command.key,
                name=command.name,
                description=command.description,
                default_value=command.default_value,
                created_by=command.created_by,
            )

            return CreateFeatureFlagResult(
                success=True,
                flag=flag,
            )

        except Exception as e:
            return CreateFeatureFlagResult(
                success=False,
                error=str(e),
            )


@dataclass
class ActivateFeatureFlagCommand:
    """Command to activate a feature flag."""
    key: str


@dataclass
class ActivateFeatureFlagResult:
    """Result of activation."""
    success: bool
    flag: Optional[FeatureFlag] = None
    error: Optional[str] = None


class ActivateFeatureFlagHandler:
    """Handler for ActivateFeatureFlagCommand."""

    def __init__(self, platform_service: PlatformService):
        self._platform_service = platform_service

    async def handle(self, command: ActivateFeatureFlagCommand) -> ActivateFeatureFlagResult:
        """Execute feature flag activation."""
        try:
            flag = await self._platform_service.activate_flag(command.key)

            return ActivateFeatureFlagResult(
                success=True,
                flag=flag,
            )

        except Exception as e:
            return ActivateFeatureFlagResult(
                success=False,
                error=str(e),
            )


@dataclass
class AddFlagTargetingCommand:
    """Command to add targeting rule to a flag."""
    key: str
    rule_type: str  # TargetType value
    user_ids: Optional[List[str]] = None
    user_tiers: Optional[List[str]] = None
    percentage: int = 0


@dataclass
class AddFlagTargetingResult:
    """Result of adding targeting."""
    success: bool
    flag: Optional[FeatureFlag] = None
    error: Optional[str] = None


class AddFlagTargetingHandler:
    """Handler for AddFlagTargetingCommand."""

    def __init__(self, platform_service: PlatformService):
        self._platform_service = platform_service

    async def handle(self, command: AddFlagTargetingCommand) -> AddFlagTargetingResult:
        """Execute targeting rule addition."""
        try:
            rule_type = TargetType(command.rule_type)

            flag = await self._platform_service.add_flag_targeting(
                key=command.key,
                rule_type=rule_type,
                user_ids=command.user_ids or [],
                user_tiers=command.user_tiers or [],
                percentage=command.percentage,
            )

            return AddFlagTargetingResult(
                success=True,
                flag=flag,
            )

        except Exception as e:
            return AddFlagTargetingResult(
                success=False,
                error=str(e),
            )


@dataclass
class CreateExperimentCommand:
    """
    Command to create a new A/B experiment.
    """
    name: str
    description: Optional[str] = None
    created_by: Optional[str] = None


@dataclass
class CreateExperimentResult:
    """Result of experiment creation."""
    success: bool
    experiment: Optional[Experiment] = None
    error: Optional[str] = None


class CreateExperimentHandler:
    """Handler for CreateExperimentCommand."""

    def __init__(self, platform_service: PlatformService):
        self._platform_service = platform_service

    async def handle(self, command: CreateExperimentCommand) -> CreateExperimentResult:
        """Execute experiment creation."""
        try:
            experiment = await self._platform_service.create_experiment(
                name=command.name,
                description=command.description,
                created_by=command.created_by,
            )

            return CreateExperimentResult(
                success=True,
                experiment=experiment,
            )

        except Exception as e:
            return CreateExperimentResult(
                success=False,
                error=str(e),
            )


@dataclass
class StartExperimentCommand:
    """Command to start an experiment."""
    experiment_id: str


@dataclass
class StartExperimentResult:
    """Result of starting experiment."""
    success: bool
    experiment: Optional[Experiment] = None
    error: Optional[str] = None


class StartExperimentHandler:
    """Handler for StartExperimentCommand."""

    def __init__(self, platform_service: PlatformService):
        self._platform_service = platform_service

    async def handle(self, command: StartExperimentCommand) -> StartExperimentResult:
        """Execute experiment start."""
        try:
            experiment = await self._platform_service.start_experiment(
                command.experiment_id
            )

            return StartExperimentResult(
                success=True,
                experiment=experiment,
            )

        except Exception as e:
            return StartExperimentResult(
                success=False,
                error=str(e),
            )
