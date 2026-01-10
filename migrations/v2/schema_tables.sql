-- ============================================================================
-- Make Decodables - 表结构定义
-- ============================================================================
-- 生成时间: 2026-01-10
-- 来源: refactored_schema_v2.sql
-- PostgreSQL 版本: 15+
-- ============================================================================

BEGIN;


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
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

ALTER TABLE credit_transactions ENABLE ROW LEVEL SECURITY;

ALTER TABLE user_generations ENABLE ROW LEVEL SECURITY;

ALTER TABLE marketplace_listings ENABLE ROW LEVEL SECURITY;

ALTER TABLE marketplace_purchases ENABLE ROW LEVEL SECURITY;

ALTER TABLE system_configs ENABLE ROW LEVEL SECURITY;

ALTER TABLE pricing_plans ENABLE ROW LEVEL SECURITY;

ALTER TABLE pricing_history ENABLE ROW LEVEL SECURITY;

ALTER TABLE holidays ENABLE ROW LEVEL SECURITY;

ALTER TABLE daily_themes ENABLE ROW LEVEL SECURITY;

ALTER TABLE system_assets ENABLE ROW LEVEL SECURITY;

ALTER TABLE asset_categories ENABLE ROW LEVEL SECURITY;

ALTER TABLE feature_flags ENABLE ROW LEVEL SECURITY;

ALTER TABLE experiments ENABLE ROW LEVEL SECURITY;

ALTER TABLE experiment_assignments ENABLE ROW LEVEL SECURITY;

ALTER TABLE experiment_results ENABLE ROW LEVEL SECURITY;

ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY;

ALTER TABLE campaign_participations ENABLE ROW LEVEL SECURITY;

ALTER TABLE campaign_dismissals ENABLE ROW LEVEL SECURITY;

ALTER TABLE api_logs ENABLE ROW LEVEL SECURITY;

ALTER TABLE ai_call_logs ENABLE ROW LEVEL SECURITY;

ALTER TABLE ai_usage_daily ENABLE ROW LEVEL SECURITY;

ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY;

ALTER TABLE analytics_events ENABLE ROW LEVEL SECURITY;

ALTER TABLE analytics_aggregation ENABLE ROW LEVEL SECURITY;

ALTER TABLE scheduled_task_logs ENABLE ROW LEVEL SECURITY;

ALTER TABLE clerk_webhook_events ENABLE ROW LEVEL SECURITY;

ALTER TABLE stripe_webhook_events ENABLE ROW LEVEL SECURITY;

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



COMMIT;
