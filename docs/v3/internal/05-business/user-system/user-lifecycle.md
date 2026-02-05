# 用户生命周期

> **同步范围**: [fullstack]
> **状态**: 🟢 已验证
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `domains/identity/`, `domains/billing/`

---

## 一、概述

用户生命周期描述用户从注册到流失的完整旅程，以及各阶段的状态转换。

---

## 二、用户状态

### 2.1 状态定义

| 状态 | 说明 | 数据库值 |
|------|------|----------|
| **pending** | 注册中，OTP 未验证 | `pending` |
| **active** | 正常使用 | `active` |
| **suspended** | 暂停 (付款失败) | `suspended` |
| **deleting** | 删除冷静期 | `deleting` |
| **deleted** | 已删除 | `deleted` |

### 2.2 状态流转图

```
┌─────────────────────────────────────────────────────────────┐
│                    用户状态流转                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│     ┌─────────┐                                            │
│     │ pending │ ←── 注册开始                               │
│     └────┬────┘                                            │
│          │ OTP 验证成功                                     │
│          ▼                                                  │
│     ┌─────────┐                                            │
│     │ active  │ ←── 正常使用                               │
│     └────┬────┘                                            │
│          │                                                  │
│     ┌────┴────┬────────────┐                               │
│     │         │            │                                │
│     │ 付款失败 │ 请求删除   │ 正常使用                       │
│     ▼         ▼            │                                │
│ ┌──────────┐ ┌──────────┐  │                               │
│ │suspended │ │ deleting │  │                               │
│ └────┬─────┘ └────┬─────┘  │                               │
│      │            │         │                               │
│      │ 恢复付款   │ 30天后   │                               │
│      └──────┬─────┘         │                               │
│             │               │                               │
│             ▼               │                               │
│       ┌──────────┐          │                               │
│       │ deleted  │          │                               │
│       └──────────┘          │                               │
│                             │                               │
│   撤销删除 ─────────────────┘                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、生命周期阶段

### 3.1 获客阶段

| 事件 | 说明 | 数据变化 |
|------|------|----------|
| 访问网站 | 匿名用户 | - |
| 注册开始 | 输入邮箱 | 创建 pending 用户 |
| OTP 验证 | 验证邮箱 | 状态 → active |
| 注册完成 | 设置密码 | +100 永久积分 |

### 3.2 激活阶段

| 事件 | 说明 | 指标 |
|------|------|------|
| 首次登录 | 进入应用 | Day 1 留存 |
| 创建项目 | 开始使用 | 激活率 |
| 使用 AI | 核心功能 | 功能采用率 |
| 首次导出 | 完成价值 | Aha 时刻 |

### 3.3 留存阶段

| 事件 | 说明 | 触发 |
|------|------|------|
| 周活跃 | 每周回访 | 内容推荐 |
| 月活跃 | 每月回访 | 邮件提醒 |
| 项目累积 | 持续创作 | - |

### 3.4 付费转化

| 事件 | 说明 | 触发 |
|------|------|------|
| 触达付费墙 | 积分用尽/功能限制 | 升级提示 |
| 开始订阅 | 首次付费 | Stripe 支付 |
| 续费成功 | 持续付费 | 自动续费 |

### 3.5 流失阶段

| 事件 | 说明 | 挽回策略 |
|------|------|----------|
| 不活跃 | 30天未登录 | 邮件召回 |
| 取消订阅 | 主动取消 | 挽留弹窗 |
| 账户删除 | 永久离开 | 冷静期 |

---

## 四、关键事件

### 4.1 注册事件

```python
# 注册完成时触发
async def on_user_registered(user: UserProfile):
    # 1. 发放注册积分
    await credits_service.grant_signup_bonus(user.id, 100)
    
    # 2. 创建 onboarding 记录
    await onboarding_service.initialize(user.id)
    
    # 3. 发送欢迎通知
    await notification_service.create(
        user.id, 
        "welcome",
        {"name": user.name}
    )
    
    # 4. 追踪事件
    await event_service.track("user_registered", user.id)
```

### 4.2 订阅事件

```python
# 首次订阅
async def on_first_subscription(user_id: UUID, tier: str):
    # 1. 更新 Tier
    await user_service.update_tier(user_id, tier)
    
    # 2. 发放月度积分
    await credits_service.grant_monthly(user_id, tier)
    
    # 3. 发送通知
    await notification_service.create(
        user_id,
        "subscription_activated",
        {"tier": tier}
    )
```

### 4.3 取消订阅

```python
# 取消订阅
async def on_subscription_cancelled(user_id: UUID):
    # 1. 设置取消状态 (保持到周期结束)
    await subscription_service.set_cancel_at_period_end(user_id)
    
    # 2. 发送通知
    await notification_service.create(
        user_id,
        "subscription_cancelled"
    )
```

---

## 五、数据处理

### 5.1 数据保留

| 状态 | 数据保留 |
|------|----------|
| active | 完整保留 |
| suspended | 完整保留 |
| deleting | 完整保留 (30天) |
| deleted | 匿名化/删除 |

### 5.2 删除流程

1. **请求删除**: 用户发起，进入 `deleting` 状态
2. **冷静期**: 30 天内可撤销
3. **执行删除**: 30 天后自动执行
   - 个人信息匿名化
   - 项目数据删除
   - 支付信息保留 (合规要求)

---

## 六、指标监控

### 6.1 漏斗指标

| 阶段 | 指标 | 计算 |
|------|------|------|
| 注册 | 注册转化率 | 注册数 / 访问数 |
| 激活 | 激活率 | 创建项目数 / 注册数 |
| 留存 | Day 7 留存 | Day7 回访 / 注册数 |
| 付费 | 付费转化率 | 付费用户 / 活跃用户 |
| 流失 | 月流失率 | 流失用户 / 月初用户 |

### 6.2 追踪事件

| 事件 | 触发时机 |
|------|----------|
| `user_registered` | 注册完成 |
| `user_activated` | 首次创建项目 |
| `subscription_started` | 首次订阅 |
| `subscription_cancelled` | 取消订阅 |
| `user_churned` | 30天未活跃 |

---

## 七、相关文档

- [用户 ID 系统](../user-id-system.md)
- [Tier 系统](../tier-system/overview.md)
- [计费模块架构](../../04-engineering/modules/billing/architecture.md)

---

**END OF DOCUMENT**
