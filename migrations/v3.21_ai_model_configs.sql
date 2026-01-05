-- ==========================================
-- v3.21: AI Model Configuration System
-- AI 模型配置管理系统
-- ==========================================

-- 1. AI 模型相关配置 (存入 system_configs)
INSERT INTO system_configs (key, value, value_type, config_group, description) VALUES

-- 提供商启用状态
('ai_providers.enabled', 
 '{"openai": true, "fal": true, "qwen": false, "gemini": false, "grok": false, "jimeng": false, "anthropic": false}', 
 'json', 'ai_providers', 'Enable/disable AI providers'),

-- 用户文本推理配置
('ai_model.user.text_reasoning', 
 '{"provider": "openai", "model": "gpt-4o-mini", "fallback": {"provider": "openai", "model": "gpt-4o-mini"}, "show_provider": false}', 
 'json', 'ai_models', 'User text reasoning model'),

-- 用户图像生成配置 (按等级区分)
('ai_model.user.image_generation', 
 '{"provider": "fal", "models": {"free": "flux-schnell", "starter": "flux-schnell", "pro": "flux-dev"}, "fallback": {"provider": "fal", "model": "flux-schnell"}, "show_provider": false}', 
 'json', 'ai_models', 'User image generation model by tier'),

-- Admin 分析配置
('ai_model.admin.analysis', 
 '{"provider": "openai", "model": "gpt-4o", "fallback": {"provider": "openai", "model": "gpt-4o-mini"}}', 
 'json', 'ai_models', 'Admin analysis model'),

-- 灰度发布配置
('ai_model.canary', 
 '{"enabled": false, "text_reasoning": {"canary_provider": "qwen", "canary_model": "qwen-plus", "traffic_percent": 10, "target_tiers": ["pro"]}, "image_generation": {"canary_provider": "jimeng", "canary_model": "jimeng-2.1", "traffic_percent": 5, "target_tiers": ["pro"]}}', 
 'json', 'ai_models', 'Canary release configuration'),

-- 各提供商可用模型列表
('ai_providers.models', 
 '{"openai": {"text": ["gpt-4o-mini", "gpt-4o", "o1-mini", "o1"], "image": ["dall-e-3"]}, "fal": {"image": ["flux-schnell", "flux-dev", "flux-pro"]}, "qwen": {"text": ["qwen-turbo", "qwen-plus", "qwen-max"], "image": ["wanx-v1"]}, "gemini": {"text": ["gemini-2.0-flash", "gemini-2.0-pro"], "image": ["imagen-3"]}, "grok": {"text": ["grok-2", "grok-2-vision"]}, "jimeng": {"image": ["jimeng-2.1", "jimeng-2.1-pro"]}, "anthropic": {"text": ["claude-3-5-sonnet-latest", "claude-3-5-haiku-latest"]}}', 
 'json', 'ai_providers', 'Available models per provider'),

-- 超时配置 (秒)
('ai_providers.timeouts', 
 '{"openai": {"text": 60, "image": 120}, "fal": {"image": 180}, "qwen": {"text": 60}, "gemini": {"text": 30}, "anthropic": {"text": 60}}', 
 'json', 'ai_providers', 'Timeout in seconds'),

-- 成本参考 (用于预算估算, USD)
('ai_providers.costs', 
 '{"openai": {"gpt-4o-mini": 0.15, "gpt-4o": 2.50, "o1-mini": 3.00, "o1": 15.00, "dall-e-3": 0.04}, "fal": {"flux-schnell": 0.003, "flux-dev": 0.025, "flux-pro": 0.05}, "qwen": {"qwen-plus": 0.004}, "anthropic": {"claude-3-5-sonnet-latest": 3.00}}', 
 'json', 'ai_providers', 'Cost per 1M tokens or per image (USD)')

ON CONFLICT (key) DO UPDATE SET 
  value = EXCLUDED.value, 
  updated_at = NOW();


-- 2. AI 使用量日汇总表
CREATE TABLE IF NOT EXISTS ai_usage_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    call_type TEXT NOT NULL,              -- 'text' | 'image'
    
    -- 调用统计
    total_calls INT DEFAULT 0,
    successful_calls INT DEFAULT 0,
    failed_calls INT DEFAULT 0,
    
    -- Token 统计 (文本模型)
    total_input_tokens BIGINT DEFAULT 0,
    total_output_tokens BIGINT DEFAULT 0,
    
    -- 图像统计
    total_images INT DEFAULT 0,
    
    -- 性能统计
    avg_latency_ms INT,
    
    -- 成本估算
    estimated_cost_usd DECIMAL(10, 4) DEFAULT 0,
    
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(date, provider, model, call_type)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_ai_usage_daily_date ON ai_usage_daily(date DESC);
CREATE INDEX IF NOT EXISTS idx_ai_usage_daily_provider ON ai_usage_daily(provider, date DESC);
CREATE INDEX IF NOT EXISTS idx_ai_usage_daily_model ON ai_usage_daily(model, date DESC);


-- 3. Upsert 函数 (用于增量更新日汇总)
CREATE OR REPLACE FUNCTION upsert_ai_usage_daily(
    p_date DATE,
    p_provider TEXT,
    p_model TEXT,
    p_call_type TEXT,
    p_success BOOLEAN,
    p_input_tokens BIGINT DEFAULT 0,
    p_output_tokens BIGINT DEFAULT 0,
    p_images INT DEFAULT 0,
    p_latency_ms INT DEFAULT 0,
    p_cost_usd DECIMAL DEFAULT 0
) RETURNS VOID AS $$
BEGIN
    INSERT INTO ai_usage_daily (
        date, provider, model, call_type,
        total_calls, successful_calls, failed_calls,
        total_input_tokens, total_output_tokens, total_images,
        avg_latency_ms, estimated_cost_usd
    ) VALUES (
        p_date, p_provider, p_model, p_call_type,
        1,
        CASE WHEN p_success THEN 1 ELSE 0 END,
        CASE WHEN p_success THEN 0 ELSE 1 END,
        p_input_tokens, p_output_tokens, p_images,
        p_latency_ms, p_cost_usd
    )
    ON CONFLICT (date, provider, model, call_type) DO UPDATE SET
        total_calls = ai_usage_daily.total_calls + 1,
        successful_calls = ai_usage_daily.successful_calls + CASE WHEN p_success THEN 1 ELSE 0 END,
        failed_calls = ai_usage_daily.failed_calls + CASE WHEN p_success THEN 0 ELSE 1 END,
        total_input_tokens = ai_usage_daily.total_input_tokens + p_input_tokens,
        total_output_tokens = ai_usage_daily.total_output_tokens + p_output_tokens,
        total_images = ai_usage_daily.total_images + p_images,
        avg_latency_ms = CASE 
            WHEN ai_usage_daily.total_calls = 0 THEN p_latency_ms
            ELSE (ai_usage_daily.avg_latency_ms * ai_usage_daily.total_calls + p_latency_ms) / (ai_usage_daily.total_calls + 1)
        END,
        estimated_cost_usd = ai_usage_daily.estimated_cost_usd + p_cost_usd,
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql;


-- 4. RLS 策略
ALTER TABLE ai_usage_daily ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Admin can read ai usage" ON ai_usage_daily;
CREATE POLICY "Admin can read ai usage" ON ai_usage_daily
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin')
    );

DROP POLICY IF EXISTS "System can write ai usage" ON ai_usage_daily;
CREATE POLICY "System can write ai usage" ON ai_usage_daily
    FOR ALL USING (true);


-- 5. 表注释
COMMENT ON TABLE ai_usage_daily IS 'Daily aggregated AI usage statistics for cost tracking and monitoring';
COMMENT ON COLUMN ai_usage_daily.call_type IS 'Type of AI call: text (chat/completion) or image (generation)';
COMMENT ON COLUMN ai_usage_daily.estimated_cost_usd IS 'Estimated cost based on ai_providers.costs config';
