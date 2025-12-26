-- 1. 用户档案表 (扩展字段)
create table profiles (
  id text primary key, -- 对应 Clerk user_id
  email text,
  username text,
  avatar_url text,
  credits int default 50, -- 当前剩余积分
  tier text default 'free', -- free, starter, pro
  stripe_customer_id text, -- 关联 Stripe
  role text default 'user', -- user, admin (用于后台权限)
  created_at timestamptz default now()
);

-- 2. 积分流水表 (满足需求 3: 历史记录查询)
create table credit_transactions (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id) not null,
  amount int not null, -- 正数表示增加(购买)，负数表示扣除(生成/下载)
  type text not null, -- 'bonus'(赠送), 'purchase'(购买), 'subscription'(订阅), 'generation'(生成), 'download'(下载), 'admin_adjustment'(后台补偿)
  description text, -- e.g. "Generated Project XYZ", "Monthly Plan"
  created_at timestamptz default now()
);

-- 3. 项目表 (满足需求 5: 自动保存与备份)
create table projects (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id) not null,
  title text default 'Untitled Story',
  canvas_data jsonb default '{}'::jsonb, -- 存储 Fabric.js 完整 JSON
  thumbnail_url text, -- 项目封面图
  last_downloaded_hash text, -- 用于下载扣费校验
  is_deleted boolean default false, -- 软删除 (备份机制)
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- 4. 行为日志表 (满足需求 7: 后台查看用户路径)
create table activity_logs (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id),
  action text not null, -- 'login', 'create_project', 'payment_success', 'click_download'
  metadata jsonb, -- 存储 IP, UserAgent, 或操作详情
  created_at timestamptz default now()
);

-- 5. 客服工单表 (满足需求 6: 邮件表单备份)
create table support_tickets (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id),
  email text not null,
  message text not null,
  status text default 'open', -- open, resolved
  created_at timestamptz default now()
);