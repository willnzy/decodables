-- ==============================================================================
-- Make Decodables Database Initialization Script (v3.15 - Complete)
-- Includes: core schema + RLS policies + v3.9-v3.15 updates
-- 
-- Version History:
-- v3.0: Credit buckets, marketplace, notifications, discounts
-- v3.1: assets.metadata, OCR support
-- v3.2: admin_operation_logs, user_events, aggregated_stats, system_configs
-- v3.3: Dashboard refactor, soft delete, purchase tracking, content_reports
-- v3.4: analytics_events, cohort tracking
-- v3.5: error_logs
-- v3.6: asset_prompt_templates (5W1H naming)
-- v3.7: page_prompt_templates
-- v3.8: Naming convention refactor
-- v3.9: Timezone support (timezone + created_at_local columns)
-- v3.10: System configs refactor (key, value, value_type, config_group)
-- v3.11: Analytics events enhancement (event_name, context)
-- v3.12: Analytics aggregation tables (daily/monthly metrics, cohorts, funnels)
-- v3.13: Holiday themes + Marketing campaigns system
-- v3.14: Global holidays expansion (28+ themes)
-- v3.15: Scheduled task monitoring logs
-- ==============================================================================

-- ==========================================
-- Part 1: Schema Definition
-- ==========================================

-- 1. User profiles
CREATE TABLE IF NOT EXISTS profiles (
  id TEXT PRIMARY KEY,
  email TEXT,
  username TEXT,
  first_name TEXT,
  last_name TEXT,
  avatar_url TEXT,
  user_code TEXT UNIQUE,
  credits_monthly INT DEFAULT 0,
  credits_permanent INT DEFAULT 0,
  tier TEXT DEFAULT 'free',
  subscription_status TEXT DEFAULT 'inactive',
  subscription_valid_until TIMESTAMPTZ,
  monthly_credits_cycle_anchor TIMESTAMPTZ,
  stripe_customer_id TEXT,
  role TEXT DEFAULT 'user',
  cohort_month TEXT,
  -- v3.9: Timezone support
  timezone TEXT DEFAULT 'UTC',
  created_at_local TIMESTAMP,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. User discounts
CREATE TABLE IF NOT EXISTS user_discounts (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id TEXT REFERENCES profiles(id) NOT NULL,
  discount_percent INT NOT NULL,
  valid_until TIMESTAMPTZ,
  target_plan TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Credit ledger (APPEND-ONLY)
CREATE TABLE IF NOT EXISTS credit_transactions (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id TEXT REFERENCES profiles(id) NOT NULL,
  amount INT NOT NULL,
  bucket TEXT NOT NULL DEFAULT 'permanent',
  balance_monthly_after INT NOT NULL DEFAULT 0,
  balance_permanent_after INT NOT NULL DEFAULT 0,
  type TEXT NOT NULL,
  description TEXT,
  idempotency_key TEXT,
  -- v3.9: Timezone support
  timezone TEXT DEFAULT 'UTC',
  created_at_local TIMESTAMP,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_transactions_idempotency 
ON credit_transactions(idempotency_key) WHERE idempotency_key IS NOT NULL;

-- 4. User projects
CREATE TABLE IF NOT EXISTS projects (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id TEXT REFERENCES profiles(id) NOT NULL,
  title TEXT DEFAULT 'My Magic Story',
  canvas_data JSONB DEFAULT '{}'::jsonb,
  thumbnail_url TEXT,
  last_downloaded_hash TEXT,
  is_deleted BOOLEAN DEFAULT false,
  deleted_at TIMESTAMPTZ DEFAULT NULL,
  is_hidden_from_trash BOOLEAN DEFAULT false,
  contains_locked_elements BOOLEAN DEFAULT false,
  source_listing_id UUID,
  is_purchased BOOLEAN DEFAULT false,
  origin_owner_id TEXT,
  listing_status TEXT DEFAULT NULL,
  marketplace_listing_id UUID,
  -- v3.9: Timezone support
  timezone TEXT DEFAULT 'UTC',
  created_at_local TIMESTAMP,
  updated_at_local TIMESTAMP,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Marketplace listings
CREATE TABLE IF NOT EXISTS marketplace_listings (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  seller_id TEXT REFERENCES profiles(id),
  title TEXT NOT NULL,
  description TEXT,
  thumbnail_url TEXT NOT NULL,
  resource_url TEXT NOT NULL,
  resource_type TEXT NOT NULL,
  resource_id UUID,
  price_credits INT NOT NULL DEFAULT 0,
  allowed_tiers TEXT[] NOT NULL DEFAULT '{free, starter, pro}',
  usage_count BIGINT DEFAULT 0,
  sales_count INT DEFAULT 0,
  unique_buyers_count INT DEFAULT 0,
  total_revenue INT DEFAULT 0,
  is_public BOOLEAN DEFAULT false,
  is_deleted BOOLEAN DEFAULT false,
  moderation_status TEXT NOT NULL DEFAULT 'draft',
  moderation_note TEXT,
  moderated_by TEXT REFERENCES profiles(id),
  moderated_at TIMESTAMPTZ,
  version VARCHAR(20) DEFAULT '1.0',
  changelog TEXT DEFAULT '',
  version_history JSONB DEFAULT '[]'::jsonb,
  -- v3.9: Timezone support
  timezone TEXT DEFAULT 'UTC',
  created_at_local TIMESTAMP,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. User purchases
CREATE TABLE IF NOT EXISTS user_purchases (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id TEXT REFERENCES profiles(id) NOT NULL,
  listing_id UUID REFERENCES marketplace_listings(id) NOT NULL,
  price_paid INT NOT NULL,
  purchased_at TIMESTAMPTZ DEFAULT NOW(),
  idempotency_key TEXT,
  snapshot_title TEXT,
  snapshot_thumbnail_url TEXT,
  snapshot_description TEXT,
  snapshot_version TEXT,
  snapshot_resource_type TEXT,
  snapshot_resource_id UUID,
  utm_source TEXT,
  utm_medium TEXT,
  utm_campaign TEXT,
  referral_context TEXT,
  -- v3.9: Timezone support
  timezone TEXT DEFAULT 'UTC',
  purchased_at_local TIMESTAMP,
  UNIQUE(user_id, listing_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_purchases_idempotency 
ON user_purchases(idempotency_key) WHERE idempotency_key IS NOT NULL;

-- 7. User assets
CREATE TABLE IF NOT EXISTS assets (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id TEXT REFERENCES profiles(id) NOT NULL,
  project_id UUID REFERENCES projects(id),
  url TEXT NOT NULL,
  type TEXT NOT NULL,
  prompt TEXT,
  description TEXT,
  metadata JSONB,
  is_deleted BOOLEAN DEFAULT false,
  deleted_at TIMESTAMPTZ DEFAULT NULL,
  is_hidden_from_trash BOOLEAN DEFAULT false,
  source_listing_id UUID REFERENCES marketplace_listings(id),
  is_purchased BOOLEAN DEFAULT false,
  origin_owner_id TEXT REFERENCES profiles(id),
  listing_status TEXT DEFAULT NULL,
  marketplace_listing_id UUID REFERENCES marketplace_listings(id),
  -- v3.9: Timezone support
  timezone TEXT DEFAULT 'UTC',
  created_at_local TIMESTAMP,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_assets_user_proj ON assets(user_id, project_id);

-- 8. Notifications
CREATE TABLE IF NOT EXISTS notifications (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id TEXT REFERENCES profiles(id),
  target_group TEXT,
  notification_type TEXT DEFAULT 'system',
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  is_read BOOLEAN DEFAULT false,
  -- v3.9: Timezone support
  timezone TEXT DEFAULT 'UTC',
  created_at_local TIMESTAMP,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9. System resources
CREATE TABLE IF NOT EXISTS system_resources (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  type TEXT NOT NULL,
  category TEXT,
  url TEXT NOT NULL,
  allowed_tiers TEXT[] DEFAULT '{free, starter, pro}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 10. Activity logs
CREATE TABLE IF NOT EXISTS activity_logs (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id TEXT REFERENCES profiles(id),
  action TEXT NOT NULL,
  metadata JSONB,
  -- v3.9: Timezone support
  timezone TEXT DEFAULT 'UTC',
  created_at_local TIMESTAMP,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 11. Support & admin ops
CREATE TABLE IF NOT EXISTS support_tickets (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id TEXT REFERENCES profiles(id),
  admin_id TEXT REFERENCES profiles(id),
  category TEXT NOT NULL,
  content TEXT,
  metadata JSONB,
  status TEXT DEFAULT 'closed',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 12. Listing usages table
CREATE TABLE IF NOT EXISTS listing_usages (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  listing_id UUID REFERENCES marketplace_listings(id) NOT NULL,
  used_by_user_id TEXT REFERENCES profiles(id) NOT NULL,
  project_id UUID REFERENCES projects(id) NOT NULL,
  used_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(listing_id, used_by_user_id, project_id)
);

-- 13. Leaderboard snapshots
CREATE TABLE IF NOT EXISTS leaderboard_snapshots (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  period_start DATE NOT NULL,
  period_end DATE NOT NULL,
  board_type TEXT NOT NULL,
  top_list JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(period_start, period_end, board_type)
);

-- 14. Admin operation logs
CREATE TABLE IF NOT EXISTS admin_operation_logs (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  admin_id TEXT NOT NULL REFERENCES profiles(id),
  operation_type TEXT NOT NULL,
  target_user_id TEXT REFERENCES profiles(id),
  details TEXT,
  reason TEXT,
  -- v3.9: Timezone support
  timezone TEXT DEFAULT 'UTC',
  created_at_local TIMESTAMP,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_admin_logs_created_at ON admin_operation_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_logs_operation_type ON admin_operation_logs(operation_type);
CREATE INDEX IF NOT EXISTS idx_admin_logs_admin_id ON admin_operation_logs(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_logs_target_user ON admin_operation_logs(target_user_id);

-- 15. User events
CREATE TABLE IF NOT EXISTS user_events (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id TEXT REFERENCES profiles(id),
  event_type TEXT NOT NULL,
  properties JSONB DEFAULT '{}',
  session_id TEXT,
  -- v3.9: Timezone support
  timezone TEXT DEFAULT 'UTC',
  created_at_local TIMESTAMP,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_user_events_created_at ON user_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_events_event_type ON user_events(event_type);
CREATE INDEX IF NOT EXISTS idx_user_events_user_id ON user_events(user_id);
CREATE INDEX IF NOT EXISTS idx_user_events_session ON user_events(session_id);
CREATE INDEX IF NOT EXISTS idx_user_events_properties ON user_events USING gin(properties);

-- 16. Analytics events (v3.4 + v3.11 enhancements)
CREATE TABLE IF NOT EXISTS analytics_events (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id TEXT,
  event_type TEXT NOT NULL,
  event_name TEXT,  -- v3.11: Normalized event name
  event_level TEXT,
  event_data JSONB NOT NULL DEFAULT '{}',
  context JSONB DEFAULT '{}',  -- v3.11: Rich context (device, geo, etc.)
  session_id TEXT,
  -- v3.9: Timezone support
  timezone TEXT DEFAULT 'UTC',
  created_at_local TIMESTAMP,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_analytics_events_user_id ON analytics_events(user_id);
CREATE INDEX IF NOT EXISTS idx_analytics_events_event_type ON analytics_events(event_type);
CREATE INDEX IF NOT EXISTS idx_analytics_events_event_name ON analytics_events(event_name);
CREATE INDEX IF NOT EXISTS idx_analytics_events_created_at ON analytics_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analytics_events_session_id ON analytics_events(session_id);

-- 17. Error logs
CREATE TABLE IF NOT EXISTS error_logs (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  error_id VARCHAR(100),
  error_type VARCHAR(50) NOT NULL,
  error_code VARCHAR(50),
  message TEXT NOT NULL,
  status_code INTEGER,
  endpoint VARCHAR(500),
  method VARCHAR(10),
  user_id VARCHAR(100),
  user_code VARCHAR(30),
  session_id VARCHAR(100),
  page_url TEXT,
  user_agent TEXT,
  stack_trace TEXT,
  context JSONB DEFAULT '{}',
  client_timestamp TIMESTAMPTZ,
  -- v3.9: Timezone support
  timezone TEXT DEFAULT 'UTC',
  created_at_local TIMESTAMP,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT error_logs_type_check CHECK (error_type IN ('API', 'NETWORK', 'JS_ERROR', 'UNHANDLED_REJECTION', 'REACT_ERROR', 'CORS', 'OTHER'))
);
CREATE INDEX IF NOT EXISTS idx_error_logs_created_at ON error_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_error_logs_user_id ON error_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_error_logs_user_code ON error_logs(user_code);
CREATE INDEX IF NOT EXISTS idx_error_logs_error_type ON error_logs(error_type);
CREATE INDEX IF NOT EXISTS idx_error_logs_status_code ON error_logs(status_code);
CREATE INDEX IF NOT EXISTS idx_error_logs_endpoint ON error_logs(endpoint);

-- 18. Aggregated stats
CREATE TABLE IF NOT EXISTS aggregated_stats (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  date DATE NOT NULL,
  stat_type TEXT NOT NULL,
  data JSONB NOT NULL DEFAULT '{}',
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(date, stat_type)
);
CREATE INDEX IF NOT EXISTS idx_agg_stats_date ON aggregated_stats(date DESC);
CREATE INDEX IF NOT EXISTS idx_agg_stats_type ON aggregated_stats(stat_type);
CREATE INDEX IF NOT EXISTS idx_agg_stats_date_type ON aggregated_stats(date DESC, stat_type);

-- 19. System configs (v3.10 - Refactored with correct field names)
-- Uses: key, value, value_type, config_group
DROP TABLE IF EXISTS config_audit_logs CASCADE;
DROP TABLE IF EXISTS system_configs CASCADE;

CREATE TABLE system_configs (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  value_type TEXT NOT NULL DEFAULT 'text',
  config_group TEXT NOT NULL DEFAULT 'general',
  description TEXT,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  updated_by TEXT
);
CREATE INDEX IF NOT EXISTS idx_system_configs_group ON system_configs(config_group);
CREATE INDEX IF NOT EXISTS idx_system_configs_active ON system_configs(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_system_configs_updated ON system_configs(updated_at DESC);

-- 20. Config audit logs (v3.10)
CREATE TABLE IF NOT EXISTS config_audit_logs (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  config_key TEXT NOT NULL,
  old_value TEXT,
  new_value TEXT,
  action TEXT NOT NULL,
  changed_by TEXT,
  changed_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_config_audit_key ON config_audit_logs(config_key);
CREATE INDEX IF NOT EXISTS idx_config_audit_time ON config_audit_logs(changed_at DESC);

-- 21. Content reports
CREATE TABLE IF NOT EXISTS content_reports (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  reporter_id TEXT NOT NULL REFERENCES profiles(id),
  listing_id UUID NOT NULL REFERENCES marketplace_listings(id),
  reason TEXT NOT NULL,
  status TEXT DEFAULT 'pending',
  admin_response TEXT,
  reviewed_by TEXT REFERENCES profiles(id),
  reviewed_at TIMESTAMPTZ,
  -- v3.9: Timezone support
  timezone TEXT DEFAULT 'UTC',
  created_at_local TIMESTAMP,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_reports_status ON content_reports(status);
CREATE INDEX IF NOT EXISTS idx_reports_listing_id ON content_reports(listing_id);
CREATE INDEX IF NOT EXISTS idx_reports_reporter_id ON content_reports(reporter_id);
CREATE INDEX IF NOT EXISTS idx_reports_created_at ON content_reports(created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_reports_unique_user_listing 
  ON content_reports(reporter_id, listing_id) 
  WHERE status IN ('pending', 'reviewed');

-- 22. Asset prompt templates
CREATE TABLE IF NOT EXISTS asset_prompt_templates (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  who_type TEXT,
  who_custom TEXT,
  what_type TEXT,
  what_custom TEXT,
  where_type TEXT,
  where_custom TEXT,
  style TEXT DEFAULT 'cartoon',
  moods TEXT[] DEFAULT '{warm}',
  aspect_ratio TEXT DEFAULT 'square',
  creativity_level REAL DEFAULT 0.3,
  negative_prompt TEXT,
  use_count INT DEFAULT 0,
  last_used_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_asset_prompt_templates_user ON asset_prompt_templates(user_id);
CREATE INDEX IF NOT EXISTS idx_asset_prompt_templates_usage ON asset_prompt_templates(user_id, use_count DESC);

-- 23. Page prompt templates
CREATE TABLE IF NOT EXISTS page_prompt_templates (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id TEXT NOT NULL,
  name TEXT NOT NULL,
  layout TEXT DEFAULT 'image_top',
  story_theme TEXT,
  main_character TEXT,
  style TEXT DEFAULT 'cartoon',
  creativity_level REAL DEFAULT 0.3,
  negative_prompt TEXT,
  generation_mode TEXT DEFAULT 'guided',
  use_count INTEGER DEFAULT 0,
  last_used_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_page_prompt_templates_user ON page_prompt_templates(user_id);
CREATE INDEX IF NOT EXISTS idx_page_prompt_templates_usage ON page_prompt_templates(user_id, use_count DESC);

-- ==========================================
-- Part 1.5: v3.12 Analytics Aggregation Tables
-- ==========================================

-- 24. Daily metrics aggregation
CREATE TABLE IF NOT EXISTS analytics_daily_metrics (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  metric_date DATE NOT NULL UNIQUE,
  -- User metrics
  dau INT DEFAULT 0,
  new_users INT DEFAULT 0,
  returning_users INT DEFAULT 0,
  -- Engagement metrics
  total_sessions INT DEFAULT 0,
  avg_session_duration_sec INT DEFAULT 0,
  pages_per_session REAL DEFAULT 0,
  -- AI usage
  ai_generations INT DEFAULT 0,
  ai_credits_used INT DEFAULT 0,
  -- Marketplace
  marketplace_purchases INT DEFAULT 0,
  marketplace_revenue INT DEFAULT 0,
  -- Projects
  projects_created INT DEFAULT 0,
  projects_exported INT DEFAULT 0,
  -- Raw data for drill-down
  raw_data JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_daily_metrics_date ON analytics_daily_metrics(metric_date DESC);

-- 25. Monthly metrics aggregation
CREATE TABLE IF NOT EXISTS analytics_monthly_metrics (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  metric_month DATE NOT NULL UNIQUE,
  -- User metrics
  mau INT DEFAULT 0,
  new_users INT DEFAULT 0,
  churned_users INT DEFAULT 0,
  -- Revenue metrics
  mrr DECIMAL(12,2) DEFAULT 0,
  arr DECIMAL(12,2) DEFAULT 0,
  arpu DECIMAL(8,2) DEFAULT 0,
  -- Conversion
  trial_to_paid_rate REAL DEFAULT 0,
  free_to_paid_rate REAL DEFAULT 0,
  -- Tier distribution
  tier_distribution JSONB DEFAULT '{}',
  -- Raw data
  raw_data JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_monthly_metrics_month ON analytics_monthly_metrics(metric_month DESC);

-- 26. User cohorts
CREATE TABLE IF NOT EXISTS analytics_user_cohorts (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id TEXT REFERENCES profiles(id),
  cohort_date DATE NOT NULL,
  cohort_type TEXT NOT NULL DEFAULT 'signup',
  first_action_at TIMESTAMPTZ,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, cohort_type)
);
CREATE INDEX IF NOT EXISTS idx_user_cohorts_date ON analytics_user_cohorts(cohort_date);
CREATE INDEX IF NOT EXISTS idx_user_cohorts_type ON analytics_user_cohorts(cohort_type);

-- 27. Cohort retention
CREATE TABLE IF NOT EXISTS analytics_cohort_retention (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  cohort_date DATE NOT NULL,
  cohort_type TEXT NOT NULL DEFAULT 'week',
  cohort_size INT DEFAULT 0,
  retention_d1 REAL DEFAULT 0,
  retention_d7 REAL DEFAULT 0,
  retention_d14 REAL DEFAULT 0,
  retention_d30 REAL DEFAULT 0,
  retention_d60 REAL DEFAULT 0,
  retention_d90 REAL DEFAULT 0,
  raw_data JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(cohort_date, cohort_type)
);
CREATE INDEX IF NOT EXISTS idx_cohort_retention_date ON analytics_cohort_retention(cohort_date DESC);

-- 28. Error summary aggregation
CREATE TABLE IF NOT EXISTS analytics_error_summary (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  summary_date DATE NOT NULL,
  error_type TEXT NOT NULL,
  error_code TEXT,
  endpoint TEXT,
  occurrence_count INT DEFAULT 0,
  affected_users INT DEFAULT 0,
  sample_message TEXT,
  sample_request_id TEXT,
  trend_vs_previous REAL DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(summary_date, error_type, error_code, endpoint)
);
CREATE INDEX IF NOT EXISTS idx_error_summary_date ON analytics_error_summary(summary_date DESC);
CREATE INDEX IF NOT EXISTS idx_error_summary_type ON analytics_error_summary(error_type);

-- 29. Funnel metrics
CREATE TABLE IF NOT EXISTS analytics_funnel_metrics (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  metric_date DATE NOT NULL,
  funnel_type TEXT NOT NULL DEFAULT 'main',
  stage_visitors INT DEFAULT 0,
  stage_signups INT DEFAULT 0,
  stage_activated INT DEFAULT 0,
  stage_engaged INT DEFAULT 0,
  stage_converted INT DEFAULT 0,
  conversion_rates JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(metric_date, funnel_type)
);
CREATE INDEX IF NOT EXISTS idx_funnel_metrics_date ON analytics_funnel_metrics(metric_date DESC);

-- ==========================================
-- Part 1.6: Dashboard Optimized Indexes
-- ==========================================

CREATE INDEX IF NOT EXISTS idx_projects_user_deleted ON projects(user_id, is_deleted, deleted_at);
CREATE INDEX IF NOT EXISTS idx_projects_user_purchased ON projects(user_id, is_purchased) WHERE is_purchased = true;
CREATE INDEX IF NOT EXISTS idx_projects_user_listing_status ON projects(user_id, listing_status) WHERE listing_status IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_projects_trash ON projects(user_id, is_deleted, is_hidden_from_trash) 
  WHERE is_deleted = true AND is_hidden_from_trash = false;
CREATE INDEX IF NOT EXISTS idx_projects_marketplace_listing ON projects(marketplace_listing_id) WHERE marketplace_listing_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_projects_deleted_at ON projects(deleted_at);

CREATE INDEX IF NOT EXISTS idx_assets_user_deleted ON assets(user_id, is_deleted);
CREATE INDEX IF NOT EXISTS idx_assets_user_purchased ON assets(user_id, is_purchased) WHERE is_purchased = true;
CREATE INDEX IF NOT EXISTS idx_assets_user_listing_status ON assets(user_id, listing_status) WHERE listing_status IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_assets_trash ON assets(user_id, is_deleted, is_hidden_from_trash)
  WHERE is_deleted = true AND is_hidden_from_trash = false;
CREATE INDEX IF NOT EXISTS idx_assets_marketplace_listing ON assets(marketplace_listing_id) WHERE marketplace_listing_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_listings_resource_id ON marketplace_listings(resource_id) WHERE resource_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_marketplace_listings_resource_id ON marketplace_listings(resource_id);
CREATE INDEX IF NOT EXISTS idx_listings_seller_public ON marketplace_listings(seller_id, is_public, is_deleted);
CREATE INDEX IF NOT EXISTS idx_marketplace_listings_version ON marketplace_listings(version);

-- ==========================================
-- Part 2: RLS Policy Configuration
-- ==========================================

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
ALTER TABLE config_audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE asset_prompt_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE page_prompt_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_daily_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_monthly_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_user_cohorts ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_cohort_retention ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_error_summary ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_funnel_metrics ENABLE ROW LEVEL SECURITY;

-- Admin check function
CREATE OR REPLACE FUNCTION is_admin() RETURNS BOOLEAN LANGUAGE sql SECURITY DEFINER AS $$
SELECT EXISTS (
  SELECT 1 FROM profiles
  WHERE id = (SELECT auth.jwt() ->> 'sub') AND role = 'admin'
);
$$;

-- [Profiles]
DROP POLICY IF EXISTS "View profiles" ON profiles;
CREATE POLICY "View profiles" ON profiles FOR SELECT
USING ((SELECT auth.jwt() ->> 'sub') = id OR is_admin());

DROP POLICY IF EXISTS "Update profiles" ON profiles;
CREATE POLICY "Update profiles" ON profiles FOR UPDATE
USING ((SELECT auth.jwt() ->> 'sub') = id);

DROP POLICY IF EXISTS "Insert profiles" ON profiles;
CREATE POLICY "Insert profiles" ON profiles FOR INSERT
WITH CHECK ((SELECT auth.jwt() ->> 'sub') = id);

-- [User Discounts]
DROP POLICY IF EXISTS "Users read own discounts" ON user_discounts;
CREATE POLICY "Users read own discounts" ON user_discounts FOR SELECT
USING ((SELECT auth.jwt() ->> 'sub') = user_id OR is_admin());

-- [Projects]
DROP POLICY IF EXISTS "Users can CRUD own projects" ON projects;
CREATE POLICY "Users can CRUD own projects" ON projects FOR ALL
USING ((SELECT auth.jwt() ->> 'sub') = user_id);

-- [Marketplace Listings]
DROP POLICY IF EXISTS "Read Listings" ON marketplace_listings;
CREATE POLICY "Read Listings" ON marketplace_listings FOR SELECT
USING (is_public = true OR (SELECT auth.jwt() ->> 'sub') = seller_id OR is_admin());

DROP POLICY IF EXISTS "Manage Listings" ON marketplace_listings;
CREATE POLICY "Manage Listings" ON marketplace_listings FOR UPDATE
USING ((SELECT auth.jwt() ->> 'sub') = seller_id);

DROP POLICY IF EXISTS "Insert Listings" ON marketplace_listings;
CREATE POLICY "Insert Listings" ON marketplace_listings FOR INSERT
WITH CHECK ((SELECT auth.jwt() ->> 'sub') = seller_id);

-- [User Purchases]
DROP POLICY IF EXISTS "Read Purchases" ON user_purchases;
CREATE POLICY "Read Purchases" ON user_purchases FOR SELECT
USING ((SELECT auth.jwt() ->> 'sub') = user_id);

DROP POLICY IF EXISTS "Insert Purchases" ON user_purchases;
CREATE POLICY "Insert Purchases" ON user_purchases FOR INSERT
WITH CHECK ((SELECT auth.jwt() ->> 'sub') = user_id);

-- [Assets]
DROP POLICY IF EXISTS "Users can CRUD own assets" ON assets;
CREATE POLICY "Users can CRUD own assets" ON assets FOR ALL
USING ((SELECT auth.jwt() ->> 'sub') = user_id);

-- [Notifications]
DROP POLICY IF EXISTS "Read Notifications" ON notifications;
CREATE POLICY "Read Notifications" ON notifications FOR SELECT
USING (user_id = (SELECT auth.jwt() ->> 'sub') OR user_id IS NULL);

-- [Credit Transactions]
DROP POLICY IF EXISTS "Users view own txs or Admin view all" ON credit_transactions;
CREATE POLICY "Users view own txs or Admin view all" ON credit_transactions FOR SELECT
USING ((SELECT auth.jwt() ->> 'sub') = user_id OR is_admin());

-- [System Resources]
DROP POLICY IF EXISTS "Public can view system resources" ON system_resources;
CREATE POLICY "Public can view system resources" ON system_resources FOR SELECT
USING (true);

-- [Activity Logs]
DROP POLICY IF EXISTS "Users can insert own logs" ON activity_logs;
CREATE POLICY "Users can insert own logs" ON activity_logs FOR INSERT
WITH CHECK ((SELECT auth.jwt() ->> 'sub') = user_id);

DROP POLICY IF EXISTS "Users view own logs or Admin view all" ON activity_logs;
CREATE POLICY "Users view own logs or Admin view all" ON activity_logs FOR SELECT
USING ((SELECT auth.jwt() ->> 'sub') = user_id OR is_admin());

-- [Support Tickets]
DROP POLICY IF EXISTS "Users CRUD own tickets or Admin manage all" ON support_tickets;
CREATE POLICY "Users CRUD own tickets or Admin manage all" ON support_tickets FOR ALL
USING ((SELECT auth.jwt() ->> 'sub') = user_id OR is_admin());

-- [Listing Usages]
DROP POLICY IF EXISTS "Users can insert own usage" ON listing_usages;
CREATE POLICY "Users can insert own usage" ON listing_usages FOR INSERT
WITH CHECK ((SELECT auth.jwt() ->> 'sub') = used_by_user_id);

DROP POLICY IF EXISTS "Users view own usage or Admin view all" ON listing_usages;
CREATE POLICY "Users view own usage or Admin view all" ON listing_usages FOR SELECT
USING ((SELECT auth.jwt() ->> 'sub') = used_by_user_id OR is_admin());

-- [Leaderboard Snapshots]
DROP POLICY IF EXISTS "Public can view leaderboard" ON leaderboard_snapshots;
CREATE POLICY "Public can view leaderboard" ON leaderboard_snapshots FOR SELECT
USING (true);

-- [Service role access policies for backend-only tables]
DROP POLICY IF EXISTS "Service role full access to admin_logs" ON admin_operation_logs;
CREATE POLICY "Service role full access to admin_logs" ON admin_operation_logs FOR ALL
TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role full access to user_events" ON user_events;
CREATE POLICY "Service role full access to user_events" ON user_events FOR ALL
TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role insert analytics events" ON analytics_events;
CREATE POLICY "Service role insert analytics events" ON analytics_events FOR INSERT
TO service_role WITH CHECK (true);

DROP POLICY IF EXISTS "Service role read analytics events" ON analytics_events;
CREATE POLICY "Service role read analytics events" ON analytics_events FOR SELECT
TO service_role USING (true);

DROP POLICY IF EXISTS "Allow insert error logs" ON error_logs;
CREATE POLICY "Allow insert error logs" ON error_logs FOR INSERT WITH CHECK (true);

DROP POLICY IF EXISTS "Service role read error logs" ON error_logs;
CREATE POLICY "Service role read error logs" ON error_logs FOR SELECT
TO service_role USING (true);

DROP POLICY IF EXISTS "Service role full access to aggregated_stats" ON aggregated_stats;
CREATE POLICY "Service role full access to aggregated_stats" ON aggregated_stats FOR ALL
TO service_role USING (true) WITH CHECK (true);

-- [System Configs] (v3.10 - public read for active, admin write)
DROP POLICY IF EXISTS "Public can read active configs" ON system_configs;
CREATE POLICY "Public can read active configs" ON system_configs FOR SELECT
USING (is_active = true);

DROP POLICY IF EXISTS "Service role full access to system_configs" ON system_configs;
CREATE POLICY "Service role full access to system_configs" ON system_configs FOR ALL
TO service_role USING (true) WITH CHECK (true);

-- [Config Audit Logs]
DROP POLICY IF EXISTS "Service role access to config_audit_logs" ON config_audit_logs;
CREATE POLICY "Service role access to config_audit_logs" ON config_audit_logs FOR ALL
TO service_role USING (true) WITH CHECK (true);

-- [Content Reports]
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

-- [Template tables]
DROP POLICY IF EXISTS "Service role full access to asset prompt templates" ON asset_prompt_templates;
CREATE POLICY "Service role full access to asset prompt templates" ON asset_prompt_templates FOR ALL
TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role full access to page prompt templates" ON page_prompt_templates;
CREATE POLICY "Service role full access to page prompt templates" ON page_prompt_templates FOR ALL
TO service_role USING (true) WITH CHECK (true);

-- [Analytics aggregation tables]
DROP POLICY IF EXISTS "Service role full access to daily metrics" ON analytics_daily_metrics;
CREATE POLICY "Service role full access to daily metrics" ON analytics_daily_metrics FOR ALL
TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role full access to monthly metrics" ON analytics_monthly_metrics;
CREATE POLICY "Service role full access to monthly metrics" ON analytics_monthly_metrics FOR ALL
TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role full access to user cohorts" ON analytics_user_cohorts;
CREATE POLICY "Service role full access to user cohorts" ON analytics_user_cohorts FOR ALL
TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role full access to cohort retention" ON analytics_cohort_retention;
CREATE POLICY "Service role full access to cohort retention" ON analytics_cohort_retention FOR ALL
TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role full access to error summary" ON analytics_error_summary;
CREATE POLICY "Service role full access to error summary" ON analytics_error_summary FOR ALL
TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role full access to funnel metrics" ON analytics_funnel_metrics;
CREATE POLICY "Service role full access to funnel metrics" ON analytics_funnel_metrics FOR ALL
TO service_role USING (true) WITH CHECK (true);

-- ==========================================
-- Part 3: Dashboard Views
-- ==========================================

CREATE OR REPLACE VIEW dashboard_projects AS
SELECT 
  p.id, p.user_id, p.title, p.thumbnail_url, p.canvas_data,
  p.is_deleted, p.deleted_at, p.is_hidden_from_trash, p.is_purchased,
  p.source_listing_id, p.origin_owner_id, p.listing_status,
  p.marketplace_listing_id, p.contains_locked_elements, p.created_at, p.updated_at,
  ml.id as listing_id, ml.title as listing_title, ml.price_credits as listing_price,
  ml.is_public as listing_is_public, ml.moderation_status as listing_moderation_status,
  ml.sales_count as listing_sales_count, ml.unique_buyers_count as listing_unique_buyers,
  ml.total_revenue as listing_total_revenue, ml.usage_count as listing_usage_count,
  op.username as origin_owner_username, op.avatar_url as origin_owner_avatar
FROM projects p
LEFT JOIN marketplace_listings ml ON p.marketplace_listing_id = ml.id
LEFT JOIN profiles op ON p.origin_owner_id = op.id;

CREATE OR REPLACE VIEW dashboard_assets AS
SELECT 
  a.id, a.user_id, a.url, a.type, a.prompt, a.description, a.metadata,
  a.is_deleted, a.deleted_at, a.is_hidden_from_trash, a.is_purchased,
  a.source_listing_id, a.origin_owner_id, a.listing_status,
  a.marketplace_listing_id, a.project_id, a.created_at,
  ml.id as listing_id, ml.title as listing_title, ml.description as listing_description,
  ml.price_credits as listing_price, ml.is_public as listing_is_public,
  ml.moderation_status as listing_moderation_status, ml.sales_count as listing_sales_count,
  ml.unique_buyers_count as listing_unique_buyers, ml.total_revenue as listing_total_revenue,
  ml.usage_count as listing_usage_count,
  op.username as origin_owner_username, op.avatar_url as origin_owner_avatar
FROM assets a
LEFT JOIN marketplace_listings ml ON a.marketplace_listing_id = ml.id
LEFT JOIN profiles op ON a.origin_owner_id = op.id;

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

-- ==========================================
-- Part 4: Materialized Views for Analytics
-- ==========================================

-- DAU Trend with 7-day moving average
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_dau_trend AS
SELECT 
  metric_date,
  dau,
  new_users,
  returning_users,
  AVG(dau) OVER (ORDER BY metric_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as dau_7day_avg
FROM analytics_daily_metrics
ORDER BY metric_date DESC;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_dau_trend_date ON mv_dau_trend(metric_date);

-- Top Errors
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_top_errors AS
SELECT 
  error_type,
  error_code,
  endpoint,
  SUM(occurrence_count) as total_occurrences,
  SUM(affected_users) as total_affected_users,
  MAX(summary_date) as last_seen
FROM analytics_error_summary
WHERE summary_date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY error_type, error_code, endpoint
ORDER BY total_occurrences DESC
LIMIT 100;

-- Daily Event Summary
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_daily_event_summary AS
SELECT 
  DATE(created_at) as event_date,
  COALESCE(event_name, event_type) as event_name,
  COUNT(*) as event_count,
  COUNT(DISTINCT user_id) as unique_users,
  COUNT(DISTINCT session_id) as unique_sessions
FROM analytics_events
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at), COALESCE(event_name, event_type)
ORDER BY event_date DESC, event_count DESC;

CREATE INDEX IF NOT EXISTS idx_mv_daily_event_date ON mv_daily_event_summary(event_date);

-- ==========================================
-- Part 5: Helper Functions & Triggers
-- ==========================================

-- Sync listing status
CREATE OR REPLACE FUNCTION sync_listing_status()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.resource_type = 'project' AND NEW.resource_id IS NOT NULL THEN
    UPDATE projects SET listing_status = NEW.moderation_status, marketplace_listing_id = NEW.id
    WHERE id = NEW.resource_id::uuid;
  END IF;
  IF NEW.resource_type = 'asset' AND NEW.resource_id IS NOT NULL THEN
    UPDATE assets SET listing_status = NEW.moderation_status, marketplace_listing_id = NEW.id
    WHERE id = NEW.resource_id::uuid;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_sync_listing_status ON marketplace_listings;
CREATE TRIGGER trigger_sync_listing_status
  AFTER INSERT OR UPDATE OF moderation_status, is_public, is_deleted
  ON marketplace_listings FOR EACH ROW EXECUTE FUNCTION sync_listing_status();

-- Update seller stats on purchase
CREATE OR REPLACE FUNCTION update_seller_stats_on_purchase()
RETURNS TRIGGER AS $$
DECLARE v_listing_price INT; v_seller_revenue INT;
BEGIN
  SELECT price_credits INTO v_listing_price FROM marketplace_listings WHERE id = NEW.listing_id;
  v_seller_revenue := FLOOR(v_listing_price * 0.9);
  UPDATE marketplace_listings SET 
    sales_count = sales_count + 1,
    unique_buyers_count = (SELECT COUNT(DISTINCT user_id) FROM user_purchases WHERE listing_id = NEW.listing_id),
    total_revenue = total_revenue + v_seller_revenue
  WHERE id = NEW.listing_id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_seller_stats ON user_purchases;
CREATE TRIGGER trigger_update_seller_stats
  AFTER INSERT ON user_purchases FOR EACH ROW EXECUTE FUNCTION update_seller_stats_on_purchase();

-- Set deleted timestamp
CREATE OR REPLACE FUNCTION set_deleted_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.is_deleted = true AND OLD.is_deleted = false THEN NEW.deleted_at = NOW(); END IF;
  IF NEW.is_deleted = false AND OLD.is_deleted = true THEN NEW.deleted_at = NULL; NEW.is_hidden_from_trash = false; END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_projects_deleted_at ON projects;
CREATE TRIGGER trigger_projects_deleted_at
  BEFORE UPDATE OF is_deleted ON projects FOR EACH ROW EXECUTE FUNCTION set_deleted_timestamp();

DROP TRIGGER IF EXISTS trigger_assets_deleted_at ON assets;
CREATE TRIGGER trigger_assets_deleted_at
  BEFORE UPDATE OF is_deleted ON assets FOR EACH ROW EXECUTE FUNCTION set_deleted_timestamp();

-- Prevent credit modification (append-only)
CREATE OR REPLACE FUNCTION prevent_credit_modification()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'credit_transactions is append-only. For refunds, insert a negative amount record.';
  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS prevent_credit_update ON credit_transactions;
CREATE TRIGGER prevent_credit_update
  BEFORE UPDATE ON credit_transactions FOR EACH ROW EXECUTE FUNCTION prevent_credit_modification();

DROP TRIGGER IF EXISTS prevent_credit_delete ON credit_transactions;
CREATE TRIGGER prevent_credit_delete
  BEFORE DELETE ON credit_transactions FOR EACH ROW EXECUTE FUNCTION prevent_credit_modification();

-- Auto-update timestamps
CREATE OR REPLACE FUNCTION update_timestamp() RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_reports_updated_at ON content_reports;
CREATE TRIGGER trigger_reports_updated_at BEFORE UPDATE ON content_reports FOR EACH ROW EXECUTE FUNCTION update_timestamp();

DROP TRIGGER IF EXISTS trigger_asset_prompt_templates_updated_at ON asset_prompt_templates;
CREATE TRIGGER trigger_asset_prompt_templates_updated_at BEFORE UPDATE ON asset_prompt_templates FOR EACH ROW EXECUTE FUNCTION update_timestamp();

DROP TRIGGER IF EXISTS trigger_page_prompt_templates_updated_at ON page_prompt_templates;
CREATE TRIGGER trigger_page_prompt_templates_updated_at BEFORE UPDATE ON page_prompt_templates FOR EACH ROW EXECUTE FUNCTION update_timestamp();

DROP TRIGGER IF EXISTS trigger_system_configs_updated_at ON system_configs;
CREATE TRIGGER trigger_system_configs_updated_at BEFORE UPDATE ON system_configs FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- ==========================================
-- Part 6: Helper Functions (System Config)
-- ==========================================

-- Get config by key with fallback
CREATE OR REPLACE FUNCTION get_config(config_key TEXT, default_value TEXT DEFAULT NULL)
RETURNS TEXT LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE result TEXT;
BEGIN
  SELECT value INTO result FROM system_configs WHERE key = config_key AND is_active = true;
  RETURN COALESCE(result, default_value);
END;
$$;

-- Get configs by group
CREATE OR REPLACE FUNCTION get_configs_by_group(group_name TEXT)
RETURNS TABLE(key TEXT, value TEXT, value_type TEXT, description TEXT) LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  RETURN QUERY SELECT sc.key, sc.value, sc.value_type, sc.description
  FROM system_configs sc WHERE sc.config_group = group_name AND sc.is_active = true ORDER BY sc.key;
END;
$$;

-- Get rate limit config
CREATE OR REPLACE FUNCTION get_rate_limit_config(p_config_key TEXT)
RETURNS JSONB AS $$
DECLARE v_config JSONB;
BEGIN
  SELECT value::JSONB INTO v_config FROM system_configs WHERE key = p_config_key AND is_active = true;
  IF v_config IS NULL THEN
    SELECT value::JSONB INTO v_config FROM system_configs WHERE key = 'rate_limit.global.default' AND is_active = true;
  END IF;
  RETURN COALESCE(v_config, '{"limit": 100, "window": "minute", "enabled": true}'::JSONB);
END;
$$ LANGUAGE plpgsql;

-- Aggregated stats helpers
CREATE OR REPLACE FUNCTION get_latest_stats(p_stat_type VARCHAR) RETURNS JSONB LANGUAGE plpgsql AS $$
DECLARE result JSONB;
BEGIN
  SELECT data INTO result FROM aggregated_stats WHERE stat_type = p_stat_type ORDER BY date DESC LIMIT 1;
  RETURN COALESCE(result, '{}'::JSONB);
END;
$$;

CREATE OR REPLACE FUNCTION get_stats_range(p_stat_type VARCHAR, p_start_date DATE, p_end_date DATE DEFAULT CURRENT_DATE)
RETURNS TABLE (date DATE, data JSONB) LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY SELECT a.date, a.data FROM aggregated_stats a
  WHERE a.stat_type = p_stat_type AND a.date >= p_start_date AND a.date <= p_end_date ORDER BY a.date ASC;
END;
$$;

-- Refresh materialized views
CREATE OR REPLACE FUNCTION refresh_analytics_views() RETURNS void LANGUAGE plpgsql AS $$
BEGIN
  REFRESH MATERIALIZED VIEW CONCURRENTLY mv_dau_trend;
  REFRESH MATERIALIZED VIEW mv_top_errors;
  REFRESH MATERIALIZED VIEW mv_daily_event_summary;
END;
$$;

-- ==========================================
-- Part 7: Core Optimized Indexes
-- ==========================================

CREATE INDEX IF NOT EXISTS idx_profiles_tier ON profiles(tier);
CREATE INDEX IF NOT EXISTS idx_profiles_created_at ON profiles(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_profiles_subscription_status ON profiles(subscription_status);
CREATE INDEX IF NOT EXISTS idx_credit_tx_bucket ON credit_transactions(bucket);
CREATE INDEX IF NOT EXISTS idx_credit_tx_type ON credit_transactions(type);
CREATE INDEX IF NOT EXISTS idx_credit_tx_created_at ON credit_transactions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_logs_action ON activity_logs(action);
CREATE INDEX IF NOT EXISTS idx_activity_logs_created_at ON activity_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(notification_type);

-- ==========================================
-- Part 8: Default System Configs (v3.10 format)
-- ==========================================

INSERT INTO system_configs (key, value, value_type, config_group, description) VALUES
  -- Rate Limits
  ('rate_limit.payment.checkout', '{"limit": 5, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Checkout API limit'),
  ('rate_limit.payment.portal', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Billing portal limit'),
  ('rate_limit.marketplace.purchase', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Marketplace purchase limit'),
  ('rate_limit.generate.story', '{"limit": 20, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'AI story generation limit'),
  ('rate_limit.generate.images', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'AI image generation limit'),
  ('rate_limit.tools.ocr', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'OCR limit'),
  ('rate_limit.export.pdf', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'PDF export limit'),
  ('rate_limit.export.zip', '{"limit": 5, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'ZIP export limit'),
  ('rate_limit.export.preview', '{"limit": 20, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Preview generation limit'),
  ('rate_limit.projects.create', '{"limit": 20, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Project creation limit'),
  ('rate_limit.assets.upload', '{"limit": 20, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Asset upload limit'),
  ('rate_limit.marketplace.publish', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Listing publish limit'),
  ('rate_limit.support.email', '{"limit": 3, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Support ticket limit'),
  ('rate_limit.contact.form', '{"limit": 3, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Contact form limit'),
  ('rate_limit.feedback.submit', '{"limit": 3, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Feedback submission limit'),
  ('rate_limit.admin.credits', '{"limit": 30, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin credit adjustment limit'),
  ('rate_limit.admin.tier', '{"limit": 30, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin tier update limit'),
  ('rate_limit.admin.refund', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin refund limit'),
  ('rate_limit.admin.subscription', '{"limit": 10, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin subscription ops limit'),
  ('rate_limit.admin.broadcast', '{"limit": 5, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin broadcast limit'),
  ('rate_limit.admin.search', '{"limit": 60, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Admin search limit'),
  ('rate_limit.marketplace.list', '{"limit": 60, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Marketplace listing limit'),
  ('rate_limit.analytics.events', '{"limit": 60, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Analytics event ingestion limit'),
  ('rate_limit.global.default', '{"limit": 100, "window": "minute", "enabled": true}', 'json', 'rate_limit', 'Global default limit'),
  ('rate_limit.global.enabled', '{"enabled": true}', 'json', 'rate_limit', 'Enable/disable global rate limit'),
  
  -- Analytics configuration
  ('analytics.enabled', '{"enabled": true}', 'json', 'analytics', 'Enable analytics tracking'),
  ('analytics.sampling_rate', '{"critical": 1.0, "important": 1.0, "normal": 0.3, "debug": 0.0}', 'json', 'analytics', 'Event sampling rates'),
  ('analytics.min_level', '{"level": "normal"}', 'json', 'analytics', 'Minimum tracking level'),
  
  -- Feature Flags
  ('FEATURE_AI_GENERATION', 'true', 'boolean', 'feature_flag', 'Enable AI image generation'),
  ('FEATURE_MARKETPLACE', 'true', 'boolean', 'feature_flag', 'Enable marketplace'),
  ('FEATURE_OCR', 'true', 'boolean', 'feature_flag', 'Enable OCR/Smart Scan'),
  ('FEATURE_ZIP_EXPORT', 'true', 'boolean', 'feature_flag', 'Enable ZIP export'),
  
  -- Limits
  ('FREE_PROJECT_LIMIT', '1', 'number', 'limits', 'Max projects for free tier'),
  ('STARTER_PROJECT_LIMIT', '20', 'number', 'limits', 'Max projects for starter tier'),
  ('PRO_PROJECT_LIMIT', '200', 'number', 'limits', 'Max projects for pro tier'),
  ('MAX_UPLOAD_FILE_SIZE_MB', '5', 'number', 'limits', 'Max file upload size in MB'),
  ('MAX_LISTING_PRICE', '500', 'number', 'limits', 'Max marketplace listing price'),
  
  -- Credits
  ('CREDITS_PER_IMAGE', '5', 'number', 'credits', 'Credits per AI image'),
  ('CREDITS_PER_OCR', '5', 'number', 'credits', 'Credits per OCR'),
  ('CREDITS_PER_AI_DESIGN_PAGE', '5', 'number', 'credits', 'Credits per AI design page'),
  ('SIGNUP_BONUS_CREDITS', '50', 'number', 'credits', 'Signup bonus credits'),
  
  -- Pricing
  ('STARTER_PLAN_PRICE', '14.9', 'number', 'pricing', 'Starter monthly price'),
  ('PRO_PLAN_PRICE', '29.9', 'number', 'pricing', 'Pro monthly price'),
  ('STARTER_MONTHLY_CREDITS', '500', 'number', 'pricing', 'Starter monthly credits'),
  ('PRO_MONTHLY_CREDITS', '1000', 'number', 'pricing', 'Pro monthly credits'),
  
  -- UI Text
  ('UI_UPGRADE_CTA', 'Upgrade Now', 'text', 'ui', 'Upgrade button text'),
  ('UI_TRIAL_EXPIRED', 'Your 7-day trial period has expired. This project is read-only.', 'text', 'ui', 'Trial expired message'),
  ('UI_AI_TYPING_INDICATOR', 'AI is thinking...', 'text', 'ui', 'AI typing indicator text in Help Center'),
  
  -- Marketing
  ('HOME_HERO_TITLE', 'Create Beautiful 8-Page Zines in Minutes', 'text', 'marketing', 'Homepage hero title'),
  ('HOME_HERO_SUBTITLE', 'AI-powered story generation meets easy drag-and-drop editing.', 'text', 'marketing', 'Homepage hero subtitle'),
  
  -- Tooltip Text
  ('TOOLTIP_DELETE', 'Delete', 'text', 'tooltip', 'Delete button tooltip when enabled'),
  ('TOOLTIP_DELETE_DISABLED', 'Unpublish first to delete', 'text', 'tooltip', 'Delete button tooltip when project is published (disabled state)')

ON CONFLICT (key) DO UPDATE SET
  value = EXCLUDED.value,
  value_type = EXCLUDED.value_type,
  config_group = EXCLUDED.config_group,
  description = EXCLUDED.description,
  updated_at = NOW();

-- ==========================================
-- Part 8: Holiday Themes & Marketing Campaigns (v3.13)
-- ==========================================

-- Holiday themes table
CREATE TABLE IF NOT EXISTS holiday_themes (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    date_rule JSONB NOT NULL,
    theme_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    priority INTEGER DEFAULT 50,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_holiday_themes_active ON holiday_themes(is_active, priority DESC);

-- Marketing campaigns table
CREATE TABLE IF NOT EXISTS campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    type TEXT NOT NULL,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    target_type TEXT NOT NULL DEFAULT 'all',
    target_config JSONB DEFAULT '{}'::jsonb,
    notification_channels TEXT[] DEFAULT ARRAY['banner'],
    notification_config JSONB DEFAULT '{}'::jsonb,
    start_at TIMESTAMPTZ NOT NULL,
    end_at TIMESTAMPTZ NOT NULL,
    timezone TEXT DEFAULT 'America/New_York',
    usage_limit INTEGER,
    usage_per_user INTEGER DEFAULT 1,
    usage_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'draft',
    is_active BOOLEAN DEFAULT true,
    created_by TEXT REFERENCES profiles(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status, is_active);
CREATE INDEX IF NOT EXISTS idx_campaigns_dates ON campaigns(start_at, end_at);

-- Campaign claims tracking
CREATE TABLE IF NOT EXISTS campaign_claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES profiles(id),
    credits_received INTEGER,
    claimed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(campaign_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_campaign_claims_user ON campaign_claims(user_id);

-- Campaign notification dismissals
CREATE TABLE IF NOT EXISTS campaign_dismissals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES profiles(id),
    channel TEXT NOT NULL,
    dismissed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(campaign_id, user_id, channel)
);

-- Helper function for US Thanksgiving
CREATE OR REPLACE FUNCTION calculate_us_thanksgiving(year_val INTEGER)
RETURNS DATE AS $$
DECLARE
    nov_first DATE;
    first_thursday DATE;
BEGIN
    nov_first := make_date(year_val, 11, 1);
    first_thursday := nov_first + ((4 - EXTRACT(DOW FROM nov_first)::INTEGER + 7) % 7);
    RETURN first_thursday + 21;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Helper function for Mother's Day (2nd Sunday of May)
CREATE OR REPLACE FUNCTION calculate_mothers_day(year_val INTEGER)
RETURNS DATE AS $$
DECLARE
    first_day DATE;
    first_sunday DATE;
BEGIN
    first_day := make_date(year_val, 5, 1);
    first_sunday := first_day + ((7 - EXTRACT(DOW FROM first_day)::INTEGER) % 7);
    IF EXTRACT(DOW FROM first_day) = 0 THEN
        first_sunday := first_day;
    END IF;
    RETURN first_sunday + 7;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Helper function for Father's Day (3rd Sunday of June)
CREATE OR REPLACE FUNCTION calculate_fathers_day(year_val INTEGER)
RETURNS DATE AS $$
DECLARE
    first_day DATE;
    first_sunday DATE;
BEGIN
    first_day := make_date(year_val, 6, 1);
    first_sunday := first_day + ((7 - EXTRACT(DOW FROM first_day)::INTEGER) % 7);
    IF EXTRACT(DOW FROM first_day) = 0 THEN
        first_sunday := first_day;
    END IF;
    RETURN first_sunday + 14;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Dynamic date calculator
CREATE OR REPLACE FUNCTION calculate_dynamic_date(rule_name TEXT, year_val INTEGER)
RETURNS DATE AS $$
BEGIN
    CASE rule_name
        WHEN 'us_thanksgiving' THEN
            RETURN calculate_us_thanksgiving(year_val);
        WHEN 'black_friday' THEN
            RETURN calculate_us_thanksgiving(year_val) + 1;
        WHEN 'mothers_day' THEN
            RETURN calculate_mothers_day(year_val);
        WHEN 'fathers_day' THEN
            RETURN calculate_fathers_day(year_val);
        ELSE
            RETURN NULL;
    END CASE;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- RLS for campaigns
ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaign_claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaign_dismissals ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public can view active campaigns" ON campaigns
    FOR SELECT USING (status = 'active' AND is_active = true);

CREATE POLICY "Users can view own claims" ON campaign_claims
    FOR SELECT USING (user_id = auth.uid()::text);

CREATE POLICY "Users can insert own claims" ON campaign_claims
    FOR INSERT WITH CHECK (user_id = auth.uid()::text);

CREATE POLICY "Users can manage own dismissals" ON campaign_dismissals
    FOR ALL USING (user_id = auth.uid()::text);

-- ==========================================
-- Part 9: Holiday Themes Data (v3.13 + v3.14)
-- ==========================================

-- Insert default holiday themes (US holidays + Global celebrations)
INSERT INTO holiday_themes (id, name, date_rule, theme_config, priority) VALUES

-- US Holidays
('newyear', 'New Year',
 '{"type": "fixed", "start": "12-30", "end": "01-02"}',
 '{"colors": {"primary": "#ffd700", "secondary": "#c0c0c0", "accent": "#ffffff", "banner_bg": "linear-gradient(135deg, #1a1a2e, #16213e)", "banner_text": "#ffd700"}, "badge": {"text": "🎉 Happy New Year!", "style": "sparkle"}, "decorations": {"type": "confetti", "density": "heavy"}, "banner_style": "gradient"}',
 100),

('mlk', 'Martin Luther King Jr. Day',
 '{"type": "dynamic", "rule": "mlk_day", "offset_start": -1, "offset_end": 0}',
 '{"colors": {"primary": "#1a1a1a", "secondary": "#ffffff", "accent": "#c41e3a", "banner_bg": "#1a1a1a", "banner_text": "#ffffff"}, "badge": {"text": "✊ MLK Day - Dream of Equality", "style": "default"}, "decorations": {"type": "none"}, "banner_style": "solid"}',
 60),

('valentine', 'Valentine''s Day',
 '{"type": "fixed", "start": "02-12", "end": "02-15"}',
 '{"colors": {"primary": "#ff69b4", "secondary": "#ff1493", "accent": "#dc143c", "banner_bg": "linear-gradient(135deg, #ff69b4, #ff1493)", "banner_text": "#ffffff"}, "badge": {"text": "💝 Valentine''s Day", "style": "pulse"}, "decorations": {"type": "hearts", "density": "light"}, "banner_style": "gradient"}',
 50),

('stpatrick', 'St. Patrick''s Day',
 '{"type": "fixed", "start": "03-15", "end": "03-18"}',
 '{"colors": {"primary": "#228b22", "secondary": "#32cd32", "accent": "#ffd700", "banner_bg": "#228b22", "banner_text": "#ffffff"}, "badge": {"text": "☘️ St. Patrick''s Day", "style": "default"}, "decorations": {"type": "none"}, "banner_style": "solid"}',
 40),

('july4th', 'Independence Day',
 '{"type": "fixed", "start": "07-02", "end": "07-05"}',
 '{"colors": {"primary": "#b22234", "secondary": "#3c3b6e", "accent": "#ffffff", "banner_bg": "#b22234", "banner_text": "#ffffff"}, "badge": {"text": "🇺🇸 Happy 4th of July!", "style": "default"}, "decorations": {"type": "fireworks", "density": "heavy"}, "banner_style": "striped"}',
 60),

('halloween', 'Halloween',
 '{"type": "fixed", "start": "10-28", "end": "11-01"}',
 '{"colors": {"primary": "#ff6600", "secondary": "#1a1a1a", "accent": "#9933ff", "banner_bg": "#1a1a1a", "banner_text": "#ff6600"}, "badge": {"text": "🎃 Happy Halloween!", "style": "spooky"}, "decorations": {"type": "confetti", "density": "light"}, "banner_style": "solid"}',
 70),

('thanksgiving', 'Thanksgiving',
 '{"type": "dynamic", "rule": "us_thanksgiving", "offset_start": -1, "offset_end": 1}',
 '{"colors": {"primary": "#cd853f", "secondary": "#8b4513", "accent": "#daa520", "banner_bg": "linear-gradient(135deg, #cd853f, #8b4513)", "banner_text": "#ffffff"}, "badge": {"text": "🦃 Happy Thanksgiving!", "style": "warm"}, "decorations": {"type": "none"}, "banner_style": "gradient"}',
 80),

('blackfriday', 'Black Friday',
 '{"type": "dynamic", "rule": "black_friday", "offset_start": 0, "offset_end": 3}',
 '{"colors": {"primary": "#000000", "secondary": "#1a1a1a", "accent": "#ff0000", "banner_bg": "#000000", "banner_text": "#ffffff"}, "badge": {"text": "🖤 BLACK FRIDAY DEALS!", "style": "flash"}, "decorations": {"type": "none"}, "banner_style": "solid"}',
 90),

('christmas', 'Christmas',
 '{"type": "fixed", "start": "12-20", "end": "12-26"}',
 '{"colors": {"primary": "#c41e3a", "secondary": "#228b22", "accent": "#ffd700", "banner_bg": "#c41e3a", "banner_text": "#ffffff"}, "badge": {"text": "🎄 Merry Christmas!", "style": "festive"}, "decorations": {"type": "snowflakes", "density": "medium"}, "banner_style": "striped"}',
 95),

-- Global Celebrations (v3.14)
('lunar_newyear', 'Lunar New Year',
 '{"type": "fixed", "start": "01-20", "end": "02-15"}',
 '{"colors": {"primary": "#de2910", "secondary": "#ffde00", "accent": "#c41e3a", "banner_bg": "linear-gradient(135deg, #de2910, #c41e3a)", "banner_text": "#ffde00"}, "badge": {"text": "🧧 Happy Lunar New Year!", "style": "festive"}, "decorations": {"type": "confetti", "density": "medium"}, "banner_style": "gradient"}',
 75),

('womens_day', 'International Women''s Day',
 '{"type": "fixed", "start": "03-07", "end": "03-09"}',
 '{"colors": {"primary": "#9b59b6", "secondary": "#8e44ad", "accent": "#f39c12", "banner_bg": "linear-gradient(135deg, #9b59b6, #e91e63)", "banner_text": "#ffffff"}, "badge": {"text": "💜 International Women''s Day", "style": "default"}, "decorations": {"type": "hearts", "density": "light"}, "banner_style": "gradient"}',
 45),

('pi_day', 'Pi Day & Einstein''s Birthday',
 '{"type": "fixed", "start": "03-13", "end": "03-15"}',
 '{"colors": {"primary": "#3498db", "secondary": "#2980b9", "accent": "#9b59b6", "banner_bg": "linear-gradient(135deg, #3498db, #9b59b6)", "banner_text": "#ffffff"}, "badge": {"text": "🔬 Pi Day & Einstein''s Birthday", "style": "default"}, "decorations": {"type": "none"}, "banner_style": "gradient"}',
 35),

('earth_day', 'Earth Day',
 '{"type": "fixed", "start": "04-21", "end": "04-23"}',
 '{"colors": {"primary": "#2ecc71", "secondary": "#27ae60", "accent": "#3498db", "banner_bg": "linear-gradient(135deg, #2ecc71, #3498db)", "banner_text": "#ffffff"}, "badge": {"text": "🌍 Earth Day - Protect Our Planet!", "style": "default"}, "decorations": {"type": "none"}, "banner_style": "gradient"}',
 50),

('book_day', 'World Book Day',
 '{"type": "fixed", "start": "04-22", "end": "04-24"}',
 '{"colors": {"primary": "#8e44ad", "secondary": "#9b59b6", "accent": "#f39c12", "banner_bg": "linear-gradient(135deg, #8e44ad, #3498db)", "banner_text": "#ffffff"}, "badge": {"text": "📖 World Book Day", "style": "default"}, "decorations": {"type": "none"}, "banner_style": "gradient"}',
 35),

('mothers_day', 'Mother''s Day',
 '{"type": "dynamic", "rule": "mothers_day", "offset_start": -1, "offset_end": 0}',
 '{"colors": {"primary": "#ff69b4", "secondary": "#db7093", "accent": "#ff1493", "banner_bg": "linear-gradient(135deg, #ff69b4, #ff1493)", "banner_text": "#ffffff"}, "badge": {"text": "💐 Happy Mother''s Day!", "style": "pulse"}, "decorations": {"type": "hearts", "density": "light"}, "banner_style": "gradient"}',
 70),

('fathers_day', 'Father''s Day',
 '{"type": "dynamic", "rule": "fathers_day", "offset_start": -1, "offset_end": 0}',
 '{"colors": {"primary": "#2980b9", "secondary": "#3498db", "accent": "#f39c12", "banner_bg": "linear-gradient(135deg, #2980b9, #3498db)", "banner_text": "#ffffff"}, "badge": {"text": "👔 Happy Father''s Day!", "style": "default"}, "decorations": {"type": "none"}, "banner_style": "gradient"}',
 70),

('mandela_day', 'Nelson Mandela International Day',
 '{"type": "fixed", "start": "07-17", "end": "07-19"}',
 '{"colors": {"primary": "#2ecc71", "secondary": "#f1c40f", "accent": "#e74c3c", "banner_bg": "linear-gradient(135deg, #2ecc71, #27ae60)", "banner_text": "#ffffff"}, "badge": {"text": "✊ Mandela Day - 67 Minutes of Service", "style": "default"}, "decorations": {"type": "none"}, "banner_style": "gradient"}',
 45),

('peace_day', 'International Day of Peace',
 '{"type": "fixed", "start": "09-20", "end": "09-22"}',
 '{"colors": {"primary": "#3498db", "secondary": "#ffffff", "accent": "#2ecc71", "banner_bg": "linear-gradient(135deg, #3498db, #2ecc71)", "banner_text": "#ffffff"}, "badge": {"text": "☮️ International Day of Peace", "style": "default"}, "decorations": {"type": "none"}, "banner_style": "gradient"}',
 45),

('gandhi_day', 'International Day of Non-Violence',
 '{"type": "fixed", "start": "10-01", "end": "10-03"}',
 '{"colors": {"primary": "#ff9933", "secondary": "#ffffff", "accent": "#138808", "banner_bg": "linear-gradient(135deg, #ff9933, #ffffff, #138808)", "banner_text": "#2c3e50"}, "badge": {"text": "☮️ International Day of Non-Violence", "style": "default"}, "decorations": {"type": "none"}, "banner_style": "gradient"}',
 45),

('teachers_day', 'World Teachers'' Day',
 '{"type": "fixed", "start": "10-04", "end": "10-06"}',
 '{"colors": {"primary": "#27ae60", "secondary": "#2ecc71", "accent": "#f1c40f", "banner_bg": "linear-gradient(135deg, #27ae60, #2ecc71)", "banner_text": "#ffffff"}, "badge": {"text": "📚 World Teachers'' Day", "style": "default"}, "decorations": {"type": "none"}, "banner_style": "gradient"}',
 40),

('human_rights_day', 'Human Rights Day',
 '{"type": "fixed", "start": "12-09", "end": "12-11"}',
 '{"colors": {"primary": "#3498db", "secondary": "#2980b9", "accent": "#f1c40f", "banner_bg": "linear-gradient(135deg, #3498db, #2980b9)", "banner_text": "#ffffff"}, "badge": {"text": "🌐 Human Rights Day", "style": "default"}, "decorations": {"type": "none"}, "banner_style": "gradient"}',
 50)

ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    date_rule = EXCLUDED.date_rule,
    theme_config = EXCLUDED.theme_config,
    priority = EXCLUDED.priority,
    updated_at = NOW();

-- ==========================================
-- Part 10: Scheduled Task Logs (v3.15)
-- ==========================================

CREATE TABLE IF NOT EXISTS scheduled_task_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_name TEXT NOT NULL,
    task_type TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    status TEXT NOT NULL DEFAULT 'running',
    result_summary JSONB DEFAULT '{}'::jsonb,
    error_message TEXT,
    error_stack TEXT,
    hostname TEXT,
    pid INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_task_logs_task_name ON scheduled_task_logs(task_name);
CREATE INDEX IF NOT EXISTS idx_task_logs_started_at ON scheduled_task_logs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_task_logs_status ON scheduled_task_logs(status);

-- View for latest task status
CREATE OR REPLACE VIEW v_latest_task_status AS
SELECT DISTINCT ON (task_name)
    task_name,
    task_type,
    started_at,
    completed_at,
    duration_ms,
    status,
    result_summary,
    error_message,
    hostname,
    EXTRACT(EPOCH FROM (NOW() - started_at)) / 60 AS minutes_since_last_run
FROM scheduled_task_logs
ORDER BY task_name, started_at DESC;

-- Cleanup function
CREATE OR REPLACE FUNCTION cleanup_old_task_logs()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM scheduled_task_logs
    WHERE started_at < NOW() - INTERVAL '7 days';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- RLS for task logs
ALTER TABLE scheduled_task_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role can manage task logs"
    ON scheduled_task_logs FOR ALL
    USING (true)
    WITH CHECK (true);

-- ==========================================
-- Done!
-- ==========================================
