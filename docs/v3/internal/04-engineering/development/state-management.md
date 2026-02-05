# 状态管理规范

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [frontend]
> **来源**: v1 2-Rules/coding/STATE-MANAGEMENT

---

## 概述

前端状态管理规范，使用 Zustand。

---

## 状态分类

| 类型 | 存储位置 | 示例 |
|------|----------|------|
| 服务端状态 | React Query | 用户数据、列表 |
| 全局 UI 状态 | Zustand | 主题、侧边栏开关 |
| 本地 UI 状态 | useState | 表单输入、模态框 |
| URL 状态 | URL params | 筛选、分页 |

---

## Zustand Store 结构

### 拆分式 Store

```typescript
// stores/auth-store.ts
export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  
  setUser: (user) => set({ user, isAuthenticated: !!user }),
  logout: () => set({ user: null, isAuthenticated: false }),
}));

// stores/ui-store.ts
export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  theme: 'light',
  
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setTheme: (theme) => set({ theme }),
}));
```

### 使用选择器

```typescript
// ✅ 只订阅需要的状态
const user = useAuthStore((state) => state.user);
const setUser = useAuthStore((state) => state.setUser);

// ❌ 避免订阅整个 store
const store = useAuthStore();
```

---

## React Query 使用

```typescript
// 查询
const { data: user } = useQuery({
  queryKey: ['user', userId],
  queryFn: () => getUser(userId),
});

// 变更
const { mutate } = useMutation({
  mutationFn: updateUser,
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['user'] });
  },
});
```

---

## 状态持久化

```typescript
// 使用 persist 中间件
export const useSettingsStore = create(
  persist<SettingsState>(
    (set) => ({
      language: 'en',
      setLanguage: (language) => set({ language }),
    }),
    { name: 'settings' }
  )
);
```

---

## 相关文档

- [Hooks 模式](./hooks-patterns.md)
- [前端架构](../architecture/frontend.md)
