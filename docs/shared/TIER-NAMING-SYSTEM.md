# Tier 命名系统 (可配置化)

## 概述

Make Decodables 的用户等级 (Tier) 系统采用**配置化命名**机制,允许管理员动态修改等级名称,以便未来营销策略调整。

---

## 系统架构

### 三层等级系统

| 等级代码 (tier) | 当前显示名称 | 月度积分 | 价格 |
|-----------------|--------------|----------|------|
| `free` | **Free Plan** | 0 | $0 |
| `starter` | **Starter Plan** | 200 | $9.9/月 |
| `pro` | **Pro Plan** | 500 | $19.9/月 |

**设计原则**:
- **tier 代码** (`free`/`starter`/`pro`) - 系统内部使用,不可更改
- **显示名称** (Free Plan/Starter Plan/Pro Plan) - 用户看到的名称,可配置

---

## 当前问题 ❌

系统中 tier 名称是**硬编码**的,分散在多个位置:

### 后端硬编码
```python
# api/admin/subscriptions.py
if 'starter' in price_id.lower():
    plan_name = "Starter"  # 硬编码
elif 'pro' in price_id.lower():
    plan_name = "Pro"  # 硬编码
```

### 前端硬编码
```tsx
// 假设存在
const TIER_NAMES = {
  free: "Free Plan",
  starter: "Starter Plan",
  pro: "Pro Plan"
}
```

**问题**:
1. 如果想将 "Starter Plan" 改为 "Growth Plan",需要修改代码
2. 多处硬编码,容易遗漏
3. 不支持 A/B 测试或多语言

---

## 解决方案 ✅

### 方案 1: 数据库配置表 (推荐)

#### 1.1 创建 `tier_configs` 表

```sql
CREATE TABLE tier_configs (
    tier TEXT PRIMARY KEY,  -- 'free', 'starter', 'pro'
    display_name TEXT NOT NULL,  -- 'Free Plan', 'Starter Plan', 'Pro Plan'
    description TEXT,  -- 等级描述
    monthly_credits INT NOT NULL,  -- 月度积分
    is_active BOOLEAN DEFAULT TRUE,  -- 是否启用
    sort_order INT DEFAULT 0,  -- 显示顺序
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 初始数据
INSERT INTO tier_configs (tier, display_name, description, monthly_credits, sort_order) VALUES
('free', 'Free Plan', 'Perfect for trying out Make Decodables', 0, 1),
('starter', 'Starter Plan', 'Great for regular creators', 200, 2),
('pro', 'Pro Plan', 'For professional creators and teams', 500, 3);

-- 索引
CREATE INDEX idx_tier_configs_active ON tier_configs(is_active);
CREATE INDEX idx_tier_configs_sort ON tier_configs(sort_order);
```

#### 1.2 Repository 层

```python
# infrastructure/repositories/tier_repository.py
class SupabaseTierRepository:
    """Tier configuration repository."""

    def __init__(self, client):
        self.client = client

    async def get_all_tiers(self) -> list[dict]:
        """Get all active tiers ordered by sort_order."""
        result = self.client.table("tier_configs").select("*").eq(
            "is_active", True
        ).order("sort_order").execute()
        return result.data or []

    async def get_tier_by_code(self, tier: str) -> dict:
        """
        Get tier configuration by tier code.

        Args:
            tier: Tier code ('free', 'starter', 'pro')

        Returns:
            Tier configuration dict with display_name, monthly_credits, etc.
        """
        result = self.client.table("tier_configs").select("*").eq(
            "tier", tier
        ).execute()
        return result.data[0] if result.data else None

    async def update_tier_display_name(self, tier: str, display_name: str) -> dict:
        """
        Update tier display name (Admin operation).

        Args:
            tier: Tier code
            display_name: New display name

        Returns:
            Updated tier config
        """
        result = self.client.table("tier_configs").update({
            "display_name": display_name,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("tier", tier).execute()
        return result.data[0] if result.data else None
```

#### 1.3 Service 层 (缓存优化)

```python
# domains/user/tier_service.py
from functools import lru_cache
from typing import Dict

class TierService:
    """Tier configuration service with caching."""

    def __init__(self, tier_repo: SupabaseTierRepository):
        self.tier_repo = tier_repo
        self._cache: Dict[str, dict] = {}
        self._cache_timestamp = None

    async def get_tier_display_name(self, tier: str) -> str:
        """
        Get tier display name with caching.

        Args:
            tier: Tier code ('free', 'starter', 'pro')

        Returns:
            Display name (e.g., 'Starter Plan')
        """
        # 缓存 5 分钟
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        if (not self._cache_timestamp or
            now - self._cache_timestamp > timedelta(minutes=5)):
            # 刷新缓存
            tiers = await self.tier_repo.get_all_tiers()
            self._cache = {t["tier"]: t for t in tiers}
            self._cache_timestamp = now

        tier_config = self._cache.get(tier)
        return tier_config["display_name"] if tier_config else tier.title()

    async def get_tier_config(self, tier: str) -> dict:
        """Get full tier configuration."""
        if tier in self._cache:
            return self._cache[tier]
        return await self.tier_repo.get_tier_by_code(tier)

    async def invalidate_cache(self):
        """Invalidate tier cache (called after admin updates)."""
        self._cache = {}
        self._cache_timestamp = None
```

#### 1.4 API 层使用

```python
# api/admin/subscriptions.py
from domains.user.tier_service import TierService

@router.post("/subscription/cancel")
async def adm_cancel_subscription(...):
    # ...

    # ❌ 旧代码: 硬编码
    # plan_name = "Unknown"
    # if 'starter' in price_id.lower():
    #     plan_name = "Starter"
    # elif 'pro' in price_id.lower():
    #     plan_name = "Pro"

    # ✅ 新代码: 从配置获取
    tier_service = TierService(SupabaseTierRepository(db))

    # 从 Stripe price_id 推断 tier code
    tier_code = get_tier_from_price_id(price_id)
    plan_name = await tier_service.get_tier_display_name(tier_code)

    # 使用 plan_name...
```

#### 1.5 Admin API (修改 tier 名称)

```python
# api/admin/system.py (新增)
@router.patch("/tiers/{tier}/display-name")
@limiter.limit("10/minute")
async def update_tier_display_name(
    request: Request,
    tier: str,
    display_name: str = Body(..., min_length=1, max_length=50),
    admin: dict = Depends(require_admin)
):
    """
    Update tier display name.

    Example: Change "Starter Plan" to "Growth Plan"
    """
    if tier not in ["free", "starter", "pro"]:
        raise HTTPException(400, "Invalid tier code")

    db = get_database_client()
    tier_repo = SupabaseTierRepository(db)
    tier_service = TierService(tier_repo)

    # 更新数据库
    updated = await tier_repo.update_tier_display_name(tier, display_name)

    # 清除缓存
    await tier_service.invalidate_cache()

    # 审计日志
    admin_repo = SupabaseAdminUsersRepository(db)
    await admin_repo.admin_log_operation(
        admin_id=admin["id"],
        operation_type="tier_config_update",
        target_user_id=None,
        details=f"Changed {tier} display name to '{display_name}'",
        reason=None
    )

    return {"status": "updated", "tier": tier, "display_name": display_name}
```

---

### 方案 2: 环境变量配置 (简单但不灵活)

```python
# config.py
import os

TIER_DISPLAY_NAMES = {
    "free": os.getenv("TIER_FREE_NAME", "Free Plan"),
    "starter": os.getenv("TIER_STARTER_NAME", "Starter Plan"),
    "pro": os.getenv("TIER_PRO_NAME", "Pro Plan"),
}

# 使用
from config import TIER_DISPLAY_NAMES
plan_name = TIER_DISPLAY_NAMES.get(tier, tier.title())
```

**缺点**:
- 需要重启服务才能生效
- 不支持运行时修改
- 无法记录修改历史

---

## 实施计划

### Phase 1: 数据库设计

- [x] 创建 `tier_configs` 表
- [x] 插入初始数据
- [ ] 创建迁移脚本

### Phase 2: 后端实现

- [ ] 创建 `TierRepository`
- [ ] 创建 `TierService` (含缓存)
- [ ] 添加 Admin API (更新 tier 名称)
- [ ] 更新所有使用 tier 名称的地方

**需要更新的文件**:
```bash
# 后端
api/admin/subscriptions.py  # 使用 TierService
api/user/profile.py         # 返回 tier 配置
domains/user/tier_service.py  # 新文件
infrastructure/repositories/tier_repository.py  # 新文件

# 测试
tests/domains/test_tier_service.py  # 新文件
tests/api/admin/test_tier_config.py  # 新文件
```

### Phase 3: 前端实现

- [ ] 创建 `useTierConfig` hook
- [ ] 更新所有显示 tier 名称的组件
- [ ] Admin 面板添加 Tier 配置页面

```tsx
// decodables-fe/@business/hooks/useTierConfig.ts
export function useTierConfig() {
  const { data, isLoading } = useQuery({
    queryKey: ['tier-configs'],
    queryFn: async () => {
      const res = await fetch('/api/v2/tiers/configs')
      return res.json()
    },
    staleTime: 5 * 60 * 1000, // 5 分钟缓存
  })

  return {
    tiers: data?.tiers || [],
    getTierName: (tier: string) => {
      const config = data?.tiers?.find(t => t.tier === tier)
      return config?.display_name || tier
    },
    isLoading,
  }
}

// 使用
function PricingCard({ tier }: { tier: string }) {
  const { getTierName } = useTierConfig()

  return (
    <Card>
      <h3>{getTierName(tier)}</h3>  {/* "Starter Plan" */}
    </Card>
  )
}
```

### Phase 4: Admin 面板

```tsx
// decodables-fe/app/admin/settings/tiers/page.tsx
export default function TierSettingsPage() {
  const { tiers, refetch } = useTierConfig()
  const [editingTier, setEditingTier] = useState(null)

  async function handleUpdateName(tier: string, newName: string) {
    await fetch(`/api/v2/admin/tiers/${tier}/display-name`, {
      method: 'PATCH',
      body: JSON.stringify({ display_name: newName }),
    })
    refetch()
  }

  return (
    <AdminLayout>
      <h1>Tier Configuration</h1>
      <Table>
        {tiers.map(tier => (
          <TableRow key={tier.tier}>
            <TableCell>{tier.tier}</TableCell>
            <TableCell>
              {editingTier === tier.tier ? (
                <Input
                  defaultValue={tier.display_name}
                  onBlur={(e) => {
                    handleUpdateName(tier.tier, e.target.value)
                    setEditingTier(null)
                  }}
                />
              ) : (
                <div onClick={() => setEditingTier(tier.tier)}>
                  {tier.display_name} ✏️
                </div>
              )}
            </TableCell>
            <TableCell>{tier.monthly_credits}</TableCell>
          </TableRow>
        ))}
      </Table>
    </AdminLayout>
  )
}
```

---

## Tier Code 到 Stripe Price ID 的映射

为了从 Stripe price_id 推断 tier code,需要建立映射关系:

```python
# config.py
import os

STRIPE_PRICE_TO_TIER = {
    os.getenv("STRIPE_STARTER_MONTHLY_PRICE_ID"): "starter",
    os.getenv("STRIPE_STARTER_ANNUAL_PRICE_ID"): "starter",
    os.getenv("STRIPE_PRO_MONTHLY_PRICE_ID"): "pro",
    os.getenv("STRIPE_PRO_ANNUAL_PRICE_ID"): "pro",
}

def get_tier_from_price_id(price_id: str) -> str:
    """
    Get tier code from Stripe price ID.

    Args:
        price_id: Stripe price ID

    Returns:
        Tier code ('starter', 'pro', or 'unknown')
    """
    return STRIPE_PRICE_TO_TIER.get(price_id, "unknown")
```

**使用**:
```python
# api/admin/subscriptions.py
from config import get_tier_from_price_id

price_id = subscription_detail.items.data[0].price.id
tier_code = get_tier_from_price_id(price_id)
plan_name = await tier_service.get_tier_display_name(tier_code)
```

---

## 常量定义 (保持向后兼容)

```python
# domains/user/constants.py
"""User tier constants and configurations."""

# Tier codes (系统内部使用,不可更改)
TIER_FREE = "free"
TIER_STARTER = "starter"
TIER_PRO = "pro"

# Valid tier codes
VALID_TIERS = {TIER_FREE, TIER_STARTER, TIER_PRO}

# Default display names (仅用于 fallback)
DEFAULT_TIER_NAMES = {
    TIER_FREE: "Free Plan",
    TIER_STARTER: "Starter Plan",
    TIER_PRO: "Pro Plan",
}

# Monthly credits by tier
TIER_MONTHLY_CREDITS = {
    TIER_FREE: 0,
    TIER_STARTER: 200,
    TIER_PRO: 500,
}

# Tier levels (用于比较,如降级验证)
TIER_LEVELS = {
    TIER_FREE: 0,
    TIER_STARTER: 1,
    TIER_PRO: 2,
}
```

**使用**:
```python
from domains.user.constants import TIER_STARTER, TIER_MONTHLY_CREDITS

# 判断 tier
if user.tier == TIER_STARTER:
    # ...

# 获取月度积分
credits = TIER_MONTHLY_CREDITS[user.tier]
```

---

## 更新现有代码

### 1. 更新 subscriptions.py

```python
# api/admin/subscriptions.py

# 添加 helper 函数
def get_tier_code_from_price_id(price_id: str) -> str:
    """Get tier code from Stripe price ID."""
    from config import STRIPE_PRICE_TO_TIER
    return STRIPE_PRICE_TO_TIER.get(price_id, "unknown")

# 使用 TierService
@router.post("/subscription/cancel")
async def adm_cancel_subscription(...):
    # ...
    tier_service = TierService(SupabaseTierRepository(db))

    # 获取 tier code
    price_id = subscription_detail.items.data[0].price.id
    tier_code = get_tier_code_from_price_id(price_id)

    # 获取显示名称
    plan_name = await tier_service.get_tier_display_name(tier_code)

    # 记录到日志/审计
    await admin_repo.admin_log_operation(
        admin_id=admin["id"],
        operation_type="subscription_cancel",
        target_user_id=req.user_id,
        details=f"{plan_name} ({'immediate' if req.immediate else 'at period end'})",
        reason=req.reason
    )
```

### 2. 更新 CLAUDE.md

```markdown
# CLAUDE.md

## 用户等级

| 等级代码 | 默认名称 | 月度积分 | 价格 |
|----------|----------|----------|------|
| free | Free Plan | 0 | $0 |
| starter | Starter Plan | 200 | $9.9/月 |
| pro | Pro Plan | 500 | $19.9/月 |

**重要**:
- 等级代码 (`free`/`starter`/`pro`) 是系统内部使用,不可更改
- 显示名称 (Free Plan/Starter Plan/Pro Plan) 可通过 Admin 面板配置
- 月度积分由系统常量定义 (TIER_MONTHLY_CREDITS)
```

---

## 测试

### 单元测试

```python
# tests/domains/test_tier_service.py
import pytest
from domains.user.tier_service import TierService

@pytest.mark.asyncio
async def test_get_tier_display_name():
    """Should return correct tier display name."""
    tier_repo = MockTierRepository()
    tier_service = TierService(tier_repo)

    name = await tier_service.get_tier_display_name("starter")
    assert name == "Starter Plan"

@pytest.mark.asyncio
async def test_tier_cache():
    """Should cache tier configs for 5 minutes."""
    tier_repo = MockTierRepository()
    tier_service = TierService(tier_repo)

    # First call - should hit DB
    name1 = await tier_service.get_tier_display_name("starter")
    assert tier_repo.call_count == 1

    # Second call - should use cache
    name2 = await tier_service.get_tier_display_name("pro")
    assert tier_repo.call_count == 1  # Still 1

    # Same result
    assert name1 == name2 == "Starter Plan"
```

### 集成测试

```python
# tests/api/admin/test_tier_config.py
@pytest.mark.asyncio
async def test_update_tier_display_name():
    """Admin should be able to update tier display name."""
    response = await client.patch(
        "/api/v2/admin/tiers/starter/display-name",
        json={"display_name": "Growth Plan"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    assert response.status_code == 200
    assert response.json()["display_name"] == "Growth Plan"

    # Verify database updated
    tier_config = await tier_repo.get_tier_by_code("starter")
    assert tier_config["display_name"] == "Growth Plan"
```

---

## 文档更新清单

### 后端文档
- [x] `docs/shared/TIER-NAMING-SYSTEM.md` (本文档)
- [ ] `docs/后台业务逻辑说明.md` - 添加 Tier 配置系统说明
- [ ] `CLAUDE.md` - 更新用户等级表,说明可配置性
- [ ] `API_REFERENCE.md` - 添加 Tier 配置 API

### 前端文档
- [ ] `decodables-fe/docs/shared/TIER-NAMING-SYSTEM.md` (复制本文档)
- [ ] `decodables-fe/docs/前端完整开发规范.md` - 添加 Tier 显示规范

### 代码注释
- [ ] 所有硬编码 tier 名称的地方更新为使用 `TierService`
- [ ] 添加注释说明 tier code vs display name 的区别

---

## 总结

| 方面 | Tier Code | Display Name |
|------|-----------|--------------|
| **性质** | 系统内部标识符 | 用户可见名称 |
| **示例** | `starter` | `Starter Plan` |
| **可修改** | ❌ 不可修改 | ✅ Admin 可配置 |
| **存储位置** | 代码常量 | 数据库 `tier_configs` 表 |
| **使用场景** | 业务逻辑,数据库字段 | UI 显示,营销文案 |

**最佳实践**:
- ✅ 业务逻辑使用 **tier code** (`free`/`starter`/`pro`)
- ✅ UI 显示使用 **display name** (从 `TierService` 获取)
- ✅ 新增 tier 时,同时更新代码常量和数据库配置
- ✅ 修改名称只需通过 Admin API,无需改代码

---

最后更新: 2026-01-09
维护人: 后端团队
状态: 设计完成,待实施
