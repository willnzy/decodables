# 数据库重构设计评估报告

> **日期**: 2026-01-09
> **评估人**: Senior Database Architect
> **评估范围**: refactored_schema.sql vs 当前系统文档和 ddl.sql

---

## 一、评估总结

### 1.1 整体评估结果

| 评估维度 | 评分 | 状态 |
|---------|------|------|
| **命名规范一致性** | ✅ 95% | 优秀 |
| **业务规则完整性** | ⚠️ 75% | 需要补充 |
| **表结构完整性** | ⚠️ 70% | 缺失关键表 |
| **初始数据完整性** | ❌ 30% | 严重缺失 |
| **索引策略** | ✅ 90% | 优秀 |
| **触发器逻辑** | ✅ 85% | 良好 |

**总体结论**: 重构SQL在架构设计和命名规范上表现优秀，但**缺失大量业务必需的表和初始化数据**，需要重大修订。

---

## 二、核心问题分析

### 2.1 🔴 严重问题：缺失关键业务表

根据当前 ddl.sql (v3.27) 和设计文档，以下表在 refactored_schema.sql 中**完全缺失**：

#### A. AI 相关表 (Critical)

```sql
-- ❌ 缺失: ai_call_logs (v3.21) - AI 调用日志表
-- 用途: 记录所有 AI API 调用（OpenAI, FAL, Qwen 等）
-- 重要性: 🔴 成本追踪、性能监控、故障排查

CREATE TABLE ai_call_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT REFERENCES profiles(id),
    provider TEXT NOT NULL,               -- 'openai', 'fal', 'qwen', etc.
    model TEXT NOT NULL,
    call_type TEXT NOT NULL,              -- 'text_reasoning', 'image_generation'
    status TEXT NOT NULL,                 -- 'success', 'failed', 'timeout'

    -- 输入/输出
    input_data JSONB NOT NULL,
    output_data JSONB,

    -- Token 统计
    input_tokens INT DEFAULT 0,
    output_tokens INT DEFAULT 0,
    total_tokens INT DEFAULT 0,

    -- 性能
    latency_ms INT,
    cost_usd DECIMAL(10,6),

    -- 错误信息
    error_code TEXT,
    error_message TEXT,

    -- 时间
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- 索引
    INDEX idx_ai_calls_provider_time (provider, created_at DESC),
    INDEX idx_ai_calls_user_time (user_id, created_at DESC),
    INDEX idx_ai_calls_status (status) WHERE status != 'success'
);

-- ❌ 缺失: ai_usage_daily (v3.25) - AI 使用量日汇总表
-- 用途: 每日 AI 使用量聚合统计
-- 重要性: 🔴 成本分析、容量规划

CREATE TABLE ai_usage_daily (
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
```

#### B. 素材分类系统 (Critical)

根据 `[重构后]Asset-Category-System-Design.md`，需要以下表：

```sql
-- ❌ 缺失: asset_categories - 素材分类表
-- 用途: 支持多级分类的树形结构（Graphics/Stickers/Animals）
-- 重要性: 🔴 核心业务功能

CREATE TABLE asset_categories (
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

-- ❌ 缺失: assets - 统一素材表
-- 用途: 存储所有类型的素材（Emoji, Stickers, Shapes, Tables）
-- 重要性: 🔴 核心业务功能

CREATE TABLE assets (
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

CREATE INDEX idx_assets_category ON assets(category_id);
CREATE INDEX idx_assets_type ON assets(asset_type);
CREATE INDEX idx_assets_source ON assets(source);
CREATE INDEX idx_assets_tier ON assets(min_tier);
CREATE INDEX idx_assets_tags ON assets USING GIN(tags);
CREATE INDEX idx_assets_visible ON assets(is_visible, display_order);
```

#### C. 主题与节日系统 (Important)

根据 `[重构后]Theme-Daily-Doodle-Design.md` 和 v3.13 迁移：

```sql
-- ❌ 缺失: daily_themes - 每日主题表
-- 用途: 每日涂鸦主题配置
-- 重要性: 🟡 产品特色功能

CREATE TABLE daily_themes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 主题信息
    title TEXT NOT NULL,
    description TEXT,
    date DATE NOT NULL UNIQUE,

    -- 视觉资源
    thumbnail_url TEXT,
    preview_urls TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- 素材关联
    featured_asset_ids UUID[] DEFAULT ARRAY[]::UUID[],
    recommended_categories TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- 标签
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- 状态
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'archived')),

    -- 元数据
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_daily_themes_date ON daily_themes(date DESC);
CREATE INDEX idx_daily_themes_status ON daily_themes(status);

-- ❌ 缺失: holidays - 节日数据表
-- 用途: 全球节日数据库（用于节日主题素材展示）
-- 重要性: 🟡 产品特色功能

CREATE TABLE holidays (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 节日信息
    name TEXT NOT NULL,
    name_i18n JSONB DEFAULT '{}',
    slug TEXT NOT NULL,

    -- 日期
    month INT NOT NULL CHECK (month BETWEEN 1 AND 12),
    day INT NOT NULL CHECK (day BETWEEN 1 AND 31),

    -- 地区
    regions TEXT[] DEFAULT ARRAY[]::TEXT[],  -- ['US', 'UK', 'global']

    -- 类型
    category TEXT NOT NULL,                  -- 'cultural', 'educational', 'commercial'
    is_major BOOLEAN DEFAULT FALSE,

    -- 主题色
    theme_colors TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- 关联素材
    asset_category_ids UUID[] DEFAULT ARRAY[]::UUID[],

    -- 元数据
    description TEXT,
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(slug)
);

CREATE INDEX idx_holidays_date ON holidays(month, day);
CREATE INDEX idx_holidays_regions ON holidays USING GIN(regions);
```

#### D. Analytics 聚合表 (Important)

根据 v3.11 和 v3.12 迁移：

```sql
-- ❌ 缺失: user_events - 用户事件表
-- 用途: 记录用户关键行为事件（区别于 analytics_events）
-- 重要性: 🟡 用户行为分析

CREATE TABLE user_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES profiles(id),

    -- 事件信息
    event_name TEXT NOT NULL,
    event_category TEXT,
    event_properties JSONB DEFAULT '{}',

    -- 会话
    session_id TEXT,

    -- 元数据
    device_type TEXT,
    browser TEXT,
    os TEXT,
    country TEXT,
    referrer TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_user_events_user_time ON user_events(user_id, created_at DESC);
CREATE INDEX idx_user_events_name ON user_events(event_name);

-- ❌ 缺失: activity_logs - 用户活动日志表
-- 用途: 轻量级活动记录（区别于 analytics_events 的详细事件）
-- 重要性: 🟡 管理员审计、用户活动追踪

CREATE TABLE activity_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES profiles(id),

    -- 活动信息
    action TEXT NOT NULL,                    -- 'project_created', 'listing_published'
    resource_type TEXT,                      -- 'project', 'listing'
    resource_id TEXT,

    -- 详情
    description TEXT,
    metadata JSONB DEFAULT '{}',

    -- IP
    ip_address INET,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_activity_logs_user_time ON activity_logs(user_id, created_at DESC);
CREATE INDEX idx_activity_logs_action ON activity_logs(action);

-- ❌ 缺失: analytics_aggregation - Analytics 聚合表
-- 用途: 预聚合的分析数据（日、周、月维度）
-- 重要性: 🟡 Dashboard 性能优化

CREATE TABLE analytics_aggregation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 维度
    date DATE NOT NULL,
    granularity TEXT NOT NULL CHECK (granularity IN ('daily', 'weekly', 'monthly')),
    dimension_type TEXT NOT NULL,            -- 'user', 'project', 'event', 'global'
    dimension_value TEXT,                    -- user_id, event_name, etc.

    -- 指标
    metrics JSONB NOT NULL DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(date, granularity, dimension_type, dimension_value)
);

CREATE INDEX idx_analytics_agg_date ON analytics_aggregation(date DESC);
CREATE INDEX idx_analytics_agg_dimension ON analytics_aggregation(dimension_type, dimension_value);
```

#### E. 任务队列与调度系统 (Important)

根据 v3.15 和 v3.23 迁移：

```sql
-- ❌ 缺失: scheduled_task_logs - 调度任务日志表
-- 用途: 记录定时任务执行状态（刷新物化视图、清理过期数据等）
-- 重要性: 🟡 运维监控

CREATE TABLE scheduled_task_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 任务信息
    task_name TEXT NOT NULL,
    task_type TEXT NOT NULL,                 -- 'refresh_materialized_view', 'cleanup_expired_data'

    -- 执行状态
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'success', 'failed')),

    -- 时间
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_ms INT,

    -- 结果
    result_message TEXT,
    error_message TEXT,
    rows_affected INT,

    -- 元数据
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_scheduled_tasks_name_time ON scheduled_task_logs(task_name, created_at DESC);
CREATE INDEX idx_scheduled_tasks_status ON scheduled_task_logs(status);
```

#### F. 其他系统表 (Normal)

```sql
-- ❌ 缺失: config_audit_logs - 配置审计日志表 (v3.10)
-- 重要性: 🟢 配置变更审计

CREATE TABLE config_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_key TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    action TEXT NOT NULL,                    -- 'create', 'update', 'delete'
    changed_by TEXT,
    changed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_config_audit_key ON config_audit_logs(config_key);
CREATE INDEX idx_config_audit_time ON config_audit_logs(changed_at DESC);

-- ❌ 缺失: content_reports - 内容举报表
-- 重要性: 🟢 内容审核

CREATE TABLE content_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reporter_id TEXT NOT NULL REFERENCES profiles(id),
    listing_id UUID NOT NULL REFERENCES marketplace_listings(id),

    -- 举报信息
    reason TEXT NOT NULL,
    description TEXT,

    -- 状态
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'reviewed', 'resolved', 'dismissed')),

    -- 审核
    admin_response TEXT,
    reviewed_by TEXT REFERENCES profiles(id),
    reviewed_at TIMESTAMPTZ,

    -- 时区字段 (v3.9)
    timezone TEXT DEFAULT 'UTC',
    created_at_local TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(reporter_id, listing_id)
);

CREATE INDEX idx_reports_status ON content_reports(status);
CREATE INDEX idx_reports_listing_id ON content_reports(listing_id);

-- ❌ 缺失: tooltip_configs - Tooltip 配置表 (v3.16)
-- 重要性: 🟢 UI 配置

CREATE TABLE tooltip_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 标识
    key TEXT NOT NULL UNIQUE,

    -- 内容
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    content_i18n JSONB DEFAULT '{}',

    -- 显示控制
    is_active BOOLEAN DEFAULT TRUE,
    target_selector TEXT,                    -- CSS selector
    position TEXT DEFAULT 'top',

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tooltip_configs_active ON tooltip_configs(is_active) WHERE is_active = TRUE;

-- ❌ 缺失: seller_stats - 卖家统计表
-- 重要性: 🟢 性能优化（冗余字段的替代方案）

CREATE TABLE seller_stats (
    user_id TEXT PRIMARY KEY REFERENCES profiles(id),

    -- 统计指标
    total_listings INT DEFAULT 0,
    approved_listings INT DEFAULT 0,
    total_sales INT DEFAULT 0,
    total_revenue_credits INT DEFAULT 0,

    -- 评分
    average_rating DECIMAL(3,2),
    total_reviews INT DEFAULT 0,

    -- 时间
    last_listing_at TIMESTAMPTZ,
    last_sale_at TIMESTAMPTZ,

    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

### 2.2 🟡 中等问题：缺失初始化数据

refactored_schema.sql 中 `system_configs` 表的 INSERT 数据**严重不足**，仅包含 14 行基础配置：

#### 当前 refactored_schema.sql 的数据（14行）:

```sql
INSERT INTO system_configs (config_key, config_value, value_type, config_group, description, is_editable) VALUES
-- AI 成本配置 (3条)
('ai.image.cost', '5', 'integer', 'ai', 'AI图片生成成本 (积分)', TRUE),
('ai.text.cost', '1', 'integer', 'ai', 'AI文字生成成本 (积分)', TRUE),
('ai.smart_scan.cost', '10', 'integer', 'ai', 'Smart Scan 成本 (积分)', TRUE),

-- 等级月度积分 (3条)
('tier.free.monthly_credits', '0', 'integer', 'tier', 'Free 等级月度积分', FALSE),
('tier.starter.monthly_credits', '200', 'integer', 'tier', 'Starter 等级月度积分', FALSE),
('tier.pro.monthly_credits', '500', 'integer', 'tier', 'Pro 等级月度积分', FALSE),

-- 注册奖励 (1条)
('signup.bonus_credits', '50', 'integer', 'signup', '注册奖励积分 (永久)', TRUE),

-- 市场收益分成 (2条)
('marketplace.seller_revenue_ratio', '0.9', 'decimal', 'marketplace', '卖家收益比例 (90%)', FALSE),
('marketplace.platform_fee_ratio', '0.1', 'decimal', 'marketplace', '平台手续费比例 (10%)', FALSE),

-- 试用期 (1条)
('trial.duration_days', '30', 'integer', 'trial', '试用期天数', TRUE);
```

#### 当前 ddl.sql 的数据（120+行）:

根据 ddl.sql 第 1192-1250 行和 1770-1850 行，实际包含：

```sql
-- 1. Rate Limits (24条)
rate_limit.payment.checkout
rate_limit.payment.portal
rate_limit.marketplace.purchase
rate_limit.generate.story
rate_limit.generate.images
rate_limit.tools.ocr
rate_limit.export.pdf
rate_limit.export.zip
rate_limit.export.preview
rate_limit.projects.create
rate_limit.assets.upload
rate_limit.marketplace.publish
rate_limit.support.email
rate_limit.contact.form
rate_limit.feedback.submit
rate_limit.admin.credits
rate_limit.admin.tier
rate_limit.admin.refund
rate_limit.admin.subscription
rate_limit.admin.broadcast
rate_limit.admin.search
rate_limit.marketplace.list
rate_limit.analytics.events
rate_limit.global.default

-- 2. Analytics Configuration (3条)
analytics.enabled
analytics.sampling_rate
analytics.min_level

-- 3. Feature Flags (4条)
FEATURE_AI_GENERATION
FEATURE_MARKETPLACE
FEATURE_OCR
FEATURE_ZIP_EXPORT

-- 4. Limits (5条)
FREE_PROJECT_LIMIT
STARTER_PROJECT_LIMIT
PRO_PROJECT_LIMIT
MAX_UPLOAD_FILE_SIZE_MB
MAX_LISTING_PRICE

-- 5. Credits (4条)
CREDITS_PER_IMAGE
CREDITS_PER_OCR
CREDITS_PER_AI_DESIGN_PAGE
SIGNUP_BONUS_CREDITS

-- 6. Pricing (4条)
STARTER_PLAN_PRICE
PRO_PLAN_PRICE
STARTER_MONTHLY_CREDITS
PRO_MONTHLY_CREDITS

-- 7. AI Providers Configuration (8条, v3.21/v3.25)
ai_providers.enabled
ai_model.user.text_reasoning
ai_model.user.image_generation
ai_model.admin.analysis
ai_model.canary
ai_providers.models
ai_providers.timeouts
ai_providers.costs
ai_providers.retry

-- 8. Credit Costs (5条, v3.23/v3.25)
credits.cost.image_generation
credits.cost.image_generation_reference
credits.cost.text_generation
credits.cost.smart_scan
credits.cost.ocr
```

**缺失数据统计**:
- ❌ Rate Limits: 0/24 (缺失 100%)
- ❌ Analytics Configuration: 0/3 (缺失 100%)
- ❌ Feature Flags: 0/4 (缺失 100%)
- ❌ Limits: 0/5 (缺失 100%)
- ⚠️ Credits: 3/9 (缺失 67%)
- ❌ Pricing: 0/4 (缺失 100%)
- ❌ AI Providers: 0/8 (缺失 100%)

**影响**:
- 🔴 Rate Limit 完全失效，API 无保护
- 🔴 AI Provider 配置缺失，AI 功能无法工作
- 🔴 Feature Flags 缺失，无法控制功能开关
- 🟡 Pricing 配置缺失，依赖硬编码

---

### 2.3 🟡 中等问题：字段名不一致

#### 问题 1: `system_configs` 表字段名

**refactored_schema.sql** 使用:
```sql
CREATE TABLE system_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    config_key TEXT NOT NULL UNIQUE,        -- ✅ 新名称
    config_value TEXT NOT NULL,             -- ✅ 新名称
    value_type TEXT NOT NULL,
    config_group TEXT NOT NULL,
    description TEXT,
    is_editable BOOLEAN DEFAULT TRUE,       -- ✅ 新字段
    ext_json JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    is_deleted BOOLEAN,
    deleted_at TIMESTAMPTZ
);
```

**当前 ddl.sql** 使用:
```sql
CREATE TABLE system_configs (
    key TEXT PRIMARY KEY,                   -- ❌ 旧名称
    value TEXT NOT NULL,                    -- ❌ 旧名称
    value_type TEXT NOT NULL DEFAULT 'text',
    config_group TEXT NOT NULL DEFAULT 'general',
    description TEXT,
    is_active BOOLEAN DEFAULT true,         -- ❌ 旧字段
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by TEXT
);
```

**影响**:
- 🔴 现有后端代码引用 `key` 和 `value` 字段，改为 `config_key` 和 `config_value` 会导致代码全部失效
- 🔴 所有现有 INSERT 语句需要重写

**建议**:
- **方案 A (推荐)**: 保留 `key` 和 `value` 字段名，仅添加 `is_editable`
- **方案 B**: 重命名字段，同时提供数据库视图兼容旧名称
- **方案 C**: 重命名字段，提供完整的后端代码迁移脚本

#### 问题 2: `marketplace_listings.primary_category` 字段

**v3.26 迁移** 已将 `category` 改为两级分类:
```sql
-- v3.26_marketplace_two_level_category.sql
ALTER TABLE marketplace_listings
ADD COLUMN primary_category TEXT,
ADD COLUMN secondary_category TEXT;

UPDATE marketplace_listings
SET primary_category = category;

ALTER TABLE marketplace_listings
DROP COLUMN category;
```

但 **refactored_schema.sql** 中仍使用 `primary_category` 和 `secondary_category`，这是正确的。

**验证**: ✅ 与最新迁移一致

---

### 2.4 🟢 轻微问题：Storage Buckets 配置

**refactored_schema.sql** 包含:
```sql
CREATE TABLE storage.buckets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    ...
);

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types) VALUES
('avatars', 'avatars', TRUE, 5242880, ARRAY['image/png', 'image/jpeg', 'image/webp']),
('projects', 'projects', FALSE, 52428800, ARRAY['image/png', 'image/jpeg', 'application/json']),
('marketplace', 'marketplace', TRUE, 104857600, ARRAY['image/png', 'image/jpeg', 'image/svg+xml', 'application/pdf']),
('generations', 'generations', FALSE, 10485760, ARRAY['image/png', 'image/jpeg']);
```

**问题**:
- Supabase Storage 的 `buckets` 表是系统表，不应该在应用 DDL 中直接 CREATE
- 应该通过 Supabase Dashboard 或 CLI 创建

**建议**:
- 移除 `CREATE TABLE storage.buckets`
- 添加注释说明需要手动创建这些 buckets
- 或者提供 Supabase CLI 脚本

---

## 三、缺失功能评估

### 3.1 缺失表的优先级排序

| 优先级 | 表名 | 用途 | 影响 |
|-------|------|------|------|
| 🔴 P0 | `ai_call_logs` | AI API 调用日志 | AI 功能无法追踪成本和性能 |
| 🔴 P0 | `ai_usage_daily` | AI 使用量汇总 | 无法进行成本分析和容量规划 |
| 🔴 P0 | `asset_categories` | 素材分类树 | 素材库功能完全不可用 |
| 🔴 P0 | `assets` | 统一素材表 | 素材库功能完全不可用 |
| 🟡 P1 | `daily_themes` | 每日主题 | 产品特色功能缺失 |
| 🟡 P1 | `holidays` | 节日数据 | 节日主题素材无法展示 |
| 🟡 P1 | `user_events` | 用户事件 | 用户行为分析缺失 |
| 🟡 P1 | `activity_logs` | 活动日志 | 审计和活动追踪缺失 |
| 🟡 P1 | `analytics_aggregation` | Analytics 聚合 | Dashboard 性能差 |
| 🟡 P1 | `scheduled_task_logs` | 调度任务日志 | 运维监控缺失 |
| 🟢 P2 | `config_audit_logs` | 配置审计 | 配置变更无审计 |
| 🟢 P2 | `content_reports` | 内容举报 | 内容审核功能缺失 |
| 🟢 P2 | `tooltip_configs` | Tooltip 配置 | UI 配置缺失 |
| 🟢 P2 | `seller_stats` | 卖家统计 | 性能优化缺失 |

---

## 四、建议修订方案

### 4.1 立即修订（阻塞性问题）

#### A. 补充所有 P0 级别表

**AI 相关表** (2 张):
- `ai_call_logs`
- `ai_usage_daily`
- 包含对应的索引、RLS 策略、Upsert 函数

**素材系统表** (2 张):
- `asset_categories`
- `assets`
- 包含对应的索引、触发器

#### B. 补充完整的 `system_configs` 初始化数据

**必须包含**:
- Rate Limits (24条)
- AI Providers Configuration (8条)
- Feature Flags (4条)
- Limits (5条)
- Credits (9条)
- Pricing (4条)
- Analytics Configuration (3条)

**总计**: 至少 57 行配置数据

#### C. 字段名一致性修复

**system_configs 表** - 保持向后兼容:
```sql
CREATE TABLE system_configs (
    -- 主键保持原名
    key TEXT PRIMARY KEY,                   -- ✅ 保持原名
    value TEXT NOT NULL,                    -- ✅ 保持原名
    value_type TEXT NOT NULL DEFAULT 'text',
    config_group TEXT NOT NULL DEFAULT 'general',
    description TEXT,

    -- 新增字段
    is_editable BOOLEAN DEFAULT TRUE,       -- ✨ 新增

    -- 保留原有字段
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by TEXT
);

COMMENT ON COLUMN system_configs.key IS '配置键 @Ref: 原名 key, 未改为 config_key 以保持兼容性';
```

---

### 4.2 优先补充（重要但非阻塞）

#### A. 补充 P1 级别表

**主题系统** (2 张):
- `daily_themes`
- `holidays`

**Analytics 系统** (3 张):
- `user_events`
- `activity_logs`
- `analytics_aggregation`

**调度系统** (1 张):
- `scheduled_task_logs`

#### B. 补充缺失的物化视图刷新函数

根据 v3.12 迁移，需要以下函数：

```sql
-- 刷新所有物化视图的函数
CREATE OR REPLACE FUNCTION refresh_all_materialized_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY daily_revenue;
    REFRESH MATERIALIZED VIEW CONCURRENTLY marketplace_rankings;
    REFRESH MATERIALIZED VIEW CONCURRENTLY user_activity_summary;
END;
$$ LANGUAGE plpgsql;

-- 定时刷新任务 (通过 pg_cron 或外部调度)
-- 每小时刷新一次
```

---

### 4.3 可选补充（增强功能）

#### A. 补充 P2 级别表

- `config_audit_logs`
- `content_reports`
- `tooltip_configs`
- `seller_stats`

#### B. 补充触发器和函数

根据 v3.22 和 v3.27 迁移，需要以下原子操作函数：

```sql
-- increment_campaign_usage() - 原子递增活动使用次数
CREATE OR REPLACE FUNCTION increment_campaign_usage(p_campaign_id UUID)
RETURNS void AS $$
BEGIN
    UPDATE campaigns
    SET current_uses = current_uses + 1
    WHERE id = p_campaign_id;
END;
$$ LANGUAGE plpgsql;
```

---

## 五、最终建议

### 5.1 重构策略建议

#### 策略 A: 分阶段迁移（推荐）

**Phase 1**: 补充核心缺失内容
- ✅ 添加所有 P0 表 (AI, Assets)
- ✅ 补充完整 system_configs 数据
- ✅ 修复字段名不一致问题
- ✅ 移除 storage.buckets 直接创建

**Phase 2**: 补充重要功能
- ✅ 添加 P1 表 (Themes, Analytics, Scheduler)
- ✅ 添加物化视图刷新函数
- ✅ 添加原子操作函数

**Phase 3**: 补充增强功能
- ✅ 添加 P2 表 (Audit, Reports, Tooltips)
- ✅ 完善注释和文档

#### 策略 B: 一次性完整重构

**优点**: 一次性解决所有问题
**缺点**: 风险高，测试周期长

**不推荐**，除非有充足的测试时间

---

### 5.2 执行步骤

1. **立即执行**:
   ```bash
   # 1. 备份当前 refactored_schema.sql
   cp refactored_schema.sql refactored_schema_v1.sql

   # 2. 基于现有 ddl.sql 生成增量补充脚本
   # 3. 合并到 refactored_schema.sql
   # 4. 在测试环境验证
   # 5. 对比输出，确保所有表、索引、函数都存在
   ```

2. **验证清单**:
   - [ ] 所有表都已创建（对比 ddl.sql 表清单）
   - [ ] 所有索引都已创建
   - [ ] 所有触发器都已创建
   - [ ] 所有函数都已创建
   - [ ] system_configs 数据完整（57+ 行）
   - [ ] 字段名与现有代码兼容
   - [ ] RLS 策略已应用

3. **回归测试**:
   - [ ] AI 生成功能测试
   - [ ] 素材库浏览测试
   - [ ] 积分扣除测试
   - [ ] 市场购买测试
   - [ ] Analytics 追踪测试
   - [ ] 后台管理功能测试

---

## 六、总结

### 6.1 核心问题

1. **🔴 严重**: 缺失 14 张核心业务表（AI、Assets、Themes、Analytics 等）
2. **🔴 严重**: system_configs 初始化数据严重不足（14/70+行，缺失 80%）
3. **🟡 中等**: 字段名不一致（system_configs.key vs config_key）
4. **🟢 轻微**: storage.buckets 不应直接在 DDL 中创建

### 6.2 推荐行动

**立即行动**:
1. 补充所有 P0 表（4 张：AI、Assets）
2. 补充完整 system_configs 数据（至少 57 行）
3. 修复 system_configs 字段名（保持 `key`/`value`）
4. 移除 storage.buckets CREATE 语句

**后续行动**:
1. 补充 P1 表（6 张：Themes、Analytics、Scheduler）
2. 补充物化视图刷新函数
3. 补充 P2 表（4 张：Audit、Reports 等）

**验证标准**:
- ✅ 表数量: 28 → 42+ 张
- ✅ system_configs 数据: 14 → 60+ 行
- ✅ 所有功能模块可正常工作
- ✅ 后端代码无需大规模改动

---

**评估结论**: 当前 refactored_schema.sql 在架构设计上优秀，但**功能完整性严重不足**，需要立即补充核心表和初始化数据，否则无法用于生产环境。
