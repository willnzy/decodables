-- ============================================================
-- Phase 3.1: 为核心业务表添加软删除字段 (P0 - 8张表)
-- ============================================================
-- 创建时间: 2026-01-10
-- 目标: 将8张核心业务表添加软删除支持
-- 影响表:
--   1. marketplace_favorites - 市场收藏
--   2. marketplace_reviews - 市场评价
--   3. campaigns - 营销活动
--   4. daily_themes - 每日主题
--   5. holidays - 节假日
--   6. asset_prompt_templates - 资源提示模板
--   7. support_tickets - 支持工单
--   8. support_replies - 工单回复
--
-- 策略: 添加 is_deleted, deleted_at 字段 + 条件索引
-- ============================================================

BEGIN;

-- ============================================================
-- 1. marketplace_favorites - 市场收藏
-- ============================================================

ALTER TABLE marketplace_favorites
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- 添加约束: 确保 deleted_at 与 is_deleted 一致性
ALTER TABLE marketplace_favorites
ADD CONSTRAINT chk_marketplace_favorites_deleted_at_consistency
CHECK ((is_deleted = false AND deleted_at IS NULL) OR (is_deleted = true AND deleted_at IS NOT NULL));

-- 条件索引: 查询活跃收藏时排除已删除
CREATE INDEX idx_marketplace_favorites_active
ON marketplace_favorites(user_id, listing_id, created_at DESC)
WHERE is_deleted = false;

-- 添加注释
COMMENT ON COLUMN marketplace_favorites.is_deleted IS '软删除标记';
COMMENT ON COLUMN marketplace_favorites.deleted_at IS '删除时间';

-- ============================================================
-- 2. marketplace_reviews - 市场评价
-- ============================================================

ALTER TABLE marketplace_reviews
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

ALTER TABLE marketplace_reviews
ADD CONSTRAINT chk_marketplace_reviews_deleted_at_consistency
CHECK ((is_deleted = false AND deleted_at IS NULL) OR (is_deleted = true AND deleted_at IS NOT NULL));

-- 条件索引: 查询商品评价时排除已删除
CREATE INDEX idx_marketplace_reviews_active
ON marketplace_reviews(listing_id, created_at DESC)
WHERE is_deleted = false;

-- 用户评价索引
CREATE INDEX idx_marketplace_reviews_user_active
ON marketplace_reviews(user_id, created_at DESC)
WHERE is_deleted = false;

COMMENT ON COLUMN marketplace_reviews.is_deleted IS '软删除标记';
COMMENT ON COLUMN marketplace_reviews.deleted_at IS '删除时间';

-- ============================================================
-- 3. campaigns - 营销活动
-- ============================================================

ALTER TABLE campaigns
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS is_permanently_deleted BOOLEAN DEFAULT false;

ALTER TABLE campaigns
ADD CONSTRAINT chk_campaigns_deleted_at_consistency
CHECK ((is_deleted = false AND deleted_at IS NULL) OR (is_deleted = true AND deleted_at IS NOT NULL));

-- 条件索引: 查询活跃活动
CREATE INDEX idx_campaigns_active
ON campaigns(status, start_date DESC)
WHERE is_deleted = false AND is_permanently_deleted = false;

-- 按类型查询活动
CREATE INDEX idx_campaigns_type_active
ON campaigns(campaign_type, created_at DESC)
WHERE is_deleted = false;

COMMENT ON COLUMN campaigns.is_deleted IS '软删除标记 (30天内可恢复)';
COMMENT ON COLUMN campaigns.deleted_at IS '删除时间';
COMMENT ON COLUMN campaigns.is_permanently_deleted IS '永久删除标记 (不可恢复)';

-- ============================================================
-- 4. daily_themes - 每日主题
-- ============================================================

ALTER TABLE daily_themes
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

ALTER TABLE daily_themes
ADD CONSTRAINT chk_daily_themes_deleted_at_consistency
CHECK ((is_deleted = false AND deleted_at IS NULL) OR (is_deleted = true AND deleted_at IS NOT NULL));

-- 条件索引: 按日期查询活跃主题
CREATE INDEX idx_daily_themes_active
ON daily_themes(theme_date DESC)
WHERE is_deleted = false;

COMMENT ON COLUMN daily_themes.is_deleted IS '软删除标记';
COMMENT ON COLUMN daily_themes.deleted_at IS '删除时间';

-- ============================================================
-- 5. holidays - 节假日
-- ============================================================

ALTER TABLE holidays
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

ALTER TABLE holidays
ADD CONSTRAINT chk_holidays_deleted_at_consistency
CHECK ((is_deleted = false AND deleted_at IS NULL) OR (is_deleted = true AND deleted_at IS NOT NULL));

-- 条件索引: 按日期查询活跃节假日
CREATE INDEX idx_holidays_active
ON holidays(holiday_date DESC)
WHERE is_deleted = false;

-- 按国家/地区查询
CREATE INDEX idx_holidays_country_active
ON holidays(country, holiday_date DESC)
WHERE is_deleted = false;

COMMENT ON COLUMN holidays.is_deleted IS '软删除标记';
COMMENT ON COLUMN holidays.deleted_at IS '删除时间';

-- ============================================================
-- 6. asset_prompt_templates - 资源提示模板
-- ============================================================

ALTER TABLE asset_prompt_templates
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

ALTER TABLE asset_prompt_templates
ADD CONSTRAINT chk_asset_prompt_templates_deleted_at_consistency
CHECK ((is_deleted = false AND deleted_at IS NULL) OR (is_deleted = true AND deleted_at IS NOT NULL));

-- 条件索引: 按分类查询活跃模板
CREATE INDEX idx_asset_prompt_templates_active
ON asset_prompt_templates(category, created_at DESC)
WHERE is_deleted = false;

COMMENT ON COLUMN asset_prompt_templates.is_deleted IS '软删除标记';
COMMENT ON COLUMN asset_prompt_templates.deleted_at IS '删除时间';

-- ============================================================
-- 7. support_tickets - 支持工单
-- ============================================================

ALTER TABLE support_tickets
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

ALTER TABLE support_tickets
ADD CONSTRAINT chk_support_tickets_deleted_at_consistency
CHECK ((is_deleted = false AND deleted_at IS NULL) OR (is_deleted = true AND deleted_at IS NOT NULL));

-- 条件索引: 查询用户工单
CREATE INDEX idx_support_tickets_user_active
ON support_tickets(user_id, created_at DESC)
WHERE is_deleted = false;

-- 按状态查询工单
CREATE INDEX idx_support_tickets_status_active
ON support_tickets(status, created_at DESC)
WHERE is_deleted = false;

COMMENT ON COLUMN support_tickets.is_deleted IS '软删除标记';
COMMENT ON COLUMN support_tickets.deleted_at IS '删除时间';

-- ============================================================
-- 8. support_replies - 工单回复
-- ============================================================

ALTER TABLE support_replies
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

ALTER TABLE support_replies
ADD CONSTRAINT chk_support_replies_deleted_at_consistency
CHECK ((is_deleted = false AND deleted_at IS NULL) OR (is_deleted = true AND deleted_at IS NOT NULL));

-- 条件索引: 查询工单的回复
CREATE INDEX idx_support_replies_ticket_active
ON support_replies(ticket_id, created_at)
WHERE is_deleted = false;

COMMENT ON COLUMN support_replies.is_deleted IS '软删除标记';
COMMENT ON COLUMN support_replies.deleted_at IS '删除时间';

-- ============================================================
-- 验证迁移结果
-- ============================================================

-- 验证所有表都添加了字段
DO $$
DECLARE
    table_name TEXT;
    missing_tables TEXT[] := ARRAY[]::TEXT[];
BEGIN
    FOR table_name IN
        SELECT unnest(ARRAY[
            'marketplace_favorites',
            'marketplace_reviews',
            'campaigns',
            'daily_themes',
            'holidays',
            'asset_prompt_templates',
            'support_tickets',
            'support_replies'
        ])
    LOOP
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = table_name
            AND column_name = 'is_deleted'
        ) THEN
            missing_tables := array_append(missing_tables, table_name);
        END IF;
    END LOOP;

    IF array_length(missing_tables, 1) > 0 THEN
        RAISE EXCEPTION 'Migration incomplete. Missing is_deleted in tables: %', missing_tables;
    ELSE
        RAISE NOTICE '✅ Phase 3.1 migration completed successfully. All 8 tables have soft delete support.';
    END IF;
END $$;

COMMIT;

-- ============================================================
-- 回滚脚本 (如需回滚, 执行以下命令)
-- ============================================================
-- BEGIN;
--
-- ALTER TABLE marketplace_favorites
--     DROP CONSTRAINT IF EXISTS chk_marketplace_favorites_deleted_at_consistency,
--     DROP COLUMN IF EXISTS is_deleted,
--     DROP COLUMN IF EXISTS deleted_at;
-- DROP INDEX IF EXISTS idx_marketplace_favorites_active;
--
-- ALTER TABLE marketplace_reviews
--     DROP CONSTRAINT IF EXISTS chk_marketplace_reviews_deleted_at_consistency,
--     DROP COLUMN IF EXISTS is_deleted,
--     DROP COLUMN IF EXISTS deleted_at;
-- DROP INDEX IF EXISTS idx_marketplace_reviews_active;
-- DROP INDEX IF EXISTS idx_marketplace_reviews_user_active;
--
-- ALTER TABLE campaigns
--     DROP CONSTRAINT IF EXISTS chk_campaigns_deleted_at_consistency,
--     DROP COLUMN IF EXISTS is_deleted,
--     DROP COLUMN IF EXISTS deleted_at,
--     DROP COLUMN IF EXISTS is_permanently_deleted;
-- DROP INDEX IF EXISTS idx_campaigns_active;
-- DROP INDEX IF EXISTS idx_campaigns_type_active;
--
-- ALTER TABLE daily_themes
--     DROP CONSTRAINT IF EXISTS chk_daily_themes_deleted_at_consistency,
--     DROP COLUMN IF EXISTS is_deleted,
--     DROP COLUMN IF EXISTS deleted_at;
-- DROP INDEX IF EXISTS idx_daily_themes_active;
--
-- ALTER TABLE holidays
--     DROP CONSTRAINT IF EXISTS chk_holidays_deleted_at_consistency,
--     DROP COLUMN IF EXISTS is_deleted,
--     DROP COLUMN IF EXISTS deleted_at;
-- DROP INDEX IF EXISTS idx_holidays_active;
-- DROP INDEX IF EXISTS idx_holidays_country_active;
--
-- ALTER TABLE asset_prompt_templates
--     DROP CONSTRAINT IF EXISTS chk_asset_prompt_templates_deleted_at_consistency,
--     DROP COLUMN IF EXISTS is_deleted,
--     DROP COLUMN IF EXISTS deleted_at;
-- DROP INDEX IF EXISTS idx_asset_prompt_templates_active;
--
-- ALTER TABLE support_tickets
--     DROP CONSTRAINT IF EXISTS chk_support_tickets_deleted_at_consistency,
--     DROP COLUMN IF EXISTS is_deleted,
--     DROP COLUMN IF EXISTS deleted_at;
-- DROP INDEX IF EXISTS idx_support_tickets_user_active;
-- DROP INDEX IF EXISTS idx_support_tickets_status_active;
--
-- ALTER TABLE support_replies
--     DROP CONSTRAINT IF EXISTS chk_support_replies_deleted_at_consistency,
--     DROP COLUMN IF EXISTS is_deleted,
--     DROP COLUMN IF EXISTS deleted_at;
-- DROP INDEX IF EXISTS idx_support_replies_ticket_active;
--
-- COMMIT;
