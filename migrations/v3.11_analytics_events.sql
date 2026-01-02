-- ============================================================
-- Migration: v3.11 - Analytics Events System
-- Description: Behavioral analytics for data-driven insights
-- Author: AI Assistant
-- Date: 2026-01-03
-- ============================================================

-- ==========================================
-- IMPORTANT: Distinction from activity_logs
-- ==========================================
-- activity_logs: Security audit (admin/user visible) - low volume, high importance
-- analytics_events: Data analytics (internal) - high volume, for product insights
-- 
-- DO NOT merge these tables - they serve different purposes!

-- ==========================================
-- 1. Analytics Events Table
-- ==========================================
CREATE TABLE IF NOT EXISTS analytics_events (
    -- Primary Key: UUID for distributed systems compatibility
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Event identification
    event_name TEXT NOT NULL,
    
    -- User identification
    user_id TEXT,                    -- Nullable: anonymous users have no user_id
    session_id TEXT NOT NULL,        -- Always present: browser session tracking
    anonymous_id TEXT,               -- Device fingerprint for cross-session tracking
    
    -- Dynamic properties (JSONB for flexibility)
    properties JSONB DEFAULT '{}',   -- Event-specific data: { "project_id": "...", "duration": 120 }
    context JSONB DEFAULT '{}',      -- Environment info: { "user_agent": "...", "ip": "...", "url": "..." }
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Source identification
    source TEXT DEFAULT 'web',       -- 'web', 'api', 'server', 'mobile'
    
    -- Optional: Event grouping for batch processing
    batch_id TEXT                    -- For identifying events sent in same batch
);

-- ==========================================
-- 2. Performance Indexes
-- ==========================================

-- Primary query patterns: filter by event_name and time range
CREATE INDEX IF NOT EXISTS idx_analytics_events_name_created 
    ON analytics_events(event_name, created_at DESC);

-- User-centric queries: find all events for a user
CREATE INDEX IF NOT EXISTS idx_analytics_events_user_id 
    ON analytics_events(user_id) 
    WHERE user_id IS NOT NULL;

-- Session analysis: track user journey
CREATE INDEX IF NOT EXISTS idx_analytics_events_session_id 
    ON analytics_events(session_id, created_at);

-- Time-based partitioning queries
CREATE INDEX IF NOT EXISTS idx_analytics_events_created_at 
    ON analytics_events(created_at DESC);

-- GIN index for JSONB properties queries
-- Enables: WHERE properties->>'project_id' = 'xxx'
-- Or: WHERE properties @> '{"model": "flux"}'
CREATE INDEX IF NOT EXISTS idx_analytics_events_properties 
    ON analytics_events USING GIN (properties);

-- GIN index for context queries (user_agent analysis, etc.)
CREATE INDEX IF NOT EXISTS idx_analytics_events_context 
    ON analytics_events USING GIN (context);

-- ==========================================
-- 3. RLS Policies
-- ==========================================

-- Enable RLS (important for Supabase)
ALTER TABLE analytics_events ENABLE ROW LEVEL SECURITY;

-- Policy: Service role can do everything (for server-side writes)
CREATE POLICY "Service role full access" ON analytics_events
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- Policy: Authenticated users can insert their own events
-- (for direct client tracking if needed)
CREATE POLICY "Users can insert own events" ON analytics_events
    FOR INSERT
    WITH CHECK (
        user_id IS NULL 
        OR user_id = auth.uid()::text
    );

-- Policy: Admin can read all events
CREATE POLICY "Admin can read all events" ON analytics_events
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE id = auth.uid()::text 
            AND role = 'admin'
        )
    );

-- ==========================================
-- 4. Helper Functions
-- ==========================================

-- Function: Batch insert events (for high-throughput ingestion)
CREATE OR REPLACE FUNCTION insert_analytics_events_batch(
    events JSONB
)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    inserted_count INTEGER;
BEGIN
    INSERT INTO analytics_events (
        event_name,
        user_id,
        session_id,
        anonymous_id,
        properties,
        context,
        source,
        batch_id,
        created_at
    )
    SELECT 
        e->>'event_name',
        e->>'user_id',
        e->>'session_id',
        e->>'anonymous_id',
        COALESCE((e->'properties')::jsonb, '{}'::jsonb),
        COALESCE((e->'context')::jsonb, '{}'::jsonb),
        COALESCE(e->>'source', 'web'),
        e->>'batch_id',
        COALESCE((e->>'created_at')::timestamptz, NOW())
    FROM jsonb_array_elements(events) AS e;
    
    GET DIAGNOSTICS inserted_count = ROW_COUNT;
    RETURN inserted_count;
END;
$$;

-- Function: Get event counts by name (for dashboard)
CREATE OR REPLACE FUNCTION get_event_counts(
    start_date TIMESTAMPTZ DEFAULT NOW() - INTERVAL '7 days',
    end_date TIMESTAMPTZ DEFAULT NOW()
)
RETURNS TABLE (
    event_name TEXT,
    total_count BIGINT,
    unique_users BIGINT,
    unique_sessions BIGINT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ae.event_name,
        COUNT(*)::BIGINT AS total_count,
        COUNT(DISTINCT ae.user_id)::BIGINT AS unique_users,
        COUNT(DISTINCT ae.session_id)::BIGINT AS unique_sessions
    FROM analytics_events ae
    WHERE ae.created_at BETWEEN start_date AND end_date
    GROUP BY ae.event_name
    ORDER BY total_count DESC;
END;
$$;

-- Function: Get user journey (events in order for a session)
CREATE OR REPLACE FUNCTION get_session_journey(
    p_session_id TEXT
)
RETURNS TABLE (
    event_name TEXT,
    properties JSONB,
    created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ae.event_name,
        ae.properties,
        ae.created_at
    FROM analytics_events ae
    WHERE ae.session_id = p_session_id
    ORDER BY ae.created_at ASC;
END;
$$;

-- ==========================================
-- 5. Data Retention (Optional - Enable if needed)
-- ==========================================

-- Function: Clean old analytics events (call via cron job)
-- Keeps data for 90 days by default
CREATE OR REPLACE FUNCTION cleanup_old_analytics_events(
    retention_days INTEGER DEFAULT 90
)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM analytics_events
    WHERE created_at < NOW() - (retention_days || ' days')::INTERVAL;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$;

-- ==========================================
-- 6. Materialized Views for Common Queries
-- ==========================================

-- Daily event summary (refresh periodically via cron)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_daily_event_summary AS
SELECT 
    DATE_TRUNC('day', created_at) AS event_date,
    event_name,
    COUNT(*) AS event_count,
    COUNT(DISTINCT user_id) AS unique_users,
    COUNT(DISTINCT session_id) AS unique_sessions
FROM analytics_events
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', created_at), event_name
ORDER BY event_date DESC, event_count DESC;

-- Create index on materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_daily_event_summary 
    ON mv_daily_event_summary(event_date, event_name);

-- Function to refresh the materialized view
CREATE OR REPLACE FUNCTION refresh_analytics_summary()
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_event_summary;
END;
$$;

-- ==========================================
-- 7. Comments for Documentation
-- ==========================================

COMMENT ON TABLE analytics_events IS 'High-volume behavioral analytics events for product insights. Separate from activity_logs (security audit).';
COMMENT ON COLUMN analytics_events.event_name IS 'Event type: page_view, btn_click, ai_generate_success, etc.';
COMMENT ON COLUMN analytics_events.user_id IS 'Clerk user ID (null for anonymous users)';
COMMENT ON COLUMN analytics_events.session_id IS 'Browser session ID for journey tracking';
COMMENT ON COLUMN analytics_events.anonymous_id IS 'Device fingerprint stored in localStorage';
COMMENT ON COLUMN analytics_events.properties IS 'Event-specific dynamic data as JSONB';
COMMENT ON COLUMN analytics_events.context IS 'Environment info: user_agent, ip, url, referrer';
COMMENT ON COLUMN analytics_events.source IS 'Event source: web, api, server, mobile';

-- ==========================================
-- Standard Event Names Reference
-- ==========================================
-- Page Views:
--   page_view                 - Page load
-- 
-- User Actions:
--   btn_click                 - Button click (properties: { button_id, button_text })
--   form_submit               - Form submission
--   search                    - Search query (properties: { query, results_count })
--
-- Project Actions:
--   project_created           - New project
--   project_opened            - Project opened in editor
--   project_saved             - Project saved
--   project_exported          - PDF/ZIP export
--   project_duplicated        - Project duplicated
--   project_deleted           - Project deleted
--
-- AI Features:
--   ai_generate_started       - AI generation initiated
--   ai_generate_success       - AI generation completed (properties: { cost_credits, model, duration_ms })
--   ai_generate_failed        - AI generation failed (properties: { error_code })
--
-- Marketplace:
--   marketplace_view          - Item viewed
--   marketplace_purchase      - Item purchased
--   marketplace_publish       - Item published
--
-- Auth:
--   user_signed_up            - New registration
--   user_signed_in            - Login
--   user_signed_out           - Logout
--
-- Payments:
--   checkout_started          - Checkout initiated
--   checkout_completed        - Payment successful
--   subscription_changed      - Plan upgrade/downgrade
