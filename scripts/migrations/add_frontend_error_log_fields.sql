-- ============================================================================
-- Migration: Add frontend error log fields to error_logs table
-- Date: 2026-01-12
-- Description: Add fields required for frontend error logging (errorLogger.ts)
-- ============================================================================

-- 在 Supabase Dashboard SQL Editor 中执行此脚本

BEGIN;

-- 添加前端错误日志字段
ALTER TABLE error_logs
ADD COLUMN IF NOT EXISTS error_id TEXT,
ADD COLUMN IF NOT EXISTS error_code TEXT,
ADD COLUMN IF NOT EXISTS message TEXT,
ADD COLUMN IF NOT EXISTS status_code INTEGER,
ADD COLUMN IF NOT EXISTS endpoint TEXT,
ADD COLUMN IF NOT EXISTS method TEXT,
ADD COLUMN IF NOT EXISTS stack_trace TEXT,
ADD COLUMN IF NOT EXISTS page_url TEXT,
ADD COLUMN IF NOT EXISTS user_agent TEXT,
ADD COLUMN IF NOT EXISTS session_id TEXT,
ADD COLUMN IF NOT EXISTS user_code TEXT,
ADD COLUMN IF NOT EXISTS context JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS client_timestamp TEXT,
ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'frontend';

-- 添加索引
CREATE INDEX IF NOT EXISTS idx_error_logs_error_id ON error_logs(error_id) WHERE error_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_error_logs_session_id ON error_logs(session_id) WHERE session_id IS NOT NULL;

-- 验证
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'error_logs'
ORDER BY ordinal_position;

COMMIT;
