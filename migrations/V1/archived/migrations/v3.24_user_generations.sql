-- =============================================================================
-- Migration v3.24: User Generations History Table
-- 用户 AI 生成历史记录
-- =============================================================================
-- 
-- Purpose:
-- - Track all AI image generations per user
-- - Store prompt details, style parameters, and generation metadata
-- - Support generation history viewing and analytics
--
-- Note: This table was used in code but migration was missing.
--       Adding retroactively as v3.24.
--
-- =============================================================================

-- =====================================================
-- 1. User Generations Table
-- =====================================================

CREATE TABLE IF NOT EXISTS user_generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    
    -- Image info
    image_url TEXT NOT NULL,
    
    -- Prompt details
    original_prompt TEXT,
    enhanced_prompt TEXT,
    negative_prompt TEXT,
    
    -- Style parameters
    style VARCHAR(50),
    moods TEXT[],
    aspect_ratio VARCHAR(50),
    generation_mode VARCHAR(20),
    creativity_level REAL,
    
    -- 5W1H parameters
    who_param TEXT,
    what_param TEXT,
    where_param TEXT,
    
    -- Reference image
    has_reference BOOLEAN DEFAULT false,
    reference_strength REAL,
    
    -- Batch info
    batch_id VARCHAR(50),
    batch_index INTEGER,
    
    -- Credits and model
    credits_used INTEGER DEFAULT 0,
    model_used VARCHAR(100),
    generation_time_ms INTEGER,
    
    -- Timezone support (v3.9)
    timezone TEXT DEFAULT 'UTC',
    created_at_local TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE user_generations IS 'AI image generation history for each user';

-- =====================================================
-- 2. Indexes
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_user_generations_user_id 
    ON user_generations(user_id);
CREATE INDEX IF NOT EXISTS idx_user_generations_batch_id 
    ON user_generations(batch_id);
CREATE INDEX IF NOT EXISTS idx_user_generations_created_at 
    ON user_generations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_generations_model 
    ON user_generations(model_used);

-- =====================================================
-- 3. Row Level Security
-- =====================================================

ALTER TABLE user_generations ENABLE ROW LEVEL SECURITY;

-- Users can view their own generations
DROP POLICY IF EXISTS user_generations_select_policy ON user_generations;
CREATE POLICY user_generations_select_policy ON user_generations
    FOR SELECT
    USING (user_id = auth.uid()::text OR auth.role() = 'service_role');

-- Service role has full access (for backend insertion)
DROP POLICY IF EXISTS user_generations_service_policy ON user_generations;
CREATE POLICY user_generations_service_policy ON user_generations
    FOR ALL
    USING (auth.role() = 'service_role');

-- =====================================================
-- 4. Helper Functions (Optional)
-- =====================================================

-- Get user's recent generations
CREATE OR REPLACE FUNCTION get_user_generations(
    p_user_id TEXT,
    p_limit INTEGER DEFAULT 50,
    p_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
    id UUID,
    image_url TEXT,
    original_prompt TEXT,
    enhanced_prompt TEXT,
    style VARCHAR(50),
    model_used VARCHAR(100),
    credits_used INTEGER,
    created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ug.id,
        ug.image_url,
        ug.original_prompt,
        ug.enhanced_prompt,
        ug.style,
        ug.model_used,
        ug.credits_used,
        ug.created_at
    FROM user_generations ug
    WHERE ug.user_id = p_user_id
    ORDER BY ug.created_at DESC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$;

-- Get generation stats for a user
CREATE OR REPLACE FUNCTION get_user_generation_stats(p_user_id TEXT)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_stats JSONB;
BEGIN
    SELECT jsonb_build_object(
        'total_generations', COUNT(*),
        'total_credits_used', COALESCE(SUM(credits_used), 0),
        'favorite_style', (
            SELECT style FROM user_generations 
            WHERE user_id = p_user_id AND style IS NOT NULL
            GROUP BY style ORDER BY COUNT(*) DESC LIMIT 1
        ),
        'favorite_model', (
            SELECT model_used FROM user_generations 
            WHERE user_id = p_user_id AND model_used IS NOT NULL
            GROUP BY model_used ORDER BY COUNT(*) DESC LIMIT 1
        ),
        'first_generation', MIN(created_at),
        'last_generation', MAX(created_at)
    ) INTO v_stats
    FROM user_generations
    WHERE user_id = p_user_id;
    
    RETURN v_stats;
END;
$$;

-- =====================================================
-- End of Migration v3.24
-- =====================================================
