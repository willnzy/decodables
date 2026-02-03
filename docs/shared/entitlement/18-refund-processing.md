# 退款完整处理流程

> **版本**: v2.0
> **日期**: 2026-02-04
> **状态**: 产品确认

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [README.md](./README.md) | 文档导航索引 |
| [12-tier-downgrade.md](./12-tier-downgrade.md) | Tier 降级处理 |
| [15-credits-lifecycle.md](./15-credits-lifecycle.md) | 积分生命周期 |
| [17-invoice-management.md](./17-invoice-management.md) | 发票管理 |

---

## 一、退款政策

### 1.1 退款类型

| 类型 | 说明 | 处理时间 |
|------|------|----------|
| **全额退款** | 退还全部付款金额 | 3-5 工作日 |
| **部分退款** | 退还部分付款金额 | 3-5 工作日 |
| **积分补偿** | 不退款，补偿等值积分 | 即时 |

### 1.2 退款条件

| 产品类型 | 退款条件 | 时间限制 |
|----------|----------|----------|
| 订阅 (首次) | 无条件退款 | 付款后 7 天内 |
| 订阅 (续费) | 需审核 | 付款后 3 天内 |
| 积分充值 | 未使用部分可退 | 付款后 30 天内 |
| 商城购买 | 不支持退款 | - |

---

## 二、退款流程

### 2.1 用户申请退款

```
1. 进入账户设置 → 订阅管理
2. 点击 "申请退款"
3. 选择退款原因
4. 提交申请
5. 等待审核 (1-3 工作日)
6. 退款处理 (3-5 工作日到账)
```

### 2.2 退款原因选项

```
- 功能不符合预期
- 技术问题无法解决
- 误操作/重复购买
- 价格原因
- 其他 (需填写说明)
```

### 2.3 审核标准

| 条件 | 自动批准 | 需人工审核 |
|------|----------|------------|
| 首次订阅 7 天内 | ✅ | - |
| 续费订阅 3 天内 | - | ✅ |
| 积分未使用 | ✅ | - |
| 积分已使用部分 | - | ✅ |
| 多次退款历史 | - | ✅ |

---

## 三、积分扣回

### 3.1 扣回规则

退款时需要扣回已发放的积分:

```
订阅退款:
- 扣回本周期发放的月度积分

积分充值退款:
- 扣回购买的全部积分 (按剩余比例计算)

计算公式:
扣回积分 = 购买积分 - 已消耗积分
```

### 3.2 积分不足处理

如果用户已消耗积分超过退款金额对应积分:

```
方案 1: 拒绝退款
- 告知用户积分已消耗过多

方案 2: 部分退款
- 只退还未消耗积分对应金额

方案 3: 记录欠款
- 全额退款
- 欠款记入 credits_debt
- 下次充值/发放时扣回
```

### 3.3 扣回顺序

```
按逆优先级扣回:
1. compensation (补偿积分)
2. gift (赠送积分)
3. permanent (永久积分)
4. monthly (月度积分)
```

---

## 四、权限处理

### 4.1 订阅退款后

```
退款成功后立即:
1. 取消订阅
2. Tier 降级为 t1
3. 触发 Graceful Degradation
4. 超限资源变为只读
5. 发送确认邮件
```

### 4.2 积分退款后

```
退款成功后立即:
1. 扣回对应积分
2. 更新余额
3. 记录交易日志
4. 发送确认邮件
```

---

## 五、Stripe 退款处理

### 5.1 退款 API

```python
# 创建退款
stripe.Refund.create(
    payment_intent="pi_xxx",
    amount=990,  # 部分退款时指定金额 (分)
    reason="requested_by_customer"
)

# Webhook 处理
@app.post("/webhooks/stripe")
async def handle_webhook(event: StripeEvent):
    if event.type == "charge.refunded":
        await process_refund(event.data.object)
```

### 5.2 退款状态

| Stripe 状态 | 系统状态 | 说明 |
|-------------|----------|------|
| succeeded | completed | 退款成功 |
| pending | processing | 退款处理中 |
| failed | failed | 退款失败 |
| canceled | cancelled | 退款取消 |

---

## 六、数据结构

### 6.1 退款记录表

```sql
CREATE TABLE IF NOT EXISTS refunds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES profiles(user_id),
    transaction_id UUID NOT NULL, -- 原交易ID
    stripe_refund_id TEXT,
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    refund_type VARCHAR(20) NOT NULL, -- full, partial, credits
    reason VARCHAR(50),
    reason_detail TEXT,
    credits_deducted INT DEFAULT 0,
    credits_debt INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',
    requested_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    processed_by TEXT -- admin user_id (如果是人工审核)
);

-- 索引
CREATE INDEX idx_refunds_user ON refunds(user_id, created_at DESC);
CREATE INDEX idx_refunds_status ON refunds(status);
```

---

## 七、通知策略

| 事件 | 通知方式 | 内容 |
|------|----------|------|
| 申请已收到 | 邮件 | 确认收到退款申请 |
| 审核通过 | 邮件 | 退款已批准，处理中 |
| 退款成功 | 邮件 + Credit Note | 退款已到账 |
| 审核拒绝 | 邮件 | 说明拒绝原因 |

---

## 八、监控指标

| 指标 | 告警阈值 | 说明 |
|------|----------|------|
| 日退款率 | > 5% | 可能存在产品问题 |
| 退款处理时长 | > 5 天 | 流程效率问题 |
| 重复退款用户 | > 3 次 | 可能存在滥用 |

---

## 九、API 接口

```python
# 申请退款
POST /api/v1/refunds
{
    "transaction_id": "uuid",
    "reason": "feature_not_as_expected",
    "reason_detail": "详细说明"
}

# 查询退款状态
GET /api/v1/refunds/{refund_id}

# 查询退款历史
GET /api/v1/refunds?limit=20&offset=0
```

---

**END OF DOCUMENT**
