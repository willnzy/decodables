-- ============================================================================
-- Enable Row-Level Security (RLS) for Supabase
-- ============================================================================
-- This script enables RLS on tables that have policies defined
-- Only run this if you're using Supabase and need multi-tenant security
-- ============================================================================

-- WARNING: Enabling RLS will restrict data access based on policies
-- Make sure your application sets app.current_user_id before queries

BEGIN;

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE '⚠️  ENABLING ROW-LEVEL SECURITY';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'This will enable RLS on 6 tables';
    RAISE NOTICE 'Your application MUST set app.current_user_id for queries to work';
    RAISE NOTICE '';
    RAISE NOTICE 'Example: SET app.current_user_id = ''user_xxx'';';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE '';
END $$;

-- Enable RLS on user-owned tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_generations ENABLE ROW LEVEL SECURITY;
ALTER TABLE marketplace_listings ENABLE ROW LEVEL SECURITY;
ALTER TABLE marketplace_purchases ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '✅ RLS enabled on 6 tables:';
    RAISE NOTICE '   - profiles';
    RAISE NOTICE '   - projects';
    RAISE NOTICE '   - credit_transactions';
    RAISE NOTICE '   - user_generations';
    RAISE NOTICE '   - marketplace_listings';
    RAISE NOTICE '   - marketplace_purchases';
    RAISE NOTICE '';
    RAISE NOTICE '⚠️  IMPORTANT: Your application must now set the user context:';
    RAISE NOTICE '   SET app.current_user_id = ''<user_id>'' before each query';
    RAISE NOTICE '';
    RAISE NOTICE '📚 Policies already defined in main migration (refactored_schema_v2.sql)';
    RAISE NOTICE '';
    RAISE NOTICE '🔄 To disable RLS, run: disable_rls.sql';
    RAISE NOTICE '';
END $$;

COMMIT;

-- End of RLS enablement script
