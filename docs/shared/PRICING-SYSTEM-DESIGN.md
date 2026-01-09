# Pricing System Design - 价格配置系统设计

> 版本: 1.0.0
> 作者: Claude + Team
> 日期: 2026-01-09

## 1. 当前问题分析

### 1.1 现状

当前系统的价格配置存在以下问题：

**硬编码问题**:
```python
# domains/identity/constants.py (硬编码)
TIER_MONTHLY_PRICES = {
    TIER_T1: 0.0,
    TIER_T2: 14.9,  # 硬编码,修改需要改代码+重新部署
    TIER_T3: 29.9,
}

# domains/billing/payment_service.py (环境变量)
PRICE_MAP = {
    "credits_100": os.environ.get("STRIPE_PRICE_CREDITS_100"),  # Stripe Price ID
    "starter": os.environ.get("STRIPE_PRICE_SUB_STARTER"),
    "pro": os.environ.get("STRIPE_PRICE_SUB_PRO")
}
```

**问题**:
1. ❌ **价格硬编码**: 修改价格需要改代码 + 重新部署
2. ❌ **现价/原价分离**: 原价用于展示划线价,但没有统一管理
3. ❌ **Stripe Price ID 散落**: 环境变量维护,不同环境需要同步
4. ❌ **历史价格无追踪**: 无法查询历史价格变化记录
5. ❌ **新增档位困难**: 增加新的订阅/积分档位需要多处修改
6. ❌ **价格不一致风险**: 代码、数据库、Stripe 三处不同步

### 1.2 业界最佳实践

参考 Stripe、Shopify、AWS Pricing 等成熟系统：

**核心原则**:
- ✅ **配置驱动**: 所有价格存储在数据库,动态读取
- ✅ **版本管理**: 价格修改不删除旧记录,新增版本
- ✅ **审计追踪**: 记录每次价格变更的时间、原因、操作人
- ✅ **环境隔离**: Dev/Staging/Prod 各自维护 Stripe Price ID 映射
- ✅ **灰度发布**: 支持 A/B 测试,不同用户看到不同价格
- ✅ **向后兼容**: 老用户保持原价,新用户使用新价

---

## 2. 设计方案

### 2.1 数据库设计

#### A. `pricing_plans` 表 - 定价方案主表

存储所有订阅方案和积分包的定价信息。

```sql
CREATE TABLE pricing_plans (
    id SERIAL PRIMARY KEY,

    -- 基础信息
    plan_code VARCHAR(50) UNIQUE NOT NULL,  -- 'tier_t2_monthly', 'credits_500'
    plan_type VARCHAR(20) NOT NULL,         -- 'subscription', 'credits'
    plan_name VARCHAR(100) NOT NULL,        -- 'Starter Plan', '500 Credits Pack'
    description TEXT,

    -- 价格信息 (美分,避免浮点精度问题)
    price_cents INT NOT NULL,               -- 实际收费价格 (cents)
    original_price_cents INT,               -- 原价 (用于展示划线价,可选)
    currency VARCHAR(3) DEFAULT 'USD',

    -- 订阅专用字段
    billing_interval VARCHAR(20),           -- 'month', 'year' (仅订阅)
    tier VARCHAR(10),                       -- 't2', 't3' (仅订阅)
    monthly_credits INT,                    -- 月度积分数 (仅订阅)

    -- 积分包专用字段
    credits_amount INT,                     -- 积分数量 (仅积分包)

    -- Stripe 集成
    stripe_price_id_prod VARCHAR(100),      -- Stripe Price ID (生产环境)
    stripe_price_id_dev VARCHAR(100),       -- Stripe Price ID (开发环境)
    stripe_product_id VARCHAR(100),         -- Stripe Product ID

    -- 状态管理
    is_active BOOLEAN DEFAULT TRUE,         -- 是否激活 (下架旧方案用)
    is_visible BOOLEAN DEFAULT TRUE,        -- 是否在前端展示
    is_featured BOOLEAN DEFAULT FALSE,      -- 是否推荐
    sort_order INT DEFAULT 0,               -- 展示顺序

    -- 版本管理
    version INT DEFAULT 1,                  -- 版本号
    effective_from TIMESTAMPTZ,             -- 生效时间
    effective_until TIMESTAMPTZ,            -- 失效时间 (可选)

    -- 元数据
    metadata JSONB DEFAULT '{}',            -- 额外配置 (如优惠信息)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100),                -- 操作人
    updated_by VARCHAR(100)
);

-- 索引
CREATE INDEX idx_pricing_plans_plan_code ON pricing_plans(plan_code);
CREATE INDEX idx_pricing_plans_is_active ON pricing_plans(is_active);
CREATE INDEX idx_pricing_plans_effective_from ON pricing_plans(effective_from);
```

**设计亮点**:
- ✅ **价格用美分**: 避免浮点数精度问题 (`$14.9` → `1490 cents`)
- ✅ **环境隔离**: dev/prod 各自的 Stripe Price ID
- ✅ **软删除**: `is_active` 下架,`is_visible` 隐藏
- ✅ **版本管理**: 修改价格时新增记录,`version++`
- ✅ **时间生效**: `effective_from` 支持定时调价

#### B. `pricing_history` 表 - 价格变更历史

审计追踪,记录每次价格变更。

```sql
CREATE TABLE pricing_history (
    id SERIAL PRIMARY KEY,
    pricing_plan_id INT NOT NULL REFERENCES pricing_plans(id),

    -- 变更信息
    action VARCHAR(20) NOT NULL,            -- 'create', 'update', 'deactivate'
    old_price_cents INT,                    -- 旧价格
    new_price_cents INT,                    -- 新价格
    change_reason TEXT,                     -- 变更原因

    -- 审计信息
    changed_by VARCHAR(100) NOT NULL,       -- 操作人 (user_id 或 admin_id)
    changed_at TIMESTAMPTZ DEFAULT NOW(),

    -- 快照 (便于审计)
    snapshot JSONB                          -- 完整的 pricing_plan 数据快照
);

CREATE INDEX idx_pricing_history_plan_id ON pricing_history(pricing_plan_id);
CREATE INDEX idx_pricing_history_changed_at ON pricing_history(changed_at DESC);
```

#### C. `user_price_overrides` 表 - 用户级价格覆盖

支持特定用户的定制价格 (如老用户优惠价、企业客户定制价)。

```sql
CREATE TABLE user_price_overrides (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    pricing_plan_id INT NOT NULL REFERENCES pricing_plans(id),

    -- 覆盖价格
    override_price_cents INT NOT NULL,      -- 用户专属价格
    reason TEXT,                            -- 原因 (如 "老用户续费优惠")

    -- 有效期
    valid_from TIMESTAMPTZ DEFAULT NOW(),
    valid_until TIMESTAMPTZ,                -- 可选,永久则为 NULL

    -- 审计
    created_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id, pricing_plan_id)
);

CREATE INDEX idx_user_price_overrides_user_id ON user_price_overrides(user_id);
```

---

### 2.2 配置数据示例

#### 订阅方案

```sql
-- Starter Plan (t2)
INSERT INTO pricing_plans (
    plan_code, plan_type, plan_name, description,
    price_cents, original_price_cents,
    billing_interval, tier, monthly_credits,
    stripe_price_id_prod, stripe_price_id_dev,
    is_active, is_visible, sort_order, version, effective_from
) VALUES (
    'tier_t2_monthly',              -- plan_code
    'subscription',                 -- plan_type
    'Starter Plan',                 -- plan_name
    '适合个人创作者',                -- description
    990,                            -- price_cents ($9.9)
    1490,                           -- original_price_cents ($14.9, 划线价)
    'month',                        -- billing_interval
    't2',                           -- tier
    200,                            -- monthly_credits
    'price_xxx_prod',               -- stripe_price_id_prod
    'price_xxx_dev',                -- stripe_price_id_dev
    TRUE,                           -- is_active
    TRUE,                           -- is_visible
    1,                              -- sort_order
    1,                              -- version
    NOW()                           -- effective_from
);

-- Pro Plan (t3)
INSERT INTO pricing_plans (
    plan_code, plan_type, plan_name, description,
    price_cents, original_price_cents,
    billing_interval, tier, monthly_credits,
    stripe_price_id_prod, stripe_price_id_dev,
    is_active, is_visible, sort_order, version, effective_from
) VALUES (
    'tier_t3_monthly', 'subscription', 'Pro Plan', '专业创作者首选',
    1990, 2990,  -- $19.9 / $29.9
    'month', 't3', 500,
    'price_yyy_prod', 'price_yyy_dev',
    TRUE, TRUE, 2, 1, NOW()
);
```

#### 积分包

```sql
-- 100 Credits Pack
INSERT INTO pricing_plans (
    plan_code, plan_type, plan_name,
    price_cents, original_price_cents,
    credits_amount,
    stripe_price_id_prod, stripe_price_id_dev,
    is_active, is_visible, sort_order, version, effective_from
) VALUES (
    'credits_100', 'credits', '100 Credits Pack',
    299, NULL,  -- $2.99, 无划线价
    100,
    'price_credits_100_prod', 'price_credits_100_dev',
    TRUE, TRUE, 10, 1, NOW()
);

-- 500 Credits Pack (折扣)
INSERT INTO pricing_plans (
    plan_code, plan_type, plan_name,
    price_cents, original_price_cents,
    credits_amount,
    stripe_price_id_prod, stripe_price_id_dev,
    is_active, is_visible, sort_order, version, effective_from,
    metadata
) VALUES (
    'credits_500', 'credits', '500 Credits Pack',
    1349, 1499,  -- $13.49 / $14.99 (9折)
    500,
    'price_credits_500_prod', 'price_credits_500_dev',
    TRUE, TRUE, 11, 1, NOW(),
    '{"discount_percent": 10, "badge": "POPULAR"}'::jsonb
);

-- 2000 Credits Pack (折扣)
INSERT INTO pricing_plans (
    plan_code, plan_type, plan_name,
    price_cents, original_price_cents,
    credits_amount,
    stripe_price_id_prod, stripe_price_id_dev,
    is_active, is_visible, sort_order, version, effective_from,
    metadata
) VALUES (
    'credits_2000', 'credits', '2000 Credits Pack',
    4800, 6000,  -- $48.00 / $60.00 (8折)
    2000,
    'price_credits_2000_prod', 'price_credits_2000_dev',
    TRUE, TRUE, 12, 1, NOW(),
    '{"discount_percent": 20, "badge": "BEST VALUE"}'::jsonb
);
```

---

### 2.3 Service 层设计

#### PricingService - 价格管理服务

**核心职责**:
- 获取当前激活的定价方案
- 根据用户获取价格 (考虑用户级覆盖)
- 创建/更新定价方案 (Admin 操作)
- 查询价格历史

**接口设计**:

```python
class PricingService:
    """价格管理服务"""

    async def get_active_plans(
        self,
        plan_type: Optional[str] = None,  # 'subscription', 'credits'
        visible_only: bool = True
    ) -> List[PricingPlan]:
        """获取当前激活的定价方案列表"""
        pass

    async def get_plan_by_code(
        self,
        plan_code: str,
        user_id: Optional[str] = None  # 考虑用户级覆盖
    ) -> Optional[PricingPlan]:
        """获取指定方案 (考虑用户特殊价格)"""
        pass

    async def get_stripe_price_id(
        self,
        plan_code: str,
        environment: str = "prod"  # 'prod', 'dev'
    ) -> str:
        """获取 Stripe Price ID"""
        pass

    async def get_user_override_price(
        self,
        user_id: str,
        plan_code: str
    ) -> Optional[int]:
        """获取用户专属价格 (如果有)"""
        pass

    async def create_plan(
        self,
        plan_data: Dict[str, Any],
        created_by: str
    ) -> PricingPlan:
        """创建新定价方案 (Admin)"""
        pass

    async def update_plan_price(
        self,
        plan_code: str,
        new_price_cents: int,
        reason: str,
        updated_by: str,
        effective_from: Optional[datetime] = None
    ) -> PricingPlan:
        """更新价格 (新增版本,保留历史)"""
        pass

    async def deactivate_plan(
        self,
        plan_code: str,
        reason: str,
        deactivated_by: str
    ) -> bool:
        """下架方案"""
        pass

    async def get_price_history(
        self,
        plan_code: str
    ) -> List[PricingHistory]:
        """获取价格变更历史"""
        pass

    async def set_user_override(
        self,
        user_id: str,
        plan_code: str,
        override_price_cents: int,
        reason: str,
        created_by: str,
        valid_until: Optional[datetime] = None
    ) -> UserPriceOverride:
        """设置用户专属价格 (Admin)"""
        pass
```

---

### 2.4 迁移策略

#### 阶段 1: 创建表 + 初始化数据

1. 创建 `pricing_plans`, `pricing_history`, `user_price_overrides` 表
2. 从现有配置迁移数据到 `pricing_plans`
3. 保留环境变量作为 fallback (向后兼容)

#### 阶段 2: 更新代码使用 PricingService

1. `payment_service.py` 从 `PricingService` 读取 Stripe Price ID
2. 前端 pricing 页面从 API 获取价格信息
3. `identity.constants.py` 的 `TIER_MONTHLY_PRICES` 标记为 deprecated

#### 阶段 3: 移除旧配置 (可选)

1. 移除 `system_configs` 中的 `STARTER_PLAN_PRICE`, `PRO_PLAN_PRICE`
2. 移除 `constants.py` 中的硬编码价格
3. 环境变量仅保留 Stripe API Key 和 Webhook Secret

---

### 2.5 向后兼容方案

在过渡期间，保持多种配置方式共存：

**优先级顺序**:
```
1. user_price_overrides (用户级覆盖) - 最高优先级
2. pricing_plans (数据库配置) - 推荐方式
3. system_configs (旧配置) - 降级 fallback
4. constants.py (硬编码) - 最终 fallback
```

**代码示例**:
```python
async def get_plan_price(plan_code: str, user_id: Optional[str] = None) -> int:
    """获取价格 (多层 fallback)"""

    # 1. 检查用户专属价格
    if user_id:
        override = await pricing_service.get_user_override_price(user_id, plan_code)
        if override:
            return override

    # 2. 从 pricing_plans 获取
    plan = await pricing_service.get_plan_by_code(plan_code)
    if plan:
        return plan.price_cents

    # 3. fallback to system_configs
    config_key = f"pricing.{plan_code}.price_cents"
    price_str = await config_repo.get_by_key(config_key)
    if price_str:
        return int(price_str)

    # 4. fallback to constants
    from domains.identity.constants import TIER_MONTHLY_PRICES
    if plan_code == "tier_t2_monthly":
        return int(TIER_MONTHLY_PRICES[TIER_T2] * 100)
    elif plan_code == "tier_t3_monthly":
        return int(TIER_MONTHLY_PRICES[TIER_T3] * 100)

    raise ValueError(f"Price not found for plan: {plan_code}")
```

---

## 3. 使用场景

### 3.1 场景 1: 调整 Starter Plan 价格

**需求**: 将 Starter Plan 从 $9.9 调整为 $12.9

**操作** (通过 Admin API):
```python
await pricing_service.update_plan_price(
    plan_code="tier_t2_monthly",
    new_price_cents=1290,  # $12.9
    reason="市场调研后决定调整定价",
    updated_by="admin_user_123",
    effective_from=datetime(2026, 2, 1)  # 2月1日生效
)
```

**效果**:
- ✅ 自动记录到 `pricing_history`
- ✅ 新增 version=2 的记录
- ✅ 老用户保持 $9.9 (通过 `user_price_overrides` 设置)
- ✅ 2月1日后新用户看到 $12.9

### 3.2 场景 2: 新增年付方案

**需求**: 增加 Pro Plan 年付方案,优惠价 $199

**操作**:
```python
await pricing_service.create_plan({
    "plan_code": "tier_t3_yearly",
    "plan_type": "subscription",
    "plan_name": "Pro Plan (Yearly)",
    "price_cents": 19900,  # $199
    "original_price_cents": 23880,  # $19.9 x 12 = $238.8
    "billing_interval": "year",
    "tier": "t3",
    "monthly_credits": 500,
    "stripe_price_id_prod": "price_yearly_prod",
    "stripe_price_id_dev": "price_yearly_dev",
    "is_featured": True,
    "metadata": {"savings": "17% off"}
}, created_by="admin_user_123")
```

**效果**:
- ✅ 无需修改代码
- ✅ 前端自动显示新方案
- ✅ Stripe checkout 自动支持

### 3.3 场景 3: 给特定用户设置优惠价

**需求**: 老用户续费 Pro Plan 时保持 $19.9 原价

**操作**:
```python
await pricing_service.set_user_override(
    user_id="user_xxx",
    plan_code="tier_t3_monthly",
    override_price_cents=1990,  # $19.9
    reason="老用户续费保持原价",
    created_by="admin_user_123",
    valid_until=None  # 永久有效
)
```

---

## 4. 优势总结

### 4.1 对比旧方案

| 方面 | 旧方案 | 新方案 |
|------|--------|--------|
| 价格修改 | 改代码 + 重新部署 | Admin API 动态修改 |
| 历史追踪 | ❌ 无 | ✅ 完整审计日志 |
| 新增档位 | 改多处代码 | 数据库新增一条记录 |
| 用户定价 | ❌ 不支持 | ✅ user_price_overrides |
| A/B 测试 | ❌ 困难 | ✅ metadata + experiments |
| 环境隔离 | 环境变量 | 数据库字段 |
| 原价/现价 | 分离管理 | 统一存储 |

### 4.2 核心收益

**业务灵活性**:
- ✅ 可随时调整价格而无需发版
- ✅ 支持定时调价 (如节假日促销)
- ✅ 老用户保持原价,新用户新价
- ✅ 特定用户定制价格

**技术稳定性**:
- ✅ 数据库为单一数据源 (Single Source of Truth)
- ✅ 价格不一致风险降低
- ✅ 审计追踪完整
- ✅ 向后兼容,平滑迁移

**运营效率**:
- ✅ Admin 可自助调整价格
- ✅ 价格变更有记录可查
- ✅ 支持 A/B 测试验证定价策略

---

## 5. 实施 Checklist

- [ ] 创建 `pricing_plans` 表
- [ ] 创建 `pricing_history` 表
- [ ] 创建 `user_price_overrides` 表
- [ ] 创建 `PricingService` 服务
- [ ] 创建 `PricingRepository` 数据访问层
- [ ] 创建初始化脚本 (导入现有价格)
- [ ] 更新 `payment_service.py` 使用 `PricingService`
- [ ] 创建 Admin API 端点 (CRUD 定价方案)
- [ ] 编写单元测试
- [ ] 编写集成测试
- [ ] 更新 API 文档
- [ ] 前端适配新 API

---

## 6. 参考资料

- Stripe Pricing Best Practices: https://stripe.com/docs/products-prices/pricing-models
- Shopify Price Rules: https://shopify.dev/docs/api/admin-rest/2024-01/resources/pricerule
- AWS Pricing Versioning: https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/price-changes.html

---

*文档由 Claude Code 生成*
