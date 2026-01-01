-- =====================================================
-- 数据库优化迁移：快照 + 幂等性 + 审计 + 分析
-- =====================================================
-- Version: 3.4
-- Date: 2026-01-01
-- 
-- 包含以下优化：
-- 1. 快照字段 - 防止商品信息"时空错乱"
-- 2. 幂等性 - 防止重复购买/扣款
-- 3. Append-Only 约束 - 财务审计合规
-- 4. 来源追踪 - 用户行为分析
-- 5. 用户分群 - 留存率分析
-- =====================================================

-- ==========================================
-- 1. user_purchases 添加快照字段
-- ==========================================
-- 作用：保存购买时刻的商品信息，防止卖家修改后影响买家已购列表显示

ALTER TABLE user_purchases ADD COLUMN IF NOT EXISTS snapshot_title text;
ALTER TABLE user_purchases ADD COLUMN IF NOT EXISTS snapshot_thumbnail_url text;
ALTER TABLE user_purchases ADD COLUMN IF NOT EXISTS snapshot_description text;
ALTER TABLE user_purchases ADD COLUMN IF NOT EXISTS snapshot_version text;
ALTER TABLE user_purchases ADD COLUMN IF NOT EXISTS snapshot_resource_type text;
ALTER TABLE user_purchases ADD COLUMN IF NOT EXISTS snapshot_resource_id uuid;

-- ==========================================
-- 2. 幂等性字段
-- ==========================================
-- 作用：防止用户重复点击或网络重试导致的重复购买/扣款

ALTER TABLE user_purchases ADD COLUMN IF NOT EXISTS idempotency_key text;
ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS idempotency_key text;

-- 创建唯一索引（允许 NULL，只约束非空值）
CREATE UNIQUE INDEX IF NOT EXISTS idx_purchases_idempotency 
ON user_purchases(idempotency_key) WHERE idempotency_key IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_transactions_idempotency 
ON credit_transactions(idempotency_key) WHERE idempotency_key IS NOT NULL;

-- ==========================================
-- 3. 来源追踪字段
-- ==========================================
-- 作用：分析用户从哪里来的（首页推荐、搜索、外部广告等）

ALTER TABLE user_purchases ADD COLUMN IF NOT EXISTS utm_source text;
ALTER TABLE user_purchases ADD COLUMN IF NOT EXISTS utm_medium text;
ALTER TABLE user_purchases ADD COLUMN IF NOT EXISTS utm_campaign text;
ALTER TABLE user_purchases ADD COLUMN IF NOT EXISTS referral_context text; -- 'homepage', 'search', 'category', 'direct_link'

-- ==========================================
-- 4. 用户分群字段
-- ==========================================
-- 作用：用于留存率分析（按注册月份分群）

ALTER TABLE profiles ADD COLUMN IF NOT EXISTS cohort_month text; -- 格式: '2026-01'

-- 回填现有用户的 cohort_month
UPDATE profiles 
SET cohort_month = TO_CHAR(created_at, 'YYYY-MM')
WHERE cohort_month IS NULL;

-- ==========================================
-- 5. 回填历史购买数据的快照
-- ==========================================

UPDATE user_purchases up
SET 
    snapshot_title = ml.title,
    snapshot_thumbnail_url = ml.thumbnail_url,
    snapshot_description = ml.description,
    snapshot_version = COALESCE(ml.version, '1.0'),
    snapshot_resource_type = ml.resource_type,
    snapshot_resource_id = ml.resource_id
FROM marketplace_listings ml
WHERE up.listing_id = ml.id
  AND up.snapshot_title IS NULL;

-- ==========================================
-- 6. Append-Only 约束 (财务审计)
-- ==========================================
-- 作用：禁止修改或删除 credit_transactions 记录
-- 退款通过插入负数金额的新记录实现

CREATE OR REPLACE FUNCTION prevent_credit_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'credit_transactions is append-only. For refunds, insert a negative amount record.';
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- 禁止 UPDATE
DROP TRIGGER IF EXISTS prevent_credit_update ON credit_transactions;
CREATE TRIGGER prevent_credit_update
    BEFORE UPDATE ON credit_transactions
    FOR EACH ROW
    EXECUTE FUNCTION prevent_credit_modification();

-- 禁止 DELETE
DROP TRIGGER IF EXISTS prevent_credit_delete ON credit_transactions;
CREATE TRIGGER prevent_credit_delete
    BEFORE DELETE ON credit_transactions
    FOR EACH ROW
    EXECUTE FUNCTION prevent_credit_modification();

-- ==========================================
-- 7. 签名 URL 支持 (可选 - 需要 Supabase Storage 配置)
-- ==========================================
-- 注意：这部分主要是 RLS 策略，需要根据实际情况配置
-- 以下是示例 RLS 策略模板

-- 对于 assets 存储桶的访问控制：
-- CREATE POLICY "Allow read for owners or purchasers" ON storage.objects
-- FOR SELECT USING (
--     bucket_id = 'generated-images' AND (
--         -- 资源所有者
--         (storage.foldername(name))[1] = auth.uid()::text
--         OR
--         -- 购买者（通过 user_purchases 验证）
--         EXISTS (
--             SELECT 1 FROM user_purchases up
--             JOIN marketplace_listings ml ON up.listing_id = ml.id
--             WHERE up.user_id = auth.uid()::text
--             AND ml.resource_url = name
--         )
--     )
-- );

-- ==========================================
-- 8. 验证迁移结果
-- ==========================================

-- 检查快照字段
SELECT 
    'user_purchases' as table_name,
    COUNT(*) as total,
    COUNT(snapshot_title) as has_snapshot,
    COUNT(*) - COUNT(snapshot_title) as missing_snapshot
FROM user_purchases;

-- 检查 cohort_month
SELECT 
    cohort_month,
    COUNT(*) as user_count
FROM profiles
WHERE cohort_month IS NOT NULL
GROUP BY cohort_month
ORDER BY cohort_month DESC
LIMIT 10;

-- 检查幂等性索引
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename IN ('user_purchases', 'credit_transactions')
AND indexname LIKE '%idempotency%';
