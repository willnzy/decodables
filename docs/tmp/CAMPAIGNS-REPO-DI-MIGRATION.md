# Campaigns Service - Repository 依赖注入迁移计划

## 目标

将 `domains/marketing/campaigns/service.py` 从直接操作数据库改为依赖注入 Repository 模式。

## 当前状态

Campaigns 模块有 8 个函数,其中 5 个写操作函数直接使用 `db_client.table("campaigns")`:

### 写操作函数 (需要 DI)
1. `create_campaign` - 创建 Campaign
2. `update_campaign` - 更新 Campaign
3. `delete_campaign` - 删除 Campaign (软删除)
4. `activate_campaign` - 激活 Campaign
5. `pause_campaign` - 暂停 Campaign

### 只读操作 (可选 DI)
6. `list_campaigns` - 列表查询
7. `get_campaign` - 单个查询
8. `get_campaign_stats` - 统计信息

### 审计日志
9. `_log_campaign_change` - 专用审计表 (campaign_audit_logs)

## 特点分析

### 与 Notifications/AI Models 的相似性
1. ✅ 已有完整审计日志 (`_log_campaign_change` → `campaign_audit_logs` 表)
2. ✅ 使用专用审计表,不需要迁移到 `@audit_log` 装饰器
3. ✅ 有 `ICampaignRepository` 接口定义
4. ⚠️ 当前直接使用 `db_client.table()`,没有使用 Repository 层

### Repository 使用
- 需要从 `db_client.table()` 迁移到 Repository 调用
- 需要添加 `ICampaignRepository` 接口依赖

## 迁移方案

### Step 1: 添加工厂函数

```python
from typing import Optional
from domains.marketing.repository import ICampaignRepository

def _get_campaign_repo(repo: Optional[ICampaignRepository] = None) -> ICampaignRepository:
    """
    获取 CampaignRepository 实例 (依赖注入或默认实例).

    Args:
        repo: 可选的 Repository 实例 (用于依赖注入/测试)

    Returns:
        ICampaignRepository 实例
    """
    if repo:
        return repo

    from core.database import get_database_client
    from infrastructure.repositories import SupabaseCampaignRepository

    db_client = get_database_client()
    return SupabaseCampaignRepository(db_client)
```

### Step 2: 修改写操作函数

为每个写操作函数添加 `campaign_repo: Optional[ICampaignRepository] = None` 参数。

#### 函数 1: create_campaign

**修改前**:
```python
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
    from core.database import get_database_client

    campaign_data = {...}

    try:
        db_client = get_database_client()
        result = db_client.table("campaigns").insert(campaign_data).execute()

        if not result.data:
            return None

        campaign = result.data[0]
        # ... audit log ...
```

**修改后**:
```python
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
    campaign_repo: Optional[ICampaignRepository] = None,  # ← 新增
) -> Optional[Dict[str, Any]]:
    repo = _get_campaign_repo(campaign_repo)  # ← 使用工厂

    campaign_data = {...}

    try:
        campaign = await repo.create(campaign_data)  # ← 使用 Repository

        if not campaign:
            return None

        # ... audit log ...
```

#### 函数 2-5: update/delete/activate/pause_campaign

同样模式:
- 添加 `campaign_repo: Optional[ICampaignRepository] = None` 参数
- 使用 `repo = _get_campaign_repo(campaign_repo)`
- 将 `db_client.table()` 调用改为 Repository 方法

### Step 3 (可选): 为只读操作添加 DI

虽然只读操作不是强制需求,但为了一致性可以同样添加 Repository DI:
- `list_campaigns` → `repo.list()`
- `get_campaign` → `repo.get_by_id()`
- `get_campaign_stats` → 可能需要新增 Repository 方法

## 代码统计

| 函数 | 迁移前行数 | 迁移后行数 | 变化 | 说明 |
|------|-----------|-----------|------|------|
| create_campaign | 87 | 82 | -5 | 移除重复实例化 |
| update_campaign | 60 | 55 | -5 | 移除重复实例化 |
| delete_campaign | 53 | 48 | -5 | 移除重复实例化 |
| activate_campaign | 53 | 48 | -5 | 移除重复实例化 |
| pause_campaign | 53 | 48 | -5 | 移除重复实例化 |
| **工厂函数** | 0 | +16 | +16 | 新增 |
| **总计** | 306 | 297 | -9 | 净减少 |

## 测试验证

### 1. 现有测试应该通过
```bash
pytest tests/api/admin/test_campaigns.py -v
```

### 2. 依赖注入测试 (新增)
```python
async def test_create_campaign_with_mock_repo():
    mock_repo = AsyncMock(spec=ICampaignRepository)
    mock_repo.create.return_value = {"id": "camp-1", "name": "Test"}

    result = await create_campaign(
        name="Test Campaign",
        description="Test",
        campaign_type="promotion",
        config={},
        target_type="all_users",
        target_config=None,
        notification_channels=["email"],
        notification_config={},
        start_at="2026-01-10T00:00:00Z",
        end_at=None,
        timezone="UTC",
        usage_limit=None,
        usage_per_user=None,
        admin_id="admin-123",
        campaign_repo=mock_repo,  # ← 注入 Mock
    )

    assert result is not None
    mock_repo.create.assert_called_once()
```

## 向后兼容性

✅ **完全兼容** - API 层调用无需修改:

```python
# API 层代码 (无需修改)
result = await create_campaign(
    name=req.name,
    description=req.description,
    # ... other params ...
    admin_id=admin["id"],
)  # ← 不传 campaign_repo，使用默认实例
```

## 关键决策

### 为什么不迁移审计日志装饰器？

Campaigns 使用专用审计日志表 (`campaign_audit_logs`),数据结构与通用审计日志不同:
- 记录 `campaign_id`, `action`, `old_value`, `new_value`
- 专门为 Campaign 变更设计
- 与 AI Models 的 `config_audit_logs` 类似

**决定**: 保留现有 `_log_campaign_change()` 机制,不使用 `@audit_log` 装饰器。

## 风险评估

| 风险 | 级别 | 缓解措施 |
|------|------|---------| |
| 破坏现有调用 | 🟢 无 | 可选参数,向后兼容 |
| 测试失败 | 🟢 极低 | 函数签名改动小 |
| 审计日志丢失 | 🟢 无 | 保留现有审计机制 |
| Repository 方法不存在 | 🟡 低 | 需先确认 ICampaignRepository 接口完整性 |

## 实施顺序

1. ✅ 确认 ICampaignRepository 接口定义
2. ✅ 确认 SupabaseCampaignRepository 实现
3. ✅ 添加工厂函数 `_get_campaign_repo()`
4. ✅ 修改 5 个写操作函数签名
5. ✅ 更新所有数据库调用为 Repository 调用
6. ✅ 运行测试验证
7. ✅ Git commit + push
8. ✅ 添加单元测试 (test_campaigns_service.py)
