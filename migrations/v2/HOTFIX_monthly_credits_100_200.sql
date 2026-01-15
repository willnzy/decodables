-- =============================================================================
-- HOTFIX: 统一 Monthly Credits 配置为 t2=100, t3=200
-- =============================================================================
-- 问题: 文档定义 t2=100, t3=200，但数据库配置为 t2=200, t3=500
-- 修复: 将数据库配置更新为文档定义的值
-- 
-- 正确配置 (与 TIER-PERMISSIONS.md 一致):
--   - tier.t1.monthly_credits = 0
--   - tier.t2.monthly_credits = 100 (Starter)
--   - tier.t3.monthly_credits = 200 (Pro)
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

-- 2. 更新 PRICING 组配置 (前端显示用)
UPDATE system_configs 
SET config_value = '100',
    updated_at = NOW()
WHERE config_key = 'STARTER_MONTHLY_CREDITS';

UPDATE system_configs 
SET config_value = '200',
    updated_at = NOW()
WHERE config_key = 'PRO_MONTHLY_CREDITS';

-- 3. 验证修改
SELECT config_key, config_value, config_group
FROM system_configs 
WHERE config_key IN (
    'tier.t1.monthly_credits',
    'tier.t2.monthly_credits', 
    'tier.t3.monthly_credits',
    'STARTER_MONTHLY_CREDITS',
    'PRO_MONTHLY_CREDITS'
)
ORDER BY config_key;

-- 预期结果:
-- | config_key                 | config_value | config_group |
-- |---------------------------|--------------|--------------|
-- | PRO_MONTHLY_CREDITS       | 200          | pricing      |
-- | STARTER_MONTHLY_CREDITS   | 100          | pricing      |
-- | tier.t1.monthly_credits   | 0            | tier         |
-- | tier.t2.monthly_credits   | 100          | tier         |
-- | tier.t3.monthly_credits   | 200          | tier         |
