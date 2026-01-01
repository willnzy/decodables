-- Migration: Create missing purchased items in projects/assets tables
-- This fixes historical purchases that only exist in user_purchases but not in projects/assets

-- Step 1: Create purchased projects for existing purchases
-- Note: resource_url for projects stores the project UUID as a string
INSERT INTO projects (user_id, title, canvas_data, thumbnail_url, is_purchased, source_listing_id, origin_owner_id, created_at, updated_at)
SELECT 
    up.user_id,
    p.title,
    p.canvas_data,
    p.thumbnail_url,
    true as is_purchased,
    up.listing_id as source_listing_id,
    ml.seller_id as origin_owner_id,
    up.purchased_at as created_at,
    up.purchased_at as updated_at
FROM user_purchases up
JOIN marketplace_listings ml ON up.listing_id = ml.id
JOIN projects p ON p.id::text = ml.resource_url
WHERE ml.resource_type = 'project'
AND ml.resource_url IS NOT NULL
AND ml.resource_url ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'  -- Only valid UUIDs
AND NOT EXISTS (
    -- Check if purchased project already exists for this user
    SELECT 1 FROM projects existing 
    WHERE existing.user_id = up.user_id 
    AND existing.source_listing_id = up.listing_id
    AND existing.is_purchased = true
);

-- Step 2: Create purchased assets for existing purchases  
-- Use resource_id (UUID reference) instead of resource_url (which may be a URL string)
INSERT INTO assets (user_id, url, type, prompt, description, is_purchased, source_listing_id, origin_owner_id, created_at)
SELECT 
    up.user_id,
    a.url,
    a.type,
    a.prompt,
    a.description,
    true as is_purchased,
    up.listing_id as source_listing_id,
    ml.seller_id as origin_owner_id,
    up.purchased_at as created_at
FROM user_purchases up
JOIN marketplace_listings ml ON up.listing_id = ml.id
JOIN assets a ON ml.resource_id = a.id
WHERE ml.resource_type = 'asset'
AND ml.resource_id IS NOT NULL
AND NOT EXISTS (
    -- Check if purchased asset already exists for this user
    SELECT 1 FROM assets existing 
    WHERE existing.user_id = up.user_id 
    AND existing.source_listing_id = up.listing_id
    AND existing.is_purchased = true
);

-- Verify the migration
SELECT 'Projects created' as type, count(*) as count 
FROM projects WHERE is_purchased = true
UNION ALL
SELECT 'Assets created' as type, count(*) as count 
FROM assets WHERE is_purchased = true;
