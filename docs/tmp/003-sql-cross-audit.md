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
| **P1 High** | 0 | 2 | 0 | 3 | 0 | 0 | 5 | **10** |
| **P2 Medium** | 3 | 4 | 1 | 4 | 0 | 0 | 7 | **19** |
| **P3 Low** | 6 | 3 | 2 | 3 | 1 | 0 | 4 | **19** |
| **合计** | **18** | **9** | **3** | **10** | **1** | **0** | **16** | **57** |

> **第二轮复核修正 (2026-02-02)**:
> - D1-4 #4 `soft_delete_category_descendants`: P2→P3 (返回值被忽略，非解析错误)
> - D4 `system_resources_admin_repository.py:88`: P1→P2 (API 层已有 sanitize)
> - D5 `projects.idempotency_key`: P1→移除 (已有复合唯一索引 `user_id + idempotency_key`)
> - D2 TransactionType: Python 10 值 (非 11)，SQL 独有 6 值 (非 5，漏算 `refund_reversal`)
>
> **第三轮复核修正 (2026-02-02 — 解决方案验证)**:
> - D2 `revoke_reason` CHECK: P3→**P1 升级** (Python 使用 `session_limit_exceeded` 但 DB CHECK 不含，写入会失败)
> - C-5 #3 `update_webhook_result`: 表无 `result` 列，修正为使用现有列 `processed`+`error_message`
> - C-1 restore: 补充说明当前 SQL 用 `deleted_at + 30 days` 而 Python 用 `recovery_expires_at`
> - D4 Webhook 白名单: 移除已删除的 `clerk_webhook_events`，仅保留 `stripe_webhook_events`

> **全维度审计已完成**，发现 **57 项独立问题**：
> - **P0 Critical** (9 项): RPC 函数缺失/参数不匹配/返回值解析错误，运行时崩溃
> - **P1 High** (10 项): 枚举缺失、CHECK 约束不匹配、安全注入风险、权限检查失效、业务逻辑硬编码
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

### 第二批: P1 High (10 项) — 建议修复

| 序号 | 来源 | 维度 | 修复内容 | 预估工时 |
|------|------|------|---------|---------|
| 10 | 003 | D2 | TransactionType 枚举同步 (SQL 16 值 vs Python 10 值) | 1h |
| 10b | 003 | D2 | `revoke_reason` CHECK 约束添加 `session_limit_exceeded` | 0.1h |
| 11 | 003 | D4 | 后端设置 `app.current_user_role` 会话变量 | 1h |
| 12 | 003 | D4 | Webhook 处理函数添加表名白名单验证 | 0.5h |
| 13 | 003 | D4 | `system_resources_admin_repository.py:88` Repository 层添加 sanitize (防御纵深，API 层已有) | 0.2h |
| 14 | 003 | D4 | `feature_flags/repository.py:102` 添加 sanitize | 0.2h |
| ~~15~~ | ~~003~~ | ~~D5~~ | ~~`projects.idempotency_key` 添加 UNIQUE 部分索引~~ | ~~已有复合唯一索引，无需修复~~ |
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

**总预估工时**: P0 ~8h + P1 ~4h + P2 ~11h + P3 ~2h = **~25 小时**

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
| 4 | `soft_delete_category_descendants` | `RETURNS INTEGER` | `await .execute()` 未捕获返回值 | 返回值被完全忽略，无法得知操作影响行数 | **P3** (降级: 功能不受影响，仅缺少可观测性) |

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

| # | 函数名 | SQL 位置 | 分析 | 性质 |
|---|--------|---------|------|------|
| 1 | `increment_project_view_count()` | `01_core_business.sql:3682` | 无任何 Python 调用 | 完全死代码 |
| 2 | `increment_project_like_count()` | `01_core_business.sql:3707` | 无任何 Python 调用 | 完全死代码 |
| 3 | `get_dashboard_projects()` | `01_core_business.sql:3233` | Python `project_repository.py` 有同名方法但使用 `.table().select()` 直接查询而非 `.rpc()` | RPC 被直接查询替代 |
| 4 | `get_dashboard_assets()` | `01_core_business.sql:3389` | Python `asset_repository.py` 有同名方法但使用 `.table().select()` 直接查询 | RPC 被直接查询替代 |
| 5 | `get_dashboard_stats()` | `01_core_business.sql:3539` | 同上。注意: 与 `get_user_dashboard_stats()` 是不同函数 | RPC 被直接查询替代 |

**建议**:
- #1, #2: 完全死代码且是 SECURITY DEFINER，**强烈建议删除** (见 D4-1)
- #3~#5: Python 已用直接查询替代 RPC，RPC 函数冗余。确认无前端直接调用后可删除，或保留作为性能优化备用。

---

### D1-6. 汇总统计

| 分类 | 数量 | 严重等级 |
|------|------|---------|
| 缺失 SQL 函数 (代码调用不存在的函数) | **4** | P0 Critical |
| 参数/返回值严重不匹配 (来自 002) | **5** | P0 Critical |
| 返回类型解析错误 (标量 vs 列表) | **3** | P2 Medium |
| 返回值未捕获 | **1** | P3 Low |
| 死 SQL 函数 (无调用方) | **5** | P3 Low |

**D1 维度总计**: **18 项发现** (9 P0 + 0 P1 + 3 P2 + 6 P3)

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
| revoke_reason | TEXT CHECK(IN (...)) | revoke_reason: Optional[str] | ⚠️ **P1 升级** — `session_limit_exceeded` 不在 CHECK 中，写入会被 DB 拒绝 |
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
| **Python enum** | **10 值** | `subscription_grant`, `purchase`, `signup_bonus`, `referral_bonus`, `campaign_reward`, `refund`, `admin_adjustment`, `ai_generation`, `smart_scan`, `expiration` |
| **SQL CHECK** | **16 值** | 额外 6 值: `topup_purchase`, `sub_grant`, `monthly_reset`, `marketplace_purchase`, `monthly_credits_cleared`, `refund_reversal` |

**修复建议**: 调研 6 个额外值是否仍在使用，废弃则从 SQL 移除，在用则添加到 Python。

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
| **INET vs str / tx_type deprecated** | 3 | P3 |
| **revoke_reason CHECK 缺 `session_limit_exceeded`** | 1 | **P1 升级** (DB 拒绝写入) |

**D2 维度总计**: **9 项发现** (0 P0 + 2 P1 + 4 P2 + 3 P3)

> **复核修正**: `revoke_reason` 从 P3 升级为 P1 — Python 定义了 `session_limit_exceeded` 常量并在代码中使用，但 SQL CHECK 约束不包含此值，写入时会抛出 CHECK violation 错误。

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

**修复**: 添加表名白名单 `IN ('stripe_webhook_events')` (注: `clerk_webhook_events` 已删除)

#### PostgREST 搜索注入 — P1 x1 + P2 x2

| # | 文件 | 风险 |
|---|------|------|
| 6 | `system_resources_admin_repository.py:88` | ⚠️ **P2** — API 层已 sanitize，Repository 层缺防御纵深 |
| 7 | `analytics_events_repository.py:204` | ⚠️ **P2** — 直接 f-string |
| 8 | `feature_flags/repository.py:102` | ⚠️ **P1** — 未 sanitize |

#### Sanitize 实现不一致 — P2

3 种不同实现 (`escape_like_wildcards`, `_sanitize_postgrest_query`, `_escape_or_filter_query`)，行为不一致。

**修复**: 统一提升为全局 `sanitize_postgrest_query()` 函数。

---

### D4-4. 汇总统计

**D4 维度总计**: **10 项发现** (0 P0 + 3 P1 + 4 P2 + 3 P3)

> **复核修正**: `system_resources_admin_repository.py:88` 从 P1 降为 P2 (API 层已有 sanitize)。

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
| **项目创建** | `projects.idempotency_key` | ✅ 复合唯一索引 `(user_id, idempotency_key)` | ✅ (用户级幂等) |

**说明**: `projects` 已有复合唯一索引 `idx_projects_user_idempotency_key ON projects(user_id, idempotency_key) WHERE idempotency_key IS NOT NULL AND is_deleted = false`。这是用户级幂等性保护 — 不同用户可以有相同的 key，同一用户不能重复。这是合理的设计。

### D5-4. 汇总统计

**D5 维度总计**: **1 项发现** (0 P0 + 0 P1 + 0 P2 + 1 P3)

> **复核修正**: `projects.idempotency_key` 已有复合唯一索引 `(user_id, idempotency_key)`，原 P1 误判已移除。

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
| 10-12 | **无冲突/无重复** | 所有 57 项互不重复 | — |

### 第二轮复核 (深度交叉验证)

> 复核日期: 2026-02-02 (审计报告合并后)
> 复核方法: 逐条对照实际代码文件验证审计声明的准确性

| # | 类型 | 发现 | 处理 |
|---|------|------|------|
| 1 | **数据修正** | TransactionType: Python 实际 10 值 (非 11)，SQL 独有 6 值 (非 5，漏算 `refund_reversal`) | 修正 D2-4 + E-7 |
| 2 | **误判修正** | `projects.idempotency_key` 已有复合唯一索引 `(user_id, idempotency_key)` | D5 P1→移除，修正 E-3 |
| 3 | **降级修正** | `system_resources_admin_repository.py:88` API 层已有 `sanitize_search()` | D4 P1→P2，修正 D-3 |
| 4 | **描述修正** | `soft_delete_category_descendants` 实际是返回值未捕获 (非标量解析错误) | D1-4 #4 P2→P3 |
| 5 | **精确化** | D1-5 死函数: 区分 "完全死代码" (#1,#2) 和 "被直接查询替代的 RPC" (#3-#5) | 补充性质列 |
| 6 | **方案补充** | C-1 restore 方案缺少旧 auth_users 记录清理步骤 | 新增步骤 3: DELETE 旧记录 |
| 7 | **字段名修正** | D-3 #6 实际搜索字段是 `description` 不是 `type` | 修正代码片段 |
| 8 | **统计修正** | Executive Summary 表更新: P1 11→9, P2 19→19, P3 19→20, 总计 58→57 | 修正统计表 |

### 第三轮复核 (解决方案验证)

> 复核日期: 2026-02-02 (逐条验证每个解决方案的正确性、完整性、无副作用)
> 复核方法: 读取每个问题涉及的实际代码文件，验证修复方案是否可直接应用

| # | 类型 | 发现 | 处理 |
|---|------|------|------|
| 1 | **升级 (P3→P1)** | `revoke_reason` CHECK 缺 `session_limit_exceeded`，Python 代码使用此值但 DB 会拒绝写入 | 升级为 P1，添加到优先队列 |
| 2 | **方案修正** | C-5 #3 `update_webhook_result`: `stripe_webhook_events` 表无 `result` 列和 `updated_at` 列 | 修正为使用现有列 `processed`+`error_message` |
| 3 | **方案补充** | C-1 restore: 当前 SQL 用 `deleted_at + 30 days` 而 Python `get_restorable_by_email()` 用 `recovery_expires_at` | 补充说明不一致性，修复方案已统一为 `recovery_expires_at` |
| 4 | **方案修正** | D4 Webhook 白名单误含已删除的 `clerk_webhook_events` | 修正为仅含 `stripe_webhook_events` |
| 5 | **验证通过** | C-1 restore: `get_restorable_by_email` 方法已存在 (auth_user_repository.py:104) | 修复方案可直接使用 |
| 6 | **验证通过** | C-1 restore: `recovery_expires_at` 列已存在于 profiles 表 (01_core_business.sql:164) | 修复方案正确引用 |
| 7 | **验证通过** | P0-3/P0-4 DEFAULT 参数: 不影响现有调用 | 向后兼容 ✅ |
| 8 | **验证通过** | P0-5 RETURNS TABLE: PostgREST 返回格式将匹配 Python 解析 | 修复方案正确 ✅ |
| 9 | **验证通过** | D1-1 #1 `create_user_idempotent`: `generation_tasks` 表存在 (01_core_business.sql:1147) | 参考签名可用 ✅ |
| 10 | **验证通过** | P1 `is_admin()`: 无 RLS 策略引用此函数，可安全删除 | 删除方案安全 ✅ |
| 11 | **统计修正** | P1 9→10, P3 20→19 (revoke_reason 升级) | 修正统计表 |

---

## 附录 C: P0 详细修复方案代码

> 本附录包含所有 P0 Critical 问题的完整修复代码，供实施时直接参考。

---

### C-1. P0-1: `restore_auth_user_with_profile` 完整重写

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

#### 步骤 1: 修改 DB 函数 (`01_core_business.sql`)

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
    -- 1. 查询可恢复的 profiles 记录
    -- ✅ 改用 recovery_expires_at (profiles 表 line 164 已有此列)
    -- ❌ 当前 SQL 用 deleted_at > now() - INTERVAL '30 days'，与 Python 的 get_restorable_by_email() 不一致
    --    Python (auth_user_repository.py:119) 用 .gt("recovery_expires_at", now)
    SELECT id, email, display_name, deleted_at, is_deleted, recovery_expires_at
        INTO v_profile
        FROM profiles
       WHERE id = p_old_profile_id
         AND is_deleted = true
         AND recovery_expires_at > CURRENT_TIMESTAMP  -- ✅ 与 Python 层一致
         FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'RESTORE_NOT_FOUND: profile % not found or not restorable', p_old_profile_id;
    END IF;

    -- 2. 确认邮箱匹配
    IF v_profile.email <> LOWER(TRIM(p_email)) THEN
        RAISE EXCEPTION 'RESTORE_EMAIL_MISMATCH: email does not match profile record';
    END IF;

    -- 3. 清理可能残留的 auth_users 记录 (软删除只标记 profiles，auth_users 可能仍存在)
    DELETE FROM auth_users WHERE id = p_old_profile_id;

    -- 4. 创建新的 auth_users 记录（复用旧 UUID）
    INSERT INTO auth_users (id, email, password_hash, email_verified, email_verified_at, created_at, updated_at)
    VALUES (p_old_profile_id, LOWER(TRIM(p_email)), p_password_hash, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    RETURNING * INTO v_auth_user;

    -- 5. 恢复 profiles 记录
    v_restored_name := COALESCE(p_display_name, v_profile.display_name);
    -- ⚠️ SYNC_REQUIRED: 此值必须与账户删除脱敏逻辑中的占位符一致
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

    -- 6. 记录恢复事件 (source 改为参数)
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

    -- 7. 返回结果 (与 create_auth_user_with_profile 风格统一)
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

#### 步骤 2: 修改 Repository 接口 (`domains/auth/repository.py`)

```python
@abstractmethod
async def restore_account(
    self,
    profile_id: UUID,       # 新增: 待恢复的 profile ID
    email: str,
    password_hash: str,
) -> AuthUser:
    """Restore a soft-deleted account via RPC."""
```

#### 步骤 3: 修改 Repository 实现 (`infrastructure/repositories/auth_user_repository.py`)

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

#### 步骤 4: 修改 Service 层 (`domains/auth/service.py`)

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

#### 步骤 5: 修改测试文件

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

### C-2. P0-3: 订阅 RPC 添加 `p_payment_method` 参数

#### `process_subscription_start` (`01_core_business.sql`)

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

函数体中将硬编码 `'card'` 替换为 `p_payment_method`。

#### `process_subscription_renewal` (`01_core_business.sql`)

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

函数体中将硬编码 `'card'` 替换为 `p_payment_method`。

**代码层**: 无需修改。新参数有 `DEFAULT 'card'`，现有调用兼容。

---

### C-3. P0-4: `create_auth_user_with_profile` 添加 `p_created_by`

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
-- profiles INSERT 的 created_by 字段:
p_created_by,                  -- 替换 'register'

-- user_creation_logs INSERT 的 source 字段:
p_created_by,                  -- 替换 'register'
```

**代码层**: 无需修改。将来 OAuth 注册可传 `'oauth'`，Admin 创建可传 `'admin'`。

---

### C-4. P0-5: `create_pending_auth_user` 返回值修复

#### 方案 B (推荐): 修改 DB 函数返回 TABLE

```sql
CREATE OR REPLACE FUNCTION create_pending_auth_user(...)
RETURNS TABLE(user_id UUID)     -- 改为 TABLE (原为 RETURNS UUID)
...
    -- 场景 1: 新建用户
    RETURN QUERY SELECT v_user_id;       -- 替换 RETURN v_user_id

    -- 场景 2: 已存在待验证用户
    RETURN QUERY SELECT v_existing.id;   -- 替换 RETURN v_existing.id

    -- 场景 3: 已注册用户
    RETURN QUERY SELECT NULL::UUID;      -- 替换 RETURN NULL
```

这样 PostgREST 返回格式变为 `[{"user_id": "xxx"}]`，代码的 `row.get("user_id")` 就能正确工作。

#### 方案 A (备选): 修改代码适配标量返回

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

---

### C-5. D1-1 缺失函数补建参考签名

#### #1 `create_user_idempotent` (用户注册核心)

```sql
-- 建议放在 01_core_business.sql
CREATE OR REPLACE FUNCTION create_user_idempotent(
    p_user_id UUID,
    p_email TEXT,
    p_source TEXT DEFAULT 'register',
    p_username TEXT DEFAULT NULL,
    p_first_name TEXT DEFAULT NULL,
    p_last_name TEXT DEFAULT NULL,
    p_avatar_url TEXT DEFAULT NULL,
    p_display_name TEXT DEFAULT NULL,
    p_signup_bonus INT DEFAULT 0
)
RETURNS TABLE(
    user_profile JSONB,
    was_created BOOLEAN,
    created_by TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = 'public'
AS $$
-- 实现: 幂等创建用户 + profile
-- 如果用户已存在，返回已有记录 + was_created=false
-- 如果用户不存在，创建新记录 + was_created=true
-- 需要参考 create_auth_user_with_profile 的实现模式
BEGIN
    -- TODO: 实现幂等逻辑
    -- 1. 检查 profiles 表是否已存在 p_user_id
    -- 2. 如果存在，返回已有记录
    -- 3. 如果不存在，创建 profiles + 发放 signup_bonus
    RAISE EXCEPTION 'TODO: implement create_user_idempotent';
END;
$$;
```

#### #2 `create_generation_task` (AI 生成任务)

```sql
-- 建议放在 02_platform_services.sql
CREATE OR REPLACE FUNCTION create_generation_task(
    p_task_id UUID,
    p_user_id UUID,
    p_task_type TEXT,
    p_params JSONB DEFAULT '{}'::JSONB,
    p_priority INT DEFAULT 0,
    p_total_steps INT DEFAULT 1
)
RETURNS VOID
LANGUAGE plpgsql
SET search_path = 'public'
AS $$
BEGIN
    INSERT INTO generation_tasks (id, user_id, task_type, params, priority, total_steps, status, created_at)
    VALUES (p_task_id, p_user_id, p_task_type, p_params, p_priority, p_total_steps, 'pending', CURRENT_TIMESTAMP);
END;
$$;
```

#### #3 `update_webhook_result` (Webhook 结果记录)

> ⚠️ **注意**: `stripe_webhook_events` 表当前没有 `result` 列和 `updated_at` 列。
> 需先 ALTER TABLE 添加列，或改用现有列存储结果。

```sql
-- 方案 A (推荐): 添加列后创建函数
-- 先在 02_platform_services.sql 的 stripe_webhook_events 表定义中添加:
--   result JSONB,
--   updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP

-- 建议放在 03_infrastructure.sql
CREATE OR REPLACE FUNCTION update_webhook_result(
    p_event_id TEXT,
    p_result JSONB
)
RETURNS VOID
LANGUAGE plpgsql
SET search_path = 'public'
AS $$
BEGIN
    UPDATE stripe_webhook_events
    SET processed = TRUE,
        processed_at = CURRENT_TIMESTAMP,
        error_message = CASE
            WHEN (p_result->>'success')::boolean = false THEN p_result->>'error'
            ELSE NULL
        END
    WHERE event_id = p_event_id;
END;
$$;

-- 方案 B (替代): 使用现有列 (不需要 ALTER TABLE)
-- 将 result JSON 存入 error_message (不理想但可用)
```

#### #4 `get_event_stats_by_type` 等 (事件统计)

```sql
-- 建议放在 02_platform_services.sql
-- 需要根据 events_repository.py 中的 function_map 确认所有需要的函数名
-- 示例:
CREATE OR REPLACE FUNCTION get_event_stats_by_type(
    p_start_date TIMESTAMPTZ,
    p_end_date TIMESTAMPTZ
)
RETURNS TABLE(
    event_type TEXT,
    count BIGINT
)
LANGUAGE plpgsql
SET search_path = 'public'
AS $$
BEGIN
    RETURN QUERY
    SELECT ae.event_type, COUNT(*)::BIGINT
    FROM analytics_events ae
    WHERE ae.created_at BETWEEN p_start_date AND p_end_date
    GROUP BY ae.event_type
    ORDER BY count DESC;
END;
$$;
```

---

## 附录 D: D4 安全审计详细分析

> 本附录包含 D4 安全审计中每个问题的完整代码片段和修复方案。

---

### D-1. SECURITY DEFINER 函数详细审计

#### 安全函数验证详情 (3 个)

| # | 函数名 | SQL 位置 | search_path | 安全验证 |
|---|--------|---------|------------|---------|
| 1 | `create_pending_auth_user` | `01_core_business.sql:2026` | ✅ `'public'` | ✅ 参数化查询 + `FOR UPDATE` 防并发 |
| 2 | `create_auth_user_with_profile` | `01_core_business.sql:2091` | ✅ `'public'` | ✅ 幂等性检查 (`password_hash IS NOT NULL`) |
| 3 | `restore_auth_user_with_profile` | `01_core_business.sql:2219` | ✅ `'public'` | ✅ `FOR UPDATE` + 邮箱验证 + 30 天时间窗口检查 |

**验证详情**:
- ✅ 全部设置 `SET search_path = 'public'`，防止 search_path 注入攻击
- ✅ 无动态 SQL (`EXECUTE`)，全部使用参数化操作
- ✅ `create_pending_auth_user`: 使用 `SELECT ... FOR UPDATE` 防止并发竞态条件
- ✅ `create_auth_user_with_profile`: 通过 `password_hash IS NOT NULL` 检查实现幂等性
- ✅ `restore_auth_user_with_profile`: 三重验证 (`FOR UPDATE` + 邮箱匹配 + `deleted_at > NOW() - INTERVAL '30 days'`)
- ✅ 异常处理: 错误时写入 `system_error_logs`，带 `EXCEPTION` 块保护

#### 死代码 SECURITY DEFINER 详细风险 (P2)

| # | 函数名 | SQL 位置 | search_path | 风险 |
|---|--------|---------|------------|------|
| 4 | `increment_project_view_count` | `01_core_business.sql:3701` | ✅ `'public'` | ⚠️ 无调用者身份验证，任何人可无限刷浏览量 |
| 5 | `increment_project_like_count` | `01_core_business.sql:3727` | ✅ `'public'` | ⚠️ 无调用者身份验证，任何人可无限刷点赞量 |

**风险分析**:
- 已在 D1-2 中标记为死代码 (无 Python 调用方)
- 但作为 SECURITY DEFINER 存在，任何知道 `project_id` 的人都可以通过 PostgREST 直接调用
- 无身份验证、无频率限制

**修复建议**:
1. **最佳方案**: 删除这两个死代码函数
2. **保留方案**: 移除 `SECURITY DEFINER` 属性
3. **加固方案**: 添加身份验证 + 频率限制

#### `is_admin()` 权限检查失效详细分析 (P1)

```sql
-- SQL 函数定义
CREATE OR REPLACE FUNCTION is_admin()
RETURNS BOOLEAN AS $$
BEGIN
    RETURN (current_setting('app.current_user_role', true) = 'admin');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = 'public';
```

**问题**: 在整个 Python 后端代码中**未找到**设置 `app.current_user_role` 会话变量的代码。`is_admin()` 永远返回 FALSE。

**修复方案 A (推荐)**: 后端设置会话变量

```python
# 在 dependencies.py 或 supabase_client.py 中
async def set_user_role_session(user_id: str):
    role = await get_user_role(user_id)
    await supabase.rpc("set_config", {
        "setting_name": "app.current_user_role",
        "new_value": role,
        "is_local": True
    })
```

**修复方案 B**: 删除 `is_admin()` 函数，使用 Python 层权限检查代替。

---

### D-2. RLS 策略详细验证

#### 覆盖率统计

| 指标 | 数值 | 说明 |
|------|------|------|
| **总表数** | **78** | 3 个 SQL schema 文件中全部表 |
| **启用 RLS 的表** | **78** | 100% 覆盖 ✅ |
| **未启用 RLS 的表** | **0** | 无遗漏 ✅ |

#### 详细策略验证 (按业务模块)

| 模块 | 表 | 核心策略 | 验证结果 |
|------|----|---------|---------|
| **认证系统** | `auth_users`, `auth_sessions`, `auth_oauth_accounts` | `service_role_full_access` (所有操作) | ✅ 安全 — 认证数据仅后端可访问 |
| **用户档案** | `profiles` | `service_role_all` + `auth_user_own_profile (id = auth.uid())` | ✅ 安全 — 用户可查看自己的档案 |
| **项目管理** | `projects` | `service_role_all` + `auth_user_own_projects (user_id = auth.uid())` + 额外 owner 策略 | ✅ 安全（但有重复策略 P3） |
| **素材管理** | `assets` | `service_role_all` + `auth_user_own_assets (user_id = auth.uid())` | ✅ 安全 |
| **积分系统** | `credit_transactions` | `service_role_all` + `auth_user_own_credit_transactions (FOR SELECT only)` | ✅ 安全 — 用户只读 |
| **订阅系统** | `stripe_subscriptions`, `subscription_history` | `service_role_all` only | ✅ 安全 — 仅后端可访问 |
| **市场功能** | `marketplace_listings` | service_role 全量 + 公开读取 approved + 卖家管理自己的 | ✅ 安全 — 三层访问控制 |
| **市场交易** | `marketplace_purchases` | `service_role_all` + `buyer_own_purchases` | ✅ 安全 |
| **用户收藏** | `marketplace_favorites` | `service_role_all` + `user_own_favorites` | ✅ 安全 |
| **举报系统** | `marketplace_reports` | `service_role_all` + `reporter_own_reports` | ✅ 安全（有注释矛盾 P3） |

#### P3 问题详细分析

**P3-1: 重复 RLS 策略**

| 表 | 问题 | 文件位置 | 说明 |
|----|----|---------|------|
| `projects` | 两组策略定义相同功能 | `01_core_business.sql` (L3650) + `03_infrastructure.sql` (L1700) | `projects_owner_policy` + `projects_service_role_policy` 与 `auth_user_own_projects` + `service_role_all` 功能重复 |
| `marketplace_listings` | 同上 | `01_core_business.sql` (L4200) + `03_infrastructure.sql` (L1750) | 详细策略 + `service_role_all` 重复 |

**影响**: PostgreSQL 会 OR 合并多个策略，功能不受影响，但增加维护混乱。

**修复**: 删除 `03_infrastructure.sql` 中的简化策略，保留 `01_core_business.sql` 中的详细策略。

**P3-2: `marketplace_reports` 注释矛盾**

```sql
-- 03_infrastructure.sql L1740
-- marketplace_reports 是视图 (VIEW)，不是表，不需要启用 RLS

-- 但在 01_core_business.sql L4128
ALTER TABLE marketplace_reports ENABLE ROW LEVEL SECURITY;
CREATE POLICY reporter_own_reports ON marketplace_reports ...
```

**修复**: 确认实际对象类型，如果是视图则删除 RLS 语句，如果是表则修正注释。

---

### D-3. SQL 注入详细审计

#### Webhook 处理函数表名注入风险 (P1)

```sql
-- 问题代码示例
CREATE OR REPLACE FUNCTION p_start_webhook_processing(
    p_event_id TEXT,
    p_table_name TEXT  -- 攻击面: 调用方传入任意表名
)
...
BEGIN
    EXECUTE format('UPDATE %I SET processing_status = ''processing'' WHERE event_id = $1', p_table_name)
    USING p_event_id;
END;
```

**风险**: 虽然 `%I` 防止语法注入，但可传入任意表名修改不该修改的表。

**当前缓解措施**: 后端调用时表名硬编码为 `'stripe_webhook_events'`。

**修复** (防御纵深):
```sql
-- 在函数内添加表名白名单验证
-- 注意: clerk_webhook_events 已删除 (迁移到自建认证系统)，仅保留 stripe
IF p_table_name NOT IN ('stripe_webhook_events') THEN
    RAISE EXCEPTION 'Invalid table name: %', p_table_name;
END IF;
```

#### PostgREST 搜索注入详细分析

**完整审计结果**:

| # | 文件 | 行号 | 代码片段 | 风险级别 |
|---|------|------|---------|---------|
| 1 | `user_repository.py` | 727 | `.or_(f"email.ilike.%{safe_query}%,username.ilike.%{safe_query}%")` | ✅ 安全 — 使用 `escape_like_wildcards()` |
| 2 | `project_repository.py` | 425, 534, 686 | `.ilike("title", f"%{safe_query}%")` | ✅ 安全 — 使用 `escape_like_wildcards()` |
| 3 | `listing_repository.py` | 309 | `.or_(f"title.ilike.%{sanitized}%,...")` | ✅ 安全 — 使用 `_sanitize_postgrest_query()` |
| 4 | `article_repository.py` | 317 | `.or_(f"title.ilike.{search_pattern}...")` | ✅ 安全 — 使用 `_escape_or_filter_query()` |
| 5 | `asset_repository.py` | 482, 525 | `.ilike("name", f"%{escaped}%")` | ✅ 安全 — 使用 `escape_like_wildcards()` |
| 6 | **`system_resources_admin_repository.py`** | **88** | `.or_(f"name.ilike.%{search}%,description.ilike.%{search}%")` | ⚠️ **P2** (API 层已 sanitize，但 Repository 层缺防御纵深) |
| 7 | **`analytics_events_repository.py`** | **204** | `.or_(f'id.eq.{event_id},event_id.eq.{event_id}')` | ⚠️ **P2** |
| 8 | **`feature_flags/repository.py`** | **102** | `.or_(f"key.ilike.%{search}%,name.ilike.%{search}%")` | ⚠️ **P1** |

**#6 `system_resources_admin_repository.py:88` 详细修复** (P2 — 降级，API 层已 sanitize):

```python
# 问题代码
async def list_resources(search: str):
    # Search query is pre-sanitized by API layer  <- 注释正确: api/user/system_resources.py:87 有 sanitize_search()
    query = supabase.table("system_resources").select("*")
    if search:
        query = query.or_(f"name.ilike.%{search}%,description.ilike.%{search}%")

# 当前缓解: API 层 sanitize_search() 已移除 %, _, \ 字符
# 修复 (防御纵深): Repository 层也应自行 sanitize
from core.validators.input_validator import sanitize_postgrest_query
safe_search = sanitize_postgrest_query(search)
query = query.or_(f"name.ilike.%{safe_search}%,description.ilike.%{safe_search}%")
```

> **复核修正**: 原报告标为 P1 且注释称"无保证"，实际 API 层 `api/user/system_resources.py:87-90` 定义了 `sanitize_search()` 并在 line 197 调用。攻击路径已被阻断。降级为 P2 (防御纵深建议)。

**#7 `analytics_events_repository.py:204` 详细修复** (P2):

```python
# 问题代码
query = query.or_(f'id.eq.{event_id},event_id.eq.{event_id}')

# 修复: 使用参数化方式
query = query.filter("id", "eq", event_id).filter("event_id", "eq", event_id)
```

**#8 `feature_flags/repository.py:102` 详细修复** (P1):

```python
# 问题代码
query = query.or_(f"key.ilike.%{search}%,name.ilike.%{search}%")

# 修复
from core.validators.input_validator import sanitize_postgrest_query
safe_search = sanitize_postgrest_query(search)
query = query.or_(f"key.ilike.%{safe_search}%,name.ilike.%{safe_search}%")
```

#### Sanitize 实现不一致详细对比

| 函数名 | 位置 | 转义字符 | 适用场景 |
|--------|------|---------|---------|
| `escape_like_wildcards()` | `core/validators/input_validator.py` | `%`, `_`, `\\` | ILIKE 模式匹配 |
| `_sanitize_postgrest_query()` | `listing_repository.py` | `,`, `.`, `(`, `)`, `*`, `%`, `_` | PostgREST filter 结构 + ILIKE |
| `_escape_or_filter_query()` | `article_repository.py` | 先 strip `,`, `.`, `(`, `)`, 再调用 `sanitize_postgrest_query` | PostgREST `.or_()` 上下文 |

**上下文安全区别**:

```python
# 场景 1: .ilike() 方法参数 — escape_like_wildcards() 足够
query = query.ilike("title", f"%{escape_like_wildcards(search)}%")  # ✅ 安全

# 场景 2: .or_() 字符串拼接 — 需要 sanitize_postgrest_query()
query = query.or_(f"title.ilike.%{escape_like_wildcards(search)}%,...")  # ⚠️ 不够
query = query.or_(f"title.ilike.%{sanitize_postgrest_query(search)}%,...")  # ✅ 安全
```

**统一修复方案**:
1. 将 `listing_repository.py` 中的 `_sanitize_postgrest_query()` 提升为 `core/validators/input_validator.py` 全局函数
2. 所有在 `.or_()` 中使用 f-string 的代码统一使用 `sanitize_postgrest_query()`
3. `.ilike()` 方法参数可继续使用 `escape_like_wildcards()` (supabase-py 自动处理)

---

## 附录 E: D5/D6 详细验证过程

> 本附录包含数据完整性和一致性模式的逐条验证结果。

---

### E-1. 外键 CASCADE 行为逐条验证

| FK 关系 | CASCADE 行为 | Python 代码行为 | 一致性 |
|---------|-------------|----------------|--------|
| auth_sessions.user_id → auth_users(id) | ON DELETE CASCADE | ✅ `delete()` 方法删除 auth_users，sessions 自动级联删除 | ✅ |
| projects.user_id → profiles(id) | ON DELETE CASCADE | ✅ 软删除 profiles (is_deleted=true) 不触发 CASCADE | ✅ |
| assets.user_id → profiles(id) | ON DELETE CASCADE | ✅ 同上 | ✅ |
| tags.workspace_id → workspaces(id) | ON DELETE CASCADE | ✅ 删除 workspace 级联删除 tags | ✅ |
| folders.workspace_id → workspaces(id) | ON DELETE CASCADE | ✅ 删除 workspace 级联删除 folders | ✅ |
| projects.folder_id → folders(id) | ON DELETE SET NULL | ✅ 删除文件夹不影响项目，folder_id 置为 NULL | ✅ |
| projects.workspace_id → workspaces(id) | ON DELETE SET NULL | ✅ 向后兼容设计 | ✅ |

---

### E-2. 触发器逻辑逐条验证

#### 已验证正确的触发器

| 触发器 | 表 | 功能 | 正确性验证 |
|--------|---|------|-----------|
| `update_updated_at_column` | ~12 个表 | 自动更新 updated_at | ✅ 标准模式 |
| `sync_credit_transaction_type` | credit_transactions | 双向同步 tx_type ↔ transaction_type | ✅ 双写逻辑正确 |
| `sync_notification_type` | notifications | 同步通知类型 | ✅ |
| `generate_ticket_number` | support_tickets | 自动生成工单号 | ✅ 使用序列生成 |
| `set_deleted_at_on_soft_delete` | 多个表 | is_deleted=true 时自动设置 deleted_at | ✅ |

#### updated_at 双重更新详细分析 (P3)

**示例 1 — 无触发器的表 (正确)**:
```python
# auth_user_repository.py:update_otp()
await supabase.table("auth_users").update({
    "otp_code_hash": hash_value,
    "otp_expires_at": expires_at,
    "updated_at": datetime.now(timezone.utc).isoformat()  # 手动设置 (正确，auth_users 无触发器)
}).eq("id", user_id).execute()
```

**示例 2 — 有触发器的表 (冗余)**:
```python
# workspaces_repository.py
await supabase.table("workspaces").update({
    "name": new_name,
    "updated_at": datetime.now(timezone.utc).isoformat()  # 手动设置 (冗余，触发器会覆盖)
}).eq("id", workspace_id).execute()
# workspaces 表同时有 update_updated_at_column 触发器
```

**修复建议**: 删除有触发器的表的 Python 代码中冗余的 `updated_at` 手动设置。

---

### E-3. 幂等性 Key 覆盖完整验证

| 操作 | 幂等性 Key 字段 | 唯一索引/约束 | 覆盖情况 |
|------|---------------|-------------|---------|
| **积分扣减** | `credit_transactions.idempotency_key` | `idx_credit_transactions_idempotency_key UNIQUE (WHERE idempotency_key IS NOT NULL)` | ✅ 完全覆盖 |
| **积分充值** | `credit_purchases.idempotency_key` | `idempotency_key TEXT UNIQUE` | ✅ 完全覆盖 |
| **Stripe Webhook 处理** | `stripe_webhook_events.event_id` | `stripe_webhook_events(event_id) UNIQUE` | ✅ 完全覆盖 |
| **项目创建** | `projects.idempotency_key` | ✅ 复合唯一索引 `(user_id, idempotency_key)` | ✅ |

**projects.idempotency_key 分析** (复核修正):

```sql
-- SQL 定义 (01_core_business.sql)
CREATE UNIQUE INDEX IF NOT EXISTS idx_projects_user_idempotency_key
ON projects(user_id, idempotency_key)
WHERE idempotency_key IS NOT NULL AND is_deleted = false;
```

已有用户级复合唯一索引。同一用户的相同 `idempotency_key` 会被数据库拒绝 (UNIQUE violation)。不同用户可以有相同 key，这是合理的设计。

**原报告误判原因**: 搜索了 `idempotency_key` 的单列 UNIQUE 约束而非复合索引。

---

### E-4. 分页模式验证

所有 Repository 统一使用 `offset + limit`:

```python
# 标准分页模式 (所有 Repository 共用)
def get_projects(user_id: str, offset: int, limit: int):
    result = await supabase.table("projects") \
        .select("*") \
        .eq("user_id", user_id) \
        .eq("is_deleted", False) \
        .order("updated_at", desc=True) \
        .range(offset, offset + limit - 1) \
        .execute()
```

✅ 100% 一致，无 `page + limit` 旧模式。

---

### E-5. 软删除模式验证

```python
# 标准软删除过滤 (所有需要的查询都使用)
query = supabase.table("projects") \
    .select("*") \
    .eq("user_id", user_id) \
    .eq("is_deleted", False)  # 统一过滤

# 软删除操作
await supabase.table("projects").update({
    "is_deleted": True,
    "deleted_at": datetime.now(timezone.utc).isoformat()
}).eq("id", project_id).execute()
```

✅ 100% 一致。

---

### E-6. 时间戳处理对比

```python
# ✅ 正确模式 (Repository 层 — 大部分代码使用)
from datetime import datetime, timezone
created_at = datetime.now(timezone.utc).isoformat()  # 带时区信息

# ❌ 已废弃模式 (Entity 层 — UserProfile 使用)
from datetime import datetime
created_at = datetime.utcnow()  # Python 3.12+ 已废弃，无时区信息
```

```sql
-- SQL 层统一模式
created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
```

---

### E-7. Enum 枚举完整对比

| 枚举类型 | SQL CHECK 约束 | Python Enum | 一致性 |
|----------|--------------|------------|--------|
| **TransactionType** | 16 值 | 10 值 | ⚠️ **P1** — 缺少 6 值 |
| **UserTier** | `CHECK (tier IN ('t1', 't2', 't3', 't4'))` | `TIER_T1`, `TIER_T2`, `TIER_T3` | ✅ |
| **UserRole** | `CHECK (role IN ('user', 'admin', 'staff'))` | `USER`, `ADMIN`, `STAFF` | ✅ |
| **OnboardingStep** | `CHECK (onboarding_step IN (...))` | Python enum | ✅ |
| **SessionRevokeReason** | `CHECK (revoke_reason IN ('logout','rotation','security','admin','account_deleted'))` | Python 有 6 值 (含 `session_limit_exceeded`) | ⚠️ **P1 升级** — `session_limit_exceeded` 不在 CHECK 中，DB 写入会失败 |

**TransactionType 差异详情**:

| SQL 独有值 | 可能对应 | 状态 |
|-----------|---------|------|
| `topup_purchase` | 旧版充值 (现用 `purchase`) | 待确认是否废弃 |
| `sub_grant` | 缩写 (现用 `subscription_grant`) | 待确认是否废弃 |
| `monthly_reset` | 月度积分重置 (现用 `subscription_grant`?) | 待确认 |
| `marketplace_purchase` | 市场购买 | 功能未上线? |
| `monthly_credits_cleared` | 月度积分清零 | 功能未上线? |
| `refund_reversal` | 退款撤回 | 功能未上线? |
