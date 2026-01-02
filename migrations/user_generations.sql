-- User Generations History Table
-- Stores AI-generated images for persistent history and favorites
-- Created: 2026-01-02

-- =====================================================
-- TABLE: user_generations
-- =====================================================
CREATE TABLE IF NOT EXISTS user_generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Image data
    image_url TEXT NOT NULL,
    thumbnail_url TEXT,  -- Optional smaller version for faster loading
    
    -- Prompt information
    original_prompt TEXT,
    enhanced_prompt TEXT,
    negative_prompt TEXT,
    
    -- Generation parameters
    style TEXT,
    moods TEXT[],  -- Array of mood tags
    aspect_ratio TEXT DEFAULT 'square',
    generation_mode TEXT DEFAULT 'guided',  -- 'guided' or 'flexible'
    creativity_level REAL DEFAULT 0.3,
    
    -- 5W1H parameters (for asset generation)
    who_param TEXT,
    what_param TEXT,
    where_param TEXT,
    
    -- Reference image info
    has_reference BOOLEAN DEFAULT false,
    reference_strength REAL,
    
    -- Batch info (for multi-image generations)
    batch_id TEXT,  -- Groups images generated together
    batch_index INTEGER DEFAULT 0,  -- Index within the batch
    
    -- User actions
    is_favorited BOOLEAN DEFAULT false,
    is_imported BOOLEAN DEFAULT false,  -- Whether imported to asset library
    
    -- Metadata
    credits_used INTEGER DEFAULT 5,
    model_used TEXT,
    generation_time_ms INTEGER,  -- How long generation took
    
    -- Audit fields
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_user_generations_user_id 
    ON user_generations(user_id);

CREATE INDEX IF NOT EXISTS idx_user_generations_user_created 
    ON user_generations(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_generations_favorited 
    ON user_generations(user_id, is_favorited) 
    WHERE is_favorited = true;

CREATE INDEX IF NOT EXISTS idx_user_generations_batch 
    ON user_generations(batch_id);

-- RLS Policies
ALTER TABLE user_generations ENABLE ROW LEVEL SECURITY;

-- Users can only see their own generations
CREATE POLICY "Users can view own generations" ON user_generations
    FOR SELECT USING (auth.uid() = user_id);

-- Users can insert their own generations
CREATE POLICY "Users can insert own generations" ON user_generations
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Users can update their own generations (for favorites, etc.)
CREATE POLICY "Users can update own generations" ON user_generations
    FOR UPDATE USING (auth.uid() = user_id);

-- Users can delete their own generations
CREATE POLICY "Users can delete own generations" ON user_generations
    FOR DELETE USING (auth.uid() = user_id);

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_user_generations_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_user_generations_updated_at
    BEFORE UPDATE ON user_generations
    FOR EACH ROW
    EXECUTE FUNCTION update_user_generations_updated_at();


-- =====================================================
-- TABLE: user_generation_templates
-- =====================================================
CREATE TABLE IF NOT EXISTS user_generation_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Template info
    name TEXT NOT NULL,
    description TEXT,
    
    -- Saved parameters
    character_type TEXT,
    character_custom TEXT,
    action_type TEXT,
    action_custom TEXT,
    setting_type TEXT,
    setting_custom TEXT,
    style TEXT DEFAULT 'cartoon',
    moods TEXT[] DEFAULT ARRAY['warm'],
    aspect_ratio TEXT DEFAULT 'square',
    creativity_level REAL DEFAULT 0.3,
    
    -- Usage tracking
    use_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,
    
    -- Audit fields
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_user_generation_templates_user 
    ON user_generation_templates(user_id);

CREATE INDEX IF NOT EXISTS idx_user_generation_templates_user_usage 
    ON user_generation_templates(user_id, use_count DESC);

-- RLS Policies
ALTER TABLE user_generation_templates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own templates" ON user_generation_templates
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own templates" ON user_generation_templates
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own templates" ON user_generation_templates
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own templates" ON user_generation_templates
    FOR DELETE USING (auth.uid() = user_id);

-- Updated_at trigger
CREATE TRIGGER trigger_user_generation_templates_updated_at
    BEFORE UPDATE ON user_generation_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_user_generations_updated_at();


-- =====================================================
-- COMMENTS
-- =====================================================
COMMENT ON TABLE user_generations IS 'Stores AI-generated image history with favorites support';
COMMENT ON TABLE user_generation_templates IS 'Stores user-saved generation presets/templates';

COMMENT ON COLUMN user_generations.batch_id IS 'Groups images generated in the same batch (e.g., when generating 4 variations)';
COMMENT ON COLUMN user_generations.is_favorited IS 'User marked this image as a favorite';
COMMENT ON COLUMN user_generations.is_imported IS 'Image was imported to the asset library';
COMMENT ON COLUMN user_generation_templates.use_count IS 'Number of times this template was used';
