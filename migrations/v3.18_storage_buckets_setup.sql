-- =====================================================
-- Migration: v3.18_storage_buckets_setup.sql
-- Description: Setup Supabase Storage buckets for Make Decodables
-- Date: 2026-01-03
-- 
-- 安全策略设计：
-- - 读取：公开（CDN 加速）
-- - 上传/更改：仅后端服务（service_role key）
-- - 删除：完全禁止（只能软删除）
-- =====================================================

-- =====================================================
-- 桶设计（2个桶）：
-- 1. make-decodables-s: 系统素材（Admin 管理，公开读取）
-- 2. make-decodables-u: 用户内容（后端写入，公开读取）
-- =====================================================

-- =====================================================
-- Step 1: 创建 make-decodables-s 桶（系统素材）
-- =====================================================

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'make-decodables-s',
  'make-decodables-s',
  true,  -- 公开读取（通过 CDN）
  10485760,  -- 10MB 限制
  ARRAY[
    'image/png', 
    'image/jpeg', 
    'image/webp', 
    'image/gif',
    'image/svg+xml'
  ]
)
ON CONFLICT (id) DO UPDATE SET
  public = EXCLUDED.public,
  file_size_limit = EXCLUDED.file_size_limit,
  allowed_mime_types = EXCLUDED.allowed_mime_types;

-- =====================================================
-- Step 2: 创建 make-decodables-u 桶（用户内容）
-- =====================================================

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'make-decodables-u',
  'make-decodables-u',
  true,  -- 公开读取（通过 CDN）
  52428800,  -- 50MB 限制
  ARRAY[
    'image/png', 
    'image/jpeg', 
    'image/webp', 
    'image/gif',
    'image/svg+xml',
    'application/pdf'
  ]
)
ON CONFLICT (id) DO UPDATE SET
  public = EXCLUDED.public,
  file_size_limit = EXCLUDED.file_size_limit,
  allowed_mime_types = EXCLUDED.allowed_mime_types;

-- =====================================================
-- Step 3: 清除旧策略（如果存在）
-- =====================================================

-- make-decodables-s 旧策略
DROP POLICY IF EXISTS "make-decodables-s: public read" ON storage.objects;
DROP POLICY IF EXISTS "make-decodables-s: service write" ON storage.objects;
DROP POLICY IF EXISTS "make-decodables-s: service update" ON storage.objects;
DROP POLICY IF EXISTS "make-decodables-s: service delete" ON storage.objects;
DROP POLICY IF EXISTS "make-decodables-s: deny insert" ON storage.objects;
DROP POLICY IF EXISTS "make-decodables-s: deny update" ON storage.objects;
DROP POLICY IF EXISTS "make-decodables-s: deny delete" ON storage.objects;

-- make-decodables-u 旧策略
DROP POLICY IF EXISTS "make-decodables-u: public read" ON storage.objects;
DROP POLICY IF EXISTS "make-decodables-u: service write" ON storage.objects;
DROP POLICY IF EXISTS "make-decodables-u: service delete" ON storage.objects;
DROP POLICY IF EXISTS "make-decodables-u: deny insert" ON storage.objects;
DROP POLICY IF EXISTS "make-decodables-u: deny update" ON storage.objects;
DROP POLICY IF EXISTS "make-decodables-u: deny delete" ON storage.objects;

-- =====================================================
-- Step 4: Storage RLS 策略 - make-decodables-s（系统素材桶）
-- =====================================================

-- 4.1 公开读取（任何人都可以读取系统素材）
CREATE POLICY "make-decodables-s: public read"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'make-decodables-s');

-- 4.2 禁止前端上传（后端使用 service_role 绕过 RLS）
-- 注意：这个策略对 anon/authenticated 用户生效
-- service_role key 会绕过 RLS，所以后端仍可上传
CREATE POLICY "make-decodables-s: deny insert"
  ON storage.objects FOR INSERT
  WITH CHECK (
    bucket_id = 'make-decodables-s' 
    AND false  -- 永远拒绝前端直接上传
  );

-- 4.3 禁止前端更改
CREATE POLICY "make-decodables-s: deny update"
  ON storage.objects FOR UPDATE
  USING (
    bucket_id = 'make-decodables-s'
    AND false  -- 永远拒绝前端直接更改
  );

-- 4.4 禁止所有删除（包括后端！只能软删除）
-- 即使 service_role 也无法删除，需要从数据库层面禁用
-- 注意：这里我们用 RLS 策略禁止，但 service_role 会绕过
-- 真正的禁止需要在应用层实现
CREATE POLICY "make-decodables-s: deny delete"
  ON storage.objects FOR DELETE
  USING (
    bucket_id = 'make-decodables-s'
    AND false  -- 永远拒绝
  );

-- =====================================================
-- Step 5: Storage RLS 策略 - make-decodables-u（用户内容桶）
-- =====================================================

-- 5.1 公开读取（任何人都可以读取用户生成的内容）
CREATE POLICY "make-decodables-u: public read"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'make-decodables-u');

-- 5.2 禁止前端上传（后端使用 service_role 绕过 RLS）
CREATE POLICY "make-decodables-u: deny insert"
  ON storage.objects FOR INSERT
  WITH CHECK (
    bucket_id = 'make-decodables-u'
    AND false  -- 永远拒绝前端直接上传
  );

-- 5.3 禁止前端更改
CREATE POLICY "make-decodables-u: deny update"
  ON storage.objects FOR UPDATE
  USING (
    bucket_id = 'make-decodables-u'
    AND false  -- 永远拒绝前端直接更改
  );

-- 5.4 禁止所有删除（只能软删除）
CREATE POLICY "make-decodables-u: deny delete"
  ON storage.objects FOR DELETE
  USING (
    bucket_id = 'make-decodables-u'
    AND false  -- 永远拒绝
  );

-- =====================================================
-- Step 6: 验证
-- =====================================================

DO $$
DECLARE
  bucket_count INTEGER;
  policy_count INTEGER;
BEGIN
  -- 验证桶
  SELECT COUNT(*) INTO bucket_count 
  FROM storage.buckets 
  WHERE id IN ('make-decodables-s', 'make-decodables-u');
  
  -- 验证策略
  SELECT COUNT(*) INTO policy_count
  FROM pg_policies 
  WHERE tablename = 'objects' 
    AND schemaname = 'storage'
    AND policyname LIKE 'make-decodables-%';
  
  RAISE NOTICE '';
  RAISE NOTICE '=====================================================';
  RAISE NOTICE '✅ Storage Setup Complete';
  RAISE NOTICE '=====================================================';
  RAISE NOTICE '';
  RAISE NOTICE '📦 Buckets: % of 2', bucket_count;
  RAISE NOTICE '   - make-decodables-s: 系统素材（Admin 管理）';
  RAISE NOTICE '   - make-decodables-u: 用户内容（AI生成、上传、扫描）';
  RAISE NOTICE '';
  RAISE NOTICE '🔐 Policies: % policies created', policy_count;
  RAISE NOTICE '';
  RAISE NOTICE '📋 权限矩阵:';
  RAISE NOTICE '   ┌─────────────┬──────────┬──────────┐';
  RAISE NOTICE '   │ 操作        │ 前端用户 │ 后端服务 │';
  RAISE NOTICE '   ├─────────────┼──────────┼──────────┤';
  RAISE NOTICE '   │ 读取 SELECT │ ✅ 允许  │ ✅ 允许  │';
  RAISE NOTICE '   │ 上传 INSERT │ ❌ 禁止  │ ✅ 允许  │';
  RAISE NOTICE '   │ 更改 UPDATE │ ❌ 禁止  │ ✅ 允许  │';
  RAISE NOTICE '   │ 删除 DELETE │ ❌ 禁止  │ ⚠️ 受控  │';
  RAISE NOTICE '   └─────────────┴──────────┴──────────┘';
  RAISE NOTICE '';
  RAISE NOTICE '⚠️ 注意: 后端服务使用 service_role key 会绕过 RLS';
  RAISE NOTICE '   删除操作需要在应用层控制（软删除/定时清理）';
  RAISE NOTICE '=====================================================';
END $$;
