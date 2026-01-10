"""
Feature Flag Service Facade

@module core.feature_flag.service
@version 1.0.0

统一的Feature Flag服务,提供简洁的API

Example:
    from core.feature_flag import feature_service, EvaluationContext

    # 简单检查
    if feature_service.is_enabled("new_editor", context):
        return new_editor_response()

    # 获取变体
    variant = feature_service.get_variant("checkout_experiment", context)
    if variant == "variant_a":
        return new_checkout()

    # 追踪转化
    feature_service.track_conversion("checkout_experiment", context, "purchase", 99.99)
"""

import logging
from typing import Dict, Optional, Any

from .types import EvaluationContext, EvaluationResult
from .interface import IFeatureFlagProvider

logger = logging.getLogger(__name__)


class FeatureFlagService:
    """
    Feature Flag 服务 Facade

    提供统一的API,底层可切换不同Provider
    """

    _instance: Optional['FeatureFlagService'] = None
    _provider: Optional[IFeatureFlagProvider] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Provider由外部注入 (应用启动时配置)
        pass

    @classmethod
    def set_provider(cls, provider: IFeatureFlagProvider):
        """
        设置Provider (应用启动时调用)

        Args:
            provider: Provider实例
        """
        cls._provider = provider
        logger.info(f"Feature Flag Provider set to: {provider.get_provider_name()}")

    def _get_provider(self) -> IFeatureFlagProvider:
        """获取Provider实例"""
        if self._provider is None:
            raise RuntimeError(
                "Feature Flag Provider not configured. "
                "Call FeatureFlagService.set_provider() first."
            )
        return self._provider

    # ==================== 主要 API ====================

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
            default: 默认值

        Returns:
            bool: 是否启用

        Example:
            if feature_service.is_enabled("new_editor", context):
                return new_editor_response()
        """
        try:
            return self._get_provider().is_enabled(flag_key, context, default)
        except Exception as e:
            logger.error(f"Failed to evaluate flag {flag_key}: {e}")
            return default

    def get_variant(
        self,
        flag_key: str,
        context: Optional[EvaluationContext] = None,
        default: str = "control"
    ) -> str:
        """
        获取变体Key

        Args:
            flag_key: Flag唯一标识
            context: 评估上下文
            default: 默认变体

        Returns:
            str: 变体key

        Example:
            variant = feature_service.get_variant("checkout_experiment", context)
            if variant == "variant_a":
                return new_checkout()
        """
        try:
            result = self._get_provider().evaluate(flag_key, context, default)
            return result.variant
        except Exception as e:
            logger.error(f"Failed to get variant for {flag_key}: {e}")
            return default

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

        Example:
            result = feature_service.evaluate("experiment_1", context)
            print(result.enabled, result.variant, result.reason)
        """
        try:
            return self._get_provider().evaluate(flag_key, context, default)
        except Exception as e:
            logger.error(f"Failed to evaluate {flag_key}: {e}")
            from .types import EvaluationReason
            return EvaluationResult(
                enabled=False,
                value=default,
                reason=EvaluationReason.ERROR,
                flag_key=flag_key,
            )

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
        try:
            return self._get_provider().get_all_flags(context)
        except Exception as e:
            logger.error(f"Failed to get all flags: {e}")
            return {}

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
        try:
            return self._get_provider().get_all_variants(context)
        except Exception as e:
            logger.error(f"Failed to get all variants: {e}")
            return {}

    # ==================== 实验追踪 ====================

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

        Example:
            # 用户完成购买
            feature_service.track_conversion(
                "checkout_experiment",
                context,
                metric="purchase",
                value=99.99
            )
        """
        try:
            self._get_provider().track_conversion(flag_key, context, metric, value)
        except Exception as e:
            logger.error(f"Failed to track conversion for {flag_key}: {e}")

    # ==================== 工具方法 ====================

    def health_check(self) -> Dict[str, Any]:
        """
        健康检查

        Returns:
            Dict: 健康状态
        """
        try:
            return self._get_provider().health_check()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    def get_provider_name(self) -> str:
        """
        获取当前Provider名称

        Returns:
            str: Provider名称
        """
        try:
            return self._get_provider().get_provider_name()
        except:
            return "unknown"


# 全局单例
feature_service = FeatureFlagService()
