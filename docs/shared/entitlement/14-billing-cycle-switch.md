# 年付/月付切换

> **版本**: v2.0
> **日期**: 2026-02-04
> **状态**: 产品确认
> **参考**: Stripe Proration

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [README.md](./README.md) | 文档导航索引 |
| [02-tier-config.md](./02-tier-config.md) | Tier 配置 |
| [15-credits-lifecycle.md](./15-credits-lifecycle.md) | 积分生命周期 |

---

## 一、计费周期类型

### 1.1 定价对比

| Plan | 月付 | 年付 | 年付折扣 |
|------|------|------|----------|
| Starter (t2) | $6.9/月 | $69/年 | 16% off |
| Pro (t3) | $9.9/月 | $99/年 | 16% off |

### 1.2 切换方向

| 方向 | 场景 | 处理方式 |
|------|------|----------|
| 月付 → 年付 | 用户想省钱 | 立即生效 + Proration |
| 年付 → 月付 | 用户不确定长期使用 | 当前周期结束后生效 |

---

## 二、月付 → 年付

### 2.1 Proration 计算

```
公式:
剩余价值 = 月付价格 × (剩余天数 / 30)
应付金额 = 年付价格 - 剩余价值

示例:
- 用户: Starter 月付 $6.9/月
- 当前周期已使用 10 天，剩余 20 天
- 切换到年付 $69/年

计算:
剩余价值 = $6.9 × (20/30) = $4.60
应付金额 = $69 - $4.60 = $64.40
```

### 2.2 切换流程

```
1. 用户选择切换到年付
2. 显示 Proration 计算明细
3. 用户确认支付差额
4. 立即生效，新周期从今日开始
5. 发送确认邮件和收据
```

### 2.3 积分处理

月付 → 年付时:
- 当月剩余的月度积分保留
- 从下月开始按年付方案发放

---

## 三、年付 → 月付

### 3.1 生效时间

**原则**: 年付 → 月付 不退款，当前周期结束后生效

```
示例:
- 用户: Pro 年付 $99/年
- 年付周期: 2026-01-01 到 2026-12-31
- 2026-03-15 申请切换到月付

处理:
- 2026-01-01 ~ 2026-12-31: 继续享受 Pro 年付权益
- 2027-01-01: 开始 Pro 月付 $9.9/月
```

### 3.2 切换流程

```
1. 用户选择切换到月付
2. 显示生效日期 (当前年付周期结束日)
3. 用户确认
4. 记录切换请求
5. 到期后自动切换
6. 发送确认邮件
```

### 3.3 取消切换

在年付周期结束前，用户可以取消切换请求:
- 进入订阅管理
- 点击 "取消切换"
- 保持年付状态

---

## 四、边界情况

### 4.1 切换 + 升降级

| 场景 | 处理 |
|------|------|
| 月付 t2 → 年付 t3 | 同时升级 + 切换周期，Proration 计算 |
| 年付 t3 → 月付 t2 | 当前周期结束后同时生效 |

### 4.2 切换 + 暂停

| 场景 | 处理 |
|------|------|
| 暂停中申请切换 | 不允许，需先恢复订阅 |
| 切换待生效期间暂停 | 允许暂停，切换请求保留 |

### 4.3 重复切换

```
月付 → 申请年付 → 取消 → 再次申请年付
✅ 允许，只要在生效前取消

年付 → 申请月付 → 取消 → 再次申请月付
✅ 允许，只要在生效前取消
```

---

## 五、UI 设计

### 5.1 切换入口

```
订阅管理页:
┌─────────────────────────────────┐
│ 当前方案: Pro Plan (月付)        │
│ 价格: $9.9/月                    │
│ 下次扣款: 2026-02-15             │
│                                  │
│ [切换到年付] 节省 16%            │
└─────────────────────────────────┘
```

### 5.2 Proration 确认

```
┌─────────────────────────────────┐
│ 切换到年付                        │
│                                  │
│ 原价: $99/年                     │
│ 已付月份抵扣: -$4.60             │
│ ─────────────────                │
│ 应付金额: $64.40                 │
│                                  │
│ 新周期: 2026-02-01 ~ 2027-01-31  │
│                                  │
│ [确认支付]  [取消]               │
└─────────────────────────────────┘
```

---

## 六、数据结构

### 6.1 切换请求记录

```sql
CREATE TABLE IF NOT EXISTS billing_cycle_changes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES profiles(user_id),
    from_cycle VARCHAR(10) NOT NULL, -- monthly, yearly
    to_cycle VARCHAR(10) NOT NULL,
    requested_at TIMESTAMPTZ DEFAULT NOW(),
    effective_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', -- pending, completed, cancelled
    proration_amount DECIMAL(10,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 七、API 接口

```python
# 切换计费周期
POST /api/v1/subscriptions/switch-cycle
{
    "to_cycle": "yearly"
}

# 预览 Proration
GET /api/v1/subscriptions/proration-preview?to_cycle=yearly
Response: {
    "current_cycle": "monthly",
    "to_cycle": "yearly",
    "current_price": 6.9,
    "new_price": 69,
    "remaining_value": 4.60,
    "amount_due": 64.40,
    "effective_date": "2026-02-01"
}

# 取消切换请求
DELETE /api/v1/subscriptions/cycle-change
```

---

**END OF DOCUMENT**
