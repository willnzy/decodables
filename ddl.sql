-- ==============================================================================
-- Make Decodables Database Initialization Script (v3.2 - Admin Analytics + System Config)
-- Includes: core schema + final RLS policies
-- 
-- Highlights (v3.0):
-- - Credit buckets: credits_monthly + credits_permanent
-- - Marketplace tables: marketplace_listings, user_purchases
-- - Notification system: notifications
-- - Discount system: user_discounts
-- - system_resources adds allowed_tiers
--
-- Highlights (v3.1):
-- - assets.metadata column for scanned results, canvas elements, etc.
-- - assets.type supports 'scanned' (AI Smart Scan OCR)
--
-- Highlights (v3.2):
-- - admin_operation_logs: admin audit trail
-- - user_events: detailed user event tracking
-- - aggregated_stats: scheduled precomputed stats
-- - system_config: dynamic config (rate limits, analytics, etc.)
-- - notifications adds notification_type column
-- ==============================================================================

-- ==========================================
-- Part 1: Schema Definition
-- ==========================================

-- 1. User profiles
create table if not exists profiles (
  id text primary key, -- Matches Clerk user_id
  email text,
  username text,
  first_name text,     -- From Clerk
  last_name text,      -- From Clerk
  avatar_url text,
  
  -- Unique user code (format: YYYYMMDDHHMMSS + ms + 6 digits)
  -- Example: 20251230143025123000001
  user_code text unique,

  -- Credit buckets (important)
  credits_monthly int default 0,    -- Subscription grant: resets monthly, no rollover
  credits_permanent int default 0,  -- Earned via purchase/sales: never expires

  tier text default 'free', -- 'free', 'starter', 'pro'

  -- Subscription status (used for membership checks)
  subscription_status text default 'inactive', -- 'active' | 'inactive' | 'past_due' | 'canceled' | 'trialing'
  subscription_valid_until timestamptz,        -- Optional: offline membership check
  monthly_credits_cycle_anchor timestamptz,    -- Optional: anchor for monthly refresh

  stripe_customer_id text,
  role text default 'user', -- 'user', 'admin'
  created_at timestamptz default now()
);

-- 2. User discounts
create table if not exists user_discounts (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id) not null,
  discount_percent int not null,
  valid_until timestamptz,
  target_plan text,
  created_at timestamptz default now()
);

-- 3. Credit ledger
create table if not exists credit_transactions (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id) not null,

  amount int not null, -- Delta (+100, -50)

  -- Identify which bucket was affected for auditing
  bucket text not null default 'permanent', -- 'monthly' | 'permanent'

  balance_monthly_after int not null default 0,
  balance_permanent_after int not null default 0,

  type text not null, -- 'signup_bonus', 'topup_purchase', 'sub_grant', 'generation', 'ocr', 'market_purchase', 'market_sale', 'admin_adj'
  description text,
  created_at timestamptz default now()
);

-- 4. User projects
create table if not exists projects (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id) not null,
  title text default 'My Magic Story',
  canvas_data jsonb default '{}'::jsonb, -- Fabric.js JSON
  thumbnail_url text,
  last_downloaded_hash text, -- Cache/version identifier (no billing impact)
  is_deleted boolean default false,
  deleted_at timestamptz default null, -- Deletion timestamp for history

  -- Optional flag for locked content
  contains_locked_elements boolean default false,
  
  -- Source listing if project was created from a purchased template
  source_listing_id uuid references marketplace_listings(id),

  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- 5. Marketplace listings
-- PRD: must pass moderation + price caps + usage tracking
create table if not exists marketplace_listings (
  id uuid default gen_random_uuid() primary key,
  seller_id text references profiles(id), -- NULL = official asset
  title text not null,
  description text,
  thumbnail_url text not null,
  resource_url text not null,
  resource_type text not null, -- 'project' | 'asset' (e.g. 'image'|'sticker')
  price_credits int not null default 0, -- 0..500
  allowed_tiers text[] not null default '{free, starter, pro}', -- Tier-gated access/purchase

  usage_count bigint default 0, -- Times used (leaderboards)
  sales_count int default 0, -- Number of sales

  is_public boolean default false,
  is_deleted boolean default false,

  -- Moderation fields
  moderation_status text not null default 'draft', -- 'draft'|'pending'|'approved'|'rejected'
  moderation_note text, -- Rejection reason / admin notes
  moderated_by text references profiles(id), -- Moderator ID
  moderated_at timestamptz, -- Moderation timestamp

  created_at timestamptz default now()
);

-- 6. User purchases
create table if not exists user_purchases (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id) not null,
  listing_id uuid references marketplace_listings(id) not null,
  price_paid int not null,
  purchased_at timestamptz default now(),
  unique(user_id, listing_id)
);

-- 7. User assets
-- Stores user uploads, AI generations, and OCR scans.
-- type field:
--   'uploaded'     - user upload
--   'ai_generated' - AI-generated image
--   'scanned'      - AI Smart Scan (OCR) result
-- metadata (scanned only):
--   source_image_url: original scan
--   ocr_result: structured OCR output
--   canvas_elements: precomputed canvas elements
create table if not exists assets (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id) not null,
  project_id uuid references projects(id), -- Optional project association
  url text not null,
  type text not null, -- 'uploaded' | 'ai_generated' | 'scanned'
  prompt text, -- Prompt for AI generations
  metadata jsonb, -- Structured scan/canvas data (added v3.1)
  is_deleted boolean default false,
  created_at timestamptz default now()
);
create index if not exists idx_assets_user_proj on assets(user_id, project_id);

-- 8. Notifications
create table if not exists notifications (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id), -- NULL = broadcast
  target_group text, -- 'all', 'free', 'starter', 'pro'
  notification_type text default 'system', -- 'system', 'promotion', 'update', 'warning'
  title text not null,
  content text not null,
  is_read boolean default false,
  created_at timestamptz default now()
);

-- 9. System resources
create table if not exists system_resources (
  id uuid default gen_random_uuid() primary key,
  type text not null, -- 'sticker', 'project'
  category text,
  url text not null,
  allowed_tiers text[] default '{free, starter, pro}',
  created_at timestamptz default now()
);

-- 10. Activity logs
create table if not exists activity_logs (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id),
  action text not null,
  metadata jsonb,
  created_at timestamptz default now()
);

-- 11. Support & admin ops
create table if not exists support_tickets (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id),
  admin_id text references profiles(id),
  category text not null,
  content text,
  metadata jsonb,
  status text default 'closed',
  created_at timestamptz default now()
);

-- 12. Listing usage table (deduplicated counts)
-- PRD: track usage_count with unique key (listing_id, user_id, project_id)
create table if not exists listing_usage (
  id uuid default gen_random_uuid() primary key,
  listing_id uuid references marketplace_listings(id) not null,
  used_by_user_id text references profiles(id) not null,
  project_id uuid references projects(id) not null,
  used_at timestamptz default now(),
  unique(listing_id, used_by_user_id, project_id)
);

-- 13. Leaderboard snapshots (cache)
-- Optional cache for periodic leaderboards
create table if not exists leaderboard_snapshots (
  id uuid default gen_random_uuid() primary key,
  period_start date not null,
  period_end date not null,
  board_type text not null, -- 'all' | 'project' | 'asset'
  top_list jsonb not null, -- [{listing_id, usage_count, rank}, ...]
  created_at timestamptz default now(),
  unique(period_start, period_end, board_type)
);

-- 14. Admin operation logs (audit)
-- Added v3.2: capture all admin actions for auditing
create table if not exists admin_operation_logs (
  id uuid default gen_random_uuid() primary key,
  admin_id text not null references profiles(id),
  operation_type text not null, -- 'credit_adjust', 'tier_change', 'refund', 'subscription_cancel', etc.
  target_user_id text references profiles(id),
  details text,
  reason text,
  created_at timestamptz default now()
);
create index if not exists idx_admin_logs_created_at on admin_operation_logs(created_at desc);
create index if not exists idx_admin_logs_operation_type on admin_operation_logs(operation_type);
create index if not exists idx_admin_logs_admin_id on admin_operation_logs(admin_id);
create index if not exists idx_admin_logs_target_user on admin_operation_logs(target_user_id);

-- 15. User events (behavior tracking)
-- Added v3.2: supports analytics and optimization
create table if not exists user_events (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id), -- Nullable for anonymous users
  event_type text not null,
  properties jsonb default '{}',
  session_id text,
  created_at timestamptz default now()
);
create index if not exists idx_user_events_created_at on user_events(created_at desc);
create index if not exists idx_user_events_event_type on user_events(event_type);
create index if not exists idx_user_events_user_id on user_events(user_id);
create index if not exists idx_user_events_session on user_events(session_id);
create index if not exists idx_user_events_properties on user_events using gin(properties);

-- 16. Aggregated stats (precomputed)
-- Added v3.2: store scheduled aggregation output
create table if not exists aggregated_stats (
  id uuid default gen_random_uuid() primary key,
  date date not null,
  stat_type text not null, -- 'daily_users', 'daily_revenue', 'daily_projects', etc.
  data jsonb not null default '{}',
  updated_at timestamptz default now(),
  unique(date, stat_type)
);
create index if not exists idx_agg_stats_date on aggregated_stats(date desc);
create index if not exists idx_agg_stats_type on aggregated_stats(stat_type);
create index if not exists idx_agg_stats_date_type on aggregated_stats(date desc, stat_type);

-- 17. System config (dynamic parameters)
-- Added v3.2: runtime-adjustable settings (rate limits, analytics, etc.)
create table if not exists system_config (
  id uuid default gen_random_uuid() primary key,
  config_key text unique not null,
  config_value jsonb not null,
  category text not null default 'general', -- 'rate_limit', 'analytics', 'system'
  description text,
  is_active boolean default true,
  updated_at timestamptz default now(),
  updated_by text -- Last modifying admin ID
);
create index if not exists idx_system_config_key on system_config(config_key);
create index if not exists idx_system_config_category on system_config(category);

-- ==========================================
-- Part 2: RLS policy configuration
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
ALTER TABLE listing_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE leaderboard_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_operation_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE aggregated_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_config ENABLE ROW LEVEL SECURITY;

create or replace function is_admin() returns boolean language sql security definer as $$
select exists (
  select 1 from profiles
  where id = (select auth.jwt() ->> 'sub') and role = 'admin'
);
$$;

-- [Profiles]
drop policy if exists "View profiles" on profiles;
create policy "View profiles" on profiles for select
using ((select auth.jwt() ->> 'sub') = id or is_admin());

drop policy if exists "Update profiles" on profiles;
create policy "Update profiles" on profiles for update
using ((select auth.jwt() ->> 'sub') = id);

drop policy if exists "Insert profiles" on profiles;
create policy "Insert profiles" on profiles for insert
with check ((select auth.jwt() ->> 'sub') = id);

-- [User Discounts]
drop policy if exists "Users read own discounts" on user_discounts;
create policy "Users read own discounts" on user_discounts for select
using ((select auth.jwt() ->> 'sub') = user_id or is_admin());

-- [Projects]
drop policy if exists "Users can CRUD own projects" on projects;
create policy "Users can CRUD own projects" on projects for all
using ((select auth.jwt() ->> 'sub') = user_id);

-- [Marketplace Listings]
drop policy if exists "Read Listings" on marketplace_listings;
create policy "Read Listings" on marketplace_listings for select
using (is_public = true or (select auth.jwt() ->> 'sub') = seller_id or is_admin());

drop policy if exists "Manage Listings" on marketplace_listings;
create policy "Manage Listings" on marketplace_listings for update
using ((select auth.jwt() ->> 'sub') = seller_id);

drop policy if exists "Insert Listings" on marketplace_listings;
create policy "Insert Listings" on marketplace_listings for insert
with check ((select auth.jwt() ->> 'sub') = seller_id);

-- [User Purchases]
drop policy if exists "Read Purchases" on user_purchases;
create policy "Read Purchases" on user_purchases for select
using ((select auth.jwt() ->> 'sub') = user_id);

drop policy if exists "Insert Purchases" on user_purchases;
create policy "Insert Purchases" on user_purchases for insert
with check ((select auth.jwt() ->> 'sub') = user_id);

-- [Assets]
drop policy if exists "Users can CRUD own assets" on assets;
create policy "Users can CRUD own assets" on assets for all
using ((select auth.jwt() ->> 'sub') = user_id);

-- [Notifications]
drop policy if exists "Read Notifications" on notifications;
create policy "Read Notifications" on notifications for select
using (user_id = (select auth.jwt() ->> 'sub') or user_id is null);

-- [Credit Transactions]
drop policy if exists "Users view own txs or Admin view all" on credit_transactions;
create policy "Users view own txs or Admin view all" on credit_transactions for select
using ((select auth.jwt() ->> 'sub') = user_id or is_admin());

-- [System Resources]
drop policy if exists "Public can view system resources" on system_resources;
create policy "Public can view system resources" on system_resources for select
using (true);

-- [Activity Logs]
drop policy if exists "Users can insert own logs" on activity_logs;
create policy "Users can insert own logs" on activity_logs for insert
with check ((select auth.jwt() ->> 'sub') = user_id);

drop policy if exists "Users view own logs or Admin view all" on activity_logs;
create policy "Users view own logs or Admin view all" on activity_logs for select
using ((select auth.jwt() ->> 'sub') = user_id or is_admin());

-- [Support Tickets]
drop policy if exists "Users CRUD own tickets or Admin manage all" on support_tickets;
create policy "Users CRUD own tickets or Admin manage all" on support_tickets for all
using ((select auth.jwt() ->> 'sub') = user_id or is_admin());

-- [Listing Usage]
drop policy if exists "Users can insert own usage" on listing_usage;
create policy "Users can insert own usage" on listing_usage for insert
with check ((select auth.jwt() ->> 'sub') = used_by_user_id);

drop policy if exists "Users view own usage or Admin view all" on listing_usage;
create policy "Users view own usage or Admin view all" on listing_usage for select
using ((select auth.jwt() ->> 'sub') = used_by_user_id or is_admin());

-- [Leaderboard Snapshots]
drop policy if exists "Public can view leaderboard" on leaderboard_snapshots;
create policy "Public can view leaderboard" on leaderboard_snapshots for select
using (true);

-- [Admin Operation Logs] (v3.2)
-- Restrict to service_role (backend via service key)
drop policy if exists "Service role full access to admin_logs" on admin_operation_logs;
create policy "Service role full access to admin_logs" on admin_operation_logs for all
to service_role
using (true)
with check (true);

-- [User Events] (v3.2)
-- Full access for service_role
drop policy if exists "Service role full access to user_events" on user_events;
create policy "Service role full access to user_events" on user_events for all
to service_role
using (true)
with check (true);

-- [Aggregated Stats] (v3.2)
-- Restrict to service_role
drop policy if exists "Service role full access to aggregated_stats" on aggregated_stats;
create policy "Service role full access to aggregated_stats" on aggregated_stats for all
to service_role
using (true)
with check (true);

-- [System Config] (v3.2)
-- Restrict to service_role
drop policy if exists "Service role full access to system_config" on system_config;
create policy "Service role full access to system_config" on system_config for all
to service_role
using (true)
with check (true);

-- ==========================================
-- Part 3: Migration scripts (upgrade from older versions)
-- ==========================================
-- Run these commands when migrating:

-- 1. Add new columns to profiles (v3.0)
-- ALTER TABLE profiles ADD COLUMN IF NOT EXISTS credits_monthly int default 0;
-- ALTER TABLE profiles ADD COLUMN IF NOT EXISTS credits_permanent int default 0;
-- ALTER TABLE profiles ADD COLUMN IF NOT EXISTS subscription_status text default 'inactive';
-- ALTER TABLE profiles ADD COLUMN IF NOT EXISTS subscription_valid_until timestamptz;
-- ALTER TABLE profiles ADD COLUMN IF NOT EXISTS monthly_credits_cycle_anchor timestamptz;

-- 2. Move legacy credits into credits_permanent (v3.0)
-- UPDATE profiles SET credits_permanent = COALESCE(credits, 0) WHERE credits_permanent = 0;

-- 3. Add new columns to credit_transactions (v3.0)
-- ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS bucket text default 'permanent';
-- ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS balance_monthly_after int default 0;
-- ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS balance_permanent_after int default 0;

-- 4. Update legacy credit_transactions rows (v3.0)
-- UPDATE credit_transactions SET balance_permanent_after = balance_after WHERE balance_permanent_after = 0;

-- 5. Add allowed_tiers to system_resources (v3.0)
-- ALTER TABLE system_resources ADD COLUMN IF NOT EXISTS allowed_tiers text[] default '{free, starter, pro}';
-- UPDATE system_resources SET allowed_tiers = CASE WHEN is_pro_only THEN '{pro}' ELSE '{free, starter, pro}' END;

-- ==========================================
-- Part 4: v3.1 migration (PRD parity + Advanced OCR)
-- ==========================================
-- Run these when upgrading:

-- 1. Add moderation/usage fields to marketplace_listings
ALTER TABLE marketplace_listings ADD COLUMN IF NOT EXISTS usage_count bigint default 0;
ALTER TABLE marketplace_listings ADD COLUMN IF NOT EXISTS moderation_status text not null default 'draft';
ALTER TABLE marketplace_listings ADD COLUMN IF NOT EXISTS moderation_note text;
ALTER TABLE marketplace_listings ADD COLUMN IF NOT EXISTS moderated_by text references profiles(id);
ALTER TABLE marketplace_listings ADD COLUMN IF NOT EXISTS moderated_at timestamptz;

-- 2. Add OCR metadata column to assets
ALTER TABLE assets ADD COLUMN IF NOT EXISTS metadata jsonb;

-- 3. Create listing_usage if missing
CREATE TABLE IF NOT EXISTS listing_usage (
  id uuid default gen_random_uuid() primary key,
  listing_id uuid references marketplace_listings(id) not null,
  used_by_user_id text references profiles(id) not null,
  project_id uuid references projects(id) not null,
  used_at timestamptz default now(),
  unique(listing_id, used_by_user_id, project_id)
);
ALTER TABLE listing_usage ENABLE ROW LEVEL SECURITY;

-- 4. Create leaderboard_snapshots if missing
CREATE TABLE IF NOT EXISTS leaderboard_snapshots (
  id uuid default gen_random_uuid() primary key,
  period_start date not null,
  period_end date not null,
  board_type text not null,
  top_list jsonb not null,
  created_at timestamptz default now(),
  unique(period_start, period_end, board_type)
);
ALTER TABLE leaderboard_snapshots ENABLE ROW LEVEL SECURITY;

-- 5. Normalize old 'user_upload' to 'uploaded'
UPDATE assets SET type = 'uploaded' WHERE type = 'user_upload';

-- 6. Set legacy approved listings without status to 'approved'
UPDATE marketplace_listings SET moderation_status = 'approved' WHERE moderation_status IS NULL AND is_public = true;

-- ==========================================
-- Part 5: v3.2 migration (Admin Analytics + System Config)
-- ==========================================
-- Run these when upgrading:

-- 1. Add notification_type to notifications
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS notification_type TEXT DEFAULT 'system';
CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(notification_type);

-- 2. Create admin_operation_logs if missing
CREATE TABLE IF NOT EXISTS admin_operation_logs (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  admin_id TEXT NOT NULL REFERENCES profiles(id),
  operation_type TEXT NOT NULL,
  target_user_id TEXT REFERENCES profiles(id),
  details TEXT,
  reason TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_admin_logs_created_at ON admin_operation_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_logs_operation_type ON admin_operation_logs(operation_type);
CREATE INDEX IF NOT EXISTS idx_admin_logs_admin_id ON admin_operation_logs(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_logs_target_user ON admin_operation_logs(target_user_id);
ALTER TABLE admin_operation_logs ENABLE ROW LEVEL SECURITY;

-- 3. Create user_events table if missing
CREATE TABLE IF NOT EXISTS user_events (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id TEXT REFERENCES profiles(id),
  event_type TEXT NOT NULL,
  properties JSONB DEFAULT '{}',
  session_id TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_user_events_created_at ON user_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_events_event_type ON user_events(event_type);
CREATE INDEX IF NOT EXISTS idx_user_events_user_id ON user_events(user_id);
CREATE INDEX IF NOT EXISTS idx_user_events_session ON user_events(session_id);
CREATE INDEX IF NOT EXISTS idx_user_events_properties ON user_events USING GIN(properties);
ALTER TABLE user_events ENABLE ROW LEVEL SECURITY;

-- 4. Create aggregated_stats table if missing
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
ALTER TABLE aggregated_stats ENABLE ROW LEVEL SECURITY;

-- 5. Create system_config table if missing
CREATE TABLE IF NOT EXISTS system_config (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  config_key TEXT UNIQUE NOT NULL,
  config_value JSONB NOT NULL,
  category TEXT NOT NULL DEFAULT 'general',
  description TEXT,
  is_active BOOLEAN DEFAULT true,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  updated_by TEXT
);
CREATE INDEX IF NOT EXISTS idx_system_config_key ON system_config(config_key);
CREATE INDEX IF NOT EXISTS idx_system_config_category ON system_config(category);
ALTER TABLE system_config ENABLE ROW LEVEL SECURITY;

-- 6. RLS policy (service_role only)
DROP POLICY IF EXISTS "Service role full access to admin_logs" ON admin_operation_logs;
CREATE POLICY "Service role full access to admin_logs" ON admin_operation_logs FOR ALL
TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role full access to user_events" ON user_events;
CREATE POLICY "Service role full access to user_events" ON user_events FOR ALL
TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role full access to aggregated_stats" ON aggregated_stats;
CREATE POLICY "Service role full access to aggregated_stats" ON aggregated_stats FOR ALL
TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role full access to system_config" ON system_config;
CREATE POLICY "Service role full access to system_config" ON system_config FOR ALL
TO service_role USING (true) WITH CHECK (true);

-- 7. Create system config helper functions
CREATE OR REPLACE FUNCTION update_system_config_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_system_config_timestamp ON system_config;
CREATE TRIGGER trigger_update_system_config_timestamp
    BEFORE UPDATE ON system_config
    FOR EACH ROW
    EXECUTE FUNCTION update_system_config_timestamp();

-- 8. Create helper to fetch rate-limit config
CREATE OR REPLACE FUNCTION get_rate_limit_config(p_config_key TEXT)
RETURNS JSONB AS $$
DECLARE
    v_config JSONB;
BEGIN
    SELECT config_value INTO v_config
    FROM system_config
    WHERE config_key = p_config_key AND is_active = true;
    
    IF v_config IS NULL THEN
        SELECT config_value INTO v_config
        FROM system_config
        WHERE config_key = 'rate_limit.global.default' AND is_active = true;
    END IF;
    
    RETURN COALESCE(v_config, '{"limit": 100, "window": "minute", "enabled": true}'::JSONB);
END;
$$ LANGUAGE plpgsql;

-- 9. Create aggregated stats helper functions
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

-- 10. Add optimized indexes
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

-- 11. Insert default system configs (rate limits)
INSERT INTO system_config (config_key, config_value, category, description) VALUES
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
