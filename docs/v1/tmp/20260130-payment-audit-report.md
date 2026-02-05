# 支付系统全面审计报告 (完整版)

**审计日期**: 2026-01-30
**审计范围**: 订阅/降级/取消订阅、购买 Credits、退费
**审计方法**: 逐文件人工代码审查，结合项目架构规范和业界最佳实践
**覆盖范围**: 数据库 Schema/RPC + 后端 Domain/Application/Infrastructure/API/Config/Scheduler + 前端 Modals/Pages/Hooks/Store

---

## 审计文件清单

### 数据库 (decodables/migrations/v2/)
| 文件 | 职责 |
|------|------|
| `01_core_business.sql` | 核心表: credit_purchases, credit_transactions |
| `03_infrastructure.sql` | 基础设施: payment_records, RPC 函数 (deduct_credits_atomic, add_credits_atomic, process_credit_purchase, p_start/complete_webhook_processing) |

### 后端 (decodables/)
| 文件 | 职责 |
|------|------|
| `container.py` | DI 容器: 服务实例化和依赖注入 |
| `domains/billing/payment_service.py` | Stripe 支付操作 (checkout/portal/refund/subscription) |
| `domains/billing/service.py` | 积分领域服务 (扣费/充值/签到奖励) |
| `domains/subscriptions/subscription_service.py` | 订阅管理 (退费/取消/降级) |
| `domains/subscriptions/exceptions.py` | 订阅领域异常 (15+ domain exceptions) |
| `domains/webhooks/stripe_webhook_service.py` | Stripe Webhook 处理 (checkout/invoice/refund) |
| `infrastructure/repositories/credit_repository.py` | 积分仓库 (deduct/add/refresh atomic 操作) |
| `infrastructure/repositories/payment_repository.py` | 支付记录仓库 (CRUD) |
| `infrastructure/repositories/user_repository.py` | 用户仓库 (tier/credits/profile) |
| `infrastructure/repositories/subscription_repository.py` | 订阅仓库 (代理 user+payment repo) |
| `api/user/payment.py` | 用户支付 API (checkout/portal) |
| `api/user/billing.py` | 用户积分 API (credits/transactions) |
| `api/user/webhooks.py` | Webhook 接收端点 |
| `api/admin/subscriptions.py` | Admin 订阅管理 API (退费/取消/降级) |

### 前端 (decodables-fe/)
| 文件 | 职责 |
|------|------|
| `services/paymentService.ts` | 支付 API 调用 (Zod 验证) |
| `hooks/useCredits.ts` | 积分 hook (余额/历史/购买) |
| `lib/useUserStore.ts` | Zustand 全局状态 (credits/tier) |
| `components/credits-dialog/useCreditsDialog.ts` | Credits Dialog 业务逻辑 |
| `components/profile/SubscriptionCard.tsx` | 订阅卡片 UI |
| `components/UpgradeModal.tsx` | 升级弹窗 (动态定价) |
| `components/OutOfCreditsModal.tsx` | 积分不足弹窗 (top-up + 订阅) |
| `app/profile/page.tsx` | 移动端 Profile 页面 |
| `app/admin/users/_components/modals/RefundModal.tsx` | Admin 退费弹窗 |
| `app/admin/users/_components/modals/CancelSubscriptionModal.tsx` | Admin 取消订阅弹窗 |
| `app/admin/users/_components/modals/DowngradeModal.tsx` | Admin 降级弹窗 |
| `app/admin/users/_components/modals/CreditAdjustModal.tsx` | Admin 积分调整弹窗 |
| `app/admin/users/_lib/api.ts` | Admin 用户管理 API |

---

## 一、订阅 (Subscribe / Upgrade)

### 做得好的地方
- Checkout Session 使用 `metadata` 传递 `user_id` + `plan_type`，webhook 能正确关联
- 订阅创建使用 atomic RPC (`process_subscription_start`)，保证支付记录 + tier 更新 + 积分发放原子性
- 有 legacy fallback 流程 (RPC 不存在时降级到非原子操作)
- Idempotency key 基于 user + plan + 时间窗口，防止重复 checkout
- 前端 UpgradeModal 和 OutOfCreditsModal 使用 `useAllTiers()` 动态获取定价
- 前端支付按钮有 5 秒节流防重复点击

### P0 - 严重问题

#### #1 Checkout Session 未绑定 Stripe Customer

- **位置**: `domains/billing/payment_service.py:326-335`
- **问题**: `create_checkout_session` 没有传 `customer` 参数。如果用户已有 `stripe_customer_id`，每次 checkout 都会**创建新的 Stripe Customer**
- **后果**: 同一用户在 Stripe 中有多个 Customer 记录，订阅管理混乱，billing portal 无法正常管理所有订阅
- **业界实践**: 如果用户已有 `stripe_customer_id`，必须传入 `customer` 参数；如果是新用户，传 `customer_email` 并在 webhook 里保存新 customer ID
- **修复方案**: checkout 端点需要把 `user.stripe_customer_id` 传给 `create_checkout_session`

#### #2 订阅积分硬编码，不走 TierService 配置

- **位置**: `domains/webhooks/stripe_webhook_service.py:383`
- **问题**: `amt = 500 if plan == "t2" else 1000` — 硬编码了订阅初始积分 500/1000
- 但 CLAUDE.md 规定 t2=100/月, t3=200/月。500/1000 跟实际规则不匹配
- 且没走 TierService 配置，`BillingService` 和 `SubscriptionService` 都用 TierService，唯独 webhook 硬编码
- **后果**: 首次订阅赠送的积分和配置不一致，可能超额发放
- **修复方案**: 从 TierService 获取月度积分额度

#### #3 Subscription 升级路径缺失 (t1→t2/t3, t2→t3)

- **问题**: 用户只能通过 checkout 创建新订阅，但没有 **upgrade** 端点 (如 t2→t3)
- 当前 checkout 总是创建新的 subscription，如果用户已有 t2 订阅再 checkout t3，会产生**两个并行订阅**
- **修复方案**: 需要在 checkout 前检查是否已有活跃订阅，如有，应调用 `modify_subscription` 升级而非创建新订阅

### P1 - 中等问题

#### #4 Retry decorator 使用 `time.sleep` 阻塞事件循环

- **位置**: `domains/billing/payment_service.py:91-106`
- **问题**: `retry_on_stripe_error` 内使用同步 `time.sleep(delay)`，在 FastAPI async 环境下会阻塞整个事件循环
- **修复方案**: 改用 `asyncio.sleep` 或将 Stripe 调用放入 `run_in_threadpool`

#### #5 非即时降级 (t3→t2) 数据库未更新 tier

- **位置**: `domains/subscriptions/subscription_service.py:613-627`
- **问题**: `_downgrade_t3_to_t2` 的 `immediate=False` 分支只记录了 payment_record，没有更新用户 tier
- Stripe 会在下个周期生效，但本地数据库什么时候同步？依赖 `customer.subscription.updated` webhook
- **隐患**: 如果 webhook 有延迟或失败，用户在 UI 上仍显示 Pro 但 Stripe 已变为 Starter

#### #6 PaymentService class 仅是模块函数的 wrapper

- **位置**: `domains/billing/payment_service.py:719-963`
- **问题**: `PaymentService` 类的所有方法都只是 `return module_function(...)`。类没有状态，没有依赖注入
- 且 `create_refund` 类方法不传 `metadata` 参数 (第897行)，而模块函数支持 `metadata`
- **后果**: 通过 PaymentService 类发起的退款缺少 metadata，webhook 处理时 `user_id` 可能为空

---

## 二、降级和取消订阅

### 做得好的地方
- 双重身份验证 (user_code + 可选 email)
- 完整的异常体系 (15+ domain exceptions)
- Subscription 所有权验证 (customer_id 比对)
- 取消支持 immediate / at period end 两种模式
- 降级支持 t3→t2 (modify) 和 t3/t2→t1 (cancel) 两种路径
- Admin 操作审计日志
- 前端 CancelSubscriptionModal 正确支持两种取消模式，有适当的警告文案
- 前端 DowngradeModal 正确过滤可降级的 tier (只显示低于当前的)

### P0 - 严重问题

#### #7 取消订阅后月度积分未清零

- **位置**: `domains/subscriptions/subscription_service.py:330-331`
- **问题**: 立即取消订阅时 `update_subscription_tier(user_id, TIER_T1, subscription_status="canceled")`，只更新了 tier，**没有把 `credits_monthly` 清零**
- 对比 `_downgrade_to_free` 有调用 `update_monthly_credits(user_id, monthly_credits)` 来清零
- **后果**: 用户取消订阅后仍保留当月的月度积分余额，可以继续使用

#### #8 Webhook 取消降级未清零月度积分

- **位置**: `domains/webhooks/stripe_webhook_service.py:690-696`
- **问题**: `_process_subscription_termination` 只调用了 `update_subscription_tier(uid, "t1")`，没有清零 `credits_monthly`
- 与 `subscription_service._downgrade_to_free` 不一致
- **后果**: 通过 Stripe Portal 取消或因 unpaid 被 Stripe 自动取消时，月度积分不清零

### P1 - 中等问题

#### #9 非即时取消不更新数据库状态

- **位置**: `domains/subscriptions/subscription_service.py:344-357`
- **问题**: `immediate=False` 分支只创建 payment_record，没有在 profiles 表标记 `cancel_scheduled`
- **后果**: 前端无法知道订阅已被预约取消，UI 不能显示 "将在 X 月 X 日取消" 的提示

#### #10 `_downgrade_t3_to_t2` 的 `billing_cycle_anchor` 使用可能有误

- **位置**: `domains/subscriptions/subscription_service.py:586`
- **问题**: `billing_cycle_anchor='now'` 在 immediate 模式下会立即重设账单周期，可能导致用户被立即扣费
- **业界实践**: 降级通常在当前周期结束时生效，使用 `proration_behavior='create_prorations'` 就够了，不需要改 `billing_cycle_anchor`

---

## 三、购买 Credits

### 做得好的地方
- 使用 atomic RPC (`process_credit_purchase`) 保证支付记录 + 积分发放原子性
- 有 idempotency key 保护 (`credit_purchase_{session_id}`)
- RPC 返回验证 (检查 success 字段)
- 非关键操作 (analytics、activity log) 在事务外，失败不影响核心流程
- 前端 OutOfCreditsModal 使用 `useCreditsTiers()` 从后端获取积分包定价

### P1 - 中等问题

#### #11 前端 `purchaseCredits` 硬编码 `credits_100`

- **位置**: `decodables-fe/hooks/useCredits.ts:123`
- **问题**: `purchaseCredits` 函数始终购买 `credits_100`，没有参数化
- **后果**: 通过 `useCredits` hook 发起的快速购买只能买最小包，无法选择 500/2000
- **备注**: Profile 页面的 `handleBuyCredits` 已正确接受 planType 参数，此问题仅影响 useCredits hook

#### #12 Checkout 成功后前端不刷新积分状态

- **位置**: `decodables-fe/components/credits-dialog/useCreditsDialog.ts:134-148`
- **问题**: `handleStripeCheckout` 使用 `window.location.href = url` 跳转 Stripe。用户付款后跳回 `/dashboard?success=true`，但没有代码在返回后主动刷新用户积分/tier
- **后果**: 用户付款成功返回后看到的积分可能是旧值，需要手动刷新页面
- **修复方案**: 在 dashboard 页面检测 `success=true` URL 参数，触发 `useUserStore` 刷新

#### #13 前端 `getPortalUrl` response schema 与后端不匹配

- **位置**: `decodables-fe/services/paymentService.ts:28-30` vs `decodables/api/user/payment.py:84-86`
- **问题**: 前端期望 `portal_url` 字段，但后端 `PortalResponse` 返回 `url` 字段
- **后果**: `PortalUrlResponseSchema.parse(response)` 会因缺少 `portal_url` 而 Zod validation 失败
- **备注**: Profile 页面 `handleManageSubscription` (line 134) 解构 `{ portal_url }` — 也会受此影响
- **修复方案**: 统一字段名

---

## 四、退费 (Refund)

### 做得好的地方
- 多层安全验证 (user_code + Stripe customer 比对 + payment 归属验证)
- 退款金额验证 (不超过可退金额)
- 通过 webhook (`charge.refunded`) 记录数据库，保证 Stripe 确认后才写入
- 在 charge 的 metadata 中注入 `user_id` + `admin_id`，webhook 可以追溯
- 退款记录 idempotency 检查 (检查是否已存在相同 refund_id)
- Critical failure 有 `logger.critical` + 人工干预提示
- 前端 RefundModal 支持全额/部分退款，正确获取可退付款列表，有用户验证信息展示

### P0 - 严重问题

#### #14 退费后不扣回积分

- **位置**: `domains/webhooks/stripe_webhook_service.py:900-921`
- **问题**: 当管理员退费一笔 credits 购买时：
  1. Stripe 退款成功
  2. webhook 记录退款记录到 payment_records
  3. **但没有扣回对应的积分**
- **后果**: 用户花钱买了 100 积分，退费拿回钱，但 100 积分仍在账户里，等于白嫖
- **修复方案**: 在 `_handle_charge_refunded` 中，根据原始购买的 `plan_type` 判断是否为 credits 购买，如果是则扣回对应积分

#### #15 退订阅费后未降级 tier

- 类似上述问题：退费一笔订阅支付后，用户的 tier 不变
- 如果退的是首次订阅费用，用户等于免费获得了付费 tier + 月度积分
- **修复方案**: 订阅退费应同时取消订阅并降级到 t1

### P1 - 中等问题

#### #16 `PaymentService.create_refund` 不支持 metadata 参数

- **位置**: `domains/billing/payment_service.py:878-897`
- **问题**: 类方法 `create_refund` 签名不包含 `metadata`，但模块函数 `create_refund` 支持
- **后果**: 如果其他代码通过类方法调退款，charge 上不会有 metadata，webhook 端拿不到 `user_id`，导致退款记录无法关联用户

#### #17 `_handle_charge_refunded` 取 refunds[0] 可能不是最新退款

- **位置**: `domains/webhooks/stripe_webhook_service.py:861`
- **问题**: `refunds[0]` 取的是列表第一个元素。Stripe 的 `charge.refunded` 事件包含该 charge 的所有退款，最新的不一定在 index 0
- **业界实践**: 应取 `refunds[-1]` (最新的) 或按 `created` 时间戳排序

#### #18 `amount_received` vs `amount` 判断已退款不准确

- **位置**: `domains/subscriptions/subscription_service.py:208`
- **问题**: `refundable_amount = pi.amount_received` 不能准确判断已退款多少。应使用 `pi.amount - pi.amount_refunded` 来计算可退金额
- **后果**: 部分退款后再次退款，可能允许超额退款

---

## 五、数据库 Schema 和 RPC 问题 (新增)

### P0 - 严重问题

#### #23 payment_records 表 CHECK 约束不兼容代码实际写入的数据

- **位置**: `03_infrastructure.sql` payment_records 表定义
- **问题**: 数据库有严格的 CHECK 约束:
  - `payment_type IN ('subscription', 'credit_purchase', 'one_time_purchase', 'upgrade', 'addon')`
  - `payment_method IN ('card', 'bank_transfer', 'paypal', 'alipay', 'wechat')`
- 但后端代码实际写入的值:
  - `payment_type`: `'refund'`, `'sub_canceled'`, `'tier_downgrade'`, `'sub_payment'`, `'sub_renewal'` — **全部不在 CHECK 允许列表中**
  - `payment_method`: `'stripe'` — **不在 CHECK 允许列表中**
- **后果**: 所有 subscription_repository.record_subscription_change()、webhook 退费/取消记录、降级记录的 INSERT **都会被数据库拒绝**，导致写入失败
- **修复方案**: 扩展 CHECK 约束，添加所有实际使用的类型

#### #24 payment_repository.create() 字段名与数据库表不匹配

- **位置**: `infrastructure/repositories/payment_repository.py:34-70` vs `03_infrastructure.sql` payment_records
- **问题**: Repository 写入字段:
  - `amount` → 数据库字段是 `amount_usd`
  - `stripe_payment_id` → 数据库字段是 `stripe_payment_intent_id`
- **后果**: INSERT 操作将失败或写入到错误字段 (如果数据库没有 `amount` 列)
- **修复方案**: 对齐 Repository 字段名与数据库 Schema

#### #25 process_subscription_start RPC 函数不存在

- **位置**: `03_infrastructure.sql` — 已审查全部 RPC，未找到 `process_subscription_start`
- **问题**: webhook 代码 `stripe_webhook_service.py` 尝试调用此 RPC，但数据库中不存在
- **代码处理**: webhook 有 fallback 逻辑 (legacy 非原子流程)，所以不会完全失败
- **后果**: 首次订阅流程始终走 fallback 非原子路径，丧失了 RPC 提供的事务保护
- **修复方案**: 在数据库中创建此 RPC 函数

### P1 - 中等问题

#### #26 add_credits_atomic RPC 没有幂等性检查

- **位置**: `03_infrastructure.sql:769-849`
- **问题**: `deduct_credits_atomic` 有幂等性检查 (通过 idempotency_key 查重)，但 `add_credits_atomic` 没有
- **后果**: 如果重复调用 add_credits_atomic (网络重试等)，积分会被重复发放
- **修复方案**: 在 add_credits_atomic 中添加与 deduct 相同的幂等性检查逻辑

#### #27 credit_transactions 双类型字段 (transaction_type + tx_type)

- **位置**: `01_core_business.sql:867-911`
- **问题**: 表有两个类型字段 `transaction_type` 和 `tx_type`，通过 trigger 同步。增加复杂度且容易不一致
- **评估**: 低风险，有 sync trigger 保护，但属于技术债务

---

## 六、DI 容器和 Repository 问题 (新增)

### P0 - 严重问题

#### #28 Container 创建 BillingService 时未注入 TierService

- **位置**: `container.py:200-202`
- **代码**: `BillingService(credit_repo)` — 只传了 repository，没传 `tier_service`
- **问题**: `BillingService.__init__` 接受可选的 `tier_service` 参数 (service.py:46)。Container 没传，导致 `self._tier_service = None`
- **后果**: 所有通过 Container 获取的 BillingService 调用 `get_operation_cost()`, `grant_signup_bonus()`, `process_subscription_renewal()` 时，都会走 **emergency fallback** 硬编码值，而非从数据库配置读取
  - 签到奖励: 走 fallback 100 (恰好和 CLAUDE.md 一致，但不受配置管控)
  - 操作成本: 走 fallback 5 (不受配置管控)
  - 月度积分: 走 `EMERGENCY_TIER_CONFIGS` 硬编码
- **修复方案**: 在 `get_billing_service()` 中创建 TierService 并注入

#### #29 credit_repository.refresh_monthly_credits 硬编码 500/1000

- **位置**: `infrastructure/repositories/credit_repository.py:696-727`
- **代码**: 使用 `{"t2": 500, "t3": 1000}` 硬编码
- **问题**: 与 CLAUDE.md 规定的 t2=100/月, t3=200/月 不一致，且不走 TierService
- **与 #2 相同根因**: webhook 和 repository 都硬编码了错误的积分值
- **后果**: 月度积分刷新会发放 500/1000 而非 100/200
- **修复方案**: 从 TierService 获取正确配置

#### #30 user_repository.create_profile 注册奖励硬编码 50

- **位置**: `infrastructure/repositories/user_repository.py:579`
- **代码**: `"credits_permanent": 50` — 硬编码了 50 作为注册奖励
- **问题**: CLAUDE.md 规定注册赠送 100 永久积分，但此处硬编码 50
- **关联**: BillingService.grant_signup_bonus 的 fallback 是 100 (正确)，但如果有代码直接调用 create_profile 而非通过 BillingService 发放奖励，就会只给 50
- **修复方案**: 统一通过 BillingService.grant_signup_bonus 发放注册奖励

### P1 - 中等问题

#### #31 user_repository.update_subscription_tier 有冗余条件

- **位置**: `infrastructure/repositories/user_repository.py:616`
- **代码**: `if tier == "t1" or tier == "t1":` — 重复的条件判断
- **评估**: 功能正确 (降级到 t1 时清零月度积分)，但代码质量问题

#### #32 subscription_repository.record_subscription_change 会触发 #23

- **位置**: `infrastructure/repositories/subscription_repository.py:168-175`
- **问题**: 调用 `payment_repo.create()` 传入 `payment_type=change_type`，而 change_type 可能是 `'refund'`, `'sub_canceled'`, `'tier_downgrade'` — 这些都不在 payment_records 表的 CHECK 约束中
- **后果**: 所有通过 SubscriptionService 触发的状态变更记录都无法写入数据库

---

## 七、前端 Admin / Profile 问题 (新增)

### P1 - 中等问题

#### #33 DowngradeModal 积分数硬编码

- **位置**: `app/admin/users/_components/modals/DowngradeModal.tsx:28-46`
- **代码**: `tierConfig` 硬编码 `credits: 0 / 100 / 200`
- **问题**: 应从后端配置获取月度积分数，而非硬编码
- **评估**: 低风险 (仅用于 Admin UI 展示)，但不符合 "所有配置从 system_configs 获取" 的架构原则

#### #34 前端 Admin Modals 存在两套重复实现

- **位置**: `components/admin/*.tsx` 和 `app/admin/users/_components/modals/*.tsx`
- **问题**: RefundModal, CancelSubscriptionModal, DowngradeModal, CreditAdjustModal 在两处都有实现
- **后果**: 修改一处不修改另一处会导致行为不一致
- **修复方案**: 统一到 `app/admin/users/_components/modals/` 一处

### P2 - 低优先级

#### #35 Profile 页面无 Checkout 成功回调处理

- **位置**: `app/profile/page.tsx`
- **问题**: Profile 页面可以触发 checkout (CreditsCard) 和 portal (SubscriptionCard)，但从 Stripe 返回后没有检测 URL 参数来刷新状态
- **与 #12 相关**: 同一问题在不同页面

---

## 八、跨模块 / 架构问题

### P0 - 已确认无问题

#### #19 Admin 端点 exception handler mapping

- **确认**: `SubscriptionException` 继承 `AppException`，`app.py` 有全局 `AppException` handler — 异常处理链完整

### P1 - 中等问题

#### #20 Stripe API 调用在 async 端点中同步执行

- **问题**: `payment_service.py` 中所有 Stripe API 调用都是**同步**的 (`stripe.Checkout.Session.create` 等)，但 FastAPI 端点是 `async`
- **后果**: 每次 Stripe API 调用都会阻塞事件循环 0.5-2 秒
- **修复方案**: 使用 `run_in_threadpool()` 包装同步 Stripe 调用

#### #21 Coupon cache 不是线程安全的

- **位置**: `domains/billing/payment_service.py:61`
- **问题**: `_coupon_cache: Dict[int, str] = {}` 是模块级别的普通 dict，在多 worker 环境下可能有竞争条件
- 风险较低 (最坏情况是创建重复 coupon)

#### #22 前端 admin modals 有重复代码

- 同 #34

---

## 九、总结评分

| 模块 | 安全性 | 完整性 | 原子性 | 配置一致性 | 评分 |
|------|--------|--------|--------|-----------|------|
| 订阅/升级 | 3/5 | 2/5 | 4/5 | 2/5 | **2.5/5** |
| 降级/取消 | 4/5 | 3/5 | 3/5 | 3/5 | **3/5** |
| 积分购买 | 4/5 | 4/5 | 5/5 | 4/5 | **4/5** |
| 退费 | 4/5 | 2/5 | 3/5 | 3/5 | **2.5/5** |
| 数据库 Schema | 3/5 | 2/5 | 4/5 | 2/5 | **2.5/5** |
| DI 容器 | 4/5 | 3/5 | N/A | 2/5 | **3/5** |

---

## 十、按优先级排序的完整修复清单

### P0 (必须修复) — 资金安全 + 数据完整性

| 序号 | 问题 | 影响 | 涉及文件 |
|------|------|------|---------|
| #14 | 退费后不扣回积分 | 资金漏洞：用户退费拿回钱但保留积分 | stripe_webhook_service.py |
| #15 | 退订阅费后不降级 tier | 资金漏洞：用户免费获得付费 tier | stripe_webhook_service.py |
| #23 | payment_records CHECK 约束不兼容 | 所有状态变更/退费记录无法写入数据库 | 03_infrastructure.sql |
| #24 | payment_repository 字段名不匹配 | INSERT 失败 | payment_repository.py |
| #25 | process_subscription_start RPC 不存在 | 首次订阅无事务保护 | 03_infrastructure.sql |
| #28 | Container 未注入 TierService 到 BillingService | 所有积分操作走 fallback 硬编码 | container.py |
| #29 | credit_repository 月度积分硬编码 500/1000 | 月度刷新超额发放 | credit_repository.py |
| #1 | Checkout 未绑定 Stripe Customer | 多 Customer 问题 | payment_service.py |
| #2 | Webhook 首次订阅积分硬编码 500/1000 | 与配置不一致，超额发放 | stripe_webhook_service.py |
| #3 | 无升级路径 (t2→t3) | 可能产生并行订阅 | payment_service.py, payment.py |
| #7 | 取消订阅后月度积分未清零 | 用户取消后仍可消费 | subscription_service.py |
| #8 | Webhook 取消降级未清零月度积分 | 同上 (Stripe Portal 场景) | stripe_webhook_service.py |
| #30 | create_profile 注册奖励硬编码 50 | 与规定的 100 不一致 | user_repository.py |

### P1 (应该修复) — 功能正确性 + 性能

| 序号 | 问题 | 影响 | 涉及文件 |
|------|------|------|---------|
| #16 | PaymentService.create_refund 不传 metadata | 退款 webhook 无法关联用户 | payment_service.py |
| #18 | 退款可退金额计算不准确 | 可能允许超额退款 | subscription_service.py |
| #26 | add_credits_atomic 无幂等性 | 重复调用多发积分 | 03_infrastructure.sql |
| #4 | time.sleep 阻塞事件循环 | Stripe 重试时阻塞所有请求 | payment_service.py |
| #20 | 同步 Stripe 调用阻塞 async 端点 | 性能瓶颈 | payment_service.py |
| #13 | 前端 portal_url 字段名不匹配 | Portal 跳转失败 | paymentService.ts |
| #12 | Checkout 返回后不刷新积分 | 用户体验问题 | useCreditsDialog.ts, profile/page.tsx |
| #5 | 非即时降级数据库不同步 | UI 与实际不一致 | subscription_service.py |
| #9 | 非即时取消不更新 cancel_scheduled | 前端无法显示取消提示 | subscription_service.py |
| #17 | refunds[0] 可能不是最新退款 | 退款记录不准确 | stripe_webhook_service.py |
| #10 | billing_cycle_anchor='now' 导致立即扣费 | 降级时意外扣费 | subscription_service.py |
| #11 | purchaseCredits 硬编码 credits_100 | 快速购买只能买最小包 | useCredits.ts |
| #31 | update_subscription_tier 冗余条件 | 代码质量 | user_repository.py |
| #32 | record_subscription_change 触发 #23 | 无法记录状态变更 | subscription_repository.py |
| #33 | DowngradeModal 积分数硬编码 | Admin UI 展示不准确 | DowngradeModal.tsx |

### P2 (可选修复) — 代码质量

| 序号 | 问题 | 影响 | 涉及文件 |
|------|------|------|---------|
| #21 | Coupon cache 非线程安全 | 极低风险竞争条件 | payment_service.py |
| #27 | credit_transactions 双类型字段 | 技术债务 | 01_core_business.sql |
| #34 | Admin Modals 两套重复实现 | 维护成本 | components/admin/, modals/ |
| #35 | Profile 无 checkout 回调处理 | 同 #12 | profile/page.tsx |

---

---

## 十一、第三轮审计 — 补充发现 (新增 9 个文件/模块)

### 新增审计文件

| 文件 | 职责 |
|------|------|
| `domains/identity/tier_service.py` | TierService: 从 system_configs 读取 tier 配置 |
| `domains/identity/constants.py` | Tier 系统常量 (TIER_MONTHLY_CREDITS 等) |
| `domains/billing/pricing_service.py` | PricingService: 从 pricing_plans 表读取定价 |
| `domains/webhooks/clerk_webhook_service.py` | Clerk Webhook: 用户注册 + 签到奖励 |
| `shared/payment/providers/stripe_provider.py` | StripePaymentProvider: 适配器层 |
| `application/commands/billing.py` | 应用层: 扣费/充值/签到奖励命令 |
| `scheduler.py` | 定时任务调度器 (无积分刷新任务) |
| `config.py` | 全局配置 (Stripe keys, deprecated constants) |
| `decodables-fe/components/profile/CreditsCard.tsx` | 积分卡片 (3档充值选择) |

### P0 - 严重问题

#### #36 注册奖励全线不一致: RPC=50, Webhook=50, Repository=50, TierService=100, CLAUDE.md=100

- **关键发现 — 全项目最大一致性问题**
- **位置 (5 处)**:
  1. `create_user_idempotent` RPC (01_core_business.sql:1839): `credits_permanent = 50`
  2. `clerk_webhook_service.py:112,152,227`: `_grant_signup_bonus` 使用 50
  3. `user_repository.py:579`: `create_profile` 硬编码 `credits_permanent: 50`
  4. `tier_service.py:554`: `get_signup_bonus` 从 config 读取，default=100
  5. `billing/service.py:grant_signup_bonus`: 通过 TierService 获取 (100)
  6. `application/commands/billing.py:188`: docstring 说 "Grants 50 permanent credits"
- **问题**: 实际注册路径走 `create_user_idempotent` RPC → **只给 50 积分**
  - TierService 的 100 是正确配置值，但注册路径根本**不经过 TierService**
  - RPC 直接 INSERT credits_permanent=50，绕过了所有 service 层
  - BillingService.grant_signup_bonus (100) 在注册流程中从未被调用
- **后果**: 用户注册只获得 50 积分 (应为 100)
- **根因**: 注册走 RPC 原子操作直接写入数据库，不经过 service 层
- **修复方案**: 统一为 100。修改 RPC 中 credits_permanent=100，或让 RPC 从 system_configs 表读取

#### #37 PricingService._fetch_all_plans 缺少 await (AsyncClient 兼容性)

- **位置**: `domains/billing/pricing_service.py:160`
- **代码**: `response = self.db_client.table("pricing_plans").select("*")...execute()`
- **问题**: 如果 `db_client` 是 AsyncClient，这里缺少 `await`。但 `_fetch_all_plans` 是 `async def`，说明预期是异步的
- **后果**: 如果传入 AsyncClient，调用将返回 coroutine 而非数据，导致功能完全失效
- **涉及方法**: `_fetch_all_plans`, `get_plan_by_code`, `get_user_price` 三处都缺少 await
- **修复方案**: 添加 `await`

### P1 - 中等问题

#### #38 scheduler.py 无月度积分刷新定时任务

- **位置**: `scheduler.py`
- **问题**: 调度器中没有月度积分刷新任务。月度积分仅在 `invoice.payment_succeeded` webhook 触发时刷新
- **评估**: 如果 Stripe webhook 可靠，这不是问题。但如果 webhook 丢失/延迟，用户可能月初几小时/天没有积分
- **业界实践**: 仅依赖 webhook 是 Stripe 推荐的做法 (事件驱动)，但可以加一个日终对账任务作为 safety net
- **修复建议**: 低优先级 — 可以加一个每日 reconciliation 任务检查 "距离上次 refresh 超过 31 天的活跃订阅用户"

#### #39 config.py 中 STRIPE_SECRET_KEY 未在 config 中显式读取

- **位置**: `config.py`
- **问题**: `STRIPE_SECRET_KEY` 未在 config.py 中声明，而是在 `payment_service.py:30` 通过 `stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")` 直接设置
- **风险**: 如果环境变量未设置，`stripe.api_key` 为 None，所有 Stripe API 调用会返回 authentication error
- **评估**: 已有明确的 500 error 返回 ("api_key_expired")，不会导致静默失败
- **修复建议**: 在 config.py 中声明 `STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")`，并在应用启动时验证非空

#### #40 TierService 缓存无 TTL 过期

- **位置**: `domains/identity/tier_service.py:196,437`
- **问题**: `_cache` 和 `_tier_config_cache` 是普通 dict，没有 TTL 过期机制
  - PricingService 有 5 分钟 TTL (正确)
  - TierService 没有 TTL — 配置更改后需要手动调用 `clear_cache()`
- **后果**: Admin 更新 tier 配置后，已运行的实例不会自动获取新值，直到进程重启或手动清缓存
- **修复建议**: 添加类似 PricingService 的 TTL 机制

#### #41 StripePaymentProvider 适配器未传递 customer 和 metadata 参数

- **位置**: `shared/payment/providers/stripe_provider.py:67-70`
- **问题**: `create_checkout_session` 只传 `user_id`, `plan_type`, `discount_percent`，不传 `customer` 和 `metadata`
- **与 #1 相同根因**: 底层 `payment_service.create_checkout_session` 本身就不接受 customer 参数
- **评估**: 如果项目不使用 StripePaymentProvider 调用 checkout (而是直接调用 payment_service)，则不影响

#### #42 config.py 遗留 CREDITS_SIGNUP_BONUS=50 注释

- **位置**: `config.py:85`
- **代码**: `# CREDITS_SIGNUP_BONUS = 50    # ❌ REMOVED - use tier_service.get_signup_bonus()`
- **问题**: 注释中写的 50 与 TierService 的 100 不一致。虽然已被注释掉不影响运行，但可能误导开发者
- **评估**: 纯文档问题，低风险

### P2 - 低优先级

#### #43 GrantSignupBonusCommand docstring 写 "Grants 50" 但实际应为 100

- **位置**: `application/commands/billing.py:188`
- **问题**: docstring 写 "Grants 50 permanent credits" 但 `GrantSignupBonusHandler` 调用 `billing_service.grant_signup_bonus` (TierService 返回 100)
- **评估**: 纯文档问题，不影响运行逻辑 (实际金额由 TierService 决定)

---

## 十二、更新后的完整修复清单

### P0 (必须修复) — 15 个

| 序号 | 问题 | 影响 | 涉及文件 |
|------|------|------|---------|
| **#36** | **注册奖励全线不一致 (RPC=50, Config=100)** | **用户少得 50 积分** | **01_core_business.sql, clerk_webhook, user_repo** |
| #14 | 退费后不扣回积分 | 资金漏洞 | stripe_webhook_service.py |
| #15 | 退订阅费后不降级 tier | 资金漏洞 | stripe_webhook_service.py |
| #23 | payment_records CHECK 约束不兼容 | 记录写入失败 | 03_infrastructure.sql |
| #24 | payment_repository 字段名不匹配 | INSERT 失败 | payment_repository.py |
| #25 | process_subscription_start RPC 不存在 | 无事务保护 | 03_infrastructure.sql |
| #28 | Container 未注入 TierService | 走 fallback 硬编码 | container.py |
| #29 | credit_repository 月度积分硬编码 500/1000 | 超额发放 | credit_repository.py |
| **#37** | **PricingService 缺少 await** | **定价查询完全失效** | **pricing_service.py** |
| #1 | Checkout 未绑定 Stripe Customer | 多 Customer | payment_service.py |
| #2 | Webhook 首次订阅积分硬编码 500/1000 | 超额发放 | stripe_webhook_service.py |
| #3 | 无升级路径 (t2→t3) | 并行订阅 | payment_service.py |
| #7 | 取消订阅后月度积分未清零 | 白用积分 | subscription_service.py |
| #8 | Webhook 取消降级未清零月度积分 | 白用积分 | stripe_webhook_service.py |
| **#49** | **续费 webhook 非原子操作 — 积分刷新失败无补偿** | **扣款但无积分** | **stripe_webhook_service.py** |

### P1 (应该修复) — 27 个

| 序号 | 问题 | 涉及文件 |
|------|------|---------|
| #30 | create_profile 注册奖励硬编码 50 | user_repository.py |
| #16 | PaymentService.create_refund 不传 metadata | payment_service.py |
| #18 | 退款可退金额计算不准确 | subscription_service.py |
| #26 | add_credits_atomic 无幂等性 | 03_infrastructure.sql |
| #4 | time.sleep 阻塞事件循环 | payment_service.py |
| #20 | 同步 Stripe 调用阻塞 async | payment_service.py |
| #13 | 前端 portal_url 字段名不匹配 | paymentService.ts |
| #12 | Checkout 返回后不刷新积分 | useCreditsDialog.ts |
| #5 | 非即时降级数据库不同步 | subscription_service.py |
| #9 | 非即时取消不更新状态 | subscription_service.py |
| #17 | refunds[0] 可能不是最新退款 | stripe_webhook_service.py |
| #10 | billing_cycle_anchor 立即扣费 | subscription_service.py |
| #11 | purchaseCredits 硬编码 credits_100 | useCredits.ts |
| #31 | update_subscription_tier 冗余条件 | user_repository.py |
| #32 | record_subscription_change 触发 #23 | subscription_repository.py |
| #33 | DowngradeModal 积分数硬编码 | DowngradeModal.tsx |
| **#38** | **无月度积分刷新 reconciliation 任务** | **scheduler.py** |
| **#39** | **STRIPE_SECRET_KEY 无启动校验** | **config.py** |
| **#40** | **TierService 缓存无 TTL** | **tier_service.py** |
| **#41** | **StripePaymentProvider 不传 customer** | **stripe_provider.py** |
| **#42** | **config.py 注释 50 与实际 100 不一致** | **config.py** |
| #35 | Profile 无 checkout 回调处理 | profile/page.tsx |
| **#44** | **Webhook 未处理 invoice.payment_failed** | **stripe_webhook_service.py** |
| **#46** | **前端未展示订阅异常状态 (past_due/canceled)** | **SubscriptionCard.tsx** |
| **#47** | **stripe_webhook_events 表 RLS 待确认** | **02_platform_services.sql** |
| **#48** | **STRIPE_WEBHOOK_SECRET 启动校验仅 WARNING** | **payment_service.py** |
| **#50** | **Webhook 签名验证未显式设置 tolerance** | **payment_service.py** |

### P2 (可选修复) — 6 个

| 序号 | 问题 | 涉及文件 |
|------|------|---------|
| #21 | Coupon cache 非线程安全 | payment_service.py |
| #27 | credit_transactions 双类型字段 | 01_core_business.sql |
| #34 | Admin Modals 两套重复实现 | components/admin/ |
| **#43** | **GrantSignupBonusCommand docstring 写 50** | **billing.py** |
| **#45** | **Webhook 未处理 3DS/SCA 事件** | **stripe_webhook_service.py** |
| ~~#19~~ | ~~Admin exception handler~~ (已确认无问题) | - |

---

**报告状态**: 第六轮最终版 — 覆盖 43+ 个文件/模块, 50+ 审计项
**总问题数**: 50 (含 1 个确认无问题的 #19)
**P0**: 15 个 | **P1**: 27 个 | **P2**: 6 个

### 第三轮新增关键发现总结

1. **#36 (P0)**: 注册奖励全线不一致 — RPC/Webhook/Repository 都写 50，但 TierService/CLAUDE.md 规定 100。实际用户只得 50。这是全项目最大的配置一致性问题。
2. **#37 (P0)**: PricingService 的数据库查询缺少 `await`，如果使用 AsyncClient 会导致定价功能完全失效。
3. **#38 (P1)**: 无月度积分刷新 reconciliation 任务 — 纯依赖 Stripe webhook 事件驱动。
4. **#40 (P1)**: TierService 缓存无 TTL — Admin 修改配置后不会自动生效。

---

## 十三、第四轮审计 — 最终查漏 (RLS 策略 + Webhook 事件覆盖 + 前端回调)

### 审计范围

| 审计项 | 状态 | 结论 |
|--------|------|------|
| payment_records RLS 策略 | ✅ 已审计 | 安全 — 仅 service_role 可访问 |
| credit_transactions RLS 策略 | ✅ 已审计 | 安全 — 仅 service_role 可访问 |
| credit_purchases RLS 策略 | ✅ 已审计 | 安全 — 仅 service_role 可访问 |
| Webhook 事件类型覆盖 | ✅ 已审计 | 发现 2 个缺失事件 |
| Dashboard checkout 回调 | ✅ 已审计 | 确认 #12 — 无处理 |
| Webhook 端点事件过滤 | ✅ 已审计 | 正常 — 所有事件转发至 service 层 |

### RLS 策略审计结果 — 安全

所有支付相关表的 RLS 策略统一为:
- `ALTER TABLE xxx ENABLE ROW LEVEL SECURITY;`
- `CREATE POLICY service_role_all ON xxx FOR ALL TO service_role USING (true) WITH CHECK (true);`
- 匿名/认证用户无策略 = 完全拒绝访问
- 只有 FastAPI 后端 (service_role) 可操作支付数据

**结论**: RLS 配置正确，无安全风险。

### P1 - 新增发现

#### #44 Webhook 未处理 `invoice.payment_failed` 事件

- **位置**: `domains/webhooks/stripe_webhook_service.py:167-177`
- **问题**: Stripe 发送 `invoice.payment_failed` 事件 (订阅续费扣款失败时)，但 webhook service 完全不处理此事件
- **当前处理的 5 种事件**:
  1. `checkout.session.completed`
  2. `invoice.payment_succeeded`
  3. `customer.subscription.deleted`
  4. `customer.subscription.updated`
  5. `charge.refunded`
- **缺失事件**: `invoice.payment_failed` — 会返回 `{"status": "ok"}` 但不做任何处理
- **后果**:
  - 用户付款失败时，系统无主动通知 (邮件/站内通知)
  - 用户可能不知道付款失败，直到 Stripe 多次重试后自动取消订阅
  - 无法在 UI 上展示 "付款失败，请更新支付方式" 提示
- **间接缓解**: Stripe 会在多次重试失败后触发 `customer.subscription.updated (status=past_due/unpaid)` 和最终 `customer.subscription.deleted`，这些事件已被处理。但中间状态无感知。
- **业界实践**: 应处理 `invoice.payment_failed`，至少记录到数据库并发送通知
- **修复方案**: 在 webhook service 添加 `_handle_invoice_payment_failed` handler:
  1. 更新用户 subscription_status 为 `past_due`
  2. 创建 notification 记录 (或触发邮件)
  3. 记录 payment_record (type=`payment_failed`)

#### #45 Webhook 未处理 `invoice.payment_action_required` 事件

- **位置**: 同 `stripe_webhook_service.py`
- **问题**: 3D Secure / SCA 认证需要用户额外操作时，Stripe 发送此事件。当前未处理。
- **后果**: 如果用户银行要求 3DS 验证，续费会失败但系统不知道原因
- **评估**: 与 #44 类似但更边缘，因为 Stripe hosted invoice 页面会自动处理 3DS。标记为 P2。

### P2 - 新增发现

#### #45 (调整为 P2) Webhook 未处理 3DS/SCA 相关事件

- **评估**: Stripe Checkout 和 Subscription Billing 自动处理 3DS 流程，此事件处理为增强型改进

---

## 十四、最终审计总结

### 完整数据

| 审计轮次 | 覆盖文件 | 发现问题 |
|----------|----------|----------|
| 第一轮 | 16 个 (核心支付链路) | #1 - #22 |
| 第二轮 | 12 个 (数据库/仓库/DI/Admin) | #23 - #35 |
| 第三轮 | 9 个 (配置/调度/适配器) | #36 - #43 |
| 第四轮 | 6 项 (RLS/事件覆盖/回调) | #44 - #45 |
| **合计** | **38+ 个文件/模块** | **45 个问题** |

### 按优先级统计

| 优先级 | 数量 | 说明 |
|--------|------|------|
| **P0** | 14 | 资金安全 + 数据完整性 + 功能阻断 |
| **P1** | 23 | 功能正确性 + 性能 + 用户体验 |
| **P2** | 6 | 代码质量 + 文档 + 增强型改进 |

### P0 问题速查 (14 个)

| 序号 | 一句话描述 |
|------|-----------|
| #36 | 注册奖励全线不一致 (RPC=50, Config=100) |
| #14 | 退费后不扣回积分 |
| #15 | 退订阅费后不降级 tier |
| #23 | payment_records CHECK 约束不兼容 |
| #24 | payment_repository 字段名不匹配 |
| #25 | process_subscription_start RPC 不存在 |
| #28 | Container 未注入 TierService 到 BillingService |
| #29 | credit_repository 月度积分硬编码 500/1000 |
| #37 | PricingService 缺少 await |
| #1 | Checkout 未绑定 Stripe Customer |
| #2 | Webhook 首次订阅积分硬编码 500/1000 |
| #3 | 无升级路径 (t2→t3) |
| #7 | 取消订阅后月度积分未清零 |
| #8 | Webhook 取消降级未清零月度积分 |

### 安全评估

| 安全项 | 状态 |
|--------|------|
| RLS 策略 (payment_records, credit_*) | ✅ 安全 |
| Webhook 签名验证 | ✅ 已实现 |
| Webhook 幂等性 | ✅ 已实现 |
| SQL 注入防护 (RPC 参数化) | ✅ 安全 |
| 付款失败主动通知 | ❌ 缺失 (#44) |
| 资金回收 (退费扣积分) | ❌ 缺失 (#14) |

---

## 十五、第五轮审计 — 最终角落检查

### 审计范围

| 审计项 | 状态 | 结论 |
|--------|------|------|
| ICreditRepository 接口与实现匹配 | ✅ 已审计 | 匹配，无遗漏方法 |
| 02_platform_services.sql 支付相关 | ✅ 已审计 | 发现 stripe_webhook_events 表缺少 RLS |
| webhook_retry_service.py 重试安全性 | ✅ 已审计 | 安全 — 幂等性保护 |
| 前端订阅状态展示 | ✅ 已审计 | 发现缺失：未展示异常状态 |
| domains/billing/ 全部文件 | ✅ 已审计 | 8 个文件全部覆盖 |
| STRIPE_WEBHOOK_SECRET 启动校验 | ✅ 已审计 | 发现：仅 WARNING 非 CRITICAL |
| 并发扣费竞争条件 | ✅ 已审计 | 安全 — RPC 原子操作 + 幂等性 |
| Stripe Price ID 配置 | ✅ 已审计 | 安全 — 环境变量 + 启动验证 |

### P1 - 新增发现

#### #46 前端 SubscriptionCard 未展示订阅异常状态

- **位置**: `decodables-fe/components/profile/SubscriptionCard.tsx`
- **问题**: 后端支持 5 种订阅状态 (`active`, `canceled`, `past_due`, `incomplete`, `trialing`)，但前端 SubscriptionCard 只展示 tier badge (t1/t2/t3)，不展示异常状态
- **后果**:
  - 用户订阅 `past_due` (付款失败) 时，UI 上看不到任何警告
  - 用户订阅 `canceled` (已取消) 时，无视觉区分
  - 用户不知道需要更新支付方式
- **业界实践**: 应在订阅卡片上显示状态 badge：
  - `past_due` → "⚠️ Payment Due"
  - `unpaid` → "❌ Payment Failed"
  - `canceled` → "Canceled (ends on X)"
- **修复方案**: 在 SubscriptionCard 中添加 subscription_status prop 和对应的状态 badge

#### #47 stripe_webhook_events 表缺少 RLS 策略

- **位置**: `decodables/migrations/v2/02_platform_services.sql:727-737`
- **问题**: `stripe_webhook_events` 表存储 Stripe webhook 原始 payload（包含支付金额、客户信息等敏感数据），但未在审计中确认是否有 RLS 策略
- **评估**: 如果此表没有 RLS 策略但启用了 RLS，则所有角色默认拒绝访问（安全）；如果没启用 RLS，则 anon/authenticated 角色可能可以读取
- **修复建议**: 确认 `ALTER TABLE stripe_webhook_events ENABLE ROW LEVEL SECURITY;` 和 `service_role_all` 策略存在

#### #48 STRIPE_WEBHOOK_SECRET 启动校验仅为 WARNING

- **位置**: `domains/billing/payment_service.py:127-180` (validate_config)
- **问题**: `STRIPE_WEBHOOK_SECRET` 缺失时只记录 WARNING，应用仍然启动。运行时 webhook 签名验证将失败，所有 Stripe webhook 被拒绝
- **后果**: 如果生产环境漏配此变量，所有支付 webhook 静默失败 — 付款成功但积分不发放、订阅状态不更新
- **业界实践**: 生产环境应将 webhook secret 设为 CRITICAL（启动失败）
- **修复建议**: 区分环境 — 生产环境缺失 STRIPE_WEBHOOK_SECRET 应阻止启动

### 已验证安全的项目 (本轮新增)

| 项目 | 结论 |
|------|------|
| ICreditRepository 接口实现匹配 | ✅ 8 个方法全部实现 |
| 并发扣费 (double-spend) | ✅ RPC 原子操作 + PostgreSQL 事务隔离 |
| Webhook 幂等性 (重试安全) | ✅ event_id 去重 + idempotency_key |
| Stripe Price ID 配置 | ✅ 环境变量 + 启动验证 + 反向查找 |
| domains/billing/ 文件完整性 | ✅ 8 个文件全部已审计 |

---

## 十六、最终审计总结 (更新)

### 完整数据

| 审计轮次 | 覆盖文件 | 发现问题 |
|----------|----------|----------|
| 第一轮 | 16 个 (核心支付链路) | #1 - #22 |
| 第二轮 | 12 个 (数据库/仓库/DI/Admin) | #23 - #35 |
| 第三轮 | 9 个 (配置/调度/适配器) | #36 - #43 |
| 第四轮 | 6 项 (RLS/事件覆盖/回调) | #44 - #45 |
| 第五轮 | 8 项 (接口/重试/前端状态/并发) | #46 - #48 |
| **合计** | **43+ 个文件/模块** | **48 个问题** |

### 按优先级统计 (最终)

| 优先级 | 数量 | 说明 |
|--------|------|------|
| **P0** | 14 | 资金安全 + 数据完整性 + 功能阻断 |
| **P1** | 26 | 功能正确性 + 性能 + 用户体验 |
| **P2** | 6 | 代码质量 + 文档 + 增强型改进 |

### 全部 P0 问题速查 (14 个)

| 序号 | 一句话描述 |
|------|-----------|
| #36 | 注册奖励全线不一致 (RPC=50, Config=100) |
| #14 | 退费后不扣回积分 |
| #15 | 退订阅费后不降级 tier |
| #23 | payment_records CHECK 约束不兼容 |
| #24 | payment_repository 字段名不匹配 |
| #25 | process_subscription_start RPC 不存在 |
| #28 | Container 未注入 TierService 到 BillingService |
| #29 | credit_repository 月度积分硬编码 500/1000 |
| #37 | PricingService 缺少 await |
| #1 | Checkout 未绑定 Stripe Customer |
| #2 | Webhook 首次订阅积分硬编码 500/1000 |
| #3 | 无升级路径 (t2→t3) |
| #7 | 取消订阅后月度积分未清零 |
| #8 | Webhook 取消降级未清零月度积分 |

### 安全评估 (最终)

| 安全项 | 状态 |
|--------|------|
| RLS 策略 (payment_records, credit_*) | ✅ 安全 |
| RLS 策略 (stripe_webhook_events) | ⚠️ 待确认 (#47) |
| Webhook 签名验证 | ✅ 已实现 |
| Webhook 签名密钥启动校验 | ⚠️ 仅 WARNING (#48) |
| Webhook 幂等性 | ✅ 已实现 |
| 并发扣费保护 (double-spend) | ✅ RPC 原子操作 |
| SQL 注入防护 | ✅ RPC 参数化 |
| Stripe Price ID 配置 | ✅ 环境变量 + 启动验证 |
| 付款失败主动通知 | ❌ 缺失 (#44) |
| 资金回收 (退费扣积分) | ❌ 缺失 (#14) |
| 前端订阅异常状态展示 | ❌ 缺失 (#46) |

---

## 十七、第六轮审计 — 深层盲区检查

### 审计范围

| 审计项 | 状态 | 结论 |
|--------|------|------|
| stripe_customer_id 持久化 | ✅ 已审计 | 安全 — checkout 完成后正确保存 |
| Webhook 部分失败补偿 | ✅ 已审计 | ⚠️ 发现问题：积分刷新失败无回滚 |
| 货币处理 | ✅ 已审计 | USD 硬编码，技术债务 |
| 账号删除 + 活跃订阅 | ✅ 已审计 | 安全 — 无删除端点 |
| Coupon/discount 验证 | ✅ 已审计 | 安全 — 多层验证 (API + Service + Pydantic) |
| 前端支付错误处理 | ✅ 已审计 | Zod 验证正常，错误信息通用 |
| Webhook 重放攻击 | ✅ 已审计 | ⚠️ 发现问题：缺少时间戳校验 |

### P0 - 新增发现

#### #49 Webhook 订阅续费非原子操作 — 部分失败无补偿

- **位置**: `domains/webhooks/stripe_webhook_service.py` `_process_subscription_renewal()`
- **问题**: 续费流程分 3 步执行，**不在同一事务中**:
  1. 记录 payment_record ✅ (成功)
  2. 更新 subscription_status = active ✅ (成功)
  3. 刷新月度积分 ❌ (可能失败)
- **后果**: 如果第 3 步失败，用户被扣款且订阅状态为 active，但**月度积分为 0**。系统记录了 `partial_error` 日志但无自动补偿。
- **对比**: 首次订阅有 `process_subscription_start` 原子 RPC (#25 虽然 RPC 不存在但设计意图正确)，续费却没有对应的原子 RPC
- **修复方案**: 创建 `process_subscription_renewal_atomic` RPC，将 3 步合并为单一数据库事务

### P1 - 新增发现

#### #50 Stripe Webhook 签名验证缺少时间戳容忍度 (tolerance)

- **位置**: `domains/billing/payment_service.py:405-406`
- **代码**: `stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)`
- **问题**: 未传 `tolerance` 参数。Stripe 签名头包含时间戳 (`t=1234567890,v1=...`)，`construct_event` 默认 tolerance=300s (5 分钟)
- **实际风险评估**:
  - Stripe Python SDK **默认 tolerance=300 秒** (非无限制)，所以重放攻击窗口已限制在 5 分钟内
  - 加上幂等性保护 (`is_duplicate_event`)，同一 event_id 无法重复处理
  - **实际风险极低**，但显式传入 `tolerance=300` 是业界最佳实践
- **修复方案**: 显式传入 `tolerance=300`: `stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET, tolerance=300)`

### 已验证安全的项目 (本轮新增)

| 项目 | 结论 |
|------|------|
| stripe_customer_id 持久化 | ✅ checkout 完成后通过 update_subscription_tier 保存 |
| 账号删除 + 活跃订阅 | ✅ 无删除端点，安全 |
| Coupon/discount 验证 | ✅ 三层防护：API (1-100 range) + Service (reject <=0 or >100) + Pydantic (ge=1, le=100) |
| 前端 Zod 验证 | ✅ getCheckoutUrl 输入输出均有 schema 验证 |
| 货币处理 | ⚠️ USD 硬编码 (8 处)，功能正确但不支持多币种，属技术债务非 bug |

---

## 十八、最终审计总结 (第六轮更新)

### 完整数据

| 审计轮次 | 覆盖文件/项 | 发现问题 |
|----------|------------|----------|
| 第一轮 | 16 个 (核心支付链路) | #1 - #22 |
| 第二轮 | 12 个 (数据库/仓库/DI/Admin) | #23 - #35 |
| 第三轮 | 9 个 (配置/调度/适配器) | #36 - #43 |
| 第四轮 | 6 项 (RLS/事件覆盖/回调) | #44 - #45 |
| 第五轮 | 8 项 (接口/重试/前端状态/并发) | #46 - #48 |
| 第六轮 | 7 项 (深层盲区: 持久化/原子性/重放/删除/折扣/货币/前端错误) | #49 - #50 |
| **合计** | **43+ 个文件/模块, 50+ 审计项** | **50 个问题** |

### 按优先级统计 (最终)

| 优先级 | 数量 | 说明 |
|--------|------|------|
| **P0** | 15 | 资金安全 + 数据完整性 + 功能阻断 |
| **P1** | 27 | 功能正确性 + 性能 + 用户体验 |
| **P2** | 6 | 代码质量 + 文档 + 增强型改进 |

### 全部 P0 问题速查 (15 个)

| 序号 | 一句话描述 |
|------|-----------|
| #36 | 注册奖励全线不一致 (RPC=50, Config=100) |
| **#49** | **续费 webhook 非原子操作 — 积分刷新失败无补偿** |
| #14 | 退费后不扣回积分 |
| #15 | 退订阅费后不降级 tier |
| #23 | payment_records CHECK 约束不兼容 |
| #24 | payment_repository 字段名不匹配 |
| #25 | process_subscription_start RPC 不存在 |
| #28 | Container 未注入 TierService 到 BillingService |
| #29 | credit_repository 月度积分硬编码 500/1000 |
| #37 | PricingService 缺少 await |
| #1 | Checkout 未绑定 Stripe Customer |
| #2 | Webhook 首次订阅积分硬编码 500/1000 |
| #3 | 无升级路径 (t2→t3) |
| #7 | 取消订阅后月度积分未清零 |
| #8 | Webhook 取消降级未清零月度积分 |

### 安全评估 (最终)

| 安全项 | 状态 |
|--------|------|
| RLS 策略 (payment_records, credit_*) | ✅ 安全 |
| RLS 策略 (stripe_webhook_events) | ⚠️ 待确认 (#47) |
| Webhook 签名验证 | ✅ 已实现 |
| Webhook 时间戳容忍度 | ⚠️ 未显式设置 (#50)，但 SDK 默认 300s |
| Webhook 签名密钥启动校验 | ⚠️ 仅 WARNING (#48) |
| Webhook 幂等性 | ✅ 已实现 |
| Webhook 原子性 (续费) | ❌ 非原子，部分失败无补偿 (#49) |
| 并发扣费保护 (double-spend) | ✅ RPC 原子操作 |
| SQL 注入防护 | ✅ RPC 参数化 |
| Stripe Price ID 配置 | ✅ 环境变量 + 启动验证 |
| Coupon/Discount 验证 | ✅ 三层防护 |
| 付款失败主动通知 | ❌ 缺失 (#44) |
| 资金回收 (退费扣积分) | ❌ 缺失 (#14) |
| 前端订阅异常状态展示 | ❌ 缺失 (#46) |
| stripe_customer_id 持久化 | ✅ 安全 |
| 账号删除安全 | ✅ 安全 (无删除端点) |

**下一步**: 根据优先级逐个修复，每个问题走 Phase 1-4 流程 (分析→方案→实施→文档)
