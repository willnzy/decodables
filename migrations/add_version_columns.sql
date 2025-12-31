-- Migration: Add version tracking columns to marketplace_listings
-- Date: 2025-12-31

-- Add version column (current version number)
ALTER TABLE marketplace_listings 
ADD COLUMN IF NOT EXISTS version VARCHAR(20) DEFAULT '1.0';

-- Add changelog column (what's new in current version)
ALTER TABLE marketplace_listings 
ADD COLUMN IF NOT EXISTS changelog TEXT DEFAULT '';

-- Add version_history column (JSON array of all versions)
-- Structure: [{ "version": "1.0", "changelog": "Initial release", "published_at": "2025-01-01T00:00:00Z" }]
ALTER TABLE marketplace_listings 
ADD COLUMN IF NOT EXISTS version_history JSONB DEFAULT '[]'::jsonb;

-- Create index for version lookups
CREATE INDEX IF NOT EXISTS idx_marketplace_listings_version 
ON marketplace_listings(version);

-- Update existing listings to have default version history
UPDATE marketplace_listings 
SET version_history = jsonb_build_array(
  jsonb_build_object(
    'version', COALESCE(version, '1.0'),
    'changelog', COALESCE(changelog, 'Initial release'),
    'published_at', created_at
  )
)
WHERE version_history IS NULL OR version_history = '[]'::jsonb;
