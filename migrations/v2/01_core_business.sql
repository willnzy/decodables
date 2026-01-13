-- ============================================================================
-- Make Decodables - 数据库架构 (文件 1/3)
-- ============================================================================
-- 分类: 核心业务
-- 说明: 用户、积分、项目、素材、市场
-- 执行顺序: 第 1 个执行
-- 生成时间: 2026-01-10
-- 更新时间: 2026-01-12 (修复表创建顺序)
-- ============================================================================

-- 开始事务
BEGIN;

-- ============================================================================
-- 启用必要的 PostgreSQL 扩展
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";      -- UUID 生成函数
CREATE EXTENSION IF NOT EXISTS "ltree";          -- 层级树结构支持 (用于 asset_categories)

-- ============================================================================
-- 辅助函数 (需要先创建)
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 表创建顺序 (按依赖关系排列)
-- ============================================================================
-- 第一层: 无外键依赖的基础表
--   1. profiles
--   2. asset_categories
--   3. asset_tags
--
-- 第二层: 依赖第一层的表
--   4. projects (依赖 profiles)
--   5. marketplace_listings (依赖 profiles)
--
-- 第三层: 依赖第一、二层的表
--   6. assets (依赖 profiles, projects, marketplace_listings)
--   7. project_versions (依赖 projects, profiles)
--   ... 其他表


-- ============================================================================
-- 第一层: 基础表 (无外键依赖)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. profiles (用户表 - 最基础的表)
-- ----------------------------------------------------------------------------
CREATE TABLE profiles (
    -- 主键 (Clerk ID，TEXT 类型!)
    id TEXT PRIMARY KEY,

    -- 基础信息
    email TEXT NOT NULL UNIQUE,
    username TEXT,
    display_name TEXT,
    first_name TEXT,  -- P0-1: Repository 使用的字段
    last_name TEXT,   -- P0-1: Repository 使用的字段
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
    credits_reset_at TIMESTAMPTZ,  -- P0-2: 月度积分重置时间

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

    -- Onboarding 状态 (P0-4: Repository 使用的字段)
    onboarding_step TEXT DEFAULT 'not_started' CHECK (onboarding_step IN (
        'not_started', 'welcome', 'profile_setup', 'first_project', 'completed'
    )),

    -- 本地化时间字段
    created_at_local TIMESTAMP,

    -- Cohort 分析
    cohort_month TEXT,

    -- 统计字段 (冗余字段，由触发器维护)
    project_count INTEGER DEFAULT 0 CHECK (project_count >= 0),
    asset_count INTEGER DEFAULT 0 CHECK (asset_count >= 0),

    -- 偏好设置 (P0-3: Repository 使用 preferences，保留 ext_json 作为通用扩展)
    preferences JSONB DEFAULT '{}'::jsonb,
    ext_json JSONB DEFAULT '{}'::jsonb,

    -- 创建来源追踪 (用于监控 Webhook vs JIT 创建)
    created_by TEXT DEFAULT 'legacy' CHECK (created_by IN ('webhook', 'jit', 'legacy', 'manual')),
    
    -- 标准审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    recovery_expires_at TIMESTAMPTZ,

    -- 日期逻辑验证
    CONSTRAINT check_trial_dates CHECK (trial_end_date IS NULL OR trial_start_date IS NULL OR trial_end_date > trial_start_date),
    CONSTRAINT check_subscription_dates CHECK (subscription_current_period_end IS NULL OR subscription_current_period_start IS NULL OR subscription_current_period_end > subscription_current_period_start),

    -- Stripe ID 格式验证
    CONSTRAINT check_stripe_customer_id_format CHECK (stripe_customer_id IS NULL OR stripe_customer_id ~ '^cus_[A-Za-z0-9]+$'),
    CONSTRAINT check_stripe_subscription_id_format CHECK (stripe_subscription_id IS NULL OR stripe_subscription_id ~ '^sub_[A-Za-z0-9]+$'),

    -- user_code 格式验证 (26位数字: YYMMDDHHMMSS+mmmm+UUUUUUU+RRR)
    CONSTRAINT check_user_code_format CHECK (user_code ~ '^[0-9]{26}$'),

    CONSTRAINT chk_profiles_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);


-- ----------------------------------------------------------------------------
-- 2. asset_categories (素材分类 - 自引用)
-- ----------------------------------------------------------------------------
CREATE TABLE asset_categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 层级关系
    parent_id UUID REFERENCES asset_categories(id) ON DELETE SET NULL,
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

    -- 标准审计字段
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ,
    recovery_expires_at TIMESTAMPTZ,

    CONSTRAINT chk_asset_categories_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);


-- ----------------------------------------------------------------------------
-- 3. asset_tags (标签 - 无外键依赖)
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

CREATE TRIGGER update_asset_tags_updated_at
    BEFORE UPDATE ON asset_tags
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ============================================================================
-- 第二层: 依赖 profiles 的表
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 4. projects (项目表)
-- ----------------------------------------------------------------------------
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 用户ID (P0-8: Repository 同时使用 user_id 和 owner_id)
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    -- 项目信息
    title TEXT NOT NULL DEFAULT 'My Magic Story',
    description TEXT,  -- P0-8: Repository 使用的字段
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],  -- P0-8: Repository 使用的字段
    canvas_data JSONB DEFAULT '{}'::jsonb,
    thumbnail_url TEXT,
    canvas_size TEXT DEFAULT '1080x1080',  -- P0-8: Repository 使用的字段

    -- 项目状态 (P0-8: Repository 使用 status 字段)
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'archived', 'deleted')),

    -- 公开与模板设置 (P0-8: Repository 使用的字段)
    is_public BOOLEAN DEFAULT FALSE,
    is_template BOOLEAN DEFAULT FALSE,
    template_category TEXT,

    -- 协作者 (P0-8: Repository 使用的字段)
    collaborators TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- 统计字段 (P0-8: Repository 使用的字段)
    view_count INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,

    -- 下载追踪
    last_downloaded_hash TEXT,
    content_hash TEXT,  -- P0-8: Repository 使用的字段

    -- 市场相关
    marketplace_listing_id UUID,
    source_listing_id UUID,
    is_purchased BOOLEAN DEFAULT FALSE,
    origin_owner_id TEXT REFERENCES profiles(id),
    listing_status TEXT,  -- P0-8: Repository 使用的字段 (如 'published', 'draft')

    -- 永久删除标记 (P0-8: Repository 使用的字段)
    is_permanently_deleted BOOLEAN DEFAULT FALSE,

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
    recovery_expires_at TIMESTAMPTZ,

    CONSTRAINT chk_projects_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);

-- P0-8: 为 Repository 兼容创建 owner_id 作为 user_id 的别名视图
-- 注意: Repository 可能使用 owner_id 或 user_id，此视图确保两者都可用
-- 命名规范: 视图统一使用 v_ 前缀
DROP VIEW IF EXISTS projects_v CASCADE;  -- 删除旧视图名
CREATE OR REPLACE VIEW v_projects AS
SELECT
    *,
    user_id AS owner_id  -- 别名
FROM projects;


-- ----------------------------------------------------------------------------
-- 4.1 project_pages (项目页面 - P0-9: Repository 使用但之前缺失的表)
-- ----------------------------------------------------------------------------
CREATE TABLE project_pages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    page_id TEXT NOT NULL UNIQUE,  -- P0-9: Repository 使用的业务 ID
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- 页面信息
    page_number INTEGER NOT NULL DEFAULT 1,
    canvas_data JSONB DEFAULT '{}'::jsonb,
    thumbnail_url TEXT,

    -- 时间戳
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- 唯一约束: 每个项目的页码不能重复
    UNIQUE(project_id, page_number)
);

CREATE INDEX idx_project_pages_project ON project_pages(project_id, page_number);


-- ----------------------------------------------------------------------------
-- 5. marketplace_listings (市场列表)
-- ----------------------------------------------------------------------------
CREATE TABLE marketplace_listings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    seller_id TEXT REFERENCES profiles(id),

    -- 基本信息
    title TEXT NOT NULL,
    description TEXT,
    thumbnail_url TEXT NOT NULL,
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],  -- P0-10: Repository 使用的字段

    -- 资源信息
    resource_url TEXT NOT NULL,
    resource_type TEXT NOT NULL CHECK (resource_type IN ('project', 'asset', 'template')),
    resource_id UUID,

    -- 文件信息 (P0-10: Repository 使用的字段)
    preview_url TEXT,
    file_url TEXT,
    file_size INTEGER,
    file_format TEXT,
    dimensions TEXT,  -- 如 "1080x1080"

    -- 分类
    category TEXT DEFAULT 'element' CHECK (category IN (
        'clipart', 'illustration', 'photo', 'background',
        'template', 'font', 'sticker', 'icon', 'pattern', 'element',
        'emoji', 'frame', 'character', 'scene',
        'mini_book', 'worksheet', 'flashcard'
    )),
    source TEXT DEFAULT 'user' CHECK (source IN ('system', 'user', 'ai', 'community')),
    license_type TEXT DEFAULT 'standard',  -- P0-10: Repository 使用的字段

    -- 定价 (P0-10: 同时支持 price_credits 和 credit_price)
    price_credits INTEGER NOT NULL DEFAULT 0 CHECK (price_credits >= 0),
    price_type TEXT DEFAULT 'credits' CHECK (price_type IN ('free', 'credits', 'subscription')),  -- P0-10: Repository 使用的字段
    allowed_tiers TEXT[] NOT NULL DEFAULT '{t1, t2, t3}',

    -- 统计 (P0-10: 补充 Repository 使用的统计字段)
    usage_count BIGINT DEFAULT 0,
    sales_count INTEGER DEFAULT 0,
    unique_buyers_count INTEGER DEFAULT 0,
    total_revenue INTEGER DEFAULT 0,
    view_count INTEGER DEFAULT 0,  -- P0-10: Repository 使用的字段
    download_count INTEGER DEFAULT 0,  -- P0-10: Repository 使用的字段
    rating_average NUMERIC(3,2) DEFAULT 0,  -- P0-10: Repository 使用的字段
    rating_count INTEGER DEFAULT 0,  -- P0-10: Repository 使用的字段

    -- 状态 (P0-10: 添加 status 字段供 Repository 使用)
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'pending', 'published', 'unpublished', 'rejected', 'deleted')),
    is_public BOOLEAN DEFAULT FALSE,
    moderation_status TEXT NOT NULL DEFAULT 'draft' CHECK (moderation_status IN ('draft', 'pending', 'approved', 'rejected')),
    moderation_note TEXT,
    moderated_by TEXT REFERENCES profiles(id),
    moderated_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,  -- P0-10: Repository 使用的字段

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
    recovery_expires_at TIMESTAMPTZ,

    -- seller_id 一致性约束
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


-- ============================================================================
-- 第三层: 依赖第一、二层的表
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 6. assets (用户素材)
-- ----------------------------------------------------------------------------
CREATE TABLE assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id),
    url TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('image', 'video', 'audio', 'document')),

    -- P0-11: Repository 使用的字段
    name TEXT,
    category TEXT,  -- 素材分类
    source TEXT DEFAULT 'upload' CHECK (source IN ('upload', 'ai', 'system', 'marketplace')),
    usage_count INTEGER DEFAULT 0,

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
    recovery_expires_at TIMESTAMPTZ,

    CONSTRAINT chk_assets_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);


-- ----------------------------------------------------------------------------
-- 7. asset_tag_relations (素材-标签关联)
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
-- 8. user_recent_assets (用户最近使用素材)
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
-- 9. user_favorite_assets (用户收藏素材)
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
-- 10. project_versions (项目版本)
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
);


-- ----------------------------------------------------------------------------
-- 11. asset_prompt_templates (AI提示词模板)
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
    recovery_expires_at TIMESTAMPTZ,
    CONSTRAINT chk_asset_prompt_templates_deleted_at_consistency
        CHECK ((is_deleted = false AND deleted_at IS NULL) OR (is_deleted = true AND deleted_at IS NOT NULL)),
    CONSTRAINT chk_asset_prompt_templates_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);


-- ----------------------------------------------------------------------------
-- 12. credit_purchases (积分购买记录)
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

    CONSTRAINT check_credit_purchase_idempotency_format CHECK (idempotency_key IS NULL OR length(idempotency_key) >= 16)
);


-- ----------------------------------------------------------------------------
-- 13. credit_transactions (积分交易流水)
-- ----------------------------------------------------------------------------
CREATE TABLE credit_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    -- 交易类型 (P0-6: 同时支持 transaction_type 和 tx_type)
    -- transaction_type: 规范字段名 (用于报表和管理)
    -- tx_type: Repository 使用的字段名 (用于插入)
    -- 至少一个必须有值，两个都有值时必须相同
    transaction_type TEXT CHECK (transaction_type IN (
        'subscription_grant', 'purchase', 'ai_generation', 'smart_scan',
        'refund', 'admin_adjustment', 'signup_bonus', 'referral_bonus',
        'campaign_reward', 'expiration', 'topup_purchase', 'sub_grant',
        'monthly_reset', 'marketplace_purchase'
    )),
    tx_type TEXT CHECK (tx_type IN (
        'subscription_grant', 'purchase', 'ai_generation', 'smart_scan',
        'refund', 'admin_adjustment', 'signup_bonus', 'referral_bonus',
        'campaign_reward', 'expiration', 'topup_purchase', 'sub_grant',
        'monthly_reset', 'marketplace_purchase'
    )),

    bucket TEXT NOT NULL CHECK (bucket IN ('monthly', 'permanent')),
    amount INTEGER NOT NULL,

    balance_monthly_after INTEGER NOT NULL CHECK (balance_monthly_after >= 0),
    balance_permanent_after INTEGER NOT NULL CHECK (balance_permanent_after >= 0),

    idempotency_key TEXT,
    related_entity_type TEXT,
    related_entity_id TEXT,
    description TEXT,

    timezone TEXT DEFAULT 'UTC',
    created_at_local TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- 约束: 至少一个类型字段必须有值
    CONSTRAINT check_type_not_null CHECK (transaction_type IS NOT NULL OR tx_type IS NOT NULL),
    -- 约束: 两个都有值时必须相同
    CONSTRAINT check_type_consistency CHECK (
        transaction_type IS NULL OR tx_type IS NULL OR transaction_type = tx_type
    ),
    CONSTRAINT check_idempotency_key_format CHECK (idempotency_key IS NULL OR length(idempotency_key) >= 16)
);

-- P0-6: 触发器自动同步 transaction_type 和 tx_type
CREATE OR REPLACE FUNCTION sync_credit_transaction_type()
RETURNS TRIGGER AS $$
BEGIN
    -- 如果只有 tx_type，复制到 transaction_type
    IF NEW.transaction_type IS NULL AND NEW.tx_type IS NOT NULL THEN
        NEW.transaction_type := NEW.tx_type;
    -- 如果只有 transaction_type，复制到 tx_type
    ELSIF NEW.tx_type IS NULL AND NEW.transaction_type IS NOT NULL THEN
        NEW.tx_type := NEW.transaction_type;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_sync_credit_transaction_type
    BEFORE INSERT OR UPDATE ON credit_transactions
    FOR EACH ROW
    EXECUTE FUNCTION sync_credit_transaction_type();


-- ----------------------------------------------------------------------------
-- 14. generation_tasks (AI生成任务)
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
-- 15. listing_usages (市场使用记录)
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
-- 16. marketplace_favorites (市场收藏)
-- ----------------------------------------------------------------------------
CREATE TABLE marketplace_favorites (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    listing_id UUID NOT NULL REFERENCES marketplace_listings(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMPTZ,
    recovery_expires_at TIMESTAMPTZ,
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
-- 17. marketplace_purchases (市场购买记录)
-- ----------------------------------------------------------------------------
CREATE TABLE marketplace_purchases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    listing_id UUID NOT NULL REFERENCES marketplace_listings(id) ON DELETE CASCADE,

    price_paid INTEGER NOT NULL,
    idempotency_key TEXT,

    snapshot_title TEXT,
    snapshot_thumbnail_url TEXT,
    snapshot_description TEXT,
    snapshot_version TEXT,
    snapshot_resource_type TEXT,
    snapshot_resource_id UUID,

    utm_source TEXT,
    utm_medium TEXT,
    utm_campaign TEXT,
    referral_context TEXT,

    timezone TEXT DEFAULT 'UTC',
    purchased_at_local TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb,
    purchased_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, listing_id),
    CONSTRAINT check_purchase_idempotency_format CHECK (idempotency_key IS NULL OR length(idempotency_key) >= 16)
);


-- ----------------------------------------------------------------------------
-- 18. marketplace_reports (市场举报)
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
-- 19. marketplace_reviews (市场评价)
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
    recovery_expires_at TIMESTAMPTZ,
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
-- 20. page_prompt_templates (页面提示词模板)
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
-- 21. subscription_history (订阅历史)
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
-- 22. system_assets (系统素材)
-- ----------------------------------------------------------------------------
CREATE TABLE system_assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category_id UUID NOT NULL REFERENCES asset_categories(id),

    name VARCHAR(200) NOT NULL,
    slug VARCHAR(100),
    description TEXT,

    asset_type VARCHAR(20) NOT NULL CHECK (asset_type IN ('text', 'image', 'shape', 'table', 'sticker', 'icon', 'frame')),

    source VARCHAR(20) NOT NULL DEFAULT 'system' CHECK (source IN ('system', 'user', 'ai', 'community')),
    source_user_id TEXT REFERENCES profiles(id),

    file_url TEXT,
    thumbnail_url TEXT,
    file_size INTEGER,
    file_format VARCHAR(20),

    width INTEGER,
    height INTEGER,

    content JSONB NOT NULL DEFAULT '{}',

    min_tier VARCHAR(20) DEFAULT 't1' CHECK (min_tier IN ('t1', 't2', 't3')),
    is_pro_only BOOLEAN DEFAULT FALSE,

    tags TEXT[] DEFAULT ARRAY[]::TEXT[],

    is_visible BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,
    display_order INTEGER DEFAULT 0,

    usage_count INTEGER DEFAULT 0,
    download_count INTEGER DEFAULT 0,
    favorite_count INTEGER DEFAULT 0,

    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ,
    recovery_expires_at TIMESTAMPTZ,

    CONSTRAINT chk_system_assets_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);


-- ----------------------------------------------------------------------------
-- 23. system_resources (系统资源表)
-- ----------------------------------------------------------------------------
CREATE TABLE system_resources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    resource_type TEXT NOT NULL CHECK (resource_type IN (
        'text', 'image', 'shape', 'table', 'sticker',
        'icon', 'frame', 'background', 'font', 'pattern'
    )),

    category_id UUID REFERENCES asset_categories(id) ON DELETE SET NULL,
    category TEXT,

    url TEXT NOT NULL,
    thumbnail_url TEXT,

    name TEXT,
    description TEXT,
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    metadata JSONB DEFAULT '{}',

    file_size INTEGER,
    width INTEGER,
    height INTEGER,
    format TEXT,

    allowed_tiers TEXT[] DEFAULT ARRAY['t1']::TEXT[],
    min_tier TEXT DEFAULT 't1' CHECK (min_tier IN ('t1', 't2', 't3')),

    is_active BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,
    display_order INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    updated_by TEXT,

    deleted_at TIMESTAMPTZ,
    recovery_expires_at TIMESTAMPTZ,

    CONSTRAINT chk_system_resources_recovery_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);

COMMENT ON TABLE system_resources IS '系统资源表: stickers, templates, fonts等系统素材';

CREATE INDEX idx_sr_type ON system_resources(resource_type) WHERE deleted_at IS NULL;
CREATE INDEX idx_sr_category ON system_resources(category_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_sr_active_type ON system_resources(is_active, resource_type) WHERE deleted_at IS NULL AND is_active = true;
CREATE INDEX idx_sr_tier ON system_resources(min_tier) WHERE deleted_at IS NULL;
CREATE INDEX idx_sr_tags ON system_resources USING GIN(tags) WHERE deleted_at IS NULL;
CREATE INDEX idx_sr_created ON system_resources(created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX idx_sr_featured ON system_resources(is_featured, display_order) WHERE deleted_at IS NULL AND is_featured = true;

CREATE TRIGGER update_system_resources_updated_at
    BEFORE UPDATE ON system_resources
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ----------------------------------------------------------------------------
-- 24. user_discounts (用户折扣)
-- ----------------------------------------------------------------------------
CREATE TABLE user_discounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    discount_percent INTEGER NOT NULL CHECK (discount_percent BETWEEN 1 AND 100),

    -- 有效期 (同时支持 valid_from/valid_until 和 expires_at 两种风格)
    valid_from TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    valid_until TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,  -- P0-5: Repository 使用的字段 (等价于 valid_until)

    -- 目标计划 (支持 t2/t3 和 starter/pro 两种格式)
    target_plan TEXT CHECK (target_plan IN ('starter', 'pro', 't2', 't3')),

    -- 使用状态 (P0-5: Repository 使用的字段)
    is_used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT check_discount_dates CHECK (valid_until IS NULL OR valid_until > valid_from),
    CONSTRAINT check_expires_at CHECK (expires_at IS NULL OR expires_at > valid_from),
    CONSTRAINT check_used_at CHECK (used_at IS NULL OR is_used = TRUE)
);


-- ----------------------------------------------------------------------------
-- 25. user_generations (用户生成记录)
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
-- Performance Indexes
-- ============================================================================

CREATE INDEX idx_listings_moderation_status
ON marketplace_listings(moderation_status)
WHERE is_deleted = false;

CREATE INDEX idx_listings_category_public
ON marketplace_listings(category, is_public)
WHERE is_deleted = false;

CREATE INDEX idx_profiles_user_code
ON profiles(user_code)
WHERE user_code IS NOT NULL;

CREATE INDEX idx_credit_tx_user_type_date
ON credit_transactions(user_id, transaction_type, created_at DESC);

CREATE INDEX idx_credit_tx_idempotency
ON credit_transactions(idempotency_key)
WHERE idempotency_key IS NOT NULL;

CREATE INDEX idx_profiles_created_at
ON profiles(created_at DESC)
WHERE is_deleted = false;

CREATE INDEX idx_profiles_tier_created_at
ON profiles(tier, created_at DESC)
WHERE is_deleted = false AND tier IN ('t2', 't3');

CREATE INDEX idx_projects_user_created_at
ON projects(user_id, created_at DESC)
WHERE is_deleted = false;


-- ============================================================================
-- RPC Functions
-- ============================================================================

-- Marketplace listings with seller info
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
    listing_id UUID,
    seller_id TEXT,
    resource_type TEXT,
    category TEXT,
    source TEXT,
    title TEXT,
    description TEXT,
    thumbnail_url TEXT,
    price_credits INTEGER,
    allowed_tiers TEXT[],
    moderation_status TEXT,
    is_featured BOOLEAN,
    is_public BOOLEAN,
    is_deleted BOOLEAN,
    usage_count BIGINT,
    sales_count INTEGER,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
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
      AND (p_category IS NULL OR ml.category = p_category)
      AND (p_tier_filter IS NULL OR p_tier_filter = ANY(ml.allowed_tiers))
      AND (
          CASE p_price_filter
              WHEN 'free' THEN ml.price_credits = 0
              WHEN 'paid' THEN ml.price_credits > 0
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
        ml.id AS listing_id,
        ml.seller_id,
        ml.resource_type,
        ml.category,
        ml.source,
        ml.title,
        ml.description,
        ml.thumbnail_url,
        ml.price_credits,
        ml.allowed_tiers,
        ml.moderation_status,
        ml.is_featured,
        ml.is_public,
        ml.is_deleted,
        ml.usage_count,
        ml.sales_count,
        ml.created_at,
        ml.updated_at,
        p.username AS seller_username,
        p.avatar_url AS seller_avatar_url,
        v_total_count AS total_count
    FROM marketplace_listings ml
    LEFT JOIN profiles p ON ml.seller_id = p.id
    WHERE ml.is_public = true
      AND ml.is_deleted = false
      AND ml.moderation_status = 'approved'
      AND (p_category IS NULL OR ml.category = p_category)
      AND (p_tier_filter IS NULL OR p_tier_filter = ANY(ml.allowed_tiers))
      AND (
          CASE p_price_filter
              WHEN 'free' THEN ml.price_credits = 0
              WHEN 'paid' THEN ml.price_credits > 0
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
            WHEN p_sort_by = 'best_selling' THEN ml.sales_count
            WHEN p_sort_by = 'popular' THEN ml.usage_count::INTEGER
            ELSE 0
        END DESC,
        CASE
            WHEN p_sort_by = 'price_asc' THEN ml.price_credits
            ELSE NULL
        END ASC,
        CASE
            WHEN p_sort_by = 'price_desc' THEN ml.price_credits
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


-- Conversion funnel statistics
CREATE OR REPLACE FUNCTION p_get_conversion_funnel(
    p_period TEXT DEFAULT 'month'
)
RETURNS TABLE (
    signups BIGINT,
    created_project BIGINT,
    converted BIGINT
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
    v_start_date := CASE p_period
        WHEN 'day' THEN NOW() - INTERVAL '1 day'
        WHEN 'week' THEN NOW() - INTERVAL '7 days'
        WHEN 'month' THEN NOW() - INTERVAL '30 days'
        WHEN 'year' THEN NOW() - INTERVAL '365 days'
        ELSE NOW() - INTERVAL '30 days'
    END;

    SELECT COUNT(*) INTO v_signups
    FROM profiles WHERE is_deleted = false AND created_at >= v_start_date;

    SELECT COUNT(DISTINCT user_id) INTO v_created_project
    FROM projects WHERE is_deleted = false AND created_at >= v_start_date;

    SELECT COUNT(*) INTO v_converted
    FROM profiles WHERE is_deleted = false AND tier IN ('t2', 't3') AND created_at >= v_start_date;

    RETURN QUERY SELECT v_signups, v_created_project, v_converted;
END;
$$;


-- Category descendants (LTREE)
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
        ac.id, ac.parent_id, ac.path, ac.level, ac.slug, ac.name, ac.name_i18n,
        ac.description, ac.icon, ac.asset_type, ac.is_visible, ac.is_featured,
        ac.display_order, ac.min_tier, ac.visible_from, ac.visible_until,
        ac.asset_count, ac.usage_count, ac.metadata, ac.created_at, ac.updated_at
    FROM asset_categories ac
    WHERE ac.path <@ parent_path_input AND ac.deleted_at IS NULL
    ORDER BY ac.path, ac.display_order;
END;
$$ LANGUAGE plpgsql;


-- Update category descendants path
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
    WHERE path <@ old_path_input AND path != old_path_input AND deleted_at IS NULL;

    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count;
END;
$$ LANGUAGE plpgsql;


-- Soft delete category descendants
CREATE OR REPLACE FUNCTION soft_delete_category_descendants(parent_path_input LTREE)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    UPDATE asset_categories
    SET
        deleted_at = CURRENT_TIMESTAMP,
        recovery_expires_at = CURRENT_TIMESTAMP + INTERVAL '30 days',
        updated_at = CURRENT_TIMESTAMP
    WHERE path <@ parent_path_input AND path != parent_path_input AND deleted_at IS NULL;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;


-- Increment category usage
CREATE OR REPLACE FUNCTION increment_category_usage(category_id_input UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE asset_categories
    SET usage_count = usage_count + 1, updated_at = CURRENT_TIMESTAMP
    WHERE id = category_id_input AND deleted_at IS NULL;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- User Creation Monitoring (幂等用户创建监控)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- user_creation_logs - 用户创建日志表
-- ----------------------------------------------------------------------------
CREATE TABLE user_creation_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('webhook', 'jit', 'manual')),
    action TEXT NOT NULL CHECK (action IN ('created', 'duplicate_attempt', 'error')),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_user_creation_logs_user_id ON user_creation_logs(user_id);
CREATE INDEX idx_user_creation_logs_created_at ON user_creation_logs(created_at DESC);
CREATE INDEX idx_user_creation_logs_source ON user_creation_logs(source);
CREATE INDEX idx_user_creation_logs_action ON user_creation_logs(action);

COMMENT ON TABLE user_creation_logs IS '用户创建日志表，用于监控 Webhook vs JIT 创建健康度';
COMMENT ON COLUMN user_creation_logs.source IS '创建源：webhook（Clerk webhook）、jit（API JIT 创建）、manual（手动）';
COMMENT ON COLUMN user_creation_logs.action IS '操作类型：created（成功创建）、duplicate_attempt（重复尝试）、error（错误）';

-- ----------------------------------------------------------------------------
-- profiles 索引增强
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_profiles_created_by ON profiles(created_by);
CREATE INDEX IF NOT EXISTS idx_profiles_username ON profiles(username) WHERE username IS NOT NULL;


-- ============================================================================
-- Helper Sequences and Functions
-- ============================================================================

-- ----------------------------------------------------------------------------
-- user_code_seq - 用户码序列（避免并发冲突）
-- ----------------------------------------------------------------------------
CREATE SEQUENCE IF NOT EXISTS user_code_seq START 1;

COMMENT ON SEQUENCE user_code_seq IS '用户码序列，用于生成唯一的 user_code（原子递增，避免并发冲突）';


-- ----------------------------------------------------------------------------
-- generate_user_code - 生成唯一的 26 位用户码
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION generate_user_code()
RETURNS TEXT AS $$
DECLARE
    new_user_code TEXT;
    current_timestamp_str TEXT;
    sequence_number BIGINT;
BEGIN
    -- 时间戳 (YYMMDDHHMMSS) - 12 位
    current_timestamp_str := TO_CHAR(NOW(), 'YYMMDDHH24MISS');
    
    -- ✅ 使用序列（原子递增，无并发冲突）- 10 位
    sequence_number := nextval('user_code_seq');
    
    -- 组合成 26 位用户码
    -- 格式: [时间12位][序列10位][随机4位]
    new_user_code := 
        current_timestamp_str ||                           -- 12 位: 时间戳
        LPAD(sequence_number::TEXT, 10, '0') ||           -- 10 位: 序列号
        LPAD(FLOOR(RANDOM() * 10000)::TEXT, 4, '0');      --  4 位: 随机数
    
    RETURN new_user_code;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION generate_user_code() IS 
'生成 26 位唯一用户码（HOTFIX: 使用序列避免并发冲突）
格式: YYMMDDHHMMSS(12位) + 序列号(10位) + 随机数(4位)';


-- ----------------------------------------------------------------------------
-- system_error_logs - 系统错误日志表（RPC 函数专用）
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS system_error_logs (
    id BIGSERIAL PRIMARY KEY,
    operation TEXT NOT NULL,
    error_message TEXT NOT NULL,
    details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_system_error_logs_created_at ON system_error_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_error_logs_operation ON system_error_logs(operation);

COMMENT ON TABLE system_error_logs IS '系统错误日志表（用于追踪 RPC 函数异常和数据库层错误）';
COMMENT ON COLUMN system_error_logs.operation IS '操作名称（如 create_user_idempotent）';
COMMENT ON COLUMN system_error_logs.error_message IS '错误信息（SQLERRM）';
COMMENT ON COLUMN system_error_logs.details IS '详细信息（JSONB 格式，包含 user_id、参数等）';


-- ============================================================================
-- RPC Functions - 幂等用户创建
-- ============================================================================

-- ----------------------------------------------------------------------------
-- create_user_idempotent - 幂等的用户创建函数（HOTFIX: 使用 UPSERT）
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION create_user_idempotent(
    p_user_id TEXT,
    p_email TEXT,
    p_source TEXT,  -- 'webhook' or 'jit'
    
    -- Optional fields
    p_username TEXT DEFAULT NULL,
    p_first_name TEXT DEFAULT NULL,
    p_last_name TEXT DEFAULT NULL,
    p_avatar_url TEXT DEFAULT NULL,
    p_display_name TEXT DEFAULT NULL
)
RETURNS TABLE(
    user_profile JSONB,
    was_created BOOLEAN,
    created_by TEXT
) 
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_existing_profile profiles%ROWTYPE;
    v_new_user_code TEXT;
    v_was_created BOOLEAN;
    v_display_name_final TEXT;
BEGIN
    -- ✅ HOTFIX: 使用 UPSERT 模式（原子操作，无 race condition）
    
    -- Step 1: 准备数据
    v_new_user_code := generate_user_code();
    
    v_display_name_final := COALESCE(
        p_display_name,
        p_username,
        p_first_name,
        split_part(p_email, '@', 1)
    );
    
    -- Step 2: 原子插入（如果已存在则忽略）
    INSERT INTO profiles (
        id,
        email,
        user_code,
        username,
        first_name,
        last_name,
        avatar_url,
        display_name,
        tier,
        credits_permanent,
        created_by,
        created_at,
        updated_at
    ) VALUES (
        p_user_id,
        p_email,
        v_new_user_code,
        p_username,
        p_first_name,
        p_last_name,
        p_avatar_url,
        v_display_name_final,
        't1',
        50,  -- 注册奖励（仅在创建时发放一次）
        p_source,
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP
    )
    ON CONFLICT (id) DO NOTHING  -- ✅ 如果已存在，不做任何操作
    RETURNING * INTO v_existing_profile;
    
    -- Step 3: 判断是新创建还是已存在
    IF v_existing_profile.id IS NOT NULL THEN
        -- ✅ 新创建成功
        v_was_created := TRUE;
        
        -- 记录创建事件
        INSERT INTO user_creation_logs (
            user_id,
            source,
            action,
            metadata,
            created_at
        ) VALUES (
            p_user_id,
            p_source,
            'created',
            jsonb_build_object(
                'email', p_email,
                'username', p_username,
                'has_avatar', (p_avatar_url IS NOT NULL)
            ),
            CURRENT_TIMESTAMP
        );
        
        -- 返回新创建的用户
        RETURN QUERY
        SELECT 
            row_to_json(v_existing_profile)::jsonb,
            v_was_created,
            p_source;
        RETURN;
    ELSE
        -- ✅ 用户已存在（被其他进程创建）
        v_was_created := FALSE;
        
        -- 读取现有用户
        SELECT * INTO v_existing_profile
        FROM profiles
        WHERE id = p_user_id;
        
        -- 记录重复创建尝试
        INSERT INTO user_creation_logs (
            user_id,
            source,
            action,
            metadata,
            created_at
        ) VALUES (
            p_user_id,
            p_source,
            'duplicate_attempt',
            jsonb_build_object(
                'existing_created_by', v_existing_profile.created_by,
                'existing_created_at', v_existing_profile.created_at,
                'attempted_with_email', p_email
            ),
            CURRENT_TIMESTAMP
        );
        
        -- 返回现有用户
        RETURN QUERY
        SELECT 
            row_to_json(v_existing_profile)::jsonb,
            v_was_created,
            v_existing_profile.created_by;
        RETURN;
    END IF;
    
EXCEPTION
    WHEN OTHERS THEN
        -- 记录错误（但不影响事务回滚）
        BEGIN
            INSERT INTO system_error_logs (
                operation,
                error_message,
                details,
                created_at
            ) VALUES (
                'create_user_idempotent',
                SQLERRM,
                jsonb_build_object(
                    'user_id', p_user_id,
                    'source', p_source,
                    'email', p_email
                ),
                CURRENT_TIMESTAMP
            );
        EXCEPTION
            WHEN OTHERS THEN
                -- 即使记录错误失败也不影响主流程
                NULL;
        END;
        
        -- 重新抛出原始异常
        RAISE;
END;
$$;

COMMENT ON FUNCTION create_user_idempotent IS '幂等的用户创建函数，支持 Webhook 和 JIT 并发创建而无 race condition';


-- ----------------------------------------------------------------------------
-- get_user_creation_stats - 获取用户创建统计
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_user_creation_stats(p_days INTEGER DEFAULT 7)
RETURNS TABLE(
    total_users BIGINT,
    webhook_created BIGINT,
    jit_created BIGINT,
    webhook_success_rate NUMERIC,
    jit_fallback_rate NUMERIC,
    avg_creation_duration_ms NUMERIC,
    duplicate_attempts BIGINT,
    errors BIGINT
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH recent_users AS (
        SELECT 
            id,
            created_by,
            created_at
        FROM profiles
        WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '1 day' * p_days
    ),
    creation_events AS (
        -- ✅ HOTFIX: 使用 DISTINCT ON 避免重复计数
        SELECT DISTINCT ON (user_id)
            user_id,
            source,
            action,
            created_at
        FROM user_creation_logs
        WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '1 day' * p_days
          AND action = 'created'
        ORDER BY user_id, created_at ASC
    ),
    stats AS (
        SELECT
            COUNT(DISTINCT ru.id) AS total_users,
            COUNT(DISTINCT CASE WHEN ru.created_by = 'webhook' THEN ru.id END) AS webhook_created,
            COUNT(DISTINCT CASE WHEN ru.created_by = 'jit' THEN ru.id END) AS jit_created,
            (
                SELECT COUNT(*) 
                FROM user_creation_logs 
                WHERE action = 'duplicate_attempt'
                  AND created_at >= CURRENT_TIMESTAMP - INTERVAL '1 day' * p_days
            ) AS duplicate_attempts,
            (
                SELECT COUNT(*) 
                FROM user_creation_logs 
                WHERE action = 'error'
                  AND created_at >= CURRENT_TIMESTAMP - INTERVAL '1 day' * p_days
            ) AS errors
        FROM recent_users ru
        LEFT JOIN creation_events ce ON ru.id = ce.user_id
    )
    SELECT
        s.total_users,
        s.webhook_created,
        s.jit_created,
        -- ✅ HOTFIX: 使用 COALESCE 和 NULLIF 避免除以 0
        ROUND(
            COALESCE(
                s.webhook_created::NUMERIC / NULLIF(s.total_users, 0) * 100,
                0
            ), 
            2
        ) AS webhook_success_rate,
        ROUND(
            COALESCE(
                s.jit_created::NUMERIC / NULLIF(s.total_users, 0) * 100,
                0
            ), 
            2
        ) AS jit_fallback_rate,
        0.0 AS avg_creation_duration_ms,
        s.duplicate_attempts,
        s.errors
    FROM stats s;
END;
$$;

COMMENT ON FUNCTION get_user_creation_stats IS '获取用户创建统计数据，用于监控 Webhook 健康度';


-- ----------------------------------------------------------------------------
-- cleanup_old_user_creation_logs - 清理旧日志
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION cleanup_old_user_creation_logs(p_retention_days INTEGER DEFAULT 90)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_deleted_count INTEGER;
BEGIN
    DELETE FROM user_creation_logs
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '1 day' * p_retention_days;
    
    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;
    
    RETURN v_deleted_count;
END;
$$;

COMMENT ON FUNCTION cleanup_old_user_creation_logs IS '清理旧的用户创建日志，默认保留 90 天';


-- ============================================================================
-- Views - 用户创建监控视图
-- ============================================================================

-- ----------------------------------------------------------------------------
-- v_user_creation_events - 用户创建事件视图
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_user_creation_events AS
SELECT 
    p.id AS user_id,
    p.email,
    p.username,
    p.created_by AS created_by_source,
    p.created_at AS user_created_at,
    ucl.source AS log_source,
    ucl.action AS log_action,
    ucl.metadata AS log_metadata,
    ucl.created_at AS log_created_at,
    EXTRACT(EPOCH FROM (ucl.created_at - p.created_at)) AS delay_seconds
FROM profiles p
LEFT JOIN user_creation_logs ucl ON p.id = ucl.user_id
WHERE ucl.action IN ('created', 'duplicate_attempt')
ORDER BY p.created_at DESC;

COMMENT ON VIEW v_user_creation_events IS '用户创建事件视图，包含延迟分析';


-- ============================================================================
-- 提交事务
-- ============================================================================
COMMIT;
