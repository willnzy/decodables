"""
Feature Flag Type Definitions

@module core.feature_flag.types
@version 1.0.0
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum


# ==========================================
# Enums
# ==========================================

class FlagType(str, Enum):
    """Flag类型枚举"""
    BOOLEAN = "boolean"  # 简单开关
    MULTIVARIATE = "multivariate"  # 多变体
    EXPERIMENT = "experiment"  # A/B实验


class EvaluationReason(str, Enum):
    """评估原因枚举"""
    DISABLED = "disabled"  # Flag 未启用
    TIME_WINDOW = "time_window"  # 不在时间窗口内
    ENVIRONMENT = "environment"  # 环境不匹配
    TIER_MISMATCH = "tier_mismatch"  # v1.2: Tier 不匹配
    BLACKLIST = "blacklist"  # 在黑名单中
    WHITELIST = "whitelist"  # 在白名单中
    RULE = "rule"  # 命中定向规则
    PERCENTAGE = "percentage"  # 百分比灰度
    DEFAULT = "default"  # 默认值
    ERROR = "error"  # 评估错误
    NOT_FOUND = "not_found"  # Flag 不存在


# ==========================================
# Data Classes
# ==========================================

@dataclass
class Variant:
    """
    变体定义

    Attributes:
        key: 变体唯一标识 (如 "control", "treatment", "variant_a")
        value: 变体值 (Boolean, String, Number, JSON等)
        weight: 权重 (用于随机分配,总和为100)
    """
    key: str
    value: Any
    weight: int = 50

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "weight": self.weight,
        }


@dataclass
class EvaluationContext:
    """
    评估上下文

    包含用户/环境信息,用于Flag评估

    Attributes:
        user_id: 用户ID (登录用户)
        anonymous_id: 匿名ID (未登录用户)
        email: 邮箱
        tier: 用户层级 (t1/t2/t3)
        role: 用户角色 (admin/user)
        country: 国家代码
        device: 设备类型 (desktop/mobile/tablet)
        platform: 平台 (web/ios/android)
        app_version: 应用版本
        environment: 环境 (production/staging/development)
        custom: 自定义属性
    """
    user_id: Optional[str] = None
    anonymous_id: Optional[str] = None
    email: Optional[str] = None
    tier: Optional[str] = None
    role: Optional[str] = None
    country: Optional[str] = None
    device: Optional[str] = None
    platform: Optional[str] = None
    app_version: Optional[str] = None
    environment: str = "production"
    custom: Dict[str, Any] = field(default_factory=dict)

    @property
    def identifier(self) -> str:
        """获取用户唯一标识 (用于哈希分配)"""
        return self.user_id or self.anonymous_id or "anonymous"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "user_id": self.user_id,
            "anonymous_id": self.anonymous_id,
            "email": self.email,
            "tier": self.tier,
            "role": self.role,
            "country": self.country,
            "device": self.device,
            "platform": self.platform,
            "app_version": self.app_version,
            "environment": self.environment,
        }
        result.update(self.custom)
        return {k: v for k, v in result.items() if v is not None}

    def get(self, key: str, default: Any = None) -> Any:
        """获取属性值"""
        if hasattr(self, key) and getattr(self, key) is not None:
            return getattr(self, key)
        return self.custom.get(key, default)


@dataclass
class EvaluationResult:
    """
    评估结果

    Attributes:
        enabled: 是否启用
        variant: 变体key
        value: 变体值
        reason: 评估原因
        rule_id: 命中的规则ID (如果通过规则分配)
        flag_key: Flag key
        flag_type: Flag类型
    """
    enabled: bool
    variant: str = "control"
    value: Any = None
    reason: EvaluationReason = EvaluationReason.DEFAULT
    rule_id: Optional[str] = None
    flag_key: Optional[str] = None
    flag_type: Optional[FlagType] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "enabled": self.enabled,
            "variant": self.variant,
            "value": self.value,
            "reason": self.reason.value,
            "rule_id": self.rule_id,
            "flag_key": self.flag_key,
            "flag_type": self.flag_type.value if self.flag_type else None,
        }
