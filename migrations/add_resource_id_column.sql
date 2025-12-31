-- Migration: Add resource_id column to marketplace_listings
-- Purpose: Store the actual resource ID (asset.id or project.id) separately from resource_url
-- Date: 2025-12-31

-- Step 1: Add the new resource_id column
ALTER TABLE marketplace_listings 
ADD COLUMN IF NOT EXISTS resource_id UUID;

-- Step 2: Populate resource_id for existing asset listings
-- For assets: resource_url contains the URL, we need to find the asset.id by matching URL
UPDATE marketplace_listings ml
SET resource_id = a.id
FROM assets a
WHERE ml.resource_type = 'asset'
  AND ml.resource_url = a.url
  AND ml.resource_id IS NULL;

-- Step 3: Populate resource_id for existing project listings  
-- For projects: resource_url already contains the project.id (as text)
UPDATE marketplace_listings
SET resource_id = resource_url::uuid
WHERE resource_type = 'project'
  AND resource_id IS NULL
  AND resource_url IS NOT NULL
  AND resource_url ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';

-- Step 4: Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_marketplace_listings_resource_id 
ON marketplace_listings(resource_id);

-- Verification query:
-- SELECT id, title, resource_type, resource_id, resource_url 
-- FROM marketplace_listings 
-- WHERE is_deleted = false 
-- ORDER BY created_at DESC;
