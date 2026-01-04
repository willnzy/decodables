-- =====================================================
-- Migration: v3.18_storage_buckets_setup.sql
-- Description: Setup Supabase Storage buckets for Make Decodables
-- Date: 2026-01-03
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
  true,  -- 公开读取
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
  true,  -- 公开读取
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
-- Step 3: Storage RLS 策略
-- =====================================================

-- ----- make-decodables-s 策略 -----

-- 公开读取
DROP POLICY IF EXISTS "make-decodables-s: public read" ON storage.objects;
CREATE POLICY "make-decodables-s: public read"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'make-decodables-s');

-- 仅服务端写入（通过 service_role key）
DROP POLICY IF EXISTS "make-decodables-s: service write" ON storage.objects;
CREATE POLICY "make-decodables-s: service write"
  ON storage.objects FOR INSERT
  WITH CHECK (bucket_id = 'make-decodables-s');

-- 仅服务端更新
DROP POLICY IF EXISTS "make-decodables-s: service update" ON storage.objects;
CREATE POLICY "make-decodables-s: service update"
  ON storage.objects FOR UPDATE
  USING (bucket_id = 'make-decodables-s');

-- 仅服务端删除
DROP POLICY IF EXISTS "make-decodables-s: service delete" ON storage.objects;
CREATE POLICY "make-decodables-s: service delete"
  ON storage.objects FOR DELETE
  USING (bucket_id = 'make-decodables-s');

-- ----- make-decodables-u 策略 -----

DROP POLICY IF EXISTS "make-decodables-u: public read" ON storage.objects;
CREATE POLICY "make-decodables-u: public read"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'make-decodables-u');

DROP POLICY IF EXISTS "make-decodables-u: service write" ON storage.objects;
CREATE POLICY "make-decodables-u: service write"
  ON storage.objects FOR INSERT
  WITH CHECK (bucket_id = 'make-decodables-u');

DROP POLICY IF EXISTS "make-decodables-u: service delete" ON storage.objects;
CREATE POLICY "make-decodables-u: service delete"
  ON storage.objects FOR DELETE
  USING (bucket_id = 'make-decodables-u');

-- =====================================================
-- Step 4: 验证
-- =====================================================

DO $$
DECLARE
  bucket_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO bucket_count 
  FROM storage.buckets 
  WHERE id IN ('make-decodables-s', 'make-decodables-u');
  
  RAISE NOTICE '✅ Storage buckets created: % of 2', bucket_count;
  RAISE NOTICE '  - make-decodables-s: 系统素材（Admin 管理）';
  RAISE NOTICE '  - make-decodables-u: 用户内容（AI生成、上传、扫描、PDF）';
END $$;
