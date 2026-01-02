-- =====================================================
-- TABLE: page_design_templates (AI Design Page presets)
-- =====================================================
-- Stores user-saved templates for AI Design Page
-- Similar to user_generation_templates but for page designs

CREATE TABLE IF NOT EXISTS page_design_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,  -- Clerk user IDs are strings
    
    -- Template info
    name TEXT NOT NULL,
    
    -- Page design parameters
    layout TEXT DEFAULT 'image_top',  -- full_image, full_text, image_top, text_top
    story_theme TEXT,
    main_character TEXT,
    style TEXT DEFAULT 'cartoon',
    creativity_level REAL DEFAULT 0.3,
    negative_prompt TEXT,
    generation_mode TEXT DEFAULT 'guided',  -- guided or flexible
    
    -- Usage tracking
    use_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for faster queries
CREATE INDEX IF NOT EXISTS idx_page_design_templates_user 
    ON page_design_templates(user_id, use_count DESC);

-- Enable RLS
ALTER TABLE page_design_templates ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Service role has full access
DROP POLICY IF EXISTS "Service role full access to page design templates" ON page_design_templates;
CREATE POLICY "Service role full access to page design templates" ON page_design_templates FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Auto-update timestamp trigger
CREATE OR REPLACE FUNCTION update_page_design_templates_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_page_design_templates_updated_at ON page_design_templates;
CREATE TRIGGER trigger_page_design_templates_updated_at
    BEFORE UPDATE ON page_design_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_page_design_templates_updated_at();
