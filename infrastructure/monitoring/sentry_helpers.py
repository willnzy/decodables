"""
Sentry 监控辅助函数

提供统一的 Sentry 事件捕获接口，增强监控和告警能力。

参考业界实践：
- Stripe: 结构化错误上下文
- Datadog: 标准化标签和指标
- Sentry: 最佳实践
"""
import logging
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class SentryLevel(str, Enum):
    """Sentry 严重级别"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


class SentryMonitoring:
    """Sentry 监控辅助类"""
    
    @staticmethod
    def capture_user_creation_event(
        event_type: str,
        user_id: str,
        source: str,
        level: SentryLevel = SentryLevel.INFO,
        extra_context: Optional[Dict[str, Any]] = None
    ):
        """
        捕获用户创建事件
        
        Args:
            event_type: 事件类型 (created, duplicate, fallback, error)
            user_id: 用户 ID
            source: 创建来源 (webhook, jit)
            level: 严重级别
            extra_context: 额外上下文信息
        """
        try:
            import sentry_sdk
            
            context = {
                "user_id": user_id,
                "source": source,
                "event_type": event_type,
                **(extra_context or {})
            }
            
            # 设置标签（用于过滤和聚合）
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("component", "user-creation")
                scope.set_tag("source", source)
                scope.set_tag("event_type", event_type)
                scope.set_context("user_creation", context)
                
                # 根据事件类型设置消息
                messages = {
                    "created": f"User {user_id} created via {source}",
                    "duplicate": f"Duplicate creation attempt for {user_id} via {source}",
                    "fallback": f"JIT Fallback triggered for {user_id}",
                    "error": f"User creation failed for {user_id} via {source}"
                }
                
                message = messages.get(event_type, f"User creation event: {event_type}")
                
                sentry_sdk.capture_message(
                    message,
                    level=level.value
                )
                
        except Exception as e:
            # 不要让 Sentry 错误影响主流程
            logger.warning(f"Failed to send Sentry event: {e}")
    
    
    @staticmethod
    def capture_jit_fallback(
        user_id: str,
        email: str,
        reason: str = "webhook_not_arrived"
    ):
        """
        捕获 JIT Fallback 事件（需要关注的警告）
        
        Args:
            user_id: 用户 ID
            email: 用户邮箱
            reason: 回退原因
        """
        SentryMonitoring.capture_user_creation_event(
            event_type="fallback",
            user_id=user_id,
            source="jit",
            level=SentryLevel.WARNING,
            extra_context={
                "email": email,
                "reason": reason,
                "recommendation": "Check Clerk webhook configuration"
            }
        )
    
    
    @staticmethod
    def capture_webhook_delay(
        user_id: str,
        delay_seconds: float,
        threshold: float = 5.0
    ):
        """
        捕获 Webhook 延迟事件
        
        Args:
            user_id: 用户 ID
            delay_seconds: 延迟秒数
            threshold: 告警阈值（秒）
        """
        if delay_seconds > threshold:
            try:
                import sentry_sdk
                
                with sentry_sdk.push_scope() as scope:
                    scope.set_tag("component", "webhook")
                    scope.set_tag("issue_type", "latency")
                    scope.set_context("webhook_delay", {
                        "user_id": user_id,
                        "delay_seconds": delay_seconds,
                        "threshold": threshold,
                        "severity": "high" if delay_seconds > 10 else "medium"
                    })
                    
                    sentry_sdk.capture_message(
                        f"Webhook delay for {user_id}: {delay_seconds:.2f}s (threshold: {threshold}s)",
                        level="warning"
                    )
            except Exception as e:
                logger.warning(f"Failed to capture webhook delay event: {e}")
    
    
    @staticmethod
    def capture_duplicate_creation(
        user_id: str,
        attempted_source: str,
        existing_source: str
    ):
        """
        捕获重复创建尝试（race condition 监控）
        
        Args:
            user_id: 用户 ID
            attempted_source: 尝试创建的来源
            existing_source: 已存在用户的来源
        """
        SentryMonitoring.capture_user_creation_event(
            event_type="duplicate",
            user_id=user_id,
            source=attempted_source,
            level=SentryLevel.INFO,
            extra_context={
                "existing_source": existing_source,
                "race_condition": "handled_gracefully"
            }
        )
    
    
    @staticmethod
    def capture_creation_error(
        user_id: str,
        source: str,
        error: Exception,
        fallback_attempted: bool = False,
        fallback_success: bool = False
    ):
        """
        捕获用户创建错误（需要立即关注）
        
        Args:
            user_id: 用户 ID
            source: 创建来源
            error: 错误对象
            fallback_attempted: 是否尝试了降级方案
            fallback_success: 降级是否成功
        """
        try:
            import sentry_sdk
            
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("component", "user-creation")
                scope.set_tag("source", source)
                scope.set_tag("error_type", type(error).__name__)
                scope.set_tag("fallback_attempted", str(fallback_attempted))
                scope.set_tag("fallback_success", str(fallback_success))
                
                scope.set_context("user_creation_error", {
                    "user_id": user_id,
                    "source": source,
                    "error_message": str(error),
                    "fallback_attempted": fallback_attempted,
                    "fallback_success": fallback_success,
                    "severity": "critical" if not fallback_success else "high"
                })
                
                # 捕获异常（而不是消息）
                sentry_sdk.capture_exception(error)
                
        except Exception as e:
            logger.warning(f"Failed to capture creation error event: {e}")
    
    
    @staticmethod
    def capture_maintenance_event(
        task_name: str,
        result: Dict[str, Any],
        level: SentryLevel = SentryLevel.INFO
    ):
        """
        捕获维护任务事件
        
        Args:
            task_name: 任务名称 (daily_maintenance, weekly_maintenance)
            result: 执行结果
            level: 严重级别
        """
        try:
            import sentry_sdk
            
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("component", "maintenance")
                scope.set_tag("task_name", task_name)
                scope.set_context("maintenance_result", result)
                
                success = result.get("success", False)
                deleted_count = result.get("total_deleted", 0)
                
                if success:
                    message = f"Maintenance task '{task_name}' completed: {deleted_count} records deleted"
                else:
                    message = f"Maintenance task '{task_name}' failed"
                    level = SentryLevel.ERROR
                
                sentry_sdk.capture_message(message, level=level.value)
                
        except Exception as e:
            logger.warning(f"Failed to capture maintenance event: {e}")
    
    
    @staticmethod
    def capture_log_table_size_warning(
        table_name: str,
        current_rows: int,
        threshold: int,
        table_size: str
    ):
        """
        捕获日志表过大警告
        
        Args:
            table_name: 表名
            current_rows: 当前行数
            threshold: 阈值
            table_size: 表大小（人类可读）
        """
        if current_rows > threshold:
            try:
                import sentry_sdk
                
                with sentry_sdk.push_scope() as scope:
                    scope.set_tag("component", "maintenance")
                    scope.set_tag("issue_type", "log_table_size")
                    scope.set_tag("table_name", table_name)
                    
                    scope.set_context("table_size_warning", {
                        "table_name": table_name,
                        "current_rows": current_rows,
                        "threshold": threshold,
                        "table_size": table_size,
                        "recommendation": "Increase cleanup frequency or reduce retention days"
                    })
                    
                    sentry_sdk.capture_message(
                        f"Log table '{table_name}' is large: {current_rows} rows ({table_size})",
                        level="warning"
                    )
            except Exception as e:
                logger.warning(f"Failed to capture log table size warning: {e}")


# 便捷函数（兼容旧代码）

def capture_jit_fallback(user_id: str, email: str, reason: str = "webhook_not_arrived"):
    """JIT Fallback 事件（便捷函数）"""
    SentryMonitoring.capture_jit_fallback(user_id, email, reason)


def capture_webhook_delay(user_id: str, delay_seconds: float, threshold: float = 5.0):
    """Webhook 延迟事件（便捷函数）"""
    SentryMonitoring.capture_webhook_delay(user_id, delay_seconds, threshold)


def capture_duplicate_creation(user_id: str, attempted_source: str, existing_source: str):
    """重复创建尝试（便捷函数）"""
    SentryMonitoring.capture_duplicate_creation(user_id, attempted_source, existing_source)


def capture_creation_error(
    user_id: str,
    source: str,
    error: Exception,
    fallback_attempted: bool = False,
    fallback_success: bool = False
):
    """用户创建错误（便捷函数）"""
    SentryMonitoring.capture_creation_error(
        user_id, source, error, fallback_attempted, fallback_success
    )
