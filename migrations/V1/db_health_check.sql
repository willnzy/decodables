-- ==============================================================================
-- Make Decodables - Database Health Check Script
-- 
-- Run this script to verify database integrity before and after production launch.
-- Safe to run multiple times - no data modifications.
-- ==============================================================================

-- ============================================
-- 1. 表结构检查
-- ============================================

SELECT '📊 TABLE STRUCTURE CHECK' as section;

-- 1.1 列出所有表及行数
SELECT 
    schemaname,
    relname as table_name,
    n_live_tup as estimated_rows
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY relname;

-- 1.2 检查必须存在的表
SELECT 
    table_name,
    CASE WHEN EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = t.table_name
    ) THEN '✅ EXISTS' ELSE '❌ MISSING' END as status
FROM (VALUES 
    ('profiles'),
    ('projects'),
    ('assets'),
    ('marketplace_listings'),
    ('user_purchases'),
    ('credit_transactions'),
    ('notifications'),
    ('system_configs'),
    ('system_resources'),
    ('analytics_events'),
    ('error_logs'),
    ('user_events'),
    ('activity_logs'),
    ('admin_operation_logs'),
    ('support_tickets'),
    ('content_reports'),
    ('listing_usages'),
    ('leaderboard_snapshots'),
    ('user_discounts'),
    ('aggregated_stats'),
    ('asset_prompt_templates'),
    ('page_prompt_templates')
) as t(table_name)
ORDER BY table_name;

-- ============================================
-- 2. 关键字段检查
-- ============================================

SELECT '📋 KEY COLUMNS CHECK' as section;

-- 2.1 检查时区字段是否存在
SELECT 
    t.table_name,
    CASE WHEN EXISTS (
        SELECT 1 FROM information_schema.columns c
        WHERE c.table_schema = 'public' 
        AND c.table_name = t.table_name 
        AND c.column_name = 'timezone'
    ) THEN '✅' ELSE '❌' END as has_timezone,
    CASE WHEN EXISTS (
        SELECT 1 FROM information_schema.columns c
        WHERE c.table_schema = 'public' 
        AND c.table_name = t.table_name 
        AND c.column_name = 'created_at_local'
    ) THEN '✅' ELSE '❌' END as has_created_at_local
FROM (VALUES 
    ('profiles'),
    ('projects'),
    ('assets'),
    ('marketplace_listings'),
    ('user_purchases'),
    ('credit_transactions'),
    ('notifications'),
    ('analytics_events'),
    ('error_logs'),
    ('user_events'),
    ('activity_logs'),
    ('admin_operation_logs'),
    ('content_reports')
) as t(table_name)
ORDER BY table_name;

-- ============================================
-- 3. 索引检查
-- ============================================

SELECT '🔍 INDEX CHECK' as section;

-- 3.1 列出所有索引
SELECT 
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

-- 3.2 检查关键索引是否存在
SELECT 
    'Key indexes count: ' || COUNT(*)::text as info
FROM pg_indexes
WHERE schemaname = 'public'
AND indexname IN (
    'idx_profiles_tier',
    'idx_credit_tx_user_id',
    'idx_projects_user_id',
    'idx_assets_user_proj',
    'idx_marketplace_listings_resource_id',
    'idx_analytics_events_created_at',
    'idx_error_logs_created_at',
    'idx_transactions_idempotency'
);

-- ============================================
-- 4. RLS 策略检查
-- ============================================

SELECT '🔐 RLS POLICIES CHECK' as section;

-- 4.1 检查 RLS 是否启用
SELECT 
    relname as table_name,
    CASE WHEN relrowsecurity THEN '✅ ENABLED' ELSE '❌ DISABLED' END as rls_status
FROM pg_class
WHERE relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
AND relkind = 'r'
AND relname IN (
    'profiles', 'projects', 'assets', 'marketplace_listings',
    'user_purchases', 'credit_transactions', 'notifications',
    'system_configs', 'system_resources', 'analytics_events',
    'error_logs', 'user_events', 'activity_logs', 'admin_operation_logs',
    'support_tickets', 'content_reports', 'listing_usages',
    'leaderboard_snapshots', 'user_discounts', 'aggregated_stats',
    'asset_prompt_templates', 'page_prompt_templates'
)
ORDER BY relname;

-- 4.2 列出所有策略
SELECT 
    tablename,
    policyname,
    permissive,
    roles,
    cmd
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;

-- ============================================
-- 5. 视图检查
-- ============================================

SELECT '📈 VIEWS CHECK' as section;

SELECT 
    viewname,
    CASE WHEN definition IS NOT NULL THEN '✅' ELSE '❌' END as status
FROM pg_views
WHERE schemaname = 'public'
ORDER BY viewname;

-- ============================================
-- 6. 函数检查
-- ============================================

SELECT '⚙️ FUNCTIONS CHECK' as section;

SELECT 
    proname as function_name,
    pg_get_function_result(oid) as return_type
FROM pg_proc
WHERE pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
AND proname IN (
    'is_admin',
    'sync_listing_status',
    'update_seller_stats_on_purchase',
    'set_deleted_timestamp',
    'prevent_credit_modification',
    'update_updated_at_timestamp',
    'get_rate_limit_config',
    'get_latest_stats',
    'get_stats_range'
)
ORDER BY proname;

-- ============================================
-- 7. 触发器检查
-- ============================================

SELECT '🎯 TRIGGERS CHECK' as section;

SELECT 
    trigger_name,
    event_object_table as table_name,
    event_manipulation as event,
    action_timing as timing
FROM information_schema.triggers
WHERE trigger_schema = 'public'
ORDER BY event_object_table, trigger_name;

-- ============================================
-- 8. 外键约束检查
-- ============================================

SELECT '🔗 FOREIGN KEYS CHECK' as section;

SELECT
    tc.constraint_name,
    tc.table_name as from_table,
    kcu.column_name as from_column,
    ccu.table_name AS to_table,
    ccu.column_name AS to_column
FROM 
    information_schema.table_constraints AS tc 
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name
      AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage AS ccu
      ON ccu.constraint_name = tc.constraint_name
      AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
AND tc.table_schema = 'public'
ORDER BY tc.table_name, tc.constraint_name;

-- ============================================
-- 9. System Configs 检查
-- ============================================

SELECT '⚡ SYSTEM CONFIGS CHECK' as section;

SELECT 
    config_key,
    category,
    is_active,
    description
FROM system_configs
ORDER BY category, config_key;

-- ============================================
-- 10. 数据统计概览
-- ============================================

SELECT '📊 DATA SUMMARY' as section;

SELECT 
    'Total profiles' as metric,
    COUNT(*) as value
FROM profiles
UNION ALL
SELECT 'Total projects', COUNT(*) FROM projects WHERE is_deleted = false
UNION ALL
SELECT 'Total assets', COUNT(*) FROM assets WHERE is_deleted = false
UNION ALL
SELECT 'Active listings', COUNT(*) FROM marketplace_listings WHERE is_public = true AND is_deleted = false
UNION ALL
SELECT 'Total purchases', COUNT(*) FROM user_purchases
UNION ALL
SELECT 'Total transactions', COUNT(*) FROM credit_transactions
UNION ALL
SELECT 'System configs', COUNT(*) FROM system_configs
UNION ALL
SELECT 'System resources', COUNT(*) FROM system_resources;

-- ============================================
-- 完成
-- ============================================

SELECT '✅ Database health check completed!' as message;
