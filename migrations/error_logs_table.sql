-- Error Logs Table
-- Stores frontend and API errors for debugging and monitoring

CREATE TABLE IF NOT EXISTS error_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Error identification
    error_id VARCHAR(100),           -- Frontend generated error ID
    error_type VARCHAR(50) NOT NULL, -- API, NETWORK, JS_ERROR, UNHANDLED_REJECTION, etc.
    error_code VARCHAR(50),          -- Error code (UNAUTHORIZED, NETWORK_ERROR, etc.)
    
    -- Error details
    message TEXT NOT NULL,
    status_code INTEGER,             -- HTTP status code for API errors
    endpoint VARCHAR(500),           -- API endpoint
    method VARCHAR(10),              -- HTTP method
    
    -- Context
    user_id VARCHAR(100),            -- User ID if authenticated
    session_id VARCHAR(100),         -- Browser session ID
    page_url TEXT,                   -- Page where error occurred
    user_agent TEXT,                 -- Browser/device info
    
    -- Stack trace and additional info
    stack_trace TEXT,
    context JSONB DEFAULT '{}',      -- Additional context data
    
    -- Timestamps
    client_timestamp TIMESTAMPTZ,    -- When error occurred on client
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Indexes for common queries
    CONSTRAINT error_logs_type_check CHECK (error_type IN ('API', 'NETWORK', 'JS_ERROR', 'UNHANDLED_REJECTION', 'REACT_ERROR', 'CORS', 'OTHER'))
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_error_logs_created_at ON error_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_error_logs_user_id ON error_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_error_logs_error_type ON error_logs(error_type);
CREATE INDEX IF NOT EXISTS idx_error_logs_status_code ON error_logs(status_code);
CREATE INDEX IF NOT EXISTS idx_error_logs_endpoint ON error_logs(endpoint);

-- Enable RLS
ALTER TABLE error_logs ENABLE ROW LEVEL SECURITY;

-- Policy: Allow insert from authenticated users and anonymous
CREATE POLICY "Allow insert error logs" ON error_logs
    FOR INSERT
    WITH CHECK (true);

-- Policy: Only allow read for admin users (you may need to adjust based on your auth setup)
CREATE POLICY "Allow read error logs for admins" ON error_logs
    FOR SELECT
    USING (true);  -- Adjust this based on your admin check

COMMENT ON TABLE error_logs IS 'Stores frontend and API errors for debugging and monitoring';
