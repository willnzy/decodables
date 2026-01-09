-- ==============================================================================
-- Make Decodables Production Launch SQL Script
-- Version: v3.12
-- Purpose: Clean test data + Standardize database before production launch
-- 
-- ⚠️ WARNING: This script will DELETE ALL USER DATA!
-- Only run this ONCE before production launch.
-- 
-- Execution Order:
-- 1. Part 1: Data Cleanup (清空所有测试数据)
-- 2. Part 2: Schema Standardization (确保所有表结构正确)
-- 3. Part 3: Index Optimization (创建/更新索引)
-- 4. Part 4: RLS Policies (重新应用安全策略)
-- 5. Part 5: Views & Functions (重建视图和函数)
-- 6. Part 6: Triggers (重建触发器)
-- 7. Part 7: Default System Data (插入初始系统配置)
-- 8. Part 8: Verification (验证脚本)
-- ==============================================================================

-- ==============================================================================
-- Part 1: Data Cleanup (清空所有测试数据)
-- 按照外键依赖顺序删除，避免约束冲突
-- ==============================================================================

BEGIN;

-- 1.1 禁用触发器以加速删除（可选）
-- SET session_replication_role = replica;

-- 1.2 删除所有用户生成的数据 (按依赖顺序)

-- 日志和事件表（无外键依赖，先删）
TRUNCATE TABLE error_logs CASCADE;
TRUNCATE TABLE analytics_events CASCADE;
TRUNCATE TABLE user_events CASCADE;
TRUNCATE TABLE activity_logs CASCADE;
TRUNCATE TABLE admin_operation_logs CASCADE;

-- 聚合统计（可重建）
TRUNCATE TABLE aggregated_stats CASCADE;
TRUNCATE TABLE leaderboard_snapshots CASCADE;

-- 内容举报
TRUNCATE TABLE content_reports CASCADE;

-- 购买和使用记录
TRUNCATE TABLE listing_usages CASCADE;
TRUNCATE TABLE user_purchases CASCADE;

-- 资产和项目（有外键到 marketplace_listings）
TRUNCATE TABLE assets CASCADE;
TRUNCATE TABLE projects CASCADE;

-- 市场相关
TRUNCATE TABLE marketplace_listings CASCADE;

-- 用户相关数据
TRUNCATE TABLE credit_transactions CASCADE;
TRUNCATE TABLE user_discounts CASCADE;
TRUNCATE TABLE notifications CASCADE;
TRUNCATE TABLE support_tickets CASCADE;
TRUNCATE TABLE asset_prompt_templates CASCADE;
TRUNCATE TABLE page_prompt_templates CASCADE;

-- 最后删除用户表
TRUNCATE TABLE profiles CASCADE;

-- 1.3 重新启用触发器
-- SET session_replication_role = DEFAULT;

-- 1.4 重置序列（如果有的话）
-- UUID 主键不需要重置序列

COMMIT;

-- 验证数据已清空
SELECT 'profiles' as table_name, COUNT(*) as row_count FROM profiles
UNION ALL SELECT 'projects', COUNT(*) FROM projects
UNION ALL SELECT 'assets', COUNT(*) FROM assets
UNION ALL SELECT 'marketplace_listings', COUNT(*) FROM marketplace_listings
UNION ALL SELECT 'user_purchases', COUNT(*) FROM user_purchases
UNION ALL SELECT 'credit_transactions', COUNT(*) FROM credit_transactions;

-- ==============================================================================
-- Part 2: Schema Standardization (确保所有表结构正确)
-- 检查并添加可能缺失的列
-- ==============================================================================

-- 2.1 profiles 表标准化
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS timezone text DEFAULT 'UTC';
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS created_at_local timestamp without time zone;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS first_name text;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS last_name text;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS cohort_month text;

-- 2.2 projects 表标准化
ALTER TABLE projects ADD COLUMN IF NOT EXISTS timezone text DEFAULT 'UTC';
ALTER TABLE projects ADD COLUMN IF NOT EXISTS created_at_local timestamp without time zone;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS updated_at_local timestamp without time zone;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS is_hidden_from_trash boolean DEFAULT false;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS is_purchased boolean DEFAULT false;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS origin_owner_id text;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS listing_status text;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS marketplace_listing_id uuid;

-- 添加外键约束（如果不存在）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'projects_origin_owner_id_fkey'
    ) THEN
        ALTER TABLE projects ADD CONSTRAINT projects_origin_owner_id_fkey 
            FOREIGN KEY (origin_owner_id) REFERENCES profiles(id);
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'projects_marketplace_listing_id_fkey'
    ) THEN
        ALTER TABLE projects ADD CONSTRAINT projects_marketplace_listing_id_fkey 
            FOREIGN KEY (marketplace_listing_id) REFERENCES marketplace_listings(id);
    END IF;
END $$;

-- 2.3 assets 表标准化
ALTER TABLE assets ADD COLUMN IF NOT EXISTS timezone text DEFAULT 'UTC';
ALTER TABLE assets ADD COLUMN IF NOT EXISTS created_at_local timestamp without time zone;
ALTER TABLE assets ADD COLUMN IF NOT EXISTS is_hidden_from_trash boolean DEFAULT false;
ALTER TABLE assets ADD COLUMN IF NOT EXISTS deleted_at timestamp with time zone;
ALTER TABLE assets ADD COLUMN IF NOT EXISTS is_purchased boolean DEFAULT false;
ALTER TABLE assets ADD COLUMN IF NOT EXISTS origin_owner_id text;
ALTER TABLE assets ADD COLUMN IF NOT EXISTS listing_status text;
ALTER TABLE assets ADD COLUMN IF NOT EXISTS marketplace_listing_id uuid;
ALTER TABLE assets ADD COLUMN IF NOT EXISTS description text;

-- 2.4 marketplace_listings 表标准化
ALTER TABLE marketplace_listings ADD COLUMN IF NOT EXISTS timezone text DEFAULT 'UTC';
ALTER TABLE marketplace_listings ADD COLUMN IF NOT EXISTS created_at_local timestamp without time zone;
ALTER TABLE marketplace_listings ADD COLUMN IF NOT EXISTS resource_id uuid;
ALTER TABLE marketplace_listings ADD COLUMN IF NOT EXISTS version varchar(20) DEFAULT '1.0';
ALTER TABLE marketplace_listings ADD COLUMN IF NOT EXISTS changelog text DEFAULT '';
ALTER TABLE marketplace_listings ADD COLUMN IF NOT EXISTS version_history jsonb DEFAULT '[]'::jsonb;
ALTER TABLE marketplace_listings ADD COLUMN IF NOT EXISTS unique_buyers_count integer DEFAULT 0;
ALTER TABLE marketplace_listings ADD COLUMN IF NOT EXISTS total_revenue integer DEFAULT 0;

-- 2.5 user_purchases 表标准化
ALTER TABLE user_purchases ADD COLUMN IF NOT EXISTS timezone text DEFAULT 'UTC';
ALTER TABLE user_purchases ADD COLUMN IF NOT EXISTS purchased_at_local timestamp without time zone;
ALTER TABLE user_purchases ADD COLUMN IF NOT EXISTS idempotency_key text;
ALTER TABLE user_purchases ADD COLUMN IF NOT EXISTS snapshot_title text;
ALTER TABLE user_purchases ADD COLUMN IF NOT EXISTS snapshot_thumbnail_url text;
ALTER TABLE user_purchases ADD COLUMN IF NOT EXISTS snapshot_description text;
ALTER TABLE user_purchases ADD COLUMN IF NOT EXISTS snapshot_version text;
ALTER TABLE user_purchases ADD COLUMN IF NOT EXISTS snapshot_resource_type text;
ALTER TABLE user_purchases ADD COLUMN IF NOT EXISTS snapshot_resource_id uuid;
ALTER TABLE user_purchases ADD COLUMN IF NOT EXISTS utm_source text;
ALTER TABLE user_purchases ADD COLUMN IF NOT EXISTS utm_medium text;
ALTER TABLE user_purchases ADD COLUMN IF NOT EXISTS utm_campaign text;
ALTER TABLE user_purchases ADD COLUMN IF NOT EXISTS referral_context text;

-- 2.6 credit_transactions 表标准化
ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS timezone text DEFAULT 'UTC';
ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS created_at_local timestamp without time zone;
ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS idempotency_key text;

-- 2.7 其他表时区字段
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS timezone text DEFAULT 'UTC';
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS created_at_local timestamp without time zone;

ALTER TABLE content_reports ADD COLUMN IF NOT EXISTS timezone text DEFAULT 'UTC';
ALTER TABLE content_reports ADD COLUMN IF NOT EXISTS created_at_local timestamp without time zone;

ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS timezone text DEFAULT 'UTC';
ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS created_at_local timestamp without time zone;

ALTER TABLE admin_operation_logs ADD COLUMN IF NOT EXISTS timezone text DEFAULT 'UTC';
ALTER TABLE admin_operation_logs ADD COLUMN IF NOT EXISTS created_at_local timestamp without time zone;

ALTER TABLE user_events ADD COLUMN IF NOT EXISTS timezone text DEFAULT 'UTC';
ALTER TABLE user_events ADD COLUMN IF NOT EXISTS created_at_local timestamp without time zone;

ALTER TABLE analytics_events ADD COLUMN IF NOT EXISTS timezone text DEFAULT 'UTC';
ALTER TABLE analytics_events ADD COLUMN IF NOT EXISTS created_at_local timestamp without time zone;

ALTER TABLE error_logs ADD COLUMN IF NOT EXISTS timezone text DEFAULT 'UTC';
ALTER TABLE error_logs ADD COLUMN IF NOT EXISTS created_at_local timestamp without time zone;

-- ==============================================================================
-- Part 3: Index Optimization (创建/更新索引)
-- ==============================================================================

-- 3.1 Profiles indexes
CREATE INDEX IF NOT EXISTS idx_profiles_tier ON profiles(tier);
CREATE INDEX IF NOT EXISTS idx_profiles_created_at ON profiles(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_profiles_subscription_status ON profiles(subscription_status);
CREATE INDEX IF NOT EXISTS idx_profiles_cohort_month ON profiles(cohort_month);
CREATE INDEX IF NOT EXISTS idx_profiles_user_code ON profiles(user_code) WHERE user_code IS NOT NULL;

-- 3.2 Credit transactions indexes
CREATE INDEX IF NOT EXISTS idx_credit_tx_bucket ON credit_transactions(bucket);
CREATE INDEX IF NOT EXISTS idx_credit_tx_type ON credit_transactions(type);
CREATE INDEX IF NOT EXISTS idx_credit_tx_created_at ON credit_transactions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_credit_tx_user_id ON credit_transactions(user_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_transactions_idempotency 
    ON credit_transactions(idempotency_key) WHERE idempotency_key IS NOT NULL;

-- 3.3 Projects indexes
CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_projects_user_deleted ON projects(user_id, is_deleted, deleted_at);
CREATE INDEX IF NOT EXISTS idx_projects_user_purchased ON projects(user_id, is_purchased) WHERE is_purchased = true;
CREATE INDEX IF NOT EXISTS idx_projects_user_listing_status ON projects(user_id, listing_status) WHERE listing_status IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_projects_trash ON projects(user_id, is_deleted, is_hidden_from_trash) 
    WHERE is_deleted = true AND is_hidden_from_trash = false;
CREATE INDEX IF NOT EXISTS idx_projects_marketplace_listing ON projects(marketplace_listing_id) WHERE marketplace_listing_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_projects_deleted_at ON projects(deleted_at);

-- 3.4 Assets indexes
CREATE INDEX IF NOT EXISTS idx_assets_user_proj ON assets(user_id, project_id);
CREATE INDEX IF NOT EXISTS idx_assets_user_deleted ON assets(user_id, is_deleted);
CREATE INDEX IF NOT EXISTS idx_assets_user_purchased ON assets(user_id, is_purchased) WHERE is_purchased = true;
CREATE INDEX IF NOT EXISTS idx_assets_user_listing_status ON assets(user_id, listing_status) WHERE listing_status IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_assets_trash ON assets(user_id, is_deleted, is_hidden_from_trash)
    WHERE is_deleted = true AND is_hidden_from_trash = false;
CREATE INDEX IF NOT EXISTS idx_assets_marketplace_listing ON assets(marketplace_listing_id) WHERE marketplace_listing_id IS NOT NULL;

-- 3.5 Marketplace listings indexes
CREATE INDEX IF NOT EXISTS idx_listings_resource_id ON marketplace_listings(resource_id) WHERE resource_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_marketplace_listings_resource_id ON marketplace_listings(resource_id);
CREATE INDEX IF NOT EXISTS idx_listings_seller_public ON marketplace_listings(seller_id, is_public, is_deleted);
CREATE INDEX IF NOT EXISTS idx_marketplace_listings_version ON marketplace_listings(version);
CREATE INDEX IF NOT EXISTS idx_marketplace_listings_moderation ON marketplace_listings(moderation_status);

-- 3.6 User purchases indexes
CREATE UNIQUE INDEX IF NOT EXISTS idx_purchases_user_listing ON user_purchases(user_id, listing_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_purchases_idempotency 
    ON user_purchases(idempotency_key) WHERE idempotency_key IS NOT NULL;

-- 3.7 Analytics indexes
CREATE INDEX IF NOT EXISTS idx_analytics_events_user_id ON analytics_events(user_id);
CREATE INDEX IF NOT EXISTS idx_analytics_events_event_type ON analytics_events(event_type);
CREATE INDEX IF NOT EXISTS idx_analytics_events_created_at ON analytics_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analytics_events_session_id ON analytics_events(session_id);

-- 3.8 Error logs indexes
CREATE INDEX IF NOT EXISTS idx_error_logs_created_at ON error_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_error_logs_user_id ON error_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_error_logs_user_code ON error_logs(user_code);
CREATE INDEX IF NOT EXISTS idx_error_logs_error_type ON error_logs(error_type);
CREATE INDEX IF NOT EXISTS idx_error_logs_status_code ON error_logs(status_code);
CREATE INDEX IF NOT EXISTS idx_error_logs_endpoint ON error_logs(endpoint);

-- 3.9 Admin operation logs indexes
CREATE INDEX IF NOT EXISTS idx_admin_logs_created_at ON admin_operation_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_logs_operation_type ON admin_operation_logs(operation_type);
CREATE INDEX IF NOT EXISTS idx_admin_logs_admin_id ON admin_operation_logs(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_logs_target_user ON admin_operation_logs(target_user_id);

-- 3.10 User events indexes
CREATE INDEX IF NOT EXISTS idx_user_events_created_at ON user_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_events_event_type ON user_events(event_type);
CREATE INDEX IF NOT EXISTS idx_user_events_user_id ON user_events(user_id);
CREATE INDEX IF NOT EXISTS idx_user_events_session ON user_events(session_id);
CREATE INDEX IF NOT EXISTS idx_user_events_properties ON user_events USING gin(properties);

-- 3.11 Aggregated stats indexes
CREATE INDEX IF NOT EXISTS idx_agg_stats_date ON aggregated_stats(date DESC);
CREATE INDEX IF NOT EXISTS idx_agg_stats_type ON aggregated_stats(stat_type);
CREATE INDEX IF NOT EXISTS idx_agg_stats_date_type ON aggregated_stats(date DESC, stat_type);
CREATE UNIQUE INDEX IF NOT EXISTS idx_agg_stats_unique ON aggregated_stats(date, stat_type);

-- 3.12 System configs indexes
CREATE INDEX IF NOT EXISTS idx_system_configs_key ON system_configs(config_key);
CREATE INDEX IF NOT EXISTS idx_system_configs_category ON system_configs(category);

-- 3.13 Content reports indexes
CREATE INDEX IF NOT EXISTS idx_reports_status ON content_reports(status);
CREATE INDEX IF NOT EXISTS idx_reports_listing_id ON content_reports(listing_id);
CREATE INDEX IF NOT EXISTS idx_reports_reporter_id ON content_reports(reporter_id);
CREATE INDEX IF NOT EXISTS idx_reports_created_at ON content_reports(created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_reports_unique_user_listing 
    ON content_reports(reporter_id, listing_id) WHERE status IN ('pending', 'reviewed');

-- 3.14 Notifications indexes
CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(notification_type);
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at DESC);

-- 3.15 Activity logs indexes
CREATE INDEX IF NOT EXISTS idx_activity_logs_action ON activity_logs(action);
CREATE INDEX IF NOT EXISTS idx_activity_logs_created_at ON activity_logs(created_at DESC);

-- 3.16 Asset/Page prompt templates indexes
CREATE INDEX IF NOT EXISTS idx_asset_prompt_templates_user ON asset_prompt_templates(user_id);
CREATE INDEX IF NOT EXISTS idx_asset_prompt_templates_usage ON asset_prompt_templates(user_id, use_count DESC);
CREATE INDEX IF NOT EXISTS idx_page_prompt_templates_user ON page_prompt_templates(user_id);
CREATE INDEX IF NOT EXISTS idx_page_prompt_templates_usage ON page_prompt_templates(user_id, use_count DESC);

-- ==============================================================================
-- Part 4: RLS Policies (重新应用安全策略)
-- ==============================================================================

-- 4.1 启用 RLS
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_discounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE marketplace_listings ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_purchases ENABLE ROW LEVEL SECURITY;
ALTER TABLE assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_resources ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE listing_usages ENABLE ROW LEVEL SECURITY;
ALTER TABLE leaderboard_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_operation_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE error_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE aggregated_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE asset_prompt_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE page_prompt_templates ENABLE ROW LEVEL SECURITY;

-- 4.2 创建 is_admin 函数
CREATE OR REPLACE FUNCTION is_admin() RETURNS boolean 
LANGUAGE sql SECURITY DEFINER AS $$
SELECT EXISTS (
    SELECT 1 FROM profiles
    WHERE id = (SELECT auth.jwt() ->> 'sub') AND role = 'admin'
);
$$;

-- 4.3 Profiles policies
DROP POLICY IF EXISTS "View profiles" ON profiles;
CREATE POLICY "View profiles" ON profiles FOR SELECT
USING ((SELECT auth.jwt() ->> 'sub') = id OR is_admin());

DROP POLICY IF EXISTS "Update profiles" ON profiles;
CREATE POLICY "Update profiles" ON profiles FOR UPDATE
USING ((SELECT auth.jwt() ->> 'sub') = id);

DROP POLICY IF EXISTS "Insert profiles" ON profiles;
CREATE POLICY "Insert profiles" ON profiles FOR INSERT
WITH CHECK ((SELECT auth.jwt() ->> 'sub') = id);

-- 4.4 User Discounts policies
DROP POLICY IF EXISTS "Users read own discounts" ON user_discounts;
CREATE POLICY "Users read own discounts" ON user_discounts FOR SELECT
USING ((SELECT auth.jwt() ->> 'sub') = user_id OR is_admin());

-- 4.5 Projects policies
DROP POLICY IF EXISTS "Users can CRUD own projects" ON projects;
CREATE POLICY "Users can CRUD own projects" ON projects FOR ALL
USING ((SELECT auth.jwt() ->> 'sub') = user_id);

-- 4.6 Marketplace Listings policies
DROP POLICY IF EXISTS "Read Listings" ON marketplace_listings;
CREATE POLICY "Read Listings" ON marketplace_listings FOR SELECT
USING (is_public = true OR (SELECT auth.jwt() ->> 'sub') = seller_id OR is_admin());

DROP POLICY IF EXISTS "Manage Listings" ON marketplace_listings;
CREATE POLICY "Manage Listings" ON marketplace_listings FOR UPDATE
USING ((SELECT auth.jwt() ->> 'sub') = seller_id);

DROP POLICY IF EXISTS "Insert Listings" ON marketplace_listings;
CREATE POLICY "Insert Listings" ON marketplace_listings FOR INSERT
WITH CHECK ((SELECT auth.jwt() ->> 'sub') = seller_id);

-- 4.7 User Purchases policies
DROP POLICY IF EXISTS "Read Purchases" ON user_purchases;
CREATE POLICY "Read Purchases" ON user_purchases FOR SELECT
USING ((SELECT auth.jwt() ->> 'sub') = user_id);

DROP POLICY IF EXISTS "Insert Purchases" ON user_purchases;
CREATE POLICY "Insert Purchases" ON user_purchases FOR INSERT
WITH CHECK ((SELECT auth.jwt() ->> 'sub') = user_id);

-- 4.8 Assets policies
DROP POLICY IF EXISTS "Users can CRUD own assets" ON assets;
CREATE POLICY "Users can CRUD own assets" ON assets FOR ALL
USING ((SELECT auth.jwt() ->> 'sub') = user_id);

-- 4.9 Notifications policies
DROP POLICY IF EXISTS "Read Notifications" ON notifications;
CREATE POLICY "Read Notifications" ON notifications FOR SELECT
USING (user_id = (SELECT auth.jwt() ->> 'sub') OR user_id IS NULL);

-- 4.10 Credit Transactions policies
DROP POLICY IF EXISTS "Users view own txs or Admin view all" ON credit_transactions;
CREATE POLICY "Users view own txs or Admin view all" ON credit_transactions FOR SELECT
USING ((SELECT auth.jwt() ->> 'sub') = user_id OR is_admin());

-- 4.11 System Resources policies
DROP POLICY IF EXISTS "Public can view system resources" ON system_resources;
CREATE POLICY "Public can view system resources" ON system_resources FOR SELECT
USING (true);

-- 4.12 Activity Logs policies
DROP POLICY IF EXISTS "Users can insert own logs" ON activity_logs;
CREATE POLICY "Users can insert own logs" ON activity_logs FOR INSERT
WITH CHECK ((SELECT auth.jwt() ->> 'sub') = user_id);

DROP POLICY IF EXISTS "Users view own logs or Admin view all" ON activity_logs;
CREATE POLICY "Users view own logs or Admin view all" ON activity_logs FOR SELECT
USING ((SELECT auth.jwt() ->> 'sub') = user_id OR is_admin());

-- 4.13 Support Tickets policies
DROP POLICY IF EXISTS "Users CRUD own tickets or Admin manage all" ON support_tickets;
CREATE POLICY "Users CRUD own tickets or Admin manage all" ON support_tickets FOR ALL
USING ((SELECT auth.jwt() ->> 'sub') = user_id OR is_admin());

-- 4.14 Listing Usages policies
DROP POLICY IF EXISTS "Users can insert own usage" ON listing_usages;
CREATE POLICY "Users can insert own usage" ON listing_usages FOR INSERT
WITH CHECK ((SELECT auth.jwt() ->> 'sub') = used_by_user_id);

DROP POLICY IF EXISTS "Users view own usage or Admin view all" ON listing_usages;
CREATE POLICY "Users view own usage or Admin view all" ON listing_usages FOR SELECT
USING ((SELECT auth.jwt() ->> 'sub') = used_by_user_id OR is_admin());

-- 4.15 Leaderboard Snapshots policies
DROP POLICY IF EXISTS "Public can view leaderboard" ON leaderboard_snapshots;
CREATE POLICY "Public can view leaderboard" ON leaderboard_snapshots FOR SELECT
USING (true);

-- 4.16 Admin Operation Logs policies (service_role only)
DROP POLICY IF EXISTS "Service role full access to admin_logs" ON admin_operation_logs;
CREATE POLICY "Service role full access to admin_logs" ON admin_operation_logs FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- 4.17 User Events policies (service_role only)
DROP POLICY IF EXISTS "Service role full access to user_events" ON user_events;
CREATE POLICY "Service role full access to user_events" ON user_events FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- 4.18 Analytics Events policies (service_role only)
DROP POLICY IF EXISTS "Service role insert analytics events" ON analytics_events;
CREATE POLICY "Service role insert analytics events" ON analytics_events FOR INSERT
TO service_role
WITH CHECK (true);

DROP POLICY IF EXISTS "Service role read analytics events" ON analytics_events;
CREATE POLICY "Service role read analytics events" ON analytics_events FOR SELECT
TO service_role
USING (true);

-- 4.19 Error Logs policies
DROP POLICY IF EXISTS "Allow insert error logs" ON error_logs;
CREATE POLICY "Allow insert error logs" ON error_logs FOR INSERT
WITH CHECK (true);

DROP POLICY IF EXISTS "Service role read error logs" ON error_logs;
CREATE POLICY "Service role read error logs" ON error_logs FOR SELECT
TO service_role
USING (true);

-- 4.20 Aggregated Stats policies (service_role only)
DROP POLICY IF EXISTS "Service role full access to aggregated_stats" ON aggregated_stats;
CREATE POLICY "Service role full access to aggregated_stats" ON aggregated_stats FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- 4.21 System Configs policies (service_role only)
DROP POLICY IF EXISTS "Service role full access to system_configs" ON system_configs;
CREATE POLICY "Service role full access to system_configs" ON system_configs FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- 4.22 Content Reports policies
DROP POLICY IF EXISTS "Users can view own reports" ON content_reports;
CREATE POLICY "Users can view own reports" ON content_reports FOR SELECT
USING ((SELECT auth.jwt() ->> 'sub') = reporter_id);

DROP POLICY IF EXISTS "Users can create reports" ON content_reports;
CREATE POLICY "Users can create reports" ON content_reports FOR INSERT
WITH CHECK ((SELECT auth.jwt() ->> 'sub') = reporter_id);

DROP POLICY IF EXISTS "Admin can view all reports" ON content_reports;
CREATE POLICY "Admin can view all reports" ON content_reports FOR SELECT
USING (is_admin());

DROP POLICY IF EXISTS "Admin can update reports" ON content_reports;
CREATE POLICY "Admin can update reports" ON content_reports FOR UPDATE
USING (is_admin());

-- 4.23 Asset Prompt Templates policies (service_role only)
DROP POLICY IF EXISTS "Service role full access to asset prompt templates" ON asset_prompt_templates;
CREATE POLICY "Service role full access to asset prompt templates" ON asset_prompt_templates FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- 4.24 Page Prompt Templates policies (service_role only)
DROP POLICY IF EXISTS "Service role full access to page prompt templates" ON page_prompt_templates;
CREATE POLICY "Service role full access to page prompt templates" ON page_prompt_templates FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- ==============================================================================
-- Part 5: Views & Functions (重建视图和函数)
-- ==============================================================================

-- 5.1 Dashboard Projects View
DROP VIEW IF EXISTS dashboard_projects;
CREATE OR REPLACE VIEW dashboard_projects AS
SELECT 
    p.id,
    p.user_id,
    p.title,
    p.thumbnail_url,
    p.canvas_data,
    p.is_deleted,
    p.deleted_at,
    p.is_hidden_from_trash,
    p.is_purchased,
    p.source_listing_id,
    p.origin_owner_id,
    p.listing_status,
    p.marketplace_listing_id,
    p.contains_locked_elements,
    p.created_at,
    p.updated_at,
    ml.id as listing_id,
    ml.title as listing_title,
    ml.price_credits as listing_price,
    ml.is_public as listing_is_public,
    ml.moderation_status as listing_moderation_status,
    ml.sales_count as listing_sales_count,
    ml.unique_buyers_count as listing_unique_buyers,
    ml.total_revenue as listing_total_revenue,
    ml.usage_count as listing_usage_count,
    op.username as origin_owner_username,
    op.avatar_url as origin_owner_avatar
FROM projects p
LEFT JOIN marketplace_listings ml ON p.marketplace_listing_id = ml.id
LEFT JOIN profiles op ON p.origin_owner_id = op.id;

-- 5.2 Dashboard Assets View
DROP VIEW IF EXISTS dashboard_assets;
CREATE OR REPLACE VIEW dashboard_assets AS
SELECT 
    a.id,
    a.user_id,
    a.url,
    a.type,
    a.prompt,
    a.description,
    a.metadata,
    a.is_deleted,
    a.deleted_at,
    a.is_hidden_from_trash,
    a.is_purchased,
    a.source_listing_id,
    a.origin_owner_id,
    a.listing_status,
    a.marketplace_listing_id,
    a.project_id,
    a.created_at,
    ml.id as listing_id,
    ml.title as listing_title,
    ml.description as listing_description,
    ml.price_credits as listing_price,
    ml.is_public as listing_is_public,
    ml.moderation_status as listing_moderation_status,
    ml.sales_count as listing_sales_count,
    ml.unique_buyers_count as listing_unique_buyers,
    ml.total_revenue as listing_total_revenue,
    ml.usage_count as listing_usage_count,
    op.username as origin_owner_username,
    op.avatar_url as origin_owner_avatar
FROM assets a
LEFT JOIN marketplace_listings ml ON a.marketplace_listing_id = ml.id
LEFT JOIN profiles op ON a.origin_owner_id = op.id;

-- 5.3 Seller Stats Summary View
DROP VIEW IF EXISTS seller_stats_summary;
CREATE OR REPLACE VIEW seller_stats_summary AS
SELECT 
    seller_id,
    COUNT(*) as total_listings,
    SUM(CASE WHEN is_public = true AND moderation_status = 'approved' THEN 1 ELSE 0 END) as active_listings,
    SUM(sales_count) as total_sales,
    SUM(unique_buyers_count) as total_unique_buyers,
    SUM(total_revenue) as total_revenue,
    SUM(usage_count) as total_usage
FROM marketplace_listings
WHERE is_deleted = false
GROUP BY seller_id;

-- 5.4 Helper Functions

-- Get rate limit config
CREATE OR REPLACE FUNCTION get_rate_limit_config(p_config_key TEXT)
RETURNS JSONB AS $$
DECLARE
    v_config JSONB;
BEGIN
    SELECT config_value INTO v_config
    FROM system_configs
    WHERE config_key = p_config_key AND is_active = true;
    
    IF v_config IS NULL THEN
        SELECT config_value INTO v_config
        FROM system_configs
        WHERE config_key = 'rate_limit.global.default' AND is_active = true;
    END IF;
    
    RETURN COALESCE(v_config, '{"limit": 100, "window": "minute", "enabled": true}'::JSONB);
END;
$$ LANGUAGE plpgsql;

-- Get latest stats
CREATE OR REPLACE FUNCTION get_latest_stats(p_stat_type VARCHAR)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT data INTO result
    FROM aggregated_stats
    WHERE stat_type = p_stat_type
    ORDER BY date DESC
    LIMIT 1;
    
    RETURN COALESCE(result, '{}'::JSONB);
END;
$$;

-- Get stats range
CREATE OR REPLACE FUNCTION get_stats_range(
    p_stat_type VARCHAR,
    p_start_date DATE,
    p_end_date DATE DEFAULT CURRENT_DATE
)
RETURNS TABLE (
    date DATE,
    data JSONB
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT a.date, a.data
    FROM aggregated_stats a
    WHERE a.stat_type = p_stat_type
      AND a.date >= p_start_date
      AND a.date <= p_end_date
    ORDER BY a.date ASC;
END;
$$;

-- ==============================================================================
-- Part 6: Triggers (重建触发器)
-- ==============================================================================

-- 6.1 Sync listing status to projects/assets
CREATE OR REPLACE FUNCTION sync_listing_status()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.resource_type = 'project' AND NEW.resource_id IS NOT NULL THEN
        UPDATE projects 
        SET 
            listing_status = NEW.moderation_status,
            marketplace_listing_id = NEW.id
        WHERE id = NEW.resource_id::uuid;
    END IF;
    
    IF NEW.resource_type = 'asset' AND NEW.resource_id IS NOT NULL THEN
        UPDATE assets 
        SET 
            listing_status = NEW.moderation_status,
            marketplace_listing_id = NEW.id
        WHERE id = NEW.resource_id::uuid;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_sync_listing_status ON marketplace_listings;
CREATE TRIGGER trigger_sync_listing_status
    AFTER INSERT OR UPDATE OF moderation_status, is_public, is_deleted
    ON marketplace_listings
    FOR EACH ROW
    EXECUTE FUNCTION sync_listing_status();

-- 6.2 Update seller stats after purchase
CREATE OR REPLACE FUNCTION update_seller_stats_on_purchase()
RETURNS TRIGGER AS $$
DECLARE
    v_listing_price INT;
    v_seller_revenue INT;
BEGIN
    SELECT price_credits INTO v_listing_price
    FROM marketplace_listings
    WHERE id = NEW.listing_id;
    
    v_seller_revenue := FLOOR(v_listing_price * 0.9);
    
    UPDATE marketplace_listings
    SET 
        sales_count = sales_count + 1,
        unique_buyers_count = (
            SELECT COUNT(DISTINCT user_id) 
            FROM user_purchases 
            WHERE listing_id = NEW.listing_id
        ),
        total_revenue = total_revenue + v_seller_revenue
    WHERE id = NEW.listing_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_seller_stats ON user_purchases;
CREATE TRIGGER trigger_update_seller_stats
    AFTER INSERT ON user_purchases
    FOR EACH ROW
    EXECUTE FUNCTION update_seller_stats_on_purchase();

-- 6.3 Set deleted_at timestamp on soft delete
CREATE OR REPLACE FUNCTION set_deleted_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_deleted = true AND OLD.is_deleted = false THEN
        NEW.deleted_at = NOW();
    END IF;
    IF NEW.is_deleted = false AND OLD.is_deleted = true THEN
        NEW.deleted_at = NULL;
        NEW.is_hidden_from_trash = false;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_projects_deleted_at ON projects;
CREATE TRIGGER trigger_projects_deleted_at
    BEFORE UPDATE OF is_deleted ON projects
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_timestamp();

DROP TRIGGER IF EXISTS trigger_assets_deleted_at ON assets;
CREATE TRIGGER trigger_assets_deleted_at
    BEFORE UPDATE OF is_deleted ON assets
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_timestamp();

-- 6.4 Append-only constraint for credit_transactions
CREATE OR REPLACE FUNCTION prevent_credit_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'credit_transactions is append-only. For refunds, insert a negative amount record.';
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS prevent_credit_update ON credit_transactions;
CREATE TRIGGER prevent_credit_update
    BEFORE UPDATE ON credit_transactions
    FOR EACH ROW
    EXECUTE FUNCTION prevent_credit_modification();

DROP TRIGGER IF EXISTS prevent_credit_delete ON credit_transactions;
CREATE TRIGGER prevent_credit_delete
    BEFORE DELETE ON credit_transactions
    FOR EACH ROW
    EXECUTE FUNCTION prevent_credit_modification();

-- 6.5 Auto-update updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_reports_updated_at ON content_reports;
CREATE TRIGGER trigger_reports_updated_at
    BEFORE UPDATE ON content_reports
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_timestamp();

DROP TRIGGER IF EXISTS trigger_asset_prompt_templates_updated_at ON asset_prompt_templates;
CREATE TRIGGER trigger_asset_prompt_templates_updated_at
    BEFORE UPDATE ON asset_prompt_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_timestamp();

DROP TRIGGER IF EXISTS trigger_page_prompt_templates_updated_at ON page_prompt_templates;
CREATE TRIGGER trigger_page_prompt_templates_updated_at
    BEFORE UPDATE ON page_prompt_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_timestamp();

DROP TRIGGER IF EXISTS trigger_system_configs_updated_at ON system_configs;
CREATE TRIGGER trigger_system_configs_updated_at
    BEFORE UPDATE ON system_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_timestamp();

-- ==============================================================================
-- Part 7: Default System Data (插入初始系统配置)
-- ==============================================================================

-- 7.1 Rate limit configurations
INSERT INTO system_configs (config_key, config_value, category, description) VALUES
-- Payments (high risk, strict limits)
('rate_limit.payment.checkout', '{"limit": 5, "window": "minute", "enabled": true}', 'rate_limit', 'Checkout API limit'),
('rate_limit.payment.portal', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', 'Billing portal limit'),
('rate_limit.marketplace.purchase', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', 'Marketplace purchase limit'),
-- AI generation (resource intensive)
('rate_limit.generate.story', '{"limit": 20, "window": "minute", "enabled": true}', 'rate_limit', 'AI story generation limit'),
('rate_limit.generate.images', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', 'AI image generation limit'),
('rate_limit.tools.ocr', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', 'OCR limit'),
-- Export operations (resource heavy)
('rate_limit.export.pdf', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', 'PDF export limit'),
('rate_limit.export.zip', '{"limit": 5, "window": "minute", "enabled": true}', 'rate_limit', 'ZIP export limit'),
('rate_limit.export.preview', '{"limit": 20, "window": "minute", "enabled": true}', 'rate_limit', 'Preview generation limit'),
-- User operations
('rate_limit.projects.create', '{"limit": 20, "window": "minute", "enabled": true}', 'rate_limit', 'Project creation limit'),
('rate_limit.assets.upload', '{"limit": 20, "window": "minute", "enabled": true}', 'rate_limit', 'Asset upload limit'),
('rate_limit.marketplace.publish', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', 'Listing publish limit'),
-- Public endpoints (abuse protection)
('rate_limit.support.email', '{"limit": 3, "window": "minute", "enabled": true}', 'rate_limit', 'Support ticket limit'),
('rate_limit.contact.form', '{"limit": 3, "window": "minute", "enabled": true}', 'rate_limit', 'Contact form limit'),
('rate_limit.feedback.submit', '{"limit": 3, "window": "minute", "enabled": true}', 'rate_limit', 'Feedback submission limit'),
-- Admin operations
('rate_limit.admin.credits', '{"limit": 30, "window": "minute", "enabled": true}', 'rate_limit', 'Admin credit adjustment limit'),
('rate_limit.admin.tier', '{"limit": 30, "window": "minute", "enabled": true}', 'rate_limit', 'Admin tier update limit'),
('rate_limit.admin.refund', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', 'Admin refund limit'),
('rate_limit.admin.subscription', '{"limit": 10, "window": "minute", "enabled": true}', 'rate_limit', 'Admin subscription ops limit'),
('rate_limit.admin.broadcast', '{"limit": 5, "window": "minute", "enabled": true}', 'rate_limit', 'Admin broadcast limit'),
-- Query endpoints
('rate_limit.admin.search', '{"limit": 60, "window": "minute", "enabled": true}', 'rate_limit', 'Admin search limit'),
('rate_limit.marketplace.list', '{"limit": 60, "window": "minute", "enabled": true}', 'rate_limit', 'Marketplace listing limit'),
('rate_limit.analytics.events', '{"limit": 60, "window": "minute", "enabled": true}', 'rate_limit', 'Analytics event ingestion limit'),
-- Global defaults
('rate_limit.global.default', '{"limit": 100, "window": "minute", "enabled": true}', 'rate_limit', 'Global default limit'),
('rate_limit.global.enabled', '{"enabled": true}', 'rate_limit', 'Enable/disable global rate limit'),
-- Analytics configuration
('analytics.enabled', '{"enabled": true}', 'analytics', 'Enable analytics tracking'),
('analytics.sampling_rate', '{"critical": 1.0, "important": 1.0, "normal": 0.3, "debug": 0.0}', 'analytics', 'Event sampling rates'),
('analytics.min_level', '{"level": "normal"}', 'analytics', 'Minimum tracking level')
ON CONFLICT (config_key) DO NOTHING;

-- ==============================================================================
-- Part 8: Verification (验证脚本)
-- ==============================================================================

-- 8.1 验证表结构
SELECT 
    'Tables' as check_type,
    COUNT(*) as count,
    string_agg(tablename, ', ') as items
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN (
    'profiles', 'projects', 'assets', 'marketplace_listings', 
    'user_purchases', 'credit_transactions', 'notifications',
    'system_configs', 'analytics_events', 'error_logs'
);

-- 8.2 验证索引
SELECT 
    'Indexes' as check_type,
    COUNT(*) as count
FROM pg_indexes 
WHERE schemaname = 'public';

-- 8.3 验证 RLS 策略
SELECT 
    'RLS Policies' as check_type,
    COUNT(*) as count
FROM pg_policies 
WHERE schemaname = 'public';

-- 8.4 验证视图
SELECT 
    'Views' as check_type,
    COUNT(*) as count,
    string_agg(viewname, ', ') as items
FROM pg_views 
WHERE schemaname = 'public';

-- 8.5 验证触发器
SELECT 
    'Triggers' as check_type,
    COUNT(*) as count
FROM information_schema.triggers 
WHERE trigger_schema = 'public';

-- 8.6 验证 system_configs 数据
SELECT 
    'System Configs' as check_type,
    COUNT(*) as count
FROM system_configs;

-- 8.7 验证数据已清空
SELECT 
    'User Data Cleared' as check_type,
    CASE 
        WHEN (SELECT COUNT(*) FROM profiles) = 0 THEN 'YES' 
        ELSE 'NO - ' || (SELECT COUNT(*) FROM profiles)::text || ' profiles remain'
    END as status;

-- ==============================================================================
-- End of Production Launch Script
-- ==============================================================================

-- 显示完成信息
SELECT '✅ Production launch SQL script completed successfully!' as message;
SELECT 'Next steps:' as message
UNION ALL SELECT '1. Verify all checks above passed'
UNION ALL SELECT '2. Create admin user manually or via first login'
UNION ALL SELECT '3. Upload system resources (stickers, templates)'
UNION ALL SELECT '4. Test critical paths (signup, generation, export, payment)';
