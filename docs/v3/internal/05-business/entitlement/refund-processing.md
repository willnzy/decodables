# 退款处理

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [fullstack]
> **来源**: v1 shared/entitlement/

---

## 概述

退款处理的规则和流程。

---

## 退款政策

### 订阅退款

| 条件 | 退款比例 |
|------|----------|
| 订阅后 7 天内 | 100% (全额) |
| 订阅后 8-14 天 | 50% (按比例) |
| 订阅后 15+ 天 | 不支持退款 |

### 积分包退款

| 条件 | 退款 |
|------|------|
| 未使用 | 100% |
| 已使用 | 不支持 |

---

## 处理流程

```
用户申请退款
    ↓
客服审核 (确认符合政策)
    ↓
Stripe 执行退款
    ↓
Webhook 接收 charge.refunded
    ↓
系统处理:
    - 降级用户 tier → t1
    - 清零月度积分
    - 标记退款记录
    ↓
发送确认邮件
```

---

## 权益回收

退款后:
- 订阅: 立即降级到 t1
- 月度积分: 立即清零
- 永久积分: 保留 (不回收)
- 项目: 保留 (超出限制的变为只读)

---

## 代码实现

```python
async def handle_refund(charge_id: str):
    """处理退款后的权益回收"""
    # 获取关联订阅/积分包
    transaction = await get_transaction_by_charge(charge_id)
    
    if transaction.type == 'subscription':
        await downgrade_user_tier(transaction.user_id, 't1')
        await clear_monthly_credits(transaction.user_id)
    
    elif transaction.type == 'credits':
        # 回收未使用积分
        await deduct_credits(transaction.user_id, transaction.credits_amount)
```

---

## 相关文档

- [Stripe Webhook 处理](../../04-engineering/modules/billing/stripe-webhooks.md)
- [计费政策 (Public)](../../../public/legal/billing-policy.md)
