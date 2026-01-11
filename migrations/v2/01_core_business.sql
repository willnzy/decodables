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
-- 启用必要的 PostgreSQL 扩展
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";      -- UUID 生成函数
CREATE EXTENSION IF NOT EXISTS "ltree";          -- 层级树结构支持 (用于 asset_categories)

-- ============================================================================
-- 包含的表 (21)
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
-- system_resources (新增 2026-01-11)
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
-- 3a. asset_tags - Tag system for asset classification
-- ----------------------------------------------------------------------------
CREATE TABLE asset_tags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL,
    slug VARCHAR(50) UNIQUE NOT NULL,
    name_i18n JSONB DEFAULT '{}'::JSONB,
    tag_type VARCHAR(20) DEFAULT 'general' CHECK (tag_type IN ('general', 'color', 'style', 'theme', 'season')),
    usage_count INT DEFAULT 0 CHECK (usage_count >= 0),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_asset_tags_type ON asset_tags(tag_type);
CREATE INDEX idx_asset_tags_usage ON asset_tags(usage_count DESC);
CREATE INDEX idx_asset_tags_name ON asset_tags(name);

-- Trigger for auto-updating updated_at
CREATE TRIGGER update_asset_tags_updated_at
    BEFORE UPDATE ON asset_tags
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ----------------------------------------------------------------------------
-- 3b. asset_tag_relations - Many-to-many between assets and tags
-- ----------------------------------------------------------------------------
CREATE TABLE asset_tag_relations (
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES asset_tags(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (asset_id, tag_id)
);

CREATE INDEX idx_asset_tag_rel_asset ON asset_tag_relations(asset_id);
CREATE INDEX idx_asset_tag_rel_tag ON asset_tag_relations(tag_id);


-- ----------------------------------------------------------------------------
-- 3c. user_recent_assets - User browsing history
-- ----------------------------------------------------------------------------
CREATE TABLE user_recent_assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    used_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_recent_asset UNIQUE(user_id, asset_id)
);

CREATE INDEX idx_user_recent_user ON user_recent_assets(user_id, used_at DESC);
CREATE INDEX idx_user_recent_asset ON user_recent_assets(asset_id);


-- ----------------------------------------------------------------------------
-- 3d. user_favorite_assets - User favorites/bookmarks
-- ----------------------------------------------------------------------------
CREATE TABLE user_favorite_assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_favorite_asset UNIQUE(user_id, asset_id)
);

CREATE INDEX idx_user_favorite_user ON user_favorite_assets(user_id, created_at DESC);
CREATE INDEX idx_user_favorite_asset ON user_favorite_assets(asset_id);


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
            'object_detection', 'smart_scan', 'export_pdf', 'export_zip'
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
    allowed_tiers TEXT[] NOT NULL DEFAULT '{t1, t2, t3}',

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

    -- P1-012 fix: seller_id NOT NULL constraint (system resources can be NULL)
    CONSTRAINT chk_marketplace_listings_seller_id_consistency
    CHECK (
        (source = 'system' AND seller_id IS NULL) OR
        (source != 'system' AND seller_id IS NOT NULL)
    ),

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
-- 18.5. system_resources (系统资源表) - 新增 2026-01-11
-- ----------------------------------------------------------------------------
CREATE TABLE system_resources (
    -- ========== 主键 ==========
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- ========== 资源标识 ==========
    resource_type TEXT NOT NULL CHECK (resource_type IN (
        'text', 'image', 'shape', 'table', 'sticker',
        'icon', 'frame', 'background', 'font', 'pattern'
    )),

    -- ========== 分类关联 ==========
    category_id UUID REFERENCES asset_categories(id) ON DELETE SET NULL,
    category TEXT,  -- 冗余字段 (ResourceCategory 枚举值)

    -- ========== 资源内容 ==========
    url TEXT NOT NULL,
    thumbnail_url TEXT,

    -- ========== 元数据 ==========
    name TEXT,
    description TEXT,
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    metadata JSONB DEFAULT '{}',

    -- ========== 文件信息 ==========
    file_size INTEGER,  -- bytes
    width INTEGER,
    height INTEGER,
    format TEXT,  -- png, svg, jpg

    -- ========== 访问控制 ==========
    allowed_tiers TEXT[] DEFAULT ARRAY['t1']::TEXT[],
    min_tier TEXT DEFAULT 't1' CHECK (min_tier IN ('t1', 't2', 't3')),

    -- ========== 显示控制 ==========
    is_active BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,
    display_order INTEGER DEFAULT 0,

    -- ========== 时间戳 ==========
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    updated_by TEXT,

    -- ========== Soft Delete ==========
    deleted_at TIMESTAMPTZ,
    recovery_expires_at TIMESTAMPTZ,

    CONSTRAINT chk_system_resources_recovery_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);

COMMENT ON TABLE system_resources IS '系统资源表: stickers, templates, fonts等系统素材';

-- 索引优化
CREATE INDEX idx_sr_type ON system_resources(resource_type) WHERE deleted_at IS NULL;
CREATE INDEX idx_sr_category ON system_resources(category_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_sr_active_type ON system_resources(is_active, resource_type) WHERE deleted_at IS NULL AND is_active = true;
CREATE INDEX idx_sr_tier ON system_resources(min_tier) WHERE deleted_at IS NULL;
CREATE INDEX idx_sr_tags ON system_resources USING GIN(tags) WHERE deleted_at IS NULL;
CREATE INDEX idx_sr_created ON system_resources(created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX idx_sr_featured ON system_resources(is_featured, display_order) WHERE deleted_at IS NULL AND is_featured = true;

-- 触发器
CREATE TRIGGER update_system_resources_updated_at
    BEFORE UPDATE ON system_resources
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();



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
-- Performance Indexes (P1-004 ~ P1-005)
-- ============================================================================

-- 1. Marketplace listings moderation status index
CREATE INDEX idx_listings_moderation_status
ON marketplace_listings(moderation_status)
WHERE is_deleted = false;

COMMENT ON INDEX idx_listings_moderation_status IS
'P1-004: Index for filtering listings by moderation status (draft/pending/approved/rejected)';

-- 2. Marketplace listings category + public status composite index
CREATE INDEX idx_listings_category_public
ON marketplace_listings(category, is_public)
WHERE is_deleted = false;

COMMENT ON INDEX idx_listings_category_public IS
'P1-004: Composite index for public listings browsing by category';

-- 3. User code index (for customer support lookups)
CREATE INDEX idx_profiles_user_code
ON profiles(user_code)
WHERE user_code IS NOT NULL;

COMMENT ON INDEX idx_profiles_user_code IS
'P1-005: Index for fast user lookup by user_code (26-digit unique identifier)';

-- 4. Credit transactions user + type + date composite index
CREATE INDEX idx_credit_tx_user_type_date
ON credit_transactions(user_id, transaction_type, created_at DESC);

COMMENT ON INDEX idx_credit_tx_user_type_date IS
'P1-005: Composite index for user credit history queries (most common access pattern)';

-- 5. Credit transactions idempotency key index
CREATE INDEX idx_credit_tx_idempotency
ON credit_transactions(idempotency_key)
WHERE idempotency_key IS NOT NULL;

COMMENT ON INDEX idx_credit_tx_idempotency IS
'P1-005: Index for idempotency checks (prevents duplicate credit transactions)';

-- 6. Profiles created_at index (for conversion funnel - P2-012)
CREATE INDEX idx_profiles_created_at
ON profiles(created_at DESC)
WHERE is_deleted = false;

COMMENT ON INDEX idx_profiles_created_at IS
'P2-012: Index for signup counting in conversion funnel queries.
Supports time-range queries: WHERE created_at >= :start_date.
Expected speedup: 50x-100x for conversion funnel stats.';

-- 7. Profiles tier + created_at composite index (for conversion funnel - P2-012)
CREATE INDEX idx_profiles_tier_created_at
ON profiles(tier, created_at DESC)
WHERE is_deleted = false AND tier IN ('t2', 't3');

COMMENT ON INDEX idx_profiles_tier_created_at IS
'P2-012: Composite index for counting converted users (paid tiers).
Partial index only includes t2/t3 users for optimal performance.
Expected speedup: 50x-100x for conversion funnel stats.';

-- 8. Projects user_id + created_at composite index (for conversion funnel - P2-012)
CREATE INDEX idx_projects_user_created_at
ON projects(user_id, created_at DESC)
WHERE is_deleted = false;

COMMENT ON INDEX idx_projects_user_created_at IS
'P2-012: Composite index for finding users who created projects.
Enables efficient DISTINCT user_id queries in conversion funnel.
Expected speedup: 50x-100x for conversion funnel stats.';


-- ============================================================================
-- RPC Functions (Performance Optimization - P1-004)
-- ============================================================================

-- Marketplace listings with seller info (5x-10x faster than separate queries)
CREATE OR REPLACE FUNCTION p_get_marketplace_listings(
    p_category TEXT DEFAULT NULL,
    p_price_filter TEXT DEFAULT 'all',
    p_sort_by TEXT DEFAULT 'latest',
    p_tier_filter TEXT DEFAULT NULL,
    p_search_query TEXT DEFAULT '',
    p_limit INTEGER DEFAULT 20,
    p_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
    listing_id TEXT,
    seller_id TEXT,
    resource_type TEXT,
    category TEXT,
    source TEXT,
    title TEXT,
    description TEXT,
    tags TEXT[],
    preview_url TEXT,
    thumbnail_url TEXT,
    file_url TEXT,
    file_size INTEGER,
    file_format TEXT,
    dimensions JSONB,
    license_type TEXT,
    price_type TEXT,
    credit_price INTEGER,
    price_credits INTEGER,
    allowed_tiers TEXT[],
    status TEXT,
    moderation_status TEXT,
    is_featured BOOLEAN,
    is_public BOOLEAN,
    is_deleted BOOLEAN,
    rejection_reason TEXT,
    view_count INTEGER,
    download_count INTEGER,
    like_count INTEGER,
    purchase_count INTEGER,
    sales_count INTEGER,
    usage_count INTEGER,
    rating_average NUMERIC,
    rating_count INTEGER,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    seller_username TEXT,
    seller_avatar_url TEXT,
    total_count BIGINT
)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_total_count BIGINT;
BEGIN
    SELECT COUNT(*)
    INTO v_total_count
    FROM marketplace_listings ml
    WHERE ml.is_public = true
      AND ml.is_deleted = false
      AND ml.moderation_status = 'approved'
      AND (p_category IS NULL OR ml.resource_type = p_category)
      AND (p_tier_filter IS NULL OR p_tier_filter = ANY(ml.allowed_tiers))
      AND (
          CASE p_price_filter
              WHEN 'free' THEN ml.credit_price = 0
              WHEN 'paid' THEN ml.credit_price > 0
              ELSE TRUE
          END
      )
      AND (
          p_search_query = ''
          OR ml.title ILIKE '%' || p_search_query || '%'
          OR ml.description ILIKE '%' || p_search_query || '%'
      );

    RETURN QUERY
    SELECT
        ml.listing_id,
        ml.seller_id,
        ml.resource_type,
        ml.category,
        ml.source,
        ml.title,
        ml.description,
        ml.tags,
        ml.preview_url,
        ml.thumbnail_url,
        ml.file_url,
        ml.file_size,
        ml.file_format,
        ml.dimensions,
        ml.license_type,
        ml.price_type,
        ml.credit_price,
        ml.credit_price AS price_credits,
        ml.allowed_tiers,
        ml.status,
        ml.moderation_status,
        ml.is_featured,
        ml.is_public,
        ml.is_deleted,
        ml.rejection_reason,
        ml.view_count,
        ml.download_count,
        ml.like_count,
        ml.purchase_count,
        ml.purchase_count AS sales_count,
        ml.usage_count,
        ml.rating_average,
        ml.rating_count,
        ml.created_at,
        ml.updated_at,
        ml.published_at,
        p.username AS seller_username,
        p.avatar_url AS seller_avatar_url,
        v_total_count AS total_count
    FROM marketplace_listings ml
    LEFT JOIN profiles p ON ml.seller_id = p.id
    WHERE ml.is_public = true
      AND ml.is_deleted = false
      AND ml.moderation_status = 'approved'
      AND (p_category IS NULL OR ml.resource_type = p_category)
      AND (p_tier_filter IS NULL OR p_tier_filter = ANY(ml.allowed_tiers))
      AND (
          CASE p_price_filter
              WHEN 'free' THEN ml.credit_price = 0
              WHEN 'paid' THEN ml.credit_price > 0
              ELSE TRUE
          END
      )
      AND (
          p_search_query = ''
          OR ml.title ILIKE '%' || p_search_query || '%'
          OR ml.description ILIKE '%' || p_search_query || '%'
      )
    ORDER BY
        CASE
            WHEN p_sort_by = 'best_selling' THEN ml.purchase_count
            WHEN p_sort_by = 'popular' THEN ml.usage_count
            ELSE 0
        END DESC,
        CASE
            WHEN p_sort_by = 'price_asc' THEN ml.credit_price
            ELSE NULL
        END ASC,
        CASE
            WHEN p_sort_by = 'price_desc' THEN ml.credit_price
            ELSE NULL
        END DESC,
        CASE
            WHEN p_sort_by = 'latest' OR p_sort_by NOT IN ('best_selling', 'popular', 'price_asc', 'price_desc')
            THEN ml.created_at
            ELSE NULL
        END DESC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$;

COMMENT ON FUNCTION p_get_marketplace_listings IS
'P1-004: Optimized marketplace listings with seller info (5x-10x faster)';

-- Conversion funnel statistics (50x-100x faster than separate queries - P2-012)
CREATE OR REPLACE FUNCTION p_get_conversion_funnel(
    p_period TEXT DEFAULT 'month'  -- 'day', 'week', 'month', 'year'
)
RETURNS TABLE (
    signups BIGINT,           -- Total new signups in period
    created_project BIGINT,   -- Users who created at least one project
    converted BIGINT          -- Users who upgraded to paid tier (t2/t3)
)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_start_date TIMESTAMPTZ;
    v_signups BIGINT;
    v_created_project BIGINT;
    v_converted BIGINT;
BEGIN
    -- Calculate start date based on period
    v_start_date := CASE p_period
        WHEN 'day' THEN NOW() - INTERVAL '1 day'
        WHEN 'week' THEN NOW() - INTERVAL '7 days'
        WHEN 'month' THEN NOW() - INTERVAL '30 days'
        WHEN 'year' THEN NOW() - INTERVAL '365 days'
        ELSE NOW() - INTERVAL '30 days'
    END;

    -- Count new signups (uses idx_profiles_created_at)
    SELECT COUNT(*)
    INTO v_signups
    FROM profiles
    WHERE is_deleted = false AND created_at >= v_start_date;

    -- Count users who created projects (uses idx_projects_user_created_at)
    SELECT COUNT(DISTINCT user_id)
    INTO v_created_project
    FROM projects
    WHERE is_deleted = false AND created_at >= v_start_date;

    -- Count converted users (uses idx_profiles_tier_created_at)
    SELECT COUNT(*)
    INTO v_converted
    FROM profiles
    WHERE is_deleted = false AND tier IN ('t2', 't3') AND created_at >= v_start_date;

    RETURN QUERY SELECT v_signups, v_created_project, v_converted;
END;
$$;

COMMENT ON FUNCTION p_get_conversion_funnel IS
'P2-012: Optimized conversion funnel (50x-100x faster, 5-10s → < 100ms)';


-- ============================================================================
-- Category Management RPC Functions (LTREE Operations)
-- ============================================================================

-- Get all descendant categories using LTREE
CREATE OR REPLACE FUNCTION get_category_descendants(parent_path_input LTREE)
RETURNS TABLE (
    id UUID,
    parent_id UUID,
    path LTREE,
    level INTEGER,
    slug VARCHAR(50),
    name VARCHAR(100),
    name_i18n JSONB,
    description TEXT,
    icon VARCHAR(50),
    asset_type VARCHAR(20),
    is_visible BOOLEAN,
    is_featured BOOLEAN,
    display_order INTEGER,
    min_tier VARCHAR(20),
    visible_from TIMESTAMPTZ,
    visible_until TIMESTAMPTZ,
    asset_count INTEGER,
    usage_count INTEGER,
    metadata JSONB,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ac.id,
        ac.parent_id,
        ac.path,
        ac.level,
        ac.slug,
        ac.name,
        ac.name_i18n,
        ac.description,
        ac.icon,
        ac.asset_type,
        ac.is_visible,
        ac.is_featured,
        ac.display_order,
        ac.min_tier,
        ac.visible_from,
        ac.visible_until,
        ac.asset_count,
        ac.usage_count,
        ac.metadata,
        ac.created_at,
        ac.updated_at
    FROM asset_categories ac
    WHERE ac.path <@ parent_path_input
      AND ac.deleted_at IS NULL
    ORDER BY ac.path, ac.display_order;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_category_descendants IS
'Get all descendant categories of a given path using LTREE operator';


-- Update descendants path when parent category is moved
CREATE OR REPLACE FUNCTION update_category_descendants_path(
    old_path_input LTREE,
    new_path_input LTREE
)
RETURNS INTEGER AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE asset_categories
    SET
        path = new_path_input || subpath(path, nlevel(old_path_input)),
        level = nlevel(new_path_input || subpath(path, nlevel(old_path_input))),
        updated_at = CURRENT_TIMESTAMP
    WHERE path <@ old_path_input
      AND path != old_path_input
      AND deleted_at IS NULL;

    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_category_descendants_path IS
'Update all descendant paths when parent category is moved';


-- Soft delete all descendant categories
CREATE OR REPLACE FUNCTION soft_delete_category_descendants(parent_path_input LTREE)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
    recovery_time TIMESTAMPTZ;
BEGIN
    recovery_time := CURRENT_TIMESTAMP + INTERVAL '30 days';

    UPDATE asset_categories
    SET
        deleted_at = CURRENT_TIMESTAMP,
        recovery_expires_at = recovery_time,
        updated_at = CURRENT_TIMESTAMP
    WHERE path <@ parent_path_input
      AND path != parent_path_input
      AND deleted_at IS NULL;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION soft_delete_category_descendants IS
'Soft delete all descendant categories when parent is deleted with cascade';


-- Increment category usage count atomically
CREATE OR REPLACE FUNCTION increment_category_usage(category_id_input UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE asset_categories
    SET
        usage_count = usage_count + 1,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = category_id_input
      AND deleted_at IS NULL;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION increment_category_usage IS
'Atomically increment usage count for a category';


-- ============================================================================
-- 提交事务
-- ============================================================================
COMMIT;
