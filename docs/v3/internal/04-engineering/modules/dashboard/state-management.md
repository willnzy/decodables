# Dashboard 状态管理

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [frontend]
> **对应代码**: `decodables-fe/app/dashboard/_stores/`

---

## 概述

Dashboard 的状态管理，使用 Zustand 管理 UI 状态，React Query 管理服务端数据。

---

## Store 结构

### dashboardStore

```typescript
interface DashboardStore {
  // 视图状态
  view: 'grid' | 'list';
  sortBy: 'recent' | 'name' | 'created';
  sortOrder: 'asc' | 'desc';
  
  // 选择状态
  selectedIds: string[];
  isSelectionMode: boolean;
  
  // 侧边栏
  sidebarCollapsed: boolean;
  activeSection: 'projects' | 'assets' | 'starred' | 'trash';
  
  // 工作区
  currentWorkspaceId: string | null;
  
  // Actions
  setView: (view: 'grid' | 'list') => void;
  setSortBy: (sortBy: string) => void;
  toggleSelection: (id: string) => void;
  clearSelection: () => void;
  setCurrentWorkspace: (id: string) => void;
}
```

---

## React Query 数据

### 项目列表

```typescript
const useProjects = (options: ProjectQueryOptions) => {
  return useQuery({
    queryKey: ['projects', options],
    queryFn: () => fetchProjects(options),
    staleTime: 5 * 60 * 1000, // 5 分钟
  });
};
```

### 素材列表

```typescript
const useAssets = (options: AssetQueryOptions) => {
  return useQuery({
    queryKey: ['assets', options],
    queryFn: () => fetchAssets(options),
  });
};
```

### 文件夹

```typescript
const useFolders = () => {
  return useQuery({
    queryKey: ['folders'],
    queryFn: fetchFolders,
  });
};
```

---

## Mutations

### 创建项目

```typescript
const useCreateProject = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: createProject,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
};
```

### 删除项目

```typescript
const useDeleteProject = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: deleteProject,
    onMutate: async (projectId) => {
      // 乐观更新
      await queryClient.cancelQueries({ queryKey: ['projects'] });
      const previous = queryClient.getQueryData(['projects']);
      queryClient.setQueryData(['projects'], (old) =>
        old.filter((p) => p.id !== projectId)
      );
      return { previous };
    },
    onError: (err, variables, context) => {
      // 回滚
      queryClient.setQueryData(['projects'], context.previous);
    },
  });
};
```

---

## 状态持久化

```typescript
// 视图偏好持久化到 localStorage
const dashboardStore = create(
  persist(
    (set) => ({
      view: 'grid',
      sortBy: 'recent',
      // ...
    }),
    {
      name: 'dashboard-preferences',
      partialize: (state) => ({
        view: state.view,
        sortBy: state.sortBy,
        sidebarCollapsed: state.sidebarCollapsed,
      }),
    }
  )
);
```

---

## 相关文档

- [架构设计](./architecture.md)
- [状态管理规范](../../development/state-management.md)
