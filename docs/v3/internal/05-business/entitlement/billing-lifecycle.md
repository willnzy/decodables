# 订阅与账单生命周期

> **同步范围**: [fullstack]
> **状态**: 🟡 待验证 (需结合实际代码确认)
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `domains/billing/`, Stripe Webhook

---

## 一、概述

### 1.1 覆盖场景

| 场景 | 说明 |
|------|------|
| 新订阅 | 用户首次订阅付费计划 |
| 续费 | 自动续费或手动续费 |
| 升级 | 从低 Tier 升级到高 Tier |
| 降级 | 从高 Tier 降级到低 Tier |
| 取消 | 用户取消订阅 |
| 退款 | 发起退款处理 |

### 1.2 核心原则

```
1. 权益变更即时生效
2. 退款按 FEFO 逆序扣回
3. 升级立即生效，降级周期末生效
4. 取消保留至周期末
```

---

## 二、订阅状态流转

### 2.1 状态定义

| 状态 | 说明 | 数据库值 |
|------|------|----------|
| Active | 正常订阅中 | `active` |
| Trialing | 试用期 | `trialing` |
| Past Due | 付款失败 | `past_due` |
| Canceled | 已取消(等待到期) | `canceled` |
| Unpaid | 未付款 | `unpaid` |
| Inactive | 已失效 | `inactive` |

### 2.2 状态流转图

```
                    ┌─────────────┐
                    │   注册      │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
            ┌───────│  Trialing   │───────┐
            │       │   (t1)      │       │
            │       └──────┬──────┘       │
            │              │              │
       订阅到期            │订阅         │试用到期
            │              │              │
            ▼              ▼              ▼
     ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
     │  Inactive   │ │   Active    │ │  Inactive   │
     │   (t1)      │ │  (t2/t3)    │ │   (t1)      │
     └─────────────┘ └──────┬──────┘ └─────────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
     取消订阅         付款失败          续费成功
          │                │                │
          ▼                ▼                │
     ┌─────────────┐ ┌─────────────┐       │
     │  Canceled   │ │  Past Due   │       │
     │ (等待到期)  │ │  (宽限期)   │       │
     └──────┬──────┘ └──────┬──────┘       │
            │              │                │
       周期结束        付款成功             │
            │              │                │
            ▼              └────────────────┘
     ┌─────────────┐
     │  Inactive   │
     │   (t1)      │
     └─────────────┘
```

---

## 三、新订阅流程

### 3.1 流程步骤

```
1. 用户选择计划 (Starter/Pro)
2. 跳转 Stripe Checkout
3. 支付成功
4. Webhook: checkout.session.completed
5. 更新用户 Tier
6. 发放月度积分
7. 发送确认邮件
```

### 3.2 Webhook 处理

```python
async def handle_checkout_completed(event: StripeEvent):
    session = event.data.object
    user_id = session.metadata.get('user_id')
    plan = session.metadata.get('plan')
    
    # 1. 创建订阅记录
    subscription = await create_subscription(
        user_id=user_id,
        stripe_subscription_id=session.subscription,
        plan=plan,
        status='active'
    )
    
    # 2. 更新用户 Tier
    new_tier = 't2' if plan == 'starter' else 't3'
    await update_user_tier(user_id, new_tier)
    
    # 3. 发放月度积分
    credits = 100 if new_tier == 't2' else 200
    await grant_monthly_credits(user_id, credits)
    
    # 4. 发送通知
    await send_notification(user_id, 'subscription_created', {
        'plan': plan,
        'credits': credits
    })
```

---

## 四、升级流程

### 4.1 立即生效

```
t1 → t2: 立即获得 t2 权益
t1 → t3: 立即获得 t3 权益
t2 → t3: 立即获得 t3 权益
```

### 4.2 积分处理

```python
async def handle_upgrade(user_id: UUID, from_tier: str, to_tier: str):
    # 1. 计算积分差额
    credits_diff = TIER_CREDITS[to_tier] - TIER_CREDITS[from_tier]
    
    # 2. 立即发放差额
    if credits_diff > 0:
        await grant_monthly_credits(user_id, credits_diff)
    
    # 3. 更新 Tier
    await update_user_tier(user_id, to_tier)
```

### 4.3 计费处理

- **按比例计费**: Stripe 自动计算 prorate
- **升级后**: 下次账单反映新价格

---

## 五、降级流程

### 5.1 周期末生效

```
降级请求 → 标记 pending_downgrade → 周期末执行 → 更新 Tier
```

### 5.2 积分处理

```python
async def execute_downgrade(user_id: UUID, to_tier: str):
    # 1. 更新 Tier
    await update_user_tier(user_id, to_tier)
    
    # 2. 清空月度积分
    await clear_monthly_credits(user_id)
    
    # 3. 发放新 Tier 积分
    new_credits = TIER_CREDITS[to_tier]
    if new_credits > 0:
        await grant_monthly_credits(user_id, new_credits)
```

### 5.3 权益变化

| 场景 | 权益变化 |
|------|----------|
| t3 → t2 | 失去 Smart Scan、ZIP 导出等 |
| t3 → t1 | 失去大部分功能 |
| t2 → t1 | 失去 AI 功能 |

---

## 六、取消订阅

### 6.1 流程

```
1. 用户发起取消
2. 标记 cancel_at_period_end = true
3. 继续享有权益至周期末
4. 周期末触发 subscription.deleted
5. 降级至 t1
```

### 6.2 Webhook 处理

```python
async def handle_subscription_deleted(event: StripeEvent):
    subscription = event.data.object
    user_id = await get_user_by_stripe_customer(subscription.customer)
    
    # 1. 更新订阅状态
    await update_subscription_status(subscription.id, 'inactive')
    
    # 2. 降级至 t1
    await update_user_tier(user_id, 't1')
    
    # 3. 清空月度积分
    await clear_monthly_credits(user_id)
    
    # 4. 发送通知
    await send_notification(user_id, 'subscription_canceled')
```

---

## 七、退款处理

### 7.1 退款类型

| 类型 | 说明 | 积分处理 |
|------|------|----------|
| 全额退款 | 退还全部金额 | 扣回全部积分 |
| 部分退款 | 退还部分金额 | 按比例扣回 |
| 仅退款 | 不影响订阅 | 不扣回积分 |

### 7.2 积分扣回 (FEFO 逆序)

```python
async def handle_refund(user_id: UUID, credits_to_deduct: int):
    """按 FEFO 逆序扣回积分"""
    remaining = credits_to_deduct
    
    # 1. 先扣购买积分
    remaining = await deduct_purchase_credits(user_id, remaining)
    
    # 2. 再扣月度积分
    if remaining > 0:
        remaining = await deduct_monthly_credits(user_id, remaining)
    
    # 3. 最后扣赠送积分
    if remaining > 0:
        remaining = await deduct_bonus_credits(user_id, remaining)
    
    if remaining > 0:
        # 记录负债或标记异常
        await log_credit_shortage(user_id, remaining)
```

---

## 八、续费提醒

### 8.1 提醒时机

| 时机 | 通知方式 |
|------|----------|
| 到期前 7 天 | 邮件 + 站内通知 |
| 到期前 3 天 | 邮件 + 站内通知 |
| 到期前 1 天 | 邮件 + 站内通知 |
| 续费失败 | 邮件 + 站内通知 |

### 8.2 付款失败处理

```
1. 首次失败: 发送提醒，等待重试
2. 3 天后仍失败: 再次提醒
3. 7 天后仍失败: 标记 past_due
4. 14 天后仍失败: 取消订阅，降级 t1
```

---

## 九、相关文档

- [权限矩阵](./permission-matrix.md)
- [积分系统流程](../credits-system/flow.md)
- [Billing 模块架构](../../04-engineering/modules/billing/architecture.md)
- [订阅功能规格](../../02-product/features/subscription.md)

---

**END OF DOCUMENT**
