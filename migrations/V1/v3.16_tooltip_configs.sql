-- ============================================
-- Migration: v3.16_tooltip_configs.sql
-- Description: Add tooltip text configurations
-- Date: 2026-01-03
-- ============================================

-- Add tooltip text configurations for ProjectCard delete button
INSERT INTO system_configs (key, value, value_type, config_group, description) VALUES
  -- ==========================================
  -- Tooltip Text (Round 7)
  -- ==========================================
  ('TOOLTIP_DELETE', 'Delete', 'text', 'tooltip', 'Delete button tooltip when enabled'),
  ('TOOLTIP_DELETE_DISABLED', 'Unpublish first to delete', 'text', 'tooltip', 'Delete button tooltip when project is published (disabled state)')
ON CONFLICT (key) DO UPDATE SET
  value = EXCLUDED.value,
  value_type = EXCLUDED.value_type,
  config_group = EXCLUDED.config_group,
  description = EXCLUDED.description,
  updated_at = NOW();

-- Verify the inserts
DO $$
BEGIN
  RAISE NOTICE 'Tooltip configs added successfully';
  RAISE NOTICE 'Total tooltip configs: %', (SELECT COUNT(*) FROM system_configs WHERE config_group = 'tooltip');
END $$;
