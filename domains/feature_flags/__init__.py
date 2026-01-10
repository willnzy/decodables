"""
Feature Flags Domain

@module domains.feature_flags
@version 1.0.0

DDD层次结构:
- Entity: 领域实体 (FeatureFlagEntity)
- Repository: 数据访问接口 + 实现
- Service: 领域服务 (业务逻辑)
"""

from .entity import FeatureFlagEntity
from .repository import FeatureFlagRepository
from .service import FeatureFlagService

__all__ = [
    "FeatureFlagEntity",
    "FeatureFlagRepository",
    "FeatureFlagService",
]
