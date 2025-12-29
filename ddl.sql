-- ==============================================================================
-- Make Decodables 数据库完整初始化脚本 (v3.0 - PRD Final)
-- 包含：核心表结构 + 最终版 RLS 安全策略
-- 
-- 重要更新 (v3.0):
-- - Credits 分桶：credits_monthly + credits_permanent
-- - Marketplace 表：marketplace_listings, user_purchases
-- - 通知系统：notifications
-- - 折扣系统：user_discounts
-- - system_resources 增加 allowed_tiers
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
create table if not exists marketplace_listings (
  id uuid default gen_random_uuid() primary key,
  seller_id text references profiles(id), -- NULL = 官方资源
  title text not null,
  description text,
  thumbnail_url text not null,
  resource_url text not null,
  resource_type text not null, -- 'template', 'sticker', 'image'
  price_credits int default 0, -- 0 = Free

  allowed_tiers text[] default '{free, starter, pro}', -- 分级访问与购买

  sales_count int default 0,
  is_public boolean default false,
  is_deleted boolean default false,
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
create table if not exists assets (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id) not null,
  project_id uuid references projects(id), -- 可为空
  url text not null,
  type text not null, -- 'uploaded' | 'ai_generated' | 'scanned'
  prompt text,
  metadata jsonb, -- 存储扫描结果、画布元素等结构化数据
  is_deleted boolean default false,
  created_at timestamptz default now()
);
create index if not exists idx_assets_user_proj on assets(user_id, project_id);

-- 添加 metadata 字段（如果表已存在）
-- ALTER TABLE assets ADD COLUMN IF NOT EXISTS metadata jsonb;

-- 8. 站内信/通知表 (Notifications)
create table if not exists notifications (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id), -- NULL = 全员广播
  target_group text, -- 'all', 'free', 'starter', 'pro'
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

-- ==========================================
-- Part 3: 迁移脚本（如果从旧版本升级）
-- ==========================================
-- 如果你需要从旧版本迁移，请运行以下命令：

-- 1. 添加新列到 profiles
-- ALTER TABLE profiles ADD COLUMN IF NOT EXISTS credits_monthly int default 0;
-- ALTER TABLE profiles ADD COLUMN IF NOT EXISTS credits_permanent int default 0;
-- ALTER TABLE profiles ADD COLUMN IF NOT EXISTS subscription_status text default 'inactive';
-- ALTER TABLE profiles ADD COLUMN IF NOT EXISTS subscription_valid_until timestamptz;
-- ALTER TABLE profiles ADD COLUMN IF NOT EXISTS monthly_credits_cycle_anchor timestamptz;

-- 2. 迁移旧的 credits 到 credits_permanent
-- UPDATE profiles SET credits_permanent = COALESCE(credits, 0) WHERE credits_permanent = 0;

-- 3. 添加新列到 credit_transactions
-- ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS bucket text default 'permanent';
-- ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS balance_monthly_after int default 0;
-- ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS balance_permanent_after int default 0;

-- 4. 更新旧的 credit_transactions 记录
-- UPDATE credit_transactions SET balance_permanent_after = balance_after WHERE balance_permanent_after = 0;

-- 5. 添加 allowed_tiers 到 system_resources
-- ALTER TABLE system_resources ADD COLUMN IF NOT EXISTS allowed_tiers text[] default '{free, starter, pro}';
-- UPDATE system_resources SET allowed_tiers = CASE WHEN is_pro_only THEN '{pro}' ELSE '{free, starter, pro}' END;
