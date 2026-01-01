-- Migration: Create missing purchased items in projects/assets tables
-- This fixes historical purchases that only exist in user_purchases but not in projects/assets

-- Step 1: Create purchased projects for existing purchases
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
JOIN projects p ON ml.resource_url::uuid = p.id
WHERE ml.resource_type = 'project'
AND NOT EXISTS (
    -- Check if purchased project already exists for this user
    SELECT 1 FROM projects existing 
    WHERE existing.user_id = up.user_id 
    AND existing.source_listing_id = up.listing_id
    AND existing.is_purchased = true
);

-- Step 2: Create purchased assets for existing purchases  
INSERT INTO assets (user_id, url, name, type, prompt, is_purchased, source_listing_id, origin_owner_id, created_at)
SELECT 
    up.user_id,
    a.url,
    a.name,
    a.type,
    a.prompt,
    true as is_purchased,
    up.listing_id as source_listing_id,
    ml.seller_id as origin_owner_id,
    up.purchased_at as created_at
FROM user_purchases up
JOIN marketplace_listings ml ON up.listing_id = ml.id
JOIN assets a ON (ml.resource_id = a.id OR ml.resource_url::uuid = a.id)
WHERE ml.resource_type = 'asset'
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
