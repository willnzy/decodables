# 积分系统概述

> **同步范围**: [fullstack]
> **状态**: 🟢 已验证
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `domains/billing/value_objects.py`, `CLAUDE.md`

---

## 一、积分类型

### 1.1 双桶模型

系统使用**双桶积分模型**，分为月度积分和永久积分：

| 类型 | 来源 | 有效期 | 扣费优先级 |
|------|------|--------|------------|
| **月度积分** (monthly) | 订阅会员每月发放 | 每月重置，不累积 | **优先扣除** |
| **永久积分** (permanent) | 注册赠送 / 充值购买 | **永久有效** | 后扣 |

### 1.2 扣费规则

```python
# 扣费顺序: 月度 → 永久
def deduct(self, amount: int) -> 'Credits':
    if self.monthly >= amount:
        # 月度积分足够，只扣月度
        return Credits(monthly=self.monthly - amount, permanent=self.permanent)
    
    # 月度不足，扣完月度后从永久扣
    remaining = amount - self.monthly
    return Credits(monthly=0, permanent=self.permanent - remaining)
```

---

## 二、积分配置

### 2.1 月度发放 (按 Tier)

| Tier | 月度积分 |
|------|----------|
| t1 (Free) | 0 |
| t2 (Starter) | 200 |
| t3 (Pro) | 500 |
| t4 (预留) | 待定 |

### 2.2 注册赠送

| 用户类型 | 赠送积分 | 积分类型 |
|----------|----------|----------|
| 新注册用户 | 100 | **永久积分** |

### 2.3 充值档位

| 档位 | 积分 | 现价 | 单价 | Plan Type |
|------|------|------|------|-----------|
| 小包 | 100 | $2.99 | $0.030/积分 | `credits_100` |
| 中包 | 500 | $13.49 | $0.027/积分 | `credits_500` |
| 大包 | 2000 | $48.00 | $0.024/积分 | `credits_2000` |

> 💡 充值积分为**永久积分**，永不过期

---

## 三、消耗成本

### 3.1 AI 功能成本

| 功能 | 消耗积分 | 说明 |
|------|----------|------|
| AI 生图 | 5 | AI image generation |
| Smart Scan (OCR) | 10 | 智能扫描/文字识别 |
| AI 文字生成 | 1 | 预留功能 |

### 3.2 成本常量

```python
@dataclass(frozen=True)
class CreditCost:
    AI_GENERATION: int = 5   # AI 生图
    SMART_SCAN: int = 10     # OCR
    TEXT_GEN: int = 1        # AI 文字
```

---

## 四、交易类型

### 4.1 TransactionType 枚举

**增加积分 (正数金额)**:

| 类型 | 说明 |
|------|------|
| `subscription_grant` | 月度订阅发放 |
| `purchase` | 充值购买 |
| `topup_purchase` | Stripe 充值 |
| `signup_bonus` | 注册赠送 |
| `referral_bonus` | 推荐奖励 |
| `campaign_reward` | 活动奖励 |
| `refund` | 退款返还 |
| `admin_adjustment` | 管理员调整 |

**扣除积分 (负数金额)**:

| 类型 | 说明 |
|------|------|
| `ai_generation` | AI 生图 |
| `smart_scan` | OCR 识别 |
| `expiration` | 过期清零 |
| `monthly_reset` | 月度重置 |
| `monthly_credits_cleared` | 降级清零 |
| `marketplace_purchase` | 市场购买 |

---

## 五、数据库结构

### 5.1 profiles 表积分字段

```sql
-- 积分余额
credits_monthly INTEGER NOT NULL DEFAULT 0 CHECK (credits_monthly >= 0),
credits_permanent INTEGER NOT NULL DEFAULT 0 CHECK (credits_permanent >= 0),

-- 统计字段
credits_total_earned INTEGER DEFAULT 0,    -- 累计获得
credits_total_spent INTEGER DEFAULT 0,     -- 累计消耗
credits_last_updated_at TIMESTAMPTZ,       -- 最后更新时间
```

### 5.2 credit_transactions 表

```sql
CREATE TABLE credit_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id),
    
    -- 交易信息
    type TEXT NOT NULL,  -- TransactionType
    amount INTEGER NOT NULL,  -- 正数增加，负数扣除
    
    -- 余额快照
    balance_before_monthly INTEGER NOT NULL,
    balance_before_permanent INTEGER NOT NULL,
    balance_after_monthly INTEGER NOT NULL,
    balance_after_permanent INTEGER NOT NULL,
    
    -- 元数据
    description TEXT,
    reference_id TEXT,  -- 关联 ID (如订单号)
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 六、核心操作

### 6.1 积分扣除

```python
async def deduct_credits(
    user_id: UUID, 
    amount: int, 
    transaction_type: TransactionType,
    description: str = None
) -> Credits:
    """
    扣除积分 (原子操作)
    
    1. 检查余额是否充足
    2. 计算扣除后余额 (月度优先)
    3. 更新 profiles 表
    4. 记录 credit_transactions
    """
```

### 6.2 积分充值

```python
async def add_credits(
    user_id: UUID,
    amount: int,
    bucket: CreditBucket,  # MONTHLY 或 PERMANENT
    transaction_type: TransactionType,
    reference_id: str = None
) -> Credits:
    """
    增加积分 (原子操作)
    
    1. 更新对应桶的余额
    2. 更新累计获得统计
    3. 记录 credit_transactions
    """
```

### 6.3 月度重置

```python
async def reset_monthly_credits(user_id: UUID, new_amount: int):
    """
    月度积分重置 (订阅续期时)
    
    1. 清零当前月度积分 (记录 monthly_reset)
    2. 发放新的月度积分 (记录 subscription_grant)
    """
```

---

## 七、API 接口

### 7.1 获取积分余额

```http
GET /api/v1/billing/credits
```

响应：
```json
{
  "monthly": 45,
  "permanent": 200,
  "total": 245
}
```

### 7.2 获取交易历史

```http
GET /api/v1/billing/transactions?limit=20&offset=0
```

响应：
```json
{
  "items": [
    {
      "id": "uuid",
      "type": "ai_generation",
      "amount": -5,
      "balance_after": { "monthly": 45, "permanent": 200 },
      "description": "AI Image Generation",
      "created_at": "2026-02-05T10:30:00Z"
    }
  ],
  "total": 150
}
```

### 7.3 充值积分

```http
POST /api/v1/billing/credits/topup
{
  "plan_type": "credits_500"
}
```

---

## 八、业务流程

### 8.1 新用户注册

```
用户注册 
  → 创建 profile (tier=t1)
  → 发放注册奖励 (100 永久积分)
  → 记录 signup_bonus 交易
```

### 8.2 订阅升级

```
用户升级到 t2
  → Stripe 付款成功
  → 更新 tier = t2
  → 发放月度积分 (100 月度积分)
  → 记录 subscription_grant 交易
```

### 8.3 AI 功能使用

```
用户触发 AI 生图
  → 检查积分 >= 5
  → 扣除 5 积分 (月度优先)
  → 记录 ai_generation 交易
  → 调用 AI 服务
```

### 8.4 月度续期

```
订阅周期结束
  → Stripe Webhook (invoice.paid)
  → 清零剩余月度积分 (monthly_reset)
  → 发放新月度积分 (subscription_grant)
```

---

## 九、Value Object

### 9.1 Credits 类

```python
@dataclass(frozen=True)
class Credits:
    """不可变积分值对象"""
    monthly: int = 0
    permanent: int = 0
    
    @property
    def total(self) -> int:
        return self.monthly + self.permanent
    
    def has_enough(self, required: int) -> bool:
        return self.total >= required
    
    def deduct(self, amount: int) -> 'Credits':
        """返回扣除后的新 Credits 对象"""
    
    def add(self, amount: int, bucket: CreditBucket) -> 'Credits':
        """返回增加后的新 Credits 对象"""
```

### 9.2 不可变性保证

- `frozen=True` 确保实例创建后不可修改
- 所有操作返回**新对象**而非修改原对象
- 便于追踪状态变化和调试

---

## 十、相关文档

- [Tier 系统](../tier-system/overview.md)
- [Stripe 集成](../stripe-integration/)
- [API 参考 - Billing](../../03-api/billing.md)

---

**END OF DOCUMENT**
