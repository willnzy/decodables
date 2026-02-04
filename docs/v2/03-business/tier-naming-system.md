# Tier 命名系统 (可配置化)

> 用户等级命名与显示策略的统一规范。

**状态**: active  
**版本**: 2.1.0  
**版本日期**: 2026-01-12  
**最后复核**: 2026-01-12  
**负责人**: Backend Team  
**适用范围**: shared  
**source_repo**: backend  
**sync_required**: yes

---

## 概述

Make Decodables 的用户等级 (Tier) 系统采用**配置化命名**机制，允许管理员通过 Admin 面板动态修改等级显示名称，以便未来营销策略调整。

**实施状态**: 此设计已于 2026-01-10 完成实施，所有代码已迁移至 `t1/t2/t3` 命名系统。

---

## 系统架构

### 四层等级系统

| 系统代码 (tier) | 简称 | 当前显示名称 (可配置) | 月度积分 | 价格 | 主题色 |
|-----------------|------|---------------------|----------|------|--------|
| `t1` | First Tier | Free Plan | 0 | $0 | Emerald |
| `t2` | Second Tier | Starter Plan | 100 | ~~$9.9~~ $6.9/月 | Blue |
| `t3` | Third Tier | Pro Plan | 200 | ~~$15.9~~ $9.9/月 | Violet |
| `t4` | Fourth Tier | Enterprise Plan | 500 | 待定 | Orange |

> **t4 说明**: t4 目前预留，尚未启用。详见 `docs/v2/03-business/entitlement/permission-matrix.md`

**设计原则**:
- **系统代码** (`t1`/`t2`/`t3`/`t4`) - 数据库字段、代码逻辑使用，永不改变
- **简称** (First/Second/Third/Fourth Tier) - 固定描述，便于理解层级
- **显示名称** - 用户看到的名称，可通过 Admin 配置

**为什么使用 t1/t2/t3**:
- 简洁：减少输入和存储
- 中立：不绑定业务语义，便于营销改名
- 可扩展：可增加更高等级
- 国际化：系统代码无需翻译

---

## 主题色配置

| 系统代码 | 主题色名称 | 主色 (500) | 深色 (600) | 浅背景 (50) | Tailwind 类名 |
|----------|------------|------------|------------|-------------|---------------|
| `t1` | Emerald | `#10B981` | `#059669` | `#ECFDF5` | `emerald-*` |
| `t2` | Blue | `#3B82F6` | `#2563EB` | `#EFF6FF` | `blue-*` |
| `t3` | Violet | `#7C3AED` | `#6D28D9` | `#F5F3FF` | `violet-*` |

### CSS 变量

```css
:root {
  --tier-t1-50: #ECFDF5;
  --tier-t1-100: #D1FAE5;
  --tier-t1-500: #10B981;
  --tier-t1-600: #059669;

  --tier-t2-50: #EFF6FF;
  --tier-t2-100: #DBEAFE;
  --tier-t2-500: #3B82F6;
  --tier-t2-600: #2563EB;

  --tier-t3-50: #F5F3FF;
  --tier-t3-100: #EDE9FE;
  --tier-t3-500: #8B5CF6;
  --tier-t3-600: #7C3AED;
}
```

---

## 存储设计

### system_configs 配置表

显示名称存储在 `system_configs` 表中，支持通过 Admin API 动态修改：

```sql
INSERT INTO system_configs (key, value, value_type, category, description, is_user_visible) VALUES
('tier.t1.display_name', 'Free Plan', 'text', 'tier', 'First Tier 显示名称', FALSE),
('tier.t2.display_name', 'Starter Plan', 'text', 'tier', 'Second Tier 显示名称', FALSE),
('tier.t3.display_name', 'Pro Plan', 'text', 'tier', 'Third Tier 显示名称', FALSE),
('tier.t4.display_name', 'Enterprise Plan', 'text', 'tier', 'Fourth Tier 显示名称', FALSE);

INSERT INTO system_configs (key, value, value_type, category, description, is_user_visible) VALUES
('tier.t1.monthly_credits', '0', 'integer', 'tier', 'First Tier 月度积分', FALSE),
('tier.t2.monthly_credits', '100', 'integer', 'tier', 'Second Tier 月度积分', FALSE),
('tier.t3.monthly_credits', '200', 'integer', 'tier', 'Third Tier 月度积分', FALSE),
('tier.t4.monthly_credits', '500', 'integer', 'tier', 'Fourth Tier 月度积分', FALSE);
```

### profiles 表

```sql
CREATE TABLE profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    tier TEXT NOT NULL DEFAULT 't1' CHECK (tier IN ('t1', 't2', 't3', 't4')),
    tier_changed_at TIMESTAMPTZ,
    credits_monthly INTEGER NOT NULL DEFAULT 0,
    credits_permanent INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_profiles_tier ON profiles(tier);
```

---

## 代码使用规范

### 正确使用

```python
TIER_T1 = "t1"
TIER_T2 = "t2"
TIER_T3 = "t3"
TIER_T4 = "t4"

VALID_TIERS = {TIER_T1, TIER_T2, TIER_T3, TIER_T4}

TIER_LABELS = {
    TIER_T1: "First Tier",
    TIER_T2: "Second Tier",
    TIER_T3: "Third Tier",
    TIER_T4: "Fourth Tier",
}
```

### 错误使用

```python
if user.tier == "t2":
    plan_name = "Starter Plan"  # 错误: 硬编码显示名称
```

---

## 相关文档

- `docs/v2/03-business/entitlement/permission-matrix.md`
