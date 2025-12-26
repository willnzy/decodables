-- 1. 用户档案表 (User Profiles)
create table profiles (
  id text primary key, -- 对应 Clerk user_id
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
-- [核心] 记录每一笔资金/积分变动，用于财务对账
create table credit_transactions (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id) not null,
  amount int not null, -- 变动值 (+100, -50)
  balance_after int not null, -- [核心] 变动后的余额快照 (Running Balance)
  type text not null, -- 枚举见下方
  description text, 
  created_at timestamptz default now()
);
-- type 枚举: 'signup_bonus', 'purchase', 'sub_grant', 'sub_renewal', 'generation', 'download_pdf', 'admin_adj'

-- 3. 项目表 (User Projects)
create table projects (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id) not null,
  title text default 'My Magic Story',
  canvas_data jsonb default '{}'::jsonb, -- Fabric.js JSON
  thumbnail_url text,
  last_downloaded_hash text, -- 用于 "严格扣费" 校验
  is_deleted boolean default false, -- 软删除
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- 4. 用户素材表 (User Assets)
-- [核心] 支持用户上传及 AI 生成图片的复用，支持按项目筛选
create table assets (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id) not null,
  project_id uuid references projects(id), -- 可为空 (若为通用上传)
  url text not null, -- Storage URL
  type text not null, -- 'user_upload' | 'ai_generated'
  prompt text, -- AI 生成时的提示词 (可选)
  is_deleted boolean default false,
  created_at timestamptz default now()
);
create index idx_assets_user_proj on assets(user_id, project_id);

-- 5. 系统资源表 (System Resources)
-- [新增] 用于存储 Sticker 贴纸库
create table system_resources (
  id uuid default gen_random_uuid() primary key,
  type text not null, -- 'sticker', 'template'
  category text, -- 'animals', 'badges'
  url text not null,
  is_pro_only boolean default false, -- 区分权益
  created_at timestamptz default now()
);

-- 6. 行为日志表 (User Behavior Logs)
-- [核心] 仅记录普通用户的 C 端行为，用于漏斗分析
create table activity_logs (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id),
  action text not null, 
  metadata jsonb, -- 记录 IP, 来源, 错误信息
  created_at timestamptz default now()
);
-- action 枚举: 'login', 'click_checkout', 'payment_success', 'create_project', 'download_pdf', 'submit_support_ticket'

-- 7. 客服与运营记录表 (Support & Admin Ops)
-- [核心] 记录工单 + 所有 Admin 后台操作 (审计用)
create table support_tickets (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id), -- 目标用户
  admin_id text references profiles(id), -- 操作管理员 (若为用户提交工单则为NULL)
  category text not null, -- 'ticket_submission', 'admin_adjustment_credits', 'admin_change_tier'
  content text, -- 工单内容 或 操作理由
  metadata jsonb, -- {old_val: x, new_val: y}
  status text default 'closed',
  created_at timestamptz default now()
);

-- MagicZine AI - RLS 安全策略配置脚本
-- 请在 Supabase SQL Editor 中执行

-- ==========================================
-- 第一步：强制开启所有表的 RLS (关上大门)
-- ==========================================
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_resources ENABLE ROW LEVEL SECURITY;

-- ==========================================
-- 第二步：定义通用 Helper (方便判断是否是本人)
-- ==========================================
-- 注意：这里假设您的应用层通过 Clerk 传递了正确的 UserID 给 Supabase
-- 如果您主要通过后端 Service Role 操作数据库，这些策略主要用于防范前端直接攻击

-- ==========================================
-- 第三步：配置具体表的权限策略
-- ==========================================

-- 1. Profiles (用户档案)
-- 允许: 用户查/改自己，所有人查自己(用于登录检查)
create policy "Users can view own profile" on profiles
  for select using ( auth.uid()::text = id );

create policy "Users can update own profile" on profiles
  for update using ( auth.uid()::text = id );

-- 2. Projects (项目)
-- 允许: 用户增删改查自己的项目
create policy "Users can CRUD own projects" on projects
  for all using ( auth.uid()::text = user_id );

-- 3. Assets (素材)
-- 允许: 用户增删改查自己的素材
create policy "Users can CRUD own assets" on assets
  for all using ( auth.uid()::text = user_id );

-- 4. Credit Transactions (积分流水 - 敏感!)
-- 允许: 用户只能【查看】自己的流水，【严禁】用户自己修改或删除！
create policy "Users can view own transactions" on credit_transactions
  for select using ( auth.uid()::text = user_id );

-- 5. Activity Logs (行为日志)
-- 允许: 用户只能插入和查看自己的日志
create policy "Users can insert own logs" on activity_logs
  for insert with check ( auth.uid()::text = user_id );

create policy "Users can view own logs" on activity_logs
  for select using ( auth.uid()::text = user_id );

-- 6. Support Tickets (工单)
-- 允许: 用户只能管理自己的工单
create policy "Users can CRUD own tickets" on support_tickets
  for all using ( auth.uid()::text = user_id );

-- 7. System Resources (系统贴纸/资源)
-- 允许: 所有人【只读】 (Public Read)，禁止普通用户修改
create policy "Public can view system resources" on system_resources
  for select using ( true );

-- ==========================================
-- 第四步：补充管理员权限 (可选)
-- ==========================================
-- 如果您需要在前端直接用 Admin 账号操作 DB (不推荐，建议走后端 API)，可添加如下策略：
-- (这里利用 profiles 表中的 role 字段)

-- 示例: 允许 Admin 查看所有 Profiles
create policy "Admins can view all profiles" on profiles
  for select using (
    exists (
      select 1 from profiles
      where id = auth.uid()::text and role = 'admin'
    )
  );

-- 注意：您的 FastAPI 后端使用 'service_role' key 连接 Supabase 时，
-- 会自动绕过上述所有 RLS 规则 (拥有上帝权限)，这正是我们想要的。
-- RLS 主要是为了防止前端匿名用户直接攻击数据库。