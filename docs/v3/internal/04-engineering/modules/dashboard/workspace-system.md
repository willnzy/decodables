# 工作区系统

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [fullstack]
> **对应代码**: `decodables-fe/app/dashboard/_hooks/useWorkspace.ts`

---

## 概述

工作区系统用于隔离个人和团队的项目、素材。支持工作区切换和成员管理。

---

## 数据结构

### 数据库表

```sql
CREATE TABLE workspaces (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('personal', 'team')),
  owner_id UUID NOT NULL REFERENCES users(id),
  avatar_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE workspace_members (
  workspace_id UUID REFERENCES workspaces(id),
  user_id UUID REFERENCES users(id),
  role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'member', 'guest')),
  joined_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (workspace_id, user_id)
);
```

### TypeScript 类型

```typescript
interface Workspace {
  id: string;
  name: string;
  type: 'personal' | 'team';
  avatarUrl?: string;
  role: 'owner' | 'admin' | 'member' | 'guest';
  memberCount: number;
}
```

---

## API 设计

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/workspaces` | 获取用户的工作区列表 |
| POST | `/api/workspaces` | 创建团队工作区 |
| PATCH | `/api/workspaces/{id}` | 更新工作区信息 |
| DELETE | `/api/workspaces/{id}` | 删除工作区 |
| GET | `/api/workspaces/{id}/members` | 获取成员列表 |
| POST | `/api/workspaces/{id}/members` | 邀请成员 |
| PATCH | `/api/workspaces/{id}/members/{userId}` | 更新成员角色 |
| DELETE | `/api/workspaces/{id}/members/{userId}` | 移除成员 |

---

## 前端实现

### useWorkspace Hook

```typescript
const useWorkspace = () => {
  const currentWorkspaceId = useDashboardStore((s) => s.currentWorkspaceId);
  
  const { data: workspaces } = useQuery({
    queryKey: ['workspaces'],
    queryFn: fetchWorkspaces,
  });
  
  const currentWorkspace = workspaces?.find(
    (w) => w.id === currentWorkspaceId
  );
  
  const switchWorkspace = (id: string) => {
    useDashboardStore.setState({ currentWorkspaceId: id });
    // 重新获取项目和素材
    queryClient.invalidateQueries(['projects']);
    queryClient.invalidateQueries(['assets']);
  };
  
  return { workspaces, currentWorkspace, switchWorkspace };
};
```

### useMembers Hook

```typescript
const useMembers = (workspaceId: string) => {
  const { data: members } = useQuery({
    queryKey: ['workspace-members', workspaceId],
    queryFn: () => fetchMembers(workspaceId),
  });
  
  const inviteMember = useMutation({
    mutationFn: ({ email, role }) => 
      api.post(`/api/workspaces/${workspaceId}/members`, { email, role }),
  });
  
  const updateMemberRole = useMutation({
    mutationFn: ({ userId, role }) =>
      api.patch(`/api/workspaces/${workspaceId}/members/${userId}`, { role }),
  });
  
  const removeMember = useMutation({
    mutationFn: (userId: string) =>
      api.delete(`/api/workspaces/${workspaceId}/members/${userId}`),
  });
  
  return { members, inviteMember, updateMemberRole, removeMember };
};
```

---

## 权限控制

### 角色权限矩阵

| 操作 | Owner | Admin | Member | Guest |
|------|-------|-------|--------|-------|
| 查看项目 | ✅ | ✅ | ✅ | ✅ |
| 创建项目 | ✅ | ✅ | ✅ | ❌ |
| 编辑项目 | ✅ | ✅ | ✅ | ❌ |
| 删除项目 | ✅ | ✅ | 自己的 | ❌ |
| 邀请成员 | ✅ | ✅ | ❌ | ❌ |
| 管理成员 | ✅ | ✅ | ❌ | ❌ |
| 删除工作区 | ✅ | ❌ | ❌ | ❌ |

### 权限检查

```typescript
const useWorkspacePermission = () => {
  const { currentWorkspace } = useWorkspace();
  
  const can = (action: string) => {
    const role = currentWorkspace?.role;
    return PERMISSION_MATRIX[action]?.includes(role);
  };
  
  return { can };
};
```

---

## 邀请系统

### 邀请流程

```
创建邀请 → 发送邮件 → 用户点击链接 → 接受/拒绝 → 加入工作区
```

### 邀请表

```sql
CREATE TABLE workspace_invitations (
  id UUID PRIMARY KEY,
  workspace_id UUID REFERENCES workspaces(id),
  email TEXT NOT NULL,
  role TEXT NOT NULL,
  token TEXT UNIQUE NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  accepted_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## t3 限制

- 只有 t3 用户可以创建团队工作区
- 每个团队工作区最多 10 个成员
- 升级提示显示在创建入口

---

## 相关文档

- [架构设计](./architecture.md)
- [工作区页面设计](../../../02-product/pages/user/dashboard/workspace.md)
- [t3 权益](../../../05-business/tier-system.md)
