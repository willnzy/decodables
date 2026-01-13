-- ============================================================================
-- HOTFIX: 更新 admin_operations 表的 CHECK 约束
-- ============================================================================
-- 
-- 问题描述：
-- - admin_operations.operation_type CHECK 约束不包含 webhook_* 操作类型
-- - 导致 webhook 操作日志记录失败
--
-- 修复内容：
-- 1. 移除旧的 check_operation_type 约束
-- 2. 添加新的约束，包含 webhook 操作类型
--
-- 执行方法：
-- psql $DATABASE_URL -f HOTFIX_admin_operations_constraints.sql
--
-- ============================================================================

-- ============================================================================
-- Step 1: 移除旧的 operation_type CHECK 约束
-- ============================================================================

DO $$ 
BEGIN
    -- 尝试移除旧约束（如果存在）
    IF EXISTS (
        SELECT 1 
        FROM information_schema.table_constraints 
        WHERE table_name = 'admin_operations' 
        AND constraint_name = 'check_operation_type'
    ) THEN
        ALTER TABLE admin_operations DROP CONSTRAINT check_operation_type;
        RAISE NOTICE '✅ Dropped old check_operation_type constraint';
    ELSE
        RAISE NOTICE 'ℹ️ check_operation_type constraint does not exist (OK)';
    END IF;
END $$;

-- ============================================================================
-- Step 2: 添加新的 operation_type CHECK 约束（包含 webhook 操作）
-- ============================================================================

DO $$ 
BEGIN
    -- 添加新约束
    ALTER TABLE admin_operations ADD CONSTRAINT check_operation_type CHECK (
        operation_type IN (
            -- 原有操作类型
            'create', 'update', 'delete', 'restore',
            'approve', 'reject', 'ban', 'unban',
            'grant_credits', 'refund', 'adjust_tier',
            'force_delete', 'export_data', 'import_data',
            -- 新增的扩展操作类型（Phase 4 - Task 9）
            'project_delete_soft', 'project_delete_permanent', 'project_restore',
            'template_delete', 'generation_delete', 'generation_batch_delete',
            'resource_delete', 'feature_flag_delete', 'campaign_delete', 'experiment_delete',
            'config_update', 'config_delete', 'rate_limit_preset_apply', 'cache_clear',
            'broadcast',
            -- Webhook 操作类型
            'webhook_subscription_create', 'webhook_subscription_update', 'webhook_subscription_cancel',
            'webhook_invoice_paid', 'webhook_refund_process', 'webhook_credits_purchase',
            'webhook_user_create', 'webhook_tier_update'
        )
    );
    RAISE NOTICE '✅ Added new check_operation_type constraint with webhook types';
EXCEPTION
    WHEN duplicate_object THEN
        RAISE NOTICE 'ℹ️ check_operation_type constraint already exists with correct values';
END $$;

-- ============================================================================
-- Step 3: 验证约束
-- ============================================================================

DO $$
DECLARE
    constraint_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 
        FROM information_schema.table_constraints 
        WHERE table_name = 'admin_operations' 
        AND constraint_name = 'check_operation_type'
    ) INTO constraint_exists;
    
    IF constraint_exists THEN
        RAISE NOTICE '✅ HOTFIX VERIFICATION PASSED';
        RAISE NOTICE '   - check_operation_type constraint: EXISTS';
    ELSE
        RAISE WARNING '⚠️  HOTFIX VERIFICATION FAILED';
        RAISE WARNING '   - check_operation_type constraint: MISSING';
    END IF;
END $$;

-- ============================================================================
-- 完成
-- ============================================================================
-- 说明：
-- 1. 此 HOTFIX 是幂等的，可以安全地重复执行
-- 2. 执行后，webhook 操作日志将正常记录
-- ============================================================================
