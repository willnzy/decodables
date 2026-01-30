# 支付系统 50 个审计问题 — 重构式修复方案 (v3.0)

**创建日期**: 2026-01-30
**关联审计报告**: `docs/tmp/20260130-payment-audit-report.md`
**状态**: 待讨论确认
**版本历史**: v1.0 初版 → v2.0 补全 6 个遗漏问题 → v3.0 架构合规修正 → v3.1 代码探查确认 + WS7 拆分 + 消除待确认项 → v3.2 代码兼容性验证 (10 个矛盾点修正) → v3.3 深度审计 (7 个新发现修正) → v3.4 二轮审计 (6 个新发现修正) → v3.5 三轮审计 (7 个新发现: 并发/幂等/配置)

---

## 零、全局性修正 (v3.0 新增)

### G1. 测试规划 — 每个 WS 必须包含测试

CLAUDE.md 规定: "代码改动 = 业务代码 + 测试代码 (缺一不可)"。

每个 WS 的验证部分增加具体测试项。新 RPC / 新 handler / 新 API 端点必须有对应测试。

### G2. DDD 层级修复 — stripe_webhook_service.py 直接 table() 调用

**现状**: `stripe_webhook_service.py` 存在多处直接 `self.db_client.table("profiles")` 调用，绕过 Repository 层。

**项目规范**: `API → Service → Repository (非 API → Repository)`

**修复策略**: 在 WS2 中，将所有直接 `table()` 调用迁移到对应的 Repository 方法中：

**`table("activity_logs")` 直接插入 — 共 9 处**:
- `stripe_webhook_service.py`: 5 处 (lines 306, 427, 583, 700, 777)
- `clerk_webhook_service.py`: 4 处 (lines 182, 343, 385, 416)
- 迁移到: 新增 `ActivityLogRepository.log_activity()` 方法

**`table("profiles")` 直接操作 — 共 5 处** (v3.3 补充精确位置):
- `stripe_webhook_service.py` line 490: `select("user_id").eq("stripe_customer_id", ...)` → `user_repo.get_by_stripe_customer_id()`
- `stripe_webhook_service.py` line 512: `update({"subscription_status": ...})` → `user_repo.update_subscription_status()`
- `stripe_webhook_service.py` line 562: `select("user_id").eq("stripe_customer_id", ...)` → `user_repo.get_by_stripe_customer_id()`
- `stripe_webhook_service.py` line 641: `select("user_id").eq("stripe_customer_id", ...)` → `user_repo.get_by_stripe_customer_id()`
- `clerk_webhook_service.py` line 380: `update(...)` → `user_repo.update_profile()` 或新增对应方法

**共 14 处** 需要迁移 (9 activity_logs + 5 profiles)
- 确保 webhook service 只通过 Repository 接口访问数据

### G3. 新 RPC 调用路径 — 必须经过 Repository 层

**现有模式**: 所有 RPC 调用封装在 Repository 中：
```python
# 现有代码 (正确模式):
class SupabaseCreditRepository:
    async def deduct_credits(self, ...):
        result = await self.client.rpc('deduct_credits_atomic', {...}).execute()
```

**修复策略**: 新增的 4 个 RPC 同样封装在 Repository 中：
- `process_subscription_start` → `SubscriptionRepository.start_subscription()`
- `process_subscription_renewal` → `SubscriptionRepository.renew_subscription()`
- `process_subscription_termination` → `SubscriptionRepository.terminate_subscription()`
- `process_credit_refund` → `CreditRepository.process_refund()`

Webhook service 通过 Repository 方法调用 RPC，不直接 `db_client.rpc()`。

---

## 一、方案概述

将 50 个问题归纳为 **12 个根因 (Root Cause)**，组织为 **8 个工作流 (Workstream)**，按依赖顺序串行执行。

### 12 个根因

| 根因 ID | 描述 | 关联问题 |
|---------|------|---------|
| RC1 | 各层硬编码积分/tier 值，TierService 未注入 | #2, #28, #29, #30, #36, #42, #43 |
| RC2 | 关键操作缺失原子事务 (多步非原子) | #25, #26, #49 |
| RC3 | 数据库 Schema 与代码字段名/约束不匹配 | #23, #24, #32 |
| RC4 | 取消/降级路径遗漏月度积分清零 | #5, #7, #8, #9, #10 |
| RC5 | 退费后不回收积分/tier | #6, #14, #15, #16, #17, #18 |
| RC6 | Checkout 未绑定 Stripe Customer，无升级路径 | #1, #3, #41 |
| RC7 | 同步阻塞事件循环 (time.sleep + sync Stripe) | #4, #20 |
| RC8 | Webhook 事件覆盖不全 | #44, #45 |
| RC9 | 前端缺少回调处理、字段不匹配、硬编码 | #11, #12, #13, #33, #35, #46 |
| RC10 | 启动校验不够严格 | #39, #48 |
| RC11 | 代码质量 (冗余条件、缓存 TTL、线程安全) | #21, #27, #31, #34, #37, #40 |
| RC12 | 缺失对账和监控机制 | #38, #47, #50 |

### 50 问题 → WS 映射完整表

| 问题 | 级别 | 归属 WS | 备注 |
|------|------|---------|------|
| #1 | P0 | WS6 | Checkout 未绑定 Customer |
| #2 | P0 | WS2 | Webhook 积分硬编码 |
| #3 | P0 | WS6 | 无升级路径 |
| #4 | P1 | WS7 | time.sleep 阻塞 |
| #5 | P1 | **WS4** | 非即时降级不同步 tier **(v1 遗漏)** |
| #6 | P1 | **WS5** | PaymentService class wrapper **(v1 遗漏)** |
| #7 | P0 | WS4 | 取消后积分未清零 |
| #8 | P0 | WS4 | Webhook 取消未清零 |
| #9 | P1 | **WS4** | 非即时取消不更新状态 **(v1 遗漏)** |
| #10 | P1 | **WS4** | billing_cycle_anchor 立即扣费 **(v1 遗漏)** |
| #11 | P1 | WS8 | purchaseCredits 硬编码 |
| #12 | P1 | WS8 | Checkout 返回不刷新 |
| #13 | P1 | WS8 | portal_url 字段不匹配 |
| #14 | P0 | WS5 | 退费不扣积分 |
| #15 | P0 | WS5 | 退订阅不降级 |
| #16 | P1 | WS5 | create_refund 不传 metadata |
| #17 | P1 | WS5 | refunds[0] 非最新 |
| #18 | P1 | WS5 | 退款金额计算不准 |
| #19 | - | - | 已确认无问题 |
| #20 | P1 | WS7 | Stripe 同步阻塞 |
| #21 | P2 | WS7 | coupon cache 非线程安全 |
| #22 | P1 | WS7 | 同 #34 |
| #23 | P0 | WS1 | CHECK 约束不兼容 |
| #24 | P0 | WS1 | 字段名不匹配 |
| #25 | P0 | WS3 | process_subscription_start 不存在 |
| #26 | P1 | WS3 | add_credits_atomic 无幂等性 |
| #27 | P2 | WS7 | 双类型字段 |
| #28 | P0 | WS2 | Container 未注入 TierService |
| #29 | P0 | WS2 | credit_repo 硬编码 500/1000 |
| #30 | P0 | WS2 | create_profile 硬编码 50 |
| #31 | P1 | WS7 | 冗余条件 |
| #32 | P1 | WS1 | record_subscription_change 触发 #23 |
| #33 | P1 | WS8 | DowngradeModal 硬编码 |
| #34 | P2 | WS7 | Admin Modals 重复 |
| #35 | P2 | WS8 | Profile 无回调 |
| #36 | P0 | WS2 | 注册奖励全线不一致 |
| #37 | P0 | **WS7** | PricingService 缺 await **(v1 遗漏)** |
| #38 | P1 | WS7 | 无 reconciliation |
| #39 | P1 | WS7 | STRIPE_SECRET_KEY 无声明 |
| #40 | P1 | WS7 | TierService 缓存无 TTL |
| #41 | P1 | WS6 | StripeProvider 不传 customer |
| #42 | P1 | WS2 | config.py 注释 50 不一致 |
| #43 | P2 | WS2 | docstring 写 50 |
| #44 | P1 | WS7 | 未处理 invoice.payment_failed |
| #45 | P2 | **WS7** | 未处理 3DS/SCA **(v1 遗漏)** |
| #46 | P1 | WS8 | 前端未展示异常状态 |
| #47 | P1 | WS7 | stripe_webhook_events RLS |
| #48 | P1 | WS7 | WEBHOOK_SECRET 仅 WARNING |
| #49 | P0 | WS3 | 续费非原子操作 |
| #50 | P1 | WS7 | 签名验证无显式 tolerance |

**统计**: WS1(3) + WS2(7) + WS3(3) + WS4(5) + WS5(6) + WS6(3) + WS7(15) + WS8(6) + 无问题(1) + 重复(1) = **50**

---

## 二、依赖图 (v2.0 修正)

```
WS1 (Schema 对齐)
    │
    v
WS2 (配置集中化 + DI)
    │
    v
WS3 (原子 RPC)  ← 依赖 WS2: webhook 调 RPC 需传入 TierService 获取的积分值
    │
    ├──> WS4 (取消/降级路径完善)
    │
    ├──> WS5 (退费处理完善)
    │
    └──> WS6 (Checkout 客户绑定 + 升级)
              │
              v
         WS7a (Async + 线程安全)
         WS7b (Webhook + 启动校验)    ← 7a/7b/7c/7d 可并行，无相互依赖
         WS7c (缓存 + 代码质量)
         WS7d (对账 + 死代码清理)
              │
              v
         WS8 (前端修复)
```

**v2.0 修正说明**:
- WS2 → WS3 改为串行 (v1 错误地标为并行)
- WS4/WS5/WS6 可并行，但都依赖 WS3
- WS7 依赖 WS4-WS6 完成后，清理收尾
- WS8 最后执行 (前端依赖后端 API 稳定)

---

## 三、各 WS 详细方案

### WS1: payment_records Schema 对齐

**根因**: RC3 — 数据库 CHECK 约束、字段名与代码不匹配
**解决**: #23, #24, #32
**文件**: 5 个

#### 修改清单

**1. `decodables/migrations/v2/03_infrastructure.sql`**

- 扩展 `check_payment_type` CHECK 约束，增加代码实际写入的类型:
  ```sql
  payment_type IN (
    'subscription', 'credit_purchase', 'one_time_purchase', 'upgrade', 'addon',
    -- 新增: 代码实际使用的类型
    'refund', 'sub_canceled', 'sub_cancel_scheduled', 'sub_renewal',
    'sub_payment', 'tier_downgrade', 'tier_downgrade_scheduled',
    'admin_adjustment', 'payment_failed'
  )
  ```
- `payment_method` 改为 `NOT NULL DEFAULT 'card'` (保持 NOT NULL 约束 + 添加 DEFAULT；card 是支付方式，stripe 是处理商，不应混淆)
  - ⚠️ **现状**: `payment_method TEXT NOT NULL` 无 DEFAULT，且 `payment_repository.py` 的 `create()` 方法完全不包含此字段 — 现有代码每次 INSERT 都会因约束失败
- 新增字段: `stripe_refund_id TEXT`

**2. `decodables/infrastructure/repositories/payment_repository.py`**

- `create()` 方法字段对齐:
  - `amount` → `amount_usd`
  - `stripe_payment_id` → `stripe_payment_intent_id`
- 添加 `payment_method` 默认值 `'card'`
- 新增 `status: str = "succeeded"` 可选参数 (退费记录需要 `"refunded"`)
  - ⚠️ **v3.4 审计发现 (P1)**: 当前硬编码 `"completed"` **不在 DB CHECK 约束中** (`status IN ('pending', 'processing', 'succeeded', 'failed', 'cancelled', 'refunded')`)。默认值必须改为 `"succeeded"`
  - ⚠️ **v3.3 审计发现 (P0)**: `_handle_charge_refunded()` (line 901-916) 传入 `status="refunded"` 但 `create()` 无此参数，导致 **TypeError 崩溃**
  - 同时传入 `payment_intent_id=` (错误参数名，应为 `stripe_payment_id=`)
  - 本修正同时解决这两个传参错误

**3. `decodables/domains/webhooks/stripe_webhook_service.py`** (仅字段名)

- 所有 `payment_repo.create()` 调用使用对齐后的字段名
- ⚠️ **重点修复**: `_handle_charge_refunded()` (line 901-916):
  - `payment_intent_id=payment_intent_id` → `stripe_payment_intent_id=payment_intent_id` (对齐后的字段名)
  - `status="refunded"` → 依赖 WS1 新增的 `status` 参数 (不再 TypeError)

**4. `decodables/domains/subscriptions/subscription_service.py`** (仅字段名)

- 所有 `payment_repo.create()` 调用使用对齐后的字段名

**5. `decodables/infrastructure/repositories/subscription_repository.py`**

- `record_subscription_change()` 使用对齐后的字段名

#### 验证

- [ ] 全局搜索 `payment_repo.create(` — 确认所有调用方字段名一致
- [ ] CHECK 约束覆盖所有实际写入的 payment_type 值
- [ ] 后端 build 通过

---

### WS2: 配置集中化 + Container DI 修复

**根因**: RC1 — 各层硬编码值，TierService 未注入
**解决**: #36, #2, #29, #30, #42, #43, #28
**文件**: 9 个

#### 核心思路

**单一配置源**: 所有积分/tier 相关数值必须来自 TierService (读 system_configs 表)。
硬编码值 → TierService 方法调用。Container 负责注入 TierService 到所有需要的 Service。

#### 修改清单

**1. `decodables/container.py`** — DI 修复 (核心)

- 新增 `_get_or_create_tier_service()` 方法，匹配现有 lazy caching 模式:
  ```python
  async def _get_or_create_tier_service(self) -> TierService:
      if 'tier_service' not in self._services:
          db = await get_async_db_client()
          config_repo = SupabaseConfigRepository(db)
          self._services['tier_service'] = TierService(config_repo)
      return self._services['tier_service']
  ```
- `get_billing_service()`: `BillingService(credit_repo, tier_service=await self._get_or_create_tier_service())`
- `get_stripe_webhook_service()`: 注入 `tier_service=await self._get_or_create_tier_service()`
- `get_clerk_webhook_service()`: 注入 `tier_service=await self._get_or_create_tier_service()`
- `get_subscription_service()`: **显式注入** `tier_service=await self._get_or_create_tier_service()`
  - ⚠️ SubscriptionService 已接受 tier_service 参数但 Container 当前未传入，需修复

**2. `decodables/domains/webhooks/stripe_webhook_service.py`**

- 构造函数增加 `tier_service: TierService` 参数
- `_process_subscription_start()`:
  - `amt = 500 if plan == "t2" else 1000` → `amt = await self.tier_service.get_monthly_credits(plan)`
- `_process_subscription_renewal()`:
  - 积分数从 TierService 获取
- **G2 修复**: 将所有直接 `self.db_client.table("profiles")` 调用迁移到 Repository 方法:
  - `table("profiles").select(...)` → `self.user_repo.get_profile()` 或新增 Repository 方法
  - `table("profiles").update(...)` → `self.user_repo.update_*()` 或新增 Repository 方法
  - 逐个排查，确保 webhook service 不再直接访问数据库表

**3. `decodables/domains/webhooks/clerk_webhook_service.py`**

- 构造函数增加 `tier_service: TierService` 参数
- ⚠️ **v3.3 审计发现**: `_grant_signup_bonus()` 是**死代码** — line 113 注释 `# DO NOT call`，line 156 注释 `# 无需再次调用`。注册奖励由 `create_user_idempotent` RPC 处理。
- **修复**: 删除 `_grant_signup_bonus()` 方法 (不是修改)
- TierService 注入目的改为: 将 `signup_bonus` 金额传给 `create_user_idempotent` RPC 的新参数 `p_signup_bonus` (见 WS2 文件 6)

**4. `decodables/infrastructure/repositories/credit_repository.py`**

- `refresh_monthly_credits(user_id, tier)` → `refresh_monthly_credits(user_id, amount)`
- 删除内部硬编码 `{"t2": 500, "t3": 1000}`
  - ⚠️ **代码探查发现**: 当前硬编码值 500/1000 本身就是错误的 (应为 100/200)，这进一步证实必须改为参数化
- 调用方 (webhook service) 从 TierService 获取金额后传入

**5. `decodables/infrastructure/repositories/subscription_repository.py`** — DI 修复

- **现状**: `__init__` 内部自行创建 `SupabaseUserRepository` 和 `SupabasePaymentRepository` (lines 77-90)，与 Container 创建的实例完全独立，违反 DI 原则
- **修复**: 改为构造函数注入依赖的 repos:
  ```python
  def __init__(self, db_client, user_repo, payment_repo):
      self.client = db_client
      self.user_repo = user_repo
      self.payment_repo = payment_repo
  ```
- Container `get_subscription_repository()` 传入已有的 repos 实例

**6. `decodables/migrations/v2/01_core_business.sql`**

- `create_user_idempotent` RPC: 增加参数 `p_signup_bonus INT DEFAULT 100`
  - RPC 不应读 system_configs (基础设施层不读业务配置)
  - 由调用方 (Service 层) 从 TierService 获取后传入
  - 默认值 100 作为安全保底

**7. `decodables/infrastructure/repositories/user_repository.py`**

- `create_profile()`: `credits_permanent: 50` → 接受 `signup_bonus` 参数
- 调用 `create_user_idempotent` RPC 时传入 `p_signup_bonus`
- ⚠️ **v3.3 审计发现**: G2 迁移 `table("profiles")` 直接操作需要新增 Repository 方法:
  - 新增 `get_by_stripe_customer_id(customer_id: str) -> Optional[dict]`: 根据 stripe_customer_id 查用户
    - 用于替换 stripe_webhook_service.py 中 4 处 `table("profiles").select("user_id").eq("stripe_customer_id", ...)` (lines 490, 512, 562, 641)
  - 新增 `update_subscription_status(user_id: str, status: str)`: 更新 subscription_status
    - 用于替换 stripe_webhook_service.py 中 `table("profiles").update({"subscription_status": ...})` (line 512)

**8. `decodables/config.py`**

- `# CREDITS_SIGNUP_BONUS = 50` 注释更新为指向 TierService

**9. `decodables/application/commands/billing.py`**

- docstring "Grants 50" → "Grants signup bonus (configured in system_configs)"

#### 验证

- [ ] 全局搜索硬编码 `500`, `1000`, `50` (积分相关) — 确认全部替换
- [ ] TierService 注入链完整: Container → Service → 使用
- [ ] 后端 build 通过

---

### WS3: 原子 RPC 函数

**根因**: RC2 — 缺失原子操作，多步操作无事务保护
**解决**: #25, #49, #26
**文件**: 6 个

#### 设计决策

**RPC 文件归属**: 新 RPC 操作 `profiles` + `credit_transactions` (核心业务表)，应放在 **`01_core_business.sql`**。仅 `payment_records` 相关 schema 变更放 `03_infrastructure.sql`。

**无需 Fallback**: 项目未上线，无生产流量。直接切换到新 RPC，删除旧代码路径。新 RPC 在本地充分测试后部署。

#### 修改清单

**1. `decodables/migrations/v2/01_core_business.sql`** — 新增 2 个 RPC

**`process_subscription_start`** RPC (解决 #25):
- 输入: `p_user_id, p_plan, p_stripe_customer_id, p_credits_amount, p_payment_amount, p_currency, p_session_id`
  - ⚠️ **v3.3 审计发现**: 参数名对齐现有代码 (line 387) 的 `p_credits_amount` / `p_payment_amount`，而非 v3.2 的 `p_monthly_credits` / `p_amount_usd`，减少调用方改动
- 原子执行:
  1. 幂等性检查 (p_session_id 查重 credit_transactions.idempotency_key)
  2. 更新 profiles: tier, stripe_customer_id, subscription_status='active', credits_monthly=p_credits_amount
  3. 插入 payment_records (type='subscription', amount_usd=p_payment_amount)
  4. 插入 credit_transactions (type='monthly_reset', amount=p_credits_amount, **balance_monthly_after=p_credits_amount, balance_permanent_after=当前值**)
- 返回: JSONB `{success, user_id, tier, credits_monthly}`
- 幂等性: 以 `p_session_id` 作为 idempotency_key (已在现有代码 line 387 传入)
- 状态前置检查: 若用户已是 t2/t3 (delayed event)，返回 `{success: true, already_processed: true}`

**`process_subscription_renewal`** RPC (解决 #49):
- 输入: `p_user_id, p_tier, p_amount_usd, p_currency, p_invoice_id, p_monthly_credits, p_idempotency_key`
- 原子执行:
  1. 幂等性检查 (idempotency_key 查重)
  2. 状态前置检查: 若 subscription_status='canceled'，跳过 (防止乱序 event 覆盖)
  3. 插入 payment_records (type='sub_renewal')
  4. 更新 subscription_status='active'
  5. 重置 credits_monthly=p_monthly_credits
  6. 插入 credit_transactions (type='monthly_reset', amount=p_monthly_credits, **balance_monthly_after=p_monthly_credits, balance_permanent_after=当前值**)
- 返回: JSONB `{success, already_processed, credits_monthly}`

> ⚠️ **部署顺序**: 这两个 RPC 放在 `01_core_business.sql` 但 INSERT 到 `payment_records`（定义在 `03_infrastructure.sql`）。部署时必须先执行 `03` 再执行 `01`，与文件编号顺序相反。在 SQL 文件头部添加注释说明。

**`add_credits_atomic` 增加幂等性** (解决 #26):
- 在函数开头加 idempotency_key 查重逻辑
- 参考已有 `deduct_credits_atomic` 的幂等实现

**`check_webhook_idempotency`** RPC (v3.5 新增 — 解决 P0-3):
- ⚠️ **v3.5 审计发现 (P0)**: `stripe_webhook_service.py` line 107 调用 `rpc("check_webhook_idempotency")`，但 SQL 中**无此函数**。与 #25 同类问题
- **当前行为**: RPC 不存在 → 抛异常 → 关键事件 (checkout/invoice) reject → 非关键事件 fallback `return False` (继续处理，可能重复退费)
- 输入: `p_event_id, p_event_type, p_payload`
- 原子执行: `INSERT INTO stripe_webhook_events (...) ON CONFLICT (event_id) DO NOTHING RETURNING ...`
- 返回: `{idempotent: true/false}` — true = 已处理过 (跳过)，false = 首次处理 (继续)
- 归属文件: **`03_infrastructure.sql`** (stripe_webhook_events 属于基础设施表)

**`admin_adjust_credits_atomic`** RPC (v3.5 新增 — 解决 P0-4):
- ⚠️ **v3.5 审计发现 (P0)**: `admin_repository.py` line 64-91 的 `admin_adjust_credits()` 是非原子 Read-Modify-Write (无行级锁)，存在 Lost Update 竞态
- 输入: `p_user_id, p_amount, p_bucket ('monthly'|'permanent'), p_reason, p_admin_id`
- 原子执行:
  1. `SELECT credits_monthly, credits_permanent FROM profiles WHERE id = p_user_id FOR UPDATE` (行级锁)
  2. 计算新值: `new_value = GREATEST(0, current + p_amount)`
  3. UPDATE profiles SET credits_{bucket} = new_value
  4. INSERT credit_transactions (审计记录，含 balance_monthly_after / balance_permanent_after)
- 返回: `{success, old_value, new_value, actual_change}`
- 归属文件: **`01_core_business.sql`** (操作 profiles + credit_transactions)
- **同步修改**: `admin_repository.py` 的 `admin_adjust_credits()` 改为调用此 RPC

**2. `decodables/infrastructure/repositories/subscription_repository.py`** — G3: Repository 封装

- 新增 `start_subscription(user_id, plan, ...)` 方法: 封装 `process_subscription_start` RPC 调用
- 新增 `renew_subscription(user_id, tier, ...)` 方法: 封装 `process_subscription_renewal` RPC 调用
- Webhook service 通过 Repository 方法调用，不直接 `db_client.rpc()`

**3. `decodables/container.py`** — 新增 DI 方法

- ⚠️ **v3.4 审计发现 (P1)**: Container 缺少 `get_subscription_repository()` 方法。WS3 要求 webhook service 注入 `subscription_repo`，但 Container 无法提供
- **新增方法**:
  ```python
  async def get_subscription_repository(self) -> SubscriptionRepository:
      if 'subscription_repository' not in self._services:
          db = await get_async_db_client()
          user_repo = await self._get_or_create_user_repo()
          payment_repo = await self._get_or_create_payment_repo()
          self._services['subscription_repository'] = SubscriptionRepository(db, user_repo, payment_repo)
      return self._services['subscription_repository']
  ```
- `get_stripe_webhook_service()` 注入 `subscription_repo=await self.get_subscription_repository()`

**4. `decodables/domains/webhooks/stripe_webhook_service.py`**

- ⚠️ **代码探查发现**: `_process_subscription_start()` (line 387) **已经调用** `rpc("process_subscription_start")`，但 SQL 函数不存在 (这正是 bug #25)
- **因此**: 只需创建 SQL RPC 函数 + 校验调用参数签名一致，不需要从头编写 webhook 端调用代码
- `_process_subscription_start()`:
  - 改为通过 Repository: `await self.subscription_repo.start_subscription(...)` (G3 规范)
  - 校验现有 `rpc()` 调用的参数名是否与新 RPC 定义一致，不一致则修正
  - 删除 rpc 调用失败后的 legacy fallback 代码路径
- `_process_subscription_renewal()`:
  - 通过 Repository: `await self.subscription_repo.renew_subscription(...)`
  - 删除旧的多步非原子代码路径
- 构造函数需增加 `subscription_repo` 依赖 (由 Container 注入)

**4. `decodables/migrations/v2/03_infrastructure.sql`**

- `add_credits_atomic` 函数增加幂等性检查代码

#### Webhook 事件顺序安全

Stripe 不保证事件顺序。RPC 内需加状态前置条件检查:
- `process_subscription_start`: 检查用户当前 tier 是否为 t1，若已是 t2/t3 则跳过 (防止 delayed event 覆盖)
- `process_subscription_renewal`: 检查 subscription_status 不是 'canceled'，若已取消则跳过

#### 验证

- [ ] 首次订阅: RPC 原子完成 (tier + credits + payment record)
- [ ] 续费: RPC 原子完成 (credits reset + payment record)
- [ ] add_credits_atomic: 重复 idempotency_key 不重复发放
- [ ] 乱序事件不会覆盖正确状态
- [ ] 旧的多步非原子代码路径已删除
- [ ] check_webhook_idempotency: 重复 event_id 返回 `{idempotent: true}` ✓
- [ ] admin_adjust_credits_atomic: 并发操作不丢失更新 (FOR UPDATE 锁) ✓
- [ ] admin_repository.py 改为调用新 RPC ✓

---

### WS4: 取消/降级路径完善

**根因**: RC4 — 多个取消/降级路径遗漏状态更新
**解决**: #5, #7, #8, #9, #10

#### 核心思路

区分 **立即生效** vs **期末生效** 两种模式:
- 立即取消/降级 → 立即更新 tier + 清零 credits_monthly
- 期末取消/降级 → 记录 `cancel_at_period_end` 状态 + 等待 Stripe webhook 触发实际降级

#### 修改清单

**1. `decodables/migrations/v2/01_core_business.sql`** — 新增 RPC + 字段

**profiles 表新增字段**:
- `cancel_at_period_end BOOLEAN DEFAULT FALSE` — 标记期末取消状态
- `cancel_at TIMESTAMPTZ` — 期末取消的具体时间点
- `pending_tier_change TEXT DEFAULT NULL` — 期末降级目标 tier (e.g. 't2')

> ⚠️ 这三个字段当前 profiles 表中 **不存在**，必须新增。

**`process_subscription_termination`** RPC:
- 输入: `p_user_id, p_new_tier, p_reason, p_subscription_status`
- 原子执行:
  1. 读取当前 credits_monthly (用于审计)
  2. 更新 profiles: tier=p_new_tier, subscription_status=p_subscription_status, credits_monthly=0, cancel_at_period_end=FALSE, cancel_at=NULL, pending_tier_change=NULL
  3. 插入 payment_record (type=p_reason)
  4. **审计**: 插入 credit_transaction (type='monthly_credits_cleared', amount=-原credits_monthly, balance_monthly_after=0, balance_permanent_after=当前值)
  5. 不清零 `stripe_customer_id` (保留以便未来复购)
- 返回: JSONB `{success, cleared_credits}`

**2. `decodables/domains/webhooks/stripe_webhook_service.py`**

- `_process_subscription_termination()`: 使用新 RPC 替代 `update_subscription_tier(uid, "t1")`
- 确保 `customer.subscription.deleted` 事件触发此方法

**3. `decodables/domains/subscriptions/subscription_service.py`**

- `cancel_user_subscription()` (⚠️ 实际方法名，非 `cancel_subscription`):
  - **完整签名** (v3.3 补充): `async def cancel_user_subscription(self, user_id, user_code, subscription_id, immediate, reason, admin_id)`
  - **immediate=True**: 调用 `process_subscription_termination` RPC (清零积分)
  - **immediate=False** (解决 #9):
    - 调用 Stripe API: `stripe.Subscription.modify(sub_id, cancel_at_period_end=True)`
    - 本地更新 profiles: `cancel_at_period_end=true, cancel_at=subscription.current_period_end`
    - 积分不立即清零 (期末 Stripe 会发 subscription.deleted webhook 触发清零)
    - 前端可据此展示 "将于 X 日取消"

- `_downgrade_t3_to_t2()`:
  - **immediate=True**: 保持现有逻辑，但移除 `billing_cycle_anchor='now'` (解决 #10)
    - 使用 `proration_behavior='create_prorations'` 替代
  - **immediate=False** (解决 #5): 使用 Stripe `Subscription.modify(proration_behavior='none')` + `schedule`
    - 本地更新 profiles: `pending_tier_change='t2'`
    - 等 webhook 确认后更新 tier (不在 API 中直接改 tier)

#### 验证

- [ ] Admin 立即取消 → credits_monthly=0, tier='t1' ✓
- [ ] Stripe webhook subscription.deleted → credits_monthly=0 ✓
- [ ] 期末取消 → cancel_at_period_end=true, 积分不变 ✓
- [ ] 期末取消后 Stripe 到期触发 deletion → 清零 ✓
- [ ] 降级 t3→t2 immediate=True → 不触发 billing_cycle_anchor ✓

---

### WS5: 退费处理完善

**根因**: RC5 — 退费后不回收积分/tier
**解决**: #6, #14, #15, #16, #17, #18

#### 核心思路

退费 webhook 根据原始交易类型执行不同回收:
- **积分购买退费** → 扣回永久积分
- **订阅退费** → 降级 tier + 清零月度积分 (复用 WS4 的 `process_subscription_termination`)

Metadata 缺失 fallback: 通过 payment_records 反查原始交易类型。

#### 修改清单

**1. `decodables/migrations/v2/01_core_business.sql`** — 新增 RPC

**`process_credit_refund`** RPC:
- 输入: `p_user_id, p_credits_to_deduct, p_payment_intent_id, p_refund_id, p_amount_usd`
- **幂等性**: 以 `p_refund_id` (Stripe refund ID) 作为 idempotency_key，在 payment_records 中查重
- 原子执行:
  1. 幂等性检查: 查询 `payment_records WHERE stripe_refund_id = p_refund_id`，已存在则返回 `{success: true, already_processed: true}`
  2. 读取当前 credits_permanent (用于计算实际扣除数)
  3. 实际扣除数 = LEAST(p_credits_to_deduct, 当前 credits_permanent) — 不允许扣成负数
  4. 扣回永久积分: credits_permanent = credits_permanent - 实际扣除数
  5. 插入 credit_transaction (type='refund_reversal', amount=-实际扣除数, balance_permanent_after=新值)
  6. 插入 payment_record (type='refund', stripe_refund_id=p_refund_id)
- 返回: JSONB `{success, already_processed, credits_deducted, remaining_permanent}`

**部分退费积分计算公式**:
- 全额退费: 扣回全部购买积分
- 部分退费: `退回积分 = ROUND(退款金额 / 原始金额 × 原始积分数)` (按比例)

**2. `decodables/infrastructure/repositories/payment_repository.py`** — 新增查询方法

- ⚠️ **v3.4 审计发现 (P0)**: `_handle_charge_refunded()` (line 892) 调用 `self.payment_repo.get_by_payment_intent_and_type(payment_intent_id, "credit_purchase")`，**但此方法在 PaymentRepository 中不存在**。当前代码 try/except 吞掉异常，导致退费幂等性检查完全失效
- **新增方法**:
  ```python
  async def get_by_payment_intent_and_type(
      self, stripe_payment_intent_id: str, payment_type: str
  ) -> Optional[dict]:
      """查询指定 payment_intent + type 的记录 (用于退费幂等性检查和原始交易反查)"""
  ```
- ⚠️ **v3.4 审计发现 (P2)**: `payment_records` 表**已有** `refunded_amount NUMERIC(10,2) DEFAULT 0` 和 `refunded_at TIMESTAMPTZ` 字段。退费处理应更新这些现有字段而非仅插入新 refund 记录
- **新增方法**:
  ```python
  async def update_refund_status(
      self, stripe_payment_intent_id: str, refunded_amount: float
  ) -> bool:
      """更新原始交易记录的 refunded_amount 和 refunded_at"""
  ```

**3. `decodables/domains/webhooks/stripe_webhook_service.py`**

- `_handle_charge_refunded()` 扩展:
  1. 获取原始 payment_intent metadata
  2. **如果有 metadata**: 直接判断 `plan_type`
  3. **如果无 metadata (fallback)**: 通过 `self.payment_repo.get_by_payment_intent_and_type()` 在 payment_records 中反查原始交易类型
  4. 积分购买退费 → 通过 Repository: `await self.credit_repo.process_refund(...)` (G3 封装)
  5. 订阅退费 → 通过 Repository: `await self.subscription_repo.terminate_subscription(...)` (复用 WS4 RPC)
  6. `charge.refunds.data` → 按 `created` 排序取最新 (解决 #17)
  7. 传递 Stripe refund ID 用于 RPC 幂等性检查
  8. **更新原始记录**: 调用 `self.payment_repo.update_refund_status()` 更新 refunded_amount/refunded_at

**4. `decodables/domains/billing/payment_service.py`**

- `PaymentService.create_refund()` **类方法** (line ~878):
  - 增加 `metadata: Optional[Dict] = None` 参数并透传到模块函数 (解决 #16)
  - ⚠️ **代码探查发现**: 模块级函数 `create_refund` (line ~561) **已有** `metadata` 参数，只有类方法缺少
  - 修改范围仅限类方法签名对齐，不需要改模块函数
- 退款金额计算: `amount - amount_refunded` 替代 `amount_received` (解决 #18)

**5. `decodables/domains/subscriptions/subscription_service.py`**

- `process_refund()`: 退款金额计算改为 `pi.amount - pi.amount_refunded`

#### 验证

- [ ] 积分购买退费 → 积分扣回 (按比例计算) ✓
- [ ] 订阅退费 → 降级 t1 + 清零月度积分 ✓
- [ ] 无 metadata 退费 → 通过 payment_records 反查成功 ✓
- [ ] 部分退款后再次退款 → 可退金额计算准确 ✓
- [ ] PaymentService.create_refund → 正确传递 metadata ✓
- [ ] 重复 refund webhook → 幂等处理 (不重复扣积分) ✓
- [ ] Webhook service 通过 Repository 调用 RPC (不直接 db_client.rpc) ✓

---

### WS6: Checkout 客户绑定 + 升级路径

**根因**: RC6 — 未绑定 Stripe Customer，无升级路径
**解决**: #1, #3, #41

#### 设计决策

**升级 (t2→t3) proration 策略**:
- 使用 `proration_behavior='create_prorations'` (Stripe 默认)
- Stripe 自动计算剩余周期差额，在下次 invoice 中调整
- 不使用 `billing_cycle_anchor='now'` (避免立即扣费)

#### 修改清单

**1. `decodables/domains/billing/payment_service.py`**

- `create_checkout_session()`:
  - 增加 `customer_id: Optional[str] = None` 参数
  - `if customer_id: session_params["customer"] = customer_id`
  - 无 customer_id 时不设 `customer_creation` (Stripe Checkout 默认行为已会创建 Customer，无需显式指定)
  - ⚠️ **v3.5 新增 (P1-5)**: metadata 补充 `credits_amount`:
    ```python
    "metadata": {
        "user_id": user_id,
        "plan_type": plan_type,
        "credits_amount": get_credits_amount(plan_type)  # 新增: 锁定 checkout 时的积分数
    }
    ```
    - 防止 checkout 创建后到 webhook 处理期间配置变更导致积分发放数不一致
    - Webhook handler 优先读 metadata.credits_amount，fallback 到 `get_credits_amount(plan)`
  - ⚠️ **v3.5 新增 (P2-2)**: 捕获 Stripe `IdempotencyError`，返回友好提示而非 500:
    ```python
    except stripe.error.IdempotencyError:
        return None  # 当前返回 None → API 500
    # 改为:
    except stripe.error.IdempotencyError:
        logger.info(f"[Checkout] Duplicate request for {user_id}:{plan_type}")
        raise HTTPException(409, "Checkout session already created. Please wait.")
    ```

**2. `decodables/api/user/payment.py`**

- ⚠️ **代码探查发现**: Payment API 使用 `PaymentService()` 直接实例化 (via `Depends(get_payment_service)`)，**不走 Container DI**
- **策略**: 不改造 DI 路径，在 endpoint 层直接获取 user profile 的 `stripe_customer_id` 传给 `PaymentService`:
  ```python
  # checkout 端点内:
  user_profile = await user_repo.get_profile(user_id)
  stripe_customer_id = user_profile.get("stripe_customer_id")
  result = payment_service.create_checkout_session(
      user_id=user_id, plan_type=plan_type,
      customer_id=stripe_customer_id  # 新增参数
  )
  ```
- **升级拦截**: 如果用户已有活跃订阅且请求订阅类 plan:
  - 当前 tier == 请求 tier → 400 "Already on this plan"
  - 当前 tier < 请求 tier → 走升级流程
  - 当前 tier > 请求 tier → 400 "Use downgrade endpoint"

**3. `decodables/shared/payment/providers/stripe_provider.py`**

- `create_checkout_session()`: 增加 `customer_id` 参数并透传

**4. `decodables/domains/subscriptions/subscription_service.py`** — 升级接口

- 新增 `upgrade_subscription(user_id, target_tier)`:
  - 获取当前 Stripe subscription ID
  - 查找 target_tier 的 Price ID (从 pricing_plans 或环境变量)
  - 调用 `stripe.Subscription.modify(sub_id, items=[{price: new_price}], proration_behavior='create_prorations')`
  - **不在 API 中直接更新本地 tier** — Stripe 修改成功后，tier 变更由 `customer.subscription.updated` webhook 驱动
  - API 返回 `{success: true, message: "Upgrade initiated, changes will be applied shortly"}`

**5. `decodables/api/user/payment.py`** — 新增端点

- `POST /api/v2/user/payment/upgrade` (与 checkout/portal 同域)
  - Body: `{target_tier: "t3"}`
  - 调用 `subscription_service.upgrade_subscription`

#### 验证

- [ ] 已有 stripe_customer_id 的用户 checkout → 复用同一 Customer ✓
- [ ] 新用户 checkout → 自动创建 Customer ✓
- [ ] 已有 t2 订阅再请求 t3 → 走升级流程 ✓
- [ ] 降级请求 → 返回 400 ✓
- [ ] Checkout metadata 包含 credits_amount ✓
- [ ] 双击 checkout → 返回 409 而非 500 ✓

---

### WS7: Async + Webhook + 缓存 + 代码质量 (拆分为 4 个子 WS)

**根因**: RC7, RC8, RC10, RC11, RC12
**解决**: #4, #20, #21, #22, #27, #31, #34, #37, #38, #39, #40, #44, #45, #47, #48, #50

> 原 WS7 涵盖 16 个问题、10 个文件，横跨 async/webhook/缓存/清理/对账 5 种不同类型。
> 按关注点分离原则拆分为 4 个子 WS，每个独立 commit，降低 review 难度和 revert 风险。

---

#### WS7a: Async + 线程安全 (解决 #4, #20, #21, #37)

**关注点**: 事件循环阻塞 + 线程安全
**文件**: 3 个

**1. `decodables/domains/billing/payment_service.py`** (#4, #20, #21)

- **#4 (retry 装饰器)**: `retry_on_stripe_error` 中 `time.sleep` → `asyncio.sleep`
  - 创建 `async_retry_on_stripe_error` async 版装饰器
  - 保留原同步版本供模块级函数使用
- **#20 (Stripe SDK 阻塞)**: Stripe SDK 是同步库，在 async Service 方法中用 `run_in_threadpool` 包装:
  ```python
  from starlette.concurrency import run_in_threadpool
  result = await run_in_threadpool(stripe.Checkout.Session.create, **params)
  ```
  - 注意: `run_in_threadpool` 解决的是 I/O 阻塞，`asyncio.sleep` 解决的是 sleep 阻塞，两者是不同问题
- **#21**: `_coupon_cache` 加 `threading.Lock` 保护

**2. `decodables/domains/billing/pricing_service.py`** (#37)

- **已确认**: db_client 是 **SyncClient** — `.execute()` 调用无 await，但方法声明为 async
- **问题本质**: async 方法内同步阻塞数据库调用，阻塞事件循环
- **修复**: 用 `run_in_threadpool` 包装同步查询:
  ```python
  from starlette.concurrency import run_in_threadpool

  async def _fetch_all_plans(self):
      response = await run_in_threadpool(
          lambda: self.db_client.table("pricing_plans").select("*").eq("is_active", True).order("sort_order").execute()
      )
  ```
- 涉及方法: `_fetch_all_plans()`, `get_plan_by_code()`, `get_user_price()`

**3. `decodables/domains/subscriptions/subscription_service.py`** (#20 扩展)

- ⚠️ **v3.4 审计发现 (P1)**: 此文件也有同步 Stripe SDK 调用未包装 `run_in_threadpool`，与 payment_service.py (#20) 同类问题
- **涉及方法** (同步 Stripe 调用):
  - `cancel_user_subscription()`: 调用 `stripe.Subscription.cancel()` / `stripe.Subscription.modify()`
  - `_downgrade_t3_to_t2()`: 调用 `stripe.Subscription.modify()`
  - `get_subscription_details()`: 调用 `stripe.Subscription.retrieve()`
- **修复**: 所有同步 Stripe SDK 调用用 `run_in_threadpool` 包装

**验证**:
- [ ] Stripe 调用不阻塞事件循环 (payment_service + subscription_service) ✓
- [ ] PricingService 同步查询通过 run_in_threadpool 包装 ✓
- [ ] SubscriptionService Stripe 调用通过 run_in_threadpool 包装 ✓
- [ ] coupon_cache 线程安全 ✓

---

#### WS7b: Webhook 补全 + 启动校验 (解决 #39, #44, #45, #47, #48, #50)

**关注点**: Webhook 事件覆盖 + 安全配置
**文件**: 4 个

**1. `decodables/domains/billing/payment_service.py`** (#48, #50)

- `construct_event()`: 显式传入 `tolerance=300`
- `validate_config()`:
  - `STRIPE_WEBHOOK_SECRET` 缺失: 生产环境 `raise RuntimeError` 而非 `logger.warning`
  - 开发环境保持 WARNING

**2. `decodables/config.py`** (#39)

- 新增 `STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")`
- 启动时验证非空 (生产环境)
- ⚠️ **v3.5 新增 (P1-4)**: 新增 `STRIPE_API_VERSION = os.environ.get("STRIPE_API_VERSION", "2024-12-18.acacia")`
  - 初始化时设置 `stripe.api_version = STRIPE_API_VERSION`
  - 防止 Stripe SDK 自动升级 API 版本导致 webhook 签名/字段/行为不可预期变化

**3. `decodables/domains/webhooks/stripe_webhook_service.py`** (#44, #45)

- `handle_event()` 新增:
  - `invoice.payment_failed` → `_handle_invoice_payment_failed()`
  - (P2) `invoice.payment_action_required` → 记录日志
  - ⚠️ **v3.5 新增 (P2-3)**: `customer.deleted` → `_handle_customer_deleted()` (清除本地 `stripe_customer_id`，GDPR 合规)
- ⚠️ **v3.5 新增 (P1-6)**: `_handle_invoice_payment()` 中当 `tier not in ["t2", "t3"]` 时 (line 503-519)，增加 `logger.warning` + Sentry alert，而非静默返回 `{"status": "ok"}`
- `_handle_invoice_payment_failed()`:
  - 更新 subscription_status='past_due'
  - 记录 payment_record (type='payment_failed')
- ⚠️ **v3.4 审计发现 (P0)**: `_process_subscription_termination()` (line 652) 中 `termination_statuses = ["canceled", "unpaid", "past_due", "incomplete_expired"]`
  - **`past_due` 不应触发立即降级**: 业界实践 (Stripe Dunning) 是 past_due → 重试扣费 → 多次失败后才 unpaid → 最终 canceled
  - **修复**: 从 `termination_statuses` 列表中移除 `past_due`
  - `past_due` 由新增的 `_handle_invoice_payment_failed()` 处理: 仅更新 subscription_status='past_due' + 记录日志，**不降级不清积分**
  - 修正后: `termination_statuses = ["canceled", "unpaid", "incomplete_expired"]`

**4. `decodables/migrations/v2/02_platform_services.sql`** (#47)

- 确认 `stripe_webhook_events` 表有:
  ```sql
  ALTER TABLE stripe_webhook_events ENABLE ROW LEVEL SECURITY;
  CREATE POLICY service_role_all ON stripe_webhook_events FOR ALL TO service_role USING (true) WITH CHECK (true);
  ```

**验证**:
- [ ] invoice.payment_failed → subscription_status='past_due' ✓
- [ ] 生产环境缺 STRIPE_WEBHOOK_SECRET → 启动失败 ✓
- [ ] construct_event 使用显式 tolerance=300 ✓
- [ ] stripe_webhook_events RLS 启用 ✓
- [ ] stripe.api_version 已锁定 ✓
- [ ] t1 用户收到 subscription webhook → WARNING 日志 + Sentry ✓
- [ ] customer.deleted → 清除本地 stripe_customer_id ✓

---

#### WS7c: 缓存 + 代码质量 (解决 #27, #31, #40)

**关注点**: 数据一致性 + 冗余代码清理
**文件**: 3 个

**1. `decodables/domains/identity/tier_service.py`** (#40)

- 为 `_cache` 和 `_tier_config_cache` 添加 TTL:
  ```python
  _cache_timestamp: float = 0
  _cache_ttl: int = 300  # 5 分钟

  def _is_cache_valid(self) -> bool:
      return (time.time() - self._cache_timestamp) < self._cache_ttl
  ```
- 参考 PricingService 已有的 `_cache_timestamp` + `_cache_ttl` 模式

**2. `decodables/infrastructure/repositories/user_repository.py`** (#31)

- `update_subscription_tier()`: `tier == "t1" or tier == "t1"` → `tier == "t1"`

**3. `decodables/migrations/v2/01_core_business.sql`** (#27)

- **问题**: `credit_transactions` 表有两个语义相同的类型字段 `transaction_type` 和 `tx_type`，通过 trigger 自动同步
- **操作** (渐进式清理):
  1. **第一步 (本次执行)**: 审查所有写入路径，确认全部使用 `transaction_type`
  2. **第二步 (本次执行)**: 将 `tx_type` 标记为 deprecated (添加 SQL 注释)；所有新 RPC (WS3) 统一使用 `transaction_type`
  3. **第三步 (未来清理)**: 移除 `tx_type` 字段 + trigger + 相关约束

**验证**:
- [ ] TierService 缓存 5 分钟后自动过期 ✓
- [ ] update_subscription_tier 冗余条件已修复 ✓
- [ ] 所有新 RPC 统一使用 `transaction_type` 字段 ✓

---

#### WS7d: 对账任务 + 死代码清理 (解决 #22, #34, #38)

**关注点**: 运维监控 + 代码库清洁
**文件**: 2 个 (后端 1 + 前端 1 目录)

**1. `decodables/scheduler.py`** (#38)

- 新增 reconciliation 任务:
  ```python
  async def run_credit_reconciliation(db=None):
      """检查距上次 monthly refresh 超过 32 天的活跃订阅用户"""
  ```
  - 查询: `profiles WHERE subscription_status='active' AND tier IN ('t2','t3')`
  - 检查: `credit_transactions WHERE transaction_type='monthly_reset' AND created_at > now() - 32 days`
  - **TierService 访问**: 调度器运行在 BackgroundScheduler 线程，需要独立创建:
    ```python
    db = await create_task_async_client()
    config_repo = SupabaseConfigRepository(db)
    tier_service = TierService(config_repo)
    monthly_credits = await tier_service.get_monthly_credits(user.tier)
    ```
  - **安全机制**: 仅记录日志 + Sentry，不自动补发。人工确认后通过 Admin API 手动补发
  - 每日 6:00 AM UTC 执行

**2. `decodables-fe/components/admin/` 整个目录** (#22, #34)

- **问题**: 与 `app/admin/users/_components/modals/` 存在两套完全重复的 Admin Modal
- **调查结论**: `components/admin/` 是废弃版本 (1,847 行死代码，零引用)
- **操作**:
  1. 全局搜索 `from.*components/admin` 和 `from.*@/components/admin` 确认零引用
  2. 删除整个 `components/admin/` 目录 (6 个 Modal + index.ts)
  3. 如有残留类型引用，迁移到 `app/admin/users/_components/modals/`

**验证**:
- [ ] 对账任务能发现漏发积分的用户 ✓
- [ ] `components/admin/` 已删除，无残留引用 ✓
- [ ] 前端 build 通过 ✓

---

### WS8: 前端修复

**根因**: RC9 — 前端缺少回调处理、字段不匹配、硬编码
**解决**: #11, #12, #13, #33, #35, #46

#### 修改清单

**1. `decodables-fe/app/dashboard/_components/DashboardContent.tsx`** (解决 #12)

- 检测 `?success=true&plan=xxx`:
  - 显示 toast "Credits added!" 或 "Subscription activated!"
  - 调用 `useUserStore.getState().refreshUser()` 刷新积分/tier
- 检测 `?canceled=true`:
  - 显示 "Payment canceled" 提示
- 成功处理后清除 URL 参数 (`router.replace` 去掉 query params)

**2. `decodables-fe/app/profile/page.tsx`** (解决 #35)

- 同 DashboardContent 逻辑 (profile 页也是 checkout 返回目标)
- 可抽取为共享 hook: `useCheckoutCallback()`

**3. `decodables-fe/services/paymentService.ts`** (解决 #13)

- **已确认**: 后端 `PortalResponse` 返回 `url`，前端 `PortalUrlResponseSchema` 期望 `portal_url`
- **修复**: 前端 Zod schema `portal_url` → `url` (改前端，因为后端已稳定)
  ```typescript
  const PortalUrlResponseSchema = z.object({
    url: z.string().url(),  // 原为 portal_url
  });
  ```
- 同步修改引用 `portal_url` 的代码为 `url`

**4. `decodables-fe/hooks/useCredits.ts`** (解决 #11)

- `purchaseCredits(planType: string = 'credits_100')`: 接受参数替代硬编码

**5. `decodables-fe/app/admin/users/_components/modals/DowngradeModal.tsx`** (解决 #33)

- 积分数从 `useAllTiers()` hook 动态获取
- 替代硬编码 `{t1: 0, t2: 100, t3: 200}`

**6. `decodables-fe/components/profile/SubscriptionCard.tsx`** (解决 #46)

- 新增 `subscription_status` prop
- 展示异常状态 badge:
  - `past_due` → "Payment Due" 警告样式
  - `canceled` → "Canceled (ends on X)"
  - `incomplete` → "Setup Incomplete"
  - `active` → 无额外 badge (默认)
- **已确认**: 后端 `GET /api/v2/user/profile/me` 已返回 `subscription_status` 字段
- **需补充**: WS4 新增的 `cancel_at_period_end` 和 `cancel_at` 字段需在后端 profile 响应中添加:
  - 在 `decodables/api/user/user_profile.py` 的 `/me` 端点 response dict 中增加:
    ```python
    "cancel_at_period_end": user.cancel_at_period_end or False,
    "cancel_at": user.cancel_at.isoformat() if user.cancel_at else None,
    ```

**7. 升级/降级操作后的前端 UX** (配合 WS6 webhook 驱动)

- 升级/降级 API 返回后 → 展示 "Processing..." loading 状态
- 轮询 `/api/v2/user/profile/me` 检测 tier 变化 (间隔 2 秒，最多 15 次)
- 超时 30 秒未检测到变化 → 展示 "Changes are being processed. Please refresh in a moment."
- 检测到 tier 变化 → toast 通知 + 刷新 user store

#### 验证

- [ ] Checkout 成功返回 → toast + 刷新数据 ✓
- [ ] Portal 跳转正常 (字段名 `url` 一致) ✓
- [ ] purchaseCredits 支持选择包型 ✓
- [ ] DowngradeModal 动态积分数 ✓
- [ ] SubscriptionCard 展示 past_due/canceled 状态 ✓
- [ ] 升级操作后 → loading + 轮询检测 tier 变化 ✓
- [ ] 后端 /me 返回 cancel_at_period_end 和 cancel_at ✓
- [ ] 前端 build 通过 ✓

---

## 四、方案自审发现的设计要点

### 4.1 v1 → v2 修正项

| 修正项 | v1 问题 | v2 修正 |
|--------|---------|---------|
| 6 个问题遗漏 | #5, #6, #9, #10, #37, #45 未分配 | 全部分配到对应 WS |
| 依赖图错误 | WS2 和 WS3 标为并行 | WS2 → WS3 改为串行 |
| RPC 文件归属 | 所有新 RPC 放 03_infrastructure.sql | 操作核心业务表的 RPC 放 01_core_business.sql |
| 无 fallback | 删除 legacy fallback | 保留 30 天，监控确认后再删 |
| 取消路径不完整 | 只考虑 immediate=True | 增加 immediate=False (期末生效) 处理 |
| proration 未指定 | 升级 proration 行为未定义 | 明确使用 create_prorations |
| 事件顺序 | 未考虑 webhook 乱序 | RPC 内加状态前置条件检查 |

### 4.2 关键设计决策记录

| 决策 | 选项 | 选择 | 理由 |
|------|------|------|------|
| RPC 读 system_configs? | A: RPC 内读 / B: 参数传入 | B: 参数传入 | DDD: 基础设施层不读业务配置 |
| Legacy fallback | A: 删除 / B: 保留 | A: 直接删除 | 项目未上线，无需熔断降级；双路径增加复杂度 |
| 升级实现 | A: 新 checkout / B: Subscription.modify | B: modify | 避免并行订阅，Stripe 推荐做法 |
| 取消清积分时机 | A: 立即 / B: 期末 | 视 immediate 参数 | 即时取消立即清零，期末取消等 webhook |
| stripe_customer_id 清零 | A: 取消时清零 / B: 保留 | B: 保留 | 用户可能复购，保留关联 |
| 退费 metadata 缺失 | A: 跳过 / B: 反查 | B: 反查 payment_records | 确保旧交易也能正确回收 |
| Webhook 乱序 | A: 忽略 / B: 状态前置检查 | B: 前置检查 | 防止 deleted 事件被晚到的 succeeded 覆盖 |

### 4.3 已确认的问题 (v3.1 代码探查结果)

| 问题 | 确认结果 | 方案影响 |
|------|---------|---------|
| PricingService db_client 类型 | **SyncClient** — `.execute()` 无 await | #37 用 `run_in_threadpool` 包装，不加 await |
| profiles 表 cancel_at_period_end 字段 | **不存在** — 需新增 3 个字段 | WS4 方案正确 |
| PortalResponse 字段名 | 后端返回 `url`，前端期望 `portal_url` | WS8 改前端 Zod schema |
| 对账任务检测字段 | `transaction_type='monthly_reset'` + `created_at` 可用 | WS7d 方案可行 |
| /me API subscription_status | **已返回** `subscription_status` | WS8 前提满足，补充 cancel_at 字段 |

### 4.4 代码兼容性验证 (v3.2 代码-方案矛盾排查)

| # | 矛盾 | 实际代码 | 方案修正 |
|---|-------|---------|---------|
| 1 | 方法名错误 | `cancel_user_subscription()` (非 `cancel_subscription`) | WS4 已更正方法名 |
| 2 | create_refund metadata 范围过大 | 模块函数 (line ~561) **已有** metadata 参数 | WS5 缩小范围: 只改类方法 (line ~878) |
| 3 | Payment API 不走 Container DI | `get_payment_service()` 直接返回 `PaymentService()` | WS6 改为 endpoint 层传 customer_id |
| 4 | activity_logs 直接插入遗漏 | 9 处 `table("activity_logs").insert(...)` 未纳入 G2 | G2 已扩展覆盖范围 |
| 5 | Webhook 已调用 RPC | `_process_subscription_start` line 387 已调 `rpc()` (SQL 不存在) | WS3 只建 SQL + 校验参数签名 |
| 6 | db_client fallback 模式 | StripeWebhookService 构造函数 fallback 到 `user_repo.client` | 保持现状，来源一致无需改动 |
| 7 | payment_method NOT NULL 无 DEFAULT | `payment_method TEXT NOT NULL`，repo 未传值 | WS1 改为 `NOT NULL DEFAULT 'card'` |
| 8 | SubscriptionRepo 内部自建 repos | `__init__` 自行创建 UserRepo + PaymentRepo 实例 | WS2 增加第 5 项: 改为 Container 注入 |
| 9 | refresh_monthly_credits 硬编码值错误 | 当前值 `{"t2": 500, "t3": 1000}` 本身就是错的 | WS2 增加备注，进一步证实必须参数化 |
| 10 | signup bonus RPC 硬编码 50 | `create_user_idempotent` 设 `credits_permanent = 50` | 方案已正确 (改为参数化 DEFAULT 100) |

### 4.5 深度审计验证 (v3.3 全方案逐项审计)

| WS | 审计结论 | 新发现 |
|----|---------|--------|
| G1 | ✅ 无问题 | - |
| G2 | ⚠️ 补充 | 5 处 `table("profiles")` 未列出精确位置，已补充 14 处完整清单 |
| G3 | ✅ 无问题 | - |
| WS1 | ⚠️ P0 发现 | `_handle_charge_refunded` 传参 TypeError 崩溃 + `create()` 缺 status 参数 |
| WS2 | ⚠️ 调整 | `_grant_signup_bonus` 是死代码应删除；需新增 `get_by_stripe_customer_id` repo 方法 |
| WS3 | ⚠️ P0×2+DI | RPC 参数名对齐；Container 缺 DI；`check_webhook_idempotency` 不存在；Admin 积分非原子 |
| WS4 | ⚠️ 签名 | 补充完整方法签名 (含 user_code, subscription_id, reason, admin_id) |
| WS5 | ⚠️ P0 发现 | `get_by_payment_intent_and_type()` 不存在 (退费幂等性失效)；补充 `refunded_amount`/`refunded_at` 更新 |
| WS6 | ⚠️ 补充 | Checkout metadata 缺 `credits_amount`；IdempotencyError 返回 500 |
| WS7a | ⚠️ 补充 | `subscription_service.py` 也有同步 Stripe 调用需要 `run_in_threadpool` |
| WS7b | ⚠️ P0+补充 | `past_due` 过度降级；API 版本未锁定；t1 webhook 静默忽略；缺 `customer.deleted` |
| WS7c | ✅ 无问题 | - |
| WS7d | ✅ 无问题 | - |
| WS8 | ✅ 无问题 | - |

---

## 五、执行顺序与 Commit 规划

### 执行顺序

| 顺序 | 工作流 | 解决问题 | 涉及文件数 |
|------|--------|---------|-----------|
| 1 | WS1: Schema 对齐 | #23, #24, #32 | 5 |
| 2 | WS2: 配置集中化 + DI | #36, #2, #28, #29, #30, #42, #43 | 9 |
| 3 | WS3: 原子 RPC | #25, #49, #26 | 6 |
| 4 | WS4: 取消/降级完善 | #5, #7, #8, #9, #10 | 4 |
| 5 | WS5: 退费完善 | #6, #14, #15, #16, #17, #18 | 5 |
| 6 | WS6: 客户绑定 + 升级 | #1, #3, #41 | 5 |
| 7a | WS7a: Async + 线程安全 | #4, #20, #21, #37 | 3 |
| 7b | WS7b: Webhook + 启动校验 | #39, #44, #45, #47, #48, #50 | 4 |
| 7c | WS7c: 缓存 + 代码质量 | #27, #31, #40 | 3 |
| 7d | WS7d: 对账 + 死代码清理 | #22, #34, #38 | 2 |
| 8 | WS8: 前端修复 | #11, #12, #13, #33, #35, #46 | 7 |

### Commit 策略

每个 WS / 子 WS 作为一个独立 commit:
```
git commit 格式:
fix(payment): WS{N} - {简述} (#问题编号列表)

示例:
fix(payment): WS1 - align payment_records schema with code (#23, #24, #32)
fix(payment): WS2 - centralize config + inject TierService via Container DI (#36, #2, #28, #29, #30, #42, #43)
fix(payment): WS7a - fix async blocking with run_in_threadpool (#4, #20, #21, #37)
fix(payment): WS7b - add invoice.payment_failed handler + startup validation (#39, #44, #45, #47, #48, #50)
```

总计 **11 个 commit** (WS1-WS6 各 1 个 + WS7a/7b/7c/7d 各 1 个 + WS8 1 个)

### 每个 WS 完成后

1. 后端 `python -m py_compile` 语法验证
2. 前端 `npm run build` (WS8)
3. git commit + push
4. 更新审计报告标记已修复问题
5. 进入下一个 WS

---

## 六、风险与缓解

| 风险 | 影响 | 缓解策略 |
|------|------|---------|
| stripe_webhook_service.py 被 6 个 WS 修改 | 改动相互干扰 | 严格按 WS 顺序串行执行，每个 WS 完成后 read-through 完整文件 |
| 新 RPC 有 bug | 支付流程阻断 | 项目未上线，本地充分测试后再部署；RPC 有状态前置检查防止脏数据 |
| TierService 注入后缓存 miss | 首次调用慢 | TierService 有 EMERGENCY_TIER_CONFIGS 作为同步 fallback |
| 前端 portal_url→url 改动 | Portal 跳转临时不可用 | 项目未上线，前后端一起部署即可 |
| 对账任务误补发 | 多发积分 | 仅记录日志 + Sentry，不自动补发，人工确认后操作 |
| 升级 API webhook 延迟 | 用户看不到即时 tier 变化 | 前端 polling 机制 + 超时友好提示 |

---

**文档版本**: v3.5
**最后更新**: 2026-01-30
**状态**: 待讨论确认

### v3.5 修正清单 (三轮审计 — 7 个新发现: 并发/幂等/配置)

| 修正位置 | 修正内容 | 严重度 |
|----------|---------|--------|
| WS3 新增 RPC | `check_webhook_idempotency` RPC 不存在 (line 107 调用，SQL 无定义)。新建原子 check-and-insert 函数 | 🔴 P0 |
| WS3 新增 RPC + `admin_repository.py` | `admin_adjust_credits()` 非原子 Read-Modify-Write → 新建 `admin_adjust_credits_atomic` RPC (FOR UPDATE 锁) | 🔴 P0 |
| WS3 文件数 | 5 → 6 | - |
| WS7b 文件 2 (`config.py`) | Stripe API 版本未锁定 → 新增 `STRIPE_API_VERSION` 环境变量 + `stripe.api_version` 初始化 | 🟡 P1 |
| WS6 文件 1 (`payment_service.py`) | Checkout metadata 缺 `credits_amount` → 新增，webhook 优先使用 metadata 值 | 🟡 P1 |
| WS7b 文件 3 (`stripe_webhook_service.py`) | t1 用户收到 subscription webhook 静默忽略 → 增加 WARNING + Sentry | 🟡 P1 |
| WS6 文件 1 (`payment_service.py`) | Checkout IdempotencyError 返回 500 → 改为 409 + 友好提示 | 🟢 P2 |
| WS7b 文件 3 (`stripe_webhook_service.py`) | 缺 `customer.deleted` 事件处理 → 新增 handler 清除 stripe_customer_id | 🟢 P2 |

### v3.4 修正清单 (二轮审计 — 6 个新发现修正)

| 修正位置 | 修正内容 | 严重度 |
|----------|---------|--------|
| WS1 文件 2 | `status` 默认值 `"completed"` → `"succeeded"` (不在 DB CHECK 约束中) | 🟡 P1 |
| WS5 新增文件 2 | 新增 `payment_repo.get_by_payment_intent_and_type()` 方法 (line 892 调用但不存在，退费幂等性失效) | 🔴 P0 |
| WS5 新增文件 2 | 新增 `payment_repo.update_refund_status()` 方法 (利用现有 `refunded_amount`/`refunded_at` 字段) | 🟢 P2 |
| WS5 文件数 | 4 → 5 | - |
| WS7b 文件 3 | `past_due` 从 `termination_statuses` 移除 (业界实践: past_due 应走 Dunning 重试，不立即降级) | 🔴 P0 |
| WS3 新增文件 3 | Container 新增 `get_subscription_repository()` 方法 (webhook service 注入 subscription_repo 的前提) | 🟡 P1 |
| WS3 文件数 | 4 → 5 | - |
| WS7a 新增文件 3 | `subscription_service.py` 同步 Stripe 调用也需 `run_in_threadpool` 包装 | 🟡 P1 |
| WS7a 文件数 | 2 → 3 | - |

### v3.3 修正清单 (深度审计 — 7 个新发现修正)

| 修正位置 | 修正内容 | 严重度 |
|----------|---------|--------|
| WS1 文件 2 | `payment_repo.create()` 新增 `status: str = "completed"` 可选参数 (退费需 `"refunded"`) | 🔴 P0 |
| WS1 文件 3 | `_handle_charge_refunded()` 修正: `payment_intent_id=` → `stripe_payment_intent_id=`, `status=` 依赖新参数 | 🔴 P0 |
| WS2 文件 3 | `_grant_signup_bonus()` 改为**删除** (死代码，line 113/156 注释禁用)；TierService 改为传参给 RPC | 🟡 P1 |
| WS2 文件 7 | 新增 `user_repo.get_by_stripe_customer_id()` + `update_subscription_status()` 方法 (G2 迁移依赖) | 🟡 P1 |
| G2 | 补充 5 处 `table("profiles")` 精确行号 (stripe 4 处 + clerk 1 处)，总计 14 处→全部列出 | 🟡 P1 |
| WS3 文件 1 | RPC 参数名对齐代码: `p_monthly_credits` → `p_credits_amount`, `p_amount_usd` → `p_payment_amount` | 🟡 P1 |
| WS4 文件 3 | 补充 `cancel_user_subscription` 完整签名 (含 user_code, subscription_id, reason, admin_id) | 🟢 P2 |

### v3.2 修正清单 (代码兼容性验证 — 10 个矛盾点修正)

| 修正位置 | 修正内容 |
|----------|---------|
| G2 | **扩展范围**: 增加 9 处 `table("activity_logs").insert(...)` 迁移 (stripe_webhook 5 处 + clerk_webhook 4 处) |
| WS1 | `payment_method` 改为 `NOT NULL DEFAULT 'card'` (非可空)；增加现状说明: repo 未传值导致 INSERT 失败 |
| WS2 文件 4 | `refresh_monthly_credits` 增加备注: 当前硬编码 500/1000 本身就是错误值 |
| WS2 新增文件 5 | `subscription_repository.py` DI 修复: 内部自建 repos → Container 注入 |
| WS2 文件数 | 8 → 9 |
| WS3 文件 3 | `_process_subscription_start()` 已调用 `rpc()` (SQL 不存在)，只需建 SQL + 校验参数签名 |
| WS4 | 方法名修正: `cancel_subscription()` → `cancel_user_subscription()` (实际代码方法名) |
| WS5 | `create_refund` metadata: 模块函数已有，只需改类方法 — 缩小修改范围 |
| WS6 | Payment API 不走 Container DI → endpoint 层直接获取 `stripe_customer_id` 传给 `PaymentService` |
| Section 4.4 | 新增代码兼容性验证表 (10 个矛盾点完整记录) |

### v3.1 修正清单 (业界最佳实践 + 代码探查确认)

| 修正位置 | 修正内容 |
|----------|---------|
| WS3 | **删除 legacy fallback** — 项目未上线，直接切换新 RPC，删除旧代码路径 |
| WS6 | 升级端点改为 `POST /api/v2/user/payment/upgrade` (与 checkout/portal 同域) |
| WS7 | **拆分为 WS7a/7b/7c/7d** 四个子 WS (关注点分离，独立 commit) |
| WS7a #37 | PricingService 确认为 SyncClient，用 `run_in_threadpool` 包装 (非加 await) |
| WS8 #13 | Portal 字段确认: 后端返回 `url`，前端改 `portal_url` → `url` |
| WS8 #46 | subscription_status 确认: `/me` API 已返回，补充 cancel_at 字段 |
| WS8 新增 | 升级/降级后前端 UX: polling 检测 tier 变化 + 超时友好提示 |
| Section 4.3 | "待确认"全部替换为"已确认" + 实际代码探查结果 |
| 风险表 | 删除 fallback 风险行，新增 webhook 延迟风险行 |
| 设计决策表 | Legacy fallback 改为"直接删除" |
| 执行顺序 | WS7 行拆分为 WS7a/7b/7c/7d 四行 |

### v3.0 修正清单

| 修正位置 | 修正内容 |
|----------|---------|
| 全局新增 G1 | 每个 WS 必须包含测试计划 |
| 全局新增 G2 | stripe_webhook_service.py 直接 table() 调用迁移到 Repository |
| 全局新增 G3 | 新 RPC 必须经过 Repository 层封装 |
| WS1 | `payment_method DEFAULT 'card'` (非 'stripe'，card 是支付方式，stripe 是处理商) |
| WS2 | Container 使用 `_get_or_create_tier_service()` 匹配现有 lazy caching 模式 |
| WS2 | SubscriptionService 改为 "显式注入" (非 "确认已注入"，因为当前未注入) |
| WS2 | 增加 G2 修复: 迁移直接 table() 调用到 Repository |
| WS3 | RPC 返回增加 balance_monthly_after / balance_permanent_after 审计字段 |
| WS3 | 部署顺序警告: 03.sql 需先于 01.sql 执行 |
| WS3 | G3: 新增 subscription_repository.py 封装方法 |
| WS3 | webhook service 构造函数增加 subscription_repo 依赖 |
| WS4 | profiles 表三个字段改为 "新增" (cancel_at_period_end, cancel_at, pending_tier_change) |
| WS4 | process_subscription_termination RPC 增加 credit_transaction 审计记录 |
| WS4 | 期末取消/降级增加具体 Stripe API 调用和本地状态更新细节 |
| WS5 | process_credit_refund RPC 增加幂等性 (p_refund_id) |
| WS5 | 增加部分退费积分计算公式 (按比例) |
| WS5 | webhook service 通过 Repository 调用 RPC (G3) |
| WS6 | 移除不必要的 `customer_creation="always"` |
| WS6 | 升级 API: tier 变更由 webhook 驱动，非 API 直接更新 |
| WS7 | 区分 #4 (asyncio.sleep) 和 #20 (run_in_threadpool) 为不同问题 |
| WS7 | 对账调度器: 明确 TierService 独立创建路径 + 安全机制 (仅记录不自动补发) |
| WS8 | SubscriptionCard: 增加后端 API 字段返回确认前提 |
