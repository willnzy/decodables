-- ============================================================================
-- 修复脚本: 为所有 RLS 启用的表添加显式 service_role 策略
-- ============================================================================
-- 问题: 80 张表启用了 RLS 但没有创建任何 policy
--       Supabase 审计报 INFO: "RLS enabled but no policies exist"
-- 现状: 已经安全 (RLS 启用 + 无策略 = 拒绝非 service_role 访问)
-- 方案: 添加显式 service_role policy，使安全意图自文档化
-- 日期: 2026-01-30
-- ============================================================================

BEGIN;

-- ============================================================================
-- 01_core_business.sql 中的表 (35个)
-- ============================================================================
DROP POLICY IF EXISTS service_role_all ON profiles;
CREATE POLICY service_role_all ON profiles FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON asset_categories;
CREATE POLICY service_role_all ON asset_categories FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON workspaces;
CREATE POLICY service_role_all ON workspaces FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON folders;
CREATE POLICY service_role_all ON folders FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON legacy_system_tags;
CREATE POLICY service_role_all ON legacy_system_tags FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON tags;
CREATE POLICY service_role_all ON tags FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON tag_group_presets;
CREATE POLICY service_role_all ON tag_group_presets FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON projects;
CREATE POLICY service_role_all ON projects FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON project_pages;
CREATE POLICY service_role_all ON project_pages FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON marketplace_listings;
CREATE POLICY service_role_all ON marketplace_listings FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON assets;
CREATE POLICY service_role_all ON assets FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON legacy_asset_tag_relations;
CREATE POLICY service_role_all ON legacy_asset_tag_relations FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON project_tags;
CREATE POLICY service_role_all ON project_tags FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON user_asset_tags;
CREATE POLICY service_role_all ON user_asset_tags FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON workspace_members;
CREATE POLICY service_role_all ON workspace_members FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON workspace_invitations;
CREATE POLICY service_role_all ON workspace_invitations FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON user_recent_assets;
CREATE POLICY service_role_all ON user_recent_assets FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON user_favorite_assets;
CREATE POLICY service_role_all ON user_favorite_assets FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON project_versions;
CREATE POLICY service_role_all ON project_versions FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON user_asset_prompt_templates;
CREATE POLICY service_role_all ON user_asset_prompt_templates FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON credit_purchases;
CREATE POLICY service_role_all ON credit_purchases FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON credit_transactions;
CREATE POLICY service_role_all ON credit_transactions FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON generation_tasks;
CREATE POLICY service_role_all ON generation_tasks FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON listing_usages;
CREATE POLICY service_role_all ON listing_usages FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON marketplace_favorites;
CREATE POLICY service_role_all ON marketplace_favorites FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON marketplace_purchases;
CREATE POLICY service_role_all ON marketplace_purchases FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON marketplace_reviews;
CREATE POLICY service_role_all ON marketplace_reviews FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON user_page_prompt_templates;
CREATE POLICY service_role_all ON user_page_prompt_templates FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON subscription_history;
CREATE POLICY service_role_all ON subscription_history FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON system_assets;
CREATE POLICY service_role_all ON system_assets FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON system_resources;
CREATE POLICY service_role_all ON system_resources FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON user_discounts;
CREATE POLICY service_role_all ON user_discounts FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON user_generations;
CREATE POLICY service_role_all ON user_generations FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON system_error_logs;
CREATE POLICY service_role_all ON system_error_logs FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON user_creation_logs;
CREATE POLICY service_role_all ON user_creation_logs FOR ALL TO service_role USING (true) WITH CHECK (true);


-- ============================================================================
-- 02_platform_services.sql 中的表 (33个)
-- ============================================================================
DROP POLICY IF EXISTS service_role_all ON activity_logs;
CREATE POLICY service_role_all ON activity_logs FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON aggregated_stats;
CREATE POLICY service_role_all ON aggregated_stats FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON ai_usage_daily;
CREATE POLICY service_role_all ON ai_usage_daily FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON analytics_aggregation;
CREATE POLICY service_role_all ON analytics_aggregation FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON analytics_events;
CREATE POLICY service_role_all ON analytics_events FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON config_audit_logs;
CREATE POLICY service_role_all ON config_audit_logs FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON daily_metrics;
CREATE POLICY service_role_all ON daily_metrics FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON daily_themes;
CREATE POLICY service_role_all ON daily_themes FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON feature_flags;
CREATE POLICY service_role_all ON feature_flags FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON holidays;
CREATE POLICY service_role_all ON holidays FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON monthly_metrics;
CREATE POLICY service_role_all ON monthly_metrics FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON hourly_metrics;
CREATE POLICY service_role_all ON hourly_metrics FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON notifications;
CREATE POLICY service_role_all ON notifications FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON stripe_webhook_events;
CREATE POLICY service_role_all ON stripe_webhook_events FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON system_resource_audit_logs;
CREATE POLICY service_role_all ON system_resource_audit_logs FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON user_events;
CREATE POLICY service_role_all ON user_events FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON campaigns;
CREATE POLICY service_role_all ON campaigns FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON content_reports;
CREATE POLICY service_role_all ON content_reports FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON experiments;
CREATE POLICY service_role_all ON experiments FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON onboarding_steps;
CREATE POLICY service_role_all ON onboarding_steps FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON articles;
CREATE POLICY service_role_all ON articles FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON experiment_configs;
CREATE POLICY service_role_all ON experiment_configs FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON flag_exposures;
CREATE POLICY service_role_all ON flag_exposures FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON flag_audit_logs;
CREATE POLICY service_role_all ON flag_audit_logs FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON campaign_dismissals;
CREATE POLICY service_role_all ON campaign_dismissals FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON campaign_participations;
CREATE POLICY service_role_all ON campaign_participations FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON experiment_assignments;
CREATE POLICY service_role_all ON experiment_assignments FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON experiment_conversions;
CREATE POLICY service_role_all ON experiment_conversions FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON experiment_exposures;
CREATE POLICY service_role_all ON experiment_exposures FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON experiment_results;
CREATE POLICY service_role_all ON experiment_results FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON referrals;
CREATE POLICY service_role_all ON referrals FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON user_onboarding_progress;
CREATE POLICY service_role_all ON user_onboarding_progress FOR ALL TO service_role USING (true) WITH CHECK (true);


-- ============================================================================
-- 03_infrastructure.sql 中的表 (12个)
-- ============================================================================
DROP POLICY IF EXISTS service_role_all ON admin_operations;
CREATE POLICY service_role_all ON admin_operations FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON ai_call_logs;
CREATE POLICY service_role_all ON ai_call_logs FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON api_logs;
CREATE POLICY service_role_all ON api_logs FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON error_logs;
CREATE POLICY service_role_all ON error_logs FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON payment_records;
CREATE POLICY service_role_all ON payment_records FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON pricing_plans;
CREATE POLICY service_role_all ON pricing_plans FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON scheduled_task_logs;
CREATE POLICY service_role_all ON scheduled_task_logs FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON system_configs;
CREATE POLICY service_role_all ON system_configs FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON pricing_history;
CREATE POLICY service_role_all ON pricing_history FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON support_tickets;
CREATE POLICY service_role_all ON support_tickets FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON user_price_overrides;
CREATE POLICY service_role_all ON user_price_overrides FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS service_role_all ON support_replies;
CREATE POLICY service_role_all ON support_replies FOR ALL TO service_role USING (true) WITH CHECK (true);


COMMIT;

-- ============================================================================
-- 验证
-- ============================================================================
-- 检查所有表是否都有 policy:
-- SELECT t.tablename, COUNT(p.polname) as policy_count
-- FROM pg_tables t
-- LEFT JOIN pg_policy p ON p.polrelid = (t.schemaname || '.' || t.tablename)::regclass
-- WHERE t.schemaname = 'public'
-- GROUP BY t.tablename
-- HAVING COUNT(p.polname) = 0
-- ORDER BY t.tablename;
--
-- 应返回空结果 (所有表都有 policy)
