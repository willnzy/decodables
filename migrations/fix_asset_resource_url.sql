-- Migration: Fix asset marketplace_listings resource_url
-- Problem: Asset listings currently store full URL in resource_url, should store asset.id
-- Date: 2025-12-31

-- This migration updates existing asset marketplace_listings to use asset.id instead of asset.url
-- For consistency with project listings (which store project.id in resource_url)

-- Step 1: Find and update asset listings where resource_url is a full URL
-- Match by: marketplace_listings.resource_url = assets.url
-- Update to: marketplace_listings.resource_url = assets.id

UPDATE marketplace_listings ml
SET resource_url = a.id::text
FROM assets a
WHERE ml.resource_type = 'asset'
  AND ml.resource_url = a.url
  AND ml.is_deleted = false;

-- Verification query (run separately to check results):
-- SELECT 
--   ml.id as listing_id,
--   ml.title,
--   ml.resource_url,
--   ml.resource_type,
--   a.id as asset_id,
--   a.url as asset_url
-- FROM marketplace_listings ml
-- LEFT JOIN assets a ON ml.resource_url = a.id::text
-- WHERE ml.resource_type = 'asset'
--   AND ml.is_deleted = false;
