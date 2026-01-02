-- ==============================================================================
-- Make Decodables - Fix Admin Panel Dependencies
-- 
-- 这个脚本创建 Admin 面板所需的所有表、视图和初始数据
-- 解决 admin 报错问题
-- 
-- 在 Supabase SQL Editor 中运行
-- ==============================================================================

-- ==========================================
-- 1. 创建 Analytics 聚合表
-- ==========================================

-- 1.1 Daily Metrics Table
CREATE TABLE IF NOT EXISTS analytics_daily_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_date DATE NOT NULL,
    dau INTEGER DEFAULT 0,
    new_users INTEGER DEFAULT 0,
    new_free INTEGER DEFAULT 0,
    new_starter INTEGER DEFAULT 0,
    new_pro INTEGER DEFAULT 0,
    total_sessions INTEGER DEFAULT 0,
    avg_session_duration_ms INTEGER DEFAULT 0,
    bounce_rate DECIMAL(5,2) DEFAULT 0,
    total_events INTEGER DEFAULT 0,
    total_page_views INTEGER DEFAULT 0,
    ai_generations INTEGER DEFAULT 0,
    ai_success_rate DECIMAL(5,2) DEFAULT 0,
    projects_created INTEGER DEFAULT 0,
    projects_exported INTEGER DEFAULT 0,
    projects_deleted INTEGER DEFAULT 0,
    revenue_subscription_cents INTEGER DEFAULT 0,
    revenue_credits_cents INTEGER DEFAULT 0,
    revenue_total_cents INTEGER DEFAULT 0,
    credits_purchased INTEGER DEFAULT 0,
    credits_consumed INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    api_error_count INTEGER DEFAULT 0,
    frontend_error_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(metric_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_metrics_date 
    ON analytics_daily_metrics(metric_date DESC);

-- 1.2 Monthly Metrics Table
CREATE TABLE IF NOT EXISTS analytics_monthly_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_month DATE NOT NULL,
    mau INTEGER DEFAULT 0,
    new_users INTEGER DEFAULT 0,
    churned_users INTEGER DEFAULT 0,
    mrr_cents INTEGER DEFAULT 0,
    arr_cents INTEGER DEFAULT 0,
    arpu_cents INTEGER DEFAULT 0,
    active_subscribers INTEGER DEFAULT 0,
    new_subscribers INTEGER DEFAULT 0,
    cancelled_subscribers INTEGER DEFAULT 0,
    upgraded_users INTEGER DEFAULT 0,
    downgraded_users INTEGER DEFAULT 0,
    avg_dau INTEGER DEFAULT 0,
    total_sessions INTEGER DEFAULT 0,
    total_events INTEGER DEFAULT 0,
    visitor_to_signup_rate DECIMAL(5,2) DEFAULT 0,
    signup_to_paid_rate DECIMAL(5,2) DEFAULT 0,
    free_to_paid_rate DECIMAL(5,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(metric_month)
);

CREATE INDEX IF NOT EXISTS idx_monthly_metrics_month 
    ON analytics_monthly_metrics(metric_month DESC);

-- 1.3 User Cohorts Table
CREATE TABLE IF NOT EXISTS analytics_user_cohorts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    cohort_week DATE NOT NULL,
    cohort_month DATE NOT NULL,
    signup_source TEXT,
    initial_tier TEXT DEFAULT 'free',
    first_activity_at TIMESTAMPTZ,
    last_activity_at TIMESTAMPTZ,
    total_sessions INTEGER DEFAULT 0,
    total_events INTEGER DEFAULT 0,
    first_payment_at TIMESTAMPTZ,
    first_paid_tier TEXT,
    current_tier TEXT DEFAULT 'free',
    lifetime_value_cents INTEGER DEFAULT 0,
    retention_d1 BOOLEAN DEFAULT FALSE,
    retention_d7 BOOLEAN DEFAULT FALSE,
    retention_d14 BOOLEAN DEFAULT FALSE,
    retention_d30 BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);

CREATE INDEX IF NOT EXISTS idx_user_cohorts_week ON analytics_user_cohorts(cohort_week);
CREATE INDEX IF NOT EXISTS idx_user_cohorts_month ON analytics_user_cohorts(cohort_month);
CREATE INDEX IF NOT EXISTS idx_user_cohorts_last_activity ON analytics_user_cohorts(last_activity_at DESC);

-- 1.4 Cohort Retention Table
CREATE TABLE IF NOT EXISTS analytics_cohort_retention (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cohort_date DATE NOT NULL,
    cohort_type TEXT NOT NULL,
    cohort_size INTEGER DEFAULT 0,
    retained_d1 INTEGER DEFAULT 0,
    retained_d7 INTEGER DEFAULT 0,
    retained_d14 INTEGER DEFAULT 0,
    retained_d30 INTEGER DEFAULT 0,
    retained_d60 INTEGER DEFAULT 0,
    retained_d90 INTEGER DEFAULT 0,
    rate_d1 DECIMAL(5,2) DEFAULT 0,
    rate_d7 DECIMAL(5,2) DEFAULT 0,
    rate_d14 DECIMAL(5,2) DEFAULT 0,
    rate_d30 DECIMAL(5,2) DEFAULT 0,
    rate_d60 DECIMAL(5,2) DEFAULT 0,
    rate_d90 DECIMAL(5,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(cohort_date, cohort_type)
);

CREATE INDEX IF NOT EXISTS idx_cohort_retention_date 
    ON analytics_cohort_retention(cohort_date DESC, cohort_type);

-- 1.5 Error Summary Table
CREATE TABLE IF NOT EXISTS analytics_error_summary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    summary_date DATE NOT NULL,
    error_code TEXT NOT NULL,
    error_type TEXT NOT NULL,
    endpoint TEXT,
    occurrence_count INTEGER DEFAULT 0,
    affected_users INTEGER DEFAULT 0,
    affected_sessions INTEGER DEFAULT 0,
    trend_percent DECIMAL(6,2) DEFAULT 0,
    sample_message TEXT,
    sample_request_id TEXT,
    sample_stack_trace TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(summary_date, error_code, error_type, endpoint)
);

CREATE INDEX IF NOT EXISTS idx_error_summary_date 
    ON analytics_error_summary(summary_date DESC);
CREATE INDEX IF NOT EXISTS idx_error_summary_code 
    ON analytics_error_summary(error_code, summary_date DESC);

-- 1.6 Funnel Metrics Table
CREATE TABLE IF NOT EXISTS analytics_funnel_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_date DATE NOT NULL,
    funnel_type TEXT NOT NULL DEFAULT 'main',
    stage_visitors INTEGER DEFAULT 0,
    stage_signups INTEGER DEFAULT 0,
    stage_activated INTEGER DEFAULT 0,
    stage_engaged INTEGER DEFAULT 0,
    stage_converted INTEGER DEFAULT 0,
    stage_retained INTEGER DEFAULT 0,
    rate_visitor_signup DECIMAL(5,2) DEFAULT 0,
    rate_signup_activated DECIMAL(5,2) DEFAULT 0,
    rate_activated_engaged DECIMAL(5,2) DEFAULT 0,
    rate_engaged_converted DECIMAL(5,2) DEFAULT 0,
    rate_converted_retained DECIMAL(5,2) DEFAULT 0,
    rate_visitor_converted DECIMAL(5,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(metric_date, funnel_type)
);

CREATE INDEX IF NOT EXISTS idx_funnel_metrics_date 
    ON analytics_funnel_metrics(metric_date DESC, funnel_type);

-- ==========================================
-- 2. 确保 analytics_events 表结构完整（必须在创建视图之前）
-- ==========================================

-- 添加可能缺失的列
ALTER TABLE analytics_events ADD COLUMN IF NOT EXISTS event_name TEXT;
ALTER TABLE analytics_events ADD COLUMN IF NOT EXISTS context JSONB DEFAULT '{}'::jsonb;

-- 如果 event_name 为空，从 event_type 复制
UPDATE analytics_events SET event_name = event_type WHERE event_name IS NULL;

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_analytics_events_event_name ON analytics_events(event_name);
CREATE INDEX IF NOT EXISTS idx_analytics_events_context ON analytics_events USING gin(context);

-- ==========================================
-- 3. 创建物化视图
-- ==========================================

-- 2.1 DAU Trend View
DROP MATERIALIZED VIEW IF EXISTS mv_dau_trend;
CREATE MATERIALIZED VIEW mv_dau_trend AS
SELECT 
    metric_date,
    dau,
    new_users,
    total_sessions,
    ai_generations,
    ai_success_rate,
    projects_created,
    error_count,
    AVG(dau) OVER (ORDER BY metric_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as dau_7d_avg,
    LAG(dau) OVER (ORDER BY metric_date) as dau_prev_day,
    ROUND(
        ((dau - COALESCE(LAG(dau) OVER (ORDER BY metric_date), dau))::DECIMAL / 
        NULLIF(LAG(dau) OVER (ORDER BY metric_date), 0)) * 100, 2
    ) as dau_change_pct
FROM analytics_daily_metrics
WHERE metric_date >= CURRENT_DATE - 30
ORDER BY metric_date DESC;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_dau_trend_date ON mv_dau_trend(metric_date);

-- 2.2 Top Errors View
DROP MATERIALIZED VIEW IF EXISTS mv_top_errors;
CREATE MATERIALIZED VIEW mv_top_errors AS
SELECT 
    error_code,
    error_type,
    endpoint,
    SUM(occurrence_count) as total_occurrences,
    SUM(affected_users) as total_affected_users,
    AVG(trend_percent) as avg_trend,
    MAX(sample_message) as latest_message,
    MAX(sample_request_id) as latest_request_id
FROM analytics_error_summary
WHERE summary_date >= CURRENT_DATE - 7
GROUP BY error_code, error_type, endpoint
ORDER BY total_occurrences DESC
LIMIT 50;

-- 2.3 Daily Event Summary View (缺失的视图)
DROP MATERIALIZED VIEW IF EXISTS mv_daily_event_summary;
CREATE MATERIALIZED VIEW mv_daily_event_summary AS
SELECT 
    DATE(created_at AT TIME ZONE 'UTC') as event_date,
    COALESCE(event_name, event_type) as event_name,
    event_type,
    COUNT(*) as event_count,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(DISTINCT session_id) as unique_sessions
FROM analytics_events
WHERE created_at >= CURRENT_DATE - 30
GROUP BY DATE(created_at AT TIME ZONE 'UTC'), COALESCE(event_name, event_type), event_type
ORDER BY event_date DESC, event_count DESC;

-- ==========================================
-- 4. 启用 RLS
-- ==========================================

ALTER TABLE analytics_daily_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_monthly_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_user_cohorts ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_cohort_retention ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_error_summary ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_funnel_metrics ENABLE ROW LEVEL SECURITY;

-- 删除可能存在的旧策略
DROP POLICY IF EXISTS "Admin read access" ON analytics_daily_metrics;
DROP POLICY IF EXISTS "Admin read access" ON analytics_monthly_metrics;
DROP POLICY IF EXISTS "Admin read access" ON analytics_error_summary;
DROP POLICY IF EXISTS "Service role access" ON analytics_daily_metrics;
DROP POLICY IF EXISTS "Service role access" ON analytics_monthly_metrics;
DROP POLICY IF EXISTS "Service role access" ON analytics_user_cohorts;
DROP POLICY IF EXISTS "Service role access" ON analytics_cohort_retention;
DROP POLICY IF EXISTS "Service role access" ON analytics_error_summary;
DROP POLICY IF EXISTS "Service role access" ON analytics_funnel_metrics;

-- Service role full access (后端 API 使用)
CREATE POLICY "Service role full access" ON analytics_daily_metrics FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access" ON analytics_monthly_metrics FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access" ON analytics_user_cohorts FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access" ON analytics_cohort_retention FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access" ON analytics_error_summary FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access" ON analytics_funnel_metrics FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ==========================================
-- 5. 确保 system_configs 表存在
-- ==========================================

CREATE TABLE IF NOT EXISTS system_configs (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    config_key text NOT NULL UNIQUE,
    config_value jsonb NOT NULL,
    category text NOT NULL DEFAULT 'general',
    description text,
    is_active boolean DEFAULT true,
    updated_at timestamptz DEFAULT now(),
    updated_by text,
    CONSTRAINT system_configs_pkey PRIMARY KEY (id)
);

ALTER TABLE system_configs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role full access to system_configs" ON system_configs;
CREATE POLICY "Service role full access to system_configs" ON system_configs FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE INDEX IF NOT EXISTS idx_system_configs_key ON system_configs(config_key);
CREATE INDEX IF NOT EXISTS idx_system_configs_category ON system_configs(category);

-- ==========================================
-- 6. 插入初始 system_configs 数据
-- ==========================================

INSERT INTO system_configs (config_key, config_value, category, description) VALUES
-- Rate limits
('rate_limit.payment.checkout', '{"limit": 5, "window": "minute", "enabled": true}', 'rate_limit', 'Checkout API rate limit'),
('rate_limit.payment.portal', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', 'Billing portal rate limit'),
('rate_limit.marketplace.purchase', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', 'Marketplace purchase rate limit'),
('rate_limit.generate.story', '{"limit": 20, "window": "minute", "enabled": true}', 'rate_limit', 'AI story generation rate limit'),
('rate_limit.generate.images', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', 'AI image generation rate limit'),
('rate_limit.tools.ocr', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', 'OCR rate limit'),
('rate_limit.export.pdf', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', 'PDF export rate limit'),
('rate_limit.export.zip', '{"limit": 5, "window": "minute", "enabled": true}', 'rate_limit', 'ZIP export rate limit'),
('rate_limit.export.preview', '{"limit": 20, "window": "minute", "enabled": true}', 'rate_limit', 'Preview generation rate limit'),
('rate_limit.projects.create', '{"limit": 20, "window": "minute", "enabled": true}', 'rate_limit', 'Project creation rate limit'),
('rate_limit.assets.upload', '{"limit": 20, "window": "minute", "enabled": true}', 'rate_limit', 'Asset upload rate limit'),
('rate_limit.marketplace.publish', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', 'Listing publish rate limit'),
('rate_limit.support.email', '{"limit": 3, "window": "minute", "enabled": true}', 'rate_limit', 'Support email rate limit'),
('rate_limit.contact.form', '{"limit": 3, "window": "minute", "enabled": true}', 'rate_limit', 'Contact form rate limit'),
('rate_limit.feedback.submit', '{"limit": 3, "window": "minute", "enabled": true}', 'rate_limit', 'Feedback submission rate limit'),
('rate_limit.admin.credits', '{"limit": 30, "window": "minute", "enabled": true}', 'rate_limit', 'Admin credit adjustment rate limit'),
('rate_limit.admin.tier', '{"limit": 30, "window": "minute", "enabled": true}', 'rate_limit', 'Admin tier update rate limit'),
('rate_limit.admin.refund', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', 'Admin refund rate limit'),
('rate_limit.admin.subscription', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', 'Admin subscription operations rate limit'),
('rate_limit.admin.broadcast', '{"limit": 5, "window": "minute", "enabled": true}', 'rate_limit', 'Admin broadcast rate limit'),
('rate_limit.admin.search', '{"limit": 60, "window": "minute", "enabled": true}', 'rate_limit', 'Admin search rate limit'),
('rate_limit.marketplace.list', '{"limit": 60, "window": "minute", "enabled": true}', 'rate_limit', 'Marketplace listing rate limit'),
('rate_limit.analytics.events', '{"limit": 60, "window": "minute", "enabled": true}', 'rate_limit', 'Analytics event ingestion rate limit'),
('rate_limit.global.default', '{"limit": 100, "window": "minute", "enabled": true}', 'rate_limit', 'Global default rate limit'),
('rate_limit.global.enabled', '{"enabled": true}', 'rate_limit', 'Enable/disable global rate limiting'),
-- Analytics
('analytics.enabled', '{"enabled": true}', 'analytics', 'Enable analytics tracking'),
('analytics.sampling_rate', '{"critical": 1.0, "important": 1.0, "normal": 0.3, "debug": 0.0}', 'analytics', 'Event sampling rates'),
('analytics.min_level', '{"level": "normal"}', 'analytics', 'Minimum tracking level'),
-- Feature flags
('feature.marketplace.enabled', '{"enabled": true}', 'feature', 'Enable marketplace feature'),
('feature.ai_generation.enabled', '{"enabled": true}', 'feature', 'Enable AI generation feature'),
('feature.ocr.enabled', '{"enabled": true}', 'feature', 'Enable OCR feature'),
-- UI texts (可配置的 CTA 文本等)
('ui.cta.primary', '{"text": "Start Creating", "subtitle": "No credit card required"}', 'ui', 'Primary CTA button text'),
('ui.announcement.enabled', '{"enabled": false, "text": "", "link": ""}', 'ui', 'Announcement bar config')
ON CONFLICT (config_key) DO NOTHING;

-- ==========================================
-- 7. 插入初始 Analytics 数据（避免空查询错误）
-- ==========================================

-- 插入今天和过去7天的占位数据
INSERT INTO analytics_daily_metrics (metric_date, dau, new_users, total_sessions, total_events)
SELECT 
    d::date,
    0, 0, 0, 0
FROM generate_series(
    CURRENT_DATE - INTERVAL '7 days',
    CURRENT_DATE,
    '1 day'::interval
) d
ON CONFLICT (metric_date) DO NOTHING;

-- 插入当月的月度数据
INSERT INTO analytics_monthly_metrics (metric_month, mau, new_users)
VALUES (DATE_TRUNC('month', CURRENT_DATE)::date, 0, 0)
ON CONFLICT (metric_month) DO NOTHING;

-- 插入一条空的 cohort 数据
INSERT INTO analytics_cohort_retention (cohort_date, cohort_type, cohort_size)
VALUES (DATE_TRUNC('week', CURRENT_DATE)::date, 'week', 0)
ON CONFLICT (cohort_date, cohort_type) DO NOTHING;

-- 插入一条空的 funnel 数据
INSERT INTO analytics_funnel_metrics (metric_date, funnel_type)
VALUES (CURRENT_DATE, 'main')
ON CONFLICT (metric_date, funnel_type) DO NOTHING;

-- ==========================================
-- 8. 刷新物化视图
-- ==========================================

REFRESH MATERIALIZED VIEW mv_dau_trend;
REFRESH MATERIALIZED VIEW mv_top_errors;
REFRESH MATERIALIZED VIEW mv_daily_event_summary;

-- ==========================================
-- 9. 创建辅助函数
-- ==========================================

-- 刷新所有 analytics 物化视图的函数
CREATE OR REPLACE FUNCTION refresh_analytics_views()
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_dau_trend;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_top_errors;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_event_summary;
EXCEPTION WHEN OTHERS THEN
    -- 如果 CONCURRENTLY 失败，使用普通刷新
    REFRESH MATERIALIZED VIEW mv_dau_trend;
    REFRESH MATERIALIZED VIEW mv_top_errors;
    REFRESH MATERIALIZED VIEW mv_daily_event_summary;
END;
$$;

-- ==========================================
-- 10. 验证
-- ==========================================

SELECT '✅ 表创建检查' as check_type;
SELECT 
    table_name,
    CASE WHEN EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = t.table_name
    ) THEN '✅' ELSE '❌' END as status
FROM (VALUES 
    ('analytics_daily_metrics'),
    ('analytics_monthly_metrics'),
    ('analytics_user_cohorts'),
    ('analytics_cohort_retention'),
    ('analytics_error_summary'),
    ('analytics_funnel_metrics'),
    ('system_configs')
) as t(table_name);

SELECT '✅ 物化视图检查' as check_type;
SELECT 
    matviewname as view_name,
    '✅' as status
FROM pg_matviews
WHERE schemaname = 'public'
AND matviewname IN ('mv_dau_trend', 'mv_top_errors', 'mv_daily_event_summary');

SELECT '✅ System Configs 数据检查' as check_type;
SELECT 
    category,
    COUNT(*) as count
FROM system_configs
GROUP BY category
ORDER BY category;

SELECT '✅ Analytics 初始数据检查' as check_type;
SELECT 
    'analytics_daily_metrics' as table_name,
    COUNT(*) as row_count
FROM analytics_daily_metrics
UNION ALL
SELECT 'analytics_monthly_metrics', COUNT(*) FROM analytics_monthly_metrics
UNION ALL
SELECT 'analytics_cohort_retention', COUNT(*) FROM analytics_cohort_retention
UNION ALL
SELECT 'analytics_funnel_metrics', COUNT(*) FROM analytics_funnel_metrics;

SELECT '🎉 Admin 表修复完成!' as message;
