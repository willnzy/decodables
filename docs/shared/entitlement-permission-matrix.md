# 功能权限矩阵

> **版本**: v1.4
> **日期**: 2026-02-04
> **状态**: 产品确认
> **说明**: 本文档是功能权限的**唯一数据源**，后端配置和前端实现都以此为准

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [entitlement-system-design.md](./entitlement-system-design.md) | 系统架构总览 |
| [feature-flag-engine.md](./feature-flag-engine.md) | Feature Flag 评估引擎 |
| [entitlement-ui-spec.md](./entitlement-ui-spec.md) | 前端 UI 交互规范 |

---

## 一、用户身份层级

### 1.1 认证层 (Authentication)

| 身份 | 判断依据 | 数据库记录 |
|------|---------|-----------|
| **游客 (Guest)** | `isSignedIn: false` | 无 |
| **注册用户** | `isSignedIn: true` | profiles 表 |

### 1.2 授权层 (Authorization) — 仅注册用户

| Tier | 代码 | 显示名称 | 月度积分 | 价格 |
|------|------|---------|:---:|------|
| Free | `t1` | Free Plan | 0 | $0 |
| Starter | `t2` | Starter Plan | 100 | $6.9/月 |
| Pro | `t3` | Pro Plan | 200 | $9.9/月 |
| Enterprise | `t4` | Enterprise | 500 | 待定 |

### 1.3 试用期 (Trial)

- **适用对象**: 仅 t1 用户
- **默认天数**: 7 天 (可通过 Admin 配置)
- **计算方式**: `当前时间 - 注册时间 ≤ trial_days`
- **配置 Key**: `trial.default_days`

---

## 二、完整功能权限矩阵

> **权限值说明**:
> - `YES` = 完全可用
> - `NO` = 不可用 (功能可见但带锁，点击后弹升级窗口)
> - `trial` = 试用期内可用，超出试用期后变为 NO
> - 数字 = 数量限制 (`unlimited` = 无限制)

### 2.1 资源数量限制 (Quota)

| # | 功能 | Key | 游客 | t1 试用期内 | t1 超出试用期 | t2 | t3 | 控制方式 |
|---|------|-----|:---:|:---:|:---:|:---:|:---:|---------|
| 1 | Workspace 最大数量 | `quota.max_workspaces` | 0 | 1 | 1 | 1 | unlimited | - |
| 2 | 邀请成员加入 Workspace | `feature.can_invite_members` | NO | NO | NO | NO | YES | Member管理入口控制 |
| 3 | 文件夹最大数量 | `quota.max_folders` | 0 | 1 | 1 | 20/Account | 200/Account | New Folder按钮控制 |
| 4 | 项目最大数量 | `quota.max_projects` | 0 | 1 | 1 | 10/Account | unlimited | 新建/复制项目按钮控制 |
| 5 | 自定义素材上传 | `feature.can_upload_custom_assets` | NO | YES | NO | NO | YES | 上传素材入口按钮控制 |
| 6 | 自定义素材最大数量 | `quota.max_custom_assets` | 0 | 10 | 0 | 50/Account | unlimited | 上传素材入口按钮控制 |

### 2.2 编辑器功能 (Editor)

| # | 功能 | Key | 游客 | t1 试用期内 | t1 超出试用期 | t2 | t3 | 控制方式 |
|---|------|-----|:---:|:---:|:---:|:---:|:---:|---------|
| 7 | 使用平台素材 | `feature.platform_assets` | YES | YES | YES | YES | YES | 能进入到项目编辑页面,就都可见可用 |
| 8 | 矢量图工具 | `feature.vector_tools` | YES | YES | YES | YES | YES | 能进入到项目编辑页面,就都可见可用 |
| 9 | 画笔工具 | `feature.freehand_tools` | YES | YES | YES | YES | YES | 能进入到项目编辑页面,就都可见可用 |
| 10 | Page 中剪贴板粘贴 | `feature.clipboard_paste` | NO | YES | NO | NO | YES | 右键菜单+快捷键控制 |
| 11 | AI 生成素材 | `feature.ai_generate_assets` | NO | YES | NO | YES | YES | AI入口按钮控制 |
| 12 | AI 生成 Page | `feature.ai_generate_page` | NO | YES | NO | YES | YES | AI入口按钮控制 |
| 13 | 图片识别并生成 Page (Smart Scan) | `feature.smart_scan` | NO | YES | NO | NO | YES | Smart Scan入口控制 |

> **注**: 第 7-9 行当前配置为所有用户可用 (包括游客)，能进入编辑页面即可使用。

### 2.3 导出功能 (Export)

| # | 功能 | Key | 游客 | t1 试用期内 | t1 超出试用期 | t2 | t3 | 控制方式 |
|---|------|-----|:---:|:---:|:---:|:---:|:---:|---------|
| 14 | 8-Page PDF 打印 | `feature.pdf_print` | NO | YES | YES | YES | YES | PDF打印按钮控制 |
| 15 | 8-Page PDF 下载 | `feature.pdf_download` | NO | YES | YES | YES | YES | PDF下载按钮控制 |
| 16 | PDF + 每个页面图片下载 (ZIP) | `feature.zip_export` | NO | YES | NO | NO | YES | ZIP下载按钮控制 |

### 2.4 商城功能 (Marketplace)

| # | 功能 | Key | 游客 | t1 试用期内 | t1 超出试用期 | t2 | t3 | 控制方式 |
|---|------|-----|:---:|:---:|:---:|:---:|:---:|---------|
| 17 | 发布付费项目/素材到商城 | `feature.publish_paid` | NO | YES | NO | NO | YES | Publish按钮+Credits输入控制 |
| 18 | 发布免费项目/素材到商城 | `feature.publish_free` | NO | YES | NO | YES | YES | Publish按钮控制 |
| 19 | 浏览商城 | `feature.browse_marketplace` | NO | YES | NO | YES | YES | Marketplace入口+路由拦截 |
| 20 | 购买商城内的项目或素材 | `feature.purchase_marketplace` | NO | YES | NO | YES | YES | 卡片购买按钮控制 |

### 2.5 数据恢复 (Recovery)

| # | 功能 | Key | 游客 | t1 试用期内 | t1 超出试用期 | t2 | t3 | 控制方式 |
|---|------|-----|:---:|:---:|:---:|:---:|:---:|---------|
| 21 | 30天内恢复已删除的 Workspace/项目/素材 | `feature.recover_deleted` | NO | NO | NO | NO | YES | Trash中恢复按钮控制 |

### 2.6 订阅与支付 (Payment)

| # | 功能 | Key | 游客 | t1 试用期内 | t1 超出试用期 | t2 | t3 | 控制方式 |
|---|------|-----|:---:|:---:|:---:|:---:|:---:|---------|
| 22 | 订阅 Plan | `feature.can_subscribe` | NO | YES | YES | YES | YES | Pricing按钮、胶囊按钮、升级提示、首页pricing区域 |
| 23 | 购买 Credits | `feature.can_purchase_credits` | NO | NO | NO | YES | YES | Pricing按钮、胶囊按钮、Credits购买提示、首页pricing区域 |

### 2.7 页面访问控制 (Page Access)

| # | 页面 | 游客 | t1 | t2 | t3 | 控制方式 |
|---|------|:---:|:---:|:---:|:---:|---------|
| 24 | Landing 页 | 可见 (CTA→登录) | 可见 | 可见 | 可见 | 页面本身无需控制，只需控制页面上的按钮 |
| 25 | Marketplace 页 | 跳登录注册页 | 可见 | 可见 | 可见 | 路由拦截：游客→登录注册页；可返回首页 |
| 26 | Dashboard 页 | 跳登录注册页 | 可见 | 可见 | 可见 | 路由拦截：游客→登录注册页；可返回首页 |
| 27 | Create 页 (编辑器) | 跳登录注册页 | 可见 | 可见 | 可见 | 路由拦截：游客→登录注册页；可返回首页 |
| 28 | Profile 页 | 跳登录注册页 | 可见 | 可见 | 可见 | 路由拦截：游客→登录注册页；可返回首页 |
| 29 | Notification 页 | 跳登录注册页 | 可见 | 可见 | 可见 | 路由拦截：游客→登录注册页；可返回首页 |
| 30 | Transaction History 页 | 跳登录注册页 | 可见 | 可见 | 可见 | 路由拦截：游客→登录注册页；可返回首页 |
| 31 | Manual/News 页 | 可见 | 可见 | 可见 | 可见 | ⚪ **无需控制** |
| 32 | 静态页面 (Contact Us/About Us/Privacy Policy/Terms of Service/Billing Policy/Marketplace Guidelines) | 可见 | 可见 | 可见 | 可见 | ⚪ **无需控制** |

> **路由拦截规则**:
> - **游客**直接访问受保护页面 URL 时 → 展示登录注册页面，可返回首页
> - **已登录用户**直接打开页面路径 → 提示用户升级订阅 Plan，可返回首页

### 2.8 UI 组件 (Components)

| # | 组件 | 游客 | t1 | t2 | t3 | 控制方式 |
|---|------|:---:|:---:|:---:|:---:|---------|
| 33 | Pricing 按钮 | 弹窗 | 弹窗 | 弹窗 | 弹窗 | 根据登录状态和 tier 层级展示响应内容 |
| 34 | CTA 按钮 | 跳登录注册页 | 可用 | 可用 | 可用 | 根据登录状态和 tier 层级展示响应内容 |
| 35 | Help 按钮 | 可用 | 可用 | 可用 | 可用 | ⚪ **无需控制** |

---

## 三、功能 Key 映射表

> 统一 PRD 功能名 → 后端 FeatureKey → 前端 FEATURES 常量

| # | PRD 功能名 | 后端 FeatureKey | 前端 FEATURES | 当前代码状态 |
|---|-----------|----------------|--------------|-------------|
| 7 | 使用平台素材 | `platform_assets` | `PLATFORM_ASSETS` | ❌ 需新增 |
| 8 | 矢量图工具 | `vector_tools` | `VECTOR_TOOLS` | ❌ 需新增 |
| 9 | 画笔工具 | `freehand_tools` | `FREEHAND_TOOLS` | ❌ 需新增 |
| 10 | 剪贴板粘贴 | `clipboard_paste` | `CLIPBOARD_PASTE` | ⚠️ 后端有，前端无 |
| 11 | AI 生成素材 | `ai_features` | `AI_FEATURES` | ✅ 有 |
| 12 | AI 生成 Page | `ai_features` | `AI_FEATURES` | ✅ 复用 |
| 13 | Smart Scan | `smart_scan` | `SMART_SCAN` | ✅ 有 |
| 14 | PDF 打印 | `pdf_print` | `PDF_PRINT` | ✅ 有 |
| 15 | PDF 下载 | `pdf_export` | `EXPORT_PDF` | ✅ 有 |
| 16 | ZIP 导出 | `zip_export` | `EXPORT_ZIP` | ✅ 有 |
| 17 | 发布付费 | `publish_paid` | `PUBLISH_PAID` | ❌ 需新增 |
| 18 | 发布免费 | `publish_free` | `PUBLISH_FREE` | ❌ 需新增 |
| 19 | 浏览商城 | `browse_marketplace` | `BROWSE_MARKETPLACE` | ⚠️ 后端有，前端无 |
| 20 | 购买商城 | `purchase_marketplace` | `PURCHASE_MARKETPLACE` | ⚠️ 后端有，前端无 |
| 21 | 30天恢复 | `recover_deleted` | `RECOVER_DELETED` | ❌ 需新增 |
| 22 | 订阅 Plan | `can_subscribe` | `CAN_SUBSCRIBE` | ✅ 有 |
| 23 | 购买 Credits | `can_purchase_credits` | `CAN_PURCHASE_CREDITS` | ✅ 有 |

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

**优先级**: `全局开关 (关闭)` > `用户 Override` > `Tier 配置` > `默认值`

> **用户 Override 使用场景**:
> - **客服补偿**: 为特定 t1 用户开通 Pro 功能
> - **Beta 测试**: 为测试用户开通未上线功能
> - **Bug 隔离**: 临时为某用户关闭有 Bug 的功能
> - **AB 实验**: 跨 Tier 用户验证某个功能 (实验组获得该功能，对照组不变)

### 4.3 配置值类型

| 值 | 说明 | 前端表现 |
|----|------|---------|
| `true` | 完全可用 | 正常按钮 |
| `false` | 不可用 | 按钮 + 🔒 + Tooltip + 点击弹 UpgradeModal |
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
  user_id TEXT NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
  feature_key TEXT NOT NULL,           -- 功能 Key, 如 'smart_scan', 'ai_features'
  override_value TEXT NOT NULL,        -- 覆盖值: 'true' | 'false' | 'trial'
  reason TEXT,                         -- 覆盖原因 (运营记录)
  expires_at TIMESTAMPTZ,              -- 过期时间 (可选, NULL=永久)
  created_by TEXT,                     -- 操作人 (Admin user_id)
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, feature_key)
);

-- 索引
CREATE INDEX idx_user_feature_overrides_user_id ON user_feature_overrides(user_id);
CREATE INDEX idx_user_feature_overrides_expires ON user_feature_overrides(expires_at) WHERE expires_at IS NOT NULL;
```

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
```

---

## 五、交互规则

### 5.1 NO 状态的 UI 表现

当功能权限为 `NO` 时：
- 功能按钮**可见**
- 按钮带**锁图标** (`Lock`, `w-3.5 h-3.5 text-amber-500`)
- Tooltip 显示**升级提示**
- 点击后弹出 **UpgradeModal**

### 5.2 Trial 状态的 UI 表现

当功能权限为 `trial` 且用户在试用期内时：
- 功能按钮**正常可用**
- 显示 **Trial Badge** (`Trial · Xd left`)
- 试用期结束后自动变为 NO

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
  // useTierFeature 的 FEATURES enum
  'PLATFORM_ASSETS': 'platform_assets',
  'VECTOR_TOOLS': 'vector_tools',
  'FREEHAND_TOOLS': 'freehand_tools',
  'SMART_SCAN': 'smart_scan',
  'ZIP_EXPORT': 'zip_export',
  'PROJECT_TEMPLATES': 'ai_features',
  'AI_FEATURES': 'ai_features',
  'EXPORT_PDF': 'pdf_export',
  'EXPORT_ZIP': 'zip_export',
  'PREMIUM_STICKERS': 'platform_assets',

  // useFeatureFlag 的 key
  'ocr': 'smart_scan',
  'ai_generation': 'ai_features',
  'zip_export': 'zip_export',
  'smart_scan': 'smart_scan',
  'clipboard_paste': 'clipboard_paste',
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

---

## 七、变更记录

| 日期 | 版本 | 变更内容 |
|------|------|---------|
| 2026-02-03 | v1.0 | 初始版本，基于产品图表整理 35 个功能点 |
| 2026-02-03 | v1.1 | 补充遗漏：TIER_FEATURES_FALLBACK、EMERGENCY_TIER_CONFIGS、LEGACY_KEY_MAP、完整 JSON 配置 |
| 2026-02-04 | v1.2 | 基于 CSV 表格校准：添加控制方式列、第 7-9 行权限配置、页面访问控制规则 (含已登录用户直接访问路径的处理)、UI 组件控制方式 |
| 2026-02-04 | v1.3 | 新增用户级功能覆盖 (user_feature_overrides)：支持为特定用户开通/关闭功能，与 Tier 配置解耦 |
| 2026-02-04 | v1.4 | 补充 AB 实验场景：跨 Tier 用户验证功能的实验组/对照组配置示例 |

---

**END OF DOCUMENT**
