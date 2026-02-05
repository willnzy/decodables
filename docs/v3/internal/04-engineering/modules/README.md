# 模块文档

> **同步范围**: [fullstack]
> **状态**: 🟡 待完善

---

## 目录说明

按业务域组织的模块技术文档，描述模块的架构和实现。

## 模块列表

### 核心模块

| 模块 | 说明 | 后端 Domains | 前端代码 |
|------|------|--------------|----------|
| `editor/` | 编辑器模块 | creation, templates, export | `@business/editor/` |
| `dashboard/` | 仪表盘模块 | workspace, folder, stats | `@business/dashboard/` |
| `marketplace/` | 素材市场模块 | marketplace, assets, content, themes | `@business/marketplace/` |

### 用户模块

| 模块 | 说明 | 后端 Domains | 前端代码 |
|------|------|--------------|----------|
| `auth/` | 认证模块 | auth, identity | `@shared/auth/` |
| `billing/` | 计费模块 | billing, subscriptions, credits | `@business/billing/` |
| `profile/` | 个人资料模块 | profile, user_preferences | `@business/profile/` |

### AI 模块

| 模块 | 说明 | 后端 Domains | 前端代码 |
|------|------|--------------|----------|
| `ai/` | AI 服务模块 | generation, shared/ai, text_processing, image_processing | `@business/ai/` |

### 平台模块

| 模块 | 说明 | 后端 Domains | 前端代码 |
|------|------|--------------|----------|
| `platform/` | 平台服务 | platform, feature_flags, onboarding, events | `@core/platform/` |
| `notifications/` | 通知模块 | notifications | `@business/notifications/` |
| `search/` | 搜索模块 | search | `@business/search/` |
| `favorites/` | 收藏模块 | favorites | `@business/favorites/` |
| `analytics/` | 数据分析模块 | analytics, tracking | `@shared/analytics/` |

### 管理模块

| 模块 | 说明 | 后端 Domains | 前端代码 |
|------|------|--------------|----------|
| `admin/` | 管理后台 | admin, moderation, support | `app/(admin)/` |
| `content/` | 内容管理 | articles, static_pages, marketing | `@business/content/` |

### 基础设施模块

| 模块 | 说明 | 后端代码 | 前端代码 |
|------|------|----------|----------|
| `storage/` | 文件存储 | shared/storage | `@shared/storage/` |
| `email/` | 邮件服务 | shared/email | - |
| `payment/` | 支付服务 | shared/payment | `@shared/payment/` |

## 后端 Domains 完整映射

```
domains/
├── admin/           → admin/
├── analytics/       → analytics/
├── articles/        → content/
├── assets/          → marketplace/
├── auth/            → auth/
├── billing/         → billing/
├── content/         → marketplace/
├── creation/        → editor/
├── events/          → platform/
├── export/          → editor/
├── favorites/       → favorites/
├── feature_flags/   → platform/
├── folder/          → dashboard/
├── generation/      → ai/
├── identity/        → auth/
├── image_processing → ai/
├── marketplace/     → marketplace/
├── marketing/       → content/
├── moderation/      → admin/
├── notifications/   → notifications/
├── onboarding/      → platform/
├── platform/        → platform/
├── profile/         → profile/
├── search/          → search/
├── static_pages/    → content/
├── stats/           → dashboard/
├── subscriptions/   → billing/
├── support/         → admin/
├── templates/       → editor/
├── text_processing/ → ai/
├── themes/          → marketplace/
├── tracking/        → analytics/
├── user_preferences → profile/
└── workspace/       → dashboard/
```

## 文档结构

每个模块目录应包含：
- `README.md` - 模块概览、代码结构、域映射
- `architecture.md` - 模块架构设计（可选）
- `api.md` - 模块 API 定义（可选）
- `data-model.md` - 数据模型（可选）