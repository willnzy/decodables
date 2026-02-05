# 积分完整生命周期

> **版本**: v3.1
> **日期**: 2026-02-04
> **状态**: 产品确认
> **重大变更**: 采用二维模型（来源类型 + 有效期）
> **实现状态**: 🔴 数据库层待实现

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [README.md](./README.md) | 文档导航索引 |
| [01-permission-matrix.md](./01-permission-matrix.md) | 权限矩阵 |
| [18-refund-processing.md](./18-refund-processing.md) | 退款处理 |

---

## 一、积分类型（二维模型）

### 1.1 设计理念

采用**来源类型 + 有效期**二维模型，参考 Figma、Adobe、Canva 等业界最佳实践：

```
维度 1: 来源类型 (source_type) - 用于审计、报表、业务规则
维度 2: 有效期 (expires_at) - 控制积分生命周期
```

### 1.2 来源类型定义

| 来源类型 | 代码 | 默认有效期 | 说明 |
|----------|------|-----------|------|
| **订阅积分** | `subscription` | 当月月底 | 订阅自动发放，每月重置 |
| **购买积分** | `purchase` | **永久** | 用户付费购买，永不过期 |
| **注册赠送** | `bonus_signup` | **永久** | 新用户注册赠送 |
| **邀请奖励** | `bonus_referral` | **永久** | 邀请好友奖励 |
| **营销活动** | `bonus_campaign` | **30-90天** (可配) | 促销/节日活动，驱动紧迫感 |
| **客服补偿** | `compensation` | **永久** | 问题补偿，无限制 |
| **销售收入** | `earning` | **永久** | 卖素材/项目收入 |

### 1.3 扣费优先级（FEFO）

采用 **FEFO (First Expire, First Out)** 策略：

```
扣费规则:
1. 先扣即将过期的积分 (expires_at 升序)
2. 永久积分按来源优先级扣费:
   subscription > bonus_signup > bonus_referral > bonus_campaign > earning > purchase > compensation
```

**原理**:
- `subscription` 先扣：会重置，不用浪费
- `purchase` 后扣：用户花钱买的，应该最后消耗（体验好）
- `compensation` 最后扣：公司给的补偿，应该最后消耗

### 1.4 退款回收顺序（反向）

```
退款回收规则 (反向):
compensation → earning → purchase → bonus_campaign → bonus_referral → bonus_signup → subscription
```

---

## 二、数据结构

### 2.1 积分池表 (credit_pools)

```sql
-- 积分池表：每个用户可有多个积分池
CREATE TABLE IF NOT EXISTS credit_pools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

    -- 来源类型
    source_type VARCHAR(30) NOT NULL CHECK (source_type IN (
        'subscription',      -- 订阅发放
        'purchase',          -- 用户购买
        'bonus_signup',      -- 注册赠送
        'bonus_referral',    -- 邀请奖励
        'bonus_campaign',    -- 营销活动
        'compensation',      -- 客服补偿
        'earning'            -- 销售收入
    )),

    -- 余额与有效期
    balance INT NOT NULL DEFAULT 0 CHECK (balance >= 0),
    expires_at TIMESTAMPTZ,  -- NULL = 永久有效

    -- 来源追踪
    source_id TEXT,          -- 关联的订单/活动/交易 ID
    description TEXT,        -- 描述信息

    -- 元数据
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引：支持 FEFO 扣费查询
CREATE INDEX idx_credit_pools_user_expiry
ON credit_pools(user_id, COALESCE(expires_at, '9999-12-31'::timestamptz), source_type);

-- 索引：按用户查询
CREATE INDEX idx_credit_pools_user ON credit_pools(user_id);

-- 索引：过期积分清理
CREATE INDEX idx_credit_pools_expires ON credit_pools(expires_at)
WHERE expires_at IS NOT NULL AND balance > 0;
```

### 2.2 积分流水表 (credit_transactions)

```sql
-- 积分流水表：记录每笔积分变动
CREATE TABLE IF NOT EXISTS credit_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    pool_id UUID REFERENCES credit_pools(id),  -- 关联的积分池

    -- 交易类型
    transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN (
        'grant',       -- 发放
        'consume',     -- 消耗
        'expire',      -- 过期
        'refund',      -- 退款回收
        'adjust'       -- 调整 (Admin)
    )),

    -- 金额与余额
    amount INT NOT NULL,           -- 正数=获得, 负数=消耗
    balance_before INT NOT NULL,   -- 变动前余额
    balance_after INT NOT NULL,    -- 变动后余额

    -- 来源追踪
    source_type VARCHAR(30) NOT NULL,  -- 同 credit_pools.source_type
    source_id TEXT,                    -- 关联的订单/消费 ID
    feature VARCHAR(50),               -- 消耗的功能 (ai_generate, ocr, etc.)
    description TEXT,

    -- 幂等性
    idempotency_key VARCHAR(100) UNIQUE,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_credit_transactions_user ON credit_transactions(user_id, created_at DESC);
CREATE INDEX idx_credit_transactions_pool ON credit_transactions(pool_id);
```

### 2.3 profiles 表扩展

```sql
-- profiles 表增加汇总字段 (用于快速查询)
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS
    credits_total INT DEFAULT 0,      -- 总可用积分 (缓存)
    credits_debt INT DEFAULT 0;       -- 积分欠款

-- 注意: credits_total 是缓存字段，真实余额以 credit_pools 为准
```

---

## 三、积分获取

### 3.1 订阅发放 (subscription)

| Tier | 月度积分 | 发放时间 | 有效期 |
|------|----------|----------|--------|
| t1 (Free) | 0 | - | - |
| t2 (Starter) | 100 | 订阅日每月发放 | 当月月底 |
| t3 (Pro) | 200 | 订阅日每月发放 | 当月月底 |

```python
# 订阅积分发放
async def grant_subscription_credits(user_id: str, tier: str):
    amount = TIER_MONTHLY_CREDITS.get(tier, 0)
    if amount <= 0:
        return

    # 计算月底过期时间
    now = datetime.now()
    expires_at = (now.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)

    await create_credit_pool(
        user_id=user_id,
        source_type='subscription',
        balance=amount,
        expires_at=expires_at,
        description=f'{tier} 月度积分'
    )
```

### 3.2 注册赠送 (bonus_signup)

```python
# t1 用户注册赠送 100 永久积分
async def grant_signup_bonus(user_id: str):
    await create_credit_pool(
        user_id=user_id,
        source_type='bonus_signup',
        balance=100,
        expires_at=None,  # 永久
        description='新用户注册赠送'
    )
```

### 3.3 购买积分 (purchase)

| 档位 | 积分 | 价格 | 有效期 |
|------|------|------|--------|
| 小包 | 100 | $2.99 | **永久** |
| 中包 | 500 | $13.46 | **永久** |
| 大包 | 2000 | $47.84 | **永久** |

```python
# 购买积分入账
async def grant_purchased_credits(user_id: str, amount: int, order_id: str):
    await create_credit_pool(
        user_id=user_id,
        source_type='purchase',
        balance=amount,
        expires_at=None,  # 永久
        source_id=order_id,
        description=f'购买 {amount} 积分'
    )
```

### 3.4 邀请奖励 (bonus_referral)

```python
# 邀请好友奖励 50 永久积分
async def grant_referral_bonus(user_id: str, referred_user_id: str):
    await create_credit_pool(
        user_id=user_id,
        source_type='bonus_referral',
        balance=50,
        expires_at=None,  # 永久
        source_id=referred_user_id,
        description=f'邀请用户 {referred_user_id[:8]}...'
    )
```

### 3.5 营销活动 (bonus_campaign)

```python
# 营销活动积分 (有过期时间)
async def grant_campaign_bonus(user_id: str, amount: int, campaign_id: str, expires_days: int = 30):
    expires_at = datetime.now() + timedelta(days=expires_days)

    await create_credit_pool(
        user_id=user_id,
        source_type='bonus_campaign',
        balance=amount,
        expires_at=expires_at,  # 有期限
        source_id=campaign_id,
        description=f'活动奖励 - {campaign_id}'
    )
```

### 3.6 客服补偿 (compensation)

```python
# 客服补偿 (永久)
async def grant_compensation(user_id: str, amount: int, ticket_id: str, reason: str):
    await create_credit_pool(
        user_id=user_id,
        source_type='compensation',
        balance=amount,
        expires_at=None,  # 永久
        source_id=ticket_id,
        description=f'客服补偿: {reason}'
    )
```

### 3.7 销售收入 (earning)

```python
# 卖素材/项目收入 (永久)
async def grant_earning(user_id: str, amount: int, sale_id: str, item_name: str):
    await create_credit_pool(
        user_id=user_id,
        source_type='earning',
        balance=amount,
        expires_at=None,  # 永久
        source_id=sale_id,
        description=f'销售收入: {item_name}'
    )
```

---

## 四、积分消耗

### 4.1 AI 功能成本

| 功能 | 积分消耗 |
|------|----------|
| AI 生图 | 5 |
| AI 生 Page | 5 |
| OCR 识别 | 5 |

### 4.2 FEFO 扣费算法

```python
async def consume_credits(user_id: str, amount: int, feature: str) -> bool:
    """
    FEFO 扣费算法：先扣即将过期的，永久积分按来源优先级扣
    """
    # 1. 检查总余额
    total = await get_total_balance(user_id)
    if total < amount:
        raise InsufficientCreditsError(f'余额不足: 需要 {amount}, 当前 {total}')

    # 2. 获取所有有余额的积分池，按 FEFO 排序
    pools = await db.fetch_all("""
        SELECT id, source_type, balance, expires_at
        FROM credit_pools
        WHERE user_id = $1 AND balance > 0
        ORDER BY
            -- 先按过期时间排序 (NULL 放最后)
            COALESCE(expires_at, '9999-12-31'::timestamptz) ASC,
            -- 同为永久积分时，按来源优先级
            CASE source_type
                WHEN 'subscription' THEN 1
                WHEN 'bonus_signup' THEN 2
                WHEN 'bonus_referral' THEN 3
                WHEN 'bonus_campaign' THEN 4
                WHEN 'earning' THEN 5
                WHEN 'purchase' THEN 6
                WHEN 'compensation' THEN 7
            END ASC
    """, user_id)

    # 3. 按顺序扣费
    remaining = amount
    deductions = []

    for pool in pools:
        if remaining <= 0:
            break

        deduct = min(pool['balance'], remaining)
        remaining -= deduct
        deductions.append({
            'pool_id': pool['id'],
            'source_type': pool['source_type'],
            'amount': deduct
        })

    # 4. 执行扣费 (事务)
    async with db.transaction():
        for d in deductions:
            await db.execute("""
                UPDATE credit_pools SET balance = balance - $1, updated_at = NOW()
                WHERE id = $2
            """, d['amount'], d['pool_id'])

            # 记录流水
            await log_transaction(
                user_id=user_id,
                pool_id=d['pool_id'],
                transaction_type='consume',
                amount=-d['amount'],
                source_type=d['source_type'],
                feature=feature
            )

        # 更新汇总缓存
        await update_credits_total(user_id)

    return True
```

### 4.3 余额查询

```python
async def get_credit_balance(user_id: str) -> dict:
    """获取积分余额明细"""

    # 按来源类型汇总
    result = await db.fetch_all("""
        SELECT
            source_type,
            SUM(balance) as balance,
            MIN(expires_at) as nearest_expiry
        FROM credit_pools
        WHERE user_id = $1 AND balance > 0
        GROUP BY source_type
    """, user_id)

    balance = {
        'subscription': 0,
        'purchase': 0,
        'bonus_signup': 0,
        'bonus_referral': 0,
        'bonus_campaign': 0,
        'compensation': 0,
        'earning': 0,
        'total': 0,
        'expiring_soon': 0,  # 7 天内过期
        'debt': 0
    }

    for row in result:
        balance[row['source_type']] = row['balance']
        balance['total'] += row['balance']

        # 统计即将过期
        if row['nearest_expiry']:
            days_until = (row['nearest_expiry'] - datetime.now()).days
            if 0 <= days_until <= 7:
                balance['expiring_soon'] += row['balance']

    # 获取欠款
    user = await db.fetch_one("SELECT credits_debt FROM profiles WHERE user_id = $1", user_id)
    balance['debt'] = user['credits_debt'] or 0

    return balance
```

---

## 五、特殊场景

### 5.1 积分过期处理

```python
# 定时任务：每小时运行
async def expire_credits():
    """清理过期积分"""

    expired_pools = await db.fetch_all("""
        SELECT id, user_id, source_type, balance
        FROM credit_pools
        WHERE expires_at < NOW() AND balance > 0
    """)

    for pool in expired_pools:
        async with db.transaction():
            # 记录过期流水
            await log_transaction(
                user_id=pool['user_id'],
                pool_id=pool['id'],
                transaction_type='expire',
                amount=-pool['balance'],
                source_type=pool['source_type'],
                description='积分过期'
            )

            # 清零余额
            await db.execute("""
                UPDATE credit_pools SET balance = 0, updated_at = NOW()
                WHERE id = $1
            """, pool['id'])

            # 更新汇总
            await update_credits_total(pool['user_id'])
```

### 5.2 退款扣回（反向回收）

```python
async def revoke_credits_for_refund(user_id: str, amount: int, refund_id: str):
    """
    退款时扣回积分（反向顺序）
    """
    # 反向优先级
    pools = await db.fetch_all("""
        SELECT id, source_type, balance
        FROM credit_pools
        WHERE user_id = $1 AND balance > 0
        ORDER BY
            CASE source_type
                WHEN 'compensation' THEN 1
                WHEN 'earning' THEN 2
                WHEN 'purchase' THEN 3
                WHEN 'bonus_campaign' THEN 4
                WHEN 'bonus_referral' THEN 5
                WHEN 'bonus_signup' THEN 6
                WHEN 'subscription' THEN 7
            END ASC
    """, user_id)

    remaining = amount
    for pool in pools:
        if remaining <= 0:
            break

        deduct = min(pool['balance'], remaining)
        remaining -= deduct

        await db.execute("""
            UPDATE credit_pools SET balance = balance - $1 WHERE id = $2
        """, deduct, pool['id'])

        await log_transaction(
            user_id=user_id,
            pool_id=pool['id'],
            transaction_type='refund',
            amount=-deduct,
            source_type=pool['source_type'],
            source_id=refund_id,
            description='退款扣回'
        )

    # 余额不足则记录欠款
    if remaining > 0:
        await db.execute("""
            UPDATE profiles SET credits_debt = credits_debt + $1 WHERE user_id = $2
        """, remaining, user_id)

    await update_credits_total(user_id)
```

### 5.3 积分欠款处理

```python
async def handle_debt_on_grant(user_id: str, new_credits: int) -> int:
    """
    发放积分时，先抵扣欠款
    返回实际可用积分
    """
    user = await db.fetch_one("SELECT credits_debt FROM profiles WHERE user_id = $1", user_id)
    debt = user['credits_debt'] or 0

    if debt <= 0:
        return new_credits

    deduct = min(new_credits, debt)
    remaining = new_credits - deduct

    await db.execute("""
        UPDATE profiles SET credits_debt = credits_debt - $1 WHERE user_id = $2
    """, deduct, user_id)

    return remaining
```

### 5.4 积分冻结

```
触发条件:
- 订阅暂停
- 付款失败宽限期
- 账户安全审核

冻结处理:
- 所有积分池标记为 frozen
- 不可消耗，但不影响过期
- 解冻后立即可用
```

---

## 六、API 接口

### 6.1 查询余额

```python
GET /api/v1/credits/balance

Response: {
    "subscription": 150,
    "purchase": 200,
    "bonus_signup": 100,
    "bonus_referral": 50,
    "bonus_campaign": 30,
    "compensation": 0,
    "earning": 0,
    "total": 530,
    "expiring_soon": 30,  # 7 天内过期
    "debt": 0
}
```

### 6.2 消耗积分

```python
POST /api/v1/credits/consume
{
    "amount": 5,
    "feature": "ai_generate"
}

Response: {
    "success": true,
    "consumed": 5,
    "remaining": 525,
    "deductions": [
        {"source_type": "subscription", "amount": 5}
    ]
}
```

### 6.3 查询流水

```python
GET /api/v1/credits/transactions?limit=20&offset=0

Response: {
    "transactions": [
        {
            "id": "...",
            "transaction_type": "consume",
            "amount": -5,
            "source_type": "subscription",
            "feature": "ai_generate",
            "balance_after": 525,
            "created_at": "2026-02-04T10:30:00Z"
        }
    ],
    "total": 100
}
```

### 6.4 查询积分池明细

```python
GET /api/v1/credits/pools

Response: {
    "pools": [
        {
            "id": "...",
            "source_type": "subscription",
            "balance": 150,
            "expires_at": "2026-02-28T23:59:59Z",
            "created_at": "2026-02-01T00:00:00Z"
        },
        {
            "id": "...",
            "source_type": "purchase",
            "balance": 200,
            "expires_at": null,
            "created_at": "2026-01-15T10:00:00Z"
        }
    ]
}
```

---

## 七、前端展示

### 7.1 CreditsDisplay 组件

```typescript
interface CreditsBalance {
  subscription: number;
  purchase: number;
  bonus_signup: number;
  bonus_referral: number;
  bonus_campaign: number;
  compensation: number;
  earning: number;
  total: number;
  expiring_soon: number;
  debt: number;
}

function CreditsDisplay({ balance }: { balance: CreditsBalance }) {
  return (
    <div className="credits-display">
      {/* 总余额 */}
      <div className="total">
        <span className="label">可用积分</span>
        <span className="value">{balance.total}</span>
      </div>

      {/* 即将过期提醒 */}
      {balance.expiring_soon > 0 && (
        <Alert variant="warning">
          {balance.expiring_soon} 积分将在 7 天内过期
        </Alert>
      )}

      {/* 欠款提醒 */}
      {balance.debt > 0 && (
        <Alert variant="error">
          您有 {balance.debt} 积分欠款，新获得的积分将优先抵扣
        </Alert>
      )}

      {/* 明细展开 */}
      <Collapsible title="积分明细">
        <div className="breakdown">
          {balance.subscription > 0 && (
            <div className="item">
              <span>订阅积分</span>
              <span>{balance.subscription}</span>
            </div>
          )}
          {balance.purchase > 0 && (
            <div className="item">
              <span>购买积分</span>
              <span>{balance.purchase}</span>
            </div>
          )}
          {/* ... 其他类型 */}
        </div>
      </Collapsible>
    </div>
  );
}
```

### 7.2 过期提醒 Banner

```typescript
function ExpiringCreditsBanner({ expiringSoon }: { expiringSoon: number }) {
  if (expiringSoon <= 0) return null;

  return (
    <Banner variant="warning" dismissible>
      <Icon name="clock" />
      <span>您有 {expiringSoon} 积分将在 7 天内过期，请尽快使用</span>
      <Button size="sm" variant="primary">
        立即使用
      </Button>
    </Banner>
  );
}
```

---

## 八、监控指标

| 指标 | 告警阈值 | 说明 |
|------|----------|------|
| 日均积分消耗 | 异常波动 >50% | 可能存在滥用 |
| 过期积分占比 | > 30% | 用户活跃度低 |
| 欠款用户数 | > 100 | 需要关注退款策略 |
| 积分池数量/用户 | > 50 | 需要合并或清理 |

---

## 九、积分池运维场景

> 补充审计发现的遗漏场景：积分池合并/拆分

### 9.1 积分池合并

**触发条件**：用户积分池数量超过阈值（默认 50），影响查询性能

**合并规则**：

```sql
-- 合并同类型、同过期日期的积分池
WITH pools_to_merge AS (
    SELECT
        user_id,
        source_type,
        DATE(expires_at) as expiry_date,  -- 按天合并
        COUNT(*) as pool_count,
        SUM(balance) as total_balance
    FROM credit_pools
    WHERE balance > 0
    GROUP BY user_id, source_type, DATE(expires_at)
    HAVING COUNT(*) > 1
)
-- 执行合并
INSERT INTO credit_pools (user_id, source_type, balance, expires_at, description)
SELECT
    user_id,
    source_type,
    total_balance,
    expiry_date + INTERVAL '23 hours 59 minutes 59 seconds',
    '系统合并 - 原 ' || pool_count || ' 个积分池'
FROM pools_to_merge;

-- 删除已合并的旧记录
DELETE FROM credit_pools
WHERE id IN (SELECT id FROM old_pools_to_delete);
```

**合并触发方式**：

| 方式 | 说明 | 优先级 |
|------|------|--------|
| 定时任务 | 每周自动合并超过 50 个池的用户 | 🟢 P2 |
| 手动触发 | Admin 页面操作 | 🟢 P2 |
| 消费时合并 | 消费后池数量超阈值则触发 | 🟡 P1 |

### 9.2 积分池拆分

**触发条件**：退款时需要从特定来源回收积分，但该池已被部分消费

**拆分场景示例**：

```
原始状态:
- 池 A: purchase, balance=80, 原始=100 (已消费 20)
- 用户请求退款 100 积分

问题: 池 A 只剩 80，无法完全回收

处理方式: 欠款机制（已在 §五 定义），而非拆分
```

**设计决策**：不支持积分池拆分，使用欠款机制替代

| 方案 | 优点 | 缺点 | 采用 |
|------|------|------|:----:|
| **欠款机制** | 简单，不破坏已有池结构 | 需要额外字段 | ✅ |
| 池拆分 | 精确匹配退款 | 复杂，易出错 | ❌ |
| 比例回收 | 平均分摊 | 不符合财务要求 | ❌ |

### 9.3 清零与重置

**月度积分重置**：

```sql
-- 每月 1 日 00:00:00 UTC 执行
-- 1. 清零上月未消费的月度积分
UPDATE credit_pools
SET balance = 0,
    updated_at = NOW()
WHERE source_type = 'subscription'
  AND expires_at < NOW()
  AND balance > 0;

-- 2. 记录过期流水
INSERT INTO credit_transactions (user_id, type, amount, balance_after, source_type, description)
SELECT
    user_id,
    'expired',
    -balance,
    0,
    'subscription',
    '月度积分过期'
FROM credit_pools
WHERE source_type = 'subscription'
  AND expires_at < NOW()
  AND balance > 0;
```

**全额清零场景**（管理员操作）：

| 场景 | 处理方式 | 审计要求 |
|------|---------|---------|
| 账户冻结 | 保留池但标记 frozen | 需记录原因 |
| 退款滥用 | 扣除所有可用积分 | 需双人审批 |
| 测试账户清理 | 物理删除所有池 | 需标记为测试 |

---

## 十、配置项

```sql
INSERT INTO system_configs (key, value, value_type, config_group, description) VALUES
-- 有效期配置
('credits.campaign_default_days', '30', 'integer', 'credits', '营销活动积分默认有效天数'),
('credits.campaign_max_days', '90', 'integer', 'credits', '营销活动积分最大有效天数'),

-- 注册赠送
('credits.signup_bonus', '100', 'integer', 'credits', '注册赠送积分'),

-- 邀请奖励
('credits.referral_bonus', '50', 'integer', 'credits', '邀请奖励积分'),
('credits.referral_max_per_year', '500', 'integer', 'credits', '年度邀请奖励上限'),

-- 过期提醒
('credits.expiry_warning_days', '7', 'integer', 'credits', '过期前提醒天数');
```

---

## 十一、迁移方案

### 11.1 从旧模型迁移

```sql
-- 将旧的 profiles 字段迁移到 credit_pools 表
INSERT INTO credit_pools (user_id, source_type, balance, expires_at, description)
SELECT
    user_id,
    'subscription',
    credits_monthly,
    (DATE_TRUNC('month', NOW()) + INTERVAL '1 month' - INTERVAL '1 second'),
    '迁移: 月度积分'
FROM profiles
WHERE credits_monthly > 0;

INSERT INTO credit_pools (user_id, source_type, balance, expires_at, description)
SELECT user_id, 'purchase', credits_permanent, NULL, '迁移: 永久积分'
FROM profiles
WHERE credits_permanent > 0;

INSERT INTO credit_pools (user_id, source_type, balance, expires_at, description)
SELECT user_id, 'bonus_campaign', credits_gift, NULL, '迁移: 赠送积分 (原 gift)'
FROM profiles
WHERE credits_gift > 0;

INSERT INTO credit_pools (user_id, source_type, balance, expires_at, description)
SELECT user_id, 'compensation', credits_compensation, NULL, '迁移: 补偿积分'
FROM profiles
WHERE credits_compensation > 0;
```

### 11.2 兼容性

迁移完成后，保留 profiles 表的旧字段作为缓存，通过触发器同步：

```sql
-- 更新 credits_total 缓存
CREATE OR REPLACE FUNCTION update_profile_credits_cache()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE profiles
    SET credits_total = (
        SELECT COALESCE(SUM(balance), 0)
        FROM credit_pools
        WHERE user_id = NEW.user_id AND balance > 0
    )
    WHERE user_id = NEW.user_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_credit_pools_update
AFTER INSERT OR UPDATE OR DELETE ON credit_pools
FOR EACH ROW EXECUTE FUNCTION update_profile_credits_cache();
```

---

## 十二、待实现清单

> ⚠️ **审计发现** (2026-02-04): 以下内容已设计但尚未在数据库/后端实现

### 12.1 数据库层 (🔴 P0)

| # | 待实现项 | 说明 | 优先级 |
|---|---------|------|--------|
| 1 | **创建 `credit_pools` 表** | 积分二维模型核心表，当前系统仍使用旧的 profiles 二桶模型 | 🔴 P0 |
| 2 | **创建 FEFO 查询索引** | `idx_credit_pools_user_expiry` 索引支持高效扣费查询 | 🔴 P0 |
| 3 | **创建过期清理索引** | `idx_credit_pools_expires` 索引支持定时任务清理 | 🟡 P1 |
| 4 | **扩展 `profiles` 表** | 添加 `credits_total` (缓存), `credits_debt` (欠款) 字段 | 🔴 P0 |
| 5 | **扩展 `credit_transactions` 表** | 添加 `pool_id`, `source_type` CHECK (7种) 约束 | 🔴 P0 |
| 6 | **创建 `add_credits_atomic` RPC** | 原子发放积分，支持欠款抵扣 | 🔴 P0 |
| 7 | **更新 `deduct_credits_atomic` RPC** | 基于 credit_pools 实现 FEFO 算法 | 🔴 P0 |
| 8 | **创建缓存同步触发器** | `trg_credit_pools_update` 同步 profiles.credits_total | 🟡 P1 |

### 12.2 后端逻辑层 (🟡 P1)

| # | 待实现项 | 说明 |
|---|---------|------|
| 1 | 积分池 Repository | `CreditPoolRepository` CRUD 操作 |
| 2 | FEFO 扣费 Service | `consume_credits()` 按优先级扣费 |
| 3 | 退款回收 Service | `revoke_credits_for_refund()` 反向回收 |
| 4 | 过期处理定时任务 | 每小时清理过期积分 |
| 5 | 欠款处理逻辑 | 新积分自动抵扣欠款 |

### 12.3 前端展示层 (🟡 P1)

| # | 待实现项 | 说明 |
|---|---------|------|
| 1 | `CreditsDisplay` 组件升级 | 支持 7 种来源类型显示 |
| 2 | 过期提醒 Banner | `ExpiringCreditsBanner` 组件 |
| 3 | 积分明细 Collapsible | 展开显示各类型余额 |

### 12.4 数据迁移 (⚠️ 一次性)

| # | 待实现项 | 说明 |
|---|---------|------|
| 1 | 旧数据迁移脚本 | 将 profiles 二桶模型数据迁移到 credit_pools |
| 2 | 数据一致性验证 | 迁移后验证总余额一致 |

---

**END OF DOCUMENT**
