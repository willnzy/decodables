-- ============================================================
-- Migration: v3.12 - Analytics Aggregation System
-- Description: Industry-standard SaaS metrics calculation
-- Author: AI Assistant  
-- Date: 2026-01-03
-- ============================================================

-- ==========================================
-- 1. Daily Metrics Aggregation Table
-- ==========================================
-- Pre-computed daily metrics for fast dashboard queries
CREATE TABLE IF NOT EXISTS analytics_daily_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Date dimension (UTC date)
    metric_date DATE NOT NULL,
    
    -- Growth Metrics
    dau INTEGER DEFAULT 0,                      -- Daily Active Users (unique user_id + session_id)
    new_users INTEGER DEFAULT 0,                -- New registrations
    new_free INTEGER DEFAULT 0,                 -- New free tier users
    new_starter INTEGER DEFAULT 0,              -- New starter tier users
    new_pro INTEGER DEFAULT 0,                  -- New pro tier users
    
    -- Session Metrics
    total_sessions INTEGER DEFAULT 0,           -- Total unique sessions
    avg_session_duration_ms INTEGER DEFAULT 0,  -- Average session duration
    bounce_rate DECIMAL(5,2) DEFAULT 0,         -- Single-page sessions / total sessions
    
    -- Engagement Metrics
    total_events INTEGER DEFAULT 0,             -- Total events tracked
    total_page_views INTEGER DEFAULT 0,         -- Page view count
    ai_generations INTEGER DEFAULT 0,           -- AI generation attempts
    ai_success_rate DECIMAL(5,2) DEFAULT 0,     -- AI generation success rate %
    
    -- Project Metrics
    projects_created INTEGER DEFAULT 0,
    projects_exported INTEGER DEFAULT 0,
    projects_deleted INTEGER DEFAULT 0,
    
    -- Revenue Metrics (in cents for precision)
    revenue_subscription_cents INTEGER DEFAULT 0,
    revenue_credits_cents INTEGER DEFAULT 0,
    revenue_total_cents INTEGER DEFAULT 0,
    
    -- Credit Metrics
    credits_purchased INTEGER DEFAULT 0,
    credits_consumed INTEGER DEFAULT 0,
    
    -- Error Metrics
    error_count INTEGER DEFAULT 0,
    api_error_count INTEGER DEFAULT 0,
    frontend_error_count INTEGER DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(metric_date)
);

-- Index for fast date range queries
CREATE INDEX IF NOT EXISTS idx_daily_metrics_date 
    ON analytics_daily_metrics(metric_date DESC);

-- ==========================================
-- 2. Monthly Metrics Aggregation Table
-- ==========================================
CREATE TABLE IF NOT EXISTS analytics_monthly_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Month dimension (first day of month, UTC)
    metric_month DATE NOT NULL,
    
    -- Growth Metrics
    mau INTEGER DEFAULT 0,                      -- Monthly Active Users
    new_users INTEGER DEFAULT 0,                -- Total new registrations
    churned_users INTEGER DEFAULT 0,            -- Users who became inactive
    
    -- Revenue Metrics
    mrr_cents INTEGER DEFAULT 0,                -- Monthly Recurring Revenue (active subscriptions)
    arr_cents INTEGER DEFAULT 0,                -- Annual Run Rate (MRR * 12)
    arpu_cents INTEGER DEFAULT 0,               -- Average Revenue Per User
    
    -- Subscription Metrics
    active_subscribers INTEGER DEFAULT 0,
    new_subscribers INTEGER DEFAULT 0,
    cancelled_subscribers INTEGER DEFAULT 0,
    upgraded_users INTEGER DEFAULT 0,
    downgraded_users INTEGER DEFAULT 0,
    
    -- Engagement Metrics
    avg_dau INTEGER DEFAULT 0,                  -- Average daily active users
    total_sessions INTEGER DEFAULT 0,
    total_events INTEGER DEFAULT 0,
    
    -- Conversion Metrics
    visitor_to_signup_rate DECIMAL(5,2) DEFAULT 0,
    signup_to_paid_rate DECIMAL(5,2) DEFAULT 0,
    free_to_paid_rate DECIMAL(5,2) DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(metric_month)
);

CREATE INDEX IF NOT EXISTS idx_monthly_metrics_month 
    ON analytics_monthly_metrics(metric_month DESC);

-- ==========================================
-- 3. User Cohort Table (for Retention Analysis)
-- ==========================================
CREATE TABLE IF NOT EXISTS analytics_user_cohorts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- User identification
    user_id TEXT NOT NULL,
    
    -- Cohort assignment (signup week/month)
    cohort_week DATE NOT NULL,                  -- First day of signup week
    cohort_month DATE NOT NULL,                 -- First day of signup month
    
    -- User properties at signup
    signup_source TEXT,                         -- 'organic', 'referral', 'ads', etc.
    initial_tier TEXT DEFAULT 'free',
    
    -- Activity tracking
    first_activity_at TIMESTAMPTZ,
    last_activity_at TIMESTAMPTZ,
    total_sessions INTEGER DEFAULT 0,
    total_events INTEGER DEFAULT 0,
    
    -- Conversion tracking
    first_payment_at TIMESTAMPTZ,
    first_paid_tier TEXT,
    current_tier TEXT DEFAULT 'free',
    lifetime_value_cents INTEGER DEFAULT 0,
    
    -- Retention flags (bit flags for each day 1-30)
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

-- ==========================================
-- 4. Cohort Retention Summary Table
-- ==========================================
-- Pre-aggregated cohort retention rates for fast dashboard queries
CREATE TABLE IF NOT EXISTS analytics_cohort_retention (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    cohort_date DATE NOT NULL,                  -- Cohort start date
    cohort_type TEXT NOT NULL,                  -- 'week' or 'month'
    cohort_size INTEGER DEFAULT 0,              -- Total users in cohort
    
    -- Retention by period (users retained)
    retained_d1 INTEGER DEFAULT 0,
    retained_d7 INTEGER DEFAULT 0,
    retained_d14 INTEGER DEFAULT 0,
    retained_d30 INTEGER DEFAULT 0,
    retained_d60 INTEGER DEFAULT 0,
    retained_d90 INTEGER DEFAULT 0,
    
    -- Retention rates (percentage)
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

-- ==========================================
-- 5. Error Analytics Table
-- ==========================================
-- Aggregated error statistics for monitoring dashboard
CREATE TABLE IF NOT EXISTS analytics_error_summary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    summary_date DATE NOT NULL,
    
    -- Error identification
    error_code TEXT NOT NULL,                   -- Error code from exceptions.py
    error_type TEXT NOT NULL,                   -- 'api', 'frontend', 'validation', etc.
    endpoint TEXT,                              -- API endpoint if applicable
    
    -- Metrics
    occurrence_count INTEGER DEFAULT 0,
    affected_users INTEGER DEFAULT 0,           -- Unique users impacted
    affected_sessions INTEGER DEFAULT 0,        -- Unique sessions impacted
    
    -- Trend (compared to previous day)
    trend_percent DECIMAL(6,2) DEFAULT 0,       -- +10% means 10% more than yesterday
    
    -- Sample data (for debugging)
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

-- ==========================================
-- 6. Conversion Funnel Table
-- ==========================================
CREATE TABLE IF NOT EXISTS analytics_funnel_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    metric_date DATE NOT NULL,
    funnel_type TEXT NOT NULL DEFAULT 'main',   -- 'main', 'onboarding', 'upgrade', etc.
    
    -- Main Funnel Stages
    stage_visitors INTEGER DEFAULT 0,           -- Unique sessions with page_view
    stage_signups INTEGER DEFAULT 0,            -- New registrations
    stage_activated INTEGER DEFAULT 0,          -- Users who created first project
    stage_engaged INTEGER DEFAULT 0,            -- Users with 3+ sessions
    stage_converted INTEGER DEFAULT 0,          -- First payment/upgrade
    stage_retained INTEGER DEFAULT 0,           -- Still active after 30 days
    
    -- Conversion Rates (calculated)
    rate_visitor_signup DECIMAL(5,2) DEFAULT 0,
    rate_signup_activated DECIMAL(5,2) DEFAULT 0,
    rate_activated_engaged DECIMAL(5,2) DEFAULT 0,
    rate_engaged_converted DECIMAL(5,2) DEFAULT 0,
    rate_converted_retained DECIMAL(5,2) DEFAULT 0,
    
    -- Overall
    rate_visitor_converted DECIMAL(5,2) DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(metric_date, funnel_type)
);

CREATE INDEX IF NOT EXISTS idx_funnel_metrics_date 
    ON analytics_funnel_metrics(metric_date DESC, funnel_type);

-- ==========================================
-- 7. Core Metric Calculation Functions
-- ==========================================

-- Function: Calculate DAU for a specific date
-- Uses hybrid ID: user_id for logged-in users, session_id for anonymous
CREATE OR REPLACE FUNCTION calculate_dau(target_date DATE)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    dau_count INTEGER;
BEGIN
    SELECT COUNT(DISTINCT 
        CASE 
            WHEN user_id IS NOT NULL THEN user_id 
            ELSE session_id 
        END
    )
    INTO dau_count
    FROM analytics_events
    WHERE DATE(created_at AT TIME ZONE 'UTC') = target_date
      -- Filter bots
      AND (context->>'user_agent' IS NULL 
           OR NOT (
               context->>'user_agent' ~* 'bot|crawler|spider|scraper|headless'
           ));
    
    RETURN COALESCE(dau_count, 0);
END;
$$;

-- Function: Calculate MAU for a specific month
CREATE OR REPLACE FUNCTION calculate_mau(target_month DATE)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    mau_count INTEGER;
    month_start DATE;
    month_end DATE;
BEGIN
    month_start := DATE_TRUNC('month', target_month)::DATE;
    month_end := (DATE_TRUNC('month', target_month) + INTERVAL '1 month')::DATE;
    
    SELECT COUNT(DISTINCT 
        CASE 
            WHEN user_id IS NOT NULL THEN user_id 
            ELSE session_id 
        END
    )
    INTO mau_count
    FROM analytics_events
    WHERE created_at >= month_start 
      AND created_at < month_end
      AND (context->>'user_agent' IS NULL 
           OR NOT (context->>'user_agent' ~* 'bot|crawler|spider|scraper|headless'));
    
    RETURN COALESCE(mau_count, 0);
END;
$$;

-- Function: Calculate retention rate for a cohort
CREATE OR REPLACE FUNCTION calculate_cohort_retention(
    cohort_start DATE,
    cohort_end DATE,
    retention_day INTEGER
)
RETURNS TABLE (
    cohort_size INTEGER,
    retained_count INTEGER,
    retention_rate DECIMAL(5,2)
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    check_date DATE;
BEGIN
    check_date := cohort_start + (retention_day || ' days')::INTERVAL;
    
    RETURN QUERY
    WITH cohort_users AS (
        -- Users who signed up in the cohort period
        SELECT DISTINCT p.id as user_id
        FROM profiles p
        WHERE p.created_at >= cohort_start 
          AND p.created_at < cohort_end
    ),
    retained_users AS (
        -- Users from cohort who were active on retention day
        SELECT DISTINCT cu.user_id
        FROM cohort_users cu
        JOIN analytics_events ae ON ae.user_id = cu.user_id
        WHERE DATE(ae.created_at AT TIME ZONE 'UTC') = check_date
    )
    SELECT 
        (SELECT COUNT(*)::INTEGER FROM cohort_users) as cohort_size,
        (SELECT COUNT(*)::INTEGER FROM retained_users) as retained_count,
        CASE 
            WHEN (SELECT COUNT(*) FROM cohort_users) > 0 
            THEN ROUND(
                (SELECT COUNT(*) FROM retained_users)::DECIMAL / 
                (SELECT COUNT(*) FROM cohort_users) * 100, 2
            )
            ELSE 0
        END as retention_rate;
END;
$$;

-- Function: Calculate MRR (Monthly Recurring Revenue)
CREATE OR REPLACE FUNCTION calculate_mrr(target_month DATE)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    mrr_cents INTEGER;
BEGIN
    -- Sum of monthly subscription values for active subscribers
    SELECT COALESCE(SUM(
        CASE 
            WHEN tier = 'starter' THEN 999   -- $9.99/month in cents
            WHEN tier = 'pro' THEN 2499      -- $24.99/month in cents
            ELSE 0
        END
    ), 0)
    INTO mrr_cents
    FROM profiles
    WHERE tier IN ('starter', 'pro')
      AND subscription_status = 'active';
    
    RETURN mrr_cents;
END;
$$;

-- Function: Aggregate daily metrics
CREATE OR REPLACE FUNCTION aggregate_daily_metrics(target_date DATE)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    next_date DATE := target_date + 1;
BEGIN
    INSERT INTO analytics_daily_metrics (
        metric_date,
        dau,
        new_users,
        new_free,
        new_starter,
        new_pro,
        total_sessions,
        total_events,
        total_page_views,
        ai_generations,
        ai_success_rate,
        projects_created,
        projects_exported,
        error_count,
        updated_at
    )
    SELECT
        target_date,
        -- DAU (hybrid ID)
        (SELECT calculate_dau(target_date)),
        -- New users
        (SELECT COUNT(*) FROM profiles WHERE DATE(created_at AT TIME ZONE 'UTC') = target_date),
        -- New by tier
        (SELECT COUNT(*) FROM profiles WHERE DATE(created_at AT TIME ZONE 'UTC') = target_date AND tier = 'free'),
        (SELECT COUNT(*) FROM profiles WHERE DATE(created_at AT TIME ZONE 'UTC') = target_date AND tier = 'starter'),
        (SELECT COUNT(*) FROM profiles WHERE DATE(created_at AT TIME ZONE 'UTC') = target_date AND tier = 'pro'),
        -- Sessions
        (SELECT COUNT(DISTINCT session_id) FROM analytics_events 
         WHERE created_at >= target_date AND created_at < next_date),
        -- Total events
        (SELECT COUNT(*) FROM analytics_events 
         WHERE created_at >= target_date AND created_at < next_date),
        -- Page views
        (SELECT COUNT(*) FROM analytics_events 
         WHERE event_name = 'page_view' 
           AND created_at >= target_date AND created_at < next_date),
        -- AI generations
        (SELECT COUNT(*) FROM analytics_events 
         WHERE event_name IN ('ai_generate_started', 'ai_generation_start')
           AND created_at >= target_date AND created_at < next_date),
        -- AI success rate
        (SELECT 
            CASE 
                WHEN COUNT(*) FILTER (WHERE event_name IN ('ai_generate_started', 'ai_generation_start')) > 0
                THEN ROUND(
                    COUNT(*) FILTER (WHERE event_name IN ('ai_generate_success', 'ai_generation_complete'))::DECIMAL /
                    COUNT(*) FILTER (WHERE event_name IN ('ai_generate_started', 'ai_generation_start')) * 100, 2
                )
                ELSE 0
            END
         FROM analytics_events 
         WHERE created_at >= target_date AND created_at < next_date),
        -- Projects created
        (SELECT COUNT(*) FROM projects 
         WHERE DATE(created_at AT TIME ZONE 'UTC') = target_date AND is_deleted = FALSE),
        -- Projects exported (from analytics events)
        (SELECT COUNT(*) FROM analytics_events 
         WHERE event_name IN ('project_exported', 'project_export_pdf', 'project_export_zip')
           AND created_at >= target_date AND created_at < next_date),
        -- Errors
        (SELECT COUNT(*) FROM error_logs 
         WHERE DATE(created_at AT TIME ZONE 'UTC') = target_date),
        NOW()
    ON CONFLICT (metric_date) 
    DO UPDATE SET
        dau = EXCLUDED.dau,
        new_users = EXCLUDED.new_users,
        new_free = EXCLUDED.new_free,
        new_starter = EXCLUDED.new_starter,
        new_pro = EXCLUDED.new_pro,
        total_sessions = EXCLUDED.total_sessions,
        total_events = EXCLUDED.total_events,
        total_page_views = EXCLUDED.total_page_views,
        ai_generations = EXCLUDED.ai_generations,
        ai_success_rate = EXCLUDED.ai_success_rate,
        projects_created = EXCLUDED.projects_created,
        projects_exported = EXCLUDED.projects_exported,
        error_count = EXCLUDED.error_count,
        updated_at = NOW();
END;
$$;

-- Function: Aggregate error summary
CREATE OR REPLACE FUNCTION aggregate_error_summary(target_date DATE)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Clear existing data for this date
    DELETE FROM analytics_error_summary WHERE summary_date = target_date;
    
    -- Insert aggregated error data
    INSERT INTO analytics_error_summary (
        summary_date,
        error_code,
        error_type,
        endpoint,
        occurrence_count,
        affected_users,
        affected_sessions,
        sample_message,
        sample_request_id
    )
    SELECT
        target_date,
        COALESCE(error_code, 'UNKNOWN'),
        COALESCE(error_type, 'OTHER'),
        endpoint,
        COUNT(*),
        COUNT(DISTINCT user_id),
        COUNT(DISTINCT session_id),
        (ARRAY_AGG(message ORDER BY created_at DESC))[1],
        (ARRAY_AGG(context->>'request_id' ORDER BY created_at DESC))[1]
    FROM error_logs
    WHERE DATE(created_at AT TIME ZONE 'UTC') = target_date
    GROUP BY error_code, error_type, endpoint;
    
    -- Calculate trend compared to previous day
    UPDATE analytics_error_summary curr
    SET trend_percent = CASE 
        WHEN prev.occurrence_count > 0 
        THEN ROUND(((curr.occurrence_count - prev.occurrence_count)::DECIMAL / prev.occurrence_count) * 100, 2)
        ELSE 100
    END
    FROM analytics_error_summary prev
    WHERE curr.summary_date = target_date
      AND prev.summary_date = target_date - 1
      AND curr.error_code = prev.error_code
      AND curr.error_type = prev.error_type
      AND COALESCE(curr.endpoint, '') = COALESCE(prev.endpoint, '');
END;
$$;

-- Function: Update cohort retention data
CREATE OR REPLACE FUNCTION update_cohort_retention()
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    cohort_record RECORD;
    retention_result RECORD;
BEGIN
    -- Process weekly cohorts for the last 90 days
    FOR cohort_record IN 
        SELECT DISTINCT DATE_TRUNC('week', created_at)::DATE as cohort_start
        FROM profiles
        WHERE created_at >= NOW() - INTERVAL '90 days'
        ORDER BY cohort_start
    LOOP
        -- Calculate retention for each period
        FOR retention_result IN
            SELECT * FROM calculate_cohort_retention(
                cohort_record.cohort_start,
                cohort_record.cohort_start + 7,
                unnest(ARRAY[1, 7, 14, 30, 60, 90])
            )
        LOOP
            -- Update cohort retention table
            INSERT INTO analytics_cohort_retention (
                cohort_date, cohort_type, cohort_size,
                retained_d1, rate_d1
            ) VALUES (
                cohort_record.cohort_start, 'week', retention_result.cohort_size,
                retention_result.retained_count, retention_result.retention_rate
            )
            ON CONFLICT (cohort_date, cohort_type) DO UPDATE SET
                cohort_size = EXCLUDED.cohort_size,
                updated_at = NOW();
        END LOOP;
    END LOOP;
END;
$$;

-- ==========================================
-- 8. Materialized Views for Complex Queries
-- ==========================================

-- View: DAU trend (last 30 days)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_dau_trend AS
SELECT 
    metric_date,
    dau,
    new_users,
    total_sessions,
    ai_generations,
    ai_success_rate,
    projects_created,
    error_count,
    -- 7-day moving average
    AVG(dau) OVER (ORDER BY metric_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as dau_7d_avg,
    -- Day-over-day change
    LAG(dau) OVER (ORDER BY metric_date) as dau_prev_day,
    ROUND(
        ((dau - COALESCE(LAG(dau) OVER (ORDER BY metric_date), dau))::DECIMAL / 
        NULLIF(LAG(dau) OVER (ORDER BY metric_date), 0)) * 100, 2
    ) as dau_change_pct
FROM analytics_daily_metrics
WHERE metric_date >= CURRENT_DATE - 30
ORDER BY metric_date DESC;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_dau_trend_date ON mv_dau_trend(metric_date);

-- View: Top errors (current week)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_top_errors AS
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

-- Function to refresh all materialized views
CREATE OR REPLACE FUNCTION refresh_analytics_views()
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_dau_trend;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_top_errors;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_event_summary;
END;
$$;

-- ==========================================
-- 9. Comments for Documentation
-- ==========================================
COMMENT ON TABLE analytics_daily_metrics IS 'Pre-aggregated daily SaaS metrics. Updated by scheduled ETL job.';
COMMENT ON TABLE analytics_monthly_metrics IS 'Pre-aggregated monthly SaaS metrics for long-term trends.';
COMMENT ON TABLE analytics_user_cohorts IS 'User cohort assignments for retention analysis.';
COMMENT ON TABLE analytics_cohort_retention IS 'Pre-computed cohort retention rates by period.';
COMMENT ON TABLE analytics_error_summary IS 'Daily aggregated error statistics for monitoring.';
COMMENT ON TABLE analytics_funnel_metrics IS 'Conversion funnel metrics by stage.';

COMMENT ON FUNCTION calculate_dau IS 'Calculate DAU using hybrid ID (user_id for logged in, session_id for anonymous). Filters bots.';
COMMENT ON FUNCTION calculate_mau IS 'Calculate MAU using hybrid ID. Filters bots.';
COMMENT ON FUNCTION calculate_cohort_retention IS 'Calculate retention rate for a specific cohort and retention day.';
COMMENT ON FUNCTION aggregate_daily_metrics IS 'Main ETL function to aggregate daily metrics. Run via cron at 2AM UTC.';

-- ==========================================
-- 10. Enable RLS
-- ==========================================
ALTER TABLE analytics_daily_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_monthly_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_user_cohorts ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_cohort_retention ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_error_summary ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_funnel_metrics ENABLE ROW LEVEL SECURITY;

-- Admin-only read access
CREATE POLICY "Admin read access" ON analytics_daily_metrics FOR SELECT
    USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid()::text AND role = 'admin'));
CREATE POLICY "Admin read access" ON analytics_monthly_metrics FOR SELECT
    USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid()::text AND role = 'admin'));
CREATE POLICY "Admin read access" ON analytics_error_summary FOR SELECT
    USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid()::text AND role = 'admin'));

-- Service role full access
CREATE POLICY "Service role access" ON analytics_daily_metrics FOR ALL
    USING (auth.role() = 'service_role');
CREATE POLICY "Service role access" ON analytics_monthly_metrics FOR ALL
    USING (auth.role() = 'service_role');
CREATE POLICY "Service role access" ON analytics_user_cohorts FOR ALL
    USING (auth.role() = 'service_role');
CREATE POLICY "Service role access" ON analytics_cohort_retention FOR ALL
    USING (auth.role() = 'service_role');
CREATE POLICY "Service role access" ON analytics_error_summary FOR ALL
    USING (auth.role() = 'service_role');
CREATE POLICY "Service role access" ON analytics_funnel_metrics FOR ALL
    USING (auth.role() = 'service_role');
