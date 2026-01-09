# Audit Log Decorator - 使用指南

## 概述

`core.audit` 模块提供了统一的审计日志装饰器,用于自动记录管理员操作,避免在每个 Service 函数中重复调用审计日志代码。

## 当前问题

目前每个 Service 函数都需要手动调用审计日志:

```python
# ❌ 旧方式: 在每个函数中重复调用
async def create_campaign(..., admin_id: str):
    # 业务逻辑
    campaign = ...

    # 手动审计日志 (重复代码)
    await stats_repo.log_user_event(admin_id, "admin_campaign_create", {...})
    await admin_users_repo.admin_log_operation(
        admin_id=admin_id,
        operation_type="campaign_create",
        target_user_id=None,
        details=f"Campaign: {campaign['name']}",
        reason=None
    )

    return campaign
```

**问题**:
1. 代码重复 (每个函数都要写类似的代码)
2. 容易遗漏 (新功能可能忘记添加审计日志)
3. 难以维护 (修改审计日志格式需要改所有地方)
4. 错误处理不一致

## 新方案: 使用装饰器

### 方式 1: `@audit_log` (高级用法)

适用于需要自定义日志内容的场景:

```python
from core.audit import audit_log

@audit_log(
    operation_type="campaign_create",
    event_type="admin_campaign_create",
    get_details=lambda result, **kwargs: f"Created campaign: {result['name']}"
)
async def create_campaign(
    name: str,
    description: str,
    ...,
    admin_id: str,  # ← 必须有 admin_id 参数
) -> Dict[str, Any]:
    """创建 Campaign."""
    campaign_data = {...}
    result = db_client.table("campaigns").insert(campaign_data).execute()
    return result.data[0]
```

**特点**:
- ✅ 自动记录到 `admin_log_operations` 和 `stats_events`
- ✅ 只在成功时记录 (失败不记录)
- ✅ 不影响业务逻辑 (审计失败不会导致操作失败)
- ✅ 支持自定义详情内容

### 方式 2: `@audit_log_simple` (简化用法)

适用于简单场景,使用模板字符串:

```python
from core.audit import audit_log_simple

@audit_log_simple("campaign_delete", "Deleted campaign {campaign_id}")
async def delete_campaign(
    campaign_id: str,
    admin_id: str,  # ← 必须有 admin_id 参数
) -> bool:
    """删除 Campaign (软删除)."""
    result = db_client.table("campaigns").update({
        "status": "deleted",
        "is_active": False,
    }).eq("id", campaign_id).execute()

    return len(result.data) > 0
```

**特点**:
- ✅ 更简洁,适合简单操作
- ✅ 模板字符串自动填充参数
- ✅ 自动处理目标用户 ID (如果有 `target_user_id` 参数)

### 方式 3: 带目标用户 ID

```python
@audit_log(
    operation_type="notification_send",
    get_target_user_id=lambda *args, **kwargs: kwargs.get("user_id"),
    get_details=lambda result, **kwargs: f"Notification: {kwargs.get('title', '')[:50]}"
)
async def send_to_user(
    user_id: str,
    title: str,
    content: str,
    notification_type: str,
    admin_id: str,
) -> Dict[str, Any]:
    """发送通知给单个用户."""
    notification = await notification_repo.send_notification_to_user(...)
    return {"status": "sent", "notification": notification}
```

## 迁移指南

### Step 1: 识别需要迁移的函数

查找所有手动调用审计日志的 Service 函数:

```bash
grep -r "admin_log_operation" domains/
grep -r "log_user_event" domains/
```

### Step 2: 选择装饰器类型

| 场景 | 使用装饰器 |
|------|-----------|
| 简单操作 (如删除、激活) | `@audit_log_simple` |
| 需要自定义日志内容 | `@audit_log` |
| 需要记录目标用户 ID | `@audit_log` with `get_target_user_id` |

### Step 3: 应用装饰器

**迁移前**:
```python
async def create_campaign(..., admin_id: str):
    campaign = ...

    # 手动审计日志
    await stats_repo.log_user_event(admin_id, "admin_campaign_create", {...})
    await admin_users_repo.admin_log_operation(
        admin_id=admin_id,
        operation_type="campaign_create",
        target_user_id=None,
        details=f"Campaign: {campaign['name']}",
        reason=None
    )

    return campaign
```

**迁移后**:
```python
@audit_log(
    operation_type="campaign_create",
    event_type="admin_campaign_create",
    get_details=lambda result: f"Campaign: {result['name']}"
)
async def create_campaign(..., admin_id: str):
    campaign = ...
    return campaign  # ← 移除手动审计日志代码
```

### Step 4: 测试验证

1. 运行现有测试,确保功能正常
2. 验证审计日志是否正确记录:
   ```sql
   SELECT * FROM admin_log_operations WHERE admin_id = '...' ORDER BY created_at DESC LIMIT 10;
   SELECT * FROM stats_events WHERE user_id = '...' AND event_type LIKE 'admin_%' ORDER BY created_at DESC LIMIT 10;
   ```

## 迁移优先级

### 高优先级 (建议立即迁移)

1. **Campaigns Module** - 8 个函数
   - `create_campaign`
   - `update_campaign`
   - `delete_campaign`
   - `activate_campaign`
   - `pause_campaign`

2. **Notifications Module** - 3 个函数
   - `send_broadcast`
   - `send_to_user`
   - `send_to_users`

3. **AI Models Config Module** - 需要添加审计日志的函数

### 中优先级

其他 Admin API 模块中有审计日志需求的函数

### 低优先级

- 只读操作 (GET 请求) 通常不需要审计日志
- 统计/报表类操作

## 示例: 完整迁移

### Campaigns Module

```python
# domains/marketing/campaigns/service.py

from core.audit import audit_log, audit_log_simple

@audit_log(
    operation_type="campaign_create",
    event_type="admin_campaign_create",
    get_details=lambda result: f"Created campaign: {result['name']}"
)
async def create_campaign(
    name: str,
    description: Optional[str],
    campaign_type: str,
    config: dict,
    target_type: str,
    target_config: Optional[dict],
    notification_channels: List[str],
    notification_config: Optional[dict],
    start_at: str,
    end_at: Optional[str],
    timezone: str,
    usage_limit: Optional[int],
    usage_per_user: Optional[int],
    admin_id: str,
) -> Optional[Dict[str, Any]]:
    """创建 Campaign."""
    from core.database import get_database_client

    campaign_data = {
        "name": name,
        "description": description,
        "type": campaign_type,
        "config": config,
        "target_type": target_type,
        "target_config": target_config,
        "notification_channels": notification_channels,
        "notification_config": notification_config,
        "start_at": start_at,
        "end_at": end_at,
        "timezone": timezone,
        "usage_limit": usage_limit,
        "usage_per_user": usage_per_user,
        "status": STATUS_DRAFT,
        "is_active": False,
        "created_by": admin_id,
    }

    db_client = get_database_client()
    result = db_client.table("campaigns").insert(campaign_data).execute()

    if not result.data:
        return None

    campaign = result.data[0]
    logger.info(f"[Campaigns] Campaign {campaign['id']} created by {admin_id}")
    return campaign
    # ← 移除了手动审计日志代码


@audit_log_simple("campaign_delete", "Deleted campaign {campaign_id}")
async def delete_campaign(
    campaign_id: str,
    admin_id: str,
) -> bool:
    """删除 Campaign (软删除)."""
    from core.database import get_database_client

    db_client = get_database_client()
    result = db_client.table("campaigns").update({
        "status": STATUS_DELETED,
        "is_active": False,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", campaign_id).execute()

    if not result.data:
        return False

    logger.info(f"[Campaigns] Campaign {campaign_id} deleted by {admin_id}")
    return True
    # ← 移除了手动审计日志代码


@audit_log_simple("campaign_activate", "Activated campaign {campaign_id}")
async def activate_campaign(
    campaign_id: str,
    admin_id: str,
) -> bool:
    """激活 Campaign."""
    from core.database import get_database_client

    db_client = get_database_client()
    result = db_client.table("campaigns").update({
        "status": STATUS_ACTIVE,
        "is_active": True,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", campaign_id).execute()

    if not result.data:
        return False

    logger.info(f"[Campaigns] Campaign {campaign_id} activated by {admin_id}")
    return True
    # ← 移除了手动审计日志代码
```

## 注意事项

### 必需条件

1. **admin_id 参数**: 装饰的函数必须有 `admin_id` 参数
2. **异步函数**: 只支持 `async def` 函数
3. **返回值**: 函数必须返回结果 (用于生成详情)

### 错误处理

- 审计日志失败**不会**导致业务操作失败
- 审计失败会记录 WARNING/ERROR 日志
- 如果没有 `admin_id`,会跳过审计日志并记录 WARNING

### 性能影响

- 审计日志是异步操作,不阻塞主流程
- 失败时不会重试 (避免影响性能)
- 装饰器开销极小 (~1ms)

## 总结

### 优势

- ✅ **代码简化**: 移除重复的审计日志代码
- ✅ **易于维护**: 集中管理审计逻辑
- ✅ **不易遗漏**: 装饰器确保审计日志始终执行
- ✅ **错误处理**: 统一的错误处理逻辑
- ✅ **可测试**: 装饰器可以独立测试

### 下一步

1. 逐步迁移现有代码 (从 Campaigns/Notifications 开始)
2. 新功能直接使用装饰器
3. 定期检查审计日志覆盖率
4. 考虑添加 mypy 类型检查

## 示例测试

```python
# tests/core/test_audit.py

import pytest
from core.audit import audit_log, audit_log_simple

class TestAuditDecorator:
    @pytest.mark.asyncio
    async def test_audit_log_decorator(self, mocker):
        """Test audit_log decorator creates logs."""
        # Mock repositories
        mock_stats_repo = mocker.patch('core.audit.SupabaseAdminStatsRepository')
        mock_admin_repo = mocker.patch('core.audit.SupabaseAdminUsersRepository')

        @audit_log(
            operation_type="test_operation",
            get_details=lambda result: f"Result: {result}"
        )
        async def test_func(admin_id: str):
            return "success"

        result = await test_func(admin_id="admin-123")

        assert result == "success"
        assert mock_stats_repo.called
        assert mock_admin_repo.called

    @pytest.mark.asyncio
    async def test_audit_log_without_admin_id(self, mocker):
        """Test decorator handles missing admin_id gracefully."""
        @audit_log(operation_type="test")
        async def test_func():
            return "success"

        result = await test_func()
        assert result == "success"  # Should not fail
```
