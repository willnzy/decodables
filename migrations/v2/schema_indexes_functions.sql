-- ============================================================================
-- Make Decodables - 索引和函数
-- ============================================================================
-- 生成时间: 2026-01-10
-- 来源: refactored_schema_v2.sql
-- PostgreSQL 版本: 15+
-- ============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;

CREATE OR REPLACE FUNCTION set_deleted_at_on_soft_delete()
RETURNS TRIGGER AS $$
BEGIN
    -- INSERT 操作时 OLD 为 NULL,直接返回
    IF OLD IS NULL THEN
        RETURN NEW;
    END IF;

    -- UPDATE 操作: 检查 is_deleted 字段变化
    IF NEW.is_deleted = TRUE AND OLD.is_deleted = FALSE THEN
        NEW.deleted_at = CURRENT_TIMESTAMP;
    ELSIF NEW.is_deleted = FALSE THEN
        NEW.deleted_at = NULL;
    END IF;
    RETURN NEW;
END;

CREATE OR REPLACE FUNCTION prevent_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Table % is append-only. UPDATE and DELETE operations are not allowed.', TG_TABLE_NAME;
END;

CREATE OR REPLACE FUNCTION log_pricing_plan_change()
RETURNS TRIGGER AS $$
DECLARE
    v_action TEXT;
    v_old_data JSONB;
    v_new_data JSONB;
BEGIN
    -- 确定操作类型
    IF (TG_OP = 'INSERT') THEN
        v_action := 'create';
        v_old_data := NULL;
        v_new_data := row_to_json(NEW)::jsonb;
    ELSIF (TG_OP = 'UPDATE') THEN
        -- 判断具体更新类型
        IF (OLD.price_cents IS DISTINCT FROM NEW.price_cents OR
            OLD.original_price_cents IS DISTINCT FROM NEW.original_price_cents) THEN
            v_action := 'update_price';
        ELSIF (OLD.is_active IS DISTINCT FROM NEW.is_active) THEN
            v_action := CASE WHEN NEW.is_active THEN 'activate' ELSE 'deactivate' END;

CREATE INDEX idx_profiles_deleted_recoverable

CREATE INDEX idx_profiles_user_code ON profiles(user_code);

CREATE INDEX idx_profiles_stripe_customer_id ON profiles(stripe_customer_id) WHERE stripe_customer_id IS NOT NULL;

CREATE INDEX idx_profiles_tier ON profiles(tier);

CREATE INDEX idx_profiles_subscription_status ON profiles(subscription_status);

CREATE INDEX idx_profiles_created_at ON profiles(created_at);

CREATE INDEX idx_profiles_active ON profiles(is_deleted) WHERE is_deleted = FALSE;

CREATE INDEX idx_profiles_ext_json ON profiles USING GIN(ext_json);

CREATE TRIGGER trg_profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_profiles_soft_delete
    BEFORE UPDATE ON profiles
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();

CREATE INDEX idx_credit_transactions_deleted_recoverable

CREATE INDEX idx_credit_tx_user_id ON credit_transactions(user_id);

CREATE INDEX idx_credit_tx_user_created ON credit_transactions(user_id, created_at DESC);

CREATE INDEX idx_credit_tx_user_type_time ON credit_transactions(user_id, transaction_type, created_at DESC);  -- Composite index for filtered queries

CREATE INDEX idx_credit_tx_type ON credit_transactions(transaction_type);

CREATE INDEX idx_credit_tx_bucket ON credit_transactions(bucket);

CREATE INDEX idx_credit_tx_created_at ON credit_transactions(created_at DESC);

CREATE INDEX idx_credit_tx_metadata ON credit_transactions USING GIN(metadata);

CREATE UNIQUE INDEX idx_credit_tx_idempotency ON credit_transactions(idempotency_key) WHERE idempotency_key IS NOT NULL;

CREATE TRIGGER trg_credit_tx_prevent_modification
    BEFORE UPDATE OR DELETE ON credit_transactions
    FOR EACH ROW
    EXECUTE FUNCTION prevent_modification();

CREATE INDEX idx_projects_deleted_recoverable

CREATE INDEX idx_projects_user_id ON projects(user_id);

CREATE INDEX idx_projects_user_created ON projects(user_id, created_at DESC);

CREATE INDEX idx_projects_listing ON projects(marketplace_listing_id) WHERE marketplace_listing_id IS NOT NULL;

CREATE INDEX idx_projects_origin_owner ON projects(origin_owner_id) WHERE origin_owner_id IS NOT NULL;

CREATE INDEX idx_projects_active ON projects(is_deleted) WHERE is_deleted = FALSE;

CREATE INDEX idx_projects_metadata ON projects USING GIN(metadata);

CREATE TRIGGER trg_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_projects_soft_delete
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();

CREATE INDEX idx_system_configs_group ON system_configs(config_group);

CREATE INDEX idx_system_configs_active ON system_configs(is_active) WHERE is_active = TRUE;

CREATE INDEX idx_system_configs_updated ON system_configs(updated_at DESC);

CREATE TRIGGER trg_system_configs_updated_at
    BEFORE UPDATE ON system_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_api_logs_user ON api_logs(user_id, created_at DESC);

CREATE INDEX idx_api_logs_endpoint ON api_logs(endpoint);

CREATE INDEX idx_api_logs_status ON api_logs(status_code) WHERE status_code >= 400;

CREATE INDEX idx_api_logs_created ON api_logs(created_at DESC);

CREATE INDEX idx_ai_calls_provider_time ON ai_call_logs(provider, created_at DESC);

CREATE INDEX idx_ai_calls_user_time ON ai_call_logs(user_id, created_at DESC);

CREATE INDEX idx_ai_calls_status ON ai_call_logs(status) WHERE status != 'success';

CREATE INDEX idx_ai_calls_call_type ON ai_call_logs(call_type);

CREATE INDEX idx_ai_usage_daily_date ON ai_usage_daily(date DESC);

CREATE INDEX idx_ai_usage_daily_provider ON ai_usage_daily(provider, date DESC);

CREATE TRIGGER trg_ai_usage_daily_updated_at
    BEFORE UPDATE ON ai_usage_daily
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_generations_user ON user_generations(user_id, created_at DESC);

CREATE INDEX idx_generations_type ON user_generations(generation_type);

CREATE INDEX idx_generations_status ON user_generations(status);

CREATE INDEX idx_asset_categories_deleted_recoverable

CREATE INDEX idx_categories_path ON asset_categories USING GIST (path);

CREATE INDEX idx_categories_parent ON asset_categories(parent_id);

CREATE INDEX idx_categories_visible ON asset_categories(is_visible, display_order);

CREATE INDEX idx_categories_type ON asset_categories(asset_type);

CREATE TRIGGER trg_asset_categories_updated_at
    BEFORE UPDATE ON asset_categories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_system_assets_deleted_recoverable

CREATE INDEX idx_system_assets_category ON system_assets(category_id);

CREATE INDEX idx_system_assets_type ON system_assets(asset_type);

CREATE INDEX idx_system_assets_source ON system_assets(source);

CREATE INDEX idx_system_assets_tier ON system_assets(min_tier);

CREATE INDEX idx_system_assets_tags ON system_assets USING GIN(tags);

CREATE INDEX idx_system_assets_visible ON system_assets(is_visible, display_order);

CREATE TRIGGER trg_system_assets_updated_at
    BEFORE UPDATE ON system_assets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_marketplace_listings_deleted_recoverable

CREATE INDEX idx_listings_seller ON marketplace_listings(seller_id);

CREATE INDEX idx_listings_category ON marketplace_listings(category);

CREATE INDEX idx_listings_source ON marketplace_listings(source);

CREATE INDEX idx_listings_public ON marketplace_listings(is_public) WHERE is_public = TRUE;

CREATE INDEX idx_listings_moderation ON marketplace_listings(moderation_status);

CREATE INDEX idx_listings_created ON marketplace_listings(created_at DESC);

CREATE INDEX idx_listings_metadata ON marketplace_listings USING GIN(metadata);

CREATE TRIGGER trg_listings_updated_at
    BEFORE UPDATE ON marketplace_listings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_listings_soft_delete
    BEFORE UPDATE ON marketplace_listings
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();

CREATE INDEX idx_purchases_user ON marketplace_purchases(user_id, purchased_at DESC);

CREATE INDEX idx_purchases_listing ON marketplace_purchases(listing_id);

CREATE INDEX idx_purchases_time ON marketplace_purchases(purchased_at DESC);

CREATE UNIQUE INDEX idx_purchases_idempotency ON marketplace_purchases(idempotency_key) WHERE idempotency_key IS NOT NULL;

CREATE INDEX idx_marketplace_favorites_deleted_recoverable

CREATE INDEX idx_favorites_user ON marketplace_favorites(user_id, created_at DESC) WHERE is_deleted = false;

CREATE INDEX idx_favorites_listing ON marketplace_favorites(listing_id) WHERE is_deleted = false;

CREATE INDEX idx_marketplace_reviews_deleted_recoverable

CREATE INDEX idx_reviews_listing ON marketplace_reviews(listing_id, created_at DESC) WHERE is_deleted = false;

CREATE INDEX idx_reviews_reviewer ON marketplace_reviews(reviewer_id) WHERE is_deleted = false;

CREATE INDEX idx_reviews_rating ON marketplace_reviews(rating) WHERE is_deleted = false;

CREATE TRIGGER trg_reviews_updated_at
    BEFORE UPDATE ON marketplace_reviews
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_daily_themes_deleted_recoverable

CREATE INDEX idx_daily_themes_date ON daily_themes(date DESC) WHERE is_deleted = false;

CREATE INDEX idx_daily_themes_status ON daily_themes(status) WHERE is_deleted = false;

CREATE TRIGGER trg_daily_themes_updated_at
    BEFORE UPDATE ON daily_themes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_holidays_deleted_recoverable

CREATE INDEX idx_holidays_date ON holidays(month, day) WHERE is_deleted = false;

CREATE INDEX idx_holidays_regions ON holidays USING GIN(regions) WHERE is_deleted = false;

CREATE INDEX idx_holidays_category ON holidays(category) WHERE is_deleted = false;

CREATE TRIGGER trg_holidays_updated_at
    BEFORE UPDATE ON holidays
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_activity_logs_user_time ON activity_logs(user_id, created_at DESC);

CREATE INDEX idx_activity_logs_action ON activity_logs(action);

CREATE INDEX idx_activity_logs_resource ON activity_logs(resource_type, resource_id);

CREATE INDEX idx_analytics_events_user ON analytics_events(user_id, timestamp DESC);

CREATE INDEX idx_analytics_events_event_name ON analytics_events(event_name);

CREATE INDEX idx_analytics_events_event_id ON analytics_events(event_id);

CREATE INDEX idx_analytics_events_type_event_id ON analytics_events(event_type, event_id);

CREATE INDEX idx_analytics_events_timestamp ON analytics_events(timestamp DESC);

CREATE INDEX idx_analytics_agg_date ON analytics_aggregation(date DESC);

CREATE INDEX idx_analytics_agg_dimension ON analytics_aggregation(dimension_type, dimension_value);

CREATE TRIGGER trg_analytics_agg_updated_at
    BEFORE UPDATE ON analytics_aggregation
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_task_logs_task_name ON scheduled_task_logs(task_name);

CREATE INDEX idx_task_logs_started_at ON scheduled_task_logs(started_at DESC);

CREATE INDEX idx_task_logs_status ON scheduled_task_logs(status);

CREATE INDEX idx_clerk_events_type ON clerk_webhook_events(event_type);

CREATE INDEX idx_clerk_events_processed ON clerk_webhook_events(processed);

CREATE INDEX idx_clerk_events_created ON clerk_webhook_events(created_at DESC);

CREATE INDEX idx_stripe_events_type ON stripe_webhook_events(event_type);

CREATE INDEX idx_stripe_events_processed ON stripe_webhook_events(processed);

CREATE INDEX idx_stripe_events_created ON stripe_webhook_events(created_at DESC);

CREATE INDEX idx_config_audit_key ON config_audit_logs(config_key);

CREATE INDEX idx_config_audit_time ON config_audit_logs(changed_at DESC);

CREATE INDEX idx_reports_status ON content_reports(status);

CREATE INDEX idx_reports_listing_id ON content_reports(listing_id);

CREATE TRIGGER trg_content_reports_updated_at
    BEFORE UPDATE ON content_reports
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_resource_audit_resource_id ON system_resource_audit_logs(resource_id);

CREATE INDEX idx_resource_audit_changed_at ON system_resource_audit_logs(changed_at DESC);

CREATE INDEX idx_asset_prompt_templates_deleted_recoverable

CREATE INDEX idx_asset_prompt_templates_user ON asset_prompt_templates(user_id) WHERE is_deleted = false;

CREATE INDEX idx_asset_prompt_templates_usage ON asset_prompt_templates(user_id, use_count DESC) WHERE is_deleted = false;

CREATE TRIGGER trg_asset_prompt_templates_updated_at
    BEFORE UPDATE ON asset_prompt_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_pricing_plans_plan_code ON pricing_plans(plan_code);

CREATE INDEX idx_pricing_plans_plan_type ON pricing_plans(plan_type);

CREATE INDEX idx_pricing_plans_is_active ON pricing_plans(is_active) WHERE is_active = TRUE;

CREATE INDEX idx_pricing_plans_is_visible ON pricing_plans(is_visible) WHERE is_visible = TRUE;

CREATE INDEX idx_pricing_plans_effective_from ON pricing_plans(effective_from);

CREATE INDEX idx_pricing_plans_tier ON pricing_plans(tier) WHERE tier IS NOT NULL;

CREATE INDEX idx_pricing_plans_sort_order ON pricing_plans(sort_order);

CREATE TRIGGER trg_pricing_plans_updated_at
    BEFORE UPDATE ON pricing_plans
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_pricing_plans_audit
    AFTER INSERT OR UPDATE OR DELETE ON pricing_plans
    FOR EACH ROW
    EXECUTE FUNCTION log_pricing_plan_change();

CREATE INDEX idx_pricing_history_plan_id ON pricing_history(plan_id);

CREATE INDEX idx_pricing_history_plan_code ON pricing_history(plan_code);

CREATE INDEX idx_pricing_history_changed_at ON pricing_history(changed_at DESC);

CREATE INDEX idx_pricing_history_changed_by ON pricing_history(changed_by);

CREATE INDEX idx_pricing_history_action ON pricing_history(action);

CREATE INDEX idx_pricing_history_old_data_gin ON pricing_history USING GIN(old_data);  -- GIN 索引用于 JSONB 查询

CREATE INDEX idx_pricing_history_new_data_gin ON pricing_history USING GIN(new_data);  -- GIN 索引用于 JSONB 查询

CREATE INDEX idx_user_price_overrides_user_id ON user_price_overrides(user_id);

CREATE INDEX idx_user_price_overrides_plan_id ON user_price_overrides(pricing_plan_id);

CREATE INDEX idx_user_price_overrides_valid_from ON user_price_overrides(valid_from);

CREATE INDEX idx_user_price_overrides_valid_until ON user_price_overrides(valid_until) WHERE valid_until IS NOT NULL;

CREATE TRIGGER trg_user_price_overrides_updated_at
    BEFORE UPDATE ON user_price_overrides
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_sub_history_user ON subscription_history(user_id, effective_date DESC);

CREATE INDEX idx_sub_history_tier ON subscription_history(tier);

CREATE INDEX idx_credit_purchases_user ON credit_purchases(user_id, created_at DESC);

CREATE INDEX idx_credit_purchases_status ON credit_purchases(status);

CREATE UNIQUE INDEX idx_credit_purchases_idempotency ON credit_purchases(idempotency_key) WHERE idempotency_key IS NOT NULL;

CREATE INDEX idx_feature_flags_key ON feature_flags(flag_key);

CREATE INDEX idx_feature_flags_enabled ON feature_flags(is_enabled);

CREATE TRIGGER trg_feature_flags_updated_at
    BEFORE UPDATE ON feature_flags
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_experiments_key ON experiments(experiment_key);

CREATE INDEX idx_experiments_status ON experiments(status);

CREATE TRIGGER trg_experiments_updated_at
    BEFORE UPDATE ON experiments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_exp_assignments_experiment ON experiment_assignments(experiment_id);

CREATE INDEX idx_exp_assignments_user ON experiment_assignments(user_id);

CREATE INDEX idx_exp_results_experiment ON experiment_results(experiment_id);

CREATE INDEX idx_exp_results_date ON experiment_results(experiment_id, date DESC);

CREATE TRIGGER trg_experiment_results_updated_at
    BEFORE UPDATE ON experiment_results
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_exp_exposures_experiment ON experiment_exposures(experiment_id);

CREATE INDEX idx_exp_exposures_user ON experiment_exposures(user_id);

CREATE INDEX idx_exp_exposures_created_at ON experiment_exposures(created_at DESC);

CREATE INDEX idx_exp_exposures_dedup ON experiment_exposures(experiment_id, user_id, created_at DESC);

CREATE INDEX idx_exp_conversions_experiment ON experiment_conversions(experiment_id);

CREATE INDEX idx_exp_conversions_user ON experiment_conversions(user_id);

CREATE INDEX idx_exp_conversions_metric ON experiment_conversions(metric_key);

CREATE INDEX idx_exp_conversions_created_at ON experiment_conversions(created_at DESC);

CREATE INDEX idx_exp_conversions_exp_metric ON experiment_conversions(experiment_id, metric_key, created_at DESC);

CREATE INDEX idx_campaigns_deleted_recoverable

CREATE INDEX idx_campaigns_status ON campaigns(status, is_active) WHERE is_deleted = false AND is_permanently_deleted = false;

CREATE INDEX idx_campaigns_dates ON campaigns(start_at, end_at) WHERE is_deleted = false;

CREATE TRIGGER trg_campaigns_updated_at
    BEFORE UPDATE ON campaigns
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_campaign_participations_deleted_recoverable

CREATE INDEX idx_campaign_participations_user ON campaign_participations(user_id);

CREATE INDEX idx_campaign_participations_campaign ON campaign_participations(campaign_id);

CREATE INDEX idx_campaign_dismissals_deleted_recoverable

CREATE INDEX idx_campaign_dismissals_user ON campaign_dismissals(user_id);

CREATE INDEX idx_notifications_deleted_recoverable

CREATE INDEX idx_notifications_user ON notifications(user_id, created_at DESC);

CREATE INDEX idx_notifications_type ON notifications(notification_type);

CREATE INDEX idx_notifications_unread ON notifications(user_id, is_read) WHERE is_read = FALSE;

CREATE INDEX idx_onboarding_steps_deleted_recoverable

CREATE INDEX idx_onboarding_steps_order ON onboarding_steps(step_order);

CREATE INDEX idx_onboarding_steps_active ON onboarding_steps(is_active);

CREATE TRIGGER trg_onboarding_steps_updated_at
    BEFORE UPDATE ON onboarding_steps
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_user_onboarding_progress_deleted_recoverable

CREATE INDEX idx_onboarding_progress_user ON user_onboarding_progress(user_id);

CREATE INDEX idx_onboarding_progress_status ON user_onboarding_progress(status);

CREATE INDEX idx_referrals_deleted_recoverable

CREATE INDEX idx_referrals_referrer ON referrals(referrer_id);

CREATE INDEX idx_referrals_referee ON referrals(referee_id);

CREATE INDEX idx_referrals_code ON referrals(referral_code);

CREATE INDEX idx_referrals_status ON referrals(status);

CREATE INDEX idx_project_versions_deleted_recoverable

CREATE INDEX idx_project_versions_project ON project_versions(project_id, version_number DESC);

CREATE INDEX idx_project_versions_created ON project_versions(created_at DESC);

CREATE INDEX idx_assets_deleted_recoverable

CREATE INDEX idx_assets_user ON assets(user_id, created_at DESC);

CREATE INDEX idx_assets_project ON assets(project_id) WHERE project_id IS NOT NULL;

CREATE INDEX idx_assets_type ON assets(type);

CREATE INDEX idx_assets_active ON assets(is_deleted) WHERE is_deleted = FALSE;

CREATE TRIGGER trg_assets_updated_at
    BEFORE UPDATE ON assets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_assets_soft_delete
    BEFORE UPDATE ON assets
    FOR EACH ROW
    EXECUTE FUNCTION set_deleted_at_on_soft_delete();

CREATE INDEX idx_user_discounts_user ON user_discounts(user_id);

CREATE INDEX idx_user_discounts_valid ON user_discounts(valid_until);

CREATE OR REPLACE FUNCTION deduct_credits_atomic(
    p_user_id TEXT,
    p_amount INT,
    p_type TEXT,
    p_description TEXT DEFAULT NULL,
    p_idempotency_key TEXT DEFAULT NULL,
    p_related_entity_type TEXT DEFAULT NULL,
    p_related_entity_id TEXT DEFAULT NULL
)
RETURNS TABLE (
    success BOOLEAN,
    new_monthly INT,
    new_permanent INT,
    error_message TEXT
) AS $$
DECLARE
    v_monthly INT;
    v_permanent INT;
    v_deduct_monthly INT;
    v_deduct_permanent INT;
BEGIN
    -- 输入验证
    IF p_user_id IS NULL OR length(p_user_id) = 0 OR length(p_user_id) > 100 THEN
        RETURN QUERY SELECT FALSE, 0, 0, 'Invalid user_id'::TEXT;
        RETURN;
    END IF;

    IF p_amount <= 0 OR p_amount > 1000000 THEN
        RETURN QUERY SELECT FALSE, 0, 0, 'Invalid amount (must be 1-1000000)'::TEXT;
        RETURN;
    END IF;

    IF p_type IS NULL OR length(p_type) = 0 OR length(p_type) > 50 THEN
        RETURN QUERY SELECT FALSE, 0, 0, 'Invalid type'::TEXT;
        RETURN;
    END IF;

    IF p_description IS NOT NULL AND length(p_description) > 500 THEN
        RETURN QUERY SELECT FALSE, 0, 0, 'Description too long (max 500 chars)'::TEXT;
        RETURN;
    END IF;

    -- 幂等性检查: 防止重复扣除
    IF p_idempotency_key IS NOT NULL THEN
        IF EXISTS (
            SELECT 1 FROM credit_transactions
            WHERE idempotency_key = p_idempotency_key || '-deduct'
        ) THEN
            -- 返回已存在的交易结果
            SELECT credits_monthly, credits_permanent
            INTO v_monthly, v_permanent
            FROM profiles WHERE id = p_user_id;
            RETURN QUERY SELECT FALSE, v_monthly, v_permanent, 'Duplicate transaction (idempotency)'::TEXT;
            RETURN;
        END IF;
    END IF;

    -- 加锁获取当前余额
    SELECT credits_monthly, credits_permanent
    INTO v_monthly, v_permanent
    FROM profiles
    WHERE id = p_user_id
    FOR UPDATE;

    -- 检查用户是否存在
    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, 0, 0, 'User not found';
        RETURN;
    END IF;

    -- 检查总余额是否足够
    IF (v_monthly + v_permanent) < p_amount THEN
        RETURN QUERY SELECT FALSE, v_monthly, v_permanent, 'Insufficient credits';
        RETURN;
    END IF;

    -- 计算扣除策略: 先扣月度积分,再扣永久积分
    IF v_monthly >= p_amount THEN
        v_deduct_monthly := p_amount;
        v_deduct_permanent := 0;
    ELSE
        v_deduct_monthly := v_monthly;
        v_deduct_permanent := p_amount - v_monthly;
    END IF;

    -- 更新余额
    UPDATE profiles
    SET
        credits_monthly = v_monthly - v_deduct_monthly,
        credits_permanent = v_permanent - v_deduct_permanent,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_user_id;

    -- 记录月度积分交易
    IF v_deduct_monthly > 0 THEN
        INSERT INTO credit_transactions (
            user_id, transaction_type, bucket, amount,
            balance_monthly_after, balance_permanent_after,
            description, idempotency_key,
            related_entity_type, related_entity_id
        ) VALUES (
            p_user_id, p_type, 'monthly', -v_deduct_monthly,
            v_monthly - v_deduct_monthly, v_permanent,
            p_description, p_idempotency_key || '_monthly',
            p_related_entity_type, p_related_entity_id
        );
    END IF;

    -- 记录永久积分交易
    IF v_deduct_permanent > 0 THEN
        INSERT INTO credit_transactions (
            user_id, transaction_type, bucket, amount,
            balance_monthly_after, balance_permanent_after,
            description, idempotency_key,
            related_entity_type, related_entity_id
        ) VALUES (
            p_user_id, p_type, 'permanent', -v_deduct_permanent,
            v_monthly - v_deduct_monthly, v_permanent - v_deduct_permanent,
            p_description, p_idempotency_key || '_permanent',
            p_related_entity_type, p_related_entity_id
        );
    END IF;

    RETURN QUERY SELECT TRUE, v_monthly - v_deduct_monthly, v_permanent - v_deduct_permanent, NULL::TEXT;
END;

CREATE OR REPLACE FUNCTION add_credits_atomic(
    p_user_id TEXT,
    p_amount INT,
    p_bucket TEXT,
    p_type TEXT,
    p_description TEXT DEFAULT NULL,
    p_idempotency_key TEXT DEFAULT NULL
)
RETURNS TABLE (
    success BOOLEAN,
    new_monthly INT,
    new_permanent INT,
    error_message TEXT
) AS $$
DECLARE
    v_monthly INT;
    v_permanent INT;
BEGIN
    -- 输入验证
    IF p_user_id IS NULL OR length(p_user_id) = 0 OR length(p_user_id) > 100 THEN
        RETURN QUERY SELECT FALSE, 0, 0, 'Invalid user_id'::TEXT;
        RETURN;
    END IF;

    IF p_amount <= 0 OR p_amount > 1000000 THEN
        RETURN QUERY SELECT FALSE, 0, 0, 'Invalid amount (must be 1-1000000)'::TEXT;
        RETURN;
    END IF;

    IF p_bucket NOT IN ('monthly', 'permanent') THEN
        RETURN QUERY SELECT FALSE, 0, 0, 'Invalid bucket (must be monthly or permanent)'::TEXT;
        RETURN;
    END IF;

    IF p_type IS NULL OR length(p_type) = 0 OR length(p_type) > 50 THEN
        RETURN QUERY SELECT FALSE, 0, 0, 'Invalid type'::TEXT;
        RETURN;
    END IF;

    IF p_description IS NOT NULL AND length(p_description) > 500 THEN
        RETURN QUERY SELECT FALSE, 0, 0, 'Description too long (max 500 chars)'::TEXT;
        RETURN;
    END IF;

    -- 加锁获取当前余额
    SELECT credits_monthly, credits_permanent
    INTO v_monthly, v_permanent
    FROM profiles
    WHERE id = p_user_id
    FOR UPDATE;

    -- 检查用户是否存在
    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, 0, 0, 'User not found';
        RETURN;
    END IF;

    -- 更新余额
    IF p_bucket = 'monthly' THEN
        UPDATE profiles SET credits_monthly = credits_monthly + p_amount WHERE id = p_user_id;
        v_monthly := v_monthly + p_amount;
    ELSE
        UPDATE profiles SET credits_permanent = credits_permanent + p_amount WHERE id = p_user_id;
        v_permanent := v_permanent + p_amount;
    END IF;

    -- 记录交易
    INSERT INTO credit_transactions (
        user_id, transaction_type, bucket, amount,
        balance_monthly_after, balance_permanent_after,
        description, idempotency_key
    ) VALUES (
        p_user_id, p_type, p_bucket, p_amount,
        v_monthly, v_permanent,
        p_description, p_idempotency_key
    );

    RETURN QUERY SELECT TRUE, v_monthly, v_permanent, NULL::TEXT;
END;

CREATE OR REPLACE FUNCTION execute_marketplace_purchase(
    p_user_id TEXT,
    p_listing_id UUID,
    p_idempotency_key TEXT
)
RETURNS TABLE (
    success BOOLEAN,
    error_message TEXT
) AS $$
DECLARE
    v_price INT;
    v_title TEXT;
    v_thumbnail TEXT;
    v_description TEXT;
    v_version TEXT;
    v_resource_type TEXT;
    v_resource_id UUID;
BEGIN
    -- 输入验证
    IF p_user_id IS NULL OR length(p_user_id) = 0 OR length(p_user_id) > 100 THEN
        RETURN QUERY SELECT FALSE, 'Invalid user_id'::TEXT;
        RETURN;
    END IF;

    IF p_listing_id IS NULL THEN
        RETURN QUERY SELECT FALSE, 'Invalid listing_id'::TEXT;
        RETURN;
    END IF;

    IF p_idempotency_key IS NOT NULL AND length(p_idempotency_key) > 200 THEN
        RETURN QUERY SELECT FALSE, 'Idempotency key too long (max 200 chars)'::TEXT;
        RETURN;
    END IF;

    -- 获取 listing 信息
    SELECT price_credits, title, thumbnail_url, description, version, resource_type, resource_id
    INTO v_price, v_title, v_thumbnail, v_description, v_version, v_resource_type, v_resource_id
    FROM marketplace_listings
    WHERE id = p_listing_id AND is_public = TRUE AND is_deleted = FALSE
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, 'Listing not found or not available';
        RETURN;
    END IF;

    -- 检查是否已购买
    IF EXISTS (SELECT 1 FROM marketplace_purchases WHERE user_id = p_user_id AND listing_id = p_listing_id) THEN
        RETURN QUERY SELECT TRUE, NULL::TEXT;
        RETURN;
    END IF;

    -- 扣除积分 (必须检查是否成功)
    DECLARE
        v_deduct_success BOOLEAN;
        v_error_msg TEXT;
    BEGIN
        SELECT success, error_message
        INTO v_deduct_success, v_error_msg
        FROM deduct_credits_atomic(
            p_user_id,
            v_price,
            'marketplace_purchase',
            'Purchase listing: ' || v_title,
            p_idempotency_key,
            'listing',
            p_listing_id::TEXT
        );

        -- 如果扣费失败，立即返回错误
        IF NOT v_deduct_success THEN
            RETURN QUERY SELECT FALSE, COALESCE(v_error_msg, 'Insufficient credits');
            RETURN;
        END IF;
    END;

CREATE OR REPLACE FUNCTION increment_campaign_usage(
    p_campaign_id UUID
)
RETURNS BOOLEAN AS $$
DECLARE
    v_usage_limit INT;
    v_usage_count INT;
BEGIN
    SELECT usage_limit, usage_count
    INTO v_usage_limit, v_usage_count
    FROM campaigns
    WHERE id = p_campaign_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;

    -- 检查是否已达上限
    IF v_usage_limit IS NOT NULL AND v_usage_count >= v_usage_limit THEN
        RETURN FALSE;
    END IF;

    -- 原子递增
    UPDATE campaigns SET usage_count = usage_count + 1 WHERE id = p_campaign_id;

    RETURN TRUE;
END;

CREATE OR REPLACE FUNCTION upsert_ai_usage_daily(
    p_date DATE,
    p_provider TEXT,
    p_model TEXT,
    p_call_type TEXT,
    p_success BOOLEAN,
    p_input_tokens BIGINT DEFAULT 0,
    p_output_tokens BIGINT DEFAULT 0,
    p_images INT DEFAULT 0,
    p_latency_ms INT DEFAULT 0,
    p_cost_usd DECIMAL DEFAULT 0,
    p_error_type TEXT DEFAULT NULL
)
RETURNS VOID AS $$
DECLARE
    v_error_counts JSONB;
BEGIN
    IF p_error_type IS NOT NULL THEN
        v_error_counts := jsonb_build_object(p_error_type, 1);
    ELSE
        v_error_counts := '{}'::jsonb;
    END IF;

    INSERT INTO ai_usage_daily (
        date, provider, model, call_type,
        total_calls, successful_calls, failed_calls,
        total_input_tokens, total_output_tokens, total_images,
        avg_latency_ms, min_latency_ms, max_latency_ms,
        estimated_cost_usd, error_counts
    ) VALUES (
        p_date, p_provider, p_model, p_call_type,
        1,
        CASE WHEN p_success THEN 1 ELSE 0 END,
        CASE WHEN p_success THEN 0 ELSE 1 END,
        p_input_tokens, p_output_tokens, p_images,
        p_latency_ms, p_latency_ms, p_latency_ms,
        p_cost_usd, v_error_counts
    )
    ON CONFLICT (date, provider, model, call_type) DO UPDATE SET
        total_calls = ai_usage_daily.total_calls + 1,
        successful_calls = ai_usage_daily.successful_calls + CASE WHEN p_success THEN 1 ELSE 0 END,
        failed_calls = ai_usage_daily.failed_calls + CASE WHEN p_success THEN 0 ELSE 1 END,
        total_input_tokens = ai_usage_daily.total_input_tokens + p_input_tokens,
        total_output_tokens = ai_usage_daily.total_output_tokens + p_output_tokens,
        total_images = ai_usage_daily.total_images + p_images,
        avg_latency_ms = CASE
            WHEN ai_usage_daily.total_calls = 0 THEN p_latency_ms
            ELSE ((ai_usage_daily.avg_latency_ms * ai_usage_daily.total_calls) + p_latency_ms) / (ai_usage_daily.total_calls + 1)
        END,
        min_latency_ms = LEAST(COALESCE(ai_usage_daily.min_latency_ms, p_latency_ms), p_latency_ms),
        max_latency_ms = GREATEST(COALESCE(ai_usage_daily.max_latency_ms, p_latency_ms), p_latency_ms),
        estimated_cost_usd = ai_usage_daily.estimated_cost_usd + p_cost_usd,
        error_counts = CASE
            WHEN p_error_type IS NOT NULL THEN
                ai_usage_daily.error_counts || jsonb_build_object(
                    p_error_type,
                    COALESCE((ai_usage_daily.error_counts->>p_error_type)::int, 0) + 1
                )
            ELSE ai_usage_daily.error_counts
        END,
        updated_at = CURRENT_TIMESTAMP;
END;

CREATE OR REPLACE FUNCTION is_admin()
RETURNS BOOLEAN AS $$
BEGIN
    -- Check if current user is admin
    -- This reads from app.current_user_role set by your FastAPI backend
    RETURN current_setting('app.current_user_role', true) = 'admin';
EXCEPTION
    WHEN OTHERS THEN
        RETURN FALSE;
END;

CREATE INDEX idx_user_events_user_id ON user_events(user_id, created_at DESC);

CREATE INDEX idx_user_events_event_type ON user_events(event_type, created_at DESC);

CREATE INDEX idx_user_events_created_at ON user_events(created_at DESC);

CREATE INDEX idx_user_events_session ON user_events(session_id) WHERE session_id IS NOT NULL;

CREATE INDEX idx_aggregated_stats_period ON aggregated_stats(period_start DESC, period_end DESC);

CREATE INDEX idx_aggregated_stats_type_key ON aggregated_stats(stat_type, stat_key);

CREATE INDEX idx_aggregated_stats_key_period ON aggregated_stats(stat_key, period_start DESC);

CREATE INDEX idx_error_logs_user_id ON error_logs(user_id, created_at DESC);

CREATE INDEX idx_error_logs_error_type ON error_logs(error_type, created_at DESC);

CREATE INDEX idx_error_logs_severity ON error_logs(severity, created_at DESC);

CREATE INDEX idx_error_logs_created_at ON error_logs(created_at DESC);

CREATE INDEX idx_error_logs_unresolved ON error_logs(created_at DESC) WHERE resolved = FALSE;

CREATE INDEX idx_support_tickets_user_id ON support_tickets(user_id, created_at DESC) WHERE is_deleted = false;

CREATE INDEX idx_support_tickets_deleted_recoverable

CREATE INDEX idx_support_tickets_ticket_number ON support_tickets(ticket_number);

CREATE INDEX idx_support_tickets_status ON support_tickets(status, created_at DESC) WHERE is_deleted = false;

CREATE INDEX idx_support_tickets_priority ON support_tickets(priority, created_at DESC) WHERE is_deleted = false;

CREATE INDEX idx_support_tickets_assigned_to ON support_tickets(assigned_to, created_at DESC) WHERE is_deleted = false;

CREATE INDEX idx_support_tickets_open ON support_tickets(created_at DESC) WHERE status IN ('open', 'in_progress', 'waiting_user') AND is_deleted = false;

CREATE INDEX idx_support_replies_ticket_id ON support_replies(ticket_id, created_at ASC) WHERE is_deleted = false;

CREATE INDEX idx_support_replies_deleted_recoverable

CREATE INDEX idx_support_replies_user_id ON support_replies(user_id, created_at DESC) WHERE is_deleted = false;

CREATE INDEX idx_support_replies_created_at ON support_replies(created_at DESC) WHERE is_deleted = false;

CREATE OR REPLACE FUNCTION generate_ticket_number()
RETURNS TRIGGER AS $$
DECLARE
    today_count INTEGER;
    today_date TEXT;
BEGIN
    -- 获取今天的日期 (YYYYMMDD 格式)
    today_date := TO_CHAR(NOW(), 'YYYYMMDD');

    -- 计算今天已创建的工单数量
    SELECT COUNT(*) + 1
    INTO today_count
    FROM support_tickets
    WHERE ticket_number LIKE 'TKT-' || today_date || '-%';

    -- 生成工单编号: TKT-20260110-001
    NEW.ticket_number := 'TKT-' || today_date || '-' || LPAD(today_count::TEXT, 3, '0');

    RETURN NEW;
END;

CREATE TRIGGER trigger_generate_ticket_number
BEFORE INSERT ON support_tickets
FOR EACH ROW
WHEN (NEW.ticket_number IS NULL)
EXECUTE FUNCTION generate_ticket_number();

CREATE TRIGGER trigger_update_aggregated_stats_updated_at
BEFORE UPDATE ON aggregated_stats
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_update_support_tickets_updated_at
BEFORE UPDATE ON support_tickets
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_update_support_replies_updated_at
BEFORE UPDATE ON support_replies
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_admin_operations_admin_id ON admin_operations(admin_id, created_at DESC);

CREATE INDEX idx_admin_operations_operation_type ON admin_operations(operation_type, created_at DESC);

CREATE INDEX idx_admin_operations_target ON admin_operations(target_type, target_id);

CREATE INDEX idx_admin_operations_created_at ON admin_operations(created_at DESC);

CREATE INDEX idx_admin_operations_failed ON admin_operations(created_at DESC) WHERE status = 'failed';

CREATE INDEX idx_listing_usages_listing_id ON listing_usages(listing_id, created_at DESC);

CREATE INDEX idx_listing_usages_user_id ON listing_usages(user_id, created_at DESC);

CREATE INDEX idx_listing_usages_project_id ON listing_usages(project_id) WHERE project_id IS NOT NULL;

CREATE INDEX idx_listing_usages_usage_type ON listing_usages(usage_type, created_at DESC);

CREATE INDEX idx_listing_usages_created_at ON listing_usages(created_at DESC);

CREATE INDEX idx_marketplace_reports_listing_id ON marketplace_reports(listing_id, created_at DESC);

CREATE INDEX idx_marketplace_reports_reporter_id ON marketplace_reports(reporter_id, created_at DESC);

CREATE INDEX idx_marketplace_reports_status ON marketplace_reports(status, created_at DESC);

CREATE INDEX idx_marketplace_reports_reviewed_by ON marketplace_reports(reviewed_by, reviewed_at DESC);

CREATE INDEX idx_marketplace_reports_pending ON marketplace_reports(created_at DESC) WHERE status IN ('pending', 'under_review');

CREATE INDEX idx_daily_metrics_metric_date ON daily_metrics(metric_date DESC);

CREATE INDEX idx_daily_metrics_created_at ON daily_metrics(created_at DESC);

CREATE INDEX idx_monthly_metrics_year_month ON monthly_metrics(metric_year DESC, metric_month DESC);

CREATE INDEX idx_monthly_metrics_created_at ON monthly_metrics(created_at DESC);

CREATE TRIGGER trigger_update_marketplace_reports_updated_at
BEFORE UPDATE ON marketplace_reports
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_update_daily_metrics_updated_at
BEFORE UPDATE ON daily_metrics
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_update_monthly_metrics_updated_at
BEFORE UPDATE ON monthly_metrics
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_generation_tasks_user_id ON generation_tasks(user_id, created_at DESC);

CREATE INDEX idx_generation_tasks_project_id ON generation_tasks(project_id) WHERE project_id IS NOT NULL;

CREATE INDEX idx_generation_tasks_status ON generation_tasks(status, created_at DESC);

CREATE INDEX idx_generation_tasks_task_type ON generation_tasks(task_type, created_at DESC);

CREATE INDEX idx_generation_tasks_created_at ON generation_tasks(created_at DESC);

CREATE INDEX idx_generation_tasks_pending ON generation_tasks(created_at ASC) WHERE status = 'pending';

CREATE INDEX idx_page_prompt_templates_category ON page_prompt_templates(template_category);

CREATE INDEX idx_page_prompt_templates_active ON page_prompt_templates(is_active, usage_count DESC);

CREATE INDEX idx_page_prompt_templates_template_name ON page_prompt_templates(template_name);

CREATE INDEX idx_page_prompt_templates_created_by ON page_prompt_templates(created_by) WHERE created_by IS NOT NULL;

CREATE INDEX idx_payment_records_user_id ON payment_records(user_id, created_at DESC);

CREATE INDEX idx_payment_records_stripe_payment_intent ON payment_records(stripe_payment_intent_id);

CREATE INDEX idx_payment_records_status ON payment_records(status, created_at DESC);

CREATE INDEX idx_payment_records_payment_type ON payment_records(payment_type, created_at DESC);

CREATE INDEX idx_payment_records_created_at ON payment_records(created_at DESC);

CREATE INDEX idx_payment_records_succeeded ON payment_records(created_at DESC) WHERE status = 'succeeded';

CREATE TRIGGER trigger_update_generation_tasks_updated_at
BEFORE UPDATE ON generation_tasks
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_update_page_prompt_templates_updated_at
BEFORE UPDATE ON page_prompt_templates
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_update_payment_records_updated_at
BEFORE UPDATE ON payment_records
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_profiles_onboarding_step ON profiles(onboarding_step)

CREATE INDEX idx_projects_active ON projects(user_id, created_at DESC)


COMMIT;
