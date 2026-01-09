-- =====================================================
-- Migration: v3.23 - Task Queue System
-- 任务队列系统
-- 
-- Purpose:
-- - Track async generation tasks
-- - Support task status updates
-- - Enable progress tracking
-- - Handle task history and cleanup
--
-- Tables:
-- - generation_tasks: Async task tracking
--
-- Author: System
-- Date: 2026-01-06
-- =====================================================

-- =====================================================
-- 1. Generation Tasks Table
-- 生成任务表
-- =====================================================
CREATE TABLE IF NOT EXISTS generation_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Task identification
    task_id VARCHAR(32) NOT NULL UNIQUE,  -- Short task ID for API
    user_id VARCHAR(255) NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    
    -- Task type and priority
    task_type VARCHAR(50) NOT NULL DEFAULT 'image_generation',
    priority INTEGER NOT NULL DEFAULT 0,  -- Higher = more priority
    
    -- Task parameters (stored as JSON)
    params JSONB NOT NULL DEFAULT '{}',
    
    -- Status tracking
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- pending, queued, processing, completed, failed, cancelled
    
    -- Progress tracking
    progress INTEGER NOT NULL DEFAULT 0,  -- 0-100
    current_step INTEGER DEFAULT 0,
    total_steps INTEGER DEFAULT 0,
    progress_message VARCHAR(500),
    
    -- Results
    result JSONB,  -- Final result data
    error_message TEXT,
    error_code VARCHAR(50),
    
    -- Timing
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    queued_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    -- Worker info
    worker_id VARCHAR(100),
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    
    -- Cleanup
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '24 hours')
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_generation_tasks_user_id 
    ON generation_tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_generation_tasks_task_id 
    ON generation_tasks(task_id);
CREATE INDEX IF NOT EXISTS idx_generation_tasks_status 
    ON generation_tasks(status);
CREATE INDEX IF NOT EXISTS idx_generation_tasks_created_at 
    ON generation_tasks(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_generation_tasks_expires_at 
    ON generation_tasks(expires_at) WHERE status IN ('completed', 'failed');

-- =====================================================
-- 2. RPC Function: Create Task
-- 创建任务 (原子操作)
-- =====================================================
CREATE OR REPLACE FUNCTION create_generation_task(
    p_task_id VARCHAR(32),
    p_user_id VARCHAR(255),
    p_task_type VARCHAR(50),
    p_params JSONB,
    p_priority INTEGER DEFAULT 0,
    p_total_steps INTEGER DEFAULT 8
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_task_record generation_tasks%ROWTYPE;
BEGIN
    -- Check for duplicate task_id (idempotency)
    SELECT * INTO v_task_record
    FROM generation_tasks
    WHERE task_id = p_task_id;
    
    IF FOUND THEN
        RETURN jsonb_build_object(
            'success', true,
            'idempotent', true,
            'task_id', p_task_id,
            'status', v_task_record.status
        );
    END IF;
    
    -- Insert new task
    INSERT INTO generation_tasks (
        task_id,
        user_id,
        task_type,
        params,
        priority,
        total_steps,
        status
    ) VALUES (
        p_task_id,
        p_user_id,
        p_task_type,
        p_params,
        p_priority,
        p_total_steps,
        'pending'
    )
    RETURNING * INTO v_task_record;
    
    RETURN jsonb_build_object(
        'success', true,
        'idempotent', false,
        'task_id', p_task_id,
        'id', v_task_record.id,
        'status', v_task_record.status
    );
END;
$$;

-- =====================================================
-- 3. RPC Function: Update Task Status
-- 更新任务状态
-- =====================================================
CREATE OR REPLACE FUNCTION update_task_status(
    p_task_id VARCHAR(32),
    p_status VARCHAR(20),
    p_progress INTEGER DEFAULT NULL,
    p_current_step INTEGER DEFAULT NULL,
    p_progress_message VARCHAR(500) DEFAULT NULL,
    p_result JSONB DEFAULT NULL,
    p_error_message TEXT DEFAULT NULL,
    p_error_code VARCHAR(50) DEFAULT NULL,
    p_worker_id VARCHAR(100) DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_task generation_tasks%ROWTYPE;
BEGIN
    -- Get current task
    SELECT * INTO v_task
    FROM generation_tasks
    WHERE task_id = p_task_id
    FOR UPDATE;
    
    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Task not found'
        );
    END IF;
    
    -- Update task
    UPDATE generation_tasks
    SET
        status = COALESCE(p_status, status),
        progress = COALESCE(p_progress, progress),
        current_step = COALESCE(p_current_step, current_step),
        progress_message = COALESCE(p_progress_message, progress_message),
        result = COALESCE(p_result, result),
        error_message = COALESCE(p_error_message, error_message),
        error_code = COALESCE(p_error_code, error_code),
        worker_id = COALESCE(p_worker_id, worker_id),
        -- Update timestamps based on status
        queued_at = CASE 
            WHEN p_status = 'queued' AND queued_at IS NULL THEN NOW()
            ELSE queued_at
        END,
        started_at = CASE 
            WHEN p_status = 'processing' AND started_at IS NULL THEN NOW()
            ELSE started_at
        END,
        completed_at = CASE 
            WHEN p_status IN ('completed', 'failed', 'cancelled') AND completed_at IS NULL THEN NOW()
            ELSE completed_at
        END
    WHERE task_id = p_task_id
    RETURNING * INTO v_task;
    
    RETURN jsonb_build_object(
        'success', true,
        'task_id', p_task_id,
        'status', v_task.status,
        'progress', v_task.progress
    );
END;
$$;

-- =====================================================
-- 4. RPC Function: Get Task Details
-- 获取任务详情
-- =====================================================
CREATE OR REPLACE FUNCTION get_task_details(
    p_task_id VARCHAR(32),
    p_user_id VARCHAR(255) DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_task generation_tasks%ROWTYPE;
BEGIN
    -- Get task (optionally filter by user_id for security)
    IF p_user_id IS NOT NULL THEN
        SELECT * INTO v_task
        FROM generation_tasks
        WHERE task_id = p_task_id AND user_id = p_user_id;
    ELSE
        SELECT * INTO v_task
        FROM generation_tasks
        WHERE task_id = p_task_id;
    END IF;
    
    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Task not found'
        );
    END IF;
    
    RETURN jsonb_build_object(
        'success', true,
        'task_id', v_task.task_id,
        'status', v_task.status,
        'progress', v_task.progress,
        'current_step', v_task.current_step,
        'total_steps', v_task.total_steps,
        'progress_message', v_task.progress_message,
        'result', v_task.result,
        'error_message', v_task.error_message,
        'error_code', v_task.error_code,
        'created_at', v_task.created_at,
        'started_at', v_task.started_at,
        'completed_at', v_task.completed_at,
        'retry_count', v_task.retry_count
    );
END;
$$;

-- =====================================================
-- 5. Cleanup Function
-- 清理过期任务
-- =====================================================
CREATE OR REPLACE FUNCTION cleanup_expired_tasks()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_deleted INTEGER;
BEGIN
    -- Delete expired completed/failed tasks
    DELETE FROM generation_tasks
    WHERE expires_at < NOW()
    AND status IN ('completed', 'failed', 'cancelled');
    
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    
    RETURN v_deleted;
END;
$$;

-- =====================================================
-- 6. RLS Policies
-- 行级安全策略
-- =====================================================
ALTER TABLE generation_tasks ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if any (for idempotent migrations)
DROP POLICY IF EXISTS generation_tasks_select_policy ON generation_tasks;
DROP POLICY IF EXISTS generation_tasks_service_policy ON generation_tasks;

-- Users can only see their own tasks
CREATE POLICY generation_tasks_select_policy ON generation_tasks
    FOR SELECT
    USING (auth.uid()::text = user_id OR auth.role() = 'service_role');

-- Service role can do everything
CREATE POLICY generation_tasks_service_policy ON generation_tasks
    FOR ALL
    USING (auth.role() = 'service_role');

-- =====================================================
-- Migration Complete
-- =====================================================
COMMENT ON TABLE generation_tasks IS 'Async generation task tracking (v3.23)';
