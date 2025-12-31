-- =============================================
-- System Configuration Table
--  - 
-- =============================================

-- 
CREATE TABLE IF NOT EXISTS system_config (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    config_key TEXT UNIQUE NOT NULL,           -- 
    config_value JSONB NOT NULL,               -- （JSON，）
    category TEXT NOT NULL DEFAULT 'general',  -- ：rate_limit, analytics, system
    description TEXT,                          -- 
    is_active BOOLEAN DEFAULT true,            -- 
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by TEXT                            -- ID
);

-- 
CREATE INDEX IF NOT EXISTS idx_system_config_key ON system_config(config_key);
CREATE INDEX IF NOT EXISTS idx_system_config_category ON system_config(category);

-- 
INSERT INTO system_config (config_key, config_value, category, description) VALUES
--  (，)
('rate_limit.payment.checkout', '{"limit": 5, "window": "minute", "enabled": true}', 'rate_limit', ''),
('rate_limit.payment.portal', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', ''),
('rate_limit.marketplace.purchase', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', ''),

-- AI  ()
('rate_limit.generate.story', '{"limit": 20, "window": "minute", "enabled": true}', 'rate_limit', 'AI'),
('rate_limit.generate.images', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', 'AI'),
('rate_limit.tools.ocr', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', 'OCR'),

--  ()
('rate_limit.export.pdf', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', 'PDF'),
('rate_limit.export.zip', '{"limit": 5, "window": "minute", "enabled": true}', 'rate_limit', 'ZIP'),
('rate_limit.export.preview', '{"limit": 20, "window": "minute", "enabled": true}', 'rate_limit', ''),

-- 
('rate_limit.projects.create', '{"limit": 20, "window": "minute", "enabled": true}', 'rate_limit', ''),
('rate_limit.assets.upload', '{"limit": 20, "window": "minute", "enabled": true}', 'rate_limit', ''),
('rate_limit.marketplace.publish', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', ''),

--  ()
('rate_limit.support.email', '{"limit": 3, "window": "minute", "enabled": true}', 'rate_limit', ''),
('rate_limit.contact.form', '{"limit": 3, "window": "minute", "enabled": true}', 'rate_limit', ''),
('rate_limit.feedback.submit', '{"limit": 3, "window": "minute", "enabled": true}', 'rate_limit', ''),

-- Admin 
('rate_limit.admin.credits', '{"limit": 30, "window": "minute", "enabled": true}', 'rate_limit', 'Admin'),
('rate_limit.admin.tier', '{"limit": 30, "window": "minute", "enabled": true}', 'rate_limit', 'Admin'),
('rate_limit.admin.refund', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', 'Admin'),
('rate_limit.admin.subscription', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', 'Admin'),
('rate_limit.admin.broadcast', '{"limit": 5, "window": "minute", "enabled": true}', 'rate_limit', 'Admin'),

-- 
('rate_limit.admin.search', '{"limit": 60, "window": "minute", "enabled": true}', 'rate_limit', 'Admin'),
('rate_limit.marketplace.list', '{"limit": 60, "window": "minute", "enabled": true}', 'rate_limit', ''),
('rate_limit.analytics.events', '{"limit": 60, "window": "minute", "enabled": true}', 'rate_limit', ''),

-- 
('rate_limit.global.default', '{"limit": 100, "window": "minute", "enabled": true}', 'rate_limit', ''),
('rate_limit.global.enabled', '{"enabled": true}', 'rate_limit', ''),

-- Analytics 
('analytics.enabled', '{"enabled": true}', 'analytics', ''),
('analytics.sampling_rate', '{"critical": 1.0, "important": 1.0, "normal": 0.3, "debug": 0.0}', 'analytics', ''),
('analytics.min_level', '{"level": "normal"}', 'analytics', '')

ON CONFLICT (config_key) DO NOTHING;

--  RLS
ALTER TABLE system_config ENABLE ROW LEVEL SECURITY;

--  service_role （ service key ）
CREATE POLICY "Service role full access to system_config"
ON system_config FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- 
CREATE OR REPLACE FUNCTION update_system_config_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_system_config_timestamp
    BEFORE UPDATE ON system_config
    FOR EACH ROW
    EXECUTE FUNCTION update_system_config_timestamp();

-- 
CREATE OR REPLACE FUNCTION get_rate_limit_config(p_config_key TEXT)
RETURNS JSONB AS $$
DECLARE
    v_config JSONB;
BEGIN
    SELECT config_value INTO v_config
    FROM system_config
    WHERE config_key = p_config_key AND is_active = true;
    
    IF v_config IS NULL THEN
        -- 
        SELECT config_value INTO v_config
        FROM system_config
        WHERE config_key = 'rate_limit.global.default' AND is_active = true;
    END IF;
    
    RETURN COALESCE(v_config, '{"limit": 100, "window": "minute", "enabled": true}'::JSONB);
END;
$$ LANGUAGE plpgsql;

