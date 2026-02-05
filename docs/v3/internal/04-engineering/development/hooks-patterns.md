# Hooks 使用模式

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [frontend]
> **来源**: v1 2-Rules/coding/HOOKS-PATTERNS

---

## 概述

React Hooks 的使用模式和最佳实践。

---

## 自定义 Hook 规范

### 命名

```typescript
// ✅ 以 use 开头
function useUserProfile() {}
function useLocalStorage() {}
function useDebounce() {}
```

### 返回值

```typescript
// 单一值
function useIsMobile(): boolean {}

// 对象 (多值)
function useUser(): { user: User | null; loading: boolean; error: Error | null } {}

// 数组 (类似 useState)
function useToggle(): [boolean, () => void] {}
```

---

## 常用 Hooks 模式

### 数据获取

```typescript
function useUser(userId: string) {
  const { data, error, isLoading, refetch } = useQuery({
    queryKey: ['user', userId],
    queryFn: () => api.getUser(userId),
  });
  
  return { user: data, error, isLoading, refetch };
}
```

### 表单状态

```typescript
function useForm<T>(initialValues: T) {
  const [values, setValues] = useState(initialValues);
  
  const handleChange = (name: keyof T, value: any) => {
    setValues(prev => ({ ...prev, [name]: value }));
  };
  
  const reset = () => setValues(initialValues);
  
  return { values, handleChange, reset };
}
```

### 防抖

```typescript
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);
  
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  
  return debouncedValue;
}
```

---

## 规则

1. **只在顶层调用** - 不在循环、条件、嵌套函数中调用
2. **依赖数组完整** - useEffect/useMemo/useCallback 依赖完整
3. **避免过度优化** - 不要滥用 useMemo/useCallback

---

## 相关文档

- [状态管理](./state-management.md)
- [组件结构](./component-structure.md)
