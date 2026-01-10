-- ============================================================================
-- Make Decodables - 初始数据
-- ============================================================================
-- 生成时间: 2026-01-10
-- 来源: refactored_schema_v2.sql
-- PostgreSQL 版本: 15+
-- ============================================================================

BEGIN;


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
