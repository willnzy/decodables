# 功能权限矩阵

> **版本**: v1.9
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

**试用期内提醒**:

| 剩余天数 | 提醒方式 | 提醒频率 |
|:-------:|---------|:-------:|
| 7-4 天 | 顶部 Banner (可关闭) | 每天首次登录 |
| 3-1 天 | 顶部 Banner (不可关闭) + 编辑器内提示 | 每次进入 |
| 0 天 (当天) | Modal 弹窗 + Banner | 每次进入 |
| 已过期 | 持续 Banner + 只读模式 | 持续显示 |

**UI 组件**:

```typescript
// components/trial/TrialStatusBanner.tsx

interface TrialBannerProps {
  daysRemaining: number;
  onUpgrade: () => void;
  onDismiss?: () => void;
}

function TrialStatusBanner({ daysRemaining, onUpgrade, onDismiss }: TrialBannerProps) {
  // 根据剩余天数显示不同样式
  const variant = daysRemaining <= 1 ? 'urgent' : daysRemaining <= 3 ? 'warning' : 'info';
  const canDismiss = daysRemaining > 3;

  const messages = {
    urgent: `试用期今天结束！升级后继续使用所有功能`,
    warning: `试用期还剩 ${daysRemaining} 天`,
    info: `试用期还剩 ${daysRemaining} 天，探索所有功能`,
  };

  return (
    <Banner variant={variant} dismissible={canDismiss} onDismiss={onDismiss}>
      <span>{messages[variant]}</span>
      <Button size="sm" onClick={onUpgrade}>
        {daysRemaining <= 1 ? '立即升级' : '查看套餐'}
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
-- system_configs 配置项
INSERT INTO system_configs (key, value, value_type, config_group, description) VALUES
('trial.default_days', '7', 'integer', 'trial', '默认试用天数'),
('trial.warning_days', '3', 'integer', 'trial', '提前警告天数'),
('trial.urgent_days', '1', 'integer', 'trial', '紧急提醒天数'),
('trial.show_modal_on_expire', 'true', 'boolean', 'trial', '过期当天是否弹窗');
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

## 九、变更记录

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

---

**END OF DOCUMENT**
