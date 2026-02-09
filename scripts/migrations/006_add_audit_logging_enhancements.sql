-- Migration 006: Add Audit Logging Enhancements
-- Task: Phase 4 - Task 9 - Activity Logging
-- Date: 2026-01-11
-- Description: Add source tracking and metadata fields for comprehensive audit logging

-- ========================================
-- Step 1: Add 'source' column to admin_operations
-- ========================================
ALTER TABLE admin_operations
ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'api';

COMMENT ON COLUMN admin_operations.source IS 'Action source: api (manual), webhook, stripe, auth';

-- ========================================
-- Step 2: Add 'metadata' column (alias for action_details for backward compatibility)
-- ========================================
-- Note: The table already has 'action_details' JSONB field
-- We'll use it as metadata - no need to add a new column

-- ========================================
-- Step 3: Add indexes for performance
-- ========================================
CREATE INDEX IF NOT EXISTS idx_admin_operations_target
ON admin_operations(target_type, target_id)
WHERE target_type IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_admin_operations_source
ON admin_operations(source);

CREATE INDEX IF NOT EXISTS idx_admin_operations_admin_id_created
ON admin_operations(admin_id, created_at DESC);

-- ========================================
-- Step 4: Update operation_type constraint to include new types
-- ========================================
ALTER TABLE admin_operations
DROP CONSTRAINT IF EXISTS check_operation_type;

ALTER TABLE admin_operations
ADD CONSTRAINT check_operation_type CHECK (
    operation_type IN (
        -- Existing operations
        'create', 'update', 'delete', 'restore',
        'approve', 'reject', 'ban', 'unban',
        'grant_credits', 'refund', 'adjust_tier',
        'force_delete', 'export_data', 'import_data',

        -- NEW: Delete operations
        'project_delete_soft', 'project_delete_permanent', 'project_restore',
        'template_delete', 'generation_delete', 'generation_batch_delete',
        'resource_delete', 'feature_flag_delete', 'campaign_delete', 'experiment_delete',

        -- NEW: Configuration changes
        'config_update', 'config_delete', 'rate_limit_preset_apply', 'cache_clear',

        -- NEW: Webhook events (Stripe)
        'webhook_subscription_create', 'webhook_subscription_update', 'webhook_subscription_cancel',
        'webhook_invoice_paid', 'webhook_refund_process', 'webhook_credits_purchase',

        -- NEW: Webhook events (Auth)
        'webhook_user_create', 'webhook_tier_update',

        -- Legacy compatibility
        'tier_change', 'credit_adjust', 'discount_create'
    )
);

-- ========================================
-- Step 5: Add target_user_id column if missing
-- ========================================
ALTER TABLE admin_operations
ADD COLUMN IF NOT EXISTS target_user_id TEXT;

COMMENT ON COLUMN admin_operations.target_user_id IS 'Affected user ID (for user-specific operations)';

CREATE INDEX IF NOT EXISTS idx_admin_operations_target_user
ON admin_operations(target_user_id)
WHERE target_user_id IS NOT NULL;

-- ========================================
-- Step 6: Add details and reason columns if missing
-- ========================================
ALTER TABLE admin_operations
ADD COLUMN IF NOT EXISTS details TEXT;

ALTER TABLE admin_operations
ADD COLUMN IF NOT EXISTS reason TEXT;

COMMENT ON COLUMN admin_operations.details IS 'Human-readable description of the operation';
COMMENT ON COLUMN admin_operations.reason IS 'Why the operation was performed (admin justification)';

-- ========================================
-- Rollback script (commented out, for reference)
-- ========================================
/*
-- To rollback this migration:

ALTER TABLE admin_operations
DROP COLUMN IF EXISTS source;

DROP INDEX IF EXISTS idx_admin_operations_target;
DROP INDEX IF EXISTS idx_admin_operations_source;
DROP INDEX IF EXISTS idx_admin_operations_admin_id_created;
DROP INDEX IF EXISTS idx_admin_operations_target_user;

ALTER TABLE admin_operations
DROP CONSTRAINT IF EXISTS check_operation_type;

-- Restore original constraint (adjust as needed)
ALTER TABLE admin_operations
ADD CONSTRAINT check_operation_type CHECK (
    operation_type IN (
        'create', 'update', 'delete', 'restore',
        'approve', 'reject', 'ban', 'unban',
        'grant_credits', 'refund', 'adjust_tier',
        'force_delete', 'export_data', 'import_data'
    )
);

ALTER TABLE admin_operations
DROP COLUMN IF EXISTS target_user_id,
DROP COLUMN IF EXISTS details,
DROP COLUMN IF EXISTS reason;
*/
