-- ==========================================
-- v3.21: AI Model Configuration System
-- AI 模型配置管理系统
-- ==========================================
-- 
-- Features:
-- 1. 多 AI 提供商支持 (OpenAI, FAL, Qwen, Gemini, Grok, Jimeng, Anthropic)
-- 2. 用户文本/图像模型配置
-- 3. Admin 分析模型配置
-- 4. 灰度发布 (Canary Release) 支持
-- 5. 使用量按天汇总
-- 6. 成本追踪
--
-- Dependencies: system_configs table (v3.10)
-- ==========================================

-- ==========================================
-- 1. AI 模型相关配置 (写入 system_configs)
-- ==========================================

INSERT INTO system_configs (key, value, value_type, config_group, description, is_active) VALUES

-- 提供商启用状态
-- 注意: qwen (千问-文本) 和 wanx (万相-图像) 是两个独立的 provider
('ai_providers.enabled', 
 '{"openai": true, "fal": true, "qwen": false, "wanx": false, "gemini": false, "grok": false, "jimeng": false, "anthropic": false}', 
 'json', 'ai_providers', 'Enable/disable AI providers', true),

-- 用户文本推理配置
('ai_model.user.text_reasoning', 
 '{"provider": "openai", "model": "gpt-4o-mini", "fallback": {"provider": "openai", "model": "gpt-4o-mini"}, "show_provider": false}', 
 'json', 'ai_models', 'User text reasoning model configuration', true),

-- 用户图像生成配置 (按等级区分)
('ai_model.user.image_generation', 
 '{"provider": "fal", "models": {"free": "flux-schnell", "starter": "flux-schnell", "pro": "flux-dev"}, "fallback": {"provider": "fal", "model": "flux-schnell"}, "show_provider": false}', 
 'json', 'ai_models', 'User image generation model by tier', true),

-- Admin 分析配置
('ai_model.admin.analysis', 
 '{"provider": "openai", "model": "gpt-4o", "fallback": {"provider": "openai", "model": "gpt-4o-mini"}}', 
 'json', 'ai_models', 'Admin analysis model configuration', true),

-- 灰度发布配置
('ai_model.canary', 
 '{"enabled": false, "text_reasoning": {"canary_provider": "qwen", "canary_model": "qwen-plus", "traffic_percent": 10, "target_tiers": ["pro"]}, "image_generation": {"canary_provider": "jimeng", "canary_model": "jimeng-2.1", "traffic_percent": 5, "target_tiers": ["pro"]}}', 
 'json', 'ai_models', 'Canary release configuration for A/B testing new models', true),

-- 各提供商可用模型列表
-- 注意: qwen (千问) 只有文本模型, wanx (万相) 只有图像模型
('ai_providers.models', 
 '{"openai": {"text": ["gpt-4o-mini", "gpt-4o", "o1-mini", "o1"], "image": ["dall-e-3"]}, "fal": {"image": ["flux-schnell", "flux-dev", "flux-pro"]}, "qwen": {"text": ["qwen-turbo", "qwen-plus", "qwen-max"]}, "wanx": {"image": ["wan2.6-t2i", "wan2.6-image", "wanx-v1"]}, "gemini": {"text": ["gemini-2.0-flash", "gemini-2.0-pro"], "image": ["imagen-3"]}, "grok": {"text": ["grok-2", "grok-2-vision"]}, "jimeng": {"image": ["jimeng-2.1", "jimeng-2.1-pro"]}, "anthropic": {"text": ["claude-3.5-sonnet", "claude-3.5-opus"]}}', 
 'json', 'ai_providers', 'Available models per provider', true),

-- 超时配置 (秒)
('ai_providers.timeouts', 
 '{"openai": {"text": 60, "image": 120}, "fal": {"image": 180}, "qwen": {"text": 60}, "wanx": {"image": 180}, "gemini": {"text": 30}, "anthropic": {"text": 90}}', 
 'json', 'ai_providers', 'Timeout configuration in seconds', true),

-- 成本参考 (用于预算估算, USD per 1M tokens or per image)
-- 千问按 token 计费，万相按图片计费
('ai_providers.costs', 
 '{"openai": {"gpt-4o-mini": 0.15, "gpt-4o": 2.50, "o1-mini": 3.00, "o1": 15.00, "dall-e-3": 0.04}, "fal": {"flux-schnell": 0.003, "flux-dev": 0.025, "flux-pro": 0.05}, "qwen": {"qwen-turbo": 0.001, "qwen-plus": 0.004, "qwen-max": 0.02}, "wanx": {"wan2.6-t2i": 0.02, "wan2.6-image": 0.03, "wanx-v1": 0.015}, "anthropic": {"claude-3.5-sonnet": 3.00, "claude-3.5-opus": 15.00}}', 
 'json', 'ai_providers', 'Cost reference per 1M tokens or per image (USD)', true),

-- 重试配置
('ai_providers.retry', 
 '{"max_retries": 3, "base_delay_ms": 1000, "max_delay_ms": 10000, "retry_on_status": [429, 500, 502, 503, 504]}', 
 'json', 'ai_providers', 'Retry configuration for AI API calls', true)

ON CONFLICT (key) DO UPDATE SET 
    value = EXCLUDED.value, 
    description = EXCLUDED.description,
    updated_at = NOW();


-- ==========================================
-- 2. AI 使用量日汇总表
-- ==========================================

CREATE TABLE IF NOT EXISTS ai_usage_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 时间维度
    date DATE NOT NULL,
    
    -- AI 调用维度
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
    avg_latency_ms INT DEFAULT 0,
    min_latency_ms INT,
    max_latency_ms INT,
    
    -- 成本统计
    estimated_cost_usd DECIMAL(10, 4) DEFAULT 0,
    
    -- 错误统计
    error_counts JSONB DEFAULT '{}',      -- {"rate_limit": 5, "timeout": 2, ...}
    
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 唯一约束
    UNIQUE(date, provider, model, call_type)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_ai_usage_daily_date ON ai_usage_daily(date DESC);
CREATE INDEX IF NOT EXISTS idx_ai_usage_daily_provider ON ai_usage_daily(provider, date DESC);
CREATE INDEX IF NOT EXISTS idx_ai_usage_daily_model ON ai_usage_daily(model, date DESC);
CREATE INDEX IF NOT EXISTS idx_ai_usage_daily_call_type ON ai_usage_daily(call_type, date DESC);

-- 注释
COMMENT ON TABLE ai_usage_daily IS 'Daily aggregated AI usage statistics for cost tracking and monitoring';
COMMENT ON COLUMN ai_usage_daily.call_type IS 'Type of AI call: text (chat/completion) or image (generation)';
COMMENT ON COLUMN ai_usage_daily.error_counts IS 'JSON object with error type counts: {"rate_limit": N, "timeout": N, ...}';


-- ==========================================
-- 3. Upsert 函数 (用于更新日汇总)
-- ==========================================

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
    p_cost_usd DECIMAL DEFAULT 0,
    p_error_type TEXT DEFAULT NULL
) RETURNS VOID AS $$
DECLARE
    v_error_counts JSONB;
BEGIN
    -- 构建错误计数 JSON
    IF p_error_type IS NOT NULL THEN
        v_error_counts := jsonb_build_object(p_error_type, 1);
    ELSE
        v_error_counts := '{}'::jsonb;
    END IF;

    INSERT INTO ai_usage_daily (
        date, provider, model, call_type,
        total_calls, successful_calls, failed_calls,
        total_input_tokens, total_output_tokens, total_images,
        avg_latency_ms, min_latency_ms, max_latency_ms,
        estimated_cost_usd, error_counts
    ) VALUES (
        p_date, p_provider, p_model, p_call_type,
        1,
        CASE WHEN p_success THEN 1 ELSE 0 END,
        CASE WHEN p_success THEN 0 ELSE 1 END,
        p_input_tokens, p_output_tokens, p_images,
        p_latency_ms, p_latency_ms, p_latency_ms,
        p_cost_usd, v_error_counts
    )
    ON CONFLICT (date, provider, model, call_type) DO UPDATE SET
        total_calls = ai_usage_daily.total_calls + 1,
        successful_calls = ai_usage_daily.successful_calls + CASE WHEN p_success THEN 1 ELSE 0 END,
        failed_calls = ai_usage_daily.failed_calls + CASE WHEN p_success THEN 0 ELSE 1 END,
        total_input_tokens = ai_usage_daily.total_input_tokens + p_input_tokens,
        total_output_tokens = ai_usage_daily.total_output_tokens + p_output_tokens,
        total_images = ai_usage_daily.total_images + p_images,
        -- 更新平均延迟 (增量平均算法)
        avg_latency_ms = CASE 
            WHEN ai_usage_daily.total_calls = 0 THEN p_latency_ms
            ELSE ((ai_usage_daily.avg_latency_ms * ai_usage_daily.total_calls) + p_latency_ms) / (ai_usage_daily.total_calls + 1)
        END,
        min_latency_ms = LEAST(COALESCE(ai_usage_daily.min_latency_ms, p_latency_ms), p_latency_ms),
        max_latency_ms = GREATEST(COALESCE(ai_usage_daily.max_latency_ms, p_latency_ms), p_latency_ms),
        estimated_cost_usd = ai_usage_daily.estimated_cost_usd + p_cost_usd,
        -- 合并错误计数
        error_counts = CASE 
            WHEN p_error_type IS NOT NULL THEN
                ai_usage_daily.error_counts || jsonb_build_object(
                    p_error_type, 
                    COALESCE((ai_usage_daily.error_counts->>p_error_type)::int, 0) + 1
                )
            ELSE ai_usage_daily.error_counts
        END,
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION upsert_ai_usage_daily IS 'Upsert AI usage statistics into daily aggregation table';


-- ==========================================
-- 4. RLS 策略
-- ==========================================

ALTER TABLE ai_usage_daily ENABLE ROW LEVEL SECURITY;

-- Admin 可以读取
DROP POLICY IF EXISTS "Admin can read ai usage" ON ai_usage_daily;
CREATE POLICY "Admin can read ai usage" ON ai_usage_daily
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid()::text AND role = 'admin')
    );

-- 系统可以写入 (service role)
DROP POLICY IF EXISTS "System can write ai usage" ON ai_usage_daily;
CREATE POLICY "System can write ai usage" ON ai_usage_daily
    FOR ALL USING (true);


-- ==========================================
-- 5. 查询辅助视图
-- ==========================================

-- 最近 30 天使用量汇总视图
CREATE OR REPLACE VIEW v_ai_usage_last_30_days AS
SELECT 
    provider,
    model,
    call_type,
    SUM(total_calls) as total_calls,
    SUM(successful_calls) as successful_calls,
    SUM(failed_calls) as failed_calls,
    ROUND(SUM(successful_calls)::numeric / NULLIF(SUM(total_calls), 0) * 100, 2) as success_rate,
    SUM(total_input_tokens) as total_input_tokens,
    SUM(total_output_tokens) as total_output_tokens,
    SUM(total_images) as total_images,
    ROUND(AVG(avg_latency_ms)) as avg_latency_ms,
    SUM(estimated_cost_usd) as total_cost_usd
FROM ai_usage_daily
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY provider, model, call_type
ORDER BY total_cost_usd DESC;

COMMENT ON VIEW v_ai_usage_last_30_days IS 'Aggregated AI usage statistics for the last 30 days';


-- 每日成本趋势视图
CREATE OR REPLACE VIEW v_ai_daily_cost_trend AS
SELECT 
    date,
    SUM(estimated_cost_usd) as daily_cost_usd,
    SUM(total_calls) as daily_calls,
    jsonb_object_agg(provider, provider_cost) as cost_by_provider
FROM (
    SELECT 
        date,
        provider,
        SUM(estimated_cost_usd) as provider_cost,
        SUM(total_calls) as total_calls,
        SUM(estimated_cost_usd) as estimated_cost_usd
    FROM ai_usage_daily
    WHERE date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY date, provider
) sub
GROUP BY date
ORDER BY date DESC;

COMMENT ON VIEW v_ai_daily_cost_trend IS 'Daily AI cost trend for the last 30 days';


-- ==========================================
-- 6. 清理函数 (可选，用于数据保留策略)
-- ==========================================

CREATE OR REPLACE FUNCTION cleanup_old_ai_usage(retention_days INT DEFAULT 90)
RETURNS INT AS $$
DECLARE
    deleted_count INT;
BEGIN
    DELETE FROM ai_usage_daily
    WHERE date < CURRENT_DATE - (retention_days || ' days')::INTERVAL;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_old_ai_usage IS 'Clean up AI usage data older than specified retention days';
