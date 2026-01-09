-- ==============================================================================
-- v3.19: Add event_id for CAPI/Server-Side GTM Deduplication
-- 
-- Purpose:
-- - event_id is a unique identifier for each analytics event
-- - Used for deduplication between browser-side tracking (GTM) and server-side 
--   tracking (Facebook CAPI, TikTok Events API, Server-Side GTM)
-- - Prevents double-counting conversions when same event is sent from both
--   frontend (dataLayer push) and backend (CAPI webhook)
--
-- Schema Changes:
-- - analytics_events: Add event_id column
-- - user_events: Add event_id column
-- ==============================================================================

-- ==========================================
-- Part 1: Add event_id to analytics_events
-- ==========================================

-- Add event_id column for CAPI deduplication
ALTER TABLE analytics_events 
ADD COLUMN IF NOT EXISTS event_id VARCHAR(100);

-- Add index for efficient deduplication lookup
CREATE INDEX IF NOT EXISTS idx_analytics_events_event_id 
ON analytics_events(event_id) 
WHERE event_id IS NOT NULL;

-- Add composite index for event deduplication queries
-- (commonly query by event_type + event_id)
CREATE INDEX IF NOT EXISTS idx_analytics_events_type_event_id 
ON analytics_events(event_type, event_id) 
WHERE event_id IS NOT NULL;

-- Add comment for documentation
COMMENT ON COLUMN analytics_events.event_id IS 
'Unique event ID for CAPI/sGTM deduplication. Generated client-side using crypto.randomUUID() and passed to both GTM dataLayer and backend API. Enables server-side event tracking without double-counting.';

-- ==========================================
-- Part 2: Add event_id to user_events
-- ==========================================

-- Add event_id column for CAPI deduplication
ALTER TABLE user_events 
ADD COLUMN IF NOT EXISTS event_id VARCHAR(100);

-- Add index for efficient deduplication lookup
CREATE INDEX IF NOT EXISTS idx_user_events_event_id 
ON user_events(event_id) 
WHERE event_id IS NOT NULL;

-- Add composite index for event deduplication queries
CREATE INDEX IF NOT EXISTS idx_user_events_type_event_id 
ON user_events(event_type, event_id) 
WHERE event_id IS NOT NULL;

-- Add comment for documentation
COMMENT ON COLUMN user_events.event_id IS 
'Unique event ID for CAPI/sGTM deduplication. Generated client-side using crypto.randomUUID() and passed to both GTM dataLayer and backend API.';

-- ==========================================
-- Part 3: Verification Queries
-- ==========================================

-- Verify columns exist (run manually after migration)
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns 
-- WHERE table_name = 'analytics_events' AND column_name = 'event_id';

-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns 
-- WHERE table_name = 'user_events' AND column_name = 'event_id';

-- Verify indexes exist
-- SELECT indexname, indexdef FROM pg_indexes 
-- WHERE tablename IN ('analytics_events', 'user_events') 
-- AND indexname LIKE '%event_id%';
