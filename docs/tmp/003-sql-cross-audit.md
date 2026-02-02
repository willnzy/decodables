# SQL Schema 全面审计报告 (最终版)

> **审计日期**: 2026-02-02
> **审计范围**: `decodables/migrations/v2/*.sql` (3 文件, 7,793 行) vs 后台 Python 代码
> **审计维度**: 7 个 (RPC 交叉验证 / 表实体映射 / 索引覆盖 / 安全 / 数据完整性 / 一致性 / 硬编码)
> **合并说明**: 本报告整合了 `002-sql-hardcoding-audit.md` (21 项) 和 `003-sql-cross-audit.md` (37 项) 的全部发现

---

## Executive Summary

| 严重等级 | D1 | D2 | D3 | D4 | D5 | D6 | D7 | 总计 |
|---------|----|----|----|----|----|----|----|----|
| **P0 Critical** | 4+5 | 0 | 0 | 0 | 0 | 0 | 0 | **9** |
| **P1 High** | 0 | 1 | 0 | 4 | 1 | 0 | 5 | **11** |
| **P2 Medium** | 4 | 4 | 1 | 3 | 0 | 0 | 7 | **19** |
| **P3 Low** | 5 | 4 | 2 | 3 | 1 | 0 | 4 | **19** |
| **合计** | **18** | **9** | **3** | **10** | **2** | **0** | **16** | **58** |

> **全维度审计已完成**，发现 **58 项独立问题**：
> - **P0 Critical** (9 项): RPC 函数缺失/参数不匹配/返回值解析错误，运行时崩溃
> - **P1 High** (11 项): 枚举缺失、幂等性约束缺失、安全注入风险、权限检查失效、业务逻辑硬编码
> - **P2 Medium** (19 项): 标量返回值解析、命名不一致、架构设计、描述文本硬编码
> - **P3 Low** (19 项): 死代码、类型差异、索引优化、合理默认值

---

## 修复优先级队列 (合并版)

### 第一批: P0 Critical (9 项) — 必须修复

| 序号 | 来源 | 维度 | 修复内容 | 涉及文件 | 预估工时 |
|------|------|------|---------|---------|---------|
| 1 | 003 | D1 | 创建 `create_user_idempotent` SQL 函数 | SQL + 验证 | 1h |
| 2 | 003 | D1 | 创建 `create_generation_task` SQL 函数 | SQL | 0.5h |
| 3 | 003 | D1 | 创建 `update_webhook_result` SQL 函数 | SQL | 0.5h |
| 4 | 003 | D1 | 创建 `get_event_stats_by_*` 系列 SQL 函数 | SQL | 1h |
| 5 | 002 | D1 | `create_pending_auth_user` 返回值改为 `TABLE(user_id UUID)` | SQL (+ 验证代码兼容) | 小 |
| 6 | 002 | D1 | 重写 `restore_auth_user_with_profile` + 代码 4 层同步 | 6 文件 | 大 (4h) |
| 7 | 002 | D1 | (已包含在 #6 中) 恢复窗口判断统一使用 `recovery_expires_at` | — | — |
| 8 | 002 | D1 | 2 个订阅 RPC 添加 `p_payment_method` 参数 | SQL | 小 |
| 9 | 002 | D1 | `create_auth_user_with_profile` 添加 `p_created_by` 参数 | SQL | 小 |

### 第二批: P1 High (11 项) — 建议修复

| 序号 | 来源 | 维度 | 修复内容 | 预估工时 |
|------|------|------|---------|---------|
| 10 | 003 | D2 | TransactionType 枚举同步 (SQL 16 值 vs Python 11 值) | 1h |
| 11 | 003 | D4 | 后端设置 `app.current_user_role` 会话变量 | 1h |
| 12 | 003 | D4 | Webhook 处理函数添加表名白名单验证 | 0.5h |
| 13 | 003 | D4 | `system_resources_admin_repository.py:88` 添加 sanitize | 0.2h |
| 14 | 003 | D4 | `feature_flags/repository.py:102` 添加 sanitize | 0.2h |
| 15 | 003 | D5 | `projects.idempotency_key` 添加 UNIQUE 部分索引 | 0.3h |
| 16 | 002 | D7 | `soft_delete_category_descendants` 添加 `p_recovery_days` 参数 | 小 |
| 17 | 002 | D7 | Tier 验证 `('t2', 't3')` 添加注释标记 | 极小 |
| 18 | 002 | D7 | `'Deleted User'` 硬编码添加注释关联 | 极小 |
| 19 | 002 | D7 | `cleanup_old_activity_logs` 添加 `p_preserve_actions` 参数 | 小 |
| 20 | 002 | D7 | Workspace 邀请过期时间从配置读取 | 小 |

### 第三批: P2 Medium (19 项) — 可选优化

| 序号 | 来源 | 维度 | 修复内容 | 预估工时 |
|------|------|------|---------|---------|
| 21-24 | 003 | D1 | 修复 4 处 PostgREST 标量返回值解析 | 1h |
| 25 | 003 | D2 | `profiles.id` vs `UserProfile.user_id` 命名不一致 | 2h |
| 26-27 | 003 | D2 | `datetime.utcnow()` 改为 `datetime.now(timezone.utc)` | 0.5h |
| 28 | 003 | D2 | `projects` 表创建领域实体 | 4h |
| 29 | 003 | D3 | profiles 表 GIN trigram 索引 | 0.5h |
| 30-31 | 003 | D4 | 死代码 SECURITY DEFINER 函数评估删除 | 0.5h |
| 32 | 003 | D4 | `analytics_events_repository.py:204` 改用参数化查询 | 0.2h |
| 33 | 003 | D4 | 统一 sanitize 实现 | 2h |
| 34-40 | 002 | D7 | 交易描述硬编码 / 魔术数字 / 金额转换 / 工单格式 / 时区 / 统计列 / 幂等性前缀 | 记录在案 |

### 第四批: P3 Low (19 项) — 记录在案

| 来源 | 维度 | 说明 |
|------|------|------|
| 003 | D1 | 5 个死 SQL 函数 (建议清理) |
| 003 | D2 | INET vs str 类型差异 (2), revoke_reason CHECK 不一致, tx_type deprecated |
| 003 | D3 | projects/credit_transactions 可能缺复合索引 (2) |
| 003 | D4 | 重复 RLS 策略 (2), VIEW/TABLE 注释矛盾, is_admin() RLS 引用风险 |
| 003 | D5 | updated_at 双重更新 (冗余但无害) |
| 002 | D7 | 合理默认值 (tier='t1', language='en', timezone='UTC', 已参数化值) |

**总预估工时**: P0 ~8h + P1 ~5h + P2 ~11h + P3 ~2h = **~26 小时**

---

## D1: RPC 函数交叉验证

**审计方法**: 提取 3 个 SQL schema 文件中所有 `CREATE OR REPLACE FUNCTION` 定义，与 Python 代码中所有 `.rpc("xxx"` 调用点进行全量交叉比对。

---

### D1-1. 缺失函数 (代码调用但 SQL 不存在) — P0 Critical x4

> 代码中通过 `.rpc()` 调用的函数名在 3 个 SQL schema 文件中均未找到定义。
> 运行时将触发 PostgREST **PGRST202** 错误 (Could not find the function)，导致请求崩溃。

| # | 函数名 | 调用位置 | 参数签名 (代码侧) | 期望返回 |
|---|--------|---------|-------------------|---------|
| 1 | `create_user_idempotent` | `user_repository.py:145` | 9 params: `p_user_id`, `p_email`, `p_source`, `p_username`, `p_first_name`, `p_last_name`, `p_avatar_url`, `p_display_name`, `p_signup_bonus` | JSONB: `{user_profile, was_created, created_by}` |
| 2 | `create_generation_task` | `generation_service.py:413` | 6 params: `p_task_id`, `p_user_id`, `p_task_type`, `p_params` (JSONB), `p_priority`, `p_total_steps` | 无返回值处理 (best-effort) |
| 3 | `update_webhook_result` | `stripe_webhook_service.py:149` | 2 params: `p_event_id`, `p_result` (JSONB) | 无返回值处理 (best-effort，失败仅 log) |
| 4 | `get_event_stats_by_type` 等动态名称 | `events_repository.py:120` | 从 `function_map` dict 动态解析函数名 | TABLE |

**影响分析**:

- **#1 `create_user_idempotent`**: 用户注册流程核心函数。缺失将导致新用户无法注册。**影响面: 极大**。
- **#2 `create_generation_task`**: AI 生成任务创建。缺失将导致所有 AI 生成功能不可用。**影响面: 大**。
- **#3 `update_webhook_result`**: Stripe Webhook 结果记录。缺失不会阻塞支付流程 (best-effort)，但会丢失审计日志。**影响面: 中**。
- **#4 `get_event_stats_by_*`**: 事件统计查询。缺失将导致 Admin 面板统计功能报错。**影响面: 中**。

**修复建议**: 在对应的 SQL schema 文件中补建这 4 个函数，签名需与代码调用侧完全匹配。

---

### D1-2. RPC 参数/返回值严重不匹配 — P0 Critical x5 (来自 002)

> 以下 5 项来自 002-sql-hardcoding-audit，是参数签名或返回值解析的严重问题。

#### P0-1: `restore_auth_user_with_profile` 参数签名严重不匹配

**严重性**: 🔴 运行时必崩 (PGRST202)

DB 函数需要 4 个参数，代码只传了 2 个，且返回类型不匹配:

| 对比项 | DB 函数 | 代码调用 |
|--------|---------|---------|
| 参数1 | `p_old_profile_id UUID` (必需) | ❌ 没传 |
| 参数2 | `p_email TEXT` | ✅ `p_email` |
| 参数3 | `p_password_hash TEXT` | ✅ `p_password_hash` |
| 参数4 | `p_display_name TEXT DEFAULT NULL` | ❌ 没传 |
| 返回类型 | `RETURNS UUID` | 代码期望 `row["auth_user"]` (JSONB) |

**完整修复方案** (涉及 6 文件 4 层修改):

**1. 修改 DB 函数** (`01_core_business.sql`):
- 返回类型改为 `TABLE(auth_user JSONB, was_restored BOOLEAN)`
- 恢复窗口判断改为使用 `recovery_expires_at`
- `source` 改为参数 `p_source TEXT DEFAULT 'register'`
- 恢复时清除 `recovery_expires_at = NULL`

**2. 修改 Repository 接口** (`domains/auth/repository.py`):
```python
@abstractmethod
async def restore_account(
    self,
    profile_id: UUID,       # 新增: 待恢复的 profile ID
    email: str,
    password_hash: str,
) -> AuthUser:
```

**3. 修改 Repository 实现** (`infrastructure/repositories/auth_user_repository.py`):
- 传入 `p_old_profile_id`
- 解析 JSONB 返回值

**4. 修改 Service 层** (`domains/auth/service.py`):
- 先查询 `get_restorable_by_email` 获取 `profile_id`
- 传入 `profile_id` 到 Repository

**5. 修改测试**: mock 签名更新

**涉及文件**: `01_core_business.sql`, `domains/auth/repository.py`, `auth_user_repository.py`, `domains/auth/service.py`, 2 个 conftest.py

---

#### P0-2: 恢复窗口判断逻辑不一致

**已包含在 P0-1 修复中** — 统一使用 `recovery_expires_at > CURRENT_TIMESTAMP`。

---

#### P0-3: `process_subscription_start` / `process_subscription_renewal` 中 `payment_method` 硬编码

**严重性**: 🟡 审计记录不准确

```sql
'card',           -- ❌ 硬编码 (2 处)
```

**修复**: 两个函数添加 `p_payment_method TEXT DEFAULT 'card'` 参数。代码层无需修改 (默认值兼容)。

---

#### P0-4: `create_auth_user_with_profile` 中 `created_by` / 日志 `source` 硬编码

**严重性**: 🟡 影响数据正确性

```sql
'register',       -- ❌ 硬编码 (2 处: profiles.created_by + user_creation_logs.source)
```

**修复**: 添加 `p_created_by TEXT DEFAULT 'register'` 参数。代码层无需修改。

---

#### P0-5: `create_pending_auth_user` 返回值解析错误

**严重性**: 🔴 运行时可能崩溃 (AttributeError)

DB 函数 `RETURNS UUID` (标量)，代码用 `row.get("user_id")` 按 dict 解析:
- `result.data[0]` = UUID 字符串，不是 dict
- `str.get()` → `AttributeError`

**推荐修复 (方案 B)**: DB 返回类型改为 `RETURNS TABLE(user_id UUID)`，代码无需修改。

---

### D1-3. 参数匹配验证 (19 个已验证 RPC)

> 排除 002 中已记录的项后，所有 RPC 函数参数签名**完全匹配**。

| # | 函数名 | SQL 参数数 | 代码传参数 | 结果 |
|---|--------|-----------|-----------|------|
| 1 | `rpc_user_growth_stats` | 2 | 2 | OK |
| 2 | `admin_adjust_credits_atomic` | 5 | 5 | OK |
| 3 | `process_subscription_start` | 7 | 7 | OK |
| 4 | `process_subscription_renewal` | 7 | 7 | OK |
| 5 | `process_subscription_termination` | 5 | 5 | OK |
| 6 | `process_credit_refund` | 7 | 7 | OK |
| 7 | `deduct_credits_atomic` | 7 | 4-5 | OK (有默认值) |
| 8 | `add_credits_atomic` | 6 | 4-5 | OK |
| 9 | `process_credit_purchase` | 7 | 6 | OK |
| 10 | `delete_tag_atomic` | 1 | 1 | OK (**返回值解析有问题**, 见 D1-4) |
| 11 | `set_project_tags_atomic` | 3 | 3 | OK |
| 12 | `set_asset_tags_atomic` | 4 | 4 | OK |
| 13 | `create_project_with_limit_check` | 16 | 16 | OK |
| 14 | `p_get_marketplace_listings` | 8 | 8 | OK |
| 15 | `check_webhook_idempotency` | 3 | 3 | OK |
| 16 | `get_category_descendants` | 1 | 1 | OK |
| 17 | `update_category_descendants_path` | 2 | 2 | OK (**返回值解析有问题**) |
| 18 | `soft_delete_category_descendants` | 1 | 1 | OK (**返回值解析有问题**) |
| 19 | `increment_asset_usage` | 2 | 2 | OK (**返回值解析有问题**) |

---

### D1-4. 返回类型不匹配 (PostgREST 标量解析问题) — P2 x4

> PostgREST 对标量返回函数统一返回 JSON 数组格式，如 `[true]`、`[5]`。
> 代码直接对 `result.data` 做判断导致逻辑错误。

| # | 函数名 | SQL 返回类型 | Python 解析方式 | Bug 描述 | 严重等级 |
|---|--------|-------------|----------------|---------|---------|
| 1 | `delete_tag_atomic` | `RETURNS BOOLEAN` | `bool(result.data)` | `bool([False])` = `True`，删除失败误判为成功 | **P2** |
| 2 | `increment_asset_usage` | `RETURNS INTEGER` | `result.data != -1` | `[-1] != -1` 恒为 `True`，永远不走失败分支 | **P2** |
| 3 | `update_category_descendants_path` | `RETURNS INTEGER` | `result.data if result.data else 0` | 返回 `[5]` 而非 `5` | **P2** |
| 4 | `soft_delete_category_descendants` | `RETURNS INTEGER` | 同上 | 同 #3 | **P2** |

**统一修复模式**:
```python
# 错误
success = bool(result.data)        # [False] -> True (BUG!)
# 正确
success = bool(result.data[0]) if result.data else False
```

> **建议**: 在 Repository 基类中封装 `unwrap_scalar(result)` 方法。

---

### D1-5. 死函数 (SQL 存在但无 Python 调用) — P3 x5

| # | 函数名 | SQL 位置 | 分析 |
|---|--------|---------|------|
| 1 | `increment_project_view_count()` | `01_core_business.sql:3682` | 预留功能，无调用 |
| 2 | `increment_project_like_count()` | `01_core_business.sql:3707` | 社交功能预留 |
| 3 | `get_dashboard_projects()` | `01_core_business.sql:3233` | 被直接表查询替代 |
| 4 | `get_dashboard_assets()` | `01_core_business.sql:3389` | 同上 |
| 5 | `get_dashboard_stats()` | `01_core_business.sql:3539` | 注意: 与 `get_user_dashboard_stats()` 是不同函数 |

**建议**: 确认无前端直接调用后标记为 deprecated 或移除。

---

### D1-6. 汇总统计

| 分类 | 数量 | 严重等级 |
|------|------|---------|
| 缺失 SQL 函数 (代码调用不存在的函数) | **4** | P0 Critical |
| 参数/返回值严重不匹配 (来自 002) | **5** | P0 Critical |
| 返回类型解析错误 (标量 vs 列表) | **4** | P2 Medium |
| 死 SQL 函数 (无调用方) | **5** | P3 Low |

**D1 维度总计**: **18 项发现** (9 P0 + 0 P1 + 4 P2 + 5 P3)

---

## D2: 表-实体映射

**审计方法**: 对比 SQL `CREATE TABLE` 字段定义与 Python 领域实体属性定义，检查是否完整一致。

**审计覆盖**: 核心业务表 (auth_users, auth_sessions, profiles, credit_transactions, tags, projects)

---

### D2-1. auth_users ↔ AuthUser 聚合

| SQL 列 | SQL 类型/约束 | Python 属性 | Python 类型 | 匹配结果 |
|--------|-------------|------------|------------|---------|
| id | UUID PRIMARY KEY | id | UUID | ✅ |
| email | TEXT NOT NULL UNIQUE | email | str | ✅ |
| password_hash | TEXT (nullable) | password_hash | Optional[str] | ✅ |
| email_verified | BOOLEAN NOT NULL DEFAULT FALSE | email_verified | bool = False | ✅ |
| email_verified_at | TIMESTAMPTZ | email_verified_at | Optional[datetime] | ✅ |
| otp_code_hash | TEXT | otp_code_hash | Optional[str] | ✅ |
| otp_purpose | TEXT CHECK(enum) | otp_purpose | Optional[str] | ✅ |
| otp_expires_at | TIMESTAMPTZ | otp_expires_at | Optional[datetime] | ✅ |
| otp_attempts | INTEGER NOT NULL DEFAULT 0 | otp_attempts | int = 0 | ✅ |
| password_changed_at | TIMESTAMPTZ | password_changed_at | Optional[datetime] | ✅ |
| failed_login_attempts | INTEGER NOT NULL DEFAULT 0 | failed_login_attempts | int = 0 | ✅ |
| locked_until | TIMESTAMPTZ | locked_until | Optional[datetime] | ✅ |
| last_login_at | TIMESTAMPTZ | last_login_at | Optional[datetime] | ✅ |
| last_login_ip | **INET** | last_login_ip | **Optional[str]** | ⚠️ P3 — 类型差异 |
| is_active | BOOLEAN NOT NULL DEFAULT TRUE | is_active | bool = True | ✅ |
| created_at | TIMESTAMPTZ NOT NULL | created_at | datetime | ✅ |
| updated_at | TIMESTAMPTZ NOT NULL | updated_at | datetime | ✅ |

**结论**: ✅ **16/16 字段完整映射**，1 个 P3 类型差异 (INET→str，Repository 层正确处理)

---

### D2-2. auth_sessions ↔ Session 实体

| SQL 列 | SQL 类型/约束 | Python 属性 | 匹配结果 |
|--------|-------------|------------|---------|
| id | UUID PRIMARY KEY | id: UUID | ✅ |
| user_id | UUID NOT NULL FK | user_id: UUID | ✅ |
| family_id | UUID NOT NULL | family_id: UUID | ✅ |
| refresh_token_hash | TEXT NOT NULL UNIQUE | refresh_token_hash: str | ✅ |
| user_agent | TEXT | user_agent: Optional[str] | ✅ |
| ip_address | **INET** | ip_address: **Optional[str]** | ⚠️ P3 |
| device_name | TEXT | device_name: Optional[str] | ✅ |
| is_revoked | BOOLEAN NOT NULL DEFAULT FALSE | is_revoked: bool = False | ✅ |
| revoked_at | TIMESTAMPTZ | revoked_at: Optional[datetime] | ✅ |
| revoke_reason | TEXT CHECK(IN (...)) | revoke_reason: Optional[str] | ⚠️ P3 — `session_limit_exceeded` 不在 CHECK 中 |
| expires_at | TIMESTAMPTZ NOT NULL | expires_at: datetime | ✅ |
| last_used_at | TIMESTAMPTZ | last_used_at: Optional[datetime] | ✅ |
| created_at | TIMESTAMPTZ NOT NULL | created_at: datetime | ✅ |

**结论**: ✅ **13/13 字段完整映射**，2 个 P3 问题

---

### D2-3. profiles ↔ UserProfile 聚合

> **设计说明**: `profiles` 表有 ~45 列，DDD 设计中 `UserProfile` 聚合只映射身份相关的 ~15 列，其余由专用聚合管理 (`UserCredits`, `SubscriptionInfo` 等)。

**关键发现**:

1. **P2 命名不一致 (`profiles.id` vs `UserProfile.user_id`)**:
   - SQL 表主键: `id UUID PRIMARY KEY`
   - Python 实体: `user_id: str` (str 而非 UUID)

2. **P2 datetime.utcnow() 已废弃**:
   - `UserProfile` 的 `created_at` / `updated_at` 使用 `datetime.utcnow()`
   - Python 3.12+ 已废弃此方法，应改为 `datetime.now(timezone.utc)`

3. **✅ DDD 设计合理**: 积分由 `UserCredits` 管理，订阅由 `SubscriptionInfo` 管理

---

### D2-4. credit_transactions ↔ CreditTransaction + TransactionType

#### TransactionType 枚举不匹配 — **P1 High**

| 来源 | 枚举值数量 | 差异 |
|------|-----------|------|
| **Python enum** | **11 值** | 标准值 |
| **SQL CHECK** | **16 值** | 额外 5 值: `topup_purchase`, `sub_grant`, `monthly_reset`, `marketplace_purchase`, `monthly_credits_cleared` |

**修复建议**: 调研 5 个额外值是否仍在使用，废弃则从 SQL 移除，在用则添加到 Python。

#### tx_type deprecated 字段 — P3

Python 实体仍映射到已废弃的 `tx_type`，未迁移到 `transaction_type`。触发器同步保证功能不受影响。

#### Balance 约束一致性 — ✅

月度积分上限 1,000,000 / 永久积分上限 10,000,000 — SQL 与 Python 完全一致。

---

### D2-5. tags ↔ Tag 实体

✅ **9/9 字段完整匹配**，无问题。

---

### D2-6. projects — 无领域实体 (P2 架构问题)

`projects` 表有 ~40 列，但**没有对应的领域实体**。`project_repository.py` 所有方法直接返回 `dict`。

**修复建议**: 创建 `domains/projects/entities/project.py` 领域实体。

---

### D2-7. 汇总统计

| 分类 | 数量 | 严重等级 |
|------|------|---------|
| **TransactionType 枚举缺失** | 5 值 | **P1** |
| **命名不一致** | 1 | P2 |
| **datetime.utcnow 已废弃** | 2 | P2 |
| **projects 无领域实体** | 1 | P2 |
| **INET vs str / revoke_reason / tx_type** | 4 | P3 |

**D2 维度总计**: **9 项发现** (0 P0 + 1 P1 + 4 P2 + 4 P3)

---

## D3: 索引覆盖

**审计方法**: 从 Python Repository 代码中提取查询模式，与 SQL schema 索引定义交叉比对。

---

### D3-1. 主要查询模式审计

| 表 | 查询模式 | 索引覆盖 |
|----|---------|---------|
| **profiles** | `.eq("email")` | ✅ UNIQUE |
| **profiles** | `.eq("stripe_customer_id")` | ✅ UNIQUE |
| **profiles** | `.or_("email.ilike, username.ilike, user_code.ilike")` | ⚠️ **P2** — 无 trigram 索引 |
| **auth_users** | `.eq("email")` | ✅ UNIQUE |
| **auth_sessions** | `.eq("refresh_token_hash")` | ✅ UNIQUE |
| **auth_sessions** | `.eq("user_id").eq("is_revoked", false).gt("expires_at")` | ✅ 复合索引 |
| **projects** | `.eq("user_id").eq("is_deleted", false).order("updated_at")` | ⚠️ **P3** — 需确认复合索引 |
| **credit_transactions** | `.eq("user_id").order("created_at")` | ⚠️ **P3** — 需确认复合索引 |
| **tags** | `.eq("workspace_id").eq("is_active", true)` | ✅ |
| **marketplace_listings** | 多条件组合 | ✅ RPC 内部优化 |

---

### D3-2. P2 — profiles 模糊搜索无索引

**查询位置**: `user_repository.py:727`

使用 3 个 `ILIKE` 模糊匹配无 trigram 索引，导致全表扫描。

**修复建议**:
```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_profiles_search_trgm
ON profiles USING GIN (
    (email || ' ' || COALESCE(username, '') || ' ' || user_code) gin_trgm_ops
);
```

---

### D3-3. 汇总统计

**D3 维度总计**: **3 项发现** (0 P0 + 0 P1 + 1 P2 + 2 P3)

---

## D4: 安全审计

**审计方法**: 全面审查 SECURITY DEFINER 函数、RLS 策略、动态 SQL、PostgREST 查询构造。

---

### D4-1. SECURITY DEFINER 函数审计 (6 个)

#### 安全函数 (3 个) — ✅

| # | 函数名 | 安全验证 |
|---|--------|---------|
| 1 | `create_pending_auth_user` | ✅ 参数化查询 + `FOR UPDATE` |
| 2 | `create_auth_user_with_profile` | ✅ 幂等性检查 |
| 3 | `restore_auth_user_with_profile` | ✅ 三重验证 |

#### 死代码风险 (2 个) — P2

| # | 函数名 | 风险 |
|---|--------|------|
| 4 | `increment_project_view_count` | ⚠️ 无身份验证，可刷浏览量 |
| 5 | `increment_project_like_count` | ⚠️ 无身份验证，可刷点赞量 |

#### 权限检查问题 (1 个) — P1

| # | 函数名 | 风险 |
|---|--------|------|
| 6 | `is_admin()` | ⚠️ 依赖未设置的会话变量 `app.current_user_role`，永远返回 FALSE |

---

### D4-2. RLS 策略审计

#### 覆盖率: **100%** (78/78 表全部启用 RLS) ✅

所有策略符合最小权限原则，无权限泄漏风险。

#### P3 问题 (3 项):
- **P3-1**: `projects` / `marketplace_listings` 重复 RLS 策略
- **P3-2**: `marketplace_reports` VIEW/TABLE 注释矛盾
- **P3-3**: `is_admin()` 在 RLS 中可能被引用

---

### D4-3. SQL 注入审计

#### SQL 函数动态表名 — P1 x2

`p_start_webhook_processing` / `p_complete_webhook_processing` 接受 `p_table_name TEXT` 参数，无白名单验证。

**修复**: 添加表名白名单 `IN ('stripe_webhook_events', 'clerk_webhook_events')`

#### PostgREST 搜索注入 — P1 x2 + P2 x1

| # | 文件 | 风险 |
|---|------|------|
| 6 | `system_resources_admin_repository.py:88` | ⚠️ **P1** — 未 sanitize |
| 7 | `analytics_events_repository.py:204` | ⚠️ **P2** — 直接 f-string |
| 8 | `feature_flags/repository.py:102` | ⚠️ **P1** — 未 sanitize |

#### Sanitize 实现不一致 — P2

3 种不同实现 (`escape_like_wildcards`, `_sanitize_postgrest_query`, `_escape_or_filter_query`)，行为不一致。

**修复**: 统一提升为全局 `sanitize_postgrest_query()` 函数。

---

### D4-4. 汇总统计

**D4 维度总计**: **10 项发现** (0 P0 + 4 P1 + 3 P2 + 3 P3)

---

## D5: 数据完整性

---

### D5-1. 外键 CASCADE 行为一致性

✅ **所有外键 CASCADE 行为与 Python 代码行为一致**，无数据完整性风险。

### D5-2. 触发器逻辑正确性

✅ 所有触发器逻辑正确。

#### P3 — updated_at 双重更新 (冗余但无害)

多个表同时使用 `update_updated_at_column` 触发器 AND Python 代码手动设置 `updated_at`。功能不受影响，但代码中手动设置是多余的。

### D5-3. 幂等性 Key 覆盖

| 操作 | 幂等性 Key | 唯一约束 | 状态 |
|------|-----------|---------|------|
| 积分扣减 | `credit_transactions.idempotency_key` | UNIQUE 部分索引 | ✅ |
| 积分充值 | `credit_purchases.idempotency_key` | UNIQUE | ✅ |
| Stripe Webhook | `stripe_webhook_events.event_id` | UNIQUE | ✅ |
| **项目创建** | `projects.idempotency_key` | **无唯一索引** | ⚠️ **P1** |

**P1 详细分析**: `projects.idempotency_key` 有字段但无 UNIQUE 约束，无法防止重复创建。

**修复**:
```sql
CREATE UNIQUE INDEX idx_projects_idempotency_key
ON projects (idempotency_key)
WHERE idempotency_key IS NOT NULL;
```

### D5-4. 汇总统计

**D5 维度总计**: **2 项发现** (0 P0 + 1 P1 + 0 P2 + 1 P3)

---

## D6: 一致性模式

---

### D6-1. 分页模式 — ✅ 100% 一致

所有查询统一使用 `offset + limit` 参数，通过 `.range()` 转换。

### D6-2. 软删除模式 — ✅ 100% 一致

`is_deleted + deleted_at` 统一过滤。

### D6-3. 时间戳处理

- SQL + Repository 层: ✅ 一致 (`TIMESTAMPTZ` + `datetime.now(timezone.utc)`)
- Entity 层: ⚠️ UserProfile 使用 `datetime.utcnow()` (已在 D2 记录)

### D6-4. 命名约定 — ✅ 基本一致

除 D2 中记录的 `profiles.id` vs `user_id` 和 `tx_type` vs `transaction_type` 外，命名 100% 一致。

### D6-5. Enum 枚举一致性

- TransactionType: ⚠️ 不一致 (已在 D2-4 记录为 P1)
- UserTier / UserRole / OnboardingStep: ✅ 完全一致

### D6-6. 架构模式评估

| 模式类别 | 评分 |
|----------|------|
| 分页模式 | ⭐⭐⭐⭐⭐ 5/5 |
| 软删除模式 | ⭐⭐⭐⭐⭐ 5/5 |
| 时间戳处理 | ⭐⭐⭐⭐ 4/5 |
| 命名约定 | ⭐⭐⭐⭐ 4/5 |
| 枚举一致性 | ⭐⭐⭐ 3/5 |

**总体评估**: 架构模式一致性 **4.2/5 星**

**D6 维度总计**: **0 项新发现** (所有问题已在其他维度记录)

---

## D7: 硬编码审计

**审计方法**: 检查 SQL RPC 函数和表定义中的硬编码值，评估是否需要参数化或从配置读取。

> 本维度来自 002-sql-hardcoding-audit 中的 P1~P3 项 (非 RPC 参数/返回值问题)。

---

### D7-1. P1 High — 业务逻辑硬编码 (5 项)

#### P1-1: 软删除恢复期 `30 days` 硬编码

**位置**: `01_core_business.sql` — `soft_delete_category_descendants`

```sql
recovery_expires_at = CURRENT_TIMESTAMP + INTERVAL '30 days',
```

**修复**: 添加参数 `p_recovery_days INTEGER DEFAULT 30`

---

#### P1-2: Tier 验证 `('t2', 't3')` 硬编码

**位置**: `01_core_business.sql` — `process_subscription_start`

```sql
IF p_plan NOT IN ('t2', 't3') THEN
```

**修复**: 添加注释标记 `⚠️ TIER_VALIDATION: 新增 tier 时需更新此处`。不改为动态查询 (防御性验证应硬编码)。

---

#### P1-3: `'Deleted User'` 硬编码

**位置**: `01_core_business.sql` — `restore_auth_user_with_profile`

**修复**: 添加注释关联 `⚠️ SYNC_REQUIRED: 与 soft_delete 脱敏逻辑一致`

---

#### P1-4: `cleanup_old_activity_logs` 保留事件类型硬编码

**位置**: `03_infrastructure.sql`

```sql
AND action NOT IN ('user_signup', 'subscription_purchase');
```

**修复**: 添加参数 `p_preserve_actions TEXT[] DEFAULT ARRAY['user_signup', 'subscription_purchase']`

---

#### P1-5: Workspace 邀请过期 `7 days` 硬编码

**位置**: `01_core_business.sql` — `workspace_invitations` 表 DEFAULT

**修复**: DB DEFAULT 保留作为防御兜底，代码层从 `system_configs` 读取覆盖。

---

### D7-2. P2 Medium — 可选优化 (7 项)

| # | 问题 | 位置 | 处理 |
|---|------|------|------|
| P2-1 | 交易描述文本英文硬编码 (8 处) | 多个 RPC 函数 | **暂不修复** — 内部审计记录，前端根据 `transaction_type` 动态生成展示文本 |
| P2-2 | 积分操作上限魔术数字 (`1000000`/`100000`) | `deduct_credits_atomic` 等 | **暂不修复** — 安全防线，远超正常业务 |
| P2-3 | 金额转换 `/100.0` 硬编码 | 订阅/购买 RPC | **暂不修复** — 仅支持 USD，接入零位小数货币时再参数化 |
| P2-4 | `generate_ticket_number` 格式 `'TKT-'` | 触发器 | **暂不修复** — 格式稳定 |
| P2-5 | Campaign 默认时区 `'America/New_York'` | `02_platform_services.sql` | **改为 `'UTC'`** |
| P2-6 | `idempotency_key` 前缀构造 | 多处 | **暂不修复** — 前缀是约定，记录对照表即可 |
| P2-7 | `get_user_creation_stats` 缺 `restore` 统计列 | `01_core_business.sql` | **暂不修复** — 恢复是低频事件 |

**幂等性 Key 前缀对照表**:

| 前缀 | 用途 | 构造方 |
|------|------|--------|
| `sub_start_` | 首次订阅 | DB 函数 |
| `renewal_` | 订阅续费 | Python |
| `credit_purchase_` | 积分购买 | Python |
| `refund_` | 退费 | DB 函数 |

---

### D7-3. P3 Low — 合理默认值 (4 项，无需修改)

| 位置 | 值 | 说明 |
|------|------|------|
| `profiles.tier` | `DEFAULT 't1'` | 新用户默认免费 Tier |
| `profiles.language` | `DEFAULT 'en'` | 合理默认语言 |
| `profiles.timezone` | `DEFAULT 'UTC'` | 标准默认时区 |
| 清理函数 | `DEFAULT 30/180` 天 | 已支持参数覆盖 |

---

### D7-4. 汇总统计

**D7 维度总计**: **16 项发现** (0 P0 + 5 P1 + 7 P2 + 4 P3)

---

## 附录 A: 实施建议

1. **修改 RPC 函数签名后，必须在 staging 数据库执行更新的 SQL**
   - 通过 Supabase Dashboard SQL Editor 执行
   - 或 Railway 部署时手动执行

2. **新参数都使用 `DEFAULT` 值保证向后兼容**
   - P0-3, P0-4, P1-1, P1-4 的新参数都有默认值
   - **但 P0-1 的 `p_old_profile_id` 是必需参数，必须同步修改代码**

3. **P0-1 是最复杂的修复**，涉及 4 层代码修改

4. **修改顺序建议**:
   - **P0-5 优先**: 先修 `create_pending_auth_user` 返回类型 (注册流程正在测试中)
   - 先改 DB SQL 并部署到 staging，再改代码并部署

5. **P0-1 修复方案额外发现**: 当前 DB 恢复 profile 时没有清除 `recovery_expires_at` 字段，修复方案已包含

---

## 附录 B: 复核记录

> 复核日期: 2026-02-02

| # | 类型 | 发现 | 处理 |
|---|------|------|------|
| 1 | **遗漏 (P0)** | `create_pending_auth_user` 标量返回值解析 | 新增 P0-5 |
| 2 | **遗漏 (补充)** | restore 函数未清除 `recovery_expires_at` | 补充到 P0-1 |
| 3 | **遗漏 (P2)** | `get_user_creation_stats` 缺 restore 统计 | 新增 P2-7 |
| 4-7 | **验证通过** | P0-1~P0-4 分析准确 | — |
| 8-9 | **验证通过** | P1/P2 分析正确，无重复/冲突 | — |
| 10-12 | **无冲突/无重复** | 所有 58 项互不重复 | — |
