# 组件结构规范

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [frontend]
> **来源**: v1 2-Rules/coding/COMPONENT-STRUCTURE

---

## 概述

React 组件的结构和组织规范。

---

## 文件结构

### 单文件组件

```
components/
└── Button.tsx        # 简单组件
```

### 复杂组件 (多文件)

```
components/
└── UserProfile/
    ├── index.tsx           # 主组件 (导出入口)
    ├── UserProfile.tsx     # 实现
    ├── UserAvatar.tsx      # 子组件
    ├── useUserProfile.ts   # Hook
    ├── types.ts            # 类型定义
    └── constants.ts        # 常量
```

---

## 组件代码结构

```typescript
// 1. 导入
import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import type { ComponentProps } from './types';

// 2. 类型定义 (如果不在 types.ts)
interface Props { ... }

// 3. 常量
const DEFAULT_SIZE = 'md';

// 4. 组件
export function Component({ prop1, prop2 }: Props) {
  // 4.1 Hooks
  const [state, setState] = useState();
  const { data } = useQuery();
  
  // 4.2 派生状态
  const derivedValue = useMemo(() => ..., [dep]);
  
  // 4.3 副作用
  useEffect(() => { ... }, []);
  
  // 4.4 事件处理
  const handleClick = () => { ... };
  
  // 4.5 条件渲染逻辑
  if (loading) return <Skeleton />;
  if (error) return <Error />;
  
  // 4.6 主渲染
  return (
    <div>
      ...
    </div>
  );
}

// 5. 子组件 (如果简单且仅此处使用)
function SubComponent() { ... }
```

---

## 命名规则

| 类型 | 命名 | 示例 |
|------|------|------|
| 组件 | PascalCase | `UserProfile` |
| Hook | use 前缀 | `useUserProfile` |
| 工具函数 | camelCase | `formatDate` |
| 常量 | UPPER_SNAKE | `MAX_ITEMS` |
| 类型 | PascalCase | `UserProfileProps` |

---

## 相关文档

- [TypeScript 规范](./typescript-standards.md)
- [Hooks 模式](./hooks-patterns.md)
