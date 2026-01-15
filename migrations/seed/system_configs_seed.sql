-- ============================================================================
-- SYSTEM CONFIGS SEED FILE
-- ============================================================================
-- Contains: All system configuration data
-- Extracted from: migrations/v2/03_infrastructure.sql
--
-- Config Groups (68 total records):
--   - rate_limit: API rate limiting (24 records)
--   - analytics: Analytics settings (3 records)
--   - feature_flag: Feature toggles (4 records)
--   - limits: System limits (5 records)
--   - credits: Credit costs (9 records)
--   - pricing: Pricing display (8 records)
--   - ai_providers: AI provider settings (8 records)
--   - ui: UI text (3 records)
--   - marketing: Marketing text (2 records)
--   - tooltip: Tooltip text (2 records)
--   - marketplace: Marketplace settings (3 records)
--   - tier: Tier display names (6 records)
--   - trial: Trial period (1 record)
--   - database: Database settings (1 record)
--
-- Usage:
--   psql $DATABASE_URL -f migrations/seed/system_configs_seed.sql
--
-- Note: Uses ON CONFLICT DO UPDATE to make script idempotent
-- ============================================================================

BEGIN;

INSERT INTO system_configs (key, value, value_type, config_group, description, is_active, is_editable) VALUES

-- ============================================================================
-- RATE LIMITS (24 records)
-- ============================================================================
('rate_limit.payment.checkout', '{"limit": 5, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Checkout API limit', true, true),
('rate_limit.payment.portal', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Billing portal limit', true, true),
('rate_limit.marketplace.purchase', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Marketplace purchase limit', true, true),
('rate_limit.generate.story', '{"limit": 20, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'AI story generation limit', true, true),
('rate_limit.generate.images', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'AI image generation limit', true, true),
('rate_limit.tools.ocr', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'OCR limit', true, true),
('rate_limit.export.pdf', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'PDF export limit', true, true),
('rate_limit.export.zip', '{"limit": 5, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'ZIP export limit', true, true),
('rate_limit.export.preview', '{"limit": 20, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Preview generation limit', true, true),
('rate_limit.projects.create', '{"limit": 20, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Project creation limit', true, true),
('rate_limit.assets.upload', '{"limit": 20, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Asset upload limit', true, true),
('rate_limit.marketplace.publish', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Listing publish limit', true, true),
('rate_limit.support.email', '{"limit": 3, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Support ticket limit', true, true),
('rate_limit.contact.form', '{"limit": 3, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Contact form limit', true, true),
('rate_limit.feedback.submit', '{"limit": 3, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Feedback submission limit', true, true),
('rate_limit.admin.credits', '{"limit": 30, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin credit adjustment limit', true, true),
('rate_limit.admin.tier', '{"limit": 30, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin tier update limit', true, true),
('rate_limit.admin.refund', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin refund limit', true, true),
('rate_limit.admin.subscription', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin subscription ops limit', true, true),
('rate_limit.admin.broadcast', '{"limit": 5, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin broadcast limit', true, true),
('rate_limit.admin.search', '{"limit": 60, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin search limit', true, true),
('rate_limit.marketplace.list', '{"limit": 60, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Marketplace listing limit', true, true),
('rate_limit.analytics.events', '{"limit": 60, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Analytics event ingestion limit', true, true),
('rate_limit.global.default', '{"limit": 100, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Global default limit', true, true),

-- ============================================================================
-- ANALYTICS (3 records)
-- ============================================================================
('analytics.enabled', '{"enabled": true}', 'json', 'analytics', 'Enable analytics tracking', true, true),
('analytics.sampling_rate', '{"critical": 1.0, "important": 1.0, "normal": 0.3, "debug": 0.0}', 'json', 'analytics', 'Event sampling rates', true, true),
('analytics.min_level', '{"level": "normal"}', 'json', 'analytics', 'Minimum tracking level', true, true),

-- ============================================================================
-- FEATURE FLAGS (4 records)
-- ============================================================================
('FEATURE_AI_GENERATION', 'true', 'boolean', 'feature_flag', 'Enable AI image generation', true, true),
('FEATURE_MARKETPLACE', 'true', 'boolean', 'feature_flag', 'Enable marketplace', true, true),
('FEATURE_OCR', 'true', 'boolean', 'feature_flag', 'Enable OCR/Smart Scan', true, true),
('FEATURE_ZIP_EXPORT', 'true', 'boolean', 'feature_flag', 'Enable ZIP export', true, true),

-- ============================================================================
-- LIMITS (5 records)
-- ============================================================================
('FREE_PROJECT_LIMIT', '1', 'number', 'limits', 'Max projects for free tier', true, true),
('STARTER_PROJECT_LIMIT', '20', 'number', 'limits', 'Max projects for starter tier', true, true),
('PRO_PROJECT_LIMIT', '200', 'number', 'limits', 'Max projects for pro tier', true, true),
('MAX_UPLOAD_FILE_SIZE_MB', '5', 'number', 'limits', 'Max file upload size in MB', true, true),
('MAX_LISTING_PRICE', '500', 'number', 'limits', 'Max marketplace listing price', true, true),

-- ============================================================================
-- CREDITS (9 records)
-- ============================================================================
('CREDITS_PER_IMAGE', '5', 'number', 'credits', 'Credits per AI image', true, true),
('CREDITS_PER_OCR', '5', 'number', 'credits', 'Credits per OCR', true, true),
('CREDITS_PER_AI_DESIGN_PAGE', '5', 'number', 'credits', 'Credits per AI design page', true, true),
('SIGNUP_BONUS_CREDITS', '50', 'number', 'credits', 'Signup bonus credits', true, true),
('credits.cost.image_generation', '5', 'integer', 'credits', 'AI image generation cost per image', true, true),
('credits.cost.image_generation_reference', '7', 'integer', 'credits', 'AI image generation with reference cost', true, true),
('credits.cost.text_generation', '0', 'integer', 'credits', 'AI text generation cost (free)', true, true),
('credits.cost.smart_scan', '10', 'integer', 'credits', 'Smart Scan/OCR cost', true, true),
('credits.cost.ocr', '10', 'integer', 'credits', 'OCR recognition cost', true, true),

-- ============================================================================
-- PRICING (8 records)
-- ============================================================================
('T2_PLAN_PRICE', '14.9', 'number', 'pricing', 't2 monthly price', true, true),
('T2_PLAN_ORIGINAL_PRICE', '24.95', 'number', 'pricing', 't2 original price (for display)', true, true),
('T2_MONTHLY_CREDITS', '100', 'number', 'pricing', 't2 monthly credits (sync with tier.t2.monthly_credits)', true, true),
('T3_PLAN_PRICE', '29.9', 'number', 'pricing', 't3 monthly price', true, true),
('T3_PLAN_ORIGINAL_PRICE', '59.9', 'number', 'pricing', 't3 original price (for display)', true, true),
('T3_MONTHLY_CREDITS', '200', 'number', 'pricing', 't3 monthly credits (sync with tier.t3.monthly_credits)', true, true),
('T3_CREDITS_DISCOUNT_PERCENT', '20', 'number', 'pricing', 't3 discount on credit purchases', true, true),
('CREDITS_TIERS', '[{"id":"credits_100","credits":100,"originalPrice":2.99,"currentPrice":2.99,"discount":null,"proDiscount":20},{"id":"credits_500","credits":500,"originalPrice":14.99,"currentPrice":13.49,"discount":10,"proDiscount":20,"popular":true},{"id":"credits_2000","credits":2000,"originalPrice":60.0,"currentPrice":48.0,"discount":20,"proDiscount":20}]', 'json', 'pricing', 'Credits purchase tiers', true, true),

-- ============================================================================
-- AI PROVIDERS (8 records)
-- ============================================================================
('ai_providers.enabled', '{"openai": true, "fal": true, "qwen": false, "wanx": false, "gemini": false, "grok": false, "jimeng": false, "anthropic": false}', 'json', 'ai_providers', 'Enable/disable AI providers', true, true),
('ai_model.user.text_reasoning', '{"provider": "openai", "model": "gpt-4o-mini", "fallback": {"provider": "openai", "model": "gpt-4o-mini"}, "show_provider": false}', 'json', 'ai_models', 'User text reasoning model', true, true),
('ai_model.user.image_generation', '{"provider": "fal", "models": {"t1": "flux-schnell", "t2": "flux-schnell", "t3": "flux-dev"}, "fallback": {"provider": "fal", "model": "flux-schnell"}, "show_provider": false}', 'json', 'ai_models', 'User image generation model by tier', true, true),
('ai_model.admin.analysis', '{"provider": "openai", "model": "gpt-4o", "fallback": {"provider": "openai", "model": "gpt-4o-mini"}}', 'json', 'ai_models', 'Admin analysis model', true, true),
('ai_model.canary', '{"enabled": false, "text_reasoning": {"canary_provider": "qwen", "canary_model": "qwen-plus", "traffic_percent": 10}, "image_generation": {"canary_provider": "jimeng", "canary_model": "jimeng-2.1", "traffic_percent": 5}}', 'json', 'ai_models', 'Canary release for A/B testing', true, true),
('ai_providers.models', '{"openai": {"text": ["gpt-4o-mini", "gpt-4o", "o1-mini", "o1"], "image": ["dall-e-3"]}, "fal": {"image": ["flux-schnell", "flux-dev", "flux-pro"]}, "qwen": {"text": ["qwen-turbo", "qwen-plus", "qwen-max"]}}', 'json', 'ai_providers', 'Available models per provider', true, true),
('ai_providers.timeouts', '{"openai": {"text": 60, "image": 120}, "fal": {"image": 180}, "qwen": {"text": 60}}', 'json', 'ai_providers', 'Timeout config in seconds', true, true),
('ai_providers.costs', '{"openai": {"gpt-4o-mini": 0.15, "gpt-4o": 2.50, "o1-mini": 3.00, "o1": 15.00, "dall-e-3": 0.04}, "fal": {"flux-schnell": 0.003, "flux-dev": 0.025, "flux-pro": 0.05}, "qwen": {"qwen-turbo": 0.001, "qwen-plus": 0.004, "qwen-max": 0.02}}', 'json', 'ai_providers', 'Cost per 1M tokens/image (USD)', true, true),
('ai_providers.retry', '{"max_retries": 3, "base_delay_ms": 1000, "max_delay_ms": 10000, "retry_on_status": [429, 500, 502, 503, 504]}', 'json', 'ai_providers', 'Retry configuration', true, true),

-- ============================================================================
-- UI TEXT (3 records)
-- ============================================================================
('UI_UPGRADE_CTA', 'Upgrade Now', 'text', 'ui', 'Upgrade button text', true, true),
('UI_TRIAL_EXPIRED', 'Your 7-day trial period has expired. This project is read-only.', 'text', 'ui', 'Trial expired message', true, true),
('UI_AI_TYPING_INDICATOR', 'AI is thinking...', 'text', 'ui', 'AI typing indicator text', true, true),

-- ============================================================================
-- MARKETING (2 records)
-- ============================================================================
('HOME_HERO_TITLE', 'Create Beautiful 8-Page Zines in Minutes', 'text', 'marketing', 'Homepage hero title', true, true),
('HOME_HERO_SUBTITLE', 'AI-powered story generation meets easy drag-and-drop editing.', 'text', 'marketing', 'Homepage hero subtitle', true, true),

-- ============================================================================
-- TOOLTIP (2 records)
-- ============================================================================
('TOOLTIP_DELETE', 'Delete', 'text', 'tooltip', 'Delete button tooltip when enabled', true, true),
('TOOLTIP_DELETE_DISABLED', 'Unpublish first to delete', 'text', 'tooltip', 'Delete button tooltip when disabled', true, true),

-- ============================================================================
-- MARKETPLACE (3 records)
-- ============================================================================
('marketplace.seller_revenue_ratio', '0.70', 'number', 'marketplace', 'Seller revenue share (70%)', true, true),
('marketplace.platform_fee_ratio', '0.30', 'number', 'marketplace', 'Platform fee (30%)', true, true),
('marketplace.trial_duration_days', '7', 'number', 'marketplace', 'Trial duration in days', true, true),

-- ============================================================================
-- TIER SYSTEM (6 records)
-- ============================================================================
('tier.t1.display_name', 'Free Plan', 'text', 'tier', 'First Tier 显示名称 (可通过 Admin API 修改)', true, true),
('tier.t2.display_name', 'Starter Plan', 'text', 'tier', 'Second Tier 显示名称 (可通过 Admin API 修改)', true, true),
('tier.t3.display_name', 'Pro Plan', 'text', 'tier', 'Third Tier 显示名称 (可通过 Admin API 修改)', true, true),
('tier.t1.monthly_credits', '0', 'integer', 'tier', 'First Tier 月度积分', true, false),
('tier.t2.monthly_credits', '100', 'integer', 'tier', 'Second Tier 月度积分', true, false),
('tier.t3.monthly_credits', '200', 'integer', 'tier', 'Third Tier 月度积分', true, false),

-- ============================================================================
-- TRIAL PERIOD (1 record)
-- ============================================================================
('trial.duration_days', '30', 'integer', 'trial', 'Free tier 试用期天数 (可通过 Admin API 修改)', true, true),

-- ============================================================================
-- DATABASE SETTINGS (1 record)
-- ============================================================================
('soft_delete.recovery_period_days', '30', 'integer', 'database', '软删除恢复期天数,过期后用户无法在删除历史中看到记录', true, true)

ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value,
    value_type = EXCLUDED.value_type,
    config_group = EXCLUDED.config_group,
    description = EXCLUDED.description,
    is_active = EXCLUDED.is_active,
    is_editable = EXCLUDED.is_editable,
    updated_at = CURRENT_TIMESTAMP;

COMMIT;


-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Count configs by group
-- SELECT config_group, COUNT(*) as count
-- FROM system_configs
-- WHERE is_active = true
-- GROUP BY config_group
-- ORDER BY count DESC;

-- Expected results:
-- | config_group  | count |
-- |---------------|-------|
-- | rate_limit    | 24    |
-- | credits       | 9     |
-- | pricing       | 8     |
-- | ai_providers  | 5     |
-- | ai_models     | 4     |
-- | limits        | 5     |
-- | feature_flag  | 4     |
-- | tier          | 6     |
-- | analytics     | 3     |
-- | ui            | 3     |
-- | marketplace   | 3     |
-- | marketing     | 2     |
-- | tooltip       | 2     |
-- | trial         | 1     |
-- | database      | 1     |
-- Total: 68 records


-- ============================================================================
-- END OF SYSTEM CONFIGS SEED DATA
-- ============================================================================
