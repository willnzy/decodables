# 试用期与到期规则

> Trial & Expiration - 试用期管理与订阅到期处理

> **同步范围**: [fullstack]
> **状态**: 🟡 待验证
> **最后更新**: 2026-02-05
> **数据来源**: `v1/shared/entitlement/`, `domains/subscriptions/`

---

## 一、概述

管理用户试用期和订阅到期后的权益变化与降级流程。

---

## 二、试用期规则

### 2.1 免费试用

| 配置 | 值 | 说明 |
|------|-----|------|
| 试用时长 | 30 天 | 注册后自动开始 |
| 试用功能 | Pro 功能子集 | 部分高级功能 |
| 试用积分 | 100 永久积分 | 注册赠送 |

### 2.2 试用功能范围

```python
TRIAL_FEATURES = {
    # 可用功能
    'export_pdf': True,
    'custom_fonts': True,
    'ai_generation': True,  # 使用赠送积分
    
    # 不可用功能
    'priority_support': False,
    'watermark_removal': False,
    'team_collaboration': False,
}
```

### 2.3 试用期判断

```python
class TrialService:
    TRIAL_DURATION_DAYS = 7
    
    def is_in_trial(self, user: User) -> bool:
        """检查用户是否在试用期"""
        if user.tier != 't1':
            return False  # 付费用户无试用期概念
        
        days_since_signup = (datetime.utcnow() - user.created_at).days
        return days_since_signup <= self.TRIAL_DURATION_DAYS
    
    def get_trial_days_remaining(self, user: User) -> int:
        """获取剩余试用天数"""
        if not self.is_in_trial(user):
            return 0
        
        days_since_signup = (datetime.utcnow() - user.created_at).days
        return max(0, self.TRIAL_DURATION_DAYS - days_since_signup)
```

---

## 三、订阅到期处理

### 3.1 到期状态流转

```
┌─────────────────────────────────────────────────────────────────┐
│                    订阅到期状态流转                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  active ─────> past_due ─────> canceled                         │
│     │              │               │                            │
│     │              │               │                            │
│     │         (宽限期 7 天)        │                            │
│     │              │               │                            │
│     │              ▼               │                            │
│     │         [自动续费失败]       │                            │
│     │              │               │                            │
│     │         ┌────┴────┐         │                            │
│     │         │  重试   │         │                            │
│     │         │ (3次)   │         │                            │
│     │         └────┬────┘         │                            │
│     │              │               │                            │
│     │         失败 │  成功         │                            │
│     │              ▼    │          │                            │
│     │         canceled  │          │                            │
│     │              │    │          │                            │
│     │              │    ▼          │                            │
│     │              │  active       │                            │
│     │              │               │                            │
│     └──────────────┴───────────────┘                            │
│                    │                                            │
│                    ▼                                            │
│             [降级到 t1]                                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 宽限期处理

```python
class GracePeriodHandler:
    GRACE_PERIOD_DAYS = 7
    
    async def handle_payment_failed(self, user_id: UUID, subscription_id: str):
        """处理支付失败"""
        # 1. 标记为 past_due
        await self.update_subscription_status(
            subscription_id, 
            status='past_due'
        )
        
        # 2. 发送通知
        await self.send_payment_failed_notification(user_id)
        
        # 3. 设置降级计划
        grace_end = datetime.utcnow() + timedelta(days=self.GRACE_PERIOD_DAYS)
        await self.schedule_downgrade(user_id, grace_end)
    
    async def process_grace_period_end(self, user_id: UUID):
        """宽限期结束处理"""
        subscription = await self.get_subscription(user_id)
        
        if subscription.status == 'past_due':
            # 降级到 t1
            await self.downgrade_user(user_id, target_tier='t1')
            await self.send_downgrade_notification(user_id)
```

### 3.3 降级处理

```python
async def downgrade_user(user_id: UUID, target_tier: str = 't1'):
    """
    用户降级处理
    
    流程:
    1. 更新 Tier
    2. 重置月度积分
    3. 保留永久积分
    4. 标记需要处理的资源
    5. 发送通知
    """
    user = await get_user(user_id)
    old_tier = user.tier
    
    # 1. 更新 Tier
    await update_user_tier(user_id, target_tier)
    
    # 2. 重置月度积分 (下次发放时自动处理)
    # 注意: 不立即清零，等月度重置
    
    # 3. 保留永久积分 (无需处理)
    
    # 4. 处理超限资源
    await handle_tier_resource_limits(user_id, old_tier, target_tier)
    
    # 5. 记录事件
    await log_tier_change(user_id, old_tier, target_tier, reason='subscription_expired')
    
    # 6. 发送通知
    await send_downgrade_notification(user_id, old_tier, target_tier)
```

---

## 四、资源超限处理

### 4.1 存储配额

```python
async def handle_storage_overlimit(user_id: UUID, new_limit_mb: int):
    """
    存储超限处理
    
    策略:
    - 不自动删除文件
    - 阻止新上传
    - 提示用户清理
    """
    current_usage = await get_storage_usage(user_id)
    
    if current_usage > new_limit_mb:
        # 标记为超限状态
        await set_user_flag(user_id, 'storage_overlimit', True)
        
        # 发送清理提醒
        await send_storage_cleanup_reminder(
            user_id,
            current_usage=current_usage,
            limit=new_limit_mb
        )
```

### 4.2 项目数量

```python
async def handle_project_overlimit(user_id: UUID, new_limit: int):
    """
    项目超限处理
    
    策略:
    - 保留所有项目
    - 只读访问超限项目
    - 阻止创建新项目
    """
    projects = await get_user_projects(user_id)
    
    if len(projects) > new_limit:
        # 按最后编辑时间排序，标记超限项目
        sorted_projects = sorted(projects, key=lambda p: p.updated_at, reverse=True)
        overlimit_projects = sorted_projects[new_limit:]
        
        for project in overlimit_projects:
            await set_project_readonly(project.id, True)
```

---

## 五、通知策略

### 5.1 试用期通知

| 时机 | 通知内容 |
|------|----------|
| 注册时 | 欢迎 + 试用说明 |
| 试用第 25 天 | 试用即将结束提醒 |
| 试用第 30 天 | 试用已结束 |

### 5.2 订阅到期通知

| 时机 | 通知内容 |
|------|----------|
| 到期前 7 天 | 续费提醒 |
| 到期前 3 天 | 续费提醒 (紧急) |
| 到期当天 | 订阅到期通知 |
| 支付失败 | 更新支付方式提醒 |
| 宽限期第 3 天 | 即将降级警告 |
| 降级后 | 降级完成通知 |

### 5.3 通知模板

```python
NOTIFICATION_TEMPLATES = {
    'trial_ending': {
        'title': '试用即将结束',
        'body': '您的 {days} 天试用期将于 {date} 结束。升级以继续使用所有功能。',
        'cta': '立即升级',
        'cta_url': '/pricing'
    },
    'subscription_expiring': {
        'title': '订阅即将到期',
        'body': '您的 {tier_name} 订阅将于 {date} 到期。续费以保持您的权益。',
        'cta': '续费',
        'cta_url': '/billing'
    },
    'payment_failed': {
        'title': '支付失败',
        'body': '我们无法处理您的续费付款。请更新支付方式以避免服务中断。',
        'cta': '更新支付方式',
        'cta_url': '/billing/payment-methods'
    },
}
```

---

## 六、API 端点

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/billing/trial-status` | 获取试用状态 |
| GET | `/api/v1/billing/expiration` | 获取到期信息 |
| POST | `/api/v1/billing/reactivate` | 重新激活订阅 |

---

## 七、前端展示

### 7.1 试用期提示

```typescript
// 试用期倒计时组件
function TrialBanner({ daysRemaining }: { daysRemaining: number }) {
  if (daysRemaining <= 0) return null;
  
  return (
    <Banner variant={daysRemaining <= 2 ? 'warning' : 'info'}>
      <span>试用期还剩 {daysRemaining} 天</span>
      <Button href="/pricing">升级</Button>
    </Banner>
  );
}
```

### 7.2 到期状态指示

```typescript
// 订阅状态徽章
function SubscriptionBadge({ status }: { status: string }) {
  const variants = {
    active: { color: 'green', label: '活跃' },
    past_due: { color: 'yellow', label: '待付款' },
    canceled: { color: 'gray', label: '已取消' },
  };
  
  return <Badge {...variants[status]} />;
}
```

---

## 八、相关文档

- [Billing 架构](../../04-engineering/modules/billing/architecture.md)
- [权益策略规则](./policy-rules.md)
- [Tier 权限矩阵](./permission-matrix.md)
