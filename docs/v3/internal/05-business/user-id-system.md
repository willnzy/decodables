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
YYMMDD + HHMMSS + mmmm + UUUUUUU + RRR
```

| 部分 | 位数 | 说明 | 示例 |
|------|------|------|------|
| 日期 | 6 | YYMMDD (UTC) | `260109` |
| 时间 | 6 | HHMMSS (UTC) | `143052` |
| 毫秒 | 4 | 0000-9999 | `7890` |
| 用户序号 | 7 | 全局注册序号 | `0123456` |
| 随机数 | 3 | 000-999 | `789` |

### 3.2 示例解读

```
26010914305278900123456789
│    │     │   │      │
│    │     │   │      └── 随机数: 789
│    │     │   └── 用户序号: 0123456 (第 123,456 个用户)
│    │     └── 毫秒: 7890
│    └── 时间: 143052 (14:30:52)
└── 日期: 260109 (2026年1月9日)
```

### 3.3 生成逻辑

```python
def generate_user_code() -> str:
    """
    生成 26 位 user_code
    
    1. 取 UTC 当前时间 (精确到 0.1ms)
    2. 拼接日期/时间/毫秒
    3. 读取当前用户总数 + 1，补零 7 位
    4. 生成 3 位随机数
    5. 组合为 26 位 user_code
    6. 若冲突则重试
    """
    now = datetime.utcnow()
    
    # 日期部分
    date_part = now.strftime("%y%m%d")  # 260109
    time_part = now.strftime("%H%M%S")  # 143052
    ms_part = f"{int(now.microsecond / 100):04d}"  # 7890
    
    # 用户序号
    user_count = get_total_user_count() + 1
    seq_part = f"{user_count:07d}"  # 0123456
    
    # 随机数
    rand_part = f"{random.randint(0, 999):03d}"  # 789
    
    return date_part + time_part + ms_part + seq_part + rand_part
```

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
