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
  ('PRICING_TIP_STARTER', 'Great for educators getting started', 'text', 'marketing', 'Starter plan description tip on pricing page'),
  
  -- Feature Flags Group
  ('FEATURE_AI_GENERATION', 'true', 'boolean', 'feature_flag', 'Enable/disable AI image generation feature'),
  ('FEATURE_MARKETPLACE', 'true', 'boolean', 'feature_flag', 'Enable/disable marketplace feature'),
  ('FEATURE_OCR', 'true', 'boolean', 'feature_flag', 'Enable/disable OCR/Smart Scan feature'),
  ('FEATURE_ZIP_EXPORT', 'true', 'boolean', 'feature_flag', 'Enable/disable ZIP export feature'),
  
  -- Limits Group
  ('FREE_PROJECT_LIMIT', '1', 'number', 'limits', 'Maximum projects for free tier users'),
  ('STARTER_PROJECT_LIMIT', '20', 'number', 'limits', 'Maximum projects for starter tier users'),
  ('PRO_PROJECT_LIMIT', '200', 'number', 'limits', 'Maximum projects for pro tier users'),
  ('MAX_UPLOAD_FILE_SIZE_MB', '5', 'number', 'limits', 'Maximum file upload size in MB'),
  ('MAX_LISTING_PRICE', '500', 'number', 'limits', 'Maximum price for marketplace listings in credits'),
  
  -- Credits/Costs Group
  ('CREDITS_PER_IMAGE', '5', 'number', 'credits', 'Credits cost per AI generated image'),
  ('CREDITS_PER_OCR', '5', 'number', 'credits', 'Credits cost per OCR/Smart Scan'),
  ('CREDITS_PER_AI_DESIGN_PAGE', '5', 'number', 'credits', 'Credits cost per AI design page'),
  ('CREDITS_COST_WITH_REFERENCE', '7', 'number', 'credits', 'Credits cost for AI generation with reference image'),
  ('SIGNUP_BONUS_CREDITS', '50', 'number', 'credits', 'Permanent credits given to new users on signup'),
  
  -- Pricing Group
  ('CREDITS_PRICE_BASE', '4.99', 'number', 'pricing', 'Base price for 100 credits (USD)'),
  ('CREDITS_PRICE_PRO', '3.99', 'number', 'pricing', 'Discounted price for Pro users (USD)'),
  ('PRO_CREDITS_DISCOUNT_PERCENT', '20', 'number', 'pricing', 'Discount percentage for Pro users on credit purchases'),
  ('STARTER_PLAN_PRICE', '14.9', 'number', 'pricing', 'Monthly price for Starter plan (USD)'),
  ('PRO_PLAN_PRICE', '29.9', 'number', 'pricing', 'Monthly price for Pro plan (USD)'),
  ('STARTER_MONTHLY_CREDITS', '500', 'number', 'pricing', 'Monthly credits for Starter plan'),
  ('PRO_MONTHLY_CREDITS', '1000', 'number', 'pricing', 'Monthly credits for Pro plan'),
  
  -- Trial Group
  ('TRIAL_PERIOD_DAYS', '7', 'number', 'trial', 'Number of days for free trial period'),
  
  -- Error Messages Group
  ('ERROR_INSUFFICIENT_CREDITS', 'You don''t have enough credits. Please top up to continue.', 'text', 'error_msg', 'Shown when user has insufficient credits'),
  ('ERROR_UPLOAD_FAILED', 'Failed to upload file. Please try again or use a smaller file.', 'text', 'error_msg', 'Shown when file upload fails'),
  ('ERROR_FILE_TOO_LARGE', 'File too large. Maximum size is {size}MB', 'text', 'error_msg', 'Shown when uploaded file exceeds size limit'),
  ('ERROR_PROJECT_LIMIT_REACHED', 'Maximum {limit} projects reached. Upgrade to create more.', 'text', 'error_msg', 'Shown when user reaches project limit'),
  
  -- Notification Templates
  ('NOTIF_WELCOME', '{"title": "Welcome to Make Decodables!", "content": "Start creating your first zine today. We''ve given you 50 free credits to get started!"}', 'json', 'notification', 'Welcome notification template for new users'),
  
  -- UI Texts
  ('UI_UPGRADE_CTA', 'Upgrade Now', 'text', 'ui', 'Upgrade button text'),
  ('UI_TRIAL_BANNER', 'You have {days} days left in your free trial', 'text', 'ui', 'Trial period banner text (supports {days} placeholder)'),
  ('UI_TRIAL_EXPIRED', 'Your 7-day trial period has expired. This project is read-only.', 'text', 'ui', 'Trial expired message'),
  ('UI_TRIAL_EXPIRED_UPGRADE', 'Trial expired - Upgrade to continue', 'text', 'ui', 'Trial expired upgrade button text'),
  ('UI_UPGRADE_TO_STARTER', 'Upgrade to Starter', 'text', 'ui', 'Upgrade to Starter button text'),
  ('UI_UPGRADE_TO_PRO', 'Upgrade to Pro', 'text', 'ui', 'Upgrade to Pro button text'),
  ('UI_PUBLISH_PROMPT', 'Publish your projects to start earning credits', 'text', 'ui', 'Dashboard prompt to publish projects'),
  ('UI_CREDITS_LABEL_TOTAL', 'Total Credits', 'text', 'ui', 'Label for total credits'),
  ('UI_CREDITS_LABEL_MONTHLY', 'Monthly Credits', 'text', 'ui', 'Label for monthly credits'),
  ('UI_CREDITS_LABEL_PERMANENT', 'Permanent Credits', 'text', 'ui', 'Label for permanent credits'),
  ('UI_CREDITS_ABBREVIATION_MONTHLY', 'Monthly', 'text', 'ui', 'Abbreviation for monthly credits'),
  ('UI_CREDITS_ABBREVIATION_PERMANENT', 'Permanent', 'text', 'ui', 'Abbreviation for permanent credits'),
  
  -- File Upload Hints
  ('UI_UPLOAD_HINT_IMAGE', 'JPG, PNG, GIF, WebP · Max {size}MB', 'text', 'ui', 'File type hint for image upload'),
  ('UI_UPLOAD_HINT_IMAGE_SVG', 'JPG, PNG, GIF, WebP, SVG · Max {size}MB', 'text', 'ui', 'File type hint for image upload with SVG'),
  ('UI_UPLOAD_HINT_IMAGE_PDF', 'Images (JPG, PNG, WebP) or PDF · Max {size}MB', 'text', 'ui', 'File type hint for image/PDF upload'),
  ('UI_UPLOAD_HINT_REFERENCE', 'PNG, JPG, WebP · Max {size}MB', 'text', 'ui', 'File type hint for reference image upload'),
  ('UI_UPLOAD_HINT_REFERENCE_COMPACT', 'JPG/PNG/WebP|Max {size}MB', 'text', 'ui', 'Compact file type hint with pipe as line separator'),
  ('UI_UPLOAD_HINT_FEEDBACK', 'Max 5 images, {size}MB each', 'text', 'ui', 'File type hint for feedback image upload'),
  
  -- File Upload Error Messages  
  ('ERROR_INVALID_IMAGE_TYPE', 'Please upload JPG, PNG, or WebP image', 'text', 'error_msg', 'Error when invalid image type uploaded'),
  ('ERROR_INVALID_IMAGE_TYPE_FULL', 'Please upload an image file (PNG, JPG, WebP)', 'text', 'error_msg', 'Error when invalid image type uploaded (full format)'),
  ('ERROR_INVALID_IMAGE_TYPE_ALL', 'Only JPG, PNG, GIF, WebP images are allowed', 'text', 'error_msg', 'Error when invalid image type uploaded (all formats)'),
  
  -- Plan Feature Descriptions
  ('PLAN_FEATURE_STARTER_PROJECTS', 'Up to 20 projects', 'text', 'plan_features', 'Starter plan project limit description'),
  ('PLAN_FEATURE_PRO_PROJECTS', 'Up to 200 projects', 'text', 'plan_features', 'Pro plan project limit description'),
  ('PLAN_FEATURE_PRO_CREDITS_DISCOUNT', '20% off credits', 'text', 'plan_features', 'Pro plan credit discount description'),
  ('PLAN_FEATURE_ZIP_EXPORT', 'ZIP Export', 'text', 'plan_features', 'ZIP export feature description'),
  ('PLAN_FEATURE_OCR', 'Smart Scan (OCR)', 'text', 'plan_features', 'OCR feature description'),
  ('PLAN_FEATURE_COMMERCIAL_LICENSE', 'Commercial License', 'text', 'plan_features', 'Commercial license feature description'),
  ('PLAN_FEATURE_PERSONAL_UPLOAD', 'Personal Asset Upload', 'text', 'plan_features', 'Personal upload feature description'),
  ('PLAN_FEATURE_PROJECT_TEMPLATES', 'Project Templates', 'text', 'plan_features', 'Project templates feature description')

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
