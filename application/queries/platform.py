"""
Platform Queries - Feature flag and experiment read operations.

@module application.queries.platform
@version 1.0.0
"""

from dataclasses import dataclass
from typing import Optional, Dict

from domains.platform import PlatformService


@dataclass
class EvaluateFeatureFlagQuery:
    """Query to evaluate a feature flag for a user."""
    key: str
    user_id: Optional[str] = None
    user_tier: Optional[str] = None
    default: bool = False


@dataclass
class EvaluateFeatureFlagResult:
    """Result of feature flag evaluation."""
    success: bool
    enabled: bool = False
    flag_key: str = ""
    error: Optional[str] = None


class EvaluateFeatureFlagHandler:
    """Handler for EvaluateFeatureFlagQuery."""

    def __init__(self, platform_service: PlatformService):
        self._platform_service = platform_service

    async def handle(self, query: EvaluateFeatureFlagQuery) -> EvaluateFeatureFlagResult:
        """Execute feature flag evaluation."""
        try:
            enabled = await self._platform_service.evaluate_flag(
                key=query.key,
                user_id=query.user_id,
                user_tier=query.user_tier,
                default=query.default,
            )

            return EvaluateFeatureFlagResult(
                success=True,
                enabled=enabled,
                flag_key=query.key,
            )

        except Exception as e:
            return EvaluateFeatureFlagResult(
                success=False,
                enabled=query.default,
                flag_key=query.key,
                error=str(e),
            )


@dataclass
class GetExperimentVariantQuery:
    """Query to get user's experiment variant."""
    experiment_id: str
    user_id: str
    user_tier: Optional[str] = None


@dataclass
class GetExperimentVariantResult:
    """Result of experiment variant query."""
    success: bool
    variant_id: Optional[str] = None
    experiment_id: str = ""
    error: Optional[str] = None


class GetExperimentVariantHandler:
    """Handler for GetExperimentVariantQuery."""

    def __init__(self, platform_service: PlatformService):
        self._platform_service = platform_service

    async def handle(self, query: GetExperimentVariantQuery) -> GetExperimentVariantResult:
        """Execute experiment variant query."""
        try:
            variant_id = await self._platform_service.get_variant(
                experiment_id=query.experiment_id,
                user_id=query.user_id,
                user_tier=query.user_tier,
            )

            return GetExperimentVariantResult(
                success=True,
                variant_id=variant_id,
                experiment_id=query.experiment_id,
            )

        except Exception as e:
            return GetExperimentVariantResult(
                success=False,
                experiment_id=query.experiment_id,
                error=str(e),
            )


@dataclass
class GetUserFeaturesQuery:
    """Query to get all feature flags for a user."""
    user_id: str
    user_tier: str = "t1"


@dataclass
class GetUserFeaturesResult:
    """Result of user features query."""
    success: bool
    features: Dict[str, bool] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.features is None:
            self.features = {}


class GetUserFeaturesHandler:
    """Handler for GetUserFeaturesQuery."""

    def __init__(self, platform_service: PlatformService):
        self._platform_service = platform_service

    async def handle(self, query: GetUserFeaturesQuery) -> GetUserFeaturesResult:
        """Execute user features query."""
        try:
            features = await self._platform_service.get_user_features(
                user_id=query.user_id,
                user_tier=query.user_tier,
            )

            return GetUserFeaturesResult(
                success=True,
                features=features,
            )

        except Exception as e:
            return GetUserFeaturesResult(
                success=False,
                error=str(e),
            )


@dataclass
class GetUserExperimentsQuery:
    """Query to get all experiment assignments for a user."""
    user_id: str
    user_tier: str = "t1"


@dataclass
class GetUserExperimentsResult:
    """Result of user experiments query."""
    success: bool
    experiments: Dict[str, Optional[str]] = None  # experiment_id -> variant_id
    error: Optional[str] = None

    def __post_init__(self):
        if self.experiments is None:
            self.experiments = {}


class GetUserExperimentsHandler:
    """Handler for GetUserExperimentsQuery."""

    def __init__(self, platform_service: PlatformService):
        self._platform_service = platform_service

    async def handle(self, query: GetUserExperimentsQuery) -> GetUserExperimentsResult:
        """Execute user experiments query."""
        try:
            experiments = await self._platform_service.get_user_experiments(
                user_id=query.user_id,
                user_tier=query.user_tier,
            )

            return GetUserExperimentsResult(
                success=True,
                experiments=experiments,
            )

        except Exception as e:
            return GetUserExperimentsResult(
                success=False,
                error=str(e),
            )
