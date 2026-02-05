# Referrals System - 推荐系统

> 用户推荐与返利机制设计

**验证状态**: 🟢 已验证  
**同步范围**: [fullstack]  
**代码来源**: `domains/referrals/`, `api/user/referrals.py`

---

## 一、概述

推荐系统允许用户通过分享专属推荐码邀请新用户注册，双方均可获得积分奖励。

---

## 二、核心概念

### 2.1 推荐码

每个用户都有唯一的推荐码：

```python
def generate_referral_code(self, user_id: str) -> str:
    """
    生成推荐码
    格式: XXXX-XXXX (8字符, 基于 user_id 哈希)
    """
    timestamp = str(int(datetime.now(timezone.utc).timestamp()))
    raw = f"{user_id}:{timestamp}"
    hash_obj = hashlib.sha256(raw.encode())
    hash_hex = hash_obj.hexdigest()[:8].upper()
    return f"{hash_hex[:4]}-{hash_hex[4:]}"
```

### 2.2 推荐关系

```
推荐人 (Referrer) ──推荐码──> 被推荐人 (Referee)
       │                           │
       │                           │
       ▼                           ▼
   获得奖励                    获得奖励
   (50 积分)                   (注册赠送)
```

### 2.3 状态流转

```
pending ──(被推荐人完成条件)──> completed
   │
   │──(超过有效期)──> expired
```

---

## 三、数据模型

### 3.1 Referral Entity

```python
class ReferralEntity(BaseModel):
    id: str
    referrer_id: str           # 推荐人 ID
    referee_id: str            # 被推荐人 ID
    referral_code: str         # 推荐码
    status: str                # pending/completed/expired
    reward_given: bool         # 是否已发放奖励
    reward_amount: Optional[int]  # 奖励积分数
    completed_at: Optional[datetime]
    created_at: datetime
```

### 3.2 数据库 Schema

```sql
CREATE TABLE referrals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    referrer_id UUID NOT NULL REFERENCES profiles(id),
    referee_id UUID NOT NULL REFERENCES profiles(id),
    referral_code VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    reward_given BOOLEAN DEFAULT false,
    reward_amount INTEGER DEFAULT 50,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_referral UNIQUE (referrer_id, referee_id)
);

-- 索引
CREATE INDEX idx_referrals_referrer ON referrals(referrer_id);
CREATE INDEX idx_referrals_referee ON referrals(referee_id);
CREATE INDEX idx_referrals_code ON referrals(referral_code);
CREATE INDEX idx_referrals_status ON referrals(status);
```

---

## 四、核心流程

### 4.1 推荐完整流程

```
┌─────────────────────────────────────────────────────────────────┐
│                      推荐完整流程                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 推荐人分享推荐码                                            │
│     │                                                           │
│     ↓                                                           │
│  2. 被推荐人使用推荐码注册                                      │
│     │                                                           │
│     ↓                                                           │
│  3. 系统创建推荐记录 (status=pending)                           │
│     │                                                           │
│     ↓                                                           │
│  4. 被推荐人完成条件 (如: 首次消费)                             │
│     │                                                           │
│     ↓                                                           │
│  5. 系统调用 complete_referral                                  │
│     │  - 检查幂等性 (reward_given)                              │
│     │  - 更新状态为 completed                                   │
│     │  - 发放积分到推荐人账户                                   │
│     ↓                                                           │
│  6. 完成                                                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 完成推荐 (带幂等性)

```python
async def complete_referral(self, referral_id: str) -> Optional[ReferralEntity]:
    """
    完成推荐
    
    WS-01 fix: 原子更新状态 + 发放奖励
    幂等性: 检查 reward_given 防止重复发放
    """
    # 1. 获取推荐记录，检查幂等性
    referral = await self.repository.get_by_id(referral_id)
    if not referral:
        return None
    
    if referral.reward_given:
        return referral  # 已完成，直接返回
    
    # 2. 更新状态
    updated = await self.repository.update_status(
        referral_id=referral_id,
        status="completed",
        reward_given=True,
        completed_at=datetime.now(timezone.utc)
    )
    
    # 3. 发放积分 (使用幂等键)
    if updated and self._billing_service:
        await self._billing_service.add_credits(
            user_id=referral.referrer_id,
            amount=referral.reward_amount or 50,
            bucket=CreditBucket.PERMANENT,
            tx_type=TransactionType.REFERRAL_BONUS,
            idempotency_key=f"referral_reward_{referral_id}",
        )
    
    return updated
```

---

## 五、奖励规则

### 5.1 默认奖励

| 角色 | 奖励 |
|------|------|
| 推荐人 | 50 永久积分 |
| 被推荐人 | 注册赠送积分 (100) |

### 5.2 完成条件

被推荐人需满足以下条件之一：
- 完成邮箱验证
- 首次订阅付费
- 首次消费积分

### 5.3 防作弊规则

- 同一 IP 注册限制
- 同一设备指纹限制
- 推荐人不能推荐自己
- 被推荐人只能被推荐一次

---

## 六、API 端点

### 6.1 端点列表

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/referrals/code` | 获取我的推荐码 |
| GET | `/api/v1/referrals` | 获取我的推荐列表 |
| GET | `/api/v1/referrals/stats` | 获取推荐统计 |
| POST | `/api/v1/referrals/apply` | 应用推荐码 |

### 6.2 响应示例

**获取推荐码**:
```json
{
    "code": "ABCD-1234",
    "share_url": "https://makedecodables.com/r/ABCD-1234"
}
```

**获取统计**:
```json
{
    "total": 10,
    "completed": 8,
    "pending": 2,
    "total_rewards": 400
}
```

**获取推荐列表**:
```json
{
    "items": [
        {
            "id": "uuid",
            "referee_email": "u***@example.com",  // 脱敏
            "status": "completed",
            "reward_amount": 50,
            "completed_at": "2026-01-15T10:00:00Z"
        }
    ],
    "total": 8
}
```

---

## 七、前端交互

### 7.1 推荐入口

- **位置**: 个人中心 > 推荐好友
- **功能**: 显示推荐码、一键复制、分享链接

### 7.2 推荐列表

```
列表字段:
- 被推荐人 (邮箱脱敏)
- 状态 (待完成/已完成)
- 奖励金额
- 完成时间
```

### 7.3 统计卡片

```
展示内容:
┌───────────────────────────────────────┐
│  推荐人数: 10                          │
│  已完成: 8                             │
│  累计奖励: 400 积分                    │
└───────────────────────────────────────┘
```

---

## 八、相关文档

- [权益策略规则](../../05-business/entitlement/policy-rules.md)
- [Billing 架构](../billing/architecture.md)
- [权益促销规则](../../05-business/entitlement/promotions.md)
