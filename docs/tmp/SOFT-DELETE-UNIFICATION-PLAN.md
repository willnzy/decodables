# 全库表软删除统一化计划

**创建时间**: 2026-01-10
**更新时间**: 2026-01-10
**目标**: 将所有数据库表统一使用软删除机制，禁用硬删除
**范围**: 60 张表全面审查

---

## 🎯 执行摘要

### 当前进度

| 指标 | 数值 | 说明 |
|------|------|------|
| **总表数** | 60 | 数据库所有表 |
| **已有软删除** | 16 (26.7%) | 已实现软删除机制 |
| **需要添加** | 44 (73.3%) | 本计划要处理的表 |
| **预计工作量** | 23-32h | 3-4 个工作日 |

### 分类概览

| 类别 | 表数量 | 优先级 | 策略 | 状态 |
|------|--------|--------|------|------|
| ✅ 已有软删除 | 16 | - | 保持现状 | 完成 |
| ❌ 核心业务表 (P0) | 8 | Critical | **必须添加软删除** | 待执行 |
| ❌ 系统配置表 (P1) | 15 | High | **必须添加软删除** | 待执行 |
| ❌ 统计聚合表 (P2) | 8 | Medium | **必须添加软删除** | 待执行 |
| ⚠️ 特殊处理表 (P1) | 13 | High | **需要讨论** | 待决策 |

### 关键决策点

**🔴 重要**: 用户需要确认以下策略:

1. **类别 5 (特殊处理表)**: 原定为 Append-Only 的日志表是否添加软删除?
   - **建议**: 添加软删除以支持 GDPR 合规和数据归档
   - **影响**: 13 张表 (api_logs, ai_call_logs, activity_logs 等)
   - **理由**: 允许清理测试数据、错误日志和归档旧记录

2. **事务表**: 以下表**绝对不添加软删除** (财务审计要求):
   - ✅ credit_transactions (已有软删除，但不建议使用)
   - ❌ payment_records (已有软删除，建议移除)

---

## 📊 当前状态分析

### 总体统计

| 指标 | 数量 | 百分比 |
|------|------|--------|
| **总表数** | 60 | 100% |
| **已有软删除** | 16 | 26.7% |
| **需要添加软删除** | 44 | 73.3% |

### 已支持软删除的表 (16 张)

**✅ 核心业务表 (9 张)**:
| 表名 | 字段 | 状态 |
|------|------|------|
| `profiles` | is_deleted, deleted_at | ✅ 已实现 |
| `credit_transactions` | is_deleted, deleted_at | ✅ 已实现 |
| `projects` | is_deleted, deleted_at | ✅ 已实现 |
| `asset_categories` | is_deleted, deleted_at | ✅ 已实现 |
| `system_assets` | is_deleted, deleted_at | ✅ 已实现 |
| `marketplace_listings` | is_deleted, deleted_at | ✅ 已实现 |
| `referrals` | is_deleted, deleted_at | ✅ 已实现 |
| `project_versions` | is_deleted, deleted_at | ✅ 已实现 |
| `assets` | is_deleted, deleted_at | ✅ 已实现 |

**✅ 通知与引导 (4 张)**:
| 表名 | 字段 | 状态 |
|------|------|------|
| `campaign_participations` | is_deleted, deleted_at | ✅ 已实现 |
| `campaign_dismissals` | is_deleted, deleted_at | ✅ 已实现 |
| `notifications` | is_deleted, deleted_at | ✅ 已实现 |
| `onboarding_steps` | is_deleted, deleted_at | ✅ 已实现 |
| `user_onboarding_progress` | is_deleted, deleted_at | ✅ 已实现 |

**✅ 提示模板 (2 张)**:
| 表名 | 字段 | 状态 |
|------|------|------|
| `page_prompt_templates` | is_deleted, deleted_at | ✅ 已实现 |
| `payment_records` | is_deleted, deleted_at | ✅ 已实现 |

---

## 🎯 表分类与策略

### 分类原则

根据业务特性，我们将 60 张表分为 4 大类：

1. **核心业务表** - 必须软删除（用户数据、内容数据）
2. **事务日志表** - 只增不删（Append-Only）
3. **系统配置表** - 需要软删除（管理员管理）
4. **中间关联表** - 需要软删除（关联关系）

---

## 📋 详细表清单

### 类别 1: 核心业务表（必须软删除）- 8 张

**优先级**: P0 (Critical)

| 表名 | 当前状态 | 业务说明 | 用户可恢复 |
|------|---------|----------|-----------|
| **marketplace_favorites** | ❌ 需添加 | 用户收藏 | ✅ 30天内 |
| **marketplace_reviews** | ❌ 需添加 | 商品评价 | ✅ 30天内 |
| **campaigns** | ❌ 需添加 | 营销活动 | ✅ 管理员可恢复 |
| **daily_themes** | ❌ 需添加 | 每日主题 | ✅ 管理员可恢复 |
| **holidays** | ❌ 需添加 | 节假日配置 | ✅ 管理员可恢复 |
| **asset_prompt_templates** | ❌ 需添加 | 资源提示词模板 | ✅ 管理员可恢复 |
| **support_tickets** | ❌ 需添加 | 支持工单 | ✅ 管理员可恢复 |
| **support_replies** | ❌ 需添加 | 工单回复 | ✅ 管理员可恢复 |

---

### 类别 2: 事务日志表（Append-Only，禁止删除）- 18 张

**优先级**: N/A (不允许删除)

这些表记录历史交易、审计日志，**永不删除**（Append-Only）：

| 表名 | 说明 | 删除策略 |
|------|------|----------|
| **credit_transactions** | 积分交易记录 | 🚫 禁止删除（财务审计） |
| **credit_purchases** | 积分购买记录 | 🚫 禁止删除（财务审计） |
| **marketplace_purchases** | 市场购买记录 | 🚫 禁止删除（交易凭证） |
| **subscription_history** | 订阅历史 | 🚫 禁止删除（财务审计） |
| **payment_records** | 支付记录 | 🚫 禁止删除（财务审计） |
| **pricing_history** | 价格历史 | 🚫 禁止删除（审计追踪） |
| **user_price_overrides** | 用户专属价格 | 🚫 禁止删除（审计追踪） |
| **user_discounts** | 用户折扣 | 🚫 禁止删除（审计追踪） |
| **config_audit_logs** | 配置审计日志 | 🚫 禁止删除（审计追踪） |
| **system_resource_audit_logs** | 系统资源审计 | 🚫 禁止删除（审计追踪） |
| **admin_operations** | 管理员操作日志 | 🚫 禁止删除（审计追踪） |
| **activity_logs** | 活动日志 | 🚫 禁止删除（审计追踪） |
| **api_logs** | API 调用日志 | 🚫 禁止删除（审计追踪） |
| **ai_call_logs** | AI 调用日志 | 🚫 禁止删除（审计追踪） |
| **clerk_webhook_events** | Clerk Webhook 事件 | 🚫 禁止删除（审计追踪） |
| **stripe_webhook_events** | Stripe Webhook 事件 | 🚫 禁止删除（审计追踪） |
| **scheduled_task_logs** | 定时任务日志 | 🚫 禁止删除（审计追踪） |
| **error_logs** | 错误日志 | 🚫 禁止删除（审计追踪） |

**说明**: 这些表采用**时间分区 + 归档策略**，不使用软删除。

---

### 类别 3: 系统配置表（需要软删除）- 15 张

**优先级**: P1 (High)

| 表名 | 当前状态 | 业务说明 | 删除场景 |
|------|---------|----------|----------|
| **system_configs** | ❌ 需添加 | 系统配置 | 配置废弃 |
| **feature_flags** | ❌ 需添加 | 功能开关 | 管理员下线功能 |
| **experiments** | ❌ 需添加 | A/B 测试 | 实验结束后归档 |
| **pricing_plans** | ❌ 需添加 | 定价计划 | 计划下线 |
| **generation_tasks** | ❌ 需添加 | AI 生成任务 | 任务完成后清理 |
| **user_generations** | ❌ 需添加 | 用户生成历史 | 用户清理历史 |
| **user_events** | ❌ 需添加 | 用户行为事件 | 清理过期事件 |
| **marketplace_reports** | ❌ 需添加 | 市场举报 | 管理员处理后归档 |
| **content_reports** | ❌ 需添加 | 内容举报 | 管理员处理后归档 |
| **listing_usages** | ❌ 需添加 | 资产使用追踪 | 清理过期数据 |
| **experiment_assignments** | ❌ 需添加 | 实验分配 | 实验结束后归档 |
| **marketplace_purchases** | ❌ 需添加 | 市场购买记录 | 用户删除记录 |
| **user_discounts** | ❌ 需添加 | 用户折扣 | 折扣过期/取消 |
| **subscription_history** | ❌ 需添加 | 订阅历史 | 历史清理 |
| **credit_purchases** | ❌ 需添加 | 积分购买 | 记录归档 |

---

### 类别 4: 统计聚合表（需要软删除）- 8 张

**优先级**: P2 (Medium)

| 表名 | 当前状态 | 业务说明 | 删除场景 |
|------|---------|----------|----------|
| **aggregated_stats** | ❌ 需添加 | 聚合统计 | 重新计算时清理旧数据 |
| **daily_metrics** | ❌ 需添加 | 每日指标 | 数据修正时清理 |
| **monthly_metrics** | ❌ 需添加 | 月度指标 | 数据修正时清理 |
| **ai_usage_daily** | ❌ 需添加 | AI 每日用量 | 数据修正时清理 |
| **analytics_aggregation** | ❌ 需添加 | 分析聚合 | 数据修正时清理 |
| **experiment_results** | ❌ 需添加 | 实验结果 | 实验失效时归档 |
| **experiment_exposures** | ❌ 需添加 | 实验曝光 | 实验结束后归档 |
| **experiment_conversions** | ❌ 需添加 | 实验转化 | 实验结束后归档 |

### 类别 5: 特殊处理（Append-Only 但需要软删除标记）- 13 张

**优先级**: P1 (需要讨论)

| 表名 | 当前状态 | 建议策略 | 理由 |
|------|---------|---------|------|
| **api_logs** | ❌ 无软删除 | 添加软删除 | 允许清理测试/错误日志 |
| **ai_call_logs** | ❌ 需添加 | 添加软删除 | 允许清理测试日志 |
| **activity_logs** | ❌ 需添加 | 添加软删除 | 允许GDPR删除 |
| **analytics_events** | ❌ 需添加 | 添加软删除 | 清理测试事件 |
| **clerk_webhook_events** | ❌ 需添加 | 添加软删除 | 清理重复/错误事件 |
| **stripe_webhook_events** | ❌ 需添加 | 添加软删除 | 清理重复/错误事件 |
| **config_audit_logs** | ❌ 需添加 | 添加软删除 | 归档旧审计记录 |
| **system_resource_audit_logs** | ❌ 需添加 | 添加软删除 | 归档旧审计记录 |
| **admin_operations** | ❌ 需添加 | 添加软删除 | 归档旧操作记录 |
| **scheduled_task_logs** | ❌ 需添加 | 添加软删除 | 清理旧任务日志 |
| **error_logs** | ❌ 需添加 | 添加软删除 | 清理已修复的错误日志 |
| **pricing_history** | ❌ 需添加 | 添加软删除 | 归档过时价格 |
| **user_price_overrides** | ❌ 需添加 | 添加软删除 | 删除过期覆盖 |

**说明**: 这些表虽然是日志类,但考虑到数据清理和 GDPR 合规需求,建议添加软删除以便归档处理。

---

## 🚀 实施计划

### Phase 3.1: 核心业务表软删除（P0 - 8 张表）

**预计时间**: 3-4 小时

#### 步骤 1: 数据库迁移（2 小时）

**创建迁移文件**: `migrations/v3/001_add_soft_delete_to_core_tables.sql`

```sql
-- ============================================================
-- Phase 3.1: 为核心业务表添加软删除字段 (P0)
-- ============================================================

BEGIN;

-- 1. marketplace_favorites
ALTER TABLE marketplace_favorites
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

CREATE INDEX idx_marketplace_favorites_active ON marketplace_favorites(user_id, listing_id)
WHERE is_deleted = false;

-- 2. marketplace_reviews
ALTER TABLE marketplace_reviews
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

CREATE INDEX idx_marketplace_reviews_active ON marketplace_reviews(listing_id, created_at DESC)
WHERE is_deleted = false;

-- 3. campaigns
ALTER TABLE campaigns
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS is_permanently_deleted BOOLEAN DEFAULT false;

CREATE INDEX idx_campaigns_active ON campaigns(status, start_date DESC)
WHERE is_deleted = false;

-- 4. daily_themes
ALTER TABLE daily_themes
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

CREATE INDEX idx_daily_themes_active ON daily_themes(theme_date DESC)
WHERE is_deleted = false;

-- 5. holidays
ALTER TABLE holidays
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

CREATE INDEX idx_holidays_active ON holidays(holiday_date DESC)
WHERE is_deleted = false;

-- 6. asset_prompt_templates
ALTER TABLE asset_prompt_templates
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

CREATE INDEX idx_asset_prompt_templates_active ON asset_prompt_templates(category)
WHERE is_deleted = false;

-- 7. support_tickets
ALTER TABLE support_tickets
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

CREATE INDEX idx_support_tickets_active ON support_tickets(user_id, created_at DESC)
WHERE is_deleted = false;

-- 8. support_replies
ALTER TABLE support_replies
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

CREATE INDEX idx_support_replies_active ON support_replies(ticket_id, created_at)
WHERE is_deleted = false;

COMMIT;
```

**需要处理的表** (8张):
1. marketplace_favorites
2. marketplace_reviews
3. campaigns
4. daily_themes
5. holidays
6. asset_prompt_templates
7. support_tickets
8. support_replies

#### 步骤 2: Repository 迁移（4 小时）

**需要迁移到 BaseRepository 的 Repository**:

| Repository | 文件 | 优先级 |
|-----------|------|--------|
| MarketplaceListingRepository | listing_repository.py | ✅ 已迁移 |
| CampaignRepository | campaign_repository.py | 🔄 需迁移 |
| NotificationRepository | notification_repository.py | 🔄 需迁移 |
| SupportRepository | support_repository.py | 🔄 需迁移 |
| SystemResourceRepository | system_resource_repository.py | 🔄 需迁移 |

**迁移模板**:
```python
# 修改前
class SupabaseCampaignRepository(ICampaignRepository):
    def __init__(self, client=None):
        self._client = client

    async def delete(self, campaign_id: str) -> bool:
        result = self.client.table("campaigns").delete().eq("id", campaign_id).execute()
        return bool(result.data)

# 修改后
class SupabaseCampaignRepository(BaseRepository[Campaign], ICampaignRepository):
    @property
    def table_name(self) -> str:
        return "campaigns"

    def _map_to_entity(self, row: dict) -> Campaign:
        # 映射逻辑

    async def delete(self, campaign_id: str) -> bool:
        return await self.soft_delete(campaign_id)
```

#### 步骤 3: 业务代码更新（2 小时）

**需要更新的 Service 层代码**:

```python
# 修改前
async def delete_campaign(campaign_id: str):
    # 直接物理删除
    return await campaign_repo.delete(campaign_id)

# 修改后
async def delete_campaign(campaign_id: str):
    # 软删除（30天可恢复）
    return await campaign_repo.soft_delete(campaign_id)

async def restore_campaign(campaign_id: str):
    # 新增恢复功能
    return await campaign_repo.restore(campaign_id)
```

---

### Phase 3.2: 系统配置表软删除（P1 - 12 张表）

**预计时间**: 6-8 小时

#### 数据库迁移

**创建迁移文件**: `migrations/v2/patches/003_add_soft_delete_to_config_tables.sql`

```sql
-- feature_flags, experiments, system_configs, 等...
```

#### Repository 迁移

| Repository | 状态 | 优先级 |
|-----------|------|--------|
| FeatureFlagRepository | 🔄 需迁移 | P1 |
| ExperimentRepository | 🔄 需迁移 | P1 |
| ConfigRepository | 🔄 需迁移 | P1 |

---

### Phase 3.3: 统计聚合表软删除（P2 - 8 张表）

**预计时间**: 4-6 小时

**特殊处理**:
- 这些表通常用于统计，删除操作较少
- 可以考虑使用**归档策略**而非软删除
- 建议：旧数据归档到冷存储（S3/BigQuery）

---

### Phase 3.4: 事务日志表策略调整（18 张表）

**预计时间**: 2-4 小时

**策略**: **禁止删除 + 自动归档**

```python
# 在 Repository 中禁用 delete 方法
class CreditTransactionRepository(BaseRepository[CreditTransaction]):
    async def delete(self, id: str) -> bool:
        raise NotImplementedError(
            "Credit transactions are append-only and cannot be deleted. "
            "Use archive_old_records() for data cleanup."
        )

    async def archive_old_records(self, cutoff_date: datetime) -> int:
        """
        归档超过 N 年的记录到冷存储。

        Args:
            cutoff_date: 归档截止日期

        Returns:
            归档记录数
        """
        # 1. 导出到 S3/BigQuery
        # 2. 验证导出成功
        # 3. 从主库删除
        pass
```

---

## 📊 影响分析

### 数据库层面

| 影响 | 评估 | 说明 |
|------|------|------|
| **存储空间** | 🟡 中等 | 软删除记录保留，预计增加 10-20% |
| **查询性能** | 🟢 低 | 条件索引 (WHERE is_deleted=false) 无性能损失 |
| **索引数量** | 🟡 中等 | 每表新增 1-2 个索引 |
| **迁移时间** | 🟢 低 | ALTER TABLE ADD COLUMN 很快（nullable 列） |

### 应用层面

| 影响 | 评估 | 说明 |
|------|------|------|
| **代码变更** | 🟡 中等 | ~10 个 Repository 需迁移 |
| **API 行为** | 🟢 低 | 用户无感知（删除变为软删除） |
| **恢复功能** | ✅ 新增 | 用户可在 30 天内恢复删除内容 |
| **管理功能** | ✅ 新增 | 管理员可查看/恢复已删除记录 |

### 业务层面

| 优势 | 说明 |
|------|------|
| **数据安全** | 防止误删，30天内可恢复 |
| **合规性** | 符合 GDPR 删除要求（软删除 + 定期物理删除） |
| **审计追踪** | 保留删除历史，完整审计链 |
| **用户体验** | 减少因误删导致的客诉 |

---

## 🔧 技术实施细节

### 1. 迁移文件模板

```sql
-- migrations/v2/patches/002_add_soft_delete_to_core_tables.sql

BEGIN;

-- ============================================================
-- Part 1: 添加软删除字段（22 张核心表）
-- ============================================================

-- profiles
ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

CREATE INDEX idx_profiles_deleted ON profiles(deleted_at DESC)
WHERE is_deleted = true;

-- marketplace_listings
ALTER TABLE marketplace_listings
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS is_permanently_deleted BOOLEAN DEFAULT false;

CREATE INDEX idx_marketplace_listings_active ON marketplace_listings(user_id, created_at DESC)
WHERE is_deleted = false AND is_permanently_deleted = false;

-- ... 其他 20 张表 ...

-- ============================================================
-- Part 2: 更新触发器（如需要）
-- ============================================================

-- 可选：自动设置 deleted_at
CREATE OR REPLACE FUNCTION set_deleted_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_deleted = true AND OLD.is_deleted = false THEN
        NEW.deleted_at = NOW();
    END IF;
    IF NEW.is_deleted = false THEN
        NEW.deleted_at = NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- profiles 表触发器
CREATE TRIGGER profiles_set_deleted_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at();

-- ... 其他表触发器 ...

COMMIT;
```

### 2. Repository 迁移清单

**需要迁移的 Repository (10 个)**:

| # | Repository | 文件 | 预计时间 |
|---|-----------|------|---------|
| 1 | CampaignRepository | campaign_repository.py | 30 min |
| 2 | NotificationRepository | notification_repository.py | 30 min |
| 3 | SupportRepository | support_repository.py | 30 min |
| 4 | SystemResourceRepository | system_resource_repository.py | 30 min |
| 5 | FeatureFlagRepository | feature_flag_repository.py | 30 min |
| 6 | ExperimentRepository | experiment_repository.py | 30 min |
| 7 | ConfigRepository | config_repository.py | 30 min |
| 8 | AnalyticsRepository | analytics_repository.py | 30 min |
| 9 | MetricsRepository | metrics_repository.py | 30 min |
| 10 | ErrorLogsRepository | error_logs_repository.py | 30 min |

**总计**: 5 小时

### 3. 测试策略

**单元测试**:
```python
# tests/infrastructure/repositories/test_campaign_repository.py

@pytest.mark.asyncio
class TestCampaignRepository:
    async def test_soft_delete_campaign(self, campaign_repo):
        """测试软删除活动"""
        campaign = await campaign_repo.create(...)

        # 软删除
        deleted = await campaign_repo.soft_delete(campaign.id)
        assert deleted is True

        # 验证不可见
        found = await campaign_repo.get_by_id(campaign.id)
        assert found is None

        # 验证仍在数据库
        found_with_deleted = await campaign_repo.get_by_id(campaign.id, include_deleted=True)
        assert found_with_deleted is not None
        assert found_with_deleted.is_deleted is True

    async def test_restore_campaign(self, campaign_repo):
        """测试恢复活动"""
        campaign = await campaign_repo.create(...)
        await campaign_repo.soft_delete(campaign.id)

        # 恢复
        restored = await campaign_repo.restore(campaign.id)
        assert restored is True

        # 验证可见
        found = await campaign_repo.get_by_id(campaign.id)
        assert found is not None
        assert found.is_deleted is False
```

---

## 📅 时间线

| Phase | 任务 | 表数量 | 预计时间 | 累计时间 |
|-------|------|--------|---------|---------|
| **Phase 3.1** | 核心业务表 (P0) | 8 | 3-4h | 3-4h |
| **Phase 3.2** | 系统配置表 (P1) | 15 | 6-8h | 9-12h |
| **Phase 3.3** | 统计聚合表 (P2) | 8 | 3-4h | 12-16h |
| **Phase 3.4** | 特殊处理表 (讨论) | 13 | 5-7h | 17-23h |
| **测试 & 验证** | 全面测试 | - | 4-6h | 21-29h |
| **文档更新** | 开发文档 + ddl.sql | - | 2-3h | 23-32h |

**总计**:
- **必须执行** (Phase 3.1-3.3): 12-16 小时
- **可选执行** (Phase 3.4): 5-7 小时
- **总计**: 23-32 小时 (约 3-4 个工作日)

**实际待处理表统计**:
- ✅ 已有软删除: 16 张 (26.7%)
- ❌ 需要添加: 44 张 (73.3%)
  - P0 核心业务: 8 张
  - P1 系统配置: 15 张
  - P2 统计聚合: 8 张
  - P1 特殊处理: 13 张 (需讨论是否添加)

---

## ⚠️ 风险与注意事项

### 风险

| 风险 | 等级 | 缓解措施 |
|------|------|----------|
| **数据库性能下降** | 🟡 中 | 使用条件索引，定期归档 |
| **存储空间不足** | 🟡 中 | 实施 30 天清理策略 |
| **查询逻辑遗漏** | 🔴 高 | 全面代码审查，添加测试 |
| **现有功能异常** | 🟡 中 | 分阶段部署，灰度发布 |

### 关键注意事项

1. **事务日志表绝对不能软删除**
   - credit_transactions, payment_records 等财务表
   - 必须保留完整审计链
   - 使用归档策略替代删除

2. **GDPR 合规性**
   - profiles 表的删除需要支持完全物理删除
   - 实施：soft_delete (30天) → hard_delete (物理删除)

3. **性能监控**
   - 监控查询性能变化
   - 检查索引使用情况
   - 定期归档旧数据

4. **定时清理任务**
   ```python
   # 每天运行
   async def cleanup_old_soft_deletes():
       """将 30 天前的软删除记录物理删除"""
       cutoff = datetime.now(timezone.utc) - timedelta(days=30)

       # 只清理用户数据表，保留系统表
       for table in CLEANABLE_TABLES:
           deleted = await repo.hard_delete_before_date(cutoff)
           logger.info(f"Cleaned {deleted} records from {table}")
   ```

---

## ✅ 验收标准

### 数据库层面

- [ ] 所有核心业务表（22 张）添加 `is_deleted`, `deleted_at` 字段
- [ ] 所有系统配置表（12 张）添加软删除字段
- [ ] 所有统计聚合表（8 张）添加软删除字段
- [ ] 所有表创建条件索引 (WHERE is_deleted = false)
- [ ] 事务日志表（18 张）保持 Append-Only，无软删除字段

### 代码层面

- [ ] 10 个 Repository 迁移到 BaseRepository
- [ ] 所有 delete() 方法改为 soft_delete()
- [ ] 新增 restore() 方法
- [ ] 所有查询自动过滤 is_deleted = true
- [ ] 事务日志 Repository 禁用 delete() 方法

### 测试层面

- [ ] 所有 Repository 单元测试通过
- [ ] 软删除功能测试通过
- [ ] 恢复功能测试通过
- [ ] 查询过滤测试通过
- [ ] 性能测试通过（查询时间 < 原来 110%）

### 文档层面

- [ ] 更新开发文档（软删除使用指南）
- [ ] 更新 API 文档（新增恢复接口）
- [ ] 创建运维手册（定时清理任务）

---

## 📚 参考资料

- [BaseRepository 实现](../infrastructure/repositories/base_repository.py)
- [BaseRepository 测试](../../tests/infrastructure/repositories/test_base_repository.py)
- [Phase 2 完成总结](PHASE-2-FINAL-REPORT.md)
- [后台业务逻辑说明 v3.3.0](../main/后台业务逻辑说明.md)

---

**文档版本**: v1.0.0
**创建时间**: 2026-01-10
**预计执行时间**: 3-5 个工作日
