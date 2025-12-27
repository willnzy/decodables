-- =========================================================
-- 1. 清理旧策略和函数 (防止残留冲突)
-- =========================================================
drop policy if exists "Public profiles are viewable by everyone" on profiles;
drop policy if exists "Users can insert their own profile" on profiles;
drop policy if exists "Users can update own profile" on profiles;
drop policy if exists "Allow individual read access" on profiles;
drop policy if exists "Allow individual update access" on profiles;
drop policy if exists "Users can view own profile" on profiles;
drop policy if exists "Users can insert own profile" on profiles;
drop policy if exists "Users can update own profile" on profiles;
drop policy if exists "Users can view own profile or Admin can view all" on profiles;
drop function if exists is_admin();

-- =========================================================
-- 2. 创建 Admin 检查函数 (修复类型问题)
-- =========================================================
create or replace function is_admin()
returns boolean
language sql
security definer 
as $$
  select exists (
    select 1 from profiles
    where id = (select auth.jwt() ->> 'sub') -- <--- 关键修改：直接取 Text 类型的 ID
    and role = 'admin'
  );
$$;

-- =========================================================
-- 3. 重建 RLS 策略 (全部使用 auth.jwt() ->> 'sub')
-- =========================================================

-- A. 读取策略 (自己看自己，或者 Admin 看所有人)
create policy "Users can view own profile or Admin can view all"
on profiles for select
using ( 
  (select auth.jwt() ->> 'sub') = id 
  or 
  is_admin() 
);

-- B. 更新策略 (自己改自己)
create policy "Users can update own profile"
on profiles for update
using ( (select auth.jwt() ->> 'sub') = id );

-- C. 插入策略 (注册用)
create policy "Users can insert own profile"
on profiles for insert
with check ( (select auth.jwt() ->> 'sub') = id );