-- ==============================================================================
-- Fix system_configs Table - v2 (简化版)
-- 
-- 使用字段: config_key, config_value, category, value_type
-- ==============================================================================

-- 1. 删除旧表
DROP TABLE IF EXISTS system_configs CASCADE;

-- 2. 创建新表
CREATE TABLE system_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_key TEXT NOT NULL UNIQUE,
    config_value JSONB NOT NULL,
    value_type TEXT DEFAULT 'json',
    category TEXT DEFAULT 'general',
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by TEXT
);

-- 3. 创建索引
CREATE INDEX idx_system_configs_key ON system_configs(config_key);
CREATE INDEX idx_system_configs_category ON system_configs(category);

-- 4. 启用 RLS
ALTER TABLE system_configs ENABLE ROW LEVEL SECURITY;

-- 5. RLS 策略
CREATE POLICY "Service role full access" ON system_configs FOR ALL
    TO service_role USING (true) WITH CHECK (true);

-- 6. 插入数据
INSERT INTO system_configs (config_key, config_value, value_type, category, description) VALUES
-- Rate Limits
('rate_limit.payment.checkout', '{"limit": 5, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Checkout API'),
('rate_limit.payment.portal', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Billing portal'),
('rate_limit.marketplace.purchase', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Marketplace purchase'),
('rate_limit.marketplace.publish', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Listing publish'),
('rate_limit.marketplace.list', '{"limit": 60, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Marketplace list'),
('rate_limit.generate.story', '{"limit": 20, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'AI story'),
('rate_limit.generate.images', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'AI images'),
('rate_limit.tools.ocr', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'OCR'),
('rate_limit.export.pdf', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'PDF export'),
('rate_limit.export.zip', '{"limit": 5, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'ZIP export'),
('rate_limit.export.preview', '{"limit": 20, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Preview'),
('rate_limit.projects.create', '{"limit": 20, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Project create'),
('rate_limit.assets.upload', '{"limit": 20, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Asset upload'),
('rate_limit.support.email', '{"limit": 3, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Support email'),
('rate_limit.contact.form', '{"limit": 3, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Contact form'),
('rate_limit.feedback.submit', '{"limit": 3, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Feedback'),
('rate_limit.admin.credits', '{"limit": 30, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin credits'),
('rate_limit.admin.tier', '{"limit": 30, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin tier'),
('rate_limit.admin.refund', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin refund'),
('rate_limit.admin.subscription', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin subscription'),
('rate_limit.admin.broadcast', '{"limit": 5, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin broadcast'),
('rate_limit.admin.search', '{"limit": 60, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin search'),
('rate_limit.analytics.events', '{"limit": 60, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Analytics events'),
('rate_limit.global.default', '{"limit": 100, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Global default'),
('rate_limit.global.enabled', '{"enabled": true}', 'json', 'rate_limit', 'Global enabled'),
-- Analytics
('analytics.enabled', '{"enabled": true}', 'json', 'analytics', 'Enable analytics'),
('analytics.sampling_rate', '{"critical": 1.0, "important": 1.0, "normal": 0.3, "debug": 0.0}', 'json', 'analytics', 'Sampling rates'),
('analytics.min_level', '{"level": "normal"}', 'json', 'analytics', 'Min level'),
-- Features
('feature.marketplace.enabled', '{"enabled": true}', 'json', 'feature', 'Marketplace'),
('feature.ai_generation.enabled', '{"enabled": true}', 'json', 'feature', 'AI generation'),
('feature.ocr.enabled', '{"enabled": true}', 'json', 'feature', 'OCR'),
('feature.zip_export.enabled', '{"enabled": true}', 'json', 'feature', 'ZIP export'),
-- UI
('ui.cta.primary', '{"text": "Start Creating", "subtitle": "No credit card required"}', 'json', 'ui', 'Primary CTA'),
('ui.announcement.enabled', '{"enabled": false, "text": "", "link": ""}', 'json', 'ui', 'Announcement bar'),
-- Limits
('limits.free.projects', '{"max": 3}', 'json', 'limits', 'Free projects'),
('limits.free.monthly_credits', '{"amount": 50}', 'json', 'limits', 'Free credits'),
('limits.starter.monthly_credits', '{"amount": 200}', 'json', 'limits', 'Starter credits'),
('limits.pro.monthly_credits', '{"amount": 500}', 'json', 'limits', 'Pro credits'),
('limits.marketplace.max_price', '{"credits": 500}', 'json', 'limits', 'Max price');

-- 7. 验证
SELECT '✅ Done!' as status, COUNT(*) as total FROM system_configs;
SELECT category, COUNT(*) as cnt FROM system_configs GROUP BY category ORDER BY category;
