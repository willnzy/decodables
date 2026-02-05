# 用户 ID 系统

> **同步范围**: [fullstack]
> **状态**: 🟢 已验证
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `v2/03-business/user-id-system.md`, `domains/identity/`

---

## 一、概述

系统使用**双重用户标识符**机制：
- **user_id**: 系统内部使用，UUID 格式
- **user_code**: 管理/客服场景，26 位数字

---

## 二、标识符详情

### 2.1 user_id (系统 ID)

| 属性 | 说明 |
|------|------|
| **格式** | UUID v4 |
| **示例** | `550e8400-e29b-41d4-a716-446655440000` |
| **来源** | 注册时由 `gen_random_uuid()` 生成 |
| **存储** | profiles.id (主键) |

**用途**：
- ✅ 数据库主键/外键
- ✅ API 路径参数
- ✅ 内部业务逻辑
- ✅ JWT Token 载荷

### 2.2 user_code (管理友好 ID)

| 属性 | 说明 |
|------|------|
| **格式** | 26 位纯数字 |
| **示例** | `26010914305278900123456789` |
| **来源** | 注册时生成 |
| **存储** | profiles.user_code |

**用途**：
- ✅ 管理员搜索用户
- ✅ 客服沟通
- ✅ 敏感操作辅助验证
- ✅ 数据分析/统计

---

## 三、user_code 格式

### 3.1 格式结构

```
YYMMDDHHMMSS + SSSSSSSSSS + RRRR
```

| 部分 | 位数 | 说明 | 示例 |
|------|------|------|------|
| 时间戳 | 12 | YYMMDDHHMMSS (UTC) | `260109143052` |
| 序列号 | 10 | PostgreSQL 序列号 | `0000001234` |
| 随机数 | 4 | 0000-9999 | `5678` |

**总长度**: 12 + 10 + 4 = **26 位**

### 3.2 示例解读

```
26010914305200000012345678
│           │         │
│           │         └── 随机数: 5678 (4位)
│           └── 序列号: 0000001234 (第 1234 个序列, 10位)
└── 时间戳: 260109143052 (2026-01-09 14:30:52, 12位)
```

### 3.3 生成逻辑 (PostgreSQL)

```sql
-- 位于: migrations/v2/01_core_business.sql
CREATE OR REPLACE FUNCTION generate_user_code()
RETURNS TEXT AS $$
DECLARE
    new_user_code TEXT;
    current_timestamp_str TEXT;
    sequence_number BIGINT;
BEGIN
    -- 时间戳 (YYMMDDHHMMSS) - 12 位
    current_timestamp_str := TO_CHAR(NOW(), 'YYMMDDHH24MISS');
    
    -- ✅ 使用序列（原子递增，无并发冲突）- 10 位
    sequence_number := nextval('user_code_seq');
    
    -- 组合成 26 位用户码
    -- 格式: [时间12位][序列10位][随机4位]
    new_user_code := 
        current_timestamp_str ||                           -- 12 位: 时间戳
        LPAD(sequence_number::TEXT, 10, '0') ||           -- 10 位: 序列号
        LPAD(FLOOR(RANDOM() * 10000)::TEXT, 4, '0');      --  4 位: 随机数
    
    RETURN new_user_code;
END;
$$ LANGUAGE plpgsql;
```

> 📌 **设计说明**: 使用 PostgreSQL 序列 (`user_code_seq`) 替代用户总数计数，避免并发冲突

---

## 四、使用规范

### 4.1 场景对照表

| 场景 | user_id | user_code |
|------|:------:|:---------:|
| 数据库主键/外键 | ✅ | ❌ |
| API 路径参数 | ✅ | ❌ |
| JWT Token | ✅ | ❌ |
| 业务逻辑判断 | ✅ | ❌ |
| 管理员搜索用户 | ✅ | ✅ |
| 敏感操作验证 | ✅ (主) | ✅ (辅) |
| 用户反馈问题 | ❌ | ✅ |
| 数据分析/统计 | ❌ | ✅ |
| 客服沟通 | ❌ | ✅ |

### 4.2 代码示例

```python
# ✅ 正确: API 使用 user_id
@router.get("/users/{user_id}/profile")
async def get_profile(user_id: UUID):
    pass

# ✅ 正确: 管理员搜索支持 user_code
@router.get("/admin/users/search")
async def search_users(q: str):
    # q 可以是 user_id 或 user_code
    if len(q) == 26 and q.isdigit():
        # 按 user_code 搜索
        return await find_by_user_code(q)
    else:
        # 按 user_id 或 email 搜索
        return await find_by_user_id_or_email(q)

# ✅ 正确: 敏感操作双重验证
async def cancel_subscription(
    user_id: UUID,           # 主验证
    user_code: str = None    # 辅助验证
):
    user = await get_user(user_id)
    if user_code and user.user_code != user_code:
        raise ValidationError("User code mismatch")
```

### 4.3 前端展示

```tsx
// 用户设置页面显示 user_code 供用户查看
function UserSettings({ user }) {
  return (
    <div>
      <label>您的用户编号 (User Code)</label>
      <p className="font-mono">{user.user_code}</p>
      <small>联系客服时请提供此编号</small>
    </div>
  );
}
```

---

## 五、数据库约束

### 5.1 profiles 表字段

```sql
CREATE TABLE profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_code TEXT UNIQUE NOT NULL,
    -- ...
);

-- 唯一索引
CREATE UNIQUE INDEX idx_profiles_user_code ON profiles(user_code);
```

### 5.2 约束说明

| 字段 | 约束 |
|------|------|
| id (user_id) | PRIMARY KEY, UUID |
| user_code | UNIQUE, NOT NULL |

---

## 六、关键原则

1. **user_id** 用于**系统内部**所有场景
2. **user_code** 用于**管理/客服/用户反馈**场景
3. **两者不可混用** - 不要用 user_code 做数据库关联
4. **敏感操作** 可以用 user_code 作为**辅助验证**

---

## 七、相关文档

- [Tier 系统](./tier-system/overview.md)
- [用户认证](./auth/overview.md)
- [API 参考 - 用户](../03-api/users.md)

---

**END OF DOCUMENT**
