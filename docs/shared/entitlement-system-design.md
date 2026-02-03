# 用户权限与功能控制系统设计

> **版本**: v4.1
> **日期**: 2026-02-03
> **状态**: 设计完成
> **架构**: Entitlement Service + Feature Flag Service + Merge Layer

---

## 一、系统概述

### 1.1 系统职责

本系统统一管理以下四大能力：

| # | 能力 | 说明 | 负责模块 |
|---|------|------|---------|
| 1 | **用户权限管理** | Tier 级别功能权限、数量限制、试用期权限 | EntitlementService |
| 2 | **灰度发布** | 按百分比/用户群逐步放量新功能 | FeatureFlagService |
| 3 | **A/B 实验** | 多变体实验，收集数据做决策 | FeatureFlagService |
| 4 | **运营授权** | 给指定用户授予超出其 Tier 的权限 | EntitlementService (override) |

### 1.2 核心架构原则

**Entitlement vs Feature Flag 分离** (业界最佳实践):

| 维度 | Entitlement | Feature Flag |
|------|-------------|-------------|
| **回答的问题** | 用户有没有**资格**用？ | 功能有没有**上线**？ |
| **本质** | 商业合同 (用户付费就有权用) | 技术开关 (工程团队控制发布) |
| **生命周期** | 长期 (随订阅变化) | 短期 (灰度完成后删除) |
| **管理者** | 产品/运营 (Admin 页面) | 工程团队 (Flag 管理) |

> "Feature flags manage deployment. Entitlements manage access." — LaunchDarkly

### 1.3 相关文档

| 文档 | 说明 |
|------|------|
| [entitlement-permission-matrix.md](./entitlement-permission-matrix.md) | 功能权限矩阵 (**唯一数据源**) |
| [feature-flag-engine.md](./feature-flag-engine.md) | Feature Flag 评估引擎 (数据库+代码实现) |
| [entitlement-ui-spec.md](./entitlement-ui-spec.md) | 前端 UI 交互规范 |

---

## 二、架构设计

### 2.1 系统全景

```
┌────────────────────────────────────────────────────────────┐
│                     后端 (FastAPI)                          │
│                                                            │
│  ┌──────────────────┐    ┌──────────────────┐              │
│  │ EntitlementService│    │FeatureFlagService│              │
│  │                  │    │                  │              │
│  │ • tier 基础权限   │    │ • kill switch    │              │
│  │ • trial 状态计算  │    │ • 灰度 rollout   │              │
│  │ • override 机制   │    │ • A/B 测试       │              │
│  │ • 配额限制        │    │ • prerequisite   │              │
│  └────────┬─────────┘    └────────┬─────────┘              │
│           │                       │                        │
│           ▼                       ▼                        │
│  ┌─────────────────────────────────────────┐               │
│  │       UserFeatureService (Merge 层)      │               │
│  │                                         │               │
│  │  1. 调用 EntitlementService             │               │
│  │  2. 调用 FeatureFlagService             │               │
│  │  3. 按优先级合并结果                     │               │
│  └────────────────┬────────────────────────┘               │
│                   │                                        │
│                   ▼                                        │
│          GET /api/v2/user/features                         │
└────────────────────┬───────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────┐
│                     前端 (Next.js)                          │
│                                                            │
│  ┌──────────────────┐                                      │
│  │useEntitlementStore│ ← 独立 Zustand Store                 │
│  │                  │                                      │
│  │ • features Map   │                                      │
│  │ • quotas Map     │                                      │
│  │ • trialInfo      │                                      │
│  └────────┬─────────┘                                      │
│           │                                                │
│           ▼                                                │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ useFeatureAccess  │  │  <FeatureGate>   │                │
│  │ useQuotaGuard     │  │  (组件)           │                │
│  └──────────────────┘  └──────────────────┘                │
└────────────────────────────────────────────────────────────┘
```

### 2.2 合并优先级 (Merge 规则)

```
Level 0: Kill Switch (Flag disabled)           → 'disabled'  (最高)
Level 1: Entitlement override                  → 'full'
Level 2: Entitlement tier_trial (试用期)        → 'trial'
Level 3: Entitlement tier_base                 → 'full' / 'locked'
Level 4: Flag variant (A/B / 灰度)             → 附加 variant 信息  (最低)
```

**规则**:
- Kill Switch 优先于一切 (功能有安全问题，任何人都不能用)
- Entitlement locked → 直接返回，不走 Flag (没权限就是没权限)
- Entitlement full/trial + Flag variant → 叠加 variant (控制用哪个版本)

### 2.3 数据流示例

**场景 1: t1 用户试用期内访问 AI 功能**
```
1. EntitlementService.evaluate('ai_features')
   → tier_config['ai_features'] = 'trial'
   → trial_info.is_active = true
   → 返回 { access: 'trial', source: 'tier_trial' }

2. FeatureFlagService.evaluate('ai_features')
   → enabled = true, variant = 'v2'

3. Merge
   → { access: 'trial', variant: 'v2', trial_days_remaining: 5 }
```

**场景 2: t1 用户试用过期访问 ZIP 导出**
```
1. EntitlementService.evaluate('zip_export')
   → tier_config['zip_export'] = 'trial'
   → trial_info.is_active = false
   → 返回 { access: 'locked', source: 'tier_trial_expired' }

2. 不调用 FeatureFlagService (Entitlement 已锁定)

3. 返回 { access: 'locked', required_tier: 't3' }
```

---

## 三、后端设计概要

> 详细实现见 [feature-flag-engine.md](./feature-flag-engine.md)

### 3.1 EntitlementService

从现有 TierService (695 行) 增强而来：

| 方法 | 职责 | 数据源 |
|------|------|--------|
| `evaluate_all(user)` | 评估用户所有功能的 Entitlement | tier_config + trial + override |
| `evaluate_feature(user, key)` | 评估单个功能 | 同上 |
| `get_trial_info(user)` | 获取 trial 完整信息 | profiles.created_at + trial.default_days |
| `get_user_overrides(user_id)` | 获取用户的运营授权 | user_feature_overrides 表 |
| `get_quotas(user)` | 获取用户配额 | tier_config + 实际使用量 |

### 3.2 FeatureFlagService

保留现有评估引擎，调整步骤顺序：

```
1. enabled (kill switch)
2. prerequisite flags
3. time_window
4. environment
5. blacklist
6. whitelist ← 提前到 tier 之前
7. allowed_tiers
8. targeting_rules
9. variant_assignment
```

### 3.3 UserFeatureService (Merge 层)

唯一面向前端的出口，合并 Entitlement 和 Flag 结果。

### 3.4 数据库表

| 表 | 用途 | 详见 |
|-----|------|------|
| `feature_flags` | Feature Flag 配置 | feature-flag-engine.md §2.1 |
| `experiment_configs` | A/B 实验配置 | feature-flag-engine.md §2.2 |
| `flag_exposures` | 曝光事件记录 | feature-flag-engine.md §2.3 |
| `user_feature_overrides` | 运营授权 | 本文 §3.5 |

### 3.5 user_feature_overrides 表

```sql
CREATE TABLE IF NOT EXISTS user_feature_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES profiles(user_id),
    feature_key TEXT NOT NULL,
    access_level TEXT NOT NULL DEFAULT 'full' CHECK (access_level IN ('full', 'trial')),
    reason TEXT,                          -- "KOL 合作" / "客服补偿"
    granted_by TEXT,                      -- 授权人 (admin user_id)
    starts_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ,               -- NULL = 永不过期
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, feature_key)
);

CREATE INDEX idx_ufo_user_active ON user_feature_overrides(user_id) WHERE is_active = TRUE;
```

---

## 四、API 设计

### 4.1 核心 API

**`GET /api/v2/user/features`**

请求：需要 JWT 认证

响应示例 (t1 用户，试用期内):

```json
{
  "features": {
    "platform_assets": {
      "access": "trial",
      "source": "tier_trial",
      "metadata": {
        "required_tier": "t2",
        "trial_days_remaining": 5
      }
    },
    "zip_export": {
      "access": "trial",
      "source": "tier_trial",
      "variant": "new_export_v2",
      "metadata": {
        "required_tier": "t3",
        "trial_days_remaining": 5
      }
    },
    "recover_deleted": {
      "access": "locked",
      "source": "tier_base",
      "metadata": {
        "required_tier": "t3"
      }
    }
  },
  "quotas": {
    "projects": { "current": 0, "max": 1, "is_unlimited": false },
    "folders": { "current": 0, "max": 1, "is_unlimited": false },
    "custom_assets": { "current": 0, "max": 10, "is_unlimited": false }
  },
  "trial_info": {
    "is_active": true,
    "days_remaining": 5,
    "duration_days": 7,
    "start_date": "2026-01-29T00:00:00Z",
    "expires_at": "2026-02-05T00:00:00Z"
  }
}
```

### 4.2 API 层 Tier 校验

```python
def require_tier_feature(feature_key: str):
    """API 层 tier 校验 (纵深防御)"""
    async def dependency(
        user = Depends(get_current_user),
        entitlement_service = Depends(get_entitlement_service),
    ):
        result = await entitlement_service.evaluate_feature(user, feature_key)
        if result.access == 'locked':
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "FEATURE_LOCKED",
                    "message": f"Feature '{feature_key}' requires tier {result.required_tier}",
                    "required_tier": result.required_tier,
                }
            )
        return user
    return dependency
```

需补全的端点：

| 端点 | 添加校验 |
|------|---------|
| `POST /tools/ocr` | `require_tier_feature('smart_scan')` |
| `POST /export/zip` | `require_tier_feature('zip_export')` |
| `GET /assets?scope=all` | `require_tier_feature('history_assets')` |

---

## 五、前端设计概要

> UI 交互规范详见 [entitlement-ui-spec.md](./entitlement-ui-spec.md)

### 5.1 useEntitlementStore

```typescript
interface EntitlementState {
  // 核心数据
  features: Map<FeatureKey, FeatureEvaluation>;
  quotas: Map<QuotaKey, QuotaInfo>;
  trialInfo: TrialInfo | null;

  // 元数据
  isLoading: boolean;
  isInitialized: boolean;
  error: Error | null;

  // Actions
  fetchEntitlements: () => Promise<void>;
  getFeatureAccess: (key: FeatureKey) => FeatureAccess;
  getQuota: (key: QuotaKey) => QuotaInfo;
  invalidate: () => void;
}
```

### 5.2 useFeatureAccess Hook

```typescript
function useFeatureAccess(key: FeatureKey) {
  const evaluation = useEntitlementStore(s => s.getFeatureAccess(key));

  return {
    access: evaluation.access,
    isAvailable: evaluation.access === 'full',
    isTrial: evaluation.access === 'trial',
    isLocked: evaluation.access === 'locked',
    isDisabled: evaluation.access === 'disabled',
    variant: evaluation.variant,
    requiredTier: evaluation.metadata?.requiredTier,
    trialDaysRemaining: evaluation.metadata?.trialDaysRemaining,

    checkAndTrigger: (callback?: () => void) => {
      if (evaluation.access === 'full' || evaluation.access === 'trial') {
        callback?.();
      } else if (evaluation.access === 'locked') {
        openUpgradeModal(key);
      }
    },
  };
}
```

### 5.3 useQuotaGuard Hook

```typescript
function useQuotaGuard(type: QuotaType) {
  const quota = useEntitlementStore(s => s.getQuota(type));

  return {
    canCreate: quota.is_unlimited || quota.current < quota.max,
    isAtLimit: !quota.is_unlimited && quota.current >= quota.max,
    current: quota.current,
    max: quota.max,
    isUnlimited: quota.is_unlimited,

    checkAndTrigger: (callback?: () => void) => {
      if (quota.is_unlimited || quota.current < quota.max) {
        callback?.();
      } else {
        openUpgradeModal(`quota_${type}`);
      }
    },
  };
}
```

### 5.4 初始化时序

```
1. GlobalProviders mount
   → configStore.fetchAllConfigs() (系统配置，无需登录)

2. UserStateHandler (Clerk ready)
   → GET /user/me → useUserStore.setUser()
   → entitlementStore.fetchEntitlements() (依赖 JWT)

3. Tier 变化 (用户升级)
   → entitlementStore.invalidate() → 重新 fetch

4. 定时刷新 (每 5 分钟)
   → entitlementStore.fetchEntitlements()
```

### 5.5 降级策略

```typescript
const getFeatureAccess = (key: FeatureKey): FeatureAccess => {
  // Layer 1: 后端 API 结果 (最权威)
  const evaluation = get().features.get(key);
  if (evaluation) return evaluation;

  // Layer 2: TIER_FEATURES_FALLBACK 本地常量 (API 失败时)
  const fallback = TIER_FEATURES_FALLBACK[userTier]?.[key];
  if (fallback !== undefined) {
    return { access: fallback === true ? 'full' : 'locked', source: 'fallback' };
  }

  // Layer 3: 全部锁定 (最保守)
  return { access: 'locked', source: 'default' };
};
```

---

## 六、实施计划

### Phase 0: 数据库准备 (1 天)

| 步骤 | 文件 | 操作 |
|------|------|------|
| 0.1 | `migrations/seed/platform_config_seed.sql` | 添加 tier.t1/t2/t3.features JSON |
| 0.2 | `migrations/seed/platform_config_seed.sql` | 统一 trial.default_days |
| 0.3 | `migrations/v2/01_core_business.sql` | 新建 user_feature_overrides 表 |

### Phase 1: 后端服务 (3 天)

| 步骤 | 文件 | 操作 |
|------|------|------|
| 1.1 | `domains/identity/tier_service.py` | 增强为 EntitlementService |
| 1.2 | `domains/identity/models.py` | 新建 EntitlementResult, TrialInfo, QuotaInfo |
| 1.3 | `domains/identity/override_repository.py` | 新建 Override 仓储 |
| 1.4 | `core/feature_flag/evaluator.py` | 调整步骤顺序 + prerequisite |
| 1.5 | `domains/feature_access/service.py` | 新建 UserFeatureService |
| 1.6 | `api/user/user_features.py` | 新建 GET /api/v2/user/features |
| 1.7 | `dependencies.py` | 新增 require_tier_feature() |

### Phase 2: 前端基础设施 (2 天)

| 步骤 | 文件 | 操作 |
|------|------|------|
| 2.1 | `lib/entitlement/types.ts` | TypeScript 类型定义 |
| 2.2 | `lib/entitlement/api.ts` | API 调用 |
| 2.3 | `lib/entitlement/store.ts` | useEntitlementStore |
| 2.4 | `lib/entitlement/hooks/*.ts` | useFeatureAccess, useQuotaGuard |
| 2.5 | `components/common/FeatureGate.tsx` | FeatureGate 组件 |
| 2.6 | `components/GlobalProviders.tsx` | 触发 fetchEntitlements |

### Phase 3: 消费方迁移 (3 天)

逐文件迁移，旧 hook 保持兼容并标记 @deprecated：

| 文件 | 迁移 |
|------|------|
| `useTierFeature` 消费方 (8 个) | → `useFeatureAccess` |
| `useFeatureFlag` 消费方 (7 个) | → `useFeatureAccess` |
| `isWithinTrialPeriod()` 消费方 | → `useEntitlementStore.trialInfo` |

### Phase 4: 清理与增强 (1 天)

- 删除死代码: `trialUsage`, `incrementTrialUsage()`
- `useTierFeature` 添加 console.warn deprecated
- 补全 API 层 tier 校验

---

## 七、决策记录

| # | 决策 | 选项 | 最终选择 | 理由 |
|---|------|------|---------|------|
| 1 | 试用期天数来源 | 硬编码 / DB 值 | **DB 值** (`trial.default_days`) | Admin 可配，不依赖具体数字 |
| 2 | Trial config key | `trial.default_days` / `trial.duration_days` | **`trial.default_days`** | 删除废弃 key，统一入口 |
| 3 | t1 zip_export 权限 | `false` / `"trial"` | **`"trial"`** | 试用期可体验，到期锁定，提高转化 |
| 4 | t1 history_assets 权限 | `false` / `"trial"` | **`false`** | 功能复杂，试用期不开放 |
| 5 | 前端 Store 位置 | configStore / useUserStore / 独立 | **独立 `useEntitlementStore`** | 职责分离，刷新时机独立，降级策略独立 |
| 6 | parent_flags | 不做 / 做 | **做** | 数据库已预留，AI 功能家族是真实需求，实现成本低 |
| 7 | 架构方案 | 单一引擎 / 增强 TierService / 三层分离 | **三层分离 (方案 A)** | 职责最清晰，未上线无历史包袱，一步到位 |
| 8 | Entitlement vs Flag 分离 | 混合 / 分离 | **分离** | 业界共识，不同生命周期/管理者/变更频率 |
| 9 | 跨 tier A/B 测试 | Flag 提权 / Override | **Override** | Flag 不应授予权限，保持 Entitlement 为唯一权限源 |

---

## 八、风险与缓解

| # | 风险 | 概率 | 影响 | 缓解措施 |
|---|------|:---:|:---:|---------|
| 1 | 新 API 性能瓶颈 | 低 | 中 | EntitlementService 5 分钟缓存 + batch 查询 |
| 2 | 迁移期间行为不一致 | 中 | 低 | Phase 3 修复 trial; Phase 4 逐文件迁移, 旧 hook 继续工作 |
| 3 | useEntitlementStore 初始化时序 | 低 | 中 | isLoading 保护 + TIER_FEATURES_FALLBACK |
| 4 | system_configs 配置错误 | 低 | 高 | EMERGENCY_TIER_CONFIGS 兜底 + Admin 验证 |
| 5 | trial key 迁移遗漏 | 中 | 中 | Phase 0 集中修复, grep 全面扫描 |
| 6 | override 表被滥用 | 低 | 中 | Admin 页面审计日志 + 过期自动清理 |
| 7 | 付费 API 缺少 tier 校验被绕过 | 中 | 高 | Phase 1.7 补全 require_tier_feature() |
| 8 | TIER_FEATURES_FALLBACK 过时 | 低 | 低 | 定期与 system_configs 同步 |
| 9 | evaluator 步骤顺序调整影响现有行为 | 低 | 中 | 当前无 whitelist 数据, 调整无实际影响 |

---

## 九、v2.2 审计发现 (历史参考)

### 9.1 已发现的 11 个 Bug

> 来自 v2.1/v2.2 审计，v3.0 架构需修复

| # | Bug | 严重性 | 影响 | 归属 |
|---|-----|:---:|------|:---:|
| 1 | `is_within_trial` 后端硬编码 `false` | 🔴 HIGH | trial 功能完全失效 | Entitlement |
| 2 | 前端 `isWithinTrialPeriod()` 硬编码 7 天 | 🔴 HIGH | 不可配置 | Entitlement |
| 3 | `setUser()` 丢弃后端 `is_within_trial` | 🔴 HIGH | 后端值被忽略 | 前端 |
| 4 | `TIER_FEATURES` 硬编码 17 字段 | 🟡 MEDIUM | 改权益需发版前端 | Entitlement |
| 5 | trial 天数 5 个来源矛盾 | 🟡 MEDIUM | seed 7天 vs Python 30天 | Entitlement |
| 6 | `TierService.get_trial_duration_days()` 读废弃 key | 🟡 MEDIUM | 实际读到 30 天 | Entitlement |
| 7 | `tierFeatures.ts` 硬编码 '7-day trial' | 🟡 MEDIUM | 文案与实际不一致 | 前端 |
| 8 | evaluator 步骤顺序错误 (whitelist 在 tier 之后) | 🟡 MEDIUM | 白名单用户被 tier 拦截 | Flag |
| 9 | `tier.t1.features` JSON 未入库 seed | 🟡 MEDIUM | TierService 读不到配置 | Entitlement |
| 10 | `trialUsage` / `incrementTrialUsage()` 死代码 | 🟢 LOW | 代码膨胀 | 清理 |
| 11 | `ConfigValueType` 缺少 integer/array/richtext | 🟢 LOW | 类型不匹配 DB schema | 清理 |

### 9.2 API Tier 校验覆盖率

35 个 API Router 审计结果：

| 分类 | 数量 | 说明 |
|------|:---:|------|
| 已有完善 tier 校验 | 8 | ZIP export, marketplace, payment 等 |
| 仅 Service 层校验，API 层无显式保护 | **6** | OCR, PDF Preview, 跨项目历史等 |
| 无需 tier 校验 (只读/公开) | 21 | analytics, articles, themes 等 |

需补全 API 层校验的端点：`tools.py` (OCR, PDF Preview), `user_assets.py`, `resources.py`

---

## 十、system_configs SQL Seed 数据

### 10.1 Tier 功能权限 JSON

```sql
-- Trial 配置 (修复矛盾，删除废弃的 trial.duration_days)
INSERT INTO system_configs (key, value, value_type, config_group, description, is_public, is_active) VALUES
('trial.default_days', '7', 'integer', 'trial', 'Free tier 默认试用期天数 (Admin 可配)', true, true);

-- Tier 功能权限 (从设计文档入库)
INSERT INTO system_configs (key, value, value_type, config_group, description, is_public, is_active) VALUES
('tier.t1.features', '{
  "platform_assets": "trial",
  "vector_tools": "trial",
  "freehand_tools": "trial",
  "clipboard_paste": "trial",
  "ai_features": "trial",
  "smart_scan": "trial",
  "pdf_export": true,
  "zip_export": "trial",
  "publish_paid": "trial",
  "publish_free": "trial",
  "browse_marketplace": "trial",
  "purchase_marketplace": "trial",
  "recover_deleted": false,
  "can_invite_members": false,
  "can_upload_custom_assets": "trial",
  "can_subscribe": true,
  "can_purchase_credits": false
}', 'json', 'tier', 't1 功能权限', true, true),

('tier.t2.features', '{
  "platform_assets": true,
  "vector_tools": true,
  "freehand_tools": true,
  "clipboard_paste": false,
  "ai_features": true,
  "smart_scan": false,
  "pdf_export": true,
  "zip_export": false,
  "publish_paid": false,
  "publish_free": true,
  "browse_marketplace": true,
  "purchase_marketplace": true,
  "recover_deleted": false,
  "can_invite_members": false,
  "can_upload_custom_assets": false,
  "can_subscribe": true,
  "can_purchase_credits": true
}', 'json', 'tier', 't2 功能权限', true, true),

('tier.t3.features', '{
  "platform_assets": true,
  "vector_tools": true,
  "freehand_tools": true,
  "clipboard_paste": true,
  "ai_features": true,
  "smart_scan": true,
  "pdf_export": true,
  "zip_export": true,
  "publish_paid": true,
  "publish_free": true,
  "browse_marketplace": true,
  "purchase_marketplace": true,
  "recover_deleted": true,
  "can_invite_members": true,
  "can_upload_custom_assets": true,
  "can_subscribe": true,
  "can_purchase_credits": true
}', 'json', 'tier', 't3 功能权限', true, true);
```

### 10.2 配置读取优先级

```
1. user_feature_overrides 表 (运营授权，最高优先)
2. system_configs 表 (数据库配置)
3. EMERGENCY_TIER_CONFIGS (代码兜底，仅数据库不可用时)
```

---

## 十一、v2.2 → v3.0 变更记录

| # | v2.2 内容 | v3.0 变更 | 原因 |
|---|----------|----------|------|
| 1 | 单一 UnifiedEvaluator 混合处理 | **拆分为 EntitlementService + FeatureFlagService + UserFeatureService** | 业界 anti-pattern，职责混淆 |
| 2 | userFeatures 放 configStore 或 useUserStore | **独立 useEntitlementStore** | 数据性质不同，刷新时机不同 |
| 3 | 不做 parent_flags | **做** (prerequisite flag) | 数据库预留 + AI 功能家族真实需求 |
| 4 | evaluator 步骤顺序不变 | **whitelist 提前到 tier 之前 + 新增 prerequisite** | 修复白名单被 tier 拦截的 bug |
| 5 | 无 override 机制 | **新增 user_feature_overrides 表** | 支持场景④ (运营授权) |
| 6 | Merge 逻辑在 evaluator 内部 | **显式 Merge 层 (UserFeatureService)** | 逻辑透明，可测试 |
| 7 | trial 配置作为孤立 config | **trial 归入 tier 体系** | 业界: trial 是 Entitlement 的一部分 |
| 8 | 文档标题"Feature Flag 统一架构" | **改为"Entitlement & Feature Flag 双系统架构"** | 反映真实架构 |

---

## 十二、身份层级与权限边界

### 12.1 Authentication vs Authorization

**认证 (Authentication)** 与 **授权 (Authorization)** 是两个独立的层级：

| 层级 | 职责 | 判断依据 | 数据来源 |
|------|------|---------|---------|
| **认证层** | 区分游客/登录用户 | `isSignedIn` | Clerk JWT |
| **授权层** | 区分订阅等级 | `tier` (t1/t2/t3) | 数据库 `profiles` |

```
┌─────────────────────────────────────────────────┐
│            Authentication Layer                  │
│  isSignedIn: false → Guest (游客)               │
│  isSignedIn: true  → Registered User (注册用户) │
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│            Authorization Layer                   │
│  tier: t1 → Free Plan (试用/过期)               │
│  tier: t2 → Starter Plan                        │
│  tier: t3 → Pro Plan                            │
└─────────────────────────────────────────────────┘
```

### 12.2 身份层级完整定义

| 身份 | 认证状态 | 授权层级 | 数据库记录 | 典型场景 |
|------|---------|---------|-----------|---------|
| **游客 (Guest)** | `isSignedIn: false` | N/A | ❌ 无 | Landing 页浏览、查看定价 |
| **Free 用户 (试用中)** | `isSignedIn: true` | `tier: t1` + `isWithinTrialPeriod: true` | ✅ 有 | 新注册用户 7 天内 |
| **Free 用户 (试用过期)** | `isSignedIn: true` | `tier: t1` + `isWithinTrialPeriod: false` | ✅ 有 | 试用期结束未订阅 |
| **Starter 用户** | `isSignedIn: true` | `tier: t2` | ✅ 有 | 付费订阅用户 |
| **Pro 用户** | `isSignedIn: true` | `tier: t3` | ✅ 有 | 高级订阅用户 |

### 12.3 游客功能权限矩阵

| # | 功能 | 游客 | 说明 |
|---|------|:---:|------|
| 1 | 浏览 Landing 页 | ✅ | 公开页面 |
| 2 | 查看 Pricing 弹窗 | ✅ | 展示 Plan 对比，引导注册 |
| 3 | 浏览 Manual 页 | ✅ | 公开文档 |
| 4 | 浏览 Marketplace | ✅ | 公开商城 |
| 5 | 创建项目 | ❌ | 点击跳转登录页 |
| 6 | 进入 Dashboard | ❌ | 需要登录 |
| 7 | 进入编辑器 | ❌ | 需要登录 |
| 8 | 购买订阅/积分 | ❌ | 需要登录 |

### 12.4 前端判断逻辑

```typescript
// useAuth hook
const { isSignedIn, isLoaded } = useAuth();

// 游客判断
const isGuest = isLoaded && !isSignedIn;

// 已登录用户的 tier 判断
const { tier, isWithinTrialPeriod } = useUserStore();
const isFree = tier === 't1';
const isStarter = tier === 't2';
const isPro = tier === 't3';
const isTrialExpired = isFree && !isWithinTrialPeriod?.();
```

### 12.5 UI 组件行为规范

| 组件 | 游客行为 | 登录用户行为 |
|------|---------|-------------|
| **Pricing 弹窗 Header** | 显示 "Choose Your Plan" | 显示当前 Plan + 积分信息 |
| **Free Plan 卡片按钮** | "Sign Up Free" → 跳转登录页 | "Current Plan" (禁用) |
| **Starter/Pro 卡片按钮** | "Get Started" → 跳转登录页 | "Subscribe" → Stripe Checkout |
| **Credits 充值区域** | 不显示 | 显示 (仅登录用户可购买) |
| **Create CTA 按钮** | 跳转登录页 | 打开 CreateProjectModal |

---

## 十三、修订历史

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v4.0 | 2026-02-03 | 初始版本：从 002-entitlement 文档重组 |
| v4.1 | 2026-02-03 | 补充遗漏：决策记录 (9项)、v2.2 审计、风险缓解 (9项)、system_configs SQL、身份层级 |

---

**END OF DOCUMENT**
