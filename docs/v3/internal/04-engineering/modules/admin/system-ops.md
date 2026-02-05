# 系统运维能力设计

> **同步范围**: [backend]
> **状态**: 🟢 已验证 (来源: 代码分析 + v2 文档)
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `api/admin/system.py`, `api/admin/logs.py`, `api/admin/tasks_mgmt.py`

---

## 一、概述

### 1.1 核心能力

| 模块 | 说明 |
|------|------|
| System Configs | 系统配置管理 |
| Cache | 缓存状态与管理 |
| Logs | 日志查询与导出 |
| Tasks | 任务状态与触发 |
| Webhooks | Webhook 重试 |
| Monitoring | 系统监控 |

---

## 二、System Configs

### 2.1 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v2/admin/system/configs` | GET | 配置列表 |
| `/api/v2/admin/system/configs/groups` | GET | 配置分组 |
| `/api/v2/admin/system/configs` | POST | 创建配置 |
| `/api/v2/admin/system/configs/{key}` | PUT | 更新配置 |
| `/api/v2/admin/system/configs/{key}` | DELETE | 删除配置 |
| `/api/v2/admin/system/configs/audit` | GET | 审计日志 |
| `/api/v2/admin/system/configs/cache/invalidate` | POST | 失效缓存 |

### 2.2 配置分组

```python
class ConfigGroup(str, Enum):
    TIER_PRICING = "tier_pricing"
    CREDITS = "credits"
    FEATURES = "features"
    LIMITS = "limits"
    AI = "ai"
    NOTIFICATIONS = "notifications"
    MAINTENANCE = "maintenance"
```

### 2.3 数据结构

```python
class SystemConfig:
    key: str
    value: Any
    value_type: str          # text/json/number/boolean
    config_group: str
    description: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

class ConfigHistory:
    config_key: str
    old_value: Any
    new_value: Any
    changed_by: UUID
    changed_at: datetime
```

---

## 三、Cache 管理

### 3.1 API 端点

| 端点 | 方法 | 风险 | 说明 |
|------|------|:----:|------|
| `/api/v2/admin/system/cache/status` | GET | - | 缓存状态 |
| `/api/v2/admin/system/cache/keys` | GET | - | 缓存键列表 |
| `/api/v2/admin/system/cache/key/{key}` | DELETE | 🟡 | 删除指定键 |
| `/api/v2/admin/system/cache/clear-all/confirm` | POST | 🔴 | 确认清空 |
| `/api/v2/admin/system/cache/clear-all` | POST | 🔴 | 清空所有 |

### 3.2 缓存状态

```python
class CacheStats:
    total_keys: int
    memory_used_mb: float
    hit_rate: float
    miss_rate: float
    
    by_type: Dict[str, int]  # 按类型统计
    # {
    #   "config": 50,
    #   "user": 1200,
    #   "session": 300
    # }
```

### 3.3 安全清空流程

```python
async def clear_all_cache(admin_id: UUID, confirmation_token: str):
    """
    清空所有缓存 (两步确认)
    
    1. 先调用 /confirm 获取确认 token
    2. 5 分钟内使用 token 调用 /clear-all
    """
    # 验证 token
    if not verify_confirmation_token(confirmation_token):
        raise InvalidTokenError()
    
    # 清空缓存
    await redis.flushall()
    
    # 审计日志
    await audit_log.create(
        action="cache_cleared_all",
        operator_id=admin_id,
        details={"keys_deleted": "all"}
    )
```

---

## 四、Logs 管理

### 4.1 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v2/admin/logs/errors` | GET | 错误日志 |
| `/api/v2/admin/logs/errors/stats` | GET | 错误统计 |
| `/api/v2/admin/logs/operations` | GET | 操作日志 |
| `/api/v2/admin/logs/operations/export` | GET | 导出日志 |
| `/api/v2/admin/logs/audit` | GET | 审计日志 |

### 4.2 错误日志

```python
class ErrorLog:
    id: UUID
    level: str               # error/warning/critical
    message: str
    stack_trace: str
    
    # 上下文
    user_id: Optional[UUID]
    request_path: str
    request_method: str
    
    # 时间
    occurred_at: datetime
    
    # 分组
    error_type: str          # 用于聚合
    fingerprint: str         # 去重标识

class ErrorStats:
    total: int
    by_level: Dict[str, int]
    by_type: Dict[str, int]
    top_errors: List[ErrorSummary]
```

### 4.3 操作日志

```python
class OperationLog:
    id: UUID
    action: str
    target_type: str
    target_id: Optional[str]
    operator_id: UUID
    
    # 详情
    details: dict
    ip_address: str
    user_agent: str
    
    timestamp: datetime
```

### 4.4 查询参数

```python
class LogQueryParams:
    level: Optional[str]         # error/warning/critical
    start_date: Optional[date]
    end_date: Optional[date]
    user_id: Optional[UUID]
    error_type: Optional[str]
    offset: int = 0
    limit: int = 50
```

---

## 五、Tasks 管理

### 5.1 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/admin/tasks/management/status` | GET | 任务状态 |
| `/api/admin/tasks/management/logs` | GET | 任务日志 |
| `/api/admin/tasks/management/health` | GET | 健康检查 |
| `/api/admin/tasks/management/{task_name}/run` | POST | 手动触发 |

### 5.2 任务类型

```python
TASK_WHITELIST = [
    "hourly",      # 小时任务
    "daily",       # 日任务
    "all",         # 所有任务
    "cleanup",     # 清理任务
    "retention",   # 留存计算
    "aggregation", # 数据聚合
]
```

### 5.3 任务状态

```python
class TaskStatus:
    name: str
    status: str              # idle/running/failed
    last_run: Optional[datetime]
    last_success: Optional[datetime]
    last_error: Optional[str]
    next_scheduled: Optional[datetime]
    run_count: int
    error_count: int

class TaskHealth:
    overall: str             # healthy/degraded/unhealthy
    tasks: Dict[str, TaskStatus]
    alerts: List[str]
```

---

## 六、Webhooks 管理

### 6.1 API 端点

| 端点 | 方法 | Rate Limit | 说明 |
|------|------|------------|------|
| `/api/v2/admin/webhooks/failed` | GET | 30/min | 失败列表 |
| `/api/v2/admin/webhooks/retry` | POST | 10/hour | 重试 |

### 6.2 Webhook 来源

```python
class WebhookSource(str, Enum):
    STRIPE = "stripe"
    CLERK = "clerk"
    FAL = "fal"
    OTHER = "other"
```

### 6.3 Webhook 状态

```python
class WebhookStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
```

### 6.4 失败记录

```python
class FailedWebhook:
    id: UUID
    source: WebhookSource
    event_type: str
    payload: dict
    
    error_message: str
    retry_count: int
    max_retries: int
    next_retry_at: Optional[datetime]
    
    created_at: datetime
    last_attempt_at: datetime
```

---

## 七、Monitoring

### 7.1 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/admin/monitoring/user-creation/stats` | GET | 用户创建统计 |
| `/api/admin/monitoring/user-creation/health` | GET | 健康状态 |
| `/api/admin/monitoring/user-creation/events` | GET | 创建事件 |
| `/api/admin/monitoring/user-creation/recent` | GET | 最近创建 |
| `/api/admin/monitoring/user-creation/trends` | GET | 趋势分析 |

### 7.2 用户创建统计

```python
class UserCreationStats:
    today: int
    yesterday: int
    this_week: int
    last_week: int
    
    change_percent: float  # 环比变化
    
    hourly_breakdown: List[HourlyCount]
    by_source: Dict[str, int]  # signup/oauth/invite
```

### 7.3 健康检查

```python
class UserCreationHealth:
    status: str            # healthy/warning/critical
    
    # 指标
    avg_time_to_create_ms: float
    failure_rate: float
    
    # 告警
    alerts: List[str]
```

---

## 八、安全与护栏

### 8.1 高危操作

| 操作 | 风险 | 保护措施 |
|------|:----:|----------|
| 清空缓存 | 🔴 | 两步确认 |
| Webhook 重试 | 🟠 | 10/hour 限制 |
| 删除配置 | 🟠 | 审计日志 |
| 手动触发任务 | 🟡 | 白名单校验 |

### 8.2 审计要求

所有变更操作必须记录:

```python
AuditLog(
    action="system_config_updated",
    target_type="system_config",
    target_id=config_key,
    operator_id=admin_id,
    details={
        "old_value": old_value,
        "new_value": new_value
    }
)
```

---

## 九、前端交互

### 9.1 面板布局

```
┌─────────────────────────────────────────────────────┐
│  [Configs] [Cache] [Logs] [Tasks] [Webhooks]       │
├─────────────────────────────────────────────────────┤
│                                                     │
│  当前面板内容                                        │
│                                                     │
│  高危操作需要二次确认弹窗                            │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 9.2 确认弹窗示例

```
┌─────────────────────────────────────┐
│  ⚠️ 危险操作                        │
├─────────────────────────────────────┤
│                                     │
│  您即将清空所有缓存。               │
│  这可能导致短暂的性能下降。         │
│                                     │
│  请输入 "CONFIRM" 确认操作:         │
│  [________________]                 │
│                                     │
│      [取消]    [确认清空]           │
└─────────────────────────────────────┘
```

---

## 十、相关文档

- [Admin API 端点](../../api/admin-endpoints.md)
- [配置系统](./config-ops.md)
- [日志规范](../../../02-standards/logging-standard.md)

---

**END OF DOCUMENT**
