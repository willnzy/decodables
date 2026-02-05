# ADR-0003 双桶积分模型

> **状态**: ✅ Active
> **日期**: 2026-01-15
> **决策者**: Product & Backend Team

---

## 背景

系统需要支持两种不同来源的积分:

1. **订阅积分**: 付费会员每月获得的积分
2. **充值积分**: 用户单独购买的积分

这两种积分有不同的特性:

| 特性 | 订阅积分 | 充值积分 |
|------|----------|----------|
| 有效期 | 每月重置 | 永久有效 |
| 来源 | 订阅计划 | 单独购买 |
| 退款处理 | 随订阅处理 | 独立退款 |

---

## 决策

采用双桶积分模型 (Dual-Bucket Credit Model):

1. 分为 `credits_monthly` 和 `credits_permanent` 两个独立桶
2. 消费时先扣月度积分，再扣永久积分 (FEFO)
3. 退款时逆向恢复 (FEFO Reverse)

---

## 考虑的选项

### 选项 A: 单桶模型

- **优点**: 简单，用户易理解
- **缺点**: 无法区分积分来源，退款复杂

### 选项 B: 多桶模型 (每种来源一个桶)

- **优点**: 精确追踪每笔积分
- **缺点**: 过于复杂，消费逻辑繁琐

### 选项 C: 双桶模型 (选中)

- **优点**: 平衡复杂度和功能需求
- **缺点**: 需要特殊处理月度重置

---

## 理由

1. **业务需求**: 月度积分需要重置，充值积分需要永久有效
2. **退款需求**: 需要能准确恢复正确类型的积分
3. **复杂度可控**: 两个桶足够满足需求，又不会过于复杂
4. **用户体验**: 用户可以清楚看到两种积分余额

---

## 影响

### 正面影响

- 积分来源清晰
- 支持不同有效期策略
- 退款处理准确
- 支持月度重置

### 负面影响

- 消费逻辑略复杂
- UI 需要展示两个余额
- 交易记录需要记录桶类型

### 需要的改动

1. profiles 表添加 `credits_monthly` 和 `credits_permanent` 字段
2. 交易表添加 `bucket` 字段
3. 消费和退款逻辑支持双桶

---

## 实现方案

### 数据结构

```sql
-- profiles 表
ALTER TABLE profiles ADD COLUMN credits_monthly INTEGER DEFAULT 0;
ALTER TABLE profiles ADD COLUMN credits_permanent INTEGER DEFAULT 0;

-- 交易记录
CREATE TABLE credit_transactions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    amount INTEGER NOT NULL,
    bucket VARCHAR(20) NOT NULL,  -- 'monthly' | 'permanent'
    type VARCHAR(50) NOT NULL,
    reason VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 消费逻辑 (FEFO)

```python
async def deduct_credits(user_id: UUID, amount: int, reason: str) -> DeductResult:
    """
    先扣月度，再扣永久 (First Expire, First Out)
    """
    user = await get_user(user_id)
    
    total_available = user.credits_monthly + user.credits_permanent
    if total_available < amount:
        raise InsufficientCreditsError()
    
    # 计算各桶扣减量
    monthly_deduct = min(user.credits_monthly, amount)
    permanent_deduct = amount - monthly_deduct
    
    # 执行扣减
    await update_credits(
        user_id,
        monthly_delta=-monthly_deduct,
        permanent_delta=-permanent_deduct
    )
    
    # 记录交易
    if monthly_deduct > 0:
        await create_transaction(user_id, -monthly_deduct, 'monthly', reason)
    if permanent_deduct > 0:
        await create_transaction(user_id, -permanent_deduct, 'permanent', reason)
    
    return DeductResult(
        success=True,
        monthly_deducted=monthly_deduct,
        permanent_deducted=permanent_deduct
    )
```

### 退款逻辑 (FEFO Reverse)

```python
async def refund_credits(transaction_id: UUID) -> RefundResult:
    """
    退款时逆向恢复：先恢复永久，再恢复月度
    """
    transaction = await get_transaction(transaction_id)
    
    # 查找原始消费记录
    original_records = await get_consumption_records(transaction.reference_id)
    
    # 按逆序恢复
    for record in reversed(original_records):
        await update_credits(
            transaction.user_id,
            monthly_delta=record.monthly_amount if record.bucket == 'monthly' else 0,
            permanent_delta=record.permanent_amount if record.bucket == 'permanent' else 0
        )
        await create_transaction(
            transaction.user_id,
            record.amount,
            record.bucket,
            'refund'
        )
    
    return RefundResult(success=True)
```

### 月度重置

```python
async def monthly_reset_credits():
    """
    每月 1 号凌晨执行
    """
    # 获取所有订阅用户
    subscribers = await get_active_subscribers()
    
    for user in subscribers:
        tier_credits = TIER_MONTHLY_CREDITS[user.tier]
        
        # 重置月度积分（不累积）
        await update_credits(
            user.id,
            monthly_set=tier_credits,  # 直接设置，不是增加
            permanent_delta=0
        )
        
        await create_transaction(
            user.id,
            tier_credits,
            'monthly',
            'monthly_reset'
        )
```

---

## 相关文档

- [积分系统架构](../../04-engineering/modules/billing/architecture.md)
- [计费生命周期](../../05-business/entitlement/billing-lifecycle.md)
