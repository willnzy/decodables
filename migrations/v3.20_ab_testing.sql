-- ==========================================
-- v3.20: A/B Testing System
-- A/B 实验系统
-- 
-- Tables:
--   - experiments: 实验配置
--   - experiment_assignments: 用户分配记录
--   - experiment_results: 结果聚合（定时任务填充）
--
-- Features:
--   - 确定性变体分配（基于用户标识哈希）
--   - 支持多变体实验
--   - 支持流量分配控制
--   - 支持目标群体筛选
--   - 与 analytics_events 集成
-- ==========================================

-- 1. 实验配置表
CREATE TABLE IF NOT EXISTS experiments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- 基础信息
  experiment_key VARCHAR(100) UNIQUE NOT NULL,  -- 唯一标识，如 'pricing_v2'
  name VARCHAR(255) NOT NULL,                   -- 显示名称
  description TEXT,                             -- 描述
  
  -- 类型和状态
  experiment_type VARCHAR(20) DEFAULT 'ab',     -- 'ab', 'multivariate', 'feature_flag'
  status VARCHAR(20) DEFAULT 'draft',           -- 'draft', 'running', 'paused', 'completed'
  
  -- 变体配置 (JSONB)
  -- 例: [{"key": "control", "name": "原版", "weight": 50}, 
  --      {"key": "variant_a", "name": "新版", "weight": 50}]
  variants JSONB NOT NULL DEFAULT '[{"key": "control", "name": "Control", "weight": 100}]',
  
  -- 目标群体配置
  -- 例: {"tiers": ["free", "starter"], "include_anonymous": true}
  targeting JSONB DEFAULT '{"include_anonymous": true}',
  
  -- 流量分配（0-100，表示参与实验的流量百分比）
  traffic_allocation INT DEFAULT 100 CHECK (traffic_allocation >= 0 AND traffic_allocation <= 100),
  
  -- 目标指标配置
  -- 例: [{"key": "primary", "event": "md_subscription_started", "type": "conversion"}]
  metrics JSONB DEFAULT '[]',
  
  -- 停止后配置
  fallback_variant VARCHAR(100) DEFAULT 'control',  -- 实验停止后的默认变体
  winning_variant VARCHAR(100),                      -- 宣布的赢家（实验结束时设置）
  
  -- 调度
  start_at TIMESTAMPTZ,
  end_at TIMESTAMPTZ,
  
  -- 元数据
  created_by TEXT,
  updated_by TEXT,
  -- v3.9: Timezone support
  timezone TEXT DEFAULT 'UTC',
  created_at_local TIMESTAMP,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. 用户分配记录表
CREATE TABLE IF NOT EXISTS experiment_assignments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  experiment_id UUID NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
  experiment_key VARCHAR(100) NOT NULL,         -- 冗余存储，方便查询
  
  -- 用户标识
  user_identifier VARCHAR(100) NOT NULL,        -- userCode 或 visitor_xxx
  identifier_type VARCHAR(20) DEFAULT 'user',   -- 'user' 或 'visitor'
  
  -- 分配结果
  variant_key VARCHAR(100) NOT NULL,
  
  -- 上下文（用于后续分群分析）
  context JSONB DEFAULT '{}',
  -- 例: {"tier": "free", "device": "mobile", "source": "organic"}
  
  assigned_at TIMESTAMPTZ DEFAULT NOW(),
  
  -- 唯一约束：同一实验同一用户只能分配一次
  UNIQUE(experiment_id, user_identifier)
);

-- 3. 实验结果聚合表（每小时更新）
CREATE TABLE IF NOT EXISTS experiment_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  experiment_id UUID NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
  variant_key VARCHAR(100) NOT NULL,
  
  -- 时间粒度
  date DATE NOT NULL,
  hour INT DEFAULT 0,  -- 0-23，hour=0 且无其他小时记录表示全天汇总
  
  -- 核心指标
  participants INT DEFAULT 0,       -- 参与人数（被分配的）
  exposures INT DEFAULT 0,          -- 曝光次数（viewed 事件）
  conversions INT DEFAULT 0,        -- 转化次数
  
  -- 计算指标
  conversion_rate DECIMAL(10, 6),   -- 转化率
  
  -- 扩展指标 (JSON)
  metrics_data JSONB DEFAULT '{}',
  -- 例: {"revenue": 1234.56, "avg_session_duration": 180}
  
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  
  UNIQUE(experiment_id, variant_key, date, hour)
);

-- ==========================================
-- 索引
-- ==========================================

-- experiments 索引
CREATE INDEX IF NOT EXISTS idx_experiments_status ON experiments(status);
CREATE INDEX IF NOT EXISTS idx_experiments_key ON experiments(experiment_key);
CREATE INDEX IF NOT EXISTS idx_experiments_dates ON experiments(start_at, end_at);
CREATE INDEX IF NOT EXISTS idx_experiments_created_at ON experiments(created_at DESC);

-- experiment_assignments 索引
CREATE INDEX IF NOT EXISTS idx_exp_assignments_experiment ON experiment_assignments(experiment_id);
CREATE INDEX IF NOT EXISTS idx_exp_assignments_user ON experiment_assignments(user_identifier);
CREATE INDEX IF NOT EXISTS idx_exp_assignments_key_user ON experiment_assignments(experiment_key, user_identifier);
CREATE INDEX IF NOT EXISTS idx_exp_assignments_variant ON experiment_assignments(experiment_id, variant_key);

-- experiment_results 索引
CREATE INDEX IF NOT EXISTS idx_exp_results_experiment ON experiment_results(experiment_id);
CREATE INDEX IF NOT EXISTS idx_exp_results_experiment_date ON experiment_results(experiment_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_exp_results_variant ON experiment_results(experiment_id, variant_key);

-- ==========================================
-- RLS 策略
-- ==========================================

ALTER TABLE experiments ENABLE ROW LEVEL SECURITY;
ALTER TABLE experiment_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE experiment_results ENABLE ROW LEVEL SECURITY;

-- Service role 完全访问
DROP POLICY IF EXISTS "Service role full access on experiments" ON experiments;
CREATE POLICY "Service role full access on experiments" ON experiments
  FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role full access on experiment_assignments" ON experiment_assignments;
CREATE POLICY "Service role full access on experiment_assignments" ON experiment_assignments
  FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role full access on experiment_results" ON experiment_results;
CREATE POLICY "Service role full access on experiment_results" ON experiment_results
  FOR ALL USING (true) WITH CHECK (true);

-- ==========================================
-- 更新时间触发器
-- ==========================================

CREATE OR REPLACE FUNCTION update_experiments_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_experiments_updated_at ON experiments;
CREATE TRIGGER trg_experiments_updated_at
  BEFORE UPDATE ON experiments
  FOR EACH ROW
  EXECUTE FUNCTION update_experiments_timestamp();

-- ==========================================
-- 注释
-- ==========================================

COMMENT ON TABLE experiments IS 'A/B 测试实验配置表';
COMMENT ON TABLE experiment_assignments IS 'A/B 测试用户分配记录表';
COMMENT ON TABLE experiment_results IS 'A/B 测试结果聚合表（定时任务填充）';

COMMENT ON COLUMN experiments.experiment_key IS '实验唯一标识，用于代码引用';
COMMENT ON COLUMN experiments.variants IS '变体配置 JSON 数组，包含 key, name, weight';
COMMENT ON COLUMN experiments.targeting IS '目标群体配置，如用户等级、是否包含匿名用户';
COMMENT ON COLUMN experiments.traffic_allocation IS '流量分配百分比 0-100';
COMMENT ON COLUMN experiments.fallback_variant IS '实验停止后的默认变体';
COMMENT ON COLUMN experiments.winning_variant IS '实验结束时宣布的赢家变体';

COMMENT ON COLUMN experiment_assignments.user_identifier IS '用户标识（userCode 或 visitor_xxx）';
COMMENT ON COLUMN experiment_assignments.identifier_type IS '标识类型：user（已登录）或 visitor（匿名）';
COMMENT ON COLUMN experiment_assignments.context IS '分配时的上下文，用于后续分群分析';

COMMENT ON COLUMN experiment_results.hour IS '小时粒度，0-23；hour=0 表示全天汇总';
COMMENT ON COLUMN experiment_results.metrics_data IS '扩展指标 JSON，如收入、会话时长等';
