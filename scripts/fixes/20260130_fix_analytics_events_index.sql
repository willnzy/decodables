-- ============================================================================
-- 修复脚本: analytics_events 缺少 created_at 索引
-- ============================================================================
-- 问题: analytics_events 表按 created_at 范围查询时全表扫描
--       Supabase Index Advisor 建议: startup_cost 1348.39 → 6.09 (降低 220 倍)
-- 方案: 添加 btree 索引
-- 日期: 2026-01-30
-- ============================================================================

-- 索引: created_at 用于时间范围查询
CREATE INDEX IF NOT EXISTS idx_analytics_events_created_at
    ON public.analytics_events USING btree (created_at);

-- 索引: user_id 用于按用户查询事件
CREATE INDEX IF NOT EXISTS idx_analytics_events_user_id
    ON public.analytics_events(user_id);

-- ============================================================================
-- 验证
-- ============================================================================
-- SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'analytics_events';
