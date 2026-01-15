-- =============================================================================
-- HOTFIX: 清理重复的配置项，统一使用 tier.* 和 credits.cost.* 格式
-- =============================================================================
-- 问题: 存在多套配置，导致不一致
--   - STARTER_MONTHLY_CREDITS vs tier.t2.monthly_credits
--   - PRO_MONTHLY_CREDITS vs tier.t3.monthly_credits
--   - CREDITS_PER_OCR vs credits.cost.ocr
-- 
-- 解决方案: 删除重复配置，保留规范的配置键
-- 
-- 权威配置 (保留):
--   - tier.t1.monthly_credits = 0
--   - tier.t2.monthly_credits = 100
--   - tier.t3.monthly_credits = 200
--   - credits.cost.image_generation = 5
--   - credits.cost.ocr = 10
--   - credits.cost.smart_scan = 10
-- =============================================================================

-- Step 1: 删除重复的 PRICING 组月度积分配置
-- (这些已被 tier.*.monthly_credits 替代)
DELETE FROM system_configs 
WHERE config_key IN ('STARTER_MONTHLY_CREDITS', 'PRO_MONTHLY_CREDITS');

-- Step 2: 删除旧格式的 CREDITS_PER_* 配置
-- (这些已被 credits.cost.* 替代)
DELETE FROM system_configs 
WHERE config_key IN ('CREDITS_PER_OCR');

-- Step 3: 确保 credits.cost.* 配置存在且正确
-- OCR cost
INSERT INTO system_configs (config_key, config_value, value_type, config_group, description, is_public, is_editable)
VALUES ('credits.cost.ocr', '10', 'integer', 'credits', 'OCR recognition cost', true, true)
ON CONFLICT (config_key) DO UPDATE SET config_value = '10';

-- Smart scan cost
INSERT INTO system_configs (config_key, config_value, value_type, config_group, description, is_public, is_editable)
VALUES ('credits.cost.smart_scan', '10', 'integer', 'credits', 'Smart Scan/OCR cost', true, true)
ON CONFLICT (config_key) DO UPDATE SET config_value = '10';

-- Step 4: 验证清理结果
SELECT config_key, config_value, config_group, description
FROM system_configs
WHERE config_key LIKE 'tier.%monthly_credits%'
   OR config_key LIKE 'credits.cost.%'
   OR config_key IN ('STARTER_MONTHLY_CREDITS', 'PRO_MONTHLY_CREDITS', 'CREDITS_PER_OCR')
ORDER BY config_group, config_key;

-- 预期结果:
-- | config_key                     | config_value | config_group |
-- |-------------------------------|--------------|--------------|
-- | credits.cost.image_generation | 5            | credits      |
-- | credits.cost.ocr              | 10           | credits      |
-- | credits.cost.smart_scan       | 10           | credits      |
-- | credits.cost.text_generation  | 0            | credits      |
-- | tier.t1.monthly_credits       | 0            | tier         |
-- | tier.t2.monthly_credits       | 100          | tier         |
-- | tier.t3.monthly_credits       | 200          | tier         |
