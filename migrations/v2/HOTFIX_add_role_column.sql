-- HOTFIX: Add role column to profiles table
-- Version: v3.32
-- Date: 2026-01-14
-- Description: 添加用户角色字段，用于区分普通用户和管理员
--
-- Usage:
--   psql $DATABASE_URL -f HOTFIX_add_role_column.sql
--
-- 或在 Supabase SQL Editor 中执行

BEGIN;

-- ============================================
-- Step 1: 添加 role 字段
-- ============================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'profiles' AND column_name = 'role'
    ) THEN
        ALTER TABLE profiles ADD COLUMN role TEXT NOT NULL DEFAULT 'user';
        ALTER TABLE profiles ADD CONSTRAINT check_role CHECK (role IN ('user', 'admin'));
        RAISE NOTICE '✅ Added role column to profiles table';
    ELSE
        RAISE NOTICE 'ℹ️ role column already exists in profiles table';
    END IF;
END $$;

-- ============================================
-- Step 2: 创建索引 (可选，用于快速查询管理员)
-- ============================================

CREATE INDEX IF NOT EXISTS idx_profiles_role ON profiles (role);
RAISE NOTICE '✅ Index idx_profiles_role ensured';

-- ============================================
-- Step 3: 验证
-- ============================================

DO $$
DECLARE
    column_exists BOOLEAN;
    constraint_exists BOOLEAN;
    index_exists BOOLEAN;
BEGIN
    -- Check column
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'profiles' AND column_name = 'role'
    ) INTO column_exists;

    -- Check constraint
    SELECT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE table_name = 'profiles' AND constraint_name = 'check_role'
    ) INTO constraint_exists;

    -- Check index
    SELECT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'profiles' AND indexname = 'idx_profiles_role'
    ) INTO index_exists;

    IF column_exists AND index_exists THEN
        RAISE NOTICE '';
        RAISE NOTICE '✅ HOTFIX VERIFICATION PASSED';
        RAISE NOTICE '   - role column: EXISTS';
        RAISE NOTICE '   - check_role constraint: %', CASE WHEN constraint_exists THEN 'EXISTS' ELSE 'MISSING (OK if using inline CHECK)' END;
        RAISE NOTICE '   - idx_profiles_role index: EXISTS';
        RAISE NOTICE '';
        RAISE NOTICE '📌 Next steps:';
        RAISE NOTICE '   1. To set a user as admin, run:';
        RAISE NOTICE '      UPDATE profiles SET role = ''admin'' WHERE email = ''your-email@example.com'';';
        RAISE NOTICE '';
    ELSE
        RAISE EXCEPTION '❌ HOTFIX VERIFICATION FAILED: Column or index not found.';
    END IF;
END $$;

COMMIT;

-- ============================================
-- 设置 Admin 用户示例 (取消注释并修改邮箱执行)
-- ============================================

-- UPDATE profiles SET role = 'admin' WHERE email = 'your-admin@example.com';
-- SELECT id, email, role FROM profiles WHERE role = 'admin';
