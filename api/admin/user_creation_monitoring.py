"""
User Creation Monitoring API (Admin)

管理后台监控用户创建健康度的 API 端点

@module api.admin.user_creation_monitoring
@version 1.0.0
"""

from fastapi import APIRouter, Depends, Query
from typing import Dict, Any

from application.services.user_creation_monitoring import UserCreationMonitoringService
from dependencies import require_admin

router = APIRouter(prefix="/monitoring/user-creation", tags=["admin-monitoring"])


@router.get("/stats")
async def get_user_creation_stats(
    days: int = Query(7, ge=1, le=90, description="统计最近 N 天的数据"),
    user: Dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    获取用户创建统计数据
    
    **关键指标**:
    - `webhook_success_rate`: Webhook 成功率（应该 >95%）
    - `jit_fallback_rate`: JIT 回退率（应该 <5%）
    - `duplicate_attempts`: Race condition 处理次数
    
    **使用场景**:
    - 监控 Webhook 健康度
    - 追踪 JIT fallback 趋势
    - 分析系统稳定性
    
    Args:
        days: 统计周期（天数）
        user: 当前管理员用户（自动注入）
    
    Returns:
        统计数据字典
    
    Example Response:
        ```json
        {
            "period_days": 7,
            "total_users": 150,
            "webhook_created": 145,
            "jit_created": 5,
            "webhook_success_rate": 96.67,
            "jit_fallback_rate": 3.33,
            "duplicate_attempts": 2,
            "errors": 0,
            "timestamp": "2026-01-13T10:30:00Z"
        }
        ```
    """
    stats = await UserCreationMonitoringService.get_creation_stats(days=days)
    return {
        "success": True,
        "data": stats
    }


@router.get("/health")
async def get_user_creation_health(
    days: int = Query(7, ge=1, le=90, description="统计周期"),
    user: Dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    获取用户创建系统的健康状态
    
    **健康状态**:
    - `healthy`: 所有指标正常
    - `degraded`: 部分指标低于预期
    - `unhealthy`: 关键指标异常
    
    **告警级别**:
    - `critical`: 需要立即处理
    - `warning`: 需要关注
    
    Args:
        days: 统计周期（天数）
        user: 当前管理员用户（自动注入）
    
    Returns:
        健康状态字典
    
    Example Response:
        ```json
        {
            "success": true,
            "data": {
                "status": "degraded",
                "stats": {...},
                "alerts": [
                    {
                        "severity": "warning",
                        "metric": "webhook_success_rate",
                        "value": 93.5,
                        "threshold": 95,
                        "message": "Webhook success rate is below target: 93.5%"
                    }
                ],
                "recommendations": [
                    "Monitor Clerk webhook delivery delays"
                ],
                "evaluated_at": "2026-01-13T10:30:00Z"
            }
        }
        ```
    """
    stats = await UserCreationMonitoringService.get_creation_stats(days=days)
    health = await UserCreationMonitoringService.get_health_status(stats=stats)
    
    return {
        "success": True,
        "data": health
    }


@router.get("/events")
async def get_recent_creation_events(
    limit: int = Query(50, ge=1, le=100, description="返回的最大事件数"),
    user: Dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    获取最近的用户创建事件
    
    **用途**:
    - 查看最近的用户创建情况
    - 分析 Webhook vs JIT 创建分布
    - 调试 race condition 问题
    
    Args:
        limit: 返回的最大事件数
        user: 当前管理员用户（自动注入）
    
    Returns:
        事件列表
    
    Example Response:
        ```json
        {
            "success": true,
            "data": [
                {
                    "user_id": "user_123",
                    "email": "user@example.com",
                    "created_by_source": "webhook",
                    "user_created_at": "2026-01-13T10:30:00Z",
                    "log_action": "created",
                    "delay_seconds": 0.5
                },
                {
                    "user_id": "user_124",
                    "email": "another@example.com",
                    "created_by_source": "jit",
                    "user_created_at": "2026-01-13T10:31:00Z",
                    "log_action": "created",
                    "delay_seconds": null
                }
            ],
            "count": 2
        }
        ```
    """
    events = await UserCreationMonitoringService.get_recent_events(limit=limit)
    
    return {
        "success": True,
        "data": events,
        "count": len(events)
    }
