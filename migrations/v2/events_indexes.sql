-- Events Module Performance Indexes
-- Phase 3: 数据库索引优化
--
-- Purpose: Optimize query performance for events aggregation
-- Expected improvement: 10x-100x faster queries
--
-- Created: 2026-01-09
-- Version: v3.27

-- ============================================================================
-- Index 1: created_at descending (for time-based queries)
-- ============================================================================
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_events_created_at
  ON user_events(created_at DESC);

COMMENT ON INDEX idx_user_events_created_at IS
'Optimizes time-range queries and ordering by created_at';

-- ============================================================================
-- Index 2: event_type + created_at (for type-based aggregation)
-- ============================================================================
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_events_type_created_at
  ON user_events(event_type, created_at DESC);

COMMENT ON INDEX idx_user_events_type_created_at IS
'Optimizes event_type filtering with time-range queries';

-- ============================================================================
-- Index 3: user_id + created_at (for user-based aggregation)
-- ============================================================================
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_events_user_created_at
  ON user_events(user_id, created_at DESC);

COMMENT ON INDEX idx_user_events_user_created_at IS
'Optimizes user_id filtering with time-range queries';

-- ============================================================================
-- Index 4: Composite index for stats aggregation
-- ============================================================================
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_events_stats_composite
  ON user_events(event_type, user_id, created_at DESC);

COMMENT ON INDEX idx_user_events_stats_composite IS
'Optimizes complex aggregation queries with multiple filters';

-- ============================================================================
-- Index 5: aggregated_stats lookup
-- ============================================================================
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_aggregated_stats_lookup
  ON aggregated_stats(stat_type, date DESC);

COMMENT ON INDEX idx_aggregated_stats_lookup IS
'Optimizes aggregated_stats queries by stat_type and date';

-- ============================================================================
-- Performance Analysis
-- ============================================================================

-- Before indexes (example):
-- EXPLAIN ANALYZE SELECT COUNT(*) FROM user_events
--   WHERE created_at >= NOW() - INTERVAL '7 days';
-- → Seq Scan on user_events (cost=0.00..10000.00 rows=100000)
-- → Planning time: 0.100 ms, Execution time: 500 ms

-- After indexes (expected):
-- → Index Scan using idx_user_events_created_at (cost=0.42..100.00 rows=1000)
-- → Planning time: 0.050 ms, Execution time: 5 ms

-- ============================================================================
-- Maintenance Notes
-- ============================================================================

-- Monitor index usage:
-- SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
-- FROM pg_stat_user_indexes
-- WHERE tablename = 'user_events'
-- ORDER BY idx_scan DESC;

-- Check index size:
-- SELECT indexname, pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
-- FROM pg_stat_user_indexes
-- WHERE tablename = 'user_events';

-- Rebuild indexes (if needed):
-- REINDEX INDEX CONCURRENTLY idx_user_events_created_at;
