-- ============================================================================
-- Make Decodables - 数据库架构 (文件 1/3)
-- ============================================================================
-- 分类: 核心业务
-- 说明: 用户、积分、项目、素材、市场、Workspace、Tag
-- 执行顺序: 第 1 个执行
-- 生成时间: 2026-01-10
-- 更新时间: 2026-01-28 (v3.33 Phase 2.6: Folder + Star)
--
-- v3.33 变更:
--   Phase 0:
--   - profiles: 新增 trial_extended_days 字段
--   - 新增 workspaces 表 (用户 Workspace)
--   - 新增 tags 表 (用户级标签，替代旧系统级标签)
--   - 新增 tag_group_presets 表 (标签分组预设)
--   - 新增 project_tags 表 (项目-标签关联)
--   - 新增 user_asset_tags 表 (素材-标签关联)
--   - projects/assets: 新增 workspace_id 字段
--   - asset_tags -> legacy_system_tags (已废弃)
--   - asset_tag_relations -> legacy_asset_tag_relations (已废弃)
--   Phase 2.6:
--   - 新增 folders 表 (文件夹系统，支持 8 色标记)
--   - projects: 新增 folder_id, is_starred 字段
--   - assets: 新增 folder_id, is_starred 字段
-- ============================================================================

-- 开始事务
BEGIN;

-- 创建 internal schema (运维视图专用，PostgREST 不暴露)
CREATE SCHEMA IF NOT EXISTS internal;

-- ============================================================================
-- 启用必要的 PostgreSQL 扩展
-- ============================================================================
-- uuid-ossp 扩展已移除: 全部改用 PostgreSQL 14+ 内置 gen_random_uuid() (无需扩展依赖)
CREATE EXTENSION IF NOT EXISTS "ltree" SCHEMA extensions;  -- 层级树结构支持 (用于 asset_categories)
CREATE EXTENSION IF NOT EXISTS "pg_trgm";         -- WS-19: Trigram 索引支持 (模糊搜索优化)

-- ============================================================================
-- 辅助函数 (需要先创建)
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql
SET search_path = 'public';

-- ============================================================================
-- 表创建顺序 (按依赖关系排列)
-- ============================================================================
-- 第一层: 无外键依赖的基础表
--   1. profiles
--   2. asset_categories
--   3. workspaces (v3.33 新增，依赖 profiles)
--   4. legacy_system_tags (原 asset_tags，已废弃)
--   5. tags (v3.33 新增，依赖 workspaces)
--   6. tag_group_presets (v3.33 新增)
--
-- 第二层: 依赖第一层的表
--   7. projects (依赖 profiles, workspaces)
--   8. marketplace_listings (依赖 profiles)
--
-- 第三层: 依赖第一、二层的表
--   9. assets (依赖 profiles, projects, marketplace_listings, workspaces)
--   10. legacy_asset_tag_relations (原 asset_tag_relations，已废弃)
--   11. project_tags (v3.33 新增)
--   12. user_asset_tags (v3.33 新增)
--   ... 其他表


-- ============================================================================
-- 第一层: 基础表 (无外键依赖)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. profiles (用户表 - 最基础的表)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS profiles (
    -- 主键 (UUID，自建认证系统)
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 基础信息
    email TEXT NOT NULL,  -- 唯一性由部分索引 idx_profiles_email_unique (WHERE is_deleted=false) 保证
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

    -- 用户等级 (系统代码: t1/t2/t3/t4, 显示名称可通过 system_configs 配置)
    tier TEXT NOT NULL DEFAULT 't1' CHECK (tier IN ('t1', 't2', 't3', 't4')),
    tier_changed_at TIMESTAMPTZ,

    -- 积分余额 (核心字段!)
    credits_monthly INTEGER NOT NULL DEFAULT 0 CHECK (credits_monthly >= 0 AND credits_monthly <= 1000000),  -- 上限 1M 月度积分
    credits_permanent INTEGER NOT NULL DEFAULT 0 CHECK (credits_permanent >= 0 AND credits_permanent <= 10000000),  -- 上限 10M 永久积分
    credits_reset_at TIMESTAMPTZ,  -- P0-2: 月度积分重置时间

    -- 试用期
    trial_start_date TIMESTAMPTZ,
    trial_end_date TIMESTAMPTZ,
    is_trial_active BOOLEAN DEFAULT FALSE,
    trial_extended_days INTEGER DEFAULT 0 CHECK (trial_extended_days >= 0),  -- v3.33: Admin 可延长的试用天数

    -- Stripe 相关
    stripe_customer_id TEXT UNIQUE,
    stripe_subscription_id TEXT,
    subscription_status TEXT CHECK (subscription_status IN ('active', 'canceled', 'past_due', 'incomplete', 'trialing', 'inactive')),
    subscription_current_period_start TIMESTAMPTZ,
    subscription_current_period_end TIMESTAMPTZ,

    -- 取消/降级状态 (WS4: 期末取消/降级追踪)
    cancel_at_period_end BOOLEAN NOT NULL DEFAULT FALSE,  -- 标记期末取消状态
    cancel_at TIMESTAMPTZ,  -- 期末取消的具体时间点 (Stripe current_period_end)
    pending_tier_change TEXT DEFAULT NULL CHECK (pending_tier_change IS NULL OR pending_tier_change IN ('t1', 't2', 't3')),  -- 期末降级目标 tier

    -- 订阅暂停追踪 (ALTER-003: Phase 1 预置列, Phase 2/3 使用)
    is_paused BOOLEAN NOT NULL DEFAULT FALSE,
    paused_at TIMESTAMPTZ,
    pause_metadata JSONB DEFAULT '{}'::jsonb,  -- {pause_reason, auto_resume_date, max_pause_days}

    -- 偏好设置
    language TEXT DEFAULT 'en' CHECK (language IN ('en', 'zh', 'es', 'fr', 'de', 'ja', 'ko')),
    timezone TEXT DEFAULT 'UTC',
    notification_email_enabled BOOLEAN DEFAULT TRUE,
    notification_product_enabled BOOLEAN DEFAULT TRUE,

    -- Onboarding 状态 (P0-4: Repository 使用的字段)
    onboarding_step TEXT DEFAULT 'not_started' CHECK (onboarding_step IN (
        'not_started', 'welcome', 'profile_setup', 'first_project', 'completed'
    )),

    -- 用户角色 (v3.32: 用于区分普通用户和管理员)
    role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),

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
    created_by TEXT DEFAULT 'register' CHECK (created_by IN ('register', 'admin', 'legacy', 'oauth')),
    
    -- 标准审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    email_hash TEXT,  -- SHA-256(email)，账户删除时写入，用于去重分析和 GDPR 合规准备
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


-- ============================================================================
-- 1.5 Auth Tables (认证系统 - 自建 Email+Password)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1.5.1 auth_users (认证凭据，与 profiles 分离)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auth_users (
    -- 主键 (与 profiles.id 共享同一 UUID)
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 邮箱 (统一小写存储)
    email TEXT NOT NULL UNIQUE,
    CONSTRAINT check_email_lowercase CHECK (email = LOWER(email)),

    -- 密码 (argon2id 哈希，注册 OTP 验证阶段为 NULL，完成注册后才有值)
    password_hash TEXT,

    -- 邮箱验证
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    email_verified_at TIMESTAMPTZ,

    -- OTP 统一字段（所有场景共用：注册/修改密码/删除账户/忘记密码）
    -- 通过 otp_purpose 区分用途，同一用户同一时间只有一个活跃 OTP
    otp_code_hash TEXT,                     -- SHA-256 哈希值，不存明文
    otp_purpose TEXT CHECK (otp_purpose IS NULL OR otp_purpose IN (
        'register', 'change_password', 'delete_account', 'forgot_password'
    )),
    otp_expires_at TIMESTAMPTZ,
    otp_attempts INTEGER NOT NULL DEFAULT 0 CHECK (otp_attempts >= 0),  -- 最多 5 次尝试

    -- 密码变更追踪
    password_changed_at TIMESTAMPTZ,

    -- 登录安全
    failed_login_attempts INTEGER NOT NULL DEFAULT 0 CHECK (failed_login_attempts >= 0),
    locked_until TIMESTAMPTZ,
    last_login_at TIMESTAMPTZ,
    last_login_ip INET,

    -- 状态
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    -- 审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 部分索引：仅对有 OTP 的行建索引（大部分行 OTP 为 NULL）
CREATE INDEX IF NOT EXISTS idx_auth_users_otp
    ON auth_users(otp_code_hash)
    WHERE otp_code_hash IS NOT NULL;

-- 锁定用户索引（查询被锁定的账户）
CREATE INDEX IF NOT EXISTS idx_auth_users_locked
    ON auth_users(locked_until)
    WHERE locked_until IS NOT NULL;

-- RLS
ALTER TABLE auth_users ENABLE ROW LEVEL SECURITY;
CREATE POLICY service_role_full_access ON auth_users
    FOR ALL TO service_role
    USING (true) WITH CHECK (true);


-- ----------------------------------------------------------------------------
-- 1.5.2 auth_sessions (Refresh Token 存储 + 轮换检测)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auth_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 用户关联
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,

    -- 轮换链标识（同一登录链共享 family_id）
    family_id UUID NOT NULL,

    -- Refresh Token（SHA-256 哈希，不存明文）
    refresh_token_hash TEXT NOT NULL UNIQUE,

    -- 设备信息
    user_agent TEXT,
    ip_address INET,
    device_name TEXT,                       -- 从 user_agent 解析，用于展示

    -- 作废状态
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
    revoked_at TIMESTAMPTZ,
    revoke_reason TEXT CHECK (revoke_reason IS NULL OR revoke_reason IN (
        'logout', 'rotation', 'security', 'admin', 'account_deleted',
        'session_limit_exceeded'
    )),

    -- 生命周期
    expires_at TIMESTAMPTZ NOT NULL,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 查询用户活跃会话
CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_active
    ON auth_sessions(user_id, is_revoked, expires_at)
    WHERE is_revoked = FALSE;

-- 按 family_id 查询（重用检测时需要作废整个 family）
CREATE INDEX IF NOT EXISTS idx_auth_sessions_family
    ON auth_sessions(family_id);

-- 过期会话清理索引
CREATE INDEX IF NOT EXISTS idx_auth_sessions_expired
    ON auth_sessions(expires_at)
    WHERE is_revoked = FALSE;

-- RLS
ALTER TABLE auth_sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY service_role_full_access ON auth_sessions
    FOR ALL TO service_role
    USING (true) WITH CHECK (true);


-- ----------------------------------------------------------------------------
-- 1.5.3 auth_oauth_accounts (预留 OAuth 扩展)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auth_oauth_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 用户关联
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,

    -- OAuth 提供商
    provider TEXT NOT NULL CHECK (provider IN ('google', 'github', 'apple')),
    provider_user_id TEXT NOT NULL,
    provider_email TEXT,

    -- OAuth Token（加密存储）
    access_token_encrypted TEXT,
    refresh_token_encrypted TEXT,
    token_expires_at TIMESTAMPTZ,

    -- 额外数据
    provider_data JSONB DEFAULT '{}'::jsonb,

    -- 审计字段
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- 约束：每个第三方账号只能绑一个用户
    CONSTRAINT uq_oauth_provider_user UNIQUE (provider, provider_user_id),
    -- 约束：每个用户每个平台只能绑一个
    CONSTRAINT uq_oauth_user_provider UNIQUE (user_id, provider)
);

-- RLS
ALTER TABLE auth_oauth_accounts ENABLE ROW LEVEL SECURITY;
CREATE POLICY service_role_full_access ON auth_oauth_accounts
    FOR ALL TO service_role
    USING (true) WITH CHECK (true);


-- ----------------------------------------------------------------------------
-- 2. asset_categories (素材分类 - 自引用)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS asset_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

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
-- 3. workspaces (工作区 - v3.33 Phase 0)
-- 说明: 用户 Workspace，一期只支持 Personal Workspace (用户默认拥有一个)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 基础信息
    name TEXT NOT NULL,
    description TEXT,

    -- 所有者 (Clerk user_id)
    owner_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    -- 配置 (一期简化: 全部为 TRUE)
    is_default BOOLEAN DEFAULT TRUE,        -- 是否为用户的默认 workspace
    is_personal BOOLEAN DEFAULT TRUE,       -- 是否为个人 workspace (vs 团队)

    -- 状态
    is_active BOOLEAN DEFAULT TRUE,

    -- 标准审计字段 (WS-1: 1C#29 NOT NULL DEFAULT)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_workspaces_owner ON workspaces(owner_id);
CREATE INDEX IF NOT EXISTS idx_workspaces_default ON workspaces(owner_id, is_default) WHERE is_default = TRUE;

-- 唯一约束: 每个用户只能有一个 active 的 default workspace
-- 防止并发创建导致的重复 workspace 问题
CREATE UNIQUE INDEX IF NOT EXISTS idx_workspaces_one_default_per_owner
ON workspaces(owner_id) WHERE is_default = TRUE AND is_active = TRUE;

-- 触发器: 更新 updated_at
DROP TRIGGER IF EXISTS update_workspaces_updated_at ON workspaces;
CREATE TRIGGER update_workspaces_updated_at
    BEFORE UPDATE ON workspaces
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ----------------------------------------------------------------------------
-- 3.1 folders (文件夹 - v3.33 Phase 2.6)
-- 说明: Project/Asset 共用的文件夹系统，支持 8 色标记
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS folders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 归属 Workspace
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,

    -- 文件夹类型 (区分 Project 文件夹和 Asset 文件夹)
    folder_type TEXT NOT NULL CHECK (folder_type IN ('project', 'asset')),

    -- 基础信息
    name TEXT NOT NULL,
    color TEXT DEFAULT 'slate' CHECK (color IN ('slate', 'red', 'orange', 'amber', 'emerald', 'cyan', 'blue', 'violet')),

    -- 排序
    sort_order INTEGER DEFAULT 0,

    -- 创建者
    created_by UUID NOT NULL REFERENCES profiles(id),

    -- 时间戳 (WS-1: 1C#29 NOT NULL DEFAULT)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- 唯一约束: 同一 Workspace 内同类型文件夹名称唯一
    UNIQUE (workspace_id, folder_type, name)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_folders_workspace_type ON folders(workspace_id, folder_type);

-- 触发器
DROP TRIGGER IF EXISTS update_folders_updated_at ON folders;
CREATE TRIGGER update_folders_updated_at
    BEFORE UPDATE ON folders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ----------------------------------------------------------------------------
-- 4. legacy_system_tags (旧系统级标签 - 已废弃，保留兼容)
-- 注意: 此表已废弃，新标签系统使用 tags 表 (用户级标签)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS legacy_system_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL,
    slug VARCHAR(50) UNIQUE NOT NULL,
    name_i18n JSONB DEFAULT '{}'::JSONB,
    tag_type VARCHAR(20) DEFAULT 'general' CHECK (tag_type IN ('general', 'color', 'style', 'theme', 'season')),
    usage_count INT DEFAULT 0 CHECK (usage_count >= 0),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_legacy_system_tags_type ON legacy_system_tags(tag_type);
CREATE INDEX IF NOT EXISTS idx_legacy_system_tags_usage ON legacy_system_tags(usage_count DESC);
CREATE INDEX IF NOT EXISTS idx_legacy_system_tags_name ON legacy_system_tags(name);

DROP TRIGGER IF EXISTS update_legacy_system_tags_updated_at ON legacy_system_tags;
CREATE TRIGGER update_legacy_system_tags_updated_at
    BEFORE UPDATE ON legacy_system_tags
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ----------------------------------------------------------------------------
-- 5. tags (用户级标签 - v3.33 新标签系统)
-- 说明: 标签归属于 Workspace，每个用户通过 Workspace 管理自己的标签
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 归属 Workspace
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,

    -- 标签信息
    name TEXT NOT NULL,
    color TEXT DEFAULT 'gray' CHECK (color IN ('gray', 'red', 'orange', 'yellow', 'green', 'blue', 'purple', 'pink')),
    icon TEXT,                              -- emoji 或 icon name

    -- 标签分组
    group_name TEXT,                        -- 如: "grade_level", "phonics_pattern"

    -- 排序
    sort_order INTEGER DEFAULT 0,

    -- 创建者
    created_by UUID NOT NULL REFERENCES profiles(id),

    -- 状态
    is_active BOOLEAN DEFAULT TRUE,

    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- 唯一约束: 同一 Workspace 内标签名唯一
    UNIQUE (workspace_id, name)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_tags_workspace ON tags(workspace_id);
CREATE INDEX IF NOT EXISTS idx_tags_group ON tags(workspace_id, group_name);
CREATE INDEX IF NOT EXISTS idx_tags_active ON tags(workspace_id, is_active) WHERE is_active = TRUE;

-- 触发器
DROP TRIGGER IF EXISTS update_tags_updated_at ON tags;
CREATE TRIGGER update_tags_updated_at
    BEFORE UPDATE ON tags
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ----------------------------------------------------------------------------
-- 6. tag_group_presets (标签分组预设 - 系统级模板)
-- 说明: 系统预定义的标签分组模板，新用户创建 Workspace 时自动应用
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tag_group_presets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    group_name TEXT NOT NULL UNIQUE,        -- 内部名称 (如 'grade_level')
    display_name TEXT NOT NULL,             -- 显示名称 (如 'Grade Level')
    description TEXT,
    icon TEXT,                              -- emoji

    preset_tags JSONB DEFAULT '[]',         -- 预设标签数组: [{"name": "Grade 1", "color": "blue"}, ...]
    is_default BOOLEAN DEFAULT FALSE,       -- 是否默认应用到新 Workspace
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_tag_group_presets_default ON tag_group_presets(is_default) WHERE is_default = TRUE;

-- 触发器
DROP TRIGGER IF EXISTS update_tag_group_presets_updated_at ON tag_group_presets;
CREATE TRIGGER update_tag_group_presets_updated_at
    BEFORE UPDATE ON tag_group_presets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ============================================================================
-- 第二层: 依赖 profiles 的表
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 4. projects (项目表)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 用户ID (P0-8: Repository 同时使用 user_id 和 owner_id)
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    -- v3.33: Workspace 关联 (可空，向后兼容现有项目)
    workspace_id UUID REFERENCES workspaces(id) ON DELETE SET NULL,

    -- v3.33 Phase 2.6: 文件夹和收藏
    folder_id UUID REFERENCES folders(id) ON DELETE SET NULL,
    is_starred BOOLEAN DEFAULT FALSE,

    -- 项目信息
    title TEXT NOT NULL DEFAULT 'My Magic Story',
    description TEXT,  -- P0-8: Repository 使用的字段
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],  -- P0-8: Repository 使用的字段
    canvas_data JSONB DEFAULT '{}'::jsonb,  -- WS-1(1C#24): 应用层限制 canvas_data 大小 ≤ 5MB，DB 不加 CHECK 以避免性能影响
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
    -- WS-1(1C#25): marketplace_listing_id 引用 marketplace_listings(id)，未加 FK 因该表在 02_platform_services.sql
    marketplace_listing_id UUID,
    -- WS-1(1C#26): source_listing_id 引用 marketplace_listings(id)，表示项目来源 listing
    source_listing_id UUID,
    is_purchased BOOLEAN DEFAULT FALSE,
    origin_owner_id UUID REFERENCES profiles(id),
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

    -- v2.1.0: Idempotency support for safe retry
    -- Client-generated UUID, unique per user to prevent duplicate creation
    idempotency_key TEXT,

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

-- WS-1: RLS 纵深防御 (1C#18)
-- authenticated 用户只能访问自己的项目; service_role 保持全量访问
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

CREATE POLICY projects_owner_policy ON projects
    FOR ALL
    TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- service_role 全量访问策略 (后端 API 使用 service_role key)
CREATE POLICY projects_service_role_policy ON projects
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- WS-1: canvas_size 格式约束 (1C#22) — 必须为 NxN 格式
ALTER TABLE projects ADD CONSTRAINT chk_projects_canvas_size_format
    CHECK (canvas_size IS NULL OR canvas_size ~ '^\d{1,5}x\d{1,5}$');

-- WS-1: listing_status 枚举约束 (1C#27)
ALTER TABLE projects ADD CONSTRAINT chk_projects_listing_status
    CHECK (listing_status IS NULL OR listing_status IN ('draft', 'pending', 'published', 'rejected', 'removed'));

-- P0-8: 为 Repository 兼容创建 owner_id 作为 user_id 的别名视图
-- 注意: Repository 可能使用 owner_id 或 user_id，此视图确保两者都可用
-- 命名规范: 视图统一使用 v_ 前缀
DROP VIEW IF EXISTS projects_v CASCADE;  -- 删除旧视图名
CREATE OR REPLACE VIEW v_projects
WITH (security_invoker = true) AS
SELECT
    *,
    user_id AS owner_id  -- 别名
FROM projects;

-- WS-19: Auto-update updated_at on projects modification
DROP TRIGGER IF EXISTS update_projects_updated_at ON projects;
CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ----------------------------------------------------------------------------
-- 4.1 project_pages (项目页面 - P0-9: Repository 使用但之前缺失的表)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS project_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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

CREATE INDEX IF NOT EXISTS idx_project_pages_project ON project_pages(project_id, page_number);


-- ----------------------------------------------------------------------------
-- 5. marketplace_listings (市场列表)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS marketplace_listings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id TEXT UNIQUE NOT NULL DEFAULT gen_random_uuid()::text,  -- 业务 ID (Repository 使用)
    seller_id UUID REFERENCES profiles(id),

    -- 基本信息
    title TEXT NOT NULL,
    description TEXT,
    thumbnail_url TEXT,  -- P0-10: 改为可空，创建后通过 update 设置
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],  -- P0-10: Repository 使用的字段

    -- 资源信息
    resource_url TEXT,  -- P0-10: 改为可空，创建后通过 update 设置
    resource_type TEXT NOT NULL CHECK (resource_type IN ('project', 'asset')),
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
    like_count INTEGER DEFAULT 0,  -- P0-10: Repository 使用的字段 (收藏/喜欢数)
    purchase_count INTEGER DEFAULT 0,  -- P0-10: Repository 使用的字段 (购买次数)
    rating_average NUMERIC(3,2) DEFAULT 0,  -- P0-10: Repository 使用的字段
    rating_count INTEGER DEFAULT 0,  -- P0-10: Repository 使用的字段

    -- 状态 (P0-10: 添加 status 字段供 Repository 使用)
    -- 与代码 ListingStatus enum 保持一致: draft, pending, published, rejected, suspended, archived
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'pending', 'published', 'rejected', 'suspended', 'archived')),
    is_public BOOLEAN DEFAULT FALSE,
    is_featured BOOLEAN DEFAULT FALSE,  -- 是否精选/推荐 (由管理员设置)
    allow_preview BOOLEAN DEFAULT TRUE,  -- 是否允许购买前预览 (卖家设置)
    moderation_status TEXT NOT NULL DEFAULT 'draft' CHECK (moderation_status IN ('draft', 'pending', 'approved', 'rejected')),
    moderation_note TEXT,
    rejection_reason TEXT,  -- P0-10: Repository 使用的字段 (拒绝原因)
    moderated_by UUID REFERENCES profiles(id),
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
CREATE TABLE IF NOT EXISTS assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id),

    -- v3.33: Workspace 关联 (可空，向后兼容现有素材)
    workspace_id UUID REFERENCES workspaces(id) ON DELETE SET NULL,

    -- v3.33 Phase 2.6: 文件夹和收藏
    folder_id UUID REFERENCES folders(id) ON DELETE SET NULL,
    is_starred BOOLEAN DEFAULT FALSE,

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
    origin_owner_id UUID REFERENCES profiles(id),
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

-- v3.33: Workspace index for filtering assets by workspace
CREATE INDEX IF NOT EXISTS idx_assets_workspace
ON assets(workspace_id)
WHERE workspace_id IS NOT NULL;

-- v3.33 Phase 2.6: Folder and Star indexes for assets
CREATE INDEX IF NOT EXISTS idx_assets_folder
ON assets(folder_id)
WHERE folder_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_assets_starred
ON assets(user_id, is_starred)
WHERE is_starred = TRUE;


-- ----------------------------------------------------------------------------
-- 7. legacy_asset_tag_relations (旧素材-标签关联 - 已废弃)
-- 注意: 此表已废弃，新标签系统使用 project_tags 和 user_asset_tags
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS legacy_asset_tag_relations (
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES legacy_system_tags(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (asset_id, tag_id)
);

CREATE INDEX IF NOT EXISTS idx_legacy_asset_tag_rel_asset ON legacy_asset_tag_relations(asset_id);
CREATE INDEX IF NOT EXISTS idx_legacy_asset_tag_rel_tag ON legacy_asset_tag_relations(tag_id);


-- ----------------------------------------------------------------------------
-- 7.1 project_tags (项目-标签关联 - v3.33 新标签系统)
-- 说明: 项目与用户标签的多对多关联
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS project_tags (
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,

    added_by UUID NOT NULL REFERENCES profiles(id),
    added_at TIMESTAMPTZ DEFAULT NOW(),

    PRIMARY KEY (project_id, tag_id)
);

CREATE INDEX IF NOT EXISTS idx_project_tags_project ON project_tags(project_id);
CREATE INDEX IF NOT EXISTS idx_project_tags_tag ON project_tags(tag_id);


-- ----------------------------------------------------------------------------
-- 7.2 user_asset_tags (用户素材-标签关联 - v3.33 新标签系统)
-- 说明: 用户素材与用户标签的多对多关联，支持 AI 推荐来源标记
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_asset_tags (
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,

    added_by UUID NOT NULL REFERENCES profiles(id),
    added_at TIMESTAMPTZ DEFAULT NOW(),

    -- 来源标记 (区分手动添加 vs AI 推荐)
    source TEXT DEFAULT 'manual' CHECK (source IN ('manual', 'ai_recommended')),

    PRIMARY KEY (asset_id, tag_id)
);

CREATE INDEX IF NOT EXISTS idx_user_asset_tags_asset ON user_asset_tags(asset_id);
CREATE INDEX IF NOT EXISTS idx_user_asset_tags_tag ON user_asset_tags(tag_id);


-- ----------------------------------------------------------------------------
-- 8. user_recent_assets (用户最近使用素材)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_recent_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    used_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_recent_asset UNIQUE(user_id, asset_id)
);

CREATE INDEX IF NOT EXISTS idx_user_recent_user ON user_recent_assets(user_id, used_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_recent_asset ON user_recent_assets(asset_id);


-- ----------------------------------------------------------------------------
-- 9. user_favorite_assets (用户收藏素材)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_favorite_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_favorite_asset UNIQUE(user_id, asset_id)
);

CREATE INDEX IF NOT EXISTS idx_user_favorite_user ON user_favorite_assets(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_favorite_asset ON user_favorite_assets(asset_id);


-- ----------------------------------------------------------------------------
-- 10. project_versions (项目版本)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS project_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    canvas_data JSONB NOT NULL,
    thumbnail_url TEXT,
    change_description TEXT,
    created_by UUID NOT NULL REFERENCES profiles(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, version_number)
);


-- ----------------------------------------------------------------------------
-- 11. user_asset_prompt_templates (用户素材提示词模板)
-- User-created prompt templates for asset/image AI generation (5W1H)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_asset_prompt_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
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
    CONSTRAINT chk_uapt_deleted_at_consistency
        CHECK ((is_deleted = false AND deleted_at IS NULL) OR (is_deleted = true AND deleted_at IS NOT NULL)),
    CONSTRAINT chk_uapt_recovery_expires_at_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);


-- ----------------------------------------------------------------------------
-- 12. credit_purchases (积分购买记录)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS credit_purchases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
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
CREATE TABLE IF NOT EXISTS credit_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    -- 交易类型 (P0-6: 同时支持 transaction_type 和 tx_type)
    -- transaction_type: 规范字段名 (用于报表、管理、RPC 函数)
    -- tx_type: ⚠️ DEPRECATED — Repository 历史遗留字段，新代码应使用 transaction_type
    --   触发器 trg_sync_credit_transaction_type 自动双向同步两个字段
    -- 至少一个必须有值，两个都有值时必须相同
    -- ALTER-009 Phase 1 宽松版: 同时允许旧名(16) + 新名(19) = 29 种合集
    -- Phase 2 代码对齐后收紧为仅 19 种 TARGET 名称
    -- Phase 2 ALTER-009 收紧: 仅允许 19 种 TARGET 类型 (见 SPEC §5 ENUM-002)
    -- 增加 (+10): subscription_grant, credit_purchase, bonus_signup_grant, bonus_referral_grant, bonus_campaign_grant,
    --             compensation_grant, promotion_grant, marketplace_earning, admin_adjustment, manual_correction
    -- 减少 (-6):  credit_consume, marketplace_purchase, credits_expired, monthly_credits_cleared, refund_reversal, chargeback_reversal
    -- 重置 (=3):  monthly_reset, subscription_upgrade, subscription_downgrade
    transaction_type TEXT CHECK (transaction_type IN (
        -- 增加 (+amount) — 10 types
        'subscription_grant', 'credit_purchase',
        'bonus_signup_grant', 'bonus_referral_grant', 'bonus_campaign_grant',
        'compensation_grant', 'promotion_grant', 'marketplace_earning',
        'admin_adjustment', 'manual_correction',
        -- 减少 (-amount) — 6 types
        'credit_consume', 'marketplace_purchase',
        'credits_expired', 'monthly_credits_cleared',
        'refund_reversal', 'chargeback_reversal',
        -- 重置/调整 (=) — 3 types
        'monthly_reset', 'subscription_upgrade', 'subscription_downgrade'
    )),
    -- ⚠️ DEPRECATED: tx_type 已废弃，新代码请使用 transaction_type
    -- 保留仅为向后兼容，触发器自动同步值; 仍允许旧值 (已有数据兼容)
    tx_type TEXT CHECK (tx_type IN (
        -- TARGET 19 types (same as transaction_type)
        'subscription_grant', 'credit_purchase',
        'bonus_signup_grant', 'bonus_referral_grant', 'bonus_campaign_grant',
        'compensation_grant', 'promotion_grant', 'marketplace_earning',
        'admin_adjustment', 'manual_correction',
        'credit_consume', 'marketplace_purchase',
        'credits_expired', 'monthly_credits_cleared',
        'refund_reversal', 'chargeback_reversal',
        'monthly_reset', 'subscription_upgrade', 'subscription_downgrade',
        -- LEGACY (旧数据兼容, 新代码不使用)
        'purchase', 'ai_generation', 'smart_scan', 'refund',
        'signup_bonus', 'referral_bonus', 'campaign_reward',
        'expiration', 'topup_purchase', 'sub_grant'
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
$$ LANGUAGE plpgsql
SET search_path = 'public';

DROP TRIGGER IF EXISTS trg_sync_credit_transaction_type ON credit_transactions;
CREATE TRIGGER trg_sync_credit_transaction_type
    BEFORE INSERT OR UPDATE ON credit_transactions
    FOR EACH ROW
    EXECUTE FUNCTION sync_credit_transaction_type();

-- WS3: 幂等性 UNIQUE 部分索引 — 防止并发重复写入
CREATE UNIQUE INDEX IF NOT EXISTS idx_credit_transactions_idempotency_key
    ON credit_transactions(idempotency_key)
    WHERE idempotency_key IS NOT NULL;


-- ----------------------------------------------------------------------------
-- 14. generation_tasks (AI生成任务)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS generation_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
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
            'image_generation',
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

CREATE INDEX IF NOT EXISTS idx_generation_tasks_user_id ON generation_tasks(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_generation_tasks_project_id ON generation_tasks(project_id) WHERE project_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_generation_tasks_status ON generation_tasks(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_generation_tasks_task_type ON generation_tasks(task_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_generation_tasks_created_at ON generation_tasks(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_generation_tasks_pending ON generation_tasks(created_at ASC) WHERE status = 'pending';


-- ----------------------------------------------------------------------------
-- 15. listing_usages (市场使用记录)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS listing_usages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID NOT NULL REFERENCES marketplace_listings(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_listing_usages_listing_id ON listing_usages(listing_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_listing_usages_user_id ON listing_usages(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_listing_usages_project_id ON listing_usages(project_id) WHERE project_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_listing_usages_usage_type ON listing_usages(usage_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_listing_usages_created_at ON listing_usages(created_at DESC);


-- ----------------------------------------------------------------------------
-- 16. marketplace_favorites (市场收藏)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS marketplace_favorites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
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
CREATE TABLE IF NOT EXISTS marketplace_purchases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
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
CREATE TABLE IF NOT EXISTS marketplace_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID NOT NULL REFERENCES marketplace_listings(id) ON DELETE CASCADE,
    reporter_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    report_reason TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    reviewed_by UUID REFERENCES profiles(id) ON DELETE SET NULL,
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

CREATE INDEX IF NOT EXISTS idx_marketplace_reports_listing_id ON marketplace_reports(listing_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_marketplace_reports_reporter_id ON marketplace_reports(reporter_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_marketplace_reports_status ON marketplace_reports(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_marketplace_reports_reviewed_by ON marketplace_reports(reviewed_by, reviewed_at DESC);
CREATE INDEX IF NOT EXISTS idx_marketplace_reports_pending ON marketplace_reports(created_at DESC) WHERE status IN ('pending', 'under_review');


-- ----------------------------------------------------------------------------
-- 19. marketplace_reviews (市场评价)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS marketplace_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID NOT NULL REFERENCES marketplace_listings(id) ON DELETE CASCADE,
    reviewer_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
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
-- 20. user_page_prompt_templates (用户页面提示词模板)
-- User-created prompt templates for page AI generation
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_page_prompt_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    layout TEXT DEFAULT 'image_top',
    story_theme TEXT,
    main_character TEXT,
    style TEXT DEFAULT 'cartoon',
    creativity_level REAL DEFAULT 0.3,
    negative_prompt TEXT,
    generation_mode TEXT DEFAULT 'guided',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT uppt_name_not_empty CHECK (LENGTH(TRIM(name)) > 0),
    CONSTRAINT uppt_creativity_level CHECK (creativity_level >= 0.0 AND creativity_level <= 1.0),
    CONSTRAINT uppt_generation_mode CHECK (generation_mode IN ('guided', 'flexible')),
    CONSTRAINT uppt_unique_user_name UNIQUE (user_id, name)
);

CREATE INDEX IF NOT EXISTS idx_user_page_prompt_templates_user_id ON user_page_prompt_templates(user_id);
CREATE INDEX IF NOT EXISTS idx_user_page_prompt_templates_name ON user_page_prompt_templates(name);


-- ----------------------------------------------------------------------------
-- 21. subscription_history (订阅历史)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS subscription_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    tier TEXT NOT NULL CHECK (tier IN ('t1', 't2', 't3')),
    action TEXT NOT NULL CHECK (action IN ('upgrade', 'downgrade', 'cancel', 'renew', 'pause', 'resume', 'cycle_change')),  -- ALTER-002: +pause/resume/cycle_change
    stripe_subscription_id TEXT,
    stripe_event_id TEXT,
    effective_date TIMESTAMPTZ NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);


-- ----------------------------------------------------------------------------
-- 22. system_assets (系统素材)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS system_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id UUID NOT NULL REFERENCES asset_categories(id),

    name VARCHAR(200) NOT NULL,
    slug VARCHAR(100),
    description TEXT,

    asset_type VARCHAR(20) NOT NULL CHECK (asset_type IN ('text', 'image', 'shape', 'table', 'sticker', 'icon', 'frame')),

    source VARCHAR(20) NOT NULL DEFAULT 'system' CHECK (source IN ('system', 'user', 'ai', 'community')),
    source_user_id UUID REFERENCES profiles(id),

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
CREATE TABLE IF NOT EXISTS system_resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

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
    created_by UUID,
    updated_by UUID,

    deleted_at TIMESTAMPTZ,
    recovery_expires_at TIMESTAMPTZ,

    CONSTRAINT chk_system_resources_recovery_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);

COMMENT ON TABLE system_resources IS '系统资源表: stickers, templates, fonts等系统素材';

CREATE INDEX IF NOT EXISTS idx_sr_type ON system_resources(resource_type) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_sr_category ON system_resources(category_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_sr_active_type ON system_resources(is_active, resource_type) WHERE deleted_at IS NULL AND is_active = true;
CREATE INDEX IF NOT EXISTS idx_sr_tier ON system_resources(min_tier) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_sr_tags ON system_resources USING GIN(tags) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_sr_created ON system_resources(created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_sr_featured ON system_resources(is_featured, display_order) WHERE deleted_at IS NULL AND is_featured = true;

DROP TRIGGER IF EXISTS update_system_resources_updated_at ON system_resources;
CREATE TRIGGER update_system_resources_updated_at
    BEFORE UPDATE ON system_resources
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ----------------------------------------------------------------------------
-- 24. user_discounts (用户折扣)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_discounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
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
CREATE TABLE IF NOT EXISTS user_generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_listings_moderation_status
ON marketplace_listings(moderation_status)
WHERE is_deleted = false;

CREATE INDEX IF NOT EXISTS idx_listings_category_public
ON marketplace_listings(category, is_public)
WHERE is_deleted = false;

CREATE INDEX IF NOT EXISTS idx_profiles_user_code
ON profiles(user_code)
WHERE user_code IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_credit_tx_user_type_date
ON credit_transactions(user_id, transaction_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_credit_tx_idempotency
ON credit_transactions(idempotency_key)
WHERE idempotency_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_profiles_created_at
ON profiles(created_at DESC)
WHERE is_deleted = false;

CREATE INDEX IF NOT EXISTS idx_profiles_tier_created_at
ON profiles(tier, created_at DESC)
WHERE is_deleted = false AND tier IN ('t2', 't3');

CREATE INDEX IF NOT EXISTS idx_projects_user_created_at
ON projects(user_id, created_at DESC)
WHERE is_deleted = false;

-- v2.1.0: Idempotency key index for fast lookup during retry
-- Partial index: only index non-null keys, unique per user
CREATE UNIQUE INDEX IF NOT EXISTS idx_projects_user_idempotency_key
ON projects(user_id, idempotency_key)
WHERE idempotency_key IS NOT NULL AND is_deleted = false;

-- v3.33: Workspace index for filtering projects by workspace
CREATE INDEX IF NOT EXISTS idx_projects_workspace
ON projects(workspace_id)
WHERE workspace_id IS NOT NULL;

-- v3.33 Phase 2.6: Folder and Star indexes for projects
CREATE INDEX IF NOT EXISTS idx_projects_folder
ON projects(folder_id)
WHERE folder_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_projects_starred
ON projects(user_id, is_starred)
WHERE is_starred = TRUE;

-- WS3: Dashboard composite index for projects
-- Covers: user's non-deleted projects sorted by updated_at (dashboard default sort)
CREATE INDEX IF NOT EXISTS idx_projects_user_dashboard
ON projects(user_id, updated_at DESC)
WHERE is_deleted = false;

-- WS-19: Trigram index for fuzzy title search (ILIKE '%query%' optimization)
CREATE INDEX IF NOT EXISTS idx_projects_title_trgm
ON projects USING gin(title gin_trgm_ops)
WHERE is_deleted = false;

-- WS-19: Composite index for marketplace purchase queries
CREATE INDEX IF NOT EXISTS idx_projects_user_purchased
ON projects(user_id, is_purchased)
WHERE is_purchased = true AND is_deleted = false;

-- WS3: Dashboard composite index for assets
-- Covers: user's non-deleted assets sorted by created_at (dashboard default sort)
CREATE INDEX IF NOT EXISTS idx_assets_user_dashboard
ON assets(user_id, created_at DESC)
WHERE is_deleted = false;

-- WS3: Credit transactions user lookup index
-- Covers: user's credit history sorted by time (billing/admin pages)
CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_created_at
ON credit_transactions(user_id, created_at DESC);


-- ============================================================================
-- RPC Functions
-- ============================================================================

-- Marketplace listings with seller info (v1.1.0: 添加 p_resource_type 参数)
CREATE OR REPLACE FUNCTION p_get_marketplace_listings(
    p_resource_type TEXT DEFAULT NULL,  -- Top-level: 'asset' or 'project'
    p_category TEXT DEFAULT NULL,       -- Second-level: 'clipart', 'sticker', etc.
    p_price_filter TEXT DEFAULT 'all',
    p_sort_by TEXT DEFAULT 'latest',
    p_tier_filter TEXT DEFAULT NULL,
    p_search_query TEXT DEFAULT '',
    p_limit INTEGER DEFAULT 20,
    p_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
    listing_id UUID,
    seller_id UUID,
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
      AND (p_resource_type IS NULL OR ml.resource_type = p_resource_type)
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
      AND (p_resource_type IS NULL OR ml.resource_type = p_resource_type)
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
$$ LANGUAGE plpgsql
SET search_path = 'public';


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
$$ LANGUAGE plpgsql
SET search_path = 'public';


-- Soft delete category descendants
CREATE OR REPLACE FUNCTION soft_delete_category_descendants(
    parent_path_input LTREE,
    p_recovery_days INTEGER DEFAULT 30
)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    UPDATE asset_categories
    SET
        deleted_at = CURRENT_TIMESTAMP,
        recovery_expires_at = CURRENT_TIMESTAMP + (p_recovery_days || ' days')::INTERVAL,
        updated_at = CURRENT_TIMESTAMP
    WHERE path <@ parent_path_input AND path != parent_path_input AND deleted_at IS NULL;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql
SET search_path = 'public';


-- Increment category usage
CREATE OR REPLACE FUNCTION increment_category_usage(category_id_input UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE asset_categories
    SET usage_count = usage_count + 1, updated_at = CURRENT_TIMESTAMP
    WHERE id = category_id_input AND deleted_at IS NULL;
END;
$$ LANGUAGE plpgsql
SET search_path = 'public';


-- ============================================================================
-- User Creation Monitoring (幂等用户创建监控)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- user_creation_logs - 用户创建日志表
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_creation_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('register', 'admin', 'oauth', 'legacy')),
    action TEXT NOT NULL CHECK (action IN ('created', 'duplicate_attempt', 'error')),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_user_creation_logs_user_id ON user_creation_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_user_creation_logs_created_at ON user_creation_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_creation_logs_source ON user_creation_logs(source);
CREATE INDEX IF NOT EXISTS idx_user_creation_logs_action ON user_creation_logs(action);

COMMENT ON TABLE user_creation_logs IS '用户创建日志表，用于审计注册事件';
COMMENT ON COLUMN user_creation_logs.source IS '创建源：register（用户注册）、admin（管理员创建）、oauth（第三方登录）、legacy（历史兼容）';
COMMENT ON COLUMN user_creation_logs.action IS '操作类型：created（成功创建）、duplicate_attempt（重复尝试）、error（错误）';

-- ----------------------------------------------------------------------------
-- profiles 索引增强
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_profiles_created_by ON profiles(created_by);
CREATE INDEX IF NOT EXISTS idx_profiles_username ON profiles(username) WHERE username IS NOT NULL;

-- 部分唯一索引：活跃用户邮箱唯一，软删除记录不受约束
-- 允许同一邮箱的多条历史记录并存（用户多次注册→删除→再注册）
CREATE UNIQUE INDEX IF NOT EXISTS idx_profiles_email_unique
    ON profiles(email)
    WHERE is_deleted = false;

-- GIN trigram index for admin fuzzy search on display_name and email
CREATE INDEX IF NOT EXISTS idx_profiles_display_name_trgm
    ON profiles USING gin (display_name gin_trgm_ops)
    WHERE is_deleted = false AND display_name IS NOT NULL;


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
    v_now TIMESTAMP;
    v_date TEXT;
    v_time TEXT;
    v_ms TEXT;
    v_seq TEXT;
    v_rand TEXT;
BEGIN
    -- 使用 UTC 时间
    v_now := (NOW() AT TIME ZONE 'UTC');
    
    -- 日期部分 (YYMMDD) - 6 位
    v_date := TO_CHAR(v_now, 'YYMMDD');
    
    -- 时间部分 (HHMMSS) - 6 位
    v_time := TO_CHAR(v_now, 'HH24MISS');
    
    -- 毫秒部分 (精确到 0.1ms) - 4 位
    v_ms := LPAD(FLOOR(EXTRACT(MILLISECONDS FROM v_now))::TEXT, 4, '0');
    
    -- 序号部分（原子递增）- 7 位
    v_seq := LPAD((nextval('user_code_seq') % 10000000)::TEXT, 7, '0');
    
    -- 随机部分 - 3 位
    v_rand := LPAD(FLOOR(RANDOM() * 1000)::TEXT, 3, '0');
    
    -- 组合成 26 位用户码
    -- 格式: YYMMDD(6) + HHMMSS(6) + mmmm(4) + 序号(7) + 随机(3)
    new_user_code := v_date || v_time || v_ms || v_seq || v_rand;
    
    RETURN new_user_code;
END;
$$ LANGUAGE plpgsql
SET search_path = 'public';

COMMENT ON FUNCTION generate_user_code() IS 
'生成 26 位唯一用户码
格式: YYMMDD(6位) + HHMMSS(6位) + mmmm(4位毫秒) + 序号(7位) + 随机(3位)
示例: 26010914305278900123456789';


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
COMMENT ON COLUMN system_error_logs.operation IS '操作名称（如 create_auth_user_with_profile）';
COMMENT ON COLUMN system_error_logs.error_message IS '错误信息（SQLERRM）';
COMMENT ON COLUMN system_error_logs.details IS '详细信息（JSONB 格式，包含 user_id、参数等）';


-- ============================================================================
-- RPC Functions - 用户注册（自建认证系统）
-- ============================================================================

-- ----------------------------------------------------------------------------
-- create_pending_auth_user - 注册第一步：创建/更新 pending 用户，发送 OTP
-- 三种场景：不存在→INSERT；pending用户→UPDATE覆盖OTP；已注册→返回NULL
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION create_pending_auth_user(
    p_email TEXT,
    p_otp_code_hash TEXT,
    p_otp_purpose TEXT,
    p_otp_expires_at TIMESTAMPTZ
)
RETURNS TABLE(user_id UUID)    -- 改为 TABLE 使 PostgREST 返回 [{"user_id": "xxx"}] 格式
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = 'public'
AS $$
DECLARE
    v_user_id UUID;
    v_existing RECORD;
BEGIN
    -- SELECT ... FOR UPDATE 防止并发竞态（两个请求同时注册同一邮箱）
    SELECT id, email_verified, password_hash INTO v_existing
    FROM auth_users WHERE email = LOWER(TRIM(p_email)) FOR UPDATE;

    IF NOT FOUND THEN
        -- 场景 1: 邮箱不存在 → 创建新的 pending 用户
        v_user_id := gen_random_uuid();
        INSERT INTO auth_users (
            id, email, otp_code_hash, otp_purpose, otp_expires_at,
            password_hash, email_verified, created_at, updated_at
        ) VALUES (
            v_user_id, LOWER(TRIM(p_email)), p_otp_code_hash, p_otp_purpose, p_otp_expires_at,
            NULL, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        );
        RETURN QUERY SELECT v_user_id;

    ELSIF v_existing.email_verified = false AND v_existing.password_hash IS NULL THEN
        -- 场景 2: pending 用户（未完成注册）→ 覆盖 OTP 信息
        UPDATE auth_users SET
            otp_code_hash = p_otp_code_hash,
            otp_purpose = p_otp_purpose,
            otp_expires_at = p_otp_expires_at,
            otp_attempts = 0,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = v_existing.id;
        RETURN QUERY SELECT v_existing.id;

    ELSE
        -- 场景 3: 已注册用户 → 返回 NULL（调用方统一返回"已发送"防枚举）
        RETURN QUERY SELECT NULL::UUID;
    END IF;
END;
$$;

COMMENT ON FUNCTION create_pending_auth_user IS
    '创建待验证用户或更新已有 pending 用户的 OTP。'
    'p_otp_purpose 由调用方传入（如 register/forgot_password）。'
    '已注册用户返回 NULL（不操作），调用方统一返回成功响应防枚举。';


-- ----------------------------------------------------------------------------
-- create_auth_user_with_profile - 注册第三步：完善 pending auth_users + 创建 profiles
-- 调用时机：OTP 已验证，用户设完密码后调用
-- 前置条件：create_pending_auth_user 已创建 pending auth_users 记录
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION create_auth_user_with_profile(
    p_user_id UUID,              -- pending auth_users.id（由 create_pending_auth_user 返回）
    p_email TEXT,
    p_password_hash TEXT,
    p_display_name TEXT DEFAULT NULL,
    p_signup_bonus INT DEFAULT 0, -- 注册奖励积分，由调用方从 system_configs/TierService 获取后传入
    p_created_by TEXT DEFAULT 'register'  -- 创建来源 (register/oauth/admin)
)
RETURNS TABLE(
    auth_user JSONB,
    profile JSONB,
    was_created BOOLEAN
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = 'public'
AS $$
DECLARE
    v_user_code TEXT;
    v_display_name_final TEXT;
    v_auth_user auth_users%ROWTYPE;
    v_profile profiles%ROWTYPE;
BEGIN
    -- Step 1: 幂等性检查 — 防止 register_token 重复使用
    IF EXISTS (
        SELECT 1 FROM auth_users
        WHERE id = p_user_id AND password_hash IS NOT NULL
    ) THEN
        RAISE EXCEPTION 'already_registered: user % has already completed registration', p_user_id;
    END IF;

    -- Step 2: 生成 user_code
    v_user_code := generate_user_code();

    v_display_name_final := COALESCE(
        p_display_name,
        split_part(p_email, '@', 1)
    );

    -- Step 3: 完善 pending auth_users 记录（设置密码，标记邮箱已验证，清除 OTP）
    UPDATE auth_users SET
        password_hash = p_password_hash,
        email_verified = TRUE,
        email_verified_at = CURRENT_TIMESTAMP,
        otp_code_hash = NULL,
        otp_purpose = NULL,
        otp_expires_at = NULL,
        otp_attempts = 0,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_user_id
    RETURNING * INTO v_auth_user;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'pending_user_not_found: auth_users % does not exist', p_user_id;
    END IF;

    -- Step 4: 创建 profiles 记录（业务数据，共享同一 UUID）
    INSERT INTO profiles (
        id,
        email,
        user_code,
        display_name,
        tier,
        credits_permanent,
        created_by,
        created_at,
        updated_at
    ) VALUES (
        p_user_id,
        LOWER(TRIM(p_email)),
        v_user_code,
        v_display_name_final,
        't1',
        p_signup_bonus,
        p_created_by,
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP
    )
    RETURNING * INTO v_profile;

    -- Step 5: 记录创建事件
    INSERT INTO user_creation_logs (
        user_id,
        source,
        action,
        metadata,
        created_at
    ) VALUES (
        p_user_id,
        p_created_by,
        'created',
        jsonb_build_object(
            'email', LOWER(TRIM(p_email)),
            'display_name', v_display_name_final,
            'signup_bonus', p_signup_bonus
        ),
        CURRENT_TIMESTAMP
    );

    -- Step 6: 返回结果
    RETURN QUERY
    SELECT
        row_to_json(v_auth_user)::jsonb,
        row_to_json(v_profile)::jsonb,
        TRUE;

EXCEPTION
    WHEN unique_violation THEN
        RAISE EXCEPTION 'email_already_registered' USING ERRCODE = '23505';
    WHEN OTHERS THEN
        BEGIN
            INSERT INTO system_error_logs (operation, error_message, details, created_at)
            VALUES (
                'create_auth_user_with_profile',
                SQLERRM,
                jsonb_build_object('user_id', p_user_id, 'email', p_email),
                CURRENT_TIMESTAMP
            );
        EXCEPTION
            WHEN OTHERS THEN NULL;
        END;
        RAISE;
END;
$$;

COMMENT ON FUNCTION create_auth_user_with_profile IS
    '注册第三步：完善 pending auth_users（设密码+邮箱已验证）+ 创建 profiles。'
    'OTP 已验证后调用，email_verified 直接设为 TRUE。含幂等性检查防重复调用。';


-- ----------------------------------------------------------------------------
-- restore_auth_user_with_profile - 账户恢复：复用旧 UUID 恢复已删除账户
-- 30 天恢复期内，用户选择"恢复账号"时调用
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION restore_auth_user_with_profile(
    p_old_profile_id UUID,       -- 待恢复的 profiles.id（软删除状态）
    p_email TEXT,
    p_password_hash TEXT,
    p_display_name TEXT DEFAULT NULL,
    p_source TEXT DEFAULT 'register'  -- 创建来源 (register/oauth/admin)
)
RETURNS TABLE(
    auth_user JSONB,             -- 返回完整的 auth_user 对象 (与 create_auth_user_with_profile 统一)
    was_restored BOOLEAN
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = 'public'
AS $$
DECLARE
    v_profile RECORD;
    v_auth_user auth_users%ROWTYPE;
    v_restored_name TEXT;
BEGIN
    -- 1. 查询可恢复的 profiles 记录（使用 recovery_expires_at，与 Python 层一致）
    SELECT id, email, display_name, deleted_at, is_deleted, recovery_expires_at
        INTO v_profile
        FROM profiles
       WHERE id = p_old_profile_id
         AND is_deleted = true
         AND recovery_expires_at > CURRENT_TIMESTAMP
         FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'RESTORE_NOT_FOUND: profile % not found or not restorable', p_old_profile_id;
    END IF;

    -- 2. 确认邮箱匹配（防止篡改）
    IF v_profile.email <> LOWER(TRIM(p_email)) THEN
        RAISE EXCEPTION 'RESTORE_EMAIL_MISMATCH: email does not match profile record';
    END IF;

    -- 3. 清理可能残留的旧 auth_users 记录 (软删除只标记 profiles，auth_users 可能仍存在)
    DELETE FROM auth_users WHERE id = p_old_profile_id;

    -- 4. 创建新的 auth_users 记录（复用旧 UUID）
    INSERT INTO auth_users (id, email, password_hash, email_verified, email_verified_at, created_at, updated_at)
    VALUES (p_old_profile_id, LOWER(TRIM(p_email)), p_password_hash, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    RETURNING * INTO v_auth_user;

    -- 5. 恢复 profiles 记录
    v_restored_name := COALESCE(p_display_name, v_profile.display_name);
    -- ⚠️ SYNC_REQUIRED: 此值必须与账户删除脱敏逻辑中的占位符一致
    IF v_restored_name = 'Deleted User' THEN
        v_restored_name := COALESCE(p_display_name, 'User');
    END IF;

    UPDATE profiles SET
        is_deleted = false,
        deleted_at = NULL,
        recovery_expires_at = NULL,      -- 清除恢复窗口
        display_name = v_restored_name,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_old_profile_id;

    -- 6. 记录恢复事件
    INSERT INTO user_creation_logs (user_id, source, action, metadata, created_at)
    VALUES (
        p_old_profile_id,
        p_source,
        'account_restored',
        jsonb_build_object(
            'restored_at', now(),
            'original_deleted_at', v_profile.deleted_at
        ),
        CURRENT_TIMESTAMP
    );

    -- 7. 返回结果 (与 create_auth_user_with_profile 风格统一)
    RETURN QUERY
    SELECT
        row_to_json(v_auth_user)::jsonb,
        TRUE;

EXCEPTION
    WHEN OTHERS THEN
        BEGIN
            INSERT INTO system_error_logs (operation, error_message, details, created_at)
            VALUES (
                'restore_auth_user_with_profile',
                SQLERRM,
                jsonb_build_object('profile_id', p_old_profile_id, 'email', p_email),
                CURRENT_TIMESTAMP
            );
        EXCEPTION
            WHEN OTHERS THEN NULL;
        END;
        RAISE;
END;
$$;

COMMENT ON FUNCTION restore_auth_user_with_profile IS
    '账户恢复：复用旧 profiles UUID 创建 auth_users，恢复 profiles.is_deleted=false，清除 recovery_expires_at。'
    '仅在 30 天恢复期内有效，邮箱必须匹配。';


-- ----------------------------------------------------------------------------
-- get_user_creation_stats - 获取用户创建统计（适配自建认证系统）
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_user_creation_stats(p_days INTEGER DEFAULT 7)
RETURNS TABLE(
    total_users BIGINT,
    register_created BIGINT,
    admin_created BIGINT,
    oauth_created BIGINT,
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
    stats AS (
        SELECT
            COUNT(DISTINCT ru.id) AS total_users,
            COUNT(DISTINCT CASE WHEN ru.created_by = 'register' THEN ru.id END) AS register_created,
            COUNT(DISTINCT CASE WHEN ru.created_by = 'admin' THEN ru.id END) AS admin_created,
            COUNT(DISTINCT CASE WHEN ru.created_by = 'oauth' THEN ru.id END) AS oauth_created,
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
    )
    SELECT
        s.total_users,
        s.register_created,
        s.admin_created,
        s.oauth_created,
        s.duplicate_attempts,
        s.errors
    FROM stats s;
END;
$$;

COMMENT ON FUNCTION get_user_creation_stats IS '获取用户创建统计数据，用于监控 Webhook 健康度';


-- ----------------------------------------------------------------------------
-- get_user_dashboard_stats - 获取仪表板统计数据 (前端 User Monitoring 面板)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_user_dashboard_stats()
RETURNS TABLE(
    today BIGINT,
    yesterday BIGINT,
    this_week BIGINT,
    this_month BIGINT,
    change_percent NUMERIC,
    hourly_breakdown JSONB
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_today BIGINT;
    v_yesterday BIGINT;
    v_this_week BIGINT;
    v_this_month BIGINT;
    v_change_percent NUMERIC;
    v_hourly JSONB;
BEGIN
    -- 今日创建数
    SELECT COUNT(*) INTO v_today
    FROM profiles
    WHERE DATE(created_at AT TIME ZONE 'UTC') = CURRENT_DATE;

    -- 昨日创建数
    SELECT COUNT(*) INTO v_yesterday
    FROM profiles
    WHERE DATE(created_at AT TIME ZONE 'UTC') = CURRENT_DATE - INTERVAL '1 day';

    -- 本周创建数
    SELECT COUNT(*) INTO v_this_week
    FROM profiles
    WHERE created_at >= date_trunc('week', CURRENT_DATE);

    -- 本月创建数
    SELECT COUNT(*) INTO v_this_month
    FROM profiles
    WHERE created_at >= date_trunc('month', CURRENT_DATE);

    -- 与昨日相比的变化百分比
    IF v_yesterday > 0 THEN
        v_change_percent := ROUND(((v_today - v_yesterday)::NUMERIC / v_yesterday * 100), 1);
    ELSE
        v_change_percent := CASE WHEN v_today > 0 THEN 100.0 ELSE 0.0 END;
    END IF;

    -- 今日每小时创建数
    SELECT jsonb_agg(
        jsonb_build_object(
            'hour', h.hour,
            'count', COALESCE(c.count, 0)
        ) ORDER BY h.hour
    ) INTO v_hourly
    FROM generate_series(0, 23) AS h(hour)
    LEFT JOIN (
        SELECT
            EXTRACT(HOUR FROM created_at AT TIME ZONE 'UTC')::INTEGER AS hour,
            COUNT(*) AS count
        FROM profiles
        WHERE DATE(created_at AT TIME ZONE 'UTC') = CURRENT_DATE
        GROUP BY EXTRACT(HOUR FROM created_at AT TIME ZONE 'UTC')
    ) c ON h.hour = c.hour;

    RETURN QUERY SELECT v_today, v_yesterday, v_this_week, v_this_month, v_change_percent, v_hourly;
END;
$$;

COMMENT ON FUNCTION get_user_dashboard_stats IS '获取用户创建仪表板统计数据，用于前端 User Monitoring 面板';


-- ----------------------------------------------------------------------------
-- get_user_creation_trends - 获取用户创建趋势数据
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_user_creation_trends(p_days INTEGER DEFAULT 7)
RETURNS TABLE(
    date TEXT,
    count BIGINT,
    t1_count BIGINT,
    t2_count BIGINT,
    t3_count BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        TO_CHAR(d.date, 'YYYY-MM-DD') AS date,
        COALESCE(c.total, 0) AS count,
        COALESCE(c.t1, 0) AS t1_count,
        COALESCE(c.t2, 0) AS t2_count,
        COALESCE(c.t3, 0) AS t3_count
    FROM generate_series(
        CURRENT_DATE - INTERVAL '1 day' * (p_days - 1),
        CURRENT_DATE,
        INTERVAL '1 day'
    ) AS d(date)
    LEFT JOIN (
        SELECT
            DATE(created_at AT TIME ZONE 'UTC') AS created_date,
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE tier = 't1') AS t1,
            COUNT(*) FILTER (WHERE tier = 't2') AS t2,
            COUNT(*) FILTER (WHERE tier = 't3') AS t3
        FROM profiles
        WHERE created_at >= CURRENT_DATE - INTERVAL '1 day' * p_days
        GROUP BY DATE(created_at AT TIME ZONE 'UTC')
    ) c ON d.date = c.created_date
    ORDER BY d.date;
END;
$$;

COMMENT ON FUNCTION get_user_creation_trends IS '获取用户创建趋势数据，按天统计各 tier 创建数';


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
-- 运维视图，放在 internal schema，PostgREST 不暴露 (包含 email 等敏感信息)
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS public.v_user_creation_events CASCADE;
CREATE OR REPLACE VIEW internal.v_user_creation_events AS
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
FROM public.profiles p
LEFT JOIN public.user_creation_logs ucl ON p.id = ucl.user_id
WHERE ucl.action IN ('created', 'duplicate_attempt')
ORDER BY p.created_at DESC;

COMMENT ON VIEW internal.v_user_creation_events IS '用户创建事件视图，包含延迟分析';


-- ============================================================================
-- 3.5 workspace_members (成员 - v3.33 Phase 5)
-- 说明: Workspace 成员关系 (owner/member 角色)
-- ============================================================================
CREATE TABLE IF NOT EXISTS workspace_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 关联
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    -- 角色 (owner / member)
    role TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('owner', 'member')),

    -- 邀请来源
    invited_by UUID REFERENCES profiles(id) ON DELETE SET NULL,

    -- 状态
    is_active BOOLEAN DEFAULT TRUE,

    -- 标准审计字段
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- 唯一约束: 同一用户不能在同一 workspace 中有多个成员记录
    UNIQUE(workspace_id, user_id)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_workspace_members_workspace ON workspace_members(workspace_id) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_workspace_members_user ON workspace_members(user_id) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_workspace_members_role ON workspace_members(workspace_id, role) WHERE is_active = TRUE;

-- 触发器: 更新 updated_at
DROP TRIGGER IF EXISTS update_workspace_members_updated_at ON workspace_members;
CREATE TRIGGER update_workspace_members_updated_at
    BEFORE UPDATE ON workspace_members
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ============================================================================
-- 3.6 workspace_invitations (邀请 - v3.33 Phase 5)
-- 说明: Workspace 成员邀请，支持 email 邀请
-- ============================================================================
CREATE TABLE IF NOT EXISTS workspace_invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 关联
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,

    -- 邀请信息
    invited_email TEXT NOT NULL,
    invited_by UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    -- 角色 (被邀请者将获得的角色)
    role TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('member')),

    -- 状态: pending / accepted / declined / expired
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'declined', 'expired')),

    -- 过期时间 (默认 7 天; 应用层创建时可覆盖此默认值，建议从 system_configs 读取)
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '7 days'),

    -- 接受者 (接受邀请后填入)
    accepted_by UUID REFERENCES profiles(id) ON DELETE SET NULL,
    accepted_at TIMESTAMPTZ,

    -- 标准审计字段
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_workspace_invitations_workspace ON workspace_invitations(workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_workspace_invitations_email ON workspace_invitations(invited_email, status);
CREATE INDEX IF NOT EXISTS idx_workspace_invitations_expires ON workspace_invitations(expires_at) WHERE status = 'pending';

-- 触发器: 更新 updated_at
DROP TRIGGER IF EXISTS update_workspace_invitations_updated_at ON workspace_invitations;
CREATE TRIGGER update_workspace_invitations_updated_at
    BEFORE UPDATE ON workspace_invitations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ============================================================================
-- WS3: 原子 RPC 函数 (支付系统审计修复)
-- DEPENDS ON: 03_infrastructure.sql (payment_records table)
-- 部署顺序: 03_infrastructure.sql → 01_core_business.sql → 02_platform_services.sql
-- ============================================================================

-- ----------------------------------------------------------------------------
-- process_subscription_start - 原子处理首次订阅 (#25)
-- 幂等性: p_session_id 作为 idempotency_key
-- 原子执行: profiles 更新 + payment_records 插入 + credit_transactions 插入
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION process_subscription_start(
    p_user_id UUID,
    p_plan TEXT,                    -- 't2' or 't3'
    p_stripe_customer_id TEXT,
    p_credits_amount INT,          -- 月度积分 (从 TierService 获取)
    p_payment_amount INT,          -- 支付金额 (美分)
    p_currency TEXT,
    p_session_id TEXT,             -- Stripe checkout session ID (幂等性 key)
    p_payment_method TEXT DEFAULT 'card'  -- 支付方式 (从 Stripe 获取)
)
RETURNS JSONB AS $$
DECLARE
    v_monthly INT;
    v_permanent INT;
    v_current_tier TEXT;
    v_current_status TEXT;
    v_payment_id UUID;
BEGIN
    -- 输入验证
    IF p_user_id IS NULL THEN
        RETURN jsonb_build_object('success', false, 'error', 'Invalid user_id');
    END IF;

    -- Paid tiers only (t2=Starter, t3=Pro; see system_configs for display names)
    IF p_plan NOT IN ('t2', 't3') THEN
        RETURN jsonb_build_object('success', false, 'error', 'Invalid plan: ' || COALESCE(p_plan, 'NULL'));
    END IF;

    IF p_session_id IS NULL OR length(p_session_id) = 0 THEN
        RETURN jsonb_build_object('success', false, 'error', 'Invalid session_id');
    END IF;

    -- 幂等性检查: session_id 是否已处理过
    IF EXISTS (
        SELECT 1 FROM credit_transactions
        WHERE idempotency_key = 'sub_start_' || p_session_id
    ) THEN
        SELECT credits_monthly, credits_permanent, tier
        INTO v_monthly, v_permanent, v_current_tier
        FROM profiles WHERE id = p_user_id;

        RETURN jsonb_build_object(
            'success', true,
            'already_processed', true,
            'user_id', p_user_id,
            'tier', COALESCE(v_current_tier, p_plan),
            'credits_monthly', COALESCE(v_monthly, 0)
        );
    END IF;

    -- 加锁获取用户当前状态
    SELECT tier, subscription_status, credits_monthly, credits_permanent
    INTO v_current_tier, v_current_status, v_monthly, v_permanent
    FROM profiles
    WHERE id = p_user_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', false, 'error', 'User not found');
    END IF;

    -- 状态前置检查: 若用户已是付费 tier (t2=Starter, t3=Pro; delayed event)，跳过
    IF v_current_tier IN ('t2', 't3') AND v_current_status = 'active' THEN
        RETURN jsonb_build_object(
            'success', true,
            'already_processed', true,
            'user_id', p_user_id,
            'tier', v_current_tier,
            'credits_monthly', v_monthly
        );
    END IF;

    -- 步骤 1: 更新 profiles (tier + customer + status + credits)
    UPDATE profiles
    SET tier = p_plan,
        stripe_customer_id = p_stripe_customer_id,
        subscription_status = 'active',
        credits_monthly = p_credits_amount,
        updated_at = NOW()
    WHERE id = p_user_id;

    -- 步骤 2: 插入 payment_records
    INSERT INTO payment_records (
        user_id, payment_type, payment_method, amount_usd, currency, status, metadata, created_at
    ) VALUES (
        p_user_id,
        'sub_payment',
        p_payment_method,
        p_payment_amount / 100.0,
        UPPER(p_currency),
        'succeeded',
        jsonb_build_object(
            'session_id', p_session_id,
            'plan', p_plan,
            'description', format('%s Plan Subscription - $%s', initcap(p_plan), (p_payment_amount / 100.0)::TEXT)
        ),
        NOW()
    )
    RETURNING id INTO v_payment_id;

    -- 步骤 3: 插入 credit_transactions (月度积分发放)
    INSERT INTO credit_transactions (
        user_id, transaction_type, bucket, amount,
        balance_monthly_after, balance_permanent_after,
        description, idempotency_key, created_at
    ) VALUES (
        p_user_id,
        'monthly_reset',
        'monthly',
        p_credits_amount,
        p_credits_amount,
        v_permanent,
        format('%s Plan Monthly Credits', initcap(p_plan)),
        'sub_start_' || p_session_id,
        NOW()
    );

    RETURN jsonb_build_object(
        'success', true,
        'user_id', p_user_id,
        'tier', p_plan,
        'credits_monthly', p_credits_amount,
        'payment_id', v_payment_id
    );
END;
$$ LANGUAGE plpgsql
SET search_path = 'public';

COMMENT ON FUNCTION process_subscription_start IS 'WS3: 原子处理首次订阅 (tier更新+支付记录+积分发放)，幂等';

-- ----------------------------------------------------------------------------
-- process_subscription_renewal - 原子处理订阅续费 (#49)
-- 幂等性: p_idempotency_key (invoice_id)
-- 原子执行: payment_records 插入 + profiles 更新 + credit_transactions 插入
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION process_subscription_renewal(
    p_user_id UUID,
    p_tier TEXT,                    -- 当前 tier ('t2' or 't3')
    p_amount_usd INT,              -- 支付金额 (美分)
    p_currency TEXT,
    p_invoice_id TEXT,             -- Stripe invoice ID
    p_monthly_credits INT,         -- 月度积分 (从 TierService 获取)
    p_idempotency_key TEXT,        -- 幂等性 key (通常 = 'renewal_' + invoice_id)
    p_payment_method TEXT DEFAULT 'card'  -- 支付方式 (从 Stripe 获取)
)
RETURNS JSONB AS $$
DECLARE
    v_monthly INT;
    v_permanent INT;
    v_current_status TEXT;
    v_payment_id UUID;
BEGIN
    -- 输入验证
    IF p_user_id IS NULL THEN
        RETURN jsonb_build_object('success', false, 'error', 'Invalid user_id');
    END IF;

    IF p_idempotency_key IS NULL OR length(p_idempotency_key) < 16 THEN
        RETURN jsonb_build_object('success', false, 'error', 'Invalid idempotency_key');
    END IF;

    -- 幂等性检查
    IF EXISTS (
        SELECT 1 FROM credit_transactions
        WHERE idempotency_key = p_idempotency_key
    ) THEN
        SELECT credits_monthly, credits_permanent
        INTO v_monthly, v_permanent
        FROM profiles WHERE id = p_user_id;

        RETURN jsonb_build_object(
            'success', true,
            'already_processed', true,
            'credits_monthly', COALESCE(v_monthly, 0)
        );
    END IF;

    -- 加锁获取用户当前状态
    SELECT subscription_status, credits_monthly, credits_permanent
    INTO v_current_status, v_monthly, v_permanent
    FROM profiles
    WHERE id = p_user_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', false, 'error', 'User not found');
    END IF;

    -- 状态前置检查: 若已取消，跳过 (防止乱序 event 覆盖)
    IF v_current_status = 'canceled' THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'subscription_canceled',
            'message', 'Subscription was canceled, skipping renewal'
        );
    END IF;

    -- 步骤 1: 插入 payment_records
    INSERT INTO payment_records (
        user_id, payment_type, payment_method, amount_usd, currency, status, metadata, created_at
    ) VALUES (
        p_user_id,
        'sub_renewal',
        p_payment_method,
        p_amount_usd / 100.0,
        UPPER(p_currency),
        'succeeded',
        jsonb_build_object(
            'invoice_id', p_invoice_id,
            'tier', p_tier,
            'description', format('%s Plan Renewal - $%s', initcap(p_tier), (p_amount_usd / 100.0)::TEXT)
        ),
        NOW()
    )
    RETURNING id INTO v_payment_id;

    -- 步骤 2: 更新 subscription_status 为 active + 重置月度积分
    UPDATE profiles
    SET subscription_status = 'active',
        credits_monthly = p_monthly_credits,
        updated_at = NOW()
    WHERE id = p_user_id;

    -- 步骤 3: 插入 credit_transactions (月度积分重置)
    INSERT INTO credit_transactions (
        user_id, transaction_type, bucket, amount,
        balance_monthly_after, balance_permanent_after,
        description, idempotency_key, created_at
    ) VALUES (
        p_user_id,
        'monthly_reset',
        'monthly',
        p_monthly_credits,
        p_monthly_credits,
        v_permanent,
        format('%s Plan Monthly Credits Renewal', initcap(p_tier)),
        p_idempotency_key,
        NOW()
    );

    RETURN jsonb_build_object(
        'success', true,
        'user_id', p_user_id,
        'credits_monthly', p_monthly_credits,
        'payment_id', v_payment_id
    );
END;
$$ LANGUAGE plpgsql
SET search_path = 'public';

COMMENT ON FUNCTION process_subscription_renewal IS 'WS3: 原子处理订阅续费 (支付记录+状态更新+积分重置)，幂等';

-- ----------------------------------------------------------------------------
-- admin_adjust_credits_atomic - 原子管理员积分调整 (v3.5 审计 P0)
-- 解决 admin_repository.py 非原子 Read-Modify-Write 竞态
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION admin_adjust_credits_atomic(
    p_user_id UUID,
    p_amount INT,                  -- 正数=增加, 负数=扣减
    p_bucket TEXT,                 -- 'monthly' or 'permanent'
    p_reason TEXT,
    p_admin_id UUID
)
RETURNS JSONB AS $$
DECLARE
    v_monthly INT;
    v_permanent INT;
    v_old_value INT;
    v_new_value INT;
    v_actual_change INT;
    v_tx_type TEXT;
BEGIN
    -- 输入验证
    IF p_user_id IS NULL THEN
        RETURN jsonb_build_object('success', false, 'error', 'Invalid user_id');
    END IF;

    IF p_bucket NOT IN ('monthly', 'permanent') THEN
        RETURN jsonb_build_object('success', false, 'error', 'Invalid bucket: ' || COALESCE(p_bucket, 'NULL'));
    END IF;

    IF p_amount = 0 THEN
        RETURN jsonb_build_object('success', false, 'error', 'Amount cannot be zero');
    END IF;

    -- 加锁获取用户当前余额 (FOR UPDATE 防止 Lost Update)
    SELECT credits_monthly, credits_permanent
    INTO v_monthly, v_permanent
    FROM profiles
    WHERE id = p_user_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', false, 'error', 'User not found');
    END IF;

    -- 计算新值 (不低于0)
    IF p_bucket = 'monthly' THEN
        v_old_value := v_monthly;
        v_new_value := GREATEST(0, v_monthly + p_amount);
        v_actual_change := v_new_value - v_monthly;

        UPDATE profiles
        SET credits_monthly = v_new_value, updated_at = NOW()
        WHERE id = p_user_id;

        v_monthly := v_new_value;
    ELSE
        v_old_value := v_permanent;
        v_new_value := GREATEST(0, v_permanent + p_amount);
        v_actual_change := v_new_value - v_permanent;

        UPDATE profiles
        SET credits_permanent = v_new_value, updated_at = NOW()
        WHERE id = p_user_id;

        v_permanent := v_new_value;
    END IF;

    -- 交易类型
    v_tx_type := CASE WHEN p_amount > 0 THEN 'admin_adjustment' ELSE 'admin_adjustment' END;

    -- 插入 credit_transactions (审计记录)
    INSERT INTO credit_transactions (
        user_id, transaction_type, bucket, amount,
        balance_monthly_after, balance_permanent_after,
        description, metadata, created_at
    ) VALUES (
        p_user_id,
        v_tx_type,
        p_bucket,
        v_actual_change,
        v_monthly,
        v_permanent,
        p_reason,
        jsonb_build_object('admin_id', p_admin_id, 'requested_amount', p_amount),
        NOW()
    );

    RETURN jsonb_build_object(
        'success', true,
        'old_value', v_old_value,
        'new_value', v_new_value,
        'actual_change', v_actual_change
    );
END;
$$ LANGUAGE plpgsql
SET search_path = 'public';

COMMENT ON FUNCTION admin_adjust_credits_atomic IS 'WS3: 原子管理员积分调整 (FOR UPDATE 锁防止 Lost Update)';


-- ---------------------------------------------------------------------------
-- process_subscription_termination - 原子处理订阅终止 (WS4: #7, #8)
-- ---------------------------------------------------------------------------
-- 统一处理所有导致 tier 降级的路径:
--   1. Stripe webhook subscription.deleted (取消/unpaid/过期)
--   2. Admin 立即取消
--   3. Admin 降级到 t1
-- 原子执行: tier 降级 + credits_monthly 清零 + payment_record + credit_transaction 审计
-- 清除 cancel_at_period_end 等期末标记 (因为已经实际生效)
-- 保留 stripe_customer_id (便于用户未来复购)

CREATE OR REPLACE FUNCTION process_subscription_termination(
    p_user_id UUID,
    p_new_tier TEXT,
    p_reason TEXT,                    -- payment_type: 'sub_canceled', 'tier_downgrade', etc.
    p_subscription_status TEXT DEFAULT 'inactive',  -- 目标 subscription_status
    p_metadata JSONB DEFAULT '{}'::jsonb
)
RETURNS JSONB AS $$
DECLARE
    v_profile RECORD;
    v_cleared_monthly INTEGER;
    v_payment_id UUID;
BEGIN
    -- 1. Lock and read current profile
    SELECT id, tier, credits_monthly, credits_permanent, subscription_status,
           cancel_at_period_end, cancel_at, pending_tier_change
    INTO v_profile
    FROM profiles
    WHERE id = p_user_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'user_not_found'
        );
    END IF;

    -- Record credits being cleared for audit
    v_cleared_monthly := v_profile.credits_monthly;

    -- 2. Update profiles: tier + status + clear monthly credits + clear cancel flags
    UPDATE profiles SET
        tier = p_new_tier,
        subscription_status = p_subscription_status,
        credits_monthly = 0,
        credits_reset_at = NULL,
        cancel_at_period_end = FALSE,
        cancel_at = NULL,
        pending_tier_change = NULL,
        tier_changed_at = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_user_id;

    -- 3. Insert payment_record for audit trail
    INSERT INTO payment_records (
        user_id, payment_type, amount_usd, currency, status, metadata
    ) VALUES (
        p_user_id,
        p_reason,
        0,
        'USD',
        'completed',
        p_metadata || jsonb_build_object(
            'previous_tier', v_profile.tier,
            'new_tier', p_new_tier,
            'cleared_monthly_credits', v_cleared_monthly
        )
    )
    RETURNING id INTO v_payment_id;

    -- 4. Insert credit_transaction audit record (only if credits were actually cleared)
    IF v_cleared_monthly > 0 THEN
        INSERT INTO credit_transactions (
            user_id,
            transaction_type,
            bucket,
            amount,
            balance_monthly_after,
            balance_permanent_after,
            description,
            metadata
        ) VALUES (
            p_user_id,
            'monthly_credits_cleared',
            'monthly',
            -v_cleared_monthly,
            0,
            v_profile.credits_permanent,
            'Monthly credits cleared on subscription termination (' || p_reason || ')',
            jsonb_build_object(
                'reason', p_reason,
                'previous_tier', v_profile.tier,
                'new_tier', p_new_tier,
                'payment_record_id', v_payment_id
            )
        );
    END IF;

    RETURN jsonb_build_object(
        'success', true,
        'previous_tier', v_profile.tier,
        'new_tier', p_new_tier,
        'cleared_credits', v_cleared_monthly,
        'payment_id', v_payment_id
    );
END;
$$ LANGUAGE plpgsql
SET search_path = 'public';

COMMENT ON FUNCTION process_subscription_termination IS 'WS4: 原子处理订阅终止 (tier降级+积分清零+审计记录)，统一所有取消/降级路径';


-- ---------------------------------------------------------------------------
-- process_credit_refund - 原子处理积分购买退费 (WS5: #6, #14, #15)
-- ---------------------------------------------------------------------------
-- 退费 webhook 触发时，原子执行:
--   1. 幂等性检查 (stripe_refund_id)
--   2. 扣回永久积分 (不允许扣成负数)
--   3. 插入 credit_transaction 审计
--   4. 插入 payment_record (type='refund')
--   5. 更新原始交易记录的 refunded_amount / refunded_at

CREATE OR REPLACE FUNCTION process_credit_refund(
    p_user_id UUID,
    p_credits_to_deduct INTEGER,      -- 应扣回的积分数 (已按比例计算)
    p_payment_intent_id TEXT,          -- 原始 payment_intent ID
    p_refund_id TEXT,                  -- Stripe refund ID (幂等性 key)
    p_amount_usd NUMERIC,             -- 退款金额 (美元, 已转换)
    p_currency TEXT DEFAULT 'USD',
    p_metadata JSONB DEFAULT '{}'::jsonb
)
RETURNS JSONB AS $$
DECLARE
    v_existing_refund UUID;
    v_profile RECORD;
    v_actual_deduct INTEGER;
    v_new_permanent INTEGER;
    v_payment_id UUID;
BEGIN
    -- 1. Idempotency check: has this refund already been processed?
    SELECT id INTO v_existing_refund
    FROM payment_records
    WHERE stripe_refund_id = p_refund_id
    LIMIT 1;

    IF FOUND THEN
        RETURN jsonb_build_object(
            'success', true,
            'already_processed', true,
            'existing_payment_id', v_existing_refund
        );
    END IF;

    -- 2. Lock and read user profile
    SELECT id, credits_permanent, credits_monthly
    INTO v_profile
    FROM profiles
    WHERE id = p_user_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'user_not_found'
        );
    END IF;

    -- 3. Calculate actual deduction (cap at current balance, never go negative)
    v_actual_deduct := LEAST(p_credits_to_deduct, v_profile.credits_permanent);
    v_new_permanent := v_profile.credits_permanent - v_actual_deduct;

    -- 4. Deduct permanent credits
    IF v_actual_deduct > 0 THEN
        UPDATE profiles
        SET credits_permanent = v_new_permanent,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = p_user_id;
    END IF;

    -- 5. Insert refund payment_record
    INSERT INTO payment_records (
        user_id, payment_type, amount_usd, currency, status,
        stripe_payment_intent_id, stripe_refund_id,
        refunded_amount, refunded_at, metadata
    ) VALUES (
        p_user_id,
        'refund',
        p_amount_usd,
        p_currency,
        'refunded',
        p_payment_intent_id,
        p_refund_id,
        p_amount_usd,
        CURRENT_TIMESTAMP,
        p_metadata || jsonb_build_object(
            'credits_deducted', v_actual_deduct,
            'credits_requested', p_credits_to_deduct,
            'remaining_permanent', v_new_permanent
        )
    )
    RETURNING id INTO v_payment_id;

    -- 6. Insert credit_transaction audit record
    IF v_actual_deduct > 0 THEN
        INSERT INTO credit_transactions (
            user_id,
            transaction_type,
            bucket,
            amount,
            balance_monthly_after,
            balance_permanent_after,
            description,
            idempotency_key,
            metadata
        ) VALUES (
            p_user_id,
            'refund_reversal',
            'permanent',
            -v_actual_deduct,
            v_profile.credits_monthly,
            v_new_permanent,
            'Credits reversed due to refund (refund_id: ' || p_refund_id || ')',
            'refund_' || p_refund_id,
            jsonb_build_object(
                'refund_id', p_refund_id,
                'payment_intent_id', p_payment_intent_id,
                'payment_record_id', v_payment_id
            )
        );
    END IF;

    -- 7. Update original payment record's refunded_amount/refunded_at
    UPDATE payment_records
    SET refunded_amount = COALESCE(refunded_amount, 0) + p_amount_usd,
        refunded_at = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP
    WHERE stripe_payment_intent_id = p_payment_intent_id
      AND payment_type != 'refund';

    RETURN jsonb_build_object(
        'success', true,
        'already_processed', false,
        'credits_deducted', v_actual_deduct,
        'credits_requested', p_credits_to_deduct,
        'remaining_permanent', v_new_permanent,
        'payment_id', v_payment_id
    );
END;
$$ LANGUAGE plpgsql
SET search_path = 'public';

COMMENT ON FUNCTION process_credit_refund IS 'WS5: 原子处理积分购买退费 (幂等+积分扣回+审计)';


-- (已删除: get_dashboard_projects — Python 已改用 .table().select() 直接查询，RPC 冗余)
-- (已删除: get_dashboard_assets — 同上)
-- (已删除: get_dashboard_stats — 同上，注意与 get_user_dashboard_stats 不同)


-- WS-12: RPC — 用户增长统计 (替代 .limit(100000) + Python 聚合)
CREATE OR REPLACE FUNCTION rpc_user_growth_stats(
    p_start_date TIMESTAMPTZ,
    p_end_date TIMESTAMPTZ
)
RETURNS TABLE(date TEXT, count BIGINT) AS $$
BEGIN
    RETURN QUERY
    SELECT
        to_char(p.created_at, 'YYYY-MM-DD') AS date,
        COUNT(*)::BIGINT AS count
    FROM profiles p
    WHERE p.created_at >= p_start_date
      AND p.created_at <= p_end_date
    GROUP BY to_char(p.created_at, 'YYYY-MM-DD')
    ORDER BY date;
END;
$$ LANGUAGE plpgsql STABLE
SET search_path = 'public';


-- WS-12: RPC — Tier 分布统计 (替代 .limit(100000) + Python 聚合)
CREATE OR REPLACE FUNCTION rpc_tier_distribution()
RETURNS TABLE(tier TEXT, count BIGINT) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COALESCE(p.tier, 't1') AS tier,
        COUNT(*)::BIGINT AS count
    FROM profiles p
    GROUP BY COALESCE(p.tier, 't1');
END;
$$ LANGUAGE plpgsql STABLE
SET search_path = 'public';


-- ============================================================================
-- WS5: increment_asset_usage 原子操作
-- ============================================================================

-- Atomic increment of asset usage_count (prevents race conditions)
CREATE OR REPLACE FUNCTION increment_asset_usage(
    p_asset_id UUID,
    p_user_id UUID
)
RETURNS INTEGER AS $$
DECLARE
    v_new_count INTEGER;
BEGIN
    UPDATE assets
    SET usage_count = COALESCE(usage_count, 0) + 1
    WHERE id = p_asset_id AND user_id = p_user_id AND is_deleted = false
    RETURNING usage_count INTO v_new_count;

    IF NOT FOUND THEN
        RETURN -1;  -- Asset not found or not owned by user
    END IF;

    RETURN v_new_count;
END;
$$ LANGUAGE plpgsql VOLATILE
SET search_path = 'public';

COMMENT ON FUNCTION increment_asset_usage IS 'WS5: 原子递增素材使用次数';


-- ============================================================================
-- WS-19: Atomic counter increments for projects
-- ============================================================================

-- (已删除: increment_project_view_count — 完全死代码，无 Python 调用)
-- (已删除: increment_project_like_count — 完全死代码，无 Python 调用)


-- ============================================================================
-- WS5: delete_tag_atomic - 原子删除标签 + 关联
-- ============================================================================

CREATE OR REPLACE FUNCTION delete_tag_atomic(
    p_tag_id UUID
)
RETURNS BOOLEAN AS $$
BEGIN
    -- Step 1: Soft delete the tag
    UPDATE tags SET is_active = false WHERE id = p_tag_id;

    IF NOT FOUND THEN
        RETURN false;
    END IF;

    -- Step 2: Remove project associations
    DELETE FROM project_tags WHERE tag_id = p_tag_id;

    -- Step 3: Remove asset associations
    DELETE FROM user_asset_tags WHERE tag_id = p_tag_id;

    RETURN true;
END;
$$ LANGUAGE plpgsql VOLATILE
SET search_path = 'public';

COMMENT ON FUNCTION delete_tag_atomic IS 'WS5: 原子删除标签及其所有关联';


-- ============================================================================
-- WS5: set_project_tags_atomic - 原子替换项目标签
-- ============================================================================

CREATE OR REPLACE FUNCTION set_project_tags_atomic(
    p_project_id UUID,
    p_tag_ids UUID[],
    p_user_id UUID
)
RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER := 0;
    v_tag_id UUID;
BEGIN
    -- Step 1: Delete all existing tags for this project
    DELETE FROM project_tags WHERE project_id = p_project_id;

    -- Step 2: Insert new tags
    IF p_tag_ids IS NOT NULL AND array_length(p_tag_ids, 1) > 0 THEN
        FOREACH v_tag_id IN ARRAY p_tag_ids LOOP
            INSERT INTO project_tags (project_id, tag_id, added_by)
            VALUES (p_project_id, v_tag_id, p_user_id)
            ON CONFLICT (project_id, tag_id) DO NOTHING;
            v_count := v_count + 1;
        END LOOP;
    END IF;

    RETURN v_count;
END;
$$ LANGUAGE plpgsql VOLATILE
SET search_path = 'public';

COMMENT ON FUNCTION set_project_tags_atomic IS 'WS5: 原子替换项目标签 (删除旧标签+插入新标签)';


-- ============================================================================
-- WS5: set_asset_tags_atomic - 原子替换素材标签
-- ============================================================================

CREATE OR REPLACE FUNCTION set_asset_tags_atomic(
    p_asset_id UUID,
    p_tag_ids UUID[],
    p_user_id UUID,
    p_source TEXT DEFAULT 'manual'
)
RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER := 0;
    v_tag_id UUID;
BEGIN
    -- Step 1: Delete all existing tags for this asset
    DELETE FROM user_asset_tags WHERE asset_id = p_asset_id;

    -- Step 2: Insert new tags
    IF p_tag_ids IS NOT NULL AND array_length(p_tag_ids, 1) > 0 THEN
        FOREACH v_tag_id IN ARRAY p_tag_ids LOOP
            INSERT INTO user_asset_tags (asset_id, tag_id, added_by, source)
            VALUES (p_asset_id, v_tag_id, p_user_id, p_source)
            ON CONFLICT (asset_id, tag_id) DO NOTHING;
            v_count := v_count + 1;
        END LOOP;
    END IF;

    RETURN v_count;
END;
$$ LANGUAGE plpgsql VOLATILE
SET search_path = 'public';

COMMENT ON FUNCTION set_asset_tags_atomic IS 'WS5: 原子替换素材标签 (删除旧标签+插入新标签)';


-- ============================================================================
-- WS-2: 原子创建项目 + 限额检查 RPC
-- ============================================================================

-- create_project_with_limit_check: 在单事务内完成限额检查 + 项目创建
-- 解决 TOCTOU 竞态: count 和 insert 在同一事务中使用 advisory lock 保证原子性
CREATE OR REPLACE FUNCTION create_project_with_limit_check(
    p_user_id UUID,
    p_project_id UUID,
    p_title TEXT,
    p_canvas_size TEXT DEFAULT '1080x1080',
    p_description TEXT DEFAULT NULL,
    p_canvas_data JSONB DEFAULT '{}'::jsonb,
    p_tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    p_thumbnail_url TEXT DEFAULT NULL,
    p_is_public BOOLEAN DEFAULT FALSE,
    p_is_template BOOLEAN DEFAULT FALSE,
    p_template_category TEXT DEFAULT NULL,
    p_idempotency_key TEXT DEFAULT NULL,
    p_folder_id UUID DEFAULT NULL,
    p_is_starred BOOLEAN DEFAULT FALSE,
    p_project_limit INTEGER DEFAULT 100,
    p_workspace_id UUID DEFAULT NULL
)
RETURNS TABLE (
    success BOOLEAN,
    project_id UUID,
    error_code TEXT
) AS $$
DECLARE
    v_current_count INTEGER;
    v_lock_key BIGINT;
BEGIN
    -- 1. 幂等性检查: 如果 idempotency_key 已存在，返回已有项目
    IF p_idempotency_key IS NOT NULL THEN
        SELECT p.id INTO project_id
        FROM projects p
        WHERE p.user_id = p_user_id
          AND p.idempotency_key = p_idempotency_key
          AND p.is_deleted = FALSE;

        IF FOUND THEN
            success := TRUE;
            error_code := NULL;
            RETURN NEXT;
            RETURN;
        END IF;
    END IF;

    -- 2. Advisory lock — 基于 user_id 哈希，防止同一用户并发创建
    v_lock_key := hashtext(p_user_id::TEXT);
    PERFORM pg_advisory_xact_lock(v_lock_key);

    -- 3. 原子限额检查
    SELECT COUNT(*) INTO v_current_count
    FROM projects
    WHERE user_id = p_user_id
      AND is_deleted = FALSE
      AND status != 'deleted';

    IF v_current_count >= p_project_limit THEN
        success := FALSE;
        project_id := NULL;
        error_code := 'LIMIT_EXCEEDED';
        RETURN NEXT;
        RETURN;
    END IF;

    -- 4. 插入项目 (ON CONFLICT 处理幂等)
    INSERT INTO projects (
        id, user_id, title, canvas_size, description, canvas_data,
        tags, thumbnail_url, is_public, is_template, template_category,
        idempotency_key, folder_id, is_starred, workspace_id,
        status, is_deleted
    ) VALUES (
        p_project_id, p_user_id, p_title, p_canvas_size, p_description, p_canvas_data,
        p_tags, p_thumbnail_url, p_is_public, p_is_template, p_template_category,
        p_idempotency_key, p_folder_id, p_is_starred, p_workspace_id,
        'draft', FALSE
    );

    success := TRUE;
    project_id := p_project_id;
    error_code := NULL;
    RETURN NEXT;
    RETURN;
END;
$$ LANGUAGE plpgsql VOLATILE
SET search_path = 'public';

COMMENT ON FUNCTION create_project_with_limit_check IS 'WS-2: 原子创建项目 + 限额检查 (advisory lock + count + insert 在单事务内)';


-- ============================================================================
-- WS-M4: Marketplace Security Hardening
-- ============================================================================

-- 21. marketplace_listing_usage_log (素材使用记录)
-- Tracks when users use marketplace listings in their projects
CREATE TABLE IF NOT EXISTS marketplace_listing_usage_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID NOT NULL REFERENCES marketplace_listings(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    usage_type TEXT NOT NULL DEFAULT 'view' CHECK (usage_type IN ('view', 'download', 'use')),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_listing_usage_log_listing_id
ON marketplace_listing_usage_log(listing_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_listing_usage_log_user_id
ON marketplace_listing_usage_log(user_id, created_at DESC);


-- WS-M2: Atomic purchase RPC
-- Wraps credit deduction + purchase record in single transaction
-- Eliminates TOCTOU race condition between balance check and deduction
CREATE OR REPLACE FUNCTION p_purchase_listing(
    p_listing_id UUID,
    p_buyer_id TEXT,
    p_price INTEGER,
    p_idempotency_key TEXT DEFAULT NULL
)
RETURNS TABLE (
    success BOOLEAN,
    already_existed BOOLEAN,
    error_message TEXT
)
LANGUAGE plpgsql
VOLATILE
AS $$
DECLARE
    v_listing RECORD;
    v_monthly INTEGER;
    v_permanent INTEGER;
    v_deduct_monthly INTEGER;
    v_deduct_permanent INTEGER;
BEGIN
    -- Lock listing row to prevent concurrent modifications
    SELECT id, seller_id, price_credits, status, is_public, is_deleted, moderation_status, title
    INTO v_listing
    FROM marketplace_listings
    WHERE id = p_listing_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, FALSE, 'Listing not found'::TEXT;
        RETURN;
    END IF;

    -- Validate listing is purchasable
    IF v_listing.is_deleted OR NOT v_listing.is_public OR v_listing.moderation_status != 'approved' THEN
        RETURN QUERY SELECT FALSE, FALSE, 'Listing is not available for purchase'::TEXT;
        RETURN;
    END IF;

    -- Self-purchase guard
    IF v_listing.seller_id = p_buyer_id THEN
        RETURN QUERY SELECT FALSE, FALSE, 'Cannot purchase your own listing'::TEXT;
        RETURN;
    END IF;

    -- Idempotent insert: ON CONFLICT returns existing
    INSERT INTO marketplace_purchases (listing_id, user_id, price_paid, idempotency_key, purchased_at)
    VALUES (p_listing_id, p_buyer_id, p_price, p_idempotency_key, NOW())
    ON CONFLICT (user_id, listing_id) DO NOTHING;

    IF NOT FOUND THEN
        -- Purchase already existed (duplicate)
        RETURN QUERY SELECT TRUE, TRUE, NULL::TEXT;
        RETURN;
    END IF;

    -- Deduct credits if price > 0 (monthly first, then permanent)
    IF p_price > 0 THEN
        SELECT COALESCE(credits_monthly, 0), COALESCE(credits_permanent, 0)
        INTO v_monthly, v_permanent
        FROM profiles
        WHERE id = p_buyer_id
        FOR UPDATE;

        IF (v_monthly + v_permanent) < p_price THEN
            -- Insufficient credits - rollback
            RAISE EXCEPTION 'Insufficient credits: have %, need %', v_monthly + v_permanent, p_price;
        END IF;

        -- Deduct from monthly first, remainder from permanent
        v_deduct_monthly := LEAST(v_monthly, p_price);
        v_deduct_permanent := p_price - v_deduct_monthly;

        UPDATE profiles
        SET credits_monthly = credits_monthly - v_deduct_monthly,
            credits_permanent = credits_permanent - v_deduct_permanent
        WHERE id = p_buyer_id;

        -- Record credit transaction
        INSERT INTO credit_transactions (user_id, amount, transaction_type, description, idempotency_key)
        VALUES (p_buyer_id, -p_price, 'purchase', 'Purchase: ' || LEFT(v_listing.title, 50), p_idempotency_key);
    END IF;

    -- Update listing stats
    UPDATE marketplace_listings
    SET sales_count = sales_count + 1,
        purchase_count = purchase_count + 1,
        download_count = download_count + 1
    WHERE id = p_listing_id;

    RETURN QUERY SELECT TRUE, FALSE, NULL::TEXT;
END;
$$;

COMMENT ON FUNCTION p_purchase_listing IS 'WS-M2: Atomic purchase with credit deduction in single transaction';


-- ============================================================================
-- Idempotent User Creation (Webhook / JIT dual-source)
-- ============================================================================

CREATE OR REPLACE FUNCTION create_user_idempotent(
    p_user_id TEXT,
    p_email TEXT,
    p_source TEXT DEFAULT 'register',
    p_username TEXT DEFAULT NULL,
    p_first_name TEXT DEFAULT NULL,
    p_last_name TEXT DEFAULT NULL,
    p_avatar_url TEXT DEFAULT NULL,
    p_display_name TEXT DEFAULT NULL,
    p_signup_bonus INTEGER DEFAULT 0
)
RETURNS TABLE(user_profile JSONB, was_created BOOLEAN, created_by TEXT)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = 'public'
AS $$
DECLARE
    v_existing profiles%ROWTYPE;
    v_new profiles%ROWTYPE;
    v_user_code TEXT;
    v_user_count BIGINT;
    v_now TIMESTAMPTZ := CURRENT_TIMESTAMP;
    v_random_suffix TEXT;
BEGIN
    -- Step 1: Check if user already exists (lock row to prevent race)
    SELECT * INTO v_existing
    FROM profiles
    WHERE id = p_user_id::UUID
    FOR UPDATE;

    IF FOUND THEN
        -- User already exists — log duplicate attempt and return existing
        INSERT INTO user_creation_logs (user_id, source, action, metadata, created_at)
        VALUES (
            p_user_id::UUID,
            p_source,
            'duplicate_attempt',
            jsonb_build_object('attempted_source', p_source),
            v_now
        );

        RETURN QUERY SELECT
            to_jsonb(v_existing),
            FALSE,
            v_existing.created_by;
        RETURN;
    END IF;

    -- Step 2: Generate user_code (26 digits: YYMMDDHHMMSS + mmmm + UUUUUUU + RRR)
    SELECT COUNT(*) INTO v_user_count FROM profiles;
    v_random_suffix := LPAD(FLOOR(RANDOM() * 1000)::TEXT, 3, '0');

    v_user_code :=
        TO_CHAR(v_now AT TIME ZONE 'UTC', 'YYMMDDHH24MISS') ||
        LPAD(FLOOR(EXTRACT(MICROSECOND FROM v_now) / 100)::TEXT, 4, '0') ||
        LPAD((v_user_count + 1)::TEXT, 7, '0') ||
        v_random_suffix;

    -- Collision check (extremely rare but safe)
    WHILE EXISTS (SELECT 1 FROM profiles WHERE user_code = v_user_code) LOOP
        v_random_suffix := LPAD(FLOOR(RANDOM() * 1000)::TEXT, 3, '0');
        v_user_code :=
            TO_CHAR(v_now AT TIME ZONE 'UTC', 'YYMMDDHH24MISS') ||
            LPAD(FLOOR(EXTRACT(MICROSECOND FROM v_now) / 100)::TEXT, 4, '0') ||
            LPAD((v_user_count + 1)::TEXT, 7, '0') ||
            v_random_suffix;
    END LOOP;

    -- Step 3: Create new profile
    INSERT INTO profiles (
        id,
        email,
        user_code,
        username,
        first_name,
        last_name,
        avatar_url,
        display_name,
        credits_permanent,
        created_by,
        created_at,
        updated_at
    ) VALUES (
        p_user_id::UUID,
        LOWER(TRIM(p_email)),
        v_user_code,
        p_username,
        p_first_name,
        p_last_name,
        p_avatar_url,
        COALESCE(p_display_name, SPLIT_PART(p_email, '@', 1)),
        p_signup_bonus,
        p_source,
        v_now,
        v_now
    )
    RETURNING * INTO v_new;

    -- Step 4: Log successful creation
    INSERT INTO user_creation_logs (user_id, source, action, metadata, created_at)
    VALUES (
        p_user_id::UUID,
        p_source,
        'created',
        jsonb_build_object(
            'signup_bonus', p_signup_bonus,
            'user_code', v_user_code
        ),
        v_now
    );

    RETURN QUERY SELECT
        to_jsonb(v_new),
        TRUE,
        p_source;
END;
$$;

COMMENT ON FUNCTION create_user_idempotent IS 'Idempotent user creation for Webhook/JIT dual-source pattern with atomic user_code generation';


-- ============================================================================
-- Generation Task Creation (best-effort, failure only logs warning)
-- ============================================================================

CREATE OR REPLACE FUNCTION create_generation_task(
    p_task_id UUID,
    p_user_id UUID,
    p_task_type TEXT DEFAULT 'image_generation',
    p_params JSONB DEFAULT '{}'::jsonb,
    p_priority INTEGER DEFAULT 0,
    p_total_steps INTEGER DEFAULT 1
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = 'public'
AS $$
BEGIN
    INSERT INTO generation_tasks (
        id,
        user_id,
        task_type,
        parameters,
        status,
        created_at,
        updated_at
    ) VALUES (
        p_task_id,
        p_user_id,
        p_task_type,
        p_params || jsonb_build_object('priority', p_priority, 'total_steps', p_total_steps),
        'pending',
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP
    );
END;
$$;

COMMENT ON FUNCTION create_generation_task IS 'Create a generation task record; priority and total_steps stored in parameters JSONB';


-- ============================================================================
-- WS-M4 Phase A: Row Level Security (RLS) Policies
-- ============================================================================

-- marketplace_listings: sellers can manage own, public can read approved
ALTER TABLE marketplace_listings ENABLE ROW LEVEL SECURITY;

CREATE POLICY marketplace_listings_service_role ON marketplace_listings
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY marketplace_listings_select_public ON marketplace_listings
    FOR SELECT
    TO authenticated
    USING (
        (is_public = true AND is_deleted = false AND moderation_status = 'approved')
        OR seller_id = auth.uid()
    );

CREATE POLICY marketplace_listings_insert_own ON marketplace_listings
    FOR INSERT
    TO authenticated
    WITH CHECK (seller_id = auth.uid());

CREATE POLICY marketplace_listings_update_own ON marketplace_listings
    FOR UPDATE
    TO authenticated
    USING (seller_id = auth.uid())
    WITH CHECK (seller_id = auth.uid());


-- marketplace_purchases: users can only see own purchases
ALTER TABLE marketplace_purchases ENABLE ROW LEVEL SECURITY;

CREATE POLICY marketplace_purchases_service_role ON marketplace_purchases
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY marketplace_purchases_select_own ON marketplace_purchases
    FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY marketplace_purchases_insert_own ON marketplace_purchases
    FOR INSERT
    TO authenticated
    WITH CHECK (user_id = auth.uid());


-- marketplace_favorites: users can only manage own favorites
ALTER TABLE marketplace_favorites ENABLE ROW LEVEL SECURITY;

CREATE POLICY marketplace_favorites_service_role ON marketplace_favorites
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY marketplace_favorites_select_own ON marketplace_favorites
    FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY marketplace_favorites_insert_own ON marketplace_favorites
    FOR INSERT
    TO authenticated
    WITH CHECK (user_id = auth.uid());

CREATE POLICY marketplace_favorites_delete_own ON marketplace_favorites
    FOR DELETE
    TO authenticated
    USING (user_id = auth.uid());


-- marketplace_reports: users can see own reports
ALTER TABLE marketplace_reports ENABLE ROW LEVEL SECURITY;

CREATE POLICY marketplace_reports_service_role ON marketplace_reports
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY marketplace_reports_select_own ON marketplace_reports
    FOR SELECT
    TO authenticated
    USING (reporter_id = auth.uid());

CREATE POLICY marketplace_reports_insert_own ON marketplace_reports
    FOR INSERT
    TO authenticated
    WITH CHECK (reporter_id = auth.uid());


-- marketplace_reviews: public read, users manage own
ALTER TABLE marketplace_reviews ENABLE ROW LEVEL SECURITY;

CREATE POLICY marketplace_reviews_service_role ON marketplace_reviews
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY marketplace_reviews_select_public ON marketplace_reviews
    FOR SELECT
    TO authenticated
    USING (is_deleted = false);

CREATE POLICY marketplace_reviews_insert_own ON marketplace_reviews
    FOR INSERT
    TO authenticated
    WITH CHECK (reviewer_id = auth.uid());

CREATE POLICY marketplace_reviews_update_own ON marketplace_reviews
    FOR UPDATE
    TO authenticated
    USING (reviewer_id = auth.uid())
    WITH CHECK (reviewer_id = auth.uid());


-- marketplace_listing_usage_log: users can see own usage
ALTER TABLE marketplace_listing_usage_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY marketplace_usage_log_service_role ON marketplace_listing_usage_log
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY marketplace_usage_log_select_own ON marketplace_listing_usage_log
    FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY marketplace_usage_log_insert_own ON marketplace_listing_usage_log
    FOR INSERT
    TO authenticated
    WITH CHECK (user_id = auth.uid());


-- ============================================================================
-- WS-M4 Phase C: Missing Indexes
-- ============================================================================

-- marketplace_purchases: fast lookup by user and listing
CREATE INDEX IF NOT EXISTS idx_marketplace_purchases_user_id
ON marketplace_purchases(user_id, purchased_at DESC);

CREATE INDEX IF NOT EXISTS idx_marketplace_purchases_listing_id
ON marketplace_purchases(listing_id);

-- marketplace_favorites: fast unique check
CREATE INDEX IF NOT EXISTS idx_marketplace_favorites_user_listing
ON marketplace_favorites(user_id, listing_id)
WHERE is_deleted = false;

-- marketplace_reviews: fast lookup by listing
CREATE INDEX IF NOT EXISTS idx_marketplace_reviews_listing_id
ON marketplace_reviews(listing_id)
WHERE is_deleted = false;

-- marketplace_listings: seller lookup with soft-delete filter
CREATE INDEX IF NOT EXISTS idx_marketplace_listings_seller_id
ON marketplace_listings(seller_id, created_at DESC)
WHERE is_deleted = false;

-- marketplace_listings: published listings (common query path)
CREATE INDEX IF NOT EXISTS idx_marketplace_listings_published
ON marketplace_listings(is_public, is_deleted, moderation_status, created_at DESC)
WHERE is_public = true AND is_deleted = false AND moderation_status = 'approved';


-- ============================================================================
-- RPC: get_or_create_default_workspace
-- 原子性获取或创建用户的默认 workspace，消除并发竞态条件
-- ============================================================================
CREATE OR REPLACE FUNCTION get_or_create_default_workspace(p_owner_id UUID)
RETURNS JSON
LANGUAGE plpgsql
AS $$
DECLARE
    v_workspace RECORD;
BEGIN
    -- Step 1: 尝试获取已有的 default workspace
    SELECT * INTO v_workspace
    FROM workspaces
    WHERE owner_id = p_owner_id
      AND is_default = TRUE
      AND is_active = TRUE
    LIMIT 1;

    -- Step 2: 如果找到，直接返回
    IF FOUND THEN
        RETURN json_build_object(
            'id', v_workspace.id,
            'name', v_workspace.name,
            'description', v_workspace.description,
            'owner_id', v_workspace.owner_id,
            'is_default', v_workspace.is_default,
            'is_personal', v_workspace.is_personal,
            'is_active', v_workspace.is_active,
            'created_at', v_workspace.created_at,
            'updated_at', v_workspace.updated_at
        );
    END IF;

    -- Step 3: 不存在，尝试插入（唯一索引保证并发安全）
    INSERT INTO workspaces (name, owner_id, is_default, is_personal, is_active)
    VALUES ('My Workspace', p_owner_id, TRUE, TRUE, TRUE)
    ON CONFLICT (owner_id) WHERE is_default = TRUE AND is_active = TRUE
    DO NOTHING;

    -- Step 4: 无论是自己插入的还是并发插入的，都能查到
    SELECT * INTO v_workspace
    FROM workspaces
    WHERE owner_id = p_owner_id
      AND is_default = TRUE
      AND is_active = TRUE
    LIMIT 1;

    RETURN json_build_object(
        'id', v_workspace.id,
        'name', v_workspace.name,
        'description', v_workspace.description,
        'owner_id', v_workspace.owner_id,
        'is_default', v_workspace.is_default,
        'is_personal', v_workspace.is_personal,
        'is_active', v_workspace.is_active,
        'created_at', v_workspace.created_at,
        'updated_at', v_workspace.updated_at
    );
END;
$$
SET search_path = 'public';

COMMENT ON FUNCTION get_or_create_default_workspace IS '原子性获取或创建用户默认 workspace，防止并发重复创建';


-- ============================================================================
-- MIG-002: Entitlement Phase 1 新表
-- ============================================================================

-- ----------------------------------------------------------------------------
-- free_quota_usage (AI 免费配额追踪)
-- 追踪免费用户的每日/每月 AI 功能使用量, 实现 "t1 每天 3 次免费 AI 生成" 等限制
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS free_quota_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    feature_key VARCHAR(50) NOT NULL,         -- 对应 FeatureKey: ai_generate_asset, smart_scan 等
    period_start DATE NOT NULL,               -- 配额周期起始日 (daily=当天, monthly=月初)
    period_type VARCHAR(20) NOT NULL DEFAULT 'daily' CHECK (period_type IN ('daily', 'monthly')),
    used_count INTEGER NOT NULL DEFAULT 0 CHECK (used_count >= 0),
    quota_limit INTEGER NOT NULL CHECK (quota_limit > 0),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, feature_key, period_start, period_type)
);

CREATE INDEX IF NOT EXISTS idx_fqu_user_period
    ON free_quota_usage(user_id, period_start);

-- ----------------------------------------------------------------------------
-- reconciliation_results (积分对账审计)
-- 每日/手动对账任务的结果记录, 用于发现 credits_monthly + credits_permanent 与
-- credit_transactions 之间的不一致
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reconciliation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reconciliation_date DATE NOT NULL,
    user_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
    expected_monthly INTEGER,
    actual_monthly INTEGER,
    expected_permanent INTEGER,
    actual_permanent INTEGER,
    discrepancy_amount INTEGER NOT NULL DEFAULT 0,
    resolution_status VARCHAR(20) DEFAULT 'pending'
        CHECK (resolution_status IN ('pending', 'resolved', 'ignored', 'escalated')),
    resolution_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recon_date
    ON reconciliation_results(reconciliation_date);
CREATE INDEX IF NOT EXISTS idx_recon_status_pending
    ON reconciliation_results(resolution_status) WHERE resolution_status = 'pending';


-- ============================================================================
-- 提交事务
-- ============================================================================
COMMIT;
