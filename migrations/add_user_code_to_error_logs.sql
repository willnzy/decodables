-- Add user_code column to error_logs table
-- This allows searching error logs by user code (more user-friendly than user_id)

-- Add user_code column
ALTER TABLE error_logs ADD COLUMN IF NOT EXISTS user_code VARCHAR(20);

-- Add index for user_code searches
CREATE INDEX IF NOT EXISTS idx_error_logs_user_code ON error_logs(user_code);

-- Comment
COMMENT ON COLUMN error_logs.user_code IS 'User code for easier identification (e.g., USR001)';
