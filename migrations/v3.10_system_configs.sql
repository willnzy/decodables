-- ==========================================
-- v3.10: Global Dynamic Configuration System
-- 全局动态文案配置系统
-- ==========================================

-- 1. Create system_configs table
CREATE TABLE IF NOT EXISTS system_configs (
  key TEXT PRIMARY KEY,                           -- 唯一键名 (e.g., HOME_HERO_TITLE)
  value TEXT NOT NULL,                            -- 配置值 (支持纯文本或 JSON 字符串)
  value_type TEXT NOT NULL DEFAULT 'text',        -- 值类型: 'text', 'boolean', 'json', 'number'
  config_group TEXT NOT NULL DEFAULT 'general',   -- 分组: marketing, error_msg, feature_flag, etc.
  description TEXT,                               -- 备注说明 (给运营人员)
  is_active BOOLEAN DEFAULT true,                 -- 是否启用
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  updated_by TEXT REFERENCES profiles(id)         -- 最后修改人
);

-- 2. Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_system_configs_group ON system_configs(config_group);
CREATE INDEX IF NOT EXISTS idx_system_configs_active ON system_configs(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_system_configs_updated ON system_configs(updated_at DESC);

-- 3. Create trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_system_configs_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_system_configs_updated_at ON system_configs;
CREATE TRIGGER trg_system_configs_updated_at
  BEFORE UPDATE ON system_configs
  FOR EACH ROW
  EXECUTE FUNCTION update_system_configs_timestamp();

-- 4. Enable RLS
ALTER TABLE system_configs ENABLE ROW LEVEL SECURITY;

-- 5. RLS Policies
-- Public read for active configs (for frontend consumption)
DROP POLICY IF EXISTS "Public can read active configs" ON system_configs;
CREATE POLICY "Public can read active configs" ON system_configs
  FOR SELECT USING (is_active = true);

-- Admin can manage all configs
DROP POLICY IF EXISTS "Admin can manage configs" ON system_configs;
CREATE POLICY "Admin can manage configs" ON system_configs
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM profiles 
      WHERE id = (SELECT auth.jwt() ->> 'sub') 
      AND role = 'admin'
    )
  );

-- 6. Insert sample data
INSERT INTO system_configs (key, value, value_type, config_group, description) VALUES
  -- Marketing Group
  ('HOME_HERO_TITLE', 'Create Beautiful 8-Page Zines in Minutes', 'text', 'marketing', 'Homepage hero section main title'),
  ('HOME_HERO_SUBTITLE', 'AI-powered story generation meets easy drag-and-drop editing. Perfect for teachers, parents, and creative minds.', 'text', 'marketing', 'Homepage hero section subtitle'),
  ('PRICING_TIP_PRO', 'Best for professional educators and content creators', 'text', 'marketing', 'Pro plan description tip on pricing page'),
  
  -- Feature Flags Group
  ('FEATURE_AI_GENERATION', 'true', 'boolean', 'feature_flag', 'Enable/disable AI image generation feature'),
  ('FEATURE_MARKETPLACE', 'true', 'boolean', 'feature_flag', 'Enable/disable marketplace feature'),
  ('FEATURE_OCR', 'true', 'boolean', 'feature_flag', 'Enable/disable OCR/Smart Scan feature'),
  
  -- Limits Group
  ('FREE_PROJECT_LIMIT', '1', 'number', 'limits', 'Maximum projects for free tier users'),
  ('STARTER_PROJECT_LIMIT', '20', 'number', 'limits', 'Maximum projects for starter tier users'),
  ('PRO_PROJECT_LIMIT', '200', 'number', 'limits', 'Maximum projects for pro tier users'),
  
  -- Pricing Group
  ('CREDITS_PRICE_BASE', '4.99', 'number', 'pricing', 'Base price for 100 credits (USD)'),
  ('CREDITS_PRICE_PRO', '3.99', 'number', 'pricing', 'Discounted price for Pro users (USD)'),
  
  -- Error Messages Group
  ('ERROR_INSUFFICIENT_CREDITS', 'You don''t have enough credits. Please top up to continue.', 'text', 'error_msg', 'Shown when user has insufficient credits'),
  ('ERROR_UPLOAD_FAILED', 'Failed to upload file. Please try again or use a smaller file.', 'text', 'error_msg', 'Shown when file upload fails'),
  
  -- Notification Templates
  ('NOTIF_WELCOME', '{"title": "Welcome to Make Decodables!", "content": "Start creating your first zine today. We''ve given you 50 free credits to get started!"}', 'json', 'notification', 'Welcome notification template for new users'),
  
  -- UI Texts
  ('UI_UPGRADE_CTA', 'Upgrade Now', 'text', 'ui', 'Upgrade button text'),
  ('UI_TRIAL_BANNER', 'You have {days} days left in your free trial', 'text', 'ui', 'Trial period banner text (supports {days} placeholder)')

ON CONFLICT (key) DO NOTHING;

-- 7. Create helper function to get config with default fallback
CREATE OR REPLACE FUNCTION get_config(config_key TEXT, default_value TEXT DEFAULT NULL)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  result TEXT;
BEGIN
  SELECT value INTO result
  FROM system_configs
  WHERE key = config_key AND is_active = true;
  
  RETURN COALESCE(result, default_value);
END;
$$;

-- 8. Create function to get configs by group
CREATE OR REPLACE FUNCTION get_configs_by_group(group_name TEXT)
RETURNS TABLE(key TEXT, value TEXT, value_type TEXT, description TEXT)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  RETURN QUERY
  SELECT sc.key, sc.value, sc.value_type, sc.description
  FROM system_configs sc
  WHERE sc.config_group = group_name AND sc.is_active = true
  ORDER BY sc.key;
END;
$$;

-- 9. Create audit log for config changes
CREATE TABLE IF NOT EXISTS config_audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  config_key TEXT NOT NULL,
  old_value TEXT,
  new_value TEXT,
  action TEXT NOT NULL,  -- 'create', 'update', 'delete'
  changed_by TEXT REFERENCES profiles(id),
  changed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_config_audit_key ON config_audit_logs(config_key);
CREATE INDEX IF NOT EXISTS idx_config_audit_time ON config_audit_logs(changed_at DESC);

-- Audit log RLS
ALTER TABLE config_audit_logs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Admin can read audit logs" ON config_audit_logs;
CREATE POLICY "Admin can read audit logs" ON config_audit_logs
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM profiles 
      WHERE id = (SELECT auth.jwt() ->> 'sub') 
      AND role = 'admin'
    )
  );

DROP POLICY IF EXISTS "System can write audit logs" ON config_audit_logs;
CREATE POLICY "System can write audit logs" ON config_audit_logs
  FOR INSERT WITH CHECK (true);

COMMENT ON TABLE system_configs IS 'Global dynamic configuration system for app-wide settings and texts';
COMMENT ON TABLE config_audit_logs IS 'Audit trail for configuration changes';
