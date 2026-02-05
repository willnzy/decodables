# 限时优惠与倒计时

> **版本**: v2.0
> **日期**: 2026-02-04
> **状态**: 产品确认

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [README.md](./README.md) | 文档导航索引 |
| [20-referral-rewards.md](./20-referral-rewards.md) | 邀请奖励 |
| [21-education-discount.md](./21-education-discount.md) | 教育优惠 |

---

## 一、促销类型

### 1.1 类型定义

| 类型 | 说明 | 适用范围 |
|------|------|----------|
| **限时折扣** | 指定时间段内的折扣 | 订阅/积分 |
| **首购优惠** | 首次购买专享折扣 | 订阅 |
| **节日活动** | 特定节日的促销 | 全部 |
| **用户召回** | 流失用户专属优惠 | 订阅 |

### 1.2 折扣方式

| 方式 | 示例 | 说明 |
|------|------|------|
| 百分比折扣 | 20% off | 按原价百分比 |
| 固定金额减免 | $5 off | 减去固定金额 |
| 固定价格 | $4.99 | 直接设定价格 |
| 免费试用延长 | +7 days | 延长试用期 |

---

## 二、促销规则

### 2.1 优先级规则

当多个促销同时生效时，按以下优先级:

```
1. 用户专属优惠 (召回优惠)
2. 首购优惠
3. 限时促销
4. 默认价格

规则: 不叠加，取优先级最高的一个
```

### 2.2 使用限制

| 限制项 | 规则 |
|--------|------|
| 每用户使用次数 | 可配置 (默认 1 次) |
| 总使用次数 | 可配置 (无限制或固定数量) |
| 适用 Tier | 可配置 (全部或指定) |
| 新用户限定 | 可配置 (是/否) |

---

## 三、倒计时设计

### 3.1 显示规则

```
> 7 天: 显示日期 "优惠截止 Feb 15"
≤ 7 天: 显示天数 "还剩 5 天"
≤ 24 小时: 显示时分秒 "23:59:45"
已结束: 显示 "优惠已结束"
```

### 3.2 UI 展示位置

| 位置 | 显示内容 |
|------|----------|
| Pricing 页面 | Banner + 倒计时 |
| Dashboard | 小型提示卡片 |
| 升级弹窗 | 强调折扣信息 |

### 3.3 倒计时组件

```
┌─────────────────────────────────┐
│ 🔥 限时优惠 - Pro Plan 20% off  │
│                                 │
│   ┌──┐  ┌──┐  ┌──┐  ┌──┐      │
│   │05│: │23│: │59│: │45│       │
│   └──┘  └──┘  └──┘  └──┘       │
│   天     时     分     秒       │
│                                 │
│ [立即升级]                      │
└─────────────────────────────────┘
```

---

## 四、促销配置

### 4.1 数据结构

```sql
CREATE TABLE IF NOT EXISTS promotions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) UNIQUE, -- 促销码 (可选)
    name VARCHAR(100) NOT NULL,
    description TEXT,
    discount_type VARCHAR(20) NOT NULL, -- percentage, fixed_amount, fixed_price, trial_extension
    discount_value DECIMAL(10,2) NOT NULL,
    applicable_products TEXT[], -- 适用产品: ['t2_monthly', 't3_yearly', 'credits_500']
    start_at TIMESTAMPTZ NOT NULL,
    end_at TIMESTAMPTZ NOT NULL,
    max_uses INT, -- NULL = 无限制
    current_uses INT DEFAULT 0,
    max_uses_per_user INT DEFAULT 1,
    new_users_only BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 用户促销使用记录
CREATE TABLE IF NOT EXISTS promotion_usages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    promotion_id UUID NOT NULL REFERENCES promotions(id),
    user_id UUID NOT NULL REFERENCES profiles(id),
    used_at TIMESTAMPTZ DEFAULT NOW(),
    order_id UUID, -- 关联订单
    discount_amount DECIMAL(10,2) NOT NULL
);

-- 索引
CREATE INDEX idx_promotions_active ON promotions(is_active, start_at, end_at);
CREATE INDEX idx_promotion_usages_user ON promotion_usages(user_id);
```

### 4.2 配置示例

```json
{
  "name": "2026 春节促销",
  "code": "CNY2026",
  "discount_type": "percentage",
  "discount_value": 20,
  "applicable_products": ["t2_monthly", "t2_yearly", "t3_monthly", "t3_yearly"],
  "start_at": "2026-01-25T00:00:00Z",
  "end_at": "2026-02-10T23:59:59Z",
  "max_uses": 1000,
  "max_uses_per_user": 1,
  "new_users_only": false
}
```

---

## 五、促销码系统

### 5.1 促销码规则

| 属性 | 规则 |
|------|------|
| 长度 | 4-20 字符 |
| 字符 | 大写字母 + 数字 |
| 格式 | 无特殊字符 |

### 5.2 使用流程

```
1. 用户在 Checkout 页面输入促销码
2. 验证促销码有效性
3. 显示折扣预览
4. 完成支付
5. 记录促销使用
```

### 5.3 验证逻辑

```python
async def validate_promo_code(code: str, user_id: str, product: str):
    promo = await get_promotion_by_code(code)

    # 检查促销是否存在
    if not promo:
        raise InvalidPromoCode("促销码不存在")

    # 检查是否激活
    if not promo.is_active:
        raise InvalidPromoCode("促销码已停用")

    # 检查时间范围
    now = datetime.utcnow()
    if now < promo.start_at or now > promo.end_at:
        raise InvalidPromoCode("促销码不在有效期内")

    # 检查产品适用
    if product not in promo.applicable_products:
        raise InvalidPromoCode("促销码不适用于此产品")

    # 检查总使用次数
    if promo.max_uses and promo.current_uses >= promo.max_uses:
        raise InvalidPromoCode("促销码已达使用上限")

    # 检查用户使用次数
    user_uses = await get_user_promo_uses(promo.id, user_id)
    if user_uses >= promo.max_uses_per_user:
        raise InvalidPromoCode("您已使用过此促销码")

    # 检查新用户限定
    if promo.new_users_only:
        has_orders = await user_has_orders(user_id)
        if has_orders:
            raise InvalidPromoCode("促销码仅限新用户")

    return promo
```

---

## 六、API 接口

```python
# 验证促销码
POST /api/v1/promotions/validate
{
    "code": "CNY2026",
    "product": "t3_monthly"
}
Response: {
    "valid": true,
    "discount_type": "percentage",
    "discount_value": 20,
    "final_price": 7.92,
    "original_price": 9.90
}

# 获取当前有效促销 (用于展示)
GET /api/v1/promotions/active
Response: {
    "promotions": [
        {
            "name": "春节促销",
            "discount_type": "percentage",
            "discount_value": 20,
            "end_at": "2026-02-10T23:59:59Z",
            "applicable_products": [...]
        }
    ]
}
```

---

## 七、运营配置

### 7.1 Admin 功能

- 创建/编辑/停用促销活动
- 查看促销使用数据
- 批量生成促销码
- 导出使用报告

### 7.2 监控指标

| 指标 | 说明 |
|------|------|
| 促销转化率 | 使用促销码的订单 / 总订单 |
| 促销收入影响 | 折扣金额 / 原价收入 |
| 热门促销码 | 使用次数最多的促销 |

---

**END OF DOCUMENT**
