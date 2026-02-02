-- ============================================================================
-- Make Decodables - 数据库架构 (文件 3/3)
-- ============================================================================
-- 分类: 基础设施
-- 说明: 配置、日志、支持、管理、支付记录
-- 执行顺序: 第 3 个执行 (依赖 01_core_business.sql 和 02_platform_services.sql)
-- 生成时间: 2026-01-12 (修复版)
-- ============================================================================

-- 开始事务
BEGIN;

-- 创建 internal schema (运维视图专用，PostgREST 不暴露)
CREATE SCHEMA IF NOT EXISTS internal;

-- ============================================================================
-- 包含的表 (12) - 按依赖关系排序
-- ============================================================================
-- Layer 1: 无依赖或仅依赖 profiles
--   - admin_operations, ai_call_logs, api_logs, error_logs
--   - payment_records, pricing_plans, scheduled_task_logs
--   - system_configs
--
-- Layer 2: 依赖 Layer 1 的表
--   - pricing_history (依赖 pricing_plans)
--   - support_tickets (依赖 profiles)
--   - user_price_overrides (依赖 pricing_plans)
--
-- Layer 3: 依赖 Layer 2 的表
--   - support_replies (依赖 support_tickets, profiles)


-- ============================================================================
-- Layer 1: 无依赖的表
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. admin_operations
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_operations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id TEXT NOT NULL,  -- 不使用外键，支持系统级操作 (system_webhook, system_scheduler 等)
    operation_type TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT,
    target_user_id UUID,  -- 专门用于记录操作影响的用户ID（可为空）
    action_details JSONB DEFAULT '{}',
    -- P0-13, P0-14: Repository 使用的额外字段
    source TEXT,  -- 操作来源
    details TEXT,  -- 操作详情
    reason TEXT,  -- 操作原因
    ip_address INET,
    user_agent TEXT,
    status TEXT DEFAULT 'success',
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_operation_type CHECK (
        operation_type IN (
            -- 原有操作类型
            'create', 'update', 'delete', 'restore',
            'approve', 'reject', 'ban', 'unban',
            'grant_credits', 'refund', 'adjust_tier',
            'force_delete', 'export_data', 'import_data',
            -- 扩展操作类型 (Phase 4 - Task 9)
            'project_delete_soft', 'project_delete_permanent', 'project_restore',
            'template_delete', 'generation_delete', 'generation_batch_delete',
            'resource_delete', 'feature_flag_delete', 'campaign_delete', 'experiment_delete',
            'config_update', 'config_delete', 'rate_limit_preset_apply', 'cache_clear',
            'broadcast',
            -- Webhook 操作类型 (v3.31)
            'webhook_subscription_create', 'webhook_subscription_update', 'webhook_subscription_cancel',
            'webhook_invoice_paid', 'webhook_refund_process', 'webhook_credits_purchase',
            'auth_user_register', 'webhook_tier_update'
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

CREATE INDEX IF NOT EXISTS idx_admin_operations_admin_id ON admin_operations(admin_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_operations_operation_type ON admin_operations(operation_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_operations_target ON admin_operations(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_admin_operations_created_at ON admin_operations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_operations_failed ON admin_operations(created_at DESC) WHERE status = 'failed';


-- ----------------------------------------------------------------------------
-- 2. ai_call_logs
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ai_call_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id),

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


-- ----------------------------------------------------------------------------
-- 3. api_logs
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS api_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id),
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


-- ----------------------------------------------------------------------------
-- 4. error_logs
-- ----------------------------------------------------------------------------
-- 支持前端错误日志和后端错误日志
CREATE TABLE IF NOT EXISTS error_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- 前端错误字段
    error_id TEXT,                          -- 前端生成的唯一错误 ID
    error_type TEXT NOT NULL,               -- 错误类型 (API/NETWORK/JS_ERROR/等)
    error_code TEXT,                        -- 错误代码
    message TEXT,                           -- 错误消息 (前端用)
    status_code INTEGER,                    -- HTTP 状态码
    endpoint TEXT,                          -- API 端点
    method TEXT,                            -- HTTP 方法
    stack_trace TEXT,                       -- 堆栈跟踪
    page_url TEXT,                          -- 发生错误的页面 URL
    user_agent TEXT,                        -- 浏览器 User-Agent
    session_id TEXT,                        -- 前端会话 ID
    user_code TEXT,                         -- 用户代码 (26位)
    context JSONB DEFAULT '{}',             -- 上下文信息
    client_timestamp TEXT,                  -- 前端时间戳
    -- 用户关联
    user_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
    -- 后端错误字段 (保留兼容)
    error_message TEXT,                     -- 后端错误消息
    error_stack TEXT,                       -- 后端堆栈 (与 stack_trace 区分)
    request_path TEXT,                      -- 后端请求路径
    request_method TEXT,                    -- 后端请求方法
    request_body JSONB,                     -- 后端请求体
    response_status INTEGER,                -- 后端响应状态
    -- 元数据
    environment TEXT DEFAULT 'production',
    severity TEXT DEFAULT 'error',
    level TEXT DEFAULT 'error',
    metadata JSONB DEFAULT '{}',
    source TEXT DEFAULT 'frontend',         -- 来源: frontend/backend
    -- 解决状态
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMPTZ,
    resolved_by UUID REFERENCES profiles(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_error_logs_error_id ON error_logs(error_id) WHERE error_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_error_logs_user_id ON error_logs(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_error_logs_session_id ON error_logs(session_id) WHERE session_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_error_logs_error_type ON error_logs(error_type);
CREATE INDEX IF NOT EXISTS idx_error_logs_created_at ON error_logs(created_at DESC);

-- P0-9: 触发器同步 level 和 severity
CREATE OR REPLACE FUNCTION sync_error_level()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.level IS NOT NULL AND NEW.severity IS NULL THEN
        NEW.severity := NEW.level;
    ELSIF NEW.severity IS NOT NULL AND NEW.level IS NULL THEN
        NEW.level := NEW.severity;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql
SET search_path = 'public';

DROP TRIGGER IF EXISTS trg_error_logs_sync_level ON error_logs;
CREATE TRIGGER trg_error_logs_sync_level
    BEFORE INSERT OR UPDATE ON error_logs
    FOR EACH ROW
    EXECUTE FUNCTION sync_error_level();

CREATE INDEX IF NOT EXISTS idx_error_logs_severity ON error_logs(severity, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_error_logs_unresolved ON error_logs(created_at DESC) WHERE resolved = FALSE;


-- ----------------------------------------------------------------------------
-- 5. payment_records
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS payment_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    payment_type TEXT NOT NULL,
    payment_method TEXT NOT NULL DEFAULT 'card',
    amount_usd NUMERIC(10, 2) NOT NULL,
    amount_credits INTEGER,
    currency TEXT DEFAULT 'USD',
    timezone TEXT DEFAULT 'UTC',  -- P0-12: Repository 使用的时区字段
    stripe_payment_intent_id TEXT UNIQUE,
    stripe_charge_id TEXT,
    stripe_customer_id TEXT,
    status TEXT DEFAULT 'pending',
    failure_reason TEXT,
    receipt_url TEXT,
    metadata JSONB DEFAULT '{}',
    stripe_refund_id TEXT,
    refunded_amount NUMERIC(10, 2) DEFAULT 0,
    refunded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_payment_type CHECK (
        payment_type IN (
            'subscription', 'credit_purchase', 'one_time_purchase',
            'upgrade', 'addon',
            -- WS1: 代码实际写入的类型
            'refund', 'sub_canceled', 'sub_cancel_scheduled', 'sub_renewal',
            'sub_payment', 'tier_downgrade', 'tier_downgrade_scheduled',
            'admin_adjustment', 'payment_failed'
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

CREATE INDEX IF NOT EXISTS idx_payment_records_user_id ON payment_records(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_payment_records_stripe_payment_intent ON payment_records(stripe_payment_intent_id);
CREATE INDEX IF NOT EXISTS idx_payment_records_status ON payment_records(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_payment_records_payment_type ON payment_records(payment_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_payment_records_created_at ON payment_records(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_payment_records_succeeded ON payment_records(created_at DESC) WHERE status = 'succeeded';


-- ----------------------------------------------------------------------------
-- 6. pricing_plans (必须在 pricing_history 之前创建)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pricing_plans (
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
    created_by UUID,
    updated_by UUID,

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


-- ----------------------------------------------------------------------------
-- 7. scheduled_task_logs
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scheduled_task_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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


-- ----------------------------------------------------------------------------
-- 8. system_configs
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS system_configs (
    -- 主键 (保持 V1 兼容性)
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,

    -- 类型与分组
    -- v2.1: 添加 'array' (JSON 数组) 和 'richtext' (Markdown/HTML) 类型
    value_type TEXT NOT NULL DEFAULT 'text' CHECK (value_type IN ('text', 'number', 'integer', 'boolean', 'json', 'array', 'richtext')),
    config_group TEXT NOT NULL DEFAULT 'general',

    -- 描述
    description TEXT,

    -- 状态控制
    is_active BOOLEAN DEFAULT TRUE,
    is_editable BOOLEAN DEFAULT TRUE,

    -- 审计字段
    updated_by UUID,

    -- 扩展字段
    ext_json JSONB DEFAULT '{}'::jsonb,

    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================================
-- Layer 2: 依赖 Layer 1 的表
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 9. pricing_history (依赖 pricing_plans)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pricing_history (
    id SERIAL PRIMARY KEY,
    plan_id INT NOT NULL REFERENCES pricing_plans(id) ON DELETE CASCADE,
    plan_code VARCHAR(50) NOT NULL,

    -- 变更信息
    action VARCHAR(20) NOT NULL CHECK (action IN ('create', 'update', 'update_price', 'activate', 'deactivate', 'show', 'hide', 'delete')),
    old_data JSONB,
    new_data JSONB,

    -- 审计信息
    changed_by UUID NOT NULL,
    changed_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);


-- ----------------------------------------------------------------------------
-- 10. support_tickets (依赖 profiles)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS support_tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    ticket_number TEXT NOT NULL UNIQUE,
    subject TEXT NOT NULL,
    description TEXT NOT NULL,
    message TEXT,  -- P0-7: Repository 使用 message 字段 (与 description 同步)
    category TEXT NOT NULL,
    priority TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'open',
    assigned_to UUID REFERENCES profiles(id) ON DELETE SET NULL,
    admin_note TEXT,  -- P0-11: Repository 使用的管理员备注字段
    attachments JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMPTZ,
    recovery_expires_at TIMESTAMPTZ,

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

CREATE INDEX IF NOT EXISTS idx_support_tickets_user_id ON support_tickets(user_id, created_at DESC) WHERE is_deleted = false;


-- ----------------------------------------------------------------------------
-- 11. user_price_overrides (依赖 pricing_plans)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_price_overrides (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    pricing_plan_id INT NOT NULL REFERENCES pricing_plans(id) ON DELETE CASCADE,

    -- 覆盖价格
    override_price_cents INT NOT NULL CHECK (override_price_cents >= 0),
    reason TEXT NOT NULL,

    -- 有效期
    valid_from TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    valid_until TIMESTAMPTZ,

    -- 审计
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- 约束
    UNIQUE(user_id, pricing_plan_id),
    CONSTRAINT check_valid_dates CHECK (valid_until IS NULL OR valid_until > valid_from)
);


-- ============================================================================
-- Layer 3: 依赖 Layer 2 的表
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 12. support_replies (依赖 support_tickets, profiles)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS support_replies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id UUID NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    is_staff_reply BOOLEAN DEFAULT FALSE,
    is_admin_reply BOOLEAN DEFAULT FALSE,  -- P0-8: Repository 使用的字段
    message TEXT NOT NULL,
    attachments JSONB DEFAULT '[]',
    read_at TIMESTAMPTZ,  -- P0-18: 回复读取时间
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMPTZ,
    recovery_expires_at TIMESTAMPTZ,

    CONSTRAINT check_message_not_empty CHECK (LENGTH(TRIM(message)) > 0),
    CONSTRAINT chk_support_replies_deleted_at_consistency
        CHECK ((is_deleted = false AND deleted_at IS NULL) OR (is_deleted = true AND deleted_at IS NOT NULL)),
    CONSTRAINT chk_support_replies_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);

CREATE INDEX IF NOT EXISTS idx_support_replies_ticket_id ON support_replies(ticket_id, created_at ASC) WHERE is_deleted = false;


-- ============================================================================
-- 数据库函数 (11)
-- ============================================================================

-- 函数 1
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql
SET search_path = 'public';


-- 函数 2
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
$$ LANGUAGE plpgsql
SET search_path = 'public';


-- 函数 3
CREATE OR REPLACE FUNCTION prevent_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Table % is append-only. UPDATE and DELETE operations are not allowed.', TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql
SET search_path = 'public';


-- 函数 4
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
$$ LANGUAGE plpgsql
SET search_path = 'public';


-- 函数 5
-- P0-7: 修复返回字段名，Repository 期望 balance_monthly/balance_permanent
CREATE OR REPLACE FUNCTION deduct_credits_atomic(
    p_user_id UUID,
    p_amount INT,
    p_type TEXT,
    p_description TEXT DEFAULT NULL,
    p_idempotency_key TEXT DEFAULT NULL,
    p_related_entity_type TEXT DEFAULT NULL,
    p_related_entity_id TEXT DEFAULT NULL
)
RETURNS TABLE (
    success BOOLEAN,
    balance_monthly INT,  -- P0-7: 改为 Repository 期望的字段名
    balance_permanent INT,  -- P0-7: 改为 Repository 期望的字段名
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
    -- WS-10: Fixed suffix mismatch — check uses '_monthly' to match actual INSERT suffix
    IF p_idempotency_key IS NOT NULL THEN
        IF EXISTS (
            SELECT 1 FROM credit_transactions
            WHERE idempotency_key = p_idempotency_key || '_monthly'
               OR idempotency_key = p_idempotency_key || '_permanent'
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
$$ LANGUAGE plpgsql
SET search_path = 'public';


-- 函数 6
-- P0-7: 修复返回字段名，Repository 期望 balance_monthly/balance_permanent
CREATE OR REPLACE FUNCTION add_credits_atomic(
    p_user_id UUID,
    p_amount INT,
    p_bucket TEXT,
    p_type TEXT,
    p_description TEXT DEFAULT NULL,
    p_idempotency_key TEXT DEFAULT NULL
)
RETURNS TABLE (
    success BOOLEAN,
    balance_monthly INT,  -- P0-7: 改为 Repository 期望的字段名
    balance_permanent INT,  -- P0-7: 改为 Repository 期望的字段名
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

    -- WS3: 幂等性检查 (idempotency_key 去重)
    IF p_idempotency_key IS NOT NULL THEN
        IF EXISTS (
            SELECT 1 FROM credit_transactions
            WHERE idempotency_key = p_idempotency_key
        ) THEN
            -- 已处理过，返回当前余额
            SELECT credits_monthly, credits_permanent
            INTO v_monthly, v_permanent
            FROM profiles WHERE id = p_user_id;

            RETURN QUERY SELECT TRUE, COALESCE(v_monthly, 0), COALESCE(v_permanent, 0), NULL::TEXT;
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

    -- 更新余额
    IF p_bucket = 'monthly' THEN
        UPDATE profiles SET credits_monthly = credits_monthly + p_amount WHERE id = p_user_id;
        v_monthly := v_monthly + p_amount;
    ELSE
        UPDATE profiles SET credits_permanent = credits_permanent + p_amount WHERE id = p_user_id;
        v_permanent := v_permanent + p_amount;
    END IF;

    -- 记录交易 (UNIQUE 部分索引保证并发安全)
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
$$ LANGUAGE plpgsql
SET search_path = 'public';


-- 函数 6b: 原子积分购买处理 (v3.27 - Phase 5 Part C)
-- 将支付记录 + 积分增加 + 交易记录合并为单一原子操作
CREATE OR REPLACE FUNCTION process_credit_purchase(
    p_user_id UUID,
    p_credits_amount INT,
    p_payment_amount INT,      -- 金额（美分）
    p_currency TEXT,
    p_session_id TEXT,
    p_idempotency_key TEXT DEFAULT NULL,
    p_payment_method TEXT DEFAULT 'stripe'  -- WS-12: Parameterize payment method
)
RETURNS TABLE (
    success BOOLEAN,
    payment_id UUID,
    balance_monthly INT,
    balance_permanent INT,
    error_message TEXT
) AS $$
DECLARE
    v_monthly INT;
    v_permanent INT;
    v_payment_id UUID;
    v_existing_payment UUID;
BEGIN
    -- 输入验证
    IF p_user_id IS NULL OR length(p_user_id) = 0 OR length(p_user_id) > 100 THEN
        RETURN QUERY SELECT FALSE, NULL::UUID, 0, 0, 'Invalid user_id'::TEXT;
        RETURN;
    END IF;

    IF p_credits_amount <= 0 OR p_credits_amount > 100000 THEN
        RETURN QUERY SELECT FALSE, NULL::UUID, 0, 0, 'Invalid credits_amount (must be 1-100000)'::TEXT;
        RETURN;
    END IF;

    IF p_payment_amount <= 0 THEN
        RETURN QUERY SELECT FALSE, NULL::UUID, 0, 0, 'Invalid payment_amount'::TEXT;
        RETURN;
    END IF;

    IF p_session_id IS NULL OR length(p_session_id) = 0 THEN
        RETURN QUERY SELECT FALSE, NULL::UUID, 0, 0, 'Invalid session_id'::TEXT;
        RETURN;
    END IF;

    -- 幂等性检查：检查 session_id 是否已处理过
    SELECT id INTO v_existing_payment
    FROM payment_records
    WHERE metadata->>'session_id' = p_session_id
    LIMIT 1;

    IF v_existing_payment IS NOT NULL THEN
        -- 已处理过，返回现有记录
        SELECT credits_monthly, credits_permanent INTO v_monthly, v_permanent
        FROM profiles WHERE id = p_user_id;

        RETURN QUERY SELECT TRUE, v_existing_payment, COALESCE(v_monthly, 0), COALESCE(v_permanent, 0), NULL::TEXT;
        RETURN;
    END IF;

    -- 加锁获取用户当前余额
    SELECT credits_monthly, credits_permanent
    INTO v_monthly, v_permanent
    FROM profiles
    WHERE id = p_user_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, NULL::UUID, 0, 0, 'User not found'::TEXT;
        RETURN;
    END IF;

    -- 步骤 1: 创建支付记录
    INSERT INTO payment_records (
        user_id,
        payment_type,
        payment_method,
        amount_usd,
        amount_credits,
        currency,
        status,
        metadata,
        created_at
    ) VALUES (
        p_user_id,
        'credit_purchase',
        p_payment_method,  -- WS-12: Use parameterized payment method
        p_payment_amount / 100.0,  -- 转换为美元
        p_credits_amount,
        UPPER(p_currency),
        'succeeded',
        jsonb_build_object(
            'session_id', p_session_id,
            'description', format('Purchase %s Credits - $%s', p_credits_amount, (p_payment_amount / 100.0)::TEXT)
        ),
        NOW()
    )
    RETURNING id INTO v_payment_id;

    -- 步骤 2: 增加永久积分
    UPDATE profiles
    SET credits_permanent = credits_permanent + p_credits_amount,
        updated_at = NOW()
    WHERE id = p_user_id;

    v_permanent := v_permanent + p_credits_amount;

    -- 步骤 3: 记录积分交易
    INSERT INTO credit_transactions (
        user_id,
        transaction_type,
        bucket,
        amount,
        balance_monthly_after,
        balance_permanent_after,
        description,
        idempotency_key,
        created_at
    ) VALUES (
        p_user_id,
        'topup_purchase',
        'permanent',
        p_credits_amount,
        v_monthly,
        v_permanent,
        format('Purchase %s Credits', p_credits_amount),
        COALESCE(p_idempotency_key, 'credit_purchase_' || p_session_id),
        NOW()
    );

    RETURN QUERY SELECT TRUE, v_payment_id, v_monthly, v_permanent, NULL::TEXT;
END;
$$ LANGUAGE plpgsql
SET search_path = 'public';

COMMENT ON FUNCTION process_credit_purchase IS 'v3.27: 原子性处理积分购买（支付记录+积分增加+交易记录在同一事务中）';


-- 函数 7
CREATE OR REPLACE FUNCTION execute_marketplace_purchase(
    p_user_id UUID,
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
$$ LANGUAGE plpgsql
SET search_path = 'public';


-- 函数 8
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
$$ LANGUAGE plpgsql
SET search_path = 'public';


-- 函数 9
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
$$ LANGUAGE plpgsql
SET search_path = 'public';


-- (函数 10 is_admin() 已删除 — 依赖未设置的会话变量，永远返回 FALSE，无 RLS 引用)

-- 函数 11
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
$$ LANGUAGE plpgsql
SET search_path = 'public';


-- 触发器 12: 自动生成工单编号 (v2.1.0)
-- 在插入 support_tickets 时自动生成 ticket_number
DROP TRIGGER IF EXISTS trg_generate_ticket_number ON support_tickets;
CREATE TRIGGER trg_generate_ticket_number
    BEFORE INSERT ON support_tickets
    FOR EACH ROW
    WHEN (NEW.ticket_number IS NULL OR NEW.ticket_number = '')
    EXECUTE FUNCTION generate_ticket_number();


-- ============================================================================
-- 视图定义 (1)
-- ============================================================================

-- 视图 1 (运维视图，放在 internal schema，PostgREST 不暴露)
DROP VIEW IF EXISTS public.v_ai_usage_last_30_days CASCADE;
CREATE OR REPLACE VIEW internal.v_ai_usage_last_30_days AS
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
FROM public.ai_usage_daily
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY provider, model, call_type
ORDER BY total_cost_usd DESC;


-- ============================================================================
-- 初始数据 (已提取到 seed 文件)
-- ============================================================================
-- 配置数据已移至独立的 seed 文件:
--   - migrations/seed/pricing_plans_seed.sql (订阅和积分包)
--   - migrations/seed/system_configs_seed.sql (系统配置)
--
-- 运行顺序:
--   1. 先执行 schema 文件 (创建表结构)
--   2. 再执行 seed 文件 (插入初始数据)
-- ============================================================================


-- ============================================================================
-- 性能与安全优化补丁 (2026-01-12)
-- ============================================================================
-- 注意: 以下 ALTER TABLE 操作依赖 01_core_business.sql 中定义的表
-- 如果表不存在，这些操作会失败但不影响核心功能
-- ============================================================================

-- ----------------------------------------------------------------------------
-- P0-1: Marketplace 状态转换约束 (依赖 marketplace_listings)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION check_marketplace_moderation_transition()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.moderation_status = 'rejected' AND NEW.moderation_status = 'approved' THEN
        RAISE EXCEPTION 'Cannot approve a rejected listing - seller must create a new listing';
    END IF;
    INSERT INTO system_resource_audit_logs (
        resource_id, action, old_data, new_data, changed_by, changed_at
    ) VALUES (
        OLD.id,
        'moderation_status_change',
        jsonb_build_object('moderation_status', OLD.moderation_status),
        jsonb_build_object('moderation_status', NEW.moderation_status),
        CURRENT_USER,
        CURRENT_TIMESTAMP
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql
SET search_path = 'public';

-- 触发器需要在 marketplace_listings 表存在后创建
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'marketplace_listings') THEN
        DROP TRIGGER IF EXISTS trg_marketplace_listings_moderation_transition ON marketplace_listings;
        CREATE TRIGGER trg_marketplace_listings_moderation_transition
            BEFORE UPDATE OF moderation_status ON marketplace_listings
            FOR EACH ROW
            WHEN (OLD.moderation_status IS DISTINCT FROM NEW.moderation_status)
            EXECUTE FUNCTION check_marketplace_moderation_transition();
    END IF;
END $$;


-- ----------------------------------------------------------------------------
-- P1-1: 软删除通用触发器函数 (已在上面定义)
-- ----------------------------------------------------------------------------

-- ----------------------------------------------------------------------------
-- P1-2: 为 01_core_business.sql 中的表添加软删除触发器
-- ----------------------------------------------------------------------------
-- 注意: 只为有 is_deleted 字段的表添加触发器
-- marketplace_purchases 是只追加表，没有 is_deleted 字段，不需要此触发器
DO $$
DECLARE
    tables_to_update TEXT[] := ARRAY[
        'projects', 'assets', 'marketplace_listings'
    ];
    t TEXT;
BEGIN
    FOREACH t IN ARRAY tables_to_update
    LOOP
        -- 检查表存在且有 is_deleted 字段
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = t AND column_name = 'is_deleted'
        ) THEN
            EXECUTE format('DROP TRIGGER IF EXISTS trg_%s_soft_delete ON %I', t, t);
            EXECUTE format('
                CREATE TRIGGER trg_%s_soft_delete
                    BEFORE UPDATE ON %I FOR EACH ROW
                    WHEN (OLD.is_deleted IS DISTINCT FROM NEW.is_deleted)
                    EXECUTE FUNCTION set_deleted_at_on_soft_delete()
            ', t, t);
        END IF;
    END LOOP;
END $$;


-- ----------------------------------------------------------------------------
-- P2-1: RPC 聚合函数 (6个，减少 N+1 查询)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION p_get_user_dashboard_stats(p_user_id UUID)
RETURNS TABLE(
    project_count INTEGER,
    asset_count INTEGER,
    generation_count INTEGER,
    credits_total INTEGER,
    subscription_tier TEXT,
    marketplace_purchases INTEGER,
    marketplace_sales INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        (SELECT COUNT(*)::INTEGER FROM projects WHERE user_id = p_user_id AND is_deleted = false),
        (SELECT COUNT(*)::INTEGER FROM assets WHERE user_id = p_user_id AND is_deleted = false),
        0::INTEGER,  -- generation_count - 表可能不存在
        (SELECT (credits_monthly + credits_permanent)::INTEGER FROM profiles WHERE id = p_user_id),
        (SELECT tier FROM profiles WHERE id = p_user_id),
        (SELECT COUNT(*)::INTEGER FROM marketplace_purchases WHERE user_id = p_user_id),
        (SELECT COUNT(*)::INTEGER FROM marketplace_listings WHERE seller_id = p_user_id);
EXCEPTION
    WHEN undefined_table THEN
        -- 某些表不存在时返回默认值
        RETURN QUERY SELECT 0, 0, 0, 0, 't1'::TEXT, 0, 0;
END;
$$ LANGUAGE plpgsql STABLE
SET search_path = 'public';


CREATE OR REPLACE FUNCTION p_get_marketplace_trending(
    p_limit INTEGER DEFAULT 20,
    p_offset INTEGER DEFAULT 0
)
RETURNS TABLE(
    listing_id UUID,
    title TEXT,
    preview_url TEXT,
    price_credits INTEGER,
    total_purchases INTEGER,
    total_favorites INTEGER,
    avg_rating NUMERIC,
    seller_name TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        l.id, l.title, l.thumbnail_url, l.price_credits,
        l.sales_count, 0, 0::NUMERIC, p.display_name
    FROM marketplace_listings l
    JOIN profiles p ON l.seller_id = p.id
    WHERE l.is_public = true
      AND l.is_deleted = false
    ORDER BY l.sales_count DESC, l.created_at DESC
    LIMIT p_limit OFFSET p_offset;
EXCEPTION
    WHEN undefined_table THEN
        RETURN;
END;
$$ LANGUAGE plpgsql STABLE
SET search_path = 'public';


CREATE OR REPLACE FUNCTION p_get_user_credit_summary(
    p_user_id UUID,
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE(
    total_earned INTEGER,
    total_spent INTEGER,
    transaction_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0)::INTEGER,
        COALESCE(SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END), 0)::INTEGER,
        COUNT(*)::INTEGER
    FROM credit_transactions
    WHERE user_id = p_user_id
      AND created_at >= CURRENT_TIMESTAMP - (p_days || ' days')::INTERVAL;
EXCEPTION
    WHEN undefined_table THEN
        RETURN QUERY SELECT 0, 0, 0;
END;
$$ LANGUAGE plpgsql STABLE
SET search_path = 'public';


CREATE OR REPLACE FUNCTION p_calculate_user_activity_score(
    p_user_id UUID,
    p_days INTEGER DEFAULT 7
)
RETURNS TABLE(
    activity_score NUMERIC,
    project_count INTEGER,
    generation_count INTEGER
) AS $$
DECLARE
    v_project_count INTEGER := 0;
    v_generation_count INTEGER := 0;
BEGIN
    SELECT COUNT(*) INTO v_project_count
    FROM projects
    WHERE user_id = p_user_id
      AND created_at >= CURRENT_TIMESTAMP - (p_days || ' days')::INTERVAL;

    RETURN QUERY
    SELECT (v_project_count * 5 + v_generation_count * 3)::NUMERIC, v_project_count, v_generation_count;
EXCEPTION
    WHEN undefined_table THEN
        RETURN QUERY SELECT 0::NUMERIC, 0, 0;
END;
$$ LANGUAGE plpgsql STABLE
SET search_path = 'public';


CREATE OR REPLACE FUNCTION p_aggregate_experiment_results(p_experiment_id UUID)
RETURNS TABLE(
    variant_key TEXT,
    total_users INTEGER,
    conversion_rate NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ea.variant_key,
        COUNT(DISTINCT ea.user_id)::INTEGER,
        0::NUMERIC  -- 简化实现
    FROM experiment_assignments ea
    WHERE ea.experiment_id = p_experiment_id
    GROUP BY ea.variant_key;
EXCEPTION
    WHEN undefined_table THEN
        RETURN;
END;
$$ LANGUAGE plpgsql STABLE
SET search_path = 'public';


CREATE OR REPLACE FUNCTION p_check_system_health()
RETURNS TABLE(
    metric_name TEXT,
    metric_value NUMERIC,
    status TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 'total_users'::TEXT,
           (SELECT COUNT(*)::NUMERIC FROM profiles WHERE is_deleted = false),
           'ok'::TEXT
    UNION ALL
    SELECT 'active_users_24h'::TEXT,
           (SELECT COUNT(DISTINCT user_id)::NUMERIC FROM user_events WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '24 hours'),
           'ok'::TEXT;
EXCEPTION
    WHEN undefined_table THEN
        RETURN QUERY SELECT 'error'::TEXT, 0::NUMERIC, 'tables_missing'::TEXT;
END;
$$ LANGUAGE plpgsql STABLE
SET search_path = 'public';


-- ----------------------------------------------------------------------------
-- P2-2: 乐观锁机制 (version 字段)
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    -- projects
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'projects') THEN
        ALTER TABLE projects ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;
    END IF;

    -- marketplace_listings
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'marketplace_listings') THEN
        ALTER TABLE marketplace_listings ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;
    END IF;

    -- system_configs
    ALTER TABLE system_configs ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;

    -- experiments
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'experiments') THEN
        ALTER TABLE experiments ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;
    END IF;
END $$;


CREATE OR REPLACE FUNCTION p_update_project_with_version(
    p_project_id UUID,
    p_expected_version INTEGER,
    p_user_id UUID,
    p_title TEXT DEFAULT NULL
)
RETURNS TABLE(
    success BOOLEAN,
    new_version INTEGER,
    error_message TEXT
) AS $$
DECLARE
    v_new_version INTEGER;
BEGIN
    UPDATE projects
    SET title = COALESCE(p_title, title),
        version = version + 1,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_project_id
      AND user_id = p_user_id
      AND version = p_expected_version
      AND is_deleted = false
    RETURNING version INTO v_new_version;

    IF FOUND THEN
        RETURN QUERY SELECT true, v_new_version, NULL::TEXT;
    ELSE
        RETURN QUERY SELECT false, 0, 'Version conflict or permission denied';
    END IF;
EXCEPTION
    WHEN undefined_table THEN
        RETURN QUERY SELECT false, 0, 'projects table not found';
END;
$$ LANGUAGE plpgsql
SET search_path = 'public';


-- ----------------------------------------------------------------------------
-- P2-3: Webhook 状态机增强
-- ----------------------------------------------------------------------------
-- stripe_webhook_events 已有这些字段,确保存在
ALTER TABLE stripe_webhook_events
    ADD COLUMN IF NOT EXISTS processing_status TEXT DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS last_error TEXT;

-- 添加约束 (如果不存在)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.check_constraints
        WHERE constraint_name = 'stripe_webhook_events_processing_status_check'
    ) THEN
        ALTER TABLE stripe_webhook_events
            ADD CONSTRAINT stripe_webhook_events_processing_status_check
            CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed'));
    END IF;
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_stripe_webhook_events_pending
    ON stripe_webhook_events(processing_status, created_at)
    WHERE processing_status IN ('pending', 'failed');

-- (已删除: clerk_webhook_events - 迁移到自建认证系统后不再需要)


CREATE OR REPLACE FUNCTION p_start_webhook_processing(
    p_table_name TEXT,
    p_event_id TEXT
)
RETURNS TABLE(
    can_process BOOLEAN,
    current_status TEXT,
    message TEXT
) AS $$
DECLARE
    v_status TEXT;
    v_allowed_tables CONSTANT TEXT[] := ARRAY['stripe_webhook_events'];
BEGIN
    -- Table name whitelist validation (prevent SQL injection via dynamic table name)
    IF p_table_name != ALL(v_allowed_tables) THEN
        RAISE EXCEPTION 'Invalid table name: %. Allowed: %', p_table_name, v_allowed_tables;
    END IF;

    EXECUTE format('SELECT processing_status FROM %I WHERE event_id = $1', p_table_name)
    INTO v_status
    USING p_event_id;

    IF v_status = 'completed' THEN
        RETURN QUERY SELECT false, v_status, 'Already processed';
    ELSIF v_status = 'processing' THEN
        RETURN QUERY SELECT false, v_status, 'Processing by another worker';
    ELSE
        EXECUTE format('UPDATE %I SET processing_status = ''processing'' WHERE event_id = $1 AND processing_status IN (''pending'', ''failed'')', p_table_name)
        USING p_event_id;
        IF FOUND THEN
            RETURN QUERY SELECT true, 'processing'::TEXT, 'Ready';
        ELSE
            RETURN QUERY SELECT false, v_status, 'Conflict';
        END IF;
    END IF;
END;
$$ LANGUAGE plpgsql
SET search_path = 'public';


CREATE OR REPLACE FUNCTION p_complete_webhook_processing(
    p_table_name TEXT,
    p_event_id TEXT,
    p_success BOOLEAN,
    p_error TEXT DEFAULT NULL
)
RETURNS BOOLEAN AS $$
DECLARE
    v_allowed_tables CONSTANT TEXT[] := ARRAY['stripe_webhook_events'];
BEGIN
    -- Table name whitelist validation (prevent SQL injection via dynamic table name)
    IF p_table_name != ALL(v_allowed_tables) THEN
        RAISE EXCEPTION 'Invalid table name: %. Allowed: %', p_table_name, v_allowed_tables;
    END IF;

    EXECUTE format('
        UPDATE %I
        SET processing_status = $1,
            processed_at = CASE WHEN $2 THEN CURRENT_TIMESTAMP END,
            last_error = $3,
            retry_count = CASE WHEN $2 = false THEN retry_count + 1 ELSE retry_count END
        WHERE event_id = $4
    ', p_table_name)
    USING
        CASE WHEN p_success THEN 'completed' ELSE 'failed' END,
        p_success,
        p_error,
        p_event_id;
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql
SET search_path = 'public';


-- ============================================================================
-- Row Level Security (RLS) 启用
-- ============================================================================
-- 策略说明:
-- - 所有表启用 RLS + 仅授权 service_role 完全访问
-- - 后端使用 service_role key (自带 bypassrls 权限)
-- - anon / authenticated 角色无策略 = 完全拒绝访问
-- - 安全深度防御：即使 anon key 泄露，也无法访问数据
-- ============================================================================

-- 01_core_business.sql 中的表 (35个，包含 v3.33 新表和监控日志表)
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE asset_categories ENABLE ROW LEVEL SECURITY;
-- v3.33: 新增 Workspace 和 Tag 系统表
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE folders ENABLE ROW LEVEL SECURITY;  -- v3.33 Phase 2.6
ALTER TABLE legacy_system_tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE tag_group_presets ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE marketplace_listings ENABLE ROW LEVEL SECURITY;
ALTER TABLE assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE legacy_asset_tag_relations ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_asset_tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_members ENABLE ROW LEVEL SECURITY;  -- v3.33 Phase 5
ALTER TABLE workspace_invitations ENABLE ROW LEVEL SECURITY;  -- v3.33 Phase 5
ALTER TABLE user_recent_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_favorite_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_asset_prompt_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_purchases ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE generation_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE listing_usages ENABLE ROW LEVEL SECURITY;
ALTER TABLE marketplace_favorites ENABLE ROW LEVEL SECURITY;
ALTER TABLE marketplace_purchases ENABLE ROW LEVEL SECURITY;
-- marketplace_reports: RLS 已在 01_core_business.sql 中启用和配置
ALTER TABLE marketplace_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_page_prompt_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscription_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_resources ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_discounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_generations ENABLE ROW LEVEL SECURITY;
-- 监控日志表（RPC 和用户创建）
ALTER TABLE system_error_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_creation_logs ENABLE ROW LEVEL SECURITY;

-- 02_platform_services.sql 中的表 (31个)
ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE aggregated_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_usage_daily ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_aggregation ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_events ENABLE ROW LEVEL SECURITY;
-- (已删除: clerk_webhook_events RLS)
ALTER TABLE config_audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_themes ENABLE ROW LEVEL SECURITY;
ALTER TABLE feature_flags ENABLE ROW LEVEL SECURITY;
ALTER TABLE holidays ENABLE ROW LEVEL SECURITY;
ALTER TABLE monthly_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE hourly_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE stripe_webhook_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_resource_audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE experiments ENABLE ROW LEVEL SECURITY;
ALTER TABLE onboarding_steps ENABLE ROW LEVEL SECURITY;
ALTER TABLE articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE experiment_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE flag_exposures ENABLE ROW LEVEL SECURITY;
ALTER TABLE flag_audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaign_dismissals ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaign_participations ENABLE ROW LEVEL SECURITY;
ALTER TABLE experiment_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE experiment_conversions ENABLE ROW LEVEL SECURITY;
ALTER TABLE experiment_exposures ENABLE ROW LEVEL SECURITY;
ALTER TABLE experiment_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE referrals ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_onboarding_progress ENABLE ROW LEVEL SECURITY;

-- 03_infrastructure.sql 中的表 (12个)
ALTER TABLE admin_operations ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_call_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE error_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE pricing_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE scheduled_task_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE pricing_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_price_overrides ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_replies ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- Row Level Security (RLS) 策略 - service_role 显式授权
-- ============================================================================
-- 策略说明:
-- - 所有表仅允许 service_role 完全访问 (后端 FastAPI 使用 service_role key)
-- - 显式策略使安全意图自文档化，消除 Supabase 审计告警
-- - anon / authenticated 角色无任何策略 = 完全拒绝访问
-- ============================================================================

-- 01_core_business.sql 中的表
CREATE POLICY service_role_all ON profiles FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON asset_categories FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON workspaces FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON folders FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON legacy_system_tags FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON tags FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON tag_group_presets FOR ALL TO service_role USING (true) WITH CHECK (true);
-- projects: RLS 策略已在 01_core_business.sql 中定义 (projects_owner_policy + projects_service_role_policy)
CREATE POLICY service_role_all ON project_pages FOR ALL TO service_role USING (true) WITH CHECK (true);
-- marketplace_listings: RLS 策略已在 01_core_business.sql 中定义 (marketplace_listings_service_role + 细粒度策略)
CREATE POLICY service_role_all ON assets FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON legacy_asset_tag_relations FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON project_tags FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON user_asset_tags FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON workspace_members FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON workspace_invitations FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON user_recent_assets FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON user_favorite_assets FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON project_versions FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON user_asset_prompt_templates FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON credit_purchases FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON credit_transactions FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON generation_tasks FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON listing_usages FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON marketplace_favorites FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON marketplace_purchases FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON marketplace_reviews FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON user_page_prompt_templates FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON subscription_history FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON system_assets FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON system_resources FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON user_discounts FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON user_generations FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON system_error_logs FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON user_creation_logs FOR ALL TO service_role USING (true) WITH CHECK (true);

-- 02_platform_services.sql 中的表
CREATE POLICY service_role_all ON activity_logs FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON aggregated_stats FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON ai_usage_daily FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON analytics_aggregation FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON analytics_events FOR ALL TO service_role USING (true) WITH CHECK (true);
-- (已删除: clerk_webhook_events RLS policy)
CREATE POLICY service_role_all ON config_audit_logs FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON daily_metrics FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON daily_themes FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON feature_flags FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON holidays FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON monthly_metrics FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON hourly_metrics FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON notifications FOR ALL TO service_role USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS service_role_all ON stripe_webhook_events;
CREATE POLICY service_role_all ON stripe_webhook_events FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON system_resource_audit_logs FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON user_events FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON campaigns FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON content_reports FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON experiments FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON onboarding_steps FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON articles FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON experiment_configs FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON flag_exposures FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON flag_audit_logs FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON campaign_dismissals FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON campaign_participations FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON experiment_assignments FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON experiment_conversions FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON experiment_exposures FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON experiment_results FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON referrals FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON user_onboarding_progress FOR ALL TO service_role USING (true) WITH CHECK (true);

-- 03_infrastructure.sql 中的表
CREATE POLICY service_role_all ON admin_operations FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON ai_call_logs FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON api_logs FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON error_logs FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON payment_records FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON pricing_plans FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON scheduled_task_logs FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON system_configs FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON pricing_history FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON support_tickets FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON user_price_overrides FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all ON support_replies FOR ALL TO service_role USING (true) WITH CHECK (true);


-- ============================================================================
-- WS3: Authenticated User RLS Policies (Defense-in-Depth)
-- ============================================================================
-- 策略说明:
-- - 后端通过 service_role key 访问，不受这些策略影响
-- - 这些策略作为额外防线：即使 anon/authenticated key 泄露，
--   authenticated 用户也只能访问自己的数据
-- - user_id 字段类型为 TEXT (Clerk ID 格式: user_xxx)
-- - auth.uid() 匹配 Supabase Auth JWT 中的用户 ID
-- ============================================================================

-- Projects: authenticated 策略已在 01_core_business.sql 中定义 (projects_owner_policy)

-- Assets: 用户只能访问自己的素材
CREATE POLICY auth_user_own_assets ON assets
    FOR ALL TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Project Tags: 用户只能访问自己项目的标签 (通过 project 关联)
CREATE POLICY auth_user_own_project_tags ON project_tags
    FOR ALL TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM projects p
            WHERE p.id = project_id AND p.user_id = auth.uid()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM projects p
            WHERE p.id = project_id AND p.user_id = auth.uid()
        )
    );

-- Asset Tags: 用户只能访问自己素材的标签 (通过 asset 关联)
CREATE POLICY auth_user_own_asset_tags ON user_asset_tags
    FOR ALL TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM assets a
            WHERE a.id = asset_id AND a.user_id = auth.uid()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM assets a
            WHERE a.id = asset_id AND a.user_id = auth.uid()
        )
    );

-- Tags: 用户只能管理自己 workspace 的标签
CREATE POLICY auth_user_own_tags ON tags
    FOR ALL TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM workspaces w
            WHERE w.id = workspace_id AND w.owner_id = auth.uid()
        )
        OR EXISTS (
            SELECT 1 FROM workspace_members wm
            WHERE wm.workspace_id = tags.workspace_id
              AND wm.user_id = auth.uid()
              AND wm.is_active = true
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM workspaces w
            WHERE w.id = workspace_id AND w.owner_id = auth.uid()
        )
        OR EXISTS (
            SELECT 1 FROM workspace_members wm
            WHERE wm.workspace_id = tags.workspace_id
              AND wm.user_id = auth.uid()
              AND wm.is_active = true
        )
    );

-- Profiles: 用户只能读取/更新自己的 profile
CREATE POLICY auth_user_own_profile ON profiles
    FOR ALL TO authenticated
    USING (id = auth.uid())
    WITH CHECK (id = auth.uid());

-- Credit Transactions: 用户只能读取自己的积分流水
CREATE POLICY auth_user_own_credit_transactions ON credit_transactions
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());

-- Notifications: 用户只能读取自己的通知
CREATE POLICY auth_user_own_notifications ON notifications
    FOR ALL TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());


-- ============================================================================
-- 维护任务配置 (v3.30)
-- ============================================================================
-- 说明: 定期清理和优化配置，防止日志表无限增长
-- ============================================================================

-- 查看表大小监控视图 (运维视图，放在 internal schema，PostgREST 不暴露)
DROP VIEW IF EXISTS public.v_table_sizes CASCADE;
CREATE OR REPLACE VIEW internal.v_table_sizes AS
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_indexes_size(schemaname||'.'||tablename)) AS indexes_size,
    (SELECT COUNT(*) FROM information_schema.tables WHERE table_name = tablename) AS row_count_estimate
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

COMMENT ON VIEW internal.v_table_sizes IS '数据库表大小监控视图';


-- 查看日志表统计函数
CREATE OR REPLACE FUNCTION get_log_tables_stats()
RETURNS TABLE(
    table_name TEXT,
    total_rows BIGINT,
    old_rows BIGINT,
    retention_days INTEGER,
    next_cleanup_count BIGINT,
    table_size TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        'user_creation_logs'::TEXT,
        COUNT(*)::BIGINT AS total_rows,
        COUNT(*) FILTER (WHERE created_at < NOW() - INTERVAL '90 days')::BIGINT AS old_rows,
        90 AS retention_days,
        COUNT(*) FILTER (WHERE created_at < NOW() - INTERVAL '90 days')::BIGINT AS next_cleanup_count,
        pg_size_pretty(pg_total_relation_size('user_creation_logs'))::TEXT AS table_size
    FROM user_creation_logs
    
    UNION ALL
    
    SELECT 
        'error_logs'::TEXT,
        COUNT(*)::BIGINT,
        COUNT(*) FILTER (WHERE created_at < NOW() - INTERVAL '30 days')::BIGINT,
        30,
        COUNT(*) FILTER (WHERE created_at < NOW() - INTERVAL '30 days')::BIGINT,
        pg_size_pretty(pg_total_relation_size('error_logs'))::TEXT
    FROM error_logs
    
    UNION ALL
    
    SELECT 
        'activity_logs'::TEXT,
        COUNT(*)::BIGINT,
        COUNT(*) FILTER (WHERE created_at < NOW() - INTERVAL '180 days')::BIGINT,
        180,
        COUNT(*) FILTER (WHERE created_at < NOW() - INTERVAL '180 days')::BIGINT,
        pg_size_pretty(pg_total_relation_size('activity_logs'))::TEXT
    FROM activity_logs;
END;
$$ LANGUAGE plpgsql
SET search_path = 'public';

COMMENT ON FUNCTION get_log_tables_stats() IS '获取日志表统计信息（用于监控清理效果）';


-- 清理错误日志函数
CREATE OR REPLACE FUNCTION cleanup_old_error_logs(p_retention_days INTEGER DEFAULT 30)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_deleted_count INTEGER;
BEGIN
    DELETE FROM error_logs
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '1 day' * p_retention_days;
    
    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;
    
    -- 记录清理操作
    INSERT INTO activity_logs (
        user_id,
        action,
        metadata,
        created_at
    ) VALUES (
        'system',
        'cleanup_error_logs',
        jsonb_build_object(
            'deleted_count', v_deleted_count,
            'retention_days', p_retention_days,
            'execution_time', CURRENT_TIMESTAMP
        ),
        CURRENT_TIMESTAMP
    );
    
    RETURN v_deleted_count;
END;
$$;

COMMENT ON FUNCTION cleanup_old_error_logs IS '清理旧的错误日志（保留 N 天）';


-- 清理活动日志函数
CREATE OR REPLACE FUNCTION cleanup_old_activity_logs(
    p_retention_days INTEGER DEFAULT 180,
    p_preserve_actions TEXT[] DEFAULT ARRAY['user_signup', 'subscription_purchase']
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_deleted_count INTEGER;
BEGIN
    DELETE FROM activity_logs
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '1 day' * p_retention_days
      AND action != ALL(p_preserve_actions);  -- Preserve critical events

    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;

    RETURN v_deleted_count;
END;
$$;

COMMENT ON FUNCTION cleanup_old_activity_logs IS '清理旧的活动日志（保留 N 天，排除关键事件）';


-- ============================================================================
-- WS-25 (GROW-01): Purge expired soft-deleted records
-- Permanently removes records where recovery_expires_at has passed.
-- Covers: assets, projects, support_tickets, support_replies
-- ============================================================================
CREATE OR REPLACE FUNCTION cleanup_expired_soft_deletes()
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_assets INTEGER := 0;
    v_projects INTEGER := 0;
    v_tickets INTEGER := 0;
    v_replies INTEGER := 0;
BEGIN
    -- 1. Purge expired soft-deleted assets
    DELETE FROM assets
    WHERE is_deleted = true
      AND recovery_expires_at IS NOT NULL
      AND recovery_expires_at < CURRENT_TIMESTAMP;
    GET DIAGNOSTICS v_assets = ROW_COUNT;

    -- 2. Purge expired soft-deleted projects
    DELETE FROM projects
    WHERE is_deleted = true
      AND recovery_expires_at IS NOT NULL
      AND recovery_expires_at < CURRENT_TIMESTAMP;
    GET DIAGNOSTICS v_projects = ROW_COUNT;

    -- 3. Purge expired soft-deleted support tickets
    DELETE FROM support_tickets
    WHERE is_deleted = true
      AND recovery_expires_at IS NOT NULL
      AND recovery_expires_at < CURRENT_TIMESTAMP;
    GET DIAGNOSTICS v_tickets = ROW_COUNT;

    -- 4. Purge expired soft-deleted support replies
    DELETE FROM support_replies
    WHERE is_deleted = true
      AND recovery_expires_at IS NOT NULL
      AND recovery_expires_at < CURRENT_TIMESTAMP;
    GET DIAGNOSTICS v_replies = ROW_COUNT;

    RETURN jsonb_build_object(
        'assets_purged', v_assets,
        'projects_purged', v_projects,
        'tickets_purged', v_tickets,
        'replies_purged', v_replies,
        'total_purged', v_assets + v_projects + v_tickets + v_replies
    );
END;
$$;

COMMENT ON FUNCTION cleanup_expired_soft_deletes IS 'WS-25: Purge expired soft-deleted records across all tables with recovery_expires_at';


-- ============================================================================
-- WS3: check_webhook_idempotency — Webhook 事件幂等性检查
-- 与已有 p_start_webhook_processing / p_complete_webhook_processing 配合使用
-- 调用顺序: check_webhook_idempotency → p_start_webhook_processing → 业务逻辑 → p_complete_webhook_processing
-- ============================================================================
CREATE OR REPLACE FUNCTION check_webhook_idempotency(
    p_event_id TEXT,
    p_event_type TEXT,
    p_payload JSONB DEFAULT '{}'::JSONB
)
RETURNS JSONB AS $$
DECLARE
    v_existing_id UUID;
    v_processed BOOLEAN;
BEGIN
    -- 输入验证
    IF p_event_id IS NULL OR length(p_event_id) = 0 THEN
        RETURN jsonb_build_object('idempotent', false, 'error', 'Invalid event_id');
    END IF;

    -- 原子 INSERT (ON CONFLICT 保证并发安全)
    INSERT INTO stripe_webhook_events (
        event_id, event_type, payload, processed, created_at
    ) VALUES (
        p_event_id, p_event_type, p_payload, false, NOW()
    )
    ON CONFLICT (event_id) DO NOTHING
    RETURNING id INTO v_existing_id;

    IF v_existing_id IS NOT NULL THEN
        -- 首次插入成功 → 未处理过
        RETURN jsonb_build_object('idempotent', false, 'event_id', p_event_id);
    ELSE
        -- 已存在 → 检查是否已处理
        SELECT processed INTO v_processed
        FROM stripe_webhook_events
        WHERE event_id = p_event_id;

        RETURN jsonb_build_object(
            'idempotent', true,
            'event_id', p_event_id,
            'already_processed', COALESCE(v_processed, false)
        );
    END IF;
END;
$$ LANGUAGE plpgsql
SET search_path = 'public';

COMMENT ON FUNCTION check_webhook_idempotency IS 'WS3: Webhook 事件幂等性检查 (ON CONFLICT 原子去重)';


-- ============================================================================
-- 提交事务
-- ============================================================================
COMMIT;
