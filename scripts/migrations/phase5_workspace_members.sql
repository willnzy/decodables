-- ============================================================================
-- 增量迁移: Phase 5 - Workspace Members & Invitations
-- ============================================================================
-- 执行方式: 在 Supabase SQL Editor 中运行
-- 前置条件: workspaces 表和 profiles 表已存在
-- 日期: 2026-01-29
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. workspace_members (成员关系)
-- ============================================================================
CREATE TABLE IF NOT EXISTS workspace_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 关联
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    -- 角色 (owner / member)
    role TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('owner', 'member')),

    -- 邀请来源
    invited_by TEXT REFERENCES profiles(id) ON DELETE SET NULL,

    -- 状态
    is_active BOOLEAN DEFAULT TRUE,

    -- 标准审计字段
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- 唯一约束: 同一用户不能在同一 workspace 中有多个成员记录
    UNIQUE(workspace_id, user_id)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_workspace_members_workspace ON workspace_members(workspace_id) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_workspace_members_user ON workspace_members(user_id) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_workspace_members_role ON workspace_members(workspace_id, role) WHERE is_active = TRUE;

-- 触发器: 更新 updated_at
DROP TRIGGER IF EXISTS update_workspace_members_updated_at ON workspace_members;
CREATE TRIGGER update_workspace_members_updated_at
    BEFORE UPDATE ON workspace_members
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ============================================================================
-- 2. workspace_invitations (邀请)
-- ============================================================================
CREATE TABLE IF NOT EXISTS workspace_invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 关联
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,

    -- 邀请信息
    invited_email TEXT NOT NULL,
    invited_by TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    -- 角色 (被邀请者将获得的角色)
    role TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('member')),

    -- 状态: pending / accepted / declined / expired
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'declined', 'expired')),

    -- 过期时间 (7 天)
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '7 days'),

    -- 接受者 (接受邀请后填入)
    accepted_by TEXT REFERENCES profiles(id) ON DELETE SET NULL,
    accepted_at TIMESTAMPTZ,

    -- 标准审计字段
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_workspace_invitations_workspace ON workspace_invitations(workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_workspace_invitations_email ON workspace_invitations(invited_email, status);
CREATE INDEX IF NOT EXISTS idx_workspace_invitations_expires ON workspace_invitations(expires_at) WHERE status = 'pending';

-- 触发器: 更新 updated_at
DROP TRIGGER IF EXISTS update_workspace_invitations_updated_at ON workspace_invitations;
CREATE TRIGGER update_workspace_invitations_updated_at
    BEFORE UPDATE ON workspace_invitations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ============================================================================
-- 3. 启用 RLS (Row Level Security)
-- ============================================================================
ALTER TABLE workspace_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_invitations ENABLE ROW LEVEL SECURITY;


COMMIT;

-- ============================================================================
-- 验证
-- ============================================================================
-- 执行完后运行以下查询验证:
-- SELECT table_name FROM information_schema.tables WHERE table_name IN ('workspace_members', 'workspace_invitations');
-- SELECT tablename, rowsecurity FROM pg_tables WHERE tablename IN ('workspace_members', 'workspace_invitations');
