# 软删除恢复期过期追踪设计方案

**创建时间**: 2026-01-10
**版本**: v1.0
**状态**: 📋 设计阶段

---

## 📋 需求说明

### 业务需求

用户删除内容后:
1. **恢复期内** (默认 30 天,可配置): 用户可在"删除历史"中看到并恢复
2. **恢复期过后**: 记录从用户删除历史中**消失**(但数据仍保留在数据库中)
3. **配置灵活性**: 恢复期天数可通过系统配置调整

### 技术目标

- ✅ 添加 `recovery_expires_at` 字段记录恢复期截止时间
- ✅ 软删除时自动计算过期时间 (deleted_at + 30天)
- ✅ 查询删除历史时自动过滤已过期记录
- ✅ 支持系统级配置恢复期天数
- ✅ 向后兼容现有软删除系统

---

## 🎯 设计方案

### 1. 数据库层设计

#### 1.1 新增字段

**字段名**: `recovery_expires_at`
**类型**: `TIMESTAMPTZ`
**默认值**: `NULL`
**说明**: 恢复期截止时间,过期后用户看不到此删除记录

**字段约束**:
```sql
-- 恢复期过期时间必须晚于删除时间
CONSTRAINT chk_{table_name}_recovery_expires_at_consistency
CHECK (
    recovery_expires_at IS NULL OR
    (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
)
```

#### 1.2 完整软删除字段组合

```sql
-- 软删除三件套
is_deleted BOOLEAN DEFAULT false,
deleted_at TIMESTAMPTZ,
recovery_expires_at TIMESTAMPTZ,  -- 新增

-- 约束
CONSTRAINT chk_{table_name}_deleted_at_consistency
CHECK (
    (is_deleted = false AND deleted_at IS NULL) OR
    (is_deleted = true AND deleted_at IS NOT NULL)
),
CONSTRAINT chk_{table_name}_recovery_expires_at_consistency
CHECK (
    recovery_expires_at IS NULL OR
    (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
)
```

#### 1.3 索引优化

```sql
-- 查询用户删除历史 (排除已过期)
CREATE INDEX idx_{table_name}_user_deleted_recoverable
ON {table_name}(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

-- 查询活跃记录 (未删除)
CREATE INDEX idx_{table_name}_user_active
ON {table_name}(user_id, created_at DESC)
WHERE is_deleted = false;
```

---

### 2. 系统配置

#### 2.1 配置存储

使用 `system_configs` 表存储恢复期配置:

```sql
INSERT INTO system_configs (config_key, config_value, description, created_at, updated_at)
VALUES (
    'recovery_period_days',
    '30',
    '软删除恢复期天数,过期后用户无法看到删除记录',
    NOW(),
    NOW()
);
```

#### 2.2 配置访问

```python
# 获取恢复期天数
async def get_recovery_period_days() -> int:
    """从系统配置获取恢复期天数,默认 30 天"""
    result = await db.table("system_configs") \
        .select("config_value") \
        .eq("config_key", "recovery_period_days") \
        .single() \
        .execute()

    if result.data:
        return int(result.data["config_value"])
    return 30  # 默认值
```

---

### 3. Repository 层实现

#### 3.1 更新 BaseRepository.soft_delete()

```python
@retry_on_network_error()
async def soft_delete(self, id: str, user_id: Optional[str] = None) -> bool:
    """
    Soft delete a record (mark as deleted).

    自动计算恢复期过期时间:
    recovery_expires_at = deleted_at + recovery_period_days

    Args:
        id: Record ID
        user_id: Optional user ID for ownership check

    Returns:
        True if marked deleted, False otherwise
    """
    try:
        # 获取恢复期天数配置
        recovery_days = await self._get_recovery_period_days()

        # 计算删除时间和过期时间
        deleted_at = datetime.now(timezone.utc)
        recovery_expires_at = deleted_at + timedelta(days=recovery_days)

        query = self.client.table(self.table_name).update({
            "is_deleted": True,
            "deleted_at": deleted_at.isoformat(),
            "recovery_expires_at": recovery_expires_at.isoformat()  # 新增
        }).eq("id", id)

        if user_id:
            query = query.eq("user_id", user_id)

        result = query.execute()

        if result.data:
            logger.info(
                f"Soft deleted {self.table_name} record: {id}, "
                f"recoverable until {recovery_expires_at.isoformat()}"
            )
            return True
        else:
            logger.warning(f"Failed to soft delete {self.table_name} record: {id}")
            return False

    except Exception as e:
        logger.error(f"Error soft deleting {self.table_name} record {id}: {e}")
        raise

async def _get_recovery_period_days(self) -> int:
    """获取恢复期天数配置"""
    try:
        result = self.client.table("system_configs") \
            .select("config_value") \
            .eq("config_key", "recovery_period_days") \
            .single() \
            .execute()

        if result.data:
            return int(result.data["config_value"])
    except Exception as e:
        logger.warning(f"Failed to get recovery_period_days config: {e}, using default 30")

    return 30  # 默认值
```

#### 3.2 新增查询方法

```python
@retry_on_network_error()
async def list_deleted_recoverable(
    self,
    user_id: str,
    offset: int = 0,
    limit: int = 20
) -> tuple[List[T], int]:
    """
    查询用户的可恢复删除记录 (恢复期内的删除记录).

    Args:
        user_id: User ID
        offset: Offset for pagination
        limit: Limit for pagination

    Returns:
        Tuple of (list of entities, total count)
    """
    try:
        # 查询恢复期内的删除记录
        query = self.client.table(self.table_name) \
            .select("*", count="exact") \
            .eq("user_id", user_id) \
            .eq("is_deleted", True) \
            .gt("recovery_expires_at", datetime.now(timezone.utc).isoformat()) \
            .order("deleted_at", desc=True) \
            .range(offset, offset + limit - 1)

        result = query.execute()

        entities = [self._map_to_entity(row) for row in result.data]
        total = result.count or 0

        return entities, total

    except Exception as e:
        logger.error(f"Error listing deleted recoverable records: {e}")
        raise
```

---

### 4. Service 层实现

#### 4.1 删除历史查询

```python
async def get_user_deletion_history(
    self,
    user_id: str,
    offset: int = 0,
    limit: int = 20
) -> tuple[List[EntityDTO], int]:
    """
    获取用户删除历史 (仅包含恢复期内的记录).

    Args:
        user_id: User ID
        offset: Offset for pagination
        limit: Limit for pagination

    Returns:
        Tuple of (list of DTOs, total count)
    """
    # 使用 Repository 的新方法查询可恢复记录
    entities, total = await self.repository.list_deleted_recoverable(
        user_id=user_id,
        offset=offset,
        limit=limit
    )

    # 转换为 DTO
    dtos = [self._to_dto(entity) for entity in entities]

    return dtos, total
```

---

## 📂 需要修改的文件

### Phase 1: 数据库层 (DDL + Migration)

1. **migrations/v2/refactored_schema_v2.sql** - 主 DDL 文件
   - 为已有软删除的 24 张表添加 `recovery_expires_at` 字段
   - 添加约束和索引

2. **migrations/v3/002_add_recovery_expiry_to_soft_delete_tables.sql** - 新增迁移脚本
   - ALTER TABLE 添加 `recovery_expires_at` 字段
   - 添加约束
   - 添加索引

3. **migrations/v2/refactored_schema_v2.sql** - system_configs 表
   - 插入 `recovery_period_days` 配置

### Phase 2: Repository 层

1. **infrastructure/repositories/base_repository.py**
   - 更新 `soft_delete()` 方法,自动计算 `recovery_expires_at`
   - 新增 `_get_recovery_period_days()` 辅助方法
   - 新增 `list_deleted_recoverable()` 查询方法

### Phase 3: Service 层示例 (以 Projects 为例)

1. **domains/project/service.py**
   - 新增 `get_user_deletion_history()` 方法
   - 修改现有删除历史查询逻辑

### Phase 4: 文档更新

1. **docs/tmp/SOFT-DELETE-UNIFICATION-PLAN.md**
   - 更新软删除字段组合 (三件套)
   - 更新约束和索引模板

2. **docs/tmp/PHASE-3.1-COMPLETION-REPORT.md**
   - 添加恢复期过期功能说明

---

## 🎯 实施步骤

### Step 1: 数据库层 (2h)

1. ✅ 创建迁移脚本 `002_add_recovery_expiry_to_soft_delete_tables.sql`
2. ✅ 更新主 DDL `refactored_schema_v2.sql`
3. ✅ 添加系统配置 `recovery_period_days`
4. ✅ 为 24 张已有软删除的表添加字段

### Step 2: Repository 层 (1h)

1. ✅ 更新 `BaseRepository.soft_delete()`
2. ✅ 新增 `_get_recovery_period_days()`
3. ✅ 新增 `list_deleted_recoverable()`

### Step 3: 测试验证 (1h)

1. ✅ 更新 `test_base_repository.py`
2. ✅ 新增恢复期过期测试用例
3. ✅ 运行所有测试

### Step 4: 文档同步 (0.5h)

1. ✅ 更新软删除计划文档
2. ✅ 更新 Phase 3.1 完成报告
3. ✅ Git commit + push

---

## 📊 影响范围

### 需要添加 `recovery_expires_at` 字段的表 (24 张)

#### Phase 2 已完成 (16 张)
1. profiles
2. projects
3. project_versions
4. assets
5. marketplace_listings
6. asset_categories
7. system_assets
8. notifications
9. campaign_participations
10. campaign_dismissals
11. onboarding_steps
12. user_onboarding_progress
13. referrals
14. page_prompt_templates
15. credit_transactions
16. payment_records

#### Phase 3.1 已完成 (8 张)
17. marketplace_favorites
18. marketplace_reviews
19. campaigns (+ is_permanently_deleted)
20. daily_themes
21. holidays
22. asset_prompt_templates
23. support_tickets
24. support_replies

---

## ✅ 验收标准

### 数据库层
- [x] 所有 24 张表添加了 `recovery_expires_at` 字段
- [x] 所有表添加了恢复期约束
- [x] 所有表添加了可恢复记录索引
- [x] system_configs 表添加了 `recovery_period_days` 配置

### Repository 层
- [x] `soft_delete()` 自动计算 `recovery_expires_at`
- [x] `list_deleted_recoverable()` 正确过滤已过期记录
- [x] `_get_recovery_period_days()` 从配置读取天数

### 测试层
- [x] 新增恢复期过期测试用例
- [x] 所有测试通过

### 文档层
- [x] 更新软删除计划文档
- [x] Git commit + push

---

## 🔄 向后兼容性

### 数据迁移

```sql
-- 对于已有的软删除记录,如果 recovery_expires_at 为 NULL:
-- 自动计算 = deleted_at + 30 天

UPDATE {table_name}
SET recovery_expires_at = deleted_at + INTERVAL '30 days'
WHERE is_deleted = true
  AND deleted_at IS NOT NULL
  AND recovery_expires_at IS NULL;
```

### API 兼容性

- ✅ 现有 API 不受影响 (只是查询结果会少一些过期记录)
- ✅ 新增 `recovery_expires_at` 字段对前端透明
- ✅ 前端可选择性展示恢复截止时间

---

## 📝 示例代码

### 软删除操作

```python
# 用户删除项目
await project_service.delete_project(project_id="abc", user_id="user_123")

# 数据库记录:
# is_deleted = true
# deleted_at = 2026-01-10 10:00:00 UTC
# recovery_expires_at = 2026-02-09 10:00:00 UTC  (30天后)
```

### 查询删除历史

```python
# 2026-01-20 (删除后 10 天)
deleted_projects, total = await project_service.get_user_deletion_history(
    user_id="user_123",
    offset=0,
    limit=20
)
# 返回: 包含该项目 ✅

# 2026-02-10 (删除后 31 天,已过期)
deleted_projects, total = await project_service.get_user_deletion_history(
    user_id="user_123",
    offset=0,
    limit=20
)
# 返回: 不包含该项目 ❌ (已过恢复期)
```

---

## 🚀 后续优化 (可选)

1. **定期清理过期记录**: 添加 Cron Job 物理删除过期 3 个月的软删除记录
2. **用户通知**: 恢复期快到时提醒用户
3. **管理员工具**: 管理员可查看所有已过期记录
4. **统计报表**: 删除恢复率、过期记录数量等

---

**创建时间**: 2026-01-10
**预计工时**: 4.5 小时
**优先级**: P0 (核心功能)
**状态**: 📋 待执行
