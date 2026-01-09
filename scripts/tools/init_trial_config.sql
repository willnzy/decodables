-- ============================================================================
-- Trial Period Configuration Initialization
-- ============================================================================
--
-- Purpose: Initialize trial period configuration in system_configs table
-- Usage: Run this SQL script directly in Supabase SQL editor or via psql
--
-- Note: This is a one-time initialization script for trial period configuration.
--       The configuration value can be modified later via Admin API.
-- ============================================================================

INSERT INTO system_configs (key, value, value_type, config_group, description, is_active, is_editable)
VALUES
    ('trial.duration_days', '30', 'integer', 'trial', 'Free tier 试用期天数 (可通过 Admin API 修改)', TRUE, TRUE)
ON CONFLICT (key) DO NOTHING;

-- Verification
SELECT
    key,
    value,
    value_type,
    config_group,
    description,
    is_active,
    is_editable,
    created_at
FROM system_configs
WHERE key = 'trial.duration_days';
