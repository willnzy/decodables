-- ============================================================================
-- PLATFORM CONFIGURATION SEED FILE
-- ============================================================================
-- Contains: Pricing plans + System configurations + Tag presets
-- Merged from: pricing_plans_seed.sql + system_configs_seed.sql
--
-- Tables seeded:
--   - pricing_plans (6 records: 3 subscriptions + 3 credit packs)
--   - system_configs (84 records across 16 config groups)
--   - tag_group_presets (4 records) - v3.33 新增
--
-- Usage:
--   psql $DATABASE_URL -f migrations/seed/platform_config_seed.sql
--
-- Note: Uses ON CONFLICT DO UPDATE to make script idempotent
--
-- v3.33 更新:
--   - 新增 trial.default_days, trial.urgent_threshold_days 配置
--   - 新增 tag.* 配置项 (4个)
--   - 新增 tag_group_presets 预设数据 (4个标签分组)
-- ============================================================================

BEGIN;

-- ============================================================================
-- PART 1: PRICING PLANS (6 records)
-- ============================================================================

-- ============================================================================
-- SUBSCRIPTION PLANS (3 records)
-- ============================================================================

-- T1: Free Plan
INSERT INTO pricing_plans (
    plan_code, plan_type, plan_name, description,
    price_cents, original_price_cents, currency,
    billing_interval, tier, monthly_credits,
    stripe_price_id_prod, stripe_price_id_dev,
    stripe_product_id,
    is_active, is_visible, is_featured, sort_order,
    version, effective_from,
    metadata, created_by
) VALUES (
    'tier_t1_monthly',
    'subscription',
    'Free Plan',
    '免费方案，注册即可使用基础功能',
    0,
    NULL,
    'USD',
    'month',
    't1',
    0,
    NULL,
    NULL,
    NULL,
    TRUE,
    TRUE,
    FALSE,
    0,
    1,
    NOW(),
    '{"badge": "FREE"}'::jsonb,
    'system'
) ON CONFLICT (plan_code) DO UPDATE SET
    price_cents = EXCLUDED.price_cents,
    updated_at = NOW();

-- T2: Starter Plan
INSERT INTO pricing_plans (
    plan_code, plan_type, plan_name, description,
    price_cents, original_price_cents, currency,
    billing_interval, tier, monthly_credits,
    stripe_price_id_prod, stripe_price_id_dev,
    stripe_product_id,
    is_active, is_visible, is_featured, sort_order,
    version, effective_from,
    metadata, created_by
) VALUES (
    'tier_t2_monthly',
    'subscription',
    'Starter Plan',
    '适合个人创作者，包含贴纸库和发布权限',
    990,
    1490,
    'USD',
    'month',
    't2',
    200,
    '{{ STRIPE_PRICE_SUB_STARTER_PROD }}',
    '{{ STRIPE_PRICE_SUB_STARTER_DEV }}',
    '{{ STRIPE_PRODUCT_STARTER }}',
    TRUE,
    TRUE,
    FALSE,
    1,
    1,
    NOW(),
    '{"discount_percent": 34, "badge": null}'::jsonb,
    'system'
) ON CONFLICT (plan_code) DO UPDATE SET
    price_cents = EXCLUDED.price_cents,
    original_price_cents = EXCLUDED.original_price_cents,
    updated_at = NOW();

-- T3: Pro Plan
INSERT INTO pricing_plans (
    plan_code, plan_type, plan_name, description,
    price_cents, original_price_cents, currency,
    billing_interval, tier, monthly_credits,
    stripe_price_id_prod, stripe_price_id_dev,
    stripe_product_id,
    is_active, is_visible, is_featured, sort_order,
    version, effective_from,
    metadata, created_by
) VALUES (
    'tier_t3_monthly',
    'subscription',
    'Pro Plan',
    '专业创作者首选，包含全功能和商业授权',
    1990,
    2990,
    'USD',
    'month',
    't3',
    500,
    '{{ STRIPE_PRICE_SUB_PRO_PROD }}',
    '{{ STRIPE_PRICE_SUB_PRO_DEV }}',
    '{{ STRIPE_PRODUCT_PRO }}',
    TRUE,
    TRUE,
    TRUE,
    2,
    1,
    NOW(),
    '{"discount_percent": 34, "badge": "RECOMMENDED"}'::jsonb,
    'system'
) ON CONFLICT (plan_code) DO UPDATE SET
    price_cents = EXCLUDED.price_cents,
    original_price_cents = EXCLUDED.original_price_cents,
    updated_at = NOW();


-- ============================================================================
-- CREDIT PACKAGES (3 records)
-- ============================================================================

-- 100 Credits Pack
INSERT INTO pricing_plans (
    plan_code, plan_type, plan_name, description,
    price_cents, original_price_cents, currency,
    credits_amount,
    stripe_price_id_prod, stripe_price_id_dev,
    stripe_product_id,
    is_active, is_visible, is_featured, sort_order,
    version, effective_from,
    metadata, created_by
) VALUES (
    'credits_100',
    'credits',
    '100 Credits Pack',
    '适合偶尔使用 AI 功能的用户',
    299,
    NULL,
    'USD',
    100,
    '{{ STRIPE_PRICE_CREDITS_100_PROD }}',
    '{{ STRIPE_PRICE_CREDITS_100_DEV }}',
    '{{ STRIPE_PRODUCT_CREDITS }}',
    TRUE,
    TRUE,
    FALSE,
    10,
    1,
    NOW(),
    '{"unit_price_cents": 2.99, "badge": null}'::jsonb,
    'system'
) ON CONFLICT (plan_code) DO UPDATE SET
    price_cents = EXCLUDED.price_cents,
    updated_at = NOW();

-- 500 Credits Pack (Popular)
INSERT INTO pricing_plans (
    plan_code, plan_type, plan_name, description,
    price_cents, original_price_cents, currency,
    credits_amount,
    stripe_price_id_prod, stripe_price_id_dev,
    stripe_product_id,
    is_active, is_visible, is_featured, sort_order,
    version, effective_from,
    metadata, created_by
) VALUES (
    'credits_500',
    'credits',
    '500 Credits Pack',
    '适合经常使用 AI 功能的创作者',
    1349,
    1499,
    'USD',
    500,
    '{{ STRIPE_PRICE_CREDITS_500_PROD }}',
    '{{ STRIPE_PRICE_CREDITS_500_DEV }}',
    '{{ STRIPE_PRODUCT_CREDITS }}',
    TRUE,
    TRUE,
    TRUE,
    11,
    1,
    NOW(),
    '{"discount_percent": 10, "unit_price_cents": 2.698, "badge": "POPULAR"}'::jsonb,
    'system'
) ON CONFLICT (plan_code) DO UPDATE SET
    price_cents = EXCLUDED.price_cents,
    original_price_cents = EXCLUDED.original_price_cents,
    updated_at = NOW();

-- 2000 Credits Pack (Best Value)
INSERT INTO pricing_plans (
    plan_code, plan_type, plan_name, description,
    price_cents, original_price_cents, currency,
    credits_amount,
    stripe_price_id_prod, stripe_price_id_dev,
    stripe_product_id,
    is_active, is_visible, is_featured, sort_order,
    version, effective_from,
    metadata, created_by
) VALUES (
    'credits_2000',
    'credits',
    '2000 Credits Pack',
    '适合专业创作者或团队使用',
    4800,
    6000,
    'USD',
    2000,
    '{{ STRIPE_PRICE_CREDITS_2000_PROD }}',
    '{{ STRIPE_PRICE_CREDITS_2000_DEV }}',
    '{{ STRIPE_PRODUCT_CREDITS }}',
    TRUE,
    TRUE,
    TRUE,
    12,
    1,
    NOW(),
    '{"discount_percent": 20, "unit_price_cents": 2.4, "badge": "BEST VALUE"}'::jsonb,
    'system'
) ON CONFLICT (plan_code) DO UPDATE SET
    price_cents = EXCLUDED.price_cents,
    original_price_cents = EXCLUDED.original_price_cents,
    updated_at = NOW();


-- ============================================================================
-- PART 2: SYSTEM CONFIGS (80 records)
-- ============================================================================
-- Config Groups:
--   - rate_limit: API rate limiting (24 records)
--   - analytics: Analytics settings (3 records)
--   - feature_flag: Feature toggles (9 records)
--   - limits: System limits (5 records)
--   - credits: Credit costs (9 records)
--   - pricing: Pricing display (8 records)
--   - ai_providers: AI provider settings (8 records)
--   - ui: UI text (3 records)
--   - marketing: Marketing text (2 records)
--   - tooltip: Tooltip text (2 records)
--   - marketplace: Marketplace settings (3 records)
--   - tier: Tier display names (15 records)
--   - trial: Trial period (3 records) - v3.33 更新
--   - tag: Tag system (4 records) - v3.33 新增
--   - database: Database settings (1 record)
-- ============================================================================

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
-- FEATURE FLAGS (9 records)
-- ============================================================================
-- Core features
('FEATURE_AI_GENERATION', 'true', 'boolean', 'feature_flag', 'Enable AI image generation', true, true),
('FEATURE_ASYNC_GENERATION', 'false', 'boolean', 'feature_flag', 'Enable async AI generation mode (polling-based)', true, true),
('FEATURE_MARKETPLACE', 'true', 'boolean', 'feature_flag', 'Enable marketplace', true, true),
('FEATURE_OCR', 'true', 'boolean', 'feature_flag', 'Enable OCR/Smart Scan', true, true),
('FEATURE_ZIP_EXPORT', 'true', 'boolean', 'feature_flag', 'Enable ZIP export', true, true),
-- Landing page sections
('FEATURE_LANDING_HERO', 'true', 'boolean', 'feature_flag', 'Enable landing page hero section', true, true),
('FEATURE_LANDING_HOW_IT_WORKS', 'true', 'boolean', 'feature_flag', 'Enable landing page how-it-works section', true, true),
('FEATURE_LANDING_PRICING', 'true', 'boolean', 'feature_flag', 'Enable landing page pricing section', true, true),
('FEATURE_LANDING_FINAL_CTA', 'true', 'boolean', 'feature_flag', 'Enable landing page final CTA section', true, true),

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
-- TIER SYSTEM (15 records)
-- ============================================================================
-- Display names
('tier.t1.display_name', 'Free Plan', 'text', 'tier', 'First Tier 显示名称', true, true),
('tier.t2.display_name', 'Starter Plan', 'text', 'tier', 'Second Tier 显示名称', true, true),
('tier.t3.display_name', 'Pro Plan', 'text', 'tier', 'Third Tier 显示名称', true, true),
-- Monthly credits
('tier.t1.monthly_credits', '0', 'integer', 'tier', 'First Tier 月度积分', true, false),
('tier.t2.monthly_credits', '100', 'integer', 'tier', 'Second Tier 月度积分', true, false),
('tier.t3.monthly_credits', '200', 'integer', 'tier', 'Third Tier 月度积分', true, false),
-- Original prices (for display strikethrough)
('tier.t1.original_price', '0', 'number', 'tier', 'First Tier 原价', true, true),
('tier.t2.original_price', '9.9', 'number', 'tier', 'Second Tier 原价', true, true),
('tier.t3.original_price', '15.9', 'number', 'tier', 'Third Tier 原价', true, true),
-- Current prices
('tier.t1.current_price', '0', 'number', 'tier', 'First Tier 现价', true, true),
('tier.t2.current_price', '6.9', 'number', 'tier', 'Second Tier 现价', true, true),
('tier.t3.current_price', '9.9', 'number', 'tier', 'Third Tier 现价', true, true),
-- Max projects
('tier.t1.max_projects', '1', 'integer', 'tier', 'First Tier 最大项目数', true, true),
('tier.t2.max_projects', '20', 'integer', 'tier', 'Second Tier 最大项目数', true, true),
('tier.t3.max_projects', '200', 'integer', 'tier', 'Third Tier 最大项目数', true, true),

-- ============================================================================
-- TRIAL PERIOD (3 records) - v3.33 更新
-- ============================================================================
('trial.default_days', '7', 'integer', 'trial', 'Free tier 默认试用期天数', true, true),
('trial.urgent_threshold_days', '2', 'integer', 'trial', '触发紧迫状态的剩余天数 (显示为 amber 色)', true, true),
('trial.duration_days', '30', 'integer', 'trial', '[已废弃] 使用 trial.default_days', true, false),

-- ============================================================================
-- TAG SYSTEM (4 records) - v3.33 新增
-- ============================================================================
('tag.max_tags_per_workspace', '100', 'integer', 'tag', '每个 Workspace 最大标签数', true, true),
('tag.max_tags_per_project', '10', 'integer', 'tag', '每个项目最大标签数', true, true),
('tag.max_tags_per_asset', '10', 'integer', 'tag', '每个素材最大标签数', true, true),
('tag.enable_preset_groups', 'true', 'boolean', 'tag', '新 Workspace 是否自动创建预设标签分组', true, true),

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


-- ============================================================================
-- PART 3: TAG GROUP PRESETS (4 records) - v3.33 新增
-- ============================================================================
-- 预设标签分组模板，新用户创建 Workspace 时可选择应用

INSERT INTO tag_group_presets (group_name, display_name, description, icon, preset_tags, is_default, sort_order, is_active)
VALUES
  -- Grade Level (教育年级)
  ('grade_level', 'Grade Level', 'Organize by student grade level', '🎓',
   '[
     {"name": "Pre-K", "color": "pink"},
     {"name": "Kindergarten", "color": "purple"},
     {"name": "Grade 1", "color": "blue"},
     {"name": "Grade 2", "color": "green"},
     {"name": "Grade 3", "color": "yellow"},
     {"name": "Grade 4", "color": "orange"},
     {"name": "Grade 5", "color": "red"}
   ]'::jsonb, TRUE, 1, TRUE),

  -- Phonics Pattern (自然拼读)
  ('phonics_pattern', 'Phonics Pattern', 'Categorize by phonics patterns', '📖',
   '[
     {"name": "CVC Words", "color": "blue"},
     {"name": "CVCe Words", "color": "green"},
     {"name": "Blends", "color": "purple"},
     {"name": "Digraphs", "color": "orange"},
     {"name": "R-Controlled", "color": "red"},
     {"name": "Diphthongs", "color": "pink"}
   ]'::jsonb, TRUE, 2, TRUE),

  -- Topic (主题)
  ('topic', 'Topic', 'Organize by content topic', '📚',
   '[
     {"name": "Animals", "color": "green"},
     {"name": "Nature", "color": "blue"},
     {"name": "Science", "color": "purple"},
     {"name": "Holidays", "color": "red"},
     {"name": "Family", "color": "pink"},
     {"name": "Community", "color": "orange"}
   ]'::jsonb, TRUE, 3, TRUE),

  -- Status (项目状态)
  ('status', 'Status', 'Track project status', '📋',
   '[
     {"name": "Draft", "color": "gray"},
     {"name": "In Progress", "color": "yellow"},
     {"name": "Ready", "color": "green"},
     {"name": "Published", "color": "blue"}
   ]'::jsonb, FALSE, 4, TRUE)

ON CONFLICT (group_name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    icon = EXCLUDED.icon,
    preset_tags = EXCLUDED.preset_tags,
    is_default = EXCLUDED.is_default,
    sort_order = EXCLUDED.sort_order,
    is_active = EXCLUDED.is_active,
    updated_at = CURRENT_TIMESTAMP;


COMMIT;


-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- List all pricing plans
-- SELECT plan_code, plan_type, plan_name, price_cents, tier, monthly_credits, credits_amount
-- FROM pricing_plans
-- WHERE is_active = true
-- ORDER BY sort_order;

-- Expected pricing_plans results (6 rows):
-- | plan_code        | plan_type    | plan_name         | price_cents | tier | monthly_credits | credits_amount |
-- |------------------|--------------|-------------------|-------------|------|-----------------|----------------|
-- | tier_t1_monthly  | subscription | Free Plan         | 0           | t1   | 0               | NULL           |
-- | tier_t2_monthly  | subscription | Starter Plan      | 990         | t2   | 200             | NULL           |
-- | tier_t3_monthly  | subscription | Pro Plan          | 1990        | t3   | 500             | NULL           |
-- | credits_100      | credits      | 100 Credits Pack  | 299         | NULL | NULL            | 100            |
-- | credits_500      | credits      | 500 Credits Pack  | 1349        | NULL | NULL            | 500            |
-- | credits_2000     | credits      | 2000 Credits Pack | 4800        | NULL | NULL            | 2000           |

-- Count configs by group
-- SELECT config_group, COUNT(*) as count
-- FROM system_configs
-- WHERE is_active = true
-- GROUP BY config_group
-- ORDER BY count DESC;

-- Expected system_configs results (73 total records):
-- | config_group  | count |
-- |---------------|-------|
-- | rate_limit    | 24    |
-- | credits       | 9     |
-- | feature_flag  | 9     |
-- | pricing       | 8     |
-- | ai_providers  | 5     |
-- | ai_models     | 4     |
-- | limits        | 5     |
-- | tier          | 6     |
-- | analytics     | 3     |
-- | ui            | 3     |
-- | marketplace   | 3     |
-- | marketing     | 2     |
-- | tooltip       | 2     |
-- | trial         | 1     |
-- | database      | 1     |


-- ============================================================================
-- END OF PLATFORM CONFIGURATION SEED DATA
-- ============================================================================
