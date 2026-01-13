-- ============================================================================
-- HOTFIX: 为缺失的表启用 Row Level Security (RLS)
-- ============================================================================
-- 问题: system_error_logs 和 user_creation_logs 两个表未启用 RLS
-- 状态: 在 Supabase Table Editor 中显示为 "UNRESTRICTED"
-- 影响: 使用 anon key 可以直接访问这些表（安全风险）
-- 
-- 解决方案: 启用 RLS（无策略 = 默认拒绝所有 anon key 访问）
-- 
-- 执行时机: 在 Railway 数据库上执行（如果表已存在但未启用 RLS）
-- ============================================================================

BEGIN;

-- 启用 RLS（这两个表从 01_core_business.sql 创建，但在 RLS 启用部分被遗漏）
ALTER TABLE system_error_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_creation_logs ENABLE ROW LEVEL SECURITY;

-- 验证 RLS 已启用
DO $$
DECLARE
    v_system_error_logs_rls BOOLEAN;
    v_user_creation_logs_rls BOOLEAN;
BEGIN
    -- 检查 system_error_logs 的 RLS 状态
    SELECT relrowsecurity INTO v_system_error_logs_rls
    FROM pg_class
    WHERE relname = 'system_error_logs';
    
    -- 检查 user_creation_logs 的 RLS 状态
    SELECT relrowsecurity INTO v_user_creation_logs_rls
    FROM pg_class
    WHERE relname = 'user_creation_logs';
    
    IF v_system_error_logs_rls AND v_user_creation_logs_rls THEN
        RAISE NOTICE '✅ RLS 已成功启用:';
        RAISE NOTICE '   - system_error_logs: %', v_system_error_logs_rls;
        RAISE NOTICE '   - user_creation_logs: %', v_user_creation_logs_rls;
    ELSE
        RAISE WARNING '⚠️  RLS 启用状态异常:';
        RAISE WARNING '   - system_error_logs: %', COALESCE(v_system_error_logs_rls::TEXT, 'NULL');
        RAISE WARNING '   - user_creation_logs: %', COALESCE(v_user_creation_logs_rls::TEXT, 'NULL');
    END IF;
END $$;

COMMIT;

-- ============================================================================
-- 说明
-- ============================================================================
-- 
-- RLS 安全策略：
-- 1. 启用 RLS 但不创建任何策略 = 默认拒绝所有 anon key 访问
-- 2. 后端使用 service_role key，会自动绕过 RLS
-- 3. 这两个表是监控日志表，只应该由后端/RPC 写入，Grafana/Admin 读取
-- 
-- 为什么不需要添加策略？
-- - 这两个表不需要前端直接访问
-- - Python 后端使用 service_role key（自动绕过 RLS）
-- - Grafana 使用数据库直连（绕过 Supabase API）
-- - 启用 RLS 只是为了安全防御（防止 anon key 泄露后被滥用）
-- 
-- 验证 RLS 状态（可选）：
-- SELECT 
--     tablename,
--     rowsecurity as rls_enabled
-- FROM pg_tables 
-- WHERE schemaname = 'public' 
--   AND tablename IN ('system_error_logs', 'user_creation_logs');
-- 
-- ============================================================================
