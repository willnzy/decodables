# 订阅功能规格

> **同步范围**: [fullstack]
> **状态**: 🟢 已验证
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `domains/subscriptions/`, `api/user/payment.py`

---

## 一、概述

### 1.1 功能定位

订阅功能让用户升级到付费计划，获得更多权益和月度积分。

### 1.2 订阅计划

| 计划 | 月费 | 月度积分 | 核心权益 |
|------|------|----------|----------|
| Free (t1) | $0 | 0 | 基础功能 |
| Starter (t2) | $6.9 | 100 | 无水印 + 全部模板 |
| Pro (t3) | $9.9 | 200 | 优先 AI + 更多存储 |

---

## 二、功能范围

| 功能 | 优先级 | 状态 |
|------|--------|------|
| 订阅计划展示 | P0 | ✅ |
| 订阅购买 | P0 | ✅ |
| 订阅管理 | P0 | ✅ |
| 升级/降级 | P1 | ✅ |
| 取消订阅 | P1 | ✅ |

---

## 三、订阅计划页面

### 3.1 定价页面

```
┌────────────────────────────────────────────────────────────┐
│                    Choose Your Plan                        │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │    FREE     │  │   STARTER   │  │     PRO     │        │
│  │             │  │   POPULAR   │  │  BEST VALUE │        │
│  │    $0/mo    │  │  $6.9/mo    │  │  $9.9/mo    │        │
│  │             │  │  was $9.9   │  │  was $15.9  │        │
│  │ ──────────  │  │ ──────────  │  │ ──────────  │        │
│  │ ✓ 3 projects│  │ ✓ 50 projects│ │ ✓ Unlimited │        │
│  │ ✓ 100MB     │  │ ✓ 5GB storage│ │ ✓ 20GB     │        │
│  │ ✗ Watermark │  │ ✓ No watermark│ │ ✓ No water│        │
│  │ ✓ Basic temp│  │ ✓ All templates││ ✓ All temp │        │
│  │             │  │ ✓ 100 credits│ │ ✓ 200 credits│       │
│  │             │  │              │  │ ✓ Priority AI│       │
│  │             │  │              │  │              │        │
│  │ [Current]   │  │ [Upgrade]   │  │ [Upgrade]    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## 四、订阅流程

### 4.1 新订阅

```
选择计划 → Stripe Checkout → 支付成功 → Tier 升级 → 积分发放
```

### 4.2 升级

```
选择更高计划 → Stripe 计算差额 → 支付 → 立即升级 → 积分补发
```

**升级特点**:
- 立即生效
- 按比例补发积分
- 差额支付

### 4.3 降级

```
选择降级 → 确认提示 → 设置期末降级 → 周期结束时生效
```

**降级特点**:
- 当前周期结束后生效
- 保留当前周期权益
- 月度积分周期结束清零

### 4.4 取消订阅

```
点击取消 → 确认提示 → 设置期末取消 → 周期结束降为 Free
```

---

## 五、订阅管理页面

```
┌────────────────────────────────────────────────────────────┐
│  Subscription                                              │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Current Plan: Starter                                     │
│  Status: Active                                            │
│  Next billing: March 1, 2026                               │
│  Amount: $6.9/month                                        │
│                                                            │
│  Monthly Credits: 45 / 100                                 │
│  Resets on March 1, 2026                                   │
│                                                            │
│  [Upgrade to Pro]  [Manage Subscription]                   │
│                                                            │
│  ──────────────────────────────────────────────────────    │
│                                                            │
│  Billing History                                           │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ Feb 1, 2026    Starter Plan      $6.90      Paid     │ │
│  │ Jan 1, 2026    Starter Plan      $6.90      Paid     │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## 六、Stripe 集成

### 6.1 Checkout Session

创建订阅时跳转到 Stripe Checkout 页面完成支付。

### 6.2 Customer Portal

管理订阅、更新支付方式、查看发票在 Stripe Customer Portal 完成。

### 6.3 Webhook 事件

| 事件 | 处理 |
|------|------|
| checkout.session.completed | 创建订阅 |
| invoice.paid | 续期发放积分 |
| customer.subscription.updated | 升降级处理 |
| customer.subscription.deleted | 订阅取消 |

---

## 七、API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/payment/checkout` | POST | 创建 Checkout |
| `/payment/portal` | POST | 获取 Portal URL |
| `/payment/upgrade` | POST | 升级订阅 |
| `/billing/subscription` | GET | 获取订阅状态 |

---

## 八、相关文档

- [Tier 系统](../../05-business/tier-system/overview.md)
- [计费模块架构](../../04-engineering/modules/billing/architecture.md)
- [积分功能规格](./credits.md)

---

**END OF DOCUMENT**
