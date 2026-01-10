"""
Feature Flag Provider Interface

@module core.feature_flag.interface
@version 1.0.0

定义Provider接口,支持多种实现:
- SelfHostedProvider (自建,基于Supabase)
- GrowthBookProvider (集成GrowthBook)
- UnleashProvider (集成Unleash)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from .types import EvaluationContext, EvaluationResult


class IFeatureFlagProvider(ABC):
    """
    Feature Flag Provider 接口

    所有Provider实现必须遵循此接口
    """

    @abstractmethod
    def is_enabled(
        self,
        flag_key: str,
        context: Optional[EvaluationContext] = None,
        default: bool = False
    ) -> bool:
        """
        检查功能是否启用

        Args:
            flag_key: Flag唯一标识
            context: 评估上下文
            default: 默认值 (Flag不存在或评估失败时返回)

        Returns:
            bool: 是否启用
        """
        pass

    @abstractmethod
    def evaluate(
        self,
        flag_key: str,
        context: Optional[EvaluationContext] = None,
        default: Any = False
    ) -> EvaluationResult:
        """
        完整评估 (返回详细结果)

        Args:
            flag_key: Flag唯一标识
            context: 评估上下文
            default: 默认值

        Returns:
            EvaluationResult: 评估结果
        """
        pass

    @abstractmethod
    def get_all_flags(
        self,
        context: Optional[EvaluationContext] = None
    ) -> Dict[str, bool]:
        """
        获取所有Flag状态

        Args:
            context: 评估上下文

        Returns:
            Dict[str, bool]: {flag_key: enabled}
        """
        pass

    @abstractmethod
    def get_all_variants(
        self,
        context: Optional[EvaluationContext] = None
    ) -> Dict[str, str]:
        """
        获取所有Flag的变体

        Args:
            context: 评估上下文

        Returns:
            Dict[str, str]: {flag_key: variant}
        """
        pass

    @abstractmethod
    def track_conversion(
        self,
        flag_key: str,
        context: EvaluationContext,
        metric: str = "conversion",
        value: float = 1.0
    ) -> None:
        """
        追踪转化 (用于A/B测试)

        Args:
            flag_key: Flag唯一标识
            context: 评估上下文
            metric: 指标名称
            value: 指标值
        """
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        健康检查

        Returns:
            Dict: {
                "status": "healthy" | "unhealthy",
                "provider": "self_hosted",
                "flags_count": 10,
                ...
            }
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """
        获取Provider名称

        Returns:
            str: Provider名称
        """
        pass
