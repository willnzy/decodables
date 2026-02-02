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
    user: Dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    获取用户创建仪表板统计数据

    **关键指标**:
    - `today`: 今日创建用户数
    - `yesterday`: 昨日创建用户数
    - `this_week`: 本周创建用户数
    - `this_month`: 本月创建用户数
    - `change_percent`: 与昨日相比的变化百分比
    - `hourly_breakdown`: 今日每小时创建数

    **使用场景**:
    - 前端 User Monitoring 面板展示
    - 快速了解用户增长情况

    Args:
        user: 当前管理员用户（自动注入）

    Returns:
        仪表板统计数据

    Example Response:
        ```json
        {
            "today": 15,
            "yesterday": 12,
            "this_week": 85,
            "this_month": 320,
            "change_percent": 25.0,
            "hourly_breakdown": [
                {"hour": 0, "count": 2},
                {"hour": 1, "count": 1},
                ...
            ]
        }
        ```
    """
    stats = await UserCreationMonitoringService.get_dashboard_stats()
    return stats


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
                    "Monitor webhook delivery delays"
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


@router.get("/recent")
async def get_recent_users(
    offset: int = Query(0, ge=0, description="偏移量"),
    limit: int = Query(20, ge=1, le=100, description="返回的最大用户数"),
    user: Dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    获取最近注册的用户列表

    **用途**:
    - 查看最近注册的用户
    - 用于前端 User Monitoring 面板显示

    Args:
        offset: 偏移量
        limit: 返回的最大用户数
        user: 当前管理员用户（自动注入）

    Returns:
        用户列表和总数

    Example Response:
        ```json
        {
            "users": [
                {
                    "id": "uuid-123",
                    "user_id": "user_123",
                    "email": "user@example.com",
                    "tier": "t1",
                    "source": "webhook",
                    "created_at": "2026-01-13T10:30:00Z"
                }
            ],
            "total": 100
        }
        ```
    """
    result = await UserCreationMonitoringService.get_recent_users(
        offset=offset,
        limit=limit
    )

    return result


@router.get("/trends")
async def get_user_creation_trends(
    period: str = Query('week', description="统计周期: day, week, month"),
    user: Dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    获取用户创建趋势数据

    **用途**:
    - 展示用户创建趋势图表
    - 按 tier 分类显示创建数量

    Args:
        period: 统计周期 (day, week, month)
        user: 当前管理员用户（自动注入）

    Returns:
        趋势数据

    Example Response:
        ```json
        {
            "trends": [
                {
                    "date": "2026-01-13",
                    "count": 15,
                    "tier_breakdown": {
                        "t1": 10,
                        "t2": 3,
                        "t3": 2
                    }
                }
            ],
            "period": "week"
        }
        ```
    """
    result = await UserCreationMonitoringService.get_creation_trends(period=period)

    return result
