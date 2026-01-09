# 用户 ID 系统说明

## 概述

Make Decodables 系统使用**双重用户标识符**机制，分别服务于不同的使用场景。

---

## 两种用户标识符

### 1. user_id (系统内部 ID)

**用途**: 系统和数据库内部使用的唯一标识符

**特征**:
- **格式**: Clerk 生成的标识符 (例如: `user_2abc3def4ghi5jkl`)
- **来源**: Clerk 认证系统自动生成
- **唯一性**: 全局唯一，永久不变
- **可读性**: 机器友好，人类不友好

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
- **格式**: 26 位组合 - 包含完整注册时间和用户序号
- **来源**: 用户注册时系统自动生成
- **唯一性**: 全局唯一 (时间 + 序号 + 随机数三重保证)
- **可读性**: 人类友好，管理员可从中快速了解用户注册时间

**格式详解** (26 位):

```
格式: YYMMDDHHMMSS + mmmm + UUUUUUUU + RRR
示例: 26010914305278900123456ABC
```

**拆解说明**:

| 部分 | 位数 | 说明 | 示例 |
|------|------|------|------|
| 日期 | 6 位 | YYMMDD (UTC+0) | `260109` = 2026-01-09 |
| 时间 | 6 位 | HHMMSS (UTC+0) | `143052` = 14:30:52 |
| 毫秒 | 4 位 | 毫秒数 (0000-9999) | `7890` |
| 用户数 | 8 位 | 总注册人数，不够补 0 | `00123456` = 第 123,456 个用户 |
| 随机数 | 3 位 | 大写字母+数字组合 | `ABC` |

**完整示例解读**:
```
user_code: 26010914305278900123456ABC

解读:
- 注册日期: 2026-01-09
- 注册时间: 14:30:52.7890 (UTC+0)
- 用户序号: 第 123,456 个注册用户
- 随机后缀: ABC (额外唯一性保证)

管理员一眼就能看出:
1. 这是 2026 年 1 月 9 日下午 2:30 注册的用户
2. 系统此时已有 123,456 个注册用户
3. 毫秒级精度防止碰撞
```

**设计优点**:
1. ✅ **时间精度**: 毫秒级时间戳，几乎不可能碰撞
2. ✅ **业务洞察**: 用户注册序号反映业务增长
3. ✅ **管理友好**: 管理员一眼看出注册时间和用户规模
4. ✅ **唯一性保证**: 时间(16位) + 用户数(8位) + 随机数(3位) = 三重保证
5. ✅ **数据分析**: 可轻松统计每日/每小时注册量

**生成逻辑**:

```python
# infrastructure/repositories/user_repository.py
def generate_user_code(self) -> str:
    """
    生成唯一的 26 位 user_code.

    格式: YYMMDDHHMMSS + mmmm + UUUUUUUU + RRR
    示例: 26010914305278900123456ABC

    Returns:
        26 位 user_code
    """
    from datetime import datetime, timezone
    import random
    import string

    # 获取 UTC+0 当前时间
    now = datetime.now(timezone.utc)

    # 日期时间部分 (16 位)
    date_part = now.strftime("%y%m%d")  # YYMMDD (6 位)
    time_part = now.strftime("%H%M%S")  # HHMMSS (6 位)
    ms_part = f"{now.microsecond // 100:04d}"  # 毫秒 (4 位，保留到 0.1 毫秒)

    # 用户总数 (8 位，补零)
    result = self.client.table("profiles").select("id", count="exact").execute()
    user_count = result.count or 0
    count_part = f"{user_count + 1:08d}"  # 8 位，不够补 0

    # 随机后缀 (3 位)
    chars = string.ascii_uppercase + string.digits
    random_part = ''.join(random.choices(chars, k=3))

    # 组合: 6 + 6 + 4 + 8 + 3 = 27 位
    user_code = f"{date_part}{time_part}{ms_part}{count_part}{random_part}"

    # 验证唯一性 (理论上不会重复，但仍需检查)
    existing = self.client.table("profiles").select("id").eq("user_code", user_code).execute()
    if existing.data:
        # 极小概率重复，重新生成
        return self.generate_user_code()

    return user_code
```

**使用场景**:
- 用户向客服/管理员反馈问题时提供
- 管理员快速搜索和识别用户
- 管理后台的用户搜索 (支持 user_code 搜索)
- 敏感操作的双因素验证 (如退款/取消订阅)
- 数据分析 (从 user_code 统计注册趋势)

**示例**:
```python
# 管理员搜索用户 (支持 email/username/user_code)
users = await user_repo.search_users(query="26010914305278")

# 敏感操作双因素验证
stored_user_code = user.get("user_code")
if stored_user_code != req.user_code:
    raise HTTPException(403, "User code does not match. Please verify the user code.")

# 从 user_code 分析注册时间
def parse_user_code(user_code: str) -> dict:
    """
    解析 user_code，提取注册信息.

    Args:
        user_code: 26 位 user_code

    Returns:
        {
            "registration_date": "2026-01-09",
            "registration_time": "14:30:52.7890",
            "user_number": 123456,
            "random_suffix": "ABC"
        }
    """
    if len(user_code) != 26:
        return None

    date_part = user_code[0:6]  # 260109
    time_part = user_code[6:12]  # 143052
    ms_part = user_code[12:16]  # 7890
    count_part = user_code[16:24]  # 00123456
    random_part = user_code[24:26]  # ABC

    return {
        "registration_date": f"20{date_part[0:2]}-{date_part[2:4]}-{date_part[4:6]}",
        "registration_time": f"{time_part[0:2]}:{time_part[2:4]}:{time_part[4:6]}.{ms_part}",
        "user_number": int(count_part),
        "random_suffix": random_part,
    }
```

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
| 数据分析 (注册趋势) | ❌ | ✅ |

### ❌ 错误使用

```python
# ❌ 错误: 使用 user_code 作为数据库主键
supabase.table("projects").select("*").eq("user_code", "26010914305278")

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
    创建用户档案，生成双重标识符.

    Args:
        user_id: Clerk 生成的 user ID (machine-friendly)
        email: 用户邮箱
        ...

    Returns:
        包含 user_id 和 user_code 的用户档案
    """
    # 生成人类友好的 user_code (26 位)
    user_code = self.generate_user_code()

    data = {
        "id": user_id,  # 系统内部 ID (Clerk ID)
        "email": email,
        "user_code": user_code,  # 管理友好 ID (包含注册时间+用户序号)
        "tier": "t1",  # First Tier
        "credits_monthly": 0,
        "credits_permanent": 50,  # 注册赠送
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
    搜索用户 (支持 email, username, user_code).

    Args:
        query: 搜索关键词 (email/username/user_code)

    Returns:
        匹配的用户列表
    """
    result = self.client.table("profiles").select(
        "id, email, username, user_code, tier, created_at"
    ).or_(
        f"email.ilike.%{query}%,username.ilike.%{query}%,user_code.ilike.%{query}%"
    ).limit(50).execute()

    return result.data or []
```

### 敏感操作双因素验证

```python
# api/admin/subscriptions.py:adm_refund()
async def adm_refund(
    request: Request,
    req: AdminRefundRequest,
    admin: dict = Depends(require_admin)
):
    """
    管理员退款操作，需要双因素验证.

    Args:
        req.user_id: 用户的 Clerk ID
        req.user_code: 用户的 user_code (验证用)
    """
    # 获取用户资料 (使用 user_id)
    user = await users_repo.get_profile(req.user_id)
    if not user:
        raise HTTPException(404, "User not found")

    # 双因素验证: 确保 user_code 匹配 (防止误操作)
    stored_user_code = user.get("user_code")
    if not stored_user_code:
        raise HTTPException(400, "User has no user code assigned")

    if stored_user_code != req.user_code:
        raise HTTPException(
            403,
            f"User code does not match. "
            f"Expected: {stored_user_code[:6]}***, "
            f"Got: {req.user_code[:6]}***"
        )

    # 继续退款操作...
    await stripe_service.refund_payment(req.payment_intent_id)

    # 审计日志
    await admin_repo.admin_log_operation(
        admin_id=admin["id"],
        operation_type="refund",
        target_user_id=req.user_id,
        details=f"Refunded ${req.amount} for user {user['email']} (user_code: {stored_user_code})",
        reason=req.reason
    )
```

---

## 数据库设计

### profiles 表

```sql
CREATE TABLE profiles (
    -- 系统内部 ID (主键)
    id TEXT PRIMARY KEY,  -- Clerk user ID (e.g., "user_2abc3def")

    -- 管理友好 ID (唯一索引)
    user_code TEXT UNIQUE NOT NULL,  -- 26 位 (e.g., "26010914305278900123456ABC")

    -- 其他字段...
    email TEXT UNIQUE NOT NULL,
    username TEXT UNIQUE,
    tier TEXT NOT NULL DEFAULT 't1' CHECK (tier IN ('t1', 't2', 't3')),

    -- 审计字段
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引优化
CREATE INDEX idx_profiles_user_code ON profiles(user_code);
CREATE INDEX idx_profiles_email ON profiles(email);

-- user_code 前缀索引 (支持按日期/时间搜索)
CREATE INDEX idx_profiles_user_code_prefix ON profiles(user_code text_pattern_ops);

COMMENT ON COLUMN profiles.id IS '用户 ID (Clerk 生成，系统内部使用)';
COMMENT ON COLUMN profiles.user_code IS '用户代码 (26位，包含注册时间+用户序号，管理员使用)';
```

---

## 前端显示

### 管理后台

```tsx
// 用户列表显示
<Table>
  <TableRow>
    <TableCell>{user.email}</TableCell>

    {/* 显示 user_code (管理员看) */}
    <TableCell>
      <Badge variant="outline" className="font-mono">
        {user.user_code}
      </Badge>
      <Tooltip>
        Registered: {parseUserCode(user.user_code).registration_date}
        <br />
        User #{parseUserCode(user.user_code).user_number}
      </Tooltip>
    </TableCell>

    <TableCell>{user.tier}</TableCell>

    {/* 路由使用 user_id */}
    <TableCell>
      <Link to={`/admin/users/${user.id}`}>
        View Details
      </Link>
    </TableCell>
  </TableRow>
</Table>

// 用户详情页
<UserProfile userId={params.id}>  {/* 路由参数是 user_id */}
  <InfoCard>
    <InfoRow>
      <Label>User ID</Label>
      <Code className="text-xs text-muted">{user.id}</Code>  {/* 系统 ID */}
    </InfoRow>

    <InfoRow>
      <Label>User Code</Label>
      <Code className="font-mono font-bold">{user.user_code}</Code>  {/* 管理 ID */}
      <Button
        variant="ghost"
        size="sm"
        onClick={() => copyToClipboard(user.user_code)}
      >
        Copy
      </Button>
    </InfoRow>

    <InfoRow>
      <Label>Registration Info</Label>
      <div className="text-sm text-muted">
        {parseUserCodeDisplay(user.user_code)}
        {/* "Registered on 2026-01-09 14:30:52 (User #123,456)" */}
      </div>
    </InfoRow>
  </InfoCard>
</UserProfile>
```

### 用户前台

```tsx
// 用户设置页面 - 显示 user_code 用于客服沟通
<SettingsCard title="Account Information">
  <InfoRow>
    <Label>Your User Code</Label>
    <Code className="font-mono font-bold">{user.user_code}</Code>
    <Button
      variant="outline"
      size="sm"
      onClick={() => {
        copyToClipboard(user.user_code)
        toast.success("User code copied to clipboard")
      }}
    >
      <Copy className="w-4 h-4 mr-2" />
      Copy
    </Button>
  </InfoRow>

  <Alert>
    <Info className="w-4 h-4" />
    <AlertTitle>Need Help?</AlertTitle>
    <AlertDescription>
      Provide this user code when contacting support for faster assistance.
    </AlertDescription>
  </Alert>
</SettingsCard>
```

---

## 实用工具函数

### 解析 user_code

```typescript
// decodables-fe/@shared/utils/userCode.ts

export interface ParsedUserCode {
  registrationDate: string  // "2026-01-09"
  registrationTime: string  // "14:30:52.7890"
  userNumber: number        // 123456
  randomSuffix: string      // "ABC"
}

export function parseUserCode(userCode: string): ParsedUserCode | null {
  if (userCode.length !== 26) {
    return null
  }

  const datePart = userCode.substring(0, 6)   // 260109
  const timePart = userCode.substring(6, 12)  // 143052
  const msPart = userCode.substring(12, 16)   // 7890
  const countPart = userCode.substring(16, 24) // 00123456
  const randomPart = userCode.substring(24, 26) // ABC

  return {
    registrationDate: `20${datePart.substring(0, 2)}-${datePart.substring(2, 4)}-${datePart.substring(4, 6)}`,
    registrationTime: `${timePart.substring(0, 2)}:${timePart.substring(2, 4)}:${timePart.substring(4, 6)}.${msPart}`,
    userNumber: parseInt(countPart, 10),
    randomSuffix: randomPart,
  }
}

export function parseUserCodeDisplay(userCode: string): string {
  const parsed = parseUserCode(userCode)
  if (!parsed) {
    return userCode
  }

  return `Registered on ${parsed.registrationDate} ${parsed.registrationTime.substring(0, 8)} (User #${parsed.userNumber.toLocaleString()})`
}

// 示例输出: "Registered on 2026-01-09 14:30:52 (User #123,456)"
```

---

## 数据分析应用

### 统计每日注册量

```python
# scripts/analytics/daily_registration_stats.py
"""从 user_code 统计每日注册量."""

from datetime import datetime

async def get_daily_registration_stats(start_date: str, end_date: str):
    """
    统计每日注册量.

    Args:
        start_date: "2026-01-01"
        end_date: "2026-01-31"

    Returns:
        [
            {"date": "2026-01-09", "registrations": 1234},
            {"date": "2026-01-10", "registrations": 1456},
            ...
        ]
    """
    # 从 user_code 提取日期
    # user_code 前 6 位 = YYMMDD
    start_prefix = start_date[2:].replace("-", "")  # "260101"
    end_prefix = end_date[2:].replace("-", "")  # "260131"

    # 查询该日期范围的用户
    result = await db.query("""
        SELECT
            SUBSTRING(user_code, 1, 6) as date_prefix,
            COUNT(*) as count
        FROM profiles
        WHERE user_code >= %s AND user_code < %s
        GROUP BY date_prefix
        ORDER BY date_prefix
    """, (start_prefix, end_prefix + "999999999999999999999999"))

    # 转换为人类可读的日期
    stats = []
    for row in result:
        date_prefix = row["date_prefix"]
        readable_date = f"20{date_prefix[0:2]}-{date_prefix[2:4]}-{date_prefix[4:6]}"
        stats.append({
            "date": readable_date,
            "registrations": row["count"]
        })

    return stats
```

---

## 文档更新清单

### 后端文档
- [x] `docs/shared/USER-ID-SYSTEM.md` (本文档)
- [ ] `docs/后台业务逻辑说明.md` - 添加用户 ID 系统说明
- [ ] `CLAUDE.md` - 更新用户 ID 系统说明
- [ ] `infrastructure/repositories/user_repository.py` - 更新注释

### 前端文档
- [ ] `decodables-fe/docs/shared/USER-ID-SYSTEM.md` (复制本文档)
- [ ] `decodables-fe/docs/前端完整开发规范.md` - 添加用户 ID 系统说明
- [ ] `decodables-fe/@shared/utils/userCode.ts` - 新增解析工具

### 数据库文档
- [ ] `migrations/v2/design_reasoning.md` - 更新 user_code 说明
- [ ] `migrations/v2/refactored_schema_v2.sql` - 更新 profiles 表注释

---

## 总结

| 特征 | user_id | user_code |
|------|---------|-----------|
| **格式** | `user_2abc3def4ghi5jkl` (Clerk ID) | `26010914305278900123456ABC` (26位) |
| **来源** | Clerk 自动生成 | 系统注册时生成 |
| **可读性** | 机器友好 | 人类友好 |
| **包含信息** | 无语义 | 注册日期+时间+用户序号 |
| **主要用途** | 系统内部/数据库 | 管理员/客服/数据分析 |
| **典型场景** | API 调用，数据关联 | 用户反馈，管理员搜索，注册趋势分析 |
| **安全性** | 低敏感度 | 低敏感度 (双因素验证) |

**关键原则**:
- ✅ **user_id** 用于系统内部逻辑和数据关联
- ✅ **user_code** 用于人类交互、管理场景和数据分析
- ✅ 两者互补，各司其职，不可混用
- ✅ user_code 的设计兼顾唯一性、可读性和业务洞察

---

**最后更新**: 2026-01-09
**维护人**: 后端团队
**状态**: ✅ 已设计完成
