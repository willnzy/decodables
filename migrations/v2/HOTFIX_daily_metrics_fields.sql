-- ============================================================================
-- HOTFIX: daily_metrics 表字段修复
-- ============================================================================
-- 说明: Repository 代码使用 date 和 dau 字段，但表定义使用 metric_date
-- 问题: 字段名不匹配导致查询失败
-- 执行时间: 2026-01-15
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 方案: 添加别名列并创建视图
-- ----------------------------------------------------------------------------

-- 1. 添加 date 列 (metric_date 的别名)
ALTER TABLE daily_metrics 
ADD COLUMN IF NOT EXISTS date DATE;

-- 2. 添加 dau 列 (DAU = Daily Active Users)
ALTER TABLE daily_metrics 
ADD COLUMN IF NOT EXISTS dau INTEGER DEFAULT 0;

-- 3. 同步现有数据 (如果有)
UPDATE daily_metrics 
SET date = metric_date 
WHERE date IS NULL AND metric_date IS NOT NULL;

UPDATE daily_metrics 
SET dau = active_users 
WHERE dau = 0 AND active_users > 0;

-- 4. 添加触发器保持 date 和 metric_date 同步
CREATE OR REPLACE FUNCTION sync_daily_metrics_date()
RETURNS TRIGGER AS $$
BEGIN
    -- 插入时同步
    IF TG_OP = 'INSERT' THEN
        IF NEW.date IS NULL AND NEW.metric_date IS NOT NULL THEN
            NEW.date := NEW.metric_date;
        ELSIF NEW.metric_date IS NULL AND NEW.date IS NOT NULL THEN
            NEW.metric_date := NEW.date;
        END IF;
    END IF;
    
    -- 更新时同步
    IF TG_OP = 'UPDATE' THEN
        IF NEW.metric_date IS DISTINCT FROM OLD.metric_date THEN
            NEW.date := NEW.metric_date;
        ELSIF NEW.date IS DISTINCT FROM OLD.date THEN
            NEW.metric_date := NEW.date;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sync_daily_metrics_date ON daily_metrics;
CREATE TRIGGER trg_sync_daily_metrics_date
    BEFORE INSERT OR UPDATE ON daily_metrics
    FOR EACH ROW
    EXECUTE FUNCTION sync_daily_metrics_date();

-- 5. 添加索引
CREATE INDEX IF NOT EXISTS idx_daily_metrics_date ON daily_metrics(date DESC) WHERE date IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_daily_metrics_dau ON daily_metrics(dau DESC) WHERE dau IS NOT NULL;

COMMIT;

-- ============================================================================
-- 验证
-- ============================================================================
-- SELECT column_name, data_type 
-- FROM information_schema.columns 
-- WHERE table_name = 'daily_metrics' 
-- ORDER BY ordinal_position;
