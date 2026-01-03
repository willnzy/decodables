-- ============================================================
-- Migration: v3.15 - Scheduled Task Logs
-- Description: Track scheduled task execution for monitoring
-- ============================================================

-- Create table for scheduled task execution logs
CREATE TABLE IF NOT EXISTS scheduled_task_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Task identification
    task_name TEXT NOT NULL,           -- e.g., 'campaign_scheduler', 'metrics_etl'
    task_type TEXT NOT NULL,           -- e.g., 'full', 'campaigns', 'themes', 'hourly', 'daily'
    
    -- Execution details
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,               -- Execution duration in milliseconds
    
    -- Status: running | success | failed | timeout
    status TEXT NOT NULL DEFAULT 'running',
    
    -- Results summary (JSON)
    result_summary JSONB DEFAULT '{}'::jsonb,
    /*
    Example for campaign_scheduler:
    {
        "campaigns_activated": 0,
        "campaigns_ended": 0,
        "current_theme": "Christmas",
        "errors": 0
    }
    
    Example for metrics_etl:
    {
        "records_processed": 1500,
        "dau": 234,
        "errors": 0
    }
    */
    
    -- Error information (if failed)
    error_message TEXT,
    error_stack TEXT,
    
    -- Metadata
    hostname TEXT,                     -- Server hostname
    pid INTEGER,                       -- Process ID
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_task_logs_task_name ON scheduled_task_logs(task_name);
CREATE INDEX IF NOT EXISTS idx_task_logs_started_at ON scheduled_task_logs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_task_logs_status ON scheduled_task_logs(status);

-- Create a view for latest task status
CREATE OR REPLACE VIEW v_latest_task_status AS
SELECT DISTINCT ON (task_name)
    task_name,
    task_type,
    started_at,
    completed_at,
    duration_ms,
    status,
    result_summary,
    error_message,
    hostname,
    -- Calculate time since last run
    EXTRACT(EPOCH FROM (NOW() - started_at)) / 60 AS minutes_since_last_run
FROM scheduled_task_logs
ORDER BY task_name, started_at DESC;

-- Function to clean up old logs (keep last 7 days)
CREATE OR REPLACE FUNCTION cleanup_old_task_logs()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM scheduled_task_logs
    WHERE started_at < NOW() - INTERVAL '7 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- RLS Policies (admin only)
ALTER TABLE scheduled_task_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Admins can view task logs"
    ON scheduled_task_logs FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE profiles.id = auth.uid() 
            AND profiles.role = 'admin'
        )
    );

-- Comment
COMMENT ON TABLE scheduled_task_logs IS 
'Tracks scheduled task execution for monitoring and alerting.
Tasks include: campaign_scheduler, metrics_etl, aggregate_stats, etc.
Retention: 7 days (cleaned up by cleanup_old_task_logs function)';
