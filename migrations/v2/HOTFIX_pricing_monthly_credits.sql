-- =============================================================================
-- HOTFIX: 统一 PRICING 和 TIER 配置的 monthly_credits 值
-- =============================================================================
-- 问题: STARTER_MONTHLY_CREDITS/PRO_MONTHLY_CREDITS 与 tier.*.monthly_credits 不一致
-- 修复: 将 PRICING 配置与 TIER 配置同步
-- 
-- 配置值对照:
--   tier.t2.monthly_credits = 200 → STARTER_MONTHLY_CREDITS = 200
--   tier.t3.monthly_credits = 500 → PRO_MONTHLY_CREDITS = 500
-- =============================================================================

-- 1. 更新 STARTER_MONTHLY_CREDITS (500 → 200)
UPDATE system_configs 
SET config_value = '200',
    description = 'Starter monthly credits (sync with tier.t2.monthly_credits)',
    updated_at = NOW()
WHERE config_key = 'STARTER_MONTHLY_CREDITS';

-- 2. 更新 PRO_MONTHLY_CREDITS (1000 → 500)
UPDATE system_configs 
SET config_value = '500',
    description = 'Pro monthly credits (sync with tier.t3.monthly_credits)',
    updated_at = NOW()
WHERE config_key = 'PRO_MONTHLY_CREDITS';

-- 3. 验证修改
SELECT config_key, config_value, description 
FROM system_configs 
WHERE config_key IN ('STARTER_MONTHLY_CREDITS', 'PRO_MONTHLY_CREDITS', 
                     'tier.t2.monthly_credits', 'tier.t3.monthly_credits')
ORDER BY config_key;

-- 说明: 此脚本的修改已合并到 03_infrastructure.sql
