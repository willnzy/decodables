-- ============================================================================
-- Make Decodables - 数据库架构 (文件 2/3)
-- ============================================================================
-- 分类: 平台服务
-- 说明: Feature Flag、Analytics、Webhooks、审计、主题、营销
-- 执行顺序: 第 2 个执行
-- 生成时间: 2026-01-10
-- ============================================================================

-- 开始事务
BEGIN;

-- ============================================================================
-- 包含的表 (28)
-- ============================================================================
-- activity_logs
-- aggregated_stats
-- ai_usage_daily
-- analytics_aggregation
-- analytics_events
-- campaign_dismissals
-- campaign_participations
-- campaigns
-- clerk_webhook_events
-- config_audit_logs
-- content_reports
-- daily_metrics
-- daily_themes
-- experiment_assignments
-- experiment_conversions
-- experiment_exposures
-- experiment_results
-- experiments
-- feature_flags
-- holidays
-- monthly_metrics
-- notifications
-- onboarding_steps
-- referrals
-- stripe_webhook_events
-- system_resource_audit_logs
-- user_events
-- user_onboarding_progress


-- ----------------------------------------------------------------------------
-- 1. activity_logs
-- ----------------------------------------------------------------------------
CREATE TABLE activity_logs (
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
-- ----------------------------------------------------------------------------
CREATE TABLE aggregated_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stat_type TEXT NOT NULL,
    stat_key TEXT NOT NULL,
    stat_value NUMERIC DEFAULT 0,
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

CREATE INDEX idx_aggregated_stats_period ON aggregated_stats(period_start DESC, period_end DESC);
CREATE INDEX idx_aggregated_stats_type_key ON aggregated_stats(stat_type, stat_key);
CREATE INDEX idx_aggregated_stats_key_period ON aggregated_stats(stat_key, period_start DESC);



-- ----------------------------------------------------------------------------
-- 3. ai_usage_daily
-- ----------------------------------------------------------------------------
CREATE TABLE ai_usage_daily (
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
CREATE TABLE analytics_aggregation (
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
CREATE TABLE analytics_events (
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
-- 6. campaign_dismissals
-- ----------------------------------------------------------------------------
CREATE TABLE campaign_dismissals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    channel TEXT NOT NULL,
    dismissed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(campaign_id, user_id, channel)
,

    CONSTRAINT chk_campaign_dismissals_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);



-- ----------------------------------------------------------------------------
-- 7. campaign_participations
-- ----------------------------------------------------------------------------
CREATE TABLE campaign_participations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    credits_received INTEGER,
    claimed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(campaign_id, user_id)
,

    CONSTRAINT chk_campaign_participations_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);



-- ----------------------------------------------------------------------------
-- 8. campaigns
-- ----------------------------------------------------------------------------
CREATE TABLE campaigns (
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
    deleted_at TIMESTAMPTZ,,
    recovery_expires_at TIMESTAMPTZ,  -- 恢复期截止时间,过期后用户看不到此删除记录
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
-- 9. clerk_webhook_events
-- ----------------------------------------------------------------------------
CREATE TABLE clerk_webhook_events (
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
-- 10. config_audit_logs
-- ----------------------------------------------------------------------------
CREATE TABLE config_audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    config_key TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    action TEXT NOT NULL CHECK (action IN ('create', 'update', 'delete')),
    changed_by TEXT,
    changed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);



-- ----------------------------------------------------------------------------
-- 11. content_reports
-- ----------------------------------------------------------------------------
CREATE TABLE content_reports (
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



-- ----------------------------------------------------------------------------
-- 12. daily_metrics
-- ----------------------------------------------------------------------------
CREATE TABLE daily_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_date DATE NOT NULL UNIQUE,
    total_users INTEGER DEFAULT 0,
    active_users INTEGER DEFAULT 0,
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

CREATE INDEX idx_daily_metrics_metric_date ON daily_metrics(metric_date DESC);
CREATE INDEX idx_daily_metrics_created_at ON daily_metrics(created_at DESC);



-- ----------------------------------------------------------------------------
-- 13. daily_themes
-- ----------------------------------------------------------------------------
CREATE TABLE daily_themes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMPTZ,,
    recovery_expires_at TIMESTAMPTZ,  -- 恢复期截止时间,过期后用户看不到此删除记录
    CONSTRAINT chk_daily_themes_deleted_at_consistency
        CHECK ((is_deleted = false AND deleted_at IS NULL) OR (is_deleted = true AND deleted_at IS NOT NULL)),
    CONSTRAINT chk_daily_themes_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);



-- ----------------------------------------------------------------------------
-- 14. experiment_assignments
-- ----------------------------------------------------------------------------
CREATE TABLE experiment_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    experiment_id UUID NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    variant_key TEXT NOT NULL,
    assigned_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(experiment_id, user_id)
);



-- ----------------------------------------------------------------------------
-- 15. experiment_conversions
-- ----------------------------------------------------------------------------
CREATE TABLE experiment_conversions (
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
-- 16. experiment_exposures
-- ----------------------------------------------------------------------------
CREATE TABLE experiment_exposures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    experiment_id UUID NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    variant_key TEXT NOT NULL,
    context JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);



-- ----------------------------------------------------------------------------
-- 17. experiment_results
-- ----------------------------------------------------------------------------
CREATE TABLE experiment_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    experiment_id UUID NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    variant_key TEXT NOT NULL,
    metrics JSONB NOT NULL DEFAULT '{}',
    sample_size INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(experiment_id, date, variant_key)
);



-- ----------------------------------------------------------------------------
-- 18. experiments
-- ----------------------------------------------------------------------------
CREATE TABLE experiments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    experiment_key TEXT UNIQUE NOT NULL,
    experiment_name TEXT NOT NULL,
    description TEXT,
    hypothesis TEXT,
    variants JSONB NOT NULL,
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'paused', 'completed')),
    traffic_percentage INTEGER DEFAULT 100 CHECK (traffic_percentage BETWEEN 0 AND 100),
    target_tiers TEXT[] DEFAULT ARRAY[]::TEXT[],
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);



-- ----------------------------------------------------------------------------
-- 19. feature_flags
-- ----------------------------------------------------------------------------
CREATE TABLE feature_flags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    flag_type TEXT DEFAULT 'boolean' CHECK (flag_type IN ('boolean', 'multivariate', 'experiment')),
    enabled BOOLEAN DEFAULT FALSE,
    archived BOOLEAN DEFAULT FALSE,

    -- 环境和时间控制
    environments TEXT[] DEFAULT ARRAY['production', 'staging'],
    start_at TIMESTAMPTZ,
    end_at TIMESTAMPTZ,

    -- 灰度配置
    rollout_percentage INTEGER DEFAULT 0 CHECK (rollout_percentage BETWEEN 0 AND 100),

    -- 名单控制
    whitelist_user_ids TEXT[] DEFAULT ARRAY[]::TEXT[],
    blacklist_user_ids TEXT[] DEFAULT ARRAY[]::TEXT[],

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

    -- 审计字段
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    updated_by TEXT
);

-- 索引
CREATE INDEX idx_ff_key ON feature_flags(key);
CREATE INDEX idx_ff_enabled ON feature_flags(enabled) WHERE enabled = true AND archived = false;
CREATE INDEX idx_ff_type ON feature_flags(flag_type);
CREATE INDEX idx_ff_tags ON feature_flags USING GIN(tags);

-- 注释
COMMENT ON TABLE feature_flags IS 'Feature Flags统一表,支持boolean/multivariate/experiment三种类型';
COMMENT ON COLUMN feature_flags.key IS 'Flag唯一标识 (如 feat_new_editor)';
COMMENT ON COLUMN feature_flags.flag_type IS 'Flag类型: boolean(开关), multivariate(多变体), experiment(实验)';


-- ----------------------------------------------------------------------------
-- 19-1. experiment_configs (实验扩展配置)
-- ----------------------------------------------------------------------------
CREATE TABLE experiment_configs (
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

CREATE INDEX idx_exp_status ON experiment_configs(status);
CREATE INDEX idx_exp_dates ON experiment_configs(planned_start_date, planned_end_date);


-- ----------------------------------------------------------------------------
-- 19-2. flag_exposures (曝光事件)
-- ----------------------------------------------------------------------------
CREATE TABLE flag_exposures (
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

CREATE INDEX idx_exp_flag_time ON flag_exposures(flag_key, timestamp DESC);
CREATE INDEX idx_exp_user ON flag_exposures(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_exp_time ON flag_exposures(timestamp);


-- ----------------------------------------------------------------------------
-- 19-3. flag_audit_logs (审计日志)
-- ----------------------------------------------------------------------------
CREATE TABLE flag_audit_logs (
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

CREATE INDEX idx_audit_flag ON flag_audit_logs(flag_key);
CREATE INDEX idx_audit_time ON flag_audit_logs(changed_at DESC);


-- ----------------------------------------------------------------------------
-- 19-4. experiment_results (实验结果聚合)
-- ----------------------------------------------------------------------------
CREATE TABLE experiment_results (
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

CREATE INDEX idx_results_flag ON experiment_results(flag_key);
CREATE INDEX idx_results_date ON experiment_results(date DESC);



-- ----------------------------------------------------------------------------
-- 20. holidays
-- ----------------------------------------------------------------------------
CREATE TABLE holidays (
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
    deleted_at TIMESTAMPTZ,,
    recovery_expires_at TIMESTAMPTZ,  -- 恢复期截止时间,过期后用户看不到此删除记录
    CONSTRAINT chk_holidays_deleted_at_consistency
        CHECK ((is_deleted = false AND deleted_at IS NULL) OR (is_deleted = true AND deleted_at IS NOT NULL)),
    CONSTRAINT chk_holidays_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);



-- ----------------------------------------------------------------------------
-- 21. monthly_metrics
-- ----------------------------------------------------------------------------
CREATE TABLE monthly_metrics (
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

CREATE INDEX idx_monthly_metrics_year_month ON monthly_metrics(metric_year DESC, metric_month DESC);
CREATE INDEX idx_monthly_metrics_created_at ON monthly_metrics(created_at DESC);



-- ----------------------------------------------------------------------------
-- 22. notifications
-- ----------------------------------------------------------------------------
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    notification_type TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    action_url TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
,

    CONSTRAINT chk_notifications_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);



-- ----------------------------------------------------------------------------
-- 23. onboarding_steps
-- ----------------------------------------------------------------------------
CREATE TABLE onboarding_steps (
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
,

    CONSTRAINT chk_onboarding_steps_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);



-- ----------------------------------------------------------------------------
-- 24. referrals
-- ----------------------------------------------------------------------------
CREATE TABLE referrals (
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
,

    CONSTRAINT chk_referrals_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);



-- ----------------------------------------------------------------------------
-- 25. stripe_webhook_events
-- ----------------------------------------------------------------------------
CREATE TABLE stripe_webhook_events (
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
-- 26. system_resource_audit_logs
-- ----------------------------------------------------------------------------
CREATE TABLE system_resource_audit_logs (
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
-- 27. user_events
-- ----------------------------------------------------------------------------
CREATE TABLE user_events (
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

CREATE INDEX idx_user_events_user_id ON user_events(user_id, created_at DESC);
CREATE INDEX idx_user_events_event_type ON user_events(event_type, created_at DESC);
CREATE INDEX idx_user_events_created_at ON user_events(created_at DESC);
CREATE INDEX idx_user_events_session ON user_events(session_id) WHERE session_id IS NOT NULL;



-- ----------------------------------------------------------------------------
-- 28. user_onboarding_progress
-- ----------------------------------------------------------------------------
CREATE TABLE user_onboarding_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    step_id UUID NOT NULL REFERENCES onboarding_steps(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'skipped')),
    completed_at TIMESTAMPTZ,
    skipped_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, step_id)
,

    CONSTRAINT chk_user_onboarding_progress_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);




-- ============================================================================
-- 提交事务
-- ============================================================================
COMMIT;
