-- =============================================================================
-- HOTFIX: 统一 Monthly Credits 配置为 t2=100, t3=200
-- =============================================================================
-- 问题: 文档定义 t2=100, t3=200，但数据库配置为 t2=200, t3=500
-- 修复: 将数据库配置更新为文档定义的值
-- 
-- 正确配置 (与 TIER-PERMISSIONS.md 一致):
--   - tier.t1.monthly_credits = 0
--   - tier.t2.monthly_credits = 100
--   - tier.t3.monthly_credits = 200
-- =============================================================================

-- 1. 更新 tier.* 配置 (主要配置)
UPDATE system_configs 
SET config_value = '100',
    updated_at = NOW()
WHERE config_key = 'tier.t2.monthly_credits';

UPDATE system_configs 
SET config_value = '200',
    updated_at = NOW()
WHERE config_key = 'tier.t3.monthly_credits';

-- 2. 重命名并更新 PRICING 组配置 (STARTER_* → T2_*, PRO_* → T3_*)
UPDATE system_configs 
SET config_key = 'T2_MONTHLY_CREDITS',
    config_value = '100',
    description = 't2 monthly credits (sync with tier.t2.monthly_credits)',
    updated_at = NOW()
WHERE config_key = 'STARTER_MONTHLY_CREDITS';

UPDATE system_configs 
SET config_key = 'T3_MONTHLY_CREDITS',
    config_value = '200',
    description = 't3 monthly credits (sync with tier.t3.monthly_credits)',
    updated_at = NOW()
WHERE config_key = 'PRO_MONTHLY_CREDITS';

-- 3. 重命名其他 STARTER/PRO 配置
UPDATE system_configs SET config_key = 'T2_PLAN_PRICE' WHERE config_key = 'STARTER_PLAN_PRICE';
UPDATE system_configs SET config_key = 'T2_PLAN_ORIGINAL_PRICE' WHERE config_key = 'STARTER_PLAN_ORIGINAL_PRICE';
UPDATE system_configs SET config_key = 'T3_PLAN_PRICE' WHERE config_key = 'PRO_PLAN_PRICE';
UPDATE system_configs SET config_key = 'T3_PLAN_ORIGINAL_PRICE' WHERE config_key = 'PRO_PLAN_ORIGINAL_PRICE';
UPDATE system_configs SET config_key = 'T3_CREDITS_DISCOUNT_PERCENT' WHERE config_key = 'PRO_CREDITS_DISCOUNT_PERCENT';

-- 4. 更新 AI 模型配置中的 tier 命名 (free/starter/pro → t1/t2/t3)
UPDATE system_configs 
SET config_value = '{"provider": "fal", "models": {"t1": "flux-schnell", "t2": "flux-schnell", "t3": "flux-dev"}, "fallback": {"provider": "fal", "model": "flux-schnell"}, "show_provider": false}',
    updated_at = NOW()
WHERE config_key = 'ai_model.user.image_generation';

-- 5. 验证修改
SELECT config_key, config_value, config_group
FROM system_configs 
WHERE config_key IN (
    'tier.t1.monthly_credits',
    'tier.t2.monthly_credits', 
    'tier.t3.monthly_credits',
    'T2_MONTHLY_CREDITS',
    'T3_MONTHLY_CREDITS',
    'T2_PLAN_PRICE',
    'T3_PLAN_PRICE',
    'ai_model.user.image_generation'
)
ORDER BY config_key;

-- 预期结果:
-- | config_key                    | config_value | config_group |
-- |-------------------------------|--------------|--------------|
-- | T2_MONTHLY_CREDITS            | 100          | pricing      |
-- | T2_PLAN_PRICE                 | 14.9         | pricing      |
-- | T3_MONTHLY_CREDITS            | 200          | pricing      |
-- | T3_PLAN_PRICE                 | 29.9         | pricing      |
-- | ai_model.user.image_generation| {...t1/t2/t3...} | ai_models |
-- | tier.t1.monthly_credits       | 0            | tier         |
-- | tier.t2.monthly_credits       | 100          | tier         |
-- | tier.t3.monthly_credits       | 200          | tier         |
