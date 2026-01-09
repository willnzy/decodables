# Notifications Service - Repository 依赖注入迁移计划

## 目标

将 `domains/platform/notifications/service.py` 从直接实例化 Repository 改为依赖注入模式。

## 当前问题

**紧耦合**: Service 函数内部直接实例化 Repository
```python
async def send_broadcast(...):
    from core.database import get_database_client
    from infrastructure.repositories import SupabaseNotificationRepository

    db_client = get_database_client()
    notification_repo = SupabaseNotificationRepository(db_client)  # ❌ 紧耦合
    # ...
```

**问题**:
1. 违反依赖倒置原则 (DIP) - Service 依赖具体实现而非接口
2. 难以单元测试 - 无法注入 Mock Repository
3. Repository 切换困难 - 需要修改每个 Service 函数
4. 代码重复 - 每个函数都有相同的实例化代码

## 迁移方案

### 方案: 使用工厂函数 + 可选依赖注入

**优点**:
- ✅ 向后兼容 - 不破坏现有调用代码
- ✅ 测试友好 - 可以注入 Mock Repository
- ✅ 符合 DIP - 依赖 Repository Interface
- ✅ 代码简洁 - 统一的 Repository 获取逻辑

**实现**:
```python
def _get_notification_repo(repo: Optional[INotificationRepository] = None) -> INotificationRepository:
    """获取 NotificationRepository 实例 (依赖注入或默认实例)."""
    if repo:
        return repo

    from core.database import get_database_client
    from infrastructure.repositories import SupabaseNotificationRepository

    db_client = get_database_client()
    return SupabaseNotificationRepository(db_client)


async def send_broadcast(
    title: str,
    content: str,
    target_group: str,
    admin_id: str,
    notification_repo: Optional[INotificationRepository] = None,  # ← 可选参数
) -> Dict[str, Any]:
    """发送广播通知."""
    repo = _get_notification_repo(notification_repo)
    # ... 使用 repo ...
```

## 详细迁移步骤

### Step 1: 添加工厂函数

在 `service.py` 顶部添加 3 个工厂函数:

```python
from typing import Optional
from domains.platform.repository import INotificationRepository

def _get_notification_repo(repo: Optional[INotificationRepository] = None) -> INotificationRepository:
    """获取 NotificationRepository 实例."""
    if repo:
        return repo

    from core.database import get_database_client
    from infrastructure.repositories import SupabaseNotificationRepository

    db_client = get_database_client()
    return SupabaseNotificationRepository(db_client)


def _get_stats_repo(repo = None):
    """获取 AdminStatsRepository 实例."""
    if repo:
        return repo

    from core.database import get_database_client
    from infrastructure.repositories import SupabaseAdminStatsRepository

    db_client = get_database_client()
    return SupabaseAdminStatsRepository(db_client)


def _get_admin_users_repo(repo = None):
    """获取 AdminUsersRepository 实例."""
    if repo:
        return repo

    from core.database import get_database_client
    from infrastructure.repositories import SupabaseAdminUsersRepository

    db_client = get_database_client()
    return SupabaseAdminUsersRepository(db_client)
```

### Step 2: 修改 send_broadcast 函数

**修改前**:
```python
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

    # Business logic...
```

**修改后**:
```python
async def send_broadcast(
    title: str,
    content: str,
    target_group: str,
    admin_id: str,
    notification_repo: Optional[INotificationRepository] = None,
) -> Dict[str, Any]:
    repo = _get_notification_repo(notification_repo)

    # Business logic uses 'repo' instead of 'notification_repo'
```

### Step 3: 修改 send_to_user 函数

**修改后**:
```python
async def send_to_user(
    user_id: str,
    title: str,
    content: str,
    notification_type: str,
    admin_id: str,
    notification_repo: Optional[INotificationRepository] = None,
) -> Dict[str, Any]:
    repo = _get_notification_repo(notification_repo)

    notification = await repo.send_notification_to_user(...)
    # ...
```

### Step 4: 修改 send_to_users 函数

**修改后**:
```python
async def send_to_users(
    user_ids: List[str],
    title: str,
    content: str,
    notification_type: str,
    admin_id: str,
    notification_repo: Optional[INotificationRepository] = None,
) -> Dict[str, Any]:
    repo = _get_notification_repo(notification_repo)

    notifications = await repo.send_notification_to_users(...)
    # ...
```

### Step 5: 修改 get_stats 和 get_history 函数

```python
async def get_stats(
    notification_repo: Optional[INotificationRepository] = None,
) -> Dict[str, Any]:
    repo = _get_notification_repo(notification_repo)
    return await repo.get_all_notification_stats()


async def get_history(
    offset: int = 0,
    limit: int = 50,
    notification_repo: Optional[INotificationRepository] = None,
) -> Dict[str, Any]:
    repo = _get_notification_repo(notification_repo)
    return await repo.get_notification_history(offset=offset, limit=limit)
```

## 代码统计

| 函数 | 修改前行数 | 修改后行数 | 变化 | 说明 |
|------|-----------|-----------|------|------|
| send_broadcast | 67 | 62 | -5 | 移除重复实例化代码 |
| send_to_user | 48 | 43 | -5 | 移除重复实例化代码 |
| send_to_users | 43 | 38 | -5 | 移除重复实例化代码 |
| get_stats | 12 | 8 | -4 | 移除重复实例化代码 |
| get_history | 13 | 9 | -4 | 移除重复实例化代码 |
| **新增工厂函数** | 0 | +48 | +48 | 3个工厂函数 |
| **总计** | 183 | 208 | +25 | 净增加（提高可测试性） |

**说明**: 虽然总行数增加了 25 行，但带来以下好处:
1. 可测试性提升 - 可以注入 Mock Repository
2. 符合 SOLID 原则 - 依赖倒置
3. 代码更清晰 - 统一的 Repository 获取逻辑
4. 向后兼容 - 不破坏现有调用

## 测试验证

### 1. 单元测试 (现有测试应该全部通过)

```bash
python -m pytest tests/api/admin/test_notifications.py -v
```

### 2. 依赖注入测试 (新增测试)

```python
# 示例: 使用 Mock Repository
from unittest.mock import AsyncMock

async def test_send_broadcast_with_mock_repo():
    # Arrange
    mock_repo = AsyncMock(spec=INotificationRepository)
    mock_repo.create_notification.return_value = {"id": "notif-123"}

    # Act
    result = await send_broadcast(
        title="Test",
        content="Test content",
        target_group="all",
        admin_id="admin-123",
        notification_repo=mock_repo  # ← 注入 Mock
    )

    # Assert
    assert result["notification_count"] > 0
    mock_repo.create_notification.assert_called()
```

## 向后兼容性

✅ **完全兼容** - API 层调用无需修改:

```python
# API 层代码 (无需修改)
result = await send_broadcast(
    title=req.title,
    content=req.content,
    target_group=req.target_group,
    admin_id=admin["id"],
)  # ← 不传 notification_repo 参数，使用默认实例
```

## 风险评估

| 风险 | 级别 | 缓解措施 |
|------|------|---------|
| 破坏现有调用 | 🟢 无 | 可选参数，向后兼容 |
| 测试失败 | 🟢 极低 | 函数签名改动小，现有测试应该通过 |
| 性能影响 | 🟢 无 | 工厂函数开销可忽略 |

## 后续优化

迁移成功后可以考虑:
1. 为其他模块应用相同模式 (AI Models, Campaigns, etc.)
2. 添加 Service 层单元测试 (使用 Mock Repository)
3. 创建统一的 Repository Factory 模式
