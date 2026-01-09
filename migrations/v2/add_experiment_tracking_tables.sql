-- ============================================================================
-- 添加实验追踪表 (experiment_exposures & experiment_conversions)
-- ============================================================================
-- 创建时间: 2026-01-10
-- 目的: 补充 V2 schema 中缺失的实验事件追踪表
-- 问题: #EXP-UNKNOWN-1
--
-- 说明:
-- 1. experiment_exposures - 追踪用户看到实验变体的曝光事件
-- 2. experiment_conversions - 追踪实验的转化事件 (如点击、购买等)
-- 3. 这些表与 experiment_results (聚合表) 配合使用:
--    - exposures/conversions 存储原始事件 (raw events)
--    - experiment_results 存储每日聚合数据 (daily aggregates)
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 33. experiment_exposures (实验曝光表)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS experiment_exposures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    experiment_id UUID NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    variant_key TEXT NOT NULL,
    context JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE experiment_exposures IS '实验曝光表: 追踪用户看到实验变体的事件 (用于去重和分析)';
COMMENT ON COLUMN experiment_exposures.context IS '曝光上下文 (页面、来源等)';

-- 索引
CREATE INDEX IF NOT EXISTS idx_exp_exposures_experiment ON experiment_exposures(experiment_id);
CREATE INDEX IF NOT EXISTS idx_exp_exposures_user ON experiment_exposures(user_id);
CREATE INDEX IF NOT EXISTS idx_exp_exposures_created_at ON experiment_exposures(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_exp_exposures_dedup ON experiment_exposures(experiment_id, user_id, created_at DESC);

-- ----------------------------------------------------------------------------
-- 34. experiment_conversions (实验转化表)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS experiment_conversions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    experiment_id UUID NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    variant_key TEXT NOT NULL,
    metric_key TEXT NOT NULL,
    value NUMERIC(10, 2) DEFAULT 1.0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE experiment_conversions IS '实验转化表: 追踪实验的转化事件和指标';
COMMENT ON COLUMN experiment_conversions.metric_key IS '转化指标名称 (如 signup, purchase, click)';
COMMENT ON COLUMN experiment_conversions.value IS '转化值 (如收入金额、点击次数)';
COMMENT ON COLUMN experiment_conversions.metadata IS '转化元数据 (订单ID、产品信息等)';

-- 索引
CREATE INDEX IF NOT EXISTS idx_exp_conversions_experiment ON experiment_conversions(experiment_id);
CREATE INDEX IF NOT EXISTS idx_exp_conversions_user ON experiment_conversions(user_id);
CREATE INDEX IF NOT EXISTS idx_exp_conversions_metric ON experiment_conversions(metric_key);
CREATE INDEX IF NOT EXISTS idx_exp_conversions_created_at ON experiment_conversions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_exp_conversions_exp_metric ON experiment_conversions(experiment_id, metric_key, created_at DESC);

COMMIT;

-- ============================================================================
-- 使用说明
-- ============================================================================
--
-- 1. 运行此 migration:
--    psql -h <host> -U <user> -d <database> -f add_experiment_tracking_tables.sql
--
-- 2. 数据流:
--    用户访问 → track_exposure() → experiment_exposures
--    用户转化 → track_conversion() → experiment_conversions
--    定时任务 → 聚合 → experiment_results (每日/每小时)
--
-- 3. 查询示例:
--    -- 查看某实验的曝光次数
--    SELECT variant_key, COUNT(*) as exposures
--    FROM experiment_exposures
--    WHERE experiment_id = 'xxx'
--    GROUP BY variant_key;
--
--    -- 查看某实验的转化率
--    SELECT
--        e.variant_key,
--        COUNT(DISTINCT e.user_id) as exposed_users,
--        COUNT(DISTINCT c.user_id) as converted_users,
--        ROUND(COUNT(DISTINCT c.user_id)::NUMERIC / COUNT(DISTINCT e.user_id) * 100, 2) as conversion_rate
--    FROM experiment_exposures e
--    LEFT JOIN experiment_conversions c ON e.experiment_id = c.experiment_id AND e.user_id = c.user_id
--    WHERE e.experiment_id = 'xxx'
--    GROUP BY e.variant_key;
--
-- ============================================================================
