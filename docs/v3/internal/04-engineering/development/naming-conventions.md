# 命名规范

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [fullstack]
> **来源**: v1 main/naming-conventions.md, 2-Rules/coding/NAMING-CONVENTION

---

## 概述

前后端代码命名规范。

---

## 通用规则

| 类型 | 风格 | 示例 |
|------|------|------|
| 变量 | camelCase | `userName`, `isActive` |
| 常量 | UPPER_SNAKE | `MAX_RETRY`, `API_URL` |
| 函数 | camelCase | `getUserById`, `handleClick` |
| 类/组件 | PascalCase | `UserService`, `ButtonGroup` |
| 文件 (组件) | PascalCase | `UserProfile.tsx` |
| 文件 (工具) | kebab-case | `date-utils.ts` |
| 目录 | kebab-case | `user-profile/` |

---

## 后端 (Python)

```python
# 类名: PascalCase
class UserService:
    pass

# 函数/方法: snake_case
def get_user_by_id(user_id: str):
    pass

# 变量: snake_case
user_name = "John"

# 常量: UPPER_SNAKE
MAX_RETRY_COUNT = 3

# 私有: 前缀 _
def _internal_method():
    pass
```

---

## 前端 (TypeScript/React)

```typescript
// 组件: PascalCase
export function UserProfile() {}

// Hook: use 前缀
export function useUserProfile() {}

// 工具函数: camelCase
export function formatDate() {}

// 类型/接口: PascalCase
interface UserProfile {}
type ButtonVariant = 'primary' | 'secondary';

// 常量: UPPER_SNAKE
const API_BASE_URL = '';
```

---

## 数据库

```sql
-- 表名: snake_case 复数
users, credit_transactions

-- 列名: snake_case
user_id, created_at

-- 索引: idx_表名_列名
idx_users_email

-- 函数: snake_case
get_user_credits()
```

---

## 相关文档

- [术语表](../../01-project/glossary.md)
- [TypeScript 规范](./typescript-standards.md)
