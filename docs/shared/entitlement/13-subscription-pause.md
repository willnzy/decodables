# 订阅暂停

> **版本**: v2.0
> **日期**: 2026-02-04
> **状态**: 产品确认
> **参考**: Spotify / Netflix 暂停模式

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [README.md](./README.md) | 文档导航索引 |
| [12-tier-downgrade.md](./12-tier-downgrade.md) | Tier 降级处理 |
| [15-credits-lifecycle.md](./15-credits-lifecycle.md) | 积分生命周期 |

---

## 一、功能概述

### 1.1 定义

**订阅暂停** (Subscription Pause) 允许用户临时停止订阅计费，同时保留账户和数据，稍后可恢复订阅。

### 1.2 适用场景

| 场景 | 说明 |
|------|------|
| 临时不使用 | 用户短期内不会使用产品 |
| 资金紧张 | 用户暂时无法负担订阅费用 |
| 试用期后观望 | 用户想暂停观察是否需要 |

---

## 二、暂停规则

### 2.1 暂停限制

| 限制项 | 规则 |
|--------|------|
| 最短暂停时间 | 1 个月 |
| 最长暂停时间 | 3 个月 |
| 年度暂停次数 | 最多 2 次 |
| 暂停间隔 | 恢复后至少 1 个月才能再次暂停 |

### 2.2 暂停期间权限

| 功能 | 状态 | 说明 |
|------|------|------|
| 数据访问 | ✅ 保留 | 所有数据完整保留 |
| 项目编辑 | ❌ 只读 | 可查看，不可编辑 |
| 新建资源 | ❌ 禁止 | 不可新建项目/素材 |
| AI 功能 | ❌ 禁止 | 暂停期间不可使用 |
| 导出功能 | ⚠️ 受限 | 仅支持基础导出 |
| 积分使用 | ❌ 冻结 | 月度积分暂停发放 |

---

## 三、操作流程

### 3.1 暂停订阅

```
用户操作:
1. 进入账户设置 → 订阅管理
2. 点击 "暂停订阅"
3. 选择暂停时长 (1/2/3 个月)
4. 确认暂停
5. 收到确认邮件

系统处理:
1. 记录暂停开始时间和预计结束时间
2. 更新订阅状态为 paused
3. 取消下次扣款
4. 冻结月度积分
5. 设置权限为暂停状态
6. 发送确认邮件
```

### 3.2 暂停期间

```
显示状态:
- Dashboard Banner: "订阅已暂停，将于 [日期] 自动恢复"
- 受限功能显示锁定图标
- 倒计时显示剩余暂停天数

定期提醒:
- 暂停期结束前 7 天: 邮件提醒
- 暂停期结束前 1 天: 邮件提醒
```

### 3.3 恢复订阅

**自动恢复** (默认):
```
暂停期结束 → 自动恢复订阅 → 恢复扣款
```

**提前恢复** (用户主动):
```
用户操作:
1. 进入订阅管理
2. 点击 "立即恢复订阅"
3. 确认恢复
4. 立即恢复所有权限

计费规则:
- 按剩余天数比例计算本周期费用
- 或从下一周期开始计费 (用户选择)
```

---

## 四、计费处理

### 4.1 暂停期计费

```
暂停前: 正常扣款周期
暂停期: 不扣款
恢复后: 从下一完整周期开始扣款

示例:
- 1月15日 暂停 (原计费日 15日)
- 暂停 2 个月
- 3月15日 自动恢复
- 3月15日 开始新的计费周期
```

### 4.2 积分处理

| 积分类型 | 暂停期处理 |
|----------|------------|
| 月度积分 | 暂停发放，不累积 |
| 永久积分 | 保留，但不可使用 |
| 充值积分 | 保留，但不可使用 |

恢复后:
- 月度积分按新周期重新发放
- 永久/充值积分解冻可用

---

## 五、数据结构

### 5.1 订阅状态扩展

```sql
-- profiles 表扩展
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS
    subscription_status VARCHAR(20) DEFAULT 'active';
-- 可选值: active, paused, cancelled, past_due

ALTER TABLE profiles ADD COLUMN IF NOT EXISTS
    pause_started_at TIMESTAMPTZ;

ALTER TABLE profiles ADD COLUMN IF NOT EXISTS
    pause_ends_at TIMESTAMPTZ;

ALTER TABLE profiles ADD COLUMN IF NOT EXISTS
    pause_count_this_year INT DEFAULT 0;
```

### 5.2 暂停历史记录

```sql
CREATE TABLE IF NOT EXISTS subscription_pause_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES profiles(user_id),
    pause_started_at TIMESTAMPTZ NOT NULL,
    pause_ended_at TIMESTAMPTZ,
    pause_duration_months INT NOT NULL,
    resume_type VARCHAR(20), -- auto, manual
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 六、通知策略

### 6.1 暂停相关通知

| 触发点 | 通知类型 | 内容 |
|--------|----------|------|
| 暂停成功 | 邮件 | 确认暂停，说明恢复日期 |
| 暂停期 50% | 邮件 | 提醒暂停进度 |
| 恢复前 7 天 | 邮件 | 提醒即将恢复 |
| 恢复前 1 天 | 邮件 | 最后提醒 |
| 恢复成功 | 邮件 | 确认恢复，说明计费 |

---

## 七、API 接口

```python
# 暂停订阅
POST /api/v1/subscriptions/pause
{
    "duration_months": 2
}

# 恢复订阅
POST /api/v1/subscriptions/resume
{
    "billing_option": "immediate" | "next_cycle"
}

# 查询暂停状态
GET /api/v1/subscriptions/pause-status
Response: {
    "is_paused": true,
    "pause_started_at": "2026-02-01T00:00:00Z",
    "pause_ends_at": "2026-04-01T00:00:00Z",
    "remaining_days": 56,
    "pause_count_this_year": 1
}
```

---

## 八、完整服务实现

### 8.1 SubscriptionPauseService

```python
# domains/subscription/services/pause_service.py

from datetime import datetime, timedelta
from typing import Dict, Optional

class SubscriptionPauseService:
    """订阅暂停服务"""

    async def pause_subscription(
        self,
        user_id: str,
        duration_months: int,
        reason: str = None
    ) -> Dict:
        """暂停订阅"""

        # 1. 检查是否允许暂停
        validation = await self._validate_pause_eligibility(user_id, duration_months)
        if not validation['eligible']:
            raise PauseNotAllowedError(validation['reason'])

        # 2. 获取当前订阅
        subscription = await self._get_active_subscription(user_id)

        # 3. 计算暂停时间
        pause_start = self._calculate_pause_start(subscription)
        pause_end = pause_start + timedelta(days=duration_months * 30)

        # 4. 通知 Stripe 暂停 (使用 subscription_schedule)
        await self._pause_stripe_subscription(subscription.stripe_subscription_id, pause_end)

        # 5. 更新数据库
        await db.execute("""
            UPDATE subscriptions SET
                status = 'paused',
                pause_start_at = $1,
                pause_end_at = $2,
                pause_reason = $3,
                pause_count_this_year = pause_count_this_year + 1
            WHERE user_id = $4
        """, pause_start, pause_end, reason, user_id)

        # 6. 记录暂停历史
        await db.execute("""
            INSERT INTO subscription_pause_history
            (user_id, subscription_id, pause_start_at, planned_end_at, reason)
            VALUES ($1, $2, $3, $4, $5)
        """, user_id, subscription.id, pause_start, pause_end, reason)

        # 7. 触发降级处理 (临时降为 t1)
        await self.downgrade_service.process_downgrade(
            user_id,
            old_tier=subscription.tier,
            new_tier='t1',
            reason='subscription_paused'
        )

        # 8. 发送确认邮件
        await self._send_pause_confirmation_email(user_id, pause_start, pause_end)

        return {
            'status': 'paused',
            'pause_start': pause_start,
            'pause_end': pause_end,
            'auto_resume': True
        }

    async def resume_subscription(self, user_id: str) -> Dict:
        """提前恢复订阅"""

        subscription = await self._get_paused_subscription(user_id)
        if not subscription:
            raise SubscriptionNotPausedError()

        # 1. 恢复 Stripe 订阅
        await self._resume_stripe_subscription(subscription.stripe_subscription_id)

        # 2. 更新数据库
        await db.execute("""
            UPDATE subscriptions SET
                status = 'active',
                pause_start_at = NULL,
                pause_end_at = NULL
            WHERE user_id = $1
        """, user_id)

        # 3. 标记历史记录
        await db.execute("""
            UPDATE subscription_pause_history SET
                pause_end_at = NOW(),
                resumed_early = TRUE
            WHERE user_id = $1 AND pause_end_at IS NULL
        """, user_id)

        # 4. 恢复 Tier 权限
        await self.upgrade_service.process_upgrade(user_id, subscription.tier)

        # 5. 发送恢复确认邮件
        await self._send_resume_confirmation_email(user_id)

        return {'status': 'active', 'tier': subscription.tier}

    async def _validate_pause_eligibility(self, user_id: str, duration_months: int) -> Dict:
        """验证是否有资格暂停"""

        subscription = await self._get_active_subscription(user_id)

        # 检查是否年付
        if subscription.billing_interval == 'year':
            allow_annual = await get_config('pause.allow_annual')
            if not allow_annual:
                return {'eligible': False, 'reason': '年付订阅不支持暂停，如需取消请联系客服'}

        # 检查暂停次数
        max_per_year = await get_config('pause.max_per_year') or 2
        if subscription.pause_count_this_year >= max_per_year:
            return {'eligible': False, 'reason': f'今年已暂停 {max_per_year} 次，无法再次暂停'}

        # 检查暂停间隔
        last_pause = await db.fetch_one("""
            SELECT pause_end_at FROM subscription_pause_history
            WHERE user_id = $1 ORDER BY pause_end_at DESC LIMIT 1
        """, user_id)

        if last_pause:
            min_interval = await get_config('pause.min_interval_months') or 3
            min_resume_date = last_pause['pause_end_at'] + timedelta(days=min_interval * 30)
            if datetime.now() < min_resume_date:
                return {'eligible': False, 'reason': f'距离上次暂停未满 {min_interval} 个月'}

        # 检查时长
        min_duration = await get_config('pause.min_duration_months') or 1
        max_duration = await get_config('pause.max_duration_months') or 3

        if duration_months < min_duration or duration_months > max_duration:
            return {'eligible': False, 'reason': f'暂停时长需在 {min_duration}-{max_duration} 个月之间'}

        return {'eligible': True, 'reason': None}
```

---

## 九、配置项

```sql
INSERT INTO system_configs (key, value, value_type, config_group, description) VALUES
('pause.min_duration_months', '1', 'integer', 'subscription', '最短暂停月数'),
('pause.max_duration_months', '3', 'integer', 'subscription', '最长暂停月数'),
('pause.max_per_year', '2', 'integer', 'subscription', '每年最大暂停次数'),
('pause.min_interval_months', '3', 'integer', 'subscription', '两次暂停最小间隔'),
('pause.allow_annual', 'false', 'boolean', 'subscription', '年付是否允许暂停');
```

---

## 十、UI 组件

### 10.1 PauseSubscriptionModal

```typescript
// 设置页 - 订阅管理
// /settings/subscription

interface PauseSubscriptionModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentTier: string;
  onPause: (months: number, reason?: string) => Promise<void>;
}

function PauseSubscriptionModal({ isOpen, onClose, currentTier, onPause }: PauseSubscriptionModalProps) {
  const [months, setMonths] = useState(1);
  const [reason, setReason] = useState('');

  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <ModalHeader>暂停订阅</ModalHeader>
      <ModalBody>
        <Alert variant="warning">
          暂停期间，您的账户将降为免费版，部分功能将受限。
          暂停结束后将自动恢复订阅并扣费。
        </Alert>

        <div className="mt-4">
          <Label>暂停时长</Label>
          <Select value={months} onChange={(v) => setMonths(Number(v))}>
            <Option value={1}>1 个月</Option>
            <Option value={2}>2 个月</Option>
            <Option value={3}>3 个月</Option>
          </Select>
        </div>

        <div className="mt-4">
          <Label>暂停原因 (可选)</Label>
          <Textarea
            placeholder="告诉我们为什么暂停，帮助我们改进产品"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </div>
      </ModalBody>
      <ModalFooter>
        <Button variant="ghost" onClick={onClose}>取消</Button>
        <Button variant="warning" onClick={() => onPause(months, reason)}>
          确认暂停
        </Button>
      </ModalFooter>
    </Modal>
  );
}
```

### 10.2 PausedStatusBanner

```typescript
// 暂停状态 Banner
function PausedStatusBanner({ pauseEndsAt }: { pauseEndsAt: Date }) {
  const daysRemaining = Math.ceil((pauseEndsAt.getTime() - Date.now()) / (1000 * 60 * 60 * 24));

  return (
    <Banner variant="info">
      <span>
        您的订阅已暂停，将于 {formatDate(pauseEndsAt)} 自动恢复
        （还剩 {daysRemaining} 天）
      </span>
      <Button size="sm" onClick={() => openResumeModal()}>
        立即恢复
      </Button>
    </Banner>
  );
}
```

---

## 十一、扩展数据库设计

### 11.1 subscriptions 表新增字段

```sql
-- subscriptions 表新增字段
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS
    pause_start_at TIMESTAMPTZ,          -- 暂停开始时间
    pause_end_at TIMESTAMPTZ,            -- 暂停结束时间 (预设)
    pause_reason TEXT,                   -- 暂停原因 (用户反馈)
    pause_count_this_year INT DEFAULT 0; -- 今年已暂停次数
```

### 11.2 暂停历史记录表 (完整版)

```sql
-- 暂停历史记录表
CREATE TABLE IF NOT EXISTS subscription_pause_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
    subscription_id TEXT NOT NULL,
    pause_start_at TIMESTAMPTZ NOT NULL,
    pause_end_at TIMESTAMPTZ,            -- 实际结束时间
    planned_end_at TIMESTAMPTZ NOT NULL, -- 计划结束时间
    reason TEXT,
    resumed_early BOOLEAN DEFAULT FALSE, -- 是否提前恢复
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_pause_history_user ON subscription_pause_history(user_id);
```

---

**END OF DOCUMENT**
