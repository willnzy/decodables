# AI Models Service - Repository 依赖注入迁移计划

## 目标

将 `domains/platform/ai/service.py` 从直接实例化 Repository 改为依赖注入模式。

## 当前状态

AI Models 模块有 7 个函数,其中 4 个写操作函数直接实例化 `SupabaseConfigRepository`:

### 写操作函数 (需要 DI)
1. `update_text_model_config` - 更新文本模型配置
2. `update_image_model_config` - 更新图像模型配置
3. `update_canary_config` - 更新 Canary 配置
4. `toggle_ai_provider` - 切换 AI 提供商

### 只读操作 (已通过 shared/ai 调用,不需要 DI)
5. `get_model_configs` - 通过 shared/ai 获取配置
6. `get_ai_usage_stats` - 统计信息,无 Repository
7. `clear_ai_cache` - 缓存操作,无 Repository

## 特点分析

### 与 Notifications 的差异
1. ✅ AI Models 已有完整审计日志 (`_log_config_change` → `config_audit_logs` 表)
2. ✅ 使用专用审计表,不需要迁移到 `@audit_log` 装饰器
3. ⚠️ 只读操作通过 `shared/ai/model_config.py` 调用,不在 Service 层

### Repository 使用
- 所有写操作使用 `SupabaseConfigRepository`
- 需要添加 `IAIModelConfigRepository` 接口依赖

## 迁移方案

### Step 1: 添加工厂函数

```python
from typing import Optional
from domains.platform.repository import IAIModelConfigRepository

def _get_config_repo(repo: Optional[IAIModelConfigRepository] = None) -> IAIModelConfigRepository:
    """
    获取 AIModelConfigRepository 实例 (依赖注入或默认实例).

    Args:
        repo: 可选的 Repository 实例 (用于依赖注入/测试)

    Returns:
        IAIModelConfigRepository 实例
    """
    if repo:
        return repo

    from core.database import get_database_client
    from infrastructure.repositories import SupabaseConfigRepository

    db_client = get_database_client()
    return SupabaseConfigRepository(db_client)
```

### Step 2: 修改 4 个写操作函数

为每个函数添加 `config_repo: Optional[IAIModelConfigRepository] = None` 参数。

#### 函数 1: update_text_model_config

**修改前**:
```python
async def update_text_model_config(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    admin_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    from core.database import get_database_client
    from infrastructure.repositories import SupabaseConfigRepository

    db_client = get_database_client()
    config_repo = SupabaseConfigRepository(db_client)

    # ... business logic ...
```

**修改后**:
```python
async def update_text_model_config(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    admin_id: Optional[str] = None,
    config_repo: Optional[IAIModelConfigRepository] = None,  # ← 新增
) -> Optional[Dict[str, Any]]:
    repo = _get_config_repo(config_repo)  # ← 使用工厂

    # ... business logic uses 'repo' ...
```

#### 函数 2: update_image_model_config

同样模式,添加 `config_repo` 参数。

#### 函数 3: update_canary_config

同样模式,添加 `config_repo` 参数。

#### 函数 4: toggle_ai_provider

同样模式,添加 `config_repo` 参数。

## 代码统计

| 函数 | 迁移前行数 | 迁移后行数 | 变化 | 说明 |
|------|-----------|-----------|------|------|
| update_text_model_config | 91 | 86 | -5 | 移除重复实例化 |
| update_image_model_config | 92 | 87 | -5 | 移除重复实例化 |
| update_canary_config | 72 | 67 | -5 | 移除重复实例化 |
| toggle_ai_provider | 93 | 88 | -5 | 移除重复实例化 |
| **工厂函数** | 0 | +16 | +16 | 新增 |
| **总计** | 348 | 344 | -4 | 净减少 |

## 测试验证

### 1. 现有测试应该通过
```bash
pytest tests/api/admin/test_ai_models.py -v
```

### 2. 依赖注入测试 (新增)
```python
async def test_update_text_config_with_mock_repo():
    mock_repo = AsyncMock(spec=IAIModelConfigRepository)
    mock_repo.get_by_key.return_value = None
    mock_repo.create.return_value = True

    result = await update_text_model_config(
        provider="openai",
        model="gpt-4",
        admin_id="admin-123",
        config_repo=mock_repo,  # ← 注入 Mock
    )

    assert result is not None
    mock_repo.create.assert_called_once()
```

## 向后兼容性

✅ **完全兼容** - API 层调用无需修改:

```python
# API 层代码 (无需修改)
result = await update_text_model_config(
    provider=req.provider,
    model=req.model,
    admin_id=admin["id"],
)  # ← 不传 config_repo，使用默认实例
```

## 关键决策

### 为什么不迁移审计日志装饰器？

AI Models 使用专用审计日志表 (`config_audit_logs`),数据结构与通用审计日志不同:
- 记录 `config_key`, `old_value`, `new_value`
- 专门为配置变更设计
- 与 Campaigns 的 `campaign_audit_logs` 类似

**决定**: 保留现有 `_log_config_change()` 机制,不使用 `@audit_log` 装饰器。

## 风险评估

| 风险 | 级别 | 缓解措施 |
|------|------|---------|
| 破坏现有调用 | 🟢 无 | 可选参数,向后兼容 |
| 测试失败 | 🟢 极低 | 函数签名改动小 |
| 审计日志丢失 | 🟢 无 | 保留现有审计机制 |

## 实施顺序

1. ✅ 添加工厂函数 `_get_config_repo()`
2. ✅ 修改 4 个写操作函数签名
3. ✅ 更新所有 `config_repo` 调用为 `repo`
4. ✅ 运行测试验证
5. ✅ Git commit + push
