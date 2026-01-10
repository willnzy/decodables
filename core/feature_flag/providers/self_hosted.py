"""
Self-Hosted Feature Flag Provider

@module core.feature_flag.providers.self_hosted
@version 1.0.0

基于Supabase的自建Feature Flag实现

Features:
- 从Supabase读取Flag配置
- 使用UnifiedEvaluator进行评估
- 曝光追踪
- Redis缓存 (60s TTL)
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from ..types import EvaluationContext, EvaluationResult, EvaluationReason, FlagType
from ..interface import IFeatureFlagProvider
from ..evaluator import UnifiedEvaluator

logger = logging.getLogger(__name__)


class SelfHostedProvider(IFeatureFlagProvider):
    """
    自建Feature Flag Provider

    基于Supabase存储,使用统一评估引擎
    """

    def __init__(self, supabase_client, redis_client=None):
        """
        初始化Provider

        Args:
            supabase_client: Supabase客户端
            redis_client: Redis客户端 (可选,用于缓存)
        """
        self.client = supabase_client
        self.redis = redis_client
        self.evaluator = UnifiedEvaluator()
        self._cache_ttl = 60  # 缓存60秒

    # ==================== 核心方法 ====================

    def is_enabled(
        self,
        flag_key: str,
        context: Optional[EvaluationContext] = None,
        default: bool = False
    ) -> bool:
        """检查功能是否启用"""
        result = self.evaluate(flag_key, context, default)
        return result.enabled

    def evaluate(
        self,
        flag_key: str,
        context: Optional[EvaluationContext] = None,
        default: Any = False
    ) -> EvaluationResult:
        """完整评估"""
        if context is None:
            context = EvaluationContext()

        try:
            # 1. 获取Flag配置 (带缓存)
            flag = self._get_flag_config(flag_key)
            if not flag:
                return EvaluationResult(
                    enabled=False,
                    value=default,
                    reason=EvaluationReason.NOT_FOUND,
                    flag_key=flag_key,
                )

            # 2. 评估
            result = self.evaluator.evaluate(flag, context)

            # 3. 追踪曝光 (异步,不阻塞)
            self._track_exposure(flag_key, context, result)

            return result

        except Exception as e:
            logger.error(f"Failed to evaluate flag {flag_key}: {e}", exc_info=True)
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
        """获取所有Flag状态"""
        if context is None:
            context = EvaluationContext()

        flags_config = self._get_all_flags_config()
        result = {}

        for flag in flags_config:
            eval_result = self.evaluator.evaluate(flag, context)
            result[flag["key"]] = eval_result.enabled

        return result

    def get_all_variants(
        self,
        context: Optional[EvaluationContext] = None
    ) -> Dict[str, str]:
        """获取所有Flag的变体"""
        if context is None:
            context = EvaluationContext()

        flags_config = self._get_all_flags_config()
        result = {}

        for flag in flags_config:
            eval_result = self.evaluator.evaluate(flag, context)
            result[flag["key"]] = eval_result.variant

        return result

    def track_conversion(
        self,
        flag_key: str,
        context: EvaluationContext,
        metric: str = "conversion",
        value: float = 1.0
    ) -> None:
        """追踪转化"""
        try:
            self.client.table("experiment_conversions").insert({
                "flag_key": flag_key,
                "user_id": context.user_id,
                "anonymous_id": context.anonymous_id,
                "metric": metric,
                "value": value,
                "context": context.to_dict(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }).execute()
            logger.debug(f"Tracked conversion: {flag_key}, {metric}={value}")
        except Exception as e:
            logger.error(f"Failed to track conversion: {e}")

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 测试数据库连接
            result = self.client.table("feature_flags").select("count", count="exact").limit(0).execute()
            flags_count = result.count or 0

            return {
                "status": "healthy",
                "provider": "self_hosted",
                "flags_count": flags_count,
                "cache_enabled": self.redis is not None,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": "self_hosted",
                "error": str(e),
            }

    def get_provider_name(self) -> str:
        """获取Provider名称"""
        return "self_hosted"

    # ==================== 数据访问 ====================

    def _get_flag_config(self, flag_key: str) -> Optional[Dict[str, Any]]:
        """
        获取Flag配置 (带缓存)

        Returns:
            Dict: Flag配置,或None (不存在)
        """
        # 尝试从缓存读取
        if self.redis:
            cache_key = f"feature_flag:{flag_key}"
            try:
                import json
                cached = self.redis.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Redis cache read failed: {e}")

        # 从数据库读取
        try:
            result = self.client.table("feature_flags") \
                .select("*") \
                .eq("key", flag_key) \
                .eq("archived", False) \
                .execute()

            if not result.data:
                return None

            flag = result.data[0]

            # 写入缓存
            if self.redis:
                try:
                    import json
                    self.redis.setex(
                        cache_key,
                        self._cache_ttl,
                        json.dumps(flag)
                    )
                except Exception as e:
                    logger.warning(f"Redis cache write failed: {e}")

            return flag

        except Exception as e:
            logger.error(f"Failed to get flag config: {e}")
            return None

    def _get_all_flags_config(self) -> list:
        """获取所有Flag配置"""
        try:
            result = self.client.table("feature_flags") \
                .select("*") \
                .eq("archived", False) \
                .execute()

            return result.data or []

        except Exception as e:
            logger.error(f"Failed to get all flags config: {e}")
            return []

    def _track_exposure(
        self,
        flag_key: str,
        context: EvaluationContext,
        result: EvaluationResult
    ) -> None:
        """
        追踪Flag曝光

        异步写入,不阻塞主流程
        """
        try:
            self.client.table("flag_exposures").insert({
                "flag_key": flag_key,
                "flag_type": result.flag_type.value if result.flag_type else "boolean",
                "user_id": context.user_id,
                "anonymous_id": context.anonymous_id,
                "variant": result.variant,
                "enabled": result.enabled,
                "reason": result.reason.value,
                "rule_id": result.rule_id,
                "context": context.to_dict(),
                "environment": context.environment,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }).execute()
        except Exception as e:
            # 曝光追踪失败不应影响主流程
            logger.warning(f"Failed to track exposure: {e}")

    def invalidate_cache(self, flag_key: str = None):
        """清除缓存"""
        if not self.redis:
            return

        try:
            if flag_key:
                cache_key = f"feature_flag:{flag_key}"
                self.redis.delete(cache_key)
                logger.info(f"Invalidated cache for {flag_key}")
            else:
                # 清除所有缓存
                pattern = "feature_flag:*"
                keys = self.redis.keys(pattern)
                if keys:
                    self.redis.delete(*keys)
                    logger.info(f"Invalidated {len(keys)} flag caches")
        except Exception as e:
            logger.error(f"Failed to invalidate cache: {e}")
