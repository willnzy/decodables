-- ============================================================================
-- HOTFIX: 添加 hourly_metrics 表
-- ============================================================================
-- 说明: 应用层代码 (metrics/etl.py) 使用了 hourly_metrics 表，但数据库中缺失
-- 执行时间: 2026-01-15
-- 执行顺序: 在 02_platform_services.sql 之后执行
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- hourly_metrics - 小时级指标存储表
-- ----------------------------------------------------------------------------
-- 用途: 存储每小时的快速指标统计
-- 写入: scheduler.py 中的 hourly ETL 任务
-- 字段: hour (时间戳), events (事件数)
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS hourly_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 时间标识 (小时精度)
    hour TIMESTAMPTZ NOT NULL,
    
    -- 指标数据
    events INTEGER DEFAULT 0 CHECK (events >= 0),
    
    -- 扩展字段 (预留)
    active_users INTEGER DEFAULT 0 CHECK (active_users >= 0),
    new_projects INTEGER DEFAULT 0 CHECK (new_projects >= 0),
    ai_generations INTEGER DEFAULT 0 CHECK (ai_generations >= 0),
    
    -- 元数据
    metadata JSONB DEFAULT '{}',
    
    -- 审计字段
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 唯一约束: 每小时只有一条记录
    CONSTRAINT unique_hourly_metric UNIQUE (hour)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_hourly_metrics_hour ON hourly_metrics(hour DESC);
CREATE INDEX IF NOT EXISTS idx_hourly_metrics_created_at ON hourly_metrics(created_at DESC);

-- 注释
COMMENT ON TABLE hourly_metrics IS '小时级指标存储表，由 ETL 定时任务写入';
COMMENT ON COLUMN hourly_metrics.hour IS '小时时间戳（每小时整点）';
COMMENT ON COLUMN hourly_metrics.events IS '该小时内的事件数量';

-- ============================================================================
-- RLS 策略
-- ============================================================================

ALTER TABLE hourly_metrics ENABLE ROW LEVEL SECURITY;

-- Admin 只读
CREATE POLICY "Admin can read hourly_metrics"
    ON hourly_metrics
    FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE id = auth.uid()::text
            AND role = 'admin'
        )
    );

-- Service role 可写 (用于 ETL)
CREATE POLICY "Service role can insert hourly_metrics"
    ON hourly_metrics
    FOR INSERT
    TO service_role
    WITH CHECK (true);

COMMIT;

-- ============================================================================
-- 验证
-- ============================================================================
-- SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'hourly_metrics');
