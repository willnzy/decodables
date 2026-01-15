-- =============================================================================
-- HOTFIX: 重命名 PRICING 配置键 (STARTER/PRO → T2/T3)
-- =============================================================================
-- 问题: 配置键使用 STARTER/PRO 命名，应统一为 T2/T3
-- 修复: 重命名所有 PRICING 组中的配置键
-- 
-- 重命名映射:
--   STARTER_PLAN_PRICE → T2_PLAN_PRICE
--   STARTER_PLAN_ORIGINAL_PRICE → T2_PLAN_ORIGINAL_PRICE
--   STARTER_MONTHLY_CREDITS → T2_MONTHLY_CREDITS
--   PRO_PLAN_PRICE → T3_PLAN_PRICE
--   PRO_PLAN_ORIGINAL_PRICE → T3_PLAN_ORIGINAL_PRICE
--   PRO_MONTHLY_CREDITS → T3_MONTHLY_CREDITS
--   PRO_CREDITS_DISCOUNT_PERCENT → T3_CREDITS_DISCOUNT_PERCENT
-- =============================================================================

-- 重命名 STARTER → T2
UPDATE system_configs SET config_key = 'T2_PLAN_PRICE', description = 't2 monthly price' 
WHERE config_key = 'STARTER_PLAN_PRICE';

UPDATE system_configs SET config_key = 'T2_PLAN_ORIGINAL_PRICE', description = 't2 original price (for display)' 
WHERE config_key = 'STARTER_PLAN_ORIGINAL_PRICE';

UPDATE system_configs SET config_key = 'T2_MONTHLY_CREDITS', description = 't2 monthly credits (sync with tier.t2.monthly_credits)' 
WHERE config_key = 'STARTER_MONTHLY_CREDITS';

-- 重命名 PRO → T3
UPDATE system_configs SET config_key = 'T3_PLAN_PRICE', description = 't3 monthly price' 
WHERE config_key = 'PRO_PLAN_PRICE';

UPDATE system_configs SET config_key = 'T3_PLAN_ORIGINAL_PRICE', description = 't3 original price (for display)' 
WHERE config_key = 'PRO_PLAN_ORIGINAL_PRICE';

UPDATE system_configs SET config_key = 'T3_MONTHLY_CREDITS', description = 't3 monthly credits (sync with tier.t3.monthly_credits)' 
WHERE config_key = 'PRO_MONTHLY_CREDITS';

UPDATE system_configs SET config_key = 'T3_CREDITS_DISCOUNT_PERCENT', description = 't3 discount on credit purchases' 
WHERE config_key = 'PRO_CREDITS_DISCOUNT_PERCENT';

-- 验证修改
SELECT config_key, config_value, description 
FROM system_configs 
WHERE config_key LIKE 'T2_%' OR config_key LIKE 'T3_%'
ORDER BY config_key;
