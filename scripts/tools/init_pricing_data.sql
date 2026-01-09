-- ============================================================================
-- Initialize Pricing Data - 初始化价格配置数据
-- ============================================================================
-- Description: 导入当前系统的订阅方案和积分包价格
-- Usage: 在创建 pricing_plans 表后运行此脚本
-- Reference: docs/main/API_REFERENCE.md Section 6.1 & 6.2
--
-- ⚠️ 注意: Stripe Price ID 需要根据实际环境配置
-- ============================================================================

BEGIN;

-- ============================================================================
-- Part 1: 订阅方案 (Subscription Plans)
-- ============================================================================

-- Free Plan (t1) - Monthly
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
    'tier_t1_monthly',                      -- plan_code
    'subscription',                         -- plan_type
    'Free Plan',                            -- plan_name
    '免费方案，注册即可使用基础功能',        -- description
    0,                                      -- price_cents ($0)
    NULL,                                   -- original_price_cents (无划线价)
    'USD',                                  -- currency
    'month',                                -- billing_interval
    't1',                                   -- tier
    0,                                      -- monthly_credits
    NULL,                                   -- stripe_price_id_prod (免费无需 Price ID)
    NULL,                                   -- stripe_price_id_dev
    NULL,                                   -- stripe_product_id
    TRUE,                                   -- is_active
    TRUE,                                   -- is_visible
    FALSE,                                  -- is_featured
    0,                                      -- sort_order (最先显示)
    1,                                      -- version
    NOW(),                                  -- effective_from
    '{"badge": "FREE"}'::jsonb,             -- metadata
    'system'                                -- created_by
) ON CONFLICT (plan_code) DO UPDATE SET
    price_cents = EXCLUDED.price_cents,
    updated_at = NOW();

-- Starter Plan (t2) - Monthly
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
    'tier_t2_monthly',                      -- plan_code
    'subscription',                         -- plan_type
    'Starter Plan',                         -- plan_name
    '适合个人创作者，包含贴纸库和发布权限',  -- description
    990,                                    -- price_cents ($9.9)
    1490,                                   -- original_price_cents ($14.9)
    'USD',                                  -- currency
    'month',                                -- billing_interval
    't2',                                   -- tier
    200,                                    -- monthly_credits
    '{{ STRIPE_PRICE_SUB_STARTER_PROD }}',  -- ⚠️ 替换为实际 Price ID
    '{{ STRIPE_PRICE_SUB_STARTER_DEV }}',   -- ⚠️ 替换为实际 Price ID
    '{{ STRIPE_PRODUCT_STARTER }}',         -- ⚠️ 替换为实际 Product ID
    TRUE,                                   -- is_active
    TRUE,                                   -- is_visible
    FALSE,                                  -- is_featured
    1,                                      -- sort_order
    1,                                      -- version
    NOW(),                                  -- effective_from
    '{"discount_percent": 34, "badge": null}'::jsonb,  -- metadata (34% off: $14.9 → $9.9)
    'system'                                -- created_by
) ON CONFLICT (plan_code) DO UPDATE SET
    price_cents = EXCLUDED.price_cents,
    original_price_cents = EXCLUDED.original_price_cents,
    updated_at = NOW();

-- Pro Plan (t3) - Monthly
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
    'tier_t3_monthly',                      -- plan_code
    'subscription',                         -- plan_type
    'Pro Plan',                             -- plan_name
    '专业创作者首选，包含全功能和商业授权', -- description
    1990,                                   -- price_cents ($19.9)
    2990,                                   -- original_price_cents ($29.9)
    'USD',                                  -- currency
    'month',                                -- billing_interval
    't3',                                   -- tier
    500,                                    -- monthly_credits
    '{{ STRIPE_PRICE_SUB_PRO_PROD }}',      -- ⚠️ 替换为实际 Price ID
    '{{ STRIPE_PRICE_SUB_PRO_DEV }}',       -- ⚠️ 替换为实际 Price ID
    '{{ STRIPE_PRODUCT_PRO }}',             -- ⚠️ 替换为实际 Product ID
    TRUE,                                   -- is_active
    TRUE,                                   -- is_visible
    TRUE,                                   -- is_featured (推荐)
    2,                                      -- sort_order
    1,                                      -- version
    NOW(),                                  -- effective_from
    '{"discount_percent": 34, "badge": "RECOMMENDED"}'::jsonb,  -- metadata
    'system'                                -- created_by
) ON CONFLICT (plan_code) DO UPDATE SET
    price_cents = EXCLUDED.price_cents,
    original_price_cents = EXCLUDED.original_price_cents,
    updated_at = NOW();

-- ============================================================================
-- Part 2: 积分包 (Credits Packs)
-- ============================================================================

-- 100 Credits Pack (小包)
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
    'credits_100',                          -- plan_code
    'credits',                              -- plan_type
    '100 Credits Pack',                     -- plan_name
    '适合偶尔使用 AI 功能的用户',            -- description
    299,                                    -- price_cents ($2.99)
    NULL,                                   -- original_price_cents (无划线价)
    'USD',                                  -- currency
    100,                                    -- credits_amount
    '{{ STRIPE_PRICE_CREDITS_100_PROD }}',  -- ⚠️ 替换为实际 Price ID
    '{{ STRIPE_PRICE_CREDITS_100_DEV }}',   -- ⚠️ 替换为实际 Price ID
    '{{ STRIPE_PRODUCT_CREDITS }}',         -- ⚠️ 替换为实际 Product ID
    TRUE,                                   -- is_active
    TRUE,                                   -- is_visible
    FALSE,                                  -- is_featured
    10,                                     -- sort_order
    1,                                      -- version
    NOW(),                                  -- effective_from
    '{"unit_price_cents": 2.99, "badge": null}'::jsonb,  -- metadata ($0.0299/credit)
    'system'                                -- created_by
) ON CONFLICT (plan_code) DO UPDATE SET
    price_cents = EXCLUDED.price_cents,
    updated_at = NOW();

-- 500 Credits Pack (中包) - 9折
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
    'credits_500',                          -- plan_code
    'credits',                              -- plan_type
    '500 Credits Pack',                     -- plan_name
    '适合经常使用 AI 功能的创作者',          -- description
    1349,                                   -- price_cents ($13.49)
    1499,                                   -- original_price_cents ($14.99)
    'USD',                                  -- currency
    500,                                    -- credits_amount
    '{{ STRIPE_PRICE_CREDITS_500_PROD }}',  -- ⚠️ 替换为实际 Price ID
    '{{ STRIPE_PRICE_CREDITS_500_DEV }}',   -- ⚠️ 替换为实际 Price ID
    '{{ STRIPE_PRODUCT_CREDITS }}',         -- ⚠️ 替换为实际 Product ID
    TRUE,                                   -- is_active
    TRUE,                                   -- is_visible
    TRUE,                                   -- is_featured
    11,                                     -- sort_order
    1,                                      -- version
    NOW(),                                  -- effective_from
    '{"discount_percent": 10, "unit_price_cents": 2.698, "badge": "POPULAR"}'::jsonb,  -- metadata
    'system'                                -- created_by
) ON CONFLICT (plan_code) DO UPDATE SET
    price_cents = EXCLUDED.price_cents,
    original_price_cents = EXCLUDED.original_price_cents,
    updated_at = NOW();

-- 2000 Credits Pack (大包) - 8折
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
    'credits_2000',                         -- plan_code
    'credits',                              -- plan_type
    '2000 Credits Pack',                    -- plan_name
    '适合专业创作者或团队使用',              -- description
    4800,                                   -- price_cents ($48.00)
    6000,                                   -- original_price_cents ($60.00)
    'USD',                                  -- currency
    2000,                                   -- credits_amount
    '{{ STRIPE_PRICE_CREDITS_2000_PROD }}', -- ⚠️ 替换为实际 Price ID
    '{{ STRIPE_PRICE_CREDITS_2000_DEV }}',  -- ⚠️ 替换为实际 Price ID
    '{{ STRIPE_PRODUCT_CREDITS }}',         -- ⚠️ 替换为实际 Product ID
    TRUE,                                   -- is_active
    TRUE,                                   -- is_visible
    TRUE,                                   -- is_featured
    12,                                     -- sort_order
    1,                                      -- version
    NOW(),                                  -- effective_from
    '{"discount_percent": 20, "unit_price_cents": 2.4, "badge": "BEST VALUE"}'::jsonb,  -- metadata
    'system'                                -- created_by
) ON CONFLICT (plan_code) DO UPDATE SET
    price_cents = EXCLUDED.price_cents,
    original_price_cents = EXCLUDED.original_price_cents,
    updated_at = NOW();

-- ============================================================================
-- Verification
-- ============================================================================

DO $$
DECLARE
    v_subscription_count INT;
    v_credits_count INT;
    v_total_count INT;
BEGIN
    -- Count subscription plans
    SELECT COUNT(*) INTO v_subscription_count
    FROM pricing_plans
    WHERE plan_type = 'subscription' AND is_active = TRUE;

    -- Count credits packs
    SELECT COUNT(*) INTO v_credits_count
    FROM pricing_plans
    WHERE plan_type = 'credits' AND is_active = TRUE;

    -- Total
    v_total_count := v_subscription_count + v_credits_count;

    RAISE NOTICE '========================================';
    RAISE NOTICE '✅ Pricing Data Initialization Summary';
    RAISE NOTICE '========================================';
    RAISE NOTICE '  Subscription Plans: %', v_subscription_count;
    RAISE NOTICE '  Credits Packs: %', v_credits_count;
    RAISE NOTICE '  Total Active Plans: %', v_total_count;
    RAISE NOTICE '========================================';

    IF v_total_count >= 6 THEN
        RAISE NOTICE '✅ Pricing data initialized successfully';
    ELSE
        RAISE WARNING '⚠️ Expected at least 6 plans, found %', v_total_count;
    END IF;

    -- Display pricing summary
    RAISE NOTICE '';
    RAISE NOTICE 'Current Pricing:';
    FOR rec IN (
        SELECT
            plan_code,
            plan_name,
            CASE
                WHEN plan_type = 'subscription' THEN '$' || (price_cents::float / 100)::text || '/month'
                ELSE '$' || (price_cents::float / 100)::text || ' (' || credits_amount::text || ' credits)'
            END AS display_price
        FROM pricing_plans
        WHERE is_active = TRUE
        ORDER BY sort_order
    ) LOOP
        RAISE NOTICE '  - %: % - %', rec.plan_code, rec.plan_name, rec.display_price;
    END LOOP;
END $$;

COMMIT;

-- ============================================================================
-- Notes for Deployment
-- ============================================================================
/*
部署前检查清单:

1. 替换 Stripe Price ID 占位符:
   - {{ STRIPE_PRICE_SUB_STARTER_PROD }}
   - {{ STRIPE_PRICE_SUB_PRO_PROD }}
   - {{ STRIPE_PRICE_CREDITS_100_PROD }}
   - {{ STRIPE_PRICE_CREDITS_500_PROD }}
   - {{ STRIPE_PRICE_CREDITS_2000_PROD }}
   - (对应的 _DEV 版本)

2. 从 Stripe Dashboard 获取:
   - Products → 找到对应 Product
   - Pricing → 复制 Price ID

3. 验证价格匹配:
   - Stripe 中的价格必须与此处的 price_cents 一致
   - 否则 checkout 会失败

4. 环境变量备份:
   - 保留现有环境变量作为 fallback
   - 逐步迁移到数据库配置

5. 测试:
   - 先在 dev 环境测试完整支付流程
   - 确认 webhook 正确识别 plan_code
*/
