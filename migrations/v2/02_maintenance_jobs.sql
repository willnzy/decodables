-- ============================================================================
-- 维护任务配置 - 定期清理和优化
-- ============================================================================
-- 版本: v2.0
-- 日期: 2026-01-13
-- 说明: 配置自动化维护任务，防止日志表无限增长
-- ============================================================================

-- ============================================================================
-- 1. Supabase Cron Extension（如果可用）
-- ============================================================================

-- 启用 pg_cron 扩展（如果 Supabase 支持）
-- 注意：Supabase 可能需要在 Dashboard 中手动启用
-- CREATE EXTENSION IF NOT EXISTS pg_cron;


-- ============================================================================
-- 2. 定期清理函数（已存在于 01_core_business.sql）
-- ============================================================================

-- cleanup_old_user_creation_logs() 函数已在主 schema 中定义
-- 这里提供调用示例和配置


-- ============================================================================
-- 3. Supabase Cron 任务配置（推荐方式）
-- ============================================================================

-- 方式 A: 使用 Supabase Cron (如果可用)
-- 在 Supabase Dashboard > Database > Cron Jobs 中添加

/*
任务名称: cleanup-user-creation-logs
Schedule: 0 3 * * *  (每天凌晨 3 点)
SQL:
*/
-- SELECT cleanup_old_user_creation_logs(90);

/*
任务名称: cleanup-error-logs
Schedule: 0 4 * * *  (每天凌晨 4 点)
SQL:
*/
-- DELETE FROM error_logs WHERE created_at < NOW() - INTERVAL '30 days';


-- ============================================================================
-- 4. 手动清理命令（备用方案）
-- ============================================================================

-- 如果无法配置自动任务，可以手动定期执行以下命令：

-- 清理 90 天前的用户创建日志
-- SELECT cleanup_old_user_creation_logs(90);

-- 清理 30 天前的错误日志
-- DELETE FROM error_logs WHERE created_at < NOW() - INTERVAL '30 days';

-- 清理 180 天前的活动日志
-- DELETE FROM activity_logs WHERE created_at < NOW() - INTERVAL '180 days';


-- ============================================================================
-- 5. 监控清理效果
-- ============================================================================

-- 查看表大小
CREATE OR REPLACE VIEW v_table_sizes AS
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

COMMENT ON VIEW v_table_sizes IS '数据库表大小监控视图';


-- 查看日志表统计
CREATE OR REPLACE FUNCTION get_log_tables_stats()
RETURNS TABLE(
    table_name TEXT,
    total_rows BIGINT,
    old_rows BIGINT,
    retention_days INTEGER,
    next_cleanup_count BIGINT,
    table_size TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        'user_creation_logs'::TEXT,
        COUNT(*)::BIGINT AS total_rows,
        COUNT(*) FILTER (WHERE created_at < NOW() - INTERVAL '90 days')::BIGINT AS old_rows,
        90 AS retention_days,
        COUNT(*) FILTER (WHERE created_at < NOW() - INTERVAL '90 days')::BIGINT AS next_cleanup_count,
        pg_size_pretty(pg_total_relation_size('user_creation_logs'))::TEXT AS table_size
    FROM user_creation_logs
    
    UNION ALL
    
    SELECT 
        'error_logs'::TEXT,
        COUNT(*)::BIGINT,
        COUNT(*) FILTER (WHERE created_at < NOW() - INTERVAL '30 days')::BIGINT,
        30,
        COUNT(*) FILTER (WHERE created_at < NOW() - INTERVAL '30 days')::BIGINT,
        pg_size_pretty(pg_total_relation_size('error_logs'))::TEXT
    FROM error_logs
    
    UNION ALL
    
    SELECT 
        'activity_logs'::TEXT,
        COUNT(*)::BIGINT,
        COUNT(*) FILTER (WHERE created_at < NOW() - INTERVAL '180 days')::BIGINT,
        180,
        COUNT(*) FILTER (WHERE created_at < NOW() - INTERVAL '180 days')::BIGINT,
        pg_size_pretty(pg_total_relation_size('activity_logs'))::TEXT
    FROM activity_logs;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_log_tables_stats() IS '获取日志表统计信息（用于监控清理效果）';


-- ============================================================================
-- 6. 清理错误日志函数（新增）
-- ============================================================================

CREATE OR REPLACE FUNCTION cleanup_old_error_logs(p_retention_days INTEGER DEFAULT 30)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_deleted_count INTEGER;
BEGIN
    DELETE FROM error_logs
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '1 day' * p_retention_days;
    
    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;
    
    -- 记录清理操作
    INSERT INTO activity_logs (
        user_id,
        action,
        metadata,
        created_at
    ) VALUES (
        'system',
        'cleanup_error_logs',
        jsonb_build_object(
            'deleted_count', v_deleted_count,
            'retention_days', p_retention_days,
            'execution_time', CURRENT_TIMESTAMP
        ),
        CURRENT_TIMESTAMP
    );
    
    RETURN v_deleted_count;
END;
$$;

COMMENT ON FUNCTION cleanup_old_error_logs IS '清理旧的错误日志（保留 N 天）';


-- ============================================================================
-- 7. 清理活动日志函数（新增）
-- ============================================================================

CREATE OR REPLACE FUNCTION cleanup_old_activity_logs(p_retention_days INTEGER DEFAULT 180)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_deleted_count INTEGER;
BEGIN
    DELETE FROM activity_logs
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '1 day' * p_retention_days
      AND action NOT IN ('user_signup', 'subscription_purchase');  -- 保留关键事件
    
    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;
    
    RETURN v_deleted_count;
END;
$$;

COMMENT ON FUNCTION cleanup_old_activity_logs IS '清理旧的活动日志（保留 N 天，排除关键事件）';


-- ============================================================================
-- 8. 定期维护任务清单（文档）
-- ============================================================================

COMMENT ON SCHEMA public IS 
'定期维护任务清单：

1. 每日任务（凌晨 3-5 点执行）：
   - cleanup_old_user_creation_logs(90)    -- 清理 90 天前的用户创建日志
   - cleanup_old_error_logs(30)            -- 清理 30 天前的错误日志

2. 每周任务（周日凌晨）：
   - cleanup_old_activity_logs(180)        -- 清理 180 天前的活动日志
   - VACUUM ANALYZE                        -- 优化数据库性能

3. 每月任务（每月 1 号）：
   - 检查表大小：SELECT * FROM v_table_sizes;
   - 检查日志统计：SELECT * FROM get_log_tables_stats();
   - 评估保留策略是否需要调整

4. 告警阈值：
   - user_creation_logs > 100MB: 考虑减少保留天数
   - error_logs > 50MB: 检查错误频率，解决根本问题
   - activity_logs > 500MB: 考虑分区或归档

配置方式：
- Supabase Cron: Dashboard > Database > Cron Jobs
- 应用层: scheduler.py 使用 APScheduler
- 手动: 定期执行 SQL 命令
';


-- ============================================================================
-- 验证
-- ============================================================================

DO $$
BEGIN
    -- 验证函数
    IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'cleanup_old_user_creation_logs') THEN
        RAISE NOTICE '✅ cleanup_old_user_creation_logs 函数已就绪';
    ELSE
        RAISE EXCEPTION '❌ cleanup_old_user_creation_logs 函数未找到';
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'cleanup_old_error_logs') THEN
        RAISE NOTICE '✅ cleanup_old_error_logs 函数已创建';
    ELSE
        RAISE EXCEPTION '❌ cleanup_old_error_logs 函数创建失败';
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'cleanup_old_activity_logs') THEN
        RAISE NOTICE '✅ cleanup_old_activity_logs 函数已创建';
    ELSE
        RAISE EXCEPTION '❌ cleanup_old_activity_logs 函数创建失败';
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'get_log_tables_stats') THEN
        RAISE NOTICE '✅ get_log_tables_stats 函数已创建';
    ELSE
        RAISE EXCEPTION '❌ get_log_tables_stats 函数创建失败';
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_views WHERE viewname = 'v_table_sizes') THEN
        RAISE NOTICE '✅ v_table_sizes 视图已创建';
    ELSE
        RAISE EXCEPTION '❌ v_table_sizes 视图创建失败';
    END IF;
    
    RAISE NOTICE '🎉 所有维护任务配置已完成！';
    RAISE NOTICE '📋 下一步: 在 Supabase Dashboard 配置 Cron 任务或在应用层配置定时任务';
END
$$;
