-- ============================================================================
-- Fix: Update marketplace_listings.resource_id from projects table
-- Date: 2026-01-21
-- Issue: marketplace_listings.resource_id was NULL, causing Selling view to show empty
--
-- Root cause: When creating a listing, only projects.marketplace_listing_id was set,
-- but marketplace_listings.resource_id was not set (bidirectional link was incomplete)
--
-- This script fixes existing data by populating resource_id from the projects table.
-- ============================================================================

-- Step 1: Preview affected records
SELECT
    ml.id AS listing_id,
    ml.listing_id AS listing_business_id,
    ml.title,
    ml.resource_type,
    ml.resource_id AS current_resource_id,
    p.id AS project_id,
    p.title AS project_title
FROM marketplace_listings ml
JOIN projects p ON p.marketplace_listing_id = ml.id
WHERE ml.resource_id IS NULL
  AND ml.resource_type = 'project'
  AND ml.is_deleted = FALSE;

-- Step 2: Execute the fix (uncomment to run)
-- UPDATE marketplace_listings ml
-- SET resource_id = p.id
-- FROM projects p
-- WHERE p.marketplace_listing_id = ml.id
--   AND ml.resource_id IS NULL
--   AND ml.resource_type = 'project';

-- Step 3: Verify fix
-- SELECT COUNT(*) AS fixed_count
-- FROM marketplace_listings ml
-- JOIN projects p ON p.marketplace_listing_id = ml.id
-- WHERE ml.resource_id = p.id
--   AND ml.resource_type = 'project';
