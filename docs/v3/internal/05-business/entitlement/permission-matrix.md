# 功能权限矩阵

> **同步范围**: [fullstack]
> **状态**: 🟢 已验证 (来源: v2 文档 + 代码分析)
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `domains/identity/constants.py`, `system_configs` 表

---

## 一、概述

### 1.1 目的

定义各 Tier 用户的功能权限和配额限制，作为前后端权限判断的唯一数据源。

### 1.2 设计原则

- 所有配额数值通过 `system_configs` 配置，代码不硬编码
- 权限通过 Feature Key 统一管理
- 前后端使用相同的权限判断逻辑

---

## 二、用户身份层级

### 2.1 认证层 (Authentication)

| 身份 | 判断依据 | 数据库记录 |
|------|---------|-----------|
| **游客 (Guest)** | `isSignedIn: false` | 无 |
| **注册用户** | `isSignedIn: true` | profiles 表 |

### 2.2 授权层 (Authorization)

| Tier | 代码 | 显示名称 | 月度积分 | 价格 |
|------|------|---------|:-------:|------|
| Free | `t1` | Free Plan | 0 | $0 |
| Starter | `t2` | Starter Plan | 100 | $6.9/月 |
| Pro | `t3` | Pro Plan | 200 | $9.9/月 |
| (预留) | `t4` | (未定) | (未定) | (未定) |

> **t4 说明**: t4 为未来预留层级，当前不对外开放，前端不展示。

### 2.3 试用期 (Trial)

| 属性 | 说明 |
|------|------|
| 适用对象 | 仅 t1 用户 |
| 默认天数 | 30 天 |
| 计算方式 | `当前时间 - 注册时间 ≤ trial_days` |
| 配置 Key | `trial.default_days` |

---

## 三、完整功能权限矩阵

> **权限值说明**:
> - `YES` = 完全可用
> - `NO` = 不可用 (功能可见但带锁)
> - `trial` = 试用期内可用
> - `N/A` = 无此功能

### 3.1 资源数量限制 (Quota)

| # | 功能 | Key | 游客 | t1 试用期 | t1 超出 | t2 | t3 |
|---|------|-----|:---:|:---------:|:-------:|:--:|:--:|
| 1 | Workspace 最大数量 | `quota.max_workspaces` | 0 | 1 | 1 | 1 | ∞ |
| 2 | 文件夹最大数量 | `quota.max_folders` | 0 | 1 | 1 | 5 | ∞ |
| 3 | 项目最大数量 | `quota.max_projects` | 0 | 1 | 1 | 10 | 50 |
| 4 | 自定义素材上传 | `feature.can_upload_custom_assets` | NO | YES | NO | NO | YES |
| 5 | 自定义素材最大数量 | `quota.max_custom_assets` | 0 | 10 | 0 | 0 | 100 |

### 3.2 编辑器功能 (Editor)

| # | 功能 | Key | 游客 | t1 试用期 | t1 超出 | t2 | t3 |
|---|------|-----|:---:|:---------:|:-------:|:--:|:--:|
| 6 | 使用平台素材 | `feature.platform_assets` | YES | YES | YES | YES | YES |
| 7 | 矢量图工具 | `feature.vector_tools` | YES | YES | YES | YES | YES |
| 8 | 画笔工具 | `feature.freehand_tools` | YES | YES | YES | YES | YES |
| 9 | 剪贴板粘贴 | `feature.clipboard_paste` | NO | YES | NO | NO | YES |
| 10 | AI 生成素材 | `feature.ai_generate_assets` | NO | YES | NO | YES | YES |
| 11 | AI 生成 Page | `feature.ai_generate_page` | NO | YES | NO | YES | YES |
| 12 | Smart Scan (OCR) | `feature.smart_scan` | NO | YES | NO | NO | YES |

### 3.3 导出功能 (Export)

| # | 功能 | Key | 游客 | t1 试用期 | t1 超出 | t2 | t3 |
|---|------|-----|:---:|:---------:|:-------:|:--:|:--:|
| 13 | PDF 打印 | `feature.pdf_print` | NO | YES | YES | YES | YES |
| 14 | PDF 下载 | `feature.pdf_download` | NO | YES | YES | YES | YES |
| 15 | ZIP 导出 | `feature.zip_export` | NO | YES | NO | NO | YES |

### 3.4 商城功能 (Marketplace)

| # | 功能 | Key | 游客 | t1 试用期 | t1 超出 | t2 | t3 |
|---|------|-----|:---:|:---------:|:-------:|:--:|:--:|
| 16 | 浏览商城 | `feature.browse_marketplace` | NO | YES | NO | YES | YES |
| 17 | 发布免费内容 | `feature.publish_free` | NO | YES | NO | YES | YES |
| 18 | 发布付费内容 | `feature.publish_paid` | NO | YES | NO | NO | YES |
| 19 | 购买商城内容 | `feature.purchase_marketplace` | NO | YES | NO | YES | YES |

### 3.5 其他功能

| # | 功能 | Key | 游客 | t1 试用期 | t1 超出 | t2 | t3 |
|---|------|-----|:---:|:---------:|:-------:|:--:|:--:|
| 20 | 30 天内恢复删除 | `feature.recover_deleted` | NO | NO | NO | NO | YES |
| 21 | 公开分享链接 | `feature.share_public_link` | NO | NO | NO | YES | YES |
| 22 | 订阅 Plan | `feature.can_subscribe` | NO | YES | YES | YES | YES |
| 23 | 购买 Credits | `feature.can_purchase_credits` | NO | NO | NO | YES | YES |

---

## 四、页面访问控制

| # | 页面 | 游客 | t1 | t2 | t3 |
|---|------|:---:|:--:|:--:|:--:|
| 1 | Landing 页 | 可见 | 可见 | 可见 | 可见 |
| 2 | Dashboard 页 | 跳登录 | 可见 | 可见 | 可见 |
| 3 | Create 页 | 跳登录 | 可见 | 可见 | 可见 |
| 4 | Marketplace 页 | 跳登录 | 可见 | 可见 | 可见 |
| 5 | Profile 页 | 跳登录 | 可见 | 可见 | 可见 |
| 6 | Manual/News 页 | 可见 | 可见 | 可见 | 可见 |

---

## 五、AI 功能权限与消耗

| 功能 | 游客 | t1 试用期 | t1 超出 | t2 | t3 | 积分消耗 |
|------|:---:|:---------:|:-------:|:--:|:--:|:-------:|
| AI 生成素材 | ❌ | ✅ | ❌ | ✅ | ✅ | 5 |
| AI 生成 Page | ❌ | ✅ | ❌ | ✅ | ✅ | 5 |
| Smart Scan | ❌ | ✅ | ❌ | ❌ | ✅ | 5 |

---

## 六、交互规则

### 6.1 被锁定功能的交互

| 情况 | 交互方式 |
|------|---------|
| 功能可见但锁定 | 显示锁图标，点击弹升级窗口 |
| 功能完全隐藏 | 不显示入口 |
| 配额已满 | 按钮置灰并提示 |

### 6.2 试用期交互

| 状态 | 显示 | 交互 |
|------|------|------|
| 试用期内 (>3天) | Banner 可关闭 | 正常使用 |
| 试用期内 (≤3天) | Banner 不可关闭 | 强提醒 |
| 试用期结束当天 | Modal 弹窗 | 必须操作 |
| 试用期已过 | 持续 Banner | 功能锁定 |

---

## 七、Feature Key 映射表

| PRD 功能名 | 后端 Key | 前端常量 | 状态 |
|-----------|----------|---------|------|
| AI 生成素材 | `ai_features` | `AI_FEATURES` | ✅ |
| AI 生成 Page | `ai_features` | `AI_FEATURES` | ✅ |
| Smart Scan | `smart_scan` | `SMART_SCAN` | ✅ |
| PDF 打印 | `pdf_print` | `PDF_PRINT` | ✅ |
| PDF 下载 | `pdf_export` | `PDF_EXPORT` | ✅ |
| ZIP 导出 | `zip_export` | `ZIP_EXPORT` | ✅ |
| 订阅 | `can_subscribe` | `CAN_SUBSCRIBE` | ✅ |
| 购买积分 | `can_purchase_credits` | `CAN_PURCHASE_CREDITS` | ✅ |

---

## 八、相关文档

- [Tier 系统概述](../tier-system/overview.md)
- [积分系统流程](../credits-system/flow.md)
- [系统设计](./system-design.md)
- [订阅生命周期](./billing-lifecycle.md)

---

**END OF DOCUMENT**
