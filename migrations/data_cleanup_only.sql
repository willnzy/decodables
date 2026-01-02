-- ==============================================================================
-- Make Decodables - Data Cleanup Script (仅清空测试数据)
-- 
-- ⚠️ WARNING: This script will DELETE ALL USER DATA!
-- Use this when you only need to reset data without schema changes.
-- 
-- Run this script in Supabase SQL Editor with service_role permissions.
-- ==============================================================================

-- 开始事务
BEGIN;

-- ============================================
-- Step 1: 清空所有用户数据（按外键依赖顺序）
-- ============================================

-- 1.1 日志和分析数据（无外键依赖）
TRUNCATE TABLE error_logs CASCADE;
TRUNCATE TABLE analytics_events CASCADE;
TRUNCATE TABLE user_events CASCADE;
TRUNCATE TABLE activity_logs CASCADE;
TRUNCATE TABLE admin_operation_logs CASCADE;

-- 1.2 聚合和统计数据
TRUNCATE TABLE aggregated_stats CASCADE;
TRUNCATE TABLE leaderboard_snapshots CASCADE;

-- 1.3 内容举报
TRUNCATE TABLE content_reports CASCADE;

-- 1.4 交易记录
TRUNCATE TABLE listing_usages CASCADE;
TRUNCATE TABLE user_purchases CASCADE;

-- 1.5 用户资源（有外键到 marketplace_listings）
TRUNCATE TABLE assets CASCADE;
TRUNCATE TABLE projects CASCADE;

-- 1.6 市场数据
TRUNCATE TABLE marketplace_listings CASCADE;

-- 1.7 用户相关数据
TRUNCATE TABLE credit_transactions CASCADE;
TRUNCATE TABLE user_discounts CASCADE;
TRUNCATE TABLE notifications CASCADE;
TRUNCATE TABLE support_tickets CASCADE;
TRUNCATE TABLE asset_prompt_templates CASCADE;
TRUNCATE TABLE page_prompt_templates CASCADE;

-- 1.8 最后清空用户表
TRUNCATE TABLE profiles CASCADE;

-- 提交事务
COMMIT;

-- ============================================
-- Step 2: 验证数据已清空
-- ============================================

SELECT 
    table_name,
    row_count,
    CASE WHEN row_count = 0 THEN '✅' ELSE '❌' END as status
FROM (
    SELECT 'profiles' as table_name, COUNT(*) as row_count FROM profiles
    UNION ALL SELECT 'projects', COUNT(*) FROM projects
    UNION ALL SELECT 'assets', COUNT(*) FROM assets
    UNION ALL SELECT 'marketplace_listings', COUNT(*) FROM marketplace_listings
    UNION ALL SELECT 'user_purchases', COUNT(*) FROM user_purchases
    UNION ALL SELECT 'credit_transactions', COUNT(*) FROM credit_transactions
    UNION ALL SELECT 'notifications', COUNT(*) FROM notifications
    UNION ALL SELECT 'analytics_events', COUNT(*) FROM analytics_events
    UNION ALL SELECT 'error_logs', COUNT(*) FROM error_logs
    UNION ALL SELECT 'user_events', COUNT(*) FROM user_events
    UNION ALL SELECT 'activity_logs', COUNT(*) FROM activity_logs
    UNION ALL SELECT 'admin_operation_logs', COUNT(*) FROM admin_operation_logs
    UNION ALL SELECT 'support_tickets', COUNT(*) FROM support_tickets
    UNION ALL SELECT 'content_reports', COUNT(*) FROM content_reports
    UNION ALL SELECT 'listing_usages', COUNT(*) FROM listing_usages
) as counts
ORDER BY table_name;

-- ============================================
-- Step 3: 保留 system_configs 和 system_resources
-- ============================================
-- 注意：这个脚本不会清空 system_configs 和 system_resources
-- 因为这些通常是系统配置，不是用户数据

SELECT 
    '📋 System data retained:' as info
UNION ALL 
SELECT 
    'system_configs: ' || COUNT(*)::text || ' rows'
FROM system_configs
UNION ALL
SELECT 
    'system_resources: ' || COUNT(*)::text || ' rows'
FROM system_resources;

-- ============================================
-- 完成
-- ============================================

SELECT '✅ Data cleanup completed!' as message;
