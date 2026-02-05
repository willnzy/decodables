# 订阅续期提醒

> **版本**: v1.1
> **日期**: 2026-02-04
> **优先级**: P0 (核心功能)
> **参考**: 所有 SaaS 产品

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [README.md](./README.md) | 文档导航索引 |
| [02-tier-config.md](./02-tier-config.md) | Tier 配置 |
| [14-billing-cycle-switch.md](./14-billing-cycle-switch.md) | 计费周期切换 |
| [26-audit-checklist.md](./26-audit-checklist.md) | 审计检查清单 S12 场景 |

---

## 概述

订阅续期提醒系统确保用户在订阅自动续期前收到充分的通知，避免意外扣费并保持良好的用户体验。

---

## 1. 提醒规则

### 1.1 年付订阅提醒

| 时间点 | 渠道 | 内容 | 配置 key |
|--------|------|------|----------|
| 续期前 **30 天** | 邮件 | 年度续期提前通知 | `renewal.yearly_30day` |
| 续期前 **7 天** | 邮件 + 应用内 | 温和提醒，显示续期日期和金额 | `renewal.yearly_7day` |
| 续期前 **1 天** | 邮件 + 应用内 + Push | 最后提醒 | `renewal.yearly_1day` |
| 续期当天 | 应用内 | 显示扣费成功/失败状态 | - |

### 1.2 月付订阅提醒

| 时间点 | 渠道 | 内容 | 配置 key |
|--------|------|------|----------|
| 续期前 **7 天** | 邮件 | 温和提醒，显示续期日期和金额 | `renewal.monthly_7day` |
| 续期前 **3 天** | 邮件 + 应用内 | 提醒检查支付方式 | `renewal.monthly_3day` |
| 续期前 **1 天** | 邮件 + 应用内 + Push | 最后提醒 | `renewal.monthly_1day` |
| 续期当天 | 应用内 | 显示扣费成功/失败状态 | - |

> **注意**: 年付订阅因金额较大，增加 30 天提前通知，符合 [26-audit-checklist.md](./26-audit-checklist.md) S12 场景要求。

---

## 2. 配置项

```sql
INSERT INTO system_configs (key, value, value_type, config_group, description) VALUES
-- 年付提醒配置
('renewal.yearly_reminder_days', '[30, 7, 1]', 'json', 'subscription', '年付续期提醒天数数组'),
-- 月付提醒配置
('renewal.monthly_reminder_days', '[7, 3, 1]', 'json', 'subscription', '月付续期提醒天数数组'),
-- 通用配置
('renewal.email_enabled', 'true', 'boolean', 'subscription', '是否发送邮件提醒'),
('renewal.push_enabled', 'true', 'boolean', 'subscription', '是否发送推送提醒'),
('renewal.allow_user_disable', 'true', 'boolean', 'subscription', '用户是否可关闭提醒');
```

---

## 3. 数据库设计

### 3.1 用户通知偏好表

```sql
-- 用户通知偏好
CREATE TABLE IF NOT EXISTS user_notification_preferences (
    user_id UUID PRIMARY KEY REFERENCES profiles(id),
    renewal_email BOOLEAN DEFAULT TRUE,
    renewal_push BOOLEAN DEFAULT TRUE,
    marketing_email BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.2 通知发送记录表

```sql
-- 通知发送记录
CREATE TABLE IF NOT EXISTS notification_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id),
    notification_type TEXT NOT NULL,      -- 'renewal_reminder' | 'payment_failed' | 'trial_ending'
    channel TEXT NOT NULL,                -- 'email' | 'push' | 'in_app'
    template_id TEXT,
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    opened_at TIMESTAMPTZ,
    clicked_at TIMESTAMPTZ,
    metadata JSONB                        -- 额外数据
);

CREATE INDEX idx_notification_logs_user ON notification_logs(user_id);
CREATE INDEX idx_notification_logs_type ON notification_logs(notification_type);
```

---

## 4. 服务实现

```python
# domains/notification/services/renewal_reminder_service.py

class RenewalReminderService:
    """续期提醒服务"""

    async def send_renewal_reminders(self):
        """定时任务: 发送续期提醒"""

        # 根据订阅类型获取不同提醒配置
        # 年付: [30, 7, 1]  月付: [7, 3, 1]
        yearly_reminder_days = await get_config('renewal.yearly_reminder_days') or [30, 7, 1]
        monthly_reminder_days = await get_config('renewal.monthly_reminder_days') or [7, 3, 1]

        # 合并所有需要检查的天数
        all_reminder_days = list(set(yearly_reminder_days + monthly_reminder_days))

        for days in all_reminder_days:
            target_date = datetime.now() + timedelta(days=days)

            # 查找即将续期的订阅
            subscriptions = await db.fetch_all("""
                SELECT s.*, u.email, u.name, np.renewal_email, np.renewal_push
                FROM subscriptions s
                JOIN profiles u ON s.user_id = u.user_id
                LEFT JOIN user_notification_preferences np ON s.user_id = np.user_id
                WHERE DATE(s.current_period_end) = DATE($1)
                AND s.status = 'active'
                AND s.cancel_at_period_end = FALSE
            """, target_date)

            for sub in subscriptions:
                # 检查是否已发送过
                already_sent = await self._check_already_sent(sub['user_id'], days)
                if already_sent:
                    continue

                # 发送邮件
                if sub.get('renewal_email', True):
                    await self._send_email_reminder(sub, days)

                # 发送推送 (仅最后一天)
                if days == 1 and sub.get('renewal_push', True):
                    await self._send_push_reminder(sub)

                # 创建应用内通知 (3 天和 1 天)
                if days <= 3:
                    await self._create_in_app_notification(sub, days)

    async def _send_email_reminder(self, subscription: Dict, days_until: int):
        """发送邮件提醒"""

        # 年付 30/7/1 天模板，月付 7/3/1 天模板
        template = {
            30: 'renewal_reminder_30days',  # 年付专用
            7: 'renewal_reminder_7days',
            3: 'renewal_reminder_3days',
            1: 'renewal_reminder_1day'
        }.get(days_until)

        await email_service.send(
            to=subscription['email'],
            template=template,
            data={
                'user_name': subscription['name'],
                'tier_name': TIER_DISPLAY_NAMES[subscription['tier']],
                'renewal_date': subscription['current_period_end'].strftime('%Y年%m月%d日'),
                'amount': subscription['price'],
                'payment_method_last4': subscription.get('card_last4', '****'),
                'manage_url': f"{BASE_URL}/settings/subscription"
            }
        )

        # 记录
        await self._log_notification(
            subscription['user_id'],
            'renewal_reminder',
            'email',
            template
        )
```

---

## 5. 邮件模板示例

### 续期前 3 天邮件模板

```html
<!-- 续期前 3 天邮件模板 -->
<h2>您的订阅即将续期</h2>

<p>亲爱的 {{user_name}}，</p>

<p>您的 <strong>{{tier_name}}</strong> 订阅将于 <strong>{{renewal_date}}</strong> 自动续期。</p>

<div class="info-box">
  <p>续期金额: <strong>${{amount}}</strong></p>
  <p>支付方式: 尾号 {{payment_method_last4}} 的信用卡</p>
</div>

<p>请确保您的支付方式有效，以避免服务中断。</p>

<div class="cta">
  <a href="{{manage_url}}">管理订阅</a>
</div>

<p class="footer">
  如果您不希望续期，可以在续期日期前<a href="{{manage_url}}">取消订阅</a>。
</p>
```

---

## 相关文档

- [权益矩阵总览](./01-permission-matrix.md)
- [Tier 配置](./02-tier-config.md)
- [系统设计](./03-system-design.md)
- [返回目录](./README.md)

---

**文档版本**: v1.1
**创建日期**: 2026-02-04
**来源**: 权益矩阵文档 第九章 9.4 节
**更新**: v1.1 - 补充年付 30 天提醒，符合 S12 场景要求
