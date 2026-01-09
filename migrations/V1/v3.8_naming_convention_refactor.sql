-- ==============================================================================
-- Migration: v3.8 Naming Convention Refactor
-- Date: 2026-01-02
-- ==============================================================================
-- This migration renames tables and columns to follow consistent naming conventions:
-- 1. All tables use plural form
-- 2. 5W1H column naming for asset prompt templates
-- 3. Clearer table names for prompt templates
-- ==============================================================================

-- ==========================================
-- Step 1: Rename Tables
-- ==========================================

-- 1.1 Rename listing_usage → listing_usages
ALTER TABLE IF EXISTS listing_usage RENAME TO listing_usages;

-- 1.2 Rename system_config → system_configs  
ALTER TABLE IF EXISTS system_config RENAME TO system_configs;

-- 1.3 Rename user_generation_templates → asset_prompt_templates
ALTER TABLE IF EXISTS user_generation_templates RENAME TO asset_prompt_templates;

-- 1.4 Rename page_design_templates → page_prompt_templates
ALTER TABLE IF EXISTS page_design_templates RENAME TO page_prompt_templates;

-- ==========================================
-- Step 2: Rename Columns (asset_prompt_templates)
-- ==========================================

-- 2.1 Rename 5W1H columns
ALTER TABLE asset_prompt_templates RENAME COLUMN character_type TO who_type;
ALTER TABLE asset_prompt_templates RENAME COLUMN character_custom TO who_custom;
ALTER TABLE asset_prompt_templates RENAME COLUMN action_type TO what_type;
ALTER TABLE asset_prompt_templates RENAME COLUMN action_custom TO what_custom;
ALTER TABLE asset_prompt_templates RENAME COLUMN setting_type TO where_type;
ALTER TABLE asset_prompt_templates RENAME COLUMN setting_custom TO where_custom;

-- 2.2 Add negative_prompt column if not exists
ALTER TABLE asset_prompt_templates 
ADD COLUMN IF NOT EXISTS negative_prompt TEXT;

-- ==========================================
-- Step 3: Update Indexes
-- ==========================================

-- 3.1 Drop old indexes
DROP INDEX IF EXISTS idx_system_config_key;
DROP INDEX IF EXISTS idx_system_config_category;
DROP INDEX IF EXISTS idx_user_templates_user;
DROP INDEX IF EXISTS idx_user_templates_user_usage;
DROP INDEX IF EXISTS idx_page_design_templates_user;
DROP INDEX IF EXISTS idx_page_design_templates_usage;

-- 3.2 Create new indexes with correct names
CREATE INDEX IF NOT EXISTS idx_system_configs_key ON system_configs(config_key);
CREATE INDEX IF NOT EXISTS idx_system_configs_category ON system_configs(category);
CREATE INDEX IF NOT EXISTS idx_asset_prompt_templates_user ON asset_prompt_templates(user_id);
CREATE INDEX IF NOT EXISTS idx_asset_prompt_templates_usage ON asset_prompt_templates(user_id, use_count DESC);
CREATE INDEX IF NOT EXISTS idx_page_prompt_templates_user ON page_prompt_templates(user_id);
CREATE INDEX IF NOT EXISTS idx_page_prompt_templates_usage ON page_prompt_templates(user_id, use_count DESC);

-- ==========================================
-- Step 4: Update RLS Policies
-- ==========================================

-- 4.1 listing_usages policies
DROP POLICY IF EXISTS "Users can insert own usage" ON listing_usages;
CREATE POLICY "Users can insert own usage" ON listing_usages FOR INSERT
WITH CHECK ((SELECT auth.jwt() ->> 'sub') = used_by_user_id);

DROP POLICY IF EXISTS "Users view own usage or Admin view all" ON listing_usages;
CREATE POLICY "Users view own usage or Admin view all" ON listing_usages FOR SELECT
USING ((SELECT auth.jwt() ->> 'sub') = used_by_user_id OR is_admin());

-- 4.2 system_configs policies
DROP POLICY IF EXISTS "Service role full access to system_config" ON system_configs;
DROP POLICY IF EXISTS "Service role full access to system_configs" ON system_configs;
CREATE POLICY "Service role full access to system_configs" ON system_configs FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- 4.3 asset_prompt_templates policies
DROP POLICY IF EXISTS "Service role full access to templates" ON asset_prompt_templates;
DROP POLICY IF EXISTS "Service role full access to asset prompt templates" ON asset_prompt_templates;
CREATE POLICY "Service role full access to asset prompt templates" ON asset_prompt_templates FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- 4.4 page_prompt_templates policies
DROP POLICY IF EXISTS "Service role full access to page design templates" ON page_prompt_templates;
DROP POLICY IF EXISTS "Service role full access to page prompt templates" ON page_prompt_templates;
CREATE POLICY "Service role full access to page prompt templates" ON page_prompt_templates FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- ==========================================
-- Step 5: Update Triggers
-- ==========================================

-- 5.1 system_configs trigger
DROP TRIGGER IF EXISTS trigger_update_system_config_timestamp ON system_configs;
DROP FUNCTION IF EXISTS update_system_config_timestamp();

CREATE OR REPLACE FUNCTION update_system_configs_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_system_configs_timestamp
    BEFORE UPDATE ON system_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_system_configs_timestamp();

-- 5.2 asset_prompt_templates trigger
DROP TRIGGER IF EXISTS trigger_templates_updated_at ON asset_prompt_templates;
DROP FUNCTION IF EXISTS update_templates_updated_at();

CREATE OR REPLACE FUNCTION update_asset_prompt_templates_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_asset_prompt_templates_updated_at
    BEFORE UPDATE ON asset_prompt_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_asset_prompt_templates_updated_at();

-- 5.3 page_prompt_templates trigger
DROP TRIGGER IF EXISTS trigger_page_design_templates_updated_at ON page_prompt_templates;
DROP FUNCTION IF EXISTS update_page_design_templates_updated_at();

CREATE OR REPLACE FUNCTION update_page_prompt_templates_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_page_prompt_templates_updated_at
    BEFORE UPDATE ON page_prompt_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_page_prompt_templates_updated_at();

-- ==========================================
-- Step 6: Update Helper Functions
-- ==========================================

CREATE OR REPLACE FUNCTION get_rate_limit_config(p_config_key TEXT)
RETURNS JSONB AS $$
DECLARE
    v_config JSONB;
BEGIN
    SELECT config_value INTO v_config
    FROM system_configs
    WHERE config_key = p_config_key AND is_active = true;
    
    IF v_config IS NULL THEN
        SELECT config_value INTO v_config
        FROM system_configs
        WHERE config_key = 'rate_limit.global.default' AND is_active = true;
    END IF;
    
    RETURN COALESCE(v_config, '{"limit": 100, "window": "minute", "enabled": true}'::JSONB);
END;
$$ LANGUAGE plpgsql;

-- ==============================================================================
-- Summary of Changes:
-- ==============================================================================
-- Tables Renamed:
--   listing_usage        → listing_usages
--   system_config        → system_configs
--   user_generation_templates → asset_prompt_templates
--   page_design_templates    → page_prompt_templates
--
-- Columns Renamed (asset_prompt_templates):
--   character_type   → who_type
--   character_custom → who_custom
--   action_type      → what_type
--   action_custom    → what_custom
--   setting_type     → where_type
--   setting_custom   → where_custom
--
-- Columns Added:
--   asset_prompt_templates.negative_prompt
-- ==============================================================================
