-- ==============================================================================
-- Make Decodables Database Initialization Script (v3.8 - Naming Convention Refactor)
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
-- - system_configs: dynamic config (rate limits, analytics, etc.)
-- - notifications adds notification_type column
--
-- Highlights (v3.3):
-- - Dashboard refactor: soft delete enhancement (is_hidden_from_trash)
-- - Purchase tracking fields (is_purchased, origin_owner_id, listing_status)
-- - Seller stats fields (unique_buyers_count, total_revenue)
-- - Dashboard views (dashboard_projects, dashboard_assets, seller_stats_summary)
-- - Auto-sync triggers for listing status
-- - marketplace_listings adds version, changelog, version_history
-- - content_reports table for user reports
--
-- Highlights (v3.4):
-- - analytics_events table for frontend analytics tracking
--
-- Highlights (v3.5):
-- - error_logs table for centralized error monitoring
--
-- Highlights (v3.6):
-- - asset_prompt_templates table for AI image generation presets (5W1H naming)
--
-- Highlights (v3.7):
-- - page_prompt_templates table for AI Design Page presets
--
-- Highlights (v3.8):
-- - Naming convention refactor: plural tables, 5W1H column names
-- - listing_usage → listing_usages
-- - system_config → system_configs
-- - user_generation_templates → asset_prompt_templates
-- - page_design_templates → page_prompt_templates
-- - character_type/action_type/setting_type → who_type/what_type/where_type
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
  
  -- v3.4: User cohort for retention analysis
  cohort_month text, -- Format: '2026-01' (auto-set from created_at)
  
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

-- 3. Credit ledger (APPEND-ONLY - no updates or deletes allowed)
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
  
  -- v3.4: Idempotency key for duplicate prevention
  idempotency_key text,
  
  created_at timestamptz default now()
);
-- Idempotency index
create unique index if not exists idx_transactions_idempotency 
on credit_transactions(idempotency_key) where idempotency_key is not null;

-- 4. User projects
create table if not exists projects (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id) not null,
  title text default 'My Magic Story',
  canvas_data jsonb default '{}'::jsonb, -- Fabric.js JSON
  thumbnail_url text,
  last_downloaded_hash text, -- Cache/version identifier (no billing impact)
  
  -- Soft delete fields
  is_deleted boolean default false,
  deleted_at timestamptz default null, -- Deletion timestamp for 30-day retention
  is_hidden_from_trash boolean default false, -- v3.3: True = hidden from trash UI

  -- Optional flag for locked content
  contains_locked_elements boolean default false,
  
  -- Source listing if project was created from a purchased template
  source_listing_id uuid references marketplace_listings(id),
  
  -- v3.3: Purchase tracking & dashboard optimization
  is_purchased boolean default false, -- Redundant flag for fast filtering
  origin_owner_id text references profiles(id), -- Original creator (for purchased projects)
  listing_status text default null, -- Cached: 'draft'|'pending'|'approved'|'rejected'
  marketplace_listing_id uuid references marketplace_listings(id), -- Link to own listing

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
  resource_id uuid, -- v3.3: Links to actual project.id or asset.id
  price_credits int not null default 0, -- 0..500
  allowed_tiers text[] not null default '{free, starter, pro}', -- Tier-gated access/purchase

  usage_count bigint default 0, -- Times used (leaderboards)
  sales_count int default 0, -- Number of sales
  unique_buyers_count int default 0, -- v3.3: Distinct buyer count
  total_revenue int default 0, -- v3.3: Accumulated seller earnings

  is_public boolean default false,
  is_deleted boolean default false,

  -- Moderation fields
  moderation_status text not null default 'draft', -- 'draft'|'pending'|'approved'|'rejected'
  moderation_note text, -- Rejection reason / admin notes
  moderated_by text references profiles(id), -- Moderator ID
  moderated_at timestamptz, -- Moderation timestamp
  
  -- Version tracking fields (added v3.1)
  version varchar(20) default '1.0', -- Current version number
  changelog text default '', -- What's new in current version
  version_history jsonb default '[]'::jsonb, -- [{version, changelog, published_at}]

  created_at timestamptz default now()
);

-- 6. User purchases
create table if not exists user_purchases (
  id uuid default gen_random_uuid() primary key,
  user_id text references profiles(id) not null,
  listing_id uuid references marketplace_listings(id) not null,
  price_paid int not null,
  purchased_at timestamptz default now(),
  
  -- v3.4: Idempotency key for duplicate prevention
  idempotency_key text,
  
  -- v3.4: Snapshot - capture listing state at purchase time
  snapshot_title text,
  snapshot_thumbnail_url text,
  snapshot_description text,
  snapshot_version text,
  snapshot_resource_type text,
  snapshot_resource_id uuid,
  
  -- v3.4: Analytics tracking
  utm_source text,
  utm_medium text,
  utm_campaign text,
  referral_context text, -- 'homepage', 'search', 'category', 'direct_link'
  
  unique(user_id, listing_id)
);
-- Idempotency index (allow NULL, only constrain non-null values)
create unique index if not exists idx_purchases_idempotency 
on user_purchases(idempotency_key) where idempotency_key is not null;

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
  description text, -- v3.3: Separate description field
  metadata jsonb, -- Structured scan/canvas data (added v3.1)
  
  -- Soft delete fields
  is_deleted boolean default false,
  deleted_at timestamptz default null, -- v3.3: Deletion timestamp for 30-day retention
  is_hidden_from_trash boolean default false, -- v3.3: True = hidden from trash UI
  
  -- v3.3: Purchase tracking & dashboard optimization
  source_listing_id uuid references marketplace_listings(id), -- Purchased from this listing
  is_purchased boolean default false, -- Redundant flag for fast filtering
  origin_owner_id text references profiles(id), -- Original creator (for purchased assets)
  listing_status text default null, -- Cached: 'draft'|'pending'|'approved'|'rejected'
  marketplace_listing_id uuid references marketplace_listings(id), -- Link to own listing
  
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

-- 12. Listing usages table (deduplicated counts)
-- PRD: track usage_count with unique key (listing_id, user_id, project_id)
create table if not exists listing_usages (
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

-- 16. Analytics events (frontend tracking)
-- Added v3.4: stores frontend analytics events for user behavior tracking
create table if not exists analytics_events (
  id uuid default gen_random_uuid() primary key,
  user_id text, -- Optional, may be null for anonymous users
  event_type text not null,
  event_level text, -- 'critical', 'important', 'normal'
  event_data jsonb not null default '{}',
  session_id text,
  created_at timestamptz default now()
);
create index if not exists idx_analytics_events_user_id on analytics_events(user_id);
create index if not exists idx_analytics_events_event_type on analytics_events(event_type);
create index if not exists idx_analytics_events_created_at on analytics_events(created_at desc);
create index if not exists idx_analytics_events_session_id on analytics_events(session_id);

-- 17. Error logs (centralized error monitoring)
-- Added v3.5: stores frontend and API errors for debugging and monitoring
create table if not exists error_logs (
  id uuid default gen_random_uuid() primary key,
  
  -- Error identification
  error_id varchar(100),           -- Frontend generated error ID
  error_type varchar(50) not null, -- API, NETWORK, JS_ERROR, UNHANDLED_REJECTION, REACT_ERROR, CORS, OTHER
  error_code varchar(50),          -- Error code (UNAUTHORIZED, NETWORK_ERROR, etc.)
  
  -- Error details
  message text not null,
  status_code integer,             -- HTTP status code for API errors
  endpoint varchar(500),           -- API endpoint
  method varchar(10),              -- HTTP method
  
  -- User context
  user_id varchar(100),            -- User ID if authenticated
  user_code varchar(30),           -- User code (format: YYYYMMDDHHMMSS + ms + 6 digits = 23 chars)
  session_id varchar(100),         -- Browser session ID
  page_url text,                   -- Page where error occurred
  user_agent text,                 -- Browser/device info
  
  -- Stack trace and additional info
  stack_trace text,
  context jsonb default '{}',      -- Additional context data
  
  -- Timestamps
  client_timestamp timestamptz,    -- When error occurred on client
  created_at timestamptz default now(),
  
  -- Type constraint
  constraint error_logs_type_check check (error_type in ('API', 'NETWORK', 'JS_ERROR', 'UNHANDLED_REJECTION', 'REACT_ERROR', 'CORS', 'OTHER'))
);
create index if not exists idx_error_logs_created_at on error_logs(created_at desc);
create index if not exists idx_error_logs_user_id on error_logs(user_id);
create index if not exists idx_error_logs_user_code on error_logs(user_code);
create index if not exists idx_error_logs_error_type on error_logs(error_type);
create index if not exists idx_error_logs_status_code on error_logs(status_code);
create index if not exists idx_error_logs_endpoint on error_logs(endpoint);

-- 18. Aggregated stats (precomputed)
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

-- 19. System configs (dynamic parameters)
-- Added v3.2: runtime-adjustable settings (rate limits, analytics, etc.)
create table if not exists system_configs (
  id uuid default gen_random_uuid() primary key,
  config_key text unique not null,
  config_value jsonb not null,
  category text not null default 'general', -- 'rate_limit', 'analytics', 'system'
  description text,
  is_active boolean default true,
  updated_at timestamptz default now(),
  updated_by text -- Last modifying admin ID
);
create index if not exists idx_system_configs_key on system_configs(config_key);
create index if not exists idx_system_configs_category on system_configs(category);

-- 20. Content reports (user-submitted reports for marketplace items)
-- Added v3.3: Allows users to report inappropriate/copyright content
create table if not exists content_reports (
  id uuid default gen_random_uuid() primary key,
  reporter_id text not null references profiles(id),
  listing_id uuid not null references marketplace_listings(id),
  reason text not null, -- User-provided reason for report
  status text default 'pending', -- 'pending' | 'reviewed' | 'resolved' | 'dismissed'
  admin_response text, -- Admin's response to the reporter
  reviewed_by text references profiles(id),
  reviewed_at timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
create index if not exists idx_reports_status on content_reports(status);
create index if not exists idx_reports_listing_id on content_reports(listing_id);
create index if not exists idx_reports_reporter_id on content_reports(reporter_id);
create index if not exists idx_reports_created_at on content_reports(created_at desc);
-- Prevent duplicate active reports from same user for same listing
create unique index if not exists idx_reports_unique_user_listing 
  on content_reports(reporter_id, listing_id) 
  where status in ('pending', 'reviewed');

-- 21. Asset prompt templates (AI image generation presets with 5W1H naming)
-- Added v3.6: Stores user-saved generation presets for quick access
create table if not exists asset_prompt_templates (
  id uuid default gen_random_uuid() primary key,
  user_id text not null,  -- Clerk user IDs are strings, not UUIDs
  
  -- Template info
  name text not null,
  description text,
  
  -- Saved 5W1H parameters (using 5W1H naming convention)
  who_type text,      -- Character type (was character_type)
  who_custom text,    -- Custom character (was character_custom)
  what_type text,     -- Action type (was action_type)
  what_custom text,   -- Custom action (was action_custom)
  where_type text,    -- Setting type (was setting_type)
  where_custom text,  -- Custom setting (was setting_custom)
  style text default 'cartoon',
  moods text[] default '{warm}',
  aspect_ratio text default 'square',
  creativity_level real default 0.3,
  negative_prompt text,  -- Elements to avoid
  
  -- Usage tracking
  use_count int default 0,
  last_used_at timestamptz,
  
  -- Audit fields
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
create index if not exists idx_asset_prompt_templates_user on asset_prompt_templates(user_id);
create index if not exists idx_asset_prompt_templates_usage on asset_prompt_templates(user_id, use_count desc);

-- 22. Page prompt templates (AI Design Page presets)
-- Added v3.7: Stores user-saved page design presets for quick access
create table if not exists page_prompt_templates (
  id uuid default gen_random_uuid() primary key,
  user_id text not null,  -- Clerk user IDs are strings
  
  -- Template info
  name text not null,
  
  -- Page design parameters
  layout text default 'image_top',  -- full_image, full_text, image_top, text_top
  story_theme text,
  main_character text,
  style text default 'cartoon',
  creativity_level real default 0.3,
  negative_prompt text,
  generation_mode text default 'guided',  -- guided or flexible
  
  -- Usage tracking
  use_count integer default 0,
  last_used_at timestamptz,
  
  -- Timestamps
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
create index if not exists idx_page_prompt_templates_user on page_prompt_templates(user_id);
create index if not exists idx_page_prompt_templates_usage on page_prompt_templates(user_id, use_count desc);

-- ==========================================
-- Part 1.5: v3.3 Dashboard Optimized Indexes
-- ==========================================

-- Projects indexes for dashboard queries
CREATE INDEX IF NOT EXISTS idx_projects_user_deleted ON projects(user_id, is_deleted, deleted_at);
CREATE INDEX IF NOT EXISTS idx_projects_user_purchased ON projects(user_id, is_purchased) WHERE is_purchased = true;
CREATE INDEX IF NOT EXISTS idx_projects_user_listing_status ON projects(user_id, listing_status) WHERE listing_status IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_projects_trash ON projects(user_id, is_deleted, is_hidden_from_trash) 
  WHERE is_deleted = true AND is_hidden_from_trash = false;
CREATE INDEX IF NOT EXISTS idx_projects_marketplace_listing ON projects(marketplace_listing_id) WHERE marketplace_listing_id IS NOT NULL;

-- Assets indexes for dashboard queries
CREATE INDEX IF NOT EXISTS idx_assets_user_deleted ON assets(user_id, is_deleted);
CREATE INDEX IF NOT EXISTS idx_assets_user_purchased ON assets(user_id, is_purchased) WHERE is_purchased = true;
CREATE INDEX IF NOT EXISTS idx_assets_user_listing_status ON assets(user_id, listing_status) WHERE listing_status IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_assets_trash ON assets(user_id, is_deleted, is_hidden_from_trash)
  WHERE is_deleted = true AND is_hidden_from_trash = false;
CREATE INDEX IF NOT EXISTS idx_assets_marketplace_listing ON assets(marketplace_listing_id) WHERE marketplace_listing_id IS NOT NULL;

-- Marketplace listings indexes
CREATE INDEX IF NOT EXISTS idx_listings_resource_id ON marketplace_listings(resource_id) WHERE resource_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_marketplace_listings_resource_id ON marketplace_listings(resource_id);
CREATE INDEX IF NOT EXISTS idx_listings_seller_public ON marketplace_listings(seller_id, is_public, is_deleted);
CREATE INDEX IF NOT EXISTS idx_marketplace_listings_version ON marketplace_listings(version);

-- Projects additional indexes
CREATE INDEX IF NOT EXISTS idx_projects_deleted_at ON projects(deleted_at);

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

-- [Listing Usages]
drop policy if exists "Users can insert own usage" on listing_usages;
create policy "Users can insert own usage" on listing_usages for insert
with check ((select auth.jwt() ->> 'sub') = used_by_user_id);

drop policy if exists "Users view own usage or Admin view all" on listing_usages;
create policy "Users view own usage or Admin view all" on listing_usages for select
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

-- [Analytics Events] (v3.4)
-- Allow insert from service_role (backend API)
drop policy if exists "Service role insert analytics events" on analytics_events;
create policy "Service role insert analytics events" on analytics_events for insert
to service_role
with check (true);

-- Only service role can read (for admin analytics)
drop policy if exists "Service role read analytics events" on analytics_events;
create policy "Service role read analytics events" on analytics_events for select
to service_role
using (true);

-- [Error Logs] (v3.5)
-- Allow insert from anyone (errors should be logged even for unauthenticated users)
drop policy if exists "Allow insert error logs" on error_logs;
create policy "Allow insert error logs" on error_logs for insert
with check (true);

-- Service role can read all (for admin panel)
drop policy if exists "Service role read error logs" on error_logs;
create policy "Service role read error logs" on error_logs for select
to service_role
using (true);

-- [Aggregated Stats] (v3.2)
-- Restrict to service_role
drop policy if exists "Service role full access to aggregated_stats" on aggregated_stats;
create policy "Service role full access to aggregated_stats" on aggregated_stats for all
to service_role
using (true)
with check (true);

-- [System Configs] (v3.2)
-- Restrict to service_role
drop policy if exists "Service role full access to system_configs" on system_configs;
create policy "Service role full access to system_configs" on system_configs for all
to service_role
using (true)
with check (true);

-- [Content Reports] (v3.3)
-- Users can view their own reports
drop policy if exists "Users can view own reports" on content_reports;
create policy "Users can view own reports" on content_reports for select
using ((select auth.jwt() ->> 'sub') = reporter_id);

-- Users can create reports
drop policy if exists "Users can create reports" on content_reports;
create policy "Users can create reports" on content_reports for insert
with check ((select auth.jwt() ->> 'sub') = reporter_id);

-- Admin can view all reports
drop policy if exists "Admin can view all reports" on content_reports;
create policy "Admin can view all reports" on content_reports for select
using (is_admin());

-- Admin can update reports
drop policy if exists "Admin can update reports" on content_reports;
create policy "Admin can update reports" on content_reports for update
using (is_admin());

-- [Asset Prompt Templates] (v3.6)
-- Full access for service_role (backend API)
drop policy if exists "Service role full access to asset prompt templates" on asset_prompt_templates;
create policy "Service role full access to asset prompt templates" on asset_prompt_templates for all
to service_role
using (true)
with check (true);

-- [Page Prompt Templates] (v3.7)
-- Full access for service_role (backend API)
drop policy if exists "Service role full access to page prompt templates" on page_prompt_templates;
create policy "Service role full access to page prompt templates" on page_prompt_templates for all
to service_role
using (true)
with check (true);

-- ==========================================
-- Part 3: v3.3 Dashboard Views
-- ==========================================

-- View for user's projects dashboard (All/Bought/Selling combined)
-- This view returns all necessary data for the dashboard in one query
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
  -- Listing details if exists
  ml.id as listing_id,
  ml.title as listing_title,
  ml.price_credits as listing_price,
  ml.is_public as listing_is_public,
  ml.moderation_status as listing_moderation_status,
  ml.sales_count as listing_sales_count,
  ml.unique_buyers_count as listing_unique_buyers,
  ml.total_revenue as listing_total_revenue,
  ml.usage_count as listing_usage_count,
  -- Origin owner info (for purchased projects)
  op.username as origin_owner_username,
  op.avatar_url as origin_owner_avatar
FROM projects p
LEFT JOIN marketplace_listings ml ON p.marketplace_listing_id = ml.id
LEFT JOIN profiles op ON p.origin_owner_id = op.id;

-- View for user's assets dashboard (All/Bought/Selling combined)
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
  -- Listing details if exists
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
  -- Origin owner info (for purchased assets)
  op.username as origin_owner_username,
  op.avatar_url as origin_owner_avatar
FROM assets a
LEFT JOIN marketplace_listings ml ON a.marketplace_listing_id = ml.id
LEFT JOIN profiles op ON a.origin_owner_id = op.id;

-- View for seller stats aggregation
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
-- Part 4: v3.3 Helper Functions & Triggers
-- ==========================================

-- Function to sync listing status to projects/assets
-- Called automatically when a marketplace listing is created/updated
CREATE OR REPLACE FUNCTION sync_listing_status()
RETURNS TRIGGER AS $$
BEGIN
  -- Update project if this is a project listing
  IF NEW.resource_type = 'project' AND NEW.resource_id IS NOT NULL THEN
    UPDATE projects 
    SET 
      listing_status = NEW.moderation_status,
      marketplace_listing_id = NEW.id
    WHERE id = NEW.resource_id::uuid;
  END IF;
  
  -- Update asset if this is an asset listing
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

-- Trigger for listing status sync
DROP TRIGGER IF EXISTS trigger_sync_listing_status ON marketplace_listings;
CREATE TRIGGER trigger_sync_listing_status
  AFTER INSERT OR UPDATE OF moderation_status, is_public, is_deleted
  ON marketplace_listings
  FOR EACH ROW
  EXECUTE FUNCTION sync_listing_status();

-- Function to update seller stats after purchase
CREATE OR REPLACE FUNCTION update_seller_stats_on_purchase()
RETURNS TRIGGER AS $$
DECLARE
  v_listing_price INT;
  v_seller_revenue INT;
BEGIN
  -- Get listing price
  SELECT price_credits INTO v_listing_price
  FROM marketplace_listings
  WHERE id = NEW.listing_id;
  
  -- Calculate seller revenue (90% to seller after 10% platform fee)
  v_seller_revenue := FLOOR(v_listing_price * 0.9);
  
  -- Update listing stats
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

-- Trigger for purchase stats
DROP TRIGGER IF EXISTS trigger_update_seller_stats ON user_purchases;
CREATE TRIGGER trigger_update_seller_stats
  AFTER INSERT ON user_purchases
  FOR EACH ROW
  EXECUTE FUNCTION update_seller_stats_on_purchase();

-- Function to set deleted_at timestamp on soft delete
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

-- Triggers for deleted_at on projects and assets
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

-- v3.4: Append-Only constraint for credit_transactions (financial audit)
-- Prevents UPDATE and DELETE on credit_transactions table
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

-- Function to update content_reports updated_at
CREATE OR REPLACE FUNCTION update_reports_updated_at()
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
    EXECUTE FUNCTION update_reports_updated_at();

-- Function to update asset_prompt_templates updated_at
CREATE OR REPLACE FUNCTION update_asset_prompt_templates_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_asset_prompt_templates_updated_at ON asset_prompt_templates;
CREATE TRIGGER trigger_asset_prompt_templates_updated_at
    BEFORE UPDATE ON asset_prompt_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_asset_prompt_templates_updated_at();

-- Function to update page_prompt_templates updated_at
CREATE OR REPLACE FUNCTION update_page_prompt_templates_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_page_prompt_templates_updated_at ON page_prompt_templates;
CREATE TRIGGER trigger_page_prompt_templates_updated_at
    BEFORE UPDATE ON page_prompt_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_page_prompt_templates_updated_at();

-- ==========================================
-- Part 5: v3.2 Helper Functions (System Config)
-- ==========================================

CREATE OR REPLACE FUNCTION update_system_configs_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_system_configs_timestamp ON system_configs;
CREATE TRIGGER trigger_update_system_configs_timestamp
    BEFORE UPDATE ON system_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_system_configs_timestamp();

-- Helper to fetch rate-limit config
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

-- Aggregated stats helper functions
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

-- ==========================================
-- Part 6: Core Optimized Indexes
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
-- Part 7: Default System Configs (Rate Limits)
-- ==========================================

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

-- ==========================================
-- Migration Scripts (for existing installations)
-- ==========================================

-- v3.3 Migration: Run these to upgrade existing databases

-- 1. Add v3.3 columns to projects
-- ALTER TABLE projects ADD COLUMN IF NOT EXISTS is_hidden_from_trash BOOLEAN DEFAULT false;
-- ALTER TABLE projects ADD COLUMN IF NOT EXISTS is_purchased BOOLEAN DEFAULT false;
-- ALTER TABLE projects ADD COLUMN IF NOT EXISTS origin_owner_id TEXT REFERENCES profiles(id);
-- ALTER TABLE projects ADD COLUMN IF NOT EXISTS listing_status TEXT DEFAULT NULL;
-- ALTER TABLE projects ADD COLUMN IF NOT EXISTS marketplace_listing_id UUID REFERENCES marketplace_listings(id);

-- 2. Add v3.3 columns to assets
-- ALTER TABLE assets ADD COLUMN IF NOT EXISTS is_hidden_from_trash BOOLEAN DEFAULT false;
-- ALTER TABLE assets ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ DEFAULT NULL;
-- ALTER TABLE assets ADD COLUMN IF NOT EXISTS source_listing_id UUID REFERENCES marketplace_listings(id);
-- ALTER TABLE assets ADD COLUMN IF NOT EXISTS is_purchased BOOLEAN DEFAULT false;
-- ALTER TABLE assets ADD COLUMN IF NOT EXISTS origin_owner_id TEXT REFERENCES profiles(id);
-- ALTER TABLE assets ADD COLUMN IF NOT EXISTS listing_status TEXT DEFAULT NULL;
-- ALTER TABLE assets ADD COLUMN IF NOT EXISTS marketplace_listing_id UUID REFERENCES marketplace_listings(id);
-- ALTER TABLE assets ADD COLUMN IF NOT EXISTS description TEXT DEFAULT NULL;

-- 3. Add v3.3 columns to marketplace_listings
-- ALTER TABLE marketplace_listings ADD COLUMN IF NOT EXISTS resource_id UUID;
-- ALTER TABLE marketplace_listings ADD COLUMN IF NOT EXISTS unique_buyers_count INT DEFAULT 0;
-- ALTER TABLE marketplace_listings ADD COLUMN IF NOT EXISTS total_revenue INT DEFAULT 0;
-- ALTER TABLE marketplace_listings ADD COLUMN IF NOT EXISTS version VARCHAR(20) DEFAULT '1.0';
-- ALTER TABLE marketplace_listings ADD COLUMN IF NOT EXISTS changelog TEXT DEFAULT '';
-- ALTER TABLE marketplace_listings ADD COLUMN IF NOT EXISTS version_history JSONB DEFAULT '[]'::jsonb;

-- 4. Create content_reports table (run the CREATE TABLE statement from Part 1 if not exists)

-- 5. Sync existing data
-- UPDATE projects SET is_purchased = true WHERE source_listing_id IS NOT NULL AND is_purchased = false;
-- 
-- UPDATE projects p SET 
--   listing_status = ml.moderation_status,
--   marketplace_listing_id = ml.id
-- FROM marketplace_listings ml
-- WHERE ml.resource_type = 'project' AND ml.resource_id IS NOT NULL 
--   AND ml.resource_id::uuid = p.id AND ml.is_deleted = false AND p.listing_status IS NULL;
-- 
-- UPDATE assets a SET 
--   listing_status = ml.moderation_status,
--   marketplace_listing_id = ml.id
-- FROM marketplace_listings ml
-- WHERE ml.resource_type = 'asset' AND ml.resource_id IS NOT NULL 
--   AND ml.resource_id::uuid = a.id AND ml.is_deleted = false AND a.listing_status IS NULL;
-- 
-- UPDATE marketplace_listings ml SET unique_buyers_count = (
--   SELECT COUNT(DISTINCT user_id) FROM user_purchases up WHERE up.listing_id = ml.id
-- ) WHERE unique_buyers_count = 0 AND sales_count > 0;
-- 
-- UPDATE marketplace_listings ml SET total_revenue = FLOOR(
--   (SELECT COALESCE(SUM(price_paid), 0) FROM user_purchases WHERE listing_id = ml.id) * 0.9
-- ) WHERE total_revenue = 0 AND sales_count > 0;
