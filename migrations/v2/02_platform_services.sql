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
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL REFERENCES profiles(id),
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
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT REFERENCES profiles(id),
    session_id TEXT,
    event_id TEXT,
    event_name TEXT NOT NULL,
    event_type TEXT NOT NULL,
    context JSONB DEFAULT '{}',
    properties JSONB DEFAULT '{}',
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);


-- ----------------------------------------------------------------------------
-- 6. clerk_webhook_events
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clerk_webhook_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id TEXT UNIQUE NOT NULL,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMPTZ,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);


-- ----------------------------------------------------------------------------
-- 7. config_audit_logs
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS config_audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    config_key TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    action TEXT NOT NULL CHECK (action IN ('create', 'update', 'delete')),
    changed_by TEXT,
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
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sync_daily_metrics_date ON daily_metrics;
CREATE TRIGGER trg_sync_daily_metrics_date
    BEFORE INSERT OR UPDATE ON daily_metrics
    FOR EACH ROW
    EXECUTE FUNCTION sync_daily_metrics_date();


-- ----------------------------------------------------------------------------
-- 9. campaigns (依赖 profiles) - MOVED HERE: daily_themes depends on it
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
    timezone TEXT DEFAULT 'America/New_York',
    usage_limit INTEGER,
    usage_per_user INTEGER DEFAULT 1,
    usage_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'paused', 'completed')),
    is_active BOOLEAN DEFAULT TRUE,
    created_by TEXT REFERENCES profiles(id),
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
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

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
    reviewed_by TEXT,                                      -- Reviewer user_id
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


-- ----------------------------------------------------------------------------
-- 10. feature_flags
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS feature_flags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
    created_by TEXT,
    updated_by TEXT
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
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
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
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_notifications_sync_type ON notifications;
CREATE TRIGGER trg_notifications_sync_type
    BEFORE INSERT OR UPDATE ON notifications
    FOR EACH ROW
    EXECUTE FUNCTION sync_notification_type();


-- ----------------------------------------------------------------------------
-- 14. stripe_webhook_events
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stripe_webhook_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id TEXT UNIQUE NOT NULL,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMPTZ,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);


-- ----------------------------------------------------------------------------
-- 15. system_resource_audit_logs
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS system_resource_audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resource_id UUID,
    action TEXT NOT NULL,
    old_data JSONB,
    new_data JSONB,
    changed_by TEXT NOT NULL,
    changed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    ip_address TEXT,
    user_agent TEXT
);


-- ----------------------------------------------------------------------------
-- 16. user_events
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
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
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
CREATE OR REPLACE VIEW v_marketplace_reports AS
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
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_v_marketplace_reports_insert ON v_marketplace_reports;
CREATE TRIGGER trg_v_marketplace_reports_insert
    INSTEAD OF INSERT ON v_marketplace_reports
    FOR EACH ROW
    EXECUTE FUNCTION insert_v_marketplace_report();


-- ----------------------------------------------------------------------------
-- 19. experiments (独立)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS experiments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_experiments_generate_id ON experiments;
CREATE TRIGGER trg_experiments_generate_id
    BEFORE INSERT ON experiments
    FOR EACH ROW
    EXECUTE FUNCTION generate_experiment_id();


-- ----------------------------------------------------------------------------
-- 20. onboarding_steps (独立,无软删除)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS onboarding_steps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    step_key TEXT UNIQUE NOT NULL,
    step_name TEXT NOT NULL,
    description TEXT,
    step_order INTEGER NOT NULL,
    is_required BOOLEAN DEFAULT TRUE,
    target_tiers TEXT[] DEFAULT ARRAY['free', 'starter', 'pro'],
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
    author_id TEXT REFERENCES profiles(id),
    sort_order INTEGER DEFAULT 0,
    view_count INTEGER DEFAULT 0,

    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category);
CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(is_published, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_featured ON articles(is_featured, published_at DESC) WHERE is_featured = true;  -- v1.1.0 新增
CREATE INDEX IF NOT EXISTS idx_articles_slug ON articles(slug);
CREATE INDEX IF NOT EXISTS idx_articles_author ON articles(author_id);


-- ----------------------------------------------------------------------------
-- 22. experiment_configs (依赖 feature_flags)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS experiment_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
    decided_by TEXT,
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
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

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
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    flag_id UUID REFERENCES feature_flags(id) ON DELETE SET NULL,
    flag_key TEXT NOT NULL,

    action TEXT NOT NULL,
    changes JSONB,
    previous_value JSONB,

    changed_by TEXT NOT NULL,
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
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    channel TEXT NOT NULL,
    dismissed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(campaign_id, user_id, channel)
);


-- ----------------------------------------------------------------------------
-- 26. campaign_participations (依赖 campaigns, profiles)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS campaign_participations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    credits_received INTEGER,
    claimed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(campaign_id, user_id)
);


-- ----------------------------------------------------------------------------
-- 27. experiment_assignments (依赖 experiments, profiles)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS experiment_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    experiment_id UUID NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    variant_key TEXT NOT NULL,
    assigned_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(experiment_id, user_id)
);


-- ----------------------------------------------------------------------------
-- 28. experiment_conversions (依赖 experiments, profiles)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS experiment_conversions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    experiment_id UUID NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
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
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    experiment_id UUID NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    variant_key TEXT NOT NULL,
    context JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);


-- ----------------------------------------------------------------------------
-- 30. experiment_results (依赖 feature_flags - 统一版本)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS experiment_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

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
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    referrer_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    referee_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    referral_code TEXT NOT NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'expired')),
    reward_given BOOLEAN DEFAULT FALSE,
    reward_amount INTEGER,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(referrer_id, referee_id)
);


-- ----------------------------------------------------------------------------
-- 32. user_onboarding_progress (依赖 onboarding_steps, profiles)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_onboarding_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    step_id UUID NOT NULL REFERENCES onboarding_steps(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'skipped')),
    completed_at TIMESTAMPTZ,
    skipped_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, step_id)
);


-- ============================================================================
-- 提交事务
-- ============================================================================
COMMIT;
