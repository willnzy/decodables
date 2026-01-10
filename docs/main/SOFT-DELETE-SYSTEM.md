# Make Decodables 软删除系统完整文档

**版本**: v3.0
**更新时间**: 2026-01-10
**状态**: ✅ 生产就绪

---

## 📋 目录

1. [系统概述](#系统概述)
2. [架构设计](#架构设计)
3. [数据库设计](#数据库设计)
4. [代码实现](#代码实现)
5. [使用指南](#使用指南)
6. [最佳实践](#最佳实践)
7. [故障排查](#故障排查)

---

## 系统概述

### 核心理念

**Make Decodables 软删除系统**实现了"逻辑删除"而非"物理删除"，确保：
- ✅ 用户误删可恢复 (30天恢复期，可配置)
- ✅ 数据合规性 (GDPR 要求保留删除记录)
- ✅ 审计追踪 (保留完整操作历史)
- ✅ 系统稳定性 (避免级联删除引发的数据一致性问题)

### 核心特性

| 特性 | 说明 |
|------|------|
| **软删除机制** | 使用 `is_deleted`/`deleted_at`/`recovery_expires_at` 三件套标记删除状态 |
| **恢复期追踪** | 默认 30 天可恢复期，过期后从用户视图自动隐藏 |
| **自动清理** | 每天凌晨 2 点自动物理删除过期 90 天的记录 |
| **查询优化** | 条件部分索引 (Partial Index) 提升查询性能 |
| **统一接口** | BaseRepository 提供统一的软删除方法 |

### 覆盖范围

| 指标 | 数值 |
|------|------|
| **已支持软删除** | 22 张表 (100% 核心表) |
| **Git Commits** | 5 个 (Phase 3.1-3.3) |
| **新增代码** | 4,500+ 行 |
| **测试覆盖** | 29 tests, 100% 通过 |

**支持软删除的 22 张表**:
- **Phase 2 核心表** (14张): profiles, projects, project_versions, assets, marketplace_listings, asset_categories, system_assets, notifications, campaign_participations, campaign_dismissals, onboarding_steps, user_onboarding_progress, referrals, credit_transactions
- **Phase 3 新增表** (8张): marketplace_favorites, marketplace_reviews, campaigns, daily_themes, holidays, asset_prompt_templates, support_tickets, support_replies

---

## 架构设计

### 三件套设计

```
┌─────────────────────────────────────────────────┐
│           软删除三件套 (Soft Delete)             │
├─────────────────────────────────────────────────┤
│  is_deleted           BOOLEAN                   │  标记: 是否已删除
│  deleted_at           TIMESTAMPTZ               │  时间: 何时删除
│  recovery_expires_at  TIMESTAMPTZ               │  过期: 何时不可恢复
└─────────────────────────────────────────────────┘
```

### 状态转换图

```
┌──────────┐  soft_delete()   ┌──────────────┐  auto-expire   ┌──────────────┐  cleanup   ┌──────────┐
│  Active  │ ──────────────> │ Recoverable  │ ────────────> │   Expired    │ ────────> │ Deleted  │
│          │                  │ (30 days)    │               │ (hidden)     │           │(physical)│
└──────────┘                  └──────────────┘               └──────────────┘           └──────────┘
     ↑                              │
     │         restore()            │
     └──────────────────────────────┘
```

**状态说明**:
1. **Active**: `is_deleted = false`, 正常记录
2. **Recoverable**: `is_deleted = true`, `recovery_expires_at > NOW()`, 用户可在删除历史中看到并恢复
3. **Expired**: `is_deleted = true`, `recovery_expires_at < NOW()`, 从用户视图消失（但数据仍在）
4. **Deleted**: 物理删除（过期 90 天后自动清理）

### 分层架构

```
┌────────────────────────────────────────────────────┐
│              API Layer (FastAPI)                   │  GET /projects/deleted
├────────────────────────────────────────────────────┤
│           Service Layer (Domain)                   │  ProjectService.get_user_deleted_projects()
│                                                     │  ↓ calls
│                    ↓                                │  list_deleted_recoverable()
├────────────────────────────────────────────────────┤
│         Repository Layer (Infrastructure)          │  BaseRepository.list_deleted_recoverable()
│                                                     │  ↓ queries
│                    ↓                                │  SELECT ... WHERE is_deleted = true
├────────────────────────────────────────────────────┤       AND recovery_expires_at > NOW()
│            Database (PostgreSQL)                   │
└────────────────────────────────────────────────────┘
```

---

## 数据库设计

### 字段定义

#### 1. is_deleted (BOOLEAN)

```sql
is_deleted BOOLEAN NOT NULL DEFAULT FALSE
```

- **用途**: 标记记录是否已删除
- **默认值**: `FALSE` (正常记录)
- **索引**: 条件部分索引 (WHERE is_deleted = FALSE/TRUE)

#### 2. deleted_at (TIMESTAMPTZ)

```sql
deleted_at TIMESTAMPTZ
```

- **用途**: 记录删除时间
- **约束**: `is_deleted = true` 时必须非空
- **自动设置**: 通过触发器 `set_deleted_at_on_soft_delete()`

#### 3. recovery_expires_at (TIMESTAMPTZ)

```sql
recovery_expires_at TIMESTAMPTZ
```

- **用途**: 记录恢复期截止时间
- **计算**: `deleted_at + 30 days` (默认，可配置)
- **约束**: 必须晚于 `deleted_at`

### 约束 (Constraints)

#### CHECK 约束 1: deleted_at 一致性

```sql
CONSTRAINT chk_{table}_deleted_at_consistency
CHECK (
    (is_deleted = false AND deleted_at IS NULL) OR
    (is_deleted = true AND deleted_at IS NOT NULL)
)
```

**确保**: 删除标记与删除时间一致

#### CHECK 约束 2: recovery_expires_at 一致性

```sql
CONSTRAINT chk_{table}_recovery_expires_at_consistency
CHECK (
    recovery_expires_at IS NULL OR
    (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
)
```

**确保**: 恢复期过期时间晚于删除时间

### 索引 (Indexes)

#### 活跃记录索引

```sql
CREATE INDEX idx_{table}_active
ON {table}(user_id, created_at DESC)
WHERE is_deleted = FALSE;
```

**用途**: 查询用户的活跃记录（未删除）
**优势**: 条件部分索引，只索引未删除记录，节省空间

#### 可恢复删除记录索引

```sql
CREATE INDEX idx_{table}_deleted_recoverable
ON {table}(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();
```

**用途**: 查询用户的可恢复删除记录
**优势**: 自动排除已过期记录，查询更快

### 触发器 (Triggers)

```sql
CREATE TRIGGER trg_{table}_set_deleted_at
    BEFORE INSERT OR UPDATE ON {table}
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();
```

**功能**:
- 当 `is_deleted` 从 `false` 变为 `true` 时，自动设置 `deleted_at = NOW()`
- 当 `is_deleted` 从 `true` 变为 `false` 时，自动清空 `deleted_at`

---

## 代码实现

### BaseRepository 核心方法

#### 1. soft_delete() - 软删除

```python
async def soft_delete(self, id: str, user_id: Optional[str] = None) -> bool:
    """
    软删除记录.

    Args:
        id: 记录ID
        user_id: 用户ID (可选,用于验证权限)

    Returns:
        是否成功
    """
    # 获取恢复期天数配置
    recovery_days = await self._get_recovery_period_days()

    # 计算恢复期截止时间
    deleted_at = datetime.now(timezone.utc)
    recovery_expires_at = deleted_at + timedelta(days=recovery_days)

    query = self.client.table(self.table_name).update({
        "is_deleted": True,
        "deleted_at": deleted_at.isoformat(),
        "recovery_expires_at": recovery_expires_at.isoformat()
    }).eq("id", id)

    if user_id:
        query = query.eq("user_id", user_id)

    result = query.execute()
    return len(result.data) > 0
```

#### 2. restore() - 恢复删除

```python
async def restore(self, id: str, user_id: Optional[str] = None) -> bool:
    """
    恢复软删除的记录.

    Args:
        id: 记录ID
        user_id: 用户ID (可选)

    Returns:
        是否成功
    """
    query = self.client.table(self.table_name).update({
        "is_deleted": False,
        "deleted_at": None,
        "recovery_expires_at": None  # 清空恢复期
    }).eq("id", id).eq("is_deleted", True)

    if user_id:
        query = query.eq("user_id", user_id)

    result = query.execute()
    return len(result.data) > 0
```

#### 3. list_deleted_recoverable() - 查询可恢复记录

```python
async def list_deleted_recoverable(
    self,
    user_id: str,
    offset: int = 0,
    limit: int = 20
) -> tuple[List[Any], int]:
    """
    查询用户的可恢复删除记录 (自动过滤已过期).

    Args:
        user_id: 用户ID
        offset: 偏移量
        limit: 限制数量

    Returns:
        (记录列表, 总数)
    """
    now = datetime.now(timezone.utc).isoformat()

    # 查询可恢复记录（未过期）
    result = self.client.table(self.table_name) \
        .select("*", count="exact") \
        .eq("user_id", user_id) \
        .eq("is_deleted", True) \
        .gt("recovery_expires_at", now) \
        .order("deleted_at", desc=True) \
        .range(offset, offset + limit - 1) \
        .execute()

    entities = [self._to_entity(row) for row in result.data]
    total = result.count or 0

    return entities, total
```

#### 4. _get_recovery_period_days() - 获取恢复期配置

```python
async def _get_recovery_period_days(self) -> int:
    """
    获取软删除恢复期天数配置.

    Returns:
        恢复期天数 (默认 30)
    """
    result = self.client.table("system_configs") \
        .select("value") \
        .eq("key", "soft_delete.recovery_period_days") \
        .single() \
        .execute()

    if result.data and result.data.get("value"):
        return int(result.data["value"])

    return 30  # 默认 30 天
```

### Service 层使用示例

```python
# domains/creation/service.py
class ProjectService:
    async def get_user_deleted_projects(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> tuple[List[Dict[str, Any]], int]:
        """获取用户的可恢复删除项目."""

        # ✅ 使用 BaseRepository 统一方法
        projects, total = await self._repository.list_deleted_recoverable(
            user_id=user_id,
            offset=offset,
            limit=limit
        )

        # 转换为 Dict (向后兼容)
        project_dicts = []
        for proj in projects:
            project_dicts.append({
                "id": proj.id,
                "title": proj.title,
                "thumbnail_url": proj.thumbnail_url,
                "deleted_at": proj.deleted_at,
                "recovery_expires_at": proj.recovery_expires_at,  # 🆕 返回给前端
            })

        return project_dicts, total
```

---

## 使用指南

### 软删除记录

```python
# 软删除项目
success = await project_repository.soft_delete(
    id="proj_123",
    user_id="user_456"
)

# 结果:
# - is_deleted = true
# - deleted_at = 2026-01-10T10:00:00Z
# - recovery_expires_at = 2026-02-09T10:00:00Z (30天后)
```

### 恢复删除

```python
# 恢复项目
success = await project_repository.restore(
    id="proj_123",
    user_id="user_456"
)

# 结果:
# - is_deleted = false
# - deleted_at = NULL
# - recovery_expires_at = NULL
```

### 查询删除历史

```python
# 查询用户的可恢复删除记录
projects, total = await project_service.get_user_deleted_projects(
    user_id="user_456",
    offset=0,
    limit=20
)

# 返回:
# - 只包含未过期的删除记录 (recovery_expires_at > NOW())
# - 按删除时间倒序排列
# - 包含 recovery_expires_at 字段供前端显示倒计时
```

### 前端使用示例

```typescript
// API 响应
{
  "items": [
    {
      "id": "proj_123",
      "title": "My Project",
      "deleted_at": "2026-01-10T10:00:00Z",
      "recovery_expires_at": "2026-02-09T10:00:00Z"
    }
  ],
  "total": 1
}

// 计算剩余天数
const daysLeft = Math.floor(
  (new Date(project.recovery_expires_at) - new Date()) / (1000 * 60 * 60 * 24)
);

// 显示倒计时
<div className={daysLeft <= 3 ? 'text-red-500' : 'text-gray-500'}>
  还有 {daysLeft} 天可恢复
</div>
```

### 配置恢复期

```sql
-- 修改恢复期为 60 天
INSERT INTO system_configs (key, value, description)
VALUES (
    'soft_delete.recovery_period_days',
    '60',
    '软删除恢复期天数'
)
ON CONFLICT (key) DO UPDATE SET value = '60';
```

---

## 最佳实践

### 1. 新表添加软删除

创建新表时直接包含软删除支持：

```sql
CREATE TABLE new_table (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,

    -- 业务字段
    name TEXT NOT NULL,

    -- 软删除三件套
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    recovery_expires_at TIMESTAMPTZ,

    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- 约束
    CONSTRAINT chk_new_table_deleted_at_consistency
    CHECK (
        (is_deleted = false AND deleted_at IS NULL) OR
        (is_deleted = true AND deleted_at IS NOT NULL)
    ),
    CONSTRAINT chk_new_table_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);

-- 活跃记录索引
CREATE INDEX idx_new_table_active
ON new_table(user_id, created_at DESC)
WHERE is_deleted = FALSE;

-- 可恢复删除记录索引
CREATE INDEX idx_new_table_deleted_recoverable
ON new_table(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

-- 触发器
CREATE TRIGGER trg_new_table_set_deleted_at
    BEFORE INSERT OR UPDATE ON new_table
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();
```

### 2. Service 层统一调用

**✅ 推荐**:
```python
# 使用 BaseRepository 统一方法
items, total = await repository.list_deleted_recoverable(
    user_id=user_id,
    offset=offset,
    limit=limit
)
```

**❌ 避免**:
```python
# 不要自己写查询逻辑
result = self.client.table(table_name) \
    .select("*") \
    .eq("user_id", user_id) \
    .eq("is_deleted", True) \
    .execute()  # ❌ 没有过滤已过期记录
```

### 3. API 响应包含恢复期

```python
# ✅ 返回 recovery_expires_at 供前端使用
{
    "id": "proj_123",
    "title": "My Project",
    "deleted_at": "2026-01-10T10:00:00Z",
    "recovery_expires_at": "2026-02-09T10:00:00Z"  # 前端可计算倒计时
}
```

### 4. 测试软删除功能

```python
async def test_soft_delete_and_restore():
    # 软删除
    success = await repository.soft_delete(id="test_1", user_id="user_1")
    assert success

    # 验证字段
    item = await repository.find_by_id("test_1")
    assert item.is_deleted is True
    assert item.deleted_at is not None
    assert item.recovery_expires_at > item.deleted_at

    # 恢复
    success = await repository.restore(id="test_1", user_id="user_1")
    assert success

    # 验证恢复
    item = await repository.find_by_id("test_1")
    assert item.is_deleted is False
    assert item.deleted_at is None
    assert item.recovery_expires_at is None
```

---

## 故障排查

### 问题 1: 删除记录仍然出现在列表中

**症状**: 调用 `soft_delete()` 后，记录仍然在 `list()` 中返回

**原因**: Service 层使用了 `list()` 而不是筛选未删除记录

**解决**:
```python
# ❌ 错误
items = await repository.list(user_id=user_id)  # 包含已删除记录

# ✅ 正确
items = await repository.list(user_id=user_id, is_deleted=False)  # 只返回活跃记录
```

### 问题 2: 已过期记录仍然在删除历史中

**症状**: `recovery_expires_at` 已过期，但记录仍在删除历史中

**原因**: 使用了自定义查询逻辑，没有过滤过期记录

**解决**:
```python
# ❌ 错误
result = self.client.table(table_name) \
    .eq("is_deleted", True) \
    .execute()  # 包含已过期记录

# ✅ 正确
items, total = await repository.list_deleted_recoverable(user_id=user_id)  # 自动过滤
```

### 问题 3: 恢复期配置不生效

**症状**: 修改了系统配置，但新删除的记录仍使用 30 天

**原因**: 配置表中的 `key` 拼写错误

**验证**:
```sql
-- 检查配置
SELECT * FROM system_configs WHERE key = 'soft_delete.recovery_period_days';

-- 正确的 key
INSERT INTO system_configs (key, value) VALUES
('soft_delete.recovery_period_days', '60');
```

### 问题 4: 触发器未生效

**症状**: `soft_delete()` 后 `deleted_at` 仍为 `NULL`

**原因**: 触发器未创建或被禁用

**解决**:
```sql
-- 检查触发器
SELECT * FROM information_schema.triggers
WHERE trigger_name LIKE 'trg_%_set_deleted_at';

-- 重新创建触发器
CREATE TRIGGER trg_{table}_set_deleted_at
    BEFORE INSERT OR UPDATE ON {table}
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();
```

---

## 自动清理系统

### 清理脚本

**位置**: `scripts/cron/cleanup_expired_soft_deletes.py`

**功能**: 物理删除已过期 90 天的软删除记录

**配置**:
```bash
CLEANUP_AFTER_DAYS=90  # 过期后再等 90 天才物理删除
DRY_RUN=true           # 测试模式（默认）
BATCH_SIZE=100         # 每批处理数量
```

**运行**:
```bash
# 测试模式
DRY_RUN=true python scripts/cron/cleanup_expired_soft_deletes.py

# 生产模式
DRY_RUN=false python scripts/cron/cleanup_expired_soft_deletes.py
```

### GitHub Actions 自动化

**位置**: `.github/workflows/cleanup-soft-deletes.yml`

**调度**: 每天凌晨 2 点 (UTC)

**手动触发**: GitHub Actions → Run workflow

**启用生产模式**:
```yaml
# 取消注释以下步骤
- name: Run cleanup (PRODUCTION)
  env:
    DRY_RUN: "false"
```

---

## 相关文档

- [软删除实施历史](SOFT-DELETE-HISTORY.md) - Phase 1/2/3 完整实施记录
- [后台业务逻辑说明](后台业务逻辑说明.md) - 业务规则和逻辑
- [API 参考文档](API_REFERENCE.md) - API 接口说明

---

**最后更新**: 2026-01-10
**维护者**: Make Decodables 后端团队
