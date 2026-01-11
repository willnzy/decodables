# Make Decodables - 数据库架构迁移 v2

## 概述

本目录包含 Make Decodables 项目的**完整数据库架构文件**和**切分工具**。

**最后更新**: 2026-01-10
**总表数**: 60
**总函数数**: 11
**总视图数**: 1

> ⚠️ **重要**: 业务切分后的 SQL 文件已移至 [../v3/](../v3/) 目录，请前往查看执行说明。

---

## 文件结构

```
migrations/v2/
├── README.md                        # 本文件
├── SPLIT_REPORT.md                  # 详细切分报告
├── split_schema.py                  # 切分脚本（可复用）
└── refactored_schema_v2.sql         # 完整架构文件（185KB，主文件）

migrations/v3/  ← 业务切分文件在这里
├── README.md                        # 执行说明
├── 01_core_business.sql             # 核心业务表（20 表，31KB）
├── 02_platform_services.sql         # 平台服务表（28 表，26KB）
└── 03_infrastructure.sql            # 基础设施表（12 表，52KB）+ 函数 + 视图 + 初始数据
```

---

## 文件说明

### 主文件

**refactored_schema_v2.sql** (185KB)
- ✅ **完整的数据库架构定义**（60 表 + 11 函数 + 1 视图 + 初始数据）
- ✅ **用途**: 备份、参考、切分源文件
- ✅ **执行**: 可直接在新数据库上执行（单文件模式）
- ✅ **优点**: 一次性创建全部对象，适合快速搭建开发环境

**使用场景**:
```bash
# 快速搭建开发数据库
psql -h localhost -U postgres -d your_database -f refactored_schema_v2.sql
```

### 切分工具

**split_schema.py** (19KB)
- ✅ **功能**: 将 `refactored_schema_v2.sql` 按业务领域切分为 3 个文件
- ✅ **输出**: 生成 `01_core_business.sql`, `02_platform_services.sql`, `03_infrastructure.sql`
- ✅ **可复用**: 修改 `BUSINESS_CATEGORIES` 字典可自定义分类

**使用方法**:
```bash
cd /Users/zhangyi/Code_all/AI-WEB/decodables/migrations/v2
python3 split_schema.py
```

**输出位置**: 默认输出到当前目录，可自行移动到 v3 或其他目录

### 切分报告

**SPLIT_REPORT.md** (1.8KB)
- ✅ 详细的表分类说明
- ✅ 每个业务领域包含哪些表
- ✅ 文件大小和表数量统计

---

## 业务切分版本 (v3)

如需按业务领域分步执行，请查看 [../v3/README.md](../v3/README.md)

**v3 优势**:
- ✅ 按业务领域组织，便于理解
- ✅ 分 3 个文件执行，可逐步部署
- ✅ 每个文件有独立事务控制
- ✅ 符合依赖关系，按顺序执行

**v3 执行顺序**:
1. `01_core_business.sql` - 核心业务表（20 表）
2. `02_platform_services.sql` - 平台服务表（28 表）
3. `03_infrastructure.sql` - 基础设施表（12 表）+ 函数 + 视图 + 初始数据

详细说明请查看: [../v3/README.md](../v3/README.md)

---

## ~~执行顺序~~ (已移至 v3)

⚠️ 以下内容已过时，业务切分文件已移至 v3 目录

<details>
<summary>展开查看旧版执行说明（仅供参考）</summary>

### 1️⃣ 核心业务层 (01_core_business.sql)

**包含内容**: 用户、积分、项目、素材、市场等核心业务表

**表列表** (20 个):
- 用户相关: `profiles`, `user_discounts`
- 积分相关: `credit_transactions`, `credit_purchases`, `subscription_history`
- 项目相关: `projects`, `project_versions`
- 素材相关: `assets`, `asset_categories`, `system_assets`, `asset_prompt_templates`
- 市场相关: `marketplace_listings`, `marketplace_purchases`, `marketplace_favorites`, `marketplace_reviews`, `listing_usages`, `marketplace_reports`
- AI 生成: `user_generations`, `generation_tasks`, `page_prompt_templates`

**执行方式**:
```bash
# 方式 1: psql 命令行
psql -h your-host -U your-user -d your-database -f 01_core_business.sql

# 方式 2: Supabase Dashboard
# 在 SQL Editor 中复制文件内容，点击 Run
```

---

### 2️⃣ 平台服务层 (02_platform_services.sql)

**包含内容**: Feature Flag、Analytics、Webhooks、审计、主题、营销等平台服务表

**表列表** (28 个):
- Feature Flag: `feature_flags`, `experiments`, `experiment_*` (5 个实验相关表)
- Analytics: `analytics_events`, `analytics_aggregation`, `user_events`, `aggregated_stats`, `ai_usage_daily`
- Webhooks: `clerk_webhook_events`, `stripe_webhook_events`
- 审计: `activity_logs`, `config_audit_logs`, `content_reports`, `system_resource_audit_logs`
- 主题/营销: `daily_themes`, `holidays`, `campaigns`, `campaign_participations`, `campaign_dismissals`
- 新手引导: `onboarding_steps`, `user_onboarding_progress`
- 其他: `notifications`, `referrals`, `daily_metrics`, `monthly_metrics`

**执行方式**:
```bash
psql -h your-host -U your-user -d your-database -f 02_platform_services.sql
```

---

### 3️⃣ 基础设施层 (03_infrastructure.sql)

**包含内容**: 配置、日志、支持、管理、函数、视图、初始数据

**表列表** (12 个):
- 配置: `system_configs`, `pricing_plans`, `pricing_history`, `user_price_overrides`
- 日志: `api_logs`, `ai_call_logs`, `scheduled_task_logs`, `error_logs`
- 支持: `support_tickets`, `support_replies`
- 管理: `admin_operations`, `payment_records`

**额外内容**:
- ✅ **11 个数据库函数** (RPC 函数，`p_` 前缀)
- ✅ **1 个视图定义**
- ✅ **所有 INSERT 初始数据** (8 个表的初始记录)

**执行方式**:
```bash
psql -h your-host -U your-user -d your-database -f 03_infrastructure.sql
```

---

## 完整执行示例

### 使用 psql 连续执行

```bash
#!/bin/bash
# 数据库连接配置
DB_HOST="your-supabase-host.supabase.co"
DB_USER="postgres"
DB_NAME="postgres"

echo "开始执行数据库迁移..."

# 执行第 1 个文件
echo "1/3 执行核心业务层..."
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f 01_core_business.sql
if [ $? -ne 0 ]; then
    echo "❌ 核心业务层执行失败，停止迁移"
    exit 1
fi

# 执行第 2 个文件
echo "2/3 执行平台服务层..."
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f 02_platform_services.sql
if [ $? -ne 0 ]; then
    echo "❌ 平台服务层执行失败，停止迁移"
    exit 1
fi

# 执行第 3 个文件
echo "3/3 执行基础设施层..."
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f 03_infrastructure.sql
if [ $? -ne 0 ]; then
    echo "❌ 基础设施层执行失败，停止迁移"
    exit 1
fi

echo "✅ 数据库迁移完成！"
```

### 使用 Supabase Dashboard

1. 打开 Supabase 项目的 **SQL Editor**
2. 创建新的查询
3. 按顺序复制每个文件的内容并执行:
   - 先执行 `01_core_business.sql`
   - 等待成功后执行 `02_platform_services.sql`
   - 最后执行 `03_infrastructure.sql`

---

## 事务控制

每个文件都包含完整的事务控制:

```sql
-- 文件开头
BEGIN;

-- ... SQL 语句 ...

-- 文件结尾
COMMIT;
```

**优点**:
- ✅ 每个文件要么全部成功，要么全部回滚
- ✅ 出错时自动回滚，不会造成部分迁移
- ✅ 保证数据一致性

**如果执行失败**:
- 数据库会自动回滚该文件的所有更改
- 检查错误信息，修复后重新执行该文件
- 无需手动清理

---

## 依赖关系说明

### 为什么必须按顺序执行？

1. **外键依赖**:
   - `02_platform_services.sql` 中的表可能引用 `01_core_business.sql` 中的表
   - 例如: `analytics_events.user_id` → `profiles.user_id`

2. **函数依赖**:
   - `03_infrastructure.sql` 中的函数可能操作前面的表
   - 例如: `p_get_user_stats()` 需要 `profiles` 表存在

3. **初始数据依赖**:
   - `03_infrastructure.sql` 中的 INSERT 语句依赖前面的表结构
   - 例如: `INSERT INTO system_configs` 需要该表已创建

---

## 回滚策略

如果需要完全回滚迁移:

```bash
# 方式 1: 删除所有表（谨慎！）
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;
"

# 方式 2: 逐个删除表（更安全）
# 按照与创建相反的顺序删除
# 先删除 03_infrastructure.sql 中的表
# 再删除 02_platform_services.sql 中的表
# 最后删除 01_core_business.sql 中的表
```

---

## 验证迁移成功

执行完成后，运行以下检查:

```sql
-- 1. 检查表数量
SELECT COUNT(*) as table_count
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
-- 期望结果: 60

-- 2. 检查函数数量
SELECT COUNT(*) as function_count
FROM pg_proc
WHERE proname LIKE 'p_%';
-- 期望结果: 11

-- 3. 检查视图数量
SELECT COUNT(*) as view_count
FROM information_schema.views
WHERE table_schema = 'public';
-- 期望结果: 1

-- 4. 检查初始数据
SELECT
    (SELECT COUNT(*) FROM system_configs) as configs,
    (SELECT COUNT(*) FROM pricing_plans) as pricing_plans,
    (SELECT COUNT(*) FROM asset_categories) as asset_categories,
    (SELECT COUNT(*) FROM onboarding_steps) as onboarding_steps;
-- 应该都有数据
```

---

## 常见问题

### Q1: 可以只执行某个文件吗？

**A**: 不建议。虽然每个文件是独立的事务，但存在外键依赖。如果只执行部分文件，可能导致:
- 外键约束失败
- 函数引用不存在的表
- 初始数据插入失败

**建议**: 始终按顺序执行全部 3 个文件。

### Q2: 执行失败了怎么办？

**A**:
1. 查看错误信息，定位问题（通常是外键冲突或数据类型错误）
2. 由于有事务控制，失败的文件会自动回滚
3. 修复问题后，重新执行失败的文件即可
4. 无需重新执行已成功的文件

### Q3: 如何在现有数据库上执行？

**A**:
⚠️ **警告**: 这些 SQL 文件会创建新表，如果表已存在会报错。

**选项 1**: 全新数据库（推荐）
```bash
# 创建新的空数据库
createdb -h $DB_HOST -U $DB_USER make_decodables_new
# 在新数据库上执行迁移
```

**选项 2**: 现有数据库（需要先备份）
```bash
# 1. 备份现有数据库
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME > backup_$(date +%Y%m%d).sql

# 2. 删除冲突的表（谨慎！）
# 手动检查并删除已存在的表

# 3. 执行迁移
```

### Q4: 如何修改分类或重新切分？

**A**:
1. 编辑 `split_schema.py` 中的 `BUSINESS_CATEGORIES` 字典
2. 调整表的分类
3. 重新运行脚本: `python3 split_schema.py`
4. 会重新生成 3 个 SQL 文件

---

## 技术细节

### 切分策略

每个表的完整定义包括:
- ✅ `CREATE TABLE` 语句
- ✅ `ALTER TABLE` 约束和外键
- ✅ `CREATE INDEX` 索引定义
- ✅ `CREATE TRIGGER` 触发器
- ✅ 相关注释

**保证**: 每个表的所有相关对象都在同一个文件中，不会分散。

### 文件大小

| 文件 | 大小 | 表数 | 说明 |
|------|------|------|------|
| 01_core_business.sql | 31 KB | 20 | 核心业务表 |
| 02_platform_services.sql | 26 KB | 28 | 平台服务表 |
| 03_infrastructure.sql | 52 KB | 12 | 基础设施 + 函数 + 视图 + 初始数据 |
| **总计** | **109 KB** | **60** | (原始文件 185 KB) |

> 注: 总大小比原始文件小，因为切分时去除了冗余注释和空行

---

## 维护指南

### 添加新表

1. 在 `refactored_schema_v2.sql` 中添加表定义
2. 运行 `python3 split_schema.py` 重新切分
3. 新表会自动分类到对应文件

### 修改表结构

1. 在 `refactored_schema_v2.sql` 中修改
2. 重新切分
3. **或**: 直接在对应的切分文件中修改（推荐用于小改动）

### 重新分类

编辑 `split_schema.py`:

```python
BUSINESS_CATEGORIES = {
    "core_business": {
        "tables": [
            "profiles",
            "新表名",  # 添加到这里
            ...
        ]
    },
    ...
}
```

---

## 已废弃的文件

以下文件内容已合并到 `refactored_schema_v2.sql` 和切分后的文件中，无需再执行：

- ❌ `schema_tables.sql` (已被 3 个业务文件替代)
- ❌ `schema_indexes_functions.sql` (已分散到各业务文件)
- ❌ `schema_data.sql` (已合并到 `03_infrastructure.sql`)
- ❌ `003_create_pricing_tables.sql` (内容已包含)
- ❌ `add_experiment_tracking_tables.sql` (内容已包含)

---

## 联系信息

**项目**: Make Decodables
**维护者**: 后端团队
**最后更新**: 2026-01-10
**版本**: v2.0

有问题请查看:
- `SPLIT_REPORT.md` - 详细的表分类报告
- `split_schema.py` - 切分脚本源代码
- `refactored_schema_v2.sql` - 原始完整架构

---

## 附录: 表分类速查

### 核心业务表 (20)

```
profiles                    # 用户资料
credit_transactions         # 积分交易
credit_purchases           # 积分购买
subscription_history       # 订阅历史
projects                   # 项目
project_versions           # 项目版本
assets                     # 用户素材
asset_categories           # 素材分类
system_assets             # 系统素材
asset_prompt_templates     # 素材提示模板
marketplace_listings       # 市场列表
marketplace_purchases      # 市场购买
marketplace_favorites      # 市场收藏
marketplace_reviews        # 市场评价
listing_usages            # 列表使用记录
marketplace_reports        # 市场举报
user_generations          # 用户生成记录
generation_tasks          # 生成任务
page_prompt_templates     # 页面提示模板
user_discounts            # 用户折扣
```

### 平台服务表 (28)

```
feature_flags              # 功能开关
experiments               # 实验配置
experiment_assignments    # 实验分配
experiment_results        # 实验结果
experiment_exposures      # 实验曝光
experiment_conversions    # 实验转化
analytics_events          # 分析事件
analytics_aggregation     # 分析聚合
user_events               # 用户事件
aggregated_stats          # 聚合统计
activity_logs             # 活动日志
ai_usage_daily            # AI 使用日统计
clerk_webhook_events      # Clerk Webhook
stripe_webhook_events     # Stripe Webhook
config_audit_logs         # 配置审计日志
content_reports           # 内容举报
system_resource_audit_logs # 系统资源审计
daily_themes              # 每日主题
holidays                  # 节假日
campaigns                 # 营销活动
campaign_participations   # 活动参与
campaign_dismissals       # 活动关闭
notifications             # 通知
onboarding_steps          # 新手引导步骤
user_onboarding_progress  # 用户引导进度
referrals                 # 推荐
daily_metrics             # 日度指标
monthly_metrics           # 月度指标
```

### 基础设施表 (12)

```
system_configs            # 系统配置
pricing_plans             # 定价方案
pricing_history           # 定价历史
user_price_overrides      # 用户价格覆盖
api_logs                  # API 日志
ai_call_logs              # AI 调用日志
scheduled_task_logs       # 定时任务日志
error_logs                # 错误日志
support_tickets           # 支持工单
support_replies           # 支持回复
admin_operations          # 管理员操作
payment_records           # 支付记录
```

</details>

---

## 快速开始

### 选项 1: 单文件模式（推荐用于开发环境）

```bash
cd /Users/zhangyi/Code_all/AI-WEB/decodables/migrations/v2
psql -h your-host -U postgres -d your-database -f refactored_schema_v2.sql
```

**优点**: 简单快速，一次性创建全部对象

### 选项 2: 业务切分模式（推荐用于生产环境）

```bash
cd /Users/zhangyi/Code_all/AI-WEB/decodables/migrations/v3

# 按顺序执行
psql -h your-host -U postgres -d your-database -f 01_core_business.sql
psql -h your-host -U postgres -d your-database -f 02_platform_services.sql
psql -h your-host -U postgres -d your-database -f 03_infrastructure.sql
```

**优点**: 分步执行，便于理解，符合业务逻辑

详细说明: [../v3/README.md](../v3/README.md)

---

## 验证迁移成功

```sql
-- 检查表数量 (期望: 60)
SELECT COUNT(*) FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';

-- 检查函数数量 (期望: 11)
SELECT COUNT(*) FROM pg_proc WHERE proname LIKE 'p_%';

-- 检查视图数量 (期望: 1)
SELECT COUNT(*) FROM information_schema.views WHERE table_schema = 'public';
```

---

## 文件维护

### 如何更新架构

1. **修改主文件**: 编辑 `refactored_schema_v2.sql`
2. **重新切分**: 运行 `python3 split_schema.py`
3. **更新 v3**: 将生成的 3 个文件移动到 v3 目录

### 自定义分类

编辑 `split_schema.py` 中的 `BUSINESS_CATEGORIES` 字典:

```python
BUSINESS_CATEGORIES = {
    "core_business": {
        "tables": [
            "profiles",
            "your_new_table",  # 添加新表到对应分类
            ...
        ]
    },
    ...
}
```

---

## 相关文档

- **v3 执行说明**: [../v3/README.md](../v3/README.md)
- **切分报告**: [SPLIT_REPORT.md](SPLIT_REPORT.md)
- **切分工具**: [split_schema.py](split_schema.py)

---

**版本**: v2.0
**最后更新**: 2026-01-10
**维护**: Make Decodables 后端团队
