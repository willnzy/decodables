# 续订提醒

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [fullstack]
> **来源**: v1 shared/entitlement/

---

## 概述

订阅续订提醒的策略和实现。

---

## 提醒时间点

| 时间 | 类型 | 渠道 |
|------|------|------|
| 到期前 7 天 | 首次提醒 | 邮件 + 应用内 |
| 到期前 3 天 | 二次提醒 | 邮件 + 应用内 |
| 到期前 1 天 | 最后提醒 | 邮件 + 应用内 |
| 到期当天 | 到期通知 | 邮件 + 应用内 |

---

## 提醒内容

### 邮件模板

```
主题: 您的 Make Decodables Pro 订阅将于 {days} 天后到期

Hi {name},

您的 Pro 订阅将于 {expire_date} 到期。

续订后您将继续享有:
- 无限项目
- 每月 200 积分
- 高级模板
- ...

[立即续订]

如有问题请联系我们。

Make Decodables 团队
```

---

## 应用内提醒

- 顶部 Banner (可关闭)
- 设置页提示
- 个人中心到期倒计时

---

## 实现

```python
async def check_expiring_subscriptions():
    """定时任务: 检查即将到期的订阅"""
    for days in [7, 3, 1, 0]:
        users = await get_users_expiring_in(days)
        for user in users:
            await send_renewal_reminder(user, days)
```

---

## 相关文档

- [试用过期处理](./trial-expiration.md)
- [通知系统](../../04-engineering/modules/notifications/)
