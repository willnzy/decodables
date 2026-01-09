-- ============================================================================
-- Rollback Script for refactored_schema_v2.sql
-- ============================================================================
-- This script completely reverses the v2 migration
-- Use with EXTREME caution - this will destroy all data
-- ============================================================================

-- WARNING: This is a destructive operation!
-- Backup your database before running this script!

BEGIN;

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE '⚠️  ROLLBACK WARNING';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'This script will DROP ALL tables created in v2 migration';
    RAISE NOTICE 'All data will be permanently lost';
    RAISE NOTICE '';
    RAISE NOTICE 'Press Ctrl+C NOW to cancel';
    RAISE NOTICE 'Waiting 5 seconds...';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE '';

    -- Wait 5 seconds (PostgreSQL doesn't have sleep, but this forces user to review)
    PERFORM pg_sleep(5);
END $$;

-- ============================================================================
-- Step 1: Drop Row-Level Security Policies
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE 'Step 1: Dropping RLS policies...';
END $$;

-- Drop profiles policies
DROP POLICY IF EXISTS profiles_select_own ON profiles;
DROP POLICY IF EXISTS profiles_update_own ON profiles;

-- Drop projects policies
DROP POLICY IF EXISTS projects_select_own ON projects;
DROP POLICY IF EXISTS projects_insert_own ON projects;
DROP POLICY IF EXISTS projects_update_own ON projects;
DROP POLICY IF EXISTS projects_delete_own ON projects;

-- Drop credit_transactions policies
DROP POLICY IF EXISTS credit_tx_select_own ON credit_transactions;

-- Drop user_generations policies
DROP POLICY IF EXISTS generations_select_own ON user_generations;
DROP POLICY IF EXISTS generations_insert_own ON user_generations;

-- Drop marketplace_listings policies
DROP POLICY IF EXISTS listings_select_public ON marketplace_listings;
DROP POLICY IF EXISTS listings_select_own ON marketplace_listings;
DROP POLICY IF EXISTS listings_insert_own ON marketplace_listings;
DROP POLICY IF EXISTS listings_update_own ON marketplace_listings;
DROP POLICY IF EXISTS listings_delete_own ON marketplace_listings;

-- Drop marketplace_purchases policies
DROP POLICY IF EXISTS purchases_select_own ON marketplace_purchases;

-- Disable RLS
ALTER TABLE IF EXISTS profiles DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS projects DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS credit_transactions DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS user_generations DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS marketplace_listings DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS marketplace_purchases DISABLE ROW LEVEL SECURITY;

-- ============================================================================
-- Step 2: Drop Views
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE 'Step 2: Dropping views...';
END $$;

DROP VIEW IF EXISTS v_ai_usage_last_30_days CASCADE;

-- ============================================================================
-- Step 3: Drop Functions
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE 'Step 3: Dropping functions...';
END $$;

DROP FUNCTION IF EXISTS deduct_credits_atomic(TEXT, INT, TEXT, TEXT, TEXT, TEXT, TEXT) CASCADE;
DROP FUNCTION IF EXISTS add_credits_atomic(TEXT, INT, TEXT, TEXT, TEXT, TEXT) CASCADE;
DROP FUNCTION IF EXISTS execute_marketplace_purchase(TEXT, UUID, TEXT) CASCADE;
DROP FUNCTION IF EXISTS increment_campaign_usage(UUID) CASCADE;
DROP FUNCTION IF EXISTS upsert_ai_usage_daily(TEXT, TEXT, TEXT, DECIMAL, INT) CASCADE;
DROP FUNCTION IF EXISTS log_pricing_plan_change() CASCADE;
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;
DROP FUNCTION IF EXISTS set_deleted_at_on_soft_delete() CASCADE;
DROP FUNCTION IF EXISTS prevent_modification() CASCADE;

-- ============================================================================
-- Step 4: Drop Tables (in reverse dependency order)
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE 'Step 4: Dropping tables...';
END $$;

-- Drop tables in reverse order to handle foreign key dependencies
DROP TABLE IF EXISTS ai_usage_daily CASCADE;
DROP TABLE IF EXISTS api_logs CASCADE;
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS user_notifications CASCADE;
DROP TABLE IF EXISTS support_tickets CASCADE;
DROP TABLE IF EXISTS admin_actions CASCADE;
DROP TABLE IF EXISTS analytics_reports CASCADE;
DROP TABLE IF EXISTS experiments CASCADE;
DROP TABLE IF EXISTS feature_flags CASCADE;
DROP TABLE IF EXISTS campaigns CASCADE;
DROP TABLE IF EXISTS credit_purchases CASCADE;
DROP TABLE IF EXISTS subscription_history CASCADE;
DROP TABLE IF EXISTS pricing_history CASCADE;
DROP TABLE IF EXISTS user_price_overrides CASCADE;
DROP TABLE IF EXISTS pricing_plans CASCADE;
DROP TABLE IF EXISTS user_discounts CASCADE;
DROP TABLE IF EXISTS holidays CASCADE;
DROP TABLE IF EXISTS themes CASCADE;
DROP TABLE IF EXISTS assets CASCADE;
DROP TABLE IF EXISTS system_assets CASCADE;
DROP TABLE IF EXISTS asset_categories CASCADE;
DROP TABLE IF EXISTS user_generations CASCADE;
DROP TABLE IF EXISTS feedback CASCADE;
DROP TABLE IF EXISTS marketplace_reviews CASCADE;
DROP TABLE IF EXISTS marketplace_purchases CASCADE;
DROP TABLE IF EXISTS marketplace_listings CASCADE;
DROP TABLE IF EXISTS user_favorites CASCADE;
DROP TABLE IF EXISTS projects CASCADE;
DROP TABLE IF EXISTS credit_transactions CASCADE;
DROP TABLE IF EXISTS system_configs CASCADE;
DROP TABLE IF EXISTS profiles CASCADE;

-- ============================================================================
-- Step 5: Drop Extensions
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE 'Step 5: Dropping extensions...';
END $$;

DROP EXTENSION IF EXISTS ltree CASCADE;
DROP EXTENSION IF EXISTS pg_trgm CASCADE;
DROP EXTENSION IF EXISTS "uuid-ossp" CASCADE;

-- ============================================================================
-- Completion
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE '✅ Rollback completed successfully';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'All v2 tables, functions, and views have been dropped';
    RAISE NOTICE 'Database has been rolled back to pre-migration state';
    RAISE NOTICE '';
    RAISE NOTICE '⚠️  Remember to restore from backup if you need the data back';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE '';
END $$;

COMMIT;

-- End of rollback script
