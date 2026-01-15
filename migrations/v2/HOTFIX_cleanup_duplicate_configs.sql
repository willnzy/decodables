-- =============================================================================
-- HOTFIX: 清理 system_configs 表中的重复/过时 Credits 配置
-- =============================================================================
-- 背景:
-- 1. system_configs 中曾存在重复的月度积分配置
-- 2. 配置键已从 STARTER_*/PRO_* 重命名为 T2_*/T3_*
-- 3. 此脚本清理旧的配置键
--
-- 删除的配置键:
--   - STARTER_MONTHLY_CREDITS (已重命名为 T2_MONTHLY_CREDITS)
--   - PRO_MONTHLY_CREDITS (已重命名为 T3_MONTHLY_CREDITS)
--   - STARTER_PLAN_PRICE (已重命名为 T2_PLAN_PRICE)
--   - PRO_PLAN_PRICE (已重命名为 T3_PLAN_PRICE)
--   - CREDITS_PER_OCR (使用 credits.cost.ocr)
--
-- 当前正确配置 (数据库权威):
-- | config_key                | config_value | config_group |
-- |---------------------------|--------------|--------------|
-- | tier.t2.monthly_credits   | 100          | tier         |
-- | tier.t3.monthly_credits   | 200          | tier         |
-- | T2_MONTHLY_CREDITS        | 100          | pricing      |
-- | T3_MONTHLY_CREDITS        | 200          | pricing      |
-- =============================================================================

-- 删除旧的 STARTER/PRO 配置键 (如果存在)
DELETE FROM system_configs 
WHERE config_key IN (
    'STARTER_MONTHLY_CREDITS',
    'PRO_MONTHLY_CREDITS',
    'STARTER_PLAN_PRICE',
    'STARTER_PLAN_ORIGINAL_PRICE',
    'PRO_PLAN_PRICE',
    'PRO_PLAN_ORIGINAL_PRICE',
    'PRO_CREDITS_DISCOUNT_PERCENT',
    'CREDITS_PER_OCR'
);

-- 验证清理结果
SELECT config_key, config_value, config_group
FROM system_configs 
WHERE config_key LIKE '%STARTER%' 
   OR config_key LIKE '%PRO_%'
   OR config_key = 'CREDITS_PER_OCR';

-- 预期结果: 空 (所有旧配置已删除)
