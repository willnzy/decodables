# 积分完整生命周期

> 二维模型（来源类型 + 有效期）与 FEFO 扣费规则。

**状态**: active  
**版本**: 3.1.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Product Team  
**适用范围**: shared  
**source_repo**: backend  
**sync_required**: yes

---

## 积分类型（二维模型）

| 来源类型 | 代码 | 默认有效期 | 说明 |
|----------|------|-----------|------|
| 订阅积分 | `subscription` | 当月月底 | 订阅自动发放 |
| 购买积分 | `purchase` | 永久 | 付费购买 |
| 注册赠送 | `bonus_signup` | 永久 | 新用户赠送 |
| 邀请奖励 | `bonus_referral` | 永久 | 邀请激励 |
| 营销活动 | `bonus_campaign` | 30-90天 | 促销活动 |
| 客服补偿 | `compensation` | 永久 | 客服补偿 |
| 销售收入 | `earning` | 永久 | 素材/项目销售 |

---

## 扣费优先级（FEFO）

```
1. 先扣即将过期的积分 (expires_at 升序)
2. 永久积分按来源优先级:
   subscription > bonus_signup > bonus_referral > bonus_campaign > earning > purchase > compensation
```

退款回收顺序（反向）：

```
compensation → earning → purchase → bonus_campaign → bonus_referral → bonus_signup → subscription
```

---

## 数据结构 (核心表)

### credit_pools

```sql
CREATE TABLE credit_pools (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES profiles(id),
  source_type VARCHAR(30) NOT NULL,
  balance INT NOT NULL DEFAULT 0,
  expires_at TIMESTAMPTZ,
  source_id TEXT,
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### credit_transactions

```sql
CREATE TABLE credit_transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES profiles(id),
  pool_id UUID REFERENCES credit_pools(id),
  transaction_type VARCHAR(20) NOT NULL,
  amount INT NOT NULL,
  balance_before INT NOT NULL,
  balance_after INT NOT NULL,
  source_type VARCHAR(30) NOT NULL,
  source_id TEXT,
  feature VARCHAR(50),
  description TEXT,
  idempotency_key VARCHAR(100) UNIQUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 特殊场景

- 订阅暂停：积分冻结，不可消耗
- 退款不足：形成 `credits_debt`，新积分自动抵扣
- 过期清理：定时任务归零并记录流水
