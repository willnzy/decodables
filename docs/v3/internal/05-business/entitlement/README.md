# 权益系统 (Entitlement)

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [fullstack]

---

## 概述

权益系统管理用户可使用的功能和资源配额。

---

## 核心概念

| 概念 | 说明 |
|------|------|
| **Tier** | 用户层级 (t1/t2/t3) |
| **Entitlement** | 具体权益项 (功能/配额) |
| **Quota** | 资源使用限制 |
| **Override** | 特殊权益覆盖 |

---

## 文档索引

### 核心规则

| 文档 | 说明 |
|------|------|
| [权益配置](./config.md) | 配置存储和获取 |
| [层级继承](./tier-inheritance.md) | 高层级继承低层级权益 |
| [冲突解决](./conflict-resolution.md) | 多权益来源时的处理 |

### 配额管理

| 文档 | 说明 |
|------|------|
| [免费配额](./free-quota.md) | t1 用户限制和超额处理 |
| [试用过期](./trial-expiration.md) | 试用到期的处理 |

### 计费相关

| 文档 | 说明 |
|------|------|
| [退款处理](./refund-processing.md) | 退款后的权益回收 |
| [发票管理](./invoice-management.md) | 发票生成和下载 |
| [续订提醒](./renewal-reminders.md) | 到期前的通知 |

### 变更管理

| 文档 | 说明 |
|------|------|
| [功能下线](./feature-sunset.md) | 功能移除/降级策略 |

---

## 相关文档

- [Tier 系统](../tier-system.md)
- [积分系统](../credits-system.md)
- [计费模块](../../04-engineering/modules/billing/)
