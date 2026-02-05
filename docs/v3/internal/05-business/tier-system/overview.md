# Tier 系统概述

> **同步范围**: [fullstack]
> **状态**: 🟢 已验证
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `domains/identity/constants.py`, `CLAUDE.md`

---

## 一、设计原则

### 1.1 系统代码与显示名称分离

| 概念 | 说明 | 示例 |
|------|------|------|
| **系统代码 (tier)** | 数据库字段、代码逻辑，永不改变 | `t1`, `t2`, `t3`, `t4` |
| **简称 (label)** | 固定描述，便于理解层级 | First Tier, Second Tier |
| **显示名称 (display)** | 用户看到的，可通过配置修改 | Free Plan, Starter Plan |

### 1.2 核心约束

```python
# 数据库约束
tier TEXT NOT NULL DEFAULT 't1' CHECK (tier IN ('t1', 't2', 't3', 't4'))
```

---

## 二、Tier 定义

### 2.1 完整 Tier 列表

| 系统代码 | 简称 | 显示名称 | 月费 (原价/现价) | 月度积分 | 主题色 |
|----------|------|----------|------------------|----------|--------|
| `t1` | First Tier | **Free Plan** | $0 | 0 | 🟢 Emerald `#10B981` |
| `t2` | Second Tier | **Starter Plan** | $14.90 / $9.90 | 200 | 🔵 Blue `#3B82F6` |
| `t3` | Third Tier | **Pro Plan** | $29.90 / $19.90 | 500 | 🟣 Violet `#7C3AED` |
| `t4` | Fourth Tier | **(预留)** | 待定 | 待定 | 预留 |

### 2.2 Tier 等级比较

```python
TIER_LEVELS = {
    "t1": 1,  # First Tier (Free)
    "t2": 2,  # Second Tier (Starter)
    "t3": 3,  # Third Tier (Pro)
    "t4": 4,  # Fourth Tier (Enterprise)
}

# 比较函数
def compare_tiers(tier1: str, tier2: str) -> int:
    """返回: -1 (tier1 < tier2), 0 (相等), 1 (tier1 > tier2)"""
```

---

## 三、代码使用规范

### 3.1 正确使用

```python
# ✅ 使用系统代码常量
from domains.identity.constants import TIER_T1, TIER_T2, TIER_T3

if user.tier == TIER_T2:
    # 处理 Starter 用户
    pass

# ✅ 从配置获取显示名称
plan_name = await tier_service.get_tier_display_name(user.tier)

# ✅ 从配置获取月度积分
credits = await tier_service.get_monthly_credits(user.tier)
```

### 3.2 错误使用

```python
# ❌ 硬编码显示名称
if user.tier == "Starter Plan":  # 错误！可能会改名
    pass

# ❌ 硬编码积分数量
credits = 100  # 错误！应该从配置获取

# ❌ 使用魔法字符串
if user.tier == "t2":  # 应该使用常量 TIER_T2
    pass
```

---

## 四、权益配置

### 4.1 基础权益

| 权益 | t1 (Free) | t2 (Starter) | t3 (Pro) |
|------|-----------|--------------|----------|
| 月度积分 | 0 | 200 | 500 |
| 项目数量 | 3 | 50 | 无限 |
| 素材存储 | 100 MB | 5 GB | 20 GB |
| 导出水印 | 有 | 无 | 无 |
| 高级模板 | 部分 | 全部 | 全部 |

### 4.2 配置来源

所有权益配置存储在 `system_configs` 表，支持 Admin 页面动态调整：

```sql
-- 查询 Tier 配置
SELECT * FROM system_configs 
WHERE key LIKE 'tier.%';
```

---

## 五、状态流转

### 5.1 升级流程

```
┌─────┐    升级     ┌─────┐    升级     ┌─────┐
│ t1  │ ─────────▶ │ t2  │ ─────────▶ │ t3  │
│Free │   Stripe   │Start│   Stripe   │ Pro │
└─────┘            └─────┘            └─────┘
```

**升级时机**: 立即生效，当月积分按比例补发

### 5.2 降级流程

```
┌─────┐   期末降级  ┌─────┐   期末降级  ┌─────┐
│ t3  │ ────────▶ │ t2  │ ────────▶ │ t1  │
│ Pro │  period_end│Start│  period_end│Free │
└─────┘            └─────┘            └─────┘
```

**降级时机**: 当前周期结束后生效 (`cancel_at_period_end = true`)

### 5.3 取消订阅

```
┌──────────────┐    取消订阅    ┌──────────────┐
│ t2/t3 Active │ ────────────▶ │ t1 (期末)    │
│              │   期末降级     │              │
└──────────────┘               └──────────────┘
```

---

## 六、数据库字段

### 6.1 profiles 表相关字段

```sql
-- Tier 相关
tier TEXT NOT NULL DEFAULT 't1',
tier_changed_at TIMESTAMPTZ,

-- 订阅相关
subscription_status TEXT,  -- active, canceled, past_due, etc.
subscription_current_period_start TIMESTAMPTZ,
subscription_current_period_end TIMESTAMPTZ,

-- 取消/降级状态
cancel_at_period_end BOOLEAN DEFAULT FALSE,
cancel_at TIMESTAMPTZ,
pending_tier_change TEXT,  -- 期末降级目标 tier
```

### 6.2 subscription_status 值

| 状态 | 说明 |
|------|------|
| `active` | 订阅活跃 |
| `canceled` | 已取消（期末失效） |
| `past_due` | 付款逾期 |
| `incomplete` | 首次付款未完成 |
| `trialing` | 试用期 |
| `inactive` | 不活跃 |

---

## 七、API 接口

### 7.1 获取当前 Tier

```http
GET /api/v1/billing/tier
```

响应：
```json
{
  "tier": "t2",
  "display_name": "Starter Plan",
  "monthly_credits": 100,
  "subscription_status": "active",
  "period_end": "2026-03-01T00:00:00Z"
}
```

### 7.2 升级 Tier

```http
POST /api/v1/billing/upgrade
{
  "target_tier": "t3"
}
```

### 7.3 降级/取消

```http
POST /api/v1/billing/downgrade
{
  "target_tier": "t1"  // null 表示取消订阅
}
```

---

## 八、试用期

### 8.1 试用期规则

| 配置 | 值 |
|------|-----|
| 试用时长 | 30 天 |
| 试用权益 | t3 (Pro) 权益 |
| 试用积分 | 100 永久积分 (注册赠送) |

### 8.2 相关字段

```sql
trial_start_date TIMESTAMPTZ,
trial_end_date TIMESTAMPTZ,
is_trial_active BOOLEAN DEFAULT FALSE,
trial_extended_days INTEGER DEFAULT 0,  -- Admin 可延长
```

---

## 九、相关文档

- [积分系统](../credits-system/overview.md)
- [用户 ID 系统](../user-id-system.md)
- [Stripe 集成](../stripe-integration/)
- [Tier 权益详情](./permissions.md)

---

**END OF DOCUMENT**
