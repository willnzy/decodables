# Make Decodables 系统优化执行方案

> **创建时间**: 2026-01-10
> **版本**: v1.0
> **状态**: 待执行

---

## 执行摘要

经过深度分析，发现 9 个关键问题，分为 P0/P1/P2 三个优先级。总工作量 **45-63 小时**（7-10 工作日）。

### 核心发现

| 问题 | 优先级 | 影响 | 工作量 |
|------|--------|------|--------|
| 1. field_mappings.py 覆盖不完整 (6/60 表) | P0 | 代码一致性 | 8-10h |
| 2. Repository 接口缺失 (15个实现无接口) | P0 | DDD 架构 | 6-8h |
| 3. Marketplace 状态转换无约束 | P0 | 数据一致性 | 2.5h |
| 4. 软删除覆盖不完整 (24/60 表) | P1 | 数据恢复 | 4-5h |
| 5. 复合索引缺失 | P1 | 查询性能 | 1.5-2h |
| 6. 缓存策略未完全覆盖 | P1 | 系统负载 | 3.5-4.5h |
| 7. RPC 函数数量不足 | P2 | N+1 查询 | 2-3h |
| 8. 乐观锁机制缺失 | P2 | 并发控制 | 2-3h |
| 9. Webhook 状态机缺失 | P2 | 重复处理 | 2-3h |

---

## P0 执行计划 (立即执行)

### 任务 1: 补充 field_mappings.py ⭐

**问题**: 只有 6/60 表有映射定义，导致 Repository 硬编码字段名

**影响文件**:
- `infrastructure/repositories/field_mappings.py` (核心)
- 26 个 `infrastructure/repositories/*_repository.py` 文件

**执行步骤**:

1. **生成映射骨架** (1h) - 使用 `scripts/tools/generate_field_mappings.py`
2. **人工审查** (2-3h) - 检查特殊映射 (如 user_id vs buyer_id/seller_id)
3. **更新 Repository** (4-6h) - 替换硬编码为 `map_db_to_domain()`
4. **测试验证** (1h) - 运行 `pytest tests/infrastructure/repositories/`

**验收标准**:
- ✅ 所有 60 张表都有对应映射定义
- ✅ 所有 Repository 使用 `map_db_to_domain/map_domain_to_db`
- ✅ 测试覆盖率 ≥ 70%

---

### 任务 2: 补充 Repository 接口 ⭐

**问题**: 26 个实现 vs 11 个接口，15 个实现绕过 DDD 依赖倒置

**缺失接口的 Repository**:
- analytics_repository → IAnalyticsRepository
- support_repository → ISupportRepository
- notification_repository → INotificationRepository
- campaign_repository → ICampaignRepository
- themes_repository → IThemesRepository
- 等 10+ 个

**执行步骤**:

1. **分类 Repository** (1h) - 核心业务 vs 基础设施
2. **定义接口** (3-4h) - 在 `domains/*/repository.py` 中添加接口
3. **更新实现** (2-3h) - 实现类继承接口

**验收标准**:
- ✅ 所有核心业务 Repository 有接口定义
- ✅ 所有实现类继承对应接口
- ✅ domains 层不依赖 infrastructure 层

---

### 任务 3: Marketplace 状态转换约束 ⭐

**问题**: rejected → approved 转换无阻止，违反业务规则

**执行步骤**:

1. **创建迁移** (0.5h) - `migrations/v4/001_add_moderation_status_constraint.sql`
2. **更新代码** (1h) - `domains/marketplace/service.py` 添加验证
3. **测试** (1h) - 验证约束生效

**SQL**:
```sql
CREATE OR REPLACE FUNCTION check_marketplace_moderation_transition()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.moderation_status = 'rejected' AND NEW.moderation_status = 'approved' THEN
        RAISE EXCEPTION 'Cannot approve a rejected listing';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

---

## P1 执行计划 (1-2周内)

### 任务 4: 补充软删除支持

**需补充的表** (12张):
- generation_tasks, user_generations ✅ (用户数据)
- experiments, experiment_assignments ✅ (A/B 测试)
- user_events ✅ (行为数据)
- activity_logs, content_reports, user_discounts (次要)

**迁移文件**: `migrations/v4/002_add_soft_delete_to_user_data_tables.sql`

---

### 任务 5: 补充复合索引

**高频查询索引**:
```sql
-- 市场浏览
CREATE INDEX idx_marketplace_listings_browse
ON marketplace_listings(moderation_status, is_visible, created_at DESC)
WHERE is_deleted = false;

-- 生成任务状态
CREATE INDEX idx_generation_tasks_user_status
ON generation_tasks(user_id, status, created_at DESC);

-- 实验分组查询
CREATE INDEX idx_experiment_assignments_user_exp
ON experiment_assignments(user_id, experiment_id, is_active);
```

**迁移文件**: `migrations/v4/003_add_composite_indexes.sql`

---

### 任务 6: 缓存策略补充

**补充缓存场景**:

| 数据 | TTL | 失效时机 |
|------|-----|----------|
| UserProfile | 5分钟 | 更新时主动失效 |
| SystemConfig | 1小时 | 管理员更新 |
| 热门商品 | 10分钟 | 新商品发布 |
| 用户积分 | 1分钟 | 积分变动 |

**执行步骤**:
1. 补充 `infrastructure/cache/keys.py` 缓存键定义
2. 在 Repository 中集成缓存 (get → 查缓存 → 查DB → 写缓存)
3. 添加热点数据预热定时任务

---

## P2 执行计划 (按需执行)

### 任务 7: RPC 函数补充

**Dashboard 统计**:
```sql
CREATE FUNCTION get_user_dashboard_stats(p_user_id TEXT)
RETURNS TABLE(project_count INT, asset_count INT, credits_total INT)
```

**市场热门商品**:
```sql
CREATE FUNCTION get_marketplace_trending(p_limit INT, p_offset INT)
RETURNS TABLE(...) -- 聚合 listings + purchases + reviews
```

---

### 任务 8: 乐观锁机制

```sql
ALTER TABLE projects ADD COLUMN version INTEGER DEFAULT 1;

CREATE FUNCTION update_project_with_version(
    p_project_id UUID,
    p_expected_version INT,
    ...
) RETURNS BOOLEAN
```

---

### 任务 9: Webhook 状态机

```sql
ALTER TABLE stripe_webhook_events ADD COLUMN processing_status TEXT
CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed'));
```

---

## 验证方案

### 架构验证
```bash
# 检查 domains 层不依赖 infrastructure
grep -r "from infrastructure" decodables/domains/
# 预期: 无结果
```

### 数据库验证
```sql
-- 检查软删除字段完整性
SELECT table_name,
       COUNT(CASE WHEN column_name = 'is_deleted' THEN 1 END) as has_soft_delete
FROM information_schema.columns
WHERE table_name IN ('generation_tasks', 'user_generations', ...)
GROUP BY table_name;
```

### 性能验证
```python
# 缓存命中率测试
cold_time = await test_cold_query()  # 缓存未命中
hot_time = await test_hot_query()    # 缓存命中
speedup = cold_time / hot_time  # 预期 10x+
```

---

## 执行顺序

**Week 1 (P0)**:
- Day 1-2: 任务 1 (field_mappings)
- Day 3: 任务 2 (Repository 接口)
- Day 4: 任务 3 (Marketplace 约束) + 测试验证

**Week 2 (P1)**:
- Day 1: 任务 4 (软删除)
- Day 2: 任务 5 (索引) + 任务 6 (缓存)
- Day 3-4: 测试验证

**Week 3+ (P2)**:
- 按需执行任务 7/8/9

---

## 风险控制

**高风险操作**:
- ✅ 数据库迁移 → 在维护窗口执行，使用事务
- ✅ 索引创建 → 使用 `CONCURRENTLY` 避免锁表
- ✅ Repository 重构 → 逐模块进行，每次 commit

**回滚策略**:
- 所有迁移文件包含 `BEGIN...COMMIT`
- 保留旧代码注释，便于回滚
- 缓存修改先在测试环境验证

---

## 关键文件清单

| 文件 | 优先级 | 原因 |
|------|--------|------|
| `infrastructure/repositories/field_mappings.py` | P0 | 需补充 54 个表映射 |
| `infrastructure/repositories/base_repository.py` | P0 | 所有 Repository 的基类 |
| `migrations/v2/refactored_schema_v2.sql` | P0 | DDL 主文件 |
| `domains/*/repository.py` (11个) | P0 | 需补充接口定义 |
| `infrastructure/cache/keys.py` | P1 | 缓存键定义 |
| `migrations/v4/*.sql` (新建) | P0-P2 | 增量迁移文件 |

---

**下一步**: 执行 P0 任务 1 - 补充 field_mappings.py
