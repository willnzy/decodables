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

**END OF DOCUMENT**
