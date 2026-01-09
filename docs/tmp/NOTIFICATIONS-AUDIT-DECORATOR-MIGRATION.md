# Notifications Service - 审计日志装饰器迁移计划

## 目标

将 `domains/platform/notifications/service.py` 中的 3 个函数从手动审计日志迁移到使用 `@audit_log` 装饰器。

## 当前状态分析

### 需要迁移的函数

1. **send_broadcast** (93-108 行)
   - 手动审计: `stats_repo.log_user_event()` + `admin_users_repo.admin_log_operation()`
   - 特点: 广播操作,无 target_user_id

2. **send_to_user** (111-171 行)
   - 手动审计: `stats_repo.log_user_event()` + `admin_users_repo.admin_log_operation()`
   - 特点: 单用户操作,有 target_user_id

3. **send_to_users** (174-238 行)
   - 手动审计: `stats_repo.log_user_event()` + `admin_users_repo.admin_log_operation()`
   - 特点: 批量操作,无 target_user_id (多个用户)

### 不需要迁移的函数

4. **get_stats** - 只读操作,无审计日志
5. **get_history** - 只读操作,无审计日志

## 迁移方案

### 方案 A: 完整使用 @audit_log 装饰器 (推荐)

**优点**:
- ✅ 完全消除重复代码
- ✅ 统一审计日志机制
- ✅ 易于维护

**缺点**:
- ⚠️ 需要修改函数返回值（装饰器从返回值提取信息）

### 方案 B: 创建专用 @audit_log_notification 装饰器

**优点**:
- ✅ 针对 Notifications 的特殊需求定制
- ✅ 可以保持现有返回值结构

**缺点**:
- ❌ 增加代码复杂度
- ❌ 不够通用

**决定**: 采用方案 A

## 详细迁移步骤

### 函数 1: send_broadcast

**迁移前**:
```python
async def send_broadcast(
    title: str,
    content: str,
    target_group: str,
    admin_id: str,
) -> Dict[str, Any]:
    # ... 业务逻辑 ...

    result = {
        "target_group": target_group,
        "user_count": len(user_ids),
        "notification_count": len(notifications),
        "title": title
    }

    # 手动审计日志
    await stats_repo.log_user_event(admin_id, "admin_broadcast", {
        "target_group": target_group,
        "title": title
    })
    await admin_users_repo.admin_log_operation(
        admin_id=admin_id,
        operation_type="broadcast",
        target_user_id=None,
        details=f"Broadcast to {target_group}: {title[:50]}",
        reason=None
    )

    logger.info(f"[Notifications] Broadcast sent to {len(user_ids)} users by admin {admin_id}")
    return result
```

**迁移后**:
```python
from core.audit import audit_log

@audit_log(
    operation_type="broadcast",
    event_type="admin_broadcast",
    get_details=lambda result, **kwargs: f"Broadcast to {kwargs.get('target_group')}: {kwargs.get('title', '')[:50]}"
)
async def send_broadcast(
    title: str,
    content: str,
    target_group: str,
    admin_id: str,
) -> Dict[str, Any]:
    from core.database import get_database_client
    from infrastructure.repositories import SupabaseNotificationRepository

    db_client = get_database_client()
    notification_repo = SupabaseNotificationRepository(db_client)

    # Business Logic: Query target users based on group
    if target_group == "all":
        users_result = db_client.table("profiles").select("id").execute()
    else:
        users_result = db_client.table("profiles").select("id").eq(
            "tier", target_group
        ).execute()

    users = users_result.data or []
    user_ids = [u["id"] for u in users]

    # Create notifications for all users
    notifications = []
    for user_id in user_ids:
        notification = await notification_repo.create_notification(
            user_id=user_id,
            title=title,
            message=content,
            notification_type="system"
        )
        if notification:
            notifications.append(notification)

    result = {
        "target_group": target_group,
        "user_count": len(user_ids),
        "notification_count": len(notifications),
        "title": title
    }

    logger.info(f"[Notifications] Broadcast sent to {len(user_ids)} users by admin {admin_id}")
    return result
    # ← 移除了手动审计日志代码
```

**代码减少**: 15 行 → 0 行审计日志代码

### 函数 2: send_to_user

**迁移后**:
```python
@audit_log(
    operation_type="notification_send",
    event_type="admin_notification_send",
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
    # ... 只保留业务逻辑 ...
```

**特点**: 使用 `get_target_user_id` 提取目标用户 ID

### 函数 3: send_to_users

**迁移后**:
```python
@audit_log(
    operation_type="notification_batch",
    event_type="admin_notification_batch",
    get_details=lambda result, **kwargs: f"Batch notification to {len(kwargs.get('user_ids', []))} users: {kwargs.get('title', '')[:50]}"
)
async def send_to_users(
    user_ids: List[str],
    title: str,
    content: str,
    notification_type: str,
    admin_id: str,
) -> Dict[str, Any]:
    # ... 只保留业务逻辑 ...
```

## 迁移后代码统计

| 函数 | 迁移前行数 | 迁移后行数 | 减少行数 | 审计日志代码 |
|------|-----------|-----------|---------|-------------|
| send_broadcast | 76 | 61 | -15 | 移除 |
| send_to_user | 60 | 45 | -15 | 移除 |
| send_to_users | 64 | 49 | -15 | 移除 |
| **总计** | **200** | **155** | **-45** | **-45 行** |

## 测试验证

### 1. 单元测试
- 现有测试应该全部通过 (39/39)
- 无需修改测试代码（装饰器不改变函数签名）

### 2. 审计日志验证

运行后检查数据库:
```sql
-- 检查 admin_log_operations 表
SELECT * FROM admin_log_operations
WHERE operation_type IN ('broadcast', 'notification_send', 'notification_batch')
ORDER BY created_at DESC LIMIT 10;

-- 检查 stats_events 表
SELECT * FROM stats_events
WHERE event_type IN ('admin_broadcast', 'admin_notification_send', 'admin_notification_batch')
ORDER BY created_at DESC LIMIT 10;
```

### 3. 功能测试
- 测试广播通知
- 测试单用户通知
- 测试批量通知
- 验证审计日志正确记录

## 风险评估

| 风险 | 级别 | 缓解措施 |
|------|------|---------|
| 装饰器失败导致操作失败 | 🟡 低 | 装饰器已设计为失败时不影响业务操作 |
| 审计日志格式变化 | 🟡 低 | 装饰器生成的日志格式与现有一致 |
| 测试失败 | 🟢 极低 | 函数签名和返回值不变 |

## 回滚计划

如果迁移出现问题:
1. 使用 Git 回滚到迁移前的 commit
2. 重新评估装饰器设计
3. 逐个函数迁移而非批量迁移

## 后续优化

迁移成功后可以考虑:
1. 为其他模块应用相同模式
2. 为 Campaigns 模块创建专用装饰器（使用 campaign_audit_logs 表）
3. 添加装饰器的单元测试
