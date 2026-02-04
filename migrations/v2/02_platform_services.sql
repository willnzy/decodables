-- ============================================================================
-- Make Decodables - 数据库架构 (文件 2/3)
-- ============================================================================
-- 分类: 平台服务
-- 说明: Feature Flag、Analytics、Webhooks、审计、主题、营销
-- 执行顺序: 第 2 个执行 (依赖 01_core_business.sql 中的 profiles, marketplace_listings)
-- 生成时间: 2026-01-12 (Feature Flag v1.1 树状结构支持)
-- ============================================================================

-- 开始事务
BEGIN;

-- ============================================================================
-- 包含的表 (29) - 按依赖关系排序
-- ============================================================================
-- Layer 1: 无依赖 (仅依赖 profiles)
--   - activity_logs, aggregated_stats, ai_usage_daily, analytics_aggregation
--   - analytics_events, clerk_webhook_events, config_audit_logs, daily_metrics
--   - campaigns (依赖 profiles - MOVED HERE because daily_themes depends on it)
--   - daily_themes (依赖 campaigns), feature_flags, holidays, monthly_metrics
--   - notifications, stripe_webhook_events, system_resource_audit_logs, user_events
--
-- Layer 2: 依赖 Layer 1 或 01_core_business.sql 的表
--   - content_reports (依赖 profiles, marketplace_listings)
--   - experiments (独立)
--   - onboarding_steps (独立)
--   - articles (依赖 profiles)
--   - experiment_configs (依赖 feature_flags)
--   - flag_exposures (依赖 feature_flags - 仅字段关联,无外键)
--   - flag_audit_logs (依赖 feature_flags)
--
-- Layer 3: 依赖 Layer 2 的表
--   - campaign_dismissals (依赖 campaigns, profiles)
--   - campaign_participations (依赖 campaigns, profiles)
--   - experiment_assignments (依赖 experiments, profiles)
--   - experiment_conversions (依赖 experiments, profiles)
--   - experiment_exposures (依赖 experiments, profiles)
--   - experiment_results (依赖 feature_flags - 使用统一版本)
--   - referrals (依赖 profiles)
--   - user_onboarding_progress (依赖 onboarding_steps, profiles)


-- ============================================================================
-- Layer 1: 无依赖的表
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. activity_logs
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS activity_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id),
    action TEXT NOT NULL,
    resource_type TEXT,
    resource_id TEXT,
    description TEXT,
    metadata JSONB DEFAULT '{}',
    ip_address INET,
    timezone TEXT DEFAULT 'UTC',
    created_at_local TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);


-- ----------------------------------------------------------------------------
-- 2. aggregated_stats
-- P0-15, P0-16, P0-17: Repository 使用 date 和 data 字段
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS aggregated_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stat_type TEXT NOT NULL,
    stat_key TEXT NOT NULL,
    stat_value NUMERIC DEFAULT 0,
    -- P0-15, P0-16: Repository 使用的额外字段
    date DATE,  -- 日期字段，用于按日期查询
    data JSONB DEFAULT '{}',  -- 数据字段，用于存储复杂数据
    metadata JSONB DEFAULT '{}',
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_stat_type CHECK (
        stat_type IN ('daily', 'weekly', 'monthly', 'quarterly', 'yearly', 'custom')
    ),
    CONSTRAINT check_period_range CHECK (period_end >= period_start),
    CONSTRAINT unique_aggregated_stat UNIQUE (stat_type, stat_key, period_start)
);

CREATE INDEX IF NOT EXISTS idx_aggregated_stats_period ON aggregated_stats(period_start DESC, period_end DESC);
CREATE INDEX IF NOT EXISTS idx_aggregated_stats_type_key ON aggregated_stats(stat_type, stat_key);
CREATE INDEX IF NOT EXISTS idx_aggregated_stats_key_period ON aggregated_stats(stat_key, period_start DESC);
CREATE INDEX IF NOT EXISTS idx_aggregated_stats_date ON aggregated_stats(date) WHERE date IS NOT NULL;  -- P0-15: 日期索引


-- ----------------------------------------------------------------------------
-- 3. ai_usage_daily
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ai_usage_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    call_type TEXT NOT NULL,

    -- 统计指标
    total_calls INTEGER DEFAULT 0,
    successful_calls INTEGER DEFAULT 0,
    failed_calls INTEGER DEFAULT 0,
    total_input_tokens BIGINT DEFAULT 0,
    total_output_tokens BIGINT DEFAULT 0,
    total_images INTEGER DEFAULT 0,

    -- 性能指标
    avg_latency_ms INTEGER DEFAULT 0,
    min_latency_ms INTEGER,
    max_latency_ms INTEGER,

    -- 成本
    estimated_cost_usd DECIMAL(10, 4) DEFAULT 0,

    -- 错误统计
    error_counts JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(date, provider, model, call_type)
);


-- ----------------------------------------------------------------------------
-- 4. analytics_aggregation
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics_aggregation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    granularity TEXT NOT NULL CHECK (granularity IN ('daily', 'weekly', 'monthly')),
    dimension_type TEXT NOT NULL,
    dimension_value TEXT,
    metrics JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, granularity, dimension_type, dimension_value)
);


-- ----------------------------------------------------------------------------
-- 5. analytics_events
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id),
    session_id TEXT,
    event_id TEXT,
    event_name TEXT NOT NULL,
    event_type TEXT NOT NULL,
    context JSONB DEFAULT '{}',
    properties JSONB DEFAULT '{}',
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 索引: created_at 用于时间范围查询 (Supabase Index Advisor 建议, startup_cost 1348→6)
CREATE INDEX IF NOT EXISTS idx_analytics_events_created_at
    ON analytics_events USING btree (created_at);

-- 索引: user_id 用于按用户查询事件
CREATE INDEX IF NOT EXISTS idx_analytics_events_user_id
    ON analytics_events(user_id);

-- WS-11: 索引优化 — event_type + created_at 复合索引 (按类型统计/筛选)
CREATE INDEX IF NOT EXISTS idx_analytics_events_type_created
    ON analytics_events (event_type, created_at);


-- ----------------------------------------------------------------------------
-- 6. (已删除: clerk_webhook_events - 迁移到自建认证系统后不再需要)
-- ----------------------------------------------------------------------------


-- ----------------------------------------------------------------------------
-- 7. config_audit_logs
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS config_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_key TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    action TEXT NOT NULL CHECK (action IN ('create', 'update', 'delete')),
    changed_by UUID,
    changed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);


-- ----------------------------------------------------------------------------
-- 8. daily_metrics
-- P0-18: Repository 使用 date 和 dau 字段，添加别名列
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS daily_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_date DATE NOT NULL UNIQUE,
    date DATE,  -- P0-18: metric_date 的别名，供 Repository 使用
    total_users INTEGER DEFAULT 0,
    active_users INTEGER DEFAULT 0,
    dau INTEGER DEFAULT 0,  -- P0-18: DAU (Daily Active Users)，供 Repository 使用
    new_users INTEGER DEFAULT 0,
    total_projects INTEGER DEFAULT 0,
    new_projects INTEGER DEFAULT 0,
    total_listings INTEGER DEFAULT 0,
    new_listings INTEGER DEFAULT 0,
    total_purchases INTEGER DEFAULT 0,
    revenue_usd NUMERIC(10, 2) DEFAULT 0,
    revenue_credits INTEGER DEFAULT 0,
    ai_generations INTEGER DEFAULT 0,
    smart_scans INTEGER DEFAULT 0,
    credits_consumed INTEGER DEFAULT 0,
    credits_granted INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    avg_response_time_ms NUMERIC(10, 2),
    p95_response_time_ms NUMERIC(10, 2),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_metric_date CHECK (metric_date >= '2024-01-01'),
    CONSTRAINT check_non_negative_counts CHECK (
        total_users >= 0 AND active_users >= 0 AND new_users >= 0 AND
        total_projects >= 0 AND new_projects >= 0 AND
        total_listings >= 0 AND new_listings >= 0 AND
        total_purchases >= 0 AND ai_generations >= 0 AND
        smart_scans >= 0 AND credits_consumed >= 0 AND
        credits_granted >= 0 AND error_count >= 0
    )
);

CREATE INDEX IF NOT EXISTS idx_daily_metrics_metric_date ON daily_metrics(metric_date DESC);
CREATE INDEX IF NOT EXISTS idx_daily_metrics_date ON daily_metrics(date DESC) WHERE date IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_daily_metrics_dau ON daily_metrics(dau DESC) WHERE dau IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_daily_metrics_created_at ON daily_metrics(created_at DESC);

-- P0-18: 触发器保持 date 和 metric_date 同步
CREATE OR REPLACE FUNCTION sync_daily_metrics_date()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.date IS NULL AND NEW.metric_date IS NOT NULL THEN
            NEW.date := NEW.metric_date;
        ELSIF NEW.metric_date IS NULL AND NEW.date IS NOT NULL THEN
            NEW.metric_date := NEW.date;
        END IF;
    END IF;
    
    IF TG_OP = 'UPDATE' THEN
        IF NEW.metric_date IS DISTINCT FROM OLD.metric_date THEN
            NEW.date := NEW.metric_date;
        ELSIF NEW.date IS DISTINCT FROM OLD.date THEN
            NEW.metric_date := NEW.date;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql
SET search_path = 'public';

DROP TRIGGER IF EXISTS trg_sync_daily_metrics_date ON daily_metrics;
CREATE TRIGGER trg_sync_daily_metrics_date
    BEFORE INSERT OR UPDATE ON daily_metrics
    FOR EACH ROW
    EXECUTE FUNCTION sync_daily_metrics_date();


-- ----------------------------------------------------------------------------
-- 9. campaigns (依赖 profiles) - MOVED HERE: daily_themes depends on it
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    type TEXT NOT NULL CHECK (type IN ('credits_reward', 'discount', 'trial_extension', 'bonus')),
    config JSONB NOT NULL DEFAULT '{}',
    target_type TEXT NOT NULL DEFAULT 'all' CHECK (target_type IN ('all', 'tier', 'cohort', 'user_list')),
    target_config JSONB DEFAULT '{}',
    notification_channels TEXT[] DEFAULT ARRAY['banner'],
    notification_config JSONB DEFAULT '{}',
    start_at TIMESTAMPTZ NOT NULL,
    end_at TIMESTAMPTZ NOT NULL,
    timezone TEXT DEFAULT 'UTC',
    usage_limit INTEGER,
    usage_per_user INTEGER DEFAULT 1,
    usage_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'paused', 'completed')),
    is_active BOOLEAN DEFAULT TRUE,
    created_by UUID REFERENCES profiles(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMPTZ,
    recovery_expires_at TIMESTAMPTZ,
    is_permanently_deleted BOOLEAN DEFAULT false,
    CONSTRAINT chk_campaigns_deleted_at_consistency
        CHECK ((is_deleted = false AND deleted_at IS NULL) OR (is_deleted = true AND deleted_at IS NOT NULL)),
    CONSTRAINT chk_campaigns_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);


-- ----------------------------------------------------------------------------
-- 10. daily_themes (also supports holiday themes)
-- v2.1: Added category, i18n, AI generation, review workflow fields
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS daily_themes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- ========== Basic Info ==========
    name TEXT NOT NULL,                                    -- Theme display name (used by code)
    title TEXT,                                            -- Alias for name (backward compat)
    description TEXT,                                      -- Theme description (primary language)

    -- ========== Category (v2.1) ==========
    category TEXT DEFAULT 'holiday',                       -- Theme category
    -- Values: holiday, memorial, historical, notable, campaign, special

    -- ========== i18n Support (v2.1) ==========
    name_i18n JSONB DEFAULT '{}',                          -- Multi-language name {"en": "...", "zh": "..."}
    slogan TEXT,                                           -- Theme slogan (primary language)
    slogan_i18n JSONB DEFAULT '{}',                        -- Multi-language slogan
    description_i18n JSONB DEFAULT '{}',                   -- Multi-language description

    -- ========== Region Control (v2.1) ==========
    regions TEXT[] DEFAULT ARRAY[]::TEXT[],                -- Target regions ['US', 'CN', 'GLOBAL']

    -- ========== Activation Control ==========
    is_active BOOLEAN DEFAULT true,                        -- Whether theme is enabled
    priority INTEGER DEFAULT 0,                            -- Higher priority = shown first
    date DATE,                                             -- Specific date (for daily themes)
    date_rule JSONB,                                       -- Date rule for holiday themes

    -- ========== Campaign Linkage (v2.1) ==========
    linked_campaign_id UUID,                               -- Linked marketing campaign (FK)

    -- ========== Content ==========
    thumbnail_url TEXT,
    preview_urls TEXT[] DEFAULT ARRAY[]::TEXT[],
    featured_asset_ids UUID[] DEFAULT ARRAY[]::UUID[],
    recommended_categories TEXT[] DEFAULT ARRAY[]::TEXT[],
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    theme_config JSONB DEFAULT '{}',                       -- Colors, badges, decorations, etc.

    -- ========== AI Generation (v2.1) ==========
    ai_generated BOOLEAN DEFAULT false,                    -- Whether AI generated this theme
    ai_alternatives JSONB DEFAULT '[]',                    -- AI alternative options [{id, name, config, created_at}]
    selected_alternative_id TEXT,                          -- Currently selected alternative ID
    ai_recommended_id TEXT,                                -- AI recommended alternative ID

    -- ========== External Links (v2.1) ==========
    source_url TEXT,                                       -- Information source URL
    learn_more_url TEXT,                                   -- Learn more URL for users

    -- ========== Review Workflow (v2.1) ==========
    review_status TEXT DEFAULT 'pending',                  -- Review status
    -- Values: pending, auto_approved, reviewed, rejected
    reviewed_by UUID,                                      -- Reviewer user_id
    reviewed_at TIMESTAMPTZ,                               -- Review timestamp
    review_notes TEXT,                                     -- Review notes/comments

    -- ========== Regeneration History (v2.1) ==========
    generation_history JSONB DEFAULT '[]',                 -- History [{timestamp, reason, by, snapshot}]
    regenerate_count INTEGER DEFAULT 0,                    -- Number of regenerations

    -- ========== Status ==========
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'archived')),
    metadata JSONB DEFAULT '{}',

    -- ========== Timestamps ==========
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    -- ========== Soft Delete ==========
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMPTZ,
    recovery_expires_at TIMESTAMPTZ,

    -- ========== Constraints ==========
    CONSTRAINT chk_daily_themes_deleted_at_consistency
        CHECK ((is_deleted = false AND deleted_at IS NULL) OR (is_deleted = true AND deleted_at IS NOT NULL)),
    CONSTRAINT chk_daily_themes_recovery_expires_at_consistency
        CHECK (
            recovery_expires_at IS NULL OR
            (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
        ),
    -- v2.1 constraints
    CONSTRAINT chk_daily_themes_category
        CHECK (category IN ('holiday', 'memorial', 'historical', 'notable', 'campaign', 'special')),
    CONSTRAINT chk_daily_themes_review_status
        CHECK (review_status IN ('pending', 'auto_approved', 'reviewed', 'rejected')),
    -- Foreign key (campaigns table must exist)
    CONSTRAINT fk_daily_themes_campaign
        FOREIGN KEY (linked_campaign_id) REFERENCES campaigns(id) ON DELETE SET NULL
);

-- ========== Indexes ==========
-- Original index
CREATE INDEX IF NOT EXISTS idx_daily_themes_is_active_priority ON daily_themes (is_active, priority DESC) WHERE is_deleted = false;
-- v2.1 indexes
CREATE INDEX IF NOT EXISTS idx_daily_themes_category ON daily_themes (category) WHERE is_deleted = false;
CREATE INDEX IF NOT EXISTS idx_daily_themes_regions ON daily_themes USING GIN (regions) WHERE is_deleted = false;
CREATE INDEX IF NOT EXISTS idx_daily_themes_review_status ON daily_themes (review_status) WHERE is_deleted = false;
CREATE INDEX IF NOT EXISTS idx_daily_themes_date ON daily_themes (date) WHERE is_deleted = false;
CREATE INDEX IF NOT EXISTS idx_daily_themes_ai_generated ON daily_themes (ai_generated) WHERE is_deleted = false AND ai_generated = true;
-- WS-04: Partial unique index to prevent duplicate themes for the same date (non-deleted only)
CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_themes_unique_date ON daily_themes (date) WHERE is_deleted = false;


-- ----------------------------------------------------------------------------
-- 10. feature_flags
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS feature_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    flag_type TEXT DEFAULT 'boolean' CHECK (flag_type IN ('boolean', 'multivariate', 'experiment')),
    enabled BOOLEAN DEFAULT FALSE,
    archived BOOLEAN DEFAULT FALSE,
    -- P0-2: Repository 使用 status 字段过滤
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'archived', 'draft')),
    -- P0-3: Repository 使用 default_value (布尔)
    default_value BOOLEAN DEFAULT FALSE,

    -- 环境和时间控制
    environments TEXT[] DEFAULT ARRAY['production', 'staging'],
    start_at TIMESTAMPTZ,
    end_at TIMESTAMPTZ,

    -- 灰度配置
    rollout_percentage INTEGER DEFAULT 0 CHECK (rollout_percentage BETWEEN 0 AND 100),

    -- 名单控制
    whitelist_user_ids TEXT[] DEFAULT ARRAY[]::TEXT[],
    blacklist_user_ids TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- v1.2 Tier 分层筛选
    -- 允许的 Tier 列表，空数组表示不限制 (所有 Tier 都允许)
    -- 格式: ["t2", "t3"] 表示仅 Starter 和 Pro 用户可见
    allowed_tiers TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- 定向规则 (JSON数组)
    -- 格式: [{"id": "rule1", "priority": 1, "conditions": [...], "variant": "treatment"}]
    targeting_rules JSONB DEFAULT '[]',

    -- 变体配置 (JSON数组)
    -- 格式: [{"key": "control", "value": false, "weight": 50}, {"key": "treatment", "value": true, "weight": 50}]
    variants JSONB DEFAULT '[{"key": "control", "value": false, "weight": 50}, {"key": "treatment", "value": true, "weight": 50}]'::JSONB,
    default_variant TEXT DEFAULT 'control',

    -- 元数据
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    owner TEXT,

    -- v1.1 树状结构支持
    -- 父级 Flag keys，用于实现 Flag 依赖关系
    -- 当任何父级 Flag 禁用时，当前 Flag 自动返回 disabled (评估原因: PARENT_DISABLED)
    parent_flags TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- 审计字段
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_ff_key ON feature_flags(key);
CREATE INDEX IF NOT EXISTS idx_ff_enabled ON feature_flags(enabled) WHERE enabled = true AND archived = false;
CREATE INDEX IF NOT EXISTS idx_ff_type ON feature_flags(flag_type);
CREATE INDEX IF NOT EXISTS idx_ff_tags ON feature_flags USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_ff_parent_flags ON feature_flags USING GIN(parent_flags);  -- v1.1: 父级关系查询

-- 注释
COMMENT ON TABLE feature_flags IS 'Feature Flags统一表,支持boolean/multivariate/experiment三种类型,v1.1支持树状结构,v1.2支持Tier分层筛选';
COMMENT ON COLUMN feature_flags.key IS 'Flag唯一标识 (如 feat_new_editor)';
COMMENT ON COLUMN feature_flags.flag_type IS 'Flag类型: boolean(开关), multivariate(多变体), experiment(实验)';
COMMENT ON COLUMN feature_flags.allowed_tiers IS 'v1.2: 允许的Tier列表,空数组表示不限制,格式["t2","t3"]';
COMMENT ON COLUMN feature_flags.parent_flags IS 'v1.1: 父级Flag keys数组,父级禁用时子级自动返回disabled';


-- ----------------------------------------------------------------------------
-- 11. holidays
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS holidays (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    name_i18n JSONB DEFAULT '{}',
    slug TEXT NOT NULL UNIQUE,
    month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    day INTEGER NOT NULL CHECK (day BETWEEN 1 AND 31),
    regions TEXT[] DEFAULT ARRAY[]::TEXT[],
    category TEXT NOT NULL,
    is_major BOOLEAN DEFAULT FALSE,
    theme_colors TEXT[] DEFAULT ARRAY[]::TEXT[],
    asset_category_ids UUID[] DEFAULT ARRAY[]::UUID[],
    description TEXT,
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMPTZ,
    recovery_expires_at TIMESTAMPTZ,
    CONSTRAINT chk_holidays_deleted_at_consistency
        CHECK ((is_deleted = false AND deleted_at IS NULL) OR (is_deleted = true AND deleted_at IS NOT NULL)),
    CONSTRAINT chk_holidays_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);


-- ----------------------------------------------------------------------------
-- 12. monthly_metrics
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS monthly_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_year INTEGER NOT NULL,
    metric_month INTEGER NOT NULL,
    total_users INTEGER DEFAULT 0,
    active_users INTEGER DEFAULT 0,
    new_users INTEGER DEFAULT 0,
    churned_users INTEGER DEFAULT 0,
    total_projects INTEGER DEFAULT 0,
    new_projects INTEGER DEFAULT 0,
    total_listings INTEGER DEFAULT 0,
    new_listings INTEGER DEFAULT 0,
    total_purchases INTEGER DEFAULT 0,
    revenue_usd NUMERIC(12, 2) DEFAULT 0,
    revenue_credits INTEGER DEFAULT 0,
    ai_generations INTEGER DEFAULT 0,
    smart_scans INTEGER DEFAULT 0,
    credits_consumed INTEGER DEFAULT 0,
    credits_granted INTEGER DEFAULT 0,
    mrr NUMERIC(12, 2) DEFAULT 0,
    arr NUMERIC(12, 2) DEFAULT 0,
    ltv NUMERIC(12, 2),
    cac NUMERIC(12, 2),
    retention_rate NUMERIC(5, 2),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_metric_year CHECK (metric_year >= 2024 AND metric_year <= 2100),
    CONSTRAINT check_metric_month CHECK (metric_month >= 1 AND metric_month <= 12),
    CONSTRAINT unique_monthly_metric UNIQUE (metric_year, metric_month),
    CONSTRAINT check_non_negative_monthly_counts CHECK (
        total_users >= 0 AND active_users >= 0 AND new_users >= 0 AND
        churned_users >= 0 AND total_projects >= 0 AND new_projects >= 0 AND
        total_listings >= 0 AND new_listings >= 0 AND
        total_purchases >= 0 AND ai_generations >= 0 AND
        smart_scans >= 0 AND credits_consumed >= 0 AND credits_granted >= 0
    )
);

CREATE INDEX IF NOT EXISTS idx_monthly_metrics_year_month ON monthly_metrics(metric_year DESC, metric_month DESC);
CREATE INDEX IF NOT EXISTS idx_monthly_metrics_created_at ON monthly_metrics(created_at DESC);


-- ----------------------------------------------------------------------------
-- 13. hourly_metrics (小时级指标)
-- ----------------------------------------------------------------------------
-- 用途: 存储每小时的快速指标统计
-- 写入: scheduler.py 中的 hourly ETL 任务
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS hourly_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 时间标识 (小时精度)
    hour TIMESTAMPTZ NOT NULL,
    
    -- 指标数据
    events INTEGER DEFAULT 0 CHECK (events >= 0),
    
    -- 扩展字段 (预留)
    active_users INTEGER DEFAULT 0 CHECK (active_users >= 0),
    new_projects INTEGER DEFAULT 0 CHECK (new_projects >= 0),
    ai_generations INTEGER DEFAULT 0 CHECK (ai_generations >= 0),
    
    -- 元数据
    metadata JSONB DEFAULT '{}',
    
    -- 审计字段
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 唯一约束: 每小时只有一条记录
    CONSTRAINT unique_hourly_metric UNIQUE (hour)
);

CREATE INDEX IF NOT EXISTS idx_hourly_metrics_hour ON hourly_metrics(hour DESC);
CREATE INDEX IF NOT EXISTS idx_hourly_metrics_created_at ON hourly_metrics(created_at DESC);

COMMENT ON TABLE hourly_metrics IS '小时级指标存储表，由 ETL 定时任务写入';


-- ----------------------------------------------------------------------------
-- 14. notifications (无软删除,只追加)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    notification_type TEXT NOT NULL,  -- SQL 标准字段
    type TEXT,  -- P0-1: Repository 使用的别名字段
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    action_url TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- P0-1: 触发器同步 type 和 notification_type
CREATE OR REPLACE FUNCTION sync_notification_type()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.type IS NOT NULL AND NEW.notification_type IS NULL THEN
        NEW.notification_type := NEW.type;
    ELSIF NEW.notification_type IS NOT NULL AND NEW.type IS NULL THEN
        NEW.type := NEW.notification_type;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql
SET search_path = 'public';

DROP TRIGGER IF EXISTS trg_notifications_sync_type ON notifications;
CREATE TRIGGER trg_notifications_sync_type
    BEFORE INSERT OR UPDATE ON notifications
    FOR EACH ROW
    EXECUTE FUNCTION sync_notification_type();

-- WS-11: 索引优化 — 未读通知查询 (partial index, 只索引未读)
CREATE INDEX IF NOT EXISTS idx_notifications_user_unread
    ON notifications (user_id)
    WHERE is_read = false;

-- WS-11: 索引优化 — 通知列表按时间倒序
CREATE INDEX IF NOT EXISTS idx_notifications_user_created
    ON notifications (user_id, created_at DESC);


-- ----------------------------------------------------------------------------
-- 14b. admin_notification_templates (Admin 通知模板/草稿)
-- ----------------------------------------------------------------------------
-- 用于 Admin Panel 的通知管理功能，支持草稿、定时发送
CREATE TABLE IF NOT EXISTS admin_notification_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    notification_type TEXT NOT NULL DEFAULT 'info',  -- info/warning/error/success/announcement
    channel TEXT NOT NULL DEFAULT 'in_app',          -- in_app/email/push/all
    status TEXT NOT NULL DEFAULT 'draft',            -- draft/scheduled/sent/failed
    target_users TEXT[],                             -- 指定用户 ID 列表
    target_tiers TEXT[],                             -- 目标 Tier 列表 (t1/t2/t3)
    scheduled_at TIMESTAMPTZ,                        -- 定时发送时间
    sent_at TIMESTAMPTZ,                             -- 实际发送时间
    created_by UUID NOT NULL,                        -- Admin user_id
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    -- 发送统计
    stats JSONB DEFAULT '{"total_recipients": 0, "delivered": 0, "read": 0, "failed": 0}',

    CONSTRAINT check_notification_type CHECK (
        notification_type IN ('info', 'warning', 'error', 'success', 'announcement', 'system', 'alert', 'promo')
    ),
    CONSTRAINT check_channel CHECK (
        channel IN ('in_app', 'email', 'push', 'all')
    ),
    CONSTRAINT check_status CHECK (
        status IN ('draft', 'scheduled', 'sent', 'failed')
    )
);

-- 索引: 按状态查询
CREATE INDEX IF NOT EXISTS idx_admin_notification_templates_status
    ON admin_notification_templates(status, created_at DESC);

-- 索引: 按创建者查询
CREATE INDEX IF NOT EXISTS idx_admin_notification_templates_created_by
    ON admin_notification_templates(created_by, created_at DESC);

-- 索引: 定时发送查询 (找出需要发送的通知)
CREATE INDEX IF NOT EXISTS idx_admin_notification_templates_scheduled
    ON admin_notification_templates(scheduled_at)
    WHERE status = 'scheduled' AND scheduled_at IS NOT NULL;

-- 触发器: 自动更新 updated_at
CREATE OR REPLACE FUNCTION update_notification_template_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql
SET search_path = 'public';

DROP TRIGGER IF EXISTS trg_notification_template_updated_at ON admin_notification_templates;
CREATE TRIGGER trg_notification_template_updated_at
    BEFORE UPDATE ON admin_notification_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_notification_template_timestamp();

-- RLS: Admin 专用表，仅 service_role 可访问
ALTER TABLE admin_notification_templates ENABLE ROW LEVEL SECURITY;

-- 策略: 仅允许 service_role 完全访问 (通过后端 API 访问)
DROP POLICY IF EXISTS admin_notification_templates_service_role ON admin_notification_templates;
CREATE POLICY admin_notification_templates_service_role ON admin_notification_templates
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);


-- ----------------------------------------------------------------------------
-- 14. stripe_webhook_events
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stripe_webhook_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id TEXT UNIQUE NOT NULL,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMPTZ,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);


-- RLS for stripe_webhook_events: managed in 03_infrastructure.sql (unified RLS section)

-- ----------------------------------------------------------------------------
-- 15. system_resource_audit_logs
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS system_resource_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_id UUID,
    action TEXT NOT NULL,
    old_data JSONB,
    new_data JSONB,
    changed_by UUID NOT NULL,
    changed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    ip_address TEXT,
    user_agent TEXT
);


-- ----------------------------------------------------------------------------
-- 16. user_events
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    event_data JSONB DEFAULT '{}',
    session_id TEXT,
    ip_address INET,
    user_agent TEXT,
    referer TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_event_type CHECK (
        event_type IN (
            'page_view', 'button_click', 'form_submit',
            'feature_used', 'error_occurred', 'api_call',
            'project_created', 'project_updated', 'project_deleted',
            'asset_uploaded', 'asset_purchased', 'payment_completed',
            'login', 'logout', 'signup', 'profile_updated'
        )
    )
);

CREATE INDEX IF NOT EXISTS idx_user_events_user_id ON user_events(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_events_event_type ON user_events(event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_events_created_at ON user_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_events_session ON user_events(session_id) WHERE session_id IS NOT NULL;


-- ============================================================================
-- Layer 2: 依赖 Layer 1 的表
-- ============================================================================

-- Note: campaigns table was moved to before daily_themes (line ~237) due to FK dependency

-- ----------------------------------------------------------------------------
-- 17. content_reports (依赖 profiles, marketplace_listings)
-- P0-6: Repository 使用 marketplace_reports 表名，创建别名视图
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS content_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reporter_id UUID NOT NULL REFERENCES profiles(id),
    listing_id UUID NOT NULL REFERENCES marketplace_listings(id),
    reason TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'reviewed', 'resolved', 'dismissed')),
    admin_response TEXT,
    reviewed_by UUID REFERENCES profiles(id),
    reviewed_at TIMESTAMPTZ,
    timezone TEXT DEFAULT 'UTC',
    created_at_local TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(reporter_id, listing_id)
);

-- P0-6: 创建 marketplace_reports 视图供 Repository 使用
-- 注意: 如果之前存在同名表，需要先删除
-- 命名规范: 视图统一使用 v_ 前缀
DROP TABLE IF EXISTS marketplace_reports CASCADE;
DROP VIEW IF EXISTS marketplace_reports CASCADE;
DROP VIEW IF EXISTS v_marketplace_reports CASCADE;
CREATE OR REPLACE VIEW v_marketplace_reports
WITH (security_invoker = true) AS
SELECT * FROM content_reports;

-- P0-6: 允许通过视图插入
CREATE OR REPLACE FUNCTION insert_v_marketplace_report()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO content_reports (reporter_id, listing_id, reason, description, status, created_at)
    VALUES (NEW.reporter_id, NEW.listing_id, NEW.reason, NEW.description, COALESCE(NEW.status, 'pending'), COALESCE(NEW.created_at, CURRENT_TIMESTAMP))
    RETURNING * INTO NEW;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql
SET search_path = 'public';

DROP TRIGGER IF EXISTS trg_v_marketplace_reports_insert ON v_marketplace_reports;
CREATE TRIGGER trg_v_marketplace_reports_insert
    INSTEAD OF INSERT ON v_marketplace_reports
    FOR EACH ROW
    EXECUTE FUNCTION insert_v_marketplace_report();


-- ----------------------------------------------------------------------------
-- 19. experiments (独立)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id TEXT UNIQUE,  -- P0-4: Repository 使用的业务 ID (自动生成)
    experiment_key TEXT UNIQUE NOT NULL,
    experiment_name TEXT NOT NULL,
    description TEXT,
    hypothesis TEXT,
    variants JSONB NOT NULL,
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'paused', 'completed')),
    -- P0-5: Repository 使用 experiment_type 字段
    experiment_type TEXT DEFAULT 'ab_test' CHECK (experiment_type IN ('ab_test', 'multivariate', 'feature_rollout', 'holdout')),
    traffic_percentage INTEGER DEFAULT 100 CHECK (traffic_percentage BETWEEN 0 AND 100),
    target_tiers TEXT[] DEFAULT ARRAY[]::TEXT[],
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- P0-4: 自动生成 experiment_id
CREATE OR REPLACE FUNCTION generate_experiment_id()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.experiment_id IS NULL THEN
        NEW.experiment_id := 'exp_' || REPLACE(gen_random_uuid()::TEXT, '-', '');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql
SET search_path = 'public';

DROP TRIGGER IF EXISTS trg_experiments_generate_id ON experiments;
CREATE TRIGGER trg_experiments_generate_id
    BEFORE INSERT ON experiments
    FOR EACH ROW
    EXECUTE FUNCTION generate_experiment_id();


-- ----------------------------------------------------------------------------
-- 20. onboarding_steps (独立,无软删除)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS onboarding_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    step_key TEXT UNIQUE NOT NULL,
    step_name TEXT NOT NULL,
    description TEXT,
    step_order INTEGER NOT NULL,
    is_required BOOLEAN DEFAULT TRUE,
    target_tiers TEXT[] DEFAULT ARRAY['t1', 't2', 't3'],
    config JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);


-- ----------------------------------------------------------------------------
-- 21. articles (CMS - Manual, News, Changelog)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(200) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    summary TEXT,
    content TEXT NOT NULL,
    category VARCHAR(50) NOT NULL CHECK (category IN ('manual', 'news', 'changelog', 'faq', 'troubleshooting')),
    tags JSONB DEFAULT '[]'::jsonb,
    cover_image VARCHAR(500),

    -- 精选 (v1.1.0 新增)
    is_featured BOOLEAN DEFAULT false,

    -- 发布状态
    is_published BOOLEAN DEFAULT false,
    published_at TIMESTAMPTZ,

    -- 元数据
    author_id UUID REFERENCES profiles(id),
    sort_order INTEGER DEFAULT 0,
    view_count INTEGER DEFAULT 0,

    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    -- 软删除 (match campaigns/daily_themes/holidays pattern)
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMPTZ,
    recovery_expires_at TIMESTAMPTZ,

    -- 约束
    CONSTRAINT articles_slug_format CHECK (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
    CONSTRAINT chk_articles_deleted_at_consistency CHECK (
        (is_deleted = false AND deleted_at IS NULL) OR
        (is_deleted = true AND deleted_at IS NOT NULL)
    ),
    CONSTRAINT chk_articles_recovery_expires_at_consistency CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category);
CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(is_published, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_featured ON articles(is_featured, published_at DESC) WHERE is_featured = true;  -- v1.1.0 新增
CREATE INDEX IF NOT EXISTS idx_articles_author ON articles(author_id);
CREATE INDEX IF NOT EXISTS idx_articles_category_published
    ON articles(category, published_at DESC)
    WHERE is_published = true AND is_deleted = false;

-- updated_at 自动更新触发器
CREATE TRIGGER set_articles_updated_at
    BEFORE UPDATE ON articles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS
ALTER TABLE articles ENABLE ROW LEVEL SECURITY;

-- 公开读取已发布且未删除的文章
DROP POLICY IF EXISTS "articles_public_read" ON articles;
CREATE POLICY "articles_public_read" ON articles
    FOR SELECT
    USING (is_published = true AND is_deleted = false);

-- Admin 完全访问 (通过 service_role) — 注: service_role_all 在 03_infrastructure.sql 中也有定义
-- 此处保留 admin_all 与 static_pages 模式一致
DROP POLICY IF EXISTS "articles_admin_all" ON articles;
CREATE POLICY "articles_admin_all" ON articles
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');


-- ----------------------------------------------------------------------------
-- 22. static_pages (静态页面内容 CMS)
-- ----------------------------------------------------------------------------
-- 用于管理静态页面内容 (法律政策、公司信息、指南等)
-- 区别于 articles (动态文章内容)
-- 区别于 project 的 8 页 (book pages)
CREATE TABLE IF NOT EXISTS static_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 标识
    slug VARCHAR(100) UNIQUE NOT NULL,        -- 路由标识: billing-policy, about-us

    -- 内容
    title VARCHAR(200) NOT NULL,              -- 页面标题
    subtitle VARCHAR(500),                    -- 副标题/描述
    content TEXT NOT NULL,                    -- Markdown 内容 (支持模板变量)

    -- 元数据
    page_type VARCHAR(50) NOT NULL CHECK (page_type IN ('legal', 'company', 'guide', 'other')),
    icon VARCHAR(50),                         -- Lucide 图标名: Shield, FileText, CreditCard
    hero_gradient VARCHAR(100),               -- Hero 背景渐变 CSS: from-indigo-600 to-purple-600

    -- SEO
    meta_title VARCHAR(200),                  -- SEO 标题 (可选, 默认用 title)
    meta_description VARCHAR(500),            -- SEO 描述
    schema_data JSONB,                        -- JSON-LD Schema (可选)

    -- 额外数据 (用于复杂页面如 about-us 的团队信息)
    extra_data JSONB DEFAULT '{}'::jsonb,

    -- 状态
    is_published BOOLEAN DEFAULT false,
    published_at TIMESTAMPTZ,
    last_updated_display VARCHAR(50),         -- 显示用: "December 30, 2024"

    -- 排序
    sort_order INTEGER DEFAULT 0,

    -- 审计
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_static_pages_slug ON static_pages(slug);
CREATE INDEX IF NOT EXISTS idx_static_pages_type ON static_pages(page_type);
CREATE INDEX IF NOT EXISTS idx_static_pages_published ON static_pages(is_published);

-- RLS
ALTER TABLE static_pages ENABLE ROW LEVEL SECURITY;

-- 公开读取已发布的页面
DROP POLICY IF EXISTS "static_pages_public_read" ON static_pages;
CREATE POLICY "static_pages_public_read" ON static_pages
    FOR SELECT
    USING (is_published = true);

-- Admin 完全访问 (通过 service_role)
DROP POLICY IF EXISTS "static_pages_admin_all" ON static_pages;
CREATE POLICY "static_pages_admin_all" ON static_pages
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');


-- ----------------------------------------------------------------------------
-- 23. experiment_configs (依赖 feature_flags)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS experiment_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flag_key TEXT NOT NULL UNIQUE REFERENCES feature_flags(key) ON DELETE CASCADE,

    -- 实验设计
    hypothesis TEXT,

    -- 指标配置
    primary_metric TEXT NOT NULL DEFAULT 'conversion',
    secondary_metrics TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- 统计配置
    min_sample_size INTEGER DEFAULT 1000,
    confidence_level DECIMAL(3,2) DEFAULT 0.95,
    min_detectable_effect DECIMAL(5,4),

    -- 时间规划
    planned_duration_days INTEGER,
    planned_start_date DATE,
    planned_end_date DATE,
    actual_start_date DATE,
    actual_end_date DATE,

    -- 状态管理
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'running', 'paused', 'completed', 'stopped')),

    -- 结论
    winner_variant TEXT,
    conclusion TEXT,
    decision TEXT CHECK (decision IN ('ship_treatment', 'keep_control', 'inconclusive', NULL)),
    decided_by UUID,
    decided_at TIMESTAMPTZ,

    -- 审计
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_exp_status ON experiment_configs(status);
CREATE INDEX IF NOT EXISTS idx_exp_dates ON experiment_configs(planned_start_date, planned_end_date);


-- ----------------------------------------------------------------------------
-- 23. flag_exposures (曝光事件,无外键依赖)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS flag_exposures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    flag_key TEXT NOT NULL,
    flag_type TEXT NOT NULL,

    user_id TEXT,
    anonymous_id TEXT,

    variant TEXT NOT NULL,
    enabled BOOLEAN NOT NULL,
    reason TEXT NOT NULL,
    rule_id TEXT,

    context JSONB,
    environment TEXT DEFAULT 'production',

    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_exp_flag_time ON flag_exposures(flag_key, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_exp_user ON flag_exposures(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_exp_time ON flag_exposures(timestamp);


-- ----------------------------------------------------------------------------
-- 24. flag_audit_logs (依赖 feature_flags)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS flag_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    flag_id UUID REFERENCES feature_flags(id) ON DELETE SET NULL,
    flag_key TEXT NOT NULL,

    action TEXT NOT NULL,
    changes JSONB,
    previous_value JSONB,

    changed_by UUID NOT NULL,
    reason TEXT,

    changed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_flag ON flag_audit_logs(flag_key);
CREATE INDEX IF NOT EXISTS idx_audit_time ON flag_audit_logs(changed_at DESC);


-- ============================================================================
-- Layer 3: 依赖 Layer 2 的表
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 25. campaign_dismissals (依赖 campaigns, profiles)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS campaign_dismissals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    channel TEXT NOT NULL,
    dismissed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(campaign_id, user_id, channel)
);


-- ----------------------------------------------------------------------------
-- 26. campaign_participations (依赖 campaigns, profiles)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS campaign_participations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    credits_received INTEGER,
    claimed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(campaign_id, user_id)
);


-- ----------------------------------------------------------------------------
-- 27. experiment_assignments (依赖 experiments, profiles)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS experiment_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    variant_key TEXT NOT NULL,
    assigned_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(experiment_id, user_id)
);


-- ----------------------------------------------------------------------------
-- 28. experiment_conversions (依赖 experiments, profiles)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS experiment_conversions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    variant_key TEXT NOT NULL,
    metric_key TEXT NOT NULL,
    value NUMERIC(10, 2) DEFAULT 1.0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);


-- ----------------------------------------------------------------------------
-- 29. experiment_exposures (依赖 experiments, profiles)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS experiment_exposures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    variant_key TEXT NOT NULL,
    context JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);


-- ----------------------------------------------------------------------------
-- 30. experiment_results (依赖 feature_flags - 统一版本)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS experiment_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    flag_key TEXT NOT NULL REFERENCES feature_flags(key) ON DELETE CASCADE,
    variant TEXT NOT NULL,
    metric TEXT NOT NULL,

    date DATE NOT NULL,

    exposures INTEGER DEFAULT 0,
    conversions INTEGER DEFAULT 0,
    total_value DECIMAL(15,2) DEFAULT 0,

    conversion_rate DECIMAL(10,6),
    avg_value DECIMAL(10,2),

    cumulative_exposures INTEGER DEFAULT 0,
    cumulative_conversions INTEGER DEFAULT 0,
    cumulative_value DECIMAL(15,2) DEFAULT 0,
    cumulative_rate DECIMAL(10,6),

    relative_lift DECIMAL(10,4),
    p_value DECIMAL(10,6),
    confidence DECIMAL(5,2),
    is_significant BOOLEAN DEFAULT false,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(flag_key, variant, metric, date)
);

CREATE INDEX IF NOT EXISTS idx_results_flag ON experiment_results(flag_key);
CREATE INDEX IF NOT EXISTS idx_results_date ON experiment_results(date DESC);


-- ----------------------------------------------------------------------------
-- 31. referrals (依赖 profiles)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS referrals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    referrer_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    referee_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    referral_code TEXT NOT NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'expired')),
    reward_given BOOLEAN DEFAULT FALSE,
    reward_amount INTEGER,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(referrer_id, referee_id)
);

-- WS-11: 索引优化 — referral_code 唯一查找
CREATE UNIQUE INDEX IF NOT EXISTS idx_referrals_code
    ON referrals (referral_code);


-- ----------------------------------------------------------------------------
-- 32. user_onboarding_progress (依赖 onboarding_steps, profiles)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_onboarding_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    step_id UUID NOT NULL REFERENCES onboarding_steps(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'skipped')),
    completed_at TIMESTAMPTZ,
    skipped_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, step_id)
);


-- ============================================================================
-- RPC Functions: Articles
-- ============================================================================

-- Atomic view count increment (避免 read-modify-write 竞态条件)
CREATE OR REPLACE FUNCTION increment_article_view_count(p_article_id UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE articles
    SET view_count = view_count + 1
    WHERE id = p_article_id AND is_deleted = false;
END;
$$ LANGUAGE plpgsql;

-- Category counts 聚合查询 (替代 N+1 循环)
CREATE OR REPLACE FUNCTION get_article_category_counts()
RETURNS TABLE(category TEXT, published_count INTEGER) AS $$
BEGIN
    RETURN QUERY
    SELECT
        a.category::TEXT,
        COUNT(*) FILTER (WHERE a.is_published = true)::INTEGER AS published_count
    FROM articles a
    WHERE a.is_deleted = false
    GROUP BY a.category
    ORDER BY a.category;
END;
$$ LANGUAGE plpgsql STABLE;


-- ============================================================================
-- Analytics Event Statistics (4 group-by functions)
-- ============================================================================

CREATE OR REPLACE FUNCTION get_event_stats_by_type(
    p_start_date TEXT,
    p_end_date TEXT DEFAULT NULL
)
RETURNS TABLE(event_type TEXT, count BIGINT)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = 'public'
AS $$
BEGIN
    RETURN QUERY
    SELECT
        ae.event_type::TEXT,
        COUNT(*)::BIGINT
    FROM analytics_events ae
    WHERE ae.created_at >= p_start_date::TIMESTAMPTZ
      AND (p_end_date IS NULL OR ae.created_at <= p_end_date::TIMESTAMPTZ)
    GROUP BY ae.event_type
    ORDER BY COUNT(*) DESC;
END;
$$;

CREATE OR REPLACE FUNCTION get_event_stats_by_user(
    p_start_date TEXT,
    p_end_date TEXT DEFAULT NULL
)
RETURNS TABLE(user_id TEXT, count BIGINT)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = 'public'
AS $$
BEGIN
    RETURN QUERY
    SELECT
        ae.user_id::TEXT,
        COUNT(*)::BIGINT
    FROM analytics_events ae
    WHERE ae.created_at >= p_start_date::TIMESTAMPTZ
      AND (p_end_date IS NULL OR ae.created_at <= p_end_date::TIMESTAMPTZ)
      AND ae.user_id IS NOT NULL
    GROUP BY ae.user_id
    ORDER BY COUNT(*) DESC;
END;
$$;

CREATE OR REPLACE FUNCTION get_event_stats_by_date(
    p_start_date TEXT,
    p_end_date TEXT DEFAULT NULL
)
RETURNS TABLE(date TEXT, count BIGINT)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = 'public'
AS $$
BEGIN
    RETURN QUERY
    SELECT
        TO_CHAR(ae.created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD')::TEXT AS date,
        COUNT(*)::BIGINT
    FROM analytics_events ae
    WHERE ae.created_at >= p_start_date::TIMESTAMPTZ
      AND (p_end_date IS NULL OR ae.created_at <= p_end_date::TIMESTAMPTZ)
    GROUP BY TO_CHAR(ae.created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD')
    ORDER BY date;
END;
$$;

CREATE OR REPLACE FUNCTION get_event_stats_by_hour(
    p_start_date TEXT,
    p_end_date TEXT DEFAULT NULL
)
RETURNS TABLE(hour TEXT, count BIGINT)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = 'public'
AS $$
BEGIN
    RETURN QUERY
    SELECT
        TO_CHAR(ae.created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24')::TEXT AS hour,
        COUNT(*)::BIGINT
    FROM analytics_events ae
    WHERE ae.created_at >= p_start_date::TIMESTAMPTZ
      AND (p_end_date IS NULL OR ae.created_at <= p_end_date::TIMESTAMPTZ)
    GROUP BY TO_CHAR(ae.created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24')
    ORDER BY hour;
END;
$$;

COMMENT ON FUNCTION get_event_stats_by_type IS 'Aggregate analytics events by event_type for Admin dashboard';
COMMENT ON FUNCTION get_event_stats_by_user IS 'Aggregate analytics events by user_id for Admin dashboard';
COMMENT ON FUNCTION get_event_stats_by_date IS 'Aggregate analytics events by date for Admin dashboard';
COMMENT ON FUNCTION get_event_stats_by_hour IS 'Aggregate analytics events by hour for Admin dashboard';


-- ============================================================================
-- Stripe Webhook Result Update (best-effort)
-- ============================================================================

CREATE OR REPLACE FUNCTION update_webhook_result(
    p_event_id TEXT,
    p_result JSONB
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = 'public'
AS $$
BEGIN
    UPDATE stripe_webhook_events
    SET
        processed = TRUE,
        processed_at = CURRENT_TIMESTAMP,
        error_message = CASE
            WHEN p_result->>'status' != 'ok' THEN p_result->>'error'
            ELSE NULL
        END
    WHERE event_id = p_event_id;
END;
$$;

COMMENT ON FUNCTION update_webhook_result IS 'Update Stripe webhook processing result using existing processed/error_message columns';


-- ============================================================================
-- Entitlement 系统表 (2026-02-04 审计修复)
-- ============================================================================
-- 参考文档:
--   - docs/shared/entitlement/15-credits-lifecycle.md
--   - docs/shared/entitlement/02-tier-config.md
--   - docs/shared/entitlement/08-user-groups.md
--   - docs/shared/entitlement/10-workspace-override.md

-- ----------------------------------------------------------------------------
-- 1. credit_pools - 积分池表 (二维模型核心)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS credit_pools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    -- 来源类型
    source_type VARCHAR(30) NOT NULL CHECK (source_type IN (
        'subscription',      -- 订阅发放
        'purchase',          -- 用户购买
        'bonus_signup',      -- 注册赠送
        'bonus_referral',    -- 邀请奖励
        'bonus_campaign',    -- 营销活动
        'compensation',      -- 客服补偿
        'earning'            -- 销售收入
    )),

    -- 余额与有效期
    balance INT NOT NULL DEFAULT 0 CHECK (balance >= 0),
    expires_at TIMESTAMPTZ,  -- NULL = 永久有效

    -- 来源追踪
    source_id TEXT,          -- 关联的订单/活动/交易 ID
    description TEXT,        -- 描述信息

    -- 元数据
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引：支持 FEFO 扣费查询
CREATE INDEX IF NOT EXISTS idx_credit_pools_user_expiry
ON credit_pools(user_id, COALESCE(expires_at, '9999-12-31'::timestamptz), source_type);

-- 索引：按用户查询
CREATE INDEX IF NOT EXISTS idx_credit_pools_user ON credit_pools(user_id);

-- 索引：过期积分清理
CREATE INDEX IF NOT EXISTS idx_credit_pools_expires ON credit_pools(expires_at)
WHERE expires_at IS NOT NULL AND balance > 0;

COMMENT ON TABLE credit_pools IS '积分池表：支持二维模型（来源类型 + 有效期），FEFO 扣费策略';


-- ----------------------------------------------------------------------------
-- 2. user_feature_overrides - 用户级权限覆盖表
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_feature_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    feature_key TEXT NOT NULL,           -- 功能 Key, 如 'smart_scan', 'ai_features'
    override_value TEXT NOT NULL CHECK (override_value IN ('true', 'false', 'trial')),
    reason TEXT,                         -- 覆盖原因 (运营记录)
    expires_at TIMESTAMPTZ,              -- 过期时间 (可选, NULL=永久)
    created_by UUID,                     -- 操作人 (Admin user_id)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, feature_key)
);

CREATE INDEX IF NOT EXISTS idx_user_feature_overrides_user_id ON user_feature_overrides(user_id);
CREATE INDEX IF NOT EXISTS idx_user_feature_overrides_expires ON user_feature_overrides(expires_at) WHERE expires_at IS NOT NULL;

COMMENT ON TABLE user_feature_overrides IS '用户级权限覆盖：Admin 为特定用户开通/关闭功能';


-- ----------------------------------------------------------------------------
-- 3. user_feature_override_logs - 用户权限覆盖审计日志
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_feature_override_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    override_id UUID REFERENCES user_feature_overrides(id) ON DELETE SET NULL,
    user_id TEXT NOT NULL,                 -- 被操作用户
    feature_key TEXT NOT NULL,             -- 功能 Key
    action TEXT NOT NULL CHECK (action IN ('created', 'updated', 'deleted', 'expired')),
    old_value TEXT,                        -- 变更前的值
    new_value TEXT,                        -- 变更后的值
    reason TEXT,                           -- 变更原因
    changed_by TEXT NOT NULL,              -- 操作人 (Admin user_id 或 'system')
    changed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ufo_logs_user_id ON user_feature_override_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_ufo_logs_changed_at ON user_feature_override_logs(changed_at DESC);
CREATE INDEX IF NOT EXISTS idx_ufo_logs_feature_key ON user_feature_override_logs(feature_key);

COMMENT ON TABLE user_feature_override_logs IS '用户权限覆盖审计日志';


-- ----------------------------------------------------------------------------
-- 4. user_groups - 用户组表
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_key TEXT NOT NULL UNIQUE,          -- 唯一标识: 'kol', 'beta_testers', 'enterprise_pilot'
    group_name TEXT NOT NULL,                -- 显示名称: 'KOL 用户组', 'Beta 测试组'
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_by TEXT NOT NULL,                -- 创建人 (Admin user_id)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_groups_key ON user_groups(group_key);

COMMENT ON TABLE user_groups IS '用户组表：用于批量权限管理';


-- ----------------------------------------------------------------------------
-- 5. user_group_members - 用户组成员表
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_group_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES user_groups(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    added_by UUID NOT NULL,                  -- 添加人 (Admin user_id)
    added_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,                  -- 成员过期时间 (可选)
    UNIQUE(group_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_user_group_members_user ON user_group_members(user_id);
CREATE INDEX IF NOT EXISTS idx_user_group_members_group ON user_group_members(group_id);
CREATE INDEX IF NOT EXISTS idx_user_group_members_expires ON user_group_members(expires_at) WHERE expires_at IS NOT NULL;

COMMENT ON TABLE user_group_members IS '用户组成员表';


-- ----------------------------------------------------------------------------
-- 6. group_feature_overrides - 组级权限覆盖表
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS group_feature_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES user_groups(id) ON DELETE CASCADE,
    feature_key TEXT NOT NULL,
    override_value TEXT NOT NULL CHECK (override_value IN ('true', 'false', 'trial')),
    reason TEXT,
    expires_at TIMESTAMPTZ,                  -- 权限过期时间 (可选)
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(group_id, feature_key)
);

CREATE INDEX IF NOT EXISTS idx_group_feature_overrides_group ON group_feature_overrides(group_id);
CREATE INDEX IF NOT EXISTS idx_group_feature_overrides_expires ON group_feature_overrides(expires_at) WHERE expires_at IS NOT NULL;

COMMENT ON TABLE group_feature_overrides IS '组级权限覆盖表';


-- ----------------------------------------------------------------------------
-- 7. group_feature_override_logs - 组级权限覆盖审计日志
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS group_feature_override_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    override_id UUID REFERENCES group_feature_overrides(id) ON DELETE SET NULL,
    group_id UUID NOT NULL,
    feature_key TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('created', 'updated', 'deleted', 'expired')),
    old_value TEXT,
    new_value TEXT,
    reason TEXT,
    changed_by TEXT NOT NULL,
    changed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gfo_logs_group_id ON group_feature_override_logs(group_id);
CREATE INDEX IF NOT EXISTS idx_gfo_logs_changed_at ON group_feature_override_logs(changed_at DESC);

COMMENT ON TABLE group_feature_override_logs IS '组级权限覆盖审计日志';


-- ----------------------------------------------------------------------------
-- 8. workspace_feature_overrides - Workspace 权限覆盖表
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS workspace_feature_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    feature_key TEXT NOT NULL,
    override_value TEXT NOT NULL CHECK (override_value IN ('true', 'false', 'trial')),
    reason TEXT,                             -- 如 'Enterprise 试用', 'Team Plan 权益'
    expires_at TIMESTAMPTZ,
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(workspace_id, feature_key)
);

CREATE INDEX IF NOT EXISTS idx_workspace_feature_overrides_workspace ON workspace_feature_overrides(workspace_id);
CREATE INDEX IF NOT EXISTS idx_workspace_feature_overrides_expires ON workspace_feature_overrides(expires_at) WHERE expires_at IS NOT NULL;

COMMENT ON TABLE workspace_feature_overrides IS 'Workspace 级权限覆盖：支持 Team Plan 多租户场景';


-- ----------------------------------------------------------------------------
-- 9. workspace_feature_override_logs - Workspace 权限覆盖审计日志
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS workspace_feature_override_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    override_id UUID REFERENCES workspace_feature_overrides(id) ON DELETE SET NULL,
    workspace_id UUID NOT NULL,
    feature_key TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('created', 'updated', 'deleted', 'expired')),
    old_value TEXT,
    new_value TEXT,
    reason TEXT,
    changed_by TEXT NOT NULL,
    changed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wfo_logs_workspace_id ON workspace_feature_override_logs(workspace_id);
CREATE INDEX IF NOT EXISTS idx_wfo_logs_changed_at ON workspace_feature_override_logs(changed_at DESC);

COMMENT ON TABLE workspace_feature_override_logs IS 'Workspace 权限覆盖审计日志';


-- ============================================================================
-- Entitlement RLS 策略
-- ============================================================================

-- credit_pools RLS
ALTER TABLE credit_pools ENABLE ROW LEVEL SECURITY;

CREATE POLICY credit_pools_user_select ON credit_pools
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY credit_pools_service_all ON credit_pools
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- user_feature_overrides RLS
ALTER TABLE user_feature_overrides ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_feature_overrides_user_select ON user_feature_overrides
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY user_feature_overrides_service_all ON user_feature_overrides
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- user_groups RLS (Admin 可见)
ALTER TABLE user_groups ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_groups_service_all ON user_groups
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- user_group_members RLS
ALTER TABLE user_group_members ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_group_members_user_select ON user_group_members
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY user_group_members_service_all ON user_group_members
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- group_feature_overrides RLS (Admin 可见)
ALTER TABLE group_feature_overrides ENABLE ROW LEVEL SECURITY;

CREATE POLICY group_feature_overrides_service_all ON group_feature_overrides
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- workspace_feature_overrides RLS
ALTER TABLE workspace_feature_overrides ENABLE ROW LEVEL SECURITY;

CREATE POLICY workspace_feature_overrides_service_all ON workspace_feature_overrides
    FOR ALL TO service_role USING (true) WITH CHECK (true);


-- ============================================================================
-- 提交事务
-- ============================================================================
COMMIT;
