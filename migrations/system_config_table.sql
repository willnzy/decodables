-- =============================================
-- System Configuration Table
-- 系统配置表 - 用于存储可动态调整的系统参数
-- =============================================

-- 创建系统配置表
CREATE TABLE IF NOT EXISTS system_config (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    config_key TEXT UNIQUE NOT NULL,           -- 配置键名
    config_value JSONB NOT NULL,               -- 配置值（JSON格式，支持复杂结构）
    category TEXT NOT NULL DEFAULT 'general',  -- 分类：rate_limit, analytics, system
    description TEXT,                          -- 配置说明
    is_active BOOLEAN DEFAULT true,            -- 是否启用
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by TEXT                            -- 最后修改的管理员ID
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_system_config_key ON system_config(config_key);
CREATE INDEX IF NOT EXISTS idx_system_config_category ON system_config(category);

-- 插入默认的限频配置
INSERT INTO system_config (config_key, config_value, category, description) VALUES
-- 支付相关 (高风险，严格限制)
('rate_limit.payment.checkout', '{"limit": 5, "window": "minute", "enabled": true}', 'rate_limit', '支付结账接口限频'),
('rate_limit.payment.portal', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', '账单门户接口限频'),
('rate_limit.marketplace.purchase', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', '市场购买接口限频'),

-- AI 生成相关 (资源密集)
('rate_limit.generate.story', '{"limit": 20, "window": "minute", "enabled": true}', 'rate_limit', 'AI故事生成限频'),
('rate_limit.generate.images', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', 'AI图片生成限频'),
('rate_limit.tools.ocr', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', 'OCR识别限频'),

-- 导出相关 (服务器资源消耗)
('rate_limit.export.pdf', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', 'PDF导出限频'),
('rate_limit.export.zip', '{"limit": 5, "window": "minute", "enabled": true}', 'rate_limit', 'ZIP导出限频'),
('rate_limit.export.preview', '{"limit": 20, "window": "minute", "enabled": true}', 'rate_limit', '预览图生成限频'),

-- 用户操作
('rate_limit.projects.create', '{"limit": 20, "window": "minute", "enabled": true}', 'rate_limit', '创建项目限频'),
('rate_limit.assets.upload', '{"limit": 20, "window": "minute", "enabled": true}', 'rate_limit', '素材上传限频'),
('rate_limit.marketplace.publish', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', '商品发布限频'),

-- 公开接口 (防滥用)
('rate_limit.support.email', '{"limit": 3, "window": "minute", "enabled": true}', 'rate_limit', '工单提交限频'),
('rate_limit.contact.form', '{"limit": 3, "window": "minute", "enabled": true}', 'rate_limit', '联系表单限频'),
('rate_limit.feedback.submit', '{"limit": 3, "window": "minute", "enabled": true}', 'rate_limit', '反馈提交限频'),

-- Admin 操作
('rate_limit.admin.credits', '{"limit": 30, "window": "minute", "enabled": true}', 'rate_limit', 'Admin积分调整限频'),
('rate_limit.admin.tier', '{"limit": 30, "window": "minute", "enabled": true}', 'rate_limit', 'Admin等级更新限频'),
('rate_limit.admin.refund', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', 'Admin退款限频'),
('rate_limit.admin.subscription', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', 'Admin订阅操作限频'),
('rate_limit.admin.broadcast', '{"limit": 5, "window": "minute", "enabled": true}', 'rate_limit', 'Admin群发限频'),

-- 查询接口
('rate_limit.admin.search', '{"limit": 60, "window": "minute", "enabled": true}', 'rate_limit', 'Admin搜索限频'),
('rate_limit.marketplace.list', '{"limit": 60, "window": "minute", "enabled": true}', 'rate_limit', '市场列表限频'),
('rate_limit.analytics.events', '{"limit": 60, "window": "minute", "enabled": true}', 'rate_limit', '事件上报限频'),

-- 全局默认配置
('rate_limit.global.default', '{"limit": 100, "window": "minute", "enabled": true}', 'rate_limit', '全局默认限频'),
('rate_limit.global.enabled', '{"enabled": true}', 'rate_limit', '是否启用全局限频'),

-- Analytics 配置
('analytics.enabled', '{"enabled": true}', 'analytics', '是否启用用户行为追踪'),
('analytics.sampling_rate', '{"critical": 1.0, "important": 1.0, "normal": 0.3, "debug": 0.0}', 'analytics', '事件采样率'),
('analytics.min_level', '{"level": "normal"}', 'analytics', '最低追踪级别')

ON CONFLICT (config_key) DO NOTHING;

-- 启用 RLS
ALTER TABLE system_config ENABLE ROW LEVEL SECURITY;

-- 只有 service_role 可以访问（后端通过 service key 访问）
CREATE POLICY "Service role full access to system_config"
ON system_config FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- 创建更新触发器
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

-- 创建获取配置的函数
CREATE OR REPLACE FUNCTION get_rate_limit_config(p_config_key TEXT)
RETURNS JSONB AS $$
DECLARE
    v_config JSONB;
BEGIN
    SELECT config_value INTO v_config
    FROM system_config
    WHERE config_key = p_config_key AND is_active = true;
    
    IF v_config IS NULL THEN
        -- 返回默认值
        SELECT config_value INTO v_config
        FROM system_config
        WHERE config_key = 'rate_limit.global.default' AND is_active = true;
    END IF;
    
    RETURN COALESCE(v_config, '{"limit": 100, "window": "minute", "enabled": true}'::JSONB);
END;
$$ LANGUAGE plpgsql;

