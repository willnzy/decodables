-- ============================================================================
-- Disable Row-Level Security (RLS)
-- ============================================================================
-- This script disables RLS on all tables
-- Use this for Railway/standalone PostgreSQL or during development
-- ============================================================================

BEGIN;

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE '🔓 DISABLING ROW-LEVEL SECURITY';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'This will disable RLS on all tables';
    RAISE NOTICE 'All data will be accessible without user context restrictions';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE '';
END $$;

-- Disable RLS on all tables that might have it enabled
ALTER TABLE IF EXISTS profiles DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS projects DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS credit_transactions DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS user_generations DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS marketplace_listings DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS marketplace_purchases DISABLE ROW LEVEL SECURITY;

-- Also disable on other tables that show as UNRESTRICTED
ALTER TABLE IF EXISTS activity_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS ai_call_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS ai_usage_daily DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS analytics_aggregation DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS analytics_events DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS api_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS asset_categories DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS asset_prompt_templates DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS assets DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS campaign_dismissals DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS campaign_participations DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS campaigns DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS clerk_webhook_events DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS config_audit_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS content_reports DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS credit_purchases DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS daily_themes DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS experiment_assignments DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS experiment_results DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS experiments DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS feature_flags DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS holidays DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS marketplace_favorites DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS marketplace_reviews DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS notifications DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS onboarding_steps DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS pricing_history DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS pricing_plans DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS project_versions DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS referrals DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS scheduled_task_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS stripe_webhook_events DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS subscription_history DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS system_assets DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS system_configs DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS system_resource_audit_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS user_discounts DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS user_onboarding_progress DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS user_price_overrides DISABLE ROW LEVEL SECURITY;

-- Disable on views
ALTER VIEW IF EXISTS v_ai_usage_last_30_days DISABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '✅ RLS disabled on all tables';
    RAISE NOTICE '';
    RAISE NOTICE '🔓 All data is now accessible without restrictions';
    RAISE NOTICE '📝 Suitable for:';
    RAISE NOTICE '   - Railway deployment';
    RAISE NOTICE '   - Standalone PostgreSQL';
    RAISE NOTICE '   - Development environment';
    RAISE NOTICE '   - Single-tenant applications';
    RAISE NOTICE '';
    RAISE NOTICE '🔒 To re-enable RLS for Supabase, run: enable_rls.sql';
    RAISE NOTICE '';
END $$;

COMMIT;

-- End of RLS disablement script
