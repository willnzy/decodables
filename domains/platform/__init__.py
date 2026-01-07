"""
Platform Domain - Feature flags, experiments, and system configuration.

This domain handles:
- Feature flag management
- A/B experiments
- System configuration
- Theme/Daily Doodle management

@package domains.platform
@version 1.0.0

Note: This domain manages platform-wide configuration and features.
"""

from .value_objects import (
    FeatureFlagId,
    FlagStatus,
    ExperimentId,
    ExperimentStatus,
    TargetingRule,
    ThemeConfig,
)
from .aggregates.feature_flag import FeatureFlag
from .aggregates.experiment import Experiment
from .exceptions import (
    FeatureFlagNotFoundException,
    ExperimentNotFoundException,
    InvalidConfigurationException,
)
from .repository import IFeatureFlagRepository, IExperimentRepository
from .service import PlatformService

__all__ = [
    # Value Objects
    'FeatureFlagId',
    'FlagStatus',
    'ExperimentId',
    'ExperimentStatus',
    'TargetingRule',
    'ThemeConfig',
    # Aggregates
    'FeatureFlag',
    'Experiment',
    # Exceptions
    'FeatureFlagNotFoundException',
    'ExperimentNotFoundException',
    'InvalidConfigurationException',
    # Repository
    'IFeatureFlagRepository',
    'IExperimentRepository',
    # Service
    'PlatformService',
]
