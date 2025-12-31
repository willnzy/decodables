-- ============================================
-- Aggregated Stats Table ()
-- ============================================
-- 
--  admin ，

CREATE TABLE IF NOT EXISTS aggregated_stats (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    date DATE NOT NULL,                    -- 
    stat_type VARCHAR(50) NOT NULL,        --  (daily_users, daily_revenue, etc.)
    data JSONB NOT NULL DEFAULT '{}',      --  (JSON，)
    updated_at TIMESTAMPTZ DEFAULT NOW(),  -- 
    
    -- 
    UNIQUE(date, stat_type)
);

-- 
CREATE INDEX IF NOT EXISTS idx_agg_stats_date ON aggregated_stats(date DESC);
CREATE INDEX IF NOT EXISTS idx_agg_stats_type ON aggregated_stats(stat_type);
CREATE INDEX IF NOT EXISTS idx_agg_stats_date_type ON aggregated_stats(date DESC, stat_type);

-- RLS  ( admin )
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
-- 
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
-- 
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

