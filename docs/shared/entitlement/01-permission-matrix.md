# 功能权限矩阵

> **版本**: v2.0
> **日期**: 2026-02-04
> **状态**: 产品确认
> **说明**: 本文档是功能权限的**唯一数据源**，后端配置和前端实现都以此为准

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [README.md](./README.md) | 文档导航索引 |
| [02-tier-config.md](./02-tier-config.md) | Tier JSON 配置 |
| [03-system-design.md](./03-system-design.md) | 系统架构总览 |

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

## 四、交互规则

### 4.1 被锁定功能的交互

| 情况 | 交互方式 |
|------|---------|
| 功能可见但锁定 | 显示锁图标 🔒，点击后弹出升级窗口 |
| 功能完全隐藏 | 不显示入口 |
| 配额已满 | 按钮置灰，hover 提示 "已达上限" |

### 4.2 试用期交互

| 状态 | 显示 | 交互 |
|------|------|------|
| 试用期内 (>3天) | Banner: "试用期还剩 X 天" | 可关闭 |
| 试用期内 (≤3天) | Banner: "试用即将结束" | 不可关闭 |
| 试用期结束当天 | Modal 弹窗 | 必须操作 |
| 试用期已过 | 持续 Banner + 功能锁定 | 不可关闭 |

---

**END OF DOCUMENT**
