-- ============================================================================
-- Backfill workspace_id for existing projects and assets (v3.45)
-- ============================================================================
--
-- Problem: Existing projects and assets have workspace_id = NULL because they
-- were created before workspace data isolation was implemented.
-- The new workspace filtering (.eq("workspace_id", ...)) excludes them.
--
-- Solution: Set workspace_id to the user's default workspace for all rows
-- where workspace_id IS NULL.
--
-- Safe to run multiple times (idempotent).
-- ============================================================================

BEGIN;

-- 1. Backfill projects: set workspace_id from user's default workspace
UPDATE projects p
SET workspace_id = w.id
FROM workspaces w
WHERE p.workspace_id IS NULL
  AND w.owner_id = p.user_id
  AND w.is_default = true;

-- 2. Backfill assets: set workspace_id from user's default workspace
UPDATE assets a
SET workspace_id = w.id
FROM workspaces w
WHERE a.workspace_id IS NULL
  AND w.owner_id = a.user_id
  AND w.is_default = true;

COMMIT;

-- ============================================================================
-- Verification queries (run after migration)
-- ============================================================================
-- Check remaining NULL workspace_id:
-- SELECT COUNT(*) FROM projects WHERE workspace_id IS NULL;
-- SELECT COUNT(*) FROM assets WHERE workspace_id IS NULL;
--
-- Expected: 0 rows for both (all backfilled)
