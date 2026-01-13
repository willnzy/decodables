"""
User Creation Monitoring Service

监控用户创建的健康度和统计数据
用于追踪 Webhook 成功率、JIT fallback 率等关键指标

@module application.services.user_creation_monitoring
@version 1.0.0
"""

from typing import Dict, Any, List
from datetime import datetime
import logging

from core.database import get_async_db_client

logger = logging.getLogger(__name__)


class UserCreationMonitoringService:
    """
    用户创建监控服务
    
    提供以下监控能力：
    1. Webhook 成功率
    2. JIT Fallback 率
    3. Race Condition 处理统计
    4. 健康度告警
    """
    
    @staticmethod
    async def get_creation_stats(days: int = 7) -> Dict[str, Any]:
        """
        获取用户创建统计数据
        
        关键指标：
        - Webhook Success Rate: 应该 >95%
        - JIT Fallback Rate: 应该 <5%
        - Duplicate Attempts: 记录 race condition 次数
        
        Args:
            days: 统计最近 N 天的数据
        
        Returns:
            统计数据字典，包含：
            {
                "total_users": 总用户数,
                "webhook_created": Webhook 创建数,
                "jit_created": JIT 创建数,
                "webhook_success_rate": Webhook 成功率%,
                "jit_fallback_rate": JIT 回退率%,
                "duplicate_attempts": 重复尝试次数,
                "errors": 错误次数
            }
        """
        try:
            db_client = await get_async_db_client()
            
            # 调用数据库 RPC 函数
            result = await db_client.rpc('get_user_creation_stats', {
                'p_days': days
            }).execute()
            
            if not result.data or len(result.data) == 0:
                logger.warning(f"No user creation stats found for last {days} days")
                return UserCreationMonitoringService._get_empty_stats()
            
            stats = result.data[0]
            
            return {
                "period_days": days,
                "total_users": stats.get('total_users', 0),
                "webhook_created": stats.get('webhook_created', 0),
                "jit_created": stats.get('jit_created', 0),
                "webhook_success_rate": float(stats.get('webhook_success_rate', 0)),
                "jit_fallback_rate": float(stats.get('jit_fallback_rate', 0)),
                "duplicate_attempts": stats.get('duplicate_attempts', 0),
                "errors": stats.get('errors', 0),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get user creation stats: {e}", exc_info=True)
            raise
    
    @staticmethod
    async def get_health_status(stats: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        评估用户创建系统的健康状态
        
        Args:
            stats: 统计数据（如果为 None 则自动获取）
        
        Returns:
            健康状态字典：
            {
                "status": "healthy" | "degraded" | "unhealthy",
                "alerts": [...],
                "recommendations": [...]
            }
        """
        if stats is None:
            stats = await UserCreationMonitoringService.get_creation_stats()
        
        alerts = []
        recommendations = []
        
        # 检查 Webhook 成功率
        webhook_rate = stats['webhook_success_rate']
        if webhook_rate < 90:
            alerts.append({
                "severity": "critical",
                "metric": "webhook_success_rate",
                "value": webhook_rate,
                "threshold": 90,
                "message": f"Webhook success rate is critically low: {webhook_rate}%"
            })
            recommendations.append(
                "Check Clerk webhook configuration and network connectivity"
            )
        elif webhook_rate < 95:
            alerts.append({
                "severity": "warning",
                "metric": "webhook_success_rate",
                "value": webhook_rate,
                "threshold": 95,
                "message": f"Webhook success rate is below target: {webhook_rate}%"
            })
            recommendations.append(
                "Monitor Clerk webhook delivery delays"
            )
        
        # 检查 JIT Fallback 率
        jit_rate = stats['jit_fallback_rate']
        if jit_rate > 10:
            alerts.append({
                "severity": "critical",
                "metric": "jit_fallback_rate",
                "value": jit_rate,
                "threshold": 10,
                "message": f"JIT fallback rate is too high: {jit_rate}%"
            })
            recommendations.append(
                "Investigate webhook delivery issues urgently"
            )
        elif jit_rate > 5:
            alerts.append({
                "severity": "warning",
                "metric": "jit_fallback_rate",
                "value": jit_rate,
                "threshold": 5,
                "message": f"JIT fallback rate is elevated: {jit_rate}%"
            })
            recommendations.append(
                "Review webhook logs for delays or failures"
            )
        
        # 检查错误数
        errors = stats['errors']
        if errors > 0:
            alerts.append({
                "severity": "warning",
                "metric": "errors",
                "value": errors,
                "threshold": 0,
                "message": f"Detected {errors} user creation errors"
            })
            recommendations.append(
                "Check user_creation_logs table for error details"
            )
        
        # 确定整体健康状态
        if any(a['severity'] == 'critical' for a in alerts):
            status = "unhealthy"
        elif len(alerts) > 0:
            status = "degraded"
        else:
            status = "healthy"
        
        return {
            "status": status,
            "stats": stats,
            "alerts": alerts,
            "recommendations": recommendations,
            "evaluated_at": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    async def get_recent_events(limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取最近的用户创建事件
        
        Args:
            limit: 返回的最大事件数
        
        Returns:
            事件列表
        """
        try:
            db_client = await get_async_db_client()
            
            # 查询视图
            result = await db_client.table('v_user_creation_events')\
                .select('*')\
                .order('user_created_at', desc=True)\
                .limit(limit)\
                .execute()
            
            if not result.data:
                return []
            
            return result.data
            
        except Exception as e:
            logger.error(f"Failed to get recent events: {e}", exc_info=True)
            return []
    
    @staticmethod
    def _get_empty_stats() -> Dict[str, Any]:
        """返回空统计数据"""
        return {
            "period_days": 7,
            "total_users": 0,
            "webhook_created": 0,
            "jit_created": 0,
            "webhook_success_rate": 0.0,
            "jit_fallback_rate": 0.0,
            "duplicate_attempts": 0,
            "errors": 0,
            "timestamp": datetime.utcnow().isoformat()
        }
