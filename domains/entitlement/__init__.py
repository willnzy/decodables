"""
Entitlement Domain — Phase 3 新增

@module domains.entitlement
@version 1.0.0

DDD 层次结构:
- PriorityEvaluator: 7 层优先级评估引擎 (SVC-004 + BR-002)
- PermissionService: 统一权限入口 (SVC-001)
- Repository: Override 数据访问接口
"""

from .priority_evaluator import PriorityEvaluator
from .permission_service import PermissionService
from .repository import IOverrideRepository, ITierConfigRepository, ITrialRepository
from .trial_service import TrialService

__all__ = [
    "PriorityEvaluator",
    "PermissionService",
    "IOverrideRepository",
    "ITierConfigRepository",
    "ITrialRepository",
    "TrialService",
]
