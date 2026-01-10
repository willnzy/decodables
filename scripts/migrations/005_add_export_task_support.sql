-- =====================================================
-- Migration 005: Add Export Task Support
-- =====================================================
-- Description: Add PDF/ZIP export task types and idempotency index
-- Date: 2026-01-11
-- Related: PDF/ZIP Async Export Implementation (Phase 3)

BEGIN;

-- =====================================================
-- 1. Update task_type constraint to include export tasks
-- =====================================================

-- Drop existing constraint
ALTER TABLE generation_tasks
    DROP CONSTRAINT IF EXISTS check_task_type;

-- Add new constraint with export types
ALTER TABLE generation_tasks
    ADD CONSTRAINT check_task_type CHECK (
        task_type IN (
            -- Existing types
            'text_to_image', 'image_to_image', 'text_generation',
            'image_upscale', 'background_removal', 'style_transfer',
            'object_detection', 'smart_scan',
            -- New export types
            'export_pdf', 'export_zip'
        )
    );

COMMENT ON CONSTRAINT check_task_type ON generation_tasks IS
    'Valid task types: generation (text_to_image, etc), export (export_pdf, export_zip)';

-- =====================================================
-- 2. Create idempotency index
-- =====================================================

-- Create index for idempotency key lookups
-- Uses JSONB path operator to index on parameters->'idempotency_key'
CREATE INDEX IF NOT EXISTS idx_generation_tasks_idempotency
    ON generation_tasks ((parameters->>'idempotency_key'))
    WHERE parameters->>'idempotency_key' IS NOT NULL;

COMMENT ON INDEX idx_generation_tasks_idempotency IS
    'Index for fast idempotency key lookups in export tasks';

-- =====================================================
-- 3. Create index for export task queries
-- =====================================================

-- Index for finding user's export tasks
CREATE INDEX IF NOT EXISTS idx_generation_tasks_export_tasks
    ON generation_tasks (user_id, created_at DESC)
    WHERE task_type IN ('export_pdf', 'export_zip')
      AND is_deleted = false;

COMMENT ON INDEX idx_generation_tasks_export_tasks IS
    'Index for querying user export history';

-- =====================================================
-- 4. Add worker_id column if not exists
-- =====================================================

-- Track which worker processed the task (for debugging)
ALTER TABLE generation_tasks
    ADD COLUMN IF NOT EXISTS worker_id TEXT;

COMMENT ON COLUMN generation_tasks.worker_id IS
    'ID of the worker process that executed this task';

-- =====================================================
-- 5. Create helper function for export cleanup
-- =====================================================

-- Function to clean up old export tasks (> 30 days)
-- Run this periodically to prevent table bloat
CREATE OR REPLACE FUNCTION p_cleanup_old_export_tasks()
RETURNS TABLE (deleted_count INTEGER) AS $$
DECLARE
    v_count INTEGER;
BEGIN
    -- Soft delete export tasks older than 30 days
    UPDATE generation_tasks
    SET is_deleted = true,
        deleted_at = NOW()
    WHERE task_type IN ('export_pdf', 'export_zip')
      AND created_at < NOW() - INTERVAL '30 days'
      AND is_deleted = false;

    GET DIAGNOSTICS v_count = ROW_COUNT;

    RETURN QUERY SELECT v_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION p_cleanup_old_export_tasks() IS
    'Soft deletes export tasks older than 30 days to prevent table bloat';

COMMIT;
