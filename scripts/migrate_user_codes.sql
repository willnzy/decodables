-- ==============================================================================
-- 迁移脚本：为 profiles 表添加 user_code 字段
-- 
-- 步骤 1: 添加字段（如果不存在）
-- 步骤 2: 为现有用户生成 user_code
-- 
-- User Code 格式: YYYYMMDDHHMMSS + 毫秒(3位) + 用户序号(6位)
-- 例如: 20251230143025123000001
-- 
-- 注意:
-- - 时间使用 UTC-0 (created_at 在 Supabase 中已经是 timestamptz，默认 UTC)
-- - 序号补0到6位数 (000001 - 999999)
-- ==============================================================================

-- 步骤 1: 添加 user_code 字段（如果不存在）
DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'profiles' AND column_name = 'user_code'
  ) THEN
    ALTER TABLE profiles ADD COLUMN user_code text UNIQUE;
    RAISE NOTICE 'Added user_code column to profiles table';
  ELSE
    RAISE NOTICE 'user_code column already exists';
  END IF;
END $$;

-- 步骤 2: 为现有用户生成 user_code
-- 使用 created_at 时间戳 (转换为 UTC) + 行号作为序号
WITH numbered_users AS (
  SELECT 
    id,
    created_at AT TIME ZONE 'UTC' as created_at_utc,
    ROW_NUMBER() OVER (ORDER BY created_at) as row_num
  FROM profiles
  WHERE user_code IS NULL
)
UPDATE profiles p
SET user_code = 
  -- 日期部分: YYYYMMDDHHMMSS (UTC 时间)
  TO_CHAR(nu.created_at_utc, 'YYYYMMDDHH24MISS') ||
  -- 毫秒部分: 3位，补0
  LPAD(FLOOR(EXTRACT(MILLISECONDS FROM nu.created_at_utc))::int::text, 3, '0') ||
  -- 序号部分: 6位，补0
  LPAD(nu.row_num::text, 6, '0')
FROM numbered_users nu
WHERE p.id = nu.id;

-- 验证结果
SELECT 
  COUNT(*) as total_users,
  COUNT(user_code) as users_with_code,
  COUNT(*) - COUNT(user_code) as users_without_code
FROM profiles;

-- 查看生成的 user_code 示例
SELECT id, email, user_code, created_at 
FROM profiles 
WHERE user_code IS NOT NULL 
ORDER BY created_at 
LIMIT 10;

