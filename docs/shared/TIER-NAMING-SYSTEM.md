# Tier 命名系统 (可配置化)

> **版本**: 2.1.0 (Tier 权限配置化完成)
> **最后更新**: 2026-01-12
> **实施状态**: ✅ 已完成
> **Commit**: b7844be
> **实施日期**: 2026-01-12
> **覆盖范围**: 67文件, 245处修改 (v2.0.0) + Tier 权限配置化 (v2.1.0)
> **相关API**: api-reference.md v3.26 § 5.2 (System Config), § 1.9 (DDD架构)
> **权限文档**: TIER-PERMISSIONS.md (会员权益汇总表)

## 概述

Make Decodables 的用户等级 (Tier) 系统采用**配置化命名**机制，允许管理员通过 Admin 面板动态修改等级显示名称，以便未来营销策略调整。

**📍 实施状态**: 此设计已于 2026-01-10 完成实施,所有代码已迁移至 t1/t2/t3 命名系统。

---

## 系统架构

### 四层等级系统

| 系统代码 (tier) | 简称 | 当前显示名称 (可配置) | 月度积分 | 价格 | 主题色 |
|-----------------|------|---------------------|----------|------|--------|
| `t1` | First Tier | Free Plan | 0 | $0 | 🟢 Emerald |
| `t2` | Second Tier | Starter Plan | 100 | ~~$9.9~~ $6.9/月 | 🔵 Blue |
| `t3` | Third Tier | Pro Plan | 200 | ~~$15.9~~ $9.9/月 | 🟣 Violet |
| `t4` | Fourth Tier | Enterprise Plan | 500 | 待定 | 🟠 Orange |

> ⚠️ **t4 (Enterprise)** 目前预留，尚未启用。详见 [TIER-PERMISSIONS.md](./TIER-PERMISSIONS.md)

**设计原则**:
- **系统代码** (`t1`/`t2`/`t3`/`t4`) - 数据库字段、代码逻辑使用，**永不改变**
- **简称** (First Tier/Second Tier/Third Tier/Fourth Tier) - 固定的描述性名称，便于理解层级
- **显示名称** (Free Plan/Starter Plan/Pro Plan/Enterprise Plan) - 用户看到的名称，**可通过 Admin 配置**，存储在 system_configs 表

**为什么使用 t1/t2/t3**:
- ✅ **简洁**: 比 `free`/`starter`/`pro` 更短，减少输入和存储
- ✅ **中立**: 不包含业务语义，方便未来调整（例如 t2 可以从 "Starter Plan" 改名为 "Growth Plan"）
- ✅ **可扩展**: 未来可以轻松添加 t4、t5 等更高等级
- ✅ **国际化**: 不需要翻译系统代码，只需翻译显示名称

---

## 主题色配置

每个 Tier 都有对应的品牌主题色，用于 UI 视觉区分：

### 颜色映射表

| 系统代码 | 主题色名称 | 主色 (500) | 深色 (600) | 浅背景 (50) | Tailwind 类名 |
|----------|------------|------------|------------|-------------|---------------|
| `t1` | Emerald | `#10B981` | `#059669` | `#ECFDF5` | `emerald-*` |
| `t2` | Blue | `#3B82F6` | `#2563EB` | `#EFF6FF` | `blue-*` |
| `t3` | Violet | `#7C3AED` | `#6D28D9` | `#F5F3FF` | `violet-*` |

### CSS 变量

```css
/* 定义于 app/globals.css */
:root {
  /* t1 - Free (Emerald) */
  --tier-t1-50: #ECFDF5;
  --tier-t1-100: #D1FAE5;
  --tier-t1-500: #10B981;
  --tier-t1-600: #059669;

  /* t2 - Starter (Blue) */
  --tier-t2-50: #EFF6FF;
  --tier-t2-100: #DBEAFE;
  --tier-t2-500: #3B82F6;
  --tier-t2-600: #2563EB;

  /* t3 - Pro (Violet) */
  --tier-t3-50: #F5F3FF;
  --tier-t3-100: #EDE9FE;
  --tier-t3-500: #8B5CF6;
  --tier-t3-600: #7C3AED;
}
```

### 前端使用

```tsx
// 颜色映射 (使用系统代码)
const tierColors = {
  t1: {
    bg: 'bg-emerald-50',
    border: 'border-emerald-400',
    text: 'text-emerald-600',
    badge: 'badge-tier-t1',
  },
  t2: {
    bg: 'bg-blue-50',
    border: 'border-blue-400',
    text: 'text-blue-600',
    badge: 'badge-tier-t2',
  },
  t3: {
    bg: 'bg-violet-50',
    border: 'border-violet-400',
    text: 'text-violet-600',
    badge: 'badge-tier-t3',
  },
};

// 使用示例
function TierBadge({ tier }: { tier: 't1' | 't2' | 't3' }) {
  const colors = tierColors[tier];
  return (
    <span className={`${colors.bg} ${colors.text} px-2 py-1 rounded-full text-xs font-medium`}>
      {tier.toUpperCase()}
    </span>
  );
}
```

### 后端日志使用

```python
# 日志中使用系统代码 + 简称
logger.info(f"User upgraded to {tier} ({TIER_LABELS[tier]})")
# 输出: User upgraded to t2 (Second Tier)
```

---

## 存储设计

### system_configs 配置表

显示名称存储在 `system_configs` 表中，支持通过 Admin API 动态修改：

```sql
-- Tier 显示名称配置 (可通过 Admin 修改)
INSERT INTO system_configs (key, value, value_type, category, description, is_user_visible) VALUES
('tier.t1.display_name', 'Free Plan', 'text', 'tier', 'First Tier 显示名称', FALSE),
('tier.t2.display_name', 'Starter Plan', 'text', 'tier', 'Second Tier 显示名称', FALSE),
('tier.t3.display_name', 'Pro Plan', 'text', 'tier', 'Third Tier 显示名称', FALSE),
('tier.t4.display_name', 'Enterprise Plan', 'text', 'tier', 'Fourth Tier 显示名称', FALSE);

-- Tier 月度积分配置 (也可配置)
INSERT INTO system_configs (key, value, value_type, category, description, is_user_visible) VALUES
('tier.t1.monthly_credits', '0', 'integer', 'tier', 'First Tier 月度积分', FALSE),
('tier.t2.monthly_credits', '100', 'integer', 'tier', 'Second Tier 月度积分', FALSE),
('tier.t3.monthly_credits', '200', 'integer', 'tier', 'Third Tier 月度积分', FALSE),
('tier.t4.monthly_credits', '500', 'integer', 'tier', 'Fourth Tier 月度积分', FALSE);
```

### profiles 表

用户的 tier 字段存储系统代码 (`t1`/`t2`/`t3`)：

```sql
CREATE TABLE profiles (
    id TEXT PRIMARY KEY,  -- Clerk user ID
    email TEXT NOT NULL UNIQUE,

    -- 用户等级 (系统代码)
    tier TEXT NOT NULL DEFAULT 't1' CHECK (tier IN ('t1', 't2', 't3', 't4')),
    tier_changed_at TIMESTAMPTZ,

    -- 积分余额
    credits_monthly INTEGER NOT NULL DEFAULT 0,
    credits_permanent INTEGER NOT NULL DEFAULT 0,

    -- 审计字段
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_profiles_tier ON profiles(tier);
```

---

## 代码使用规范

### ✅ 正确使用

```python
# domains/user/constants.py
"""User tier constants."""

# 系统代码 (永不改变)
TIER_T1 = "t1"  # First Tier
TIER_T2 = "t2"  # Second Tier
TIER_T3 = "t3"  # Third Tier
TIER_T4 = "t4"  # Fourth Tier (Enterprise, 预留)

# 有效的 tier 代码
VALID_TIERS = {TIER_T1, TIER_T2, TIER_T3, TIER_T4}

# 简称 (固定描述)
TIER_LABELS = {
    TIER_T1: "First Tier",
    TIER_T2: "Second Tier",
    TIER_T3: "Third Tier",
    TIER_T4: "Fourth Tier",
}

# 默认月度积分 (也可从 system_configs 读取)
TIER_MONTHLY_CREDITS = {
    TIER_T1: 0,
    TIER_T2: 100,
    TIER_T3: 200,
    TIER_T4: 500,
}

# Tier 等级 (用于比较)
TIER_LEVELS = {
    TIER_T1: 1,
    TIER_T2: 2,
    TIER_T3: 3,
    TIER_T4: 4,
}
```

```python
# domains/user/tier_service.py
"""Tier configuration service."""

class TierService:
    """管理 Tier 配置和显示名称."""

    def __init__(self, config_repo):
        self.config_repo = config_repo
        self._cache = {}

    async def get_tier_display_name(self, tier: str) -> str:
        """
        获取 Tier 显示名称 (可配置).

        Args:
            tier: 系统代码 ('t1', 't2', 't3')

        Returns:
            显示名称 (例如: 'Free Plan', 可能被 Admin 修改)
        """
        if tier not in self._cache:
            config_key = f"tier.{tier}.display_name"
            config = await self.config_repo.get_config(config_key)
            self._cache[tier] = config["value"] if config else TIER_LABELS[tier]

        return self._cache[tier]

    def get_tier_label(self, tier: str) -> str:
        """
        获取 Tier 固定简称.

        Args:
            tier: 系统代码

        Returns:
            简称 (例如: 'First Tier', 永不改变)
        """
        return TIER_LABELS.get(tier, tier.upper())

    async def update_tier_display_name(self, tier: str, display_name: str):
        """
        更新 Tier 显示名称 (Admin 操作).

        Args:
            tier: 系统代码
            display_name: 新的显示名称
        """
        if tier not in VALID_TIERS:
            raise ValueError(f"Invalid tier: {tier}")

        config_key = f"tier.{tier}.display_name"
        await self.config_repo.update_config(config_key, display_name)

        # 清除缓存
        self._cache.pop(tier, None)
```

```python
# 业务逻辑使用系统代码
from domains.user.constants import TIER_T1, TIER_T2, TIER_MONTHLY_CREDITS

# ✅ 正确: 使用系统代码
if user.tier == TIER_T2:
    credits = TIER_MONTHLY_CREDITS[TIER_T2]  # 200

# ✅ 正确: 判断等级
from domains.user.constants import TIER_LEVELS
if TIER_LEVELS[user.tier] >= TIER_LEVELS[TIER_T2]:
    # 用户是 Second Tier 或更高等级
    allow_feature = True
```

```python
# API 返回显示名称
from domains.user.tier_service import TierService

@router.get("/me")
async def get_current_user(user_id: str):
    user = await user_repo.get_profile(user_id)
    tier_service = TierService(config_repo)

    return {
        "tier": user["tier"],  # "t2" (系统代码)
        "tier_label": tier_service.get_tier_label(user["tier"]),  # "Second Tier" (固定)
        "tier_name": await tier_service.get_tier_display_name(user["tier"]),  # "Starter Plan" (可配置)
        "credits_monthly": user["credits_monthly"],
        "credits_permanent": user["credits_permanent"],
    }
```

### ❌ 错误使用

```python
# ❌ 错误: 硬编码显示名称
if user.tier == "t2":
    plan_name = "Starter Plan"  # 将来可能改名!

# ✅ 正确: 从配置获取
plan_name = await tier_service.get_tier_display_name(user.tier)

# ❌ 错误: 使用字符串比较等级
if user.tier == "t2" or user.tier == "t3":
    # 不优雅,且难扩展

# ✅ 正确: 使用等级数值比较
if TIER_LEVELS[user.tier] >= TIER_LEVELS[TIER_T2]:
    # 优雅且易扩展
```

---

## Admin API

### 更新 Tier 显示名称

```python
# api/admin/system.py
@router.patch("/tiers/{tier}/display-name")
@limiter.limit("10/minute")
async def update_tier_display_name(
    request: Request,
    tier: str,
    req: UpdateTierDisplayNameRequest,
    admin: dict = Depends(require_admin)
):
    """
    更新 Tier 显示名称.

    Example:
        PATCH /api/v2/admin/tiers/t2/display-name
        {"display_name": "Growth Plan"}
    """
    if tier not in VALID_TIERS:
        raise HTTPException(400, f"Invalid tier: {tier}")

    tier_service = TierService(config_repo)
    await tier_service.update_tier_display_name(tier, req.display_name)

    # 审计日志
    await admin_repo.admin_log_operation(
        admin_id=admin["id"],
        operation_type="tier_config_update",
        target_user_id=None,
        details=f"Changed {tier} ({tier_service.get_tier_label(tier)}) display name to '{req.display_name}'",
        reason=None
    )

    return {
        "status": "updated",
        "tier": tier,
        "tier_label": tier_service.get_tier_label(tier),
        "display_name": req.display_name
    }
```

### 获取所有 Tier 配置

```python
@router.get("/tiers")
async def get_all_tiers(admin: dict = Depends(require_admin)):
    """
    获取所有 Tier 配置.

    Returns:
        [
            {
                "tier": "t1",
                "tier_label": "First Tier",
                "display_name": "Free Plan",
                "monthly_credits": 0
            },
            {
                "tier": "t2",
                "tier_label": "Second Tier",
                "display_name": "Starter Plan",
                "monthly_credits": 200
            },
            {
                "tier": "t3",
                "tier_label": "Third Tier",
                "display_name": "Pro Plan",
                "monthly_credits": 500
            }
        ]
    """
    tier_service = TierService(config_repo)

    tiers = []
    for tier_code in sorted(VALID_TIERS):
        display_name = await tier_service.get_tier_display_name(tier_code)
        tier_label = tier_service.get_tier_label(tier_code)
        monthly_credits = TIER_MONTHLY_CREDITS[tier_code]

        tiers.append({
            "tier": tier_code,
            "tier_label": tier_label,
            "display_name": display_name,
            "monthly_credits": monthly_credits,
        })

    return {"tiers": sorted(tiers, key=lambda x: TIER_LEVELS[x["tier"]])}
```

---

## 前端使用

### useTierConfig Hook

```tsx
// decodables-fe/@business/hooks/useTierConfig.ts
export function useTierConfig() {
  const { data, isLoading } = useQuery({
    queryKey: ['tier-configs'],
    queryFn: async () => {
      const res = await fetch('/api/v2/admin/tiers')
      return res.json()
    },
    staleTime: 5 * 60 * 1000, // 5 分钟缓存
  })

  return {
    tiers: data?.tiers || [],
    getTierName: (tier: string) => {
      // 返回可配置的显示名称
      const config = data?.tiers?.find(t => t.tier === tier)
      return config?.display_name || tier.toUpperCase()
    },
    getTierLabel: (tier: string) => {
      // 返回固定的简称
      const config = data?.tiers?.find(t => t.tier === tier)
      return config?.tier_label || tier.toUpperCase()
    },
    isLoading,
  }
}
```

### 前端显示

```tsx
// 使用 Hook
function PricingCard({ tier }: { tier: string }) {
  const { getTierName, getTierLabel } = useTierConfig()

  return (
    <Card>
      {/* 显示可配置的名称 */}
      <h3>{getTierName(tier)}</h3>  {/* "Starter Plan" */}

      {/* 显示固定的简称 */}
      <Badge variant="secondary">{getTierLabel(tier)}</Badge>  {/* "Second Tier" */}

      {/* 显示系统代码 (debug 用) */}
      <code className="text-xs">{tier}</code>  {/* "t2" */}
    </Card>
  )
}

// 用户档案显示
function UserProfile({ user }: { user: User }) {
  const { getTierName, getTierLabel } = useTierConfig()

  return (
    <div>
      <p>Current Plan: {getTierName(user.tier)}</p>  {/* "Starter Plan" */}
      <p>Tier Level: {getTierLabel(user.tier)}</p>  {/* "Second Tier" */}
      <p className="text-muted">Tier Code: {user.tier}</p>  {/* "t2" */}
    </div>
  )
}
```

---

## 迁移计划

### Phase 1: 数据库迁移

将现有的 `free`/`starter`/`pro` 迁移为 `t1`/`t2`/`t3`：

```sql
-- 迁移脚本: scripts/migrations/001_migrate_tier_codes.sql
BEGIN;

-- 更新 profiles 表
UPDATE profiles SET tier = 't1' WHERE tier = 'free';
UPDATE profiles SET tier = 't2' WHERE tier = 'starter';
UPDATE profiles SET tier = 't3' WHERE tier = 'pro';

-- 更新 CHECK 约束
ALTER TABLE profiles DROP CONSTRAINT IF EXISTS profiles_tier_check;
ALTER TABLE profiles ADD CONSTRAINT profiles_tier_check CHECK (tier IN ('t1', 't2', 't3'));

-- 插入 system_configs 配置
INSERT INTO system_configs (key, value, value_type, category, description, is_user_visible) VALUES
('tier.t1.display_name', 'Free Plan', 'text', 'tier', 'First Tier 显示名称 (可配置)', FALSE),
('tier.t2.display_name', 'Starter Plan', 'text', 'tier', 'Second Tier 显示名称 (可配置)', FALSE),
('tier.t3.display_name', 'Pro Plan', 'text', 'tier', 'Third Tier 显示名称 (可配置)', FALSE)
ON CONFLICT (key) DO NOTHING;

COMMIT;

-- 验证迁移结果
SELECT tier, COUNT(*) as user_count
FROM profiles
GROUP BY tier
ORDER BY tier;

-- 预期结果:
--  tier | user_count
-- ------+------------
--  t1   | XXX
--  t2   | YYY
--  t3   | ZZZ
```

### Phase 2: 后端代码更新

```bash
# 需要更新的文件
domains/user/constants.py                      # 更新常量 (free → t1)
infrastructure/repositories/user_repository.py # 更新默认值
api/**/*.py                                    # 更新所有 tier 判断逻辑
tests/**/*.py                                  # 更新所有测试用例
docs/后台业务逻辑说明.md                        # 更新文档
CLAUDE.md                                      # 更新配置文档
```

### Phase 3: 前端代码更新

```bash
# 需要更新的文件
@business/types/user.ts                # 更新 Tier 类型定义 (Tier = 't1' | 't2' | 't3')
@business/hooks/useTierConfig.ts       # 新增 Hook
@business/stores/userStore.ts          # 更新 tier 处理逻辑
app/**/components/**/*.tsx             # 更新所有显示 tier 的组件
```

---

## 测试

### 单元测试

```python
# tests/domains/test_tier_service.py
import pytest
from domains.user.tier_service import TierService
from domains.user.constants import TIER_T1, TIER_T2, TIER_T3

@pytest.mark.asyncio
async def test_get_tier_display_name():
    """Should return correct tier display name from config."""
    tier_service = TierService(mock_config_repo)

    assert await tier_service.get_tier_display_name(TIER_T1) == "Free Plan"
    assert await tier_service.get_tier_display_name(TIER_T2) == "Starter Plan"
    assert await tier_service.get_tier_display_name(TIER_T3) == "Pro Plan"

def test_get_tier_label():
    """Should return fixed tier labels."""
    tier_service = TierService(mock_config_repo)

    assert tier_service.get_tier_label(TIER_T1) == "First Tier"
    assert tier_service.get_tier_label(TIER_T2) == "Second Tier"
    assert tier_service.get_tier_label(TIER_T3) == "Third Tier"

@pytest.mark.asyncio
async def test_update_tier_display_name():
    """Admin should be able to update tier display name."""
    tier_service = TierService(mock_config_repo)

    # 更新 T2 显示名称
    await tier_service.update_tier_display_name(TIER_T2, "Growth Plan")

    # 验证缓存已清除
    assert await tier_service.get_tier_display_name(TIER_T2) == "Growth Plan"

    # 固定简称不变
    assert tier_service.get_tier_label(TIER_T2) == "Second Tier"
```

### 集成测试

```python
# tests/api/admin/test_tier_config.py
@pytest.mark.asyncio
async def test_update_tier_display_name_api():
    """Test admin API for updating tier display name."""
    response = await client.patch(
        "/api/v2/admin/tiers/t2/display-name",
        json={"display_name": "Growth Plan"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["tier"] == "t2"
    assert data["tier_label"] == "Second Tier"
    assert data["display_name"] == "Growth Plan"
```

---

## 文档更新清单

### 后端文档
- [x] `docs/shared/TIER-NAMING-SYSTEM.md` (本文档)
- [ ] `docs/后台业务逻辑说明.md` - 更新 Tier 系统说明
- [ ] `CLAUDE.md` - 更新用户等级表
- [ ] `api-reference.md` - 添加 Tier 配置 API

### 前端文档
- [ ] `decodables-fe/docs/shared/TIER-NAMING-SYSTEM.md` (复制本文档)
- [ ] `decodables-fe/docs/前端完整开发规范.md` - 添加 Tier 显示规范

### 数据库文档
- [ ] `migrations/v2/design_reasoning.md` - 更新 Tier 系统说明
- [ ] `migrations/v2/refactored_schema_v2.sql` - 更新 tier CHECK 约束和注释
- [ ] `migrations/v2/README.md` - 更新 Tier 说明

---

## 总结

| 层级 | 系统代码 | 固定简称 | 显示名称 (可配置) |
|------|----------|----------|------------------|
| **示例** | `t2` | `Second Tier` | `Starter Plan` |
| **用途** | 数据库字段、代码逻辑 | 层级描述、文档说明 | UI 显示、营销文案 |
| **可修改** | ❌ 永不改变 | ❌ 永不改变 | ✅ Admin 可配置 |
| **存储位置** | profiles.tier + 代码常量 | 代码常量 | system_configs 表 |

**最佳实践**:
- ✅ 业务逻辑使用 **系统代码** (`t1`/`t2`/`t3`/`t4`)
- ✅ 文档和日志使用 **固定简称** (First Tier/Second Tier/Third Tier/Fourth Tier)
- ✅ UI 显示使用 **显示名称** (从 TierService 获取)
- ✅ 代码中使用常量 (`TIER_T1`, `TIER_T2`, `TIER_T3`, `TIER_T4`)，不硬编码字符串
- ✅ 等级比较使用 `TIER_LEVELS` 字典，不使用字符串比较
- ✅ 修改名称只需通过 Admin API，无需改代码
- ✅ 功能权限通过 TierService.can_use_feature() 检查，支持 "trial" 值

---

## 相关文档

- [TIER-PERMISSIONS.md](./TIER-PERMISSIONS.md) - 会员权益汇总表 (完整的功能权限配置)
- `docs/tmp/TIER-PERMISSIONS-BACKEND-IMPLEMENTATION.md` - 后端实现说明

---

**最后更新**: 2026-01-12
**维护人**: 后端团队
**状态**: ✅ v2.1.0 实施完成
