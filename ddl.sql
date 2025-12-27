-- ==============================================================================
-- Make Decodables 数据库完整初始化脚本 (v2.0 Final)
-- 包含：核心表结构 + 最终版 RLS 安全策略
-- ==============================================================================

-- ==========================================
-- Part 1: 建表 (Schema Definition)
-- ==========================================

-- 1. 用户档案表 (User Profiles)
create table if not exists profiles (
  id text primary key, -- 对应 Clerk user_id (String)
  email text,
  username text,
  avatar_url text,
  credits int default 0,
  tier text default 'free', -- 'free', 'starter', 'pro'
  stripe_customer_id text,
  role text default 'user', -- 'user', 'admin'
  created_at timestamptz default now()
);

-- 2. 积分流水表 (Financial Ledger)
create table if not exists credit_transactions (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id) not null,
  amount int not null,
  balance_after int not null,
  type text not null,
  description text, 
  created_at timestamptz default now()
);

-- 3. 项目表 (User Projects)
create table if not exists projects (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id) not null,
  title text default 'My Magic Story',
  canvas_data jsonb default '{}'::jsonb,
  thumbnail_url text,
  last_downloaded_hash text,
  is_deleted boolean default false,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- 4. 用户素材表 (User Assets)
create table if not exists assets (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id) not null,
  project_id uuid references projects(id),
  url text not null,
  type text not null,
  prompt text,
  is_deleted boolean default false,
  created_at timestamptz default now()
);
create index if not exists idx_assets_user_proj on assets(user_id, project_id);

-- 5. 系统资源表 (System Resources)
create table if not exists system_resources (
  id uuid default gen_random_uuid() primary key,
  type text not null,
  category text,
  url text not null,
  is_pro_only boolean default false,
  created_at timestamptz default now()
);

-- 6. 行为日志表 (User Behavior Logs)
create table if not exists activity_logs (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id),
  action text not null, 
  metadata jsonb,
  created_at timestamptz default now()
);

-- 7. 客服与运营记录表 (Support Tickets)
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
-- Part 2: RLS 安全策略配置 (最终修正版)
-- ==========================================

-- 1. 强制开启 RLS (保护所有表)
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_resources ENABLE ROW LEVEL SECURITY;

-- 2. 定义 Helper 函数 (解决递归和类型问题)
-- 这里的 auth.jwt() ->> 'sub' 专门用于获取 Clerk 传递过来的 String 类型的 ID
-- Security Definer 意味着此函数执行时拥有上帝权限，不会被 profiles 的 RLS 拦截
create or replace function is_admin()
returns boolean
language sql
security definer 
as $$
  select exists (
    select 1 from profiles
    where id = (select auth.jwt() ->> 'sub')
    and role = 'admin'
  );
$$;

-- 3. 配置策略 (Policies)

-- [Profiles] 
-- A. 读取策略 (自己看自己，或者 Admin 看所有人)
drop policy if exists "Users can view own profile or Admin view all" on profiles;
create policy "Users can view own profile or Admin view all" on profiles
  for select using ( 
    (select auth.jwt() ->> 'sub') = id 
    or is_admin() 
  );

-- B. 更新策略 (自己改自己)
drop policy if exists "Users can update own profile" on profiles;
create policy "Users can update own profile" on profiles
  for update using ( (select auth.jwt() ->> 'sub') = id );

-- C. 插入策略 (注册用 - 关键修复：允许用户/Webhook 插入自己的档案)
drop policy if exists "Users can insert own profile" on profiles;
create policy "Users can insert own profile" on profiles
  for insert with check ( (select auth.jwt() ->> 'sub') = id );

-- [Projects]
drop policy if exists "Users can CRUD own projects" on projects;
create policy "Users can CRUD own projects" on projects
  for all using ( (select auth.jwt() ->> 'sub') = user_id );

-- [Assets]
drop policy if exists "Users can CRUD own assets" on assets;
create policy "Users can CRUD own assets" on assets
  for all using ( (select auth.jwt() ->> 'sub') = user_id );

-- [Credit Transactions]
-- 允许：自己查看，管理员查看。严禁用户修改/删除。
drop policy if exists "Users view own txs or Admin view all" on credit_transactions;
create policy "Users view own txs or Admin view all" on credit_transactions
  for select using ( 
    (select auth.jwt() ->> 'sub') = user_id 
    or is_admin() 
  );

-- [Activity Logs]
-- 允许：插入自己的日志，查看自己的日志，管理员查看所有
drop policy if exists "Users can insert own logs" on activity_logs;
create policy "Users can insert own logs" on activity_logs
  for insert with check ( (select auth.jwt() ->> 'sub') = user_id );

drop policy if exists "Users view own logs or Admin view all" on activity_logs;
create policy "Users view own logs or Admin view all" on activity_logs
  for select using ( 
    (select auth.jwt() ->> 'sub') = user_id 
    or is_admin() 
  );

-- [Support Tickets]
-- 允许：自己管理自己的工单，管理员管理所有
drop policy if exists "Users CRUD own tickets or Admin manage all" on support_tickets;
create policy "Users CRUD own tickets or Admin manage all" on support_tickets
  for all using ( 
    (select auth.jwt() ->> 'sub') = user_id 
    or is_admin() 
  );

-- [System Resources]
-- 允许：所有人只读
drop policy if exists "Public can view system resources" on system_resources;
create policy "Public can view system resources" on system_resources
  for select using ( true );