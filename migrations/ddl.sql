-- ==============================================================================
-- Make Decodables Database Initialization Script (v3.23 - Complete)
-- Includes: core schema + RLS policies + all updates through v3.23
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
-- v3.16: Tooltip configs
-- v3.17: System resources enhancement + audit logs
-- v3.18: Storage buckets (make-decodables-s, make-decodables-u)
-- v3.19: event_id for CAPI/Server-Side GTM deduplication
-- v3.20: A/B Testing system (experiments, assignments, results)
-- v3.21: AI model configs
-- v3.22: Atomic transactions (credits, marketplace), Webhook idempotency
-- v3.23: Task queue system (generation_tasks, async image generation)
-- v3.24: User generations history table (遗漏补充)
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
  -- v3.26: Two-level classification
  category TEXT DEFAULT 'element',
  source TEXT DEFAULT 'user',
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

-- 9. System resources (v3.17 enhanced)
CREATE TABLE IF NOT EXISTS system_resources (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  type TEXT NOT NULL,
  category TEXT,
  url TEXT NOT NULL,
  allowed_tiers TEXT[] DEFAULT '{free, starter, pro}',
  -- v3.17: Enhanced fields
  name TEXT,
  description TEXT,
  thumbnail_url TEXT,
  tags TEXT[] DEFAULT '{}',
  is_active BOOLEAN DEFAULT true,
  sort_order INTEGER DEFAULT 0,
  file_size INTEGER,
  file_type TEXT,
  dimensions JSONB,
  metadata JSONB DEFAULT '{}',
  created_by TEXT,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  updated_by TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- v3.17: System resources indexes
CREATE INDEX IF NOT EXISTS idx_system_resources_type ON system_resources(type);
CREATE INDEX IF NOT EXISTS idx_system_resources_category ON system_resources(category);
CREATE INDEX IF NOT EXISTS idx_system_resources_tags ON system_resources USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_system_resources_active_type ON system_resources(type, is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_system_resources_sort ON system_resources(type, sort_order, created_at DESC);

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
  -- v3.19: event_id for CAPI/sGTM deduplication
  event_id VARCHAR(100),
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_user_events_created_at ON user_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_events_event_type ON user_events(event_type);
CREATE INDEX IF NOT EXISTS idx_user_events_user_id ON user_events(user_id);
CREATE INDEX IF NOT EXISTS idx_user_events_session ON user_events(session_id);
CREATE INDEX IF NOT EXISTS idx_user_events_properties ON user_events USING gin(properties);
-- v3.19: event_id indexes for CAPI deduplication
CREATE INDEX IF NOT EXISTS idx_user_events_event_id ON user_events(event_id) WHERE event_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_user_events_type_event_id ON user_events(event_type, event_id) WHERE event_id IS NOT NULL;

-- 16. Analytics events (v3.4 + v3.11 enhancements + v3.19 event_id)
CREATE TABLE IF NOT EXISTS analytics_events (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id TEXT,
  event_type TEXT NOT NULL,
  event_name TEXT,
  event_level TEXT,
  event_data JSONB NOT NULL DEFAULT '{}',
  context JSONB DEFAULT '{}',
  session_id TEXT,
  -- v3.9: Timezone support
  timezone TEXT DEFAULT 'UTC',
  created_at_local TIMESTAMP,
  -- v3.19: event_id for CAPI/sGTM deduplication
  event_id VARCHAR(100),
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_analytics_events_user_id ON analytics_events(user_id);
CREATE INDEX IF NOT EXISTS idx_analytics_events_event_type ON analytics_events(event_type);
CREATE INDEX IF NOT EXISTS idx_analytics_events_event_name ON analytics_events(event_name);
CREATE INDEX IF NOT EXISTS idx_analytics_events_created_at ON analytics_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analytics_events_session_id ON analytics_events(session_id);
-- v3.19: event_id indexes for CAPI deduplication
CREATE INDEX IF NOT EXISTS idx_analytics_events_event_id ON analytics_events(event_id) WHERE event_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_analytics_events_type_event_id ON analytics_events(event_type, event_id) WHERE event_id IS NOT NULL;

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

-- 19. System configs (v3.10)
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
  dau INT DEFAULT 0,
  new_users INT DEFAULT 0,
  returning_users INT DEFAULT 0,
  total_sessions INT DEFAULT 0,
  avg_session_duration_sec INT DEFAULT 0,
  pages_per_session REAL DEFAULT 0,
  ai_generations INT DEFAULT 0,
  ai_credits_used INT DEFAULT 0,
  marketplace_purchases INT DEFAULT 0,
  marketplace_revenue INT DEFAULT 0,
  projects_created INT DEFAULT 0,
  projects_exported INT DEFAULT 0,
  raw_data JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_daily_metrics_date ON analytics_daily_metrics(metric_date DESC);

-- 25. Monthly metrics aggregation
CREATE TABLE IF NOT EXISTS analytics_monthly_metrics (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  metric_month DATE NOT NULL UNIQUE,
  mau INT DEFAULT 0,
  new_users INT DEFAULT 0,
  churned_users INT DEFAULT 0,
  mrr DECIMAL(12,2) DEFAULT 0,
  arr DECIMAL(12,2) DEFAULT 0,
  arpu DECIMAL(8,2) DEFAULT 0,
  trial_to_paid_rate REAL DEFAULT 0,
  free_to_paid_rate REAL DEFAULT 0,
  tier_distribution JSONB DEFAULT '{}',
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
-- Part 1.6: v3.17 System Resource Audit Logs
-- ==========================================

-- 30. System resource audit logs
CREATE TABLE IF NOT EXISTS system_resource_audit_logs (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  resource_id UUID REFERENCES system_resources(id) ON DELETE SET NULL,
  action TEXT NOT NULL,
  old_data JSONB,
  new_data JSONB,
  changed_by TEXT NOT NULL,
  changed_at TIMESTAMPTZ DEFAULT NOW(),
  ip_address TEXT,
  user_agent TEXT
);
CREATE INDEX IF NOT EXISTS idx_resource_audit_resource_id ON system_resource_audit_logs(resource_id);
CREATE INDEX IF NOT EXISTS idx_resource_audit_changed_at ON system_resource_audit_logs(changed_at DESC);

-- ==========================================
-- Part 1.7: Dashboard Optimized Indexes
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
ALTER TABLE system_resource_audit_logs ENABLE ROW LEVEL SECURITY;

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

-- [System Resources] (v3.17 enhanced)
DROP POLICY IF EXISTS "Public can view system resources" ON system_resources;
DROP POLICY IF EXISTS "Public can view active system resources" ON system_resources;
DROP POLICY IF EXISTS "Admin full access to system resources" ON system_resources;

CREATE POLICY "Public can view active system resources" ON system_resources FOR SELECT
USING (is_active = true);

CREATE POLICY "Admin full access to system resources" ON system_resources FOR ALL
USING (is_admin())
WITH CHECK (is_admin());

-- [System Resource Audit Logs] (v3.17)
DROP POLICY IF EXISTS "Admin can view resource audit logs" ON system_resource_audit_logs;
CREATE POLICY "Admin can view resource audit logs" ON system_resource_audit_logs FOR SELECT
USING (is_admin());

DROP POLICY IF EXISTS "Service can insert audit logs" ON system_resource_audit_logs;
CREATE POLICY "Service can insert audit logs" ON system_resource_audit_logs FOR INSERT
WITH CHECK (true);

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

-- [System Configs]
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

DROP MATERIALIZED VIEW IF EXISTS mv_dau_trend CASCADE;
CREATE MATERIALIZED VIEW mv_dau_trend AS
SELECT 
  metric_date,
  dau,
  new_users,
  returning_users,
  AVG(dau) OVER (ORDER BY metric_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as dau_7day_avg
FROM analytics_daily_metrics
ORDER BY metric_date DESC;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_dau_trend_date ON mv_dau_trend(metric_date);

DROP MATERIALIZED VIEW IF EXISTS mv_top_errors CASCADE;
CREATE MATERIALIZED VIEW mv_top_errors AS
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

DROP MATERIALIZED VIEW IF EXISTS mv_daily_event_summary CASCADE;
CREATE MATERIALIZED VIEW mv_daily_event_summary AS
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

-- v3.17: System resources timestamp trigger
CREATE OR REPLACE FUNCTION update_system_resources_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_system_resources_updated_at ON system_resources;
CREATE TRIGGER trigger_system_resources_updated_at
  BEFORE UPDATE ON system_resources
  FOR EACH ROW
  EXECUTE FUNCTION update_system_resources_timestamp();

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
  
  -- Tooltip Text (v3.16)
  ('TOOLTIP_DELETE', 'Delete', 'text', 'tooltip', 'Delete button tooltip when enabled'),
  ('TOOLTIP_DELETE_DISABLED', 'Unpublish first to delete', 'text', 'tooltip', 'Delete button tooltip when project is published (disabled state)')

ON CONFLICT (key) DO UPDATE SET
  value = EXCLUDED.value,
  value_type = EXCLUDED.value_type,
  config_group = EXCLUDED.config_group,
  description = EXCLUDED.description,
  updated_at = NOW();

-- ==========================================
-- Part 9: Holiday Themes & Marketing Campaigns (v3.13)
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

DROP POLICY IF EXISTS "Public can view active campaigns" ON campaigns;
CREATE POLICY "Public can view active campaigns" ON campaigns
    FOR SELECT USING (status = 'active' AND is_active = true);

DROP POLICY IF EXISTS "Users can view own claims" ON campaign_claims;
CREATE POLICY "Users can view own claims" ON campaign_claims
    FOR SELECT USING (user_id = auth.uid()::text);

DROP POLICY IF EXISTS "Users can insert own claims" ON campaign_claims;
CREATE POLICY "Users can insert own claims" ON campaign_claims
    FOR INSERT WITH CHECK (user_id = auth.uid()::text);

DROP POLICY IF EXISTS "Users can manage own dismissals" ON campaign_dismissals;
CREATE POLICY "Users can manage own dismissals" ON campaign_dismissals
    FOR ALL USING (user_id = auth.uid()::text);

-- ==========================================
-- Part 10: Holiday Themes Data (v3.13 + v3.14)
-- ==========================================

INSERT INTO holiday_themes (id, name, date_rule, theme_config, priority) VALUES
('newyear', 'New Year',
 '{"type": "fixed", "start": "12-30", "end": "01-02"}',
 '{"colors": {"primary": "#ffd700", "secondary": "#c0c0c0", "accent": "#ffffff", "banner_bg": "linear-gradient(135deg, #1a1a2e, #16213e)", "banner_text": "#ffd700"}, "badge": {"text": "🎉 Happy New Year!", "style": "sparkle"}, "decorations": {"type": "confetti", "density": "heavy"}, "banner_style": "gradient"}',
 100),

('valentine', 'Valentine''s Day',
 '{"type": "fixed", "start": "02-12", "end": "02-15"}',
 '{"colors": {"primary": "#ff69b4", "secondary": "#ff1493", "accent": "#dc143c", "banner_bg": "linear-gradient(135deg, #ff69b4, #ff1493)", "banner_text": "#ffffff"}, "badge": {"text": "💝 Valentine''s Day", "style": "pulse"}, "decorations": {"type": "hearts", "density": "light"}, "banner_style": "gradient"}',
 50),

('stpatrick', 'St. Patrick''s Day',
 '{"type": "fixed", "start": "03-15", "end": "03-18"}',
 '{"colors": {"primary": "#228b22", "secondary": "#32cd32", "accent": "#ffd700", "banner_bg": "#228b22", "banner_text": "#ffffff"}, "badge": {"text": "☘️ St. Patrick''s Day", "style": "default"}, "decorations": {"type": "none"}, "banner_style": "solid"}',
 40),

('earth_day', 'Earth Day',
 '{"type": "fixed", "start": "04-21", "end": "04-23"}',
 '{"colors": {"primary": "#2ecc71", "secondary": "#27ae60", "accent": "#3498db", "banner_bg": "linear-gradient(135deg, #2ecc71, #3498db)", "banner_text": "#ffffff"}, "badge": {"text": "🌍 Earth Day - Protect Our Planet!", "style": "default"}, "decorations": {"type": "none"}, "banner_style": "gradient"}',
 50),

('mothers_day', 'Mother''s Day',
 '{"type": "dynamic", "rule": "mothers_day", "offset_start": -1, "offset_end": 0}',
 '{"colors": {"primary": "#ff69b4", "secondary": "#db7093", "accent": "#ff1493", "banner_bg": "linear-gradient(135deg, #ff69b4, #ff1493)", "banner_text": "#ffffff"}, "badge": {"text": "💐 Happy Mother''s Day!", "style": "pulse"}, "decorations": {"type": "hearts", "density": "light"}, "banner_style": "gradient"}',
 70),

('fathers_day', 'Father''s Day',
 '{"type": "dynamic", "rule": "fathers_day", "offset_start": -1, "offset_end": 0}',
 '{"colors": {"primary": "#2980b9", "secondary": "#3498db", "accent": "#f39c12", "banner_bg": "linear-gradient(135deg, #2980b9, #3498db)", "banner_text": "#ffffff"}, "badge": {"text": "👔 Happy Father''s Day!", "style": "default"}, "decorations": {"type": "none"}, "banner_style": "gradient"}',
 70),

('july4th', 'Independence Day',
 '{"type": "fixed", "start": "07-02", "end": "07-05"}',
 '{"colors": {"primary": "#b22234", "secondary": "#3c3b6e", "accent": "#ffffff", "banner_bg": "#b22234", "banner_text": "#ffffff"}, "badge": {"text": "🇺🇸 Happy 4th of July!", "style": "default"}, "decorations": {"type": "fireworks", "density": "heavy"}, "banner_style": "striped"}',
 60),

('halloween', 'Halloween',
 '{"type": "fixed", "start": "10-28", "end": "11-01"}',
 '{"colors": {"primary": "#ff6600", "secondary": "#1a1a1a", "accent": "#9933ff", "banner_bg": "#1a1a1a", "banner_text": "#ff6600"}, "badge": {"text": "🎃 Happy Halloween!", "style": "spooky"}, "decorations": {"type": "confetti", "density": "light"}, "banner_style": "solid"}',
 70),

('teachers_day', 'World Teachers'' Day',
 '{"type": "fixed", "start": "10-04", "end": "10-06"}',
 '{"colors": {"primary": "#27ae60", "secondary": "#2ecc71", "accent": "#f1c40f", "banner_bg": "linear-gradient(135deg, #27ae60, #2ecc71)", "banner_text": "#ffffff"}, "badge": {"text": "📚 World Teachers'' Day", "style": "default"}, "decorations": {"type": "none"}, "banner_style": "gradient"}',
 40),

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
 95)

ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    date_rule = EXCLUDED.date_rule,
    theme_config = EXCLUDED.theme_config,
    priority = EXCLUDED.priority,
    updated_at = NOW();

-- ==========================================
-- Part 11: Scheduled Task Logs (v3.15)
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

DROP POLICY IF EXISTS "Service role can manage task logs" ON scheduled_task_logs;
CREATE POLICY "Service role can manage task logs"
    ON scheduled_task_logs FOR ALL
    USING (true)
    WITH CHECK (true);

-- ==========================================
-- Part 12: Storage Buckets Setup (v3.18)
-- ==========================================

-- Create make-decodables-s bucket (system assets)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'make-decodables-s',
  'make-decodables-s',
  true,
  10485760,
  ARRAY['image/png', 'image/jpeg', 'image/webp', 'image/gif', 'image/svg+xml']
)
ON CONFLICT (id) DO UPDATE SET
  public = EXCLUDED.public,
  file_size_limit = EXCLUDED.file_size_limit,
  allowed_mime_types = EXCLUDED.allowed_mime_types;

-- Create make-decodables-u bucket (user content)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'make-decodables-u',
  'make-decodables-u',
  true,
  52428800,
  ARRAY['image/png', 'image/jpeg', 'image/webp', 'image/gif', 'image/svg+xml', 'application/pdf']
)
ON CONFLICT (id) DO UPDATE SET
  public = EXCLUDED.public,
  file_size_limit = EXCLUDED.file_size_limit,
  allowed_mime_types = EXCLUDED.allowed_mime_types;

-- Storage RLS Policies
DROP POLICY IF EXISTS "make-decodables-s: public read" ON storage.objects;
DROP POLICY IF EXISTS "make-decodables-s: deny insert" ON storage.objects;
DROP POLICY IF EXISTS "make-decodables-s: deny update" ON storage.objects;
DROP POLICY IF EXISTS "make-decodables-s: deny delete" ON storage.objects;
DROP POLICY IF EXISTS "make-decodables-u: public read" ON storage.objects;
DROP POLICY IF EXISTS "make-decodables-u: deny insert" ON storage.objects;
DROP POLICY IF EXISTS "make-decodables-u: deny update" ON storage.objects;
DROP POLICY IF EXISTS "make-decodables-u: deny delete" ON storage.objects;

-- make-decodables-s policies
CREATE POLICY "make-decodables-s: public read"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'make-decodables-s');

CREATE POLICY "make-decodables-s: deny insert"
  ON storage.objects FOR INSERT
  WITH CHECK (bucket_id = 'make-decodables-s' AND false);

CREATE POLICY "make-decodables-s: deny update"
  ON storage.objects FOR UPDATE
  USING (bucket_id = 'make-decodables-s' AND false);

CREATE POLICY "make-decodables-s: deny delete"
  ON storage.objects FOR DELETE
  USING (bucket_id = 'make-decodables-s' AND false);

-- make-decodables-u policies
CREATE POLICY "make-decodables-u: public read"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'make-decodables-u');

CREATE POLICY "make-decodables-u: deny insert"
  ON storage.objects FOR INSERT
  WITH CHECK (bucket_id = 'make-decodables-u' AND false);

CREATE POLICY "make-decodables-u: deny update"
  ON storage.objects FOR UPDATE
  USING (bucket_id = 'make-decodables-u' AND false);

CREATE POLICY "make-decodables-u: deny delete"
  ON storage.objects FOR DELETE
  USING (bucket_id = 'make-decodables-u' AND false);

-- ==========================================
-- v3.20: A/B Testing System
-- ==========================================

-- 1. 实验配置表
CREATE TABLE IF NOT EXISTS experiments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  experiment_key VARCHAR(100) UNIQUE NOT NULL,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  experiment_type VARCHAR(20) DEFAULT 'ab',
  status VARCHAR(20) DEFAULT 'draft',
  variants JSONB NOT NULL DEFAULT '[{"key": "control", "name": "Control", "weight": 100}]',
  targeting JSONB DEFAULT '{"include_anonymous": true}',
  traffic_allocation INT DEFAULT 100 CHECK (traffic_allocation >= 0 AND traffic_allocation <= 100),
  metrics JSONB DEFAULT '[]',
  fallback_variant VARCHAR(100) DEFAULT 'control',
  winning_variant VARCHAR(100),
  start_at TIMESTAMPTZ,
  end_at TIMESTAMPTZ,
  created_by TEXT,
  updated_by TEXT,
  timezone TEXT DEFAULT 'UTC',
  created_at_local TIMESTAMP,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. 用户分配记录表
CREATE TABLE IF NOT EXISTS experiment_assignments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  experiment_id UUID NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
  experiment_key VARCHAR(100) NOT NULL,
  user_identifier VARCHAR(100) NOT NULL,
  identifier_type VARCHAR(20) DEFAULT 'user',
  variant_key VARCHAR(100) NOT NULL,
  context JSONB DEFAULT '{}',
  assigned_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(experiment_id, user_identifier)
);

-- 3. 实验结果聚合表
CREATE TABLE IF NOT EXISTS experiment_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  experiment_id UUID NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
  variant_key VARCHAR(100) NOT NULL,
  date DATE NOT NULL,
  hour INT DEFAULT 0,
  participants INT DEFAULT 0,
  exposures INT DEFAULT 0,
  conversions INT DEFAULT 0,
  conversion_rate DECIMAL(10, 6),
  metrics_data JSONB DEFAULT '{}',
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(experiment_id, variant_key, date, hour)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_experiments_status ON experiments(status);
CREATE INDEX IF NOT EXISTS idx_experiments_key ON experiments(experiment_key);
CREATE INDEX IF NOT EXISTS idx_experiments_dates ON experiments(start_at, end_at);
CREATE INDEX IF NOT EXISTS idx_experiments_created_at ON experiments(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_exp_assignments_experiment ON experiment_assignments(experiment_id);
CREATE INDEX IF NOT EXISTS idx_exp_assignments_user ON experiment_assignments(user_identifier);
CREATE INDEX IF NOT EXISTS idx_exp_assignments_key_user ON experiment_assignments(experiment_key, user_identifier);
CREATE INDEX IF NOT EXISTS idx_exp_assignments_variant ON experiment_assignments(experiment_id, variant_key);

CREATE INDEX IF NOT EXISTS idx_exp_results_experiment ON experiment_results(experiment_id);
CREATE INDEX IF NOT EXISTS idx_exp_results_experiment_date ON experiment_results(experiment_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_exp_results_variant ON experiment_results(experiment_id, variant_key);

-- RLS
ALTER TABLE experiments ENABLE ROW LEVEL SECURITY;
ALTER TABLE experiment_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE experiment_results ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on experiments" ON experiments
  FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access on experiment_assignments" ON experiment_assignments
  FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access on experiment_results" ON experiment_results
  FOR ALL USING (true) WITH CHECK (true);

-- 更新时间触发器
CREATE OR REPLACE FUNCTION update_experiments_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_experiments_updated_at ON experiments;
CREATE TRIGGER trg_experiments_updated_at
  BEFORE UPDATE ON experiments
  FOR EACH ROW
  EXECUTE FUNCTION update_experiments_timestamp();

-- ==========================================
-- v3.21: AI Model Configuration System
-- AI 模型配置管理系统
-- ==========================================

-- AI 模型相关配置 (写入 system_configs)
INSERT INTO system_configs (key, value, value_type, config_group, description, is_active) VALUES
('ai_providers.enabled', 
 '{"openai": true, "fal": true, "qwen": false, "wanx": false, "gemini": false, "grok": false, "jimeng": false, "anthropic": false}', 
 'json', 'ai_providers', 'Enable/disable AI providers', true),
('ai_model.user.text_reasoning', 
 '{"provider": "openai", "model": "gpt-4o-mini", "fallback": {"provider": "openai", "model": "gpt-4o-mini"}, "show_provider": false}', 
 'json', 'ai_models', 'User text reasoning model configuration', true),
('ai_model.user.image_generation', 
 '{"provider": "fal", "models": {"free": "flux-schnell", "starter": "flux-schnell", "pro": "flux-dev"}, "fallback": {"provider": "fal", "model": "flux-schnell"}, "show_provider": false}', 
 'json', 'ai_models', 'User image generation model by tier', true),
('ai_model.admin.analysis', 
 '{"provider": "openai", "model": "gpt-4o", "fallback": {"provider": "openai", "model": "gpt-4o-mini"}}', 
 'json', 'ai_models', 'Admin analysis model configuration', true),
('ai_model.canary', 
 '{"enabled": false, "text_reasoning": {"canary_provider": "qwen", "canary_model": "qwen-plus", "traffic_percent": 10, "target_tiers": ["pro"]}, "image_generation": {"canary_provider": "jimeng", "canary_model": "jimeng-2.1", "traffic_percent": 5, "target_tiers": ["pro"]}}', 
 'json', 'ai_models', 'Canary release configuration for A/B testing new models', true),
('ai_providers.models', 
 '{"openai": {"text": ["gpt-4o-mini", "gpt-4o", "o1-mini", "o1"], "image": ["dall-e-3"]}, "fal": {"image": ["flux-schnell", "flux-dev", "flux-pro"]}, "qwen": {"text": ["qwen-turbo", "qwen-plus", "qwen-max"]}, "wanx": {"image": ["wan2.6-t2i", "wan2.6-image", "wanx-v1"]}, "gemini": {"text": ["gemini-2.0-flash", "gemini-2.0-pro"], "image": ["imagen-3"]}, "grok": {"text": ["grok-2", "grok-2-vision"]}, "jimeng": {"image": ["jimeng-2.1", "jimeng-2.1-pro"]}, "anthropic": {"text": ["claude-3.5-sonnet", "claude-3.5-opus"]}}', 
 'json', 'ai_providers', 'Available models per provider', true),
('ai_providers.timeouts', 
 '{"openai": {"text": 60, "image": 120}, "fal": {"image": 180}, "qwen": {"text": 60}, "wanx": {"image": 180}, "gemini": {"text": 30}, "anthropic": {"text": 90}}', 
 'json', 'ai_providers', 'Timeout configuration in seconds', true),
('ai_providers.costs', 
 '{"openai": {"gpt-4o-mini": 0.15, "gpt-4o": 2.50, "o1-mini": 3.00, "o1": 15.00, "dall-e-3": 0.04}, "fal": {"flux-schnell": 0.003, "flux-dev": 0.025, "flux-pro": 0.05}, "qwen": {"qwen-turbo": 0.001, "qwen-plus": 0.004, "qwen-max": 0.02}, "wanx": {"wan2.6-t2i": 0.02, "wan2.6-image": 0.03, "wanx-v1": 0.015}, "anthropic": {"claude-3.5-sonnet": 3.00, "claude-3.5-opus": 15.00}}', 
 'json', 'ai_providers', 'Cost reference per 1M tokens or per image (USD)', true),
('ai_providers.retry',
 '{"max_retries": 3, "base_delay_ms": 1000, "max_delay_ms": 10000, "retry_on_status": [429, 500, 502, 503, 504]}',
 'json', 'ai_providers', 'Retry configuration for AI API calls', true),

-- Credit costs configuration (v3.23, updated v3.25)
('credits.cost.image_generation', '5', 'integer', 'credits', 'AI image generation cost per image', true),
('credits.cost.image_generation_reference', '7', 'integer', 'credits', 'AI image generation with reference image cost per image', true),
('credits.cost.text_generation', '0', 'integer', 'credits', 'AI text generation cost (currently free)', true),
('credits.cost.smart_scan', '10', 'integer', 'credits', 'Smart Scan/OCR cost per operation', true),
('credits.cost.ocr', '10', 'integer', 'credits', 'OCR recognition cost (same as Smart Scan)', true)
ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value,
    description = EXCLUDED.description,
    updated_at = NOW();

-- AI 使用量日汇总表
CREATE TABLE IF NOT EXISTS ai_usage_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    call_type TEXT NOT NULL,
    total_calls INT DEFAULT 0,
    successful_calls INT DEFAULT 0,
    failed_calls INT DEFAULT 0,
    total_input_tokens BIGINT DEFAULT 0,
    total_output_tokens BIGINT DEFAULT 0,
    total_images INT DEFAULT 0,
    avg_latency_ms INT DEFAULT 0,
    min_latency_ms INT,
    max_latency_ms INT,
    estimated_cost_usd DECIMAL(10, 4) DEFAULT 0,
    error_counts JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(date, provider, model, call_type)
);

CREATE INDEX IF NOT EXISTS idx_ai_usage_daily_date ON ai_usage_daily(date DESC);
CREATE INDEX IF NOT EXISTS idx_ai_usage_daily_provider ON ai_usage_daily(provider, date DESC);

ALTER TABLE ai_usage_daily ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Admin can read ai usage" ON ai_usage_daily;
CREATE POLICY "Admin can read ai usage" ON ai_usage_daily
    FOR SELECT USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid()::text AND role = 'admin'));

DROP POLICY IF EXISTS "System can write ai usage" ON ai_usage_daily;
CREATE POLICY "System can write ai usage" ON ai_usage_daily
    FOR ALL USING (true);

-- Upsert 函数
CREATE OR REPLACE FUNCTION upsert_ai_usage_daily(
    p_date DATE, p_provider TEXT, p_model TEXT, p_call_type TEXT,
    p_success BOOLEAN, p_input_tokens BIGINT DEFAULT 0, p_output_tokens BIGINT DEFAULT 0,
    p_images INT DEFAULT 0, p_latency_ms INT DEFAULT 0, p_cost_usd DECIMAL DEFAULT 0, p_error_type TEXT DEFAULT NULL
) RETURNS VOID AS $$
DECLARE v_error_counts JSONB;
BEGIN
    IF p_error_type IS NOT NULL THEN v_error_counts := jsonb_build_object(p_error_type, 1); ELSE v_error_counts := '{}'::jsonb; END IF;
    INSERT INTO ai_usage_daily (date, provider, model, call_type, total_calls, successful_calls, failed_calls, total_input_tokens, total_output_tokens, total_images, avg_latency_ms, min_latency_ms, max_latency_ms, estimated_cost_usd, error_counts)
    VALUES (p_date, p_provider, p_model, p_call_type, 1, CASE WHEN p_success THEN 1 ELSE 0 END, CASE WHEN p_success THEN 0 ELSE 1 END, p_input_tokens, p_output_tokens, p_images, p_latency_ms, p_latency_ms, p_latency_ms, p_cost_usd, v_error_counts)
    ON CONFLICT (date, provider, model, call_type) DO UPDATE SET
        total_calls = ai_usage_daily.total_calls + 1,
        successful_calls = ai_usage_daily.successful_calls + CASE WHEN p_success THEN 1 ELSE 0 END,
        failed_calls = ai_usage_daily.failed_calls + CASE WHEN p_success THEN 0 ELSE 1 END,
        total_input_tokens = ai_usage_daily.total_input_tokens + p_input_tokens,
        total_output_tokens = ai_usage_daily.total_output_tokens + p_output_tokens,
        total_images = ai_usage_daily.total_images + p_images,
        avg_latency_ms = CASE WHEN ai_usage_daily.total_calls = 0 THEN p_latency_ms ELSE ((ai_usage_daily.avg_latency_ms * ai_usage_daily.total_calls) + p_latency_ms) / (ai_usage_daily.total_calls + 1) END,
        min_latency_ms = LEAST(COALESCE(ai_usage_daily.min_latency_ms, p_latency_ms), p_latency_ms),
        max_latency_ms = GREATEST(COALESCE(ai_usage_daily.max_latency_ms, p_latency_ms), p_latency_ms),
        estimated_cost_usd = ai_usage_daily.estimated_cost_usd + p_cost_usd,
        error_counts = CASE WHEN p_error_type IS NOT NULL THEN ai_usage_daily.error_counts || jsonb_build_object(p_error_type, COALESCE((ai_usage_daily.error_counts->>p_error_type)::int, 0) + 1) ELSE ai_usage_daily.error_counts END,
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- AI 使用量视图
CREATE OR REPLACE VIEW v_ai_usage_last_30_days AS
SELECT provider, model, call_type, SUM(total_calls) as total_calls, SUM(successful_calls) as successful_calls, SUM(failed_calls) as failed_calls,
    ROUND(SUM(successful_calls)::numeric / NULLIF(SUM(total_calls), 0) * 100, 2) as success_rate,
    SUM(total_input_tokens) as total_input_tokens, SUM(total_output_tokens) as total_output_tokens, SUM(total_images) as total_images,
    ROUND(AVG(avg_latency_ms)) as avg_latency_ms, SUM(estimated_cost_usd) as total_cost_usd
FROM ai_usage_daily WHERE date >= CURRENT_DATE - INTERVAL '30 days' GROUP BY provider, model, call_type ORDER BY total_cost_usd DESC;

-- ==========================================
-- v3.24: User Generations History Table
-- 用户 AI 生成历史记录 (遗漏补充)
-- ==========================================

CREATE TABLE IF NOT EXISTS user_generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    
    -- Image info
    image_url TEXT NOT NULL,
    
    -- Prompt details
    original_prompt TEXT,
    enhanced_prompt TEXT,
    negative_prompt TEXT,
    
    -- Style parameters
    style VARCHAR(50),
    moods TEXT[],
    aspect_ratio VARCHAR(50),
    generation_mode VARCHAR(20),
    creativity_level REAL,
    
    -- 5W1H parameters
    who_param TEXT,
    what_param TEXT,
    where_param TEXT,
    
    -- Reference image
    has_reference BOOLEAN DEFAULT false,
    reference_strength REAL,
    
    -- Batch info
    batch_id VARCHAR(50),
    batch_index INTEGER,
    
    -- Credits and model
    credits_used INTEGER DEFAULT 0,
    model_used VARCHAR(100),
    generation_time_ms INTEGER,
    
    -- Timezone support (v3.9)
    timezone TEXT DEFAULT 'UTC',
    created_at_local TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_generations_user_id ON user_generations(user_id);
CREATE INDEX IF NOT EXISTS idx_user_generations_batch_id ON user_generations(batch_id);
CREATE INDEX IF NOT EXISTS idx_user_generations_created_at ON user_generations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_generations_model ON user_generations(model_used);

ALTER TABLE user_generations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS user_generations_select_policy ON user_generations;
DROP POLICY IF EXISTS user_generations_service_policy ON user_generations;

CREATE POLICY user_generations_select_policy ON user_generations
    FOR SELECT
    USING (user_id = auth.uid()::text OR auth.role() = 'service_role');

CREATE POLICY user_generations_service_policy ON user_generations
    FOR ALL
    USING (auth.role() = 'service_role');

-- ==========================================
-- v3.22: Webhook Events for Idempotency
-- ==========================================

CREATE TABLE IF NOT EXISTS webhook_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id TEXT UNIQUE NOT NULL,
    event_type TEXT NOT NULL,
    processed_at TIMESTAMPTZ DEFAULT NOW(),
    payload JSONB,
    result JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_webhook_events_event_id ON webhook_events(event_id);
CREATE INDEX IF NOT EXISTS idx_webhook_events_type ON webhook_events(event_type);
CREATE INDEX IF NOT EXISTS idx_webhook_events_created_at ON webhook_events(created_at);

ALTER TABLE webhook_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS webhook_events_service_policy ON webhook_events;
CREATE POLICY webhook_events_service_policy ON webhook_events
    FOR ALL
    USING (auth.role() = 'service_role');

-- ==========================================
-- v3.22: Atomic Credit Functions
-- ==========================================

CREATE OR REPLACE FUNCTION deduct_credits_atomic(
    p_user_id TEXT,
    p_amount INT,
    p_tx_type TEXT,
    p_description TEXT DEFAULT NULL,
    p_timezone TEXT DEFAULT 'UTC',
    p_idempotency_key TEXT DEFAULT NULL
) RETURNS JSONB AS $$
DECLARE
    v_monthly INT;
    v_permanent INT;
    v_deduct_monthly INT;
    v_deduct_permanent INT;
    v_new_monthly INT;
    v_new_permanent INT;
    v_bucket TEXT;
    v_existing_tx RECORD;
BEGIN
    IF p_idempotency_key IS NOT NULL THEN
        SELECT * INTO v_existing_tx 
        FROM credit_transactions 
        WHERE idempotency_key = p_idempotency_key
        LIMIT 1;
        
        IF FOUND THEN
            RETURN jsonb_build_object(
                'success', true,
                'idempotent', true,
                'message', 'Already processed',
                'balance_monthly', v_existing_tx.balance_monthly_after,
                'balance_permanent', v_existing_tx.balance_permanent_after
            );
        END IF;
    END IF;
    
    SELECT credits_monthly, credits_permanent 
    INTO v_monthly, v_permanent
    FROM profiles 
    WHERE id = p_user_id 
    FOR UPDATE;
    
    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', false, 'error', 'User not found', 'error_code', 'USER_NOT_FOUND');
    END IF;
    
    IF (v_monthly + v_permanent) < p_amount THEN
        RETURN jsonb_build_object('success', false, 'error', 'Insufficient credits', 'error_code', 'CREDITS_INSUFFICIENT');
    END IF;
    
    v_deduct_monthly := LEAST(v_monthly, p_amount);
    v_deduct_permanent := p_amount - v_deduct_monthly;
    v_new_monthly := v_monthly - v_deduct_monthly;
    v_new_permanent := v_permanent - v_deduct_permanent;
    v_bucket := CASE WHEN v_deduct_monthly > 0 THEN 'monthly' ELSE 'permanent' END;
    
    UPDATE profiles 
    SET credits_monthly = v_new_monthly, credits_permanent = v_new_permanent
    WHERE id = p_user_id;
    
    IF v_deduct_monthly > 0 THEN
        INSERT INTO credit_transactions (user_id, amount, bucket, balance_monthly_after, balance_permanent_after, type, description, timezone, idempotency_key)
        VALUES (p_user_id, -v_deduct_monthly, 'monthly', v_new_monthly, v_new_permanent, p_tx_type, p_description, p_timezone, 
                CASE WHEN v_deduct_permanent = 0 THEN p_idempotency_key ELSE NULL END);
    END IF;
    
    IF v_deduct_permanent > 0 THEN
        INSERT INTO credit_transactions (user_id, amount, bucket, balance_monthly_after, balance_permanent_after, type, description, timezone, idempotency_key)
        VALUES (p_user_id, -v_deduct_permanent, 'permanent', v_new_monthly, v_new_permanent, p_tx_type, p_description, p_timezone, p_idempotency_key);
    END IF;
    
    RETURN jsonb_build_object('success', true, 'deducted', p_amount, 'balance_monthly', v_new_monthly, 'balance_permanent', v_new_permanent, 'bucket', v_bucket);
    
EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object('success', false, 'error', SQLERRM, 'error_code', 'DB_ERROR');
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION add_credits_atomic(
    p_user_id TEXT,
    p_amount INT,
    p_bucket TEXT,
    p_tx_type TEXT,
    p_description TEXT DEFAULT NULL,
    p_timezone TEXT DEFAULT 'UTC',
    p_idempotency_key TEXT DEFAULT NULL
) RETURNS JSONB AS $$
DECLARE
    v_monthly INT;
    v_permanent INT;
    v_new_monthly INT;
    v_new_permanent INT;
    v_existing_tx RECORD;
BEGIN
    IF p_amount <= 0 THEN
        RETURN jsonb_build_object('success', false, 'error', 'Amount must be positive', 'error_code', 'INVALID_AMOUNT');
    END IF;
    
    IF p_bucket NOT IN ('monthly', 'permanent') THEN
        RETURN jsonb_build_object('success', false, 'error', 'Invalid bucket', 'error_code', 'INVALID_BUCKET');
    END IF;
    
    IF p_idempotency_key IS NOT NULL THEN
        SELECT * INTO v_existing_tx FROM credit_transactions WHERE idempotency_key = p_idempotency_key LIMIT 1;
        IF FOUND THEN
            RETURN jsonb_build_object('success', true, 'idempotent', true, 'message', 'Already processed');
        END IF;
    END IF;
    
    SELECT credits_monthly, credits_permanent INTO v_monthly, v_permanent FROM profiles WHERE id = p_user_id FOR UPDATE;
    
    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', false, 'error', 'User not found', 'error_code', 'USER_NOT_FOUND');
    END IF;
    
    IF p_bucket = 'monthly' THEN
        v_new_monthly := v_monthly + p_amount;
        v_new_permanent := v_permanent;
    ELSE
        v_new_monthly := v_monthly;
        v_new_permanent := v_permanent + p_amount;
    END IF;
    
    UPDATE profiles SET credits_monthly = v_new_monthly, credits_permanent = v_new_permanent WHERE id = p_user_id;
    
    INSERT INTO credit_transactions (user_id, amount, bucket, balance_monthly_after, balance_permanent_after, type, description, timezone, idempotency_key)
    VALUES (p_user_id, p_amount, p_bucket, v_new_monthly, v_new_permanent, p_tx_type, p_description, p_timezone, p_idempotency_key);
    
    RETURN jsonb_build_object('success', true, 'added', p_amount, 'bucket', p_bucket, 'balance_monthly', v_new_monthly, 'balance_permanent', v_new_permanent);
    
EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object('success', false, 'error', SQLERRM, 'error_code', 'DB_ERROR');
END;
$$ LANGUAGE plpgsql;

-- Atomic marketplace purchase function
CREATE OR REPLACE FUNCTION execute_marketplace_purchase(
    p_listing_id UUID,
    p_buyer_id TEXT,
    p_timezone TEXT DEFAULT 'UTC',
    p_idempotency_key TEXT DEFAULT NULL
) RETURNS JSONB AS $$
DECLARE
    v_listing RECORD;
    v_buyer RECORD;
    v_price INT;
    v_seller_id TEXT;
    v_seller_revenue INT;
    v_buyer_monthly INT;
    v_buyer_permanent INT;
    v_deduct_monthly INT;
    v_deduct_permanent INT;
    v_new_buyer_monthly INT;
    v_new_buyer_permanent INT;
    v_existing_purchase RECORD;
    v_purchase_id UUID;
BEGIN
    -- 1. Idempotency check
    IF p_idempotency_key IS NOT NULL THEN
        SELECT * INTO v_existing_purchase 
        FROM user_purchases 
        WHERE idempotency_key = p_idempotency_key
        LIMIT 1;
        
        IF FOUND THEN
            RETURN jsonb_build_object(
                'success', true,
                'idempotent', true,
                'purchase_id', v_existing_purchase.id,
                'message', 'Already processed'
            );
        END IF;
    END IF;
    
    -- 2. Check if already purchased (by listing + buyer combo)
    SELECT id INTO v_purchase_id
    FROM user_purchases
    WHERE user_id = p_buyer_id AND listing_id = p_listing_id
    LIMIT 1;
    
    IF FOUND THEN
        RETURN jsonb_build_object(
            'success', true,
            'already_owned', true,
            'purchase_id', v_purchase_id,
            'message', 'Already purchased'
        );
    END IF;
    
    -- 3. Lock and get listing
    SELECT * INTO v_listing
    FROM marketplace_listings
    WHERE id = p_listing_id
    FOR UPDATE;
    
    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'success', false, 
            'error', 'Listing not found', 
            'status', 404
        );
    END IF;
    
    -- 4. Validate listing status
    IF v_listing.moderation_status != 'approved' THEN
        RETURN jsonb_build_object(
            'success', false, 
            'error', 'Listing is not approved', 
            'status', 400
        );
    END IF;
    
    IF NOT COALESCE(v_listing.is_public, false) THEN
        RETURN jsonb_build_object(
            'success', false, 
            'error', 'Listing is not public', 
            'status', 400
        );
    END IF;
    
    IF COALESCE(v_listing.is_deleted, false) THEN
        RETURN jsonb_build_object(
            'success', false, 
            'error', 'Listing has been deleted', 
            'status', 400
        );
    END IF;
    
    v_price := COALESCE(v_listing.price_credits, 0);
    v_seller_id := v_listing.seller_id;
    
    -- 5. Handle free items
    IF v_price = 0 THEN
        INSERT INTO user_purchases (user_id, listing_id, price_paid, timezone, idempotency_key)
        VALUES (p_buyer_id, p_listing_id, 0, p_timezone, p_idempotency_key)
        RETURNING id INTO v_purchase_id;
        
        UPDATE marketplace_listings 
        SET sales_count = COALESCE(sales_count, 0) + 1
        WHERE id = p_listing_id;
        
        RETURN jsonb_build_object(
            'success', true,
            'purchase_id', v_purchase_id,
            'price_paid', 0,
            'message', 'Free item acquired'
        );
    END IF;
    
    -- 6. Lock and get buyer
    SELECT credits_monthly, credits_permanent 
    INTO v_buyer_monthly, v_buyer_permanent
    FROM profiles
    WHERE id = p_buyer_id
    FOR UPDATE;
    
    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'success', false, 
            'error', 'Buyer not found', 
            'status', 404
        );
    END IF;
    
    -- 7. Check buyer has enough credits
    IF (v_buyer_monthly + v_buyer_permanent) < v_price THEN
        RETURN jsonb_build_object(
            'success', false, 
            'error', 'Insufficient credits',
            'status', 402,
            'available', v_buyer_monthly + v_buyer_permanent,
            'required', v_price
        );
    END IF;
    
    -- 8. Calculate deduction (monthly first)
    v_deduct_monthly := LEAST(v_buyer_monthly, v_price);
    v_deduct_permanent := v_price - v_deduct_monthly;
    v_new_buyer_monthly := v_buyer_monthly - v_deduct_monthly;
    v_new_buyer_permanent := v_buyer_permanent - v_deduct_permanent;
    
    -- 9. Deduct from buyer
    UPDATE profiles SET
        credits_monthly = v_new_buyer_monthly,
        credits_permanent = v_new_buyer_permanent,
        updated_at = NOW()
    WHERE id = p_buyer_id;
    
    -- 10. Log buyer transaction(s)
    IF v_deduct_monthly > 0 THEN
        INSERT INTO credit_transactions (
            user_id, amount, bucket, type, description, timezone,
            balance_monthly_after, balance_permanent_after
        ) VALUES (
            p_buyer_id, -v_deduct_monthly, 'monthly',
            'market_purchase', 
            'Purchased: ' || COALESCE(v_listing.title, 'Item'),
            p_timezone,
            v_new_buyer_monthly, v_new_buyer_permanent
        );
    END IF;
    
    IF v_deduct_permanent > 0 THEN
        INSERT INTO credit_transactions (
            user_id, amount, bucket, type, description, timezone,
            balance_monthly_after, balance_permanent_after
        ) VALUES (
            p_buyer_id, -v_deduct_permanent, 'permanent',
            'market_purchase', 
            'Purchased: ' || COALESCE(v_listing.title, 'Item'),
            p_timezone,
            v_new_buyer_monthly, v_new_buyer_permanent
        );
    END IF;
    
    -- 11. Add to seller (90% revenue)
    v_seller_revenue := (v_price * 90) / 100;
    
    IF v_seller_id IS NOT NULL AND v_seller_revenue > 0 THEN
        PERFORM 1 FROM profiles WHERE id = v_seller_id FOR UPDATE;
        
        UPDATE profiles SET
            credits_permanent = credits_permanent + v_seller_revenue,
            updated_at = NOW()
        WHERE id = v_seller_id;
        
        INSERT INTO credit_transactions (
            user_id, amount, bucket, type, description, timezone,
            balance_monthly_after, balance_permanent_after
        ) 
        SELECT 
            v_seller_id, v_seller_revenue, 'permanent',
            'market_sale', 
            'Sale: ' || COALESCE(v_listing.title, 'Item'),
            p_timezone,
            p.credits_monthly, p.credits_permanent
        FROM profiles p WHERE p.id = v_seller_id;
    END IF;
    
    -- 12. Record purchase
    INSERT INTO user_purchases (user_id, listing_id, price_paid, timezone, idempotency_key)
    VALUES (p_buyer_id, p_listing_id, v_price, p_timezone, p_idempotency_key)
    RETURNING id INTO v_purchase_id;
    
    -- 13. Update sales count
    UPDATE marketplace_listings 
    SET sales_count = COALESCE(sales_count, 0) + 1
    WHERE id = p_listing_id;
    
    -- 14. Return success
    RETURN jsonb_build_object(
        'success', true,
        'purchase_id', v_purchase_id,
        'price_paid', v_price,
        'seller_revenue', v_seller_revenue,
        'buyer_balance_monthly', v_new_buyer_monthly,
        'buyer_balance_permanent', v_new_buyer_permanent,
        'message', 'Purchase successful'
    );
    
EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object(
        'success', false,
        'error', SQLERRM,
        'status', 500
    );
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION execute_marketplace_purchase IS 'Atomic marketplace purchase with all credit operations in single transaction';

CREATE OR REPLACE FUNCTION check_webhook_idempotency(
    p_event_id TEXT,
    p_event_type TEXT,
    p_payload JSONB DEFAULT NULL
) RETURNS JSONB AS $$
DECLARE
    v_existing RECORD;
BEGIN
    SELECT * INTO v_existing FROM webhook_events WHERE event_id = p_event_id;
    
    IF FOUND THEN
        RETURN jsonb_build_object('success', true, 'idempotent', true, 'message', 'Event already processed', 'original_result', v_existing.result);
    END IF;
    
    INSERT INTO webhook_events (event_id, event_type, payload) VALUES (p_event_id, p_event_type, p_payload);
    
    RETURN jsonb_build_object('success', true, 'idempotent', false, 'should_process', true);
    
EXCEPTION WHEN unique_violation THEN
    RETURN jsonb_build_object('success', true, 'idempotent', true, 'message', 'Concurrent processing detected');
WHEN OTHERS THEN
    RETURN jsonb_build_object('success', false, 'error', SQLERRM);
END;
$$ LANGUAGE plpgsql;

-- ==========================================
-- v3.23: Task Queue System
-- ==========================================

CREATE TABLE IF NOT EXISTS generation_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id VARCHAR(32) NOT NULL UNIQUE,
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    task_type VARCHAR(50) NOT NULL DEFAULT 'image_generation',
    priority INTEGER NOT NULL DEFAULT 0,
    params JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    progress INTEGER NOT NULL DEFAULT 0,
    current_step INTEGER DEFAULT 0,
    total_steps INTEGER DEFAULT 0,
    progress_message VARCHAR(500),
    result JSONB,
    error_message TEXT,
    error_code VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    queued_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    worker_id VARCHAR(100),
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '24 hours')
);

CREATE INDEX IF NOT EXISTS idx_generation_tasks_user_id ON generation_tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_generation_tasks_task_id ON generation_tasks(task_id);
CREATE INDEX IF NOT EXISTS idx_generation_tasks_status ON generation_tasks(status);
CREATE INDEX IF NOT EXISTS idx_generation_tasks_created_at ON generation_tasks(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_generation_tasks_expires_at ON generation_tasks(expires_at) WHERE status IN ('completed', 'failed');

ALTER TABLE generation_tasks ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS generation_tasks_select_policy ON generation_tasks;
DROP POLICY IF EXISTS generation_tasks_service_policy ON generation_tasks;

CREATE POLICY generation_tasks_select_policy ON generation_tasks
    FOR SELECT
    USING (user_id = auth.uid()::text OR auth.role() = 'service_role');

CREATE POLICY generation_tasks_service_policy ON generation_tasks
    FOR ALL
    USING (auth.role() = 'service_role');

-- Task Queue RPC Functions
CREATE OR REPLACE FUNCTION create_generation_task(
    p_task_id VARCHAR(32),
    p_user_id TEXT,
    p_task_type VARCHAR(50),
    p_params JSONB,
    p_priority INTEGER DEFAULT 0,
    p_total_steps INTEGER DEFAULT 8
) RETURNS JSONB AS $$
DECLARE
    v_task_record generation_tasks%ROWTYPE;
BEGIN
    SELECT * INTO v_task_record FROM generation_tasks WHERE task_id = p_task_id;
    
    IF FOUND THEN
        RETURN jsonb_build_object('success', true, 'idempotent', true, 'task_id', p_task_id, 'status', v_task_record.status);
    END IF;
    
    INSERT INTO generation_tasks (task_id, user_id, task_type, params, priority, total_steps, status)
    VALUES (p_task_id, p_user_id, p_task_type, p_params, p_priority, p_total_steps, 'pending')
    RETURNING * INTO v_task_record;
    
    RETURN jsonb_build_object('success', true, 'idempotent', false, 'task_id', p_task_id, 'id', v_task_record.id, 'status', v_task_record.status);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_task_status(
    p_task_id VARCHAR(32),
    p_status VARCHAR(20),
    p_progress INTEGER DEFAULT NULL,
    p_current_step INTEGER DEFAULT NULL,
    p_progress_message VARCHAR(500) DEFAULT NULL,
    p_result JSONB DEFAULT NULL,
    p_error_message TEXT DEFAULT NULL,
    p_error_code VARCHAR(50) DEFAULT NULL,
    p_worker_id VARCHAR(100) DEFAULT NULL
) RETURNS JSONB AS $$
DECLARE
    v_task generation_tasks%ROWTYPE;
BEGIN
    UPDATE generation_tasks SET
        status = p_status,
        progress = COALESCE(p_progress, progress),
        current_step = COALESCE(p_current_step, current_step),
        progress_message = COALESCE(p_progress_message, progress_message),
        result = COALESCE(p_result, result),
        error_message = COALESCE(p_error_message, error_message),
        error_code = COALESCE(p_error_code, error_code),
        worker_id = COALESCE(p_worker_id, worker_id),
        started_at = CASE WHEN p_status = 'processing' AND started_at IS NULL THEN NOW() ELSE started_at END,
        completed_at = CASE WHEN p_status IN ('completed', 'failed', 'cancelled') THEN NOW() ELSE completed_at END,
        queued_at = CASE WHEN p_status = 'queued' AND queued_at IS NULL THEN NOW() ELSE queued_at END
    WHERE task_id = p_task_id
    RETURNING * INTO v_task;
    
    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', false, 'error', 'Task not found');
    END IF;
    
    RETURN jsonb_build_object('success', true, 'task_id', p_task_id, 'status', v_task.status, 'progress', v_task.progress);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_task_details(
    p_task_id VARCHAR(32),
    p_user_id TEXT DEFAULT NULL
) RETURNS JSONB AS $$
DECLARE
    v_task generation_tasks%ROWTYPE;
BEGIN
    IF p_user_id IS NOT NULL THEN
        SELECT * INTO v_task FROM generation_tasks WHERE task_id = p_task_id AND user_id = p_user_id;
    ELSE
        SELECT * INTO v_task FROM generation_tasks WHERE task_id = p_task_id;
    END IF;
    
    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', false, 'error', 'Task not found');
    END IF;
    
    RETURN jsonb_build_object(
        'success', true, 'task_id', v_task.task_id, 'status', v_task.status,
        'progress', v_task.progress, 'current_step', v_task.current_step, 'total_steps', v_task.total_steps,
        'progress_message', v_task.progress_message, 'result', v_task.result,
        'error_message', v_task.error_message, 'error_code', v_task.error_code,
        'created_at', v_task.created_at, 'started_at', v_task.started_at, 'completed_at', v_task.completed_at
    );
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION cleanup_expired_tasks() RETURNS INTEGER AS $$
DECLARE
    v_deleted INTEGER;
BEGIN
    DELETE FROM generation_tasks WHERE expires_at < NOW() AND status IN ('completed', 'failed', 'cancelled');
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    RETURN v_deleted;
END;
$$ LANGUAGE plpgsql;

-- ==========================================
-- v3.13 RLS Fix: Holiday Themes
-- ==========================================

ALTER TABLE holiday_themes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Holiday themes are publicly readable" ON holiday_themes;
DROP POLICY IF EXISTS "Only admins can modify holiday themes" ON holiday_themes;

CREATE POLICY "Holiday themes are publicly readable" ON holiday_themes
    FOR SELECT USING (true);

CREATE POLICY "Only admins can modify holiday themes" ON holiday_themes
    FOR ALL USING (is_admin()) WITH CHECK (is_admin());

-- ==========================================
-- Done! v3.23 Complete Database Initialization
-- ==========================================

DO $$
BEGIN
  RAISE NOTICE '';
  RAISE NOTICE '=====================================================';
  RAISE NOTICE '✅ Make Decodables Database v3.24 - Setup Complete';
  RAISE NOTICE '=====================================================';
  RAISE NOTICE '';
  RAISE NOTICE 'Tables created: 38+';
  RAISE NOTICE 'Views created: 5';
  RAISE NOTICE 'Materialized views: 3';
  RAISE NOTICE 'Functions: 25+';
  RAISE NOTICE 'Triggers: 11+';
  RAISE NOTICE 'RLS Policies: 60+';
  RAISE NOTICE '';
  RAISE NOTICE 'Storage Buckets:';
  RAISE NOTICE '  - make-decodables-s (system assets, 10MB)';
  RAISE NOTICE '  - make-decodables-u (user content, 50MB)';
  RAISE NOTICE '';
  RAISE NOTICE 'Latest updates included:';
  RAISE NOTICE '  - v3.20: A/B Testing system';
  RAISE NOTICE '  - v3.22: Atomic transactions, Webhook idempotency';
  RAISE NOTICE '  - v3.23: Task queue system (generation_tasks)';
  RAISE NOTICE '  - v3.24: User generations history';
  RAISE NOTICE '=====================================================';
END $$;
