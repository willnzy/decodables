# 技术文档

> **说明**: 定义技术架构和开发规范，指导如何实现

---

## 目录结构

```
04-engineering/
├── README.md              # 本文件
│
├── architecture/          # 架构设计
│   ├── overview.md        # 系统全景
│   ├── backend.md         # 后端架构（DDD）
│   ├── frontend.md        # 前端架构
│   └── decisions/         # ADR（架构决策记录）
│
├── modules/               # 模块技术设计
│   ├── editor/            # 编辑器模块
│   ├── dashboard/         # Dashboard 模块
│   ├── marketplace/       # Marketplace 模块
│   ├── billing/           # 计费模块
│   └── auth/              # 认证模块
│
├── development/           # 开发规范
│   ├── backend.md         # 后端开发规范
│   ├── frontend.md        # 前端开发规范
│   ├── api-guide.md       # API 设计规范
│   ├── database.md        # 数据库规范
│   └── testing.md         # 测试规范
│
├── api/                   # API 参考
│   ├── user-endpoints.md  # 用户端 API
│   └── admin-endpoints.md # 管理端 API
│
└── data/                  # 数据模型
    ├── schema.md          # 数据库 Schema
    └── entities.md        # 实体定义
```

---

## architecture/ 架构设计

| 文档 | 说明 | 来源 |
|------|------|------|
| `overview.md` | 系统全景：前后端交互、部署架构 | v2/01-architecture/architecture-proposal.md |
| `backend.md` | 后端 DDD 架构：分层、依赖、模块划分 | v2/01-architecture/backend-architecture.md |
| `frontend.md` | 前端架构：目录结构、状态管理、路由 | v2/01-architecture/frontend-architecture.md |
| `decisions/` | ADR：重要架构决策记录 | v2/01-architecture/adr/ |

---

## modules/ 模块技术设计

每个模块目录包含：

```
modules/{module}/
├── README.md          # 模块概述
├── entities.md        # 领域实体
├── services.md        # 服务层设计
├── api.md             # API 设计
└── frontend.md        # 前端实现
```

| 模块 | 说明 | 来源 |
|------|------|------|
| `editor/` | 画布、元素、绘图、AI 功能 | v2/04-features/canvas-architecture.md 等 |
| `dashboard/` | 项目管理、文件夹、工作空间 | v2/04-features/user-capabilities/workspace-system-design.md |
| `marketplace/` | 模板浏览、购买、出售 | v2/04-features/user-capabilities/marketplace-system-design.md |
| `billing/` | 订阅、积分、支付 | v2/04-features/user-capabilities/billing-system-design.md |
| `auth/` | 注册、登录、OAuth | v2/01-architecture/self-hosted-auth-design.md |

---

## development/ 开发规范

| 文档 | 说明 | 来源 |
|------|------|------|
| `backend.md` | 后端开发：命名、代码风格、错误处理 | v2/02-standards/backend-naming-standards.md |
| `frontend.md` | 前端开发：组件、状态、Hooks | v2/02-standards/frontend-development-guide.md |
| `api-guide.md` | API 设计：RESTful、命名、版本 | v2/05-api/api-reference.md |
| `database.md` | 数据库：Schema、迁移、索引 | v2/02-standards/database-guide.md |
| `testing.md` | 测试：单元测试、集成测试 | v2/02-standards/testing-guide.md |

---

## api/ API 参考

| 文档 | 说明 | 来源 |
|------|------|------|
| `user-endpoints.md` | 用户端 API 列表 | v2/05-api/user-endpoints.md |
| `admin-endpoints.md` | 管理端 API 列表 | v2/05-api/admin-endpoints.md |

---

## data/ 数据模型

| 文档 | 说明 | 来源 |
|------|------|------|
| `schema.md` | 数据库表结构 | migrations/v2/*.sql |
| `entities.md` | 领域实体定义 | domains/*/entity.py |

---

## 前后端分离说明

| 内容 | 后端仓库 | 前端仓库 |
|------|----------|----------|
| `architecture/backend.md` | ✅ 详细版 | 📋 简化版 |
| `architecture/frontend.md` | 📋 简化版 | ✅ 详细版 |
| `modules/*/entities.md` | ✅ 详细版 | ❌ 无 |
| `modules/*/frontend.md` | ❌ 无 | ✅ 详细版 |
| `development/backend.md` | ✅ 详细版 | ❌ 无 |
| `development/frontend.md` | ❌ 无 | ✅ 详细版 |
| `api/*` | ✅ 两边都有 | ✅ 两边都有 |
