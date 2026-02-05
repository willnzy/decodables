# 促销规则

> Promotions - 促销活动与优惠规则

> **同步范围**: [fullstack]
> **状态**: 🟡 待验证
> **最后更新**: 2026-02-05
> **数据来源**: `v1/shared/entitlement/`, Stripe Docs

---

## 一、概述

促销系统支持多种优惠活动，包括折扣码、限时优惠、捆绑销售等。

---

## 二、促销类型

### 2.1 折扣码 (Promo Code)

```python
class PromoCodeType(Enum):
    PERCENTAGE = "percentage"  # 百分比折扣
    FIXED = "fixed"            # 固定金额
    CREDITS = "credits"        # 赠送积分
```

### 2.2 限时优惠

| 类型 | 描述 | 示例 |
|------|------|------|
| 首购优惠 | 首次订阅特价 | 首月 $4.99 |
| 节日活动 | 特定时间段折扣 | 黑五 50% off |
| 闪购 | 限时抢购 | 24 小时特价 |

### 2.3 捆绑优惠

```
年付优惠:
├── 月付: $9.9/月 = $118.8/年
├── 年付: $7.9/月 = $94.8/年
└── 节省: $24/年 (20% off)
```

---

## 三、数据模型

### 3.1 促销活动

```python
class Promotion:
    id: UUID
    name: str
    code: Optional[str]        # 折扣码 (可选)
    type: str                  # percentage/fixed/credits
    value: Decimal             # 折扣值
    min_purchase: Optional[Decimal]  # 最低消费
    max_discount: Optional[Decimal]  # 最大折扣
    applicable_tiers: List[str]      # 适用层级
    applicable_products: List[str]   # 适用产品
    start_at: datetime
    end_at: datetime
    usage_limit: Optional[int]       # 总使用限制
    per_user_limit: int              # 每用户限制
    is_active: bool
    created_at: datetime
```

### 3.2 数据库 Schema

```sql
CREATE TABLE promotions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    code VARCHAR(50) UNIQUE,
    type VARCHAR(20) NOT NULL,
    value DECIMAL(10, 2) NOT NULL,
    min_purchase DECIMAL(10, 2),
    max_discount DECIMAL(10, 2),
    applicable_tiers TEXT[],
    applicable_products TEXT[],
    start_at TIMESTAMPTZ NOT NULL,
    end_at TIMESTAMPTZ NOT NULL,
    usage_limit INTEGER,
    per_user_limit INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE promotion_usages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    promotion_id UUID REFERENCES promotions(id),
    user_id UUID REFERENCES profiles(id),
    order_id UUID,
    discount_amount DECIMAL(10, 2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(promotion_id, user_id, order_id)
);
```

---

## 四、验证规则

### 4.1 折扣码验证

```python
async def validate_promo_code(
    code: str,
    user_id: UUID,
    tier: str,
    purchase_amount: Decimal
) -> ValidationResult:
    """
    验证折扣码
    
    检查项:
    1. 折扣码存在且有效
    2. 在有效期内
    3. 未达到使用上限
    4. 用户未超过使用次数
    5. 满足最低消费
    6. 适用于当前层级/产品
    """
    promo = await get_promotion_by_code(code)
    
    if not promo:
        return ValidationResult(valid=False, error="INVALID_CODE")
    
    if not promo.is_active:
        return ValidationResult(valid=False, error="INACTIVE")
    
    now = datetime.utcnow()
    if now < promo.start_at or now > promo.end_at:
        return ValidationResult(valid=False, error="EXPIRED")
    
    if promo.usage_limit:
        usage_count = await get_usage_count(promo.id)
        if usage_count >= promo.usage_limit:
            return ValidationResult(valid=False, error="LIMIT_REACHED")
    
    user_usage = await get_user_usage_count(promo.id, user_id)
    if user_usage >= promo.per_user_limit:
        return ValidationResult(valid=False, error="USER_LIMIT_REACHED")
    
    if promo.min_purchase and purchase_amount < promo.min_purchase:
        return ValidationResult(
            valid=False, 
            error="MIN_PURCHASE_NOT_MET",
            min_required=promo.min_purchase
        )
    
    if promo.applicable_tiers and tier not in promo.applicable_tiers:
        return ValidationResult(valid=False, error="NOT_APPLICABLE")
    
    # 计算折扣
    discount = calculate_discount(promo, purchase_amount)
    
    return ValidationResult(
        valid=True,
        promotion=promo,
        discount_amount=discount
    )
```

### 4.2 折扣计算

```python
def calculate_discount(promo: Promotion, amount: Decimal) -> Decimal:
    """计算折扣金额"""
    if promo.type == "percentage":
        discount = amount * (promo.value / 100)
    elif promo.type == "fixed":
        discount = promo.value
    else:
        discount = Decimal(0)
    
    # 应用最大折扣限制
    if promo.max_discount:
        discount = min(discount, promo.max_discount)
    
    # 不能超过原价
    return min(discount, amount)
```

---

## 五、促销场景

### 5.1 新用户首购

```python
# 系统自动应用
NEW_USER_PROMO = {
    "name": "新用户首购优惠",
    "type": "percentage",
    "value": 30,  # 30% off
    "applicable_tiers": ["t1"],  # 仅免费用户
    "per_user_limit": 1,
}
```

### 5.2 节日活动

```python
# 黑五活动示例
BLACK_FRIDAY_PROMO = {
    "name": "黑五特惠",
    "code": "BF2026",
    "type": "percentage",
    "value": 50,  # 50% off
    "start_at": "2026-11-25T00:00:00Z",
    "end_at": "2026-11-30T23:59:59Z",
    "usage_limit": 1000,
}
```

### 5.3 推荐奖励

```python
# 推荐人专属优惠
REFERRAL_PROMO = {
    "name": "推荐人专属",
    "type": "credits",
    "value": 50,  # 50 积分
    "auto_apply": True,  # 自动应用
}
```

---

## 六、Stripe 集成

### 6.1 折扣券创建

```python
async def create_stripe_coupon(promo: Promotion) -> str:
    """在 Stripe 创建折扣券"""
    if promo.type == "percentage":
        coupon = await stripe.Coupon.create(
            percent_off=float(promo.value),
            duration="once",
            metadata={"promotion_id": str(promo.id)}
        )
    else:
        coupon = await stripe.Coupon.create(
            amount_off=int(promo.value * 100),
            currency="usd",
            duration="once",
            metadata={"promotion_id": str(promo.id)}
        )
    
    return coupon.id
```

### 6.2 结账时应用

```python
async def apply_promo_to_checkout(
    session_params: dict,
    promo_code: str
) -> dict:
    """在 Stripe Checkout 应用折扣"""
    promo = await get_promotion_by_code(promo_code)
    
    if promo and promo.stripe_coupon_id:
        session_params["discounts"] = [
            {"coupon": promo.stripe_coupon_id}
        ]
    
    return session_params
```

---

## 七、API 端点

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v1/promotions/validate` | 验证折扣码 |
| GET | `/api/v1/promotions/active` | 获取当前活动 |
| POST | `/api/v1/promotions/apply` | 应用折扣码 |

---

## 八、Admin 管理

### 8.1 创建促销

```json
POST /api/admin/v1/promotions
{
    "name": "春节特惠",
    "code": "CNY2026",
    "type": "percentage",
    "value": 20,
    "start_at": "2026-02-01T00:00:00Z",
    "end_at": "2026-02-15T23:59:59Z",
    "usage_limit": 500
}
```

### 8.2 促销统计

```python
async def get_promotion_stats(promo_id: UUID) -> dict:
    """获取促销统计"""
    return {
        "total_usage": 150,
        "total_discount": Decimal("1500.00"),
        "conversion_rate": 0.65,
        "revenue_impact": Decimal("3500.00")
    }
```

---

## 九、相关文档

- [Billing 架构](../../04-engineering/modules/billing/architecture.md)
- [权益策略规则](./policy-rules.md)
- [推荐系统](../../04-engineering/modules/user-capabilities/referrals-system.md)
