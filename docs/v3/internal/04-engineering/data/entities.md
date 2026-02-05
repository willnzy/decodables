# 实体定义

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [backend]
> **对应代码**: `decodables/domains/*/entity.py`

---

## 概述

DDD 领域实体定义，每个实体对应业务概念。

---

## 核心实体

### User 实体

```python
class User(Entity):
    user_id: UUID         # 系统内部 ID
    user_code: str        # 用户可见 ID (26位)
    email: str
    display_name: str
    tier: str             # t1/t2/t3/t4
    role: str             # user/admin
    credits_monthly: int  # 月度积分
    credits_permanent: int # 永久积分
```

### Subscription 实体

```python
class Subscription(Entity):
    subscription_id: UUID
    user_id: UUID
    tier: str             # t2/t3/t4
    status: str           # active/cancelled/expired
    stripe_subscription_id: str
    current_period_start: datetime
    current_period_end: datetime
```

### CreditTransaction 实体

```python
class CreditTransaction(Entity):
    transaction_id: UUID
    user_id: UUID
    amount: int           # 正数增加，负数扣减
    credit_type: str      # monthly/permanent
    reason: str           # ai_generation/purchase/...
    balance_after: int
```

---

## 实体设计原则

1. **不可变性**: 实体创建后核心属性不变
2. **唯一标识**: 每个实体有唯一 ID
3. **业务行为**: 实体包含业务逻辑方法
4. **领域事件**: 重要操作触发领域事件

---

## 相关文档

- [Schema 定义](./schema.md)
- [DDD 架构](../architecture/backend.md)
