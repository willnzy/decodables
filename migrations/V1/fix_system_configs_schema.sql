-- ==============================================================================
-- Fix system_configs Table Schema
-- 
-- 问题：数据库字段名和代码期望的字段名不匹配
-- 代码期望: key, value, value_type, config_group
-- 数据库有: config_key, config_value, category
-- ==============================================================================

-- 1. 先备份现有数据（如果有的话）
CREATE TABLE IF NOT EXISTS system_configs_backup AS 
SELECT * FROM system_configs;

-- 2. 删除旧表
DROP TABLE IF EXISTS system_configs CASCADE;

-- 3. 创建正确结构的新表（匹配代码期望）
CREATE TABLE system_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key TEXT NOT NULL UNIQUE,           -- 代码期望 'key' 不是 'config_key'
    value JSONB NOT NULL,               -- 代码期望 'value' 不是 'config_value'
    value_type TEXT DEFAULT 'json',     -- 代码期望这个字段: 'text', 'boolean', 'json', 'number'
    config_group TEXT DEFAULT 'general', -- 代码期望 'config_group' 不是 'category'
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by TEXT
);

-- 4. 创建索引
CREATE INDEX idx_system_configs_key ON system_configs(key);
CREATE INDEX idx_system_configs_group ON system_configs(config_group);
CREATE INDEX idx_system_configs_active ON system_configs(is_active);

-- 5. 启用 RLS
ALTER TABLE system_configs ENABLE ROW LEVEL SECURITY;

-- 6. 创建 RLS 策略 - Service role 完全访问
DROP POLICY IF EXISTS "Service role full access to system_configs" ON system_configs;
CREATE POLICY "Service role full access to system_configs" ON system_configs FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- 7. 插入初始配置数据
INSERT INTO system_configs (key, value, value_type, config_group, description) VALUES
-- ==========================================
-- Rate Limits - Payment (高风险，严格限制)
-- ==========================================
('rate_limit.payment.checkout', '{"limit": 5, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Checkout API rate limit'),
('rate_limit.payment.portal', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Billing portal rate limit'),

-- ==========================================
-- Rate Limits - Marketplace
-- ==========================================
('rate_limit.marketplace.purchase', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Marketplace purchase rate limit'),
('rate_limit.marketplace.publish', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Listing publish rate limit'),
('rate_limit.marketplace.list', '{"limit": 60, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Marketplace listing rate limit'),

-- ==========================================
-- Rate Limits - AI Generation (资源密集)
-- ==========================================
('rate_limit.generate.story', '{"limit": 20, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'AI story generation rate limit'),
('rate_limit.generate.images', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'AI image generation rate limit'),
('rate_limit.tools.ocr', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'OCR rate limit'),

-- ==========================================
-- Rate Limits - Export (资源密集)
-- ==========================================
('rate_limit.export.pdf', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'PDF export rate limit'),
('rate_limit.export.zip', '{"limit": 5, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'ZIP export rate limit'),
('rate_limit.export.preview', '{"limit": 20, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Preview generation rate limit'),

-- ==========================================
-- Rate Limits - User Operations
-- ==========================================
('rate_limit.projects.create', '{"limit": 20, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Project creation rate limit'),
('rate_limit.assets.upload', '{"limit": 20, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Asset upload rate limit'),

-- ==========================================
-- Rate Limits - Public Endpoints (防滥用)
-- ==========================================
('rate_limit.support.email', '{"limit": 3, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Support email rate limit'),
('rate_limit.contact.form', '{"limit": 3, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Contact form rate limit'),
('rate_limit.feedback.submit', '{"limit": 3, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Feedback submission rate limit'),

-- ==========================================
-- Rate Limits - Admin Operations
-- ==========================================
('rate_limit.admin.credits', '{"limit": 30, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin credit adjustment rate limit'),
('rate_limit.admin.tier', '{"limit": 30, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin tier update rate limit'),
('rate_limit.admin.refund', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin refund rate limit'),
('rate_limit.admin.subscription', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin subscription operations rate limit'),
('rate_limit.admin.broadcast', '{"limit": 5, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin broadcast rate limit'),
('rate_limit.admin.search', '{"limit": 60, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin search rate limit'),

-- ==========================================
-- Rate Limits - Analytics
-- ==========================================
('rate_limit.analytics.events', '{"limit": 60, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Analytics event ingestion rate limit'),

-- ==========================================
-- Rate Limits - Global
-- ==========================================
('rate_limit.global.default', '{"limit": 100, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Global default rate limit'),
('rate_limit.global.enabled', '{"enabled": true}', 'json', 'rate_limit', 'Enable/disable global rate limiting'),

-- ==========================================
-- Analytics Configuration
-- ==========================================
('analytics.enabled', '{"enabled": true}', 'json', 'analytics', 'Enable analytics tracking'),
('analytics.sampling_rate', '{"critical": 1.0, "important": 1.0, "normal": 0.3, "debug": 0.0}', 'json', 'analytics', 'Event sampling rates by level'),
('analytics.min_level', '{"level": "normal"}', 'json', 'analytics', 'Minimum tracking level'),

-- ==========================================
-- Feature Flags
-- ==========================================
('feature.marketplace.enabled', '{"enabled": true}', 'json', 'feature', 'Enable marketplace feature'),
('feature.ai_generation.enabled', '{"enabled": true}', 'json', 'feature', 'Enable AI generation feature'),
('feature.ocr.enabled', '{"enabled": true}', 'json', 'feature', 'Enable OCR feature'),
('feature.zip_export.enabled', '{"enabled": true}', 'json', 'feature', 'Enable ZIP export feature'),

-- ==========================================
-- UI Configuration
-- ==========================================
('ui.cta.primary', '{"text": "Start Creating", "subtitle": "No credit card required"}', 'json', 'ui', 'Primary CTA button text'),
('ui.announcement.enabled', '{"enabled": false, "text": "", "link": "", "dismissible": true}', 'json', 'ui', 'Announcement bar configuration'),

-- ==========================================
-- Limits Configuration
-- ==========================================
('limits.free.projects', '{"max": 3}', 'json', 'limits', 'Max projects for free tier'),
('limits.free.monthly_credits', '{"amount": 50}', 'json', 'limits', 'Monthly credits for free tier'),
('limits.starter.monthly_credits', '{"amount": 200}', 'json', 'limits', 'Monthly credits for starter tier'),
('limits.pro.monthly_credits', '{"amount": 500}', 'json', 'limits', 'Monthly credits for pro tier'),
('limits.marketplace.max_price', '{"credits": 500}', 'json', 'limits', 'Maximum listing price in credits')

ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value,
    value_type = EXCLUDED.value_type,
    config_group = EXCLUDED.config_group,
    description = EXCLUDED.description,
    updated_at = NOW();

-- 8. 清理备份表（可选，确认数据正确后再删除）
-- DROP TABLE IF EXISTS system_configs_backup;

-- 9. 验证
SELECT '✅ system_configs 表结构修复完成' as status;

SELECT 
    config_group,
    COUNT(*) as count
FROM system_configs
GROUP BY config_group
ORDER BY config_group;

SELECT '总配置数: ' || COUNT(*)::text as total FROM system_configs;
