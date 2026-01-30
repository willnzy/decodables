-- ============================================================================
-- 修复脚本: Security Definer Views
-- ============================================================================
-- 问题: Supabase 审计发现 5 个视图使用 SECURITY DEFINER (PostgreSQL 默认行为)
--       导致 RLS 策略被绕过
-- 方案:
--   - v_projects, v_marketplace_reports: 添加 security_invoker = true (RLS 生效)
--   - v_user_creation_events, v_table_sizes, v_ai_usage_last_30_days:
--     迁移到 internal schema (PostgREST 不暴露)
-- 日期: 2026-01-30
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. 创建 internal schema (运维视图专用)
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS internal;


-- ============================================================================
-- 2. v_projects - 添加 security_invoker = true
-- ============================================================================
-- 必须 DROP + CREATE，因为 ALTER VIEW 不支持修改 security_invoker
DROP VIEW IF EXISTS public.v_projects CASCADE;
CREATE OR REPLACE VIEW public.v_projects
WITH (security_invoker = true) AS
SELECT
    *,
    user_id AS owner_id
FROM public.projects;


-- ============================================================================
-- 3. v_marketplace_reports - 添加 security_invoker = true
-- ============================================================================
DROP VIEW IF EXISTS public.v_marketplace_reports CASCADE;
CREATE OR REPLACE VIEW public.v_marketplace_reports
WITH (security_invoker = true) AS
SELECT * FROM public.content_reports;

-- 重建 INSTEAD OF INSERT 触发器 (DROP VIEW 会级联删除)
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


-- ============================================================================
-- 4. v_user_creation_events - 迁移到 internal schema
-- ============================================================================
DROP VIEW IF EXISTS public.v_user_creation_events CASCADE;
CREATE OR REPLACE VIEW internal.v_user_creation_events AS
SELECT
    p.id AS user_id,
    p.email,
    p.username,
    p.created_by AS created_by_source,
    p.created_at AS user_created_at,
    ucl.source AS log_source,
    ucl.action AS log_action,
    ucl.metadata AS log_metadata,
    ucl.created_at AS log_created_at,
    EXTRACT(EPOCH FROM (ucl.created_at - p.created_at)) AS delay_seconds
FROM public.profiles p
LEFT JOIN public.user_creation_logs ucl ON p.id = ucl.user_id
WHERE ucl.action IN ('created', 'duplicate_attempt')
ORDER BY p.created_at DESC;

COMMENT ON VIEW internal.v_user_creation_events IS '用户创建事件视图，包含延迟分析';


-- ============================================================================
-- 5. v_ai_usage_last_30_days - 迁移到 internal schema
-- ============================================================================
DROP VIEW IF EXISTS public.v_ai_usage_last_30_days CASCADE;
CREATE OR REPLACE VIEW internal.v_ai_usage_last_30_days AS
SELECT
    provider,
    model,
    call_type,
    SUM(total_calls) as total_calls,
    SUM(successful_calls) as successful_calls,
    SUM(failed_calls) as failed_calls,
    ROUND(SUM(successful_calls)::numeric / NULLIF(SUM(total_calls), 0) * 100, 2) as success_rate,
    SUM(total_input_tokens) as total_input_tokens,
    SUM(total_output_tokens) as total_output_tokens,
    SUM(total_images) as total_images,
    ROUND(AVG(avg_latency_ms)) as avg_latency_ms,
    SUM(estimated_cost_usd) as total_cost_usd
FROM public.ai_usage_daily
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY provider, model, call_type
ORDER BY total_cost_usd DESC;


-- ============================================================================
-- 6. v_table_sizes - 迁移到 internal schema
-- ============================================================================
DROP VIEW IF EXISTS public.v_table_sizes CASCADE;
CREATE OR REPLACE VIEW internal.v_table_sizes AS
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_indexes_size(schemaname||'.'||tablename)) AS indexes_size,
    (SELECT COUNT(*) FROM information_schema.tables WHERE table_name = tablename) AS row_count_estimate
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

COMMENT ON VIEW internal.v_table_sizes IS '数据库表大小监控视图';


COMMIT;

-- ============================================================================
-- 验证
-- ============================================================================
-- 验证 security_invoker:
-- SELECT schemaname, viewname, definition FROM pg_views WHERE viewname IN ('v_projects', 'v_marketplace_reports');
-- SELECT c.relname, array_agg(o.option_name || '=' || o.option_value)
-- FROM pg_class c JOIN pg_options_to_table(c.reloptions) o ON true
-- WHERE c.relname IN ('v_projects', 'v_marketplace_reports')
-- GROUP BY c.relname;
--
-- 验证 internal schema 视图:
-- SELECT schemaname, viewname FROM pg_views WHERE schemaname = 'internal';
