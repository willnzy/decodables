-- =====================================================
-- Migration: v3.18_storage_buckets_setup.sql
-- Description: Setup Supabase Storage buckets for Make Decodables
-- Date: 2026-01-03
-- =====================================================

-- =====================================================
-- 桶设计原则：
-- 1. md-system-assets: 系统素材（Admin 管理，公开读取）
-- 2. md-ai-generated: AI 生成内容（后端写入，公开读取）
-- 3. md-user-content: 用户内容（后端写入，公开读取）
-- =====================================================

-- =====================================================
-- Step 1: 创建 md-system-assets 桶（系统素材）
-- =====================================================

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'md-system-assets',
  'md-system-assets',
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
-- Step 2: 创建 md-ai-generated 桶（AI 生成内容）
-- =====================================================

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'md-ai-generated',
  'md-ai-generated',
  true,  -- 公开读取
  52428800,  -- 50MB 限制
  ARRAY[
    'image/png', 
    'image/jpeg', 
    'image/webp'
  ]
)
ON CONFLICT (id) DO UPDATE SET
  public = EXCLUDED.public,
  file_size_limit = EXCLUDED.file_size_limit,
  allowed_mime_types = EXCLUDED.allowed_mime_types;

-- =====================================================
-- Step 3: 创建 md-user-content 桶（用户内容）
-- =====================================================

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'md-user-content',
  'md-user-content',
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
-- Step 4: Storage RLS 策略
-- =====================================================

-- ----- md-system-assets 策略 -----

-- 公开读取
DROP POLICY IF EXISTS "md-system-assets: public read" ON storage.objects;
CREATE POLICY "md-system-assets: public read"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'md-system-assets');

-- 仅服务端写入（通过 service_role key）
DROP POLICY IF EXISTS "md-system-assets: service write" ON storage.objects;
CREATE POLICY "md-system-assets: service write"
  ON storage.objects FOR INSERT
  WITH CHECK (bucket_id = 'md-system-assets');

-- 仅服务端更新
DROP POLICY IF EXISTS "md-system-assets: service update" ON storage.objects;
CREATE POLICY "md-system-assets: service update"
  ON storage.objects FOR UPDATE
  USING (bucket_id = 'md-system-assets');

-- 仅服务端删除
DROP POLICY IF EXISTS "md-system-assets: service delete" ON storage.objects;
CREATE POLICY "md-system-assets: service delete"
  ON storage.objects FOR DELETE
  USING (bucket_id = 'md-system-assets');

-- ----- md-ai-generated 策略 -----

DROP POLICY IF EXISTS "md-ai-generated: public read" ON storage.objects;
CREATE POLICY "md-ai-generated: public read"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'md-ai-generated');

DROP POLICY IF EXISTS "md-ai-generated: service write" ON storage.objects;
CREATE POLICY "md-ai-generated: service write"
  ON storage.objects FOR INSERT
  WITH CHECK (bucket_id = 'md-ai-generated');

DROP POLICY IF EXISTS "md-ai-generated: service delete" ON storage.objects;
CREATE POLICY "md-ai-generated: service delete"
  ON storage.objects FOR DELETE
  USING (bucket_id = 'md-ai-generated');

-- ----- md-user-content 策略 -----

DROP POLICY IF EXISTS "md-user-content: public read" ON storage.objects;
CREATE POLICY "md-user-content: public read"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'md-user-content');

DROP POLICY IF EXISTS "md-user-content: service write" ON storage.objects;
CREATE POLICY "md-user-content: service write"
  ON storage.objects FOR INSERT
  WITH CHECK (bucket_id = 'md-user-content');

DROP POLICY IF EXISTS "md-user-content: service delete" ON storage.objects;
CREATE POLICY "md-user-content: service delete"
  ON storage.objects FOR DELETE
  USING (bucket_id = 'md-user-content');

-- =====================================================
-- Step 5: 验证
-- =====================================================

DO $$
DECLARE
  bucket_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO bucket_count 
  FROM storage.buckets 
  WHERE id IN ('md-system-assets', 'md-ai-generated', 'md-user-content');
  
  RAISE NOTICE '✅ Storage buckets created: % of 3', bucket_count;
  RAISE NOTICE '  - md-system-assets: 系统素材（Admin 管理）';
  RAISE NOTICE '  - md-ai-generated: AI 生成内容';
  RAISE NOTICE '  - md-user-content: 用户上传内容';
END $$;
