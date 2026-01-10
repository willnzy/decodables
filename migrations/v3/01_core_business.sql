-- ============================================================================
-- Make Decodables - 数据库架构 (文件 1/3)
-- ============================================================================
-- 分类: 核心业务
-- 说明: 用户、积分、项目、素材、市场
-- 执行顺序: 第 1 个执行
-- 生成时间: 2026-01-10
-- ============================================================================

-- 开始事务
BEGIN;

-- ============================================================================
-- 包含的表 (20)
-- ============================================================================
-- asset_categories
-- asset_prompt_templates
-- assets
-- credit_purchases
-- credit_transactions
-- generation_tasks
-- listing_usages
-- marketplace_favorites
-- marketplace_listings
-- marketplace_purchases
-- marketplace_reports
-- marketplace_reviews
-- page_prompt_templates
-- profiles
-- project_versions
-- projects
-- subscription_history
-- system_assets
-- user_discounts
-- user_generations


-- ----------------------------------------------------------------------------
-- 1. asset_categories
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



-- ----------------------------------------------------------------------------
-- 2. asset_prompt_templates
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
    deleted_at TIMESTAMPTZ,
    recovery_expires_at TIMESTAMPTZ,  -- 恢复期截止时间,过期后用户看不到此删除记录
    CONSTRAINT chk_asset_prompt_templates_deleted_at_consistency
        CHECK ((is_deleted = false AND deleted_at IS NULL) OR (is_deleted = true AND deleted_at IS NOT NULL)),
    CONSTRAINT chk_asset_prompt_templates_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);



-- ----------------------------------------------------------------------------
-- 3. assets
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



-- ----------------------------------------------------------------------------
-- 4. credit_purchases
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



-- ----------------------------------------------------------------------------
-- 5. credit_transactions
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



-- ----------------------------------------------------------------------------
-- 6. generation_tasks
-- ----------------------------------------------------------------------------
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



-- ----------------------------------------------------------------------------
-- 7. listing_usages
-- ----------------------------------------------------------------------------
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



-- ----------------------------------------------------------------------------
-- 8. marketplace_favorites
-- ----------------------------------------------------------------------------
CREATE TABLE marketplace_favorites (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    listing_id UUID NOT NULL REFERENCES marketplace_listings(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMPTZ,
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



-- ----------------------------------------------------------------------------
-- 9. marketplace_listings
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



-- ----------------------------------------------------------------------------
-- 10. marketplace_purchases
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



-- ----------------------------------------------------------------------------
-- 11. marketplace_reports
-- ----------------------------------------------------------------------------
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



-- ----------------------------------------------------------------------------
-- 12. marketplace_reviews
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
    deleted_at TIMESTAMPTZ,
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



-- ----------------------------------------------------------------------------
-- 13. page_prompt_templates
-- ----------------------------------------------------------------------------
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



-- ----------------------------------------------------------------------------
-- 14. profiles
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
    deleted_at TIMESTAMPTZ,
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



-- ----------------------------------------------------------------------------
-- 15. project_versions
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



-- ----------------------------------------------------------------------------
-- 16. projects
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
    deleted_at TIMESTAMPTZ,
    recovery_expires_at TIMESTAMPTZ,  -- 恢复期截止时间,过期后用户看不到此删除记录

    CONSTRAINT chk_projects_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);



-- ----------------------------------------------------------------------------
-- 17. subscription_history
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



-- ----------------------------------------------------------------------------
-- 18. system_assets
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



-- ----------------------------------------------------------------------------
-- 19. user_discounts
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



-- ----------------------------------------------------------------------------
-- 20. user_generations
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




-- ============================================================================
-- 提交事务
-- ============================================================================
COMMIT;
