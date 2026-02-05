# 模块文档

> **同步范围**: [fullstack]
> **状态**: 🟡 待完善

---

## 目录说明

按业务域组织的模块技术文档，描述模块的架构和实现。

## 模块列表

| 模块 | 说明 | 对应代码 |
|------|------|----------|
| `editor/` | 编辑器模块 | creation, templates, export |
| `dashboard/` | 仪表盘模块 | workspace, folder, stats |
| `marketplace/` | 素材市场模块 | marketplace, assets, content, themes |
| `billing/` | 计费模块 | billing, subscriptions |
| `auth/` | 认证模块 | auth, identity |
| `ai/` | AI 服务模块 | generation, shared/ai |
| `platform/` | 平台服务模块 | platform, feature_flags, onboarding, events |
| `admin/` | 管理后台模块 | admin, moderation, support |
| `content/` | 内容管理模块 | articles, static_pages, marketing |

## 文档结构

每个模块目录应包含：
- `README.md` - 模块概览、代码结构
- `architecture.md` - 模块架构设计（可选）
- `api.md` - 模块 API 定义（可选）
