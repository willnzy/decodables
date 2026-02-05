# 文件夹系统

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [fullstack]
> **对应代码**: `decodables-fe/app/dashboard/_hooks/useFolders.ts`

---

## 概述

文件夹系统用于组织项目，支持创建、重命名、移动、删除等操作。

---

## 数据结构

### 数据库表

```sql
CREATE TABLE folders (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id),
  workspace_id UUID REFERENCES workspaces(id),
  name TEXT NOT NULL,
  color TEXT,  -- 可选颜色标识
  parent_id UUID REFERENCES folders(id),  -- 支持嵌套
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 项目与文件夹关联
ALTER TABLE projects ADD COLUMN folder_id UUID REFERENCES folders(id);
```

### TypeScript 类型

```typescript
interface Folder {
  id: string;
  name: string;
  color?: string;
  parentId?: string;
  projectCount: number;
  createdAt: Date;
}
```

---

## API 设计

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/folders` | 获取文件夹列表 |
| POST | `/api/folders` | 创建文件夹 |
| PATCH | `/api/folders/{id}` | 更新文件夹 |
| DELETE | `/api/folders/{id}` | 删除文件夹 |
| POST | `/api/projects/{id}/move` | 移动项目到文件夹 |

---

## 前端实现

### useFolders Hook

```typescript
const useFolders = () => {
  const { data: folders, isLoading } = useQuery({
    queryKey: ['folders'],
    queryFn: fetchFolders,
  });
  
  const createFolder = useMutation({
    mutationFn: (name: string) => api.post('/api/folders', { name }),
    onSuccess: () => queryClient.invalidateQueries(['folders']),
  });
  
  const renameFolder = useMutation({
    mutationFn: ({ id, name }) => api.patch(`/api/folders/${id}`, { name }),
  });
  
  const deleteFolder = useMutation({
    mutationFn: (id: string) => api.delete(`/api/folders/${id}`),
  });
  
  return { folders, isLoading, createFolder, renameFolder, deleteFolder };
};
```

### useMoveToFolder Hook

```typescript
const useMoveToFolder = () => {
  return useMutation({
    mutationFn: ({ projectId, folderId }) => 
      api.post(`/api/projects/${projectId}/move`, { folderId }),
    onSuccess: () => {
      queryClient.invalidateQueries(['projects']);
      queryClient.invalidateQueries(['folders']);
    },
  });
};
```

---

## 拖放实现

### DnD Kit 配置

```typescript
import { DndContext, closestCenter } from '@dnd-kit/core';

const ProjectsGrid = () => {
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    
    if (over?.data.current?.type === 'folder') {
      moveToFolder.mutate({
        projectId: active.id,
        folderId: over.id,
      });
    }
  };
  
  return (
    <DndContext onDragEnd={handleDragEnd} collisionDetection={closestCenter}>
      {/* 项目卡片 */}
    </DndContext>
  );
};
```

---

## 删除策略

### 删除空文件夹

直接删除，无需确认。

### 删除非空文件夹

```
┌─────────────────────────────────────┐
│ 删除文件夹                          │
├─────────────────────────────────────┤
│ "工作项目" 包含 5 个项目。          │
│                                     │
│ ○ 将项目移到根目录后删除            │
│ ○ 一并删除所有项目 (移到垃圾箱)    │
│                                     │
│        [取消]  [确认删除]           │
└─────────────────────────────────────┘
```

---

## 相关文档

- [架构设计](./architecture.md)
- [项目管理页面](../../../02-product/pages/user/dashboard/projects.md)
