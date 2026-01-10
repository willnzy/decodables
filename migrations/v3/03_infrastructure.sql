-- ============================================================================
-- Make Decodables - 数据库架构 (文件 3/3)
-- ============================================================================
-- 分类: 基础设施
-- 说明: 配置、日志、支持、管理、支付记录
-- 执行顺序: 第 3 个执行
-- 生成时间: 2026-01-10
-- ============================================================================

-- 开始事务
BEGIN;

-- ============================================================================
-- 包含的表 (12)
-- ============================================================================
-- admin_operations
-- ai_call_logs
-- api_logs
-- error_logs
-- payment_records
-- pricing_history
-- pricing_plans
-- scheduled_task_logs
-- support_replies
-- support_tickets
-- system_configs
-- user_price_overrides


-- ----------------------------------------------------------------------------
-- 1. admin_operations
-- ----------------------------------------------------------------------------
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



-- ----------------------------------------------------------------------------
-- 2. ai_call_logs
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



-- ----------------------------------------------------------------------------
-- 3. api_logs
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



-- ----------------------------------------------------------------------------
-- 4. error_logs
-- ----------------------------------------------------------------------------
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



-- ----------------------------------------------------------------------------
-- 5. payment_records
-- ----------------------------------------------------------------------------
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



-- ----------------------------------------------------------------------------
-- 6. pricing_history
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



-- ----------------------------------------------------------------------------
-- 7. pricing_plans
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



-- ----------------------------------------------------------------------------
-- 8. scheduled_task_logs
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



-- ----------------------------------------------------------------------------
-- 9. support_replies
-- ----------------------------------------------------------------------------
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


-- ----------------------------------------------------------------------------
-- 10. support_tickets
-- ----------------------------------------------------------------------------
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


-- ----------------------------------------------------------------------------
-- 11. system_configs
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



-- ----------------------------------------------------------------------------
-- 12. user_price_overrides
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
$$ LANGUAGE plpgsql;


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
$$ LANGUAGE plpgsql;


-- 函数 3
CREATE OR REPLACE FUNCTION prevent_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Table % is append-only. UPDATE and DELETE operations are not allowed.', TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;


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
$$ LANGUAGE plpgsql;


-- 函数 5
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


-- 函数 6
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


-- 函数 7
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
$$ LANGUAGE plpgsql;


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
$$ LANGUAGE plpgsql;


-- 函数 10
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
$$ LANGUAGE plpgsql;


-- ============================================================================
-- 视图定义 (1)
-- ============================================================================

-- 视图 1
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


-- ============================================================================
-- 初始数据
-- ============================================================================

-- holidays 表初始数据
INSERT INTO holidays (name, slug, month, day, regions, category, is_major, description) VALUES
('New Year', 'new-year', 1, 1, ARRAY['global'], 'cultural', true, 'New Year Day celebration'),
('Valentine''s Day', 'valentines-day', 2, 14, ARRAY['global'], 'cultural', true, 'Day of love and romance'),
('Halloween', 'halloween', 10, 31, ARRAY['US', 'UK', 'CA'], 'cultural', true, 'Spooky celebration'),
('Christmas', 'christmas', 12, 25, ARRAY['global'], 'cultural', true, 'Christmas Day celebration')
ON CONFLICT (slug) DO NOTHING;

-- pricing_plans 表初始数据
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

-- system_configs 表初始数据
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


-- ============================================================================
-- 提交事务
-- ============================================================================
COMMIT;
