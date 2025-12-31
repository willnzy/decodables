-- ==============================================================================
-- ： profiles  user_code 
-- 
--  1: （）
--  2:  user_code
-- 
-- User Code : YYYYMMDDHHMMSS + (3) + (7)
-- : 202512301430251230000001
-- 
-- :
-- -  UTC-0 (created_at  Supabase  timestamptz， UTC)
-- - 07 (0000001 - 9999999)
-- ==============================================================================

--  1:  user_code （）
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

--  2:  user_code
--  created_at  ( UTC) + 
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
  -- : YYYYMMDDHHMMSS (UTC )
  TO_CHAR(nu.created_at_utc, 'YYYYMMDDHH24MISS') ||
  -- : 3，0
  LPAD(FLOOR(EXTRACT(MILLISECONDS FROM nu.created_at_utc))::int::text, 3, '0') ||
  -- : 7，0
  LPAD(nu.row_num::text, 7, '0')
FROM numbered_users nu
WHERE p.id = nu.id;

-- 
SELECT 
  COUNT(*) as total_users,
  COUNT(user_code) as users_with_code,
  COUNT(*) - COUNT(user_code) as users_without_code
FROM profiles;

--  user_code 
SELECT id, email, user_code, created_at 
FROM profiles 
WHERE user_code IS NOT NULL 
ORDER BY created_at 
LIMIT 10;

