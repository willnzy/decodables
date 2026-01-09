-- ============================================================================
-- Critical Fixes Patch for refactored_schema_v2.sql
-- ============================================================================
-- This file contains SQL statements to manually apply remaining critical fixes
-- Apply these fixes to the database after running the main migration
-- ============================================================================

-- Fix #4: Add missing foreign keys for projects
-- ----------------------------------------------------------------------------
ALTER TABLE projects
    ADD CONSTRAINT fk_projects_marketplace_listing
    FOREIGN KEY (marketplace_listing_id)
    REFERENCES marketplace_listings(id)
    ON DELETE SET NULL;

ALTER TABLE projects
    ADD CONSTRAINT fk_projects_source_listing
    FOREIGN KEY (source_listing_id)
    REFERENCES marketplace_listings(id)
    ON DELETE SET NULL;

-- Fix #5: Fix asset_categories circular cascade (change to SET NULL)
-- ----------------------------------------------------------------------------
ALTER TABLE asset_categories
    DROP CONSTRAINT IF EXISTS asset_categories_parent_id_fkey,
    ADD CONSTRAINT asset_categories_parent_id_fkey
    FOREIGN KEY (parent_id)
    REFERENCES asset_categories(id)
    ON DELETE SET NULL;  -- Changed from CASCADE to SET NULL

-- Fix #6: Fix user_price_overrides.user_id type inconsistency
-- ----------------------------------------------------------------------------
ALTER TABLE user_price_overrides
    ALTER COLUMN user_id TYPE TEXT;

-- Fix #7: Add composite index on credit_transactions for performance
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_credit_tx_user_type_time
    ON credit_transactions(user_id, transaction_type, created_at DESC);

-- Fix #8: Add missing index on projects.origin_owner_id
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_projects_origin_owner
    ON projects(origin_owner_id)
    WHERE origin_owner_id IS NOT NULL;

-- Fix #9: Add date validation constraints
-- ----------------------------------------------------------------------------
-- Trial period dates
ALTER TABLE profiles
    ADD CONSTRAINT check_trial_dates
    CHECK (trial_end_at IS NULL OR trial_start_at IS NULL OR trial_end_at > trial_start_at);

-- Subscription dates
ALTER TABLE profiles
    ADD CONSTRAINT check_subscription_dates
    CHECK (subscription_end_at IS NULL OR subscription_start_at IS NULL OR subscription_end_at > subscription_start_at);

-- User discount valid dates
ALTER TABLE user_discounts
    ADD CONSTRAINT check_discount_dates
    CHECK (valid_until IS NULL OR valid_from IS NULL OR valid_until > valid_from);

-- Fix #10: Add credit balance upper bound
-- ----------------------------------------------------------------------------
ALTER TABLE profiles
    DROP CONSTRAINT IF EXISTS profiles_credits_monthly_check,
    ADD CONSTRAINT profiles_credits_monthly_check
    CHECK (credits_monthly >= 0 AND credits_monthly <= 1000000);

ALTER TABLE profiles
    DROP CONSTRAINT IF EXISTS profiles_credits_permanent_check,
    ADD CONSTRAINT profiles_credits_permanent_check
    CHECK (credits_permanent >= 0 AND credits_permanent <= 10000000);

-- Fix #11: Add Stripe ID format validation
-- ----------------------------------------------------------------------------
ALTER TABLE profiles
    ADD CONSTRAINT check_stripe_customer_id_format
    CHECK (stripe_customer_id IS NULL OR stripe_customer_id ~ '^cus_[A-Za-z0-9]+$');

ALTER TABLE profiles
    ADD CONSTRAINT check_stripe_subscription_id_format
    CHECK (stripe_subscription_id IS NULL OR stripe_subscription_id ~ '^sub_[A-Za-z0-9]+$');

ALTER TABLE pricing_plans
    ADD CONSTRAINT check_stripe_price_id_prod_format
    CHECK (stripe_price_id_prod IS NULL OR stripe_price_id_prod ~ '^price_[A-Za-z0-9]+$');

ALTER TABLE pricing_plans
    ADD CONSTRAINT check_stripe_price_id_test_format
    CHECK (stripe_price_id_test IS NULL OR stripe_price_id_test ~ '^price_[A-Za-z0-9]+$');

-- Fix #12: Remove duplicate index on profiles.email
-- ----------------------------------------------------------------------------
-- Email UNIQUE constraint already creates an index
DROP INDEX IF EXISTS idx_profiles_email;

-- Fix #13: Add idempotency key format validation
-- ----------------------------------------------------------------------------
ALTER TABLE credit_transactions
    ADD CONSTRAINT check_idempotency_key_format
    CHECK (idempotency_key IS NULL OR length(idempotency_key) >= 16);

ALTER TABLE marketplace_purchases
    ADD CONSTRAINT check_purchase_idempotency_format
    CHECK (idempotency_key IS NULL OR length(idempotency_key) >= 16);

ALTER TABLE credit_purchases
    ADD CONSTRAINT check_credit_purchase_idempotency_format
    CHECK (idempotency_key IS NULL OR length(idempotency_key) >= 16);

-- Fix #14: Add GIN indexes on JSONB audit fields
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_pricing_history_old_data_gin
    ON pricing_history USING GIN(old_data);

CREATE INDEX IF NOT EXISTS idx_pricing_history_new_data_gin
    ON pricing_history USING GIN(new_data);

-- ============================================================================
-- Verification Queries
-- ============================================================================
-- Run these to verify fixes were applied correctly

-- Check foreign keys
SELECT
    conname AS constraint_name,
    conrelid::regclass AS table_name,
    confrelid::regclass AS referenced_table
FROM pg_constraint
WHERE conname IN (
    'fk_projects_marketplace_listing',
    'fk_projects_source_listing',
    'asset_categories_parent_id_fkey'
);

-- Check indexes
SELECT
    schemaname,
    tablename,
    indexname
FROM pg_indexes
WHERE indexname IN (
    'idx_credit_tx_user_type_time',
    'idx_projects_origin_owner',
    'idx_pricing_history_old_data_gin',
    'idx_pricing_history_new_data_gin'
);

-- Check constraints
SELECT
    conname AS constraint_name,
    conrelid::regclass AS table_name,
    pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conname LIKE 'check_%'
AND conrelid::regclass::text IN ('profiles', 'pricing_plans', 'user_discounts', 'credit_transactions')
ORDER BY conrelid, conname;

-- ============================================================================
-- END OF PATCH
-- ============================================================================
