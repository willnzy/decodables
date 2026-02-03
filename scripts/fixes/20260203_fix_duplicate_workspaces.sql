-- ============================================================================
-- Fix: 清理重复的 default workspace + 部署唯一约束 + RPC 函数
-- Date: 2026-02-03
-- Issue: 并发 API 请求导致同一用户创建多个 default workspace
-- Root Cause:
--   1. get_or_create_default() 是 check-then-create 非原子操作
--   2. .single() 查询在有多行时抛出 PGRST116 (与 0 行同一错误码)
--   3. 代码将 PGRST116 误判为"不存在"，触发再次创建 → 恶性循环
-- ============================================================================

-- Step 0: 查看当前重复情况 (先执行此查询了解规模)
-- SELECT owner_id, COUNT(*) as cnt
-- FROM workspaces
-- WHERE is_default = TRUE AND is_active = TRUE
-- GROUP BY owner_id
-- HAVING COUNT(*) > 1
-- ORDER BY cnt DESC;

BEGIN;

-- Step 1: 确定每个用户保留的 workspace (最早创建的那个)
-- 使用 CTE 标记要保留的 workspace
WITH keeper AS (
    SELECT DISTINCT ON (owner_id) id AS keep_id, owner_id
    FROM workspaces
    WHERE is_default = TRUE AND is_active = TRUE
    ORDER BY owner_id, created_at ASC
),
duplicates AS (
    SELECT w.id AS dup_id, w.owner_id, k.keep_id
    FROM workspaces w
    JOIN keeper k ON k.owner_id = w.owner_id
    WHERE w.is_default = TRUE
      AND w.is_active = TRUE
      AND w.id != k.keep_id
)

-- Step 2: 迁移 CASCADE 关联数据到保留的 workspace
-- 2a: folders (ON DELETE CASCADE - 必须先迁移，否则删除 workspace 时会丢失)
UPDATE folders
SET workspace_id = d.keep_id
FROM duplicates d
WHERE folders.workspace_id = d.dup_id;

-- Step 2b: tags (ON DELETE CASCADE)
WITH keeper AS (
    SELECT DISTINCT ON (owner_id) id AS keep_id, owner_id
    FROM workspaces
    WHERE is_default = TRUE AND is_active = TRUE
    ORDER BY owner_id, created_at ASC
),
duplicates AS (
    SELECT w.id AS dup_id, w.owner_id, k.keep_id
    FROM workspaces w
    JOIN keeper k ON k.owner_id = w.owner_id
    WHERE w.is_default = TRUE
      AND w.is_active = TRUE
      AND w.id != k.keep_id
)
UPDATE tags
SET workspace_id = d.keep_id
FROM duplicates d
WHERE tags.workspace_id = d.dup_id;

-- Step 2c: workspace_members (ON DELETE CASCADE)
WITH keeper AS (
    SELECT DISTINCT ON (owner_id) id AS keep_id, owner_id
    FROM workspaces
    WHERE is_default = TRUE AND is_active = TRUE
    ORDER BY owner_id, created_at ASC
),
duplicates AS (
    SELECT w.id AS dup_id, w.owner_id, k.keep_id
    FROM workspaces w
    JOIN keeper k ON k.owner_id = w.owner_id
    WHERE w.is_default = TRUE
      AND w.is_active = TRUE
      AND w.id != k.keep_id
)
UPDATE workspace_members
SET workspace_id = d.keep_id
FROM duplicates d
WHERE workspace_members.workspace_id = d.dup_id;

-- Step 2d: workspace_invitations (ON DELETE CASCADE)
WITH keeper AS (
    SELECT DISTINCT ON (owner_id) id AS keep_id, owner_id
    FROM workspaces
    WHERE is_default = TRUE AND is_active = TRUE
    ORDER BY owner_id, created_at ASC
),
duplicates AS (
    SELECT w.id AS dup_id, w.owner_id, k.keep_id
    FROM workspaces w
    JOIN keeper k ON k.owner_id = w.owner_id
    WHERE w.is_default = TRUE
      AND w.is_active = TRUE
      AND w.id != k.keep_id
)
UPDATE workspace_invitations
SET workspace_id = d.keep_id
FROM duplicates d
WHERE workspace_invitations.workspace_id = d.dup_id;

-- Step 2e: projects (ON DELETE SET NULL - 迁移而不是让它变 NULL)
WITH keeper AS (
    SELECT DISTINCT ON (owner_id) id AS keep_id, owner_id
    FROM workspaces
    WHERE is_default = TRUE AND is_active = TRUE
    ORDER BY owner_id, created_at ASC
),
duplicates AS (
    SELECT w.id AS dup_id, w.owner_id, k.keep_id
    FROM workspaces w
    JOIN keeper k ON k.owner_id = w.owner_id
    WHERE w.is_default = TRUE
      AND w.is_active = TRUE
      AND w.id != k.keep_id
)
UPDATE projects
SET workspace_id = d.keep_id
FROM duplicates d
WHERE projects.workspace_id = d.dup_id;

-- Step 2f: assets (ON DELETE SET NULL - 迁移而不是让它变 NULL)
WITH keeper AS (
    SELECT DISTINCT ON (owner_id) id AS keep_id, owner_id
    FROM workspaces
    WHERE is_default = TRUE AND is_active = TRUE
    ORDER BY owner_id, created_at ASC
),
duplicates AS (
    SELECT w.id AS dup_id, w.owner_id, k.keep_id
    FROM workspaces w
    JOIN keeper k ON k.owner_id = w.owner_id
    WHERE w.is_default = TRUE
      AND w.is_active = TRUE
      AND w.id != k.keep_id
)
UPDATE assets
SET workspace_id = d.keep_id
FROM duplicates d
WHERE assets.workspace_id = d.dup_id;

-- Step 3: 删除重复的 workspace (关联数据已全部迁移)
WITH keeper AS (
    SELECT DISTINCT ON (owner_id) id AS keep_id, owner_id
    FROM workspaces
    WHERE is_default = TRUE AND is_active = TRUE
    ORDER BY owner_id, created_at ASC
)
DELETE FROM workspaces w
USING keeper k
WHERE w.owner_id = k.owner_id
  AND w.is_default = TRUE
  AND w.is_active = TRUE
  AND w.id != k.keep_id;

-- Step 4: 创建唯一约束 (此时数据已清理，不会冲突)
CREATE UNIQUE INDEX IF NOT EXISTS idx_workspaces_one_default_per_owner
ON workspaces(owner_id) WHERE is_default = TRUE AND is_active = TRUE;

-- Step 5: 创建 RPC 函数
CREATE OR REPLACE FUNCTION get_or_create_default_workspace(p_owner_id UUID)
RETURNS JSON
LANGUAGE plpgsql
AS $$
DECLARE
    v_workspace RECORD;
BEGIN
    -- Step 1: 尝试获取已有的 default workspace
    SELECT * INTO v_workspace
    FROM workspaces
    WHERE owner_id = p_owner_id
      AND is_default = TRUE
      AND is_active = TRUE
    LIMIT 1;

    -- Step 2: 如果找到，直接返回
    IF FOUND THEN
        RETURN json_build_object(
            'id', v_workspace.id,
            'name', v_workspace.name,
            'description', v_workspace.description,
            'owner_id', v_workspace.owner_id,
            'is_default', v_workspace.is_default,
            'is_personal', v_workspace.is_personal,
            'is_active', v_workspace.is_active,
            'created_at', v_workspace.created_at,
            'updated_at', v_workspace.updated_at
        );
    END IF;

    -- Step 3: 不存在，尝试插入（唯一索引保证并发安全）
    INSERT INTO workspaces (name, owner_id, is_default, is_personal, is_active)
    VALUES ('My Workspace', p_owner_id, TRUE, TRUE, TRUE)
    ON CONFLICT (owner_id) WHERE is_default = TRUE AND is_active = TRUE
    DO NOTHING;

    -- Step 4: 无论是自己插入的还是并发插入的，都能查到
    SELECT * INTO v_workspace
    FROM workspaces
    WHERE owner_id = p_owner_id
      AND is_default = TRUE
      AND is_active = TRUE
    LIMIT 1;

    RETURN json_build_object(
        'id', v_workspace.id,
        'name', v_workspace.name,
        'description', v_workspace.description,
        'owner_id', v_workspace.owner_id,
        'is_default', v_workspace.is_default,
        'is_personal', v_workspace.is_personal,
        'is_active', v_workspace.is_active,
        'created_at', v_workspace.created_at,
        'updated_at', v_workspace.updated_at
    );
END;
$$
SET search_path = 'public';

-- Step 6: 修复 cleanup_old_error_logs (移除了往 activity_logs 插入 user_id='system' 的语句)
CREATE OR REPLACE FUNCTION cleanup_old_error_logs(p_retention_days INTEGER DEFAULT 30)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_deleted_count INTEGER;
BEGIN
    DELETE FROM error_logs
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '1 day' * p_retention_days;

    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;

    RETURN v_deleted_count;
END;
$$
SET search_path = 'public';

COMMIT;

-- Step 7: 验证 (手动执行)
-- SELECT owner_id, COUNT(*) as cnt
-- FROM workspaces
-- WHERE is_default = TRUE AND is_active = TRUE
-- GROUP BY owner_id
-- HAVING COUNT(*) > 1;
-- 期望结果: 0 行 (没有重复)
