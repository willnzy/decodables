# 计费模块

> **同步范围**: [fullstack]
> **状态**: 🟡 待完善

---

## 模块概览

订阅计费、积分管理、支付处理。

## 对应代码

| 仓库 | 目录 |
|------|------|
| 后端 | `domains/billing/`, `domains/subscriptions/`, `domains/referrals/` |
| 前端 | `app/profile/subscription/`, `@business/stores/billing/` |

## 核心功能

- 订阅管理（创建、升级、降级、取消）
- 积分管理（消费、充值）
- 支付处理（Stripe）
- 推荐奖励

## 计划文档

| 文档 | 用途 | 状态 |
|------|------|------|
| `architecture.md` | 计费架构 | 📋 待创建 |
| `stripe-integration.md` | Stripe 集成 | 📋 待创建 |
| `webhooks.md` | Webhook 处理 | 📋 待创建 |

## 参考

- 业务规则：`05-business/tier-system/`, `05-business/credits-system/`, `05-business/pricing/`
