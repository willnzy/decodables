"""
Core Feature Flag Module

@module core.feature_flag
@version 1.0.0

统一的Feature Flag系统,支持:
- Boolean flags (功能开关)
- Multivariate flags (多变体)
- A/B experiments (实验)

Architecture:
- Evaluation Engine: 统一评估引擎
- Provider Interface: 可插拔实现
- Factory Pattern: 支持多种Provider
"""

from .types import (
    FlagType,
    EvaluationReason,
    Variant,
    EvaluationContext,
    EvaluationResult,
)
from .service import FeatureFlagService, feature_service
from .evaluator import UnifiedEvaluator
from .hasher import get_hash_bucket
from .providers import SelfHostedProvider

__all__ = [
    # Types
    "FlagType",
    "EvaluationReason",
    "Variant",
    "EvaluationContext",
    "EvaluationResult",
    # Service
    "FeatureFlagService",
    "feature_service",
    # Evaluator
    "UnifiedEvaluator",
    # Utils
    "get_hash_bucket",
    # Providers
    "SelfHostedProvider",
]
