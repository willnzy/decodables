# SQL 硬编码审计报告 + 完整修复方案

> 审计日期: 2026-02-02
> 审计范围: `decodables/migrations/v2/*.sql` (3 个主 schema 文件)
> 目的: 发现所有硬编码问题，设计包含代码同步修改的完整修复方案

---

## 一、问题总览

| 严重等级 | 数量 | 说明 |
|---------|------|------|
| **P0 Critical** | 5 | 代码与 DB 参数不匹配 / 返回值解析错误，运行时可能崩溃 |
| **P1 High** | 5 | 业务逻辑硬编码，影响扩展性和正确性 |
| **P2 Medium** | 7 | 描述文本/魔术数字硬编码，影响可维护性 |
| **P3 Low** | 4 | 合理的默认值，仅需记录 |

---

## 二、P0 Critical — 必须修复

---

### P0-1: `restore_auth_user_with_profile` 参数签名严重不匹配

**严重性**: 🔴 运行时必崩 (PGRST202)

#### 问题描述

DB 函数需要 4 个参数，代码只传了 2 个，且返回类型不匹配:

| 对比项 | DB 函数 | 代码调用 |
|--------|---------|---------|
| 参数1 | `p_old_profile_id UUID` (必需) | ❌ 没传 |
| 参数2 | `p_email TEXT` | ✅ `p_email` |
| 参数3 | `p_password_hash TEXT` | ✅ `p_password_hash` |
| 参数4 | `p_display_name TEXT DEFAULT NULL` | ❌ 没传 |
| 返回类型 | `RETURNS UUID` | 代码期望 `row["auth_user"]` (JSONB) |

#### 当前调用链

```
router.py line 252-262:
  body.restore_account = true
  email = await auth_service.get_pending_user_email(user_id)
  result = await auth_service.restore_account(email=email, password=body.password)
    ↓
service.py line 1068-1108:
  async def restore_account(self, email, password, device_info):
    password_hash = hash(password)
    restored_user = await self._auth_user_repo.restore_account(email, password_hash)
      ↓
auth_user_repository.py line 397-415:
  async def restore_account(self, email, password_hash):
    result = await self._client.rpc("restore_auth_user_with_profile", {
        "p_email": normalized,
        "p_password_hash": password_hash,
        # ❌ 缺少 p_old_profile_id
    }).execute()
    row = result.data[0]
    auth_user_data = row["auth_user"]  # ❌ DB 返回 UUID，不是 JSONB
```

#### 完整修复方案

**1. 修改 DB 函数** (`01_core_business.sql`):
- 返回类型改为 `TABLE(auth_user JSONB, was_restored BOOLEAN)` (与 `create_auth_user_with_profile` 风格统一)
- 恢复窗口判断改为使用 `recovery_expires_at` (与代码查询一致)
- `source` 改为参数 `p_source TEXT DEFAULT 'register'`

```sql
CREATE OR REPLACE FUNCTION restore_auth_user_with_profile(
    p_old_profile_id UUID,
    p_email TEXT,
    p_password_hash TEXT,
    p_display_name TEXT DEFAULT NULL,
    p_source TEXT DEFAULT 'register'     -- 新增: 创建来源
)
RETURNS TABLE(
    auth_user JSONB,                      -- 改为 JSONB (与 create_auth_user_with_profile 统一)
    was_restored BOOLEAN
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = 'public'
AS $$
DECLARE
    v_profile RECORD;
    v_auth_user auth_users%ROWTYPE;
    v_restored_name TEXT;
BEGIN
    -- 1. 查询可恢复的 profiles 记录 (使用 recovery_expires_at 而非 deleted_at + 30 days)
    SELECT id, email, display_name, deleted_at, is_deleted, recovery_expires_at
        INTO v_profile
        FROM profiles
       WHERE id = p_old_profile_id
         AND is_deleted = true
         AND recovery_expires_at > CURRENT_TIMESTAMP  -- ✅ 统一使用 recovery_expires_at
         FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'RESTORE_NOT_FOUND: profile % not found or not restorable', p_old_profile_id;
    END IF;

    -- 2. 确认邮箱匹配
    IF v_profile.email <> LOWER(TRIM(p_email)) THEN
        RAISE EXCEPTION 'RESTORE_EMAIL_MISMATCH: email does not match profile record';
    END IF;

    -- 3. 创建新的 auth_users 记录（复用旧 UUID）
    INSERT INTO auth_users (id, email, password_hash, email_verified, email_verified_at, created_at, updated_at)
    VALUES (p_old_profile_id, LOWER(TRIM(p_email)), p_password_hash, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    RETURNING * INTO v_auth_user;

    -- 4. 恢复 profiles 记录
    v_restored_name := COALESCE(p_display_name, v_profile.display_name);
    IF v_restored_name = 'Deleted User' THEN
        v_restored_name := COALESCE(p_display_name, 'User');
    END IF;

    UPDATE profiles SET
        is_deleted = false,
        deleted_at = NULL,
        recovery_expires_at = NULL,      -- ✅ 清除恢复窗口 (当前 DB 函数遗漏了此字段!)
        display_name = v_restored_name,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_old_profile_id;

    -- 5. 记录恢复事件 (source 改为参数)
    INSERT INTO user_creation_logs (user_id, source, action, metadata, created_at)
    VALUES (
        p_old_profile_id::TEXT,
        p_source,                         -- ✅ 参数化
        'account_restored',
        jsonb_build_object(
            'restored_at', now(),
            'original_deleted_at', v_profile.deleted_at
        ),
        CURRENT_TIMESTAMP
    );

    -- 6. 返回结果 (与 create_auth_user_with_profile 风格统一)
    RETURN QUERY
    SELECT
        row_to_json(v_auth_user)::jsonb,
        TRUE;

EXCEPTION
    WHEN OTHERS THEN
        BEGIN
            INSERT INTO system_error_logs (operation, error_message, details, created_at)
            VALUES (
                'restore_auth_user_with_profile',
                SQLERRM,
                jsonb_build_object('profile_id', p_old_profile_id, 'email', p_email),
                CURRENT_TIMESTAMP
            );
        EXCEPTION
            WHEN OTHERS THEN NULL;
        END;
        RAISE;
END;
$$;
```

**2. 修改 Repository 接口** (`domains/auth/repository.py` line 251-271):

```python
@abstractmethod
async def restore_account(
    self,
    profile_id: UUID,       # 新增: 待恢复的 profile ID
    email: str,
    password_hash: str,
) -> AuthUser:
```

**3. 修改 Repository 实现** (`infrastructure/repositories/auth_user_repository.py` line 396-432):

```python
@retry_on_network_error_async()
async def restore_account(
    self,
    profile_id: UUID,       # 新增
    email: str,
    password_hash: str,
) -> AuthUser:
    """
    Restore a soft-deleted account via RPC restore_auth_user_with_profile().
    """
    normalized = email.strip().lower()
    result = await self._client.rpc(
        "restore_auth_user_with_profile",
        {
            "p_old_profile_id": str(profile_id),  # 新增
            "p_email": normalized,
            "p_password_hash": password_hash,
        },
    ).execute()

    if result is None or not result.data or len(result.data) == 0:
        raise RuntimeError("RPC restore_auth_user_with_profile returned no data")

    row = result.data[0]
    auth_user_data = row["auth_user"]  # 现在 DB 也返回 JSONB 了

    return AuthUser(
        id=UUID(auth_user_data["id"]),
        email=auth_user_data["email"],
        password_hash=auth_user_data.get("password_hash"),
        email_verified=auth_user_data.get("email_verified", True),
        email_verified_at=_parse_datetime(auth_user_data.get("email_verified_at")),
        is_active=auth_user_data.get("is_active", True),
        created_at=_parse_datetime(auth_user_data.get("created_at"))
        or datetime.now(timezone.utc),
        updated_at=_parse_datetime(auth_user_data.get("updated_at"))
        or datetime.now(timezone.utc),
    )
```

**4. 修改 Service 层** (`domains/auth/service.py` line 1068-1114):

```python
async def restore_account(
    self,
    email: str,
    password: str,
    device_info: Optional[DeviceInfo] = None,
) -> Dict[str, Any]:
    """Restore a soft-deleted account."""
    # 1. 查询可恢复的 profile (获取 profile_id)
    restorable = await self._auth_user_repo.get_restorable_by_email(email)
    if restorable is None:
        raise RestoreNotFoundError("No restorable account found for this email")

    profile_id = UUID(restorable["id"])

    # 2. Validate password
    strength = self._password_svc.validate_strength(password)
    if not strength.is_valid:
        raise WeakPasswordException(errors=list(strength.errors))

    # 3. Hash password
    password_hash = await run_in_threadpool(
        self._password_svc.hash_password, password
    )

    # 4. Restore via RPC (传入 profile_id)
    restored_user = await self._auth_user_repo.restore_account(
        profile_id=profile_id,    # 新增
        email=email,
        password_hash=password_hash,
    )

    # 5. Create session + tokens
    return await self._create_session_and_tokens(
        user=restored_user,
        device_info=device_info,
    )
```

> 注意: 需要确认 `RestoreNotFoundError` 是否已定义，或使用现有异常类。

**5. 修改测试文件**:
- `tests/domains/auth/conftest.py`: `repo.restore_account` mock 签名更新
- `tests/integration/auth/conftest.py`: 同上

#### 涉及文件汇总

| 文件 | 修改类型 |
|------|---------|
| `migrations/v2/01_core_business.sql` | 重写 `restore_auth_user_with_profile` 函数 |
| `domains/auth/repository.py` | 接口添加 `profile_id` 参数 |
| `infrastructure/repositories/auth_user_repository.py` | 实现添加 `profile_id`，RPC 传参+返回值解析 |
| `domains/auth/service.py` | `restore_account` 先查 `get_restorable_by_email` 获取 profile_id |
| `tests/domains/auth/conftest.py` | mock 签名更新 |
| `tests/integration/auth/conftest.py` | mock 签名更新 |

---

### P0-2: `restore_auth_user_with_profile` 恢复窗口判断逻辑不一致

**严重性**: 🔴 可能导致"代码说可恢复但 DB 拒绝"

#### 问题描述

| 位置 | 判断方式 |
|------|---------|
| Repository 查询 (`auth_user_repository.py` line 119) | `.gt("recovery_expires_at", now)` |
| DB 函数 (`01_core_business.sql` line 2232) | `deleted_at > now() - INTERVAL '30 days'` |

两者在边界条件上可能不一致 (如 `recovery_expires_at` 被手动修改过)。

#### 修复方案

**已包含在 P0-1 的 DB 函数重写中** — 统一使用 `recovery_expires_at > CURRENT_TIMESTAMP`。

#### 涉及文件

仅 `01_core_business.sql` (已在 P0-1 中修改)。

---

### P0-3: `process_subscription_start` / `process_subscription_renewal` 中 `payment_method` 硬编码

**严重性**: 🟡 审计记录不准确 (功能不崩溃但数据不对)

#### 问题描述

```sql
-- process_subscription_start (line 2707):
'card',           -- ❌ 硬编码

-- process_subscription_renewal (line 2822):
'card',           -- ❌ 硬编码
```

而 `process_credit_purchase` (`03_infrastructure.sql`) 已正确参数化:
```sql
p_payment_method TEXT DEFAULT 'stripe'  -- ✅ 已参数化
```

#### 修复方案

**1. 修改 DB 函数** (`01_core_business.sql`):

`process_subscription_start` — 添加参数:
```sql
CREATE OR REPLACE FUNCTION process_subscription_start(
    p_user_id UUID,
    p_plan TEXT,
    p_stripe_customer_id TEXT,
    p_credits_amount INT,
    p_payment_amount INT,
    p_currency TEXT,
    p_session_id TEXT,
    p_payment_method TEXT DEFAULT 'card'   -- 新增 (放最后，有默认值)
)
```

函数体中 line 2707 改为:
```sql
p_payment_method,    -- 替换 'card'
```

`process_subscription_renewal` — 同样添加:
```sql
CREATE OR REPLACE FUNCTION process_subscription_renewal(
    p_user_id UUID,
    p_tier TEXT,
    p_amount_usd INT,
    p_currency TEXT,
    p_invoice_id TEXT,
    p_monthly_credits INT,
    p_idempotency_key TEXT,
    p_payment_method TEXT DEFAULT 'card'   -- 新增
)
```

函数体中 line 2822 改为:
```sql
p_payment_method,    -- 替换 'card'
```

**2. 代码层**: 无需修改。新参数有 `DEFAULT 'card'`，现有调用不传此参数时自动使用默认值。如果将来需要区分支付方式，只需在 `subscription_repository.py` 的调用中添加参数即可。

#### 涉及文件

| 文件 | 修改类型 |
|------|---------|
| `migrations/v2/01_core_business.sql` | 2 个函数添加 `p_payment_method` 参数 |
| _(代码层无需修改)_ | — |

---

### P0-4: `create_auth_user_with_profile` 中 `created_by` / 日志 `source` 硬编码

**严重性**: 🟡 影响数据正确性 (无法区分用户来源)

#### 问题描述

```sql
-- profiles INSERT (line 2151):
'register',                    -- created_by 硬编码

-- user_creation_logs INSERT (line 2166):
'register',                    -- source 硬编码
```

同样问题在 `restore_auth_user_with_profile` (line 2266):
```sql
'register',                    -- source 硬编码 (应为 'restore' 或可配置)
```

#### 修复方案

**1. 修改 DB 函数** (`01_core_business.sql`):

`create_auth_user_with_profile` — 添加参数:
```sql
CREATE OR REPLACE FUNCTION create_auth_user_with_profile(
    p_user_id UUID,
    p_email TEXT,
    p_password_hash TEXT,
    p_display_name TEXT DEFAULT NULL,
    p_signup_bonus INT DEFAULT 0,
    p_created_by TEXT DEFAULT 'register'   -- 新增
)
```

函数体中:
```sql
-- line 2151 改为:
p_created_by,                  -- 替换 'register'

-- line 2166 改为:
p_created_by,                  -- 替换 'register'
```

`restore_auth_user_with_profile` — 已在 P0-1 方案中添加 `p_source` 参数。

**2. 代码层**: 无需修改。新参数有 `DEFAULT 'register'`，现有注册流程不传此参数时自动使用默认值。将来 OAuth 注册可传 `'oauth'`，Admin 创建可传 `'admin'`。

#### 涉及文件

| 文件 | 修改类型 |
|------|---------|
| `migrations/v2/01_core_business.sql` | `create_auth_user_with_profile` 添加 `p_created_by` 参数 |
| _(代码层无需修改)_ | — |

---

### P0-5: `create_pending_auth_user` 返回值解析错误 (RETURNS UUID vs dict 解析)

**严重性**: 🔴 运行时可能崩溃 (AttributeError)

> ⚠️ **复核新增** (2026-02-02): 原审计未覆盖此问题

#### 问题描述

DB 函数 `create_pending_auth_user` 声明 `RETURNS UUID` (标量返回)，但代码按 dict 解析:

```python
# auth_user_repository.py line 158-170:
row = result.data[0]

# 问题: row 是 UUID 字符串 (如 "550e8400-e29b-41d4-a716-446655440000")
#       不是 dict (如 {"user_id": "550e8400-..."})
if row.get("user_id") is None:    # ❌ str 没有 .get() 方法 → AttributeError
    ...

entity = AuthUser(
    id=UUID(row["user_id"]),       # ❌ str 不支持 ["user_id"] 索引
    ...
)
```

**PostgREST 对 `RETURNS UUID` 标量函数的返回格式**:
- `result.data` = `["550e8400-e29b-41d4-a716-446655440000"]` (UUID 字符串数组)
- `result.data[0]` = `"550e8400-e29b-41d4-a716-446655440000"` (字符串)
- **不是** `[{"user_id": "550e8400-..."}]`

对于 `RETURN NULL` (场景 3: 已注册用户):
- `result.data` = `[null]` 或 `[None]`
- `result.data[0]` = `None`

#### 修复方案

**方案 A (推荐): 修改代码，适配标量返回**

```python
# auth_user_repository.py line 155-170:
if result is None or not result.data or len(result.data) == 0:
    raise RuntimeError("RPC create_pending_auth_user returned no data")

user_id_value = result.data[0]  # UUID 字符串或 None

# RPC returns NULL when email already registered
if user_id_value is None:
    existing = await self.get_by_email(auth_user.email)
    if existing:
        return existing, False
    raise RuntimeError("RPC returned null but no existing user found")

# Success — create entity
entity = AuthUser(
    id=UUID(user_id_value) if isinstance(user_id_value, str) else user_id_value,
    email=auth_user.email,
    ...
)
return entity, True
```

**方案 B: 修改 DB 函数返回 TABLE (与其他 RPC 风格统一)**

```sql
CREATE OR REPLACE FUNCTION create_pending_auth_user(...)
RETURNS TABLE(user_id UUID)     -- 改为 TABLE
...
    RETURN QUERY SELECT v_user_id;   -- 替换 RETURN v_user_id
    RETURN QUERY SELECT v_existing.id;
    RETURN QUERY SELECT NULL::UUID;
```

这样代码的 `row.get("user_id")` 就能正确工作。但需要注意 `RETURN QUERY SELECT NULL::UUID` 返回的是 `[{"user_id": null}]`，代码的判断逻辑正好匹配。

**方案选择**: 推荐**方案 B**，理由:
- 与 `create_auth_user_with_profile` (RETURNS TABLE) 风格统一
- 代码端改动最小 (仅需确认 `row.get("user_id")` 逻辑正确)
- 后续如需返回更多字段 (如 `was_created`)，扩展方便

#### 涉及文件

| 文件 | 修改类型 |
|------|---------|
| `migrations/v2/01_core_business.sql` | `create_pending_auth_user` 返回类型改为 `TABLE(user_id UUID)` |
| `infrastructure/repositories/auth_user_repository.py` | 确认 `row.get("user_id")` 逻辑兼容 (若选方案 B 则无需改代码) |

---

## 三、P1 High — 建议修复

---

### P1-1: 软删除恢复期 `30 days` 硬编码

**位置**: `01_core_business.sql`

```sql
-- soft_delete_category_descendants (line 1883):
recovery_expires_at = CURRENT_TIMESTAMP + INTERVAL '30 days',
```

#### 修复方案

**方式1 (推荐)**: 添加参数 `p_recovery_days`

```sql
CREATE OR REPLACE FUNCTION soft_delete_category_descendants(
    parent_path_input LTREE,
    p_recovery_days INTEGER DEFAULT 30    -- 新增
)
RETURNS INTEGER AS $$
...
    recovery_expires_at = CURRENT_TIMESTAMP + INTERVAL '1 day' * p_recovery_days,
...
```

**代码同步**: 调用方可选传入天数，不传使用默认 30 天。如果要从 `system_configs` 读取，在 Python service 层读取后传入。

#### 涉及文件

| 文件 | 修改类型 |
|------|---------|
| `migrations/v2/01_core_business.sql` | 函数添加参数 |
| _(代码层可选修改)_ | 传入从 system_configs 读取的天数 |

---

### P1-2: `process_subscription_start` 中 Tier 验证硬编码 `('t2', 't3')`

**位置**: `01_core_business.sql` line 2644

```sql
IF p_plan NOT IN ('t2', 't3') THEN
```

**以及** line 2682:
```sql
IF v_current_tier IN ('t2', 't3') AND v_current_status = 'active' THEN
```

#### 修复方案

**暂不修改代码**，添加注释标记:

```sql
-- ⚠️ TIER_VALIDATION: 新增 tier 时需更新此处 (如 t4)
IF p_plan NOT IN ('t2', 't3') THEN
```

**理由**:
- 这是防御性验证，硬编码是有意的 (防止传入无效 tier)
- 新增 tier 是低频操作，需要有意识地检查所有相关逻辑
- 如果改为动态查询 `system_configs`，会增加函数复杂度和性能开销

#### 涉及文件

| 文件 | 修改类型 |
|------|---------|
| `migrations/v2/01_core_business.sql` | 仅添加注释 |

---

### P1-3: `'Deleted User'` 硬编码

**位置**: `01_core_business.sql` line 2251

```sql
IF v_restored_name = 'Deleted User' THEN
    v_restored_name := COALESCE(p_display_name, 'User');
END IF;
```

#### 修复方案

**暂不修改**，添加注释关联:

```sql
-- ⚠️ SYNC_REQUIRED: 此值必须与账户删除脱敏逻辑中的占位符一致
-- 参见: domains/identity/service.py soft_delete 相关逻辑
IF v_restored_name = 'Deleted User' THEN
```

**理由**: 改为参数化增加复杂度但收益低，因为这个值极少变化。关键是保持两处同步。

---

### P1-4: `cleanup_old_activity_logs` 中保留事件类型硬编码

**位置**: `03_infrastructure.sql` line 2118

```sql
AND action NOT IN ('user_signup', 'subscription_purchase');
```

#### 修复方案

添加参数:

```sql
CREATE OR REPLACE FUNCTION cleanup_old_activity_logs(
    p_retention_days INTEGER DEFAULT 180,
    p_preserve_actions TEXT[] DEFAULT ARRAY['user_signup', 'subscription_purchase']  -- 新增
)
...
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '1 day' * p_retention_days
      AND action != ALL(p_preserve_actions);    -- 替换硬编码
```

**代码同步**: 无需修改。调用方不传时使用默认值。如需动态配置，可从 `system_configs` 读取后传入。

#### 涉及文件

| 文件 | 修改类型 |
|------|---------|
| `migrations/v2/03_infrastructure.sql` | 函数添加参数 |

---

### P1-5: Workspace 邀请过期时间 `7 days` 硬编码

**位置**: `01_core_business.sql` line 2587

```sql
expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '7 days'),
```

#### 修复方案

**保留 DB DEFAULT 作为防御** + **代码层覆盖**:

DB 无需修改 (DEFAULT 作为安全兜底)。

代码层创建邀请时从配置读取:
```python
# workspace_service.py 中创建邀请时:
expiry_days = await config_service.get_int("workspace_invitation_expiry_days", default=7)
expires_at = datetime.now(timezone.utc) + timedelta(days=expiry_days)
# 传入 expires_at 覆盖 DB DEFAULT
```

#### 涉及文件

| 文件 | 修改类型 |
|------|---------|
| _(DB 无需修改)_ | — |
| Workspace 相关 service (如有) | 从配置读取过期天数 |

---

## 四、P2 Medium — 可选优化 (记录在案)

---

### P2-1: 交易描述文本英文硬编码 (8 处)

| 文件 | 行号 | 硬编码描述 |
|------|------|-----------|
| `01_core_business.sql` | 2714 | `format('%s Plan Subscription - $%s', ...)` |
| `01_core_business.sql` | 2732 | `format('%s Plan Monthly Credits', ...)` |
| `01_core_business.sql` | 2829 | `format('%s Plan Renewal - $%s', ...)` |
| `01_core_business.sql` | 2854 | `format('%s Plan Monthly Credits Renewal', ...)` |
| `01_core_business.sql` | 3061 | `'Monthly credits cleared on subscription termination (' || p_reason || ')'` |
| `03_infrastructure.sql` | 968 | `format('Purchase %s Credits - $%s', ...)` |
| `03_infrastructure.sql` | 1000 | `format('Purchase %s Credits', ...)` |
| `03_infrastructure.sql` | 3194 | `'Credits reversed due to refund (refund_id: ' || p_refund_id || ')'` |

#### 修复方案

**当前不修复** — 理由:
- 这些是**内部审计记录**的 description 字段，不直接面向用户展示
- 前端展示交易历史时，应根据 `transaction_type` 字段动态生成用户可见的描述
- 多语言支持是前端职责，DB 记录原始英文作为审计日志是合理的

**如果将来需要修改**: 给每个 RPC 函数添加 `p_description TEXT DEFAULT NULL` 参数，由 service 层构建描述后传入。DB 的 `format(...)` 作为 `COALESCE(p_description, format(...))` 的 fallback。

---

### P2-2: 积分操作上限魔术数字

| 文件 | 行号 | 函数 | 硬编码值 |
|------|------|------|---------|
| `03_infrastructure.sql` | 670 | `deduct_credits_atomic` | `p_amount > 1000000` |
| `03_infrastructure.sql` | 800 | `add_credits_atomic` | `p_amount > 1000000` |
| `03_infrastructure.sql` | 905 | `process_credit_purchase` | `p_credits_amount > 100000` |

#### 修复方案

**当前不修复** — 理由:
- 这些是**安全防线**，防止异常值写入数据库
- 100 万 / 10 万的上限远超正常业务范围
- 在 RPC 函数中读取 `system_configs` 表会增加一次查询，性能开销不值得
- 如果真需要调整，直接修改 SQL 即可

---

### P2-3: 金额转换 `/100.0` 硬编码

**位置**: `01_core_business.sql` line 2708, `03_infrastructure.sql` line 962

```sql
p_payment_amount / 100.0,  -- 美分转美元
```

#### 修复方案

**当前不修复** — 产品目前只支持 USD。如果将来接入日元等零位小数货币，再添加 `p_currency_divisor` 参数。

---

### P2-4: `generate_ticket_number` 格式硬编码

**位置**: `03_infrastructure.sql` line 1247

```sql
NEW.ticket_number := 'TKT-' || today_date || '-' || LPAD(today_count::TEXT, 3, '0');
```

#### 修复方案

**当前不修复** — 工单编号格式通常不会改变。如需修改，直接编辑 SQL。

---

### P2-5: Campaign 默认时区 `'America/New_York'`

**位置**: `02_platform_services.sql` line 289

```sql
timezone TEXT DEFAULT 'America/New_York',
```

#### 修复方案

**改为 `'UTC'`**:
```sql
timezone TEXT DEFAULT 'UTC',
```

这是一个简单的 DDL 修改，不影响代码 (代码创建 Campaign 时会显式传入时区)。

#### 涉及文件

| 文件 | 修改类型 |
|------|---------|
| `migrations/v2/02_platform_services.sql` | 改 DEFAULT 值 |

---

### P2-7: `get_user_creation_stats` 缺少 `restore` 统计列

> ⚠️ **复核新增** (2026-02-02): 改进项

**位置**: `01_core_business.sql` line 2302-2352

```sql
RETURNS TABLE(
    total_users BIGINT,
    register_created BIGINT,
    admin_created BIGINT,
    oauth_created BIGINT,     -- 仅统计 register/admin/oauth 三种 created_by
    duplicate_attempts BIGINT,
    errors BIGINT
)
```

#### 修复方案

**与 P0-4 联动** — 如果 P0-4 在 `restore_auth_user_with_profile` 中将 `user_creation_logs.source` 改为 `'restore'`，可以考虑:

1. 在 `get_user_creation_stats` 中增加 `restore_created` 列统计从 `user_creation_logs` 查询恢复事件数
2. 注意: `profiles.created_by` 在恢复时**不会改变**（保留原值），所以统计恢复事件应查 `user_creation_logs.action = 'account_restored'`

**当前不修复** — 恢复是低频事件，可在管理面板完善时一起处理。

---

### P2-6: `idempotency_key` 前缀构造

多处硬编码:
```sql
'sub_start_' || p_session_id           -- process_subscription_start
'renewal_' || p_invoice_id             -- 在 subscription_repository.py 中构造
'credit_purchase_' || p_session_id     -- process_credit_purchase
'refund_' || p_refund_id              -- process_credit_refund
```

#### 修复方案

**当前不修复** — 前缀是约定，改为参数化反而增加不一致的风险。关键是 DB 和代码使用相同的前缀。在此文档中记录即可:

| 前缀 | 用途 | 构造方 |
|------|------|--------|
| `sub_start_` | 首次订阅 | DB 函数内构造 |
| `renewal_` | 订阅续费 | Python 代码构造 |
| `credit_purchase_` | 积分购买 | Python 代码构造 |
| `refund_` | 退费 | DB 函数内构造 |

---

## 五、P3 Low — 合理的默认值 (无需修改)

| 位置 | 值 | 说明 |
|------|------|------|
| `profiles.tier` | `DEFAULT 't1'` | 新用户默认免费 Tier |
| `profiles.language` | `DEFAULT 'en'` | 合理的默认语言 |
| `profiles.timezone` | `DEFAULT 'UTC'` | 标准默认时区 |
| `cleanup_old_error_logs` | `DEFAULT 30` 天 | 已支持参数覆盖 |
| `cleanup_old_activity_logs` | `DEFAULT 180` 天 | 已支持参数覆盖 |
| `p_signup_bonus` | `DEFAULT 0` | 已参数化 |
| `p_payment_method` (credit_purchase) | `DEFAULT 'stripe'` | 已参数化 |

---

## 六、实施计划

### 第一批: P0 (必须修复)

| 序号 | 任务 | 涉及文件数 | 预估工作量 |
|------|------|-----------|-----------|
| P0-5 | `create_pending_auth_user` 返回值改为 `TABLE(user_id UUID)` | 1 (仅 SQL) | 小 |
| P0-1 | 重写 `restore_auth_user_with_profile` + 代码 4 层同步 | 6 | 大 |
| P0-2 | (已包含在 P0-1 中) | — | — |
| P0-3 | 2 个订阅 RPC 添加 `p_payment_method` | 1 (仅 SQL) | 小 |
| P0-4 | `create_auth_user_with_profile` 添加 `p_created_by` | 1 (仅 SQL) | 小 |

### 第二批: P1 (建议修复)

| 序号 | 任务 | 涉及文件数 | 预估工作量 |
|------|------|-----------|-----------|
| P1-1 | `soft_delete_category_descendants` 添加 `p_recovery_days` | 1 | 小 |
| P1-2 | Tier 验证添加注释标记 | 1 | 极小 |
| P1-3 | `'Deleted User'` 添加注释关联 | 1 | 极小 |
| P1-4 | `cleanup_old_activity_logs` 添加 `p_preserve_actions` | 1 | 小 |
| P1-5 | Workspace 邀请 — 代码层从配置读取 | 1-2 | 小 |

### 第三批: P2 (可选)

| 序号 | 任务 | 说明 |
|------|------|------|
| P2-5 | Campaign 默认时区改 UTC | 极小 |
| 其余 P2 | 暂不修复，记录在案 | — |

---

## 七、注意事项

1. **修改 RPC 函数签名后，必须在 staging 数据库执行更新的 SQL**
   - 通过 Supabase Dashboard SQL Editor 执行
   - 或 Railway 部署时手动执行

2. **新参数都使用 `DEFAULT` 值保证向后兼容**
   - P0-3, P0-4, P1-1, P1-4 的新参数都有默认值
   - 现有代码不传这些参数时不会崩溃
   - **但 P0-1 的 `p_old_profile_id` 是必需参数，必须同步修改代码**

3. **P0-1 是最复杂的修复**，涉及 4 层代码修改:
   - SQL 函数重写 (参数 + 返回类型)
   - Repository 接口 + 实现
   - Service 层 (新增查询 profile_id 步骤)
   - 测试 mock 更新

4. **修改顺序建议**:
   - **P0-5 优先**: 先修 `create_pending_auth_user` 返回类型 (注册流程正在测试中)
   - 先改 DB SQL 并部署到 staging
   - 再改代码并部署
   - 如果反过来 (先改代码后改 DB)，代码传了新参数但 DB 还没更新，会报错

5. **P0-1 修复方案中的额外发现** (复核新增):
   - 当前 DB 的 `restore_auth_user_with_profile` 恢复 profile 时**没有清除 `recovery_expires_at`** 字段
   - 修复方案已包含 `recovery_expires_at = NULL` 的 UPDATE

---

## 八、复核记录

> 复核日期: 2026-02-02
> 复核目的: 检查文档中的错误、重复、冲突和遗漏

### 复核发现

| # | 类型 | 发现 | 处理 |
|---|------|------|------|
| 1 | **遗漏 (P0)** | `create_pending_auth_user` `RETURNS UUID` 但代码用 `row.get("user_id")` 按 dict 解析，运行时会 `AttributeError` | 新增 P0-5 |
| 2 | **遗漏 (补充)** | P0-1 的 `restore_auth_user_with_profile` 恢复 profile 时未清除 `recovery_expires_at` | 已补充到 P0-1 修复方案 |
| 3 | **遗漏 (P2)** | `get_user_creation_stats` 未统计恢复事件 (低频，可后续优化) | 新增 P2-7 |
| 4 | **验证通过** | P0-1 参数不匹配分析正确 (DB 需要 `p_old_profile_id`，代码未传) | — |
| 5 | **验证通过** | P0-2 恢复窗口判断不一致 (DB 用 `deleted_at + 30d`，代码用 `recovery_expires_at`) | — |
| 6 | **验证通过** | P0-3 `payment_method` 硬编码 `'card'` 确认准确 | — |
| 7 | **验证通过** | P0-4 `created_by`/`source` 硬编码 `'register'` 确认准确 | — |
| 8 | **验证通过** | P1-1 ~ P1-5 分析正确，无重复/冲突 | — |
| 9 | **验证通过** | P2-1 ~ P2-6 分析正确，优先级合理 | — |
| 10 | **无冲突** | P0-1 (restore 函数重写) 与 P0-2 (恢复窗口统一) 方案兼容，P0-2 已合并到 P0-1 | — |
| 11 | **无冲突** | P0-4 (source 参数化) 与 P0-1 (restore 重写) 在 restore 函数中通过 `p_source` 参数统一 | — |
| 12 | **无重复** | 所有 19+3 个问题项互不重复 | — |

### 优先级调整

- P0-5 (`create_pending_auth_user` 返回值) 应**最先修复**，因为注册流程正在测试中，这是当前最可能触发的 bug
- P0-1 (restore 重写) 仍是最复杂的修复，建议在 P0-5 之后处理
