-- ==============================================================================
-- Fix system_configs Table - Final Version
-- 
-- 问题：代码中有两套不同的字段名
-- config_service.py 使用: config_key, config_value, category
-- db_service.py 使用: key, value, value_type, config_group
-- 
-- 解决方案：创建包含所有字段的表，同时支持两种访问方式
-- ==============================================================================

-- 1. 删除旧表和备份
DROP TABLE IF EXISTS system_configs_backup CASCADE;
DROP TABLE IF EXISTS system_configs CASCADE;

-- 2. 创建新表（包含所有需要的字段）
CREATE TABLE system_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 两套字段名都支持
    config_key TEXT NOT NULL UNIQUE,     -- config_service.py 使用
    key TEXT GENERATED ALWAYS AS (config_key) STORED,  -- db_service.py 使用 (自动同步)
    
    config_value JSONB NOT NULL,         -- config_service.py 使用
    value JSONB GENERATED ALWAYS AS (config_value) STORED,  -- db_service.py 使用 (自动同步)
    
    value_type TEXT DEFAULT 'json',      -- db_service.py 需要
    
    category TEXT DEFAULT 'general',     -- config_service.py 使用
    config_group TEXT GENERATED ALWAYS AS (category) STORED,  -- db_service.py 使用 (自动同步)
    
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by TEXT
);

-- 3. 创建索引
CREATE INDEX idx_system_configs_config_key ON system_configs(config_key);
CREATE INDEX idx_system_configs_category ON system_configs(category);
CREATE INDEX idx_system_configs_active ON system_configs(is_active);

-- 4. 启用 RLS
ALTER TABLE system_configs ENABLE ROW LEVEL SECURITY;

-- 5. 创建 RLS 策略
DROP POLICY IF EXISTS "Service role full access" ON system_configs;
CREATE POLICY "Service role full access" ON system_configs FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- 同时允许 authenticated 用户读取（前端可能需要）
DROP POLICY IF EXISTS "Authenticated read access" ON system_configs;
CREATE POLICY "Authenticated read access" ON system_configs FOR SELECT
    TO authenticated
    USING (is_active = true);

-- 6. 插入配置数据
INSERT INTO system_configs (config_key, config_value, value_type, category, description) VALUES
-- ==========================================
-- Rate Limits - Payment
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
-- Rate Limits - AI Generation
-- ==========================================
('rate_limit.generate.story', '{"limit": 20, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'AI story generation rate limit'),
('rate_limit.generate.images', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'AI image generation rate limit'),
('rate_limit.tools.ocr', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'OCR rate limit'),

-- ==========================================
-- Rate Limits - Export
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
-- Rate Limits - Public Endpoints
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
-- Rate Limits - Analytics & Global
-- ==========================================
('rate_limit.analytics.events', '{"limit": 60, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Analytics event ingestion rate limit'),
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
('limits.marketplace.max_price', '{"credits": 500}', 'json', 'limits', 'Maximum listing price in credits');

-- 7. 验证
SELECT '✅ system_configs 修复完成' as status;

SELECT 
    category as group_name,
    COUNT(*) as count
FROM system_configs
GROUP BY category
ORDER BY category;

SELECT 'Total configs: ' || COUNT(*)::text as info FROM system_configs;

-- 显示前5条数据验证字段
SELECT 
    config_key,
    key,
    category,
    config_group,
    value_type,
    is_active
FROM system_configs 
LIMIT 5;
