-- ============================================================================
-- Migration: 003 - Create Pricing System Tables
-- ============================================================================
-- Description: 创建价格配置系统的三张核心表
-- Author: Claude Code + Team
-- Date: 2026-01-09
-- Depends on: 002_refactored_schema_v2.sql
--
-- Tables:
--   1. pricing_plans - 定价方案主表
--   2. pricing_history - 价格变更历史 (审计追踪)
--   3. user_price_overrides - 用户级价格覆盖
--
-- Reference: docs/main/PRICING-SYSTEM-DESIGN.md
-- ============================================================================

BEGIN;

-- ============================================================================
-- Table 1: pricing_plans - 定价方案主表
-- ============================================================================

CREATE TABLE IF NOT EXISTS pricing_plans (
    id SERIAL PRIMARY KEY,

    -- ========== 基础信息 ==========
    plan_code VARCHAR(50) UNIQUE NOT NULL,  -- 'tier_t2_monthly', 'credits_500'
    plan_type VARCHAR(20) NOT NULL,         -- 'subscription', 'credits'
    plan_name VARCHAR(100) NOT NULL,        -- 'Starter Plan', '500 Credits Pack'
    description TEXT,

    -- ========== 价格信息 (美分, 避免浮点精度问题) ==========
    price_cents INT NOT NULL CHECK (price_cents >= 0),           -- 实际收费价格 (cents)
    original_price_cents INT CHECK (original_price_cents >= 0),  -- 原价 (划线价, 可选)
    currency VARCHAR(3) DEFAULT 'USD' NOT NULL,

    -- ========== 订阅专用字段 ==========
    billing_interval VARCHAR(20),           -- 'month', 'year' (仅订阅)
    tier VARCHAR(10),                       -- 't2', 't3' (仅订阅)
    monthly_credits INT,                    -- 月度积分数 (仅订阅)

    -- ========== 积分包专用字段 ==========
    credits_amount INT,                     -- 积分数量 (仅积分包)

    -- ========== Stripe 集成 ==========
    stripe_price_id_prod VARCHAR(100),      -- Stripe Price ID (生产环境)
    stripe_price_id_dev VARCHAR(100),       -- Stripe Price ID (开发环境)
    stripe_product_id VARCHAR(100),         -- Stripe Product ID

    -- ========== 状态管理 ==========
    is_active BOOLEAN DEFAULT TRUE NOT NULL,        -- 是否激活 (下架旧方案用)
    is_visible BOOLEAN DEFAULT TRUE NOT NULL,       -- 是否在前端展示
    is_featured BOOLEAN DEFAULT FALSE NOT NULL,     -- 是否推荐
    sort_order INT DEFAULT 0 NOT NULL,              -- 展示顺序

    -- ========== 版本管理 ==========
    version INT DEFAULT 1 NOT NULL CHECK (version > 0),  -- 版本号
    effective_from TIMESTAMPTZ DEFAULT NOW(),            -- 生效时间
    effective_until TIMESTAMPTZ,                         -- 失效时间 (可选)

    -- ========== 元数据 ==========
    metadata JSONB DEFAULT '{}'::jsonb,     -- 额外配置 (如优惠信息, A/B测试标签)

    -- ========== 审计字段 ==========
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    created_by VARCHAR(100),                -- 操作人 (admin_user_id)
    updated_by VARCHAR(100),

    -- ========== 约束 ==========
    CONSTRAINT check_plan_type CHECK (plan_type IN ('subscription', 'credits')),
    CONSTRAINT check_subscription_fields CHECK (
        (plan_type = 'subscription' AND billing_interval IS NOT NULL AND tier IS NOT NULL)
        OR (plan_type = 'credits' AND credits_amount IS NOT NULL)
    ),
    CONSTRAINT check_effective_dates CHECK (effective_until IS NULL OR effective_until > effective_from)
);

-- 索引
CREATE INDEX idx_pricing_plans_plan_code ON pricing_plans(plan_code);
CREATE INDEX idx_pricing_plans_plan_type ON pricing_plans(plan_type);
CREATE INDEX idx_pricing_plans_is_active ON pricing_plans(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_pricing_plans_is_visible ON pricing_plans(is_visible) WHERE is_visible = TRUE;
CREATE INDEX idx_pricing_plans_effective_from ON pricing_plans(effective_from);
CREATE INDEX idx_pricing_plans_tier ON pricing_plans(tier) WHERE tier IS NOT NULL;
CREATE INDEX idx_pricing_plans_sort_order ON pricing_plans(sort_order);

-- 注释
COMMENT ON TABLE pricing_plans IS '定价方案主表 - 存储所有订阅方案和积分包的价格配置';
COMMENT ON COLUMN pricing_plans.plan_code IS '方案代码 (唯一标识): tier_t2_monthly, credits_500';
COMMENT ON COLUMN pricing_plans.price_cents IS '实际价格 (美分): 990 = $9.9';
COMMENT ON COLUMN pricing_plans.original_price_cents IS '原价 (美分, 用于展示划线价): 1490 = $14.9';
COMMENT ON COLUMN pricing_plans.stripe_price_id_prod IS 'Stripe Price ID (生产环境)';
COMMENT ON COLUMN pricing_plans.stripe_price_id_dev IS 'Stripe Price ID (开发环境)';
COMMENT ON COLUMN pricing_plans.is_active IS '是否激活 (FALSE = 下架但保留记录)';
COMMENT ON COLUMN pricing_plans.is_visible IS '是否在前端展示 (FALSE = 隐藏但可购买)';
COMMENT ON COLUMN pricing_plans.version IS '版本号 (价格修改时递增)';
COMMENT ON COLUMN pricing_plans.metadata IS '扩展元数据 (JSON): discount_percent, badge, experiment_id';

-- ============================================================================
-- Table 2: pricing_history - 价格变更历史
-- ============================================================================

CREATE TABLE IF NOT EXISTS pricing_history (
    id SERIAL PRIMARY KEY,
    pricing_plan_id INT NOT NULL REFERENCES pricing_plans(id) ON DELETE CASCADE,

    -- ========== 变更信息 ==========
    action VARCHAR(20) NOT NULL,            -- 'create', 'update_price', 'update_metadata', 'deactivate', 'reactivate'
    old_price_cents INT,                    -- 旧价格 (美分)
    new_price_cents INT,                    -- 新价格 (美分)
    change_reason TEXT,                     -- 变更原因

    -- ========== 审计信息 ==========
    changed_by VARCHAR(100) NOT NULL,       -- 操作人 (admin_user_id 或 system)
    changed_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- ========== 快照 (便于审计和回溯) ==========
    snapshot JSONB NOT NULL,                -- 完整的 pricing_plan 数据快照

    -- ========== 约束 ==========
    CONSTRAINT check_action CHECK (action IN ('create', 'update_price', 'update_metadata', 'deactivate', 'reactivate', 'delete'))
);

-- 索引
CREATE INDEX idx_pricing_history_plan_id ON pricing_history(pricing_plan_id);
CREATE INDEX idx_pricing_history_changed_at ON pricing_history(changed_at DESC);
CREATE INDEX idx_pricing_history_changed_by ON pricing_history(changed_by);
CREATE INDEX idx_pricing_history_action ON pricing_history(action);

-- 注释
COMMENT ON TABLE pricing_history IS '价格变更历史 - 审计追踪所有价格相关的修改';
COMMENT ON COLUMN pricing_history.snapshot IS '完整的 pricing_plan 数据快照 (JSON)';

-- ============================================================================
-- Table 3: user_price_overrides - 用户级价格覆盖
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_price_overrides (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    pricing_plan_id INT NOT NULL REFERENCES pricing_plans(id) ON DELETE CASCADE,

    -- ========== 覆盖价格 ==========
    override_price_cents INT NOT NULL CHECK (override_price_cents >= 0),  -- 用户专属价格 (美分)
    reason TEXT NOT NULL,                   -- 原因: "老用户续费优惠", "企业客户定制价"

    -- ========== 有效期 ==========
    valid_from TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    valid_until TIMESTAMPTZ,                -- NULL = 永久有效

    -- ========== 审计 ==========
    created_by VARCHAR(100) NOT NULL,       -- 操作人 (admin_user_id)
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- ========== 约束 ==========
    UNIQUE(user_id, pricing_plan_id),
    CONSTRAINT check_valid_dates CHECK (valid_until IS NULL OR valid_until > valid_from)
);

-- 索引
CREATE INDEX idx_user_price_overrides_user_id ON user_price_overrides(user_id);
CREATE INDEX idx_user_price_overrides_plan_id ON user_price_overrides(pricing_plan_id);
CREATE INDEX idx_user_price_overrides_valid_from ON user_price_overrides(valid_from);
CREATE INDEX idx_user_price_overrides_valid_until ON user_price_overrides(valid_until) WHERE valid_until IS NOT NULL;

-- 注释
COMMENT ON TABLE user_price_overrides IS '用户级价格覆盖 - 支持特定用户的定制价格';
COMMENT ON COLUMN user_price_overrides.override_price_cents IS '用户专属价格 (美分): 1990 = $19.9';
COMMENT ON COLUMN user_price_overrides.valid_until IS 'NULL = 永久有效, 否则到期后失效';

-- ============================================================================
-- Triggers: Auto-update updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER pricing_plans_updated_at
    BEFORE UPDATE ON pricing_plans
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER user_price_overrides_updated_at
    BEFORE UPDATE ON user_price_overrides
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Function: Log pricing_plan changes to pricing_history
-- ============================================================================

CREATE OR REPLACE FUNCTION log_pricing_plan_change()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        INSERT INTO pricing_history (
            pricing_plan_id, action, new_price_cents, change_reason, changed_by, snapshot
        ) VALUES (
            NEW.id,
            'create',
            NEW.price_cents,
            'Initial creation',
            COALESCE(NEW.created_by, 'system'),
            row_to_json(NEW)::jsonb
        );
        RETURN NEW;

    ELSIF (TG_OP = 'UPDATE') THEN
        -- Price change
        IF (OLD.price_cents IS DISTINCT FROM NEW.price_cents) THEN
            INSERT INTO pricing_history (
                pricing_plan_id, action, old_price_cents, new_price_cents, change_reason, changed_by, snapshot
            ) VALUES (
                NEW.id,
                'update_price',
                OLD.price_cents,
                NEW.price_cents,
                'Price updated',
                COALESCE(NEW.updated_by, 'system'),
                row_to_json(NEW)::jsonb
            );
        END IF;

        -- Activation status change
        IF (OLD.is_active IS DISTINCT FROM NEW.is_active) THEN
            INSERT INTO pricing_history (
                pricing_plan_id, action, change_reason, changed_by, snapshot
            ) VALUES (
                NEW.id,
                CASE WHEN NEW.is_active THEN 'reactivate' ELSE 'deactivate' END,
                CASE WHEN NEW.is_active THEN 'Plan reactivated' ELSE 'Plan deactivated' END,
                COALESCE(NEW.updated_by, 'system'),
                row_to_json(NEW)::jsonb
            );
        END IF;

        -- Metadata change
        IF (OLD.metadata IS DISTINCT FROM NEW.metadata) THEN
            INSERT INTO pricing_history (
                pricing_plan_id, action, change_reason, changed_by, snapshot
            ) VALUES (
                NEW.id,
                'update_metadata',
                'Metadata updated',
                COALESCE(NEW.updated_by, 'system'),
                row_to_json(NEW)::jsonb
            );
        END IF;

        RETURN NEW;

    ELSIF (TG_OP = 'DELETE') THEN
        INSERT INTO pricing_history (
            pricing_plan_id, action, change_reason, changed_by, snapshot
        ) VALUES (
            OLD.id,
            'delete',
            'Plan deleted',
            COALESCE(OLD.updated_by, 'system'),
            row_to_json(OLD)::jsonb
        );
        RETURN OLD;
    END IF;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER pricing_plans_audit_trigger
    AFTER INSERT OR UPDATE OR DELETE ON pricing_plans
    FOR EACH ROW
    EXECUTE FUNCTION log_pricing_plan_change();

-- ============================================================================
-- Verification
-- ============================================================================

DO $$
DECLARE
    v_table_count INT;
BEGIN
    -- Check tables created
    SELECT COUNT(*) INTO v_table_count
    FROM information_schema.tables
    WHERE table_name IN ('pricing_plans', 'pricing_history', 'user_price_overrides');

    RAISE NOTICE '✅ Created % pricing tables', v_table_count;

    IF v_table_count = 3 THEN
        RAISE NOTICE '✅ Pricing System Migration Successful';
    ELSE
        RAISE WARNING '⚠️ Expected 3 tables, found %', v_table_count;
    END IF;
END $$;

COMMIT;

-- ============================================================================
-- Rollback Script (保存为单独文件: 003_rollback_pricing_tables.sql)
-- ============================================================================
/*
BEGIN;

DROP TRIGGER IF EXISTS pricing_plans_audit_trigger ON pricing_plans CASCADE;
DROP TRIGGER IF EXISTS pricing_plans_updated_at ON pricing_plans CASCADE;
DROP TRIGGER IF EXISTS user_price_overrides_updated_at ON user_price_overrides CASCADE;

DROP FUNCTION IF EXISTS log_pricing_plan_change() CASCADE;
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;

DROP TABLE IF EXISTS user_price_overrides CASCADE;
DROP TABLE IF EXISTS pricing_history CASCADE;
DROP TABLE IF EXISTS pricing_plans CASCADE;

COMMIT;
*/
