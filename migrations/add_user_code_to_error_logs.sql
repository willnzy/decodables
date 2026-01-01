-- Add user_code column to error_logs table
-- This allows searching error logs by user code (more user-friendly than user_id)

-- Add user_code column
ALTER TABLE error_logs ADD COLUMN IF NOT EXISTS user_code VARCHAR(20);

-- Add index for user_code searches
CREATE INDEX IF NOT EXISTS idx_error_logs_user_code ON error_logs(user_code);

-- Comment
COMMENT ON COLUMN error_logs.user_code IS 'User code for easier identification (e.g., USR001)';

-- Backfill user_code from profiles table for existing records
UPDATE error_logs el
SET user_code = p.user_code
FROM profiles p
WHERE el.user_id = p.id
  AND el.user_code IS NULL
  AND p.user_code IS NOT NULL;
