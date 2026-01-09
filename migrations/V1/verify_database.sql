-- =============================================================================
-- 数据库验证脚本 - 在 Supabase SQL Editor 中运行
-- 检查所有必需的表、函数、RLS 策略是否存在
-- =============================================================================

-- 1️⃣ 检查核心表是否存在
SELECT '=== 核心表检查 ===' AS section;

SELECT 
    table_name,
    CASE WHEN table_name IS NOT NULL THEN '✅ 存在' ELSE '❌ 缺失' END AS status
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN (
    'profiles',
    'projects', 
    'assets',
    'credit_transactions',
    'subscriptions',
    'marketplace_listings',
    'user_generations',
    'generation_tasks',
    'webhook_events',
    'ai_usage_daily',
    'ai_model_configs',
    'holiday_themes',
    'campaigns'
)
ORDER BY table_name;

-- 2️⃣ 检查缺失的表
SELECT '=== 缺失的表 ===' AS section;

SELECT unnest(ARRAY[
    'profiles',
    'projects', 
    'assets',
    'credit_transactions',
    'subscriptions',
    'marketplace_listings',
    'user_generations',
    'generation_tasks',
    'webhook_events',
    'ai_usage_daily',
    'ai_model_configs',
    'holiday_themes',
    'campaigns'
]) AS required_table
EXCEPT
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';

-- 3️⃣ 检查 RPC 函数是否存在
SELECT '=== RPC 函数检查 ===' AS section;

SELECT 
    routine_name AS function_name,
    '✅ 存在' AS status
FROM information_schema.routines 
WHERE routine_schema = 'public' 
AND routine_type = 'FUNCTION'
AND routine_name IN (
    'deduct_credits_atomic',
    'add_credits_atomic',
    'execute_marketplace_purchase',
    'process_stripe_webhook',
    'create_generation_task',
    'update_task_progress',
    'complete_generation_task',
    'fail_generation_task',
    'get_user_generations',
    'get_user_generation_stats'
)
ORDER BY routine_name;

-- 4️⃣ 检查缺失的函数
SELECT '=== 缺失的函数 ===' AS section;

SELECT unnest(ARRAY[
    'deduct_credits_atomic',
    'add_credits_atomic',
    'execute_marketplace_purchase',
    'process_stripe_webhook',
    'create_generation_task',
    'update_task_progress',
    'complete_generation_task',
    'fail_generation_task',
    'get_user_generations',
    'get_user_generation_stats'
]) AS required_function
EXCEPT
SELECT routine_name FROM information_schema.routines 
WHERE routine_schema = 'public' AND routine_type = 'FUNCTION';

-- 5️⃣ 检查 RLS 是否启用
SELECT '=== RLS 状态检查 ===' AS section;

SELECT 
    schemaname,
    tablename,
    CASE WHEN rowsecurity THEN '✅ RLS 启用' ELSE '❌ RLS 未启用' END AS rls_status
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN (
    'generation_tasks',
    'webhook_events', 
    'user_generations',
    'holiday_themes',
    'ai_model_configs',
    'ai_usage_daily'
)
ORDER BY tablename;

-- 6️⃣ 检查 deduct_credits_atomic 函数的参数类型
SELECT '=== deduct_credits_atomic 参数类型检查 ===' AS section;

SELECT 
    p.proname AS function_name,
    pg_get_function_arguments(p.oid) AS arguments,
    CASE 
        WHEN pg_get_function_arguments(p.oid) LIKE '%p_user_id text%' THEN '✅ 正确 (TEXT)'
        WHEN pg_get_function_arguments(p.oid) LIKE '%p_user_id uuid%' THEN '❌ 错误 (UUID) - 需要修复!'
        ELSE '⚠️ 未知'
    END AS user_id_type_status
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'public' 
AND p.proname = 'deduct_credits_atomic';

-- 7️⃣ 总结
SELECT '=== 验证总结 ===' AS section;

SELECT 
    (SELECT COUNT(*) FROM information_schema.tables 
     WHERE table_schema = 'public' 
     AND table_name IN ('user_generations', 'generation_tasks', 'webhook_events', 'ai_usage_daily', 'ai_model_configs')) 
    AS "新增表数量 (预期5个)",
    
    (SELECT COUNT(*) FROM information_schema.routines 
     WHERE routine_schema = 'public' 
     AND routine_name IN ('deduct_credits_atomic', 'add_credits_atomic', 'execute_marketplace_purchase', 'process_stripe_webhook', 'create_generation_task'))
    AS "新增函数数量 (预期5个)";
