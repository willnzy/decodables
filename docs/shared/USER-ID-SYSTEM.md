# 用户 ID 系统说明

## 概述

Make Decodables 系统使用**双重用户标识符**机制,分别服务于不同的使用场景。

---

## 两种用户标识符

### 1. user_id (系统内部 ID)

**用途**: 系统和数据库内部使用的唯一标识符

**特征**:
- **格式**: Clerk 生成的 UUID 格式 (例如: `user_2abc3def4ghi5jkl`)
- **来源**: Clerk 认证系统自动生成
- **唯一性**: 全局唯一,永久不变
- **可读性**: 机器友好,人类不友好

**使用场景**:
- 数据库表的主键和外键关联
- API 调用的路径参数 (如 `/users/{user_id}`)
- 系统内部的业务逻辑处理
- Stripe/Supabase 等第三方服务集成

**示例**:
```python
# 获取用户资料
user = await users_repo.get_profile(user_id="user_2abc3def4ghi5jkl")

# 数据库查询
supabase.table("projects").select("*").eq("user_id", user_id).execute()
```

---

### 2. user_code (管理友好 ID)

**用途**: 方便管理员快速识别和管理用户的人类友好标识符

**特征**:
- **格式**: 6-8位大写字母+数字组合 (例如: `ABC123`, `XYZ789AB`)
- **来源**: 用户注册时系统自动生成
- **唯一性**: 全局唯一,随机生成
- **可读性**: 人类友好,易于记忆和传达

**生成逻辑** (当前实现):
```python
# infrastructure/repositories/user_repository.py:289-304
def generate_user_code(self) -> str:
    """Generate unique 6-char user code."""
    import random
    import string
    chars = string.ascii_uppercase + string.digits
    for _ in range(10):
        code = ''.join(random.choices(chars, k=6))
        # 检查唯一性
        existing = self.client.table("profiles").select("id").eq("user_code", code).execute()
        if not existing.data:
            return code
    return ''.join(random.choices(chars, k=8))  # Fallback to 8-char
```

**使用场景**:
- 用户向客服/管理员反馈问题时提供
- 管理员快速搜索和识别用户
- 管理后台的用户搜索 (支持 user_code 搜索)
- 用户验证 (双因素验证,如退款/取消订阅)

**示例**:
```python
# 管理员搜索用户 (支持 email/username/user_code)
users = await user_repo.search_users(query="ABC123")

# 敏感操作双因素验证
stored_user_code = user.get("user_code")
if stored_user_code != req.user_code:
    raise HTTPException(403, "User code does not match. Please verify the user code.")
```

---

## 设计意图 vs 当前实现

### ❌ 当前问题

当前的 `user_code` 生成逻辑是**随机字符串**,不包含任何时间信息:
```python
code = ''.join(random.choices(chars, k=6))  # 例如: "ABC123"
```

### ✅ 预期设计

根据您的说明,`user_code` 应该包含**注册日期时间信息**,便于管理员快速了解用户注册时间:

**建议格式** (人类友好):
- `{YYMMDD}{HHMM}{RND}` - 例如: `260109143X7Y` (2026-01-09 14:30 注册)
  - `260109` - 年月日 (2026年1月9日)
  - `1430` - 小时分钟 (14:30)
  - `X7Y` - 3位随机字符 (保证唯一性)

**优点**:
- 管理员看到 `260109143X7Y` 立即知道是 2026年1月9日 14:30 左右注册的用户
- 仍然保持全局唯一性
- 长度仍为 10-11 字符,合理范围

### 🔧 需要修复

1. **更新 `generate_user_code()` 逻辑**:
```python
from datetime import datetime, timezone

def generate_user_code(self) -> str:
    """
    Generate unique user code with registration timestamp.

    Format: {YYMMDD}{HHMM}{RND}
    Example: 260109143X7Y (registered on 2026-01-09 14:30)

    Returns:
        Unique user code (10-11 chars)
    """
    import random
    import string

    now = datetime.now(timezone.utc)
    # YYMMDD (6 chars)
    date_part = now.strftime("%y%m%d")
    # HHMM (4 chars)
    time_part = now.strftime("%H%M")
    # Random 3 chars for uniqueness
    chars = string.ascii_uppercase + string.digits

    for _ in range(10):
        random_part = ''.join(random.choices(chars, k=3))
        code = f"{date_part}{time_part}{random_part}"
        # Check uniqueness
        existing = self.client.table("profiles").select("id").eq("user_code", code).execute()
        if not existing.data:
            return code
    # Fallback: add one more random char
    random_part = ''.join(random.choices(chars, k=4))
    return f"{date_part}{time_part}{random_part}"
```

2. **更新数据库字段长度**:
```sql
-- profiles.user_code 应该支持 10-11 字符
ALTER TABLE profiles ALTER COLUMN user_code TYPE VARCHAR(15);
```

3. **更新所有相关文档和注释**

---

## 使用规范

### ✅ 正确使用

| 场景 | 使用 user_id | 使用 user_code |
|------|--------------|----------------|
| 数据库主键/外键 | ✅ | ❌ |
| API 路径参数 | ✅ | ❌ |
| 第三方服务集成 (Stripe) | ✅ | ❌ |
| 管理员搜索用户 | ✅ (也支持) | ✅ (主要) |
| 敏感操作双因素验证 | ✅ (主验证) | ✅ (辅助验证) |
| 用户反馈问题时提供 | ❌ | ✅ |
| 系统日志记录 | ✅ | ✅ (可选) |

### ❌ 错误使用

```python
# ❌ 错误: 使用 user_code 作为数据库主键
supabase.table("projects").select("*").eq("user_code", "ABC123")

# ✅ 正确: 使用 user_id
supabase.table("projects").select("*").eq("user_id", "user_2abc3def")

# ❌ 错误: API 路径使用 user_code
GET /api/users/{user_code}/projects

# ✅ 正确: API 路径使用 user_id
GET /api/users/{user_id}/projects
```

---

## 代码示例

### 用户注册时创建两个 ID

```python
# infrastructure/repositories/user_repository.py:create_profile()
async def create_profile(self, user_id: str, email: str, ...):
    """
    Create user profile with dual identifiers.

    Args:
        user_id: Clerk-generated user ID (machine-friendly)
        email: User email
        ...

    Returns:
        Created profile with both user_id and user_code
    """
    # 生成人类友好的 user_code
    user_code = self.generate_user_code()

    data = {
        "id": user_id,  # 系统内部 ID (Clerk UUID)
        "email": email,
        "user_code": user_code,  # 管理友好 ID (包含注册时间)
        "tier": "free",
        "credits_monthly": 0,
        "credits_permanent": 50,
        # ...
    }

    result = self.client.table("profiles").insert(data).execute()
    return result.data[0] if result.data else None
```

### 管理员搜索用户 (支持两种 ID)

```python
# infrastructure/repositories/user_repository.py:search_users()
async def search_users(self, query: str) -> list:
    """
    Search users by email, username, or user_code.

    Args:
        query: Search term (email/username/user_code)

    Returns:
        List of matching users
    """
    result = self.client.table("profiles").select(
        "id, email, username, user_code, tier"
    ).or_(
        f"email.ilike.%{query}%,username.ilike.%{query}%,user_code.ilike.%{query}%"
    ).execute()
    return result.data or []
```

### 敏感操作双因素验证

```python
# api/admin/subscriptions.py:adm_refund()
async def adm_refund(request: Request, req: AdminRefundRequest, admin: dict = Depends(require_admin)):
    """Admin refund with user_code verification."""

    # 获取用户资料 (使用 user_id)
    user = await users_repo.get_profile(req.user_id)
    if not user:
        raise HTTPException(404, "User not found")

    # 双因素验证: 确保 user_code 匹配 (防止误操作)
    stored_user_code = user.get("user_code")
    if not stored_user_code:
        raise HTTPException(400, "User has no user code assigned")
    if stored_user_code != req.user_code:
        raise HTTPException(403, "User code does not match. Please verify the user code.")

    # 继续退款操作...
```

---

## 数据库设计

### profiles 表

```sql
CREATE TABLE profiles (
    -- 系统内部 ID (主键)
    id TEXT PRIMARY KEY,  -- Clerk user ID (e.g., "user_2abc3def")

    -- 管理友好 ID (唯一索引)
    user_code VARCHAR(15) UNIQUE NOT NULL,  -- e.g., "260109143X7Y"

    -- 其他字段...
    email TEXT UNIQUE NOT NULL,
    username TEXT UNIQUE,
    tier TEXT NOT NULL DEFAULT 'free',

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引优化
CREATE INDEX idx_profiles_user_code ON profiles(user_code);
CREATE INDEX idx_profiles_email ON profiles(email);
```

---

## 前端显示

### 管理后台

```tsx
// 用户列表显示
<Table>
  <TableRow>
    <TableCell>{user.email}</TableCell>
    <TableCell>
      <Badge>{user.user_code}</Badge>  {/* 显示 user_code */}
    </TableCell>
    <TableCell>{user.tier}</TableCell>
    <TableCell>
      <Link to={`/admin/users/${user.id}`}>  {/* 路由使用 user_id */}
        View Details
      </Link>
    </TableCell>
  </TableRow>
</Table>

// 用户详情页
<UserProfile userId={params.id}>  {/* 路由参数是 user_id */}
  <InfoCard>
    <Label>User Code</Label>
    <Code>{user.user_code}</Code>  {/* 显示给管理员 */}
  </InfoCard>
</UserProfile>
```

### 用户前台

```tsx
// 用户设置页面 - 显示 user_code 用于客服沟通
<SettingsCard title="Account Info">
  <InfoRow>
    <Label>Your User Code</Label>
    <Code>{user.user_code}</Code>
    <Tooltip>
      Provide this code when contacting support for faster assistance.
    </Tooltip>
  </InfoRow>
</SettingsCard>
```

---

## 文档更新清单

### 后端文档
- [x] `docs/shared/USER-ID-SYSTEM.md` (本文档)
- [ ] `docs/后台业务逻辑说明.md` - 添加用户 ID 系统说明
- [ ] `infrastructure/repositories/user_repository.py` - 更新注释
- [ ] `api/admin/users.py` - 更新注释

### 前端文档
- [ ] `decodables-fe/docs/shared/USER-ID-SYSTEM.md` (复制本文档)
- [ ] `decodables-fe/docs/前端完整开发规范.md` - 添加用户 ID 系统说明

### 代码注释
- [ ] 所有使用 user_id 的地方添加注释: `# 系统内部 ID`
- [ ] 所有使用 user_code 的地方添加注释: `# 管理友好 ID (包含注册时间)`

---

## 迁移计划

### Phase 1: 更新现有用户的 user_code (可选)

如果需要将现有随机 user_code 迁移为包含注册时间的格式:

```python
# scripts/migrations/update_user_codes_with_timestamp.py
"""
Migrate existing random user_codes to timestamp-based format.

Before: ABC123 (random)
After: 260109143X7Y (with registration timestamp)
"""

from datetime import datetime
import random
import string

def migrate_user_code(user):
    """Generate new user_code based on registration timestamp."""
    created_at = datetime.fromisoformat(user['created_at'].replace('Z', '+00:00'))

    # YYMMDD + HHMM
    date_part = created_at.strftime("%y%m%d")
    time_part = created_at.strftime("%H%M")

    # Random 3 chars
    chars = string.ascii_uppercase + string.digits
    random_part = ''.join(random.choices(chars, k=3))

    return f"{date_part}{time_part}{random_part}"

# Run migration...
```

### Phase 2: 更新 generate_user_code() 函数

更新为包含时间戳的生成逻辑 (见上文"需要修复"部分)

### Phase 3: 更新文档和注释

确保所有文档和代码注释正确描述双重 ID 系统

---

## 总结

| 特征 | user_id | user_code |
|------|---------|-----------|
| **格式** | `user_2abc3def4ghi5jkl` | `260109143X7Y` |
| **来源** | Clerk 自动生成 | 系统注册时生成 |
| **可读性** | 机器友好 | 人类友好 |
| **包含信息** | 无语义 | 注册日期+时间 |
| **主要用途** | 系统内部/数据库 | 管理员/客服 |
| **典型场景** | API 调用,数据关联 | 用户反馈,管理员搜索 |
| **安全性** | 低敏感度 | 低敏感度 (双因素验证) |

**关键原则**:
- ✅ **user_id** 用于系统内部逻辑和数据关联
- ✅ **user_code** 用于人类交互和管理场景
- ✅ 两者互补,各司其职,不可混用

---

最后更新: 2026-01-09
维护人: 后端团队
状态: 待实施 (user_code 时间戳格式)
