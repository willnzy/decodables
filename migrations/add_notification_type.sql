-- =============================================
-- Add notification_type column to notifications table
-- =============================================

-- 添加 notification_type 列
ALTER TABLE notifications 
ADD COLUMN IF NOT EXISTS notification_type TEXT DEFAULT 'system';

-- 添加索引
CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(notification_type);

-- 注释
COMMENT ON COLUMN notifications.notification_type IS 'Message type: system, promotion, update, warning';

