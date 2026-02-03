# 积分完整生命周期

> **版本**: v2.0
> **日期**: 2026-02-04
> **状态**: 产品确认

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [README.md](./README.md) | 文档导航索引 |
| [01-permission-matrix.md](./01-permission-matrix.md) | 权限矩阵 |
| [18-refund-processing.md](./18-refund-processing.md) | 退款处理 |

---

## 一、积分类型

### 1.1 类型定义

| 类型 | 来源 | 有效期 | 扣费优先级 |
|------|------|--------|------------|
| **月度积分** (monthly) | 订阅自动发放 | 每月重置，不累积 | **1 (最先)** |
| **永久积分** (permanent) | 注册赠送/充值 | 永久有效 | **2** |
| **赠送积分** (gift) | 促销活动/邀请奖励 | 永久有效 | **3** |
| **补偿积分** (compensation) | 客服补偿 | 永久有效 | **4 (最后)** |

### 1.2 扣费顺序

```
消耗积分时，按优先级顺序扣费:
monthly → permanent → gift → compensation
```

---

## 二、积分获取

### 2.1 月度发放

| Tier | 月度积分 | 发放时间 |
|------|----------|----------|
| t1 (Free) | 0 | - |
| t2 (Starter) | 100 | 订阅日每月发放 |
| t3 (Pro) | 200 | 订阅日每月发放 |

**重置规则**: 月度积分每月重置，未使用部分清零，不累积。

### 2.2 注册赠送

```
t1 用户注册赠送: 100 永久积分
类型: permanent
有效期: 永久
```

### 2.3 充值购买

| 档位 | 积分 | 价格 | 类型 |
|------|------|------|------|
| 小包 | 100 | $2.99 | permanent |
| 中包 | 500 | $13.46 | permanent |
| 大包 | 2000 | $47.84 | permanent |

### 2.4 活动赠送

| 来源 | 积分 | 类型 |
|------|------|------|
| 邀请奖励 | 50/人 | gift |
| 促销活动 | 变动 | gift |
| 客服补偿 | 变动 | compensation |

---

## 三、积分消耗

### 3.1 AI 功能成本

| 功能 | 积分消耗 |
|------|----------|
| AI 生图 | 5 |
| AI 生 Page | 5 |
| OCR 识别 | 5 |

### 3.2 消耗流程

```python
async def consume_credits(user_id: str, amount: int, feature: str):
    # 1. 检查余额
    balance = await get_credit_balance(user_id)
    if balance < amount:
        raise InsufficientCreditsError()

    # 2. 按优先级扣费
    remaining = amount
    for credit_type in ['monthly', 'permanent', 'gift', 'compensation']:
        if remaining <= 0:
            break
        deducted = await deduct_by_type(user_id, credit_type, remaining)
        remaining -= deducted

    # 3. 记录消耗日志
    await log_credit_consumption(user_id, amount, feature)
```

---

## 四、特殊场景

### 4.1 积分冻结

**触发条件**:
- 订阅暂停
- 付款失败宽限期
- 账户安全审核

**冻结处理**:
```
冻结期间:
- 月度积分: 暂停发放
- 永久/赠送/补偿积分: 保留但不可使用

解冻后:
- 月度积分: 从新周期开始发放
- 其他积分: 立即可用
```

### 4.2 退款扣回

当用户退款时，需要扣回已发放的积分:

```
积分扣回规则:
1. 先扣 compensation (如有)
2. 再扣 gift (如有)
3. 再扣 permanent
4. 最后扣 monthly

如果余额不足:
- 记录欠款 (credits_debt)
- 下次充值或发放时自动扣回
```

### 4.3 积分欠款

```sql
-- profiles 表扩展
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS
    credits_debt INT DEFAULT 0;

-- 欠款处理
当用户获得新积分时:
if user.credits_debt > 0:
    deduct = min(new_credits, user.credits_debt)
    user.credits_debt -= deduct
    new_credits -= deduct
```

### 4.4 Tier 降级

**t3 → t2 降级时**:
- 当月剩余月度积分保留
- 下月按 t2 标准发放 (200 → 100)

**t2 → t1 降级时**:
- 当月剩余月度积分保留
- 下月不再发放月度积分

---

## 五、数据结构

### 5.1 积分余额表

```sql
-- 使用 profiles 表的字段
profiles.credits_monthly    -- 月度积分
profiles.credits_permanent  -- 永久积分
profiles.credits_gift       -- 赠送积分
profiles.credits_compensation -- 补偿积分
profiles.credits_debt       -- 积分欠款
```

### 5.2 积分流水表

```sql
CREATE TABLE IF NOT EXISTS credit_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES profiles(user_id),
    credit_type VARCHAR(20) NOT NULL,
    amount INT NOT NULL, -- 正数=获得, 负数=消耗
    balance_after INT NOT NULL,
    source VARCHAR(50) NOT NULL, -- subscription, purchase, gift, consumption, refund
    source_id TEXT, -- 关联的订单/消费ID
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_credit_transactions_user ON credit_transactions(user_id, created_at DESC);
```

---

## 六、API 接口

```python
# 查询积分余额
GET /api/v1/credits/balance
Response: {
    "monthly": 150,
    "permanent": 200,
    "gift": 50,
    "compensation": 0,
    "total": 400,
    "debt": 0
}

# 消耗积分
POST /api/v1/credits/consume
{
    "amount": 5,
    "feature": "ai_generate"
}

# 查询积分流水
GET /api/v1/credits/transactions?limit=20&offset=0
Response: {
    "transactions": [...],
    "total": 100
}
```

---

## 七、监控指标

| 指标 | 告警阈值 | 说明 |
|------|----------|------|
| 日均积分消耗 | 异常波动 >50% | 可能存在滥用 |
| 欠款用户数 | > 100 | 需要关注退款策略 |
| 月度积分使用率 | < 30% | 用户活跃度低 |

---

**END OF DOCUMENT**
