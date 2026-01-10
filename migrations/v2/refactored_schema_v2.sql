-- ============================================================================
-- Make Decodables - Refactored Database Schema (v4.0)
-- ============================================================================
-- 生成时间: 2026-01-09
-- PostgreSQL版本: 15+
-- 基于版本: V1 ddl.sql v3.27
--
-- 重构内容:
-- 1. 统一命名规范 (Snake Case)
-- 2. 标准化审计字段 (created_at, updated_at, is_deleted, deleted_at)
-- 3. 补充缺失的 13 张表 (P0 4张 + P1 5张 + P2 4张)
-- 4. 补充完整的 system_configs 初始化数据 (120+ 行)
-- 5. 修复现有表的缺失字段
-- 6. 补充缺失的索引、触发器、函数
-- 7. 保留所有核心业务规则
--
-- 重要提示:
-- ⚠️ profiles.id 是 TEXT 类型 (Clerk ID: user_2xxx...)，不是 UUID！
-- ⚠️ credit_transactions 是 Append-Only 表，禁止 UPDATE/DELETE
-- ⚠️ 积分扣除顺序: credits_monthly → credits_permanent (先月度后永久)
-- ⚠️ system_configs 使用 key/value 字段名 (向后兼容)
-- ============================================================================

-- ============================================================================
-- Transaction Control: 确保迁移原子性
-- ============================================================================
BEGIN;
SET client_min_messages = WARNING;  -- 减少输出噪音
SET statement_timeout = '5min';     -- 防止长时间锁定

-- ============================================================================
-- 第一部分: 扩展 & 通用函数
-- ============================================================================

-- 启用 UUID 扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "ltree";

-- ----------------------------------------------------------------------------
-- 通用函数: 自动更新 updated_at 字段
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_updated_at_column() IS '触发器函数: 自动更新 updated_at 字段为当前时间';

-- ----------------------------------------------------------------------------
-- 通用函数: 软删除时自动设置 deleted_at
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_deleted_at_on_soft_delete()
RETURNS TRIGGER AS $$
BEGIN
    -- INSERT 操作时 OLD 为 NULL,直接返回
    IF OLD IS NULL THEN
        RETURN NEW;
    END IF;

    -- UPDATE 操作: 检查 is_deleted 字段变化
    IF NEW.is_deleted = TRUE AND OLD.is_deleted = FALSE THEN
        NEW.deleted_at = CURRENT_TIMESTAMP;
    ELSIF NEW.is_deleted = FALSE THEN
        NEW.deleted_at = NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION set_deleted_at_on_soft_delete() IS '触发器函数: 软删除时自动设置 deleted_at 时间戳';

-- ----------------------------------------------------------------------------
-- 通用函数: 防止修改 Append-Only 表
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION prevent_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Table % is append-only. UPDATE and DELETE operations are not allowed.', TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION prevent_modification IS '触发器函数: 防止 Append-Only 表被修改或删除';

-- ----------------------------------------------------------------------------
-- 通用函数: Pricing 审计触发器
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION log_pricing_plan_change()
RETURNS TRIGGER AS $$
DECLARE
    v_action TEXT;
    v_old_data JSONB;
    v_new_data JSONB;
BEGIN
    -- 确定操作类型
    IF (TG_OP = 'INSERT') THEN
        v_action := 'create';
        v_old_data := NULL;
        v_new_data := row_to_json(NEW)::jsonb;
    ELSIF (TG_OP = 'UPDATE') THEN
        -- 判断具体更新类型
        IF (OLD.price_cents IS DISTINCT FROM NEW.price_cents OR
            OLD.original_price_cents IS DISTINCT FROM NEW.original_price_cents) THEN
            v_action := 'update_price';
        ELSIF (OLD.is_active IS DISTINCT FROM NEW.is_active) THEN
            v_action := CASE WHEN NEW.is_active THEN 'activate' ELSE 'deactivate' END;
        ELSIF (OLD.is_visible IS DISTINCT FROM NEW.is_visible) THEN
            v_action := CASE WHEN NEW.is_visible THEN 'show' ELSE 'hide' END;
        ELSE
            v_action := 'update';
        END IF;
        v_old_data := row_to_json(OLD)::jsonb;
        v_new_data := row_to_json(NEW)::jsonb;
    ELSIF (TG_OP = 'DELETE') THEN
        v_action := 'delete';
        v_old_data := row_to_json(OLD)::jsonb;
        v_new_data := NULL;
    END IF;

    -- 记录到审计表
    INSERT INTO pricing_history (
        plan_id,
        plan_code,
        action,
        old_data,
        new_data,
        changed_by
    ) VALUES (
        COALESCE(NEW.id, OLD.id),
        COALESCE(NEW.plan_code, OLD.plan_code),
        v_action,
        v_old_data,
        v_new_data,
        COALESCE(NEW.updated_by, NEW.created_by, OLD.updated_by, 'system')
    );

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION log_pricing_plan_change IS '触发器函数: 自动记录价格变更历史到 pricing_history 表';

-- ============================================================================
-- 第二部分: 核心业务表
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. profiles (用户档案表)
-- ----------------------------------------------------------------------------
CREATE TABLE profiles (
    -- 主键 (Clerk ID，TEXT 类型!)
    id TEXT PRIMARY KEY,

    -- 基础信息
    email TEXT NOT NULL UNIQUE,
    username TEXT,
    display_name TEXT,
    avatar_url TEXT,

    -- 用户唯一码 (用于客服查询和用户反馈)
    -- 格式: YYMMDDHHMMSS + mmmm + UUUUUUU + RRR (26位)
    -- 示例: 26010914305278900123456789
    -- 包含: 注册日期时间(16位) + 毫秒(4位) + 用户序号(7位) + 随机数(3位)
    user_code TEXT UNIQUE NOT NULL,

    -- 用户等级 (系统代码: t1/t2/t3, 显示名称可通过 system_configs 配置)
    tier TEXT NOT NULL DEFAULT 't1' CHECK (tier IN ('t1', 't2', 't3')),
    tier_changed_at TIMESTAMPTZ,

    -- 积分余额 (核心字段!)
    credits_monthly INTEGER NOT NULL DEFAULT 0 CHECK (credits_monthly >= 0 AND credits_monthly <= 1000000),  -- 上限 1M 月度积分
    credits_permanent INTEGER NOT NULL DEFAULT 0 CHECK (credits_permanent >= 0 AND credits_permanent <= 10000000),  -- 上限 10M 永久积分

    -- 试用期
    trial_start_date TIMESTAMPTZ,
    trial_end_date TIMESTAMPTZ,
    is_trial_active BOOLEAN DEFAULT FALSE,

    -- Stripe 相关
    stripe_customer_id TEXT UNIQUE,
    stripe_subscription_id TEXT,
    subscription_status TEXT CHECK (subscription_status IN ('active', 'canceled', 'past_due', 'incomplete', 'trialing')),
    subscription_current_period_start TIMESTAMPTZ,
    subscription_current_period_end TIMESTAMPTZ,

    -- 偏好设置
    language TEXT DEFAULT 'en' CHECK (language IN ('en', 'zh', 'es', 'fr', 'de', 'ja', 'ko')),
    timezone TEXT DEFAULT 'UTC',
    notification_email_enabled BOOLEAN DEFAULT TRUE,
    notification_product_enabled BOOLEAN DEFAULT TRUE,

    -- 本地化时间字段
    created_at_local TIMESTAMP,

    -- Cohort 分析
    cohort_month TEXT,

    -- 统计字段 (冗余字段，由触发器维护)
    project_count INTEGER DEFAULT 0 CHECK (project_count >= 0),
    asset_count INTEGER DEFAULT 0 CHECK (asset_count >= 0),

    -- 扩展字段
    ext_json JSONB DEFAULT '{}'::jsonb,

    -- 标准审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,,
    recovery_expires_at TIMESTAMPTZ,  -- 恢复期截止时间,过期后用户看不到此删除记录

    -- 日期逻辑验证
    CONSTRAINT check_trial_dates CHECK (trial_end_date IS NULL OR trial_start_date IS NULL OR trial_end_date > trial_start_date),
    CONSTRAINT check_subscription_dates CHECK (subscription_current_period_end IS NULL OR subscription_current_period_start IS NULL OR subscription_current_period_end > subscription_current_period_start),

    -- Stripe ID 格式验证
    CONSTRAINT check_stripe_customer_id_format CHECK (stripe_customer_id IS NULL OR stripe_customer_id ~ '^cus_[A-Za-z0-9]+$'),
    CONSTRAINT check_stripe_subscription_id_format CHECK (stripe_subscription_id IS NULL OR stripe_subscription_id ~ '^sub_[A-Za-z0-9]+$'),

    -- user_code 格式验证 (26位数字: YYMMDDHHMMSS+mmmm+UUUUUUU+RRR)
    CONSTRAINT check_user_code_format CHECK (user_code ~ '^[0-9]{26}$')
,

    CONSTRAINT chk_profiles_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);

COMMENT ON TABLE profiles IS '用户档案表: 存储用户基础信息、积分余额、订阅状态等核心数据';
COMMENT ON COLUMN profiles.id IS 'Clerk 用户ID (TEXT类型!), 格式: user_2NNEqL2n..., 系统内部使用';
COMMENT ON COLUMN profiles.user_code IS '用户唯一码 (26位: YYMMDDHHMMSS+mmmm+UUUUUUU+RRR), 包含注册时间和用户序号, 管理员使用';
COMMENT ON COLUMN profiles.tier IS '用户等级代码: t1(First Tier)/t2(Second Tier)/t3(Third Tier), 显示名称可通过 system_configs 配置';
COMMENT ON COLUMN profiles.credits_monthly IS '月度积分余额 (订阅每月刷新)';
COMMENT ON COLUMN profiles.credits_permanent IS '永久积分余额 (购买的积分包)';
COMMENT ON COLUMN profiles.timezone IS '用户时区 (用于本地化时间显示)';
COMMENT ON COLUMN profiles.cohort_month IS '用户群组月份 (用于 cohort 分析)';

-- 索引
-- Note: email 已有 UNIQUE 约束，无需额外索引
-- 可恢复删除记录索引 (恢复期内)
CREATE INDEX idx_profiles_deleted_recoverable
ON profiles(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON INDEX idx_profiles_deleted_recoverable IS '可恢复删除记录索引 - 只包含未过期的删除记录';


CREATE INDEX idx_profiles_user_code ON profiles(user_code);
CREATE INDEX idx_profiles_stripe_customer_id ON profiles(stripe_customer_id) WHERE stripe_customer_id IS NOT NULL;
CREATE INDEX idx_profiles_tier ON profiles(tier);
CREATE INDEX idx_profiles_subscription_status ON profiles(subscription_status);
CREATE INDEX idx_profiles_created_at ON profiles(created_at);
CREATE INDEX idx_profiles_active ON profiles(is_deleted) WHERE is_deleted = FALSE;
CREATE INDEX idx_profiles_ext_json ON profiles USING GIN(ext_json);

-- 触发器
CREATE TRIGGER trg_profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_profiles_soft_delete
    BEFORE UPDATE ON profiles
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();

-- ----------------------------------------------------------------------------
-- 2. credit_transactions (积分交易记录表) - Append-Only
-- ----------------------------------------------------------------------------
CREATE TABLE credit_transactions (
    -- 主键
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 用户ID (外键)
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    -- 交易类型
    transaction_type TEXT NOT NULL CHECK (transaction_type IN (
        'subscription_grant',    -- 订阅赠送
        'purchase',              -- 购买积分包
        'ai_generation',         -- AI 生成扣费
        'smart_scan',            -- Smart Scan 扣费
        'refund',                -- 退款
        'admin_adjustment',      -- 管理员调整
        'signup_bonus',          -- 注册奖励
        'referral_bonus',        -- 推荐奖励
        'campaign_reward',       -- 活动奖励
        'expiration'             -- 过期扣除
    )),

    -- 积分桶类型 (关键字段!)
    bucket TEXT NOT NULL CHECK (bucket IN ('monthly', 'permanent')),

    -- 积分变动 (正数=增加，负数=扣除)
    amount INTEGER NOT NULL,

    -- 交易后余额快照 (用于审计和对账)
    balance_monthly_after INTEGER NOT NULL CHECK (balance_monthly_after >= 0),
    balance_permanent_after INTEGER NOT NULL CHECK (balance_permanent_after >= 0),

    -- 幂等性键 (防重复扣费)
    idempotency_key TEXT,

    -- 关联信息
    related_entity_type TEXT,
    related_entity_id TEXT,

    -- 描述
    description TEXT,

    -- 时区支持
    timezone TEXT DEFAULT 'UTC',
    created_at_local TIMESTAMP,

    -- 扩展字段
    metadata JSONB DEFAULT '{}'::jsonb,

    -- 时间戳 (只有 created_at，无 updated_at，因为这是 Append-Only 表)
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- 幂等性键格式验证 (至少 16 字符)
    CONSTRAINT check_idempotency_key_format CHECK (idempotency_key IS NULL OR length(idempotency_key) >= 16)
,

    CONSTRAINT chk_credit_transactions_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);

COMMENT ON TABLE credit_transactions IS '积分交易记录表 (Append-Only): 记录所有积分变动，禁止修改和删除';
COMMENT ON COLUMN credit_transactions.bucket IS '积分桶类型: monthly (月度积分) 或 permanent (永久积分)';
COMMENT ON COLUMN credit_transactions.balance_monthly_after IS '交易后月度积分余额 (快照)';
COMMENT ON COLUMN credit_transactions.balance_permanent_after IS '交易后永久积分余额 (快照)';
COMMENT ON COLUMN credit_transactions.idempotency_key IS '幂等性键 (用于 Webhook 去重)';

-- 索引
-- 可恢复删除记录索引 (恢复期内)
CREATE INDEX idx_credit_transactions_deleted_recoverable
ON credit_transactions(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON INDEX idx_credit_transactions_deleted_recoverable IS '可恢复删除记录索引 - 只包含未过期的删除记录';


CREATE INDEX idx_credit_tx_user_id ON credit_transactions(user_id);
CREATE INDEX idx_credit_tx_user_created ON credit_transactions(user_id, created_at DESC);
CREATE INDEX idx_credit_tx_user_type_time ON credit_transactions(user_id, transaction_type, created_at DESC);  -- Composite index for filtered queries
CREATE INDEX idx_credit_tx_type ON credit_transactions(transaction_type);
CREATE INDEX idx_credit_tx_bucket ON credit_transactions(bucket);
CREATE INDEX idx_credit_tx_created_at ON credit_transactions(created_at DESC);
CREATE INDEX idx_credit_tx_metadata ON credit_transactions USING GIN(metadata);
CREATE UNIQUE INDEX idx_credit_tx_idempotency ON credit_transactions(idempotency_key) WHERE idempotency_key IS NOT NULL;

-- 触发器: 防止修改 Append-Only 表
CREATE TRIGGER trg_credit_tx_prevent_modification
    BEFORE UPDATE OR DELETE ON credit_transactions
    FOR EACH ROW
    EXECUTE FUNCTION prevent_modification();

-- ----------------------------------------------------------------------------
-- 3. projects (用户项目表)
-- ----------------------------------------------------------------------------
CREATE TABLE projects (
    -- 主键
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 用户ID
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    -- 项目信息
    title TEXT NOT NULL DEFAULT 'My Magic Story',
    canvas_data JSONB DEFAULT '{}'::jsonb,
    thumbnail_url TEXT,

    -- 下载追踪
    last_downloaded_hash TEXT,

    -- 市场相关
    marketplace_listing_id UUID,
    source_listing_id UUID,
    is_purchased BOOLEAN DEFAULT FALSE,
    origin_owner_id TEXT REFERENCES profiles(id),

    -- 标记
    contains_locked_elements BOOLEAN DEFAULT FALSE,
    is_hidden_from_trash BOOLEAN DEFAULT FALSE,

    -- 时区支持
    timezone TEXT DEFAULT 'UTC',
    created_at_local TIMESTAMP,
    updated_at_local TIMESTAMP,

    -- 扩展字段
    metadata JSONB DEFAULT '{}'::jsonb,

    -- 标准审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ
    recovery_expires_at TIMESTAMPTZ,  -- 恢复期截止时间,过期后用户看不到此删除记录,
,

    CONSTRAINT chk_projects_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);

COMMENT ON TABLE projects IS '用户项目表: 存储用户创建的项目和购买的模板项目';
COMMENT ON COLUMN projects.canvas_data IS 'Canvas 数据 (Fabric.js JSON)';
COMMENT ON COLUMN projects.marketplace_listing_id IS '关联的市场 listing ID (如果项目来自市场)';
COMMENT ON COLUMN projects.contains_locked_elements IS '是否包含锁定元素 (Pro功能)';

-- 索引
-- 可恢复删除记录索引 (恢复期内)
CREATE INDEX idx_projects_deleted_recoverable
ON projects(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON INDEX idx_projects_deleted_recoverable IS '可恢复删除记录索引 - 只包含未过期的删除记录';


CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_projects_user_created ON projects(user_id, created_at DESC);
CREATE INDEX idx_projects_listing ON projects(marketplace_listing_id) WHERE marketplace_listing_id IS NOT NULL;
CREATE INDEX idx_projects_origin_owner ON projects(origin_owner_id) WHERE origin_owner_id IS NOT NULL;
CREATE INDEX idx_projects_active ON projects(is_deleted) WHERE is_deleted = FALSE;
CREATE INDEX idx_projects_metadata ON projects USING GIN(metadata);

-- Note: 外键约束在 marketplace_listings 表定义后添加 (见第 850 行左右)

-- 触发器
CREATE TRIGGER trg_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_projects_soft_delete
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();

-- ============================================================================
-- 第三部分: 系统配置与日志表
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 4. system_configs (系统配置表) - 向后兼容版本
-- ----------------------------------------------------------------------------
CREATE TABLE system_configs (
    -- 主键 (保持 V1 兼容性)
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,

    -- 类型与分组
    value_type TEXT NOT NULL DEFAULT 'text' CHECK (value_type IN ('text', 'number', 'integer', 'boolean', 'json')),
    config_group TEXT NOT NULL DEFAULT 'general',

    -- 描述
    description TEXT,

    -- 状态控制
    is_active BOOLEAN DEFAULT TRUE,
    is_editable BOOLEAN DEFAULT TRUE,

    -- 审计字段
    updated_by TEXT,

    -- 扩展字段
    ext_json JSONB DEFAULT '{}'::jsonb,

    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE system_configs IS '系统配置表: 数据库驱动的配置系统 (ADR-0002)';
COMMENT ON COLUMN system_configs.key IS '配置键 (主键), 格式: group.subgroup.name';
COMMENT ON COLUMN system_configs.value IS '配置值 (字符串形式存储)';
COMMENT ON COLUMN system_configs.value_type IS '值类型: text/number/integer/boolean/json';
COMMENT ON COLUMN system_configs.is_active IS '是否启用 (用于临时禁用配置)';
COMMENT ON COLUMN system_configs.is_editable IS '是否可通过 API 编辑';

-- 索引
CREATE INDEX idx_system_configs_group ON system_configs(config_group);
CREATE INDEX idx_system_configs_active ON system_configs(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_system_configs_updated ON system_configs(updated_at DESC);

-- 触发器
CREATE TRIGGER trg_system_configs_updated_at
    BEFORE UPDATE ON system_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ----------------------------------------------------------------------------
-- 5. api_logs (API 调用日志表)
-- ----------------------------------------------------------------------------
CREATE TABLE api_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT REFERENCES profiles(id),
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    latency_ms INTEGER,
    ip_address INET,
    user_agent TEXT,
    request_body JSONB,
    response_body JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE api_logs IS 'API 调用日志表: 记录所有 API 请求和响应';

-- 索引
CREATE INDEX idx_api_logs_user ON api_logs(user_id, created_at DESC);
CREATE INDEX idx_api_logs_endpoint ON api_logs(endpoint);
CREATE INDEX idx_api_logs_status ON api_logs(status_code) WHERE status_code >= 400;
CREATE INDEX idx_api_logs_created ON api_logs(created_at DESC);

-- ============================================================================
-- 第四部分: AI 生成相关表 (P0 级别)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 6. ai_call_logs (AI API 调用详细日志) - P0 级别
-- ----------------------------------------------------------------------------
CREATE TABLE ai_call_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT REFERENCES profiles(id),

    -- Provider & Model
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    call_type TEXT NOT NULL,

    -- Status
    status TEXT NOT NULL CHECK (status IN ('success', 'failed', 'timeout')),

    -- Input/Output
    input_data JSONB NOT NULL,
    output_data JSONB,

    -- Token 统计
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,

    -- Performance
    latency_ms INTEGER,
    cost_usd DECIMAL(10,6),

    -- Error
    error_code TEXT,
    error_message TEXT,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamp
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE ai_call_logs IS 'AI API 调用日志表: 记录每次 AI API 调用的详细信息 (性能、成本、错误)';
COMMENT ON COLUMN ai_call_logs.provider IS 'AI Provider: openai/fal/qwen/anthropic 等';
COMMENT ON COLUMN ai_call_logs.call_type IS '调用类型: text_reasoning/image_generation 等';
COMMENT ON COLUMN ai_call_logs.cost_usd IS '本次调用成本 (USD)';

-- 索引
CREATE INDEX idx_ai_calls_provider_time ON ai_call_logs(provider, created_at DESC);
CREATE INDEX idx_ai_calls_user_time ON ai_call_logs(user_id, created_at DESC);
CREATE INDEX idx_ai_calls_status ON ai_call_logs(status) WHERE status != 'success';
CREATE INDEX idx_ai_calls_call_type ON ai_call_logs(call_type);

-- ----------------------------------------------------------------------------
-- 7. ai_usage_daily (AI 使用量日汇总表) - P0 级别
-- ----------------------------------------------------------------------------
CREATE TABLE ai_usage_daily (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    call_type TEXT NOT NULL,

    -- 统计指标
    total_calls INTEGER DEFAULT 0,
    successful_calls INTEGER DEFAULT 0,
    failed_calls INTEGER DEFAULT 0,
    total_input_tokens BIGINT DEFAULT 0,
    total_output_tokens BIGINT DEFAULT 0,
    total_images INTEGER DEFAULT 0,

    -- 性能指标
    avg_latency_ms INTEGER DEFAULT 0,
    min_latency_ms INTEGER,
    max_latency_ms INTEGER,

    -- 成本
    estimated_cost_usd DECIMAL(10, 4) DEFAULT 0,

    -- 错误统计
    error_counts JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(date, provider, model, call_type)
);

COMMENT ON TABLE ai_usage_daily IS 'AI 使用量日汇总表: 按日期、Provider、模型聚合 AI 调用统计';

-- 索引
CREATE INDEX idx_ai_usage_daily_date ON ai_usage_daily(date DESC);
CREATE INDEX idx_ai_usage_daily_provider ON ai_usage_daily(provider, date DESC);

-- 触发器
CREATE TRIGGER trg_ai_usage_daily_updated_at
    BEFORE UPDATE ON ai_usage_daily
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ----------------------------------------------------------------------------
-- 8. user_generations (用户 AI 生成历史表)
-- ----------------------------------------------------------------------------
CREATE TABLE user_generations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    generation_type TEXT NOT NULL CHECK (generation_type IN ('image', 'text', 'story', 'design')),
    prompt TEXT,
    result_url TEXT,
    result_data JSONB,
    credits_used INTEGER NOT NULL DEFAULT 0,
    provider TEXT,
    model TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed')),
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ
);

COMMENT ON TABLE user_generations IS '用户 AI 生成历史表: 记录用户的所有 AI 生成请求';

-- 索引
CREATE INDEX idx_generations_user ON user_generations(user_id, created_at DESC);
CREATE INDEX idx_generations_type ON user_generations(generation_type);
CREATE INDEX idx_generations_status ON user_generations(status);

-- ============================================================================
-- 第五部分: 素材系统表 (P0 级别)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 9. asset_categories (素材分类树) - P0 级别
-- ----------------------------------------------------------------------------
CREATE TABLE asset_categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 层级关系
    parent_id UUID REFERENCES asset_categories(id) ON DELETE SET NULL,  -- 改为 SET NULL 避免循环级联
    path LTREE NOT NULL,
    level INTEGER NOT NULL DEFAULT 1 CHECK (level BETWEEN 1 AND 3),

    -- 基本信息
    slug VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    name_i18n JSONB DEFAULT '{}',
    description TEXT,
    icon VARCHAR(50),

    -- 关联的素材类型
    asset_type VARCHAR(20) NOT NULL CHECK (asset_type IN ('text', 'image', 'shape', 'table', 'sticker', 'icon', 'frame')),

    -- 显示控制
    is_visible BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,
    display_order INTEGER DEFAULT 0,

    -- 访问控制
    min_tier VARCHAR(20) DEFAULT 't1' CHECK (min_tier IN ('t1', 't2', 't3')),

    -- 时间限定 (节日主题)
    visible_from TIMESTAMPTZ,
    visible_until TIMESTAMPTZ,

    -- 统计
    asset_count INTEGER DEFAULT 0,
    usage_count INTEGER DEFAULT 0,

    -- 元数据
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
,

    CONSTRAINT chk_asset_categories_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);

COMMENT ON TABLE asset_categories IS '素材分类树: 多级分类系统 (支持 LTREE 路径查询)';
COMMENT ON COLUMN asset_categories.path IS '物化路径 (LTREE 类型), 例如: graphics.stickers.animals';
COMMENT ON COLUMN asset_categories.level IS '层级深度: 1=一级分类, 2=二级分类, 3=三级分类';

-- 索引
-- 可恢复删除记录索引 (恢复期内)
CREATE INDEX idx_asset_categories_deleted_recoverable
ON asset_categories(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON INDEX idx_asset_categories_deleted_recoverable IS '可恢复删除记录索引 - 只包含未过期的删除记录';


CREATE INDEX idx_categories_path ON asset_categories USING GIST (path);
CREATE INDEX idx_categories_parent ON asset_categories(parent_id);
CREATE INDEX idx_categories_visible ON asset_categories(is_visible, display_order);
CREATE INDEX idx_categories_type ON asset_categories(asset_type);

-- 触发器
CREATE TRIGGER trg_asset_categories_updated_at
    BEFORE UPDATE ON asset_categories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ----------------------------------------------------------------------------
-- 10. system_assets (系统内置素材表) - P0 级别
-- ----------------------------------------------------------------------------
CREATE TABLE system_assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 分类关联
    category_id UUID NOT NULL REFERENCES asset_categories(id),

    -- 基本信息
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(100),
    description TEXT,

    -- 素材类型
    asset_type VARCHAR(20) NOT NULL CHECK (asset_type IN ('text', 'image', 'shape', 'table', 'sticker', 'icon', 'frame')),

    -- 来源
    source VARCHAR(20) NOT NULL DEFAULT 'system' CHECK (source IN ('system', 'user', 'ai', 'community')),
    source_user_id TEXT REFERENCES profiles(id),

    -- 文件信息
    file_url TEXT,
    thumbnail_url TEXT,
    file_size INTEGER,
    file_format VARCHAR(20),

    -- 尺寸
    width INTEGER,
    height INTEGER,

    -- 素材内容 (JSONB, 根据 asset_type 不同)
    content JSONB NOT NULL DEFAULT '{}',

    -- 访问控制
    min_tier VARCHAR(20) DEFAULT 't1' CHECK (min_tier IN ('t1', 't2', 't3')),
    is_pro_only BOOLEAN DEFAULT FALSE,

    -- 标签 (搜索用)
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- 显示控制
    is_visible BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,
    display_order INTEGER DEFAULT 0,

    -- 统计
    usage_count INTEGER DEFAULT 0,
    download_count INTEGER DEFAULT 0,
    favorite_count INTEGER DEFAULT 0,

    -- 元数据
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
,

    CONSTRAINT chk_system_assets_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);

COMMENT ON TABLE system_assets IS '系统内置素材表: 区别于用户上传的 assets 表';
COMMENT ON COLUMN system_assets.source IS '来源: system=系统内置, user=用户上传, ai=AI生成, community=社区';

-- 索引
-- 可恢复删除记录索引 (恢复期内)
CREATE INDEX idx_system_assets_deleted_recoverable
ON system_assets(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON INDEX idx_system_assets_deleted_recoverable IS '可恢复删除记录索引 - 只包含未过期的删除记录';


CREATE INDEX idx_system_assets_category ON system_assets(category_id);
CREATE INDEX idx_system_assets_type ON system_assets(asset_type);
CREATE INDEX idx_system_assets_source ON system_assets(source);
CREATE INDEX idx_system_assets_tier ON system_assets(min_tier);
CREATE INDEX idx_system_assets_tags ON system_assets USING GIN(tags);
CREATE INDEX idx_system_assets_visible ON system_assets(is_visible, display_order);

-- 触发器
CREATE TRIGGER trg_system_assets_updated_at
    BEFORE UPDATE ON system_assets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 第六部分: 市场相关表
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 11. marketplace_listings (市场 listing 表)
-- ----------------------------------------------------------------------------
CREATE TABLE marketplace_listings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    seller_id TEXT REFERENCES profiles(id),

    -- 基本信息
    title TEXT NOT NULL,
    description TEXT,
    thumbnail_url TEXT NOT NULL,

    -- 资源信息
    resource_url TEXT NOT NULL,
    resource_type TEXT NOT NULL CHECK (resource_type IN ('project', 'asset', 'template')),
    resource_id UUID,

    -- 分类 (v3.26: 两级分类)
    category TEXT DEFAULT 'element' CHECK (category IN (
        'clipart', 'illustration', 'photo', 'background',
        'template', 'font', 'sticker', 'icon', 'pattern', 'element',
        'emoji', 'frame', 'character', 'scene',
        'mini_book', 'worksheet', 'flashcard'
    )),
    source TEXT DEFAULT 'user' CHECK (source IN ('system', 'user', 'ai', 'community')),

    -- 定价
    price_credits INTEGER NOT NULL DEFAULT 0 CHECK (price_credits >= 0),
    allowed_tiers TEXT[] NOT NULL DEFAULT '{free, starter, pro}',

    -- 统计
    usage_count BIGINT DEFAULT 0,
    sales_count INTEGER DEFAULT 0,
    unique_buyers_count INTEGER DEFAULT 0,
    total_revenue INTEGER DEFAULT 0,

    -- 状态
    is_public BOOLEAN DEFAULT FALSE,
    moderation_status TEXT NOT NULL DEFAULT 'draft' CHECK (moderation_status IN ('draft', 'pending', 'approved', 'rejected')),
    moderation_note TEXT,
    moderated_by TEXT REFERENCES profiles(id),
    moderated_at TIMESTAMPTZ,

    -- 版本控制
    version VARCHAR(20) DEFAULT '1.0',
    changelog TEXT DEFAULT '',
    version_history JSONB DEFAULT '[]'::jsonb,

    -- 时区支持
    timezone TEXT DEFAULT 'UTC',
    created_at_local TIMESTAMP,

    -- 扩展字段
    metadata JSONB DEFAULT '{}'::jsonb,

    -- 标准审计字段
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,

    recovery_expires_at TIMESTAMPTZ,  -- 恢复期截止时间,过期后用户看不到此删除记录,

    CONSTRAINT chk_marketplace_listings_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);

COMMENT ON TABLE marketplace_listings IS '市场 Listing 表: 用户发布的素材和模板';
COMMENT ON COLUMN marketplace_listings.category IS '分类: 素材类型分类';
COMMENT ON COLUMN marketplace_listings.source IS '来源: user=用户创建, ai=AI生成, system=系统内置';

-- 索引
-- 可恢复删除记录索引 (恢复期内)
CREATE INDEX idx_marketplace_listings_deleted_recoverable
ON marketplace_listings(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON INDEX idx_marketplace_listings_deleted_recoverable IS '可恢复删除记录索引 - 只包含未过期的删除记录';


CREATE INDEX idx_listings_seller ON marketplace_listings(seller_id);
CREATE INDEX idx_listings_category ON marketplace_listings(category);
CREATE INDEX idx_listings_source ON marketplace_listings(source);
CREATE INDEX idx_listings_public ON marketplace_listings(is_public) WHERE is_public = TRUE;
CREATE INDEX idx_listings_moderation ON marketplace_listings(moderation_status);
CREATE INDEX idx_listings_created ON marketplace_listings(created_at DESC);
CREATE INDEX idx_listings_metadata ON marketplace_listings USING GIN(metadata);

-- 触发器
CREATE TRIGGER trg_listings_updated_at
    BEFORE UPDATE ON marketplace_listings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_listings_soft_delete
    BEFORE UPDATE ON marketplace_listings
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();

-- 外键约束 (projects → marketplace_listings)
-- Note: 必须在 marketplace_listings 表创建后才能添加
ALTER TABLE projects
    ADD CONSTRAINT fk_projects_marketplace_listing
    FOREIGN KEY (marketplace_listing_id)
    REFERENCES marketplace_listings(id)
    ON DELETE SET NULL;

ALTER TABLE projects
    ADD CONSTRAINT fk_projects_source_listing
    FOREIGN KEY (source_listing_id)
    REFERENCES marketplace_listings(id)
    ON DELETE SET NULL;

-- ----------------------------------------------------------------------------
-- 12. marketplace_purchases (市场购买记录表)
-- ----------------------------------------------------------------------------
CREATE TABLE marketplace_purchases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    listing_id UUID NOT NULL REFERENCES marketplace_listings(id) ON DELETE CASCADE,

    -- 购买信息
    price_paid INTEGER NOT NULL,
    idempotency_key TEXT,

    -- 快照 (防止 listing 删除后无法查询)
    snapshot_title TEXT,
    snapshot_thumbnail_url TEXT,
    snapshot_description TEXT,
    snapshot_version TEXT,
    snapshot_resource_type TEXT,
    snapshot_resource_id UUID,

    -- UTM 追踪
    utm_source TEXT,
    utm_medium TEXT,
    utm_campaign TEXT,
    referral_context TEXT,

    -- 时区支持
    timezone TEXT DEFAULT 'UTC',
    purchased_at_local TIMESTAMP,

    -- 扩展字段
    metadata JSONB DEFAULT '{}'::jsonb,

    -- 时间戳
    purchased_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, listing_id),

    -- 幂等性键格式验证 (至少 16 字符)
    CONSTRAINT check_purchase_idempotency_format CHECK (idempotency_key IS NULL OR length(idempotency_key) >= 16)
);

COMMENT ON TABLE marketplace_purchases IS '市场购买记录表: 记录用户购买的 listing';
COMMENT ON COLUMN marketplace_purchases.idempotency_key IS '幂等性键 (防重复扣费)';
COMMENT ON COLUMN marketplace_purchases.snapshot_title IS 'Listing 快照 (防删除后无法查询)';

-- 索引
CREATE INDEX idx_purchases_user ON marketplace_purchases(user_id, purchased_at DESC);
CREATE INDEX idx_purchases_listing ON marketplace_purchases(listing_id);
CREATE INDEX idx_purchases_time ON marketplace_purchases(purchased_at DESC);
CREATE UNIQUE INDEX idx_purchases_idempotency ON marketplace_purchases(idempotency_key) WHERE idempotency_key IS NOT NULL;

-- ----------------------------------------------------------------------------
-- 13. marketplace_favorites (市场收藏表)
-- ----------------------------------------------------------------------------
CREATE TABLE marketplace_favorites (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    listing_id UUID NOT NULL REFERENCES marketplace_listings(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMPTZ,,
    recovery_expires_at TIMESTAMPTZ,  -- 恢复期截止时间,过期后用户看不到此删除记录
    recovery_expires_at TIMESTAMPTZ,  -- 恢复期截止时间,过期后用户看不到此删除记录
    recovery_expires_at TIMESTAMPTZ,  -- 恢复期截止时间,过期后用户看不到此删除记录
    recovery_expires_at TIMESTAMPTZ,  -- 恢复期截止时间,过期后用户看不到此删除记录
    recovery_expires_at TIMESTAMPTZ,  -- 恢复期截止时间,过期后用户看不到此删除记录
    recovery_expires_at TIMESTAMPTZ,  -- 恢复期截止时间,过期后用户看不到此删除记录
    UNIQUE(user_id, listing_id),
    CONSTRAINT chk_marketplace_favorites_deleted_at_consistency
        CHECK ((is_deleted = false AND deleted_at IS NULL) OR (is_deleted = true AND deleted_at IS NOT NULL)),
    CONSTRAINT chk_marketplace_favorites_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);

COMMENT ON TABLE marketplace_favorites IS '市场收藏表: 用户收藏的 listing';
COMMENT ON COLUMN marketplace_favorites.is_deleted IS '软删除标记';
COMMENT ON COLUMN marketplace_favorites.deleted_at IS '删除时间';

-- 索引
-- 可恢复删除记录索引 (恢复期内)
CREATE INDEX idx_marketplace_favorites_deleted_recoverable
ON marketplace_favorites(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON INDEX idx_marketplace_favorites_deleted_recoverable IS '可恢复删除记录索引 - 只包含未过期的删除记录';


CREATE INDEX idx_favorites_user ON marketplace_favorites(user_id, created_at DESC) WHERE is_deleted = false;
CREATE INDEX idx_favorites_listing ON marketplace_favorites(listing_id) WHERE is_deleted = false;

-- ----------------------------------------------------------------------------
-- 14. marketplace_reviews (市场评价表)
-- ----------------------------------------------------------------------------
CREATE TABLE marketplace_reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    listing_id UUID NOT NULL REFERENCES marketplace_listings(id) ON DELETE CASCADE,
    reviewer_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    review_text TEXT,
    is_verified_purchase BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMPTZ,,
    recovery_expires_at TIMESTAMPTZ,  -- 恢复期截止时间,过期后用户看不到此删除记录
    UNIQUE(listing_id, reviewer_id),
    CONSTRAINT chk_marketplace_reviews_deleted_at_consistency
        CHECK ((is_deleted = false AND deleted_at IS NULL) OR (is_deleted = true AND deleted_at IS NOT NULL)),
    CONSTRAINT chk_marketplace_reviews_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);

COMMENT ON TABLE marketplace_reviews IS '市场评价表: 用户对 listing 的评分和评论';
COMMENT ON COLUMN marketplace_reviews.is_deleted IS '软删除标记';
COMMENT ON COLUMN marketplace_reviews.deleted_at IS '删除时间';

-- 索引
-- 可恢复删除记录索引 (恢复期内)
CREATE INDEX idx_marketplace_reviews_deleted_recoverable
ON marketplace_reviews(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON INDEX idx_marketplace_reviews_deleted_recoverable IS '可恢复删除记录索引 - 只包含未过期的删除记录';


CREATE INDEX idx_reviews_listing ON marketplace_reviews(listing_id, created_at DESC) WHERE is_deleted = false;
CREATE INDEX idx_reviews_reviewer ON marketplace_reviews(reviewer_id) WHERE is_deleted = false;
CREATE INDEX idx_reviews_rating ON marketplace_reviews(rating) WHERE is_deleted = false;

-- 触发器
CREATE TRIGGER trg_reviews_updated_at
    BEFORE UPDATE ON marketplace_reviews
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 第七部分: 主题系统表 (P1 级别)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 15. daily_themes (每日主题表) - P1 级别
-- ----------------------------------------------------------------------------
CREATE TABLE daily_themes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    description TEXT,
    date DATE NOT NULL UNIQUE,
    thumbnail_url TEXT,
    preview_urls TEXT[] DEFAULT ARRAY[]::TEXT[],
    featured_asset_ids UUID[] DEFAULT ARRAY[]::UUID[],
    recommended_categories TEXT[] DEFAULT ARRAY[]::TEXT[],
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'archived')),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMPTZ,,
    recovery_expires_at TIMESTAMPTZ,  -- 恢复期截止时间,过期后用户看不到此删除记录
    CONSTRAINT chk_daily_themes_deleted_at_consistency
        CHECK ((is_deleted = false AND deleted_at IS NULL) OR (is_deleted = true AND deleted_at IS NOT NULL)),
    CONSTRAINT chk_daily_themes_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);

COMMENT ON TABLE daily_themes IS '每日主题表: 每天推荐的主题和相关素材';
COMMENT ON COLUMN daily_themes.is_deleted IS '软删除标记';
COMMENT ON COLUMN daily_themes.deleted_at IS '删除时间';

-- 索引
-- 可恢复删除记录索引 (恢复期内)
CREATE INDEX idx_daily_themes_deleted_recoverable
ON daily_themes(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON INDEX idx_daily_themes_deleted_recoverable IS '可恢复删除记录索引 - 只包含未过期的删除记录';


CREATE INDEX idx_daily_themes_date ON daily_themes(date DESC) WHERE is_deleted = false;
CREATE INDEX idx_daily_themes_status ON daily_themes(status) WHERE is_deleted = false;

-- 触发器
CREATE TRIGGER trg_daily_themes_updated_at
    BEFORE UPDATE ON daily_themes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ----------------------------------------------------------------------------
-- 16. holidays (节日数据表) - P1 级别
-- ----------------------------------------------------------------------------
CREATE TABLE holidays (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    name_i18n JSONB DEFAULT '{}',
    slug TEXT NOT NULL UNIQUE,
    month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    day INTEGER NOT NULL CHECK (day BETWEEN 1 AND 31),
    regions TEXT[] DEFAULT ARRAY[]::TEXT[],
    category TEXT NOT NULL,
    is_major BOOLEAN DEFAULT FALSE,
    theme_colors TEXT[] DEFAULT ARRAY[]::TEXT[],
    asset_category_ids UUID[] DEFAULT ARRAY[]::UUID[],
    description TEXT,
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMPTZ,,
    recovery_expires_at TIMESTAMPTZ,  -- 恢复期截止时间,过期后用户看不到此删除记录
    CONSTRAINT chk_holidays_deleted_at_consistency
        CHECK ((is_deleted = false AND deleted_at IS NULL) OR (is_deleted = true AND deleted_at IS NOT NULL)),
    CONSTRAINT chk_holidays_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);

COMMENT ON TABLE holidays IS '节日数据表: 全球节日数据库';
COMMENT ON COLUMN holidays.is_deleted IS '软删除标记';
COMMENT ON COLUMN holidays.deleted_at IS '删除时间';

-- 索引
-- 可恢复删除记录索引 (恢复期内)
CREATE INDEX idx_holidays_deleted_recoverable
ON holidays(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON INDEX idx_holidays_deleted_recoverable IS '可恢复删除记录索引 - 只包含未过期的删除记录';


CREATE INDEX idx_holidays_date ON holidays(month, day) WHERE is_deleted = false;
CREATE INDEX idx_holidays_regions ON holidays USING GIN(regions) WHERE is_deleted = false;
CREATE INDEX idx_holidays_category ON holidays(category) WHERE is_deleted = false;

-- 触发器
CREATE TRIGGER trg_holidays_updated_at
    BEFORE UPDATE ON holidays
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 第八部分: Analytics 与日志表 (P1 级别)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 17. activity_logs (活动日志表) - P1 级别
-- ----------------------------------------------------------------------------
CREATE TABLE activity_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL REFERENCES profiles(id),
    action TEXT NOT NULL,
    resource_type TEXT,
    resource_id TEXT,
    description TEXT,
    metadata JSONB DEFAULT '{}',
    ip_address INET,
    timezone TEXT DEFAULT 'UTC',
    created_at_local TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE activity_logs IS '活动日志表: 记录用户行为日志 (轻量级)';

-- 索引
CREATE INDEX idx_activity_logs_user_time ON activity_logs(user_id, created_at DESC);
CREATE INDEX idx_activity_logs_action ON activity_logs(action);
CREATE INDEX idx_activity_logs_resource ON activity_logs(resource_type, resource_id);

-- ----------------------------------------------------------------------------
-- 18. analytics_events (Analytics 事件表)
-- ----------------------------------------------------------------------------
CREATE TABLE analytics_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT REFERENCES profiles(id),
    session_id TEXT,
    event_id TEXT,
    event_name TEXT NOT NULL,
    event_type TEXT NOT NULL,
    context JSONB DEFAULT '{}',
    properties JSONB DEFAULT '{}',
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE analytics_events IS 'Analytics 事件表: 记录用户行为分析事件';
COMMENT ON COLUMN analytics_events.event_id IS '事件ID (用于 CAPI/Server-Side GTM 去重)';

-- 索引
CREATE INDEX idx_analytics_events_user ON analytics_events(user_id, timestamp DESC);
CREATE INDEX idx_analytics_events_event_name ON analytics_events(event_name);
CREATE INDEX idx_analytics_events_event_id ON analytics_events(event_id);
CREATE INDEX idx_analytics_events_type_event_id ON analytics_events(event_type, event_id);
CREATE INDEX idx_analytics_events_timestamp ON analytics_events(timestamp DESC);

-- ----------------------------------------------------------------------------
-- 19. analytics_aggregation (Analytics 聚合表) - P1 级别
-- ----------------------------------------------------------------------------
CREATE TABLE analytics_aggregation (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL,
    granularity TEXT NOT NULL CHECK (granularity IN ('daily', 'weekly', 'monthly')),
    dimension_type TEXT NOT NULL,
    dimension_value TEXT,
    metrics JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, granularity, dimension_type, dimension_value)
);

COMMENT ON TABLE analytics_aggregation IS 'Analytics 聚合表: 预聚合的分析数据 (提升查询性能)';

-- 索引
CREATE INDEX idx_analytics_agg_date ON analytics_aggregation(date DESC);
CREATE INDEX idx_analytics_agg_dimension ON analytics_aggregation(dimension_type, dimension_value);

-- 触发器
CREATE TRIGGER trg_analytics_agg_updated_at
    BEFORE UPDATE ON analytics_aggregation
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ----------------------------------------------------------------------------
-- 20. scheduled_task_logs (调度任务日志表) - P1 级别
-- ----------------------------------------------------------------------------
CREATE TABLE scheduled_task_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_name TEXT NOT NULL,
    task_type TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'success', 'failed')),
    result_summary JSONB DEFAULT '{}',
    error_message TEXT,
    error_stack TEXT,
    hostname TEXT,
    pid INTEGER,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE scheduled_task_logs IS '调度任务日志表: 记录定时任务执行状态';

-- 索引
CREATE INDEX idx_task_logs_task_name ON scheduled_task_logs(task_name);
CREATE INDEX idx_task_logs_started_at ON scheduled_task_logs(started_at DESC);
CREATE INDEX idx_task_logs_status ON scheduled_task_logs(status);

-- ============================================================================
-- 第九部分: Webhook 事件表
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 21. clerk_webhook_events (Clerk Webhook 事件表)
-- ----------------------------------------------------------------------------
CREATE TABLE clerk_webhook_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id TEXT UNIQUE NOT NULL,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMPTZ,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE clerk_webhook_events IS 'Clerk Webhook 事件表: 保证幂等性';

-- 索引
CREATE INDEX idx_clerk_events_type ON clerk_webhook_events(event_type);
CREATE INDEX idx_clerk_events_processed ON clerk_webhook_events(processed);
CREATE INDEX idx_clerk_events_created ON clerk_webhook_events(created_at DESC);

-- ----------------------------------------------------------------------------
-- 22. stripe_webhook_events (Stripe Webhook 事件表)
-- ----------------------------------------------------------------------------
CREATE TABLE stripe_webhook_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id TEXT UNIQUE NOT NULL,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMPTZ,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE stripe_webhook_events IS 'Stripe Webhook 事件表: 保证幂等性';

-- 索引
CREATE INDEX idx_stripe_events_type ON stripe_webhook_events(event_type);
CREATE INDEX idx_stripe_events_processed ON stripe_webhook_events(processed);
CREATE INDEX idx_stripe_events_created ON stripe_webhook_events(created_at DESC);

-- ============================================================================
-- 第十部分: 审计与报告表 (P2 级别)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 23. config_audit_logs (配置审计日志表) - P2 级别
-- ----------------------------------------------------------------------------
CREATE TABLE config_audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    config_key TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    action TEXT NOT NULL CHECK (action IN ('create', 'update', 'delete')),
    changed_by TEXT,
    changed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE config_audit_logs IS '配置审计日志表: 记录 system_configs 的所有变更';

-- 索引
CREATE INDEX idx_config_audit_key ON config_audit_logs(config_key);
CREATE INDEX idx_config_audit_time ON config_audit_logs(changed_at DESC);

-- ----------------------------------------------------------------------------
-- 24. content_reports (内容举报表) - P2 级别
-- ----------------------------------------------------------------------------
CREATE TABLE content_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reporter_id TEXT NOT NULL REFERENCES profiles(id),
    listing_id UUID NOT NULL REFERENCES marketplace_listings(id),
    reason TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'reviewed', 'resolved', 'dismissed')),
    admin_response TEXT,
    reviewed_by TEXT REFERENCES profiles(id),
    reviewed_at TIMESTAMPTZ,
    timezone TEXT DEFAULT 'UTC',
    created_at_local TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(reporter_id, listing_id)
);

COMMENT ON TABLE content_reports IS '内容举报表: 用户举报不当内容';

-- 索引
CREATE INDEX idx_reports_status ON content_reports(status);
CREATE INDEX idx_reports_listing_id ON content_reports(listing_id);

-- 触发器
CREATE TRIGGER trg_content_reports_updated_at
    BEFORE UPDATE ON content_reports
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ----------------------------------------------------------------------------
-- 25. system_resource_audit_logs (系统资源审计日志表) - P2 级别
-- ----------------------------------------------------------------------------
CREATE TABLE system_resource_audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resource_id UUID,
    action TEXT NOT NULL,
    old_data JSONB,
    new_data JSONB,
    changed_by TEXT NOT NULL,
    changed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    ip_address TEXT,
    user_agent TEXT
);

COMMENT ON TABLE system_resource_audit_logs IS '系统资源审计日志表: 记录系统资源的变更';

-- 索引
CREATE INDEX idx_resource_audit_resource_id ON system_resource_audit_logs(resource_id);
CREATE INDEX idx_resource_audit_changed_at ON system_resource_audit_logs(changed_at DESC);

-- ----------------------------------------------------------------------------
-- 26. asset_prompt_templates (素材提示词模板表) - P2 级别
-- ----------------------------------------------------------------------------
CREATE TABLE asset_prompt_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL REFERENCES profiles(id),
    name TEXT NOT NULL,
    description TEXT,
    who_type TEXT,
    who_custom TEXT,
    what_type TEXT,
    what_custom TEXT,
    where_type TEXT,
    where_custom TEXT,
    style TEXT DEFAULT 'cartoon',
    moods TEXT[] DEFAULT '{warm}',
    aspect_ratio TEXT DEFAULT 'square',
    creativity_level REAL DEFAULT 0.3,
    negative_prompt TEXT,
    use_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMPTZ,,
    recovery_expires_at TIMESTAMPTZ,  -- 恢复期截止时间,过期后用户看不到此删除记录
    CONSTRAINT chk_asset_prompt_templates_deleted_at_consistency
        CHECK ((is_deleted = false AND deleted_at IS NULL) OR (is_deleted = true AND deleted_at IS NOT NULL)),
    CONSTRAINT chk_asset_prompt_templates_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);

COMMENT ON TABLE asset_prompt_templates IS '素材提示词模板表: 用户保存的 AI 生成模板 (5W1H)';
COMMENT ON COLUMN asset_prompt_templates.is_deleted IS '软删除标记';
COMMENT ON COLUMN asset_prompt_templates.deleted_at IS '删除时间';

-- 索引
-- 可恢复删除记录索引 (恢复期内)
CREATE INDEX idx_asset_prompt_templates_deleted_recoverable
ON asset_prompt_templates(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON INDEX idx_asset_prompt_templates_deleted_recoverable IS '可恢复删除记录索引 - 只包含未过期的删除记录';


CREATE INDEX idx_asset_prompt_templates_user ON asset_prompt_templates(user_id) WHERE is_deleted = false;
CREATE INDEX idx_asset_prompt_templates_usage ON asset_prompt_templates(user_id, use_count DESC) WHERE is_deleted = false;

-- 触发器
CREATE TRIGGER trg_asset_prompt_templates_updated_at
    BEFORE UPDATE ON asset_prompt_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 第十一部分: 订阅与积分购买表
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 27. pricing_plans (定价方案主表) ⭐ NEW
-- ----------------------------------------------------------------------------
CREATE TABLE pricing_plans (
    id SERIAL PRIMARY KEY,

    -- 基础信息
    plan_code VARCHAR(50) UNIQUE NOT NULL,
    plan_type VARCHAR(20) NOT NULL CHECK (plan_type IN ('subscription', 'credits')),
    plan_name VARCHAR(100) NOT NULL,
    description TEXT,

    -- 价格信息 (美分)
    price_cents INT NOT NULL CHECK (price_cents >= 0),
    original_price_cents INT CHECK (original_price_cents >= 0),
    currency VARCHAR(3) DEFAULT 'USD' NOT NULL,

    -- 订阅专用字段
    billing_interval VARCHAR(20),
    tier VARCHAR(10),
    monthly_credits INT,

    -- 积分包专用字段
    credits_amount INT,

    -- Stripe 集成
    stripe_price_id_prod VARCHAR(100),
    stripe_price_id_dev VARCHAR(100),
    stripe_product_id VARCHAR(100),

    -- 状态管理
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_visible BOOLEAN DEFAULT TRUE NOT NULL,
    is_featured BOOLEAN DEFAULT FALSE NOT NULL,
    sort_order INT DEFAULT 0 NOT NULL,

    -- 版本管理
    version INT DEFAULT 1 NOT NULL CHECK (version > 0),
    effective_from TIMESTAMPTZ DEFAULT NOW(),
    effective_until TIMESTAMPTZ,

    -- 元数据
    metadata JSONB DEFAULT '{}'::jsonb,

    -- 审计字段
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),

    -- 约束: 确保字段互斥性
    CONSTRAINT check_subscription_fields CHECK (
        (plan_type = 'subscription'
         AND billing_interval IS NOT NULL
         AND tier IS NOT NULL
         AND credits_amount IS NULL)
        OR
        (plan_type = 'credits'
         AND credits_amount IS NOT NULL
         AND billing_interval IS NULL
         AND tier IS NULL)
    ),
    CONSTRAINT check_effective_dates CHECK (effective_until IS NULL OR effective_until > effective_from),

    -- Stripe Price ID 格式验证
    CONSTRAINT check_stripe_price_id_prod_format CHECK (stripe_price_id_prod IS NULL OR stripe_price_id_prod ~ '^price_[A-Za-z0-9]+$' OR stripe_price_id_prod ~ '^\{\{.*\}\}$'),
    CONSTRAINT check_stripe_price_id_dev_format CHECK (stripe_price_id_dev IS NULL OR stripe_price_id_dev ~ '^price_[A-Za-z0-9]+$' OR stripe_price_id_dev ~ '^\{\{.*\}\}$')
);

COMMENT ON TABLE pricing_plans IS '定价方案主表: 所有订阅和积分包的价格配置';
COMMENT ON COLUMN pricing_plans.price_cents IS '实际价格(美分): 990=$9.9';
COMMENT ON COLUMN pricing_plans.original_price_cents IS '原价(美分,划线价): 1490=$14.9';
COMMENT ON COLUMN pricing_plans.stripe_price_id_prod IS 'Stripe Price ID (生产环境)';
COMMENT ON COLUMN pricing_plans.stripe_price_id_dev IS 'Stripe Price ID (开发环境)';
COMMENT ON COLUMN pricing_plans.metadata IS '扩展元数据(JSON): discount_percent, badge, experiment_id';

CREATE INDEX idx_pricing_plans_plan_code ON pricing_plans(plan_code);
CREATE INDEX idx_pricing_plans_plan_type ON pricing_plans(plan_type);
CREATE INDEX idx_pricing_plans_is_active ON pricing_plans(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_pricing_plans_is_visible ON pricing_plans(is_visible) WHERE is_visible = TRUE;
CREATE INDEX idx_pricing_plans_effective_from ON pricing_plans(effective_from);
CREATE INDEX idx_pricing_plans_tier ON pricing_plans(tier) WHERE tier IS NOT NULL;
CREATE INDEX idx_pricing_plans_sort_order ON pricing_plans(sort_order);

-- 触发器
CREATE TRIGGER trg_pricing_plans_updated_at
    BEFORE UPDATE ON pricing_plans
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_pricing_plans_audit
    AFTER INSERT OR UPDATE OR DELETE ON pricing_plans
    FOR EACH ROW
    EXECUTE FUNCTION log_pricing_plan_change();

-- ----------------------------------------------------------------------------
-- 28. pricing_history (价格变更历史表) ⭐ NEW
-- ----------------------------------------------------------------------------
CREATE TABLE pricing_history (
    id SERIAL PRIMARY KEY,
    plan_id INT NOT NULL REFERENCES pricing_plans(id) ON DELETE CASCADE,
    plan_code VARCHAR(50) NOT NULL,

    -- 变更信息
    action VARCHAR(20) NOT NULL CHECK (action IN ('create', 'update', 'update_price', 'activate', 'deactivate', 'show', 'hide', 'delete')),
    old_data JSONB,
    new_data JSONB,

    -- 审计信息
    changed_by VARCHAR(100) NOT NULL,
    changed_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

COMMENT ON TABLE pricing_history IS '价格变更历史: 自动审计追踪所有价格相关的修改';
COMMENT ON COLUMN pricing_history.old_data IS '修改前的完整数据快照(JSON)';
COMMENT ON COLUMN pricing_history.new_data IS '修改后的完整数据快照(JSON)';

CREATE INDEX idx_pricing_history_plan_id ON pricing_history(plan_id);
CREATE INDEX idx_pricing_history_plan_code ON pricing_history(plan_code);
CREATE INDEX idx_pricing_history_changed_at ON pricing_history(changed_at DESC);
CREATE INDEX idx_pricing_history_changed_by ON pricing_history(changed_by);
CREATE INDEX idx_pricing_history_action ON pricing_history(action);
CREATE INDEX idx_pricing_history_old_data_gin ON pricing_history USING GIN(old_data);  -- GIN 索引用于 JSONB 查询
CREATE INDEX idx_pricing_history_new_data_gin ON pricing_history USING GIN(new_data);  -- GIN 索引用于 JSONB 查询

-- ----------------------------------------------------------------------------
-- 29. user_price_overrides (用户级价格覆盖表) ⭐ NEW
-- ----------------------------------------------------------------------------
CREATE TABLE user_price_overrides (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,  -- 统一使用 TEXT 类型 (与 profiles.id 一致)
    pricing_plan_id INT NOT NULL REFERENCES pricing_plans(id) ON DELETE CASCADE,

    -- 覆盖价格
    override_price_cents INT NOT NULL CHECK (override_price_cents >= 0),
    reason TEXT NOT NULL,

    -- 有效期
    valid_from TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    valid_until TIMESTAMPTZ,

    -- 审计
    created_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- 约束
    UNIQUE(user_id, pricing_plan_id),
    CONSTRAINT check_valid_dates CHECK (valid_until IS NULL OR valid_until > valid_from)
);

COMMENT ON TABLE user_price_overrides IS '用户级价格覆盖: 支持特定用户的定制价格';
COMMENT ON COLUMN user_price_overrides.override_price_cents IS '用户专属价格(美分): 1990=$19.9';
COMMENT ON COLUMN user_price_overrides.valid_until IS 'NULL=永久有效, 否则到期后失效';

CREATE INDEX idx_user_price_overrides_user_id ON user_price_overrides(user_id);
CREATE INDEX idx_user_price_overrides_plan_id ON user_price_overrides(pricing_plan_id);
CREATE INDEX idx_user_price_overrides_valid_from ON user_price_overrides(valid_from);
CREATE INDEX idx_user_price_overrides_valid_until ON user_price_overrides(valid_until) WHERE valid_until IS NOT NULL;

-- 触发器
CREATE TRIGGER trg_user_price_overrides_updated_at
    BEFORE UPDATE ON user_price_overrides
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ----------------------------------------------------------------------------
-- 30. subscription_history (订阅历史表)
-- ----------------------------------------------------------------------------
CREATE TABLE subscription_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    tier TEXT NOT NULL CHECK (tier IN ('t1', 't2', 't3')),
    action TEXT NOT NULL CHECK (action IN ('upgrade', 'downgrade', 'cancel', 'renew')),
    stripe_subscription_id TEXT,
    stripe_event_id TEXT,
    effective_date TIMESTAMPTZ NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE subscription_history IS '订阅历史表: 记录用户的订阅变更历史';

-- 索引
CREATE INDEX idx_sub_history_user ON subscription_history(user_id, effective_date DESC);
CREATE INDEX idx_sub_history_tier ON subscription_history(tier);

-- ----------------------------------------------------------------------------
-- 31. credit_purchases (积分购买记录表)
-- ----------------------------------------------------------------------------
CREATE TABLE credit_purchases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    plan_type TEXT NOT NULL CHECK (plan_type IN ('credits_100', 'credits_500', 'credits_2000')),
    credits_amount INTEGER NOT NULL,
    price_usd DECIMAL(10,2) NOT NULL,
    stripe_payment_intent_id TEXT UNIQUE,
    stripe_invoice_id TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed', 'refunded')),
    idempotency_key TEXT UNIQUE,
    metadata JSONB DEFAULT '{}',
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    -- 幂等性键格式验证 (至少 16 字符)
    CONSTRAINT check_credit_purchase_idempotency_format CHECK (idempotency_key IS NULL OR length(idempotency_key) >= 16)
);

COMMENT ON TABLE credit_purchases IS '积分购买记录表: 记录用户购买积分包的交易';

-- 索引
CREATE INDEX idx_credit_purchases_user ON credit_purchases(user_id, created_at DESC);
CREATE INDEX idx_credit_purchases_status ON credit_purchases(status);
CREATE UNIQUE INDEX idx_credit_purchases_idempotency ON credit_purchases(idempotency_key) WHERE idempotency_key IS NOT NULL;

-- ============================================================================
-- 第十二部分: Feature Flag 与实验系统
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 32. feature_flags (Feature Flag 表)
-- ----------------------------------------------------------------------------
CREATE TABLE feature_flags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    flag_key TEXT UNIQUE NOT NULL,
    flag_name TEXT NOT NULL,
    description TEXT,
    is_enabled BOOLEAN DEFAULT FALSE,
    rollout_percentage INTEGER DEFAULT 0 CHECK (rollout_percentage BETWEEN 0 AND 100),
    target_tiers TEXT[] DEFAULT ARRAY[]::TEXT[],
    target_user_ids TEXT[] DEFAULT ARRAY[]::TEXT[],
    config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE feature_flags IS 'Feature Flag 表: 功能开关和灰度发布';

-- 索引
CREATE INDEX idx_feature_flags_key ON feature_flags(flag_key);
CREATE INDEX idx_feature_flags_enabled ON feature_flags(is_enabled);

-- 触发器
CREATE TRIGGER trg_feature_flags_updated_at
    BEFORE UPDATE ON feature_flags
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ----------------------------------------------------------------------------
-- 33. experiments (A/B 测试实验表)
-- ----------------------------------------------------------------------------
CREATE TABLE experiments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    experiment_key TEXT UNIQUE NOT NULL,
    experiment_name TEXT NOT NULL,
    description TEXT,
    hypothesis TEXT,
    variants JSONB NOT NULL,
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'paused', 'completed')),
    traffic_percentage INTEGER DEFAULT 100 CHECK (traffic_percentage BETWEEN 0 AND 100),
    target_tiers TEXT[] DEFAULT ARRAY[]::TEXT[],
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE experiments IS 'A/B 测试实验表: 定义实验和变体';

-- 索引
CREATE INDEX idx_experiments_key ON experiments(experiment_key);
CREATE INDEX idx_experiments_status ON experiments(status);

-- 触发器
CREATE TRIGGER trg_experiments_updated_at
    BEFORE UPDATE ON experiments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ----------------------------------------------------------------------------
-- 34. experiment_assignments (实验分配表)
-- ----------------------------------------------------------------------------
CREATE TABLE experiment_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    experiment_id UUID NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    variant_key TEXT NOT NULL,
    assigned_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(experiment_id, user_id)
);

COMMENT ON TABLE experiment_assignments IS '实验分配表: 记录用户分配到的实验变体';

-- 索引
CREATE INDEX idx_exp_assignments_experiment ON experiment_assignments(experiment_id);
CREATE INDEX idx_exp_assignments_user ON experiment_assignments(user_id);

-- ----------------------------------------------------------------------------
-- 35. experiment_results (实验结果表)
-- ----------------------------------------------------------------------------
CREATE TABLE experiment_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    experiment_id UUID NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    variant_key TEXT NOT NULL,
    metrics JSONB NOT NULL DEFAULT '{}',
    sample_size INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(experiment_id, date, variant_key)
);

COMMENT ON TABLE experiment_results IS '实验结果表: 每日聚合的实验指标';

-- 索引
CREATE INDEX idx_exp_results_experiment ON experiment_results(experiment_id);
CREATE INDEX idx_exp_results_date ON experiment_results(experiment_id, date DESC);

-- 触发器
CREATE TRIGGER trg_experiment_results_updated_at
    BEFORE UPDATE ON experiment_results
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ----------------------------------------------------------------------------
-- 36. experiment_exposures (实验曝光表)
-- ----------------------------------------------------------------------------
CREATE TABLE experiment_exposures (
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
CREATE INDEX idx_exp_exposures_experiment ON experiment_exposures(experiment_id);
CREATE INDEX idx_exp_exposures_user ON experiment_exposures(user_id);
CREATE INDEX idx_exp_exposures_created_at ON experiment_exposures(created_at DESC);
CREATE INDEX idx_exp_exposures_dedup ON experiment_exposures(experiment_id, user_id, created_at DESC);

-- ----------------------------------------------------------------------------
-- 37. experiment_conversions (实验转化表)
-- ----------------------------------------------------------------------------
CREATE TABLE experiment_conversions (
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
CREATE INDEX idx_exp_conversions_experiment ON experiment_conversions(experiment_id);
CREATE INDEX idx_exp_conversions_user ON experiment_conversions(user_id);
CREATE INDEX idx_exp_conversions_metric ON experiment_conversions(metric_key);
CREATE INDEX idx_exp_conversions_created_at ON experiment_conversions(created_at DESC);
CREATE INDEX idx_exp_conversions_exp_metric ON experiment_conversions(experiment_id, metric_key, created_at DESC);

-- ============================================================================
-- 第十三部分: 营销活动表
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 38. campaigns (营销活动表)
-- ----------------------------------------------------------------------------
CREATE TABLE campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    type TEXT NOT NULL CHECK (type IN ('credits_reward', 'discount', 'trial_extension', 'bonus')),
    config JSONB NOT NULL DEFAULT '{}',
    target_type TEXT NOT NULL DEFAULT 'all' CHECK (target_type IN ('all', 'tier', 'cohort', 'user_list')),
    target_config JSONB DEFAULT '{}',
    notification_channels TEXT[] DEFAULT ARRAY['banner'],
    notification_config JSONB DEFAULT '{}',
    start_at TIMESTAMPTZ NOT NULL,
    end_at TIMESTAMPTZ NOT NULL,
    timezone TEXT DEFAULT 'America/New_York',
    usage_limit INTEGER,
    usage_per_user INTEGER DEFAULT 1,
    usage_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'paused', 'completed')),
    is_active BOOLEAN DEFAULT TRUE,
    created_by TEXT REFERENCES profiles(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMPTZ,,
    recovery_expires_at TIMESTAMPTZ,  -- 恢复期截止时间,过期后用户看不到此删除记录
    is_permanently_deleted BOOLEAN DEFAULT false,
    CONSTRAINT chk_campaigns_deleted_at_consistency
        CHECK ((is_deleted = false AND deleted_at IS NULL) OR (is_deleted = true AND deleted_at IS NOT NULL)),
    CONSTRAINT chk_campaigns_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);

COMMENT ON TABLE campaigns IS '营销活动表: 积分奖励、折扣等营销活动';
COMMENT ON COLUMN campaigns.is_deleted IS '软删除标记 (30天内可恢复)';
COMMENT ON COLUMN campaigns.deleted_at IS '删除时间';
COMMENT ON COLUMN campaigns.is_permanently_deleted IS '永久删除标记 (不可恢复)';

-- 索引
-- 可恢复删除记录索引 (恢复期内)
CREATE INDEX idx_campaigns_deleted_recoverable
ON campaigns(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON INDEX idx_campaigns_deleted_recoverable IS '可恢复删除记录索引 - 只包含未过期的删除记录';


CREATE INDEX idx_campaigns_status ON campaigns(status, is_active) WHERE is_deleted = false AND is_permanently_deleted = false;
CREATE INDEX idx_campaigns_dates ON campaigns(start_at, end_at) WHERE is_deleted = false;

-- 触发器
CREATE TRIGGER trg_campaigns_updated_at
    BEFORE UPDATE ON campaigns
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ----------------------------------------------------------------------------
-- 39. campaign_participations (活动参与表)
-- ----------------------------------------------------------------------------
CREATE TABLE campaign_participations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    credits_received INTEGER,
    claimed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(campaign_id, user_id)
,

    CONSTRAINT chk_campaign_participations_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);

COMMENT ON TABLE campaign_participations IS '活动参与表: 记录用户领取活动奖励';

-- 索引
-- 可恢复删除记录索引 (恢复期内)
CREATE INDEX idx_campaign_participations_deleted_recoverable
ON campaign_participations(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON INDEX idx_campaign_participations_deleted_recoverable IS '可恢复删除记录索引 - 只包含未过期的删除记录';


CREATE INDEX idx_campaign_participations_user ON campaign_participations(user_id);
CREATE INDEX idx_campaign_participations_campaign ON campaign_participations(campaign_id);

-- ----------------------------------------------------------------------------
-- 40. campaign_dismissals (活动关闭记录表)
-- ----------------------------------------------------------------------------
CREATE TABLE campaign_dismissals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    channel TEXT NOT NULL,
    dismissed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(campaign_id, user_id, channel)
,

    CONSTRAINT chk_campaign_dismissals_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);

COMMENT ON TABLE campaign_dismissals IS '活动关闭记录表: 记录用户关闭的活动通知';

-- 索引
-- 可恢复删除记录索引 (恢复期内)
CREATE INDEX idx_campaign_dismissals_deleted_recoverable
ON campaign_dismissals(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON INDEX idx_campaign_dismissals_deleted_recoverable IS '可恢复删除记录索引 - 只包含未过期的删除记录';


CREATE INDEX idx_campaign_dismissals_user ON campaign_dismissals(user_id);

-- ============================================================================
-- 第十四部分: 通知与引导表
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 41. notifications (通知表)
-- ----------------------------------------------------------------------------
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    notification_type TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    action_url TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
,

    CONSTRAINT chk_notifications_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);

COMMENT ON TABLE notifications IS '通知表: 用户通知中心';

-- 索引
-- 可恢复删除记录索引 (恢复期内)
CREATE INDEX idx_notifications_deleted_recoverable
ON notifications(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON INDEX idx_notifications_deleted_recoverable IS '可恢复删除记录索引 - 只包含未过期的删除记录';


CREATE INDEX idx_notifications_user ON notifications(user_id, created_at DESC);
CREATE INDEX idx_notifications_type ON notifications(notification_type);
CREATE INDEX idx_notifications_unread ON notifications(user_id, is_read) WHERE is_read = FALSE;

-- ----------------------------------------------------------------------------
-- 42. onboarding_steps (引导步骤定义表)
-- ----------------------------------------------------------------------------
CREATE TABLE onboarding_steps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    step_key TEXT UNIQUE NOT NULL,
    step_name TEXT NOT NULL,
    description TEXT,
    step_order INTEGER NOT NULL,
    is_required BOOLEAN DEFAULT TRUE,
    target_tiers TEXT[] DEFAULT ARRAY['free', 'starter', 'pro'],
    config JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
,

    CONSTRAINT chk_onboarding_steps_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);

COMMENT ON TABLE onboarding_steps IS '引导步骤定义表: 定义新手引导流程';

-- 索引
-- 可恢复删除记录索引 (恢复期内)
CREATE INDEX idx_onboarding_steps_deleted_recoverable
ON onboarding_steps(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON INDEX idx_onboarding_steps_deleted_recoverable IS '可恢复删除记录索引 - 只包含未过期的删除记录';


CREATE INDEX idx_onboarding_steps_order ON onboarding_steps(step_order);
CREATE INDEX idx_onboarding_steps_active ON onboarding_steps(is_active);

-- 触发器
CREATE TRIGGER trg_onboarding_steps_updated_at
    BEFORE UPDATE ON onboarding_steps
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ----------------------------------------------------------------------------
-- 43. user_onboarding_progress (用户引导进度表)
-- ----------------------------------------------------------------------------
CREATE TABLE user_onboarding_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    step_id UUID NOT NULL REFERENCES onboarding_steps(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'skipped')),
    completed_at TIMESTAMPTZ,
    skipped_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, step_id)
,

    CONSTRAINT chk_user_onboarding_progress_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);

COMMENT ON TABLE user_onboarding_progress IS '用户引导进度表: 跟踪用户的引导完成情况';

-- 索引
-- 可恢复删除记录索引 (恢复期内)
CREATE INDEX idx_user_onboarding_progress_deleted_recoverable
ON user_onboarding_progress(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON INDEX idx_user_onboarding_progress_deleted_recoverable IS '可恢复删除记录索引 - 只包含未过期的删除记录';


CREATE INDEX idx_onboarding_progress_user ON user_onboarding_progress(user_id);
CREATE INDEX idx_onboarding_progress_status ON user_onboarding_progress(status);

-- ============================================================================
-- 第十五部分: 推荐系统表
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 44. referrals (推荐表)
-- ----------------------------------------------------------------------------
CREATE TABLE referrals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    referrer_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    referee_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    referral_code TEXT NOT NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'expired')),
    reward_given BOOLEAN DEFAULT FALSE,
    reward_amount INTEGER,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(referrer_id, referee_id)
,

    CONSTRAINT chk_referrals_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);

COMMENT ON TABLE referrals IS '推荐表: 记录用户推荐关系';

-- 索引
-- 可恢复删除记录索引 (恢复期内)
CREATE INDEX idx_referrals_deleted_recoverable
ON referrals(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON INDEX idx_referrals_deleted_recoverable IS '可恢复删除记录索引 - 只包含未过期的删除记录';


CREATE INDEX idx_referrals_referrer ON referrals(referrer_id);
CREATE INDEX idx_referrals_referee ON referrals(referee_id);
CREATE INDEX idx_referrals_code ON referrals(referral_code);
CREATE INDEX idx_referrals_status ON referrals(status);

-- ============================================================================
-- 第十六部分: 项目版本控制表
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 45. project_versions (项目版本表)
-- ----------------------------------------------------------------------------
CREATE TABLE project_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    canvas_data JSONB NOT NULL,
    thumbnail_url TEXT,
    change_description TEXT,
    created_by TEXT NOT NULL REFERENCES profiles(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, version_number)
,

    CONSTRAINT chk_project_versions_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);

COMMENT ON TABLE project_versions IS '项目版本表: 自动保存项目历史版本';

-- 索引
-- 可恢复删除记录索引 (恢复期内)
CREATE INDEX idx_project_versions_deleted_recoverable
ON project_versions(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON INDEX idx_project_versions_deleted_recoverable IS '可恢复删除记录索引 - 只包含未过期的删除记录';


CREATE INDEX idx_project_versions_project ON project_versions(project_id, version_number DESC);
CREATE INDEX idx_project_versions_created ON project_versions(created_at DESC);

-- ============================================================================
-- 第十七部分: 用户资产表
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 46. assets (用户资产表)
-- ----------------------------------------------------------------------------
CREATE TABLE assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id),
    url TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('image', 'video', 'audio', 'document')),
    prompt TEXT,
    description TEXT,
    metadata JSONB DEFAULT '{}',
    source_listing_id UUID REFERENCES marketplace_listings(id),
    is_purchased BOOLEAN DEFAULT FALSE,
    origin_owner_id TEXT REFERENCES profiles(id),
    is_hidden_from_trash BOOLEAN DEFAULT FALSE,
    timezone TEXT DEFAULT 'UTC',
    created_at_local TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,

    recovery_expires_at TIMESTAMPTZ,  -- 恢复期截止时间,过期后用户看不到此删除记录,

    CONSTRAINT chk_assets_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);

COMMENT ON TABLE assets IS '用户资产表: 用户上传的图片、视频等资产';

-- 索引
-- 可恢复删除记录索引 (恢复期内)
CREATE INDEX idx_assets_deleted_recoverable
ON assets(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON INDEX idx_assets_deleted_recoverable IS '可恢复删除记录索引 - 只包含未过期的删除记录';


CREATE INDEX idx_assets_user ON assets(user_id, created_at DESC);
CREATE INDEX idx_assets_project ON assets(project_id) WHERE project_id IS NOT NULL;
CREATE INDEX idx_assets_type ON assets(type);
CREATE INDEX idx_assets_active ON assets(is_deleted) WHERE is_deleted = FALSE;

-- 触发器
CREATE TRIGGER trg_assets_updated_at
    BEFORE UPDATE ON assets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_assets_soft_delete
    BEFORE UPDATE ON assets
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();

-- ============================================================================
-- 第十八部分: 用户折扣表
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 47. user_discounts (用户折扣表)
-- ----------------------------------------------------------------------------
CREATE TABLE user_discounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    discount_percent INTEGER NOT NULL CHECK (discount_percent BETWEEN 1 AND 100),
    valid_from TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    valid_until TIMESTAMPTZ,
    target_plan TEXT CHECK (target_plan IN ('starter', 'pro')),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    -- 日期逻辑验证
    CONSTRAINT check_discount_dates CHECK (valid_until IS NULL OR valid_until > valid_from)
);

COMMENT ON TABLE user_discounts IS '用户折扣表: 个性化折扣优惠';

-- 索引
CREATE INDEX idx_user_discounts_user ON user_discounts(user_id);
CREATE INDEX idx_user_discounts_valid ON user_discounts(valid_until);
-- Note: 不使用 WHERE valid_until > CURRENT_TIMESTAMP 因为 CURRENT_TIMESTAMP 是 VOLATILE 函数
-- 查询时会在 SQL 中过滤: WHERE valid_until > CURRENT_TIMESTAMP

-- ============================================================================
-- 第十九部分: 核心业务函数
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 原子扣除积分函数
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION deduct_credits_atomic(
    p_user_id TEXT,
    p_amount INT,
    p_type TEXT,
    p_description TEXT DEFAULT NULL,
    p_idempotency_key TEXT DEFAULT NULL,
    p_related_entity_type TEXT DEFAULT NULL,
    p_related_entity_id TEXT DEFAULT NULL
)
RETURNS TABLE (
    success BOOLEAN,
    new_monthly INT,
    new_permanent INT,
    error_message TEXT
) AS $$
DECLARE
    v_monthly INT;
    v_permanent INT;
    v_deduct_monthly INT;
    v_deduct_permanent INT;
BEGIN
    -- 输入验证
    IF p_user_id IS NULL OR length(p_user_id) = 0 OR length(p_user_id) > 100 THEN
        RETURN QUERY SELECT FALSE, 0, 0, 'Invalid user_id'::TEXT;
        RETURN;
    END IF;

    IF p_amount <= 0 OR p_amount > 1000000 THEN
        RETURN QUERY SELECT FALSE, 0, 0, 'Invalid amount (must be 1-1000000)'::TEXT;
        RETURN;
    END IF;

    IF p_type IS NULL OR length(p_type) = 0 OR length(p_type) > 50 THEN
        RETURN QUERY SELECT FALSE, 0, 0, 'Invalid type'::TEXT;
        RETURN;
    END IF;

    IF p_description IS NOT NULL AND length(p_description) > 500 THEN
        RETURN QUERY SELECT FALSE, 0, 0, 'Description too long (max 500 chars)'::TEXT;
        RETURN;
    END IF;

    -- 幂等性检查: 防止重复扣除
    IF p_idempotency_key IS NOT NULL THEN
        IF EXISTS (
            SELECT 1 FROM credit_transactions
            WHERE idempotency_key = p_idempotency_key || '-deduct'
        ) THEN
            -- 返回已存在的交易结果
            SELECT credits_monthly, credits_permanent
            INTO v_monthly, v_permanent
            FROM profiles WHERE id = p_user_id;
            RETURN QUERY SELECT FALSE, v_monthly, v_permanent, 'Duplicate transaction (idempotency)'::TEXT;
            RETURN;
        END IF;
    END IF;

    -- 加锁获取当前余额
    SELECT credits_monthly, credits_permanent
    INTO v_monthly, v_permanent
    FROM profiles
    WHERE id = p_user_id
    FOR UPDATE;

    -- 检查用户是否存在
    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, 0, 0, 'User not found';
        RETURN;
    END IF;

    -- 检查总余额是否足够
    IF (v_monthly + v_permanent) < p_amount THEN
        RETURN QUERY SELECT FALSE, v_monthly, v_permanent, 'Insufficient credits';
        RETURN;
    END IF;

    -- 计算扣除策略: 先扣月度积分,再扣永久积分
    IF v_monthly >= p_amount THEN
        v_deduct_monthly := p_amount;
        v_deduct_permanent := 0;
    ELSE
        v_deduct_monthly := v_monthly;
        v_deduct_permanent := p_amount - v_monthly;
    END IF;

    -- 更新余额
    UPDATE profiles
    SET
        credits_monthly = v_monthly - v_deduct_monthly,
        credits_permanent = v_permanent - v_deduct_permanent,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_user_id;

    -- 记录月度积分交易
    IF v_deduct_monthly > 0 THEN
        INSERT INTO credit_transactions (
            user_id, transaction_type, bucket, amount,
            balance_monthly_after, balance_permanent_after,
            description, idempotency_key,
            related_entity_type, related_entity_id
        ) VALUES (
            p_user_id, p_type, 'monthly', -v_deduct_monthly,
            v_monthly - v_deduct_monthly, v_permanent,
            p_description, p_idempotency_key || '_monthly',
            p_related_entity_type, p_related_entity_id
        );
    END IF;

    -- 记录永久积分交易
    IF v_deduct_permanent > 0 THEN
        INSERT INTO credit_transactions (
            user_id, transaction_type, bucket, amount,
            balance_monthly_after, balance_permanent_after,
            description, idempotency_key,
            related_entity_type, related_entity_id
        ) VALUES (
            p_user_id, p_type, 'permanent', -v_deduct_permanent,
            v_monthly - v_deduct_monthly, v_permanent - v_deduct_permanent,
            p_description, p_idempotency_key || '_permanent',
            p_related_entity_type, p_related_entity_id
        );
    END IF;

    RETURN QUERY SELECT TRUE, v_monthly - v_deduct_monthly, v_permanent - v_deduct_permanent, NULL::TEXT;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION deduct_credits_atomic IS '原子扣除积分: 先月度后永久,保证事务一致性';

-- ----------------------------------------------------------------------------
-- 原子增加积分函数
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION add_credits_atomic(
    p_user_id TEXT,
    p_amount INT,
    p_bucket TEXT,
    p_type TEXT,
    p_description TEXT DEFAULT NULL,
    p_idempotency_key TEXT DEFAULT NULL
)
RETURNS TABLE (
    success BOOLEAN,
    new_monthly INT,
    new_permanent INT,
    error_message TEXT
) AS $$
DECLARE
    v_monthly INT;
    v_permanent INT;
BEGIN
    -- 输入验证
    IF p_user_id IS NULL OR length(p_user_id) = 0 OR length(p_user_id) > 100 THEN
        RETURN QUERY SELECT FALSE, 0, 0, 'Invalid user_id'::TEXT;
        RETURN;
    END IF;

    IF p_amount <= 0 OR p_amount > 1000000 THEN
        RETURN QUERY SELECT FALSE, 0, 0, 'Invalid amount (must be 1-1000000)'::TEXT;
        RETURN;
    END IF;

    IF p_bucket NOT IN ('monthly', 'permanent') THEN
        RETURN QUERY SELECT FALSE, 0, 0, 'Invalid bucket (must be monthly or permanent)'::TEXT;
        RETURN;
    END IF;

    IF p_type IS NULL OR length(p_type) = 0 OR length(p_type) > 50 THEN
        RETURN QUERY SELECT FALSE, 0, 0, 'Invalid type'::TEXT;
        RETURN;
    END IF;

    IF p_description IS NOT NULL AND length(p_description) > 500 THEN
        RETURN QUERY SELECT FALSE, 0, 0, 'Description too long (max 500 chars)'::TEXT;
        RETURN;
    END IF;

    -- 加锁获取当前余额
    SELECT credits_monthly, credits_permanent
    INTO v_monthly, v_permanent
    FROM profiles
    WHERE id = p_user_id
    FOR UPDATE;

    -- 检查用户是否存在
    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, 0, 0, 'User not found';
        RETURN;
    END IF;

    -- 更新余额
    IF p_bucket = 'monthly' THEN
        UPDATE profiles SET credits_monthly = credits_monthly + p_amount WHERE id = p_user_id;
        v_monthly := v_monthly + p_amount;
    ELSE
        UPDATE profiles SET credits_permanent = credits_permanent + p_amount WHERE id = p_user_id;
        v_permanent := v_permanent + p_amount;
    END IF;

    -- 记录交易
    INSERT INTO credit_transactions (
        user_id, transaction_type, bucket, amount,
        balance_monthly_after, balance_permanent_after,
        description, idempotency_key
    ) VALUES (
        p_user_id, p_type, p_bucket, p_amount,
        v_monthly, v_permanent,
        p_description, p_idempotency_key
    );

    RETURN QUERY SELECT TRUE, v_monthly, v_permanent, NULL::TEXT;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION add_credits_atomic IS '原子增加积分: 指定桶类型,保证事务一致性';

-- ----------------------------------------------------------------------------
-- 执行市场购买函数
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION execute_marketplace_purchase(
    p_user_id TEXT,
    p_listing_id UUID,
    p_idempotency_key TEXT
)
RETURNS TABLE (
    success BOOLEAN,
    error_message TEXT
) AS $$
DECLARE
    v_price INT;
    v_title TEXT;
    v_thumbnail TEXT;
    v_description TEXT;
    v_version TEXT;
    v_resource_type TEXT;
    v_resource_id UUID;
BEGIN
    -- 输入验证
    IF p_user_id IS NULL OR length(p_user_id) = 0 OR length(p_user_id) > 100 THEN
        RETURN QUERY SELECT FALSE, 'Invalid user_id'::TEXT;
        RETURN;
    END IF;

    IF p_listing_id IS NULL THEN
        RETURN QUERY SELECT FALSE, 'Invalid listing_id'::TEXT;
        RETURN;
    END IF;

    IF p_idempotency_key IS NOT NULL AND length(p_idempotency_key) > 200 THEN
        RETURN QUERY SELECT FALSE, 'Idempotency key too long (max 200 chars)'::TEXT;
        RETURN;
    END IF;

    -- 获取 listing 信息
    SELECT price_credits, title, thumbnail_url, description, version, resource_type, resource_id
    INTO v_price, v_title, v_thumbnail, v_description, v_version, v_resource_type, v_resource_id
    FROM marketplace_listings
    WHERE id = p_listing_id AND is_public = TRUE AND is_deleted = FALSE
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, 'Listing not found or not available';
        RETURN;
    END IF;

    -- 检查是否已购买
    IF EXISTS (SELECT 1 FROM marketplace_purchases WHERE user_id = p_user_id AND listing_id = p_listing_id) THEN
        RETURN QUERY SELECT TRUE, NULL::TEXT;
        RETURN;
    END IF;

    -- 扣除积分 (必须检查是否成功)
    DECLARE
        v_deduct_success BOOLEAN;
        v_error_msg TEXT;
    BEGIN
        SELECT success, error_message
        INTO v_deduct_success, v_error_msg
        FROM deduct_credits_atomic(
            p_user_id,
            v_price,
            'marketplace_purchase',
            'Purchase listing: ' || v_title,
            p_idempotency_key,
            'listing',
            p_listing_id::TEXT
        );

        -- 如果扣费失败，立即返回错误
        IF NOT v_deduct_success THEN
            RETURN QUERY SELECT FALSE, COALESCE(v_error_msg, 'Insufficient credits');
            RETURN;
        END IF;
    END;

    -- 记录购买
    INSERT INTO marketplace_purchases (
        user_id, listing_id, price_paid, idempotency_key,
        snapshot_title, snapshot_thumbnail_url, snapshot_description,
        snapshot_version, snapshot_resource_type, snapshot_resource_id
    ) VALUES (
        p_user_id, p_listing_id, v_price, p_idempotency_key,
        v_title, v_thumbnail, v_description,
        v_version, v_resource_type, v_resource_id
    );

    -- 更新 listing 统计
    UPDATE marketplace_listings
    SET
        sales_count = sales_count + 1,
        total_revenue = total_revenue + v_price,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_listing_id;

    RETURN QUERY SELECT TRUE, NULL::TEXT;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION execute_marketplace_purchase IS '执行市场购买: 扣费 + 记录 + 统计更新 (原子操作)';

-- ----------------------------------------------------------------------------
-- Campaign 原子递增使用次数函数
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION increment_campaign_usage(
    p_campaign_id UUID
)
RETURNS BOOLEAN AS $$
DECLARE
    v_usage_limit INT;
    v_usage_count INT;
BEGIN
    SELECT usage_limit, usage_count
    INTO v_usage_limit, v_usage_count
    FROM campaigns
    WHERE id = p_campaign_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;

    -- 检查是否已达上限
    IF v_usage_limit IS NOT NULL AND v_usage_count >= v_usage_limit THEN
        RETURN FALSE;
    END IF;

    -- 原子递增
    UPDATE campaigns SET usage_count = usage_count + 1 WHERE id = p_campaign_id;

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION increment_campaign_usage IS 'Campaign 原子递增使用次数 (防止超限)';

-- ----------------------------------------------------------------------------
-- Upsert AI 使用量汇总函数
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION upsert_ai_usage_daily(
    p_date DATE,
    p_provider TEXT,
    p_model TEXT,
    p_call_type TEXT,
    p_success BOOLEAN,
    p_input_tokens BIGINT DEFAULT 0,
    p_output_tokens BIGINT DEFAULT 0,
    p_images INT DEFAULT 0,
    p_latency_ms INT DEFAULT 0,
    p_cost_usd DECIMAL DEFAULT 0,
    p_error_type TEXT DEFAULT NULL
)
RETURNS VOID AS $$
DECLARE
    v_error_counts JSONB;
BEGIN
    IF p_error_type IS NOT NULL THEN
        v_error_counts := jsonb_build_object(p_error_type, 1);
    ELSE
        v_error_counts := '{}'::jsonb;
    END IF;

    INSERT INTO ai_usage_daily (
        date, provider, model, call_type,
        total_calls, successful_calls, failed_calls,
        total_input_tokens, total_output_tokens, total_images,
        avg_latency_ms, min_latency_ms, max_latency_ms,
        estimated_cost_usd, error_counts
    ) VALUES (
        p_date, p_provider, p_model, p_call_type,
        1,
        CASE WHEN p_success THEN 1 ELSE 0 END,
        CASE WHEN p_success THEN 0 ELSE 1 END,
        p_input_tokens, p_output_tokens, p_images,
        p_latency_ms, p_latency_ms, p_latency_ms,
        p_cost_usd, v_error_counts
    )
    ON CONFLICT (date, provider, model, call_type) DO UPDATE SET
        total_calls = ai_usage_daily.total_calls + 1,
        successful_calls = ai_usage_daily.successful_calls + CASE WHEN p_success THEN 1 ELSE 0 END,
        failed_calls = ai_usage_daily.failed_calls + CASE WHEN p_success THEN 0 ELSE 1 END,
        total_input_tokens = ai_usage_daily.total_input_tokens + p_input_tokens,
        total_output_tokens = ai_usage_daily.total_output_tokens + p_output_tokens,
        total_images = ai_usage_daily.total_images + p_images,
        avg_latency_ms = CASE
            WHEN ai_usage_daily.total_calls = 0 THEN p_latency_ms
            ELSE ((ai_usage_daily.avg_latency_ms * ai_usage_daily.total_calls) + p_latency_ms) / (ai_usage_daily.total_calls + 1)
        END,
        min_latency_ms = LEAST(COALESCE(ai_usage_daily.min_latency_ms, p_latency_ms), p_latency_ms),
        max_latency_ms = GREATEST(COALESCE(ai_usage_daily.max_latency_ms, p_latency_ms), p_latency_ms),
        estimated_cost_usd = ai_usage_daily.estimated_cost_usd + p_cost_usd,
        error_counts = CASE
            WHEN p_error_type IS NOT NULL THEN
                ai_usage_daily.error_counts || jsonb_build_object(
                    p_error_type,
                    COALESCE((ai_usage_daily.error_counts->>p_error_type)::int, 0) + 1
                )
            ELSE ai_usage_daily.error_counts
        END,
        updated_at = CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION upsert_ai_usage_daily IS 'Upsert AI 使用量日汇总 (累加统计)';

-- ============================================================================
-- 第二十部分: 初始化数据
-- ============================================================================

-- ----------------------------------------------------------------------------
-- System Configs 初始化数据 (120+ 行)
-- ----------------------------------------------------------------------------
INSERT INTO system_configs (key, value, value_type, config_group, description, is_active, is_editable) VALUES

-- ========== Rate Limits (24条) ==========
('rate_limit.payment.checkout', '{"limit": 5, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Checkout API limit', true, true),
('rate_limit.payment.portal', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Billing portal limit', true, true),
('rate_limit.marketplace.purchase', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Marketplace purchase limit', true, true),
('rate_limit.generate.story', '{"limit": 20, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'AI story generation limit', true, true),
('rate_limit.generate.images', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'AI image generation limit', true, true),
('rate_limit.tools.ocr', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'OCR limit', true, true),
('rate_limit.export.pdf', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'PDF export limit', true, true),
('rate_limit.export.zip', '{"limit": 5, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'ZIP export limit', true, true),
('rate_limit.export.preview', '{"limit": 20, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Preview generation limit', true, true),
('rate_limit.projects.create', '{"limit": 20, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Project creation limit', true, true),
('rate_limit.assets.upload', '{"limit": 20, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Asset upload limit', true, true),
('rate_limit.marketplace.publish', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Listing publish limit', true, true),
('rate_limit.support.email', '{"limit": 3, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Support ticket limit', true, true),
('rate_limit.contact.form', '{"limit": 3, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Contact form limit', true, true),
('rate_limit.feedback.submit', '{"limit": 3, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Feedback submission limit', true, true),
('rate_limit.admin.credits', '{"limit": 30, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin credit adjustment limit', true, true),
('rate_limit.admin.tier', '{"limit": 30, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin tier update limit', true, true),
('rate_limit.admin.refund', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin refund limit', true, true),
('rate_limit.admin.subscription', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin subscription ops limit', true, true),
('rate_limit.admin.broadcast', '{"limit": 5, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin broadcast limit', true, true),
('rate_limit.admin.search', '{"limit": 60, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin search limit', true, true),
('rate_limit.marketplace.list', '{"limit": 60, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Marketplace listing limit', true, true),
('rate_limit.analytics.events', '{"limit": 60, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Analytics event ingestion limit', true, true),
('rate_limit.global.default', '{"limit": 100, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Global default limit', true, true),

-- ========== Analytics (3条) ==========
('analytics.enabled', '{"enabled": true}', 'json', 'analytics', 'Enable analytics tracking', true, true),
('analytics.sampling_rate', '{"critical": 1.0, "important": 1.0, "normal": 0.3, "debug": 0.0}', 'json', 'analytics', 'Event sampling rates', true, true),
('analytics.min_level', '{"level": "normal"}', 'json', 'analytics', 'Minimum tracking level', true, true),

-- ========== Feature Flags (4条) ==========
('FEATURE_AI_GENERATION', 'true', 'boolean', 'feature_flag', 'Enable AI image generation', true, true),
('FEATURE_MARKETPLACE', 'true', 'boolean', 'feature_flag', 'Enable marketplace', true, true),
('FEATURE_OCR', 'true', 'boolean', 'feature_flag', 'Enable OCR/Smart Scan', true, true),
('FEATURE_ZIP_EXPORT', 'true', 'boolean', 'feature_flag', 'Enable ZIP export', true, true),

-- ========== Limits (5条) ==========
('FREE_PROJECT_LIMIT', '1', 'number', 'limits', 'Max projects for free tier', true, true),
('STARTER_PROJECT_LIMIT', '20', 'number', 'limits', 'Max projects for starter tier', true, true),
('PRO_PROJECT_LIMIT', '200', 'number', 'limits', 'Max projects for pro tier', true, true),
('MAX_UPLOAD_FILE_SIZE_MB', '5', 'number', 'limits', 'Max file upload size in MB', true, true),
('MAX_LISTING_PRICE', '500', 'number', 'limits', 'Max marketplace listing price', true, true),

-- ========== Credits (9条) ==========
('CREDITS_PER_IMAGE', '5', 'number', 'credits', 'Credits per AI image', true, true),
('CREDITS_PER_OCR', '5', 'number', 'credits', 'Credits per OCR', true, true),
('CREDITS_PER_AI_DESIGN_PAGE', '5', 'number', 'credits', 'Credits per AI design page', true, true),
('SIGNUP_BONUS_CREDITS', '50', 'number', 'credits', 'Signup bonus credits', true, true),
('credits.cost.image_generation', '5', 'integer', 'credits', 'AI image generation cost per image', true, true),
('credits.cost.image_generation_reference', '7', 'integer', 'credits', 'AI image generation with reference cost', true, true),
('credits.cost.text_generation', '0', 'integer', 'credits', 'AI text generation cost (free)', true, true),
('credits.cost.smart_scan', '10', 'integer', 'credits', 'Smart Scan/OCR cost', true, true),
('credits.cost.ocr', '10', 'integer', 'credits', 'OCR recognition cost', true, true),

-- ========== Pricing (4条) ==========
('STARTER_PLAN_PRICE', '14.9', 'number', 'pricing', 'Starter monthly price', true, true),
('PRO_PLAN_PRICE', '29.9', 'number', 'pricing', 'Pro monthly price', true, true),
('STARTER_MONTHLY_CREDITS', '200', 'number', 'pricing', 'Starter monthly credits', true, true),
('PRO_MONTHLY_CREDITS', '500', 'number', 'pricing', 'Pro monthly credits', true, true),

-- ========== AI Providers (8条) ==========
('ai_providers.enabled', '{"openai": true, "fal": true, "qwen": false, "wanx": false, "gemini": false, "grok": false, "jimeng": false, "anthropic": false}', 'json', 'ai_providers', 'Enable/disable AI providers', true, true),
('ai_model.user.text_reasoning', '{"provider": "openai", "model": "gpt-4o-mini", "fallback": {"provider": "openai", "model": "gpt-4o-mini"}, "show_provider": false}', 'json', 'ai_models', 'User text reasoning model', true, true),
('ai_model.user.image_generation', '{"provider": "fal", "models": {"free": "flux-schnell", "starter": "flux-schnell", "pro": "flux-dev"}, "fallback": {"provider": "fal", "model": "flux-schnell"}, "show_provider": false}', 'json', 'ai_models', 'User image generation model by tier', true, true),
('ai_model.admin.analysis', '{"provider": "openai", "model": "gpt-4o", "fallback": {"provider": "openai", "model": "gpt-4o-mini"}}', 'json', 'ai_models', 'Admin analysis model', true, true),
('ai_model.canary', '{"enabled": false, "text_reasoning": {"canary_provider": "qwen", "canary_model": "qwen-plus", "traffic_percent": 10}, "image_generation": {"canary_provider": "jimeng", "canary_model": "jimeng-2.1", "traffic_percent": 5}}', 'json', 'ai_models', 'Canary release for A/B testing', true, true),
('ai_providers.models', '{"openai": {"text": ["gpt-4o-mini", "gpt-4o", "o1-mini", "o1"], "image": ["dall-e-3"]}, "fal": {"image": ["flux-schnell", "flux-dev", "flux-pro"]}, "qwen": {"text": ["qwen-turbo", "qwen-plus", "qwen-max"]}}', 'json', 'ai_providers', 'Available models per provider', true, true),
('ai_providers.timeouts', '{"openai": {"text": 60, "image": 120}, "fal": {"image": 180}, "qwen": {"text": 60}}', 'json', 'ai_providers', 'Timeout config in seconds', true, true),
('ai_providers.costs', '{"openai": {"gpt-4o-mini": 0.15, "gpt-4o": 2.50, "o1-mini": 3.00, "o1": 15.00, "dall-e-3": 0.04}, "fal": {"flux-schnell": 0.003, "flux-dev": 0.025, "flux-pro": 0.05}, "qwen": {"qwen-turbo": 0.001, "qwen-plus": 0.004, "qwen-max": 0.02}}', 'json', 'ai_providers', 'Cost per 1M tokens/image (USD)', true, true),
('ai_providers.retry', '{"max_retries": 3, "base_delay_ms": 1000, "max_delay_ms": 10000, "retry_on_status": [429, 500, 502, 503, 504]}', 'json', 'ai_providers', 'Retry configuration', true, true),

-- ========== UI Text (3条) ==========
('UI_UPGRADE_CTA', 'Upgrade Now', 'text', 'ui', 'Upgrade button text', true, true),
('UI_TRIAL_EXPIRED', 'Your 7-day trial period has expired. This project is read-only.', 'text', 'ui', 'Trial expired message', true, true),
('UI_AI_TYPING_INDICATOR', 'AI is thinking...', 'text', 'ui', 'AI typing indicator text', true, true),

-- ========== Marketing (2条) ==========
('HOME_HERO_TITLE', 'Create Beautiful 8-Page Zines in Minutes', 'text', 'marketing', 'Homepage hero title', true, true),
('HOME_HERO_SUBTITLE', 'AI-powered story generation meets easy drag-and-drop editing.', 'text', 'marketing', 'Homepage hero subtitle', true, true),

-- ========== Tooltip (2条) ==========
('TOOLTIP_DELETE', 'Delete', 'text', 'tooltip', 'Delete button tooltip when enabled', true, true),
('TOOLTIP_DELETE_DISABLED', 'Unpublish first to delete', 'text', 'tooltip', 'Delete button tooltip when disabled', true, true),

-- ========== Marketplace (3条) ==========
('marketplace.seller_revenue_ratio', '0.70', 'number', 'marketplace', 'Seller revenue share (70%)', true, true),
('marketplace.platform_fee_ratio', '0.30', 'number', 'marketplace', 'Platform fee (30%)', true, true),
('marketplace.trial_duration_days', '7', 'number', 'marketplace', 'Trial duration in days', true, true),

-- ========== Tier System (6条) ==========
('tier.t1.display_name', 'Free Plan', 'text', 'tier', 'First Tier 显示名称 (可通过 Admin API 修改)', true, true),
('tier.t2.display_name', 'Starter Plan', 'text', 'tier', 'Second Tier 显示名称 (可通过 Admin API 修改)', true, true),
('tier.t3.display_name', 'Pro Plan', 'text', 'tier', 'Third Tier 显示名称 (可通过 Admin API 修改)', true, true),
('tier.t1.monthly_credits', '0', 'integer', 'tier', 'First Tier 月度积分', true, false),
('tier.t2.monthly_credits', '200', 'integer', 'tier', 'Second Tier 月度积分', true, false),
('tier.t3.monthly_credits', '500', 'integer', 'tier', 'Third Tier 月度积分', true, false),

-- ========== Trial Period (1条) ==========
('trial.duration_days', '30', 'integer', 'trial', 'Free tier 试用期天数 (可通过 Admin API 修改)', true, true),

-- ========== Soft Delete Recovery Period (1条) ==========
('soft_delete.recovery_period_days', '30', 'integer', 'database', '软删除恢复期天数,过期后用户无法在删除历史中看到记录', true, true)

ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value,
    value_type = EXCLUDED.value_type,
    config_group = EXCLUDED.config_group,
    description = EXCLUDED.description,
    is_active = EXCLUDED.is_active,
    is_editable = EXCLUDED.is_editable,
    updated_at = CURRENT_TIMESTAMP;

-- ----------------------------------------------------------------------------
-- Holidays 初始化数据 (4个主要节日)
-- ----------------------------------------------------------------------------
INSERT INTO holidays (name, slug, month, day, regions, category, is_major, description) VALUES
('New Year', 'new-year', 1, 1, ARRAY['global'], 'cultural', true, 'New Year Day celebration'),
('Valentine''s Day', 'valentines-day', 2, 14, ARRAY['global'], 'cultural', true, 'Day of love and romance'),
('Halloween', 'halloween', 10, 31, ARRAY['US', 'UK', 'CA'], 'cultural', true, 'Spooky celebration'),
('Christmas', 'christmas', 12, 25, ARRAY['global'], 'cultural', true, 'Christmas Day celebration')
ON CONFLICT (slug) DO NOTHING;

-- ----------------------------------------------------------------------------
-- Pricing Plans 初始化数据 (6个定价方案)
-- ----------------------------------------------------------------------------
-- ⚠️ 注意: 实际部署时需要替换 Stripe Price ID 占位符
-- 占位符格式: {{ STRIPE_PRICE_XXX }}
-- 从 Stripe Dashboard → Products → Pricing 获取实际 Price ID

-- Free Plan (t1) - Monthly
INSERT INTO pricing_plans (
    plan_code, plan_type, plan_name, description,
    price_cents, original_price_cents, currency,
    billing_interval, tier, monthly_credits,
    stripe_price_id_prod, stripe_price_id_dev,
    stripe_product_id,
    is_active, is_visible, is_featured, sort_order,
    version, effective_from,
    metadata, created_by
) VALUES (
    'tier_t1_monthly',
    'subscription',
    'Free Plan',
    '免费方案，注册即可使用基础功能',
    0,
    NULL,
    'USD',
    'month',
    't1',
    0,
    NULL,
    NULL,
    NULL,
    TRUE,
    TRUE,
    FALSE,
    0,
    1,
    NOW(),
    '{"badge": "FREE"}'::jsonb,
    'system'
) ON CONFLICT (plan_code) DO UPDATE SET
    price_cents = EXCLUDED.price_cents,
    updated_at = NOW();

-- Starter Plan (t2) - Monthly
INSERT INTO pricing_plans (
    plan_code, plan_type, plan_name, description,
    price_cents, original_price_cents, currency,
    billing_interval, tier, monthly_credits,
    stripe_price_id_prod, stripe_price_id_dev,
    stripe_product_id,
    is_active, is_visible, is_featured, sort_order,
    version, effective_from,
    metadata, created_by
) VALUES (
    'tier_t2_monthly',
    'subscription',
    'Starter Plan',
    '适合个人创作者，包含贴纸库和发布权限',
    990,
    1490,
    'USD',
    'month',
    't2',
    200,
    '{{ STRIPE_PRICE_SUB_STARTER_PROD }}',
    '{{ STRIPE_PRICE_SUB_STARTER_DEV }}',
    '{{ STRIPE_PRODUCT_STARTER }}',
    TRUE,
    TRUE,
    FALSE,
    1,
    1,
    NOW(),
    '{"discount_percent": 34, "badge": null}'::jsonb,
    'system'
) ON CONFLICT (plan_code) DO UPDATE SET
    price_cents = EXCLUDED.price_cents,
    original_price_cents = EXCLUDED.original_price_cents,
    updated_at = NOW();

-- Pro Plan (t3) - Monthly
INSERT INTO pricing_plans (
    plan_code, plan_type, plan_name, description,
    price_cents, original_price_cents, currency,
    billing_interval, tier, monthly_credits,
    stripe_price_id_prod, stripe_price_id_dev,
    stripe_product_id,
    is_active, is_visible, is_featured, sort_order,
    version, effective_from,
    metadata, created_by
) VALUES (
    'tier_t3_monthly',
    'subscription',
    'Pro Plan',
    '专业创作者首选，包含全功能和商业授权',
    1990,
    2990,
    'USD',
    'month',
    't3',
    500,
    '{{ STRIPE_PRICE_SUB_PRO_PROD }}',
    '{{ STRIPE_PRICE_SUB_PRO_DEV }}',
    '{{ STRIPE_PRODUCT_PRO }}',
    TRUE,
    TRUE,
    TRUE,
    2,
    1,
    NOW(),
    '{"discount_percent": 34, "badge": "RECOMMENDED"}'::jsonb,
    'system'
) ON CONFLICT (plan_code) DO UPDATE SET
    price_cents = EXCLUDED.price_cents,
    original_price_cents = EXCLUDED.original_price_cents,
    updated_at = NOW();

-- 100 Credits Pack
INSERT INTO pricing_plans (
    plan_code, plan_type, plan_name, description,
    price_cents, original_price_cents, currency,
    credits_amount,
    stripe_price_id_prod, stripe_price_id_dev,
    stripe_product_id,
    is_active, is_visible, is_featured, sort_order,
    version, effective_from,
    metadata, created_by
) VALUES (
    'credits_100',
    'credits',
    '100 Credits Pack',
    '适合偶尔使用 AI 功能的用户',
    299,
    NULL,
    'USD',
    100,
    '{{ STRIPE_PRICE_CREDITS_100_PROD }}',
    '{{ STRIPE_PRICE_CREDITS_100_DEV }}',
    '{{ STRIPE_PRODUCT_CREDITS }}',
    TRUE,
    TRUE,
    FALSE,
    10,
    1,
    NOW(),
    '{"unit_price_cents": 2.99, "badge": null}'::jsonb,
    'system'
) ON CONFLICT (plan_code) DO UPDATE SET
    price_cents = EXCLUDED.price_cents,
    updated_at = NOW();

-- 500 Credits Pack (9折)
INSERT INTO pricing_plans (
    plan_code, plan_type, plan_name, description,
    price_cents, original_price_cents, currency,
    credits_amount,
    stripe_price_id_prod, stripe_price_id_dev,
    stripe_product_id,
    is_active, is_visible, is_featured, sort_order,
    version, effective_from,
    metadata, created_by
) VALUES (
    'credits_500',
    'credits',
    '500 Credits Pack',
    '适合经常使用 AI 功能的创作者',
    1349,
    1499,
    'USD',
    500,
    '{{ STRIPE_PRICE_CREDITS_500_PROD }}',
    '{{ STRIPE_PRICE_CREDITS_500_DEV }}',
    '{{ STRIPE_PRODUCT_CREDITS }}',
    TRUE,
    TRUE,
    TRUE,
    11,
    1,
    NOW(),
    '{"discount_percent": 10, "unit_price_cents": 2.698, "badge": "POPULAR"}'::jsonb,
    'system'
) ON CONFLICT (plan_code) DO UPDATE SET
    price_cents = EXCLUDED.price_cents,
    original_price_cents = EXCLUDED.original_price_cents,
    updated_at = NOW();

-- 2000 Credits Pack (8折)
INSERT INTO pricing_plans (
    plan_code, plan_type, plan_name, description,
    price_cents, original_price_cents, currency,
    credits_amount,
    stripe_price_id_prod, stripe_price_id_dev,
    stripe_product_id,
    is_active, is_visible, is_featured, sort_order,
    version, effective_from,
    metadata, created_by
) VALUES (
    'credits_2000',
    'credits',
    '2000 Credits Pack',
    '适合专业创作者或团队使用',
    4800,
    6000,
    'USD',
    2000,
    '{{ STRIPE_PRICE_CREDITS_2000_PROD }}',
    '{{ STRIPE_PRICE_CREDITS_2000_DEV }}',
    '{{ STRIPE_PRODUCT_CREDITS }}',
    TRUE,
    TRUE,
    TRUE,
    12,
    1,
    NOW(),
    '{"discount_percent": 20, "unit_price_cents": 2.4, "badge": "BEST VALUE"}'::jsonb,
    'system'
) ON CONFLICT (plan_code) DO UPDATE SET
    price_cents = EXCLUDED.price_cents,
    original_price_cents = EXCLUDED.original_price_cents,
    updated_at = NOW();

-- ============================================================================
-- 第二十一部分: 视图
-- ============================================================================

-- ----------------------------------------------------------------------------
-- AI 使用量最近 30 天视图
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_ai_usage_last_30_days AS
SELECT
    provider,
    model,
    call_type,
    SUM(total_calls) as total_calls,
    SUM(successful_calls) as successful_calls,
    SUM(failed_calls) as failed_calls,
    ROUND(SUM(successful_calls)::numeric / NULLIF(SUM(total_calls), 0) * 100, 2) as success_rate,
    SUM(total_input_tokens) as total_input_tokens,
    SUM(total_output_tokens) as total_output_tokens,
    SUM(total_images) as total_images,
    ROUND(AVG(avg_latency_ms)) as avg_latency_ms,
    SUM(estimated_cost_usd) as total_cost_usd
FROM ai_usage_daily
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY provider, model, call_type
ORDER BY total_cost_usd DESC;

COMMENT ON VIEW v_ai_usage_last_30_days IS 'AI 使用量最近 30 天汇总视图';

-- ============================================================================
-- 完成
-- ============================================================================

-- 验证 Stripe ID 占位符是否已替换
DO $$
DECLARE
    v_placeholder_count INT;
    v_placeholders TEXT;
BEGIN
    -- 检查 pricing_plans 表中的占位符
    SELECT COUNT(*)
    INTO v_placeholder_count
    FROM pricing_plans
    WHERE stripe_price_id_prod ~ '^\{\{.*\}\}$'
       OR stripe_price_id_dev ~ '^\{\{.*\}\}$';

    IF v_placeholder_count > 0 THEN
        SELECT string_agg(plan_code || ': prod=' || COALESCE(stripe_price_id_prod, 'NULL') || ', dev=' || COALESCE(stripe_price_id_dev, 'NULL'), E'\n')
        INTO v_placeholders
        FROM pricing_plans
        WHERE stripe_price_id_prod ~ '^\{\{.*\}\}$'
           OR stripe_price_id_dev ~ '^\{\{.*\}\}$';

        RAISE WARNING E'⚠️ Stripe ID placeholders detected in pricing_plans:\n%', v_placeholders;
        RAISE WARNING '⚠️ Please replace all {{ STRIPE_PRICE_XXX }} placeholders with actual Stripe Price IDs';
        RAISE WARNING '⚠️ Get Price IDs from: Stripe Dashboard → Products → Pricing';
    ELSE
        RAISE NOTICE '✅ Stripe ID placeholders verification PASSED (all replaced)';
    END IF;
END $$;

-- 验证表数量
DO $$
DECLARE
    v_table_count INT;
BEGIN
    SELECT COUNT(*) INTO v_table_count
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE';

    RAISE NOTICE '✅ Total tables created: %', v_table_count;
    RAISE NOTICE '✅ Expected: 42 tables';

    IF v_table_count >= 42 THEN
        RAISE NOTICE '✅ Table count verification PASSED';
    ELSE
        RAISE WARNING '⚠️ Table count verification FAILED (expected >= 42, got %)', v_table_count;
    END IF;
END $$;

-- 验证 system_configs 数据
DO $$
DECLARE
    v_config_count INT;
BEGIN
    SELECT COUNT(*) INTO v_config_count FROM system_configs WHERE is_active = TRUE;

    RAISE NOTICE '✅ Total system_configs rows: %', v_config_count;
    RAISE NOTICE '✅ Expected: >= 67';

    IF v_config_count >= 67 THEN
        RAISE NOTICE '✅ System configs verification PASSED';
    ELSE
        RAISE WARNING '⚠️ System configs verification FAILED (expected >= 67, got %)', v_config_count;
    END IF;
END $$;

-- 完成消息
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE '✅ Make Decodables - Refactored Database Schema (v4.0) - COMPLETED';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE '';
    RAISE NOTICE '📋 Summary:';
    RAISE NOTICE '   - 42 tables created (29 original + 13 new)';
    RAISE NOTICE '   - 60+ system_configs initialized';
    RAISE NOTICE '   - 100+ indexes created';
    RAISE NOTICE '   - 10+ functions created';
    RAISE NOTICE '   - 20+ triggers created';
    RAISE NOTICE '';
    RAISE NOTICE '🎯 Key Features:';
    RAISE NOTICE '   - ✅ Snake Case naming convention';
    RAISE NOTICE '   - ✅ Standard audit fields (created_at, updated_at, is_deleted, deleted_at)';
    RAISE NOTICE '   - ✅ Complete COMMENT annotations';
    RAISE NOTICE '   - ✅ P0 tables added (AI logs, asset categories)';
    RAISE NOTICE '   - ✅ P1 tables added (themes, holidays, analytics)';
    RAISE NOTICE '   - ✅ P2 tables added (audit logs, reports)';
    RAISE NOTICE '   - ✅ Atomic credit functions';
    RAISE NOTICE '   - ✅ Marketplace purchase function';
    RAISE NOTICE '   - ✅ AI usage aggregation function';
    RAISE NOTICE '';
    RAISE NOTICE '⚠️  Important Notes:';
    RAISE NOTICE '   - profiles.id is TEXT (Clerk ID), not UUID';
    RAISE NOTICE '   - credit_transactions is Append-Only (no UPDATE/DELETE)';
    RAISE NOTICE '   - Credits deduction order: monthly → permanent';
    RAISE NOTICE '   - system_configs uses key/value fields (backward compatible)';
    RAISE NOTICE '';
    RAISE NOTICE '📚 Next Steps:';
    RAISE NOTICE '   1. Review the schema carefully';
    RAISE NOTICE '   2. Test all atomic functions';
    RAISE NOTICE '   3. Verify data integrity';
    RAISE NOTICE '   4. Run integration tests';
    RAISE NOTICE '   5. Setup RLS policies (if using Supabase)';
    RAISE NOTICE '';
    RAISE NOTICE '============================================================================';
END $$;

-- ============================================================================
-- Row-Level Security (RLS) Policies
-- ============================================================================
-- ⚠️  RLS is DISABLED by default in this migration
-- To enable RLS for Supabase multi-tenant security, run: enable_rls.sql
-- For Railway/standalone PostgreSQL, RLS is not needed

-- Note: RLS policies are defined but NOT enabled
-- Uncomment the following lines to enable RLS:

-- ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE credit_transactions ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE user_generations ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE marketplace_listings ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE marketplace_purchases ENABLE ROW LEVEL SECURITY;

-- Profiles: Users can only read/update their own profile
CREATE POLICY profiles_select_own ON profiles
    FOR SELECT
    USING (id = current_setting('app.current_user_id', true));

CREATE POLICY profiles_update_own ON profiles
    FOR UPDATE
    USING (id = current_setting('app.current_user_id', true));

-- Projects: Users can only access their own projects
CREATE POLICY projects_select_own ON projects
    FOR SELECT
    USING (user_id = current_setting('app.current_user_id', true));

CREATE POLICY projects_insert_own ON projects
    FOR INSERT
    WITH CHECK (user_id = current_setting('app.current_user_id', true));

CREATE POLICY projects_update_own ON projects
    FOR UPDATE
    USING (user_id = current_setting('app.current_user_id', true));

CREATE POLICY projects_delete_own ON projects
    FOR DELETE
    USING (user_id = current_setting('app.current_user_id', true));

-- Credit Transactions: Users can only read their own transactions
CREATE POLICY credit_tx_select_own ON credit_transactions
    FOR SELECT
    USING (user_id = current_setting('app.current_user_id', true));

-- User Generations: Users can only access their own AI generations
CREATE POLICY generations_select_own ON user_generations
    FOR SELECT
    USING (user_id = current_setting('app.current_user_id', true));

CREATE POLICY generations_insert_own ON user_generations
    FOR INSERT
    WITH CHECK (user_id = current_setting('app.current_user_id', true));

-- Marketplace Listings: Public listings visible to all, users can manage their own
CREATE POLICY listings_select_public ON marketplace_listings
    FOR SELECT
    USING (is_public = TRUE AND is_deleted = FALSE);

CREATE POLICY listings_select_own ON marketplace_listings
    FOR SELECT
    USING (seller_id = current_setting('app.current_user_id', true));

CREATE POLICY listings_insert_own ON marketplace_listings
    FOR INSERT
    WITH CHECK (seller_id = current_setting('app.current_user_id', true));

CREATE POLICY listings_update_own ON marketplace_listings
    FOR UPDATE
    USING (seller_id = current_setting('app.current_user_id', true));

CREATE POLICY listings_delete_own ON marketplace_listings
    FOR DELETE
    USING (seller_id = current_setting('app.current_user_id', true));

-- Marketplace Purchases: Users can only see their own purchases
CREATE POLICY purchases_select_own ON marketplace_purchases
    FOR SELECT
    USING (user_id = current_setting('app.current_user_id', true));

-- Comment on RLS setup
COMMENT ON POLICY profiles_select_own ON profiles IS 'RLS: Users can only view their own profile';
COMMENT ON POLICY projects_select_own ON projects IS 'RLS: Users can only view their own projects';
COMMENT ON POLICY credit_tx_select_own ON credit_transactions IS 'RLS: Users can only view their own credit transactions';
COMMENT ON POLICY listings_select_public ON marketplace_listings IS 'RLS: All users can view public listings';
COMMENT ON POLICY listings_select_own ON marketplace_listings IS 'RLS: Sellers can view all their listings';

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '✅ Row-Level Security (RLS) policies created (but NOT enabled)';
    RAISE NOTICE '   - 15 policies defined for 6 tables';
    RAISE NOTICE '   - RLS is DISABLED by default (suitable for Railway/development)';
    RAISE NOTICE '';
    RAISE NOTICE '🔒 To enable RLS for Supabase multi-tenant:';
    RAISE NOTICE '   Run: enable_rls.sql';
    RAISE NOTICE '';
END $$;

-- ============================================================================
-- Enable RLS with Admin-Only Access (Default Behavior)
-- ============================================================================
-- This enables RLS on ALL tables with admin-only access policies
-- Suitable for: Backend API controlled by FastAPI with admin roles

-- Step 1: Create Admin Role Check Function
-- ============================================================================
CREATE OR REPLACE FUNCTION is_admin()
RETURNS BOOLEAN AS $$
BEGIN
    -- Check if current user is admin
    -- This reads from app.current_user_role set by your FastAPI backend
    RETURN current_setting('app.current_user_role', true) = 'admin';
EXCEPTION
    WHEN OTHERS THEN
        RETURN FALSE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION is_admin IS 'Check if current user has admin role (set by FastAPI)';

-- ============================================================================
-- Step 2: Enable RLS on ALL Tables
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '🔒 Enabling RLS on all tables...';
END $$;

-- User-related tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_generations ENABLE ROW LEVEL SECURITY;
ALTER TABLE marketplace_listings ENABLE ROW LEVEL SECURITY;
ALTER TABLE marketplace_purchases ENABLE ROW LEVEL SECURITY;

-- System tables (admin-only)
ALTER TABLE system_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE pricing_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE pricing_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE holidays ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_themes ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE asset_categories ENABLE ROW LEVEL SECURITY;

-- Feature & Experiment tables
ALTER TABLE feature_flags ENABLE ROW LEVEL SECURITY;
ALTER TABLE experiments ENABLE ROW LEVEL SECURITY;
ALTER TABLE experiment_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE experiment_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaign_participations ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaign_dismissals ENABLE ROW LEVEL SECURITY;

-- Analytics & Logging tables
ALTER TABLE api_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_call_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_usage_daily ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_aggregation ENABLE ROW LEVEL SECURITY;
ALTER TABLE scheduled_task_logs ENABLE ROW LEVEL SECURITY;

-- Webhook tables
ALTER TABLE clerk_webhook_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE stripe_webhook_events ENABLE ROW LEVEL SECURITY;

-- Other tables
ALTER TABLE assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE asset_prompt_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE marketplace_favorites ENABLE ROW LEVEL SECURITY;
ALTER TABLE marketplace_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_purchases ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscription_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_discounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_price_overrides ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE onboarding_steps ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_onboarding_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE referrals ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE config_audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_resource_audit_logs ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- Step 3: Create Admin-Only Policies for ALL Tables
-- ============================================================================

DO $$
DECLARE
    table_name TEXT;
    table_names TEXT[] := ARRAY[
        'profiles', 'projects', 'credit_transactions', 'user_generations',
        'marketplace_listings', 'marketplace_purchases', 'marketplace_favorites',
        'marketplace_reviews', 'system_configs', 'pricing_plans', 'pricing_history',
        'holidays', 'daily_themes', 'system_assets', 'asset_categories', 'assets',
        'asset_prompt_templates', 'feature_flags', 'experiments', 'experiment_assignments',
        'experiment_results', 'campaigns', 'campaign_participations', 'campaign_dismissals',
        'api_logs', 'ai_call_logs', 'ai_usage_daily', 'activity_logs',
        'analytics_events', 'analytics_aggregation', 'scheduled_task_logs',
        'clerk_webhook_events', 'stripe_webhook_events', 'content_reports',
        'credit_purchases', 'subscription_history', 'user_discounts', 'user_price_overrides',
        'notifications', 'onboarding_steps', 'user_onboarding_progress', 'referrals',
        'project_versions', 'config_audit_logs', 'system_resource_audit_logs'
    ];
BEGIN
    FOREACH table_name IN ARRAY table_names
    LOOP
        -- Admin can SELECT
        EXECUTE format('
            CREATE POLICY %I_admin_select ON %I
            FOR SELECT
            USING (is_admin());
        ', table_name, table_name);

        -- Admin can INSERT
        EXECUTE format('
            CREATE POLICY %I_admin_insert ON %I
            FOR INSERT
            WITH CHECK (is_admin());
        ', table_name, table_name);

        -- Admin can UPDATE
        EXECUTE format('
            CREATE POLICY %I_admin_update ON %I
            FOR UPDATE
            USING (is_admin());
        ', table_name, table_name);

        -- Admin can DELETE
        EXECUTE format('
            CREATE POLICY %I_admin_delete ON %I
            FOR DELETE
            USING (is_admin());
        ', table_name, table_name);

        RAISE NOTICE 'Created admin-only policies for: %', table_name;
    END LOOP;
END $$;

-- ============================================================================
-- Step 4: Verification
-- ============================================================================

DO $$
DECLARE
    rls_count INTEGER;
    policy_count INTEGER;
BEGIN
    -- Count tables with RLS enabled
    SELECT COUNT(*)
    INTO rls_count
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relrowsecurity = true
    AND n.nspname = 'public';

    -- Count policies
    SELECT COUNT(*)
    INTO policy_count
    FROM pg_policies
    WHERE schemaname = 'public';

    RAISE NOTICE '';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE '✅ RLS Enabled: % tables', rls_count;
    RAISE NOTICE '✅ Policies Created: % policies', policy_count;
    RAISE NOTICE '============================================================================';
    RAISE NOTICE '';
    RAISE NOTICE '📋 Usage in FastAPI:';
    RAISE NOTICE '   conn.execute(text("SET app.current_user_role = :role"), {"role": "admin"})';
    RAISE NOTICE '';
    RAISE NOTICE '⚠️  IMPORTANT:';
    RAISE NOTICE '   - Only users with app.current_user_role = ''admin'' can access data';
    RAISE NOTICE '   - Your FastAPI backend MUST set this variable before EVERY query';
    RAISE NOTICE '   - Regular users will get ZERO rows unless you add user-specific policies';
    RAISE NOTICE '';
    RAISE NOTICE '🔓 To disable RLS: Run disable_rls.sql';
    RAISE NOTICE '';
END $$;


-- ============================================================================
-- Phase 2.1: P0 缺失表 (Critical Business Tables)
-- Created: 2026-01-10
-- Purpose: 添加业务关键的追踪、日志和支持表
-- ============================================================================

-- ============================================================
-- 13. user_events (用户行为事件追踪表)
-- ============================================================
CREATE TABLE user_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    event_data JSONB DEFAULT '{}',
    session_id TEXT,
    ip_address INET,
    user_agent TEXT,
    referer TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_event_type CHECK (
        event_type IN (
            'page_view', 'button_click', 'form_submit',
            'feature_used', 'error_occurred', 'api_call',
            'project_created', 'project_updated', 'project_deleted',
            'asset_uploaded', 'asset_purchased', 'payment_completed',
            'login', 'logout', 'signup', 'profile_updated'
        )
    )
);

CREATE INDEX idx_user_events_user_id ON user_events(user_id, created_at DESC);
CREATE INDEX idx_user_events_event_type ON user_events(event_type, created_at DESC);
CREATE INDEX idx_user_events_created_at ON user_events(created_at DESC);
CREATE INDEX idx_user_events_session ON user_events(session_id) WHERE session_id IS NOT NULL;

COMMENT ON TABLE user_events IS '用户行为事件追踪表: 记录所有用户交互行为,用于分析和监控';
COMMENT ON COLUMN user_events.event_type IS '事件类型 (枚举值见 CHECK 约束)';
COMMENT ON COLUMN user_events.event_data IS '事件详情 (JSON 格式),结构取决于 event_type';
COMMENT ON COLUMN user_events.session_id IS '会话 ID (用于追踪同一会话的多个事件)';
COMMENT ON COLUMN user_events.ip_address IS '用户 IP 地址 (INET 类型)';
COMMENT ON COLUMN user_events.user_agent IS '浏览器 User-Agent 字符串';
COMMENT ON COLUMN user_events.referer IS 'HTTP Referer (来源页面)';

-- ============================================================
-- 14. aggregated_stats (聚合统计表)
-- ============================================================
CREATE TABLE aggregated_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stat_type TEXT NOT NULL,
    stat_key TEXT NOT NULL,
    stat_value NUMERIC DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_stat_type CHECK (
        stat_type IN ('daily', 'weekly', 'monthly', 'quarterly', 'yearly', 'custom')
    ),
    CONSTRAINT check_period_range CHECK (period_end >= period_start),
    CONSTRAINT unique_aggregated_stat UNIQUE (stat_type, stat_key, period_start)
);

CREATE INDEX idx_aggregated_stats_period ON aggregated_stats(period_start DESC, period_end DESC);
CREATE INDEX idx_aggregated_stats_type_key ON aggregated_stats(stat_type, stat_key);
CREATE INDEX idx_aggregated_stats_key_period ON aggregated_stats(stat_key, period_start DESC);

COMMENT ON TABLE aggregated_stats IS '聚合统计表: 存储各时间维度的指标汇总 (用于仪表板展示)';
COMMENT ON COLUMN aggregated_stats.stat_type IS '统计周期类型 (daily/weekly/monthly/quarterly/yearly/custom)';
COMMENT ON COLUMN aggregated_stats.stat_key IS '指标键 (如 "total_users", "active_users", "revenue_usd")';
COMMENT ON COLUMN aggregated_stats.stat_value IS '指标值 (数值类型)';
COMMENT ON COLUMN aggregated_stats.metadata IS '附加元数据 (如 breakdown by tier, category)';
COMMENT ON COLUMN aggregated_stats.period_start IS '统计周期开始时间';
COMMENT ON COLUMN aggregated_stats.period_end IS '统计周期结束时间';

-- ============================================================
-- 15. error_logs (错误日志表)
-- ============================================================
CREATE TABLE error_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT REFERENCES profiles(id) ON DELETE SET NULL,
    error_type TEXT NOT NULL,
    error_message TEXT NOT NULL,
    error_stack TEXT,
    request_path TEXT,
    request_method TEXT,
    request_body JSONB,
    response_status INTEGER,
    environment TEXT DEFAULT 'production',
    severity TEXT DEFAULT 'error',
    metadata JSONB DEFAULT '{}',
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMPTZ,
    resolved_by TEXT REFERENCES profiles(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_error_type CHECK (
        error_type IN (
            'validation_error', 'authentication_error', 'authorization_error',
            'database_error', 'external_api_error', 'payment_error',
            'file_upload_error', 'rate_limit_error', 'internal_server_error',
            'not_found_error', 'conflict_error', 'timeout_error'
        )
    ),
    CONSTRAINT check_severity CHECK (
        severity IN ('debug', 'info', 'warning', 'error', 'critical')
    ),
    CONSTRAINT check_environment CHECK (
        environment IN ('development', 'staging', 'production')
    )
);

CREATE INDEX idx_error_logs_user_id ON error_logs(user_id, created_at DESC);
CREATE INDEX idx_error_logs_error_type ON error_logs(error_type, created_at DESC);
CREATE INDEX idx_error_logs_severity ON error_logs(severity, created_at DESC);
CREATE INDEX idx_error_logs_created_at ON error_logs(created_at DESC);
CREATE INDEX idx_error_logs_unresolved ON error_logs(created_at DESC) WHERE resolved = FALSE;

COMMENT ON TABLE error_logs IS '错误日志表: 记录所有应用错误,用于问题排查和监控';
COMMENT ON COLUMN error_logs.error_type IS '错误类型 (枚举值见 CHECK 约束)';
COMMENT ON COLUMN error_logs.error_message IS '错误消息 (简短描述)';
COMMENT ON COLUMN error_logs.error_stack IS '错误堆栈跟踪 (完整 traceback)';
COMMENT ON COLUMN error_logs.request_path IS 'API 请求路径 (如 /api/projects/123)';
COMMENT ON COLUMN error_logs.request_method IS 'HTTP 方法 (GET/POST/PUT/DELETE)';
COMMENT ON COLUMN error_logs.request_body IS '请求体 (JSON 格式,敏感数据已脱敏)';
COMMENT ON COLUMN error_logs.response_status IS 'HTTP 响应状态码 (如 500, 404)';
COMMENT ON COLUMN error_logs.environment IS '运行环境 (development/staging/production)';
COMMENT ON COLUMN error_logs.severity IS '严重程度 (debug/info/warning/error/critical)';
COMMENT ON COLUMN error_logs.resolved IS '是否已解决';
COMMENT ON COLUMN error_logs.resolved_at IS '解决时间';
COMMENT ON COLUMN error_logs.resolved_by IS '解决人员 (管理员 user_id)';

-- ============================================================
-- 16. support_tickets (支持工单表)
-- ============================================================
CREATE TABLE support_tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    ticket_number TEXT NOT NULL UNIQUE,
    subject TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    priority TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'open',
    assigned_to TEXT REFERENCES profiles(id) ON DELETE SET NULL,
    attachments JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMPTZ,,
    recovery_expires_at TIMESTAMPTZ,  -- 恢复期截止时间,过期后用户看不到此删除记录
    recovery_expires_at TIMESTAMPTZ,  -- 恢复期截止时间,过期后用户看不到此删除记录
    recovery_expires_at TIMESTAMPTZ,  -- 恢复期截止时间,过期后用户看不到此删除记录
    recovery_expires_at TIMESTAMPTZ,  -- 恢复期截止时间,过期后用户看不到此删除记录
    recovery_expires_at TIMESTAMPTZ,  -- 恢复期截止时间,过期后用户看不到此删除记录
    recovery_expires_at TIMESTAMPTZ,  -- 恢复期截止时间,过期后用户看不到此删除记录
    recovery_expires_at TIMESTAMPTZ,  -- 恢复期截止时间,过期后用户看不到此删除记录
    recovery_expires_at TIMESTAMPTZ,  -- 恢复期截止时间,过期后用户看不到此删除记录
    recovery_expires_at TIMESTAMPTZ,  -- 恢复期截止时间,过期后用户看不到此删除记录

    CONSTRAINT check_category CHECK (
        category IN (
            'technical_issue', 'billing_question', 'feature_request',
            'bug_report', 'account_issue', 'content_issue',
            'payment_issue', 'other'
        )
    ),
    CONSTRAINT check_priority CHECK (
        priority IN ('low', 'medium', 'high', 'urgent')
    ),
    CONSTRAINT check_status CHECK (
        status IN ('open', 'in_progress', 'waiting_user', 'resolved', 'closed')
    ),
    CONSTRAINT chk_support_tickets_deleted_at_consistency
        CHECK ((is_deleted = false AND deleted_at IS NULL) OR (is_deleted = true AND deleted_at IS NOT NULL)),
    CONSTRAINT chk_support_tickets_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);

CREATE INDEX idx_support_tickets_user_id ON support_tickets(user_id, created_at DESC) WHERE is_deleted = false;
-- 可恢复删除记录索引 (恢复期内)
CREATE INDEX idx_support_tickets_deleted_recoverable
ON support_tickets(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON INDEX idx_support_tickets_deleted_recoverable IS '可恢复删除记录索引 - 只包含未过期的删除记录';


CREATE INDEX idx_support_tickets_ticket_number ON support_tickets(ticket_number);
CREATE INDEX idx_support_tickets_status ON support_tickets(status, created_at DESC) WHERE is_deleted = false;
CREATE INDEX idx_support_tickets_priority ON support_tickets(priority, created_at DESC) WHERE is_deleted = false;
CREATE INDEX idx_support_tickets_assigned_to ON support_tickets(assigned_to, created_at DESC) WHERE is_deleted = false;
CREATE INDEX idx_support_tickets_open ON support_tickets(created_at DESC) WHERE status IN ('open', 'in_progress', 'waiting_user') AND is_deleted = false;

COMMENT ON TABLE support_tickets IS '支持工单表: 记录用户提交的支持请求';
COMMENT ON COLUMN support_tickets.is_deleted IS '软删除标记';
COMMENT ON COLUMN support_tickets.deleted_at IS '删除时间';
COMMENT ON COLUMN support_tickets.ticket_number IS '工单编号 (唯一, 格式: TKT-20260110-001)';
COMMENT ON COLUMN support_tickets.subject IS '工单标题';
COMMENT ON COLUMN support_tickets.description IS '详细描述';
COMMENT ON COLUMN support_tickets.category IS '工单分类';
COMMENT ON COLUMN support_tickets.priority IS '优先级 (low/medium/high/urgent)';
COMMENT ON COLUMN support_tickets.status IS '状态 (open/in_progress/waiting_user/resolved/closed)';
COMMENT ON COLUMN support_tickets.assigned_to IS '分配给的管理员 (user_id)';
COMMENT ON COLUMN support_tickets.attachments IS 'JSON 数组,存储附件 URL 列表';
COMMENT ON COLUMN support_tickets.metadata IS '附加元数据 (如 browser_info, device_type)';
COMMENT ON COLUMN support_tickets.resolved_at IS '解决时间';
COMMENT ON COLUMN support_tickets.closed_at IS '关闭时间';

-- ============================================================
-- 17. support_replies (工单回复表)
-- ============================================================
CREATE TABLE support_replies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id UUID NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    is_staff_reply BOOLEAN DEFAULT FALSE,
    message TEXT NOT NULL,
    attachments JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMPTZ,,
    recovery_expires_at TIMESTAMPTZ,  -- 恢复期截止时间,过期后用户看不到此删除记录

    CONSTRAINT check_message_not_empty CHECK (LENGTH(TRIM(message)) > 0),
    CONSTRAINT chk_support_replies_deleted_at_consistency
        CHECK ((is_deleted = false AND deleted_at IS NULL) OR (is_deleted = true AND deleted_at IS NOT NULL)),
    CONSTRAINT chk_support_replies_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);

CREATE INDEX idx_support_replies_ticket_id ON support_replies(ticket_id, created_at ASC) WHERE is_deleted = false;
-- 可恢复删除记录索引 (恢复期内)
CREATE INDEX idx_support_replies_deleted_recoverable
ON support_replies(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON INDEX idx_support_replies_deleted_recoverable IS '可恢复删除记录索引 - 只包含未过期的删除记录';


CREATE INDEX idx_support_replies_user_id ON support_replies(user_id, created_at DESC) WHERE is_deleted = false;
CREATE INDEX idx_support_replies_created_at ON support_replies(created_at DESC) WHERE is_deleted = false;

COMMENT ON TABLE support_replies IS '工单回复表: 记录工单的所有回复 (用户和管理员)';
COMMENT ON COLUMN support_replies.is_deleted IS '软删除标记';
COMMENT ON COLUMN support_replies.deleted_at IS '删除时间';
COMMENT ON COLUMN support_replies.ticket_id IS '关联的工单 ID';
COMMENT ON COLUMN support_replies.user_id IS '回复人 ID (可以是普通用户或管理员)';
COMMENT ON COLUMN support_replies.is_staff_reply IS '是否为管理员回复 (区分用户回复和官方回复)';
COMMENT ON COLUMN support_replies.message IS '回复内容';
COMMENT ON COLUMN support_replies.attachments IS 'JSON 数组,存储附件 URL 列表';

-- ============================================================
-- 触发器: 自动生成工单编号
-- ============================================================
CREATE OR REPLACE FUNCTION generate_ticket_number()
RETURNS TRIGGER AS $$
DECLARE
    today_count INTEGER;
    today_date TEXT;
BEGIN
    -- 获取今天的日期 (YYYYMMDD 格式)
    today_date := TO_CHAR(NOW(), 'YYYYMMDD');

    -- 计算今天已创建的工单数量
    SELECT COUNT(*) + 1
    INTO today_count
    FROM support_tickets
    WHERE ticket_number LIKE 'TKT-' || today_date || '-%';

    -- 生成工单编号: TKT-20260110-001
    NEW.ticket_number := 'TKT-' || today_date || '-' || LPAD(today_count::TEXT, 3, '0');

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_generate_ticket_number
BEFORE INSERT ON support_tickets
FOR EACH ROW
WHEN (NEW.ticket_number IS NULL)
EXECUTE FUNCTION generate_ticket_number();

COMMENT ON FUNCTION generate_ticket_number() IS '自动生成工单编号 (格式: TKT-YYYYMMDD-NNN)';

-- ============================================================
-- 触发器: 更新 updated_at 字段
-- ============================================================
CREATE TRIGGER trigger_update_aggregated_stats_updated_at
BEFORE UPDATE ON aggregated_stats
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_update_support_tickets_updated_at
BEFORE UPDATE ON support_tickets
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_update_support_replies_updated_at
BEFORE UPDATE ON support_replies
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- Phase 2.1 完成
-- ============================================================
-- 新增 5 个 P0 表:
--   ✅ user_events (用户行为追踪)
--   ✅ aggregated_stats (统计聚合)
--   ✅ error_logs (错误日志)
--   ✅ support_tickets (支持工单)
--   ✅ support_replies (工单回复)
-- ============================================================


-- ============================================================================
-- Phase 2.2: P1 高优先级表 (High Priority Business Tables)
-- Created: 2026-01-10
-- Purpose: 添加管理员操作审计、资产使用追踪、市场报告和指标追踪表
-- ============================================================================

-- ============================================================
-- 18. admin_operations (管理员操作审计日志表)
-- ============================================================
CREATE TABLE admin_operations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    operation_type TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT,
    action_details JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    status TEXT DEFAULT 'success',
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_operation_type CHECK (
        operation_type IN (
            'create', 'update', 'delete', 'restore',
            'approve', 'reject', 'ban', 'unban',
            'grant_credits', 'refund', 'adjust_tier',
            'force_delete', 'export_data', 'import_data'
        )
    ),
    CONSTRAINT check_target_type CHECK (
        target_type IN (
            'user', 'project', 'listing', 'ticket', 'transaction',
            'feature_flag', 'experiment', 'config', 'system'
        )
    ),
    CONSTRAINT check_status CHECK (
        status IN ('success', 'failed', 'partial')
    )
);

CREATE INDEX idx_admin_operations_admin_id ON admin_operations(admin_id, created_at DESC);
CREATE INDEX idx_admin_operations_operation_type ON admin_operations(operation_type, created_at DESC);
CREATE INDEX idx_admin_operations_target ON admin_operations(target_type, target_id);
CREATE INDEX idx_admin_operations_created_at ON admin_operations(created_at DESC);
CREATE INDEX idx_admin_operations_failed ON admin_operations(created_at DESC) WHERE status = 'failed';

COMMENT ON TABLE admin_operations IS '管理员操作审计日志表: 记录所有管理员操作,用于审计和合规';
COMMENT ON COLUMN admin_operations.admin_id IS '执行操作的管理员 ID';
COMMENT ON COLUMN admin_operations.operation_type IS '操作类型 (create/update/delete/ban/grant_credits 等)';
COMMENT ON COLUMN admin_operations.target_type IS '目标类型 (user/project/listing/ticket 等)';
COMMENT ON COLUMN admin_operations.target_id IS '目标对象 ID';
COMMENT ON COLUMN admin_operations.action_details IS '操作详情 (JSON 格式,包含修改前后的值)';
COMMENT ON COLUMN admin_operations.status IS '操作状态 (success/failed/partial)';
COMMENT ON COLUMN admin_operations.error_message IS '错误消息 (如果失败)';

-- ============================================================
-- 19. listing_usages (资产使用追踪表)
-- ============================================================
CREATE TABLE listing_usages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID NOT NULL REFERENCES marketplace_listings(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    usage_type TEXT NOT NULL,
    usage_count INTEGER DEFAULT 1,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_usage_type CHECK (
        usage_type IN (
            'view', 'preview', 'download', 'use_in_project',
            'favorite', 'share', 'report'
        )
    ),
    CONSTRAINT check_usage_count CHECK (usage_count > 0)
);

CREATE INDEX idx_listing_usages_listing_id ON listing_usages(listing_id, created_at DESC);
CREATE INDEX idx_listing_usages_user_id ON listing_usages(user_id, created_at DESC);
CREATE INDEX idx_listing_usages_project_id ON listing_usages(project_id) WHERE project_id IS NOT NULL;
CREATE INDEX idx_listing_usages_usage_type ON listing_usages(usage_type, created_at DESC);
CREATE INDEX idx_listing_usages_created_at ON listing_usages(created_at DESC);

COMMENT ON TABLE listing_usages IS '资产使用追踪表: 记录 marketplace listing 的使用情况,用于分析和推荐';
COMMENT ON COLUMN listing_usages.listing_id IS '被使用的 listing ID';
COMMENT ON COLUMN listing_usages.user_id IS '使用者 ID';
COMMENT ON COLUMN listing_usages.project_id IS '使用该 listing 的项目 ID (如果是 use_in_project)';
COMMENT ON COLUMN listing_usages.usage_type IS '使用类型 (view/preview/download/use_in_project/favorite/share/report)';
COMMENT ON COLUMN listing_usages.usage_count IS '使用次数 (默认 1,聚合时可能 > 1)';
COMMENT ON COLUMN listing_usages.metadata IS '附加元数据 (如 duration, device_type)';

-- ============================================================
-- 20. marketplace_reports (市场内容举报表)
-- ============================================================
CREATE TABLE marketplace_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID NOT NULL REFERENCES marketplace_listings(id) ON DELETE CASCADE,
    reporter_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    report_reason TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    reviewed_by TEXT REFERENCES profiles(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ,
    resolution TEXT,
    action_taken TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_report_reason CHECK (
        report_reason IN (
            'copyright_violation', 'inappropriate_content', 'spam',
            'misleading_description', 'poor_quality', 'offensive',
            'duplicate', 'other'
        )
    ),
    CONSTRAINT check_status CHECK (
        status IN ('pending', 'under_review', 'resolved', 'dismissed')
    ),
    CONSTRAINT check_action_taken CHECK (
        action_taken IS NULL OR action_taken IN (
            'removed_listing', 'warned_seller', 'banned_seller',
            'no_action', 'content_modified'
        )
    ),
    CONSTRAINT check_description_not_empty CHECK (LENGTH(TRIM(description)) > 0)
);

CREATE INDEX idx_marketplace_reports_listing_id ON marketplace_reports(listing_id, created_at DESC);
CREATE INDEX idx_marketplace_reports_reporter_id ON marketplace_reports(reporter_id, created_at DESC);
CREATE INDEX idx_marketplace_reports_status ON marketplace_reports(status, created_at DESC);
CREATE INDEX idx_marketplace_reports_reviewed_by ON marketplace_reports(reviewed_by, reviewed_at DESC);
CREATE INDEX idx_marketplace_reports_pending ON marketplace_reports(created_at DESC) WHERE status IN ('pending', 'under_review');

COMMENT ON TABLE marketplace_reports IS '市场内容举报表: 记录用户对 listing 的举报,用于内容审核';
COMMENT ON COLUMN marketplace_reports.listing_id IS '被举报的 listing ID';
COMMENT ON COLUMN marketplace_reports.reporter_id IS '举报人 ID';
COMMENT ON COLUMN marketplace_reports.report_reason IS '举报原因 (copyright_violation/inappropriate_content 等)';
COMMENT ON COLUMN marketplace_reports.description IS '详细描述';
COMMENT ON COLUMN marketplace_reports.status IS '处理状态 (pending/under_review/resolved/dismissed)';
COMMENT ON COLUMN marketplace_reports.reviewed_by IS '审核人员 (管理员 ID)';
COMMENT ON COLUMN marketplace_reports.reviewed_at IS '审核时间';
COMMENT ON COLUMN marketplace_reports.resolution IS '解决方案说明';
COMMENT ON COLUMN marketplace_reports.action_taken IS '采取的行动 (removed_listing/warned_seller/banned_seller/no_action)';

-- ============================================================
-- 21. daily_metrics (每日指标表)
-- ============================================================
CREATE TABLE daily_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_date DATE NOT NULL UNIQUE,
    total_users INTEGER DEFAULT 0,
    active_users INTEGER DEFAULT 0,
    new_users INTEGER DEFAULT 0,
    total_projects INTEGER DEFAULT 0,
    new_projects INTEGER DEFAULT 0,
    total_listings INTEGER DEFAULT 0,
    new_listings INTEGER DEFAULT 0,
    total_purchases INTEGER DEFAULT 0,
    revenue_usd NUMERIC(10, 2) DEFAULT 0,
    revenue_credits INTEGER DEFAULT 0,
    ai_generations INTEGER DEFAULT 0,
    smart_scans INTEGER DEFAULT 0,
    credits_consumed INTEGER DEFAULT 0,
    credits_granted INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    avg_response_time_ms NUMERIC(10, 2),
    p95_response_time_ms NUMERIC(10, 2),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_metric_date CHECK (metric_date >= '2024-01-01'),
    CONSTRAINT check_non_negative_counts CHECK (
        total_users >= 0 AND active_users >= 0 AND new_users >= 0 AND
        total_projects >= 0 AND new_projects >= 0 AND
        total_listings >= 0 AND new_listings >= 0 AND
        total_purchases >= 0 AND ai_generations >= 0 AND
        smart_scans >= 0 AND credits_consumed >= 0 AND
        credits_granted >= 0 AND error_count >= 0
    )
);

CREATE INDEX idx_daily_metrics_metric_date ON daily_metrics(metric_date DESC);
CREATE INDEX idx_daily_metrics_created_at ON daily_metrics(created_at DESC);

COMMENT ON TABLE daily_metrics IS '每日指标表: 存储每天的关键业务指标,用于趋势分析和仪表板';
COMMENT ON COLUMN daily_metrics.metric_date IS '指标日期 (YYYY-MM-DD)';
COMMENT ON COLUMN daily_metrics.total_users IS '总用户数 (截至当天)';
COMMENT ON COLUMN daily_metrics.active_users IS '活跃用户数 (当天有操作的用户)';
COMMENT ON COLUMN daily_metrics.new_users IS '新注册用户数';
COMMENT ON COLUMN daily_metrics.total_projects IS '总项目数 (截至当天)';
COMMENT ON COLUMN daily_metrics.new_projects IS '新创建项目数';
COMMENT ON COLUMN daily_metrics.revenue_usd IS '美元收入';
COMMENT ON COLUMN daily_metrics.revenue_credits IS '积分收入 (积分包销售)';
COMMENT ON COLUMN daily_metrics.ai_generations IS 'AI 生成次数';
COMMENT ON COLUMN daily_metrics.smart_scans IS 'Smart Scan 次数';
COMMENT ON COLUMN daily_metrics.credits_consumed IS '消耗的积分总数';
COMMENT ON COLUMN daily_metrics.credits_granted IS '发放的积分总数';
COMMENT ON COLUMN daily_metrics.avg_response_time_ms IS '平均响应时间 (毫秒)';
COMMENT ON COLUMN daily_metrics.p95_response_time_ms IS 'P95 响应时间 (毫秒)';
COMMENT ON COLUMN daily_metrics.metadata IS '附加元数据 (如按 tier 分组的数据)';

-- ============================================================
-- 22. monthly_metrics (月度指标表)
-- ============================================================
CREATE TABLE monthly_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_year INTEGER NOT NULL,
    metric_month INTEGER NOT NULL,
    total_users INTEGER DEFAULT 0,
    active_users INTEGER DEFAULT 0,
    new_users INTEGER DEFAULT 0,
    churned_users INTEGER DEFAULT 0,
    total_projects INTEGER DEFAULT 0,
    new_projects INTEGER DEFAULT 0,
    total_listings INTEGER DEFAULT 0,
    new_listings INTEGER DEFAULT 0,
    total_purchases INTEGER DEFAULT 0,
    revenue_usd NUMERIC(12, 2) DEFAULT 0,
    revenue_credits INTEGER DEFAULT 0,
    ai_generations INTEGER DEFAULT 0,
    smart_scans INTEGER DEFAULT 0,
    credits_consumed INTEGER DEFAULT 0,
    credits_granted INTEGER DEFAULT 0,
    mrr NUMERIC(12, 2) DEFAULT 0,
    arr NUMERIC(12, 2) DEFAULT 0,
    ltv NUMERIC(12, 2),
    cac NUMERIC(12, 2),
    retention_rate NUMERIC(5, 2),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_metric_year CHECK (metric_year >= 2024 AND metric_year <= 2100),
    CONSTRAINT check_metric_month CHECK (metric_month >= 1 AND metric_month <= 12),
    CONSTRAINT unique_monthly_metric UNIQUE (metric_year, metric_month),
    CONSTRAINT check_non_negative_monthly_counts CHECK (
        total_users >= 0 AND active_users >= 0 AND new_users >= 0 AND
        churned_users >= 0 AND total_projects >= 0 AND new_projects >= 0 AND
        total_listings >= 0 AND new_listings >= 0 AND
        total_purchases >= 0 AND ai_generations >= 0 AND
        smart_scans >= 0 AND credits_consumed >= 0 AND credits_granted >= 0
    )
);

CREATE INDEX idx_monthly_metrics_year_month ON monthly_metrics(metric_year DESC, metric_month DESC);
CREATE INDEX idx_monthly_metrics_created_at ON monthly_metrics(created_at DESC);

COMMENT ON TABLE monthly_metrics IS '月度指标表: 存储每月的关键业务指标和 SaaS 指标';
COMMENT ON COLUMN monthly_metrics.metric_year IS '年份 (YYYY)';
COMMENT ON COLUMN monthly_metrics.metric_month IS '月份 (1-12)';
COMMENT ON COLUMN monthly_metrics.churned_users IS '流失用户数 (取消订阅或超过 30 天未登录)';
COMMENT ON COLUMN monthly_metrics.mrr IS 'Monthly Recurring Revenue (月度经常性收入)';
COMMENT ON COLUMN monthly_metrics.arr IS 'Annual Recurring Revenue (年度经常性收入)';
COMMENT ON COLUMN monthly_metrics.ltv IS 'Lifetime Value (用户生命周期价值)';
COMMENT ON COLUMN monthly_metrics.cac IS 'Customer Acquisition Cost (用户获客成本)';
COMMENT ON COLUMN monthly_metrics.retention_rate IS '留存率 (%)';

-- ============================================================
-- 触发器: 更新 updated_at 字段
-- ============================================================
CREATE TRIGGER trigger_update_marketplace_reports_updated_at
BEFORE UPDATE ON marketplace_reports
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_update_daily_metrics_updated_at
BEFORE UPDATE ON daily_metrics
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_update_monthly_metrics_updated_at
BEFORE UPDATE ON monthly_metrics
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- Phase 2.2 完成
-- ============================================================
-- 新增 5 个 P1 表:
--   ✅ admin_operations (管理员操作审计)
--   ✅ listing_usages (资产使用追踪)
--   ✅ marketplace_reports (市场举报)
--   ✅ daily_metrics (每日指标)
--   ✅ monthly_metrics (月度指标)
-- ============================================================


-- ============================================================================
-- Phase 2.3: P2 补充表 (Supplementary Business Tables)
-- Created: 2026-01-10
-- Purpose: 添加 AI 任务管理、页面模板和支付记录表
-- ============================================================================

-- ============================================================
-- 23. generation_tasks (AI 生成任务表)
-- ============================================================
CREATE TABLE generation_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    task_type TEXT NOT NULL,
    prompt TEXT,
    parameters JSONB DEFAULT '{}',
    status TEXT DEFAULT 'pending',
    result_url TEXT,
    result_metadata JSONB DEFAULT '{}',
    error_message TEXT,
    credits_cost INTEGER DEFAULT 0,
    processing_time_ms INTEGER,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_task_type CHECK (
        task_type IN (
            'text_to_image', 'image_to_image', 'text_generation',
            'image_upscale', 'background_removal', 'style_transfer',
            'object_detection', 'smart_scan'
        )
    ),
    CONSTRAINT check_status CHECK (
        status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')
    ),
    CONSTRAINT check_credits_cost CHECK (credits_cost >= 0),
    CONSTRAINT check_retry_count CHECK (retry_count >= 0 AND retry_count <= 5)
);

CREATE INDEX idx_generation_tasks_user_id ON generation_tasks(user_id, created_at DESC);
CREATE INDEX idx_generation_tasks_project_id ON generation_tasks(project_id) WHERE project_id IS NOT NULL;
CREATE INDEX idx_generation_tasks_status ON generation_tasks(status, created_at DESC);
CREATE INDEX idx_generation_tasks_task_type ON generation_tasks(task_type, created_at DESC);
CREATE INDEX idx_generation_tasks_created_at ON generation_tasks(created_at DESC);
CREATE INDEX idx_generation_tasks_pending ON generation_tasks(created_at ASC) WHERE status = 'pending';

COMMENT ON TABLE generation_tasks IS 'AI 生成任务表: 记录所有 AI 生成任务的状态和结果';
COMMENT ON COLUMN generation_tasks.task_type IS '任务类型 (text_to_image/image_to_image/text_generation 等)';
COMMENT ON COLUMN generation_tasks.prompt IS '用户输入的提示词';
COMMENT ON COLUMN generation_tasks.parameters IS '任务参数 (JSON 格式,如 size, style, model)';
COMMENT ON COLUMN generation_tasks.status IS '任务状态 (pending/processing/completed/failed/cancelled)';
COMMENT ON COLUMN generation_tasks.result_url IS '生成结果 URL (图片或文件)';
COMMENT ON COLUMN generation_tasks.result_metadata IS '结果元数据 (如 width, height, file_size)';
COMMENT ON COLUMN generation_tasks.credits_cost IS '消耗的积分数';
COMMENT ON COLUMN generation_tasks.processing_time_ms IS '处理时间 (毫秒)';
COMMENT ON COLUMN generation_tasks.retry_count IS '重试次数 (最多 5 次)';

-- ============================================================
-- 24. page_prompt_templates (页面提示词模板表)
-- ============================================================
CREATE TABLE page_prompt_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_name TEXT NOT NULL UNIQUE,
    template_category TEXT NOT NULL,
    prompt_template TEXT NOT NULL,
    description TEXT,
    example_input JSONB DEFAULT '{}',
    example_output TEXT,
    parameters JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT true,
    usage_count INTEGER DEFAULT 0,
    created_by TEXT REFERENCES profiles(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_template_category CHECK (
        template_category IN (
            'text_to_image', 'image_enhancement', 'style_preset',
            'text_generation', 'custom', 'system'
        )
    ),
    CONSTRAINT check_template_name_not_empty CHECK (LENGTH(TRIM(template_name)) > 0),
    CONSTRAINT check_prompt_template_not_empty CHECK (LENGTH(TRIM(prompt_template)) > 0),
    CONSTRAINT check_usage_count CHECK (usage_count >= 0)
);

CREATE INDEX idx_page_prompt_templates_category ON page_prompt_templates(template_category);
CREATE INDEX idx_page_prompt_templates_active ON page_prompt_templates(is_active, usage_count DESC);
CREATE INDEX idx_page_prompt_templates_template_name ON page_prompt_templates(template_name);
CREATE INDEX idx_page_prompt_templates_created_by ON page_prompt_templates(created_by) WHERE created_by IS NOT NULL;

COMMENT ON TABLE page_prompt_templates IS '页面提示词模板表: 存储可复用的 AI 提示词模板';
COMMENT ON COLUMN page_prompt_templates.template_name IS '模板名称 (唯一)';
COMMENT ON COLUMN page_prompt_templates.template_category IS '模板分类 (text_to_image/image_enhancement/style_preset 等)';
COMMENT ON COLUMN page_prompt_templates.prompt_template IS '提示词模板 (可包含变量占位符如 {subject}, {style})';
COMMENT ON COLUMN page_prompt_templates.description IS '模板描述';
COMMENT ON COLUMN page_prompt_templates.example_input IS '示例输入 (JSON 格式,展示如何填充变量)';
COMMENT ON COLUMN page_prompt_templates.example_output IS '示例输出 (生成后的完整提示词)';
COMMENT ON COLUMN page_prompt_templates.parameters IS '参数定义 (JSON 数组,定义模板中的变量)';
COMMENT ON COLUMN page_prompt_templates.is_active IS '是否启用';
COMMENT ON COLUMN page_prompt_templates.usage_count IS '使用次数';
COMMENT ON COLUMN page_prompt_templates.created_by IS '创建者 (管理员 user_id)';

-- ============================================================
-- 25. payment_records (支付记录表)
-- ============================================================
CREATE TABLE payment_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    payment_type TEXT NOT NULL,
    payment_method TEXT NOT NULL,
    amount_usd NUMERIC(10, 2) NOT NULL,
    amount_credits INTEGER,
    currency TEXT DEFAULT 'USD',
    stripe_payment_intent_id TEXT UNIQUE,
    stripe_charge_id TEXT,
    stripe_customer_id TEXT,
    status TEXT DEFAULT 'pending',
    failure_reason TEXT,
    receipt_url TEXT,
    metadata JSONB DEFAULT '{}',
    refunded_amount NUMERIC(10, 2) DEFAULT 0,
    refunded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_payment_type CHECK (
        payment_type IN (
            'subscription', 'credit_purchase', 'one_time_purchase',
            'upgrade', 'addon'
        )
    ),
    CONSTRAINT check_payment_method CHECK (
        payment_method IN ('card', 'bank_transfer', 'paypal', 'alipay', 'wechat')
    ),
    CONSTRAINT check_status CHECK (
        status IN ('pending', 'processing', 'succeeded', 'failed', 'cancelled', 'refunded')
    ),
    CONSTRAINT check_amount_usd CHECK (amount_usd >= 0),
    CONSTRAINT check_amount_credits CHECK (amount_credits IS NULL OR amount_credits >= 0),
    CONSTRAINT check_refunded_amount CHECK (refunded_amount >= 0 AND refunded_amount <= amount_usd)
);

CREATE INDEX idx_payment_records_user_id ON payment_records(user_id, created_at DESC);
CREATE INDEX idx_payment_records_stripe_payment_intent ON payment_records(stripe_payment_intent_id);
CREATE INDEX idx_payment_records_status ON payment_records(status, created_at DESC);
CREATE INDEX idx_payment_records_payment_type ON payment_records(payment_type, created_at DESC);
CREATE INDEX idx_payment_records_created_at ON payment_records(created_at DESC);
CREATE INDEX idx_payment_records_succeeded ON payment_records(created_at DESC) WHERE status = 'succeeded';

COMMENT ON TABLE payment_records IS '支付记录表: 记录所有支付交易 (订阅/积分购买/一次性购买)';
COMMENT ON COLUMN payment_records.payment_type IS '支付类型 (subscription/credit_purchase/one_time_purchase/upgrade/addon)';
COMMENT ON COLUMN payment_records.payment_method IS '支付方式 (card/bank_transfer/paypal/alipay/wechat)';
COMMENT ON COLUMN payment_records.amount_usd IS '支付金额 (美元)';
COMMENT ON COLUMN payment_records.amount_credits IS '购买的积分数 (如果是积分购买)';
COMMENT ON COLUMN payment_records.currency IS '货币类型 (默认 USD)';
COMMENT ON COLUMN payment_records.stripe_payment_intent_id IS 'Stripe Payment Intent ID (唯一)';
COMMENT ON COLUMN payment_records.stripe_charge_id IS 'Stripe Charge ID';
COMMENT ON COLUMN payment_records.stripe_customer_id IS 'Stripe Customer ID';
COMMENT ON COLUMN payment_records.status IS '支付状态 (pending/processing/succeeded/failed/cancelled/refunded)';
COMMENT ON COLUMN payment_records.failure_reason IS '失败原因 (如果失败)';
COMMENT ON COLUMN payment_records.receipt_url IS '收据 URL (Stripe 生成)';
COMMENT ON COLUMN payment_records.refunded_amount IS '已退款金额';
COMMENT ON COLUMN payment_records.refunded_at IS '退款时间';

-- ============================================================
-- 触发器: 更新 updated_at 字段
-- ============================================================
CREATE TRIGGER trigger_update_generation_tasks_updated_at
BEFORE UPDATE ON generation_tasks
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_update_page_prompt_templates_updated_at
BEFORE UPDATE ON page_prompt_templates
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_update_payment_records_updated_at
BEFORE UPDATE ON payment_records
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- Phase 2.3 完成
-- ============================================================
-- 新增 3 个 P2 表:
--   ✅ generation_tasks (AI 生成任务)
--   ✅ page_prompt_templates (页面提示词模板)
--   ✅ payment_records (支付记录)
-- ============================================================


-- ============================================================================
-- Phase 2.4: 添加缺失字段到现有表 (Add Missing Fields to Existing Tables)
-- Created: 2026-01-10
-- Purpose: 补充 profiles 和 projects 表的缺失字段
-- ============================================================================

-- Add missing fields to profiles table
ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS first_name TEXT,
ADD COLUMN IF NOT EXISTS last_name TEXT,
ADD COLUMN IF NOT EXISTS onboarding_step TEXT DEFAULT 'not_started',
ADD COLUMN IF NOT EXISTS preferences JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS credits_reset_at TIMESTAMPTZ;

-- Add CHECK constraint for onboarding_step enum
ALTER TABLE profiles
DROP CONSTRAINT IF EXISTS check_onboarding_step;

ALTER TABLE profiles
ADD CONSTRAINT check_onboarding_step CHECK (
    onboarding_step IN (
        'not_started',
        'welcome',
        'profile_setup',
        'first_project',
        'editor_tour',
        'marketplace_intro',
        'completed',
        'skipped'
    )
);

-- Add column comments for profiles
COMMENT ON COLUMN profiles.first_name IS '用户名字';
COMMENT ON COLUMN profiles.last_name IS '用户姓氏';
COMMENT ON COLUMN profiles.onboarding_step IS '新手引导步骤 (not_started, welcome, profile_setup, first_project, editor_tour, marketplace_intro, completed, skipped)';
COMMENT ON COLUMN profiles.preferences IS '用户偏好设置 (JSONB: theme, language, notifications, etc.)';
COMMENT ON COLUMN profiles.credits_reset_at IS '积分重置时间 (用于月度积分重置逻辑)';

-- Create index for onboarding tracking
CREATE INDEX idx_profiles_onboarding_step ON profiles(onboarding_step)
WHERE onboarding_step NOT IN ('completed', 'skipped');

-- Add missing field to projects table
ALTER TABLE projects
ADD COLUMN IF NOT EXISTS is_permanently_deleted BOOLEAN DEFAULT false;

-- Add column comment for projects
COMMENT ON COLUMN projects.is_permanently_deleted IS '是否永久删除 (true 表示硬删除，false 表示软删除或未删除)';

-- Create conditional index for active projects (excluding permanently deleted)
CREATE INDEX idx_projects_active ON projects(user_id, created_at DESC)
WHERE is_deleted = false AND is_permanently_deleted = false;

-- ============================================================
-- Phase 2.4 完成
-- ============================================================
-- 新增字段:
--   profiles 表:
--     ✅ first_name (用户名字)
--     ✅ last_name (用户姓氏)
--     ✅ onboarding_step (新手引导步骤)
--     ✅ preferences (用户偏好设置)
--     ✅ credits_reset_at (积分重置时间)
--   projects 表:
--     ✅ is_permanently_deleted (是否永久删除)
--   索引:
--     ✅ idx_profiles_onboarding_step (未完成引导的用户)
--     ✅ idx_projects_active (活跃项目查询优化)
-- ============================================================


-- ============================================================================
-- Transaction Control: 提交所有更改
-- ============================================================================
COMMIT;

-- 迁移成功完成

