# 功能权限矩阵

> **版本**: v1.1
> **日期**: 2026-02-03
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

| # | 功能 | Key | 游客 | t1 试用期内 | t1 超出试用期 | t2 | t3 |
|---|------|-----|:---:|:---:|:---:|:---:|:---:|
| 1 | Workspace 最大数量 | `quota.max_workspaces` | 0 | 1 | 1 | 1 | unlimited |
| 2 | 邀请成员加入 Workspace | `feature.can_invite_members` | NO | NO | NO | NO | YES |
| 3 | 文件夹最大数量 | `quota.max_folders` | 0 | 1 | 1 | 20 | 200 |
| 4 | 项目最大数量 | `quota.max_projects` | 0 | 1 | 1 | 10 | unlimited |
| 5 | 自定义素材上传 | `feature.can_upload_custom_assets` | NO | YES | NO | NO | YES |
| 6 | 自定义素材最大数量 | `quota.max_custom_assets` | 0 | 10 | 0 | 50 | unlimited |

### 2.2 编辑器功能 (Editor)

| # | 功能 | Key | 游客 | t1 试用期内 | t1 超出试用期 | t2 | t3 |
|---|------|-----|:---:|:---:|:---:|:---:|:---:|
| 7 | 使用平台素材 | `feature.platform_assets` | NO | YES | NO | YES | YES |
| 8 | 矢量图工具 | `feature.vector_tools` | NO | YES | NO | YES | YES |
| 9 | 画笔工具 | `feature.freehand_tools` | NO | YES | NO | YES | YES |
| 10 | Page 中剪贴板粘贴 | `feature.clipboard_paste` | NO | YES | NO | NO | YES |
| 11 | AI 生成素材 | `feature.ai_generate_assets` | NO | YES | NO | YES | YES |
| 12 | AI 生成 Page | `feature.ai_generate_page` | NO | YES | NO | YES | YES |
| 13 | 图片识别并生成 Page (Smart Scan) | `feature.smart_scan` | NO | YES | NO | NO | YES |

### 2.3 导出功能 (Export)

| # | 功能 | Key | 游客 | t1 试用期内 | t1 超出试用期 | t2 | t3 |
|---|------|-----|:---:|:---:|:---:|:---:|:---:|
| 14 | 8-Page PDF 打印 | `feature.pdf_print` | NO | YES | YES | YES | YES |
| 15 | 8-Page PDF 下载 | `feature.pdf_download` | NO | YES | YES | YES | YES |
| 16 | PDF + 每个页面图片下载 (ZIP) | `feature.zip_export` | NO | YES | NO | NO | YES |

### 2.4 商城功能 (Marketplace)

| # | 功能 | Key | 游客 | t1 试用期内 | t1 超出试用期 | t2 | t3 |
|---|------|-----|:---:|:---:|:---:|:---:|:---:|
| 17 | 发布付费项目/素材到商城 | `feature.publish_paid` | NO | YES | NO | NO | YES |
| 18 | 发布免费项目/素材到商城 | `feature.publish_free` | NO | YES | NO | YES | YES |
| 19 | 浏览商城 | `feature.browse_marketplace` | NO | YES | NO | YES | YES |
| 20 | 购买商城内的项目或素材 | `feature.purchase_marketplace` | NO | YES | NO | YES | YES |

### 2.5 数据恢复 (Recovery)

| # | 功能 | Key | 游客 | t1 试用期内 | t1 超出试用期 | t2 | t3 |
|---|------|-----|:---:|:---:|:---:|:---:|:---:|
| 21 | 30天内恢复已删除的数据 | `feature.recover_deleted` | NO | NO | NO | NO | YES |

### 2.6 订阅与支付 (Payment)

| # | 功能 | Key | 游客 | t1 试用期内 | t1 超出试用期 | t2 | t3 |
|---|------|-----|:---:|:---:|:---:|:---:|:---:|
| 22 | 订阅 Plan | `feature.can_subscribe` | NO | YES | YES | YES | YES |
| 23 | 购买 Credits | `feature.can_purchase_credits` | NO | NO | NO | YES | YES |

### 2.7 页面访问控制 (Page Access)

| # | 页面 | Key | 游客 | t1 | t2 | t3 |
|---|------|-----|:---:|:---:|:---:|:---:|
| 24 | Landing 页 | `page.landing` | 可见 | 可见 | 可见 | 可见 |
| 25 | Marketplace 页 | `page.marketplace` | 跳登录 | 可见 | 可见 | 可见 |
| 26 | Dashboard 页 | `page.dashboard` | 跳登录 | 可见 | 可见 | 可见 |
| 27 | Create 页 (编辑器) | `page.create` | 跳登录 | 可见 | 可见 | 可见 |
| 28 | Profile 页 | `page.profile` | 跳登录 | 可见 | 可见 | 可见 |
| 29 | Notification 页 | `page.notification` | 跳登录 | 可见 | 可见 | 可见 |
| 30 | Transaction History 页 | `page.transaction` | 跳登录 | 可见 | 可见 | 可见 |
| 31 | Manual/News 页 | `page.manual` | 可见 | 可见 | 可见 | 可见 |
| 32 | 静态页面 (About, Terms 等) | `page.static` | 可见 | 可见 | 可见 | 可见 |

### 2.8 UI 组件 (Components)

| # | 组件 | Key | 游客 | t1 | t2 | t3 |
|---|------|-----|:---:|:---:|:---:|:---:|
| 33 | Pricing 按钮 | `ui.pricing_button` | 弹窗 | 弹窗 | 弹窗 | 弹窗 |
| 34 | CTA 按钮 | `ui.cta_button` | 跳登录 | 可用 | 可用 | 可用 |
| 35 | Help 按钮 | `ui.help_button` | 可用 | 可用 | 可用 | 可用 |

---

## 三、功能 Key 映射表

> 统一 PRD 功能名 → 后端 FeatureKey → 前端 FEATURES 常量

| # | PRD 功能名 | 后端 FeatureKey | 前端 FEATURES | 当前代码状态 |
|---|-----------|----------------|--------------|-------------|
| 7 | 使用平台素材 | `platform_assets` | `PLATFORM_ASSETS` | ❌ 需新增 |
| 8 | 矢量图工具 | `vector_tools` | `VECTOR_TOOLS` | ⚠️ 后端有，前端无 |
| 9 | 画笔工具 | `freehand_tools` | `FREEHAND_TOOLS` | ⚠️ 后端有，前端无 |
| 10 | 剪贴板粘贴 | `clipboard_paste` | `CLIPBOARD_PASTE` | ⚠️ 后端有，前端无 |
| 11 | AI 生成素材 | `ai_features` | `AI_FEATURES` | ✅ 有 |
| 12 | AI 生成 Page | `ai_features` | `AI_FEATURES` | ✅ 复用 |
| 13 | Smart Scan | `ai_features` | `SMART_SCAN` | ✅ 有 |
| 14 | PDF 打印 | `pdf_export` | `EXPORT_PDF` | ✅ 有 |
| 15 | PDF 下载 | `pdf_export` | `EXPORT_PDF` | ✅ 有 |
| 16 | ZIP 导出 | `zip_export` | `EXPORT_ZIP` | ✅ 有 |
| 17 | 发布付费 | `publish_marketplace` | `PUBLISH_PAID` | ❌ 需新增 |
| 18 | 发布免费 | `publish_marketplace` | `PUBLISH_FREE` | ❌ 需新增 |
| 19 | 浏览商城 | `browse_marketplace` | `BROWSE_MARKETPLACE` | ⚠️ 后端有，前端无 |
| 20 | 购买商城 | `purchase_marketplace` | `PURCHASE_MARKETPLACE` | ⚠️ 后端有，前端无 |
| 21 | 30天恢复 | `recover_deleted` | `RECOVER_DELETED` | ❌ 需新增 |

---

## 四、配置存储方案

### 4.1 数据库表

复用现有 `system_configs` 表，使用 JSON 结构存储每个 Tier 的功能权限：

```sql
-- 示例配置
INSERT INTO system_configs (key, value, value_type, config_group) VALUES
-- Tier 基础信息
('tier.t1.display_name', 'Free Plan', 'text', 'tier'),
('tier.t1.monthly_credits', '0', 'integer', 'tier'),
('tier.t1.max_projects', '1', 'integer', 'tier'),

-- Tier 功能权限 (JSON)
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
}', 'json', 'tier'),

-- Trial 配置
('trial.default_days', '7', 'integer', 'trial');
```

### 4.2 配置读取优先级

```
1. user_feature_overrides 表 (运营授权，最高优先)
2. system_configs 表 (数据库配置)
3. EMERGENCY_TIER_CONFIGS (代码兜底，仅数据库不可用时)
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

export const TIER_FEATURES_FALLBACK: Record<string, Record<string, boolean | string>> = {
  t1: {
    platform_assets: false,
    vector_tools: false,
    freehand_tools: false,
    clipboard_paste: false,
    ai_features: false,
    smart_scan: false,
    pdf_export: true,
    zip_export: false,
    publish_paid: false,
    publish_free: false,
    browse_marketplace: false,
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
  'SMART_SCAN': 'smart_scan',
  'PREMIUM_STICKERS': 'platform_assets',
  'ZIP_EXPORT': 'zip_export',
  'PROJECT_TEMPLATES': 'ai_features',
  'AI_FEATURES': 'ai_features',
  'EXPORT_PDF': 'pdf_export',
  'EXPORT_ZIP': 'zip_export',

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

---

**END OF DOCUMENT**
