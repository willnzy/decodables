# User API 端点清单

> **同步范围**: [fullstack]
> **状态**: 🟢 已验证 (来源: v2 文档 + 代码分析)
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `api/user/` 目录

---

## 一、概述

### 1.1 端点基础路径

```
/api/v2/user/*
```

### 1.2 认证说明

| 认证状态 | 说明 |
|----------|------|
| ✅ 需认证 | 需要 Authorization: Bearer token |
| ❌ 无需认证 | 公开接口 |
| Admin | 需要 Admin 权限 |

---

## 二、Profile (用户资料)

| 端点 | 方法 | 认证 | 说明 |
|------|------|:----:|------|
| `/api/v2/user/profile/me` | GET | ✅ | 获取当前用户信息 |
| `/api/v2/user/profile/me` | PATCH | ✅ | 更新用户信息 |
| `/api/v2/user/profile/avatar` | PUT | ✅ | 上传头像 |
| `/api/v2/user/profile/history` | GET | ✅ | 获取操作历史 |
| `/api/v2/user/profile/purchases` | GET | ✅ | 获取购买记录 |
| `/api/v2/user/profile/notifications` | GET | ✅ | 获取通知列表 |
| `/api/v2/user/profile/notifications/{id}/read` | POST | ✅ | 标记通知已读 |
| `/api/v2/user/profile/notifications/read-all` | POST | ✅ | 全部标记已读 |
| `/api/v2/user/profile/timezone` | PUT | ✅ | 更新时区设置 |

---

## 三、Billing (计费)

| 端点 | 方法 | 认证 | 说明 |
|------|------|:----:|------|
| `/api/v2/user/billing/credits` | GET | ✅ | 获取积分余额 |
| `/api/v2/user/billing/transactions` | GET | ✅ | 获取交易历史 |
| `/api/v2/user/billing/can-afford` | GET | ✅ | 检查积分是否足够 |
| `/api/v2/user/billing/subscription` | GET | ✅ | 获取订阅状态 |

---

## 四、Projects (项目)

| 端点 | 方法 | 认证 | 说明 |
|------|------|:----:|------|
| `/api/v2/user/projects` | GET | ✅ | 获取项目列表 |
| `/api/v2/user/projects` | POST | ✅ | 创建项目 |
| `/api/v2/user/projects/dashboard` | GET | ✅ | Dashboard 数据 |
| `/api/v2/user/projects/deleted` | GET | ✅ | 已删除项目 |
| `/api/v2/user/projects/{id}` | GET | ✅ | 获取项目详情 |
| `/api/v2/user/projects/{id}` | PUT | ✅ | 更新项目 |
| `/api/v2/user/projects/{id}` | DELETE | ✅ | 删除项目 |
| `/api/v2/user/projects/{id}/restore` | POST | ✅ | 恢复项目 |
| `/api/v2/user/projects/{id}/duplicate` | POST | ✅ | 复制项目 |

---

## 五、Assets (素材)

| 端点 | 方法 | 认证 | 说明 |
|------|------|:----:|------|
| `/api/v2/user/assets` | GET | ✅ | 获取素材列表 |
| `/api/v2/user/assets` | POST | ✅ | 上传素材 |
| `/api/v2/user/assets/{id}` | GET | ✅ | 获取素材详情 |
| `/api/v2/user/assets/{id}` | DELETE | ✅ | 删除素材 |
| `/api/v2/user/assets/from-url` | POST | ✅ | 从 URL 创建素材 |
| `/api/v2/user/assets/check-url` | GET | ✅ | 检查 URL 有效性 |
| `/api/v2/user/assets/{id}/increment-usage` | POST | ✅ | 增加使用次数 |
| `/api/v2/user/assets/dashboard` | GET | ✅ | 素材统计 |
| `/api/v2/user/assets/deleted` | GET | ✅ | 已删除素材 |
| `/api/v2/user/assets/{id}/restore` | POST | ✅ | 恢复素材 |

---

## 六、Generation (AI 生成)

| 端点 | 方法 | 认证 | 说明 |
|------|------|:----:|------|
| `/api/v2/user/generate/images/images` | POST | ✅ | AI 生成图片 |
| `/api/v2/user/generate/images/images/async` | POST | ✅ | 异步生成图片 |
| `/api/v2/user/generate/pdf/pdf` | POST | ✅ | 生成 PDF |
| `/api/v2/user/generate/story/story` | POST | ✅ | 生成故事 |
| `/api/v2/user/generate/story/inspiration` | POST | ✅ | 获取灵感建议 |

---

## 七、Generations (生成历史)

| 端点 | 方法 | 认证 | 说明 |
|------|------|:----:|------|
| `/api/v2/user/generations/history` | GET | ✅ | 获取生成历史 |
| `/api/v2/user/generations/{id}` | PATCH | ✅ | 更新生成记录 |
| `/api/v2/user/generations/{id}` | DELETE | ✅ | 删除生成记录 |
| `/api/v2/user/generations/batch-delete` | POST | ✅ | 批量删除 |

---

## 八、Marketplace (商城)

| 端点 | 方法 | 认证 | 说明 |
|------|------|:----:|------|
| `/api/v2/user/marketplace/listings` | GET | ❌ | 获取商品列表 |
| `/api/v2/user/marketplace/listings/{id}` | GET | ❌ | 获取商品详情 |
| `/api/v2/user/marketplace/listings` | POST | ✅ | 发布商品 |
| `/api/v2/user/marketplace/listings/{id}` | PUT | ✅ | 更新商品 |
| `/api/v2/user/marketplace/listings/{id}` | DELETE | ✅ | 下架商品 |
| `/api/v2/user/marketplace/purchase` | POST | ✅ | 购买商品 |
| `/api/v2/user/marketplace/my-listings` | GET | ✅ | 我的商品 |
| `/api/v2/user/marketplace/leaderboard` | GET | ❌ | 排行榜 |
| `/api/v2/user/marketplace/report` | POST | ✅ | 举报商品 |
| `/api/v2/user/marketplace/my-reports` | GET | ✅ | 我的举报 |

---

## 九、Payment (支付)

| 端点 | 方法 | 认证 | 说明 |
|------|------|:----:|------|
| `/api/v2/user/payment/checkout` | POST | ✅ | 创建支付会话 |
| `/api/v2/user/payment/portal` | POST | ✅ | 跳转 Stripe Portal |

---

## 十、Export (导出)

| 端点 | 方法 | 认证 | 说明 |
|------|------|:----:|------|
| `/api/v2/user/export/projects/{id}/pdf` | GET | ✅ | 导出 PDF |
| `/api/v2/user/export/projects/{id}/preview` | GET | ✅ | 预览 PDF |
| `/api/v2/user/export/projects/{id}/zip` | GET | ✅ | 导出 ZIP |
| `/api/v2/user/export/projects/{id}/pdf/async` | POST | ✅ | 异步导出 PDF |
| `/api/v2/user/export/projects/{id}/zip/async` | POST | ✅ | 异步导出 ZIP |

---

## 十一、Templates (模板)

| 端点 | 方法 | 认证 | 说明 |
|------|------|:----:|------|
| `/api/v2/user/templates/asset` | GET | ❌ | 素材模板列表 |
| `/api/v2/user/templates/asset` | POST | ✅ | 创建素材模板 |
| `/api/v2/user/templates/asset/{id}` | PUT | ✅ | 更新模板 |
| `/api/v2/user/templates/asset/{id}` | DELETE | ✅ | 删除模板 |
| `/api/v2/user/templates/asset/{id}/use` | POST | ✅ | 使用模板 |
| `/api/v2/user/templates/page` | GET | ❌ | 页面模板列表 |
| `/api/v2/user/templates/page` | POST | ✅ | 创建页面模板 |
| `/api/v2/user/templates/page/{id}` | PUT | ✅ | 更新页面模板 |
| `/api/v2/user/templates/page/{id}` | DELETE | ✅ | 删除页面模板 |
| `/api/v2/user/templates/page/{id}/use` | POST | ✅ | 使用页面模板 |

---

## 十二、Resources (系统资源)

| 端点 | 方法 | 认证 | 说明 |
|------|------|:----:|------|
| `/api/v2/user/resources` | GET | ❌ | 获取资源列表 |
| `/api/v2/user/resources/types` | GET | ❌ | 获取资源类型 |
| `/api/v2/user/resources/categories/{type}` | GET | ❌ | 按类型获取分类 |
| `/api/v2/user/resources/{id}` | GET | ❌ | 获取资源详情 |

---

## 十三、Onboarding (新手引导)

| 端点 | 方法 | 认证 | 说明 |
|------|------|:----:|------|
| `/api/v2/user/onboarding/steps` | GET | ✅ | 获取引导步骤 |
| `/api/v2/user/onboarding/steps/start` | POST | ✅ | 开始引导 |
| `/api/v2/user/onboarding/steps/complete` | POST | ✅ | 完成步骤 |
| `/api/v2/user/onboarding/steps/skip` | POST | ✅ | 跳过引导 |
| `/api/v2/user/onboarding/checklist` | GET | ✅ | 获取清单状态 |

---

## 十四、Config (配置)

| 端点 | 方法 | 认证 | 说明 |
|------|------|:----:|------|
| `/api/v2/user/config` | GET | ❌ | 获取公开配置 |
| `/api/v2/user/config/group/{name}` | GET | ❌ | 按组获取配置 |
| `/api/v2/user/config/{key}` | GET | ❌ | 获取单个配置 |

---

## 十五、其他端点

### 15.1 Themes (主题)

| 端点 | 方法 | 认证 | 说明 |
|------|------|:----:|------|
| `/api/v2/user/themes/current` | GET | ❌ | 获取当前主题 |

### 15.2 Tasks (异步任务)

| 端点 | 方法 | 认证 | 说明 |
|------|------|:----:|------|
| `/api/v2/user/tasks/{id}` | GET | ✅ | 获取任务状态 |
| `/api/v2/user/tasks/{id}/cancel` | POST | ✅ | 取消任务 |

### 15.3 Tools (工具)

| 端点 | 方法 | 认证 | 说明 |
|------|------|:----:|------|
| `/api/v2/user/tools/pdf-preview` | POST | ✅ | PDF 预览 |
| `/api/v2/user/tools/ocr` | POST | ✅ | OCR 识别 |

### 15.4 Support (客服)

| 端点 | 方法 | 认证 | 说明 |
|------|------|:----:|------|
| `/api/v2/user/support/ticket` | POST | ✅ | 提交工单 |
| `/api/v2/user/support/chat` | POST | ✅ | 在线客服 |
| `/api/v2/user/support/contact` | POST | ✅ | 联系我们 |
| `/api/v2/user/support/feedback` | POST | ✅ | 提交反馈 |

### 15.5 Referrals (推荐)

| 端点 | 方法 | 认证 | 说明 |
|------|------|:----:|------|
| `/api/v2/user/referrals` | POST | ✅ | 创建推荐 |
| `/api/v2/user/referrals` | GET | ✅ | 获取推荐列表 |
| `/api/v2/user/referrals/stats` | GET | ✅ | 推荐统计 |
| `/api/v2/user/referrals/code/{code}` | GET | ❌ | 验证推荐码 |
| `/api/v2/user/referrals/{id}/complete` | POST | ✅ | 完成推荐 |

### 15.6 Experiments (实验)

| 端点 | 方法 | 认证 | 说明 |
|------|------|:----:|------|
| `/api/v2/user/experiments/{key}/assign` | POST | ❌ | 分配实验组 |
| `/api/v2/user/experiments/{key}/exposure` | POST | ❌ | 记录曝光 |
| `/api/v2/user/experiments/{key}/conversion` | POST | ❌ | 记录转化 |

### 15.7 Analytics (分析)

| 端点 | 方法 | 认证 | 说明 |
|------|------|:----:|------|
| `/api/v2/user/analytics/events` | POST | ❌ | 上报事件 |

### 15.8 Logs (日志)

| 端点 | 方法 | 认证 | 说明 |
|------|------|:----:|------|
| `/api/v2/user/logs/error` | POST | ❌ | 上报错误 |
| `/api/v2/user/logs/errors` | POST | ❌ | 批量上报错误 |

---

## 十六、端点统计

| 分类 | 端点数 |
|------|:------:|
| Profile | 9 |
| Billing | 4 |
| Projects | 9 |
| Assets | 10 |
| Generation | 5 |
| Generations | 4 |
| Marketplace | 10 |
| Payment | 2 |
| Export | 5 |
| Templates | 10 |
| Resources | 4 |
| Onboarding | 5 |
| Config | 3 |
| 其他 | ~30 |
| **总计** | **~110** |

---

## 十七、相关文档

- [API 参考文档](./api-reference.md)
- [Admin API 端点](./admin-endpoints.md)
- [认证模块](../modules/auth/architecture.md)

---

**END OF DOCUMENT**
