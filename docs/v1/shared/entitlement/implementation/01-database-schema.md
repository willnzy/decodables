# 数据库 Schema 实现

> **版本**: v1.0
> **日期**: 2026-02-04
> **状态**: 🔴 待实现
> **Schema 文件**: `decodables/migrations/v2/01_core_business.sql`

---

## 相关设计文档

| 设计文档 | 本文档章节 |
|----------|-----------|
| 02-tier-config.md | §2.1, §2.2 |
| 04-feature-flag-engine.md | §2.3 |
| 08-user-groups.md | §2.4 |
| 09-config-versioning.md | §2.5 |
| 10-workspace-override.md | §2.6 |
| 11-trial-expiration.md | §3.1 |
| 12-tier-downgrade.md | §3.2 |
| 13-subscription-pause.md | §3.3 |
| 14-billing-cycle-switch.md | §3.4 |
| 15-credits-lifecycle.md | §3.5 |
| 16-renewal-reminders.md | §3.6 |
| 17-invoice-management.md | §3.7 |
| 18-refund-processing.md | §3.8 |
| 19-promotions.md | §4.1 |
| 20-referral-rewards.md | §4.2 |
| 21-education-discount.md | §4.3 |
| 22-free-quota.md | §4.4 |

---

## 目录

- [§1. 概述](#1-概述)
- [§2. 核心配置表](#2-核心配置表)
  - [§2.1 system_configs](#21-system_configs)
  - [§2.2 user_feature_overrides](#22-user_feature_overrides)
  - [§2.3 feature_flags](#23-feature_flags)
  - [§2.4 user_groups / user_group_members](#24-user_groups--user_group_members)
  - [§2.5 config_versions](#25-config_versions)
  - [§2.6 workspace_overrides](#26-workspace_overrides)
- [§3. 生命周期表](#3-生命周期表)
  - [§3.1 trial_records](#31-trial_records)
  - [§3.2 tier_downgrade_logs](#32-tier_downgrade_logs)
  - [§3.3 subscription_pause_records](#33-subscription_pause_records)
  - [§3.4 billing_cycle_changes](#34-billing_cycle_changes)
  - [§3.5 credit_pools / credit_transactions](#35-credit_pools--credit_transactions)
  - [§3.6 renewal_reminder_logs](#36-renewal_reminder_logs)
  - [§3.7 invoices](#37-invoices)
  - [§3.8 refunds](#38-refunds)
- [§4. 营销扩展表](#4-营销扩展表)
  - [§4.1 promotions / user_promotions](#41-promotions--user_promotions)
  - [§4.2 referral_codes / referral_rewards](#42-referral_codes--referral_rewards)
  - [§4.3 education_verifications](#43-education_verifications)
  - [§4.4 free_quota_usage](#44-free_quota_usage)
- [§5. RPC 函数](#5-rpc-函数)
- [§6. 索引策略](#6-索引策略)

---

## §1. 概述

### 1.1 Schema 文件位置

所有 Entitlement 相关表定义在:
```
decodables/migrations/v2/01_core_business.sql
```

### 1.2 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 表名 | snake_case 复数 | `credit_pools`, `user_groups` |
| 字段名 | snake_case | `created_at`, `user_id` |
| 主键 | `id` (UUID) | `id UUID PRIMARY KEY` |
| 外键 | `{table}_id` | `user_id`, `group_id` |
| 时间戳 | `{action}_at` | `created_at`, `expires_at` |
| 布尔字段 | `is_{state}` | `is_active`, `is_deleted` |

### 1.3 通用字段

每个表必须包含:

```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
created_at TIMESTAMPTZ DEFAULT NOW(),
updated_at TIMESTAMPTZ DEFAULT NOW()
```

---

## §2. 核心配置表

### §2.1 system_configs

> 设计文档: [02-tier-config.md](../02-tier-config.md) §2

**实现状态**: 🟢 已存在

**表定义**:

```sql
-- 已存在于 01_core_business.sql
CREATE TABLE IF NOT EXISTS system_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(100) NOT NULL UNIQUE,
    value JSONB NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Tier 配置数据**:

```sql
-- TIER_FEATURES 配置
INSERT INTO system_configs (key, value, description) VALUES
('TIER_FEATURES', '{
  "t1": {
    "platform_assets": true,
    "vector_tools": true,
    "freehand_tools": true,
    "pdf_export": true,
    "pdf_print": true,
    "can_subscribe": true,
    "clipboard_paste": "trial",
    "ai_features": "trial",
    "smart_scan": "trial",
    "zip_export": "trial",
    "publish_paid": "trial",
    "publish_free": "trial",
    "browse_marketplace": "trial",
    "purchase_marketplace": "trial",
    "can_upload_custom_assets": "trial",
    "recover_deleted": false,
    "can_invite_members": false,
    "can_purchase_credits": false
  },
  "t2": { ... },
  "t3": { ... },
  "t4": { ... }
}', 'Tier 功能权限配置');

-- TIER_QUOTAS 配置
INSERT INTO system_configs (key, value, description) VALUES
('TIER_QUOTAS', '{
  "t1": { "max_projects": 3, "max_pages_per_project": 6, "max_custom_assets": 0 },
  "t2": { "max_projects": 50, "max_pages_per_project": 24, "max_custom_assets": 0 },
  "t3": { "max_projects": -1, "max_pages_per_project": -1, "max_custom_assets": -1 },
  "t4": { "max_projects": -1, "max_pages_per_project": -1, "max_custom_assets": -1 }
}', 'Tier 配额限制');
```

### §2.2 user_feature_overrides

> 设计文档: [02-tier-config.md](../02-tier-config.md) §3

**实现状态**: 🔴 待创建

**表定义**:

```sql
CREATE TABLE IF NOT EXISTS user_feature_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    feature_key VARCHAR(50) NOT NULL,
    override_value JSONB NOT NULL,  -- { "enabled": true/false/"trial", "quota": 100 }
    reason VARCHAR(100),             -- 覆盖原因
    granted_by UUID REFERENCES profiles(id),  -- 授权管理员
    expires_at TIMESTAMPTZ,          -- NULL = 永久
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id, feature_key)
);

-- 索引
CREATE INDEX idx_user_feature_overrides_user ON user_feature_overrides(user_id);
CREATE INDEX idx_user_feature_overrides_expires ON user_feature_overrides(expires_at)
    WHERE expires_at IS NOT NULL;
```

### §2.3 feature_flags

> 设计文档: [04-feature-flag-engine.md](../04-feature-flag-engine.md) §2

**实现状态**: 🔴 待创建

**表定义**:

```sql
CREATE TABLE IF NOT EXISTS feature_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    flag_type VARCHAR(20) NOT NULL DEFAULT 'release',  -- release, experiment, ops, permission
    enabled BOOLEAN NOT NULL DEFAULT false,
    rollout_percentage INT DEFAULT 0,  -- 0-100
    targeting_rules JSONB DEFAULT '[]',  -- 定向规则
    default_value JSONB NOT NULL DEFAULT 'false',
    variants JSONB DEFAULT '[]',  -- A/B 测试变体
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_feature_flags_type ON feature_flags(flag_type);
CREATE INDEX idx_feature_flags_enabled ON feature_flags(enabled) WHERE enabled = true;
```

### §2.4 user_groups / user_group_members

> 设计文档: [08-user-groups.md](../08-user-groups.md)

**实现状态**: 🔴 待创建

**表定义**:

```sql
-- 用户组
CREATE TABLE IF NOT EXISTS user_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    group_type VARCHAR(20) NOT NULL DEFAULT 'manual',  -- manual, auto, tier_based
    auto_rules JSONB DEFAULT '{}',  -- 自动规则
    priority INT DEFAULT 0,  -- 冲突时优先级
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 用户组成员
CREATE TABLE IF NOT EXISTS user_group_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES user_groups(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    added_by UUID REFERENCES profiles(id),
    added_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(group_id, user_id)
);

-- 索引
CREATE INDEX idx_user_group_members_user ON user_group_members(user_id);
CREATE INDEX idx_user_group_members_group ON user_group_members(group_id);
```

### §2.5 config_versions

> 设计文档: [09-config-versioning.md](../09-config-versioning.md)

**实现状态**: 🔴 待创建

**表定义**:

```sql
CREATE TABLE IF NOT EXISTS config_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_key VARCHAR(100) NOT NULL,
    version INT NOT NULL,
    value JSONB NOT NULL,
    changed_by UUID REFERENCES profiles(id),
    change_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(config_key, version)
);

-- 索引
CREATE INDEX idx_config_versions_key ON config_versions(config_key, version DESC);
```

### §2.6 workspace_overrides

> 设计文档: [10-workspace-override.md](../10-workspace-override.md)

**实现状态**: 🔴 待创建

**表定义**:

```sql
CREATE TABLE IF NOT EXISTS workspace_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,  -- 关联 workspaces 表
    feature_key VARCHAR(50) NOT NULL,
    override_value JSONB NOT NULL,
    reason VARCHAR(100),
    granted_by UUID REFERENCES profiles(id),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(workspace_id, feature_key)
);

-- 索引
CREATE INDEX idx_workspace_overrides_workspace ON workspace_overrides(workspace_id);
```

---

## §3. 生命周期表

### §3.1 trial_records

> 设计文档: [11-trial-expiration.md](../11-trial-expiration.md)

**实现状态**: 🔴 待创建

**表定义**:

```sql
CREATE TABLE IF NOT EXISTS trial_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    feature_key VARCHAR(50) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,  -- started_at + 7 days
    status VARCHAR(20) NOT NULL DEFAULT 'active',  -- active, expired, converted
    converted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id, feature_key)
);

-- 索引
CREATE INDEX idx_trial_records_user ON trial_records(user_id);
CREATE INDEX idx_trial_records_expires ON trial_records(expires_at)
    WHERE status = 'active';
```

### §3.2 tier_downgrade_logs

> 设计文档: [12-tier-downgrade.md](../12-tier-downgrade.md)

**实现状态**: 🔴 待创建

**表定义**:

```sql
CREATE TABLE IF NOT EXISTS tier_downgrade_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id),
    from_tier VARCHAR(10) NOT NULL,
    to_tier VARCHAR(10) NOT NULL,
    reason VARCHAR(50) NOT NULL,  -- subscription_cancelled, payment_failed, manual
    affected_resources JSONB DEFAULT '{}',  -- 受影响的资源统计
    processed_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_tier_downgrade_logs_user ON tier_downgrade_logs(user_id, processed_at DESC);
```

### §3.3 subscription_pause_records

> 设计文档: [13-subscription-pause.md](../13-subscription-pause.md)

**实现状态**: 🔴 待创建

**表定义**:

```sql
CREATE TABLE IF NOT EXISTS subscription_pause_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id),
    subscription_id UUID NOT NULL,
    paused_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resume_at TIMESTAMPTZ,  -- 计划恢复时间
    resumed_at TIMESTAMPTZ,  -- 实际恢复时间
    pause_reason VARCHAR(100),
    status VARCHAR(20) NOT NULL DEFAULT 'paused',  -- paused, resumed, cancelled
    max_pause_days INT DEFAULT 90,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_subscription_pause_user ON subscription_pause_records(user_id);
CREATE INDEX idx_subscription_pause_status ON subscription_pause_records(status)
    WHERE status = 'paused';
```

### §3.4 billing_cycle_changes

> 设计文档: [14-billing-cycle-switch.md](../14-billing-cycle-switch.md)

**实现状态**: 🔴 待创建

**表定义**:

```sql
CREATE TABLE IF NOT EXISTS billing_cycle_changes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id),
    subscription_id UUID NOT NULL,
    from_cycle VARCHAR(20) NOT NULL,  -- monthly, yearly
    to_cycle VARCHAR(20) NOT NULL,
    effective_at TIMESTAMPTZ NOT NULL,  -- 生效时间
    proration_amount DECIMAL(10,2),  -- 差价金额
    stripe_proration_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_billing_cycle_changes_user ON billing_cycle_changes(user_id);
```

### §3.5 credit_pools / credit_transactions

> 设计文档: [15-credits-lifecycle.md](../15-credits-lifecycle.md)

**实现状态**: 🔴 待创建

**表定义**:

```sql
-- 积分池 (二维模型: source_type + expires_at)
CREATE TABLE IF NOT EXISTS credit_pools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    source_type VARCHAR(20) NOT NULL,  -- 7 种来源
    -- subscription, purchase, bonus_signup, bonus_referral,
    -- bonus_campaign, compensation, earning
    source_id UUID,  -- 关联来源记录
    initial_amount INT NOT NULL,
    balance INT NOT NULL DEFAULT 0,
    expires_at TIMESTAMPTZ,  -- NULL = 永久
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 积分交易流水
CREATE TABLE IF NOT EXISTS credit_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id),
    pool_id UUID REFERENCES credit_pools(id),
    transaction_type VARCHAR(20) NOT NULL,  -- grant, consume, expire, refund, transfer
    amount INT NOT NULL,  -- 正数=增加, 负数=扣除
    balance_after INT NOT NULL,  -- 交易后余额
    description TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_credit_pools_user_source ON credit_pools(user_id, source_type);
CREATE INDEX idx_credit_pools_expires ON credit_pools(expires_at)
    WHERE expires_at IS NOT NULL AND balance > 0;
CREATE INDEX idx_credit_transactions_user ON credit_transactions(user_id, created_at DESC);
```

### §3.6 renewal_reminder_logs

> 设计文档: [16-renewal-reminders.md](../16-renewal-reminders.md)

**实现状态**: 🔴 待创建

**表定义**:

```sql
CREATE TABLE IF NOT EXISTS renewal_reminder_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id),
    subscription_id UUID NOT NULL,
    reminder_type VARCHAR(20) NOT NULL,  -- 7_days, 3_days, 1_day, expired
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    channel VARCHAR(20) NOT NULL DEFAULT 'email',  -- email, push, in_app
    status VARCHAR(20) NOT NULL DEFAULT 'sent'  -- sent, delivered, failed
);

-- 索引
CREATE INDEX idx_renewal_reminder_logs_user ON renewal_reminder_logs(user_id, sent_at DESC);
```

### §3.7 invoices

> 设计文档: [17-invoice-management.md](../17-invoice-management.md)

**实现状态**: 🔴 待创建

**表定义**:

```sql
CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id),
    stripe_invoice_id TEXT UNIQUE,
    invoice_number VARCHAR(50) NOT NULL UNIQUE,
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(20) NOT NULL DEFAULT 'draft',  -- draft, open, paid, void, uncollectible
    invoice_type VARCHAR(20) NOT NULL,  -- subscription, credits, refund
    line_items JSONB NOT NULL DEFAULT '[]',
    billing_address JSONB,
    issued_at TIMESTAMPTZ,
    due_at TIMESTAMPTZ,
    paid_at TIMESTAMPTZ,
    pdf_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_invoices_user ON invoices(user_id, created_at DESC);
CREATE INDEX idx_invoices_status ON invoices(status) WHERE status IN ('open', 'draft');
```

### §3.8 refunds

> 设计文档: [18-refund-processing.md](../18-refund-processing.md)

**实现状态**: 🔴 待创建

**表定义**:

```sql
CREATE TABLE IF NOT EXISTS refunds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id),
    transaction_id UUID NOT NULL,  -- 原交易 ID
    stripe_refund_id TEXT,
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    refund_type VARCHAR(20) NOT NULL,  -- full, partial, credits
    reason VARCHAR(50),
    reason_detail TEXT,
    credits_deducted INT DEFAULT 0,
    credits_debt INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, processing, completed, failed
    requested_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    processed_by UUID REFERENCES profiles(id)
);

-- 索引
CREATE INDEX idx_refunds_user ON refunds(user_id, requested_at DESC);
CREATE INDEX idx_refunds_status ON refunds(status) WHERE status IN ('pending', 'processing');
```

---

## §4. 营销扩展表

### §4.1 promotions / user_promotions

> 设计文档: [19-promotions.md](../19-promotions.md)

**实现状态**: 🔴 待创建

**表定义**:

```sql
-- 促销活动
CREATE TABLE IF NOT EXISTS promotions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    promotion_type VARCHAR(20) NOT NULL,  -- discount, credits, trial_extension
    discount_type VARCHAR(20),  -- percentage, fixed
    discount_value DECIMAL(10,2),
    credits_amount INT,
    trial_days INT,
    applicable_tiers TEXT[] DEFAULT ARRAY['t1', 't2', 't3'],
    applicable_plans TEXT[],
    max_uses INT,  -- NULL = 无限
    uses_count INT DEFAULT 0,
    max_uses_per_user INT DEFAULT 1,
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 用户促销使用记录
CREATE TABLE IF NOT EXISTS user_promotions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id),
    promotion_id UUID NOT NULL REFERENCES promotions(id),
    applied_at TIMESTAMPTZ DEFAULT NOW(),
    subscription_id UUID,
    discount_amount DECIMAL(10,2),
    credits_granted INT,

    UNIQUE(user_id, promotion_id)
);

-- 索引
CREATE INDEX idx_promotions_code ON promotions(code) WHERE is_active = true;
CREATE INDEX idx_promotions_dates ON promotions(starts_at, ends_at) WHERE is_active = true;
CREATE INDEX idx_user_promotions_user ON user_promotions(user_id);
```

### §4.2 referral_codes / referral_rewards

> 设计文档: [20-referral-rewards.md](../20-referral-rewards.md)

**实现状态**: 🔴 待创建

**表定义**:

```sql
-- 邀请码
CREATE TABLE IF NOT EXISTS referral_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id),
    code VARCHAR(20) NOT NULL UNIQUE,
    uses_count INT DEFAULT 0,
    max_uses INT,  -- NULL = 无限
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 邀请奖励记录
CREATE TABLE IF NOT EXISTS referral_rewards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    referrer_id UUID NOT NULL REFERENCES profiles(id),  -- 邀请人
    referee_id UUID NOT NULL REFERENCES profiles(id),   -- 被邀请人
    referral_code_id UUID NOT NULL REFERENCES referral_codes(id),
    referrer_reward_type VARCHAR(20) NOT NULL,  -- credits
    referrer_reward_amount INT NOT NULL,
    referee_reward_type VARCHAR(20) NOT NULL,
    referee_reward_amount INT NOT NULL,
    referrer_credited BOOLEAN DEFAULT false,
    referee_credited BOOLEAN DEFAULT false,
    qualification_event VARCHAR(50),  -- signup, first_purchase, subscription
    qualified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_referral_codes_user ON referral_codes(user_id);
CREATE INDEX idx_referral_codes_code ON referral_codes(code) WHERE is_active = true;
CREATE INDEX idx_referral_rewards_referrer ON referral_rewards(referrer_id);
CREATE INDEX idx_referral_rewards_referee ON referral_rewards(referee_id);
```

### §4.3 education_verifications

> 设计文档: [21-education-discount.md](../21-education-discount.md)

**实现状态**: 🔴 待创建

**表定义**:

```sql
CREATE TABLE IF NOT EXISTS education_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id),
    institution_name VARCHAR(200) NOT NULL,
    institution_type VARCHAR(20) NOT NULL,  -- k12, higher_ed, teacher
    email_domain VARCHAR(100),
    document_url TEXT,  -- 证明文件 URL
    verification_method VARCHAR(20) NOT NULL,  -- email, document, third_party
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, approved, rejected
    discount_percentage INT DEFAULT 50,  -- 教育折扣比例
    verified_at TIMESTAMPTZ,
    verified_by UUID REFERENCES profiles(id),
    expires_at TIMESTAMPTZ,  -- 需要年度重新验证
    rejection_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_education_verifications_user ON education_verifications(user_id);
CREATE INDEX idx_education_verifications_status ON education_verifications(status)
    WHERE status = 'pending';
```

### §4.4 free_quota_usage

> 设计文档: [22-free-quota.md](../22-free-quota.md)

**实现状态**: 🔴 待创建

**表定义**:

```sql
CREATE TABLE IF NOT EXISTS free_quota_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id),
    feature_key VARCHAR(50) NOT NULL,
    period_start DATE NOT NULL,  -- 统计周期开始
    period_type VARCHAR(20) NOT NULL DEFAULT 'daily',  -- daily, weekly, monthly
    used_count INT NOT NULL DEFAULT 0,
    quota_limit INT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id, feature_key, period_start, period_type)
);

-- 索引
CREATE INDEX idx_free_quota_usage_user_feature ON free_quota_usage(user_id, feature_key);
CREATE INDEX idx_free_quota_usage_period ON free_quota_usage(period_start);
```

---

## §5. RPC 函数

### 5.1 积分扣费 (FEFO)

> 设计文档: [15-credits-lifecycle.md](../15-credits-lifecycle.md) §4

```sql
CREATE OR REPLACE FUNCTION consume_credits_fefo(
    p_user_id UUID,
    p_amount INT,
    p_description TEXT DEFAULT NULL
) RETURNS TABLE (
    success BOOLEAN,
    consumed INT,
    remaining_balance INT,
    pools_affected JSONB
) AS $$
DECLARE
    v_remaining INT := p_amount;
    v_total_balance INT;
    v_pools_affected JSONB := '[]'::JSONB;
    v_pool RECORD;
    v_deducted INT;
BEGIN
    -- 获取用户总余额
    SELECT COALESCE(SUM(balance), 0) INTO v_total_balance
    FROM credit_pools WHERE user_id = p_user_id AND balance > 0;

    IF v_total_balance < p_amount THEN
        RETURN QUERY SELECT false, 0, v_total_balance, '[]'::JSONB;
        RETURN;
    END IF;

    -- FEFO 顺序扣费
    FOR v_pool IN
        SELECT * FROM credit_pools
        WHERE user_id = p_user_id AND balance > 0
        ORDER BY
            CASE WHEN expires_at IS NULL THEN 1 ELSE 0 END,  -- 有过期时间的优先
            expires_at ASC,  -- 先过期先扣
            CASE source_type
                WHEN 'subscription' THEN 1
                WHEN 'bonus_signup' THEN 2
                WHEN 'bonus_referral' THEN 3
                WHEN 'bonus_campaign' THEN 4
                WHEN 'purchase' THEN 5
                WHEN 'earning' THEN 6
                WHEN 'compensation' THEN 7
            END
        FOR UPDATE
    LOOP
        EXIT WHEN v_remaining <= 0;

        v_deducted := LEAST(v_pool.balance, v_remaining);

        UPDATE credit_pools SET balance = balance - v_deducted, updated_at = NOW()
        WHERE id = v_pool.id;

        v_remaining := v_remaining - v_deducted;
        v_pools_affected := v_pools_affected || jsonb_build_object(
            'pool_id', v_pool.id,
            'source_type', v_pool.source_type,
            'deducted', v_deducted
        );
    END LOOP;

    -- 记录交易
    INSERT INTO credit_transactions (user_id, transaction_type, amount, balance_after, description)
    VALUES (p_user_id, 'consume', -p_amount, v_total_balance - p_amount, p_description);

    RETURN QUERY SELECT true, p_amount, v_total_balance - p_amount, v_pools_affected;
END;
$$ LANGUAGE plpgsql;
```

### 5.2 积分退款扣回 (FEFO 逆序)

> 设计文档: [18-refund-processing.md](../18-refund-processing.md) §3.3

```sql
CREATE OR REPLACE FUNCTION deduct_credits_for_refund(
    p_user_id UUID,
    p_amount INT
) RETURNS TABLE (
    success BOOLEAN,
    deducted INT,
    remaining_debt INT
) AS $$
DECLARE
    v_remaining INT := p_amount;
    v_pool RECORD;
    v_deducted INT;
BEGIN
    -- 按 FEFO 逆序扣回 (最后扣费的来源最先扣回)
    FOR v_pool IN
        SELECT * FROM credit_pools
        WHERE user_id = p_user_id AND balance > 0
        ORDER BY
            CASE source_type
                WHEN 'compensation' THEN 1
                WHEN 'earning' THEN 2
                WHEN 'purchase' THEN 3
                WHEN 'bonus_campaign' THEN 4
                WHEN 'bonus_referral' THEN 5
                WHEN 'bonus_signup' THEN 6
                WHEN 'subscription' THEN 7
            END,
            expires_at DESC NULLS FIRST  -- 永久积分先扣回
        FOR UPDATE
    LOOP
        EXIT WHEN v_remaining <= 0;

        v_deducted := LEAST(v_pool.balance, v_remaining);

        UPDATE credit_pools SET balance = balance - v_deducted, updated_at = NOW()
        WHERE id = v_pool.id;

        v_remaining := v_remaining - v_deducted;
    END LOOP;

    RETURN QUERY SELECT
        v_remaining = 0,
        p_amount - v_remaining,
        v_remaining;
END;
$$ LANGUAGE plpgsql;
```

### 5.3 权限计算

> 设计文档: [06-priority-rules.md](../06-priority-rules.md)

```sql
CREATE OR REPLACE FUNCTION get_user_feature_permission(
    p_user_id UUID,
    p_feature_key VARCHAR(50)
) RETURNS JSONB AS $$
DECLARE
    v_result JSONB;
    v_kill_switch BOOLEAN;
    v_feature_flag JSONB;
    v_user_override JSONB;
    v_group_override JSONB;
    v_workspace_override JSONB;
    v_tier_config JSONB;
    v_user_tier VARCHAR(10);
BEGIN
    -- 1. Kill Switch (最高优先级)
    SELECT value->p_feature_key INTO v_kill_switch
    FROM system_configs WHERE key = 'KILL_SWITCHES';

    IF v_kill_switch = false THEN
        RETURN jsonb_build_object('enabled', false, 'source', 'kill_switch');
    END IF;

    -- 2. Feature Flag
    SELECT jsonb_build_object('enabled', enabled, 'rollout', rollout_percentage)
    INTO v_feature_flag
    FROM feature_flags WHERE key = p_feature_key AND enabled = true;

    IF v_feature_flag IS NOT NULL THEN
        -- 检查用户是否在灰度范围内
        -- ... 灰度计算逻辑
    END IF;

    -- 3. User Override
    SELECT override_value INTO v_user_override
    FROM user_feature_overrides
    WHERE user_id = p_user_id AND feature_key = p_feature_key
    AND (expires_at IS NULL OR expires_at > NOW());

    IF v_user_override IS NOT NULL THEN
        RETURN v_user_override || jsonb_build_object('source', 'user_override');
    END IF;

    -- 4-5. Group/Workspace Override (略)

    -- 6. Tier Config
    SELECT tier INTO v_user_tier FROM profiles WHERE id = p_user_id;
    SELECT value->v_user_tier->p_feature_key INTO v_tier_config
    FROM system_configs WHERE key = 'TIER_FEATURES';

    IF v_tier_config IS NOT NULL THEN
        RETURN jsonb_build_object('enabled', v_tier_config, 'source', 'tier_config');
    END IF;

    -- 7. Fallback
    RETURN jsonb_build_object('enabled', false, 'source', 'fallback');
END;
$$ LANGUAGE plpgsql;
```

---

## §6. 索引策略

### 6.1 索引设计原则

1. **查询模式优先**: 根据实际查询模式创建索引
2. **部分索引**: 使用 WHERE 子句减少索引大小
3. **复合索引**: 高频联合查询使用复合索引
4. **避免过度索引**: 权衡查询性能与写入性能

### 6.2 索引汇总

| 表 | 索引 | 类型 | 用途 |
|----|------|------|------|
| credit_pools | (user_id, source_type) | 复合 | 用户积分查询 |
| credit_pools | (expires_at) WHERE balance > 0 | 部分 | 过期积分处理 |
| credit_transactions | (user_id, created_at DESC) | 复合 | 交易历史 |
| user_feature_overrides | (user_id) | 单列 | 用户权限查询 |
| user_feature_overrides | (expires_at) WHERE NOT NULL | 部分 | 过期清理 |
| feature_flags | (enabled) WHERE true | 部分 | 活跃 Flag 查询 |
| invoices | (user_id, created_at DESC) | 复合 | 发票历史 |
| invoices | (status) WHERE IN ('open', 'draft') | 部分 | 待处理发票 |

---

**END OF DOCUMENT**
