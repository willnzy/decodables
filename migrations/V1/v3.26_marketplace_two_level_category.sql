-- ============================================================
-- v3.26: Marketplace Two-Level Category System
--
-- Adds category and source fields to marketplace_listings
-- to support the two-level classification system:
-- - resource_type: "asset" | "project" (already exists)
-- - category: specific content category (new)
-- - source: "system" | "user" | "ai" | "community" (new)
-- ============================================================

-- 1. Add category field (specific content type)
-- Default to 'element' for backward compatibility
ALTER TABLE marketplace_listings
ADD COLUMN IF NOT EXISTS category TEXT DEFAULT 'element';

-- 2. Add source field (where the asset comes from)
-- Default to 'user' for backward compatibility
ALTER TABLE marketplace_listings
ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'user';

-- 3. Create indexes for new fields
CREATE INDEX IF NOT EXISTS idx_listings_category
ON marketplace_listings(category);

CREATE INDEX IF NOT EXISTS idx_listings_source
ON marketplace_listings(source);

CREATE INDEX IF NOT EXISTS idx_listings_resource_category
ON marketplace_listings(resource_type, category);

-- 4. Add constraint for valid category values
-- Categories based on Asset-Category-System-Design.md
ALTER TABLE marketplace_listings
DROP CONSTRAINT IF EXISTS chk_listings_category;

ALTER TABLE marketplace_listings
ADD CONSTRAINT chk_listings_category
CHECK (category IN (
  -- Graphics categories
  'clipart', 'illustration', 'photo', 'background',
  'template', 'font', 'sticker', 'icon', 'pattern', 'element',
  -- Additional categories
  'emoji', 'frame', 'character', 'scene',
  -- Project-specific (optional for projects)
  'mini_book', 'worksheet', 'flashcard'
));

-- 5. Add constraint for valid source values
ALTER TABLE marketplace_listings
DROP CONSTRAINT IF EXISTS chk_listings_source;

ALTER TABLE marketplace_listings
ADD CONSTRAINT chk_listings_source
CHECK (source IN ('system', 'user', 'ai', 'community'));

-- 6. Update existing rows: infer category from resource_type
-- Assets default to 'element', projects default to 'template'
UPDATE marketplace_listings
SET category = CASE
  WHEN resource_type = 'project' THEN 'template'
  ELSE 'element'
END
WHERE category IS NULL OR category = '';

-- 7. Comment on new columns
COMMENT ON COLUMN marketplace_listings.category IS
'Content category: clipart, sticker, background, template, etc.';

COMMENT ON COLUMN marketplace_listings.source IS
'Asset source: system (built-in), user (uploaded), ai (generated), community (shared)';
