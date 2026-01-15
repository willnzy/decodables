-- ============================================================================
-- PRICING PLANS SEED FILE
-- ============================================================================
-- Contains: Subscription plans and credit packages
-- Extracted from: migrations/v2/03_infrastructure.sql
--
-- Tables seeded:
--   - pricing_plans (6 records: 3 subscriptions + 3 credit packs)
--
-- Usage:
--   psql $DATABASE_URL -f migrations/seed/pricing_plans_seed.sql
--
-- Note: Uses ON CONFLICT DO UPDATE to make script idempotent
-- ============================================================================

BEGIN;

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

COMMIT;


-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- List all pricing plans
-- SELECT plan_code, plan_type, plan_name, price_cents, tier, monthly_credits, credits_amount
-- FROM pricing_plans
-- WHERE is_active = true
-- ORDER BY sort_order;

-- Expected results:
-- | plan_code        | plan_type    | plan_name         | price_cents | tier | monthly_credits | credits_amount |
-- |------------------|--------------|-------------------|-------------|------|-----------------|----------------|
-- | tier_t1_monthly  | subscription | Free Plan         | 0           | t1   | 0               | NULL           |
-- | tier_t2_monthly  | subscription | Starter Plan      | 990         | t2   | 200             | NULL           |
-- | tier_t3_monthly  | subscription | Pro Plan          | 1990        | t3   | 500             | NULL           |
-- | credits_100      | credits      | 100 Credits Pack  | 299         | NULL | NULL            | 100            |
-- | credits_500      | credits      | 500 Credits Pack  | 1349        | NULL | NULL            | 500            |
-- | credits_2000     | credits      | 2000 Credits Pack | 4800        | NULL | NULL            | 2000           |


-- ============================================================================
-- END OF PRICING PLANS SEED DATA
-- ============================================================================
