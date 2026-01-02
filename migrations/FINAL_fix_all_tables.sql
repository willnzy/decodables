-- ==============================================================================
-- FINAL 汇总修复脚本
-- 
-- 基于 v3.10_system_configs.sql 的结构（这是正确的标准）
-- 字段名: key, value, value_type, config_group
-- 
-- 执行此脚本会：
-- 1. 重建 system_configs 表（使用 v3.10 的结构）
-- 2. 插入所有 UI 文案配置
-- 3. 插入 Rate Limit 配置
-- ==============================================================================

-- 1. 删除旧表
DROP TABLE IF EXISTS config_audit_logs CASCADE;
DROP TABLE IF EXISTS system_configs CASCADE;

-- 2. 创建表（使用 v3.10 的结构）
CREATE TABLE system_configs (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  value_type TEXT NOT NULL DEFAULT 'text',
  config_group TEXT NOT NULL DEFAULT 'general',
  description TEXT,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  updated_by TEXT
);

-- 3. 创建索引
CREATE INDEX idx_system_configs_group ON system_configs(config_group);
CREATE INDEX idx_system_configs_active ON system_configs(is_active) WHERE is_active = true;
CREATE INDEX idx_system_configs_updated ON system_configs(updated_at DESC);

-- 4. 创建更新时间触发器
CREATE OR REPLACE FUNCTION update_system_configs_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_system_configs_updated_at
  BEFORE UPDATE ON system_configs
  FOR EACH ROW
  EXECUTE FUNCTION update_system_configs_timestamp();

-- 5. 启用 RLS
ALTER TABLE system_configs ENABLE ROW LEVEL SECURITY;

-- 6. RLS 策略
CREATE POLICY "Public can read active configs" ON system_configs
  FOR SELECT USING (is_active = true);

CREATE POLICY "Service role full access" ON system_configs
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- 7. 插入所有配置数据
INSERT INTO system_configs (key, value, value_type, config_group, description) VALUES
  -- ==========================================
  -- Rate Limits (for config_service.py)
  -- ==========================================
  ('rate_limit.payment.checkout', '{"limit": 5, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Checkout API rate limit'),
  ('rate_limit.payment.portal', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Billing portal rate limit'),
  ('rate_limit.marketplace.purchase', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Marketplace purchase rate limit'),
  ('rate_limit.marketplace.publish', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Listing publish rate limit'),
  ('rate_limit.marketplace.list', '{"limit": 60, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Marketplace list rate limit'),
  ('rate_limit.generate.story', '{"limit": 20, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'AI story generation rate limit'),
  ('rate_limit.generate.images', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'AI image generation rate limit'),
  ('rate_limit.tools.ocr', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'OCR rate limit'),
  ('rate_limit.export.pdf', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'PDF export rate limit'),
  ('rate_limit.export.zip', '{"limit": 5, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'ZIP export rate limit'),
  ('rate_limit.export.preview', '{"limit": 20, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Preview rate limit'),
  ('rate_limit.projects.create', '{"limit": 20, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Project creation rate limit'),
  ('rate_limit.assets.upload', '{"limit": 20, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Asset upload rate limit'),
  ('rate_limit.support.email', '{"limit": 3, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Support email rate limit'),
  ('rate_limit.contact.form', '{"limit": 3, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Contact form rate limit'),
  ('rate_limit.feedback.submit', '{"limit": 3, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Feedback submission rate limit'),
  ('rate_limit.admin.credits', '{"limit": 30, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin credit adjustment rate limit'),
  ('rate_limit.admin.tier', '{"limit": 30, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin tier update rate limit'),
  ('rate_limit.admin.refund', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin refund rate limit'),
  ('rate_limit.admin.subscription', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin subscription rate limit'),
  ('rate_limit.admin.broadcast', '{"limit": 5, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin broadcast rate limit'),
  ('rate_limit.admin.search', '{"limit": 60, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin search rate limit'),
  ('rate_limit.analytics.events', '{"limit": 60, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Analytics events rate limit'),
  ('rate_limit.global.default', '{"limit": 100, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Global default rate limit'),
  ('rate_limit.global.enabled', '{"enabled": true}', 'json', 'rate_limit', 'Global rate limiting enabled'),

  -- ==========================================
  -- Marketing UI Text
  -- ==========================================
  ('HOME_HERO_TITLE', 'Create Beautiful 8-Page Zines in Minutes', 'text', 'marketing', 'Homepage hero section main title'),
  ('HOME_HERO_SUBTITLE', 'AI-powered story generation meets easy drag-and-drop editing. Perfect for teachers, parents, and creative minds.', 'text', 'marketing', 'Homepage hero section subtitle'),
  ('PRICING_TIP_PRO', 'Best for professional educators and content creators', 'text', 'marketing', 'Pro plan description tip'),
  ('PRICING_TIP_STARTER', 'Great for educators getting started', 'text', 'marketing', 'Starter plan description tip'),

  -- ==========================================
  -- Feature Flags
  -- ==========================================
  ('FEATURE_AI_GENERATION', 'true', 'boolean', 'feature_flag', 'Enable AI image generation'),
  ('FEATURE_MARKETPLACE', 'true', 'boolean', 'feature_flag', 'Enable marketplace'),
  ('FEATURE_OCR', 'true', 'boolean', 'feature_flag', 'Enable OCR/Smart Scan'),
  ('FEATURE_ZIP_EXPORT', 'true', 'boolean', 'feature_flag', 'Enable ZIP export'),

  -- ==========================================
  -- Limits
  -- ==========================================
  ('FREE_PROJECT_LIMIT', '1', 'number', 'limits', 'Max projects for free tier'),
  ('STARTER_PROJECT_LIMIT', '20', 'number', 'limits', 'Max projects for starter tier'),
  ('PRO_PROJECT_LIMIT', '200', 'number', 'limits', 'Max projects for pro tier'),
  ('MAX_UPLOAD_FILE_SIZE_MB', '5', 'number', 'limits', 'Max file upload size in MB'),
  ('MAX_LISTING_PRICE', '500', 'number', 'limits', 'Max marketplace listing price'),

  -- ==========================================
  -- Credits/Costs
  -- ==========================================
  ('CREDITS_PER_IMAGE', '5', 'number', 'credits', 'Credits per AI image'),
  ('CREDITS_PER_OCR', '5', 'number', 'credits', 'Credits per OCR'),
  ('CREDITS_PER_AI_DESIGN_PAGE', '5', 'number', 'credits', 'Credits per AI design page'),
  ('CREDITS_COST_WITH_REFERENCE', '7', 'number', 'credits', 'Credits with reference image'),
  ('SIGNUP_BONUS_CREDITS', '50', 'number', 'credits', 'Signup bonus credits'),

  -- ==========================================
  -- Pricing
  -- ==========================================
  ('CREDITS_PRICE_BASE', '4.99', 'number', 'pricing', 'Base price for 100 credits'),
  ('CREDITS_PRICE_PRO', '3.99', 'number', 'pricing', 'Pro user price for 100 credits'),
  ('PRO_CREDITS_DISCOUNT_PERCENT', '20', 'number', 'pricing', 'Pro user discount %'),
  ('STARTER_PLAN_PRICE', '14.9', 'number', 'pricing', 'Starter monthly price'),
  ('PRO_PLAN_PRICE', '29.9', 'number', 'pricing', 'Pro monthly price'),
  ('STARTER_MONTHLY_CREDITS', '500', 'number', 'pricing', 'Starter monthly credits'),
  ('PRO_MONTHLY_CREDITS', '1000', 'number', 'pricing', 'Pro monthly credits'),

  -- ==========================================
  -- Trial
  -- ==========================================
  ('TRIAL_PERIOD_DAYS', '7', 'number', 'trial', 'Trial period days'),

  -- ==========================================
  -- Error Messages
  -- ==========================================
  ('ERROR_INSUFFICIENT_CREDITS', 'You don''t have enough credits. Please top up to continue.', 'text', 'error_msg', 'Insufficient credits error'),
  ('ERROR_UPLOAD_FAILED', 'Failed to upload file. Please try again or use a smaller file.', 'text', 'error_msg', 'Upload failed error'),
  ('ERROR_FILE_TOO_LARGE', 'File too large. Maximum size is {size}MB', 'text', 'error_msg', 'File too large error'),
  ('ERROR_PROJECT_LIMIT_REACHED', 'Maximum {limit} projects reached. Upgrade to create more.', 'text', 'error_msg', 'Project limit error'),
  ('ERROR_NOT_ENOUGH_CREDITS', 'Not enough credits', 'text', 'error_msg', 'Not enough credits'),
  ('ERROR_CONTENT_POLICY', 'Content Policy Violation: Please modify your prompt', 'text', 'error_msg', 'Content policy error'),
  ('ERROR_GENERATION_FAILED', 'Generation failed. Please try again.', 'text', 'error_msg', 'Generation failed error'),

  -- ==========================================
  -- Toast Success Messages
  -- ==========================================
  ('TOAST_TEMPLATE_SAVED', '✨ Template saved!', 'text', 'toast', 'Template saved toast'),
  ('TOAST_TEMPLATE_DELETED', 'Template deleted', 'text', 'toast', 'Template deleted toast'),
  ('TOAST_IMAGE_SAVED', 'Image saved to My Assets', 'text', 'toast', 'Image saved toast'),
  ('TOAST_IMAGE_ADDED', 'Image added to page', 'text', 'toast', 'Image added toast'),
  ('TOAST_CONFIG_UPDATED', 'Configuration updated successfully', 'text', 'toast', 'Config updated toast'),
  ('TOAST_SAVED_SUCCESS', 'Saved successfully!', 'text', 'toast', 'Save success toast'),
  ('TOAST_PROJECT_DUPLICATED', 'Project duplicated successfully!', 'text', 'toast', 'Project duplicated toast'),
  ('TOAST_PROJECT_PUBLISHED', 'Project published successfully!', 'text', 'toast', 'Project published toast'),

  -- ==========================================
  -- Toast Error Messages
  -- ==========================================
  ('TOAST_SAVE_FAILED', 'Failed to save. Please try again.', 'text', 'toast', 'Save failed toast'),
  ('TOAST_GENERATION_FAILED', 'Generation failed. Please try again.', 'text', 'toast', 'Generation failed toast'),
  ('TOAST_EXPORT_FAILED', 'Export failed. Please try again.', 'text', 'toast', 'Export failed toast'),
  ('TOAST_UPLOAD_FAILED', 'Upload failed: {error}', 'text', 'toast', 'Upload failed toast'),
  ('TOAST_CONFIG_LOAD_FAILED', 'Failed to load configurations', 'text', 'toast', 'Config load failed toast'),

  -- ==========================================
  -- UI Labels
  -- ==========================================
  ('UI_UPGRADE_CTA', 'Upgrade Now', 'text', 'ui', 'Upgrade button text'),
  ('UI_UPGRADE_TO_PRO', 'Upgrade to Pro', 'text', 'ui', 'Upgrade to Pro text'),
  ('UI_BUY_CREDITS', 'Buy Credits', 'text', 'ui', 'Buy credits button'),
  ('UI_SIGN_IN', 'Sign In', 'text', 'ui', 'Sign in button'),
  ('UI_CREDITS_LABEL_TOTAL', 'Total Credits', 'text', 'ui', 'Total credits label'),
  ('UI_CREDITS_LABEL_MONTHLY', 'Monthly Credits', 'text', 'ui', 'Monthly credits label'),
  ('UI_CREDITS_LABEL_PERMANENT', 'Permanent Credits', 'text', 'ui', 'Permanent credits label'),

  -- ==========================================
  -- Button Text
  -- ==========================================
  ('BTN_CANCEL', 'Cancel', 'text', 'button', 'Cancel button'),
  ('BTN_DELETE', 'Delete', 'text', 'button', 'Delete button'),
  ('BTN_PUBLISH', 'Publish', 'text', 'button', 'Publish button'),
  ('BTN_RESTORE', 'Restore', 'text', 'button', 'Restore button'),

  -- ==========================================
  -- Loading States
  -- ==========================================
  ('LOADING_DEFAULT', 'Loading...', 'text', 'loading', 'Default loading'),
  ('LOADING_GENERATING', 'Generating...', 'text', 'loading', 'Generating loading'),
  ('LOADING_SAVING', 'Saving...', 'text', 'loading', 'Saving loading'),

  -- ==========================================
  -- Empty States
  -- ==========================================
  ('EMPTY_NO_ASSETS', 'No assets yet', 'text', 'empty_state', 'No assets empty state'),
  ('EMPTY_NO_TEMPLATES', 'No saved templates yet', 'text', 'empty_state', 'No templates empty state'),
  ('EMPTY_NO_TRANSACTIONS', 'No transactions yet', 'text', 'empty_state', 'No transactions empty state')

ON CONFLICT (key) DO UPDATE SET
  value = EXCLUDED.value,
  value_type = EXCLUDED.value_type,
  config_group = EXCLUDED.config_group,
  description = EXCLUDED.description,
  updated_at = NOW();

-- 8. 创建审计日志表
CREATE TABLE IF NOT EXISTS config_audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  config_key TEXT NOT NULL,
  old_value TEXT,
  new_value TEXT,
  action TEXT NOT NULL,
  changed_by TEXT,
  changed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_config_audit_key ON config_audit_logs(config_key);
CREATE INDEX idx_config_audit_time ON config_audit_logs(changed_at DESC);

ALTER TABLE config_audit_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role access" ON config_audit_logs FOR ALL TO service_role USING (true);

-- 9. 验证
SELECT '✅ 修复完成!' as status;
SELECT config_group, COUNT(*) as count FROM system_configs GROUP BY config_group ORDER BY config_group;
SELECT 'Total: ' || COUNT(*)::text FROM system_configs;
