-- =====================================================
-- Migration: Unify resource_id and resource_url
-- =====================================================
-- Purpose: 
--   - resource_id = 资源的唯一标识符 (UUID) - project.id 或 asset.id
--   - resource_url = 资源的可访问/预览 URL
--
-- Before (Projects):
--   resource_url = project.id (UUID string)
--   resource_id = NULL or project.id
--
-- After (Projects):
--   resource_id = project.id (UUID)
--   resource_url = thumbnail_url
--
-- Assets remain unchanged:
--   resource_id = asset.id (UUID)
--   resource_url = image URL
-- =====================================================

-- Step 1: 验证当前状态
SELECT 
    resource_type,
    COUNT(*) as total,
    COUNT(resource_id) as has_resource_id,
    COUNT(*) - COUNT(resource_id) as missing_resource_id
FROM marketplace_listings
WHERE is_deleted = false
GROUP BY resource_type;

-- Step 2: 确保所有 project listings 的 resource_id 有值
-- (从 resource_url 迁移，如果 resource_url 是有效 UUID)
UPDATE marketplace_listings
SET resource_id = resource_url::uuid
WHERE resource_type = 'project'
  AND resource_id IS NULL
  AND resource_url IS NOT NULL
  AND resource_url ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';

-- Step 3: 更新 project listings 的 resource_url 为 thumbnail_url
-- (只更新那些 resource_url 还是 UUID 格式的记录)
UPDATE marketplace_listings ml
SET resource_url = COALESCE(
    (SELECT p.thumbnail_url FROM projects p WHERE p.id = ml.resource_id),
    ml.thumbnail_url,
    ''
)
WHERE ml.resource_type = 'project'
  AND ml.resource_id IS NOT NULL
  AND ml.resource_url ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';

-- Step 4: 验证迁移结果
SELECT 
    id,
    title,
    resource_type,
    resource_id,
    LEFT(resource_url, 80) as resource_url_preview,
    LEFT(thumbnail_url, 80) as thumbnail_url_preview,
    CASE 
        WHEN resource_type = 'project' AND resource_url ~ '^[0-9a-f]{8}-' THEN '❌ Still UUID'
        WHEN resource_type = 'project' AND resource_url LIKE 'http%' THEN '✅ URL'
        WHEN resource_type = 'asset' THEN '✅ Asset OK'
        ELSE '⚠️ Unknown'
    END as status
FROM marketplace_listings
WHERE is_deleted = false
ORDER BY created_at DESC
LIMIT 20;

-- Step 5: 汇总验证
SELECT 
    resource_type,
    COUNT(*) as total,
    SUM(CASE WHEN resource_id IS NOT NULL THEN 1 ELSE 0 END) as has_resource_id,
    SUM(CASE WHEN resource_url LIKE 'http%' THEN 1 ELSE 0 END) as url_is_http,
    SUM(CASE WHEN resource_url ~ '^[0-9a-f]{8}-' THEN 1 ELSE 0 END) as url_is_uuid
FROM marketplace_listings
WHERE is_deleted = false
GROUP BY resource_type;
