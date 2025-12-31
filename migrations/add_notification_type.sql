-- =============================================
-- Add notification_type column to notifications table
-- =============================================

-- Add notification_type column
ALTER TABLE notifications 
ADD COLUMN IF NOT EXISTS notification_type TEXT DEFAULT 'system';

-- Add index
CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(notification_type);

-- Comment
COMMENT ON COLUMN notifications.notification_type IS 'Message type: system, promotion, update, warning';

