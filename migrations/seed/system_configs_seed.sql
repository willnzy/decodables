-- ============================================================================
-- SYSTEM CONFIGS SEED FILE
-- ============================================================================
-- Contains: System configuration for tier, credits, pricing, feature flags
--
-- Config Groups:
--   - tier: Subscription tier configurations
--   - credits: Credit costs and packages
--   - pricing: Pricing information
--   - feature_flag: Feature flags
--   - limits: System limits
--   - site: Site information
--   - marketplace: Marketplace settings
--   - trial: Trial configuration
--   - support: Support settings
--
-- Usage:
--   psql $DATABASE_URL -f migrations/seed/system_configs_seed.sql
--
-- Note: Uses ON CONFLICT DO UPDATE to make script idempotent
-- ============================================================================

BEGIN;

-- ============================================================================
-- TIER CONFIGURATIONS (config_group = 'tier')
-- ============================================================================

INSERT INTO system_configs (key, value, value_type, config_group, description, is_active, is_editable)
VALUES
    -- T1 (Free Plan)
    ('tier.t1.display_name', 'Free Plan', 'text', 'tier', 'First Tier display name', TRUE, TRUE),
    ('tier.t1.monthly_credits', '0', 'integer', 'tier', 'First Tier monthly credits', TRUE, FALSE),
    ('tier.t1.signup_bonus', '100', 'integer', 'tier', 'First Tier signup bonus credits', TRUE, TRUE),
    ('tier.t1.original_price', '0', 'decimal', 'tier', 'First Tier original price', TRUE, FALSE),
    ('tier.t1.current_price', '0', 'decimal', 'tier', 'First Tier current price', TRUE, FALSE),
    ('tier.t1.max_projects', '1', 'integer', 'tier', 'First Tier max projects', TRUE, TRUE),
    ('tier.t1.max_pages_per_project', '8', 'integer', 'tier', 'First Tier max pages per project', TRUE, FALSE),
    ('tier.t1.max_assets_storage', '100', 'integer', 'tier', 'First Tier max assets storage (MB)', TRUE, TRUE),
    ('tier.t1.can_publish_to_marketplace', 'false', 'boolean', 'tier', 'First Tier can publish to marketplace', TRUE, FALSE),
    ('tier.t1.can_use_premium_assets', 'false', 'boolean', 'tier', 'First Tier can use premium assets', TRUE, FALSE),
    ('tier.t1.can_use_ai_features', 'true', 'boolean', 'tier', 'First Tier can use AI features', TRUE, FALSE),
    ('tier.t1.ai_daily_limit', '5', 'integer', 'tier', 'First Tier AI daily limit', TRUE, TRUE),
    ('tier.t1.export_formats', '["pdf"]', 'json', 'tier', 'First Tier export formats', TRUE, FALSE),
    ('tier.t1.support_level', 'community', 'text', 'tier', 'First Tier support level', TRUE, FALSE),

    -- T2 (Starter Plan)
    ('tier.t2.display_name', 'Starter Plan', 'text', 'tier', 'Second Tier display name', TRUE, TRUE),
    ('tier.t2.monthly_credits', '100', 'integer', 'tier', 'Second Tier monthly credits', TRUE, TRUE),
    ('tier.t2.original_price', '9.9', 'decimal', 'tier', 'Second Tier original price', TRUE, TRUE),
    ('tier.t2.current_price', '6.9', 'decimal', 'tier', 'Second Tier current price', TRUE, TRUE),
    ('tier.t2.max_projects', '20', 'integer', 'tier', 'Second Tier max projects', TRUE, TRUE),
    ('tier.t2.max_pages_per_project', '8', 'integer', 'tier', 'Second Tier max pages per project', TRUE, FALSE),
    ('tier.t2.max_assets_storage', '500', 'integer', 'tier', 'Second Tier max assets storage (MB)', TRUE, TRUE),
    ('tier.t2.can_publish_to_marketplace', 'true', 'boolean', 'tier', 'Second Tier can publish to marketplace', TRUE, FALSE),
    ('tier.t2.can_use_premium_assets', 'true', 'boolean', 'tier', 'Second Tier can use premium assets', TRUE, FALSE),
    ('tier.t2.can_use_ai_features', 'true', 'boolean', 'tier', 'Second Tier can use AI features', TRUE, FALSE),
    ('tier.t2.ai_daily_limit', '50', 'integer', 'tier', 'Second Tier AI daily limit', TRUE, TRUE),
    ('tier.t2.export_formats', '["pdf"]', 'json', 'tier', 'Second Tier export formats', TRUE, FALSE),
    ('tier.t2.support_level', 'email', 'text', 'tier', 'Second Tier support level', TRUE, FALSE),

    -- T3 (Pro Plan)
    ('tier.t3.display_name', 'Pro Plan', 'text', 'tier', 'Third Tier display name', TRUE, TRUE),
    ('tier.t3.monthly_credits', '200', 'integer', 'tier', 'Third Tier monthly credits', TRUE, TRUE),
    ('tier.t3.original_price', '15.9', 'decimal', 'tier', 'Third Tier original price', TRUE, TRUE),
    ('tier.t3.current_price', '9.9', 'decimal', 'tier', 'Third Tier current price', TRUE, TRUE),
    ('tier.t3.max_projects', '200', 'integer', 'tier', 'Third Tier max projects', TRUE, TRUE),
    ('tier.t3.max_pages_per_project', '8', 'integer', 'tier', 'Third Tier max pages per project', TRUE, FALSE),
    ('tier.t3.max_assets_storage', '2000', 'integer', 'tier', 'Third Tier max assets storage (MB)', TRUE, TRUE),
    ('tier.t3.can_publish_to_marketplace', 'true', 'boolean', 'tier', 'Third Tier can publish to marketplace', TRUE, FALSE),
    ('tier.t3.can_use_premium_assets', 'true', 'boolean', 'tier', 'Third Tier can use premium assets', TRUE, FALSE),
    ('tier.t3.can_use_ai_features', 'true', 'boolean', 'tier', 'Third Tier can use AI features', TRUE, FALSE),
    ('tier.t3.ai_daily_limit', '0', 'integer', 'tier', 'Third Tier AI daily limit (0=unlimited)', TRUE, TRUE),
    ('tier.t3.export_formats', '["pdf", "zip"]', 'json', 'tier', 'Third Tier export formats', TRUE, FALSE),
    ('tier.t3.support_level', 'priority', 'text', 'tier', 'Third Tier support level', TRUE, FALSE),

    -- T4 (Enterprise - reserved)
    ('tier.t4.display_name', 'Enterprise', 'text', 'tier', 'Fourth Tier display name', TRUE, TRUE),
    ('tier.t4.monthly_credits', '1000', 'integer', 'tier', 'Fourth Tier monthly credits', TRUE, TRUE),
    ('tier.t4.original_price', '49.9', 'decimal', 'tier', 'Fourth Tier original price', TRUE, TRUE),
    ('tier.t4.current_price', '39.9', 'decimal', 'tier', 'Fourth Tier current price', TRUE, TRUE),
    ('tier.t4.max_projects', '0', 'integer', 'tier', 'Fourth Tier max projects (0=unlimited)', TRUE, TRUE),
    ('tier.t4.max_pages_per_project', '8', 'integer', 'tier', 'Fourth Tier max pages per project', TRUE, FALSE),
    ('tier.t4.max_assets_storage', '0', 'integer', 'tier', 'Fourth Tier max assets storage (0=unlimited)', TRUE, TRUE),
    ('tier.t4.can_publish_to_marketplace', 'true', 'boolean', 'tier', 'Fourth Tier can publish to marketplace', TRUE, FALSE),
    ('tier.t4.can_use_premium_assets', 'true', 'boolean', 'tier', 'Fourth Tier can use premium assets', TRUE, FALSE),
    ('tier.t4.can_use_ai_features', 'true', 'boolean', 'tier', 'Fourth Tier can use AI features', TRUE, FALSE),
    ('tier.t4.ai_daily_limit', '0', 'integer', 'tier', 'Fourth Tier AI daily limit (0=unlimited)', TRUE, TRUE),
    ('tier.t4.export_formats', '["pdf", "zip"]', 'json', 'tier', 'Fourth Tier export formats', TRUE, FALSE),
    ('tier.t4.support_level', 'dedicated', 'text', 'tier', 'Fourth Tier support level', TRUE, FALSE)

ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value,
    updated_at = CURRENT_TIMESTAMP;


-- ============================================================================
-- CREDITS CONFIGURATIONS (config_group = 'credits')
-- ============================================================================

INSERT INTO system_configs (key, value, value_type, config_group, description, is_active, is_editable)
VALUES
    -- Credit costs
    ('credits.cost.ai_image', '5', 'integer', 'credits', 'Credits per AI image generation', TRUE, TRUE),
    ('credits.cost.ai_image_reference', '5', 'integer', 'credits', 'Credits per AI image with reference', TRUE, TRUE),
    ('credits.cost.ai_page', '5', 'integer', 'credits', 'Credits per AI page design', TRUE, TRUE),
    ('credits.cost.ocr', '5', 'integer', 'credits', 'Credits per OCR/Smart Scan', TRUE, TRUE),
    ('credits.cost.pdf_export', '0', 'integer', 'credits', 'Credits per PDF export (free)', TRUE, FALSE),
    ('credits.cost.premium_asset', '0', 'integer', 'credits', 'Credits per premium asset use', TRUE, TRUE),

    -- Legacy keys (for backwards compatibility)
    ('CREDITS_PER_IMAGE', '5', 'integer', 'credits', 'Credits per image (legacy)', TRUE, TRUE),
    ('CREDITS_PER_OCR', '5', 'integer', 'credits', 'Credits per OCR (legacy)', TRUE, TRUE),
    ('CREDITS_PER_AI_DESIGN_PAGE', '5', 'integer', 'credits', 'Credits per AI page (legacy)', TRUE, TRUE),
    ('SIGNUP_BONUS_CREDITS', '100', 'integer', 'credits', 'Signup bonus credits', TRUE, TRUE)

ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value,
    updated_at = CURRENT_TIMESTAMP;


-- ============================================================================
-- PRICING CONFIGURATIONS (config_group = 'pricing')
-- ============================================================================

INSERT INTO system_configs (key, value, value_type, config_group, description, is_active, is_editable)
VALUES
    -- Credit packages (as JSON array)
    ('CREDITS_TIERS', '[{"id":"credits_100","credits":100,"originalPrice":2.99,"currentPrice":2.99,"popular":false},{"id":"credits_500","credits":500,"originalPrice":14.95,"currentPrice":13.46,"popular":true},{"id":"credits_2000","credits":2000,"originalPrice":59.80,"currentPrice":47.84,"popular":false}]', 'json', 'pricing', 'Credit package tiers', TRUE, TRUE),

    -- Plan prices (also stored in tier.* but duplicated here for pricing API)
    ('T2_PLAN_PRICE', '6.9', 'decimal', 'pricing', 'Starter plan current price', TRUE, TRUE),
    ('T2_PLAN_ORIGINAL_PRICE', '9.9', 'decimal', 'pricing', 'Starter plan original price', TRUE, TRUE),
    ('T3_PLAN_PRICE', '9.9', 'decimal', 'pricing', 'Pro plan current price', TRUE, TRUE),
    ('T3_PLAN_ORIGINAL_PRICE', '15.9', 'decimal', 'pricing', 'Pro plan original price', TRUE, TRUE),

    -- Pro discount
    ('PRO_CREDIT_DISCOUNT_PERCENT', '10', 'integer', 'pricing', 'Pro user credit purchase discount', TRUE, TRUE)

ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value,
    updated_at = CURRENT_TIMESTAMP;


-- ============================================================================
-- FEATURE FLAGS (config_group = 'feature_flag')
-- ============================================================================

INSERT INTO system_configs (key, value, value_type, config_group, description, is_active, is_editable)
VALUES
    ('FEATURE_AI_GENERATION', 'true', 'boolean', 'feature_flag', 'Enable AI image generation', TRUE, TRUE),
    ('FEATURE_MARKETPLACE', 'true', 'boolean', 'feature_flag', 'Enable marketplace', TRUE, TRUE),
    ('FEATURE_OCR', 'true', 'boolean', 'feature_flag', 'Enable OCR/Smart Scan', TRUE, TRUE),
    ('FEATURE_ZIP_EXPORT', 'true', 'boolean', 'feature_flag', 'Enable ZIP export (Pro only)', TRUE, TRUE),
    ('FEATURE_ASYNC_GENERATION', 'true', 'boolean', 'feature_flag', 'Enable async AI generation', TRUE, TRUE),
    ('FEATURE_STORY_GENERATION', 'true', 'boolean', 'feature_flag', 'Enable story generation', TRUE, TRUE),
    ('FEATURE_PREMIUM_ASSETS', 'true', 'boolean', 'feature_flag', 'Enable premium assets', TRUE, TRUE),
    ('FEATURE_REFERENCE_IMAGE', 'true', 'boolean', 'feature_flag', 'Enable reference image for AI', TRUE, TRUE)

ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value,
    updated_at = CURRENT_TIMESTAMP;


-- ============================================================================
-- LIMITS CONFIGURATIONS (config_group = 'limits')
-- ============================================================================

INSERT INTO system_configs (key, value, value_type, config_group, description, is_active, is_editable)
VALUES
    ('MAX_UPLOAD_FILE_SIZE_MB', '5', 'integer', 'limits', 'Max upload file size in MB', TRUE, TRUE),
    ('SUPPORTED_IMAGE_FORMATS', 'JPG, PNG, WEBP, GIF', 'text', 'limits', 'Supported image formats', TRUE, FALSE),
    ('SUPPORTED_EXPORT_FORMATS', 'PDF, ZIP', 'text', 'limits', 'Supported export formats', TRUE, FALSE),
    ('MAX_LISTING_PRICE', '500', 'integer', 'limits', 'Max marketplace listing price in credits', TRUE, TRUE),
    ('MIN_LISTING_PRICE', '0', 'integer', 'limits', 'Min marketplace listing price in credits', TRUE, TRUE)

ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value,
    updated_at = CURRENT_TIMESTAMP;


-- ============================================================================
-- SITE CONFIGURATIONS (config_group = 'site')
-- ============================================================================

INSERT INTO system_configs (key, value, value_type, config_group, description, is_active, is_editable)
VALUES
    ('SITE_NAME', 'Make Decodables', 'text', 'site', 'Site name', TRUE, TRUE),
    ('SITE_EMAIL', 'info@makedecodables.com', 'text', 'site', 'Support email', TRUE, TRUE),
    ('SITE_WHATSAPP', '+1 (725) 290 0525', 'text', 'site', 'WhatsApp number', TRUE, TRUE),
    ('SITE_URL', 'https://makedecodables.com', 'text', 'site', 'Site URL', TRUE, TRUE)

ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value,
    updated_at = CURRENT_TIMESTAMP;


-- ============================================================================
-- MARKETPLACE CONFIGURATIONS (config_group = 'marketplace')
-- ============================================================================

INSERT INTO system_configs (key, value, value_type, config_group, description, is_active, is_editable)
VALUES
    ('MARKETPLACE_SELLER_SHARE_PERCENT', '90', 'integer', 'marketplace', 'Seller share percentage', TRUE, TRUE),
    ('MARKETPLACE_PLATFORM_FEE_PERCENT', '10', 'integer', 'marketplace', 'Platform fee percentage', TRUE, TRUE),
    ('MARKETPLACE_REVIEW_HOURS', '24-48', 'text', 'marketplace', 'Review time range', TRUE, TRUE)

ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value,
    updated_at = CURRENT_TIMESTAMP;


-- ============================================================================
-- TRIAL CONFIGURATIONS (config_group = 'trial')
-- ============================================================================

INSERT INTO system_configs (key, value, value_type, config_group, description, is_active, is_editable)
VALUES
    ('TRIAL_DURATION_DAYS', '7', 'integer', 'trial', 'Trial period in days', TRUE, TRUE),
    ('TRIAL_ENABLED', 'true', 'boolean', 'trial', 'Enable trial period', TRUE, TRUE)

ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value,
    updated_at = CURRENT_TIMESTAMP;


-- ============================================================================
-- SUPPORT CONFIGURATIONS (config_group = 'support')
-- ============================================================================

INSERT INTO system_configs (key, value, value_type, config_group, description, is_active, is_editable)
VALUES
    ('SUPPORT_RESPONSE_HOURS', '24', 'integer', 'support', 'Support response time in hours', TRUE, TRUE)

ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value,
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
-- ORDER BY config_group;

-- Expected results:
-- | config_group  | count |
-- |---------------|-------|
-- | credits       | 10    |
-- | feature_flag  | 8     |
-- | limits        | 5     |
-- | marketplace   | 3     |
-- | pricing       | 6     |
-- | site          | 4     |
-- | support       | 1     |
-- | tier          | 56    |
-- | trial         | 2     |


-- ============================================================================
-- END OF SYSTEM CONFIGS SEED DATA
-- ============================================================================
