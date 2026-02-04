# Tier 配置详情

> 版本: v1.0 | 更新: 2026-02-04 | 来源: 基于 01-permission-matrix.md 权限矩阵定义

## 相关文档

| 文档 | 说明 |
|------|------|
| [README.md](./README.md) | 权限系统总览与导航 |
| [01-permission-matrix.md](./01-permission-matrix.md) | 权限矩阵与功能清单 |

---

## 四、灵活配置系统设计

### 4.1 设计原则

**核心需求**: 除了明确标注"可见和可用性不用控制"的功能外，其他所有功能都应通过后台可配置的权限系统控制。

**不需要配置控制的功能** (硬编码):
| # | 功能 | 原因 |
|---|------|------|
| 31 | Manual/News 页 | 公开文档 |
| 32 | 静态页面 (About/Terms 等) | 法律/品牌页面 |
| 35 | Help 按钮 | 帮助入口 |

**需要配置控制的功能**: 其余 32 个功能点

### 4.2 配置粒度

支持三种控制粒度：

| 粒度 | 配置位置 | 说明 | 使用场景 |
|------|----------|------|---------|
| **全局开关** | `system_configs.feature.{key}.enabled` | 所有用户统一开/关 | 功能下线、运维紧急关闭 |
| **按 Tier 配置** | `system_configs.tier.{tier}.features` | 不同 Tier 不同权限 | 常规权限控制 |
| **用户 Override** | `user_feature_overrides` 表 | 为特定用户开通/关闭功能 | VIP 用户、测试用户、补偿用户、AB 实验 |

### 4.2.1 权限优先级规则 (业界最佳实践)

参考 LaunchDarkly、Split.io、Unleash 等主流 Feature Flag 平台的设计，我们采用以下优先级：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    权限评估优先级 (从高到低)                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Level 1: 全局开关 (Kill Switch)                                        │
│  ├── 配置: feature.{key}.enabled = false                               │
│  ├── 效果: 功能完全下线，任何其他配置无效                                  │
│  ├── 场景: 紧急下线、功能维护、严重 Bug                                   │
│  └── 即使用户有 Override，全局关闭也会生效                                │
│                                                                         │
│  Level 2: 用户级覆盖 (User Override)                                    │
│  ├── 配置: user_feature_overrides 表                                    │
│  ├── 效果: 为特定用户开通/关闭功能，跨 Tier 生效                          │
│  ├── 场景: VIP 用户、Beta 测试、AB 实验、客服补偿                         │
│  └── 仅在全局开关为 true 时生效                                          │
│                                                                         │
│  Level 3: Tier 配置 (Plan-based)                                        │
│  ├── 配置: tier.{tier}.features.{key}                                   │
│  ├── 效果: 按用户订阅等级决定权限                                         │
│  ├── 场景: 常规付费功能控制                                              │
│  └── 仅在无用户 Override 时生效                                          │
│                                                                         │
│  Level 4: 默认值 (Fallback)                                             │
│  ├── 配置: EMERGENCY_TIER_CONFIGS 常量                                  │
│  ├── 效果: 数据库不可用时的兜底                                          │
│  ├── 场景: 网络故障、数据库宕机                                          │
│  └── 仅在以上配置都无法获取时生效                                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**优先级判断流程图**:

```
用户请求功能 X
      │
      ▼
┌─────────────────┐
│ 全局开关是否关闭? │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
   YES       NO
    │         │
    ▼         ▼
 返回       ┌─────────────────────┐
disabled   │ 查询用户 Override     │
           │ (检查 expires_at)    │
           └──────────┬──────────┘
                      │
              ┌───────┴───────┐
              │               │
           有 Override    无 Override
              │               │
              ▼               ▼
         返回 Override   ┌───────────────┐
         值              │ 查询 Tier 配置  │
                        └───────┬───────┘
                                │
                        ┌───────┴───────┐
                        │               │
                     有配置         无配置
                        │               │
                        ▼               ▼
                 返回 Tier 值     返回 Fallback
                 (处理 trial)     默认值
```

**设计原则 (参考业界)**:

| 原则 | 说明 | 参考产品 |
|------|------|---------|
| **Kill Switch 最高** | 全局开关必须能覆盖一切，用于紧急情况 | LaunchDarkly, Split.io |
| **用户级优先于群组** | 个人配置 > 群组/Tier 配置 | Unleash, Flagsmith |
| **显式优先于隐式** | 明确配置的值 > 继承/默认值 | 所有平台 |
| **新配置不影响旧用户** | Override 过期后自动回退到 Tier | LaunchDarkly |

> **用户 Override 使用场景**:
> - **客服补偿**: 为特定 t1 用户开通 Pro 功能
> - **Beta 测试**: 为测试用户开通未上线功能
> - **Bug 隔离**: 临时为某用户关闭有 Bug 的功能
> - **AB 实验**: 跨 Tier 用户验证某个功能 (实验组获得该功能，对照组不变)

### 4.3 配置值类型

| 值 | 说明 | 前端表现 |
|----|------|---------|
| `true` | 完全可用 | 正常按钮 |
| `false` | 不可用 | 按钮 + Lock + Tooltip + 点击弹 UpgradeModal |
| `"trial"` | 试用期可用 | 试用期内正常 + Badge；超期后锁定 |
| `"tier_required"` | 需要特定 Tier | 页面级拦截，提示升级 |

### 4.4 数据库表设计

#### 4.4.1 system_configs 表 (全局配置)

```sql
-- 1. 功能全局开关 (运维控制)
INSERT INTO system_configs (key, value, value_type, config_group, description) VALUES
('feature.platform_assets.enabled', 'true', 'boolean', 'feature', '平台素材全局开关'),
('feature.vector_tools.enabled', 'true', 'boolean', 'feature', '矢量图工具全局开关'),
('feature.ai_features.enabled', 'true', 'boolean', 'feature', 'AI 功能全局开关');

-- 2. Tier 功能权限 (产品配置)
INSERT INTO system_configs (key, value, value_type, config_group) VALUES
('tier.t1.features', '{
  "platform_assets": true,
  "vector_tools": true,
  "freehand_tools": true,
  "clipboard_paste": "trial",
  "ai_features": "trial",
  "smart_scan": "trial",
  "pdf_export": true,
  "pdf_print": true,
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
}', 'json', 'tier'),

('tier.t2.features', '{...}', 'json', 'tier'),
('tier.t3.features', '{...}', 'json', 'tier');

-- 3. 页面访问控制 (按 Tier 限制)
INSERT INTO system_configs (key, value, value_type, config_group, description) VALUES
('page.marketplace.min_tier', 't1', 'text', 'page', 'Marketplace 页最低 Tier 要求'),
('page.dashboard.min_tier', 't1', 'text', 'page', 'Dashboard 页最低 Tier 要求');

-- 4. Trial 配置
INSERT INTO system_configs (key, value, value_type, config_group) VALUES
('trial.default_days', '7', 'integer', 'trial');
```

#### 4.4.2 user_feature_overrides 表 (用户级覆盖)

为特定用户开通/关闭功能，优先级高于 Tier 配置：

```sql
-- 用户功能覆盖表
CREATE TABLE user_feature_overrides (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  feature_key TEXT NOT NULL,           -- 功能 Key, 如 'smart_scan', 'ai_features'
  override_value TEXT NOT NULL,        -- 覆盖值: 'true' | 'false' | 'trial'
  reason TEXT,                         -- 覆盖原因 (运营记录)
  expires_at TIMESTAMPTZ,              -- 过期时间 (可选, NULL=永久)
  created_by UUID,                     -- 操作人 (Admin user_id)
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, feature_key)
);

-- 索引
CREATE INDEX idx_user_feature_overrides_user_id ON user_feature_overrides(user_id);
CREATE INDEX idx_user_feature_overrides_expires ON user_feature_overrides(expires_at) WHERE expires_at IS NOT NULL;
```

#### 4.4.3 user_feature_override_logs 表 (审计日志)

记录 user_feature_overrides 的所有变更：

```sql
-- 用户功能覆盖审计日志表
CREATE TABLE user_feature_override_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  override_id UUID REFERENCES user_feature_overrides(id) ON DELETE SET NULL,
  user_id TEXT NOT NULL,                 -- 被操作用户
  feature_key TEXT NOT NULL,             -- 功能 Key
  action TEXT NOT NULL,                  -- 操作类型: 'created' | 'updated' | 'deleted' | 'expired'
  old_value TEXT,                        -- 变更前的值
  new_value TEXT,                        -- 变更后的值
  reason TEXT,                           -- 变更原因
  changed_by TEXT NOT NULL,              -- 操作人 (Admin user_id 或 'system')
  changed_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_ufo_logs_user_id ON user_feature_override_logs(user_id);
CREATE INDEX idx_ufo_logs_changed_at ON user_feature_override_logs(changed_at DESC);
CREATE INDEX idx_ufo_logs_feature_key ON user_feature_override_logs(feature_key);
```

**审计操作类型**:

| action | 说明 | 触发场景 |
|--------|------|---------|
| `created` | 创建 Override | Admin 为用户开通功能 |
| `updated` | 更新 Override | 修改 override_value 或 expires_at |
| `deleted` | 删除 Override | Admin 手动删除或实验结束清理 |
| `expired` | 自动过期 | 定时任务检测 expires_at 到期 |

**使用示例**:

```sql
-- 场景 1: 为 t1 用户开通 Smart Scan (永久)
INSERT INTO user_feature_overrides (user_id, feature_key, override_value, reason, created_by)
VALUES ('user_abc123', 'smart_scan', 'true', '客服补偿 - 工单 #12345', 'admin_user_id');

-- 场景 2: 为 Beta 测试用户开通 AI 功能 (30 天)
INSERT INTO user_feature_overrides (user_id, feature_key, override_value, reason, expires_at, created_by)
VALUES ('user_beta001', 'ai_features', 'true', 'Beta 测试计划', NOW() + INTERVAL '30 days', 'admin_user_id');

-- 场景 3: 临时关闭某用户的有 Bug 功能
INSERT INTO user_feature_overrides (user_id, feature_key, override_value, reason, created_by)
VALUES ('user_xyz789', 'zip_export', 'false', '该用户遇到导出 Bug, 临时关闭', 'admin_user_id');

-- 场景 4: AB 实验 - 让 t1 用户也能使用 AI 功能 (实验组)
-- 实验组用户批量添加 override
INSERT INTO user_feature_overrides (user_id, feature_key, override_value, reason, expires_at, created_by)
VALUES
  ('user_exp001', 'ai_features', 'true', 'AB实验#EXP-2026-001 实验组', NOW() + INTERVAL '14 days', 'admin_user_id'),
  ('user_exp002', 'ai_features', 'true', 'AB实验#EXP-2026-001 实验组', NOW() + INTERVAL '14 days', 'admin_user_id');
-- 对照组用户不添加 override，按原有 Tier 权限
```

**AB 实验与 user_feature_overrides 的配合**:

```
┌─────────────────────────────────────────────────────────────┐
│ AB 实验: 验证 AI 功能对 t1 用户的转化效果                      │
├─────────────────────────────────────────────────────────────┤
│ 实验组 (Treatment):                                          │
│   - 随机选取 1000 个 t1 用户                                  │
│   - 添加 user_feature_overrides: ai_features = true          │
│   - 这些用户即使是 t1，也能使用 AI 功能                        │
│                                                             │
│ 对照组 (Control):                                            │
│   - 随机选取 1000 个 t1 用户                                  │
│   - 不添加 override，按 Tier 配置: ai_features = "trial"      │
│   - 试用期内可用，超出后锁定                                    │
├─────────────────────────────────────────────────────────────┤
│ 实验结束后:                                                   │
│   - 删除 user_feature_overrides 中该实验的记录                 │
│   - 或设置 expires_at 自动过期                                │
└─────────────────────────────────────────────────────────────┘
```

### 4.5 配置读取优先级

```
权限判断流程:
┌──────────────────────────────────────────────────────────────┐
│ 1. 检查全局开关 (feature.{key}.enabled)                        │
│    └─ false → 返回 disabled (功能下线，任何 override 无效)     │
│                                                              │
│ 2. 检查用户 Override (user_feature_overrides 表)              │
│    ├─ 检查是否过期 (expires_at > NOW() 或 NULL)               │
│    └─ 有有效 override → 返回 override 值                       │
│                                                              │
│ 3. 检查 Tier 配置 (tier.{tier}.features.{key})                │
│    └─ "trial" 时需结合 isWithinTrialPeriod 判断               │
│                                                              │
│ 4. 返回默认值 (EMERGENCY_TIER_CONFIGS)                        │
│    └─ 仅在数据库不可用时使用                                    │
└──────────────────────────────────────────────────────────────┘
```

**后端伪代码**:

```python
async def check_feature_access(user_id: str, tier: str, feature_key: str) -> FeatureAccess:
    # 1. 全局开关检查
    global_enabled = await get_config(f"feature.{feature_key}.enabled")
    if global_enabled == "false":
        return FeatureAccess(status="disabled", reason="Feature is globally disabled")

    # 2. 用户 Override 检查
    override = await db.fetch_one("""
        SELECT override_value FROM user_feature_overrides
        WHERE user_id = $1 AND feature_key = $2
          AND (expires_at IS NULL OR expires_at > NOW())
    """, user_id, feature_key)

    if override:
        return FeatureAccess(
            status="override",
            value=override.override_value,
            reason="User-level override"
        )

    # 3. Tier 配置检查
    tier_features = await get_config(f"tier.{tier}.features")
    feature_value = tier_features.get(feature_key, False)

    if feature_value == "trial":
        is_in_trial = await check_trial_period(user_id)
        return FeatureAccess(
            status="trial" if is_in_trial else "locked",
            value=is_in_trial
        )

    return FeatureAccess(status="tier", value=feature_value)
```

### 4.6 配置同步机制

**业界最佳实践对比**:

| 方案 | 代表产品 | 实时性 | 复杂度 | 成本 |
|------|----------|:------:|:------:|:----:|
| 页面加载时获取 | Notion, Figma | 低 | 低 | 低 |
| 定时轮询 (5min) | Slack, Linear | 中 | 中 | 中 |
| WebSocket 推送 | Discord | 高 | 高 | 高 |
| 版本号对比 | LaunchDarkly | 高 | 中 | 中 |

**推荐方案**: 页面加载获取 + 5分钟轮询

```typescript
// useEntitlementStore.ts
const REFRESH_INTERVAL = 5 * 60 * 1000; // 5 分钟

export const useEntitlementStore = create((set, get) => ({
  features: null,
  lastFetchedAt: null,

  // 页面加载时调用
  fetchFeatures: async () => {
    const res = await api.get('/user/features');
    set({ features: res.data, lastFetchedAt: Date.now() });
  },

  // 检查是否需要刷新
  refreshIfStale: async () => {
    const { lastFetchedAt } = get();
    if (!lastFetchedAt || Date.now() - lastFetchedAt > REFRESH_INTERVAL) {
      await get().fetchFeatures();
    }
  },
}));
```

### 4.7 页面访问控制

支持按 Tier 限制页面访问：

```typescript
// middleware.ts 或 路由守卫
const PAGE_TIER_REQUIREMENTS: Record<string, string> = {
  '/marketplace': 't1',   // 当前: t1 可访问
  '/dashboard': 't1',
  '/create': 't1',
  // 未来可调整为:
  // '/marketplace': 't2', // 需要 Starter 才能访问
};

function checkPageAccess(pathname: string, userTier: string): 'allow' | 'login' | 'upgrade' {
  const minTier = PAGE_TIER_REQUIREMENTS[pathname];

  if (!minTier) return 'allow';  // 无限制

  if (!isSignedIn) return 'login';  // 游客 → 登录页

  if (compareTier(userTier, minTier) < 0) return 'upgrade';  // Tier 不足 → 升级提示

  return 'allow';
}

/**
 * Tier 比较函数
 * @returns 负数=userTier低于minTier, 0=相等, 正数=userTier高于minTier
 */
function compareTier(userTier: string, minTier: string): number {
  const TIER_ORDER: Record<string, number> = {
    't1': 1,
    't2': 2,
    't3': 3,
    't4': 4,
  };
  const userLevel = TIER_ORDER[userTier] ?? 0;
  const minLevel = TIER_ORDER[minTier] ?? 0;
  return userLevel - minLevel;
}
```

---

## 六、前端常量定义

### 6.1 TIER_FEATURES_FALLBACK (降级常量)

当 API 失败时使用的本地 fallback 常量：

```typescript
// lib/entitlement/constants.ts

/**
 * 降级常量 - API 失败时使用
 * 此常量是数据库不可用时的兜底值
 */
export const TIER_FEATURES_FALLBACK: Record<string, Record<string, boolean | string>> = {
  t1: {
    platform_assets: true,     // 当前全开放
    vector_tools: true,        // 当前全开放
    freehand_tools: true,      // 当前全开放
    clipboard_paste: false,    // trial 超出后锁定
    ai_features: false,        // trial 超出后锁定
    smart_scan: false,         // trial 超出后锁定
    pdf_export: true,          // 永久可用
    pdf_print: true,           // 永久可用
    zip_export: false,         // trial 超出后锁定
    publish_paid: false,       // trial 超出后锁定
    publish_free: false,       // trial 超出后锁定
    browse_marketplace: false, // trial 超出后锁定
    purchase_marketplace: false,
    recover_deleted: false,
    can_invite_members: false,
    can_upload_custom_assets: false,
    can_subscribe: true,
    can_purchase_credits: false,
  },
  t2: {
    platform_assets: true,
    vector_tools: true,
    freehand_tools: true,
    clipboard_paste: false,
    ai_features: true,
    smart_scan: false,
    pdf_export: true,
    pdf_print: true,
    zip_export: false,
    publish_paid: false,
    publish_free: true,
    browse_marketplace: true,
    purchase_marketplace: true,
    recover_deleted: false,
    can_invite_members: false,
    can_upload_custom_assets: false,
    can_subscribe: true,
    can_purchase_credits: true,
  },
  t3: {
    platform_assets: true,
    vector_tools: true,
    freehand_tools: true,
    clipboard_paste: true,
    ai_features: true,
    smart_scan: true,
    pdf_export: true,
    pdf_print: true,
    zip_export: true,
    publish_paid: true,
    publish_free: true,
    browse_marketplace: true,
    purchase_marketplace: true,
    recover_deleted: true,
    can_invite_members: true,
    can_upload_custom_assets: true,
    can_subscribe: true,
    can_purchase_credits: true,
  },
  t4: {
    platform_assets: true,
    vector_tools: true,
    freehand_tools: true,
    clipboard_paste: true,
    ai_features: true,
    smart_scan: true,
    pdf_export: true,
    pdf_print: true,
    zip_export: true,
    publish_paid: true,
    publish_free: true,
    browse_marketplace: true,
    purchase_marketplace: true,
    recover_deleted: true,
    can_invite_members: true,
    can_upload_custom_assets: true,
    can_subscribe: true,
    can_purchase_credits: true,
  },
};
```

### 6.2 EMERGENCY_TIER_CONFIGS (紧急兜底常量)

数据库不可用时的紧急兜底配置：

```typescript
// lib/entitlement/constants.ts

/**
 * 紧急兜底配置 - 仅在数据库完全不可用时使用
 *
 * 设计原则：
 * - 付费功能默认锁定（避免损失）
 * - 基础功能默认开放（避免用户完全无法使用）
 * - 此配置应与 system_configs 保持同步
 */
export const EMERGENCY_TIER_CONFIGS: Record<string, {
  displayName: string;
  monthlyCredits: number;
  maxProjects: number;
  maxFolders: number;
  maxWorkspaces: number;
  maxCustomAssets: number;
  features: Record<string, boolean | string>;
}> = {
  t1: {
    displayName: 'Free Plan',
    monthlyCredits: 0,
    maxProjects: 1,
    maxFolders: 1,
    maxWorkspaces: 1,
    maxCustomAssets: 10,
    features: TIER_FEATURES_FALLBACK.t1,
  },
  t2: {
    displayName: 'Starter Plan',
    monthlyCredits: 100,
    maxProjects: 10,
    maxFolders: 20,
    maxWorkspaces: 1,
    maxCustomAssets: 0,
    features: TIER_FEATURES_FALLBACK.t2,
  },
  t3: {
    displayName: 'Pro Plan',
    monthlyCredits: 200,
    maxProjects: -1,  // unlimited
    maxFolders: 200,
    maxWorkspaces: -1,  // unlimited
    maxCustomAssets: -1,  // unlimited
    features: TIER_FEATURES_FALLBACK.t3,
  },
  t4: {
    displayName: 'Enterprise',
    monthlyCredits: 500,
    maxProjects: -1,  // unlimited
    maxFolders: -1,   // unlimited
    maxWorkspaces: -1,  // unlimited
    maxCustomAssets: -1,  // unlimited
    features: TIER_FEATURES_FALLBACK.t4,
  },
};
```

### 6.3 LEGACY_KEY_MAP (旧 key 映射)

旧 hook 迁移到新 hook 时的 key 映射：

```typescript
// lib/entitlement/constants.ts

/**
 * 旧 key 映射表
 * useTierFeature 的 FEATURES enum → 新 FeatureKey
 * useFeatureFlag 的 key → 新 FeatureKey
 */
export const LEGACY_KEY_MAP: Record<string, string> = {
  // useTierFeature 的旧 FEATURES enum → 新 FeatureKey
  'PLATFORM_ASSETS': 'platform_assets',
  'VECTOR_TOOLS': 'vector_tools',
  'FREEHAND_TOOLS': 'freehand_tools',
  'SMART_SCAN': 'smart_scan',
  'ZIP_EXPORT': 'zip_export',
  'PROJECT_TEMPLATES': 'ai_features',
  'AI_FEATURES': 'ai_features',
  'PDF_PRINT': 'pdf_print',
  'PDF_EXPORT': 'pdf_export',       // 统一命名
  'EXPORT_PDF': 'pdf_export',       // 旧命名兼容
  'EXPORT_ZIP': 'zip_export',       // 旧命名兼容
  'PREMIUM_STICKERS': 'platform_assets',

  // useFeatureFlag 的旧 key → 新 FeatureKey
  'ocr': 'smart_scan',
  'ai_generation': 'ai_features',
  'zip_export': 'zip_export',
  'smart_scan': 'smart_scan',
  'clipboard_paste': 'clipboard_paste',
  'pdf_download': 'pdf_export',     // 旧命名兼容
};

/**
 * 将旧 key 转换为新 key
 */
export function normalizeFeatureKey(key: string): string {
  return LEGACY_KEY_MAP[key] || key;
}
```

### 6.4 完整 Tier Features JSON 配置

各 Tier 的完整功能权限配置 (与 system_configs 保持同步)：

**t1 (Free Plan)**:
```json
{
  "platform_assets": true,
  "vector_tools": true,
  "freehand_tools": true,
  "clipboard_paste": "trial",
  "ai_features": "trial",
  "smart_scan": "trial",
  "pdf_export": true,
  "pdf_print": true,
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
}
```

**t2 (Starter Plan)**:
```json
{
  "platform_assets": true,
  "vector_tools": true,
  "freehand_tools": true,
  "clipboard_paste": false,
  "ai_features": true,
  "smart_scan": false,
  "pdf_export": true,
  "pdf_print": true,
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
}
```

**t3 (Pro Plan)**:
```json
{
  "platform_assets": true,
  "vector_tools": true,
  "freehand_tools": true,
  "clipboard_paste": true,
  "ai_features": true,
  "smart_scan": true,
  "pdf_export": true,
  "pdf_print": true,
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
}
```

**t4 (Enterprise)**:
```json
{
  "platform_assets": true,
  "vector_tools": true,
  "freehand_tools": true,
  "clipboard_paste": true,
  "ai_features": true,
  "smart_scan": true,
  "pdf_export": true,
  "pdf_print": true,
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
}
```
