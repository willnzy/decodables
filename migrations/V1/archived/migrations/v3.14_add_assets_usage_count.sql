-- Migration: v3.14_add_assets_usage_count.sql
-- Description: Add usage_count column to assets table for tracking asset usage
-- Date: 2026-01-06

-- Add usage_count column to assets table
ALTER TABLE assets 
ADD COLUMN IF NOT EXISTS usage_count INTEGER DEFAULT 0;

-- Create index for efficient sorting by usage
CREATE INDEX IF NOT EXISTS idx_assets_usage_count ON assets(usage_count DESC);

-- Comment
COMMENT ON COLUMN assets.usage_count IS 'Number of times this asset has been used in projects';
