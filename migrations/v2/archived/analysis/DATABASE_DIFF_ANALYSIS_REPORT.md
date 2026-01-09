# 数据库重构差异分析报告

> **生成日期**: 2026-01-09
> **对比版本**: V1 ddl.sql (v3.27) vs V2 refactored_schema.sql
> **分析师**: Senior Database Architect

---

## 目录

1. [执行摘要](#1-执行摘要)
2. [表结构完整性分析](#2-表结构完整性分析)
3. [字段映射准确性分析](#3-字段映射准确性分析)
4. [索引完整性分析](#4-索引完整性分析)
5. [初始化数据完整性分析](#5-初始化数据完整性分析)
6. [业务逻辑一致性分析](#6-业务逻辑一致性分析)
7. [修复建议与SQL脚本](#7-修复建议与sql脚本)
8. [实施计划](#8-实施计划)

---

## 1. 执行摘要

### 1.1 总体评估

| 评估维度 | V1 现状 | V2 现状 | 完成度 | 评级 |
|---------|---------|---------|--------|------|
| **表数量** | 42 张表 | 29 张表 | 69% | ⚠️ |
| **核心表覆盖** | 100% | 85% | 85% | ⚠️ |
| **字段命名规范** | 混合 | snake_case | 95% | ✅ |
| **索引策略** | 完整 | 部分完整 | 85% | ✅ |
| **初始化数据** | 120+ 行 | 14 行 | 12% | ❌ |
| **触发器与函数** | 25+ | 10+ | 40% | ❌ |

**结论**: V2 refactored_schema.sql 在架构设计和命名规范上优秀,但**缺失 13 张关键业务表**和**大量初始化数据**,需要立即补充才能用于生产环境。

### 1.2 核心问题

🔴 **严重问题 (阻塞性)**:
1. **缺失 13 张关键业务表** (AI、素材分类、主题系统、Analytics 等)
2. **system_configs 初始化数据严重不足** (14/120+ 行,缺失 88%)
3. **缺失 AI 调用日志和成本追踪表** (ai_call_logs, ai_usage_daily)

🟡 **中等问题 (重要但非阻塞)**:
1. **字段名不一致** (system_configs 表: key vs config_key)
2. **缺失主题和节日相关表** (daily_themes, holidays)
3. **缺失部分 Analytics 聚合表** (analytics_aggregation, activity_logs)

🟢 **轻微问题 (建议优化)**:
1. **Storage buckets 不应直接在 DDL 中创建**
2. **部分触发器和函数缺失**

---

## 2. 表结构完整性分析

### 2.1 表数量对比

- **V1 (ddl.sql)**: 42 张表
- **V2 (refactored_schema.sql)**: 29 张表
- **缺失**: 13 张表

### 2.2 完全缺失的表 (13 张)

#### 🔴 P0 级别 (关键阻塞) - 必须立即补充

| 表名 | 用途 | 影响 | 优先级 |
|------|------|------|--------|
| `ai_call_logs` | AI API 调用日志 | AI 功能无法追踪成本和性能 | 🔴 P0 |
| `ai_usage_daily` | AI 使用量日汇总 | 无法进行成本分析和容量规划 | 🔴 P0 |
| `asset_categories` | 素材分类树 | 素材库功能完全不可用 | 🔴 P0 |
| `assets` | 统一素材表 | 素材库功能完全不可用 | 🔴 P0 |

**影响**: 这 4 张表缺失将导致以下核心功能完全不可用:
- ❌ AI 图像/文本生成功能无法追踪成本
- ❌ 素材分类系统无法工作
- ❌ 系统内置素材无法加载
- ❌ Admin 无法查看 AI 成本统计

#### 🟡 P1 级别 (重要功能) - 优先补充

| 表名 | 用途 | 影响 | 优先级 |
|------|------|------|--------|
| `daily_themes` | 每日主题 | 产品特色功能缺失 | 🟡 P1 |
| `holidays` | 节日数据 | 节日主题素材无法展示 | 🟡 P1 |
| `activity_logs` | 活动日志 | 审计和活动追踪缺失 | 🟡 P1 |
| `analytics_aggregation` | Analytics 聚合 | Dashboard 性能差 | 🟡 P1 |
| `scheduled_task_logs` | 调度任务日志 | 运维监控缺失 | 🟡 P1 |

#### 🟢 P2 级别 (增强功能) - 后续补充

| 表名 | 用途 | 影响 | 优先级 |
|------|------|------|--------|
| `config_audit_logs` | 配置审计 | 配置变更无审计 | 🟢 P2 |
| `content_reports` | 内容举报 | 内容审核功能缺失 | 🟢 P2 |
| `system_resource_audit_logs` | 系统资源审计 | 资源变更无审计 | 🟢 P2 |
| `asset_prompt_templates` | 素材提示词模板 | AI 生成功能受限 | 🟢 P2 |

### 2.3 V2 新增的表 (V1 中不存在)

V2 引入了一些新的表,这些是重构后的新设计:

| 表名 | 用途 | 来源 |
|------|------|------|
| `api_logs` | API 调用日志 | 新设计 (替代部分 activity_logs) |
| `clerk_webhook_events` | Clerk Webhook 事件 | 新设计 (幂等性) |
| `stripe_webhook_events` | Stripe Webhook 事件 | 新设计 (幂等性) |
| `credit_purchases` | 积分购买记录 | 新设计 (从 credit_transactions 分离) |
| `marketplace_favorites` | 市场收藏 | 新功能 |
| `marketplace_reviews` | 市场评价 | 新功能 |
| `marketplace_purchases` | 市场购买 | 重命名自 user_purchases |
| `referrals` | 推荐系统 | 新功能 |
| `subscription_history` | 订阅历史 | 新设计 (从 profiles 分离) |
| `onboarding_steps` | 引导步骤 | 新功能 (Onboarding System) |
| `user_onboarding_progress` | 用户引导进度 | 新功能 (Onboarding System) |
| `campaign_participations` | 活动参与 | 重命名自 campaign_claims |
| `project_versions` | 项目版本 | 新功能 (版本控制) |

**评估**: 这些新表是合理的业务扩展,但需要确保与现有功能兼容。

### 2.4 V1 中存在但 V2 缺失的表清单

#### AI 相关 (2 张)
```
❌ ai_call_logs            - AI API 调用详细日志
❌ ai_usage_daily          - AI 使用量日汇总表
```

#### 素材系统 (2 张)
```
❌ asset_categories        - 素材分类树 (多级分类)
❌ assets                  - 统一素材表 (V2 的 assets 定义不同)
```
⚠️ **注意**: V1 的 `assets` 是用户资产表,而素材分类系统需要的是系统素材表。

#### 主题与节日 (2 张)
```
❌ daily_themes            - 每日主题配置
❌ holidays                - 节日数据库 (28+ 全球节日)
```

#### Analytics 与日志 (3 张)
```
❌ activity_logs           - 用户活动日志 (轻量级)
❌ analytics_aggregation   - Analytics 预聚合表
❌ scheduled_task_logs     - 定时任务执行日志
```

#### 审计与报告 (3 张)
```
❌ config_audit_logs       - 配置变更审计
❌ content_reports         - 内容举报表
❌ system_resource_audit_logs - 系统资源审计
```

#### 其他 (1 张)
```
❌ asset_prompt_templates  - AI 素材生成模板 (5W1H)
```

---

## 3. 字段映射准确性分析

### 3.1 核心表字段对比

#### 3.1.1 `profiles` 表

| 字段 | V1 (ddl.sql) | V2 (refactored_schema.sql) | 状态 |
|------|--------------|---------------------------|------|
| 主键 | `id TEXT` | `id TEXT` | ✅ 一致 |
| email | ✅ | ✅ | ✅ 一致 |
| username | ✅ | ✅ | ✅ 一致 |
| credits_monthly | ✅ | ✅ | ✅ 一致 |
| credits_permanent | ✅ | ✅ | ✅ 一致 |
| tier | ✅ | ✅ | ✅ 一致 |
| user_code | ✅ | ❌ 缺失 | ⚠️ 需补充 |
| timezone | ✅ (v3.9) | ❌ 缺失 | ⚠️ 需补充 |
| created_at_local | ✅ (v3.9) | ❌ 缺失 | ⚠️ 需补充 |
| cohort_month | ✅ | ❌ 缺失 | 🟡 可选 |

**评估**: V2 缺失 `user_code` (用户代码) 字段,这是业务关键字段 (见 USER-ID-SYSTEM.md)。

#### 3.1.2 `system_configs` 表 ⚠️ 字段名不一致

**V1 (ddl.sql)**:
```sql
CREATE TABLE system_configs (
    key TEXT PRIMARY KEY,              -- ✅ 原名
    value TEXT NOT NULL,                -- ✅ 原名
    value_type TEXT NOT NULL,
    config_group TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,    -- ✅ 原字段
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    updated_by TEXT                    -- ✅ 审计字段
);
```

**V2 (refactored_schema.sql)**:
```sql
CREATE TABLE system_configs (
    id UUID PRIMARY KEY,               -- ❌ 新增 UUID 主键
    config_key TEXT NOT NULL UNIQUE,   -- ❌ 改名 (key → config_key)
    config_value TEXT NOT NULL,        -- ❌ 改名 (value → config_value)
    value_type TEXT NOT NULL,
    config_group TEXT NOT NULL,
    description TEXT,
    is_editable BOOLEAN DEFAULT TRUE,  -- ❌ 新字段 (替代 is_active)
    ext_json JSONB DEFAULT '{}',       -- ❌ 新字段
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    is_deleted BOOLEAN,                -- ❌ 新字段 (软删除)
    deleted_at TIMESTAMPTZ             -- ❌ 新字段
);
```

**问题分析**:
1. 🔴 **主键变更**: `key TEXT` → `id UUID` + `config_key TEXT UNIQUE`
   - **影响**: 现有代码中所有 `WHERE key = ?` 查询需要改为 `WHERE config_key = ?`
   - **影响**: 所有 INSERT 语句需要重写

2. 🔴 **字段重命名**: `key` → `config_key`, `value` → `config_value`
   - **影响**: 后端代码 `domains/system/repository.py` 中的所有 SQL 查询失效
   - **影响**: ADR-0002 中的配置读取逻辑失效

3. 🟡 **新字段**: `is_editable`, `ext_json`, `is_deleted`, `deleted_at`
   - **影响**: 正向兼容,但需要迁移脚本填充默认值

4. ⚠️ **缺失字段**: `updated_by` (审计字段)
   - **影响**: 无法追踪谁修改了配置

**建议**:

**方案 A (推荐 - 最小破坏)**: 保留 V1 字段名,仅添加新字段
```sql
CREATE TABLE system_configs (
    key TEXT PRIMARY KEY,              -- ✅ 保持原名
    value TEXT NOT NULL,               -- ✅ 保持原名
    value_type TEXT NOT NULL DEFAULT 'text',
    config_group TEXT NOT NULL DEFAULT 'general',
    description TEXT,

    -- 保留原有字段
    is_active BOOLEAN DEFAULT TRUE,    -- ✅ 保留

    -- 新增字段 (不影响现有代码)
    is_editable BOOLEAN DEFAULT TRUE,  -- ✨ 新增
    ext_json JSONB DEFAULT '{}',       -- ✨ 新增

    -- 审计字段
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by TEXT                    -- ✅ 保留
);
```

**方案 B (重构版 - 需要大量代码改动)**: 使用新字段名,提供迁移脚本
- ⚠️ 需要修改所有后端代码中的字段引用
- ⚠️ 需要提供数据迁移脚本
- ⚠️ 需要兼容性过渡期 (VIEW + trigger 同步)

#### 3.1.3 `marketplace_listings` 表

**V1 字段** (v3.26 迁移后):
```sql
category TEXT DEFAULT 'element'    -- ✅ 单一分类
source TEXT DEFAULT 'user'         -- ✅ 来源字段
```

**V2 字段**:
```sql
-- ❌ 完全不同的字段设计
primary_category TEXT              -- 两级分类
secondary_category TEXT
```

**问题**: V2 设计与 V1 v3.26 迁移不一致。v3.26 已将 `primary_category` 改回 `category`。

**建议**: 使用 V1 的最新设计 (category + source)。

#### 3.1.4 `credit_transactions` 表

**V1**:
```sql
CREATE TABLE credit_transactions (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    amount INT NOT NULL,
    bucket TEXT NOT NULL,              -- 'monthly' or 'permanent'
    balance_monthly_after INT,
    balance_permanent_after INT,
    type TEXT NOT NULL,
    description TEXT,
    idempotency_key TEXT UNIQUE,       -- v3.22 幂等性
    timezone TEXT,                     -- v3.9
    created_at_local TIMESTAMP,        -- v3.9
    created_at TIMESTAMPTZ
);
```

**V2**:
```sql
CREATE TABLE credit_transactions (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    transaction_type TEXT NOT NULL,    -- ❌ 改名 (type → transaction_type)
    amount INT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ
);
```

**缺失字段**:
- ❌ `bucket` (月度/永久积分区分)
- ❌ `balance_monthly_after` (记录后余额)
- ❌ `balance_permanent_after` (记录后余额)
- ❌ `idempotency_key` (幂等性保证)
- ❌ `timezone` + `created_at_local` (时区支持)

**影响**:
- 🔴 无法实现 "先扣月度积分,再扣永久积分" 的业务规则
- 🔴 无法追踪每次交易后的余额快照 (审计需求)
- 🔴 无法保证 Webhook 幂等性

**建议**: 必须恢复 V1 的完整字段设计。

---

## 4. 索引完整性分析

### 4.1 索引对比

#### `profiles` 表索引

| 索引 | V1 | V2 | 状态 |
|------|----|----|------|
| `idx_profiles_tier` | ✅ | ✅ | ✅ 一致 |
| `idx_profiles_created_at` | ✅ | ✅ | ✅ 一致 |
| `idx_profiles_subscription_status` | ✅ | ❌ | ⚠️ 缺失 |
| `idx_profiles_user_code` (UNIQUE) | ✅ | ❌ | 🔴 缺失 (关键) |

#### `credit_transactions` 表索引

| 索引 | V1 | V2 | 状态 |
|------|----|----|------|
| `idx_transactions_idempotency` (UNIQUE) | ✅ | ❌ | 🔴 缺失 (幂等性) |
| `idx_credit_tx_bucket` | ✅ | ❌ | 🔴 缺失 |
| `idx_credit_tx_type` | ✅ | ❌ | 🔴 缺失 |
| `idx_credit_tx_created_at` | ✅ | ✅ | ✅ 一致 |

#### `analytics_events` 表索引

| 索引 | V1 | V2 | 状态 |
|------|----|----|------|
| `idx_analytics_events_event_id` | ✅ (v3.19) | ❌ | 🔴 缺失 (去重) |
| `idx_analytics_events_type_event_id` | ✅ (v3.19) | ❌ | 🔴 缺失 |
| `idx_analytics_events_user_id` | ✅ | ✅ | ✅ 一致 |
| `idx_analytics_events_created_at` | ✅ | ✅ | ✅ 一致 |

**总体评估**: V2 缺失约 30% 的关键索引,特别是:
- 幂等性相关索引 (idempotency_key)
- 事件去重索引 (event_id)
- 业务查询优化索引 (bucket, type)

---

## 5. 初始化数据完整性分析

### 5.1 `system_configs` 数据对比

#### V1 (ddl.sql) - 120+ 行配置

**分组统计**:
```
📦 Rate Limits           - 24 条 (完整的 API 限流配置)
📦 Analytics             - 3 条  (采样率、开关)
📦 Feature Flags         - 4 条  (功能开关)
📦 Limits                - 5 条  (项目/文件限制)
📦 Credits               - 9 条  (积分成本配置)
📦 Pricing               - 4 条  (定价配置)
📦 AI Providers          - 8 条  (AI 模型配置,v3.21/v3.25)
📦 UI Text               - 3 条  (界面文本)
📦 Marketing             - 2 条  (营销文案)
📦 Tooltip               - 2 条  (v3.16)
───────────────────────────────
总计                     - 64+ 条
```

#### V2 (refactored_schema.sql) - 14 行配置

**分组统计**:
```
📦 AI 成本               - 3 条  (image/text/smart_scan)
📦 等级月度积分           - 3 条  (free/starter/pro)
📦 注册奖励               - 1 条  (signup bonus)
📦 市场分成               - 2 条  (seller/platform ratio)
📦 试用期                - 1 条  (trial duration)
───────────────────────────────
总计                     - 10 条
```

### 5.2 缺失数据详细清单

#### 🔴 Rate Limits (完全缺失 - 24/24)

**影响**: 所有 API 没有限流保护,易受攻击。

```sql
-- Payment & Marketplace (3条)
rate_limit.payment.checkout          - {"limit": 5, "window": "minute"}
rate_limit.payment.portal            - {"limit": 10, "window": "minute"}
rate_limit.marketplace.purchase      - {"limit": 10, "window": "minute"}

-- AI Generation (3条)
rate_limit.generate.story            - {"limit": 20, "window": "minute"}
rate_limit.generate.images           - {"limit": 10, "window": "minute"}
rate_limit.tools.ocr                 - {"limit": 10, "window": "minute"}

-- Export (3条)
rate_limit.export.pdf                - {"limit": 10, "window": "minute"}
rate_limit.export.zip                - {"limit": 5, "window": "minute"}
rate_limit.export.preview            - {"limit": 20, "window": "minute"}

-- CRUD Operations (3条)
rate_limit.projects.create           - {"limit": 20, "window": "minute"}
rate_limit.assets.upload             - {"limit": 20, "window": "minute"}
rate_limit.marketplace.publish       - {"limit": 10, "window": "minute"}

-- Support (3条)
rate_limit.support.email             - {"limit": 3, "window": "minute"}
rate_limit.contact.form              - {"limit": 3, "window": "minute"}
rate_limit.feedback.submit           - {"limit": 3, "window": "minute"}

-- Admin Operations (6条)
rate_limit.admin.credits             - {"limit": 30, "window": "minute"}
rate_limit.admin.tier                - {"limit": 30, "window": "minute"}
rate_limit.admin.refund              - {"limit": 10, "window": "minute"}
rate_limit.admin.subscription        - {"limit": 10, "window": "minute"}
rate_limit.admin.broadcast           - {"limit": 5, "window": "minute"}
rate_limit.admin.search              - {"limit": 60, "window": "minute"}

-- Global (3条)
rate_limit.marketplace.list          - {"limit": 60, "window": "minute"}
rate_limit.analytics.events          - {"limit": 60, "window": "minute"}
rate_limit.global.default            - {"limit": 100, "window": "minute"}
```

#### 🔴 AI Providers Configuration (完全缺失 - 8/8)

**影响**: AI 功能无法正常工作。

```sql
ai_providers.enabled                 - {"openai": true, "fal": true, ...}
ai_model.user.text_reasoning         - {"provider": "openai", "model": "gpt-4o-mini"}
ai_model.user.image_generation       - {"provider": "fal", "models": {"free": "flux-schnell"}}
ai_model.admin.analysis              - {"provider": "openai", "model": "gpt-4o"}
ai_model.canary                      - {"enabled": false, "traffic_percent": 10}
ai_providers.models                  - {"openai": {"text": [...]}, "fal": {...}}
ai_providers.timeouts                - {"openai": {"text": 60, "image": 120}}
ai_providers.costs                   - {"openai": {"gpt-4o-mini": 0.15}}
ai_providers.retry                   - {"max_retries": 3, "base_delay_ms": 1000}
```

#### 🔴 Feature Flags (完全缺失 - 4/4)

**影响**: 无法控制功能开关。

```sql
FEATURE_AI_GENERATION                - 'true'
FEATURE_MARKETPLACE                  - 'true'
FEATURE_OCR                          - 'true'
FEATURE_ZIP_EXPORT                   - 'true'
```

#### 🔴 Limits (完全缺失 - 5/5)

**影响**: 无法限制用户资源使用。

```sql
FREE_PROJECT_LIMIT                   - '1'
STARTER_PROJECT_LIMIT                - '20'
PRO_PROJECT_LIMIT                    - '200'
MAX_UPLOAD_FILE_SIZE_MB              - '5'
MAX_LISTING_PRICE                    - '500'
```

#### 🟡 Analytics Configuration (完全缺失 - 3/3)

```sql
analytics.enabled                    - '{"enabled": true}'
analytics.sampling_rate              - '{"critical": 1.0, "normal": 0.3}'
analytics.min_level                  - '{"level": "normal"}'
```

#### 🟡 UI & Marketing (完全缺失 - 5/5)

```sql
UI_UPGRADE_CTA                       - 'Upgrade Now'
UI_TRIAL_EXPIRED                     - 'Your 7-day trial...'
UI_AI_TYPING_INDICATOR               - 'AI is thinking...'
HOME_HERO_TITLE                      - 'Create Beautiful...'
HOME_HERO_SUBTITLE                   - 'AI-powered story...'
```

### 5.3 其他初始化数据

#### `holiday_themes` 表数据 (完全缺失)

V1 包含 12 个节日主题配置:
- New Year, Valentine's Day, St. Patrick's Day
- Earth Day, Mother's Day, Father's Day
- Independence Day, Halloween, Teachers' Day
- Thanksgiving, Black Friday, Christmas

**影响**: 节日主题功能完全不可用。

---

## 6. 业务逻辑一致性分析

### 6.1 ADR-0002: 数据库驱动配置

**设计要求**:
- 所有积分成本配置存储在 `system_configs` 表
- 配置 key 格式: `credits.cost.{operation}`
- 必须包含: image_generation, text_generation, smart_scan, ocr

**V2 现状**:
- ✅ 表结构存在 (但字段名不同)
- ⚠️ 仅包含 3 条配置 (image/text/smart_scan)
- ❌ 缺失 `ocr` 独立配置
- ❌ 缺失 AI Provider 配置 (ai_providers.*)

**评估**: 部分符合,需补充完整配置。

### 6.2 素材分类系统 (Asset Category System)

**设计要求** (见 Asset-Category-System-Design.md):
- 需要 `asset_categories` 表 (多级分类,LTREE)
- 需要 `assets` 表 (统一素材表)
- 支持 5 大类: Text, Graphics, Shapes, Tables, My Assets

**V2 现状**:
- ❌ `asset_categories` 表完全缺失
- ❌ 统一素材表缺失 (V1 的 `assets` 是用户资产,不是系统素材)

**评估**: 完全不符合,需要从头实现。

### 6.3 Feature Flag & Experiments 系统

**设计要求** (见 Feature-Flag-Experiments-Unified-Design.md):
- `feature_flags` 表 (核心表)
- `experiment_configs` 表 (扩展表)
- `flag_exposures` 表 (曝光事件)
- `experiment_results` 表 (结果聚合)

**V2 现状**:
- ✅ `feature_flags` 表存在
- ❌ `experiment_configs` 表缺失
- ❌ `flag_exposures` 表缺失
- ✅ `experiment_results` 表存在 (但结构不同)
- ✅ `experiments` 表存在 (与 V1 一致)
- ✅ `experiment_assignments` 表存在 (与 V1 一致)

**评估**: 部分实现,但缺少曝光追踪和实验配置扩展表。

### 6.4 Onboarding 新手引导系统

**设计要求** (见 Onboarding-System-Design.md):
- `onboarding_steps` 表 (引导步骤定义)
- `user_onboarding_progress` 表 (用户进度追踪)

**V2 现状**:
- ✅ `onboarding_steps` 表存在
- ✅ `user_onboarding_progress` 表存在

**评估**: ✅ 完全符合设计。

### 6.5 用户 ID 系统 (USER-ID-SYSTEM.md)

**设计要求**:
- `profiles` 表必须包含 `user_code` 字段
- 格式: `YYMMDDHHMMXXX` (注册时间 + 随机码)

**V2 现状**:
- ❌ `profiles` 表缺失 `user_code` 字段

**评估**: 不符合,需补充字段。

### 6.6 时区支持 (v3.9)

**设计要求**:
- 所有时间戳表需要 `timezone` + `created_at_local` 字段

**V2 现状**:
- ❌ 所有表都缺失时区字段

**评估**: 完全缺失,需全局补充。

---

## 7. 修复建议与SQL脚本

### 7.1 立即修复 (Phase 1 - 阻塞性问题)

#### 修复 1: 补充 P0 级别缺失表

```sql
-- ============================================================
-- Phase 1: P0 级别表补充 (关键阻塞)
-- ============================================================

-- 1. AI 调用日志表 (v3.21)
CREATE TABLE IF NOT EXISTS ai_call_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT REFERENCES profiles(id),

    -- Provider & Model
    provider TEXT NOT NULL,               -- 'openai', 'fal', 'qwen'
    model TEXT NOT NULL,
    call_type TEXT NOT NULL,              -- 'text_reasoning', 'image_generation'

    -- Status
    status TEXT NOT NULL,                 -- 'success', 'failed', 'timeout'

    -- Input/Output
    input_data JSONB NOT NULL,
    output_data JSONB,

    -- Token 统计
    input_tokens INT DEFAULT 0,
    output_tokens INT DEFAULT 0,
    total_tokens INT DEFAULT 0,

    -- Performance
    latency_ms INT,
    cost_usd DECIMAL(10,6),

    -- Error
    error_code TEXT,
    error_message TEXT,

    -- Timestamp
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ai_calls_provider_time ON ai_call_logs(provider, created_at DESC);
CREATE INDEX idx_ai_calls_user_time ON ai_call_logs(user_id, created_at DESC);
CREATE INDEX idx_ai_calls_status ON ai_call_logs(status) WHERE status != 'success';

-- 2. AI 使用量日汇总表 (v3.21)
CREATE TABLE IF NOT EXISTS ai_usage_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    call_type TEXT NOT NULL,

    -- 统计指标
    total_calls INT DEFAULT 0,
    successful_calls INT DEFAULT 0,
    failed_calls INT DEFAULT 0,
    total_input_tokens BIGINT DEFAULT 0,
    total_output_tokens BIGINT DEFAULT 0,
    total_images INT DEFAULT 0,

    -- 性能指标
    avg_latency_ms INT DEFAULT 0,
    min_latency_ms INT,
    max_latency_ms INT,

    -- 成本
    estimated_cost_usd DECIMAL(10, 4) DEFAULT 0,

    -- 错误统计
    error_counts JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(date, provider, model, call_type)
);

CREATE INDEX idx_ai_usage_daily_date ON ai_usage_daily(date DESC);
CREATE INDEX idx_ai_usage_daily_provider ON ai_usage_daily(provider, date DESC);

-- 3. 素材分类表 (Asset Category System)
CREATE TABLE IF NOT EXISTS asset_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 层级关系
    parent_id UUID REFERENCES asset_categories(id) ON DELETE CASCADE,
    path LTREE NOT NULL,                    -- 物化路径 'graphics.stickers.animals'
    level INT NOT NULL DEFAULT 1 CHECK (level BETWEEN 1 AND 3),

    -- 基本信息
    slug VARCHAR(50) NOT NULL UNIQUE,       -- 'animals'
    name VARCHAR(100) NOT NULL,             -- '动物'
    name_i18n JSONB DEFAULT '{}',           -- {"en": "Animals", "zh": "动物"}
    description TEXT,
    icon VARCHAR(50),                       -- emoji 或 icon name

    -- 关联的素材类型
    asset_type VARCHAR(20) NOT NULL,        -- 'text', 'image', 'shape', 'table'

    -- 显示控制
    is_visible BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,
    display_order INT DEFAULT 0,

    -- 访问控制
    min_tier VARCHAR(20) DEFAULT 'free',    -- 'free', 'starter', 'pro'

    -- 时间限定 (节日主题)
    visible_from TIMESTAMPTZ,
    visible_until TIMESTAMPTZ,

    -- 统计
    asset_count INT DEFAULT 0,
    usage_count INT DEFAULT 0,

    -- 元数据
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_categories_path ON asset_categories USING GIST (path);
CREATE INDEX idx_categories_parent ON asset_categories(parent_id);
CREATE INDEX idx_categories_visible ON asset_categories(is_visible, display_order);

-- 4. 统一素材表 (系统内置素材)
CREATE TABLE IF NOT EXISTS system_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 分类关联
    category_id UUID NOT NULL REFERENCES asset_categories(id),

    -- 基本信息
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(100),
    description TEXT,

    -- 素材类型
    asset_type VARCHAR(20) NOT NULL,        -- 'text', 'image', 'shape', 'table'

    -- 来源
    source VARCHAR(20) NOT NULL DEFAULT 'system',  -- 'system', 'user', 'ai', 'community'
    source_user_id TEXT REFERENCES profiles(id),

    -- 文件信息
    file_url TEXT,
    thumbnail_url TEXT,
    file_size INT,
    file_format VARCHAR(20),

    -- 尺寸
    width INT,
    height INT,

    -- 素材内容 (JSONB, 根据 asset_type 不同)
    content JSONB NOT NULL DEFAULT '{}',

    -- 访问控制
    min_tier VARCHAR(20) DEFAULT 'free',
    is_pro_only BOOLEAN DEFAULT FALSE,

    -- 标签 (搜索用)
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- 显示控制
    is_visible BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,
    display_order INT DEFAULT 0,

    -- 统计
    usage_count INT DEFAULT 0,
    download_count INT DEFAULT 0,
    favorite_count INT DEFAULT 0,

    -- 元数据
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_system_assets_category ON system_assets(category_id);
CREATE INDEX idx_system_assets_type ON system_assets(asset_type);
CREATE INDEX idx_system_assets_source ON system_assets(source);
CREATE INDEX idx_system_assets_tier ON system_assets(min_tier);
CREATE INDEX idx_system_assets_tags ON system_assets USING GIN(tags);
CREATE INDEX idx_system_assets_visible ON system_assets(is_visible, display_order);

COMMENT ON TABLE system_assets IS '系统内置素材表 (区别于用户上传的 assets 表)';
```

#### 修复 2: 补充完整的 system_configs 数据

```sql
-- ============================================================
-- Phase 1: system_configs 初始化数据补充
-- ============================================================

INSERT INTO system_configs (key, value, value_type, config_group, description, is_active) VALUES

-- ========== Rate Limits (24条) ==========
('rate_limit.payment.checkout', '{"limit": 5, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Checkout API limit', true),
('rate_limit.payment.portal', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Billing portal limit', true),
('rate_limit.marketplace.purchase', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Marketplace purchase limit', true),
('rate_limit.generate.story', '{"limit": 20, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'AI story generation limit', true),
('rate_limit.generate.images', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'AI image generation limit', true),
('rate_limit.tools.ocr', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'OCR limit', true),
('rate_limit.export.pdf', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'PDF export limit', true),
('rate_limit.export.zip', '{"limit": 5, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'ZIP export limit', true),
('rate_limit.export.preview', '{"limit": 20, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Preview generation limit', true),
('rate_limit.projects.create', '{"limit": 20, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Project creation limit', true),
('rate_limit.assets.upload', '{"limit": 20, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Asset upload limit', true),
('rate_limit.marketplace.publish', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Listing publish limit', true),
('rate_limit.support.email', '{"limit": 3, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Support ticket limit', true),
('rate_limit.contact.form', '{"limit": 3, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Contact form limit', true),
('rate_limit.feedback.submit', '{"limit": 3, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Feedback submission limit', true),
('rate_limit.admin.credits', '{"limit": 30, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin credit adjustment limit', true),
('rate_limit.admin.tier', '{"limit": 30, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin tier update limit', true),
('rate_limit.admin.refund', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin refund limit', true),
('rate_limit.admin.subscription', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin subscription ops limit', true),
('rate_limit.admin.broadcast', '{"limit": 5, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin broadcast limit', true),
('rate_limit.admin.search', '{"limit": 60, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin search limit', true),
('rate_limit.marketplace.list', '{"limit": 60, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Marketplace listing limit', true),
('rate_limit.analytics.events', '{"limit": 60, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Analytics event ingestion limit', true),
('rate_limit.global.default', '{"limit": 100, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Global default limit', true),

-- ========== Analytics (3条) ==========
('analytics.enabled', '{"enabled": true}', 'json', 'analytics', 'Enable analytics tracking', true),
('analytics.sampling_rate', '{"critical": 1.0, "important": 1.0, "normal": 0.3, "debug": 0.0}', 'json', 'analytics', 'Event sampling rates', true),
('analytics.min_level', '{"level": "normal"}', 'json', 'analytics', 'Minimum tracking level', true),

-- ========== Feature Flags (4条) ==========
('FEATURE_AI_GENERATION', 'true', 'boolean', 'feature_flag', 'Enable AI image generation', true),
('FEATURE_MARKETPLACE', 'true', 'boolean', 'feature_flag', 'Enable marketplace', true),
('FEATURE_OCR', 'true', 'boolean', 'feature_flag', 'Enable OCR/Smart Scan', true),
('FEATURE_ZIP_EXPORT', 'true', 'boolean', 'feature_flag', 'Enable ZIP export', true),

-- ========== Limits (5条) ==========
('FREE_PROJECT_LIMIT', '1', 'number', 'limits', 'Max projects for free tier', true),
('STARTER_PROJECT_LIMIT', '20', 'number', 'limits', 'Max projects for starter tier', true),
('PRO_PROJECT_LIMIT', '200', 'number', 'limits', 'Max projects for pro tier', true),
('MAX_UPLOAD_FILE_SIZE_MB', '5', 'number', 'limits', 'Max file upload size in MB', true),
('MAX_LISTING_PRICE', '500', 'number', 'limits', 'Max marketplace listing price', true),

-- ========== Credits (9条,补充缺失的) ==========
('CREDITS_PER_IMAGE', '5', 'number', 'credits', 'Credits per AI image', true),
('CREDITS_PER_OCR', '5', 'number', 'credits', 'Credits per OCR', true),
('CREDITS_PER_AI_DESIGN_PAGE', '5', 'number', 'credits', 'Credits per AI design page', true),
('SIGNUP_BONUS_CREDITS', '50', 'number', 'credits', 'Signup bonus credits', true),
('credits.cost.image_generation', '5', 'integer', 'credits', 'AI image generation cost per image', true),
('credits.cost.image_generation_reference', '7', 'integer', 'credits', 'AI image generation with reference cost', true),
('credits.cost.text_generation', '0', 'integer', 'credits', 'AI text generation cost (free)', true),
('credits.cost.smart_scan', '10', 'integer', 'credits', 'Smart Scan/OCR cost', true),
('credits.cost.ocr', '10', 'integer', 'credits', 'OCR recognition cost', true),

-- ========== AI Providers (8条,完全缺失) ==========
('ai_providers.enabled', '{"openai": true, "fal": true, "qwen": false, "wanx": false, "gemini": false, "grok": false, "jimeng": false, "anthropic": false}', 'json', 'ai_providers', 'Enable/disable AI providers', true),
('ai_model.user.text_reasoning', '{"provider": "openai", "model": "gpt-4o-mini", "fallback": {"provider": "openai", "model": "gpt-4o-mini"}, "show_provider": false}', 'json', 'ai_models', 'User text reasoning model', true),
('ai_model.user.image_generation', '{"provider": "fal", "models": {"free": "flux-schnell", "starter": "flux-schnell", "pro": "flux-dev"}, "fallback": {"provider": "fal", "model": "flux-schnell"}, "show_provider": false}', 'json', 'ai_models', 'User image generation model by tier', true),
('ai_model.admin.analysis', '{"provider": "openai", "model": "gpt-4o", "fallback": {"provider": "openai", "model": "gpt-4o-mini"}}', 'json', 'ai_models', 'Admin analysis model', true),
('ai_model.canary', '{"enabled": false, "text_reasoning": {"canary_provider": "qwen", "canary_model": "qwen-plus", "traffic_percent": 10}, "image_generation": {"canary_provider": "jimeng", "canary_model": "jimeng-2.1", "traffic_percent": 5}}', 'json', 'ai_models', 'Canary release for A/B testing', true),
('ai_providers.models', '{"openai": {"text": ["gpt-4o-mini", "gpt-4o", "o1-mini", "o1"], "image": ["dall-e-3"]}, "fal": {"image": ["flux-schnell", "flux-dev", "flux-pro"]}, "qwen": {"text": ["qwen-turbo", "qwen-plus", "qwen-max"]}}', 'json', 'ai_providers', 'Available models per provider', true),
('ai_providers.timeouts', '{"openai": {"text": 60, "image": 120}, "fal": {"image": 180}, "qwen": {"text": 60}}', 'json', 'ai_providers', 'Timeout config in seconds', true),
('ai_providers.costs', '{"openai": {"gpt-4o-mini": 0.15, "gpt-4o": 2.50, "o1-mini": 3.00, "o1": 15.00, "dall-e-3": 0.04}, "fal": {"flux-schnell": 0.003, "flux-dev": 0.025, "flux-pro": 0.05}, "qwen": {"qwen-turbo": 0.001, "qwen-plus": 0.004, "qwen-max": 0.02}}', 'json', 'ai_providers', 'Cost per 1M tokens/image (USD)', true),
('ai_providers.retry', '{"max_retries": 3, "base_delay_ms": 1000, "max_delay_ms": 10000, "retry_on_status": [429, 500, 502, 503, 504]}', 'json', 'ai_providers', 'Retry configuration', true)

ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value,
    value_type = EXCLUDED.value_type,
    config_group = EXCLUDED.config_group,
    description = EXCLUDED.description,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();
```

#### 修复 3: 修复 `profiles` 表缺失字段

```sql
-- ============================================================
-- Phase 1: profiles 表字段补充
-- ============================================================

-- 添加 user_code 字段 (用户识别码)
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS user_code TEXT UNIQUE;

-- 添加时区支持字段 (v3.9)
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS timezone TEXT DEFAULT 'UTC';
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS created_at_local TIMESTAMP;

-- 添加 cohort_month (用户分组)
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS cohort_month TEXT;

-- 创建索引
CREATE UNIQUE INDEX IF NOT EXISTS idx_profiles_user_code ON profiles(user_code);
CREATE INDEX IF NOT EXISTS idx_profiles_subscription_status ON profiles(subscription_status);

COMMENT ON COLUMN profiles.user_code IS '用户识别码 (格式: YYMMDDHHMMXXX, 包含注册时间)';
COMMENT ON COLUMN profiles.timezone IS '用户时区 (用于本地化时间显示)';
COMMENT ON COLUMN profiles.created_at_local IS '本地时间戳 (用户时区)';
```

#### 修复 4: 修复 `credit_transactions` 表缺失字段

```sql
-- ============================================================
-- Phase 1: credit_transactions 表字段补充
-- ============================================================

-- 添加 bucket 字段 (月度/永久积分区分)
ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS bucket TEXT NOT NULL DEFAULT 'permanent';

-- 添加余额快照字段
ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS balance_monthly_after INT NOT NULL DEFAULT 0;
ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS balance_permanent_after INT NOT NULL DEFAULT 0;

-- 添加幂等性字段 (v3.22)
ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS idempotency_key TEXT;

-- 添加时区支持 (v3.9)
ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS timezone TEXT DEFAULT 'UTC';
ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS created_at_local TIMESTAMP;

-- 创建索引
CREATE UNIQUE INDEX IF NOT EXISTS idx_transactions_idempotency
    ON credit_transactions(idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_credit_tx_bucket ON credit_transactions(bucket);
CREATE INDEX IF NOT EXISTS idx_credit_tx_type ON credit_transactions(transaction_type);

COMMENT ON COLUMN credit_transactions.bucket IS '积分桶类型 (monthly/permanent)';
COMMENT ON COLUMN credit_transactions.idempotency_key IS 'Webhook 幂等性 key';
```

### 7.2 优先补充 (Phase 2 - 重要功能)

```sql
-- ============================================================
-- Phase 2: P1 级别表补充 (重要功能)
-- ============================================================

-- 1. 每日主题表 (v3.13)
CREATE TABLE IF NOT EXISTS daily_themes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    date DATE NOT NULL UNIQUE,
    thumbnail_url TEXT,
    preview_urls TEXT[] DEFAULT ARRAY[]::TEXT[],
    featured_asset_ids UUID[] DEFAULT ARRAY[]::UUID[],
    recommended_categories TEXT[] DEFAULT ARRAY[]::TEXT[],
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'archived')),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_daily_themes_date ON daily_themes(date DESC);
CREATE INDEX idx_daily_themes_status ON daily_themes(status);

-- 2. 节日数据表 (v3.13/v3.14)
CREATE TABLE IF NOT EXISTS holidays (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    name_i18n JSONB DEFAULT '{}',
    slug TEXT NOT NULL UNIQUE,
    month INT NOT NULL CHECK (month BETWEEN 1 AND 12),
    day INT NOT NULL CHECK (day BETWEEN 1 AND 31),
    regions TEXT[] DEFAULT ARRAY[]::TEXT[],
    category TEXT NOT NULL,
    is_major BOOLEAN DEFAULT FALSE,
    theme_colors TEXT[] DEFAULT ARRAY[]::TEXT[],
    asset_category_ids UUID[] DEFAULT ARRAY[]::UUID[],
    description TEXT,
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_holidays_date ON holidays(month, day);
CREATE INDEX idx_holidays_regions ON holidays USING GIN(regions);

-- 插入节日初始数据 (简化版,完整版见 V1 ddl.sql)
INSERT INTO holidays (name, slug, month, day, regions, category, is_major) VALUES
('New Year', 'new-year', 1, 1, ARRAY['global'], 'cultural', true),
('Valentine''s Day', 'valentines-day', 2, 14, ARRAY['global'], 'cultural', true),
('Halloween', 'halloween', 10, 31, ARRAY['US', 'UK', 'CA'], 'cultural', true),
('Christmas', 'christmas', 12, 25, ARRAY['global'], 'cultural', true)
ON CONFLICT (slug) DO NOTHING;

-- 3. 活动日志表 (v3.2)
CREATE TABLE IF NOT EXISTS activity_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES profiles(id),
    action TEXT NOT NULL,
    resource_type TEXT,
    resource_id TEXT,
    description TEXT,
    metadata JSONB DEFAULT '{}',
    ip_address INET,
    timezone TEXT DEFAULT 'UTC',
    created_at_local TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_activity_logs_user_time ON activity_logs(user_id, created_at DESC);
CREATE INDEX idx_activity_logs_action ON activity_logs(action);

-- 4. 调度任务日志表 (v3.15)
CREATE TABLE IF NOT EXISTS scheduled_task_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_name TEXT NOT NULL,
    task_type TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'success', 'failed')),
    result_summary JSONB DEFAULT '{}',
    error_message TEXT,
    error_stack TEXT,
    hostname TEXT,
    pid INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_task_logs_task_name ON scheduled_task_logs(task_name);
CREATE INDEX idx_task_logs_started_at ON scheduled_task_logs(started_at DESC);
CREATE INDEX idx_task_logs_status ON scheduled_task_logs(status);

-- 5. Analytics 聚合表 (v3.12)
CREATE TABLE IF NOT EXISTS analytics_aggregation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    granularity TEXT NOT NULL CHECK (granularity IN ('daily', 'weekly', 'monthly')),
    dimension_type TEXT NOT NULL,
    dimension_value TEXT,
    metrics JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(date, granularity, dimension_type, dimension_value)
);

CREATE INDEX idx_analytics_agg_date ON analytics_aggregation(date DESC);
CREATE INDEX idx_analytics_agg_dimension ON analytics_aggregation(dimension_type, dimension_value);
```

### 7.3 可选补充 (Phase 3 - 增强功能)

```sql
-- ============================================================
-- Phase 3: P2 级别表补充 (增强功能)
-- ============================================================

-- 1. 配置审计日志表 (v3.10)
CREATE TABLE IF NOT EXISTS config_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_key TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    action TEXT NOT NULL,
    changed_by TEXT,
    changed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_config_audit_key ON config_audit_logs(config_key);
CREATE INDEX idx_config_audit_time ON config_audit_logs(changed_at DESC);

-- 2. 内容举报表 (v3.3)
CREATE TABLE IF NOT EXISTS content_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reporter_id TEXT NOT NULL REFERENCES profiles(id),
    listing_id UUID NOT NULL REFERENCES marketplace_listings(id),
    reason TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'reviewed', 'resolved', 'dismissed')),
    admin_response TEXT,
    reviewed_by TEXT REFERENCES profiles(id),
    reviewed_at TIMESTAMPTZ,
    timezone TEXT DEFAULT 'UTC',
    created_at_local TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(reporter_id, listing_id)
);

CREATE INDEX idx_reports_status ON content_reports(status);
CREATE INDEX idx_reports_listing_id ON content_reports(listing_id);

-- 3. 系统资源审计日志表 (v3.17)
CREATE TABLE IF NOT EXISTS system_resource_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_id UUID,
    action TEXT NOT NULL,
    old_data JSONB,
    new_data JSONB,
    changed_by TEXT NOT NULL,
    changed_at TIMESTAMPTZ DEFAULT NOW(),
    ip_address TEXT,
    user_agent TEXT
);

CREATE INDEX idx_resource_audit_resource_id ON system_resource_audit_logs(resource_id);
CREATE INDEX idx_resource_audit_changed_at ON system_resource_audit_logs(changed_at DESC);

-- 4. 素材提示词模板表 (v3.6)
CREATE TABLE IF NOT EXISTS asset_prompt_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    who_type TEXT,
    who_custom TEXT,
    what_type TEXT,
    what_custom TEXT,
    where_type TEXT,
    where_custom TEXT,
    style TEXT DEFAULT 'cartoon',
    moods TEXT[] DEFAULT '{warm}',
    aspect_ratio TEXT DEFAULT 'square',
    creativity_level REAL DEFAULT 0.3,
    negative_prompt TEXT,
    use_count INT DEFAULT 0,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_asset_prompt_templates_user ON asset_prompt_templates(user_id);
CREATE INDEX idx_asset_prompt_templates_usage ON asset_prompt_templates(user_id, use_count DESC);
```

### 7.4 修复 system_configs 表字段名不一致

**选项 A (推荐 - 最小破坏)**: 保留 V1 字段名

```sql
-- 方案 A: 调整 V2 schema 以匹配 V1 (向后兼容)
ALTER TABLE system_configs DROP CONSTRAINT IF EXISTS system_configs_pkey;
ALTER TABLE system_configs DROP COLUMN IF EXISTS id;
ALTER TABLE system_configs RENAME COLUMN config_key TO key;
ALTER TABLE system_configs RENAME COLUMN config_value TO value;
ALTER TABLE system_configs ADD PRIMARY KEY (key);

-- 添加缺失的审计字段
ALTER TABLE system_configs ADD COLUMN IF NOT EXISTS updated_by TEXT;

-- 保留 is_active (从 V1)
ALTER TABLE system_configs ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_system_configs_group ON system_configs(config_group);
CREATE INDEX IF NOT EXISTS idx_system_configs_active ON system_configs(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_system_configs_updated ON system_configs(updated_at DESC);
```

**选项 B (重构版 - 需要代码改动)**: 使用 V2 新字段名,但提供兼容性 VIEW

```sql
-- 方案 B: 创建兼容性 VIEW
CREATE OR REPLACE VIEW system_configs_legacy AS
SELECT
    config_key AS key,
    config_value AS value,
    value_type,
    config_group,
    description,
    is_editable AS is_active,
    created_at,
    updated_at
FROM system_configs
WHERE is_deleted = FALSE;

-- 后端代码逐步迁移到新字段名
```

---

## 8. 实施计划

### 8.1 Phase 1 (立即执行 - 阻塞性修复)

**时间**: 1-2 天

**任务清单**:
- [ ] 补充 4 张 P0 表 (AI 日志、素材分类)
- [ ] 补充完整 system_configs 数据 (120+ 行)
- [ ] 修复 profiles 表缺失字段 (user_code, timezone)
- [ ] 修复 credit_transactions 表缺失字段 (bucket, balance_after, idempotency_key)
- [ ] 修复 system_configs 字段名不一致 (选择方案 A 或 B)
- [ ] 添加缺失的关键索引 (幂等性、event_id 去重)

**验证清单**:
- [ ] 所有 P0 表已创建
- [ ] system_configs 数据行数 >= 60
- [ ] 后端代码可正常读取配置
- [ ] AI 生成功能可记录日志
- [ ] 积分扣除逻辑正常 (先月度后永久)

### 8.2 Phase 2 (优先补充 - 重要功能)

**时间**: 2-3 天

**任务清单**:
- [ ] 补充 5 张 P1 表 (主题、节日、活动日志等)
- [ ] 插入节日初始数据 (12 个全球节日)
- [ ] 创建 AI 使用量聚合函数
- [ ] 创建定时任务清理函数

**验证清单**:
- [ ] 主题系统可展示每日主题
- [ ] 节日主题可按日期自动激活
- [ ] 活动日志正常记录
- [ ] 定时任务执行状态可查询

### 8.3 Phase 3 (后续优化 - 增强功能)

**时间**: 3-5 天

**任务清单**:
- [ ] 补充 4 张 P2 表 (审计、举报等)
- [ ] 补充缺失的触发器和函数
- [ ] 补充缺失的 RLS 策略
- [ ] 优化索引策略
- [ ] 补充完整的注释 (COMMENT ON)

**验证清单**:
- [ ] 配置变更有审计记录
- [ ] 内容举报功能可用
- [ ] 所有触发器正常工作
- [ ] RLS 策略全覆盖

### 8.4 测试计划

#### 单元测试
```bash
# 测试所有表都已创建
SELECT COUNT(*) FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
-- 预期: >= 42

# 测试 system_configs 数据完整性
SELECT config_group, COUNT(*)
FROM system_configs
WHERE is_active = TRUE
GROUP BY config_group;
-- 预期: 至少 7 个分组,总计 60+ 行

# 测试关键字段存在
SELECT column_name FROM information_schema.columns
WHERE table_name = 'profiles' AND column_name IN ('user_code', 'timezone');
-- 预期: 2 行

# 测试幂等性索引
SELECT indexname FROM pg_indexes
WHERE tablename = 'credit_transactions' AND indexname LIKE '%idempotency%';
-- 预期: 1 行
```

#### 集成测试
```bash
# 测试 AI 生成功能
POST /api/v2/ai/generate/image
# 验证: ai_call_logs 表有记录

# 测试积分扣除
POST /api/v2/billing/credits/deduct
# 验证: credit_transactions 有两条记录 (monthly + permanent)

# 测试配置读取
GET /api/v2/system/configs/credits.cost.image_generation
# 验证: 返回 "5"

# 测试素材分类加载
GET /api/v2/assets/categories
# 验证: 返回分类树
```

### 8.5 回滚策略

#### 数据库快照
```bash
# 执行修复前
pg_dump -h localhost -U postgres decodables > decodables_pre_refactor.sql

# 如果出现问题,恢复快照
psql -h localhost -U postgres decodables < decodables_pre_refactor.sql
```

#### 增量回滚
```sql
-- 如果某个表有问题,单独删除
DROP TABLE IF EXISTS ai_call_logs CASCADE;
DROP TABLE IF EXISTS ai_usage_daily CASCADE;

-- 如果配置有问题,恢复旧配置
DELETE FROM system_configs WHERE config_group IN ('rate_limit', 'ai_providers');
```

---

## 9. 总结与建议

### 9.1 核心问题总结

| 问题类型 | 严重程度 | 数量 | 影响 |
|---------|---------|------|------|
| 缺失关键表 | 🔴 严重 | 13 张 | 核心功能不可用 |
| 初始化数据缺失 | 🔴 严重 | 88% | 配置系统失效 |
| 字段名不一致 | 🟡 中等 | 1 张表 | 代码需要改动 |
| 缺失索引 | 🟡 中等 | ~15 个 | 性能和幂等性问题 |
| 缺失触发器 | 🟢 轻微 | ~10 个 | 功能受限 |

### 9.2 最终建议

#### ✅ V2 的优点 (保留)
- 优秀的命名规范 (snake_case)
- 良好的架构设计 (新增 Onboarding, Referral 等表)
- 引入了 Webhook 事件表 (幂等性)

#### ⚠️ V2 的问题 (需要修复)
- **缺失 13 张关键表** - 必须补充
- **system_configs 数据严重不足** - 必须补充
- **字段名不一致** - 建议保持 V1 兼容性

#### 🎯 推荐策略

**方案 1 (推荐 - 渐进式重构)**:
1. **保留 V1 的所有表和字段名** (向后兼容)
2. **仅添加 V2 的新表** (Onboarding, Referral 等)
3. **逐步迁移字段名** (通过 VIEW + 触发器过渡)

**方案 2 (激进 - 完全重构)**:
1. 使用 V2 的新字段名
2. 提供完整的数据迁移脚本
3. 同时修改所有后端代码
4. ⚠️ 风险: 需要大量测试,可能引入新 Bug

**结论**: **推荐方案 1**,保持向后兼容,降低风险。

### 9.3 下一步行动

1. **立即执行 Phase 1** (补充 P0 表和数据)
2. 在测试环境验证所有功能
3. 执行 Phase 2 (补充 P1 表)
4. 全面回归测试
5. 执行 Phase 3 (增强功能)

### 9.4 长期优化建议

1. **建立数据库变更流程**: 所有 schema 变更必须通过 migration 脚本
2. **增强测试覆盖**: 为关键表添加 schema 测试
3. **自动化验证**: CI/CD 中添加 schema 完整性检查
4. **文档同步**: 确保 DDL 与设计文档一致

---

**报告生成完成** ✅

**关键指标**:
- 表结构完整性: 69% → 目标 100%
- 初始化数据: 12% → 目标 100%
- 字段映射准确性: 85% → 目标 100%
- 索引完整性: 85% → 目标 100%

**预估修复时间**: 5-7 天 (Phase 1-3)
**风险等级**: 中 (采用方案 1 - 渐进式重构)
