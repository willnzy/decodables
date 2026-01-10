-- ============================================================
-- Phase 3.2: 为软删除表添加恢复期过期字段
-- ============================================================
-- 创建时间: 2026-01-10
-- 目标: 为已有软删除的 22 张表添加 recovery_expires_at 字段
-- 业务需求: 用户删除内容后,30天(可配置)恢复期内可找回,过期后从删除历史中消失
--
-- 影响表:
--   Phase 2 已完成 (14张):
--     1-4: profiles, projects, project_versions, assets
--     5-8: marketplace_listings, asset_categories, system_assets, notifications
--     9-12: campaign_participations, campaign_dismissals, onboarding_steps, user_onboarding_progress
--     13-14: referrals, credit_transactions
--
--   Phase 3.1 已完成 (8张):
--     15-18: marketplace_favorites, marketplace_reviews, campaigns, daily_themes
--     19-22: holidays, asset_prompt_templates, support_tickets, support_replies
--
-- 新增字段: recovery_expires_at TIMESTAMPTZ
-- 业务逻辑: recovery_expires_at = deleted_at + 配置天数 (默认30天)
-- ============================================================

BEGIN;

-- ============================================================
-- 1. 添加系统配置: 恢复期天数
-- ============================================================

INSERT INTO system_configs (config_key, config_value, description, created_at, updated_at)
VALUES (
    'recovery_period_days',
    '30',
    '软删除恢复期天数,过期后用户无法在删除历史中看到记录',
    NOW(),
    NOW()
)
ON CONFLICT (config_key) DO NOTHING;

-- ============================================================
-- 2. Phase 2 已完成的表 (14张)
-- ============================================================

-- 2.1 profiles - 用户资料
ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS recovery_expires_at TIMESTAMPTZ;

ALTER TABLE profiles
ADD CONSTRAINT chk_profiles_recovery_expires_at_consistency
CHECK (
    recovery_expires_at IS NULL OR
    (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
);

CREATE INDEX idx_profiles_deleted_recoverable
ON profiles(id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON COLUMN profiles.recovery_expires_at IS '恢复期截止时间,过期后用户看不到此删除记录';

-- 2.2 projects - 项目
ALTER TABLE projects
ADD COLUMN IF NOT EXISTS recovery_expires_at TIMESTAMPTZ;

ALTER TABLE projects
ADD CONSTRAINT chk_projects_recovery_expires_at_consistency
CHECK (
    recovery_expires_at IS NULL OR
    (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
);

CREATE INDEX idx_projects_user_deleted_recoverable
ON projects(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON COLUMN projects.recovery_expires_at IS '恢复期截止时间,过期后用户看不到此删除记录';

-- 2.3 project_versions - 项目版本
ALTER TABLE project_versions
ADD COLUMN IF NOT EXISTS recovery_expires_at TIMESTAMPTZ;

ALTER TABLE project_versions
ADD CONSTRAINT chk_project_versions_recovery_expires_at_consistency
CHECK (
    recovery_expires_at IS NULL OR
    (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
);

CREATE INDEX idx_project_versions_project_deleted_recoverable
ON project_versions(project_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON COLUMN project_versions.recovery_expires_at IS '恢复期截止时间,过期后用户看不到此删除记录';

-- 2.4 assets - 素材
ALTER TABLE assets
ADD COLUMN IF NOT EXISTS recovery_expires_at TIMESTAMPTZ;

ALTER TABLE assets
ADD CONSTRAINT chk_assets_recovery_expires_at_consistency
CHECK (
    recovery_expires_at IS NULL OR
    (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
);

CREATE INDEX idx_assets_user_deleted_recoverable
ON assets(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON COLUMN assets.recovery_expires_at IS '恢复期截止时间,过期后用户看不到此删除记录';

-- 2.5 marketplace_listings - 市场商品
ALTER TABLE marketplace_listings
ADD COLUMN IF NOT EXISTS recovery_expires_at TIMESTAMPTZ;

ALTER TABLE marketplace_listings
ADD CONSTRAINT chk_marketplace_listings_recovery_expires_at_consistency
CHECK (
    recovery_expires_at IS NULL OR
    (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
);

CREATE INDEX idx_marketplace_listings_seller_deleted_recoverable
ON marketplace_listings(seller_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON COLUMN marketplace_listings.recovery_expires_at IS '恢复期截止时间,过期后卖家看不到此删除记录';

-- 2.6 asset_categories - 素材分类
ALTER TABLE asset_categories
ADD COLUMN IF NOT EXISTS recovery_expires_at TIMESTAMPTZ;

ALTER TABLE asset_categories
ADD CONSTRAINT chk_asset_categories_recovery_expires_at_consistency
CHECK (
    recovery_expires_at IS NULL OR
    (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
);

CREATE INDEX idx_asset_categories_deleted_recoverable
ON asset_categories(category_name, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON COLUMN asset_categories.recovery_expires_at IS '恢复期截止时间,过期后管理员看不到此删除记录';

-- 2.7 system_assets - 系统素材
ALTER TABLE system_assets
ADD COLUMN IF NOT EXISTS recovery_expires_at TIMESTAMPTZ;

ALTER TABLE system_assets
ADD CONSTRAINT chk_system_assets_recovery_expires_at_consistency
CHECK (
    recovery_expires_at IS NULL OR
    (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
);

CREATE INDEX idx_system_assets_category_deleted_recoverable
ON system_assets(category_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON COLUMN system_assets.recovery_expires_at IS '恢复期截止时间,过期后管理员看不到此删除记录';

-- 2.8 notifications - 通知
ALTER TABLE notifications
ADD COLUMN IF NOT EXISTS recovery_expires_at TIMESTAMPTZ;

ALTER TABLE notifications
ADD CONSTRAINT chk_notifications_recovery_expires_at_consistency
CHECK (
    recovery_expires_at IS NULL OR
    (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
);

CREATE INDEX idx_notifications_user_deleted_recoverable
ON notifications(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON COLUMN notifications.recovery_expires_at IS '恢复期截止时间,过期后用户看不到此删除记录';

-- 2.9 campaign_participations - 营销活动参与
ALTER TABLE campaign_participations
ADD COLUMN IF NOT EXISTS recovery_expires_at TIMESTAMPTZ;

ALTER TABLE campaign_participations
ADD CONSTRAINT chk_campaign_participations_recovery_expires_at_consistency
CHECK (
    recovery_expires_at IS NULL OR
    (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
);

CREATE INDEX idx_campaign_participations_user_deleted_recoverable
ON campaign_participations(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON COLUMN campaign_participations.recovery_expires_at IS '恢复期截止时间,过期后用户看不到此删除记录';

-- 2.10 campaign_dismissals - 营销活动忽略
ALTER TABLE campaign_dismissals
ADD COLUMN IF NOT EXISTS recovery_expires_at TIMESTAMPTZ;

ALTER TABLE campaign_dismissals
ADD CONSTRAINT chk_campaign_dismissals_recovery_expires_at_consistency
CHECK (
    recovery_expires_at IS NULL OR
    (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
);

CREATE INDEX idx_campaign_dismissals_user_deleted_recoverable
ON campaign_dismissals(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON COLUMN campaign_dismissals.recovery_expires_at IS '恢复期截止时间,过期后用户看不到此删除记录';

-- 2.11 onboarding_steps - 引导步骤
ALTER TABLE onboarding_steps
ADD COLUMN IF NOT EXISTS recovery_expires_at TIMESTAMPTZ;

ALTER TABLE onboarding_steps
ADD CONSTRAINT chk_onboarding_steps_recovery_expires_at_consistency
CHECK (
    recovery_expires_at IS NULL OR
    (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
);

CREATE INDEX idx_onboarding_steps_deleted_recoverable
ON onboarding_steps(step_order, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON COLUMN onboarding_steps.recovery_expires_at IS '恢复期截止时间,过期后管理员看不到此删除记录';

-- 2.12 user_onboarding_progress - 用户引导进度
ALTER TABLE user_onboarding_progress
ADD COLUMN IF NOT EXISTS recovery_expires_at TIMESTAMPTZ;

ALTER TABLE user_onboarding_progress
ADD CONSTRAINT chk_user_onboarding_progress_recovery_expires_at_consistency
CHECK (
    recovery_expires_at IS NULL OR
    (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
);

CREATE INDEX idx_user_onboarding_progress_user_deleted_recoverable
ON user_onboarding_progress(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON COLUMN user_onboarding_progress.recovery_expires_at IS '恢复期截止时间,过期后用户看不到此删除记录';

-- 2.13 referrals - 推荐记录
ALTER TABLE referrals
ADD COLUMN IF NOT EXISTS recovery_expires_at TIMESTAMPTZ;

ALTER TABLE referrals
ADD CONSTRAINT chk_referrals_recovery_expires_at_consistency
CHECK (
    recovery_expires_at IS NULL OR
    (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
);

CREATE INDEX idx_referrals_referrer_deleted_recoverable
ON referrals(referrer_user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON COLUMN referrals.recovery_expires_at IS '恢复期截止时间,过期后用户看不到此删除记录';

-- 2.14 credit_transactions - 积分交易
ALTER TABLE credit_transactions
ADD COLUMN IF NOT EXISTS recovery_expires_at TIMESTAMPTZ;

ALTER TABLE credit_transactions
ADD CONSTRAINT chk_credit_transactions_recovery_expires_at_consistency
CHECK (
    recovery_expires_at IS NULL OR
    (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
);

CREATE INDEX idx_credit_transactions_user_deleted_recoverable
ON credit_transactions(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON COLUMN credit_transactions.recovery_expires_at IS '恢复期截止时间,过期后用户看不到此删除记录';

-- ============================================================
-- 3. Phase 3.1 已完成的表 (8张)
-- ============================================================

-- 3.1 marketplace_favorites - 市场收藏
ALTER TABLE marketplace_favorites
ADD COLUMN IF NOT EXISTS recovery_expires_at TIMESTAMPTZ;

ALTER TABLE marketplace_favorites
ADD CONSTRAINT chk_marketplace_favorites_recovery_expires_at_consistency
CHECK (
    recovery_expires_at IS NULL OR
    (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
);

CREATE INDEX idx_marketplace_favorites_user_deleted_recoverable
ON marketplace_favorites(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON COLUMN marketplace_favorites.recovery_expires_at IS '恢复期截止时间,过期后用户看不到此删除记录';

-- 3.2 marketplace_reviews - 市场评价
ALTER TABLE marketplace_reviews
ADD COLUMN IF NOT EXISTS recovery_expires_at TIMESTAMPTZ;

ALTER TABLE marketplace_reviews
ADD CONSTRAINT chk_marketplace_reviews_recovery_expires_at_consistency
CHECK (
    recovery_expires_at IS NULL OR
    (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
);

CREATE INDEX idx_marketplace_reviews_user_deleted_recoverable
ON marketplace_reviews(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON COLUMN marketplace_reviews.recovery_expires_at IS '恢复期截止时间,过期后用户看不到此删除记录';

-- 3.3 campaigns - 营销活动
ALTER TABLE campaigns
ADD COLUMN IF NOT EXISTS recovery_expires_at TIMESTAMPTZ;

ALTER TABLE campaigns
ADD CONSTRAINT chk_campaigns_recovery_expires_at_consistency
CHECK (
    recovery_expires_at IS NULL OR
    (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
);

CREATE INDEX idx_campaigns_deleted_recoverable
ON campaigns(campaign_type, deleted_at DESC)
WHERE is_deleted = true AND is_permanently_deleted = false AND recovery_expires_at > NOW();

COMMENT ON COLUMN campaigns.recovery_expires_at IS '恢复期截止时间,过期后管理员看不到此删除记录';

-- 3.4 daily_themes - 每日主题
ALTER TABLE daily_themes
ADD COLUMN IF NOT EXISTS recovery_expires_at TIMESTAMPTZ;

ALTER TABLE daily_themes
ADD CONSTRAINT chk_daily_themes_recovery_expires_at_consistency
CHECK (
    recovery_expires_at IS NULL OR
    (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
);

CREATE INDEX idx_daily_themes_deleted_recoverable
ON daily_themes(theme_date DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON COLUMN daily_themes.recovery_expires_at IS '恢复期截止时间,过期后管理员看不到此删除记录';

-- 3.5 holidays - 节假日
ALTER TABLE holidays
ADD COLUMN IF NOT EXISTS recovery_expires_at TIMESTAMPTZ;

ALTER TABLE holidays
ADD CONSTRAINT chk_holidays_recovery_expires_at_consistency
CHECK (
    recovery_expires_at IS NULL OR
    (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
);

CREATE INDEX idx_holidays_deleted_recoverable
ON holidays(holiday_date DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON COLUMN holidays.recovery_expires_at IS '恢复期截止时间,过期后管理员看不到此删除记录';

-- 3.6 asset_prompt_templates - 资源提示模板
ALTER TABLE asset_prompt_templates
ADD COLUMN IF NOT EXISTS recovery_expires_at TIMESTAMPTZ;

ALTER TABLE asset_prompt_templates
ADD CONSTRAINT chk_asset_prompt_templates_recovery_expires_at_consistency
CHECK (
    recovery_expires_at IS NULL OR
    (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
);

CREATE INDEX idx_asset_prompt_templates_deleted_recoverable
ON asset_prompt_templates(category, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON COLUMN asset_prompt_templates.recovery_expires_at IS '恢复期截止时间,过期后管理员看不到此删除记录';

-- 3.7 support_tickets - 支持工单
ALTER TABLE support_tickets
ADD COLUMN IF NOT EXISTS recovery_expires_at TIMESTAMPTZ;

ALTER TABLE support_tickets
ADD CONSTRAINT chk_support_tickets_recovery_expires_at_consistency
CHECK (
    recovery_expires_at IS NULL OR
    (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
);

CREATE INDEX idx_support_tickets_user_deleted_recoverable
ON support_tickets(user_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON COLUMN support_tickets.recovery_expires_at IS '恢复期截止时间,过期后用户看不到此删除记录';

-- 3.8 support_replies - 工单回复
ALTER TABLE support_replies
ADD COLUMN IF NOT EXISTS recovery_expires_at TIMESTAMPTZ;

ALTER TABLE support_replies
ADD CONSTRAINT chk_support_replies_recovery_expires_at_consistency
CHECK (
    recovery_expires_at IS NULL OR
    (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
);

CREATE INDEX idx_support_replies_ticket_deleted_recoverable
ON support_replies(ticket_id, deleted_at DESC)
WHERE is_deleted = true AND recovery_expires_at > NOW();

COMMENT ON COLUMN support_replies.recovery_expires_at IS '恢复期截止时间,过期后用户看不到此删除记录';

-- ============================================================
-- 4. 数据迁移: 为已有软删除记录计算恢复期
-- ============================================================

-- 对于已有的软删除记录,自动计算 recovery_expires_at
-- recovery_expires_at = deleted_at + 30 天

DO $$
DECLARE
    table_name TEXT;
    update_count INT;
    total_updated INT := 0;
BEGIN
    FOR table_name IN
        SELECT unnest(ARRAY[
            'profiles', 'projects', 'project_versions', 'assets',
            'marketplace_listings', 'asset_categories', 'system_assets', 'notifications',
            'campaign_participations', 'campaign_dismissals', 'onboarding_steps', 'user_onboarding_progress',
            'referrals', 'credit_transactions',
            'marketplace_favorites', 'marketplace_reviews', 'campaigns', 'daily_themes',
            'holidays', 'asset_prompt_templates', 'support_tickets', 'support_replies'
        ])
    LOOP
        EXECUTE format('
            UPDATE %I
            SET recovery_expires_at = deleted_at + INTERVAL ''30 days''
            WHERE is_deleted = true
              AND deleted_at IS NOT NULL
              AND recovery_expires_at IS NULL
        ', table_name);

        GET DIAGNOSTICS update_count = ROW_COUNT;
        total_updated := total_updated + update_count;

        IF update_count > 0 THEN
            RAISE NOTICE 'Updated % records in table %', update_count, table_name;
        END IF;
    END LOOP;

    RAISE NOTICE '✅ Migration complete. Total % records updated with recovery_expires_at', total_updated;
END $$;

-- ============================================================
-- 5. 验证迁移结果
-- ============================================================

DO $$
DECLARE
    table_name TEXT;
    missing_tables TEXT[] := ARRAY[]::TEXT[];
    column_exists BOOLEAN;
BEGIN
    FOR table_name IN
        SELECT unnest(ARRAY[
            'profiles', 'projects', 'project_versions', 'assets',
            'marketplace_listings', 'asset_categories', 'system_assets', 'notifications',
            'campaign_participations', 'campaign_dismissals', 'onboarding_steps', 'user_onboarding_progress',
            'referrals', 'credit_transactions',
            'marketplace_favorites', 'marketplace_reviews', 'campaigns', 'daily_themes',
            'holidays', 'asset_prompt_templates', 'support_tickets', 'support_replies'
        ])
    LOOP
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = table_name
            AND column_name = 'recovery_expires_at'
        ) INTO column_exists;

        IF NOT column_exists THEN
            missing_tables := array_append(missing_tables, table_name);
        END IF;
    END LOOP;

    IF array_length(missing_tables, 1) > 0 THEN
        RAISE EXCEPTION 'Migration incomplete. Missing recovery_expires_at in tables: %', missing_tables;
    ELSE
        RAISE NOTICE '✅ Phase 3.2 migration completed successfully. All 22 tables have recovery_expires_at field.';
    END IF;
END $$;

COMMIT;

-- ============================================================
-- 回滚脚本 (如需回滚, 执行以下命令)
-- ============================================================
-- BEGIN;
--
-- -- 删除系统配置
-- DELETE FROM system_configs WHERE config_key = 'recovery_period_days';
--
-- -- Phase 2 表 (14张)
-- ALTER TABLE profiles DROP CONSTRAINT IF EXISTS chk_profiles_recovery_expires_at_consistency, DROP COLUMN IF EXISTS recovery_expires_at;
-- DROP INDEX IF EXISTS idx_profiles_deleted_recoverable;
--
-- ALTER TABLE projects DROP CONSTRAINT IF EXISTS chk_projects_recovery_expires_at_consistency, DROP COLUMN IF EXISTS recovery_expires_at;
-- DROP INDEX IF EXISTS idx_projects_user_deleted_recoverable;
--
-- ALTER TABLE project_versions DROP CONSTRAINT IF EXISTS chk_project_versions_recovery_expires_at_consistency, DROP COLUMN IF EXISTS recovery_expires_at;
-- DROP INDEX IF EXISTS idx_project_versions_project_deleted_recoverable;
--
-- ALTER TABLE assets DROP CONSTRAINT IF EXISTS chk_assets_recovery_expires_at_consistency, DROP COLUMN IF EXISTS recovery_expires_at;
-- DROP INDEX IF EXISTS idx_assets_user_deleted_recoverable;
--
-- ALTER TABLE marketplace_listings DROP CONSTRAINT IF EXISTS chk_marketplace_listings_recovery_expires_at_consistency, DROP COLUMN IF EXISTS recovery_expires_at;
-- DROP INDEX IF EXISTS idx_marketplace_listings_seller_deleted_recoverable;
--
-- ALTER TABLE asset_categories DROP CONSTRAINT IF EXISTS chk_asset_categories_recovery_expires_at_consistency, DROP COLUMN IF EXISTS recovery_expires_at;
-- DROP INDEX IF EXISTS idx_asset_categories_deleted_recoverable;
--
-- ALTER TABLE system_assets DROP CONSTRAINT IF EXISTS chk_system_assets_recovery_expires_at_consistency, DROP COLUMN IF EXISTS recovery_expires_at;
-- DROP INDEX IF EXISTS idx_system_assets_category_deleted_recoverable;
--
-- ALTER TABLE notifications DROP CONSTRAINT IF EXISTS chk_notifications_recovery_expires_at_consistency, DROP COLUMN IF EXISTS recovery_expires_at;
-- DROP INDEX IF EXISTS idx_notifications_user_deleted_recoverable;
--
-- ALTER TABLE campaign_participations DROP CONSTRAINT IF EXISTS chk_campaign_participations_recovery_expires_at_consistency, DROP COLUMN IF EXISTS recovery_expires_at;
-- DROP INDEX IF EXISTS idx_campaign_participations_user_deleted_recoverable;
--
-- ALTER TABLE campaign_dismissals DROP CONSTRAINT IF EXISTS chk_campaign_dismissals_recovery_expires_at_consistency, DROP COLUMN IF EXISTS recovery_expires_at;
-- DROP INDEX IF EXISTS idx_campaign_dismissals_user_deleted_recoverable;
--
-- ALTER TABLE onboarding_steps DROP CONSTRAINT IF EXISTS chk_onboarding_steps_recovery_expires_at_consistency, DROP COLUMN IF EXISTS recovery_expires_at;
-- DROP INDEX IF EXISTS idx_onboarding_steps_deleted_recoverable;
--
-- ALTER TABLE user_onboarding_progress DROP CONSTRAINT IF EXISTS chk_user_onboarding_progress_recovery_expires_at_consistency, DROP COLUMN IF EXISTS recovery_expires_at;
-- DROP INDEX IF EXISTS idx_user_onboarding_progress_user_deleted_recoverable;
--
-- ALTER TABLE referrals DROP CONSTRAINT IF EXISTS chk_referrals_recovery_expires_at_consistency, DROP COLUMN IF EXISTS recovery_expires_at;
-- DROP INDEX IF EXISTS idx_referrals_referrer_deleted_recoverable;
--
-- ALTER TABLE credit_transactions DROP CONSTRAINT IF EXISTS chk_credit_transactions_recovery_expires_at_consistency, DROP COLUMN IF EXISTS recovery_expires_at;
-- DROP INDEX IF EXISTS idx_credit_transactions_user_deleted_recoverable;
--
-- -- Phase 3.1 表 (8张)
-- ALTER TABLE marketplace_favorites DROP CONSTRAINT IF EXISTS chk_marketplace_favorites_recovery_expires_at_consistency, DROP COLUMN IF EXISTS recovery_expires_at;
-- DROP INDEX IF EXISTS idx_marketplace_favorites_user_deleted_recoverable;
--
-- ALTER TABLE marketplace_reviews DROP CONSTRAINT IF EXISTS chk_marketplace_reviews_recovery_expires_at_consistency, DROP COLUMN IF EXISTS recovery_expires_at;
-- DROP INDEX IF EXISTS idx_marketplace_reviews_user_deleted_recoverable;
--
-- ALTER TABLE campaigns DROP CONSTRAINT IF EXISTS chk_campaigns_recovery_expires_at_consistency, DROP COLUMN IF EXISTS recovery_expires_at;
-- DROP INDEX IF EXISTS idx_campaigns_deleted_recoverable;
--
-- ALTER TABLE daily_themes DROP CONSTRAINT IF EXISTS chk_daily_themes_recovery_expires_at_consistency, DROP COLUMN IF EXISTS recovery_expires_at;
-- DROP INDEX IF EXISTS idx_daily_themes_deleted_recoverable;
--
-- ALTER TABLE holidays DROP CONSTRAINT IF EXISTS chk_holidays_recovery_expires_at_consistency, DROP COLUMN IF EXISTS recovery_expires_at;
-- DROP INDEX IF EXISTS idx_holidays_deleted_recoverable;
--
-- ALTER TABLE asset_prompt_templates DROP CONSTRAINT IF EXISTS chk_asset_prompt_templates_recovery_expires_at_consistency, DROP COLUMN IF EXISTS recovery_expires_at;
-- DROP INDEX IF EXISTS idx_asset_prompt_templates_deleted_recoverable;
--
-- ALTER TABLE support_tickets DROP CONSTRAINT IF EXISTS chk_support_tickets_recovery_expires_at_consistency, DROP COLUMN IF EXISTS recovery_expires_at;
-- DROP INDEX IF EXISTS idx_support_tickets_user_deleted_recoverable;
--
-- ALTER TABLE support_replies DROP CONSTRAINT IF EXISTS chk_support_replies_recovery_expires_at_consistency, DROP COLUMN IF EXISTS recovery_expires_at;
-- DROP INDEX IF EXISTS idx_support_replies_ticket_deleted_recoverable;
--
-- COMMIT;
