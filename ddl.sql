-- ==============================================================================
-- Make Decodables 数据库完整初始化脚本 (v3.2 - Admin Analytics + System Config)
-- 包含：核心表结构 + 最终版 RLS 安全策略
-- 
-- 重要更新 (v3.0):
-- - Credits 分桶：credits_monthly + credits_permanent
-- - Marketplace 表：marketplace_listings, user_purchases
-- - 通知系统：notifications
-- - 折扣系统：user_discounts
-- - system_resources 增加 allowed_tiers
--
-- 重要更新 (v3.1):
-- - assets 表增加 metadata 字段：存储扫描结果、画布元素等结构化数据
-- - assets.type 支持 'scanned' 类型（AI Smart Scan OCR）
--
-- 重要更新 (v3.2):
-- - admin_operation_logs 表：管理员操作审计日志
-- - user_events 表：用户行为追踪事件
-- - aggregated_stats 表：预计算统计数据（定时任务聚合）
-- - system_config 表：动态系统配置（限频、Analytics 等）
-- - notifications 表增加 notification_type 字段
-- ==============================================================================

-- ==========================================
-- Part 1: 建表 (Schema Definition)
-- ==========================================

-- 1. 用户档案表 (User Profiles)
create table if not exists profiles (
  id text primary key, -- 对应 Clerk user_id
  email text,
  username text,
  avatar_url text,
  
  -- 用户唯一标识码（格式: YYYYMMDDHHMMSS+毫秒+6位序号）
  -- 例如: 20251230143025123000001
  user_code text unique,

  -- Credits 分桶（重要）
  credits_monthly int default 0,    -- 订阅每月赠送：每月刷新，不结转
  credits_permanent int default 0,  -- 用户购买/售卖获得：永不过期

  tier text default 'free', -- 'free', 'starter', 'pro'

  -- 订阅状态（用于"会员有效"判断）
  subscription_status text default 'inactive', -- 'active' | 'inactive' | 'past_due' | 'canceled' | 'trialing'
  subscription_valid_until timestamptz,        -- 可选：用于离线判定
  monthly_credits_cycle_anchor timestamptz,    -- 可选：用于每月刷新基准点（与 Stripe 周期对齐）

  stripe_customer_id text,
  role text default 'user', -- 'user', 'admin'
  created_at timestamptz default now()
);

-- 2. 用户折扣表 (User Discounts)
create table if not exists user_discounts (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id) not null,
  discount_percent int not null,
  valid_until timestamptz,
  target_plan text,
  created_at timestamptz default now()
);

-- 3. 积分流水表 (Financial Ledger)
create table if not exists credit_transactions (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id) not null,

  amount int not null, -- 变动值 (+100, -50)

  -- 标记本次变动影响哪个桶（monthly/permanent），便于审计
  bucket text not null default 'permanent', -- 'monthly' | 'permanent'

  balance_monthly_after int not null default 0,
  balance_permanent_after int not null default 0,

  type text not null, -- 'signup_bonus', 'topup_purchase', 'sub_grant', 'generation', 'ocr', 'market_purchase', 'market_sale', 'admin_adj'
  description text,
  created_at timestamptz default now()
);

-- 4. 项目表 (User Projects)
create table if not exists projects (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id) not null,
  title text default 'My Magic Story',
  canvas_data jsonb default '{}'::jsonb, -- Fabric.js JSON
  thumbnail_url text,
  last_downloaded_hash text, -- 仅用于缓存/版本识别（不参与扣费）
  is_deleted boolean default false,

  -- 可选：用于快速提示项目包含锁定资源
  contains_locked_elements boolean default false,

  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- 5. 市场商品表 (Marketplace Listings)
-- PRD 定义: 强制审核后上架 + 定价上限 + 使用次数统计
create table if not exists marketplace_listings (
  id uuid default gen_random_uuid() primary key,
  seller_id text references profiles(id), -- NULL = 官方资源
  title text not null,
  description text,
  thumbnail_url text not null,
  resource_url text not null,
  resource_type text not null, -- 'template' | 'asset'（可细分 'image'|'sticker'）
  price_credits int not null default 0, -- 0..500
  allowed_tiers text[] not null default '{free, starter, pro}', -- 分级访问与购买

  usage_count bigint default 0, -- 使用次数（排行榜用）
  sales_count int default 0, -- 销售次数

  is_public boolean default false,
  is_deleted boolean default false,

  -- 审核相关字段（PRD 强制审核后上架）
  moderation_status text not null default 'draft', -- 'draft'|'pending'|'approved'|'rejected'
  moderation_note text, -- 拒绝原因或管理员备注
  moderated_by text references profiles(id), -- 审核人
  moderated_at timestamptz, -- 审核时间

  created_at timestamptz default now()
);

-- 6. 用户已购资源表 (User Purchases)
create table if not exists user_purchases (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id) not null,
  listing_id uuid references marketplace_listings(id) not null,
  price_paid int not null,
  purchased_at timestamptz default now(),
  unique(user_id, listing_id)
);

-- 7. 用户素材表 (User Assets)
-- PRD 定义: 存储用户上传、AI生成、OCR扫描的图片资源
-- type 字段说明:
--   'uploaded'     - 用户手动上传的图片
--   'ai_generated' - AI Generate 生成的图片
--   'scanned'      - AI Smart Scan (OCR) 扫描的图片
-- metadata 字段说明 (仅 scanned 类型使用):
--   source_image_url: 原始扫描图片 URL
--   ocr_result: { blocks: [...], summary: "..." } - 结构化识别结果
--   canvas_elements: [...] - 预转换的画布元素
create table if not exists assets (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id) not null,
  project_id uuid references projects(id), -- 可为空，上传时关联项目
  url text not null,
  type text not null, -- 'uploaded' | 'ai_generated' | 'scanned'
  prompt text, -- AI生成时的提示词
  metadata jsonb, -- 扫描结果、画布元素等结构化数据 (v3.1 新增)
  is_deleted boolean default false,
  created_at timestamptz default now()
);
create index if not exists idx_assets_user_proj on assets(user_id, project_id);

-- 8. 站内信/通知表 (Notifications)
create table if not exists notifications (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id), -- NULL = 全员广播
  target_group text, -- 'all', 'free', 'starter', 'pro'
  notification_type text default 'system', -- 'system', 'promotion', 'update', 'warning'
  title text not null,
  content text not null,
  is_read boolean default false,
  created_at timestamptz default now()
);

-- 9. 系统资源表 (System Resources)
create table if not exists system_resources (
  id uuid default gen_random_uuid() primary key,
  type text not null, -- 'sticker', 'template'
  category text,
  url text not null,
  allowed_tiers text[] default '{free, starter, pro}',
  created_at timestamptz default now()
);

-- 10. 行为日志表 (User Behavior Logs)
create table if not exists activity_logs (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id),
  action text not null,
  metadata jsonb,
  created_at timestamptz default now()
);

-- 11. 客服与运营记录表 (Support & Admin Ops)
create table if not exists support_tickets (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id),
  admin_id text references profiles(id),
  category text not null,
  content text,
  metadata jsonb,
  status text default 'closed',
  created_at timestamptz default now()
);

-- 12. Listing 使用记录表 (Listing Usage - 去重计数)
-- PRD 定义: 用于统计 usage_count，去重规则 (listing_id, user_id, project_id)
create table if not exists listing_usage (
  id uuid default gen_random_uuid() primary key,
  listing_id uuid references marketplace_listings(id) not null,
  used_by_user_id text references profiles(id) not null,
  project_id uuid references projects(id) not null,
  used_at timestamptz default now(),
  unique(listing_id, used_by_user_id, project_id)
);

-- 13. 排行榜快照表 (Leaderboard Snapshots - 缓存榜单)
-- PRD 定义: 可选，用于缓存周期性榜单数据
create table if not exists leaderboard_snapshots (
  id uuid default gen_random_uuid() primary key,
  period_start date not null,
  period_end date not null,
  board_type text not null, -- 'all' | 'template' | 'asset'
  top_list jsonb not null, -- [{listing_id, usage_count, rank}, ...]
  created_at timestamptz default now(),
  unique(period_start, period_end, board_type)
);

-- 14. 管理员操作日志表 (Admin Operation Logs - 审计日志)
-- v3.2 新增: 用于记录所有管理员操作，便于对账和审计
create table if not exists admin_operation_logs (
  id uuid default gen_random_uuid() primary key,
  admin_id text not null references profiles(id),
  operation_type text not null, -- 'credit_adjust', 'tier_change', 'refund', 'subscription_cancel', etc.
  target_user_id text references profiles(id),
  details text,
  reason text,
  created_at timestamptz default now()
);
create index if not exists idx_admin_logs_created_at on admin_operation_logs(created_at desc);
create index if not exists idx_admin_logs_operation_type on admin_operation_logs(operation_type);
create index if not exists idx_admin_logs_admin_id on admin_operation_logs(admin_id);
create index if not exists idx_admin_logs_target_user on admin_operation_logs(target_user_id);

-- 15. 用户行为事件表 (User Events - 用户行为追踪)
-- v3.2 新增: 用于追踪用户行为，支持分析和优化
create table if not exists user_events (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id), -- 可为空（匿名用户）
  event_type text not null,
  properties jsonb default '{}',
  session_id text,
  created_at timestamptz default now()
);
create index if not exists idx_user_events_created_at on user_events(created_at desc);
create index if not exists idx_user_events_event_type on user_events(event_type);
create index if not exists idx_user_events_user_id on user_events(user_id);
create index if not exists idx_user_events_session on user_events(session_id);
create index if not exists idx_user_events_properties on user_events using gin(properties);

-- 16. 聚合统计表 (Aggregated Stats - 预计算统计数据)
-- v3.2 新增: 用于存储定时任务预计算的统计数据
create table if not exists aggregated_stats (
  id uuid default gen_random_uuid() primary key,
  date date not null,
  stat_type text not null, -- 'daily_users', 'daily_revenue', 'daily_projects', etc.
  data jsonb not null default '{}',
  updated_at timestamptz default now(),
  unique(date, stat_type)
);
create index if not exists idx_agg_stats_date on aggregated_stats(date desc);
create index if not exists idx_agg_stats_type on aggregated_stats(stat_type);
create index if not exists idx_agg_stats_date_type on aggregated_stats(date desc, stat_type);

-- 17. 系统配置表 (System Config - 动态系统参数)
-- v3.2 新增: 用于存储可动态调整的系统参数（限频、Analytics 等）
create table if not exists system_config (
  id uuid default gen_random_uuid() primary key,
  config_key text unique not null,
  config_value jsonb not null,
  category text not null default 'general', -- 'rate_limit', 'analytics', 'system'
  description text,
  is_active boolean default true,
  updated_at timestamptz default now(),
  updated_by text -- 最后修改的管理员ID
);
create index if not exists idx_system_config_key on system_config(config_key);
create index if not exists idx_system_config_category on system_config(category);

-- ==========================================
-- Part 2: RLS 安全策略配置
-- ==========================================
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_discounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE marketplace_listings ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_purchases ENABLE ROW LEVEL SECURITY;
ALTER TABLE assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_resources ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE listing_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE leaderboard_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_operation_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE aggregated_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_config ENABLE ROW LEVEL SECURITY;

create or replace function is_admin() returns boolean language sql security definer as $$
select exists (
  select 1 from profiles
  where id = (select auth.jwt() ->> 'sub') and role = 'admin'
);
$$;

-- [Profiles]
drop policy if exists "View profiles" on profiles;
create policy "View profiles" on profiles for select
using ((select auth.jwt() ->> 'sub') = id or is_admin());

drop policy if exists "Update profiles" on profiles;
create policy "Update profiles" on profiles for update
using ((select auth.jwt() ->> 'sub') = id);

drop policy if exists "Insert profiles" on profiles;
create policy "Insert profiles" on profiles for insert
with check ((select auth.jwt() ->> 'sub') = id);

-- [User Discounts]
drop policy if exists "Users read own discounts" on user_discounts;
create policy "Users read own discounts" on user_discounts for select
using ((select auth.jwt() ->> 'sub') = user_id or is_admin());

-- [Projects]
drop policy if exists "Users can CRUD own projects" on projects;
create policy "Users can CRUD own projects" on projects for all
using ((select auth.jwt() ->> 'sub') = user_id);

-- [Marketplace Listings]
drop policy if exists "Read Listings" on marketplace_listings;
create policy "Read Listings" on marketplace_listings for select
using (is_public = true or (select auth.jwt() ->> 'sub') = seller_id or is_admin());

drop policy if exists "Manage Listings" on marketplace_listings;
create policy "Manage Listings" on marketplace_listings for update
using ((select auth.jwt() ->> 'sub') = seller_id);

drop policy if exists "Insert Listings" on marketplace_listings;
create policy "Insert Listings" on marketplace_listings for insert
with check ((select auth.jwt() ->> 'sub') = seller_id);

-- [User Purchases]
drop policy if exists "Read Purchases" on user_purchases;
create policy "Read Purchases" on user_purchases for select
using ((select auth.jwt() ->> 'sub') = user_id);

drop policy if exists "Insert Purchases" on user_purchases;
create policy "Insert Purchases" on user_purchases for insert
with check ((select auth.jwt() ->> 'sub') = user_id);

-- [Assets]
drop policy if exists "Users can CRUD own assets" on assets;
create policy "Users can CRUD own assets" on assets for all
using ((select auth.jwt() ->> 'sub') = user_id);

-- [Notifications]
drop policy if exists "Read Notifications" on notifications;
create policy "Read Notifications" on notifications for select
using (user_id = (select auth.jwt() ->> 'sub') or user_id is null);

-- [Credit Transactions]
drop policy if exists "Users view own txs or Admin view all" on credit_transactions;
create policy "Users view own txs or Admin view all" on credit_transactions for select
using ((select auth.jwt() ->> 'sub') = user_id or is_admin());

-- [System Resources]
drop policy if exists "Public can view system resources" on system_resources;
create policy "Public can view system resources" on system_resources for select
using (true);

-- [Activity Logs]
drop policy if exists "Users can insert own logs" on activity_logs;
create policy "Users can insert own logs" on activity_logs for insert
with check ((select auth.jwt() ->> 'sub') = user_id);

drop policy if exists "Users view own logs or Admin view all" on activity_logs;
create policy "Users view own logs or Admin view all" on activity_logs for select
using ((select auth.jwt() ->> 'sub') = user_id or is_admin());

-- [Support Tickets]
drop policy if exists "Users CRUD own tickets or Admin manage all" on support_tickets;
create policy "Users CRUD own tickets or Admin manage all" on support_tickets for all
using ((select auth.jwt() ->> 'sub') = user_id or is_admin());

-- [Listing Usage]
drop policy if exists "Users can insert own usage" on listing_usage;
create policy "Users can insert own usage" on listing_usage for insert
with check ((select auth.jwt() ->> 'sub') = used_by_user_id);

drop policy if exists "Users view own usage or Admin view all" on listing_usage;
create policy "Users view own usage or Admin view all" on listing_usage for select
using ((select auth.jwt() ->> 'sub') = used_by_user_id or is_admin());

-- [Leaderboard Snapshots]
drop policy if exists "Public can view leaderboard" on leaderboard_snapshots;
create policy "Public can view leaderboard" on leaderboard_snapshots for select
using (true);

-- [Admin Operation Logs] (v3.2)
-- 只有 service_role 可以访问（后端通过 service key 访问）
drop policy if exists "Service role full access to admin_logs" on admin_operation_logs;
create policy "Service role full access to admin_logs" on admin_operation_logs for all
to service_role
using (true)
with check (true);

-- [User Events] (v3.2)
-- Service role 完全访问
drop policy if exists "Service role full access to user_events" on user_events;
create policy "Service role full access to user_events" on user_events for all
to service_role
using (true)
with check (true);

-- [Aggregated Stats] (v3.2)
-- 只有 service_role 可以访问
drop policy if exists "Service role full access to aggregated_stats" on aggregated_stats;
create policy "Service role full access to aggregated_stats" on aggregated_stats for all
to service_role
using (true)
with check (true);

-- [System Config] (v3.2)
-- 只有 service_role 可以访问
drop policy if exists "Service role full access to system_config" on system_config;
create policy "Service role full access to system_config" on system_config for all
to service_role
using (true)
with check (true);

-- ==========================================
-- Part 3: 迁移脚本（如果从旧版本升级）
-- ==========================================
-- 如果你需要从旧版本迁移，请运行以下命令：

-- 1. 添加新列到 profiles (v3.0)
-- ALTER TABLE profiles ADD COLUMN IF NOT EXISTS credits_monthly int default 0;
-- ALTER TABLE profiles ADD COLUMN IF NOT EXISTS credits_permanent int default 0;
-- ALTER TABLE profiles ADD COLUMN IF NOT EXISTS subscription_status text default 'inactive';
-- ALTER TABLE profiles ADD COLUMN IF NOT EXISTS subscription_valid_until timestamptz;
-- ALTER TABLE profiles ADD COLUMN IF NOT EXISTS monthly_credits_cycle_anchor timestamptz;

-- 2. 迁移旧的 credits 到 credits_permanent (v3.0)
-- UPDATE profiles SET credits_permanent = COALESCE(credits, 0) WHERE credits_permanent = 0;

-- 3. 添加新列到 credit_transactions (v3.0)
-- ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS bucket text default 'permanent';
-- ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS balance_monthly_after int default 0;
-- ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS balance_permanent_after int default 0;

-- 4. 更新旧的 credit_transactions 记录 (v3.0)
-- UPDATE credit_transactions SET balance_permanent_after = balance_after WHERE balance_permanent_after = 0;

-- 5. 添加 allowed_tiers 到 system_resources (v3.0)
-- ALTER TABLE system_resources ADD COLUMN IF NOT EXISTS allowed_tiers text[] default '{free, starter, pro}';
-- UPDATE system_resources SET allowed_tiers = CASE WHEN is_pro_only THEN '{pro}' ELSE '{free, starter, pro}' END;

-- ==========================================
-- Part 4: v3.1 迁移脚本（PRD 完整对齐 + Advanced OCR）
-- ==========================================
-- 如果从旧版本升级，请运行以下迁移命令：

-- 1. marketplace_listings 表新增字段（审核系统 + 使用统计）
ALTER TABLE marketplace_listings ADD COLUMN IF NOT EXISTS usage_count bigint default 0;
ALTER TABLE marketplace_listings ADD COLUMN IF NOT EXISTS moderation_status text not null default 'draft';
ALTER TABLE marketplace_listings ADD COLUMN IF NOT EXISTS moderation_note text;
ALTER TABLE marketplace_listings ADD COLUMN IF NOT EXISTS moderated_by text references profiles(id);
ALTER TABLE marketplace_listings ADD COLUMN IF NOT EXISTS moderated_at timestamptz;

-- 2. assets 表新增字段（OCR 扫描结果）
ALTER TABLE assets ADD COLUMN IF NOT EXISTS metadata jsonb;

-- 3. 创建 listing_usage 表（如果不存在）
CREATE TABLE IF NOT EXISTS listing_usage (
  id uuid default gen_random_uuid() primary key,
  listing_id uuid references marketplace_listings(id) not null,
  used_by_user_id text references profiles(id) not null,
  project_id uuid references projects(id) not null,
  used_at timestamptz default now(),
  unique(listing_id, used_by_user_id, project_id)
);
ALTER TABLE listing_usage ENABLE ROW LEVEL SECURITY;

-- 4. 创建 leaderboard_snapshots 表（如果不存在）
CREATE TABLE IF NOT EXISTS leaderboard_snapshots (
  id uuid default gen_random_uuid() primary key,
  period_start date not null,
  period_end date not null,
  board_type text not null,
  top_list jsonb not null,
  created_at timestamptz default now(),
  unique(period_start, period_end, board_type)
);
ALTER TABLE leaderboard_snapshots ENABLE ROW LEVEL SECURITY;

-- 5. 将旧的 'user_upload' type 更新为 'uploaded'（如果有旧数据）
UPDATE assets SET type = 'uploaded' WHERE type = 'user_upload';

-- 6. 将没有审核状态的旧 listings 设置为 approved（已上线数据）
UPDATE marketplace_listings SET moderation_status = 'approved' WHERE moderation_status IS NULL AND is_public = true;

-- ==========================================
-- Part 5: v3.2 迁移脚本（Admin Analytics + System Config）
-- ==========================================
-- 如果从旧版本升级，请运行以下迁移命令：

-- 1. notifications 表新增 notification_type 字段
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS notification_type TEXT DEFAULT 'system';
CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(notification_type);

-- 2. 创建 admin_operation_logs 表（如果不存在）
CREATE TABLE IF NOT EXISTS admin_operation_logs (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  admin_id TEXT NOT NULL REFERENCES profiles(id),
  operation_type TEXT NOT NULL,
  target_user_id TEXT REFERENCES profiles(id),
  details TEXT,
  reason TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_admin_logs_created_at ON admin_operation_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_logs_operation_type ON admin_operation_logs(operation_type);
CREATE INDEX IF NOT EXISTS idx_admin_logs_admin_id ON admin_operation_logs(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_logs_target_user ON admin_operation_logs(target_user_id);
ALTER TABLE admin_operation_logs ENABLE ROW LEVEL SECURITY;

-- 3. 创建 user_events 表（如果不存在）
CREATE TABLE IF NOT EXISTS user_events (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id TEXT REFERENCES profiles(id),
  event_type TEXT NOT NULL,
  properties JSONB DEFAULT '{}',
  session_id TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_user_events_created_at ON user_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_events_event_type ON user_events(event_type);
CREATE INDEX IF NOT EXISTS idx_user_events_user_id ON user_events(user_id);
CREATE INDEX IF NOT EXISTS idx_user_events_session ON user_events(session_id);
CREATE INDEX IF NOT EXISTS idx_user_events_properties ON user_events USING GIN(properties);
ALTER TABLE user_events ENABLE ROW LEVEL SECURITY;

-- 4. 创建 aggregated_stats 表（如果不存在）
CREATE TABLE IF NOT EXISTS aggregated_stats (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  date DATE NOT NULL,
  stat_type TEXT NOT NULL,
  data JSONB NOT NULL DEFAULT '{}',
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(date, stat_type)
);
CREATE INDEX IF NOT EXISTS idx_agg_stats_date ON aggregated_stats(date DESC);
CREATE INDEX IF NOT EXISTS idx_agg_stats_type ON aggregated_stats(stat_type);
CREATE INDEX IF NOT EXISTS idx_agg_stats_date_type ON aggregated_stats(date DESC, stat_type);
ALTER TABLE aggregated_stats ENABLE ROW LEVEL SECURITY;

-- 5. 创建 system_config 表（如果不存在）
CREATE TABLE IF NOT EXISTS system_config (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  config_key TEXT UNIQUE NOT NULL,
  config_value JSONB NOT NULL,
  category TEXT NOT NULL DEFAULT 'general',
  description TEXT,
  is_active BOOLEAN DEFAULT true,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  updated_by TEXT
);
CREATE INDEX IF NOT EXISTS idx_system_config_key ON system_config(config_key);
CREATE INDEX IF NOT EXISTS idx_system_config_category ON system_config(category);
ALTER TABLE system_config ENABLE ROW LEVEL SECURITY;

-- 6. RLS 策略 (只有 service_role 可以访问)
DROP POLICY IF EXISTS "Service role full access to admin_logs" ON admin_operation_logs;
CREATE POLICY "Service role full access to admin_logs" ON admin_operation_logs FOR ALL
TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role full access to user_events" ON user_events;
CREATE POLICY "Service role full access to user_events" ON user_events FOR ALL
TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role full access to aggregated_stats" ON aggregated_stats;
CREATE POLICY "Service role full access to aggregated_stats" ON aggregated_stats FOR ALL
TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role full access to system_config" ON system_config;
CREATE POLICY "Service role full access to system_config" ON system_config FOR ALL
TO service_role USING (true) WITH CHECK (true);

-- 7. 创建系统配置相关的函数
CREATE OR REPLACE FUNCTION update_system_config_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_system_config_timestamp ON system_config;
CREATE TRIGGER trigger_update_system_config_timestamp
    BEFORE UPDATE ON system_config
    FOR EACH ROW
    EXECUTE FUNCTION update_system_config_timestamp();

-- 8. 创建获取限频配置的函数
CREATE OR REPLACE FUNCTION get_rate_limit_config(p_config_key TEXT)
RETURNS JSONB AS $$
DECLARE
    v_config JSONB;
BEGIN
    SELECT config_value INTO v_config
    FROM system_config
    WHERE config_key = p_config_key AND is_active = true;
    
    IF v_config IS NULL THEN
        SELECT config_value INTO v_config
        FROM system_config
        WHERE config_key = 'rate_limit.global.default' AND is_active = true;
    END IF;
    
    RETURN COALESCE(v_config, '{"limit": 100, "window": "minute", "enabled": true}'::JSONB);
END;
$$ LANGUAGE plpgsql;

-- 9. 创建聚合统计相关的函数
CREATE OR REPLACE FUNCTION get_latest_stats(p_stat_type VARCHAR)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT data INTO result
    FROM aggregated_stats
    WHERE stat_type = p_stat_type
    ORDER BY date DESC
    LIMIT 1;
    
    RETURN COALESCE(result, '{}'::JSONB);
END;
$$;

CREATE OR REPLACE FUNCTION get_stats_range(
    p_stat_type VARCHAR,
    p_start_date DATE,
    p_end_date DATE DEFAULT CURRENT_DATE
)
RETURNS TABLE (
    date DATE,
    data JSONB
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT a.date, a.data
    FROM aggregated_stats a
    WHERE a.stat_type = p_stat_type
      AND a.date >= p_start_date
      AND a.date <= p_end_date
    ORDER BY a.date ASC;
END;
$$;

-- 10. 为现有表添加优化索引
CREATE INDEX IF NOT EXISTS idx_profiles_tier ON profiles(tier);
CREATE INDEX IF NOT EXISTS idx_profiles_created_at ON profiles(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_profiles_subscription_status ON profiles(subscription_status);

CREATE INDEX IF NOT EXISTS idx_credit_tx_bucket ON credit_transactions(bucket);
CREATE INDEX IF NOT EXISTS idx_credit_tx_type ON credit_transactions(type);
CREATE INDEX IF NOT EXISTS idx_credit_tx_created_at ON credit_transactions(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_activity_logs_action ON activity_logs(action);
CREATE INDEX IF NOT EXISTS idx_activity_logs_created_at ON activity_logs(created_at DESC);

-- 11. 插入默认的系统配置（限频配置）
INSERT INTO system_config (config_key, config_value, category, description) VALUES
-- 支付相关 (高风险，严格限制)
('rate_limit.payment.checkout', '{"limit": 5, "window": "minute", "enabled": true}', 'rate_limit', '支付结账接口限频'),
('rate_limit.payment.portal', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', '账单门户接口限频'),
('rate_limit.marketplace.purchase', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', '市场购买接口限频'),
-- AI 生成相关 (资源密集)
('rate_limit.generate.story', '{"limit": 20, "window": "minute", "enabled": true}', 'rate_limit', 'AI故事生成限频'),
('rate_limit.generate.images', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', 'AI图片生成限频'),
('rate_limit.tools.ocr', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', 'OCR识别限频'),
-- 导出相关 (服务器资源消耗)
('rate_limit.export.pdf', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', 'PDF导出限频'),
('rate_limit.export.zip', '{"limit": 5, "window": "minute", "enabled": true}', 'rate_limit', 'ZIP导出限频'),
('rate_limit.export.preview', '{"limit": 20, "window": "minute", "enabled": true}', 'rate_limit', '预览图生成限频'),
-- 用户操作
('rate_limit.projects.create', '{"limit": 20, "window": "minute", "enabled": true}', 'rate_limit', '创建项目限频'),
('rate_limit.assets.upload', '{"limit": 20, "window": "minute", "enabled": true}', 'rate_limit', '素材上传限频'),
('rate_limit.marketplace.publish', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', '商品发布限频'),
-- 公开接口 (防滥用)
('rate_limit.support.email', '{"limit": 3, "window": "minute", "enabled": true}', 'rate_limit', '工单提交限频'),
('rate_limit.contact.form', '{"limit": 3, "window": "minute", "enabled": true}', 'rate_limit', '联系表单限频'),
('rate_limit.feedback.submit', '{"limit": 3, "window": "minute", "enabled": true}', 'rate_limit', '反馈提交限频'),
-- Admin 操作
('rate_limit.admin.credits', '{"limit": 30, "window": "minute", "enabled": true}', 'rate_limit', 'Admin积分调整限频'),
('rate_limit.admin.tier', '{"limit": 30, "window": "minute", "enabled": true}', 'rate_limit', 'Admin等级更新限频'),
('rate_limit.admin.refund', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', 'Admin退款限频'),
('rate_limit.admin.subscription', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', 'Admin订阅操作限频'),
('rate_limit.admin.broadcast', '{"limit": 5, "window": "minute", "enabled": true}', 'rate_limit', 'Admin群发限频'),
-- 查询接口
('rate_limit.admin.search', '{"limit": 60, "window": "minute", "enabled": true}', 'rate_limit', 'Admin搜索限频'),
('rate_limit.marketplace.list', '{"limit": 60, "window": "minute", "enabled": true}', 'rate_limit', '市场列表限频'),
('rate_limit.analytics.events', '{"limit": 60, "window": "minute", "enabled": true}', 'rate_limit', '事件上报限频'),
-- 全局默认配置
('rate_limit.global.default', '{"limit": 100, "window": "minute", "enabled": true}', 'rate_limit', '全局默认限频'),
('rate_limit.global.enabled', '{"enabled": true}', 'rate_limit', '是否启用全局限频'),
-- Analytics 配置
('analytics.enabled', '{"enabled": true}', 'analytics', '是否启用用户行为追踪'),
('analytics.sampling_rate', '{"critical": 1.0, "important": 1.0, "normal": 0.3, "debug": 0.0}', 'analytics', '事件采样率'),
('analytics.min_level', '{"level": "normal"}', 'analytics', '最低追踪级别')
ON CONFLICT (config_key) DO NOTHING;
