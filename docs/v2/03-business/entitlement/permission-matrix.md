# 功能权限矩阵

> 功能权限与配额的唯一数据源。

**状态**: active  
**版本**: 2.4.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Product Team  
**适用范围**: shared  
**source_repo**: backend  
**sync_required**: yes

---

## 相关文档

| 文档 | 说明 |
|------|------|
| `docs/v2/03-business/entitlement/README.md` | 文档导航索引 |
| `docs/v2/03-business/entitlement/tier-config.md` | Tier JSON 配置 |
| `docs/v2/03-business/entitlement/system-design.md` | 系统架构总览 |
| `docs/v2/03-business/entitlement/permission-matrix-appendix.md` | 权限矩阵汇总表 |
| `docs/v2/03-business/entitlement/credits-lifecycle.md` | 积分完整生命周期 (二维模型) |
| `docs/v2/03-business/entitlement/promotions.md` | 限时优惠与促销 |
| `docs/v2/03-business/entitlement/referral-rewards.md` | 邀请奖励规则 |
| `docs/v2/03-business/entitlement/education-discount.md` | 教育优惠 |

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
| (预留) | `t4` | (未定) | (未定) | (未定) |

> **t4 说明**: t4 为未来预留层级，当前不对外开放，前端不展示。

### 1.3 试用期 (Trial)

- **适用对象**: 仅 t1 用户
- **天数**: `trial.default_days` (默认 7 天)
- **计算方式**: `当前时间 - 注册时间 ≤ trial_days`
- **配置 Key**: `trial.default_days`
- **详细规则**: `docs/v2/03-business/entitlement/trial-expiration.md`

---

## 二、完整功能权限矩阵

> **权限值说明**:
> - `YES` = 完全可用
> - `NO` = 不可用 (功能可见但带锁，点击后弹升级窗口)
> - `trial` = 试用期内可用，超出试用期后变为 NO
> - `N/A` = 无此功能
> - `可配置 (默认: X)` = 后台可配置，括号内为当前默认值
>
> **设计原则**: 所有配额数值通过 `system_configs` 后台配置，代码中不硬编码具体数值。

### 2.1 资源数量限制 (Quota)

| # | 功能 | Key | 游客 | t1 试用期内 | t1 超出试用期 | t2 | t3 | 控制方式 |
|---|------|-----|:---:|:---:|:---:|:---:|:---:|---------|
| 1 | Workspace 最大数量 | `quota.max_workspaces` | 0 | 可配置 (默认: 1) | 可配置 (默认: 1) | 可配置 (默认: 1) | 可配置 (默认: unlimited) | - |
| 2 | 邀请成员加入 Workspace | `feature.can_invite_members` | NO | NO | NO | NO | YES | Member管理入口控制 |
| 3 | Workspace 成员数量 | `quota.max_workspace_members` | 0 | 0 | 0 | 0 | 可配置 (默认: 10) | 仅 t3 可邀请 |
| 4 | 文件夹最大数量 | `quota.max_folders` | 0 | 可配置 (默认: 1) | 可配置 (默认: 1) | 可配置 (默认: 5) | 可配置 (默认: unlimited) | - |
| 5 | 项目最大数量 | `quota.max_projects` | 0 | 可配置 (默认: 1) | 可配置 (默认: 1) | 可配置 (默认: 10) | 可配置 (默认: 50) | - |
| 6 | 自定义素材上传 | `feature.can_upload_custom_assets` | NO | YES | NO | NO | YES | t2 不支持上传，t3 可上传 |
| 7 | 自定义素材最大数量 | `quota.max_custom_assets` | 0 | 可配置 (默认: 10) | 0 | 0 | 可配置 (默认: 100) | t2 配额为 0 |

> **自定义素材说明**:
> - t1 试用期内可上传，试用期结束后已上传素材保留但冻结
> - t2 不支持上传自定义素材，可查看和使用已有素材
> - t3 可上传自定义素材，有数量限制

### 2.2 编辑器功能 (Editor)

| # | 功能 | Key | 游客 | t1 试用期内 | t1 超出试用期 | t2 | t3 | 控制方式 |
|---|------|-----|:---:|:---:|:---:|:---:|:---:|---------|
| 8 | 使用平台素材 | `feature.platform_assets` | YES | YES | YES | YES | YES | 运维可全局关闭 |
| 9 | 矢量图工具 | `feature.vector_tools` | YES | YES | YES | YES | YES | 运维可全局关闭 |
| 10 | 画笔工具 | `feature.freehand_tools` | YES | YES | YES | YES | YES | 运维可全局关闭 |
| 11 | Page 中剪贴板粘贴 | `feature.clipboard_paste` | NO | YES | NO | NO | YES | 入口与快捷键控制 |
| 12 | AI 生成素材 | `feature.ai_generate_assets` | NO | YES | NO | YES | YES | AI入口按钮控制 |
| 13 | AI 生成 Page | `feature.ai_generate_page` | NO | YES | NO | YES | YES | AI入口按钮控制 |
| 14 | Smart Scan | `feature.smart_scan` | NO | YES | NO | NO | YES | Smart Scan入口控制 |

### 2.3 导出功能 (Export)

| # | 功能 | Key | 游客 | t1 试用期内 | t1 超出试用期 | t2 | t3 | 控制方式 |
|---|------|-----|:---:|:---:|:---:|:---:|:---:|---------|
| 15 | PDF 打印 | `feature.pdf_print` | NO | YES | YES | YES | YES | PDF打印按钮 |
| 16 | PDF 下载 | `feature.pdf_download` | NO | YES | YES | YES | YES | PDF下载按钮 |
| 17 | ZIP 导出 | `feature.zip_export` | NO | YES | NO | NO | YES | ZIP下载按钮 |

### 2.4 商城功能 (Marketplace)

| # | 功能 | Key | 游客 | t1 试用期内 | t1 超出试用期 | t2 | t3 | 控制方式 |
|---|------|-----|:---:|:---:|:---:|:---:|:---:|---------|
| 18 | 发布付费项目/素材 | `feature.publish_paid` | NO | YES | NO | NO | YES | Publish按钮 |
| 19 | 发布免费项目/素材 | `feature.publish_free` | NO | YES | NO | YES | YES | Publish按钮 |
| 20 | 浏览商城 | `feature.browse_marketplace` | NO | YES | NO | YES | YES | 路由拦截 |
| 21 | 购买商城内项目/素材 | `feature.purchase_marketplace` | NO | YES | NO | YES | YES | 购买按钮 |

### 2.5 数据恢复 (Recovery)

| # | 功能 | Key | 游客 | t1 试用期内 | t1 超出试用期 | t2 | t3 | 控制方式 |
|---|------|-----|:---:|:---:|:---:|:---:|:---:|---------|
| 22 | 30 天内恢复删除 | `feature.recover_deleted` | NO | NO | NO | NO | YES | Trash恢复按钮 |

### 2.6 分享功能 (Share)

| # | 功能 | Key | 游客 | t1 试用期内 | t1 超出试用期 | t2 | t3 | 控制方式 |
|---|------|-----|:---:|:---:|:---:|:---:|:---:|---------|
| 23 | 公开分享项目链接 | `feature.share_public_link` | NO | NO | NO | YES | YES | 分享按钮 |

### 2.7 订阅与支付 (Payment)

| # | 功能 | Key | 游客 | t1 试用期内 | t1 超出试用期 | t2 | t3 | 控制方式 |
|---|------|-----|:---:|:---:|:---:|:---:|:---:|---------|
| 24 | 订阅 Plan | `feature.can_subscribe` | NO | YES | YES | YES | YES | Pricing入口 |
| 25 | 购买 Credits | `feature.can_purchase_credits` | NO | NO | NO | YES | YES | 购买入口 |

### 2.8 页面访问控制 (Page Access)

| # | 页面 | 游客 | t1 | t2 | t3 | 控制方式 |
|---|------|:---:|:---:|:---:|:---:|---------|
| 26 | Landing 页 | 可见 | 可见 | 可见 | 可见 | 页面按钮控制 |
| 27 | Marketplace 页 | 跳登录页 | 可见 | 可见 | 可见 | 路由拦截 |
| 28 | Dashboard 页 | 跳登录页 | 可见 | 可见 | 可见 | 路由拦截 |
| 29 | Create 页 | 跳登录页 | 可见 | 可见 | 可见 | 路由拦截 |
| 30 | Profile 页 | 跳登录页 | 可见 | 可见 | 可见 | 路由拦截 |
| 31 | Notification 页 | 跳登录页 | 可见 | 可见 | 可见 | 路由拦截 |
| 32 | Transaction History 页 | 跳登录页 | 可见 | 可见 | 可见 | 路由拦截 |
| 33 | Manual/News 页 | 可见 | 可见 | 可见 | 可见 | 无需控制 |
| 34 | 静态页面 | 可见 | 可见 | 可见 | 可见 | 无需控制 |

### 2.9 UI 组件 (Components)

| # | 组件 | 游客 | t1 | t2 | t3 | 控制方式 |
|---|------|:---:|:---:|:---:|:---:|---------|
| 35 | Pricing 按钮 | 弹窗 | 弹窗 | 弹窗 | 弹窗 | 按登录与tier |
| 36 | CTA 按钮 | 跳登录页 | 可用 | 可用 | 可用 | 按登录与tier |
| 37 | Help 按钮 | 可用 | 可用 | 可用 | 可用 | 无需控制 |

---

## 三、功能 Key 映射表

| # | PRD 功能名 | 后端 FeatureKey | 前端 FEATURES | 当前代码状态 | 说明 |
|---|-----------|----------------|--------------|-------------|------|
| 8 | 使用平台素材 | `platform_assets` | `PLATFORM_ASSETS` | ❌ 需新增 | |
| 9 | 矢量图工具 | `vector_tools` | `VECTOR_TOOLS` | ❌ 需新增 | |
| 10 | 画笔工具 | `freehand_tools` | `FREEHAND_TOOLS` | ❌ 需新增 | |
| 11 | 剪贴板粘贴 | `clipboard_paste` | `CLIPBOARD_PASTE` | ⚠️ 后端有，前端无 | |
| 12 | AI 生成素材 | `ai_features` | `AI_FEATURES` | ✅ 有 | 与 #13 共用 |
| 13 | AI 生成 Page | `ai_features` | `AI_FEATURES` | ✅ 复用 | 与 #12 共用 |
| 14 | Smart Scan | `smart_scan` | `SMART_SCAN` | ✅ 有 | |
| 15 | PDF 打印 | `pdf_print` | `PDF_PRINT` | ✅ 有 | |
| 16 | PDF 下载 | `pdf_export` | `PDF_EXPORT` | ✅ 有 | |
| 17 | ZIP 导出 | `zip_export` | `ZIP_EXPORT` | ✅ 有 | |
| 18 | 发布付费 | `publish_paid` | `PUBLISH_PAID` | ❌ 需新增 | |
| 19 | 发布免费 | `publish_free` | `PUBLISH_FREE` | ❌ 需新增 | |
| 20 | 浏览商城 | `browse_marketplace` | `BROWSE_MARKETPLACE` | ⚠️ 后端有，前端无 | |
| 21 | 购买商城 | `purchase_marketplace` | `PURCHASE_MARKETPLACE` | ⚠️ 后端有，前端无 | |
| 22 | 30天恢复 | `recover_deleted` | `RECOVER_DELETED` | ❌ 需新增 | |
| 23 | 公开分享链接 | `share_public_link` | `SHARE_PUBLIC_LINK` | ❌ 需新增 | |
| 24 | 订阅 Plan | `can_subscribe` | `CAN_SUBSCRIBE` | ✅ 有 | |
| 25 | 购买 Credits | `can_purchase_credits` | `CAN_PURCHASE_CREDITS` | ✅ 有 | |

---

## 四、交互规则

### 4.1 被锁定功能的交互

| 情况 | 交互方式 |
|------|---------|
| 功能可见但锁定 | 显示锁图标，点击弹升级 |
| 功能完全隐藏 | 不显示入口 |
| 配额已满 | 按钮置灰并提示 |

### 4.2 试用期交互

| 状态 | 显示 | 交互 |
|------|------|------|
| 试用期内 (>3天) | Banner 可关闭 | 正常使用 |
| 试用期内 (≤3天) | Banner 不可关闭 | 强提醒 |
| 试用期结束当天 | Modal 弹窗 | 必须操作 |
| 试用期已过 | 持续 Banner | 功能锁定 |

---

## 五、Workspace 成员权限规则

> Workspace 是协作空间，t3 用户可以邀请 t2/t3 用户加入协作。

### 5.1 角色定义

| 角色 | 说明 | 可授予给 |
|------|------|----------|
| **Owner** | Workspace 创建者 | 仅 t3 用户 |
| **Admin** | 可管理成员、项目设置 | 仅 t3 成员 |
| **Editor** | 可编辑被授权的项目 | t2/t3 成员 |

### 5.2 项目权限等级

| 等级 | 权限 |
|:----:|------|
| 0 | 不可见 |
| 1 | 只读 |
| 2 | 读写 |

### 5.3 功能权限与 Tier 的关系

- 操作权限由项目授权决定
- 功能权限跟随成员自身 Tier

---

## 六、积分系统 (Credits)

> 详细规则参见 `docs/v2/03-business/entitlement/credits-lifecycle.md`

### 6.1 积分获取

| 来源 | 类型 | 数量 | 有效期 | 适用 Tier |
|------|------|------|--------|-----------|
| 订阅发放 | subscription | t2=100, t3=200 | 当月月底 | t2, t3 |
| 注册赠送 | bonus_signup | 100 | 永久 | t1 |
| 积分购买 | purchase | 100/500/2000 | 永久 | t2, t3 |
| 邀请奖励 | bonus_referral | 配置 | 永久 | 全部 |
| 营销活动 | bonus_campaign | 配置 | 30-90天 | 配置 |
| 客服补偿 | compensation | 配置 | 永久 | 配置 |

### 6.2 积分消耗

| 功能 | Key (原价) | Key (现价) | 原价 | 现价 |
|------|------------|------------|:----:|:----:|
| AI 生成素材 | `cost.ai_generate.original` | `cost.ai_generate.current` | 5 | 1 |
| AI 生成 Page | `cost.ai_page.original` | `cost.ai_page.current` | 5 | 1 |
| OCR 识别 | `cost.ocr.original` | `cost.ocr.current` | 5 | 1 |

### 6.3 扣费优先级 (FEFO)

```
1. 先扣即将过期的积分 (expires_at 升序)
2. 永久积分按来源优先级扣费:
   subscription > bonus_signup > bonus_referral > bonus_campaign > earning > purchase > compensation
```

---

## 七、AI 功能权限矩阵

| 功能 | Key | 游客 | t1 试用期 | t1 超出试用期 | t2 | t3 | 原价 | 现价 |
|------|-----|:----:|:---------:|:-------------:|:--:|:--:|:----:|:----:|
| AI 生成素材 | `feature.ai_generate_assets` | ❌ | ✅ | ❌ | ✅ | ✅ | 5 | 1 |
| AI 生成 Page | `feature.ai_generate_page` | ❌ | ✅ | ❌ | ✅ | ✅ | 5 | 1 |
| Smart Scan | `feature.smart_scan` | ❌ | ✅ | ❌ | ❌ | ✅ | 5 | 1 |
| 剪贴板粘贴 | `feature.clipboard_paste` | ❌ | ✅ | ❌ | ❌ | ✅ | - | 0 |

---

## 八、导出功能权限矩阵

| 功能 | Key | 游客 | t1 试用期 | t1 超出试用期 | t2 | t3 |
|------|-----|:----:|:---------:|:-------------:|:--:|:--:|
| 预览项目 | `feature.preview_project` | ❌ | ✅ | ✅ | ✅ | ✅ |
| PDF 打印 | `feature.pdf_print` | ❌ | ✅ | ✅ | ✅ | ✅ |
| PDF 下载 | `feature.pdf_download` | ❌ | ✅ | ✅ | ✅ | ✅ |
| ZIP 导出 | `feature.zip_export` | ❌ | ✅ | ❌ | ❌ | ✅ |

---

## 九、特殊优惠权限

### 教育优惠

| 对象 | 折扣 | 认证方式 | 有效期 |
|------|------|----------|--------|
| 学生 | 50% | .edu 邮箱 / 学生证 | 1 年 |
| 教师 | 50% | .edu 邮箱 / 教师证 | 1 年 |
| 机构 | 50% | 机构证明 | 合同期 |

### 邀请奖励

| 角色 | 配置 Key | 默认值 | 积分类型 |
|------|----------|--------|----------|
| 邀请人 | `referral.referrer_reward` | 配置 | bonus_referral |
| 被邀请人 | `referral.referee_reward` | 配置 | bonus_referral |
