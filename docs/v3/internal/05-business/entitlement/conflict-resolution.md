# 权益冲突解决

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [fullstack]
> **来源**: v1 shared/entitlement/

---

## 概述

当用户权益来自多个来源时的冲突解决规则。

---

## 冲突场景

### 1. 多重订阅

```
场景: 用户 A 同时有 t2 和 t3 订阅
解决: 取最高级别 (t3)
```

### 2. 订阅 + 促销

```
场景: 用户 B 有 t2 订阅，同时获得限时 t3 体验
解决: 体验期间享受 t3，到期回落到 t2
```

### 3. 积分来源

```
场景: 用户 C 有月度积分 50 + 永久积分 100
解决: 先消耗月度，再消耗永久
```

---

## 解决原则

| 规则 | 说明 |
|------|------|
| **最高优先** | 多个 tier 取最高 |
| **叠加累积** | 积分类可叠加 |
| **时效优先** | 临时权益不影响永久 |
| **明确回落** | 临时权益到期有明确回落路径 |

---

## 实现

```python
def resolve_tier_conflict(subscriptions: list) -> str:
    """解决多订阅冲突，返回有效 tier"""
    tiers = [s.tier for s in subscriptions if s.is_active]
    
    # 优先级: t3 > t2 > t1
    if 't3' in tiers:
        return 't3'
    elif 't2' in tiers:
        return 't2'
    return 't1'

def resolve_credits_conflict(user_id: str, amount: int) -> dict:
    """解决积分扣除冲突，返回扣除明细"""
    monthly = get_monthly_credits(user_id)
    permanent = get_permanent_credits(user_id)
    
    # 先月度后永久
    monthly_deduct = min(amount, monthly)
    permanent_deduct = min(amount - monthly_deduct, permanent)
    
    return {
        'monthly_deduct': monthly_deduct,
        'permanent_deduct': permanent_deduct
    }
```

---

## 相关文档

- [积分系统](../credits-system.md)
- [Tier 系统](../tier-system.md)
