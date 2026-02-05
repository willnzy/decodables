# 计费模块架构

> **同步范围**: [fullstack]
> **状态**: 🟢 已验证
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `domains/billing/`, `domains/subscriptions/`, `api/user/payment.py`

---

## 一、模块概述

### 1.1 职责范围

计费模块负责：
- **订阅管理**: Stripe 订阅集成、Tier 升降级
- **积分管理**: 双桶模型 (月度+永久)、消费扣除
- **支付处理**: Checkout Session、Billing Portal
- **Webhook 处理**: Stripe 事件同步

### 1.2 模块划分

| 模块 | 职责 |
|------|------|
| `domains/billing` | 积分管理、支付服务 |
| `domains/subscriptions` | 订阅生命周期管理 |
| `api/user/payment.py` | 支付 API |
| `api/user/billing.py` | 计费 API |
| `api/user/webhooks.py` | Stripe Webhook |

---

## 二、代码结构

### 2.1 目录结构

```
domains/billing/
├── __init__.py
├── aggregates/
│   └── user_credits.py     # 用户积分聚合
├── exceptions.py           # 领域异常
├── payment_service.py      # 支付服务 (Stripe)
├── pricing_service.py      # 定价服务
├── repository.py           # Repository 接口
├── service.py              # BillingService
└── value_objects.py        # Credits, TransactionType

domains/subscriptions/
├── __init__.py
├── exceptions.py           # 订阅异常
└── subscription_service.py # 订阅管理服务
```

### 2.2 API 结构

```
api/user/
├── payment.py              # POST /payment/checkout, /portal, /upgrade
├── billing.py              # GET /credits, /transactions
└── webhooks.py             # POST /webhooks/stripe
```

---

## 三、核心 Entity

### 3.1 UserCredits (聚合根)

```python
@dataclass
class UserCredits:
    """用户积分聚合根"""
    user_id: str
    credits_monthly: int      # 月度积分
    credits_permanent: int    # 永久积分
    
    @property
    def total_credits(self) -> int:
        return self.credits_monthly + self.credits_permanent
    
    def can_afford(self, amount: int) -> bool:
        return self.total_credits >= amount
```

### 3.2 CreditTransaction

```python
@dataclass
class CreditTransaction:
    """积分交易记录"""
    id: UUID
    user_id: str
    type: TransactionType
    amount: int  # 正数=增加, 负数=扣除
    
    # 余额快照
    balance_before_monthly: int
    balance_before_permanent: int
    balance_after_monthly: int
    balance_after_permanent: int
    
    description: Optional[str]
    reference_id: Optional[str]
    metadata: dict
    created_at: datetime
```

---

## 四、订阅管理

### 4.1 订阅生命周期

```
┌──────────────────────────────────────────────────────────────┐
│                  Subscription Lifecycle                       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────┐  subscribe   ┌────────┐  upgrade   ┌────────┐   │
│  │  Free  │ ──────────▶ │ Active │ ─────────▶ │ Active │   │
│  │  (t1)  │             │  (t2)  │            │  (t3)  │   │
│  └────────┘             └────────┘            └────────┘   │
│       ▲                      │                     │        │
│       │                      │ cancel              │        │
│       │                      ▼                     │        │
│       │                ┌──────────┐               │        │
│       └────────────── │ Canceled │ ◀─────────────┘        │
│         period_end    │(期末降级) │  cancel                │
│                       └──────────┘                         │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 升级流程

```python
async def upgrade_subscription(user_id: str, target_tier: str):
    """
    订阅升级流程:
    1. 验证目标 Tier 高于当前 Tier
    2. 创建 Stripe Checkout Session (带 proration)
    3. Webhook 处理支付成功 → 更新 Tier + 发放积分
    """
```

**升级特点**:
- 立即生效
- 按比例补发当月积分
- Stripe 自动计算差额

### 4.3 降级/取消流程

```python
async def downgrade_subscription(user_id: str, target_tier: str = None):
    """
    降级流程:
    1. 设置 cancel_at_period_end = true
    2. 设置 pending_tier_change = target_tier
    3. 周期结束时 Webhook 处理实际降级
    """
```

**降级特点**:
- 周期结束后生效
- 保留当前周期权益
- 月度积分在周期结束时清零

---

## 五、积分管理

### 5.1 双桶模型

```
┌─────────────────────────────────────────────────────┐
│                   Credit Buckets                    │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────┐    ┌─────────────────────┐    │
│  │  Monthly Bucket │    │  Permanent Bucket   │    │
│  │                 │    │                     │    │
│  │  来源: 订阅发放  │    │  来源: 注册/充值    │    │
│  │  有效期: 每月重置│    │  有效期: 永久       │    │
│  │  扣费优先级: 1   │    │  扣费优先级: 2      │    │
│  │                 │    │                     │    │
│  └─────────────────┘    └─────────────────────┘    │
│                                                     │
│  扣费顺序: Monthly → Permanent                      │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 5.2 积分扣除逻辑

```python
def deduct_credits(self, amount: int) -> Credits:
    """
    扣除积分 (月度优先):
    
    if monthly >= amount:
        return monthly - amount, permanent
    else:
        remaining = amount - monthly
        return 0, permanent - remaining
    """
```

### 5.3 月度重置

```python
async def reset_monthly_credits(user_id: str, tier: str):
    """
    月度积分重置 (订阅续期时):
    1. 记录 monthly_reset 交易 (清零)
    2. 记录 subscription_grant 交易 (发放)
    """
```

---

## 六、Stripe 集成

### 6.1 支付流程

```
┌────────────────────────────────────────────────────────────┐
│                    Checkout Flow                           │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  1. POST /payment/checkout                                 │
│     { plan_type: "t2" }                                    │
│           │                                                │
│           ▼                                                │
│  2. 创建 Stripe Checkout Session                           │
│     - mode: subscription (t2/t3) / payment (credits)       │
│     - customer: 复用或创建                                  │
│     - line_items: 根据 plan_type                           │
│           │                                                │
│           ▼                                                │
│  3. 返回 checkout_url                                      │
│     → 重定向用户到 Stripe Checkout 页面                     │
│           │                                                │
│           ▼                                                │
│  4. 用户完成支付                                           │
│           │                                                │
│           ▼                                                │
│  5. Webhook: checkout.session.completed                    │
│     → 更新用户 Tier / 发放积分                              │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 6.2 Webhook 事件

| 事件 | 处理逻辑 |
|------|----------|
| `checkout.session.completed` | 订阅创建/积分充值 |
| `invoice.paid` | 订阅续期，重置月度积分 |
| `invoice.payment_failed` | 标记 past_due 状态 |
| `customer.subscription.updated` | 升降级处理 |
| `customer.subscription.deleted` | 订阅取消，降级到 t1 |

### 6.3 Plan Type 映射

```python
VALID_PLAN_TYPES = {
    # 订阅
    "t2",          # Starter Plan
    "t3",          # Pro Plan
    
    # 积分充值
    "credits_100",  # 100 积分
    "credits_500",  # 500 积分
    "credits_2000", # 2000 积分
}
```

---

## 七、API 端点

### 7.1 支付

| 端点 | 方法 | 说明 |
|------|------|------|
| `/payment/checkout` | POST | 创建 Checkout Session |
| `/payment/portal` | POST | 获取 Billing Portal URL |
| `/payment/upgrade` | POST | 升级订阅 |

### 7.2 积分查询

| 端点 | 方法 | 说明 |
|------|------|------|
| `/billing/credits` | GET | 获取积分余额 |
| `/billing/transactions` | GET | 获取交易历史 |
| `/billing/tier` | GET | 获取当前 Tier |

### 7.3 Webhook

| 端点 | 方法 | 说明 |
|------|------|------|
| `/webhooks/stripe` | POST | Stripe Webhook |

---

## 八、异常定义

### 8.1 积分异常

| 异常 | HTTP | 说明 |
|------|------|------|
| `InsufficientCreditsException` | 402 | 积分不足 |
| `InvalidAmountException` | 400 | 金额无效 |
| `CreditOperationFailedException` | 500 | 操作失败 |

### 8.2 订阅异常

| 异常 | HTTP | 说明 |
|------|------|------|
| `SubscriptionNotActiveException` | 400 | 订阅未激活 |
| `InvalidTierTransitionException` | 400 | 无效的 Tier 变更 |
| `StripeError` | 500 | Stripe 错误 |

---

## 九、数据库表

### 9.1 profiles 表 (计费相关字段)

```sql
-- 积分
credits_monthly INTEGER NOT NULL DEFAULT 0,
credits_permanent INTEGER NOT NULL DEFAULT 0,

-- 订阅
tier TEXT NOT NULL DEFAULT 't1',
subscription_status TEXT,
stripe_customer_id TEXT,
stripe_subscription_id TEXT,

-- 周期
subscription_current_period_start TIMESTAMPTZ,
subscription_current_period_end TIMESTAMPTZ,

-- 取消状态
cancel_at_period_end BOOLEAN DEFAULT FALSE,
pending_tier_change TEXT,
```

### 9.2 credit_transactions 表

```sql
CREATE TABLE credit_transactions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES profiles(id),
    type TEXT NOT NULL,
    amount INTEGER NOT NULL,
    
    balance_before_monthly INTEGER,
    balance_before_permanent INTEGER,
    balance_after_monthly INTEGER,
    balance_after_permanent INTEGER,
    
    description TEXT,
    reference_id TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 9.3 payment_records 表

```sql
CREATE TABLE payment_records (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES profiles(id),
    stripe_payment_intent_id TEXT,
    stripe_checkout_session_id TEXT,
    
    amount INTEGER NOT NULL,
    currency TEXT DEFAULT 'usd',
    status TEXT NOT NULL,
    
    plan_type TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 十、安全措施

### 10.1 Webhook 安全

```python
# 验证 Stripe Webhook 签名
stripe.Webhook.construct_event(
    payload,
    sig_header,
    webhook_secret
)
```

### 10.2 幂等性保证

```python
# 使用 Stripe event.id 作为幂等键
if await is_event_processed(event.id):
    return {"status": "already_processed"}
```

### 10.3 原子性操作

```python
# 积分操作使用数据库事务
async with db.transaction():
    await deduct_credits(user_id, amount)
    await record_transaction(...)
```

---

## 十一、相关文档

- [Tier 系统](../../05-business/tier-system/overview.md)
- [积分系统](../../05-business/credits-system/overview.md)
- [API 参考 - 支付](../../03-api/payment.md)

---

**END OF DOCUMENT**
