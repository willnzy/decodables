-- ============================================
-- Aggregated Stats Table (预计算统计数据)
-- ============================================
-- 用于存储定时任务预计算的统计数据
-- 这样 admin 查询时不需要实时计算，提高性能

CREATE TABLE IF NOT EXISTS aggregated_stats (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    date DATE NOT NULL,                    -- 统计日期
    stat_type VARCHAR(50) NOT NULL,        -- 统计类型 (daily_users, daily_revenue, etc.)
    data JSONB NOT NULL DEFAULT '{}',      -- 统计数据 (JSON格式，灵活存储)
    updated_at TIMESTAMPTZ DEFAULT NOW(),  -- 最后更新时间
    
    -- 确保每天每种类型只有一条记录
    UNIQUE(date, stat_type)
);

-- 索引优化查询
CREATE INDEX IF NOT EXISTS idx_agg_stats_date ON aggregated_stats(date DESC);
CREATE INDEX IF NOT EXISTS idx_agg_stats_type ON aggregated_stats(stat_type);
CREATE INDEX IF NOT EXISTS idx_agg_stats_date_type ON aggregated_stats(date DESC, stat_type);

-- RLS 策略 (只有 admin 可以查看和修改)
ALTER TABLE aggregated_stats ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Admin can view aggregated stats" ON aggregated_stats
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM profiles 
            WHERE profiles.id = auth.uid() 
            AND profiles.role = 'admin'
        )
    );

CREATE POLICY "Service role can manage aggregated stats" ON aggregated_stats
    FOR ALL
    USING (true)
    WITH CHECK (true);


-- ============================================
-- 创建快速获取最新统计的函数
-- ============================================

CREATE OR REPLACE FUNCTION get_latest_stats(p_stat_type VARCHAR)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT data INTO result
    FROM aggregated_stats
    WHERE stat_type = p_stat_type
    ORDER BY date DESC
    LIMIT 1;
    
    RETURN COALESCE(result, '{}'::JSONB);
END;
$$;


-- ============================================
-- 创建获取时间范围内统计的函数
-- ============================================

CREATE OR REPLACE FUNCTION get_stats_range(
    p_stat_type VARCHAR,
    p_start_date DATE,
    p_end_date DATE DEFAULT CURRENT_DATE
)
RETURNS TABLE (
    date DATE,
    data JSONB
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT a.date, a.data
    FROM aggregated_stats a
    WHERE a.stat_type = p_stat_type
      AND a.date >= p_start_date
      AND a.date <= p_end_date
    ORDER BY a.date ASC;
END;
$$;

