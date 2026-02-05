# 推荐奖励规则

> Referral Rewards - 推荐系统奖励机制

**验证状态**: 🟢 已验证  
**同步范围**: [fullstack]

---

## 一、概述

推荐奖励系统激励用户邀请新用户，双方均可获得积分奖励。

---

## 二、奖励规则

### 2.1 基础奖励

| 角色 | 奖励类型 | 数量 | 条件 |
|------|----------|------|------|
| 推荐人 | 永久积分 | 50 | 被推荐人完成条件 |
| 被推荐人 | 永久积分 | 100 | 注册赠送 (无需推荐码) |

### 2.2 完成条件

被推荐人需满足以下条件之一：

1. **邮箱验证** - 完成邮箱验证
2. **首次订阅** - 购买任意付费订阅
3. **首次消费** - 使用积分消费 (如 AI 生成)

```python
REFERRAL_COMPLETION_CONDITIONS = {
    'email_verified': True,   # 基础条件
    'first_subscription': True,  # 可选更高奖励
    'first_credit_usage': True,  # 可选更高奖励
}
```

### 2.3 阶梯奖励 (可选)

```python
# 未来扩展: 根据被推荐人行为给予额外奖励
BONUS_REWARDS = {
    'referee_subscribes_t2': 25,  # 被推荐人订阅 Starter
    'referee_subscribes_t3': 50,  # 被推荐人订阅 Pro
}
```

---

## 三、奖励发放

### 3.1 发放流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    奖励发放流程                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 被推荐人满足条件                                            │
│     │                                                           │
│     ↓                                                           │
│  2. 系统触发 complete_referral                                  │
│     │                                                           │
│     ↓                                                           │
│  3. 检查幂等性 (reward_given)                                   │
│     │                                                           │
│     ├── 已发放 → 直接返回                                       │
│     │                                                           │
│     └── 未发放 ↓                                                │
│                                                                 │
│  4. 更新推荐记录状态                                            │
│     │  - status = completed                                     │
│     │  - reward_given = true                                    │
│     │  - completed_at = now                                     │
│     ↓                                                           │
│  5. 发放积分到推荐人账户                                        │
│     │  - bucket = PERMANENT                                     │
│     │  - tx_type = REFERRAL_BONUS                               │
│     │  - idempotency_key = referral_reward_{id}                 │
│     ↓                                                           │
│  6. 发送奖励通知                                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 代码实现

```python
async def complete_referral(self, referral_id: str) -> Optional[ReferralEntity]:
    """
    完成推荐并发放奖励
    
    幂等性保证:
    1. 检查 reward_given 标记
    2. 使用 idempotency_key 防止重复发放
    """
    # 1. 获取推荐记录
    referral = await self.repository.get_by_id(referral_id)
    if not referral:
        return None
    
    # 2. 幂等性检查
    if referral.reward_given:
        logger.info(f"Referral {referral_id} already completed")
        return referral
    
    # 3. 更新状态
    updated = await self.repository.update_status(
        referral_id=referral_id,
        status="completed",
        reward_given=True,
        completed_at=datetime.now(timezone.utc)
    )
    
    # 4. 发放积分 (带幂等键)
    if updated and self._billing_service:
        reward_amount = referral.reward_amount or 50
        await self._billing_service.add_credits(
            user_id=referral.referrer_id,
            amount=reward_amount,
            bucket=CreditBucket.PERMANENT,
            tx_type=TransactionType.REFERRAL_BONUS,
            description=f"Referral reward for {referral_id}",
            idempotency_key=f"referral_reward_{referral_id}",
        )
    
    # 5. 发送通知
    await self._send_reward_notification(referral.referrer_id, reward_amount)
    
    return updated
```

---

## 四、防作弊规则

### 4.1 检测规则

| 规则 | 描述 | 处理 |
|------|------|------|
| 自我推荐 | referrer_id = referee_id | 拒绝 |
| 重复推荐 | 同一被推荐人多次 | 拒绝 |
| IP 聚集 | 多个账号相同 IP | 人工审核 |
| 设备指纹 | 同一设备多账号 | 人工审核 |
| 快速注册 | 短时间大量推荐 | 暂停发放 |

### 4.2 验证代码

```python
async def validate_referral(
    referrer_id: str,
    referee_id: str,
    ip_address: str,
    device_fingerprint: Optional[str]
) -> ValidationResult:
    """验证推荐有效性"""
    
    # 1. 自我推荐检查
    if referrer_id == referee_id:
        return ValidationResult(valid=False, reason="SELF_REFERRAL")
    
    # 2. 重复推荐检查
    existing = await get_referral(referrer_id, referee_id)
    if existing:
        return ValidationResult(valid=False, reason="DUPLICATE_REFERRAL")
    
    # 3. IP 聚集检查
    ip_referrals = await count_referrals_by_ip(ip_address, days=7)
    if ip_referrals > 5:
        return ValidationResult(valid=False, reason="IP_ABUSE", needs_review=True)
    
    # 4. 设备指纹检查
    if device_fingerprint:
        fp_referrals = await count_referrals_by_fingerprint(device_fingerprint, days=7)
        if fp_referrals > 3:
            return ValidationResult(valid=False, reason="DEVICE_ABUSE", needs_review=True)
    
    # 5. 推荐人速率检查
    recent_referrals = await count_user_referrals(referrer_id, hours=24)
    if recent_referrals > 10:
        return ValidationResult(valid=False, reason="RATE_LIMIT")
    
    return ValidationResult(valid=True)
```

### 4.3 奖励冻结

```python
async def freeze_referral_rewards(user_id: str, reason: str):
    """
    冻结用户推荐奖励
    
    触发条件:
    - 检测到作弊行为
    - 收到举报
    - 人工审核标记
    """
    # 1. 标记用户
    await set_user_flag(user_id, 'referral_frozen', True)
    
    # 2. 暂停待发放奖励
    await pause_pending_referrals(user_id)
    
    # 3. 记录审计
    await log_security_event(
        user_id=user_id,
        event_type='REFERRAL_FROZEN',
        reason=reason
    )
    
    # 4. 发送通知
    await send_account_notification(
        user_id=user_id,
        notification_type='REFERRAL_FROZEN',
        message='您的推荐奖励已被暂停，如有疑问请联系客服'
    )
```

---

## 五、奖励上限

### 5.1 配置参数

```python
REFERRAL_LIMITS = {
    'max_rewards_per_month': 500,     # 每月最多获得 500 积分
    'max_referrals_per_day': 10,      # 每天最多 10 个有效推荐
    'max_total_referrals': 1000,      # 总推荐数上限
}
```

### 5.2 上限检查

```python
async def check_referral_limits(user_id: str) -> LimitResult:
    """检查推荐上限"""
    
    # 月度奖励检查
    monthly_rewards = await get_monthly_referral_rewards(user_id)
    if monthly_rewards >= REFERRAL_LIMITS['max_rewards_per_month']:
        return LimitResult(
            allowed=False,
            reason='MONTHLY_LIMIT',
            current=monthly_rewards,
            limit=REFERRAL_LIMITS['max_rewards_per_month']
        )
    
    # 日推荐数检查
    daily_referrals = await get_daily_referral_count(user_id)
    if daily_referrals >= REFERRAL_LIMITS['max_referrals_per_day']:
        return LimitResult(
            allowed=False,
            reason='DAILY_LIMIT'
        )
    
    return LimitResult(allowed=True)
```

---

## 六、统计与报表

### 6.1 用户统计

```python
async def get_referral_stats(user_id: str) -> dict:
    """获取用户推荐统计"""
    return {
        "total": 10,           # 总推荐数
        "completed": 8,        # 已完成
        "pending": 2,          # 待完成
        "total_rewards": 400,  # 累计奖励积分
    }
```

### 6.2 系统报表

```python
async def get_referral_report(start_date: date, end_date: date) -> dict:
    """系统推荐报表"""
    return {
        "total_referrals": 1500,
        "completed_referrals": 1200,
        "total_rewards_given": 60000,
        "conversion_rate": 0.80,
        "top_referrers": [...]
    }
```

---

## 七、相关文档

- [推荐系统](../../04-engineering/modules/user-capabilities/referrals-system.md)
- [权益策略规则](./policy-rules.md)
- [积分系统](../../03-business/credits-system.md)
