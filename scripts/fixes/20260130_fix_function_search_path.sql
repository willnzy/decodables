-- ============================================================================
-- 修复脚本: Function Search Path Mutable + ltree Extension + RLS 策略收紧
-- ============================================================================
-- 问题 1: 42 个函数未设置 search_path，存在 search_path injection 风险
-- 问题 2: ltree 扩展安装在 public schema，被 PostgREST 暴露
-- 问题 3: admin_notification_templates RLS 策略未限定角色
-- 方案:
--   - 所有函数添加 SET search_path = 'public'
--   - ltree 迁移到 extensions schema
--   - RLS 策略收紧为 service_role 专用
-- 日期: 2026-01-30
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. 修复所有函数的 search_path (使用 ALTER FUNCTION，无需重建)
-- ============================================================================

-- 01_core_business.sql 中的函数 (14个)
ALTER FUNCTION public.update_updated_at_column() SET search_path = 'public';
ALTER FUNCTION public.sync_credit_transaction_type() SET search_path = 'public';
ALTER FUNCTION public.p_get_marketplace_listings(TEXT, TEXT, TEXT, TEXT, TEXT, TEXT, INTEGER, INTEGER) SET search_path = 'public';
ALTER FUNCTION public.p_get_conversion_funnel(TEXT) SET search_path = 'public';
ALTER FUNCTION public.get_category_descendants(LTREE) SET search_path = 'public';
ALTER FUNCTION public.update_category_descendants_path(LTREE, LTREE) SET search_path = 'public';
ALTER FUNCTION public.soft_delete_category_descendants(LTREE) SET search_path = 'public';
ALTER FUNCTION public.increment_category_usage(UUID) SET search_path = 'public';
ALTER FUNCTION public.generate_user_code() SET search_path = 'public';
ALTER FUNCTION public.create_user_idempotent(TEXT, TEXT, TEXT, TEXT, TEXT, TEXT, TEXT, TEXT) SET search_path = 'public';
ALTER FUNCTION public.get_user_creation_stats(INTEGER) SET search_path = 'public';
ALTER FUNCTION public.get_user_dashboard_stats() SET search_path = 'public';
ALTER FUNCTION public.get_user_creation_trends(INTEGER) SET search_path = 'public';
ALTER FUNCTION public.cleanup_old_user_creation_logs(INTEGER) SET search_path = 'public';

-- 02_platform_services.sql 中的函数 (5个)
ALTER FUNCTION public.sync_daily_metrics_date() SET search_path = 'public';
ALTER FUNCTION public.sync_notification_type() SET search_path = 'public';
ALTER FUNCTION public.update_notification_template_timestamp() SET search_path = 'public';
ALTER FUNCTION public.insert_v_marketplace_report() SET search_path = 'public';
ALTER FUNCTION public.generate_experiment_id() SET search_path = 'public';

-- 03_infrastructure.sql 中的函数 (23个)
ALTER FUNCTION public.sync_error_level() SET search_path = 'public';
-- 注意: 03 中也定义了 update_updated_at_column()，与 01 中是同一个函数
ALTER FUNCTION public.set_deleted_at_on_soft_delete() SET search_path = 'public';
ALTER FUNCTION public.prevent_modification() SET search_path = 'public';
ALTER FUNCTION public.log_pricing_plan_change() SET search_path = 'public';
ALTER FUNCTION public.deduct_credits_atomic(TEXT, INT, TEXT, TEXT, TEXT, TEXT, TEXT) SET search_path = 'public';
ALTER FUNCTION public.add_credits_atomic(TEXT, INT, TEXT, TEXT, TEXT, TEXT) SET search_path = 'public';
ALTER FUNCTION public.process_credit_purchase(TEXT, INT, INT, TEXT, TEXT, TEXT) SET search_path = 'public';
ALTER FUNCTION public.execute_marketplace_purchase(TEXT, UUID, TEXT) SET search_path = 'public';
ALTER FUNCTION public.increment_campaign_usage(UUID) SET search_path = 'public';
ALTER FUNCTION public.upsert_ai_usage_daily(DATE, TEXT, TEXT, TEXT, BOOLEAN, BIGINT, BIGINT, INT, INT, DECIMAL, TEXT) SET search_path = 'public';
ALTER FUNCTION public.is_admin() SET search_path = 'public';
ALTER FUNCTION public.generate_ticket_number() SET search_path = 'public';
ALTER FUNCTION public.check_marketplace_moderation_transition() SET search_path = 'public';
ALTER FUNCTION public.p_get_user_dashboard_stats(TEXT) SET search_path = 'public';
ALTER FUNCTION public.p_get_marketplace_trending(INTEGER, INTEGER) SET search_path = 'public';
ALTER FUNCTION public.p_get_user_credit_summary(TEXT, INTEGER) SET search_path = 'public';
ALTER FUNCTION public.p_calculate_user_activity_score(TEXT, INTEGER) SET search_path = 'public';
ALTER FUNCTION public.p_aggregate_experiment_results(UUID) SET search_path = 'public';
ALTER FUNCTION public.p_check_system_health() SET search_path = 'public';
ALTER FUNCTION public.p_update_project_with_version(UUID, INTEGER, TEXT, TEXT) SET search_path = 'public';
ALTER FUNCTION public.p_start_webhook_processing(TEXT, TEXT) SET search_path = 'public';
ALTER FUNCTION public.p_complete_webhook_processing(TEXT, TEXT, BOOLEAN, TEXT) SET search_path = 'public';
ALTER FUNCTION public.get_log_tables_stats() SET search_path = 'public';
ALTER FUNCTION public.cleanup_old_error_logs(INTEGER) SET search_path = 'public';
ALTER FUNCTION public.cleanup_old_activity_logs(INTEGER) SET search_path = 'public';


-- ============================================================================
-- 2. 迁移 ltree 扩展到 extensions schema
-- ============================================================================
-- 注意: ALTER EXTENSION SET SCHEMA 是无损操作，不影响现有数据和依赖
ALTER EXTENSION ltree SET SCHEMA extensions;


-- ============================================================================
-- 3. 收紧 admin_notification_templates RLS 策略
-- ============================================================================
-- 原策略: 未限定角色 (任何角色都能访问)
-- 新策略: 仅 service_role 可访问
DROP POLICY IF EXISTS admin_notification_templates_service_role ON admin_notification_templates;
CREATE POLICY admin_notification_templates_service_role ON admin_notification_templates
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);


COMMIT;

-- ============================================================================
-- 验证
-- ============================================================================
-- 验证 search_path:
-- SELECT proname, proconfig
-- FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid
-- WHERE n.nspname = 'public' AND p.proconfig IS NOT NULL
-- ORDER BY proname;
--
-- 验证 ltree schema:
-- SELECT extname, nspname FROM pg_extension e JOIN pg_namespace n ON e.extnamespace = n.oid WHERE extname = 'ltree';
--
-- 验证 RLS 策略:
-- SELECT polname, polroles::regrole[], polcmd FROM pg_policy WHERE polrelid = 'admin_notification_templates'::regclass;
