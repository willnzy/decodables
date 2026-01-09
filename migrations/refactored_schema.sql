-- ============================================================================
-- Make Decodables - Refactored Database Schema (v4.0)
-- ============================================================================
-- 生成时间: 2026-01-09
-- PostgreSQL版本: 15+
-- 基于版本: v3.24
--
-- 重构目标:
-- 1. 统一命名规范 (Snake Case)
-- 2. 标准化审计字段 (created_at, updated_at, is_deleted, deleted_at)
-- 3. 性能优化 (冗余字段 + 触发器维护)
-- 4. 完整的COMMENT注释 (带@Ref标注)
-- 5. 保留所有核心业务规则
--
-- 重要提示:
-- ⚠️ profiles.id 是 TEXT 类型 (Clerk ID: user_2xxx...)，不是 UUID！
-- ⚠️ credit_transactions 是 Append-Only 表，禁止 UPDATE/DELETE
-- ⚠️ 积分扣除顺序: credits_monthly → credits_permanent (先月度后永久)
-- ⚠️ 所有金额字段使用 DECIMAL(10,2) 类型
--
-- 参考文档:
-- - decodables/migrations/design_reasoning.md
-- - decodables/migrations/mapping_and_changes.md
-- ============================================================================

-- ============================================================================
-- 第一部分: 扩展 & 函数
-- ============================================================================

-- 启用 UUID 扩展 (用于其他表的自动生成ID)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 启用 pg_trgm 扩展 (用于模糊搜索)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

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
    IF NEW.is_deleted = TRUE AND OLD.is_deleted = FALSE THEN
        NEW.deleted_at = CURRENT_TIMESTAMP;
    ELSIF NEW.is_deleted = FALSE THEN
        NEW.deleted_at = NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION set_deleted_at_on_soft_delete() IS '触发器函数: 软删除时自动设置 deleted_at 时间戳';

-- ============================================================================
-- 第二部分: 核心业务表
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. profiles (用户档案表)
-- 最重要的表，存储用户基础信息、积分余额、等级等
-- ----------------------------------------------------------------------------
CREATE TABLE profiles (
    -- 主键 (Clerk ID，TEXT 类型!)
    id TEXT PRIMARY KEY,

    -- 基础信息
    email TEXT NOT NULL UNIQUE,
    username TEXT,
    display_name TEXT,
    avatar_url TEXT,

    -- 用户唯一码 (用于客服查询和用户反馈，格式: 260109143X7Y)
    user_code TEXT NOT NULL UNIQUE,

    -- 用户等级 (free/starter/pro，硬编码不可改)
    tier TEXT NOT NULL DEFAULT 'free' CHECK (tier IN ('free', 'starter', 'pro')),
    tier_changed_at TIMESTAMPTZ,

    -- 积分余额 (核心字段!)
    credits_monthly INTEGER NOT NULL DEFAULT 0 CHECK (credits_monthly >= 0),
    credits_permanent INTEGER NOT NULL DEFAULT 0 CHECK (credits_permanent >= 0),

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

    -- 本地化时间字段 (v3.9 新增)
    created_at_local TIMESTAMP,

    -- 统计字段 (冗余字段，由触发器维护)
    project_count INTEGER DEFAULT 0 CHECK (project_count >= 0),
    asset_count INTEGER DEFAULT 0 CHECK (asset_count >= 0),

    -- 扩展字段
    ext_json JSONB DEFAULT '{}'::jsonb,

    -- 标准审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ
);

COMMENT ON TABLE profiles IS '用户档案表: 存储用户基础信息、积分余额、订阅状态等核心数据';
COMMENT ON COLUMN profiles.id IS 'Clerk 用户ID (TEXT类型!), 格式: user_2NNEqL2n...';
COMMENT ON COLUMN profiles.user_code IS '用户唯一码, 用于客服查询, 格式: {YYMMDD}{HHMM}{随机3位}, 如: 260109143X7Y';
COMMENT ON COLUMN profiles.tier IS '用户等级: free/starter/pro (硬编码，不可改)';
COMMENT ON COLUMN profiles.credits_monthly IS '月度积分余额 (订阅每月刷新)';
COMMENT ON COLUMN profiles.credits_permanent IS '永久积分余额 (购买的积分包)';
COMMENT ON COLUMN profiles.project_count IS '项目数量 (冗余字段，由 projects 表触发器维护)';
COMMENT ON COLUMN profiles.asset_count IS '素材数量 (冗余字段，由 marketplace_listings 表触发器维护)';
COMMENT ON COLUMN profiles.created_at_local IS '注册时间-本地时区 (v3.9) @Ref: 原字段无';

-- 索引
CREATE INDEX idx_profiles_email ON profiles(email);
CREATE INDEX idx_profiles_user_code ON profiles(user_code);
CREATE INDEX idx_profiles_stripe_customer_id ON profiles(stripe_customer_id) WHERE stripe_customer_id IS NOT NULL;
CREATE INDEX idx_profiles_tier ON profiles(tier);
CREATE INDEX idx_profiles_created_at ON profiles(created_at);
CREATE INDEX idx_profiles_active ON profiles(is_deleted) WHERE is_deleted = FALSE;

-- GIN 索引 (用于 ext_json 查询)
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
-- 2. credit_transactions (积分交易记录表)
-- Append-Only 表，记录所有积分变动，禁止修改和删除
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

    -- 积分变动 (正数=增加，负数=扣除)
    credits_monthly_delta INTEGER NOT NULL DEFAULT 0,
    credits_permanent_delta INTEGER NOT NULL DEFAULT 0,

    -- 交易后余额快照
    credits_monthly_after INTEGER NOT NULL CHECK (credits_monthly_after >= 0),
    credits_permanent_after INTEGER NOT NULL CHECK (credits_permanent_after >= 0),

    -- 幂等性键 (防重复扣费)
    idempotency_key TEXT UNIQUE,

    -- 关联信息
    related_entity_type TEXT,  -- 关联实体类型 (project/listing/generation)
    related_entity_id TEXT,    -- 关联实体ID

    -- 描述信息
    description TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,

    -- 时区字段 (v3.9)
    timezone TEXT DEFAULT 'UTC',
    created_at_local TIMESTAMP,

    -- 标准审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP

    -- 注意: 此表没有 is_deleted/deleted_at 字段 (Append-Only)
);

COMMENT ON TABLE credit_transactions IS '积分交易记录表: Append-Only 设计，禁止 UPDATE/DELETE，记录所有积分变动';
COMMENT ON COLUMN credit_transactions.transaction_type IS '交易类型: subscription_grant/purchase/ai_generation 等';
COMMENT ON COLUMN credit_transactions.credits_monthly_delta IS '月度积分变动量 (正=增加，负=扣除)';
COMMENT ON COLUMN credit_transactions.credits_permanent_delta IS '永久积分变动量 (正=增加，负=扣除)';
COMMENT ON COLUMN credit_transactions.idempotency_key IS '幂等性键: 防止重复扣费，格式: {user_id}:{type}:{timestamp}:{random}';

-- 索引
CREATE INDEX idx_credit_transactions_user_id ON credit_transactions(user_id);
CREATE INDEX idx_credit_transactions_type ON credit_transactions(transaction_type);
CREATE INDEX idx_credit_transactions_created_at ON credit_transactions(created_at);
CREATE INDEX idx_credit_transactions_idempotency ON credit_transactions(idempotency_key) WHERE idempotency_key IS NOT NULL;

-- 复合索引 (用户维度查询)
CREATE INDEX idx_credit_transactions_user_time ON credit_transactions(user_id, created_at DESC);

-- GIN 索引
CREATE INDEX idx_credit_transactions_metadata ON credit_transactions USING GIN(metadata);

-- Append-Only 保护触发器
CREATE OR REPLACE FUNCTION prevent_credit_transaction_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'credit_transactions 表是 Append-Only 表，禁止 UPDATE 操作';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prevent_credit_transaction_update
    BEFORE UPDATE ON credit_transactions
    FOR EACH ROW
    EXECUTE FUNCTION prevent_credit_transaction_modification();

CREATE OR REPLACE FUNCTION prevent_credit_transaction_deletion()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'credit_transactions 表是 Append-Only 表，禁止 DELETE 操作';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prevent_credit_transaction_delete
    BEFORE DELETE ON credit_transactions
    FOR EACH ROW
    EXECUTE FUNCTION prevent_credit_transaction_deletion();

-- 触发器 (仅 updated_at)
CREATE TRIGGER trg_credit_transactions_updated_at
    BEFORE UPDATE ON credit_transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 第三部分: 项目管理表
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 3. projects (项目表)
-- 用户创建的设计项目
-- ----------------------------------------------------------------------------
CREATE TABLE projects (
    -- 主键
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 用户ID (外键)
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    -- 基础信息
    title TEXT NOT NULL,
    description TEXT,

    -- 画布数据 (核心字段)
    canvas_data JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- 缩略图
    thumbnail_url TEXT,

    -- 尺寸信息 (像素)
    canvas_width INTEGER NOT NULL DEFAULT 800 CHECK (canvas_width > 0),
    canvas_height INTEGER NOT NULL DEFAULT 600 CHECK (canvas_height > 0),

    -- 模板/市场相关
    is_template BOOLEAN DEFAULT FALSE,
    template_category TEXT,
    is_published_to_marketplace BOOLEAN DEFAULT FALSE,
    marketplace_listing_id UUID,

    -- 统计字段
    view_count INTEGER DEFAULT 0 CHECK (view_count >= 0),
    clone_count INTEGER DEFAULT 0 CHECK (clone_count >= 0),

    -- 扩展字段
    ext_json JSONB DEFAULT '{}'::jsonb,

    -- 标准审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ
);

COMMENT ON TABLE projects IS '项目表: 用户创建的设计项目，包含画布数据和元数据';
COMMENT ON COLUMN projects.canvas_data IS '画布数据 (JSONB): Fabric.js 序列化的完整画布状态';
COMMENT ON COLUMN projects.is_published_to_marketplace IS '是否已发布到市场 @Ref: 原 isPublishedToMarketplace (camelCase)';

-- 索引
CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_projects_created_at ON projects(created_at DESC);
CREATE INDEX idx_projects_is_template ON projects(is_template) WHERE is_template = TRUE;
CREATE INDEX idx_projects_marketplace ON projects(is_published_to_marketplace) WHERE is_published_to_marketplace = TRUE;
CREATE INDEX idx_projects_active ON projects(is_deleted) WHERE is_deleted = FALSE;

-- 复合索引
CREATE INDEX idx_projects_user_active ON projects(user_id, is_deleted, created_at DESC);

-- GIN 索引
CREATE INDEX idx_projects_canvas_data ON projects USING GIN(canvas_data);
CREATE INDEX idx_projects_ext_json ON projects USING GIN(ext_json);

-- 触发器
CREATE TRIGGER trg_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_projects_soft_delete
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();

-- 维护 profiles.project_count 冗余字段的触发器
CREATE OR REPLACE FUNCTION update_profile_project_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.is_deleted = FALSE THEN
        UPDATE profiles SET project_count = project_count + 1 WHERE id = NEW.user_id;
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.is_deleted = FALSE AND NEW.is_deleted = TRUE THEN
            UPDATE profiles SET project_count = project_count - 1 WHERE id = NEW.user_id;
        ELSIF OLD.is_deleted = TRUE AND NEW.is_deleted = FALSE THEN
            UPDATE profiles SET project_count = project_count + 1 WHERE id = NEW.user_id;
        END IF;
    ELSIF TG_OP = 'DELETE' AND OLD.is_deleted = FALSE THEN
        UPDATE profiles SET project_count = project_count - 1 WHERE id = OLD.user_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_projects_update_profile_count
    AFTER INSERT OR UPDATE OR DELETE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_profile_project_count();

-- ----------------------------------------------------------------------------
-- 4. project_versions (项目版本表)
-- 记录项目的历史版本
-- ----------------------------------------------------------------------------
CREATE TABLE project_versions (
    -- 主键
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 项目ID (外键)
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- 版本信息
    version_number INTEGER NOT NULL CHECK (version_number > 0),
    version_name TEXT,

    -- 快照数据
    canvas_data JSONB NOT NULL,
    thumbnail_url TEXT,

    -- 变更信息
    change_summary TEXT,

    -- 扩展字段
    ext_json JSONB DEFAULT '{}'::jsonb,

    -- 标准审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,

    -- 唯一约束: 每个项目的版本号唯一
    UNIQUE(project_id, version_number)
);

COMMENT ON TABLE project_versions IS '项目版本表: 记录项目的历史版本快照';
COMMENT ON COLUMN project_versions.version_number IS '版本号: 从 1 开始递增';

-- 索引
CREATE INDEX idx_project_versions_project_id ON project_versions(project_id);
CREATE INDEX idx_project_versions_created_at ON project_versions(created_at DESC);

-- 复合索引
CREATE INDEX idx_project_versions_project_version ON project_versions(project_id, version_number DESC);

-- GIN 索引
CREATE INDEX idx_project_versions_canvas_data ON project_versions USING GIN(canvas_data);

-- 触发器
CREATE TRIGGER trg_project_versions_updated_at
    BEFORE UPDATE ON project_versions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_project_versions_soft_delete
    BEFORE UPDATE ON project_versions
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();

-- ============================================================================
-- 第四部分: 市场相关表
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 5. marketplace_listings (市场列表表)
-- 用户发布到市场的素材/模板
-- ----------------------------------------------------------------------------
CREATE TABLE marketplace_listings (
    -- 主键
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 卖家信息
    seller_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    -- 关联项目
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,

    -- 基础信息
    title TEXT NOT NULL,
    description TEXT,
    thumbnail_url TEXT NOT NULL,
    preview_images TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- 分类 (v3.26 两级分类)
    primary_category TEXT NOT NULL CHECK (primary_category IN (
        'template',      -- 模板
        'sticker',       -- 贴纸
        'background',    -- 背景
        'frame',         -- 边框
        'text',          -- 文字
        'shape',         -- 形状
        'icon',          -- 图标
        'pattern',       -- 图案
        'clip_art',      -- 剪贴画
        'other'          -- 其他
    )),
    secondary_category TEXT,
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- 定价
    price_type TEXT NOT NULL CHECK (price_type IN ('free', 'credits', 'subscription_only')),
    price_credits INTEGER CHECK (price_credits >= 0),

    -- 资源文件
    asset_file_url TEXT NOT NULL,
    asset_file_size INTEGER CHECK (asset_file_size > 0),
    asset_file_format TEXT,

    -- 状态
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'pending_review', 'approved', 'rejected', 'archived')),
    review_notes TEXT,
    reviewed_at TIMESTAMPTZ,
    reviewed_by TEXT,

    -- 统计字段
    view_count INTEGER DEFAULT 0 CHECK (view_count >= 0),
    download_count INTEGER DEFAULT 0 CHECK (download_count >= 0),
    purchase_count INTEGER DEFAULT 0 CHECK (purchase_count >= 0),
    favorite_count INTEGER DEFAULT 0 CHECK (favorite_count >= 0),
    rating_average DECIMAL(3,2) CHECK (rating_average >= 0 AND rating_average <= 5),
    rating_count INTEGER DEFAULT 0 CHECK (rating_count >= 0),

    -- 扩展字段
    ext_json JSONB DEFAULT '{}'::jsonb,

    -- 标准审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ
);

COMMENT ON TABLE marketplace_listings IS '市场列表表: 用户发布的素材/模板';
COMMENT ON COLUMN marketplace_listings.primary_category IS '主分类 (v3.26): template/sticker/background 等 10 类 @Ref: 原 category';
COMMENT ON COLUMN marketplace_listings.secondary_category IS '次分类 (v3.26): 细分类别，如 template → education/business @Ref: 原字段无';
COMMENT ON COLUMN marketplace_listings.price_type IS '价格类型: free=免费, credits=积分购买, subscription_only=订阅专属';

-- 索引
CREATE INDEX idx_marketplace_listings_seller_id ON marketplace_listings(seller_id);
CREATE INDEX idx_marketplace_listings_status ON marketplace_listings(status);
CREATE INDEX idx_marketplace_listings_primary_category ON marketplace_listings(primary_category);
CREATE INDEX idx_marketplace_listings_created_at ON marketplace_listings(created_at DESC);
CREATE INDEX idx_marketplace_listings_active ON marketplace_listings(is_deleted) WHERE is_deleted = FALSE;

-- 复合索引
CREATE INDEX idx_marketplace_listings_category_status ON marketplace_listings(primary_category, status, created_at DESC);
CREATE INDEX idx_marketplace_listings_seller_status ON marketplace_listings(seller_id, status);

-- 排序索引
CREATE INDEX idx_marketplace_listings_popular ON marketplace_listings(download_count DESC, view_count DESC);
CREATE INDEX idx_marketplace_listings_rating ON marketplace_listings(rating_average DESC, rating_count DESC);

-- GIN 索引
CREATE INDEX idx_marketplace_listings_tags ON marketplace_listings USING GIN(tags);
CREATE INDEX idx_marketplace_listings_ext_json ON marketplace_listings USING GIN(ext_json);

-- 全文搜索索引
CREATE INDEX idx_marketplace_listings_search ON marketplace_listings USING GIN(
    to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(description, ''))
);

-- 触发器
CREATE TRIGGER trg_marketplace_listings_updated_at
    BEFORE UPDATE ON marketplace_listings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_marketplace_listings_soft_delete
    BEFORE UPDATE ON marketplace_listings
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();

-- 维护 profiles.asset_count 冗余字段的触发器
CREATE OR REPLACE FUNCTION update_profile_asset_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.is_deleted = FALSE AND NEW.status = 'approved' THEN
        UPDATE profiles SET asset_count = asset_count + 1 WHERE id = NEW.seller_id;
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.is_deleted = FALSE AND OLD.status = 'approved' AND
           (NEW.is_deleted = TRUE OR NEW.status != 'approved') THEN
            UPDATE profiles SET asset_count = asset_count - 1 WHERE id = NEW.seller_id;
        ELSIF (OLD.is_deleted = TRUE OR OLD.status != 'approved') AND
              NEW.is_deleted = FALSE AND NEW.status = 'approved' THEN
            UPDATE profiles SET asset_count = asset_count + 1 WHERE id = NEW.seller_id;
        END IF;
    ELSIF TG_OP = 'DELETE' AND OLD.is_deleted = FALSE AND OLD.status = 'approved' THEN
        UPDATE profiles SET asset_count = asset_count - 1 WHERE id = OLD.seller_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_marketplace_listings_update_profile_count
    AFTER INSERT OR UPDATE OR DELETE ON marketplace_listings
    FOR EACH ROW
    EXECUTE FUNCTION update_profile_asset_count();

-- ----------------------------------------------------------------------------
-- 6. marketplace_purchases (市场购买记录表)
-- 记录用户购买市场素材的记录
-- ----------------------------------------------------------------------------
CREATE TABLE marketplace_purchases (
    -- 主键
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 买家信息
    buyer_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    -- 卖家信息
    seller_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    -- 列表信息
    listing_id UUID NOT NULL REFERENCES marketplace_listings(id) ON DELETE CASCADE,

    -- 价格信息
    price_credits INTEGER NOT NULL CHECK (price_credits >= 0),

    -- 收益分成 (90% 卖家，10% 平台)
    seller_revenue_credits INTEGER NOT NULL CHECK (seller_revenue_credits >= 0),
    platform_fee_credits INTEGER NOT NULL CHECK (platform_fee_credits >= 0),

    -- 幂等性键
    idempotency_key TEXT UNIQUE,

    -- 下载信息
    download_url TEXT,
    download_expires_at TIMESTAMPTZ,

    -- 扩展字段
    ext_json JSONB DEFAULT '{}'::jsonb,

    -- 标准审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,

    -- 约束: 同一用户不能重复购买同一素材
    UNIQUE(buyer_id, listing_id)
);

COMMENT ON TABLE marketplace_purchases IS '市场购买记录表: 记录用户购买素材的交易';
COMMENT ON COLUMN marketplace_purchases.seller_revenue_credits IS '卖家收益积分 (90%)';
COMMENT ON COLUMN marketplace_purchases.platform_fee_credits IS '平台手续费积分 (10%)';

-- 索引
CREATE INDEX idx_marketplace_purchases_buyer_id ON marketplace_purchases(buyer_id);
CREATE INDEX idx_marketplace_purchases_seller_id ON marketplace_purchases(seller_id);
CREATE INDEX idx_marketplace_purchases_listing_id ON marketplace_purchases(listing_id);
CREATE INDEX idx_marketplace_purchases_created_at ON marketplace_purchases(created_at DESC);

-- 复合索引
CREATE INDEX idx_marketplace_purchases_buyer_time ON marketplace_purchases(buyer_id, created_at DESC);
CREATE INDEX idx_marketplace_purchases_seller_time ON marketplace_purchases(seller_id, created_at DESC);

-- 触发器
CREATE TRIGGER trg_marketplace_purchases_updated_at
    BEFORE UPDATE ON marketplace_purchases
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_marketplace_purchases_soft_delete
    BEFORE UPDATE ON marketplace_purchases
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();

-- 维护 marketplace_listings.purchase_count 冗余字段的触发器
CREATE OR REPLACE FUNCTION update_listing_purchase_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.is_deleted = FALSE THEN
        UPDATE marketplace_listings SET purchase_count = purchase_count + 1 WHERE id = NEW.listing_id;
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.is_deleted = FALSE AND NEW.is_deleted = TRUE THEN
            UPDATE marketplace_listings SET purchase_count = purchase_count - 1 WHERE id = NEW.listing_id;
        ELSIF OLD.is_deleted = TRUE AND NEW.is_deleted = FALSE THEN
            UPDATE marketplace_listings SET purchase_count = purchase_count + 1 WHERE id = NEW.listing_id;
        END IF;
    ELSIF TG_OP = 'DELETE' AND OLD.is_deleted = FALSE THEN
        UPDATE marketplace_listings SET purchase_count = purchase_count - 1 WHERE id = OLD.listing_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_marketplace_purchases_update_listing_count
    AFTER INSERT OR UPDATE OR DELETE ON marketplace_purchases
    FOR EACH ROW
    EXECUTE FUNCTION update_listing_purchase_count();

-- ----------------------------------------------------------------------------
-- 7. marketplace_favorites (市场收藏表)
-- 用户收藏的市场素材
-- ----------------------------------------------------------------------------
CREATE TABLE marketplace_favorites (
    -- 主键
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 用户ID
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    -- 列表ID
    listing_id UUID NOT NULL REFERENCES marketplace_listings(id) ON DELETE CASCADE,

    -- 标准审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,

    -- 唯一约束
    UNIQUE(user_id, listing_id)
);

COMMENT ON TABLE marketplace_favorites IS '市场收藏表: 用户收藏的素材';

-- 索引
CREATE INDEX idx_marketplace_favorites_user_id ON marketplace_favorites(user_id);
CREATE INDEX idx_marketplace_favorites_listing_id ON marketplace_favorites(listing_id);
CREATE INDEX idx_marketplace_favorites_created_at ON marketplace_favorites(created_at DESC);

-- 复合索引
CREATE INDEX idx_marketplace_favorites_user_time ON marketplace_favorites(user_id, created_at DESC);

-- 触发器
CREATE TRIGGER trg_marketplace_favorites_updated_at
    BEFORE UPDATE ON marketplace_favorites
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_marketplace_favorites_soft_delete
    BEFORE UPDATE ON marketplace_favorites
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();

-- 维护 marketplace_listings.favorite_count 冗余字段的触发器
CREATE OR REPLACE FUNCTION update_listing_favorite_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.is_deleted = FALSE THEN
        UPDATE marketplace_listings SET favorite_count = favorite_count + 1 WHERE id = NEW.listing_id;
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.is_deleted = FALSE AND NEW.is_deleted = TRUE THEN
            UPDATE marketplace_listings SET favorite_count = favorite_count - 1 WHERE id = NEW.listing_id;
        ELSIF OLD.is_deleted = TRUE AND NEW.is_deleted = FALSE THEN
            UPDATE marketplace_listings SET favorite_count = favorite_count + 1 WHERE id = NEW.listing_id;
        END IF;
    ELSIF TG_OP = 'DELETE' AND OLD.is_deleted = FALSE THEN
        UPDATE marketplace_listings SET favorite_count = favorite_count - 1 WHERE id = OLD.listing_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_marketplace_favorites_update_listing_count
    AFTER INSERT OR UPDATE OR DELETE ON marketplace_favorites
    FOR EACH ROW
    EXECUTE FUNCTION update_listing_favorite_count();

-- ----------------------------------------------------------------------------
-- 8. marketplace_reviews (市场评论表)
-- 用户对市场素材的评价
-- ----------------------------------------------------------------------------
CREATE TABLE marketplace_reviews (
    -- 主键
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 评论者信息
    reviewer_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    -- 列表信息
    listing_id UUID NOT NULL REFERENCES marketplace_listings(id) ON DELETE CASCADE,

    -- 评分 (1-5)
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),

    -- 评论内容
    comment TEXT,

    -- 扩展字段
    ext_json JSONB DEFAULT '{}'::jsonb,

    -- 标准审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,

    -- 唯一约束: 每个用户对每个素材只能评论一次
    UNIQUE(reviewer_id, listing_id)
);

COMMENT ON TABLE marketplace_reviews IS '市场评论表: 用户对素材的评价';
COMMENT ON COLUMN marketplace_reviews.rating IS '评分: 1-5 星';

-- 索引
CREATE INDEX idx_marketplace_reviews_listing_id ON marketplace_reviews(listing_id);
CREATE INDEX idx_marketplace_reviews_reviewer_id ON marketplace_reviews(reviewer_id);
CREATE INDEX idx_marketplace_reviews_created_at ON marketplace_reviews(created_at DESC);

-- 复合索引
CREATE INDEX idx_marketplace_reviews_listing_rating ON marketplace_reviews(listing_id, rating);

-- 触发器
CREATE TRIGGER trg_marketplace_reviews_updated_at
    BEFORE UPDATE ON marketplace_reviews
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_marketplace_reviews_soft_delete
    BEFORE UPDATE ON marketplace_reviews
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();

-- 维护 marketplace_listings 评分冗余字段的触发器
CREATE OR REPLACE FUNCTION update_listing_rating()
RETURNS TRIGGER AS $$
DECLARE
    new_avg DECIMAL(3,2);
    new_count INTEGER;
BEGIN
    -- 计算新的平均分和评分数
    SELECT
        ROUND(AVG(rating)::NUMERIC, 2),
        COUNT(*)
    INTO new_avg, new_count
    FROM marketplace_reviews
    WHERE listing_id = COALESCE(NEW.listing_id, OLD.listing_id)
      AND is_deleted = FALSE;

    -- 更新 listing
    UPDATE marketplace_listings
    SET
        rating_average = new_avg,
        rating_count = new_count
    WHERE id = COALESCE(NEW.listing_id, OLD.listing_id);

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_marketplace_reviews_update_listing_rating
    AFTER INSERT OR UPDATE OR DELETE ON marketplace_reviews
    FOR EACH ROW
    EXECUTE FUNCTION update_listing_rating();

-- ============================================================================
-- 第五部分: AI 生成相关表
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 9. user_generations (用户生成记录表 v3.24)
-- 记录用户使用 AI 生成的历史
-- ----------------------------------------------------------------------------
CREATE TABLE user_generations (
    -- 主键
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 用户ID
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    -- 生成类型
    generation_type TEXT NOT NULL CHECK (generation_type IN ('image', 'text', 'smart_scan')),

    -- 输入信息
    prompt TEXT,
    input_params JSONB DEFAULT '{}'::jsonb,

    -- 输出信息
    output_url TEXT,
    output_data JSONB DEFAULT '{}'::jsonb,

    -- 状态
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    error_message TEXT,

    -- 成本信息
    credits_cost INTEGER NOT NULL CHECK (credits_cost >= 0),

    -- AI 提供商信息
    ai_provider TEXT,  -- 'fal.ai', 'openai', etc.
    ai_model TEXT,

    -- 关联项目
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,

    -- 扩展字段
    ext_json JSONB DEFAULT '{}'::jsonb,

    -- 标准审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ
);

COMMENT ON TABLE user_generations IS '用户生成记录表 (v3.24): 记录 AI 图片/文字/Smart Scan 生成历史';
COMMENT ON COLUMN user_generations.generation_type IS '生成类型: image=AI图片, text=AI文字, smart_scan=Smart Scan';
COMMENT ON COLUMN user_generations.credits_cost IS '积分成本: image=5, text=1, smart_scan=10';

-- 索引
CREATE INDEX idx_user_generations_user_id ON user_generations(user_id);
CREATE INDEX idx_user_generations_type ON user_generations(generation_type);
CREATE INDEX idx_user_generations_status ON user_generations(status);
CREATE INDEX idx_user_generations_created_at ON user_generations(created_at DESC);

-- 复合索引
CREATE INDEX idx_user_generations_user_time ON user_generations(user_id, created_at DESC);
CREATE INDEX idx_user_generations_user_type ON user_generations(user_id, generation_type);

-- GIN 索引
CREATE INDEX idx_user_generations_input_params ON user_generations USING GIN(input_params);
CREATE INDEX idx_user_generations_output_data ON user_generations USING GIN(output_data);

-- 触发器
CREATE TRIGGER trg_user_generations_updated_at
    BEFORE UPDATE ON user_generations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_user_generations_soft_delete
    BEFORE UPDATE ON user_generations
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();

-- ----------------------------------------------------------------------------
-- 10. generation_tasks (异步生成任务表 v3.23)
-- 记录异步 AI 生成任务队列
-- ----------------------------------------------------------------------------
CREATE TABLE generation_tasks (
    -- 主键
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 用户ID
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    -- 任务类型
    task_type TEXT NOT NULL CHECK (task_type IN ('image', 'text', 'smart_scan', 'batch_export')),

    -- 输入数据
    input_data JSONB NOT NULL,

    -- 输出数据
    output_data JSONB DEFAULT '{}'::jsonb,

    -- 状态
    status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'processing', 'completed', 'failed')),
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    error_message TEXT,

    -- 重试信息
    retry_count INTEGER DEFAULT 0 CHECK (retry_count >= 0),
    max_retries INTEGER DEFAULT 3 CHECK (max_retries >= 0),

    -- 优先级
    priority INTEGER DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),

    -- 时间信息
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    -- 扩展字段
    ext_json JSONB DEFAULT '{}'::jsonb,

    -- 标准审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ
);

COMMENT ON TABLE generation_tasks IS '异步生成任务表 (v3.23): 异步 AI 生成任务队列';
COMMENT ON COLUMN generation_tasks.priority IS '优先级: 1-10, 数字越大优先级越高';
COMMENT ON COLUMN generation_tasks.progress IS '进度: 0-100';

-- 索引
CREATE INDEX idx_generation_tasks_user_id ON generation_tasks(user_id);
CREATE INDEX idx_generation_tasks_status ON generation_tasks(status);
CREATE INDEX idx_generation_tasks_created_at ON generation_tasks(created_at DESC);

-- 复合索引 (任务队列查询)
CREATE INDEX idx_generation_tasks_queue ON generation_tasks(status, priority DESC, created_at ASC)
    WHERE status IN ('queued', 'processing');

-- GIN 索引
CREATE INDEX idx_generation_tasks_input_data ON generation_tasks USING GIN(input_data);
CREATE INDEX idx_generation_tasks_output_data ON generation_tasks USING GIN(output_data);

-- 触发器
CREATE TRIGGER trg_generation_tasks_updated_at
    BEFORE UPDATE ON generation_tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_generation_tasks_soft_delete
    BEFORE UPDATE ON generation_tasks
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();

-- ============================================================================
-- 第六部分: 支付相关表
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 11. stripe_webhook_events (Stripe Webhook 事件表)
-- 记录所有 Stripe Webhook 事件，防重复处理
-- ----------------------------------------------------------------------------
CREATE TABLE stripe_webhook_events (
    -- 主键 (使用 Stripe Event ID)
    id TEXT PRIMARY KEY,

    -- 事件类型
    event_type TEXT NOT NULL,

    -- 事件数据
    event_data JSONB NOT NULL,

    -- 处理状态
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'processed', 'failed')),
    processed_at TIMESTAMPTZ,
    error_message TEXT,

    -- 重试信息
    retry_count INTEGER DEFAULT 0 CHECK (retry_count >= 0),

    -- 标准审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE stripe_webhook_events IS 'Stripe Webhook 事件表: 记录所有 Webhook 事件，实现幂等性';
COMMENT ON COLUMN stripe_webhook_events.id IS 'Stripe Event ID (evt_xxx...), 保证幂等性';

-- 索引
CREATE INDEX idx_stripe_webhook_events_type ON stripe_webhook_events(event_type);
CREATE INDEX idx_stripe_webhook_events_status ON stripe_webhook_events(status);
CREATE INDEX idx_stripe_webhook_events_created_at ON stripe_webhook_events(created_at DESC);

-- 复合索引
CREATE INDEX idx_stripe_webhook_events_type_status ON stripe_webhook_events(event_type, status);

-- GIN 索引
CREATE INDEX idx_stripe_webhook_events_data ON stripe_webhook_events USING GIN(event_data);

-- 触发器
CREATE TRIGGER trg_stripe_webhook_events_updated_at
    BEFORE UPDATE ON stripe_webhook_events
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ----------------------------------------------------------------------------
-- 12. subscription_history (订阅历史表)
-- 记录用户订阅的变更历史
-- ----------------------------------------------------------------------------
CREATE TABLE subscription_history (
    -- 主键
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 用户ID
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    -- 订阅信息
    stripe_subscription_id TEXT NOT NULL,

    -- 等级信息
    tier_from TEXT CHECK (tier_from IN ('free', 'starter', 'pro')),
    tier_to TEXT NOT NULL CHECK (tier_to IN ('free', 'starter', 'pro')),

    -- 事件类型
    event_type TEXT NOT NULL CHECK (event_type IN (
        'subscription_created',
        'subscription_updated',
        'subscription_canceled',
        'subscription_renewed',
        'trial_started',
        'trial_ended'
    )),

    -- 价格信息
    price_amount DECIMAL(10,2),
    currency TEXT DEFAULT 'USD',

    -- 周期信息
    period_start TIMESTAMPTZ,
    period_end TIMESTAMPTZ,

    -- 扩展字段
    ext_json JSONB DEFAULT '{}'::jsonb,

    -- 标准审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ
);

COMMENT ON TABLE subscription_history IS '订阅历史表: 记录用户订阅的所有变更';
COMMENT ON COLUMN subscription_history.tier_from IS '原等级: free/starter/pro (新订阅时为 NULL)';
COMMENT ON COLUMN subscription_history.tier_to IS '新等级: free/starter/pro';

-- 索引
CREATE INDEX idx_subscription_history_user_id ON subscription_history(user_id);
CREATE INDEX idx_subscription_history_stripe_sub_id ON subscription_history(stripe_subscription_id);
CREATE INDEX idx_subscription_history_event_type ON subscription_history(event_type);
CREATE INDEX idx_subscription_history_created_at ON subscription_history(created_at DESC);

-- 复合索引
CREATE INDEX idx_subscription_history_user_time ON subscription_history(user_id, created_at DESC);

-- 触发器
CREATE TRIGGER trg_subscription_history_updated_at
    BEFORE UPDATE ON subscription_history
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_subscription_history_soft_delete
    BEFORE UPDATE ON subscription_history
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();

-- ----------------------------------------------------------------------------
-- 13. credit_purchases (积分购买记录表)
-- 记录用户购买积分包的交易
-- ----------------------------------------------------------------------------
CREATE TABLE credit_purchases (
    -- 主键
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 用户ID
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    -- Stripe 信息
    stripe_payment_intent_id TEXT UNIQUE,
    stripe_charge_id TEXT,

    -- 产品信息
    product_type TEXT NOT NULL CHECK (product_type IN ('credits_100', 'credits_500', 'credits_2000')),
    credits_amount INTEGER NOT NULL CHECK (credits_amount > 0),

    -- 价格信息
    price_amount DECIMAL(10,2) NOT NULL CHECK (price_amount >= 0),
    currency TEXT NOT NULL DEFAULT 'USD',

    -- 状态
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed', 'refunded')),

    -- 幂等性键
    idempotency_key TEXT UNIQUE,

    -- 扩展字段
    ext_json JSONB DEFAULT '{}'::jsonb,

    -- 标准审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ
);

COMMENT ON TABLE credit_purchases IS '积分购买记录表: 记录用户购买积分包的交易';
COMMENT ON COLUMN credit_purchases.product_type IS '产品类型: credits_100/credits_500/credits_2000';
COMMENT ON COLUMN credit_purchases.credits_amount IS '积分数量: 100/500/2000';

-- 索引
CREATE INDEX idx_credit_purchases_user_id ON credit_purchases(user_id);
CREATE INDEX idx_credit_purchases_stripe_pi ON credit_purchases(stripe_payment_intent_id) WHERE stripe_payment_intent_id IS NOT NULL;
CREATE INDEX idx_credit_purchases_status ON credit_purchases(status);
CREATE INDEX idx_credit_purchases_created_at ON credit_purchases(created_at DESC);

-- 复合索引
CREATE INDEX idx_credit_purchases_user_time ON credit_purchases(user_id, created_at DESC);

-- 触发器
CREATE TRIGGER trg_credit_purchases_updated_at
    BEFORE UPDATE ON credit_purchases
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_credit_purchases_soft_delete
    BEFORE UPDATE ON credit_purchases
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();

-- ============================================================================
-- 第七部分: 配置与系统表
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 14. system_configs (系统配置表)
-- 存储系统级配置参数
-- ----------------------------------------------------------------------------
CREATE TABLE system_configs (
    -- 主键
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 配置键 (唯一)
    config_key TEXT NOT NULL UNIQUE,

    -- 配置值
    config_value TEXT NOT NULL,

    -- 数据类型
    value_type TEXT NOT NULL CHECK (value_type IN ('string', 'integer', 'decimal', 'boolean', 'json')),

    -- 分组
    config_group TEXT NOT NULL,

    -- 描述
    description TEXT,

    -- 是否可修改
    is_editable BOOLEAN DEFAULT TRUE,

    -- 扩展字段
    ext_json JSONB DEFAULT '{}'::jsonb,

    -- 标准审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ
);

COMMENT ON TABLE system_configs IS '系统配置表: 存储系统级配置参数 (AI成本、等级权益等)';
COMMENT ON COLUMN system_configs.config_key IS '配置键: 唯一标识符, 如 ai.image.cost';
COMMENT ON COLUMN system_configs.value_type IS '值类型: string/integer/decimal/boolean/json';

-- 索引
CREATE UNIQUE INDEX idx_system_configs_key ON system_configs(config_key);
CREATE INDEX idx_system_configs_group ON system_configs(config_group);

-- 触发器
CREATE TRIGGER trg_system_configs_updated_at
    BEFORE UPDATE ON system_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_system_configs_soft_delete
    BEFORE UPDATE ON system_configs
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();

-- 默认配置数据
INSERT INTO system_configs (config_key, config_value, value_type, config_group, description, is_editable) VALUES
-- AI 成本配置
('ai.image.cost', '5', 'integer', 'ai', 'AI图片生成成本 (积分)', TRUE),
('ai.text.cost', '1', 'integer', 'ai', 'AI文字生成成本 (积分)', TRUE),
('ai.smart_scan.cost', '10', 'integer', 'ai', 'Smart Scan 成本 (积分)', TRUE),

-- 等级月度积分
('tier.free.monthly_credits', '0', 'integer', 'tier', 'Free 等级月度积分', FALSE),
('tier.starter.monthly_credits', '200', 'integer', 'tier', 'Starter 等级月度积分', FALSE),
('tier.pro.monthly_credits', '500', 'integer', 'tier', 'Pro 等级月度积分', FALSE),

-- 注册奖励
('signup.bonus_credits', '50', 'integer', 'signup', '注册奖励积分 (永久)', TRUE),

-- 市场收益分成
('marketplace.seller_revenue_ratio', '0.9', 'decimal', 'marketplace', '卖家收益比例 (90%)', FALSE),
('marketplace.platform_fee_ratio', '0.1', 'decimal', 'marketplace', '平台手续费比例 (10%)', FALSE),

-- 试用期
('trial.duration_days', '30', 'integer', 'trial', '试用期天数', TRUE);

-- ----------------------------------------------------------------------------
-- 15. clerk_webhook_events (Clerk Webhook 事件表)
-- 记录 Clerk 认证事件
-- ----------------------------------------------------------------------------
CREATE TABLE clerk_webhook_events (
    -- 主键 (使用 Clerk Event ID)
    id TEXT PRIMARY KEY,

    -- 事件类型
    event_type TEXT NOT NULL,

    -- 事件数据
    event_data JSONB NOT NULL,

    -- 处理状态
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'processed', 'failed')),
    processed_at TIMESTAMPTZ,
    error_message TEXT,

    -- 重试信息
    retry_count INTEGER DEFAULT 0 CHECK (retry_count >= 0),

    -- 标准审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE clerk_webhook_events IS 'Clerk Webhook 事件表: 记录用户注册/更新/删除事件';
COMMENT ON COLUMN clerk_webhook_events.id IS 'Clerk Event ID, 保证幂等性';

-- 索引
CREATE INDEX idx_clerk_webhook_events_type ON clerk_webhook_events(event_type);
CREATE INDEX idx_clerk_webhook_events_status ON clerk_webhook_events(status);
CREATE INDEX idx_clerk_webhook_events_created_at ON clerk_webhook_events(created_at DESC);

-- GIN 索引
CREATE INDEX idx_clerk_webhook_events_data ON clerk_webhook_events USING GIN(event_data);

-- 触发器
CREATE TRIGGER trg_clerk_webhook_events_updated_at
    BEFORE UPDATE ON clerk_webhook_events
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 第八部分: 营销活动表
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 16. campaigns (活动表)
-- 营销活动/促销活动
-- ----------------------------------------------------------------------------
CREATE TABLE campaigns (
    -- 主键
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 活动信息
    name TEXT NOT NULL,
    description TEXT,
    campaign_type TEXT NOT NULL CHECK (campaign_type IN ('promotion', 'referral', 'event', 'holiday')),

    -- 时间范围
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ NOT NULL,

    -- 奖励配置
    reward_type TEXT CHECK (reward_type IN ('credits', 'discount', 'free_tier_upgrade')),
    reward_amount INTEGER CHECK (reward_amount >= 0),

    -- 使用限制
    max_uses INTEGER CHECK (max_uses > 0),
    current_uses INTEGER DEFAULT 0 CHECK (current_uses >= 0),
    max_uses_per_user INTEGER DEFAULT 1 CHECK (max_uses_per_user > 0),

    -- 状态
    is_active BOOLEAN DEFAULT TRUE,

    -- 扩展字段
    ext_json JSONB DEFAULT '{}'::jsonb,

    -- 标准审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,

    -- 约束: 结束时间必须晚于开始时间
    CHECK (end_date > start_date)
);

COMMENT ON TABLE campaigns IS '活动表: 营销活动/促销活动配置';
COMMENT ON COLUMN campaigns.campaign_type IS '活动类型: promotion=促销, referral=推荐, event=事件, holiday=节假日';
COMMENT ON COLUMN campaigns.max_uses IS '活动总使用次数上限';
COMMENT ON COLUMN campaigns.current_uses IS '当前已使用次数 (冗余字段，由触发器维护)';

-- 索引
CREATE INDEX idx_campaigns_type ON campaigns(campaign_type);
CREATE INDEX idx_campaigns_active ON campaigns(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_campaigns_date_range ON campaigns(start_date, end_date);

-- 部分索引 (查询活跃活动)
CREATE INDEX idx_campaigns_active_now ON campaigns(start_date, end_date)
    WHERE is_active = TRUE AND is_deleted = FALSE;

-- 触发器
CREATE TRIGGER trg_campaigns_updated_at
    BEFORE UPDATE ON campaigns
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_campaigns_soft_delete
    BEFORE UPDATE ON campaigns
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();

-- ----------------------------------------------------------------------------
-- 17. campaign_participations (活动参与记录表)
-- 记录用户参与活动的记录
-- ----------------------------------------------------------------------------
CREATE TABLE campaign_participations (
    -- 主键
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 用户ID
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    -- 活动ID
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,

    -- 奖励信息
    reward_type TEXT NOT NULL,
    reward_amount INTEGER CHECK (reward_amount >= 0),

    -- 是否已发放
    is_rewarded BOOLEAN DEFAULT FALSE,
    rewarded_at TIMESTAMPTZ,

    -- 扩展字段
    ext_json JSONB DEFAULT '{}'::jsonb,

    -- 标准审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ
);

COMMENT ON TABLE campaign_participations IS '活动参与记录表: 记录用户参与活动并获得奖励';

-- 索引
CREATE INDEX idx_campaign_participations_user_id ON campaign_participations(user_id);
CREATE INDEX idx_campaign_participations_campaign_id ON campaign_participations(campaign_id);
CREATE INDEX idx_campaign_participations_created_at ON campaign_participations(created_at DESC);

-- 复合索引
CREATE INDEX idx_campaign_participations_user_campaign ON campaign_participations(user_id, campaign_id);

-- 触发器
CREATE TRIGGER trg_campaign_participations_updated_at
    BEFORE UPDATE ON campaign_participations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_campaign_participations_soft_delete
    BEFORE UPDATE ON campaign_participations
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();

-- 维护 campaigns.current_uses 冗余字段的触发器
CREATE OR REPLACE FUNCTION update_campaign_uses()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.is_deleted = FALSE THEN
        UPDATE campaigns SET current_uses = current_uses + 1 WHERE id = NEW.campaign_id;
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.is_deleted = FALSE AND NEW.is_deleted = TRUE THEN
            UPDATE campaigns SET current_uses = current_uses - 1 WHERE id = NEW.campaign_id;
        ELSIF OLD.is_deleted = TRUE AND NEW.is_deleted = FALSE THEN
            UPDATE campaigns SET current_uses = current_uses + 1 WHERE id = NEW.campaign_id;
        END IF;
    ELSIF TG_OP = 'DELETE' AND OLD.is_deleted = FALSE THEN
        UPDATE campaigns SET current_uses = current_uses - 1 WHERE id = OLD.campaign_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_campaign_participations_update_campaign_uses
    AFTER INSERT OR UPDATE OR DELETE ON campaign_participations
    FOR EACH ROW
    EXECUTE FUNCTION update_campaign_uses();

-- ----------------------------------------------------------------------------
-- 18. referrals (推荐关系表)
-- 记录用户推荐关系
-- ----------------------------------------------------------------------------
CREATE TABLE referrals (
    -- 主键
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 推荐人ID
    referrer_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    -- 被推荐人ID
    referee_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    -- 推荐码
    referral_code TEXT,

    -- 奖励状态
    is_rewarded BOOLEAN DEFAULT FALSE,
    rewarded_at TIMESTAMPTZ,
    reward_credits INTEGER CHECK (reward_credits >= 0),

    -- 扩展字段
    ext_json JSONB DEFAULT '{}'::jsonb,

    -- 标准审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,

    -- 唯一约束
    UNIQUE(referrer_id, referee_id)
);

COMMENT ON TABLE referrals IS '推荐关系表: 记录用户推荐关系和奖励';
COMMENT ON COLUMN referrals.referrer_id IS '推荐人ID';
COMMENT ON COLUMN referrals.referee_id IS '被推荐人ID';

-- 索引
CREATE INDEX idx_referrals_referrer_id ON referrals(referrer_id);
CREATE INDEX idx_referrals_referee_id ON referrals(referee_id);
CREATE INDEX idx_referrals_code ON referrals(referral_code) WHERE referral_code IS NOT NULL;
CREATE INDEX idx_referrals_created_at ON referrals(created_at DESC);

-- 触发器
CREATE TRIGGER trg_referrals_updated_at
    BEFORE UPDATE ON referrals
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_referrals_soft_delete
    BEFORE UPDATE ON referrals
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();

-- ============================================================================
-- 第九部分: Feature Flag & Experiments 表
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 19. feature_flags (功能开关表)
-- 控制功能的启用/禁用
-- ----------------------------------------------------------------------------
CREATE TABLE feature_flags (
    -- 主键
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 功能标识
    flag_key TEXT NOT NULL UNIQUE,

    -- 功能信息
    flag_name TEXT NOT NULL,
    description TEXT,

    -- 开关状态
    is_enabled BOOLEAN DEFAULT FALSE,

    -- 目标用户 (JSON 配置)
    target_config JSONB DEFAULT '{}'::jsonb,

    -- 分组
    flag_group TEXT,

    -- 扩展字段
    ext_json JSONB DEFAULT '{}'::jsonb,

    -- 标准审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ
);

COMMENT ON TABLE feature_flags IS '功能开关表: 控制功能的启用/禁用 (Feature Flag)';
COMMENT ON COLUMN feature_flags.flag_key IS '功能标识: 唯一键, 如 editor.new_ui';
COMMENT ON COLUMN feature_flags.target_config IS '目标配置: 可按用户ID/等级/百分比灰度发布';

-- 索引
CREATE UNIQUE INDEX idx_feature_flags_key ON feature_flags(flag_key);
CREATE INDEX idx_feature_flags_enabled ON feature_flags(is_enabled) WHERE is_enabled = TRUE;
CREATE INDEX idx_feature_flags_group ON feature_flags(flag_group);

-- GIN 索引
CREATE INDEX idx_feature_flags_target_config ON feature_flags USING GIN(target_config);

-- 触发器
CREATE TRIGGER trg_feature_flags_updated_at
    BEFORE UPDATE ON feature_flags
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_feature_flags_soft_delete
    BEFORE UPDATE ON feature_flags
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();

-- ----------------------------------------------------------------------------
-- 20. experiments (AB 测试表)
-- AB 测试实验配置
-- ----------------------------------------------------------------------------
CREATE TABLE experiments (
    -- 主键
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 实验信息
    experiment_key TEXT NOT NULL UNIQUE,
    experiment_name TEXT NOT NULL,
    description TEXT,

    -- 实验配置
    variants JSONB NOT NULL,  -- [{name: 'A', weight: 50}, {name: 'B', weight: 50}]

    -- 状态
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'running', 'paused', 'completed', 'archived')),

    -- 时间范围
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,

    -- 目标指标
    goal_metric TEXT,
    goal_description TEXT,

    -- 扩展字段
    ext_json JSONB DEFAULT '{}'::jsonb,

    -- 标准审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ
);

COMMENT ON TABLE experiments IS 'AB测试表: AB测试实验配置';
COMMENT ON COLUMN experiments.experiment_key IS '实验标识: 唯一键, 如 pricing.new_tiers';
COMMENT ON COLUMN experiments.variants IS '变体配置: JSON 数组，定义各变体及权重';

-- 索引
CREATE UNIQUE INDEX idx_experiments_key ON experiments(experiment_key);
CREATE INDEX idx_experiments_status ON experiments(status);
CREATE INDEX idx_experiments_date_range ON experiments(start_date, end_date);

-- GIN 索引
CREATE INDEX idx_experiments_variants ON experiments USING GIN(variants);

-- 触发器
CREATE TRIGGER trg_experiments_updated_at
    BEFORE UPDATE ON experiments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_experiments_soft_delete
    BEFORE UPDATE ON experiments
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();

-- ----------------------------------------------------------------------------
-- 21. experiment_assignments (实验分配表)
-- 记录用户被分配到的实验变体
-- ----------------------------------------------------------------------------
CREATE TABLE experiment_assignments (
    -- 主键
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 用户ID
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    -- 实验ID
    experiment_id UUID NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,

    -- 分配的变体
    variant_name TEXT NOT NULL,

    -- 扩展字段
    ext_json JSONB DEFAULT '{}'::jsonb,

    -- 标准审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,

    -- 唯一约束
    UNIQUE(user_id, experiment_id)
);

COMMENT ON TABLE experiment_assignments IS '实验分配表: 记录用户被分配到的AB测试变体';

-- 索引
CREATE INDEX idx_experiment_assignments_user_id ON experiment_assignments(user_id);
CREATE INDEX idx_experiment_assignments_experiment_id ON experiment_assignments(experiment_id);
CREATE INDEX idx_experiment_assignments_variant ON experiment_assignments(variant_name);

-- 复合索引
CREATE INDEX idx_experiment_assignments_exp_variant ON experiment_assignments(experiment_id, variant_name);

-- 触发器
CREATE TRIGGER trg_experiment_assignments_updated_at
    BEFORE UPDATE ON experiment_assignments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_experiment_assignments_soft_delete
    BEFORE UPDATE ON experiment_assignments
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();

-- ============================================================================
-- 第十部分: 分析与日志表
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 22. analytics_events (分析事件表)
-- 记录用户行为事件
-- ----------------------------------------------------------------------------
CREATE TABLE analytics_events (
    -- 主键
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 用户ID (可为空，匿名用户)
    user_id TEXT REFERENCES profiles(id) ON DELETE CASCADE,

    -- 事件信息
    event_name TEXT NOT NULL,
    event_category TEXT,

    -- 事件数据
    event_properties JSONB DEFAULT '{}'::jsonb,

    -- 会话信息
    session_id TEXT,

    -- 设备信息
    device_type TEXT,
    browser TEXT,
    os TEXT,

    -- 地理位置
    country TEXT,
    city TEXT,

    -- 来源信息
    referrer TEXT,
    utm_source TEXT,
    utm_medium TEXT,
    utm_campaign TEXT,

    -- 标准审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP

    -- 注意: 此表没有 is_deleted/deleted_at (日志表，不删除)
);

COMMENT ON TABLE analytics_events IS '分析事件表: 记录用户行为事件 (页面浏览、按钮点击等)';
COMMENT ON COLUMN analytics_events.event_name IS '事件名称: page_view, button_click, project_created 等';

-- 索引
CREATE INDEX idx_analytics_events_user_id ON analytics_events(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_analytics_events_name ON analytics_events(event_name);
CREATE INDEX idx_analytics_events_category ON analytics_events(event_category);
CREATE INDEX idx_analytics_events_created_at ON analytics_events(created_at DESC);
CREATE INDEX idx_analytics_events_session ON analytics_events(session_id) WHERE session_id IS NOT NULL;

-- 复合索引
CREATE INDEX idx_analytics_events_user_time ON analytics_events(user_id, created_at DESC);
CREATE INDEX idx_analytics_events_name_time ON analytics_events(event_name, created_at DESC);

-- GIN 索引
CREATE INDEX idx_analytics_events_properties ON analytics_events USING GIN(event_properties);

-- 触发器
CREATE TRIGGER trg_analytics_events_updated_at
    BEFORE UPDATE ON analytics_events
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ----------------------------------------------------------------------------
-- 23. api_logs (API 日志表)
-- 记录 API 请求日志
-- ----------------------------------------------------------------------------
CREATE TABLE api_logs (
    -- 主键
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 用户ID (可为空)
    user_id TEXT REFERENCES profiles(id) ON DELETE CASCADE,

    -- 请求信息
    method TEXT NOT NULL,
    path TEXT NOT NULL,
    query_params JSONB DEFAULT '{}'::jsonb,

    -- 响应信息
    status_code INTEGER NOT NULL,
    response_time_ms INTEGER CHECK (response_time_ms >= 0),

    -- IP 信息
    ip_address INET,

    -- 错误信息
    error_message TEXT,

    -- 标准审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP

    -- 注意: 此表没有 is_deleted/deleted_at (日志表，不删除)
);

COMMENT ON TABLE api_logs IS 'API 日志表: 记录所有 API 请求和响应';
COMMENT ON COLUMN api_logs.response_time_ms IS '响应时间 (毫秒)';

-- 索引
CREATE INDEX idx_api_logs_user_id ON api_logs(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_api_logs_path ON api_logs(path);
CREATE INDEX idx_api_logs_status_code ON api_logs(status_code);
CREATE INDEX idx_api_logs_created_at ON api_logs(created_at DESC);

-- 复合索引
CREATE INDEX idx_api_logs_user_time ON api_logs(user_id, created_at DESC);
CREATE INDEX idx_api_logs_path_time ON api_logs(path, created_at DESC);

-- 部分索引 (错误日志)
CREATE INDEX idx_api_logs_errors ON api_logs(status_code, created_at DESC)
    WHERE status_code >= 400;

-- 触发器
CREATE TRIGGER trg_api_logs_updated_at
    BEFORE UPDATE ON api_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ----------------------------------------------------------------------------
-- 24. error_logs (错误日志表)
-- 记录系统错误和异常
-- ----------------------------------------------------------------------------
CREATE TABLE error_logs (
    -- 主键
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 用户ID (可为空)
    user_id TEXT REFERENCES profiles(id) ON DELETE CASCADE,

    -- 错误信息
    error_type TEXT NOT NULL,
    error_message TEXT NOT NULL,
    stack_trace TEXT,

    -- 上下文
    context_data JSONB DEFAULT '{}'::jsonb,

    -- 来源
    source TEXT,  -- 'backend', 'frontend'

    -- 严重性
    severity TEXT NOT NULL CHECK (severity IN ('info', 'warning', 'error', 'critical')),

    -- 标准审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP

    -- 注意: 此表没有 is_deleted/deleted_at (日志表，不删除)
);

COMMENT ON TABLE error_logs IS '错误日志表: 记录系统错误和异常';
COMMENT ON COLUMN error_logs.severity IS '严重性: info/warning/error/critical';

-- 索引
CREATE INDEX idx_error_logs_user_id ON error_logs(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_error_logs_type ON error_logs(error_type);
CREATE INDEX idx_error_logs_severity ON error_logs(severity);
CREATE INDEX idx_error_logs_created_at ON error_logs(created_at DESC);

-- 复合索引
CREATE INDEX idx_error_logs_severity_time ON error_logs(severity, created_at DESC);

-- GIN 索引
CREATE INDEX idx_error_logs_context ON error_logs USING GIN(context_data);

-- 触发器
CREATE TRIGGER trg_error_logs_updated_at
    BEFORE UPDATE ON error_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 第十一部分: 主题与新手引导表
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 25. themes (主题表)
-- 每日涂鸦主题
-- ----------------------------------------------------------------------------
CREATE TABLE themes (
    -- 主键
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 主题信息
    title TEXT NOT NULL,
    description TEXT,

    -- 日期范围
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,

    -- 缩略图
    thumbnail_url TEXT,

    -- 标签
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- 状态
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'archived')),

    -- 扩展字段
    ext_json JSONB DEFAULT '{}'::jsonb,

    -- 标准审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,

    -- 约束
    CHECK (end_date >= start_date)
);

COMMENT ON TABLE themes IS '主题表: 每日涂鸦主题配置';

-- 索引
CREATE INDEX idx_themes_status ON themes(status);
CREATE INDEX idx_themes_date_range ON themes(start_date, end_date);
CREATE INDEX idx_themes_created_at ON themes(created_at DESC);

-- GIN 索引
CREATE INDEX idx_themes_tags ON themes USING GIN(tags);

-- 触发器
CREATE TRIGGER trg_themes_updated_at
    BEFORE UPDATE ON themes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_themes_soft_delete
    BEFORE UPDATE ON themes
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();

-- ----------------------------------------------------------------------------
-- 26. onboarding_steps (新手引导步骤表)
-- 新手引导流程配置
-- ----------------------------------------------------------------------------
CREATE TABLE onboarding_steps (
    -- 主键
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 步骤信息
    step_key TEXT NOT NULL UNIQUE,
    step_name TEXT NOT NULL,
    description TEXT,

    -- 顺序
    step_order INTEGER NOT NULL CHECK (step_order > 0),

    -- 配置
    config JSONB DEFAULT '{}'::jsonb,

    -- 是否启用
    is_enabled BOOLEAN DEFAULT TRUE,

    -- 扩展字段
    ext_json JSONB DEFAULT '{}'::jsonb,

    -- 标准审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ
);

COMMENT ON TABLE onboarding_steps IS '新手引导步骤表: 新手引导流程配置';
COMMENT ON COLUMN onboarding_steps.step_key IS '步骤标识: 唯一键, 如 welcome, create_first_project';

-- 索引
CREATE UNIQUE INDEX idx_onboarding_steps_key ON onboarding_steps(step_key);
CREATE INDEX idx_onboarding_steps_order ON onboarding_steps(step_order);
CREATE INDEX idx_onboarding_steps_enabled ON onboarding_steps(is_enabled) WHERE is_enabled = TRUE;

-- 触发器
CREATE TRIGGER trg_onboarding_steps_updated_at
    BEFORE UPDATE ON onboarding_steps
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_onboarding_steps_soft_delete
    BEFORE UPDATE ON onboarding_steps
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();

-- ----------------------------------------------------------------------------
-- 27. user_onboarding_progress (用户引导进度表)
-- 记录用户完成新手引导的进度
-- ----------------------------------------------------------------------------
CREATE TABLE user_onboarding_progress (
    -- 主键
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 用户ID
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    -- 步骤ID
    step_id UUID NOT NULL REFERENCES onboarding_steps(id) ON DELETE CASCADE,

    -- 完成状态
    is_completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMPTZ,

    -- 跳过状态
    is_skipped BOOLEAN DEFAULT FALSE,

    -- 扩展字段
    ext_json JSONB DEFAULT '{}'::jsonb,

    -- 标准审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,

    -- 唯一约束
    UNIQUE(user_id, step_id)
);

COMMENT ON TABLE user_onboarding_progress IS '用户引导进度表: 记录用户完成新手引导的进度';

-- 索引
CREATE INDEX idx_user_onboarding_progress_user_id ON user_onboarding_progress(user_id);
CREATE INDEX idx_user_onboarding_progress_step_id ON user_onboarding_progress(step_id);
CREATE INDEX idx_user_onboarding_progress_completed ON user_onboarding_progress(is_completed);

-- 复合索引
CREATE INDEX idx_user_onboarding_progress_user_step ON user_onboarding_progress(user_id, step_id);

-- 触发器
CREATE TRIGGER trg_user_onboarding_progress_updated_at
    BEFORE UPDATE ON user_onboarding_progress
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_user_onboarding_progress_soft_delete
    BEFORE UPDATE ON user_onboarding_progress
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();

-- ============================================================================
-- 第十二部分: 通知表
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 28. notifications (通知表)
-- 用户通知消息
-- ----------------------------------------------------------------------------
CREATE TABLE notifications (
    -- 主键
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 用户ID
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    -- 通知信息
    notification_type TEXT NOT NULL CHECK (notification_type IN (
        'system',
        'project',
        'marketplace',
        'payment',
        'achievement',
        'campaign'
    )),
    title TEXT NOT NULL,
    message TEXT NOT NULL,

    -- 链接
    action_url TEXT,

    -- 状态
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMPTZ,

    -- 扩展字段
    ext_json JSONB DEFAULT '{}'::jsonb,

    -- 标准审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ
);

COMMENT ON TABLE notifications IS '通知表: 用户通知消息';
COMMENT ON COLUMN notifications.notification_type IS '通知类型: system/project/marketplace/payment/achievement/campaign';

-- 索引
CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_type ON notifications(notification_type);
CREATE INDEX idx_notifications_is_read ON notifications(is_read);
CREATE INDEX idx_notifications_created_at ON notifications(created_at DESC);

-- 复合索引
CREATE INDEX idx_notifications_user_unread ON notifications(user_id, is_read, created_at DESC)
    WHERE is_read = FALSE AND is_deleted = FALSE;

-- 触发器
CREATE TRIGGER trg_notifications_updated_at
    BEFORE UPDATE ON notifications
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_notifications_soft_delete
    BEFORE UPDATE ON notifications
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();

-- ============================================================================
-- 第十三部分: 存储桶配置表
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 29. storage (存储桶配置表)
-- Supabase Storage 桶配置
-- ----------------------------------------------------------------------------
CREATE TABLE storage.buckets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    owner UUID,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    public BOOLEAN DEFAULT FALSE,
    avif_autodetection BOOLEAN DEFAULT FALSE,
    file_size_limit BIGINT,
    allowed_mime_types TEXT[]
);

COMMENT ON TABLE storage.buckets IS '存储桶配置表: Supabase Storage 桶定义';

-- 预定义存储桶
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types) VALUES
('avatars', 'avatars', TRUE, 5242880, ARRAY['image/png', 'image/jpeg', 'image/webp']),
('projects', 'projects', FALSE, 52428800, ARRAY['image/png', 'image/jpeg', 'application/json']),
('marketplace', 'marketplace', TRUE, 104857600, ARRAY['image/png', 'image/jpeg', 'image/svg+xml', 'application/pdf']),
('generations', 'generations', FALSE, 10485760, ARRAY['image/png', 'image/jpeg']);

-- ============================================================================
-- 第十四部分: 视图 (Views)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- VIEW: user_stats (用户统计视图)
-- 汇总用户的统计数据
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW user_stats AS
SELECT
    p.id AS user_id,
    p.username,
    p.tier,
    p.credits_monthly,
    p.credits_permanent,
    p.project_count,
    p.asset_count,
    COUNT(DISTINCT ug.id) AS total_generations,
    COUNT(DISTINCT mp.id) AS total_purchases,
    COUNT(DISTINCT ml.id) AS total_listings,
    COALESCE(SUM(mp.seller_revenue_credits), 0) AS total_earnings,
    p.created_at AS member_since
FROM profiles p
LEFT JOIN user_generations ug ON ug.user_id = p.id AND ug.is_deleted = FALSE
LEFT JOIN marketplace_purchases mp ON mp.seller_id = p.id AND mp.is_deleted = FALSE
LEFT JOIN marketplace_listings ml ON ml.seller_id = p.id AND ml.is_deleted = FALSE AND ml.status = 'approved'
WHERE p.is_deleted = FALSE
GROUP BY p.id;

COMMENT ON VIEW user_stats IS '用户统计视图: 汇总用户的项目、素材、生成、购买等统计数据';

-- ----------------------------------------------------------------------------
-- VIEW: marketplace_stats (市场统计视图)
-- 汇总市场素材的统计数据
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW marketplace_stats AS
SELECT
    ml.id AS listing_id,
    ml.title,
    ml.primary_category,
    ml.seller_id,
    p.username AS seller_username,
    ml.price_credits,
    ml.view_count,
    ml.download_count,
    ml.purchase_count,
    ml.favorite_count,
    ml.rating_average,
    ml.rating_count,
    COALESCE(SUM(mp.seller_revenue_credits), 0) AS total_revenue,
    ml.created_at
FROM marketplace_listings ml
LEFT JOIN profiles p ON p.id = ml.seller_id
LEFT JOIN marketplace_purchases mp ON mp.listing_id = ml.id AND mp.is_deleted = FALSE
WHERE ml.is_deleted = FALSE AND ml.status = 'approved'
GROUP BY ml.id, p.username;

COMMENT ON VIEW marketplace_stats IS '市场统计视图: 汇总市场素材的浏览、下载、购买、收益等数据';

-- ============================================================================
-- 第十五部分: 物化视图 (Materialized Views)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- MATERIALIZED VIEW: daily_revenue (每日收益物化视图)
-- 汇总每日收益数据 (用于 Dashboard)
-- ----------------------------------------------------------------------------
CREATE MATERIALIZED VIEW daily_revenue AS
SELECT
    DATE(created_at) AS date,
    COUNT(*) AS purchase_count,
    SUM(price_amount) AS total_revenue_usd,
    SUM(credits_amount) AS total_credits_sold,
    COUNT(DISTINCT user_id) AS unique_buyers
FROM credit_purchases
WHERE status = 'completed' AND is_deleted = FALSE
GROUP BY DATE(created_at)
ORDER BY date DESC;

CREATE UNIQUE INDEX idx_daily_revenue_date ON daily_revenue(date);

COMMENT ON MATERIALIZED VIEW daily_revenue IS '每日收益物化视图: 汇总每日积分购买收益';

-- 刷新函数
CREATE OR REPLACE FUNCTION refresh_daily_revenue()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY daily_revenue;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION refresh_daily_revenue() IS '刷新 daily_revenue 物化视图 (建议每小时执行一次)';

-- ----------------------------------------------------------------------------
-- MATERIALIZED VIEW: marketplace_rankings (市场排行榜物化视图)
-- 市场素材排行榜
-- ----------------------------------------------------------------------------
CREATE MATERIALIZED VIEW marketplace_rankings AS
SELECT
    ml.id,
    ml.title,
    ml.primary_category,
    ml.seller_id,
    p.username AS seller_username,
    ml.view_count,
    ml.download_count,
    ml.purchase_count,
    ml.favorite_count,
    ml.rating_average,
    ml.rating_count,
    -- 计算综合热度分数
    (
        ml.view_count * 1 +
        ml.download_count * 5 +
        ml.purchase_count * 10 +
        ml.favorite_count * 3 +
        COALESCE(ml.rating_average, 0) * ml.rating_count * 2
    ) AS popularity_score,
    ml.created_at
FROM marketplace_listings ml
LEFT JOIN profiles p ON p.id = ml.seller_id
WHERE ml.is_deleted = FALSE AND ml.status = 'approved'
ORDER BY popularity_score DESC;

CREATE UNIQUE INDEX idx_marketplace_rankings_id ON marketplace_rankings(id);

COMMENT ON MATERIALIZED VIEW marketplace_rankings IS '市场排行榜物化视图: 按综合热度排序的市场素材';

-- 刷新函数
CREATE OR REPLACE FUNCTION refresh_marketplace_rankings()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY marketplace_rankings;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION refresh_marketplace_rankings() IS '刷新 marketplace_rankings 物化视图 (建议每 15 分钟执行一次)';

-- ----------------------------------------------------------------------------
-- MATERIALIZED VIEW: user_activity_summary (用户活跃度汇总物化视图)
-- 汇总用户活跃度数据
-- ----------------------------------------------------------------------------
CREATE MATERIALIZED VIEW user_activity_summary AS
SELECT
    p.id AS user_id,
    p.username,
    p.tier,
    COUNT(DISTINCT DATE(ae.created_at)) AS active_days_30d,
    COUNT(DISTINCT CASE WHEN ae.created_at >= CURRENT_TIMESTAMP - INTERVAL '7 days' THEN DATE(ae.created_at) END) AS active_days_7d,
    COUNT(CASE WHEN ae.event_name = 'project_created' THEN 1 END) AS projects_created_30d,
    COUNT(CASE WHEN ae.event_name = 'ai_generation' THEN 1 END) AS ai_generations_30d,
    MAX(ae.created_at) AS last_active_at
FROM profiles p
LEFT JOIN analytics_events ae ON ae.user_id = p.id AND ae.created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
WHERE p.is_deleted = FALSE
GROUP BY p.id;

CREATE UNIQUE INDEX idx_user_activity_summary_user_id ON user_activity_summary(user_id);

COMMENT ON MATERIALIZED VIEW user_activity_summary IS '用户活跃度汇总物化视图: 最近 30 天的活跃度数据';

-- 刷新函数
CREATE OR REPLACE FUNCTION refresh_user_activity_summary()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY user_activity_summary;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION refresh_user_activity_summary() IS '刷新 user_activity_summary 物化视图 (建议每天执行一次)';

-- ============================================================================
-- 第十六部分: 核心业务函数
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 函数: deduct_credits_atomic (原子扣除积分)
-- 按照 月度→永久 顺序原子扣除积分
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION deduct_credits_atomic(
    p_user_id TEXT,
    p_credits_needed INTEGER,
    p_transaction_type TEXT,
    p_idempotency_key TEXT DEFAULT NULL,
    p_related_entity_type TEXT DEFAULT NULL,
    p_related_entity_id TEXT DEFAULT NULL,
    p_description TEXT DEFAULT NULL
)
RETURNS JSONB AS $$
DECLARE
    v_current_monthly INTEGER;
    v_current_permanent INTEGER;
    v_monthly_delta INTEGER := 0;
    v_permanent_delta INTEGER := 0;
    v_remaining INTEGER;
    v_user_timezone TEXT;
    v_user_local_time TIMESTAMP;
BEGIN
    -- 幂等性检查
    IF p_idempotency_key IS NOT NULL THEN
        IF EXISTS (SELECT 1 FROM credit_transactions WHERE idempotency_key = p_idempotency_key) THEN
            RAISE EXCEPTION '幂等性冲突: idempotency_key 已存在';
        END IF;
    END IF;

    -- 锁定用户行
    SELECT credits_monthly, credits_permanent, timezone
    INTO v_current_monthly, v_current_permanent, v_user_timezone
    FROM profiles
    WHERE id = p_user_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION '用户不存在: %', p_user_id;
    END IF;

    -- 计算本地时间
    v_user_local_time := CURRENT_TIMESTAMP AT TIME ZONE v_user_timezone;

    -- 检查余额
    IF v_current_monthly + v_current_permanent < p_credits_needed THEN
        RAISE EXCEPTION '积分不足: 需要 %, 当前月度=%, 永久=%',
            p_credits_needed, v_current_monthly, v_current_permanent;
    END IF;

    v_remaining := p_credits_needed;

    -- 先扣月度积分
    IF v_current_monthly > 0 THEN
        IF v_current_monthly >= v_remaining THEN
            v_monthly_delta := -v_remaining;
            v_remaining := 0;
        ELSE
            v_monthly_delta := -v_current_monthly;
            v_remaining := v_remaining - v_current_monthly;
        END IF;
    END IF;

    -- 再扣永久积分
    IF v_remaining > 0 THEN
        v_permanent_delta := -v_remaining;
    END IF;

    -- 更新用户积分
    UPDATE profiles
    SET
        credits_monthly = credits_monthly + v_monthly_delta,
        credits_permanent = credits_permanent + v_permanent_delta
    WHERE id = p_user_id;

    -- 记录交易
    INSERT INTO credit_transactions (
        user_id,
        transaction_type,
        credits_monthly_delta,
        credits_permanent_delta,
        credits_monthly_after,
        credits_permanent_after,
        idempotency_key,
        related_entity_type,
        related_entity_id,
        description,
        timezone,
        created_at_local
    ) VALUES (
        p_user_id,
        p_transaction_type,
        v_monthly_delta,
        v_permanent_delta,
        v_current_monthly + v_monthly_delta,
        v_current_permanent + v_permanent_delta,
        p_idempotency_key,
        p_related_entity_type,
        p_related_entity_id,
        p_description,
        v_user_timezone,
        v_user_local_time
    );

    RETURN jsonb_build_object(
        'success', TRUE,
        'monthly_deducted', -v_monthly_delta,
        'permanent_deducted', -v_permanent_delta,
        'monthly_after', v_current_monthly + v_monthly_delta,
        'permanent_after', v_current_permanent + v_permanent_delta
    );
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION deduct_credits_atomic IS '原子扣除积分函数: 按 月度→永久 顺序扣除，支持幂等性';

-- ----------------------------------------------------------------------------
-- 函数: add_credits_atomic (原子增加积分)
-- 原子增加积分 (月度或永久)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION add_credits_atomic(
    p_user_id TEXT,
    p_credits_monthly INTEGER DEFAULT 0,
    p_credits_permanent INTEGER DEFAULT 0,
    p_transaction_type TEXT DEFAULT 'admin_adjustment',
    p_idempotency_key TEXT DEFAULT NULL,
    p_description TEXT DEFAULT NULL
)
RETURNS JSONB AS $$
DECLARE
    v_current_monthly INTEGER;
    v_current_permanent INTEGER;
    v_user_timezone TEXT;
    v_user_local_time TIMESTAMP;
BEGIN
    -- 幂等性检查
    IF p_idempotency_key IS NOT NULL THEN
        IF EXISTS (SELECT 1 FROM credit_transactions WHERE idempotency_key = p_idempotency_key) THEN
            RAISE EXCEPTION '幂等性冲突: idempotency_key 已存在';
        END IF;
    END IF;

    -- 锁定用户行
    SELECT credits_monthly, credits_permanent, timezone
    INTO v_current_monthly, v_current_permanent, v_user_timezone
    FROM profiles
    WHERE id = p_user_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION '用户不存在: %', p_user_id;
    END IF;

    -- 计算本地时间
    v_user_local_time := CURRENT_TIMESTAMP AT TIME ZONE v_user_timezone;

    -- 更新用户积分
    UPDATE profiles
    SET
        credits_monthly = credits_monthly + p_credits_monthly,
        credits_permanent = credits_permanent + p_credits_permanent
    WHERE id = p_user_id;

    -- 记录交易
    INSERT INTO credit_transactions (
        user_id,
        transaction_type,
        credits_monthly_delta,
        credits_permanent_delta,
        credits_monthly_after,
        credits_permanent_after,
        idempotency_key,
        description,
        timezone,
        created_at_local
    ) VALUES (
        p_user_id,
        p_transaction_type,
        p_credits_monthly,
        p_credits_permanent,
        v_current_monthly + p_credits_monthly,
        v_current_permanent + p_credits_permanent,
        p_idempotency_key,
        p_description,
        v_user_timezone,
        v_user_local_time
    );

    RETURN jsonb_build_object(
        'success', TRUE,
        'monthly_added', p_credits_monthly,
        'permanent_added', p_credits_permanent,
        'monthly_after', v_current_monthly + p_credits_monthly,
        'permanent_after', v_current_permanent + p_credits_permanent
    );
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION add_credits_atomic IS '原子增加积分函数: 增加月度或永久积分，支持幂等性';

-- ----------------------------------------------------------------------------
-- 函数: execute_marketplace_purchase (执行市场购买)
-- 执行市场素材购买，包含积分扣除和收益分成
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION execute_marketplace_purchase(
    p_buyer_id TEXT,
    p_listing_id UUID,
    p_idempotency_key TEXT
)
RETURNS JSONB AS $$
DECLARE
    v_listing RECORD;
    v_price INTEGER;
    v_seller_revenue INTEGER;
    v_platform_fee INTEGER;
    v_deduct_result JSONB;
BEGIN
    -- 幂等性检查
    IF EXISTS (SELECT 1 FROM marketplace_purchases WHERE idempotency_key = p_idempotency_key) THEN
        RAISE EXCEPTION '幂等性冲突: 已购买过此素材';
    END IF;

    -- 检查是否已购买
    IF EXISTS (SELECT 1 FROM marketplace_purchases WHERE buyer_id = p_buyer_id AND listing_id = p_listing_id) THEN
        RAISE EXCEPTION '重复购买: 您已购买过此素材';
    END IF;

    -- 获取素材信息
    SELECT * INTO v_listing
    FROM marketplace_listings
    WHERE id = p_listing_id AND is_deleted = FALSE AND status = 'approved'
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION '素材不存在或未上架';
    END IF;

    -- 检查价格类型
    IF v_listing.price_type = 'free' THEN
        v_price := 0;
        v_seller_revenue := 0;
        v_platform_fee := 0;
    ELSE
        v_price := v_listing.price_credits;
        v_seller_revenue := FLOOR(v_price * 0.9);  -- 90% 给卖家
        v_platform_fee := v_price - v_seller_revenue;  -- 10% 平台费
    END IF;

    -- 扣除买家积分
    IF v_price > 0 THEN
        v_deduct_result := deduct_credits_atomic(
            p_buyer_id,
            v_price,
            'marketplace_purchase',
            p_idempotency_key,
            'listing',
            p_listing_id::TEXT,
            FORMAT('购买素材: %s', v_listing.title)
        );

        -- 给卖家增加收益
        PERFORM add_credits_atomic(
            v_listing.seller_id,
            0,  -- 月度积分
            v_seller_revenue,  -- 永久积分
            'marketplace_sale',
            p_idempotency_key || ':seller',
            FORMAT('出售素材: %s', v_listing.title)
        );
    END IF;

    -- 记录购买
    INSERT INTO marketplace_purchases (
        buyer_id,
        seller_id,
        listing_id,
        price_credits,
        seller_revenue_credits,
        platform_fee_credits,
        idempotency_key
    ) VALUES (
        p_buyer_id,
        v_listing.seller_id,
        p_listing_id,
        v_price,
        v_seller_revenue,
        v_platform_fee,
        p_idempotency_key
    );

    RETURN jsonb_build_object(
        'success', TRUE,
        'price', v_price,
        'seller_revenue', v_seller_revenue,
        'platform_fee', v_platform_fee
    );
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION execute_marketplace_purchase IS '执行市场购买函数: 扣除积分并分成 (90%卖家/10%平台)';

-- ============================================================================
-- 完成
-- ============================================================================

-- 统计信息
DO $$
DECLARE
    table_count INTEGER;
    index_count INTEGER;
    trigger_count INTEGER;
    function_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count FROM information_schema.tables
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE';

    SELECT COUNT(*) INTO index_count FROM pg_indexes
    WHERE schemaname = 'public';

    SELECT COUNT(*) INTO trigger_count FROM information_schema.triggers
    WHERE trigger_schema = 'public';

    SELECT COUNT(*) INTO function_count FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname = 'public' AND p.prokind = 'f';

    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'Make Decodables - Refactored Schema v4.0 已完成';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE '统计信息:';
    RAISE NOTICE '- 表数量: %', table_count;
    RAISE NOTICE '- 索引数量: %', index_count;
    RAISE NOTICE '- 触发器数量: %', trigger_count;
    RAISE NOTICE '- 函数数量: %', function_count;
    RAISE NOTICE '============================================================================';
END $$;
