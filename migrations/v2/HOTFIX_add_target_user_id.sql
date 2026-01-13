-- ============================================================================
-- HOTFIX: Add target_user_id column to admin_operations table
-- ============================================================================
-- 
-- 问题描述：
-- - 代码中大量使用 target_user_id 参数记录操作影响的用户
-- - 数据库表 admin_operations 缺少此列
-- - 导致审计日志记录失败：PGRST204 错误
--
-- 修复内容：
-- 1. 添加 target_user_id 列到 admin_operations 表
-- 2. 为已存在的记录创建索引（如需要）
--
-- 执行方法：
-- psql $DATABASE_URL -f HOTFIX_add_target_user_id.sql
--
-- 回滚方法（如需要）：
-- ALTER TABLE admin_operations DROP COLUMN IF EXISTS target_user_id;
--
-- ============================================================================

-- ============================================================================
-- Step 1: 添加 target_user_id 列
-- ============================================================================

DO $$ 
BEGIN
    -- 检查列是否已存在
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'admin_operations' 
        AND column_name = 'target_user_id'
    ) THEN
        -- 添加列
        ALTER TABLE admin_operations 
        ADD COLUMN target_user_id TEXT;
        
        RAISE NOTICE '✅ Added target_user_id column to admin_operations';
    ELSE
        RAISE NOTICE '✅ target_user_id column already exists in admin_operations';
    END IF;
END $$;

-- ============================================================================
-- Step 2: 添加索引（可选，用于优化查询性能）
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_admin_operations_target_user_id 
ON admin_operations(target_user_id) 
WHERE target_user_id IS NOT NULL;

-- ============================================================================
-- Step 3: 验证
-- ============================================================================

DO $$
DECLARE
    column_exists BOOLEAN;
    index_exists BOOLEAN;
BEGIN
    -- 验证列是否存在
    SELECT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'admin_operations' 
        AND column_name = 'target_user_id'
    ) INTO column_exists;
    
    -- 验证索引是否存在
    SELECT EXISTS (
        SELECT 1
        FROM pg_indexes
        WHERE tablename = 'admin_operations'
        AND indexname = 'idx_admin_operations_target_user_id'
    ) INTO index_exists;
    
    IF column_exists AND index_exists THEN
        RAISE NOTICE '✅ HOTFIX VERIFICATION PASSED';
        RAISE NOTICE '   - target_user_id column: EXISTS';
        RAISE NOTICE '   - Index on target_user_id: EXISTS';
    ELSE
        RAISE WARNING '⚠️  HOTFIX VERIFICATION FAILED';
        IF NOT column_exists THEN
            RAISE WARNING '   - target_user_id column: MISSING';
        END IF;
        IF NOT index_exists THEN
            RAISE WARNING '   - Index on target_user_id: MISSING';
        END IF;
    END IF;
END $$;

-- ============================================================================
-- 完成
-- ============================================================================
-- 说明：
-- 1. 此 HOTFIX 是幂等的，可以安全地重复执行
-- 2. target_user_id 列允许为 NULL，不影响现有数据
-- 3. 索引仅在 target_user_id 非空时生效，优化查询性能
-- 4. 执行后，webhook 和其他操作的审计日志将正常记录
-- ============================================================================
