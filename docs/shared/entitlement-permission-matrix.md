# 功能权限矩阵

> **版本**: v2.0
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

| # | PRD 功能名 | 后端 FeatureKey | 前端 FEATURES | 当前代码状态 | 说明 |
|---|-----------|----------------|--------------|-------------|------|
| 7 | 使用平台素材 | `platform_assets` | `PLATFORM_ASSETS` | ❌ 需新增 | |
| 8 | 矢量图工具 | `vector_tools` | `VECTOR_TOOLS` | ❌ 需新增 | |
| 9 | 画笔工具 | `freehand_tools` | `FREEHAND_TOOLS` | ❌ 需新增 | |
| 10 | 剪贴板粘贴 | `clipboard_paste` | `CLIPBOARD_PASTE` | ⚠️ 后端有，前端无 | |
| 11 | AI 生成素材 | `ai_features` | `AI_FEATURES` | ✅ 有 | 与 #12 共用 Key |
| 12 | AI 生成 Page | `ai_features` | `AI_FEATURES` | ✅ 复用 | 与 #11 共用 Key |
| 13 | Smart Scan | `smart_scan` | `SMART_SCAN` | ✅ 有 | |
| 14 | PDF 打印 | `pdf_print` | `PDF_PRINT` | ✅ 有 | |
| 15 | PDF 下载 | `pdf_export` | `PDF_EXPORT` | ✅ 有 | 统一命名为 pdf_export |
| 16 | ZIP 导出 | `zip_export` | `ZIP_EXPORT` | ✅ 有 | 统一命名为 zip_export |
| 17 | 发布付费 | `publish_paid` | `PUBLISH_PAID` | ❌ 需新增 | |
| 18 | 发布免费 | `publish_free` | `PUBLISH_FREE` | ❌ 需新增 | |
| 19 | 浏览商城 | `browse_marketplace` | `BROWSE_MARKETPLACE` | ⚠️ 后端有，前端无 | |
| 20 | 购买商城 | `purchase_marketplace` | `PURCHASE_MARKETPLACE` | ⚠️ 后端有，前端无 | |
| 21 | 30天恢复 | `recover_deleted` | `RECOVER_DELETED` | ❌ 需新增 | |
| 22 | 订阅 Plan | `can_subscribe` | `CAN_SUBSCRIBE` | ✅ 有 | |
| 23 | 购买 Credits | `can_purchase_credits` | `CAN_PURCHASE_CREDITS` | ✅ 有 | |

> **Key 命名规范**:
> - 后端 FeatureKey 与前端 FEATURES 使用相同命名 (snake_case)
> - AI 功能 (#11, #12) 共用 `ai_features` Key，前端通过入口位置区分
> - PDF/ZIP 导出统一使用 `pdf_export` / `zip_export` (不带 EXPORT_ 前缀)

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
│  └── ⚠️ 即使用户有 Override，全局关闭也会生效                             │
│                                                                         │
│  Level 2: 用户级覆盖 (User Override)                                    │
│  ├── 配置: user_feature_overrides 表                                    │
│  ├── 效果: 为特定用户开通/关闭功能，跨 Tier 生效                          │
│  ├── 场景: VIP 用户、Beta 测试、AB 实验、客服补偿                         │
│  └── 🔒 仅在全局开关为 true 时生效                                       │
│                                                                         │
│  Level 3: Tier 配置 (Plan-based)                                        │
│  ├── 配置: tier.{tier}.features.{key}                                   │
│  ├── 效果: 按用户订阅等级决定权限                                         │
│  ├── 场景: 常规付费功能控制                                              │
│  └── 🔒 仅在无用户 Override 时生效                                       │
│                                                                         │
│  Level 4: 默认值 (Fallback)                                             │
│  ├── 配置: EMERGENCY_TIER_CONFIGS 常量                                  │
│  ├── 效果: 数据库不可用时的兜底                                          │
│  ├── 场景: 网络故障、数据库宕机                                          │
│  └── 🔒 仅在以上配置都无法获取时生效                                      │
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

---

## 七、扩展场景完整实现方案

> 基于业界最佳实践 (LaunchDarkly, Split.io, Unleash, Statsig) 设计的扩展场景完整实现方案。

### 7.1 场景支持矩阵

| 场景 | 支持情况 | 说明 |
|------|:--------:|------|
| **灰度发布 + Tier 组合** | ✅ 支持 | 完整优先级规则 + 评估引擎 |
| **权限继承链** | ✅ 支持 | Tier 自动继承父级权限 |
| **权限批量管理** | ✅ 支持 | 用户组 + 组级权限覆盖 |
| **配置版本控制** | ✅ 支持 | 快照 + 回滚机制 |
| **多租户 (Team/Org 级权限)** | ✅ 支持 | Workspace 级权限继承 |
| **审计 + 回溯** | ✅ 已实现 | v1.6 已补充 logs 表 |

---

### 7.2 灰度发布 + Tier 组合

#### 7.2.1 完整优先级规则

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    权限评估完整优先级 (从高到低)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Level 1: 全局开关 (Kill Switch)                                            │
│  ├── 配置: feature.{key}.enabled = false                                   │
│  ├── 效果: 功能完全下线，任何其他配置无效                                      │
│  └── 场景: 紧急下线、功能维护、严重 Bug                                       │
│                                                                             │
│  Level 2: Feature Flag (技术开关)                                           │
│  ├── 配置: feature_flags 表                                                │
│  ├── 效果: 控制功能是否对特定用户群可见                                        │
│  ├── 场景: 灰度发布、AB 实验、Beta 测试                                       │
│  └── ⚠️ 即使用户有 Entitlement 权限，Flag 关闭也无法访问                       │
│                                                                             │
│  Level 3: 用户级覆盖 (User Override)                                        │
│  ├── 配置: user_feature_overrides 表                                        │
│  ├── 效果: 为特定用户开通/关闭功能，跨 Tier 生效                               │
│  └── 场景: VIP 用户、客服补偿、Bug 隔离                                       │
│                                                                             │
│  Level 4: 用户组覆盖 (Group Override)                                       │
│  ├── 配置: group_feature_overrides 表                                       │
│  ├── 效果: 为用户组批量授权                                                   │
│  └── 场景: KOL 用户组、Beta 测试组、Enterprise 试用组                          │
│                                                                             │
│  Level 5: Workspace 覆盖 (Workspace Override)                               │
│  ├── 配置: workspace_feature_overrides 表                                   │
│  ├── 效果: Workspace 成员继承权限                                            │
│  └── 场景: Team Plan、企业授权                                               │
│                                                                             │
│  Level 6: Tier 配置 (Plan-based) + 继承链                                   │
│  ├── 配置: tier.{tier}.features + TIER_INHERITANCE                         │
│  ├── 效果: 按用户订阅等级决定权限，自动继承父级                                 │
│  └── 场景: 常规付费功能控制                                                   │
│                                                                             │
│  Level 7: 默认值 (Fallback)                                                 │
│  ├── 配置: EMERGENCY_TIER_CONFIGS 常量                                      │
│  └── 场景: 数据库不可用时的兜底                                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 7.2.2 完整评估引擎

```typescript
// lib/entitlement/evaluator.ts

interface EvaluationContext {
  userId: string;
  tier: string;
  isWithinTrialPeriod: boolean;
  userGroups: string[];      // 用户所属组
  workspaceId?: string;      // 当前 Workspace
}

interface EvaluationResult {
  allowed: boolean;
  reason: string;
  source: 'kill_switch' | 'feature_flag' | 'user_override' | 'group_override' | 'workspace_override' | 'tier_config' | 'fallback';
  trialDaysRemaining?: number;
}

async function evaluateFeatureAccess(
  featureKey: string,
  context: EvaluationContext
): Promise<EvaluationResult> {

  // Level 1: Kill Switch
  const killSwitch = await getConfig(`feature.${featureKey}.enabled`);
  if (killSwitch === 'false') {
    return {
      allowed: false,
      reason: 'Feature is globally disabled',
      source: 'kill_switch'
    };
  }

  // Level 2: Feature Flag
  const flagResult = await evaluateFeatureFlag(featureKey, context);
  if (flagResult !== null) {
    return {
      allowed: flagResult.enabled,
      reason: flagResult.enabled ? 'Feature flag enabled' : 'Feature flag disabled or not in rollout',
      source: 'feature_flag'
    };
  }

  // Level 3: User Override
  const userOverride = await getUserOverride(context.userId, featureKey);
  if (userOverride) {
    return {
      allowed: userOverride.override_value === 'true',
      reason: `User override: ${userOverride.reason}`,
      source: 'user_override'
    };
  }

  // Level 4: Group Override
  if (context.userGroups.length > 0) {
    const groupOverride = await getGroupOverride(context.userGroups, featureKey);
    if (groupOverride) {
      return {
        allowed: groupOverride.override_value === 'true',
        reason: `Group override: ${groupOverride.reason}`,
        source: 'group_override'
      };
    }
  }

  // Level 5: Workspace Override
  if (context.workspaceId) {
    const workspaceOverride = await getWorkspaceOverride(context.workspaceId, featureKey);
    if (workspaceOverride) {
      return {
        allowed: workspaceOverride.override_value === 'true',
        reason: `Workspace override: ${workspaceOverride.reason}`,
        source: 'workspace_override'
      };
    }
  }

  // Level 6: Tier Config (with inheritance)
  const tierFeatures = getTierFeaturesWithInheritance(context.tier);
  const featureValue = tierFeatures[featureKey];

  if (featureValue === true) {
    return { allowed: true, reason: 'Tier permission', source: 'tier_config' };
  }

  if (featureValue === 'trial') {
    if (context.isWithinTrialPeriod) {
      const daysRemaining = await getTrialDaysRemaining(context.userId);
      return {
        allowed: true,
        reason: 'Trial period active',
        source: 'tier_config',
        trialDaysRemaining: daysRemaining
      };
    }
    return { allowed: false, reason: 'Trial period expired', source: 'tier_config' };
  }

  if (featureValue === false) {
    return { allowed: false, reason: 'Not included in tier', source: 'tier_config' };
  }

  // Level 7: Fallback
  const fallback = EMERGENCY_TIER_CONFIGS[context.tier]?.features[featureKey] ?? false;
  return {
    allowed: fallback === true,
    reason: 'Fallback default',
    source: 'fallback'
  };
}

// Feature Flag 评估 (灰度 + Tier 组合)
async function evaluateFeatureFlag(
  featureKey: string,
  context: EvaluationContext
): Promise<{ enabled: boolean } | null> {
  const flag = await db.fetch(`
    SELECT * FROM feature_flags
    WHERE flag_key = $1 AND is_enabled = true
  `, featureKey);

  if (!flag) return null;  // 无 Flag，继续下一级

  // 检查 Tier 限制
  if (flag.allowed_tiers && flag.allowed_tiers.length > 0) {
    if (!flag.allowed_tiers.includes(context.tier)) {
      return { enabled: false };  // Tier 不在允许列表
    }
  }

  // 检查灰度百分比
  if (flag.rollout_percentage < 100) {
    const hash = hashUserForRollout(context.userId, featureKey);
    if (hash > flag.rollout_percentage) {
      return { enabled: false };  // 未命中灰度
    }
  }

  return { enabled: true };
}
```

#### 7.2.3 灰度 + Tier 组合示例

```typescript
// 场景: 新 AI 模型只对 t3 用户的 30% 灰度发布

// 1. 创建 Feature Flag
await db.insert('feature_flags', {
  flag_key: 'new_ai_model_v2',
  flag_name: '新 AI 模型 v2',
  is_enabled: true,
  allowed_tiers: ['t3'],           // 只对 t3 用户
  rollout_percentage: 30,          // 30% 灰度
  description: '新 AI 模型灰度测试'
});

// 2. 评估结果
// t1 用户 → allowed: false (Tier 不在 allowed_tiers)
// t2 用户 → allowed: false (Tier 不在 allowed_tiers)
// t3 用户 (命中 30%) → allowed: true
// t3 用户 (未命中) → allowed: false (未命中灰度)

// 3. 灰度结束后，删除 Flag，回归 Tier 配置
await db.delete('feature_flags', { flag_key: 'new_ai_model_v2' });
```

---

### 7.3 权限继承链

#### 7.3.1 继承规则定义

```typescript
// lib/entitlement/inheritance.ts

/**
 * Tier 继承链定义
 * - t1: 基础层级，无继承
 * - t2: 继承 t1 所有权限
 * - t3: 继承 t2 所有权限 (间接继承 t1)
 * - t4: 继承 t3 所有权限 (间接继承 t1, t2)
 */
export const TIER_INHERITANCE: Record<string, string[]> = {
  t1: [],
  t2: ['t1'],
  t3: ['t2'],
  t4: ['t3'],
};

/**
 * Tier 增量配置
 * 只配置该层级新增/修改的权限，其余从父级继承
 */
export const TIER_FEATURES_DELTA: Record<string, Record<string, boolean | string>> = {
  t1: {
    // 基础权限
    platform_assets: true,
    vector_tools: true,
    freehand_tools: true,
    pdf_export: true,
    pdf_print: true,
    can_subscribe: true,
    // 试用权限
    clipboard_paste: 'trial',
    ai_features: 'trial',
    smart_scan: 'trial',
    zip_export: 'trial',
    publish_paid: 'trial',
    publish_free: 'trial',
    browse_marketplace: 'trial',
    purchase_marketplace: 'trial',
    can_upload_custom_assets: 'trial',
    // 禁用权限
    recover_deleted: false,
    can_invite_members: false,
    can_purchase_credits: false,
  },
  t2: {
    // t2 新增/覆盖的权限 (继承 t1 的基础)
    ai_features: true,              // 覆盖 t1 的 trial
    publish_free: true,             // 覆盖 t1 的 trial
    browse_marketplace: true,       // 覆盖 t1 的 trial
    purchase_marketplace: true,     // 覆盖 t1 的 trial
    can_purchase_credits: true,     // 覆盖 t1 的 false
    // 其余从 t1 继承
  },
  t3: {
    // t3 新增/覆盖的权限 (继承 t2 的基础)
    clipboard_paste: true,          // 覆盖 t1 的 trial
    smart_scan: true,               // 覆盖 t1 的 trial
    zip_export: true,               // 覆盖 t1 的 trial
    publish_paid: true,             // 覆盖 t1 的 trial
    recover_deleted: true,          // 覆盖 t1 的 false
    can_invite_members: true,       // 覆盖 t1 的 false
    can_upload_custom_assets: true, // 覆盖 t1 的 trial
    // 其余从 t2 继承
  },
  t4: {
    // t4 完全继承 t3，可添加额外企业功能
    // 其余从 t3 继承
  },
};

/**
 * 获取 Tier 的完整权限配置 (含继承)
 */
export function getTierFeaturesWithInheritance(tier: string): Record<string, boolean | string> {
  const result: Record<string, boolean | string> = {};

  // 递归获取父级权限
  const parents = TIER_INHERITANCE[tier] || [];
  for (const parent of parents) {
    Object.assign(result, getTierFeaturesWithInheritance(parent));
  }

  // 覆盖当前层级的权限
  Object.assign(result, TIER_FEATURES_DELTA[tier] || {});

  return result;
}

/**
 * 获取完整的 TIER_FEATURES (展开所有继承)
 * 用于生成 TIER_FEATURES_FALLBACK 和 system_configs
 */
export function generateFullTierFeatures(): Record<string, Record<string, boolean | string>> {
  return {
    t1: getTierFeaturesWithInheritance('t1'),
    t2: getTierFeaturesWithInheritance('t2'),
    t3: getTierFeaturesWithInheritance('t3'),
    t4: getTierFeaturesWithInheritance('t4'),
  };
}
```

#### 7.3.2 继承链验证工具

```typescript
// scripts/tools/verify-tier-inheritance.ts

import { generateFullTierFeatures, TIER_FEATURES_DELTA } from '@/lib/entitlement/inheritance';

/**
 * 验证继承链的正确性
 */
function verifyTierInheritance() {
  const fullFeatures = generateFullTierFeatures();

  console.log('=== Tier 继承验证 ===\n');

  // 验证规则: 高层级必须包含低层级的所有 true 权限
  const tiers = ['t1', 't2', 't3', 't4'];

  for (let i = 1; i < tiers.length; i++) {
    const currentTier = tiers[i];
    const parentTier = tiers[i - 1];

    const current = fullFeatures[currentTier];
    const parent = fullFeatures[parentTier];

    console.log(`${currentTier} vs ${parentTier}:`);

    for (const [key, value] of Object.entries(parent)) {
      if (value === true && current[key] !== true) {
        console.error(`  ❌ ${key}: ${parentTier}=${value}, ${currentTier}=${current[key]}`);
      }
    }

    // 显示增量
    const delta = TIER_FEATURES_DELTA[currentTier];
    console.log(`  增量配置: ${Object.keys(delta).length} 项`);
    for (const [key, value] of Object.entries(delta)) {
      console.log(`    ${key}: ${parent[key]} → ${value}`);
    }
    console.log('');
  }
}

verifyTierInheritance();
```

---

### 7.4 权限批量管理 (用户组)

#### 7.4.1 数据库表设计

```sql
-- =============================================
-- 用户组系统表
-- =============================================

-- 用户组表
CREATE TABLE user_groups (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  group_key TEXT NOT NULL UNIQUE,          -- 唯一标识: 'kol', 'beta_testers', 'enterprise_pilot'
  group_name TEXT NOT NULL,                -- 显示名称: 'KOL 用户组', 'Beta 测试组'
  description TEXT,
  is_active BOOLEAN DEFAULT true,
  created_by TEXT NOT NULL,                -- 创建人 (Admin user_id)
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 用户组成员表
CREATE TABLE user_group_members (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  group_id UUID NOT NULL REFERENCES user_groups(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
  added_by TEXT NOT NULL,                  -- 添加人 (Admin user_id)
  added_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ,                  -- 成员过期时间 (可选)
  UNIQUE(group_id, user_id)
);

-- 组级权限覆盖表
CREATE TABLE group_feature_overrides (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  group_id UUID NOT NULL REFERENCES user_groups(id) ON DELETE CASCADE,
  feature_key TEXT NOT NULL,
  override_value TEXT NOT NULL,            -- 'true' | 'false' | 'trial'
  reason TEXT,
  expires_at TIMESTAMPTZ,                  -- 权限过期时间 (可选)
  created_by TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(group_id, feature_key)
);

-- 组级权限变更审计日志
CREATE TABLE group_feature_override_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  override_id UUID REFERENCES group_feature_overrides(id) ON DELETE SET NULL,
  group_id UUID NOT NULL,
  feature_key TEXT NOT NULL,
  action TEXT NOT NULL,                    -- 'created' | 'updated' | 'deleted' | 'expired'
  old_value TEXT,
  new_value TEXT,
  reason TEXT,
  changed_by TEXT NOT NULL,
  changed_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_user_groups_key ON user_groups(group_key);
CREATE INDEX idx_user_group_members_user ON user_group_members(user_id);
CREATE INDEX idx_user_group_members_group ON user_group_members(group_id);
CREATE INDEX idx_user_group_members_expires ON user_group_members(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX idx_group_feature_overrides_group ON group_feature_overrides(group_id);
CREATE INDEX idx_group_feature_overrides_expires ON group_feature_overrides(expires_at) WHERE expires_at IS NOT NULL;
```

#### 7.4.2 后端 Service 实现

```python
# domains/entitlement/services/group_service.py

from typing import Optional, List
from datetime import datetime
from core.database import get_db

class GroupService:
    """用户组权限服务"""

    async def create_group(
        self,
        group_key: str,
        group_name: str,
        description: str,
        created_by: str
    ) -> dict:
        """创建用户组"""
        db = await get_db()
        result = await db.fetch_one("""
            INSERT INTO user_groups (group_key, group_name, description, created_by)
            VALUES ($1, $2, $3, $4)
            RETURNING *
        """, group_key, group_name, description, created_by)
        return dict(result)

    async def add_members(
        self,
        group_id: str,
        user_ids: List[str],
        added_by: str,
        expires_at: Optional[datetime] = None
    ) -> int:
        """批量添加成员"""
        db = await get_db()
        count = 0
        for user_id in user_ids:
            try:
                await db.execute("""
                    INSERT INTO user_group_members (group_id, user_id, added_by, expires_at)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (group_id, user_id) DO NOTHING
                """, group_id, user_id, added_by, expires_at)
                count += 1
            except Exception:
                pass
        return count

    async def set_group_feature(
        self,
        group_id: str,
        feature_key: str,
        override_value: str,
        reason: str,
        created_by: str,
        expires_at: Optional[datetime] = None
    ) -> dict:
        """设置组级权限"""
        db = await get_db()

        # 获取旧值
        old = await db.fetch_one("""
            SELECT override_value FROM group_feature_overrides
            WHERE group_id = $1 AND feature_key = $2
        """, group_id, feature_key)

        # Upsert
        result = await db.fetch_one("""
            INSERT INTO group_feature_overrides
            (group_id, feature_key, override_value, reason, expires_at, created_by)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (group_id, feature_key) DO UPDATE SET
                override_value = EXCLUDED.override_value,
                reason = EXCLUDED.reason,
                expires_at = EXCLUDED.expires_at,
                updated_at = NOW()
            RETURNING *
        """, group_id, feature_key, override_value, reason, expires_at, created_by)

        # 记录审计日志
        await db.execute("""
            INSERT INTO group_feature_override_logs
            (override_id, group_id, feature_key, action, old_value, new_value, reason, changed_by)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, result['id'], group_id, feature_key,
            'updated' if old else 'created',
            old['override_value'] if old else None,
            override_value, reason, created_by)

        return dict(result)

    async def get_user_groups(self, user_id: str) -> List[str]:
        """获取用户所属的所有有效组 ID"""
        db = await get_db()
        rows = await db.fetch_all("""
            SELECT g.id FROM user_groups g
            JOIN user_group_members m ON g.id = m.group_id
            WHERE m.user_id = $1
              AND g.is_active = true
              AND (m.expires_at IS NULL OR m.expires_at > NOW())
        """, user_id)
        return [row['id'] for row in rows]

    async def get_group_override(
        self,
        group_ids: List[str],
        feature_key: str
    ) -> Optional[dict]:
        """获取组级权限覆盖 (优先返回第一个匹配的)"""
        if not group_ids:
            return None

        db = await get_db()
        result = await db.fetch_one("""
            SELECT * FROM group_feature_overrides
            WHERE group_id = ANY($1) AND feature_key = $2
              AND (expires_at IS NULL OR expires_at > NOW())
            ORDER BY created_at DESC
            LIMIT 1
        """, group_ids, feature_key)

        return dict(result) if result else None
```

#### 7.4.3 使用示例

```python
# 场景: 为 KOL 用户组批量授权 AI 功能

# 1. 创建 KOL 用户组
kol_group = await group_service.create_group(
    group_key='kol',
    group_name='KOL 用户组',
    description='签约 KOL 用户，享受 Pro 级别 AI 功能',
    created_by='admin_user_id'
)

# 2. 批量添加 KOL 用户
kol_user_ids = ['user_kol_001', 'user_kol_002', 'user_kol_003']
await group_service.add_members(
    group_id=kol_group['id'],
    user_ids=kol_user_ids,
    added_by='admin_user_id',
    expires_at=datetime(2026, 12, 31)  # 年底到期
)

# 3. 设置组级 AI 功能权限
await group_service.set_group_feature(
    group_id=kol_group['id'],
    feature_key='ai_features',
    override_value='true',
    reason='KOL 签约权益',
    created_by='admin_user_id'
)

await group_service.set_group_feature(
    group_id=kol_group['id'],
    feature_key='smart_scan',
    override_value='true',
    reason='KOL 签约权益',
    created_by='admin_user_id'
)

# 4. 评估时自动生效
# t1 KOL 用户访问 ai_features → allowed: true (Group Override)
# t1 普通用户访问 ai_features → allowed: false (Tier Config)
```

---

### 7.5 配置版本控制

#### 7.5.1 数据库表设计

```sql
-- =============================================
-- 配置版本控制系统表
-- =============================================

-- 配置快照表
CREATE TABLE config_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  snapshot_key TEXT NOT NULL UNIQUE,       -- 唯一标识: 'pre_black_friday_2026'
  snapshot_name TEXT NOT NULL,             -- 显示名称: '黑五活动前快照'
  snapshot_type TEXT NOT NULL,             -- 类型: 'tier_configs' | 'feature_flags' | 'full'
  snapshot_data JSONB NOT NULL,            -- 完整配置数据
  description TEXT,
  is_current BOOLEAN DEFAULT false,        -- 是否为当前生效版本
  created_by TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 配置回滚日志
CREATE TABLE config_rollback_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  snapshot_id UUID NOT NULL REFERENCES config_snapshots(id),
  rollback_type TEXT NOT NULL,             -- 'full' | 'partial'
  affected_keys TEXT[],                    -- 受影响的配置 key
  rollback_reason TEXT NOT NULL,
  rollback_by TEXT NOT NULL,
  rollback_at TIMESTAMPTZ DEFAULT NOW(),
  success BOOLEAN DEFAULT true,
  error_message TEXT
);

-- 索引
CREATE INDEX idx_config_snapshots_type ON config_snapshots(snapshot_type);
CREATE INDEX idx_config_snapshots_created ON config_snapshots(created_at DESC);
CREATE INDEX idx_config_snapshots_current ON config_snapshots(is_current) WHERE is_current = true;
```

#### 7.5.2 快照服务实现

```python
# domains/entitlement/services/snapshot_service.py

from typing import Optional, List
from datetime import datetime
import json
from core.database import get_db

class ConfigSnapshotService:
    """配置快照与回滚服务"""

    async def create_snapshot(
        self,
        snapshot_key: str,
        snapshot_name: str,
        snapshot_type: str,  # 'tier_configs' | 'feature_flags' | 'full'
        description: str,
        created_by: str
    ) -> dict:
        """创建配置快照"""
        db = await get_db()

        # 根据类型收集配置数据
        snapshot_data = {}

        if snapshot_type in ['tier_configs', 'full']:
            tier_configs = await db.fetch_all("""
                SELECT key, value, value_type FROM system_configs
                WHERE config_group = 'tier' AND is_active = true
            """)
            snapshot_data['tier_configs'] = [dict(r) for r in tier_configs]

        if snapshot_type in ['feature_flags', 'full']:
            feature_flags = await db.fetch_all("""
                SELECT * FROM feature_flags WHERE is_enabled = true
            """)
            snapshot_data['feature_flags'] = [dict(r) for r in feature_flags]

        if snapshot_type == 'full':
            # 包含全局开关
            global_configs = await db.fetch_all("""
                SELECT key, value, value_type FROM system_configs
                WHERE config_group = 'feature' AND is_active = true
            """)
            snapshot_data['global_configs'] = [dict(r) for r in global_configs]

            # 包含用户组权限
            group_overrides = await db.fetch_all("""
                SELECT * FROM group_feature_overrides
            """)
            snapshot_data['group_overrides'] = [dict(r) for r in group_overrides]

        # 保存快照
        result = await db.fetch_one("""
            INSERT INTO config_snapshots
            (snapshot_key, snapshot_name, snapshot_type, snapshot_data, description, created_by)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
        """, snapshot_key, snapshot_name, snapshot_type,
            json.dumps(snapshot_data), description, created_by)

        return dict(result)

    async def rollback_to_snapshot(
        self,
        snapshot_id: str,
        rollback_reason: str,
        rollback_by: str,
        partial_keys: Optional[List[str]] = None  # 部分回滚时指定 key
    ) -> dict:
        """回滚到指定快照"""
        db = await get_db()

        # 获取快照
        snapshot = await db.fetch_one("""
            SELECT * FROM config_snapshots WHERE id = $1
        """, snapshot_id)

        if not snapshot:
            raise ValueError(f"Snapshot {snapshot_id} not found")

        snapshot_data = json.loads(snapshot['snapshot_data'])
        affected_keys = []

        try:
            # 回滚 Tier 配置
            if 'tier_configs' in snapshot_data:
                for config in snapshot_data['tier_configs']:
                    if partial_keys and config['key'] not in partial_keys:
                        continue

                    await db.execute("""
                        UPDATE system_configs
                        SET value = $1, updated_at = NOW()
                        WHERE key = $2
                    """, config['value'], config['key'])
                    affected_keys.append(config['key'])

            # 回滚 Feature Flags
            if 'feature_flags' in snapshot_data:
                # 先禁用所有当前 flags
                await db.execute("""
                    UPDATE feature_flags SET is_enabled = false, updated_at = NOW()
                """)

                # 恢复快照中的 flags
                for flag in snapshot_data['feature_flags']:
                    if partial_keys and flag['flag_key'] not in partial_keys:
                        continue

                    await db.execute("""
                        INSERT INTO feature_flags (flag_key, flag_name, is_enabled, rollout_percentage, allowed_tiers)
                        VALUES ($1, $2, $3, $4, $5)
                        ON CONFLICT (flag_key) DO UPDATE SET
                            is_enabled = EXCLUDED.is_enabled,
                            rollout_percentage = EXCLUDED.rollout_percentage,
                            allowed_tiers = EXCLUDED.allowed_tiers,
                            updated_at = NOW()
                    """, flag['flag_key'], flag['flag_name'], flag['is_enabled'],
                        flag['rollout_percentage'], flag['allowed_tiers'])
                    affected_keys.append(f"flag:{flag['flag_key']}")

            # 标记快照为当前生效
            await db.execute("""
                UPDATE config_snapshots SET is_current = false
            """)
            await db.execute("""
                UPDATE config_snapshots SET is_current = true WHERE id = $1
            """, snapshot_id)

            # 记录回滚日志
            log = await db.fetch_one("""
                INSERT INTO config_rollback_logs
                (snapshot_id, rollback_type, affected_keys, rollback_reason, rollback_by, success)
                VALUES ($1, $2, $3, $4, $5, true)
                RETURNING *
            """, snapshot_id, 'partial' if partial_keys else 'full',
                affected_keys, rollback_reason, rollback_by)

            return {
                'success': True,
                'affected_keys': affected_keys,
                'log_id': log['id']
            }

        except Exception as e:
            # 记录失败日志
            await db.execute("""
                INSERT INTO config_rollback_logs
                (snapshot_id, rollback_type, affected_keys, rollback_reason, rollback_by, success, error_message)
                VALUES ($1, $2, $3, $4, $5, false, $6)
            """, snapshot_id, 'partial' if partial_keys else 'full',
                affected_keys, rollback_reason, rollback_by, str(e))
            raise

    async def list_snapshots(
        self,
        snapshot_type: Optional[str] = None,
        limit: int = 20
    ) -> List[dict]:
        """列出快照"""
        db = await get_db()

        if snapshot_type:
            rows = await db.fetch_all("""
                SELECT id, snapshot_key, snapshot_name, snapshot_type,
                       description, is_current, created_by, created_at
                FROM config_snapshots
                WHERE snapshot_type = $1
                ORDER BY created_at DESC
                LIMIT $2
            """, snapshot_type, limit)
        else:
            rows = await db.fetch_all("""
                SELECT id, snapshot_key, snapshot_name, snapshot_type,
                       description, is_current, created_by, created_at
                FROM config_snapshots
                ORDER BY created_at DESC
                LIMIT $1
            """, limit)

        return [dict(r) for r in rows]
```

#### 7.5.3 使用示例

```python
# 场景: 黑五活动前创建快照，活动后回滚

# 1. 活动前创建完整快照
snapshot = await snapshot_service.create_snapshot(
    snapshot_key='pre_black_friday_2026',
    snapshot_name='2026 黑五活动前快照',
    snapshot_type='full',
    description='黑五促销活动前的完整配置备份',
    created_by='admin_user_id'
)
print(f"快照创建成功: {snapshot['id']}")

# 2. 进行活动配置修改...
# (修改 Tier 权限、Feature Flags 等)

# 3. 活动结束后回滚
result = await snapshot_service.rollback_to_snapshot(
    snapshot_id=snapshot['id'],
    rollback_reason='黑五活动结束，恢复正常配置',
    rollback_by='admin_user_id'
)
print(f"回滚成功，影响 {len(result['affected_keys'])} 个配置项")

# 4. 部分回滚 (只回滚特定配置)
result = await snapshot_service.rollback_to_snapshot(
    snapshot_id=snapshot['id'],
    rollback_reason='只恢复 t2 Tier 配置',
    rollback_by='admin_user_id',
    partial_keys=['tier.t2.features']  # 只回滚这个 key
)
```

---

### 7.6 多租户权限 (Workspace 级)

#### 7.6.1 数据库表设计

```sql
-- =============================================
-- Workspace 级权限系统表
-- =============================================

-- Workspace 权限覆盖表
CREATE TABLE workspace_feature_overrides (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  feature_key TEXT NOT NULL,
  override_value TEXT NOT NULL,            -- 'true' | 'false' | 'trial'
  reason TEXT,                             -- 如 'Enterprise 试用', 'Team Plan 权益'
  expires_at TIMESTAMPTZ,
  created_by TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(workspace_id, feature_key)
);

-- Workspace 权限变更审计日志
CREATE TABLE workspace_feature_override_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  override_id UUID REFERENCES workspace_feature_overrides(id) ON DELETE SET NULL,
  workspace_id UUID NOT NULL,
  feature_key TEXT NOT NULL,
  action TEXT NOT NULL,                    -- 'created' | 'updated' | 'deleted' | 'expired'
  old_value TEXT,
  new_value TEXT,
  reason TEXT,
  changed_by TEXT NOT NULL,
  changed_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_workspace_feature_overrides_workspace ON workspace_feature_overrides(workspace_id);
CREATE INDEX idx_workspace_feature_overrides_expires ON workspace_feature_overrides(expires_at) WHERE expires_at IS NOT NULL;
```

#### 7.6.2 Workspace 权限服务

```python
# domains/entitlement/services/workspace_override_service.py

from typing import Optional
from datetime import datetime
from core.database import get_db

class WorkspaceOverrideService:
    """Workspace 级权限覆盖服务"""

    async def set_workspace_feature(
        self,
        workspace_id: str,
        feature_key: str,
        override_value: str,
        reason: str,
        created_by: str,
        expires_at: Optional[datetime] = None
    ) -> dict:
        """设置 Workspace 级权限"""
        db = await get_db()

        # 获取旧值
        old = await db.fetch_one("""
            SELECT override_value FROM workspace_feature_overrides
            WHERE workspace_id = $1 AND feature_key = $2
        """, workspace_id, feature_key)

        # Upsert
        result = await db.fetch_one("""
            INSERT INTO workspace_feature_overrides
            (workspace_id, feature_key, override_value, reason, expires_at, created_by)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (workspace_id, feature_key) DO UPDATE SET
                override_value = EXCLUDED.override_value,
                reason = EXCLUDED.reason,
                expires_at = EXCLUDED.expires_at,
                updated_at = NOW()
            RETURNING *
        """, workspace_id, feature_key, override_value, reason, expires_at, created_by)

        # 记录审计日志
        await db.execute("""
            INSERT INTO workspace_feature_override_logs
            (override_id, workspace_id, feature_key, action, old_value, new_value, reason, changed_by)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, result['id'], workspace_id, feature_key,
            'updated' if old else 'created',
            old['override_value'] if old else None,
            override_value, reason, created_by)

        return dict(result)

    async def get_workspace_override(
        self,
        workspace_id: str,
        feature_key: str
    ) -> Optional[dict]:
        """获取 Workspace 级权限覆盖"""
        db = await get_db()
        result = await db.fetch_one("""
            SELECT * FROM workspace_feature_overrides
            WHERE workspace_id = $1 AND feature_key = $2
              AND (expires_at IS NULL OR expires_at > NOW())
        """, workspace_id, feature_key)

        return dict(result) if result else None

    async def apply_team_plan(
        self,
        workspace_id: str,
        team_tier: str,  # 如 't3'
        reason: str,
        created_by: str,
        expires_at: Optional[datetime] = None
    ) -> int:
        """为 Workspace 应用 Team Plan 权限"""
        from lib.entitlement.inheritance import getTierFeaturesWithInheritance

        tier_features = getTierFeaturesWithInheritance(team_tier)
        count = 0

        for feature_key, value in tier_features.items():
            if value == True:
                await self.set_workspace_feature(
                    workspace_id=workspace_id,
                    feature_key=feature_key,
                    override_value='true',
                    reason=f"{reason} - {team_tier} 权益",
                    created_by=created_by,
                    expires_at=expires_at
                )
                count += 1

        return count
```

#### 7.6.3 使用示例

```python
# 场景: Workspace Owner 购买 Team Plan，成员获得权限

# 1. Owner 购买 Team Plan 后触发
workspace_id = 'workspace_abc123'

# 2. 为 Workspace 应用 t3 级别权限
count = await workspace_override_service.apply_team_plan(
    workspace_id=workspace_id,
    team_tier='t3',
    reason='Team Pro Plan 订阅',
    created_by='system',
    expires_at=datetime(2027, 2, 4)  # 订阅到期时间
)
print(f"已为 Workspace 设置 {count} 个权限")

# 3. 成员访问时的评估
# - 成员 user_a (t1) 访问 ai_features
# - 评估流程:
#   1. Kill Switch: 通过
#   2. Feature Flag: 无
#   3. User Override: 无
#   4. Group Override: 无
#   5. Workspace Override: ✅ ai_features = true
#   → allowed: true, source: 'workspace_override'

# 4. 成员离开 Workspace 后
# - 评估时 workspaceId 为空或不同
# - 回退到 User Tier Config (t1)
# → allowed: false (试用期过期)
```

---

### 7.7 完整权限评估流程图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        完整权限评估流程                                       │
└─────────────────────────────────────────────────────────────────────────────┘

用户请求功能 X
      │
      ▼
┌─────────────────┐
│ L1: Kill Switch │ ── false ──▶ 返回 disabled
└────────┬────────┘              (功能全局关闭)
         │ true
         ▼
┌─────────────────┐
│ L2: Feature Flag│ ── 有 Flag 且关闭 ──▶ 返回 disabled
│   (灰度+Tier)   │                        (未命中灰度或 Tier 不符)
└────────┬────────┘
         │ 无 Flag 或命中
         ▼
┌─────────────────┐
│ L3: User Override│ ── 有 ──▶ 返回 Override 值
│                 │           (VIP/补偿/Bug隔离)
└────────┬────────┘
         │ 无
         ▼
┌─────────────────┐
│ L4: Group Override│ ── 有 ──▶ 返回 Override 值
│   (用户组权限)  │            (KOL/Beta/Enterprise)
└────────┬────────┘
         │ 无
         ▼
┌─────────────────┐
│ L5: Workspace   │ ── 有 ──▶ 返回 Override 值
│    Override     │           (Team Plan)
└────────┬────────┘
         │ 无
         ▼
┌─────────────────┐
│ L6: Tier Config │ ── true ──▶ 返回 allowed
│  (含继承链)     │ ── trial ──▶ 检查试用期
│                 │ ── false ──▶ 返回 locked
└────────┬────────┘
         │ 无配置
         ▼
┌─────────────────┐
│ L7: Fallback    │ ── 返回兜底默认值
└─────────────────┘   (数据库不可用时)
```

---

### 7.8 实施计划

| 阶段 | 场景 | 工作量 | 优先级 |
|:----:|------|:------:|:------:|
| Phase 1 | 灰度 + Tier 优先级 (文档 + 代码调整) | 2d | **P0** |
| Phase 2 | 权限继承链 (TIER_INHERITANCE) | 1d | **P0** |
| Phase 3 | 权限批量管理 (用户组系统) | 3d | **P1** |
| Phase 4 | 配置版本控制 (快照 + 回滚) | 2d | **P1** |
| Phase 5 | 多租户权限 (Workspace Override) | 2d | **P2** |

**总工作量**: 约 10 人天

---

## 八、权限边界场景处理

> 本章节定义试用期过期、Tier 降级、以及其他业界常见的边界场景处理规则。

### 8.1 t1 试用期过期场景

#### 8.1.1 试用期状态检测

```typescript
// lib/entitlement/trial.ts

interface TrialStatus {
  isInTrial: boolean;           // 是否在试用期内
  trialDays: number;            // 总试用天数
  daysRemaining: number;        // 剩余天数 (0 = 已过期)
  trialEndDate: Date;           // 试用期结束日期
  registeredAt: Date;           // 注册时间
}

async function getTrialStatus(userId: string): Promise<TrialStatus> {
  const user = await db.fetch('SELECT created_at FROM profiles WHERE user_id = $1', userId);
  const trialDays = await getConfig('trial.default_days') || 7;

  const registeredAt = new Date(user.created_at);
  const trialEndDate = new Date(registeredAt);
  trialEndDate.setDate(trialEndDate.getDate() + trialDays);

  const now = new Date();
  const daysRemaining = Math.max(0, Math.ceil((trialEndDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)));

  return {
    isInTrial: daysRemaining > 0,
    trialDays,
    daysRemaining,
    trialEndDate,
    registeredAt,
  };
}
```

#### 8.1.2 试用期过期后的项目处理

| 场景 | 试用期内 | 试用期过期后 | 处理方式 |
|------|:-------:|:----------:|---------|
| **编辑已有项目** | ✅ 可编辑 | ❌ 只读 | 进入编辑页面时检测，过期则显示只读模式 + 升级提示 |
| **创建新项目** | ✅ 可创建 (≤1) | ❌ 不可创建 | 新建按钮带锁，点击弹 UpgradeModal |
| **复制项目** | ✅ 可复制 (≤1) | ❌ 不可复制 | 复制按钮带锁，点击弹 UpgradeModal |
| **删除项目** | ✅ 可删除 | ✅ 可删除 | 允许删除，减少资源占用 |
| **查看项目列表** | ✅ 可查看 | ✅ 可查看 | 允许查看，项目卡片显示 "只读" 标签 |
| **发布到商城** | ✅ 可发布 | ❌ 不可发布 | Publish 按钮带锁 |
| **导出 PDF/ZIP** | ✅ 可导出 | PDF ✅ / ZIP ❌ | PDF 保留，ZIP 锁定 |

**编辑器只读模式实现**:

```typescript
// components/editor/EditorPage.tsx

function EditorPage({ projectId }: { projectId: string }) {
  const { tier, isWithinTrialPeriod } = useEntitlement();
  const [isReadOnly, setIsReadOnly] = useState(false);

  useEffect(() => {
    // t1 试用期过期 → 只读模式
    if (tier === 't1' && !isWithinTrialPeriod) {
      setIsReadOnly(true);
    }
  }, [tier, isWithinTrialPeriod]);

  if (isReadOnly) {
    return (
      <EditorReadOnlyWrapper>
        <TrialExpiredBanner
          message="试用期已结束，项目为只读模式"
          ctaText="升级解锁编辑"
          onUpgrade={() => openUpgradeModal()}
        />
        <Editor readOnly={true} projectId={projectId} />
      </EditorReadOnlyWrapper>
    );
  }

  return <Editor readOnly={false} projectId={projectId} />;
}
```

#### 8.1.3 试用期状态 UI 提醒

**试用期内提醒 (基于百分比)**:

> 使用百分比而非固定天数，以便 `trial.default_days` 配置变更时自动适配。

| 剩余比例 | 提醒方式 | 提醒频率 | 示例 (7天) |
|:-------:|---------|:-------:|:----------:|
| > 50% | 顶部 Banner (可关闭) | 每天首次登录 | 7-4 天 |
| 15% ~ 50% | 顶部 Banner (不可关闭) + 编辑器内提示 | 每次进入 | 3-1 天 |
| 0% ~ 15% | Modal 弹窗 + Banner | 每次进入 | 当天 |
| 已过期 | 持续 Banner + 只读模式 | 持续显示 | - |

**配置 Key**:

```sql
-- system_configs 配置项 (可在 Admin 调整)
INSERT INTO system_configs (key, value, value_type, config_group, description) VALUES
('trial.default_days', '7', 'integer', 'trial', '默认试用天数'),
('trial.warning_threshold', '0.5', 'float', 'trial', 'warning 样式阈值 (剩余比例 ≤ 50%)'),
('trial.urgent_threshold', '0.15', 'float', 'trial', 'urgent 样式阈值 (剩余比例 ≤ 15%)'),
('trial.show_modal_on_last_day', 'true', 'boolean', 'trial', '最后一天是否弹窗');
```

**UI 组件**:

```typescript
// components/trial/TrialStatusBanner.tsx

interface TrialBannerProps {
  daysRemaining: number;
  totalTrialDays: number;       // 从配置获取
  warningThreshold?: number;    // 默认 0.5 (50%)
  urgentThreshold?: number;     // 默认 0.15 (15%)
  onUpgrade: () => void;
  onDismiss?: () => void;
}

function TrialStatusBanner({
  daysRemaining,
  totalTrialDays,
  warningThreshold = 0.5,
  urgentThreshold = 0.15,
  onUpgrade,
  onDismiss
}: TrialBannerProps) {
  const remainingRatio = daysRemaining / totalTrialDays;

  // 基于百分比判断样式
  const variant = useMemo(() => {
    if (daysRemaining <= 0) return 'expired';
    if (remainingRatio <= urgentThreshold) return 'urgent';
    if (remainingRatio <= warningThreshold) return 'warning';
    return 'info';
  }, [daysRemaining, remainingRatio, warningThreshold, urgentThreshold]);

  const canDismiss = remainingRatio > warningThreshold;

  const messages = {
    urgent: `试用期今天结束！升级后继续使用所有功能`,
    warning: `试用期还剩 ${daysRemaining} 天`,
    info: `试用期还剩 ${daysRemaining} 天，探索所有功能`,
    expired: `试用期已结束，项目已变为只读模式`,
  };

  return (
    <Banner variant={variant} dismissible={canDismiss} onDismiss={onDismiss}>
      <span>{messages[variant]}</span>
      <Button size="sm" onClick={onUpgrade}>
        {daysRemaining <= 0 ? '升级解锁' : daysRemaining <= 1 ? '立即升级' : '查看套餐'}
      </Button>
    </Banner>
  );
}

// components/trial/TrialExpiredModal.tsx

function TrialExpiredModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <ModalHeader>
        <Icon name="clock" className="text-amber-500" />
        试用期已结束
      </ModalHeader>
      <ModalBody>
        <p>您的 7 天免费试用已结束。</p>
        <p className="mt-2">升级后可以：</p>
        <ul className="list-disc ml-4 mt-2">
          <li>继续编辑您的项目</li>
          <li>创建更多项目和文件夹</li>
          <li>使用 AI 生成功能</li>
          <li>导出 ZIP 文件</li>
        </ul>
      </ModalBody>
      <ModalFooter>
        <Button variant="ghost" onClick={onClose}>以后再说</Button>
        <Button variant="primary" onClick={() => openUpgradeModal()}>查看套餐</Button>
      </ModalFooter>
    </Modal>
  );
}
```

#### 8.1.4 试用期配置 Key

```sql
-- system_configs 配置项 (使用百分比阈值，适应不同试用期长度)
INSERT INTO system_configs (key, value, value_type, config_group, description) VALUES
('trial.default_days', '7', 'integer', 'trial', '默认试用天数'),
('trial.warning_threshold', '0.5', 'float', 'trial', 'warning 样式阈值 (剩余比例 ≤ 50%)'),
('trial.urgent_threshold', '0.15', 'float', 'trial', 'urgent 样式阈值 (剩余比例 ≤ 15%)'),
('trial.show_modal_on_expire', 'true', 'boolean', 'trial', '过期当天是否弹窗');

-- 阈值计算示例:
-- 7 天试用期: warning = 剩余 ≤ 3.5 天, urgent = 剩余 ≤ 1 天
-- 14 天试用期: warning = 剩余 ≤ 7 天, urgent = 剩余 ≤ 2 天
-- 30 天试用期: warning = 剩余 ≤ 15 天, urgent = 剩余 ≤ 4.5 天
```

---

### 8.2 Tier 降级场景 (t3→t2, t2→t1)

> 参考业界最佳实践: Notion, Figma, Slack, Dropbox, Canva

#### 8.2.1 降级触发条件

| 触发条件 | 说明 |
|---------|------|
| 订阅到期未续费 | 付费周期结束，未自动续费 |
| 主动取消订阅 | 用户主动取消，当前周期结束后生效 |
| 支付失败 | 连续 N 次扣款失败后自动降级 |
| 退款 | 用户申请退款成功后 |
| Admin 操作 | 管理员手动调整用户 Tier |

#### 8.2.2 降级处理策略 (Graceful Degradation)

**核心原则** (参考业界):

| 原则 | 说明 | 参考产品 |
|------|------|---------|
| **数据不删除** | 用户数据保留，只是无法访问/编辑部分 | Notion, Figma, Dropbox |
| **宽限期** | 降级后给予 7-30 天宽限期处理超额数据 | Slack, Dropbox |
| **最旧优先锁定** | 超额资源按创建时间锁定最旧的 | Notion |
| **核心功能保留** | 查看、导出等基础功能保留 | 所有产品 |
| **明确告知** | 清晰告知哪些受影响、如何处理 | 所有产品 |

#### 8.2.3 各资源降级处理规则

##### Workspace 降级

| 原 Tier | 新 Tier | 原配额 | 新配额 | 处理方式 |
|:-------:|:-------:|:-----:|:-----:|---------|
| t3 | t2 | unlimited | 1 | 保留所有，超额的标记为 "只读" |
| t3 | t1 | unlimited | 1 | 保留所有，超额的标记为 "只读" |
| t2 | t1 | 1 | 1 | 无变化 |

**处理逻辑**:
```typescript
// 降级时处理 Workspace
async function handleWorkspaceDowngrade(userId: string, newTier: string) {
  const maxWorkspaces = TIER_QUOTAS[newTier].maxWorkspaces;
  if (maxWorkspaces === -1) return; // unlimited

  const workspaces = await db.fetch(`
    SELECT id, name, created_at FROM workspaces
    WHERE owner_id = $1
    ORDER BY created_at ASC
  `, userId);

  // 超额的 Workspace 标记为只读
  for (let i = maxWorkspaces; i < workspaces.length; i++) {
    await db.execute(`
      UPDATE workspaces
      SET is_read_only = true,
          read_only_reason = 'tier_downgrade',
          read_only_at = NOW()
      WHERE id = $1
    `, workspaces[i].id);
  }
}
```

##### Project 降级

| 原 Tier | 新 Tier | 原配额 | 新配额 | 处理方式 |
|:-------:|:-------:|:-----:|:-----:|---------|
| t3 | t2 | unlimited | 10 | 保留所有，超额的标记为 "只读" |
| t3 | t1 | unlimited | 1 | 保留所有，超额的标记为 "只读" |
| t2 | t1 | 10 | 1 | 保留所有，超额的标记为 "只读" |

**UI 显示**:
- 只读项目卡片显示 🔒 图标
- 点击只读项目 → 提示 "升级后可编辑"
- 可以查看、导出 PDF，但不能编辑

##### Folder 降级

| 原 Tier | 新 Tier | 原配额 | 新配额 | 处理方式 |
|:-------:|:-------:|:-----:|:-----:|---------|
| t3 | t2 | 200 | 20 | 超额文件夹只读，内部项目只读 |
| t3 | t1 | 200 | 1 | 超额文件夹只读，内部项目只读 |
| t2 | t1 | 20 | 1 | 超额文件夹只读，内部项目只读 |

##### 自定义素材降级

| 原 Tier | 新 Tier | 原配额 | 新配额 | 处理方式 |
|:-------:|:-------:|:-----:|:-----:|---------|
| t3 | t2 | unlimited | 50 | 超额素材只读，可在项目中使用但不能编辑 |
| t3 | t1 | unlimited | 0 | 所有自定义素材只读 |
| t2 | t1 | 50 | 0 | 所有自定义素材只读 |

**注意**: t1 试用期过期后 `max_custom_assets = 0`，但已上传的素材仍可在项目中使用

##### Workspace 成员降级 (邀请的用户)

| 原 Tier | 新 Tier | 能力变化 | 处理方式 |
|:-------:|:-------:|---------|---------|
| t3 | t2/t1 | 失去邀请能力 | 已邀请的成员**保留**，但无法再邀请新成员 |

**业界参考 (Notion, Figma)**:
- 已邀请的成员不会被踢出
- 成员可以继续访问和编辑 (如果项目未被锁定)
- Owner 无法再邀请新成员
- 成员数量不设上限锁定 (仅锁定邀请入口)

##### 商城相关降级

| 功能 | t3 | t2 | t1 | 降级处理 |
|------|:--:|:--:|:--:|---------|
| 浏览商城 | ✅ | ✅ | ❌ | t2→t1: 入口锁定 |
| 购买商城 | ✅ | ✅ | ❌ | t2→t1: 入口锁定，已购买的项目保留 |
| 发布免费 | ✅ | ✅ | ❌ | t2→t1: 入口锁定，已发布的**保留上架** |
| 发布付费 | ✅ | ❌ | ❌ | t3→t2: 入口锁定，已发布的**保留上架** |

**已发布商品处理**:
- 降级后已发布的商品**继续保持上架**
- 用户仍可获得销售收入
- 但无法发布新商品或修改已发布商品的价格
- 可以下架已发布的商品

#### 8.2.4 宽限期 (Grace Period)

```sql
-- 宽限期配置
INSERT INTO system_configs (key, value, value_type, config_group, description) VALUES
('downgrade.grace_period_days', '7', 'integer', 'downgrade', '降级宽限期天数'),
('downgrade.lock_after_grace', 'true', 'boolean', 'downgrade', '宽限期后是否锁定超额资源');
```

**宽限期流程**:

```
Day 0: 降级生效
├── 发送邮件通知
├── 应用内 Banner 提醒
├── 超额资源标记为 "即将锁定"
└── 用户可正常使用所有资源

Day 1-6: 宽限期
├── 每天发送提醒邮件 (可配置)
├── Banner 显示剩余天数
└── 用户可正常使用，建议整理资源

Day 7: 宽限期结束
├── 超额资源正式锁定为 "只读"
├── 发送最终通知邮件
└── 锁定资源显示 🔒 图标
```

#### 8.2.5 降级通知邮件模板

```typescript
// 降级通知邮件
const downgradeEmailTemplate = {
  subject: '您的 Make Decodables 订阅已变更',
  body: `
    亲爱的 {{userName}}，

    您的订阅已从 {{oldTier}} 变更为 {{newTier}}。

    以下是受影响的内容：
    {{#if exceededWorkspaces}}
    • Workspace: {{exceededWorkspaces}} 个将在 {{gracePeriodDays}} 天后变为只读
    {{/if}}
    {{#if exceededProjects}}
    • 项目: {{exceededProjects}} 个将在 {{gracePeriodDays}} 天后变为只读
    {{/if}}
    {{#if exceededFolders}}
    • 文件夹: {{exceededFolders}} 个将在 {{gracePeriodDays}} 天后变为只读
    {{/if}}

    在宽限期内，您可以：
    • 导出项目数据
    • 删除不需要的项目
    • 重新订阅以保留所有访问权限

    如有任何问题，请联系我们的客服团队。

    Make Decodables 团队
  `
};
```

#### 8.2.6 降级处理服务

```python
# domains/entitlement/services/downgrade_service.py

from datetime import datetime, timedelta
from typing import List, Dict

class DowngradeService:
    """Tier 降级处理服务"""

    async def process_downgrade(
        self,
        user_id: str,
        old_tier: str,
        new_tier: str,
        reason: str  # 'subscription_expired' | 'cancelled' | 'payment_failed' | 'refund' | 'admin'
    ) -> Dict:
        """处理 Tier 降级"""

        # 1. 获取配额变化
        old_quotas = TIER_QUOTAS[old_tier]
        new_quotas = TIER_QUOTAS[new_tier]

        # 2. 检查超额资源
        exceeded = await self._check_exceeded_resources(user_id, new_quotas)

        # 3. 获取宽限期配置
        grace_days = await get_config('downgrade.grace_period_days') or 7
        grace_end = datetime.now() + timedelta(days=grace_days)

        # 4. 标记超额资源 (宽限期内)
        await self._mark_resources_pending_lock(user_id, exceeded, grace_end)

        # 5. 记录降级事件
        await self._log_downgrade_event(user_id, old_tier, new_tier, reason, exceeded)

        # 6. 发送通知
        await self._send_downgrade_notification(user_id, old_tier, new_tier, exceeded, grace_end)

        # 7. 调度宽限期结束任务
        await self._schedule_grace_period_end(user_id, grace_end)

        return {
            'old_tier': old_tier,
            'new_tier': new_tier,
            'exceeded_resources': exceeded,
            'grace_period_end': grace_end
        }

    async def _check_exceeded_resources(self, user_id: str, new_quotas: Dict) -> Dict:
        """检查超额资源"""
        exceeded = {
            'workspaces': [],
            'projects': [],
            'folders': [],
            'custom_assets': []
        }

        # 检查 Workspace
        if new_quotas['max_workspaces'] != -1:
            workspaces = await db.fetch_all("""
                SELECT id, name FROM workspaces
                WHERE owner_id = $1
                ORDER BY created_at ASC
            """, user_id)

            if len(workspaces) > new_quotas['max_workspaces']:
                exceeded['workspaces'] = [
                    w['id'] for w in workspaces[new_quotas['max_workspaces']:]
                ]

        # 检查 Projects
        if new_quotas['max_projects'] != -1:
            projects = await db.fetch_all("""
                SELECT id, name FROM projects
                WHERE owner_id = $1
                ORDER BY created_at ASC
            """, user_id)

            if len(projects) > new_quotas['max_projects']:
                exceeded['projects'] = [
                    p['id'] for p in projects[new_quotas['max_projects']:]
                ]

        # 检查 Folders
        if new_quotas['max_folders'] != -1:
            folders = await db.fetch_all("""
                SELECT id, name FROM folders
                WHERE owner_id = $1
                ORDER BY created_at ASC
            """, user_id)

            if len(folders) > new_quotas['max_folders']:
                exceeded['folders'] = [
                    f['id'] for f in folders[new_quotas['max_folders']:]
                ]

        # 检查自定义素材
        if new_quotas['max_custom_assets'] != -1:
            assets = await db.fetch_all("""
                SELECT id FROM custom_assets
                WHERE owner_id = $1
                ORDER BY created_at ASC
            """, user_id)

            if len(assets) > new_quotas['max_custom_assets']:
                exceeded['custom_assets'] = [
                    a['id'] for a in assets[new_quotas['max_custom_assets']:]
                ]

        return exceeded

    async def _mark_resources_pending_lock(
        self,
        user_id: str,
        exceeded: Dict,
        grace_end: datetime
    ):
        """标记资源为待锁定状态"""
        for ws_id in exceeded['workspaces']:
            await db.execute("""
                UPDATE workspaces SET
                    pending_lock = true,
                    pending_lock_at = $1,
                    lock_reason = 'tier_downgrade'
                WHERE id = $2
            """, grace_end, ws_id)

        for proj_id in exceeded['projects']:
            await db.execute("""
                UPDATE projects SET
                    pending_lock = true,
                    pending_lock_at = $1,
                    lock_reason = 'tier_downgrade'
                WHERE id = $2
            """, grace_end, proj_id)

        # ... 类似处理 folders 和 custom_assets

    async def execute_grace_period_end(self, user_id: str):
        """宽限期结束，正式锁定资源"""
        await db.execute("""
            UPDATE workspaces SET
                is_read_only = true,
                read_only_at = NOW(),
                pending_lock = false
            WHERE owner_id = $1 AND pending_lock = true
        """, user_id)

        await db.execute("""
            UPDATE projects SET
                is_read_only = true,
                read_only_at = NOW(),
                pending_lock = false
            WHERE owner_id = $1 AND pending_lock = true
        """, user_id)

        # ... 类似处理其他资源

        # 发送锁定完成通知
        await self._send_lock_completed_notification(user_id)
```

---

### 8.3 其他业界常见边界场景

#### 8.3.1 升级场景 (Upgrade)

| 场景 | 处理方式 |
|------|---------|
| t1→t2 | 立即解锁 t2 功能，只读项目恢复可编辑 |
| t1→t3 | 立即解锁 t3 功能，只读项目恢复可编辑 |
| t2→t3 | 立即解锁 t3 功能 |
| 试用期内升级 | 试用期状态取消，进入正式订阅 |

**升级处理**:
```typescript
async function handleUpgrade(userId: string, newTier: string) {
  // 1. 解锁所有只读资源
  await db.execute(`
    UPDATE workspaces SET is_read_only = false, read_only_at = NULL
    WHERE owner_id = $1 AND read_only_reason = 'tier_downgrade'
  `, userId);

  await db.execute(`
    UPDATE projects SET is_read_only = false, read_only_at = NULL
    WHERE owner_id = $1 AND read_only_reason = 'tier_downgrade'
  `, userId);

  // 2. 取消待锁定状态
  await db.execute(`
    UPDATE workspaces SET pending_lock = false, pending_lock_at = NULL
    WHERE owner_id = $1
  `, userId);

  // 3. 发送升级成功通知
  await sendUpgradeNotification(userId, newTier);
}
```

#### 8.3.2 支付失败重试

| 重试次数 | 间隔 | 操作 |
|:-------:|:----:|------|
| 第 1 次 | 立即 | 自动重试 |
| 第 2 次 | 3 天后 | 自动重试 + 邮件通知 |
| 第 3 次 | 7 天后 | 自动重试 + 邮件警告 |
| 第 4 次 | 14 天后 | 最终重试 + 降级预警 |
| 全部失败 | - | 自动降级 + 宽限期开始 |

#### 8.3.3 账户删除 / 数据导出

| 场景 | 处理方式 |
|------|---------|
| **数据导出** | 任何 Tier 都可以导出自己的项目数据 (PDF/JSON) |
| **账户删除请求** | 发起后 30 天内可取消，30 天后永久删除 |
| **删除后数据** | 所有数据永久删除，商城已发布商品下架 |

#### 8.3.4 并发订阅冲突

| 场景 | 处理方式 |
|------|---------|
| 重复订阅同一 Plan | 拒绝，提示已订阅 |
| 订阅更低 Tier | 确认降级意图，当前周期结束后生效 |
| 订阅更高 Tier | 立即升级，按比例退还原订阅余额 |
| 订阅不同周期 | 当前周期结束后切换 |

#### 8.3.5 家庭/团队共享 (未来)

| 场景 | 处理方式 |
|------|---------|
| Owner 降级 | 所有成员权限跟随降级 |
| Owner 升级 | 所有成员权限跟随升级 |
| 成员自己有订阅 | 取较高的 Tier |
| 成员离开团队 | 回退到自己的订阅 Tier |

#### 8.3.6 促销码 / 优惠

| 场景 | 处理方式 |
|------|---------|
| 限时免费 Pro | 创建 `user_feature_overrides` 带过期时间 |
| 教育优惠 | 用户组 `edu_discount`，长期有效 |
| 推荐奖励 | 延长订阅时长 或 积分奖励 |
| 黑五折扣 | 通过 Stripe Coupon 处理 |

#### 8.3.7 异常场景处理

| 场景 | 处理方式 |
|------|---------|
| Stripe Webhook 延迟 | 本地缓存 Tier，Webhook 到达后同步 |
| 数据库不一致 | 定时任务检查 Stripe 状态同步 |
| 时区问题 | 所有时间使用 UTC，前端转换显示 |
| 试用期中途升级又取消 | 恢复试用期剩余天数 (可配置) |

---

### 8.4 场景支持矩阵汇总

| 场景 | 支持情况 | 说明 |
|------|:--------:|------|
| t1 试用期过期 - 项目只读 | ✅ | 进入编辑器时检测 |
| t1 试用期过期 - 禁止新建/复制 | ✅ | 按钮带锁 |
| t1 试用期过期 - 允许删除 | ✅ | 减少资源占用 |
| t1 试用期过期 - 状态提醒 | ✅ | Banner + Modal |
| Tier 降级 - 数据保留 | ✅ | 只锁定不删除 |
| Tier 降级 - 宽限期 | ✅ | 可配置天数 |
| Tier 降级 - 超额锁定 | ✅ | 最旧优先 |
| Tier 降级 - 成员保留 | ✅ | 已邀请的不踢出 |
| Tier 降级 - 商城商品保留 | ✅ | 继续上架 |
| Tier 升级 - 立即生效 | ✅ | 解锁所有资源 |
| 支付失败重试 | ✅ | 4 次重试机制 |
| 数据导出 | ✅ | 任何 Tier 可导出 |

---

## 九、业界最佳实践补充场景

> 本章节补充业界 SaaS 产品常见但当前文档未完整覆盖的场景，参考 Stripe, Spotify, Netflix, Notion, Figma, Canva, Slack, Dropbox, Adobe 等产品的最佳实践。

---

### 9.1 订阅暂停 (Subscription Pause) 🔴 P0

> 参考: Spotify, Netflix, Adobe Creative Cloud

#### 9.1.1 功能说明

允许用户临时暂停订阅，暂停期间不扣费，权限降为 t1。

#### 9.1.2 暂停规则

| 规则 | 值 | 说明 |
|------|-----|------|
| 最短暂停时长 | 1 个月 | 暂停至少 1 个完整计费周期 |
| 最长暂停时长 | 3 个月 | 单次暂停最长 3 个月 |
| 年度暂停次数 | 2 次 | 每个自然年最多暂停 2 次 |
| 暂停间隔 | 3 个月 | 两次暂停之间至少间隔 3 个月 |
| 年付用户 | 不支持 | 年付用户不支持暂停 (可申请退款) |

#### 9.1.3 暂停期间处理

| 项目 | 处理方式 |
|------|---------|
| **Tier 权限** | 降为 t1 (非试用期状态) |
| **月度积分** | 不发放 |
| **永久积分** | 保留，可继续使用 |
| **项目数据** | 全部保留，超额部分只读 |
| **商城商品** | 已发布的保持上架 |
| **自动恢复** | 暂停结束自动恢复订阅 + 扣费 |

#### 9.1.4 数据库设计

```sql
-- subscriptions 表新增字段
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS
    pause_start_at TIMESTAMPTZ,          -- 暂停开始时间
    pause_end_at TIMESTAMPTZ,            -- 暂停结束时间 (预设)
    pause_reason TEXT,                   -- 暂停原因 (用户反馈)
    pause_count_this_year INT DEFAULT 0; -- 今年已暂停次数

-- 暂停历史记录表
CREATE TABLE IF NOT EXISTS subscription_pause_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
    subscription_id TEXT NOT NULL,
    pause_start_at TIMESTAMPTZ NOT NULL,
    pause_end_at TIMESTAMPTZ,            -- 实际结束时间
    planned_end_at TIMESTAMPTZ NOT NULL, -- 计划结束时间
    reason TEXT,
    resumed_early BOOLEAN DEFAULT FALSE, -- 是否提前恢复
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_pause_history_user ON subscription_pause_history(user_id);
```

#### 9.1.5 配置项

```sql
INSERT INTO system_configs (key, value, value_type, config_group, description) VALUES
('pause.min_duration_months', '1', 'integer', 'subscription', '最短暂停月数'),
('pause.max_duration_months', '3', 'integer', 'subscription', '最长暂停月数'),
('pause.max_per_year', '2', 'integer', 'subscription', '每年最大暂停次数'),
('pause.min_interval_months', '3', 'integer', 'subscription', '两次暂停最小间隔'),
('pause.allow_annual', 'false', 'boolean', 'subscription', '年付是否允许暂停');
```

#### 9.1.6 服务实现

```python
# domains/subscription/services/pause_service.py

class SubscriptionPauseService:
    """订阅暂停服务"""

    async def pause_subscription(
        self,
        user_id: str,
        duration_months: int,
        reason: str = None
    ) -> Dict:
        """暂停订阅"""

        # 1. 检查是否允许暂停
        validation = await self._validate_pause_eligibility(user_id, duration_months)
        if not validation['eligible']:
            raise PauseNotAllowedError(validation['reason'])

        # 2. 获取当前订阅
        subscription = await self._get_active_subscription(user_id)

        # 3. 计算暂停时间
        pause_start = self._calculate_pause_start(subscription)
        pause_end = pause_start + timedelta(days=duration_months * 30)

        # 4. 通知 Stripe 暂停 (使用 subscription_schedule)
        await self._pause_stripe_subscription(subscription.stripe_subscription_id, pause_end)

        # 5. 更新数据库
        await db.execute("""
            UPDATE subscriptions SET
                status = 'paused',
                pause_start_at = $1,
                pause_end_at = $2,
                pause_reason = $3,
                pause_count_this_year = pause_count_this_year + 1
            WHERE user_id = $4
        """, pause_start, pause_end, reason, user_id)

        # 6. 记录暂停历史
        await db.execute("""
            INSERT INTO subscription_pause_history
            (user_id, subscription_id, pause_start_at, planned_end_at, reason)
            VALUES ($1, $2, $3, $4, $5)
        """, user_id, subscription.id, pause_start, pause_end, reason)

        # 7. 触发降级处理 (临时降为 t1)
        await self.downgrade_service.process_downgrade(
            user_id,
            old_tier=subscription.tier,
            new_tier='t1',
            reason='subscription_paused'
        )

        # 8. 发送确认邮件
        await self._send_pause_confirmation_email(user_id, pause_start, pause_end)

        return {
            'status': 'paused',
            'pause_start': pause_start,
            'pause_end': pause_end,
            'auto_resume': True
        }

    async def resume_subscription(self, user_id: str) -> Dict:
        """提前恢复订阅"""

        subscription = await self._get_paused_subscription(user_id)
        if not subscription:
            raise SubscriptionNotPausedError()

        # 1. 恢复 Stripe 订阅
        await self._resume_stripe_subscription(subscription.stripe_subscription_id)

        # 2. 更新数据库
        await db.execute("""
            UPDATE subscriptions SET
                status = 'active',
                pause_start_at = NULL,
                pause_end_at = NULL
            WHERE user_id = $1
        """, user_id)

        # 3. 标记历史记录
        await db.execute("""
            UPDATE subscription_pause_history SET
                pause_end_at = NOW(),
                resumed_early = TRUE
            WHERE user_id = $1 AND pause_end_at IS NULL
        """, user_id)

        # 4. 恢复 Tier 权限
        await self.upgrade_service.process_upgrade(user_id, subscription.tier)

        # 5. 发送恢复确认邮件
        await self._send_resume_confirmation_email(user_id)

        return {'status': 'active', 'tier': subscription.tier}

    async def _validate_pause_eligibility(self, user_id: str, duration_months: int) -> Dict:
        """验证是否有资格暂停"""

        subscription = await self._get_active_subscription(user_id)

        # 检查是否年付
        if subscription.billing_interval == 'year':
            allow_annual = await get_config('pause.allow_annual')
            if not allow_annual:
                return {'eligible': False, 'reason': '年付订阅不支持暂停，如需取消请联系客服'}

        # 检查暂停次数
        max_per_year = await get_config('pause.max_per_year') or 2
        if subscription.pause_count_this_year >= max_per_year:
            return {'eligible': False, 'reason': f'今年已暂停 {max_per_year} 次，无法再次暂停'}

        # 检查暂停间隔
        last_pause = await db.fetch_one("""
            SELECT pause_end_at FROM subscription_pause_history
            WHERE user_id = $1 ORDER BY pause_end_at DESC LIMIT 1
        """, user_id)

        if last_pause:
            min_interval = await get_config('pause.min_interval_months') or 3
            min_resume_date = last_pause['pause_end_at'] + timedelta(days=min_interval * 30)
            if datetime.now() < min_resume_date:
                return {'eligible': False, 'reason': f'距离上次暂停未满 {min_interval} 个月'}

        # 检查时长
        min_duration = await get_config('pause.min_duration_months') or 1
        max_duration = await get_config('pause.max_duration_months') or 3

        if duration_months < min_duration or duration_months > max_duration:
            return {'eligible': False, 'reason': f'暂停时长需在 {min_duration}-{max_duration} 个月之间'}

        return {'eligible': True, 'reason': None}
```

#### 9.1.7 UI 入口

```typescript
// 设置页 - 订阅管理
// /settings/subscription

interface PauseSubscriptionModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentTier: string;
  onPause: (months: number, reason?: string) => Promise<void>;
}

function PauseSubscriptionModal({ isOpen, onClose, currentTier, onPause }: PauseSubscriptionModalProps) {
  const [months, setMonths] = useState(1);
  const [reason, setReason] = useState('');

  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <ModalHeader>暂停订阅</ModalHeader>
      <ModalBody>
        <Alert variant="warning">
          暂停期间，您的账户将降为免费版，部分功能将受限。
          暂停结束后将自动恢复订阅并扣费。
        </Alert>

        <div className="mt-4">
          <Label>暂停时长</Label>
          <Select value={months} onChange={(v) => setMonths(Number(v))}>
            <Option value={1}>1 个月</Option>
            <Option value={2}>2 个月</Option>
            <Option value={3}>3 个月</Option>
          </Select>
        </div>

        <div className="mt-4">
          <Label>暂停原因 (可选)</Label>
          <Textarea
            placeholder="告诉我们为什么暂停，帮助我们改进产品"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </div>
      </ModalBody>
      <ModalFooter>
        <Button variant="ghost" onClick={onClose}>取消</Button>
        <Button variant="warning" onClick={() => onPause(months, reason)}>
          确认暂停
        </Button>
      </ModalFooter>
    </Modal>
  );
}
```

---

### 9.2 年付/月付切换 (Billing Cycle Switch) 🔴 P0

> 参考: 几乎所有 SaaS 产品

#### 9.2.1 切换规则

| 切换方向 | 生效时间 | 费用处理 |
|---------|---------|---------|
| **月付→年付** | 立即生效 | 按比例抵扣当月剩余天数 |
| **年付→月付** | 当前周期结束后 | 不退款 (或可选按比例退款) |
| **同周期不同 Tier** | 见 8.3.4 并发订阅 | - |

#### 9.2.2 月付→年付计算示例

```
当前订阅: t2 月付 $6.9/月
已使用: 15 天 (当月 30 天)
剩余价值: $6.9 × (15/30) = $3.45

目标订阅: t2 年付 $69/年 (相当于 $5.75/月)

实际支付: $69 - $3.45 = $65.55
```

#### 9.2.3 年付→月付处理

```
当前订阅: t3 年付 $99/年
已使用: 6 个月
剩余月数: 6 个月
剩余价值: $99 × (6/12) = $49.50

选项 A (默认): 当前周期结束后切换为月付，不退款
选项 B (可选): 立即切换，退还 $49.50 到账户余额
```

#### 9.2.4 配置项

```sql
INSERT INTO system_configs (key, value, value_type, config_group, description) VALUES
('billing.allow_annual_to_monthly_refund', 'false', 'boolean', 'billing', '年付转月付是否允许退款'),
('billing.proration_behavior', 'create_prorations', 'string', 'billing', 'Stripe proration 策略'),
('billing.switch_preview_enabled', 'true', 'boolean', 'billing', '是否显示切换预览');
```

#### 9.2.5 服务实现

```python
# domains/subscription/services/billing_cycle_service.py

class BillingCycleService:
    """计费周期切换服务"""

    async def preview_switch(
        self,
        user_id: str,
        target_interval: str,  # 'month' | 'year'
        target_tier: str = None  # 可选同时切换 Tier
    ) -> Dict:
        """预览切换费用"""

        subscription = await self._get_active_subscription(user_id)
        target_tier = target_tier or subscription.tier

        # 获取目标价格
        target_price = await self._get_price(target_tier, target_interval)

        # 计算剩余价值
        remaining_value = self._calculate_remaining_value(subscription)

        # 计算应付金额
        if subscription.billing_interval == 'month' and target_interval == 'year':
            # 月付→年付: 立即生效，抵扣剩余
            amount_due = target_price['amount'] - remaining_value
            effective_date = datetime.now()
        elif subscription.billing_interval == 'year' and target_interval == 'month':
            # 年付→月付: 周期结束后生效
            amount_due = target_price['amount']  # 下个月开始收费
            effective_date = subscription.current_period_end

            # 可选退款
            allow_refund = await get_config('billing.allow_annual_to_monthly_refund')
            if allow_refund:
                refund_amount = remaining_value
            else:
                refund_amount = 0
        else:
            # 同周期
            amount_due = target_price['amount']
            effective_date = subscription.current_period_end

        return {
            'current': {
                'tier': subscription.tier,
                'interval': subscription.billing_interval,
                'price': subscription.price,
                'remaining_days': self._calculate_remaining_days(subscription),
                'remaining_value': remaining_value
            },
            'target': {
                'tier': target_tier,
                'interval': target_interval,
                'price': target_price['amount']
            },
            'transition': {
                'effective_date': effective_date,
                'amount_due': max(0, amount_due),
                'refund_amount': refund_amount if 'refund_amount' in locals() else 0,
                'proration_applied': amount_due != target_price['amount']
            }
        }

    async def execute_switch(
        self,
        user_id: str,
        target_interval: str,
        target_tier: str = None
    ) -> Dict:
        """执行切换"""

        subscription = await self._get_active_subscription(user_id)
        target_tier = target_tier or subscription.tier

        # 获取 Stripe Price ID
        price_id = await self._get_stripe_price_id(target_tier, target_interval)

        if subscription.billing_interval == 'month' and target_interval == 'year':
            # 月付→年付: 立即切换
            await stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                items=[{'id': subscription.stripe_item_id, 'price': price_id}],
                proration_behavior='create_prorations',
                billing_cycle_anchor='now'
            )

            # 更新本地数据
            await self._update_subscription(user_id, target_tier, target_interval)

            return {'status': 'switched', 'effective': 'immediate'}

        elif subscription.billing_interval == 'year' and target_interval == 'month':
            # 年付→月付: 周期结束后切换
            await stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                items=[{'id': subscription.stripe_item_id, 'price': price_id}],
                proration_behavior='none',
                billing_cycle_anchor='unchanged'
            )

            # 记录待切换
            await db.execute("""
                UPDATE subscriptions SET
                    pending_interval_change = $1,
                    pending_tier_change = $2
                WHERE user_id = $3
            """, target_interval, target_tier, user_id)

            return {
                'status': 'scheduled',
                'effective': subscription.current_period_end.isoformat()
            }

    def _calculate_remaining_value(self, subscription) -> float:
        """计算剩余价值"""
        total_days = (subscription.current_period_end - subscription.current_period_start).days
        used_days = (datetime.now() - subscription.current_period_start).days
        remaining_days = total_days - used_days

        daily_rate = subscription.price / total_days
        return round(daily_rate * remaining_days, 2)
```

#### 9.2.6 UI 组件

```typescript
// components/billing/BillingCycleSwitchCard.tsx

interface SwitchPreview {
  current: { tier: string; interval: string; price: number; remaining_value: number };
  target: { tier: string; interval: string; price: number };
  transition: { effective_date: string; amount_due: number; proration_applied: boolean };
}

function BillingCycleSwitchCard() {
  const { subscription } = useSubscription();
  const [preview, setPreview] = useState<SwitchPreview | null>(null);
  const [targetInterval, setTargetInterval] = useState<'month' | 'year'>('year');

  const handlePreview = async () => {
    const result = await api.post('/subscriptions/switch/preview', {
      target_interval: targetInterval
    });
    setPreview(result.data);
  };

  return (
    <Card>
      <CardHeader>
        <h3>切换计费周期</h3>
      </CardHeader>
      <CardContent>
        <div className="flex gap-4">
          <Button
            variant={targetInterval === 'month' ? 'default' : 'outline'}
            onClick={() => setTargetInterval('month')}
          >
            月付
          </Button>
          <Button
            variant={targetInterval === 'year' ? 'default' : 'outline'}
            onClick={() => setTargetInterval('year')}
          >
            年付 (省 17%)
          </Button>
        </div>

        {preview && (
          <div className="mt-4 p-4 bg-slate-50 rounded">
            <div className="flex justify-between">
              <span>当前剩余价值</span>
              <span className="text-green-600">-${preview.current.remaining_value}</span>
            </div>
            <div className="flex justify-between">
              <span>{preview.target.interval === 'year' ? '年付' : '月付'}价格</span>
              <span>${preview.target.price}</span>
            </div>
            <Divider />
            <div className="flex justify-between font-semibold">
              <span>应付金额</span>
              <span>${preview.transition.amount_due}</span>
            </div>
            <p className="text-sm text-slate-500 mt-2">
              生效时间: {new Date(preview.transition.effective_date).toLocaleDateString()}
            </p>
          </div>
        )}

        <Button className="mt-4 w-full" onClick={handlePreview}>
          {preview ? '确认切换' : '查看费用'}
        </Button>
      </CardContent>
    </Card>
  );
}
```

---

### 9.3 积分完整生命周期管理 🔴 P0

> 补充积分过期、清零、退款扣回等细节规则

#### 9.3.1 积分类型完整定义

| 类型 | 来源 | 有效期 | 过期规则 | 退款处理 |
|------|------|--------|---------|---------|
| **月度积分** | 订阅发放 | 当月有效 | 每月 1 日清零 | 不扣回 |
| **永久积分** | 充值购买 | 永久有效 | 12 个月不活跃则冻结 | 按比例扣回 |
| **赠送积分** | 注册/活动 | 90 天 | 过期作废 | 不扣回 |
| **补偿积分** | 客服发放 | 永久有效 | 不过期 | 不扣回 |

#### 9.3.2 积分冻结规则

```
账户不活跃定义: 连续 12 个月无登录、无消费、无充值

冻结处理:
1. 冻结前 30 天发送预警邮件
2. 冻结前 7 天发送最后提醒
3. 冻结后积分状态变为 'frozen'
4. 重新登录后自动解冻 (需验证身份)
5. 冻结期间不参与扣费优先级
```

#### 9.3.3 退款积分扣回规则

```
场景: 用户购买 500 积分包 ($13.46)，使用了 200 积分后申请退款

计算:
- 购买积分: 500
- 已使用: 200
- 剩余: 300
- 退款金额: $13.46 × (300/500) = $8.08

处理:
1. 退款 $8.08 到原支付方式
2. 扣除 300 永久积分
3. 如果当前永久积分 < 300，记录为负债
4. 负债在下次充值时自动扣除

负债上限:
- 负债不能超过 500 积分
- 超过需人工审核
```

#### 9.3.4 数据库设计

```sql
-- 积分表增强
ALTER TABLE user_credits ADD COLUMN IF NOT EXISTS
    gift_credits INT DEFAULT 0,           -- 赠送积分
    gift_credits_expire_at TIMESTAMPTZ,   -- 赠送积分过期时间
    compensation_credits INT DEFAULT 0,   -- 补偿积分
    frozen_credits INT DEFAULT 0,         -- 冻结积分
    credit_debt INT DEFAULT 0,            -- 积分负债
    last_activity_at TIMESTAMPTZ;         -- 最后活跃时间

-- 积分变动记录表增强
ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS
    credit_type TEXT DEFAULT 'permanent', -- 'monthly' | 'permanent' | 'gift' | 'compensation'
    expires_at TIMESTAMPTZ,               -- 过期时间 (赠送积分)
    refund_related BOOLEAN DEFAULT FALSE; -- 是否退款相关

-- 积分冻结历史
CREATE TABLE IF NOT EXISTS credit_freeze_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES profiles(user_id),
    frozen_amount INT NOT NULL,
    freeze_reason TEXT NOT NULL,         -- 'inactivity' | 'fraud_suspected' | 'admin'
    frozen_at TIMESTAMPTZ DEFAULT NOW(),
    unfrozen_at TIMESTAMPTZ,
    unfrozen_by TEXT                     -- 'user_login' | 'admin' | 'auto'
);
```

#### 9.3.5 配置项

```sql
INSERT INTO system_configs (key, value, value_type, config_group, description) VALUES
('credits.gift_expire_days', '90', 'integer', 'credits', '赠送积分有效期(天)'),
('credits.inactive_freeze_months', '12', 'integer', 'credits', '不活跃冻结月数'),
('credits.freeze_warning_days', '30', 'integer', 'credits', '冻结前预警天数'),
('credits.max_debt', '500', 'integer', 'credits', '最大积分负债'),
('credits.refund_deduct_ratio', '1.0', 'float', 'credits', '退款积分扣除比例');
```

#### 9.3.6 积分扣费优先级 (更新)

```
扣费顺序 (优先扣即将过期的):
1. 赠送积分 (按过期时间排序，最早过期的先扣)
2. 月度积分 (本月底过期)
3. 永久积分 (不过期)
4. 补偿积分 (不过期，保底)

负债处理:
- 如有负债，新充值的永久积分先抵扣负债
- 负债不影响月度积分使用
```

#### 9.3.7 服务实现

```python
# domains/credits/services/credit_lifecycle_service.py

class CreditLifecycleService:
    """积分生命周期管理"""

    async def deduct_credits(self, user_id: str, amount: int, reason: str) -> Dict:
        """扣除积分 (按优先级)"""

        credits = await self._get_user_credits(user_id)
        remaining = amount
        deductions = []

        # 1. 优先扣赠送积分 (按过期时间)
        if remaining > 0 and credits.gift_credits > 0:
            deduct = min(remaining, credits.gift_credits)
            remaining -= deduct
            deductions.append({'type': 'gift', 'amount': deduct})

        # 2. 扣月度积分
        if remaining > 0 and credits.credits_monthly > 0:
            deduct = min(remaining, credits.credits_monthly)
            remaining -= deduct
            deductions.append({'type': 'monthly', 'amount': deduct})

        # 3. 扣永久积分
        if remaining > 0 and credits.credits_permanent > 0:
            deduct = min(remaining, credits.credits_permanent)
            remaining -= deduct
            deductions.append({'type': 'permanent', 'amount': deduct})

        # 4. 扣补偿积分
        if remaining > 0 and credits.compensation_credits > 0:
            deduct = min(remaining, credits.compensation_credits)
            remaining -= deduct
            deductions.append({'type': 'compensation', 'amount': deduct})

        if remaining > 0:
            raise InsufficientCreditsError(f'积分不足，缺少 {remaining}')

        # 执行扣除
        await self._execute_deductions(user_id, deductions, reason)

        return {'deducted': amount, 'breakdown': deductions}

    async def handle_refund_credit_deduction(
        self,
        user_id: str,
        purchase_id: str,
        refund_amount: float,
        original_amount: float,
        original_credits: int
    ) -> Dict:
        """处理退款时的积分扣回"""

        # 计算应扣积分
        refund_ratio = refund_amount / original_amount
        credits_to_deduct = int(original_credits * refund_ratio)

        credits = await self._get_user_credits(user_id)

        if credits.credits_permanent >= credits_to_deduct:
            # 直接扣除
            await db.execute("""
                UPDATE user_credits SET
                    credits_permanent = credits_permanent - $1
                WHERE user_id = $2
            """, credits_to_deduct, user_id)

            debt_created = 0
        else:
            # 创建负债
            available = credits.credits_permanent
            debt_created = credits_to_deduct - available

            # 检查负债上限
            max_debt = await get_config('credits.max_debt') or 500
            total_debt = credits.credit_debt + debt_created

            if total_debt > max_debt:
                raise DebtLimitExceededError(f'积分负债超过上限 {max_debt}')

            await db.execute("""
                UPDATE user_credits SET
                    credits_permanent = 0,
                    credit_debt = credit_debt + $1
                WHERE user_id = $2
            """, debt_created, user_id)

        # 记录交易
        await self._log_transaction(
            user_id,
            -credits_to_deduct,
            'refund_deduction',
            f'退款扣回，关联订单: {purchase_id}'
        )

        return {
            'deducted': credits_to_deduct,
            'debt_created': debt_created,
            'current_debt': credits.credit_debt + debt_created
        }

    async def check_and_freeze_inactive(self):
        """定时任务: 检查并冻结不活跃账户"""

        inactive_months = await get_config('credits.inactive_freeze_months') or 12
        cutoff_date = datetime.now() - timedelta(days=inactive_months * 30)

        inactive_users = await db.fetch_all("""
            SELECT user_id, credits_permanent, gift_credits, compensation_credits
            FROM user_credits
            WHERE last_activity_at < $1
            AND (credits_permanent > 0 OR gift_credits > 0 OR compensation_credits > 0)
            AND frozen_credits = 0
        """, cutoff_date)

        for user in inactive_users:
            total_to_freeze = (
                user['credits_permanent'] +
                user['gift_credits'] +
                user['compensation_credits']
            )

            await db.execute("""
                UPDATE user_credits SET
                    frozen_credits = $1,
                    credits_permanent = 0,
                    gift_credits = 0,
                    compensation_credits = 0
                WHERE user_id = $2
            """, total_to_freeze, user['user_id'])

            await db.execute("""
                INSERT INTO credit_freeze_history (user_id, frozen_amount, freeze_reason)
                VALUES ($1, $2, 'inactivity')
            """, user['user_id'], total_to_freeze)

            await self._send_freeze_notification(user['user_id'], total_to_freeze)

    async def unfreeze_on_login(self, user_id: str):
        """用户登录时解冻积分"""

        credits = await self._get_user_credits(user_id)

        if credits.frozen_credits > 0:
            await db.execute("""
                UPDATE user_credits SET
                    credits_permanent = credits_permanent + frozen_credits,
                    frozen_credits = 0,
                    last_activity_at = NOW()
                WHERE user_id = $1
            """, user_id)

            await db.execute("""
                UPDATE credit_freeze_history SET
                    unfrozen_at = NOW(),
                    unfrozen_by = 'user_login'
                WHERE user_id = $1 AND unfrozen_at IS NULL
            """, user_id)
```

---

### 9.4 订阅续期提醒 (Renewal Reminders) 🔴 P0

> 参考: 所有 SaaS 产品

#### 9.4.1 提醒规则

| 时间点 | 渠道 | 内容 |
|--------|------|------|
| 续期前 7 天 | 邮件 | 温和提醒，显示续期日期和金额 |
| 续期前 3 天 | 邮件 + 应用内 | 提醒检查支付方式 |
| 续期前 1 天 | 邮件 + 应用内 + Push | 最后提醒 |
| 续期当天 | 应用内 | 显示扣费成功/失败状态 |

#### 9.4.2 配置项

```sql
INSERT INTO system_configs (key, value, value_type, config_group, description) VALUES
('renewal.reminder_days', '[7, 3, 1]', 'json', 'subscription', '续期提醒天数数组'),
('renewal.email_enabled', 'true', 'boolean', 'subscription', '是否发送邮件提醒'),
('renewal.push_enabled', 'true', 'boolean', 'subscription', '是否发送推送提醒'),
('renewal.allow_user_disable', 'true', 'boolean', 'subscription', '用户是否可关闭提醒');
```

#### 9.4.3 数据库设计

```sql
-- 用户通知偏好
CREATE TABLE IF NOT EXISTS user_notification_preferences (
    user_id TEXT PRIMARY KEY REFERENCES profiles(user_id),
    renewal_email BOOLEAN DEFAULT TRUE,
    renewal_push BOOLEAN DEFAULT TRUE,
    marketing_email BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 通知发送记录
CREATE TABLE IF NOT EXISTS notification_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES profiles(user_id),
    notification_type TEXT NOT NULL,      -- 'renewal_reminder' | 'payment_failed' | 'trial_ending'
    channel TEXT NOT NULL,                -- 'email' | 'push' | 'in_app'
    template_id TEXT,
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    opened_at TIMESTAMPTZ,
    clicked_at TIMESTAMPTZ,
    metadata JSONB                        -- 额外数据
);

CREATE INDEX idx_notification_logs_user ON notification_logs(user_id);
CREATE INDEX idx_notification_logs_type ON notification_logs(notification_type);
```

#### 9.4.4 服务实现

```python
# domains/notification/services/renewal_reminder_service.py

class RenewalReminderService:
    """续期提醒服务"""

    async def send_renewal_reminders(self):
        """定时任务: 发送续期提醒"""

        reminder_days = await get_config('renewal.reminder_days') or [7, 3, 1]

        for days in reminder_days:
            target_date = datetime.now() + timedelta(days=days)

            # 查找即将续期的订阅
            subscriptions = await db.fetch_all("""
                SELECT s.*, u.email, u.name, np.renewal_email, np.renewal_push
                FROM subscriptions s
                JOIN profiles u ON s.user_id = u.user_id
                LEFT JOIN user_notification_preferences np ON s.user_id = np.user_id
                WHERE DATE(s.current_period_end) = DATE($1)
                AND s.status = 'active'
                AND s.cancel_at_period_end = FALSE
            """, target_date)

            for sub in subscriptions:
                # 检查是否已发送过
                already_sent = await self._check_already_sent(sub['user_id'], days)
                if already_sent:
                    continue

                # 发送邮件
                if sub.get('renewal_email', True):
                    await self._send_email_reminder(sub, days)

                # 发送推送 (仅最后一天)
                if days == 1 and sub.get('renewal_push', True):
                    await self._send_push_reminder(sub)

                # 创建应用内通知 (3 天和 1 天)
                if days <= 3:
                    await self._create_in_app_notification(sub, days)

    async def _send_email_reminder(self, subscription: Dict, days_until: int):
        """发送邮件提醒"""

        template = {
            7: 'renewal_reminder_7days',
            3: 'renewal_reminder_3days',
            1: 'renewal_reminder_1day'
        }.get(days_until)

        await email_service.send(
            to=subscription['email'],
            template=template,
            data={
                'user_name': subscription['name'],
                'tier_name': TIER_DISPLAY_NAMES[subscription['tier']],
                'renewal_date': subscription['current_period_end'].strftime('%Y年%m月%d日'),
                'amount': subscription['price'],
                'payment_method_last4': subscription.get('card_last4', '****'),
                'manage_url': f"{BASE_URL}/settings/subscription"
            }
        )

        # 记录
        await self._log_notification(
            subscription['user_id'],
            'renewal_reminder',
            'email',
            template
        )
```

#### 9.4.5 邮件模板示例

```html
<!-- 续期前 3 天邮件模板 -->
<h2>您的订阅即将续期</h2>

<p>亲爱的 {{user_name}}，</p>

<p>您的 <strong>{{tier_name}}</strong> 订阅将于 <strong>{{renewal_date}}</strong> 自动续期。</p>

<div class="info-box">
  <p>续期金额: <strong>${{amount}}</strong></p>
  <p>支付方式: 尾号 {{payment_method_last4}} 的信用卡</p>
</div>

<p>请确保您的支付方式有效，以避免服务中断。</p>

<div class="cta">
  <a href="{{manage_url}}">管理订阅</a>
</div>

<p class="footer">
  如果您不希望续期，可以在续期日期前<a href="{{manage_url}}">取消订阅</a>。
</p>
```

---

### 9.5 发票与收据管理 (Invoice Management) 🔴 P0

> 参考: 所有 SaaS 产品

#### 9.5.1 功能清单

| 功能 | 说明 |
|------|------|
| 账单历史 | 查看所有历史账单 |
| 下载发票 | PDF 格式下载 |
| 发票信息 | 设置公司名、税号、地址 |
| 邮件发送 | 每次扣费后自动发送发票 |

#### 9.5.2 数据库设计

```sql
-- 发票信息
CREATE TABLE IF NOT EXISTS user_billing_info (
    user_id TEXT PRIMARY KEY REFERENCES profiles(user_id),
    company_name TEXT,                    -- 公司名称
    tax_id TEXT,                          -- 税号
    billing_email TEXT,                   -- 账单邮箱 (可与主邮箱不同)
    address_line1 TEXT,
    address_line2 TEXT,
    city TEXT,
    state TEXT,
    postal_code TEXT,
    country TEXT DEFAULT 'US',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 发票记录 (Stripe Invoice 同步)
CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES profiles(user_id),
    stripe_invoice_id TEXT UNIQUE,
    invoice_number TEXT,                  -- 发票号
    amount_due INT,                       -- 应付金额 (分)
    amount_paid INT,                      -- 实付金额 (分)
    currency TEXT DEFAULT 'usd',
    status TEXT,                          -- 'draft' | 'open' | 'paid' | 'void' | 'uncollectible'
    invoice_pdf_url TEXT,                 -- Stripe 生成的 PDF URL
    hosted_invoice_url TEXT,              -- Stripe 托管的发票页面
    period_start TIMESTAMPTZ,
    period_end TIMESTAMPTZ,
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_invoices_user ON invoices(user_id);
CREATE INDEX idx_invoices_stripe ON invoices(stripe_invoice_id);
```

#### 9.5.3 API 设计

```python
# api/routers/billing.py

@router.get("/invoices")
async def list_invoices(
    current_user: User = Depends(get_current_user),
    limit: int = Query(10, le=100),
    offset: int = 0
):
    """获取账单历史"""
    invoices = await invoice_service.list_user_invoices(
        current_user.user_id, limit, offset
    )
    return {
        "invoices": invoices,
        "total": await invoice_service.count_user_invoices(current_user.user_id)
    }

@router.get("/invoices/{invoice_id}/pdf")
async def download_invoice_pdf(
    invoice_id: str,
    current_user: User = Depends(get_current_user)
):
    """下载发票 PDF"""
    invoice = await invoice_service.get_invoice(invoice_id, current_user.user_id)
    if not invoice:
        raise HTTPException(404, "发票不存在")

    # 重定向到 Stripe PDF
    return RedirectResponse(invoice.invoice_pdf_url)

@router.get("/billing-info")
async def get_billing_info(current_user: User = Depends(get_current_user)):
    """获取发票信息"""
    return await billing_service.get_billing_info(current_user.user_id)

@router.put("/billing-info")
async def update_billing_info(
    data: BillingInfoUpdate,
    current_user: User = Depends(get_current_user)
):
    """更新发票信息"""
    await billing_service.update_billing_info(current_user.user_id, data)

    # 同步到 Stripe Customer
    await stripe_service.update_customer_billing_info(
        current_user.stripe_customer_id, data
    )

    return {"status": "updated"}
```

#### 9.5.4 UI 组件

```typescript
// pages/settings/billing/page.tsx

function BillingPage() {
  return (
    <SettingsLayout>
      <h1>账单管理</h1>

      {/* 发票信息 */}
      <Card className="mb-6">
        <CardHeader>
          <h2>发票信息</h2>
          <p className="text-sm text-slate-500">此信息将显示在您的发票上</p>
        </CardHeader>
        <CardContent>
          <BillingInfoForm />
        </CardContent>
      </Card>

      {/* 账单历史 */}
      <Card>
        <CardHeader>
          <h2>账单历史</h2>
        </CardHeader>
        <CardContent>
          <InvoiceList />
        </CardContent>
      </Card>
    </SettingsLayout>
  );
}

function InvoiceList() {
  const { data, isLoading } = useQuery(['invoices'], fetchInvoices);

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>日期</TableHead>
          <TableHead>描述</TableHead>
          <TableHead>金额</TableHead>
          <TableHead>状态</TableHead>
          <TableHead>操作</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data?.invoices.map((invoice) => (
          <TableRow key={invoice.id}>
            <TableCell>{formatDate(invoice.created_at)}</TableCell>
            <TableCell>{invoice.description || `${TIER_NAMES[invoice.tier]} 订阅`}</TableCell>
            <TableCell>${(invoice.amount_paid / 100).toFixed(2)}</TableCell>
            <TableCell>
              <Badge variant={invoice.status === 'paid' ? 'success' : 'warning'}>
                {invoice.status === 'paid' ? '已支付' : '待支付'}
              </Badge>
            </TableCell>
            <TableCell>
              <Button size="sm" variant="ghost" asChild>
                <a href={invoice.invoice_pdf_url} target="_blank">
                  <Download className="w-4 h-4 mr-1" />
                  下载
                </a>
              </Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
```

---

### 9.6 退款完整处理流程 🔴 P0

> 补充退款后的完整处理，包括积分、商城、权限等

#### 9.6.1 退款类型

| 类型 | 触发方式 | 积分处理 | 权限处理 |
|------|---------|---------|---------|
| **全额退款** | 用户申请/客服操作 | 全部扣回 | 立即降级 |
| **部分退款** | 客服操作 | 按比例扣回 | 不变 |
| **积分包退款** | 用户申请 | 扣回剩余积分 | 不变 |
| **争议退款** | 银行发起 | 全部扣回+标记 | 立即降级 |

#### 9.6.2 退款冷却期

```
为防止滥用退款机制:
- 同一订阅类型退款后 90 天内不能重新订阅
- 积分包退款后 30 天内不能再次购买
- 争议退款后账户被标记为 "高风险"，需人工审核后方可消费
```

#### 9.6.3 配置项

```sql
INSERT INTO system_configs (key, value, value_type, config_group, description) VALUES
('refund.subscription_cooldown_days', '90', 'integer', 'refund', '订阅退款后冷却期'),
('refund.credits_cooldown_days', '30', 'integer', 'refund', '积分退款后冷却期'),
('refund.auto_approve_threshold', '50', 'float', 'refund', '自动审批金额阈值 ($)'),
('refund.dispute_auto_block', 'true', 'boolean', 'refund', '争议退款是否自动封禁');
```

#### 9.6.4 数据库设计

```sql
-- 退款记录表
CREATE TABLE IF NOT EXISTS refund_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES profiles(user_id),
    stripe_refund_id TEXT UNIQUE,
    stripe_charge_id TEXT,
    refund_type TEXT NOT NULL,            -- 'subscription' | 'credits' | 'marketplace'
    amount INT NOT NULL,                  -- 退款金额 (分)
    reason TEXT,                          -- 退款原因
    credits_deducted INT DEFAULT 0,       -- 扣回的积分
    debt_created INT DEFAULT 0,           -- 产生的负债
    status TEXT DEFAULT 'pending',        -- 'pending' | 'approved' | 'completed' | 'rejected'
    processed_by TEXT,                    -- 处理人 (admin user_id)
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 用户风险标记
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS
    risk_level TEXT DEFAULT 'normal',     -- 'normal' | 'elevated' | 'high'
    risk_reason TEXT,
    risk_updated_at TIMESTAMPTZ;

-- 退款冷却记录
CREATE TABLE IF NOT EXISTS refund_cooldowns (
    user_id TEXT NOT NULL REFERENCES profiles(user_id),
    product_type TEXT NOT NULL,           -- 'subscription_t2' | 'subscription_t3' | 'credits'
    cooldown_until TIMESTAMPTZ NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, product_type)
);
```

#### 9.6.5 服务实现

```python
# domains/refund/services/refund_service.py

class RefundService:
    """退款处理服务"""

    async def process_subscription_refund(
        self,
        user_id: str,
        subscription_id: str,
        reason: str,
        partial_amount: float = None  # None = 全额退款
    ) -> Dict:
        """处理订阅退款"""

        subscription = await self._get_subscription(subscription_id, user_id)

        # 1. 计算退款金额
        if partial_amount:
            refund_amount = partial_amount
        else:
            refund_amount = self._calculate_prorated_refund(subscription)

        # 2. 执行 Stripe 退款
        stripe_refund = await stripe.Refund.create(
            charge=subscription.latest_charge_id,
            amount=int(refund_amount * 100),
            reason='requested_by_customer'
        )

        # 3. 计算积分扣回
        credits_result = await self._handle_subscription_credits_deduction(
            user_id, subscription, refund_amount
        )

        # 4. 降级处理
        if not partial_amount:  # 全额退款才降级
            await self.downgrade_service.process_downgrade(
                user_id,
                old_tier=subscription.tier,
                new_tier='t1',
                reason='refund'
            )

        # 5. 设置冷却期
        cooldown_days = await get_config('refund.subscription_cooldown_days') or 90
        await db.execute("""
            INSERT INTO refund_cooldowns (user_id, product_type, cooldown_until, reason)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id, product_type) DO UPDATE SET
                cooldown_until = EXCLUDED.cooldown_until,
                reason = EXCLUDED.reason
        """, user_id, f'subscription_{subscription.tier}',
            datetime.now() + timedelta(days=cooldown_days), 'refund')

        # 6. 记录退款
        await db.execute("""
            INSERT INTO refund_records
            (user_id, stripe_refund_id, stripe_charge_id, refund_type, amount, reason,
             credits_deducted, debt_created, status, processed_at)
            VALUES ($1, $2, $3, 'subscription', $4, $5, $6, $7, 'completed', NOW())
        """, user_id, stripe_refund.id, subscription.latest_charge_id,
            int(refund_amount * 100), reason,
            credits_result['deducted'], credits_result['debt_created'])

        # 7. 发送确认邮件
        await self._send_refund_confirmation_email(user_id, refund_amount, reason)

        return {
            'refund_id': stripe_refund.id,
            'amount': refund_amount,
            'credits_deducted': credits_result['deducted'],
            'debt_created': credits_result['debt_created'],
            'cooldown_until': (datetime.now() + timedelta(days=cooldown_days)).isoformat()
        }

    async def handle_dispute(self, dispute_event: Dict):
        """处理争议退款 (Stripe Webhook)"""

        user_id = await self._get_user_from_charge(dispute_event['charge'])

        # 1. 标记高风险
        await db.execute("""
            UPDATE profiles SET
                risk_level = 'high',
                risk_reason = 'dispute_chargeback',
                risk_updated_at = NOW()
            WHERE user_id = $1
        """, user_id)

        # 2. 扣回积分 (全部)
        await self.credit_service.handle_refund_credit_deduction(
            user_id,
            purchase_id=dispute_event['charge'],
            refund_amount=dispute_event['amount'] / 100,
            original_amount=dispute_event['amount'] / 100,
            original_credits=await self._get_credits_for_charge(dispute_event['charge'])
        )

        # 3. 立即降级
        subscription = await self._get_user_subscription(user_id)
        if subscription and subscription.tier != 't1':
            await self.downgrade_service.process_downgrade(
                user_id,
                old_tier=subscription.tier,
                new_tier='t1',
                reason='dispute_chargeback'
            )

        # 4. 通知管理员
        await self._notify_admin_dispute(user_id, dispute_event)

    async def check_purchase_eligibility(self, user_id: str, product_type: str) -> Dict:
        """检查是否可以购买 (冷却期检查)"""

        cooldown = await db.fetch_one("""
            SELECT cooldown_until, reason FROM refund_cooldowns
            WHERE user_id = $1 AND product_type = $2 AND cooldown_until > NOW()
        """, user_id, product_type)

        if cooldown:
            return {
                'eligible': False,
                'reason': f'由于之前的退款，该产品在 {cooldown["cooldown_until"].strftime("%Y-%m-%d")} 之前无法购买',
                'cooldown_until': cooldown['cooldown_until']
            }

        # 检查风险等级
        profile = await db.fetch_one("""
            SELECT risk_level FROM profiles WHERE user_id = $1
        """, user_id)

        if profile['risk_level'] == 'high':
            return {
                'eligible': False,
                'reason': '您的账户需要人工审核，请联系客服',
                'contact_support': True
            }

        return {'eligible': True}
```

---

### 9.7 限时优惠与倒计时 🟡 P1

> 参考: 电商、SaaS 促销活动

#### 9.7.1 优惠类型

| 类型 | 说明 | 示例 |
|------|------|------|
| **首购优惠** | 新用户首次购买折扣 | 首月 5 折 |
| **节日促销** | 特定时间段折扣 | 黑五 7 折 |
| **限时闪购** | 短时间高折扣 | 24 小时 6 折 |
| **续费优惠** | 老用户续费折扣 | 年付续费 8 折 |

#### 9.7.2 数据库设计

```sql
-- 优惠活动表
CREATE TABLE IF NOT EXISTS promotions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code TEXT UNIQUE,                     -- 优惠码 (可选)
    name TEXT NOT NULL,
    description TEXT,
    discount_type TEXT NOT NULL,          -- 'percentage' | 'fixed_amount'
    discount_value DECIMAL(10,2) NOT NULL,-- 折扣值 (百分比或金额)
    applies_to TEXT[] DEFAULT '{}',       -- 适用产品: ['t2', 't3', 'credits_500']
    min_purchase DECIMAL(10,2),           -- 最低消费
    max_discount DECIMAL(10,2),           -- 最高折扣金额
    usage_limit INT,                      -- 总使用次数限制
    usage_count INT DEFAULT 0,            -- 已使用次数
    per_user_limit INT DEFAULT 1,         -- 每用户限制
    user_eligibility TEXT DEFAULT 'all',  -- 'all' | 'new' | 'returning' | 'specific_group'
    eligible_groups TEXT[],               -- 特定用户组
    start_at TIMESTAMPTZ NOT NULL,
    end_at TIMESTAMPTZ NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 优惠使用记录
CREATE TABLE IF NOT EXISTS promotion_usages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    promotion_id UUID REFERENCES promotions(id),
    user_id TEXT NOT NULL REFERENCES profiles(user_id),
    order_id TEXT,
    discount_applied DECIMAL(10,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_promotions_active ON promotions(is_active, start_at, end_at);
CREATE INDEX idx_promotion_usages_user ON promotion_usages(user_id);
```

#### 9.7.3 服务实现

```python
# domains/promotion/services/promotion_service.py

class PromotionService:
    """促销活动服务"""

    async def get_applicable_promotions(
        self,
        user_id: str,
        product_type: str
    ) -> List[Dict]:
        """获取用户可用的优惠"""

        now = datetime.now()
        user = await self._get_user(user_id)

        # 查询有效活动
        promotions = await db.fetch_all("""
            SELECT * FROM promotions
            WHERE is_active = TRUE
            AND start_at <= $1 AND end_at > $1
            AND (usage_limit IS NULL OR usage_count < usage_limit)
            AND $2 = ANY(applies_to)
        """, now, product_type)

        applicable = []
        for promo in promotions:
            # 检查用户资格
            if not await self._check_user_eligibility(user_id, user, promo):
                continue

            # 检查使用次数
            usage_count = await db.fetch_val("""
                SELECT COUNT(*) FROM promotion_usages
                WHERE promotion_id = $1 AND user_id = $2
            """, promo['id'], user_id)

            if usage_count >= promo['per_user_limit']:
                continue

            applicable.append({
                'id': promo['id'],
                'code': promo['code'],
                'name': promo['name'],
                'description': promo['description'],
                'discount_type': promo['discount_type'],
                'discount_value': promo['discount_value'],
                'end_at': promo['end_at'],
                'remaining_time': (promo['end_at'] - now).total_seconds()
            })

        return applicable

    async def apply_promotion(
        self,
        user_id: str,
        promotion_id: str,
        original_amount: float
    ) -> Dict:
        """应用优惠"""

        promo = await self._get_promotion(promotion_id)

        # 验证
        if not await self._validate_promotion(user_id, promo, original_amount):
            raise PromotionNotApplicableError()

        # 计算折扣
        if promo['discount_type'] == 'percentage':
            discount = original_amount * (promo['discount_value'] / 100)
        else:
            discount = promo['discount_value']

        # 应用最高折扣限制
        if promo['max_discount'] and discount > promo['max_discount']:
            discount = promo['max_discount']

        final_amount = original_amount - discount

        return {
            'original_amount': original_amount,
            'discount': discount,
            'final_amount': max(0, final_amount),
            'promotion_id': promotion_id,
            'promotion_name': promo['name']
        }
```

#### 9.7.4 前端倒计时组件

```typescript
// components/promotion/PromotionCountdown.tsx

interface PromotionCountdownProps {
  endAt: string;
  promotionName: string;
  discountText: string;
}

function PromotionCountdown({ endAt, promotionName, discountText }: PromotionCountdownProps) {
  const [timeLeft, setTimeLeft] = useState(calculateTimeLeft(endAt));

  useEffect(() => {
    const timer = setInterval(() => {
      const left = calculateTimeLeft(endAt);
      setTimeLeft(left);

      if (left.total <= 0) {
        clearInterval(timer);
      }
    }, 1000);

    return () => clearInterval(timer);
  }, [endAt]);

  if (timeLeft.total <= 0) return null;

  return (
    <div className="bg-gradient-to-r from-orange-500 to-red-500 text-white px-4 py-2">
      <div className="flex items-center justify-between max-w-4xl mx-auto">
        <div className="flex items-center gap-2">
          <Zap className="w-5 h-5" />
          <span className="font-semibold">{promotionName}</span>
          <span>{discountText}</span>
        </div>

        <div className="flex items-center gap-1 font-mono">
          <span className="bg-white/20 px-2 py-1 rounded">{timeLeft.days}天</span>
          <span>:</span>
          <span className="bg-white/20 px-2 py-1 rounded">{timeLeft.hours}时</span>
          <span>:</span>
          <span className="bg-white/20 px-2 py-1 rounded">{timeLeft.minutes}分</span>
          <span>:</span>
          <span className="bg-white/20 px-2 py-1 rounded">{timeLeft.seconds}秒</span>
        </div>

        <Button size="sm" variant="secondary">
          立即抢购
        </Button>
      </div>
    </div>
  );
}

function calculateTimeLeft(endAt: string) {
  const end = new Date(endAt).getTime();
  const now = Date.now();
  const diff = end - now;

  if (diff <= 0) {
    return { total: 0, days: 0, hours: 0, minutes: 0, seconds: 0 };
  }

  return {
    total: diff,
    days: Math.floor(diff / (1000 * 60 * 60 * 24)),
    hours: Math.floor((diff / (1000 * 60 * 60)) % 24),
    minutes: Math.floor((diff / (1000 * 60)) % 60),
    seconds: Math.floor((diff / 1000) % 60)
  };
}
```

---

### 9.8 邀请奖励完整规则 🟡 P1

> 参考: Dropbox, Notion, Canva

#### 9.8.1 奖励规则

| 角色 | 奖励条件 | 奖励内容 | 上限 |
|------|---------|---------|------|
| **邀请人** | 被邀请人付费成功 | 1 个月订阅延长 或 50 积分 | 12 个月 或 600 积分 |
| **被邀请人** | 首次付费 | 首月 8 折 | 1 次 |

#### 9.8.2 防作弊规则

```
1. 同一 IP 24 小时内最多邀请 3 人
2. 同一设备指纹最多关联 5 个被邀请账号
3. 被邀请人必须使用不同邮箱域名
4. 被邀请人首次付费后 7 天内取消/退款，奖励收回
5. 邀请人账户异常 (高风险/封禁) 时奖励冻结
```

#### 9.8.3 数据库设计

```sql
-- 邀请记录表
CREATE TABLE IF NOT EXISTS referrals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    referrer_id TEXT NOT NULL REFERENCES profiles(user_id),  -- 邀请人
    referee_id TEXT REFERENCES profiles(user_id),            -- 被邀请人
    referral_code TEXT NOT NULL,                             -- 邀请码
    referee_email TEXT,                                      -- 被邀请人邮箱
    status TEXT DEFAULT 'pending',    -- 'pending' | 'registered' | 'converted' | 'rewarded' | 'revoked'
    referrer_ip TEXT,
    referrer_fingerprint TEXT,
    referee_ip TEXT,
    referee_fingerprint TEXT,
    converted_at TIMESTAMPTZ,         -- 被邀请人付费时间
    rewarded_at TIMESTAMPTZ,          -- 奖励发放时间
    reward_type TEXT,                 -- 'subscription_extension' | 'credits'
    reward_value TEXT,                -- '1_month' 或 '50'
    revoked_at TIMESTAMPTZ,           -- 奖励撤销时间
    revoke_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 邀请人奖励汇总
CREATE TABLE IF NOT EXISTS referral_rewards_summary (
    user_id TEXT PRIMARY KEY REFERENCES profiles(user_id),
    total_referrals INT DEFAULT 0,            -- 总邀请数
    successful_referrals INT DEFAULT 0,       -- 成功转化数
    subscription_months_earned INT DEFAULT 0, -- 获得的订阅月数
    credits_earned INT DEFAULT 0,             -- 获得的积分
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_referrals_referrer ON referrals(referrer_id);
CREATE INDEX idx_referrals_code ON referrals(referral_code);
```

#### 9.8.4 配置项

```sql
INSERT INTO system_configs (key, value, value_type, config_group, description) VALUES
('referral.reward_type', 'subscription_extension', 'string', 'referral', '奖励类型'),
('referral.reward_value', '1', 'integer', 'referral', '奖励值 (月数或积分)'),
('referral.max_rewards', '12', 'integer', 'referral', '最大奖励数量'),
('referral.referee_discount', '0.2', 'float', 'referral', '被邀请人首购折扣'),
('referral.conversion_window_days', '7', 'integer', 'referral', '转化窗口期'),
('referral.revoke_window_days', '7', 'integer', 'referral', '取消/退款撤销奖励窗口');
```

#### 9.8.5 服务实现

```python
# domains/referral/services/referral_service.py

class ReferralService:
    """邀请奖励服务"""

    async def generate_referral_code(self, user_id: str) -> str:
        """生成邀请码"""

        # 检查是否已有邀请码
        existing = await db.fetch_val("""
            SELECT referral_code FROM profiles WHERE user_id = $1
        """, user_id)

        if existing:
            return existing

        # 生成唯一码
        code = self._generate_unique_code(user_id)

        await db.execute("""
            UPDATE profiles SET referral_code = $1 WHERE user_id = $2
        """, code, user_id)

        return code

    async def track_referral_click(
        self,
        referral_code: str,
        referee_email: str,
        ip: str,
        fingerprint: str
    ) -> Dict:
        """记录邀请点击"""

        referrer = await self._get_referrer_by_code(referral_code)
        if not referrer:
            raise InvalidReferralCodeError()

        # 防作弊检查
        fraud_check = await self._check_fraud(referrer['user_id'], ip, fingerprint)
        if not fraud_check['passed']:
            return {'status': 'blocked', 'reason': fraud_check['reason']}

        # 创建邀请记录
        await db.execute("""
            INSERT INTO referrals
            (referrer_id, referral_code, referee_email, referrer_ip, referrer_fingerprint)
            VALUES ($1, $2, $3, $4, $5)
        """, referrer['user_id'], referral_code, referee_email, ip, fingerprint)

        return {'status': 'tracked', 'referrer_name': referrer['name']}

    async def process_conversion(self, referee_id: str, payment_id: str):
        """处理转化 (被邀请人付费)"""

        # 查找邀请记录
        referral = await db.fetch_one("""
            SELECT * FROM referrals
            WHERE referee_id = $1 AND status = 'registered'
        """, referee_id)

        if not referral:
            return  # 非邀请用户

        # 检查转化窗口
        window_days = await get_config('referral.conversion_window_days') or 7
        if (datetime.now() - referral['created_at']).days > window_days:
            return  # 超出窗口

        # 检查邀请人奖励上限
        summary = await self._get_rewards_summary(referral['referrer_id'])
        max_rewards = await get_config('referral.max_rewards') or 12

        if summary['subscription_months_earned'] >= max_rewards:
            await db.execute("""
                UPDATE referrals SET status = 'converted', converted_at = NOW()
                WHERE id = $1
            """, referral['id'])
            return  # 已达上限，只记录转化不发奖励

        # 发放奖励
        reward_type = await get_config('referral.reward_type')
        reward_value = await get_config('referral.reward_value')

        if reward_type == 'subscription_extension':
            await self._extend_subscription(referral['referrer_id'], int(reward_value))
        else:
            await self._add_credits(referral['referrer_id'], int(reward_value))

        # 更新记录
        await db.execute("""
            UPDATE referrals SET
                status = 'rewarded',
                converted_at = NOW(),
                rewarded_at = NOW(),
                reward_type = $1,
                reward_value = $2
            WHERE id = $3
        """, reward_type, str(reward_value), referral['id'])

        # 更新汇总
        await self._update_rewards_summary(referral['referrer_id'], reward_type, reward_value)

        # 通知邀请人
        await self._notify_referrer_reward(referral['referrer_id'])

    async def revoke_reward_on_refund(self, referee_id: str):
        """退款时撤销奖励"""

        revoke_window = await get_config('referral.revoke_window_days') or 7

        referral = await db.fetch_one("""
            SELECT * FROM referrals
            WHERE referee_id = $1
            AND status = 'rewarded'
            AND rewarded_at > NOW() - INTERVAL '%s days'
        """ % revoke_window, referee_id)

        if not referral:
            return

        # 撤销奖励
        if referral['reward_type'] == 'subscription_extension':
            await self._shorten_subscription(referral['referrer_id'], int(referral['reward_value']))
        else:
            await self._deduct_credits(referral['referrer_id'], int(referral['reward_value']))

        await db.execute("""
            UPDATE referrals SET
                status = 'revoked',
                revoked_at = NOW(),
                revoke_reason = 'referee_refund'
            WHERE id = $1
        """, referral['id'])

    async def _check_fraud(self, referrer_id: str, ip: str, fingerprint: str) -> Dict:
        """防作弊检查"""

        # 1. 同 IP 24 小时限制
        ip_count = await db.fetch_val("""
            SELECT COUNT(*) FROM referrals
            WHERE referrer_id = $1 AND referrer_ip = $2
            AND created_at > NOW() - INTERVAL '24 hours'
        """, referrer_id, ip)

        if ip_count >= 3:
            return {'passed': False, 'reason': '同一网络邀请过多'}

        # 2. 同设备指纹限制
        fp_count = await db.fetch_val("""
            SELECT COUNT(*) FROM referrals
            WHERE referrer_fingerprint = $1
        """, fingerprint)

        if fp_count >= 5:
            return {'passed': False, 'reason': '设备关联账号过多'}

        return {'passed': True}
```

---

### 9.9 学生/教育优惠 🟡 P1

> 参考: Notion, Canva, Adobe, Figma

#### 9.9.1 验证方式

| 方式 | 说明 | 验证周期 |
|------|------|---------|
| **edu 邮箱** | 使用 .edu 或学校邮箱注册 | 每年重新验证 |
| **第三方验证** | SheerID / UNiDAYS | 实时验证 |
| **手动审核** | 上传学生证照片 | 人工审核 (1-3 天) |

#### 9.9.2 优惠内容

```
教育优惠:
- Pro Plan (t3) 5 折: $4.95/月
- 验证有效期: 1 年
- 每年需重新验证
- 毕业后自动转为普通价格
```

#### 9.9.3 数据库设计

```sql
-- 教育验证记录
CREATE TABLE IF NOT EXISTS education_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES profiles(user_id),
    verification_method TEXT NOT NULL,    -- 'edu_email' | 'sheerid' | 'manual'
    institution_name TEXT,                -- 学校名称
    institution_type TEXT,                -- 'university' | 'high_school' | 'k12'
    edu_email TEXT,
    verification_status TEXT DEFAULT 'pending', -- 'pending' | 'verified' | 'rejected' | 'expired'
    verified_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,               -- 验证过期时间
    rejection_reason TEXT,
    document_url TEXT,                    -- 上传的学生证 (manual 方式)
    sheerid_verification_id TEXT,         -- SheerID 验证 ID
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_edu_verification_user ON education_verifications(user_id);
CREATE INDEX idx_edu_verification_status ON education_verifications(verification_status);
```

#### 9.9.4 配置项

```sql
INSERT INTO system_configs (key, value, value_type, config_group, description) VALUES
('education.discount_percentage', '50', 'integer', 'education', '教育优惠折扣'),
('education.verification_validity_days', '365', 'integer', 'education', '验证有效期(天)'),
('education.allowed_domains', '["edu", "ac.uk", "edu.cn", "edu.au"]', 'json', 'education', '允许的教育邮箱域名'),
('education.sheerid_enabled', 'true', 'boolean', 'education', '是否启用 SheerID');
```

---

### 9.10 免费额度/体验次数 🟡 P1

> 参考: ChatGPT, Midjourney, DALL-E

#### 9.10.1 额度规则

| 用户类型 | 日限额 | 月限额 | 限制维度 |
|---------|:-----:|:-----:|---------|
| **游客** | 3 次 AI 调用 | - | IP + 指纹 |
| **t1 (试用期外)** | 5 次 AI 调用 | 50 次 | 账户 |
| **t1 (试用期内)** | 不限 | 不限 | - |
| **t2/t3** | 不限 | 不限 | - |

#### 9.10.2 数据库设计

```sql
-- 免费额度使用记录
CREATE TABLE IF NOT EXISTS free_usage_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identifier TEXT NOT NULL,             -- user_id 或 ip:fingerprint
    identifier_type TEXT NOT NULL,        -- 'user' | 'anonymous'
    feature_key TEXT NOT NULL,            -- 'ai_generate' | 'smart_scan'
    used_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB                        -- 额外信息
);

-- 按天/月聚合索引
CREATE INDEX idx_free_usage_daily ON free_usage_tracking(identifier, feature_key, DATE(used_at));
```

#### 9.10.3 服务实现

```python
# domains/ratelimit/services/free_usage_service.py

class FreeUsageService:
    """免费额度服务"""

    async def check_and_consume(
        self,
        identifier: str,
        identifier_type: str,  # 'user' | 'anonymous'
        feature_key: str
    ) -> Dict:
        """检查并消耗免费额度"""

        limits = await self._get_limits(identifier_type, feature_key)

        # 获取今日使用量
        today_usage = await db.fetch_val("""
            SELECT COUNT(*) FROM free_usage_tracking
            WHERE identifier = $1 AND feature_key = $2
            AND DATE(used_at) = CURRENT_DATE
        """, identifier, feature_key)

        if today_usage >= limits['daily']:
            return {
                'allowed': False,
                'reason': 'daily_limit_exceeded',
                'reset_at': self._get_next_day_start()
            }

        # 获取本月使用量 (仅用户)
        if identifier_type == 'user' and limits.get('monthly'):
            month_usage = await db.fetch_val("""
                SELECT COUNT(*) FROM free_usage_tracking
                WHERE identifier = $1 AND feature_key = $2
                AND DATE_TRUNC('month', used_at) = DATE_TRUNC('month', CURRENT_DATE)
            """, identifier, feature_key)

            if month_usage >= limits['monthly']:
                return {
                    'allowed': False,
                    'reason': 'monthly_limit_exceeded',
                    'reset_at': self._get_next_month_start()
                }

        # 记录使用
        await db.execute("""
            INSERT INTO free_usage_tracking (identifier, identifier_type, feature_key)
            VALUES ($1, $2, $3)
        """, identifier, identifier_type, feature_key)

        return {
            'allowed': True,
            'remaining_today': limits['daily'] - today_usage - 1
        }
```

---

### 9.11 Feature Sunset (功能下线) 🟡 P1

> 参考: 产品演进过程中的功能迁移

#### 9.11.1 下线流程

```
1. 公告期 (T-30): 发布下线公告，应用内 Banner
2. 提醒期 (T-14): 邮件通知，编辑器内提示
3. 最后提醒 (T-7): 强提醒，阻断式 Modal
4. 下线日 (T-0): 功能禁用，返回迁移引导
5. 清理期 (T+30): 清理旧数据 (可选)
```

#### 9.11.2 数据库设计

```sql
-- 功能生命周期表
CREATE TABLE IF NOT EXISTS feature_lifecycle (
    feature_key TEXT PRIMARY KEY,
    status TEXT DEFAULT 'active',         -- 'active' | 'deprecated' | 'sunset' | 'removed'
    deprecated_at TIMESTAMPTZ,
    sunset_at TIMESTAMPTZ,                -- 计划下线日期
    removed_at TIMESTAMPTZ,
    replacement_feature TEXT,             -- 替代功能 Key
    migration_guide_url TEXT,             -- 迁移指南链接
    announcement_content TEXT,            -- 公告内容
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

### 9.12 权限继承冲突处理 🟡 P1

> 用户同时属于多个组时的冲突解决

#### 9.12.1 冲突场景

```
场景: 用户 A 同时属于:
- user_group: 'beta_testers' (smart_scan = true)
- user_group: 'limited_access' (smart_scan = false)

冲突: smart_scan 应该是 true 还是 false?
```

#### 9.12.2 解决策略

| 策略 | 说明 | 适用场景 |
|------|------|---------|
| **Permissive (宽松)** | 多组冲突时取最高权限 | 默认策略 |
| **Restrictive (严格)** | 多组冲突时取最低权限 | 安全敏感功能 |
| **Priority (优先级)** | 按组优先级决定 | 复杂场景 |
| **Explicit (显式)** | 必须显式解决冲突 | 审计要求高 |

#### 9.12.3 实现

```python
# 在 feature-flag-engine 中添加冲突解决

class ConflictResolutionStrategy(Enum):
    PERMISSIVE = 'permissive'      # 取最高权限
    RESTRICTIVE = 'restrictive'    # 取最低权限
    PRIORITY = 'priority'          # 按优先级
    EXPLICIT = 'explicit'          # 显式解决

async def resolve_group_override_conflict(
    user_id: str,
    feature_key: str,
    group_overrides: List[Dict]
) -> Optional[str]:
    """解决多组冲突"""

    if len(group_overrides) <= 1:
        return group_overrides[0]['value'] if group_overrides else None

    # 获取策略 (可按 feature_key 配置)
    strategy = await get_feature_conflict_strategy(feature_key)

    if strategy == ConflictResolutionStrategy.PERMISSIVE:
        # 取最高权限: true > trial > false
        priority = {'true': 3, 'trial': 2, 'false': 1}
        return max(group_overrides, key=lambda x: priority.get(x['value'], 0))['value']

    elif strategy == ConflictResolutionStrategy.RESTRICTIVE:
        # 取最低权限
        priority = {'true': 1, 'trial': 2, 'false': 3}
        return max(group_overrides, key=lambda x: priority.get(x['value'], 0))['value']

    elif strategy == ConflictResolutionStrategy.PRIORITY:
        # 按组优先级
        return max(group_overrides, key=lambda x: x['group_priority'])['value']

    else:  # EXPLICIT
        # 记录冲突，需人工解决
        await log_conflict(user_id, feature_key, group_overrides)
        return None  # 返回 None 表示使用默认值
```

---

### 9.13 低优先级场景索引 🟢 P2

以下场景当前暂不详细实现，仅记录以备后续需要:

| 场景 | 说明 | 实现复杂度 |
|------|------|:---------:|
| **地区定价差异** | 不同国家不同价格 (PPP) | 高 |
| **货币切换** | 支持多币种支付和显示 | 中 |
| **Seat-based 定价** | 按团队成员数计费 | 高 |
| **Usage-based 计费** | 按 API 调用量计费 | 高 |
| **锁定期/合约期** | 企业年度合同 | 中 |
| **跨平台订阅同步** | iOS/Android IAP 同步 | 高 |
| **非营利组织优惠** | 公益组织免费/折扣 | 低 |

---

### 9.14 场景覆盖总结

#### 更新后覆盖情况

| 优先级 | 场景数 | 覆盖数 | 覆盖率 |
|:------:|:-----:|:-----:|:------:|
| P0 (高) | 6 | 6 | 100% |
| P1 (中) | 6 | 6 | 100% |
| P2 (低) | 7 | 0* | - |

*P2 场景仅做索引记录，待业务需要时详细设计

#### 完整场景清单

| # | 场景 | 优先级 | 章节 |
|---|------|:------:|:----:|
| 1 | 订阅暂停 | P0 | 9.1 |
| 2 | 年付/月付切换 | P0 | 9.2 |
| 3 | 积分完整生命周期 | P0 | 9.3 |
| 4 | 订阅续期提醒 | P0 | 9.4 |
| 5 | 发票与收据管理 | P0 | 9.5 |
| 6 | 退款完整处理 | P0 | 9.6 |
| 7 | 限时优惠与倒计时 | P1 | 9.7 |
| 8 | 邀请奖励完整规则 | P1 | 9.8 |
| 9 | 学生/教育优惠 | P1 | 9.9 |
| 10 | 免费额度/体验次数 | P1 | 9.10 |
| 11 | Feature Sunset | P1 | 9.11 |
| 12 | 权限继承冲突 | P1 | 9.12 |
| 13-19 | P2 场景 (7个) | P2 | 9.13 |

---

## 十、变更记录

| 日期 | 版本 | 变更内容 |
|------|------|---------|
| 2026-02-03 | v1.0 | 初始版本，基于产品图表整理 35 个功能点 |
| 2026-02-03 | v1.1 | 补充遗漏：TIER_FEATURES_FALLBACK、EMERGENCY_TIER_CONFIGS、LEGACY_KEY_MAP、完整 JSON 配置 |
| 2026-02-04 | v1.2 | 基于 CSV 表格校准：添加控制方式列、第 7-9 行权限配置、页面访问控制规则 (含已登录用户直接访问路径的处理)、UI 组件控制方式 |
| 2026-02-04 | v1.3 | 新增用户级功能覆盖 (user_feature_overrides)：支持为特定用户开通/关闭功能，与 Tier 配置解耦 |
| 2026-02-04 | v1.4 | 补充 AB 实验场景：跨 Tier 用户验证功能的实验组/对照组配置示例 |
| 2026-02-04 | v1.5 | 新增权限优先级规则详解：参考 LaunchDarkly/Split.io/Unleash 业界最佳实践，含流程图和设计原则 |
| 2026-02-04 | v1.6 | 全面审计修复：补充 t4 兜底配置 (EMERGENCY_TIER_CONFIGS/TIER_FEATURES_FALLBACK/JSON 配置)；补充 compareTier() 函数定义；补充 user_feature_override_logs 审计日志表；统一 Feature Key 命名 (LEGACY_KEY_MAP 更新) |
| 2026-02-04 | v1.7 | 新增"后续扩展场景 (业界预判)"：灰度+Tier 组合、多租户权限、权限继承链、动态定价实验、权限批量管理、配置版本控制，含实施优先级建议 |
| 2026-02-04 | v1.8 | **扩展场景完整实现方案**：(1) 灰度+Tier 完整优先级规则 + 评估引擎；(2) 权限继承链 TIER_INHERITANCE + 增量配置；(3) 用户组批量授权 3 表 + Service；(4) 配置版本控制快照 + 回滚；(5) Workspace 级权限 + Team Plan 支持；含完整流程图和实施计划 |
| 2026-02-04 | v1.9 | **权限边界场景处理**：(1) t1 试用期过期完整处理 (项目只读/禁止新建复制/允许删除/状态提醒)；(2) Tier 降级 Graceful Degradation (数据保留/宽限期/超额锁定/成员保留/商城商品保留)；(3) 其他业界场景 (升级/支付失败重试/账户删除/并发订阅/促销码) |
| 2026-02-04 | v2.0 | **业界最佳实践全面补充 (第九章)**：P0 高优先级 6 个场景 (订阅暂停/年月付切换/积分生命周期/续期提醒/发票管理/退款处理)；P1 中优先级 6 个场景 (限时优惠/邀请奖励/教育优惠/免费额度/Feature Sunset/权限冲突)；P2 低优先级 7 个场景索引。参考 Stripe/Spotify/Netflix/Notion/Figma/Canva/Dropbox 等业界实践 |

---

**END OF DOCUMENT**
