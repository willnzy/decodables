# TypeScript 编码规范

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [frontend]
> **来源**: v1 2-Rules/coding/TYPESCRIPT-STANDARDS

---

## 概述

前端 TypeScript 编码规范。

---

## 类型定义

### 优先使用 interface

```typescript
// ✅ 对象结构用 interface
interface User {
  id: string;
  name: string;
}

// ✅ 联合类型用 type
type Status = 'pending' | 'active' | 'inactive';

// ✅ 工具类型用 type
type UserWithEmail = User & { email: string };
```

### 避免 any

```typescript
// ❌ 避免
function process(data: any) {}

// ✅ 使用具体类型
function process(data: unknown) {}
function process<T>(data: T) {}
```

---

## 组件类型

### Props 定义

```typescript
// 使用 interface
interface ButtonProps {
  variant?: 'primary' | 'secondary';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  onClick?: () => void;
  children: React.ReactNode;
}

export function Button({ 
  variant = 'primary',
  size = 'md',
  ...props 
}: ButtonProps) {}
```

### Event 类型

```typescript
// 使用 React 内置类型
function handleChange(e: React.ChangeEvent<HTMLInputElement>) {}
function handleSubmit(e: React.FormEvent<HTMLFormElement>) {}
```

---

## 严格模式

```json
// tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true
  }
}
```

---

## 导入导出

```typescript
// ✅ 命名导出
export function useAuth() {}
export interface AuthState {}

// ✅ 默认导出仅用于页面组件
export default function HomePage() {}

// ✅ 类型导入
import type { User } from '@/types';
```

---

## 相关文档

- [命名规范](./naming-conventions.md)
- [组件结构规范](./component-structure.md)
