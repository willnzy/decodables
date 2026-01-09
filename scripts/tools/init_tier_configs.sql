-- ==============================================================================
-- Tier Configuration Initialization Script
-- ==============================================================================
-- Purpose: Insert tier display name configurations into system_configs table
-- Version: 1.0.0
-- Date: 2026-01-09
--
-- This script initializes the configurable tier display names that admins
-- can modify through the Admin API.
--
-- System Codes (永不改变):
--   - t1: First Tier
--   - t2: Second Tier
--   - t3: Third Tier
--
-- Display Names (可配置):
--   - t1: "Free Plan" (default)
--   - t2: "Starter Plan" (default)
--   - t3: "Pro Plan" (default)
--
-- Usage:
--   psql $DATABASE_URL -f scripts/tools/init_tier_configs.sql
--
-- Note: Uses ON CONFLICT DO NOTHING to make script idempotent
-- ==============================================================================

BEGIN;

-- Insert tier display name configurations
INSERT INTO system_configs (key, value, value_type, config_group, description, is_active, is_editable)
VALUES
    -- Tier Display Names (可配置)
    ('tier.t1.display_name', 'Free Plan', 'text', 'tier', 'First Tier 显示名称 (可通过 Admin API 修改)', TRUE, TRUE),
    ('tier.t2.display_name', 'Starter Plan', 'text', 'tier', 'Second Tier 显示名称 (可通过 Admin API 修改)', TRUE, TRUE),
    ('tier.t3.display_name', 'Pro Plan', 'text', 'tier', 'Third Tier 显示名称 (可通过 Admin API 修改)', TRUE, TRUE),

    -- Tier Monthly Credits (参考值，实际使用代码中的常量)
    ('tier.t1.monthly_credits', '0', 'integer', 'tier', 'First Tier 月度积分', TRUE, FALSE),
    ('tier.t2.monthly_credits', '200', 'integer', 'tier', 'Second Tier 月度积分', TRUE, FALSE),
    ('tier.t3.monthly_credits', '500', 'integer', 'tier', 'Third Tier 月度积分', TRUE, FALSE)

ON CONFLICT (key) DO NOTHING;

-- Verify inserted data
SELECT
    key,
    value,
    value_type,
    config_group,
    is_active,
    is_editable,
    description
FROM system_configs
WHERE config_group = 'tier'
ORDER BY key;

COMMIT;

-- ==============================================================================
-- Expected Output:
-- ==============================================================================
--
--              key              |    value     | value_type | config_group | is_active | is_editable |           description
-- ------------------------------+--------------+------------+--------------+-----------+-------------+----------------------------------
--  tier.t1.display_name         | Free Plan    | text       | tier         | t         | t           | First Tier 显示名称 (可通过 Admin API 修改)
--  tier.t1.monthly_credits      | 0            | integer    | tier         | t         | f           | First Tier 月度积分
--  tier.t2.display_name         | Starter Plan | text       | tier         | t         | t           | Second Tier 显示名称 (可通过 Admin API 修改)
--  tier.t2.monthly_credits      | 200          | integer    | tier         | t         | f           | Second Tier 月度积分
--  tier.t3.display_name         | Pro Plan     | text       | tier         | t         | t           | Third Tier 显示名称 (可通过 Admin API 修改)
--  tier.t3.monthly_credits      | 500          | integer    | tier         | t         | f           | Third Tier 月度积分
-- (6 rows)
--
-- ==============================================================================
