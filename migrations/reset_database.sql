-- ==============================================================================
-- Make Decodables Database Reset Script
-- ⚠️ WARNING: This script will DELETE ALL DATA permanently!
-- 
-- Usage:
-- 1. Backup important data first
-- 2. Execute this script in Supabase SQL Editor
-- 3. Then execute ddl.sql to reinitialize
-- ==============================================================================

-- ⚠️ 警告：此脚本会删除所有数据和表结构！
-- 请确保已备份重要数据！

-- ==============================================================================
-- Step 1: 删除所有 Storage 策略
-- ==============================================================================

DROP POLICY IF EXISTS "make-decodables-s: public read" ON storage.objects;
DROP POLICY IF EXISTS "make-decodables-s: deny insert" ON storage.objects;
DROP POLICY IF EXISTS "make-decodables-s: deny update" ON storage.objects;
DROP POLICY IF EXISTS "make-decodables-s: deny delete" ON storage.objects;
DROP POLICY IF EXISTS "make-decodables-s: service write" ON storage.objects;
DROP POLICY IF EXISTS "make-decodables-s: service update" ON storage.objects;
DROP POLICY IF EXISTS "make-decodables-s: service delete" ON storage.objects;

DROP POLICY IF EXISTS "make-decodables-u: public read" ON storage.objects;
DROP POLICY IF EXISTS "make-decodables-u: deny insert" ON storage.objects;
DROP POLICY IF EXISTS "make-decodables-u: deny update" ON storage.objects;
DROP POLICY IF EXISTS "make-decodables-u: deny delete" ON storage.objects;
DROP POLICY IF EXISTS "make-decodables-u: service write" ON storage.objects;
DROP POLICY IF EXISTS "make-decodables-u: service delete" ON storage.objects;

-- Old bucket policies (if any)
DROP POLICY IF EXISTS "generated-images: public read" ON storage.objects;
DROP POLICY IF EXISTS "user-uploads: public read" ON storage.objects;

-- ==============================================================================
-- Step 2: 删除存储桶（会删除桶内所有文件！）
-- ==============================================================================

DELETE FROM storage.objects WHERE bucket_id IN ('make-decodables-s', 'make-decodables-u', 'generated-images', 'user-uploads', 'avatars', 'magic-zine-images');
DELETE FROM storage.buckets WHERE id IN ('make-decodables-s', 'make-decodables-u', 'generated-images', 'user-uploads', 'avatars', 'magic-zine-images');

-- ==============================================================================
-- Step 3: 删除物化视图
-- ==============================================================================

DROP MATERIALIZED VIEW IF EXISTS mv_dau_trend CASCADE;
DROP MATERIALIZED VIEW IF EXISTS mv_top_errors CASCADE;
DROP MATERIALIZED VIEW IF EXISTS mv_daily_event_summary CASCADE;

-- ==============================================================================
-- Step 4: 删除视图
-- ==============================================================================

DROP VIEW IF EXISTS dashboard_projects CASCADE;
DROP VIEW IF EXISTS dashboard_assets CASCADE;
DROP VIEW IF EXISTS seller_stats_summary CASCADE;
DROP VIEW IF EXISTS v_latest_task_status CASCADE;

-- ==============================================================================
-- Step 5: 删除所有表（按依赖顺序）
-- ==============================================================================

-- Campaign related
DROP TABLE IF EXISTS campaign_dismissals CASCADE;
DROP TABLE IF EXISTS campaign_claims CASCADE;
DROP TABLE IF EXISTS campaigns CASCADE;
DROP TABLE IF EXISTS holiday_themes CASCADE;

-- Scheduled tasks
DROP TABLE IF EXISTS scheduled_task_logs CASCADE;

-- System resources & audit
DROP TABLE IF EXISTS system_resource_audit_logs CASCADE;
DROP TABLE IF EXISTS config_audit_logs CASCADE;
DROP TABLE IF EXISTS system_configs CASCADE;
DROP TABLE IF EXISTS system_resources CASCADE;

-- Content moderation
DROP TABLE IF EXISTS content_reports CASCADE;

-- Templates
DROP TABLE IF EXISTS page_prompt_templates CASCADE;
DROP TABLE IF EXISTS asset_prompt_templates CASCADE;

-- Analytics tables
DROP TABLE IF EXISTS analytics_funnel_metrics CASCADE;
DROP TABLE IF EXISTS analytics_error_summary CASCADE;
DROP TABLE IF EXISTS analytics_cohort_retention CASCADE;
DROP TABLE IF EXISTS analytics_user_cohorts CASCADE;
DROP TABLE IF EXISTS analytics_monthly_metrics CASCADE;
DROP TABLE IF EXISTS analytics_daily_metrics CASCADE;
DROP TABLE IF EXISTS aggregated_stats CASCADE;

-- Logging tables
DROP TABLE IF EXISTS error_logs CASCADE;
DROP TABLE IF EXISTS analytics_events CASCADE;
DROP TABLE IF EXISTS user_events CASCADE;
DROP TABLE IF EXISTS admin_operation_logs CASCADE;
DROP TABLE IF EXISTS activity_logs CASCADE;

-- Marketplace related
DROP TABLE IF EXISTS leaderboard_snapshots CASCADE;
DROP TABLE IF EXISTS listing_usages CASCADE;
DROP TABLE IF EXISTS user_purchases CASCADE;

-- Core tables
DROP TABLE IF EXISTS support_tickets CASCADE;
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS assets CASCADE;
DROP TABLE IF EXISTS marketplace_listings CASCADE;
DROP TABLE IF EXISTS projects CASCADE;
DROP TABLE IF EXISTS credit_transactions CASCADE;
DROP TABLE IF EXISTS user_discounts CASCADE;
DROP TABLE IF EXISTS profiles CASCADE;

-- ==============================================================================
-- Step 6: 删除函数
-- ==============================================================================

-- Admin & Auth
DROP FUNCTION IF EXISTS is_admin() CASCADE;

-- Config helpers
DROP FUNCTION IF EXISTS get_config(TEXT, TEXT) CASCADE;
DROP FUNCTION IF EXISTS get_configs_by_group(TEXT) CASCADE;
DROP FUNCTION IF EXISTS get_rate_limit_config(TEXT) CASCADE;

-- Stats helpers
DROP FUNCTION IF EXISTS get_latest_stats(VARCHAR) CASCADE;
DROP FUNCTION IF EXISTS get_stats_range(VARCHAR, DATE, DATE) CASCADE;
DROP FUNCTION IF EXISTS refresh_analytics_views() CASCADE;

-- Triggers functions
DROP FUNCTION IF EXISTS sync_listing_status() CASCADE;
DROP FUNCTION IF EXISTS update_seller_stats_on_purchase() CASCADE;
DROP FUNCTION IF EXISTS set_deleted_timestamp() CASCADE;
DROP FUNCTION IF EXISTS prevent_credit_modification() CASCADE;
DROP FUNCTION IF EXISTS update_timestamp() CASCADE;
DROP FUNCTION IF EXISTS update_system_resources_timestamp() CASCADE;

-- Holiday date calculators
DROP FUNCTION IF EXISTS calculate_us_thanksgiving(INTEGER) CASCADE;
DROP FUNCTION IF EXISTS calculate_mothers_day(INTEGER) CASCADE;
DROP FUNCTION IF EXISTS calculate_fathers_day(INTEGER) CASCADE;
DROP FUNCTION IF EXISTS calculate_dynamic_date(TEXT, INTEGER) CASCADE;

-- Task cleanup
DROP FUNCTION IF EXISTS cleanup_old_task_logs() CASCADE;

-- ==============================================================================
-- Done!
-- ==============================================================================

DO $$
BEGIN
  RAISE NOTICE '';
  RAISE NOTICE '=====================================================';
  RAISE NOTICE '✅ Database Reset Complete';
  RAISE NOTICE '=====================================================';
  RAISE NOTICE '';
  RAISE NOTICE 'All tables, views, functions, and storage buckets deleted.';
  RAISE NOTICE '';
  RAISE NOTICE 'Next step: Execute ddl.sql to reinitialize the database.';
  RAISE NOTICE '=====================================================';
END $$;
