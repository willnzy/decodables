# Make Decodables - 数据库架构 v3

> **按业务领域切分的数据库架构文件**

## 📁 文件列表

| 文件 | 大小 | 内容 | 执行顺序 |
|------|------|------|----------|
| `01_core_business.sql` | 31KB | 核心业务表（21张）+ system_error_logs | ① |
| `02_platform_services.sql` | 26KB | 平台服务表（29张） | ② |
| `03_infrastructure.sql` | 52KB | 基础设施表（12张）+ 函数 + 数据 | ③ |

**总计**: 62 张表 + 20 个函数 + 2 个视图 + 初始数据 + 维护任务

---

## 🚀 快速开始

### 执行迁移

⚠️ **必须按照 1 → 2 → 3 → 4 的顺序执行**

```bash
# 连接数据库并执行
psql -h your-host -U postgres -d your-database -f 01_core_business.sql
psql -h your-host -U postgres -d your-database -f 02_platform_services.sql
psql -h your-host -U postgres -d your-database -f 03_infrastructure.sql
psql -h your-host -U postgres -d your-database -f OPTIMIZATIONS.sql  # ⭐ 推荐执行
```

### 或使用自动化脚本

```bash
#!/bin/bash
DB_HOST="your-supabase-host.supabase.co"
DB_USER="postgres"
DB_NAME="postgres"

# 核心表 (必须执行)
for file in 01_core_business.sql 02_platform_services.sql 03_infrastructure.sql; do
    echo "执行 $file..."
    psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f $file
    if [ $? -ne 0 ]; then
        echo "❌ $file 执行失败"
        exit 1
    fi
done

# 优化补丁 (强烈推荐)
echo "执行优化补丁 OPTIMIZATIONS.sql..."
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f OPTIMIZATIONS.sql

echo "✅ 迁移完成（包含优化补丁）"
```

---

## 📋 业务分类

### 1️⃣ 核心业务层 (01_core_business.sql)

**21 张表**: 用户、积分、项目、素材、市场、系统日志

```
用户相关 (2):
  - profiles (用户资料)
  - user_discounts (用户折扣)

积分相关 (3):
  - credit_transactions (积分交易)
  - credit_purchases (积分购买)
  - subscription_history (订阅历史)

项目相关 (2):
  - projects (项目)
  - project_versions (项目版本)

素材相关 (4):
  - assets (用户素材)
  - asset_categories (素材分类)
  - system_assets (系统素材)
  - user_asset_prompt_templates (用户素材提示模板)

市场相关 (6):
  - marketplace_listings (市场列表)
  - marketplace_purchases (市场购买)
  - marketplace_favorites (市场收藏)
  - marketplace_reviews (市场评价)
  - listing_usages (使用记录)
  - marketplace_reports (市场举报)

AI 生成 (3):
  - user_generations (生成记录)
  - generation_tasks (生成任务)
  - user_page_prompt_templates (用户页面提示词模板)

系统日志 (1):
  - system_error_logs (RPC 函数内部错误日志)
```

### 2️⃣ 平台服务层 (02_platform_services.sql)

**28 张表**: Feature Flag、Analytics、Webhooks、审计、营销

```
Feature Flag (6):
  - feature_flags, experiments
  - experiment_assignments, experiment_results
  - experiment_exposures, experiment_conversions

Analytics (5):
  - analytics_events, analytics_aggregation
  - user_events, aggregated_stats, ai_usage_daily

Webhooks (2):
  - clerk_webhook_events, stripe_webhook_events

审计日志 (4):
  - activity_logs, config_audit_logs
  - content_reports, system_resource_audit_logs

主题营销 (5):
  - daily_themes, holidays, campaigns
  - campaign_participations, campaign_dismissals

新手引导 (3):
  - notifications, onboarding_steps, user_onboarding_progress

其他 (4):
  - referrals, daily_metrics, monthly_metrics, hourly_metrics
```

### 3️⃣ 基础设施层 (03_infrastructure.sql)

**12 张表 + 函数 + 视图 + 初始数据 + 维护任务配置**

```
配置 (4):
  - system_configs (系统配置)
  - pricing_plans (定价方案)
  - pricing_history (定价历史)
  - user_price_overrides (价格覆盖)

日志 (4):
  - api_logs (API 日志)
  - ai_call_logs (AI 调用日志)
  - scheduled_task_logs (定时任务日志)
  - error_logs (错误日志)

支持 (2):
  - support_tickets (支持工单)
  - support_replies (支持回复)

管理 (2):
  - admin_operations (管理员操作)
  - payment_records (支付记录)

额外内容:
  - 11 个数据库函数 (p_* 前缀)
  - 2 个视图定义 (v_table_sizes 用于监控)
  - 4 个维护任务函数 (cleanup_* 前缀，get_log_tables_stats)
  - 所有初始数据 INSERT
```

---

## ✅ 验证迁移

```sql
-- 检查表数量 (期望: 60)
SELECT COUNT(*) FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';

-- 检查数据库函数数量 (期望: 11)
SELECT COUNT(*) FROM pg_proc WHERE proname LIKE 'p_%';

-- 检查维护函数数量 (期望: 4)
SELECT COUNT(*) FROM pg_proc WHERE proname IN (
    'cleanup_old_user_creation_logs', 
    'cleanup_old_error_logs', 
    'cleanup_old_activity_logs', 
    'get_log_tables_stats'
);

-- 检查视图数量 (期望: 2)
SELECT COUNT(*) FROM information_schema.views 
WHERE table_schema = 'public' 
  AND table_name IN ('v_user_creation_events', 'v_table_sizes');
```

---

## 🔧 HOTFIX 脚本

在已部署的数据库上应用增量修复（按需执行）：

| 脚本文件 | 问题描述 | 执行时机 |
|---------|---------|----------|
| `HOTFIX_enable_rls_missing_tables.sql` | 为 system_error_logs 和 user_creation_logs 启用 RLS | 如果在 Supabase 中看到 UNRESTRICTED 警告 |
| `HOTFIX_add_target_user_id.sql` | 为 admin_operations 添加 target_user_id 列 | 如果看到 PGRST204 错误（找不到 target_user_id 列） |
| `HOTFIX_add_role_column.sql` | 为 profiles 添加 role 列 (user/admin) | 需要支持管理员角色功能时 |
| `HOTFIX_add_hourly_metrics.sql` | 添加 hourly_metrics 表（ETL 使用） | 如果看到 PGRST205 错误（找不到 hourly_metrics 表） |
| `HOTFIX_daily_metrics_fields.sql` | 为 daily_metrics 添加 date 和 dau 列 | 如果看到 daily_metrics 查询失败（字段不存在） |

**执行方法**:
```bash
# 连接数据库并执行 HOTFIX
psql -h your-host -U postgres -d your-database -f HOTFIX_enable_rls_missing_tables.sql
psql -h your-host -U postgres -d your-database -f HOTFIX_add_target_user_id.sql
psql -h your-host -U postgres -d your-database -f HOTFIX_add_role_column.sql
psql -h your-host -U postgres -d your-database -f HOTFIX_add_hourly_metrics.sql
```

**特点**:
- ✅ 所有 HOTFIX 脚本都是幂等的，可以安全地重复执行
- ✅ 包含验证步骤，执行后会显示验证结果
- ✅ 不会影响现有数据

---

## 🔄 事务控制

每个文件都包含完整的事务控制：

```sql
BEGIN;
-- ... SQL 语句 ...
COMMIT;
```

**好处**: 要么全部成功，要么全部回滚，不会造成部分迁移。

---

## ⚠️ 注意事项

1. **执行顺序**: 必须按 1 → 2 → 3 顺序，因为存在外键依赖
2. **新建数据库**: 这些文件用于新建数据库，不是增量迁移
3. **备份数据**: 在现有数据库上执行前务必备份
4. **环境测试**: 先在测试环境验证，再部署生产

---

## 📚 相关文档

- **原始文件**: `../v2/refactored_schema_v2.sql` (185KB 完整版)
- **切分工具**: `../v2/split_schema.py` (可复用)
- **详细说明**: `../v2/README.md` (13KB 完整文档)

---

**版本**: v3.0
**创建时间**: 2026-01-10
**维护者**: Make Decodables 后端团队
