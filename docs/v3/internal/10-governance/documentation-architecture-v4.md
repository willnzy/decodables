# 文档架构设计 v4.0

> **状态**: published
> **版本**: 4.0.0
> **创建日期**: 2026-02-05
> **适用范围**: fullstack
> **同步要求**: 是（前后端保持一致）

---

## 1. 概述

### 1.1 设计目标

本文档定义 Make Decodables 项目的文档架构，支持：

1. **1人 + AI 协作模式** - 文档结构优化为 AI 辅助开发
2. **内部开发** - 产品规格、技术架构、业务规则
3. **外部输出** - Manual 页、News 页、AI 智能客服

### 1.2 核心原则

| 原则 | 说明 |
|------|------|
| **内外分离** | 内部开发文档 vs 外部用户内容 |
| **单一来源** | 每个知识点只在一处定义 |
| **内容转化** | 内部文档 → 外部内容的明确路径 |
| **前后端同步** | 共享文档保持一致 |

---

## 2. 目录结构

```
docs/v3/
├── README.md                            # 📖 文档导航 + AI 上下文入口

│
│  ╔═══════════════════════════════════════════════════════════╗
│  ║  Part A: 内部文档（Internal - 开发协作 + AI 编码辅助）      ║
│  ╚═══════════════════════════════════════════════════════════╝
│
├── internal/
│   │
│   │  ─────────────────────────────────────────────────────────
│   │  第一层：项目全局（给自己和 AI 的上下文）
│   │  ─────────────────────────────────────────────────────────
│   │
│   ├── 01-project/                      # 📌 项目基础
│   │   ├── README.md                    # 项目简介（AI 首先要读的）
│   │   ├── vision.md                    # 产品愿景与定位
│   │   ├── tech-stack.md                # 技术栈
│   │   ├── glossary.md                  # 术语表
│   │   └── decisions-log.md             # 重要决策记录
│   │
│   │  ─────────────────────────────────────────────────────────
│   │  第二层：产品规格（决定做什么）
│   │  ─────────────────────────────────────────────────────────
│   │
│   ├── 02-product/                      # 📋 产品规格
│   │   ├── README.md
│   │   │
│   │   ├── features/                    # 功能规格
│   │   │   ├── README.md                # 功能清单与优先级
│   │   │   ├── editor.md                # 编辑器功能
│   │   │   ├── dashboard.md             # Dashboard
│   │   │   ├── marketplace.md           # Marketplace
│   │   │   ├── billing.md               # 计费
│   │   │   ├── auth.md                  # 认证
│   │   │   └── admin.md                 # Admin
│   │   │
│   │   └── pages/                       # 页面设计
│   │       ├── user/                    # 用户端页面
│   │       └── admin/                   # 管理端页面
│   │
│   │  ─────────────────────────────────────────────────────────
│   │  第三层：设计规范（视觉一致性）
│   │  ─────────────────────────────────────────────────────────
│   │
│   ├── 03-design/                       # 🎨 设计系统
│   │   ├── README.md
│   │   ├── tokens.md                    # 设计 Token（颜色/字体/间距）
│   │   ├── components.md                # 组件规范
│   │   ├── patterns.md                  # 设计模式（响应式/布局）
│   │   └── brand.md                     # 品牌规范
│   │
│   │  ─────────────────────────────────────────────────────────
│   │  第四层：技术实现（怎么开发）
│   │  ─────────────────────────────────────────────────────────
│   │
│   ├── 04-engineering/                  # 💻 技术文档
│   │   ├── README.md
│   │   │
│   │   ├── architecture/                # 架构设计
│   │   │   ├── overview.md              # 系统全景
│   │   │   ├── backend.md               # 后端架构（DDD）
│   │   │   ├── frontend.md              # 前端架构
│   │   │   └── decisions/               # ADR（架构决策记录）
│   │   │
│   │   ├── modules/                     # 模块技术设计
│   │   │   ├── editor/
│   │   │   ├── dashboard/
│   │   │   ├── marketplace/
│   │   │   ├── billing/
│   │   │   └── auth/
│   │   │
│   │   ├── development/                 # 开发规范
│   │   │   ├── backend.md               # 后端开发规范
│   │   │   ├── frontend.md              # 前端开发规范
│   │   │   ├── api-guide.md             # API 设计规范
│   │   │   ├── database.md              # 数据库规范
│   │   │   └── testing.md               # 测试规范
│   │   │
│   │   ├── api/                         # API 参考
│   │   │   ├── user-endpoints.md
│   │   │   └── admin-endpoints.md
│   │   │
│   │   └── data/                        # 数据模型
│   │       ├── schema.md                # 数据库 Schema
│   │       └── entities.md              # 实体定义
│   │
│   │  ─────────────────────────────────────────────────────────
│   │  第五层：业务规则（核心约束）
│   │  ─────────────────────────────────────────────────────────
│   │
│   ├── 05-business/                     # 📋 业务规则
│   │   ├── README.md
│   │   ├── user-system.md               # 用户体系（双 ID）
│   │   ├── tier-system.md               # Tier 体系（t1/t2/t3/t4）
│   │   ├── credits-system.md            # 积分体系
│   │   ├── pricing.md                   # 定价规则
│   │   │
│   │   └── entitlement/                 # 权益系统
│   │       ├── permission-matrix.md     # 权限矩阵
│   │       ├── billing-lifecycle.md     # 订阅生命周期
│   │       └── promotions.md            # 促销规则
│   │
│   │  ─────────────────────────────────────────────────────────
│   │  第六层：运营增长（怎么获客变现）- 策略层
│   │  ─────────────────────────────────────────────────────────
│   │
│   ├── 06-growth/                       # 📈 运营增长策略
│   │   ├── README.md
│   │   │
│   │   ├── acquisition/                 # 用户获取
│   │   │   ├── channels.md              # 渠道策略
│   │   │   ├── content-strategy.md      # 内容策略
│   │   │   └── seo-strategy.md          # SEO 策略
│   │   │
│   │   ├── retention/                   # 用户留存
│   │   │   ├── onboarding.md            # 新手引导设计
│   │   │   ├── engagement.md            # 活跃策略
│   │   │   └── referral.md              # 邀请计划
│   │   │
│   │   ├── monetization/                # 商业化
│   │   │   ├── pricing-strategy.md      # 定价策略
│   │   │   └── conversion.md            # 转化优化
│   │   │
│   │   └── support/                     # 用户支持策略
│   │       ├── support-strategy.md      # 客服策略
│   │       └── ai-customer-service.md   # AI 客服设计
│   │
│   │  ─────────────────────────────────────────────────────────
│   │  第七层：数据洞察（效果如何）
│   │  ─────────────────────────────────────────────────────────
│   │
│   ├── 07-analytics/                    # 📊 数据分析
│   │   ├── README.md
│   │   ├── metrics.md                   # 核心指标定义
│   │   ├── tracking.md                  # 埋点规范
│   │   ├── dashboards.md                # 看板说明
│   │   └── insights-template.md         # 分析报告模板
│   │
│   │  ─────────────────────────────────────────────────────────
│   │  第八层：运维保障
│   │  ─────────────────────────────────────────────────────────
│   │
│   ├── 08-operations/                   # 🔧 运维
│   │   ├── README.md
│   │   ├── deployment.md                # 部署流程
│   │   ├── monitoring.md                # 监控告警
│   │   └── troubleshooting.md           # 故障处理
│   │
│   │  ─────────────────────────────────────────────────────────
│   │  第九层：合规与法务
│   │  ─────────────────────────────────────────────────────────
│   │
│   ├── 09-compliance/                   # ⚖️ 合规
│   │   ├── README.md
│   │   ├── legal-requirements.md        # 法务要求
│   │   └── data-compliance.md           # 数据合规
│   │
│   │  ─────────────────────────────────────────────────────────
│   │  第十层：文档治理
│   │  ─────────────────────────────────────────────────────────
│   │
│   └── 10-governance/                   # 📏 文档治理
│       ├── README.md
│       ├── templates/                   # 文档模板
│       │   ├── faq-template.md
│       │   └── news-template.md
│       └── documentation-governance.md  # 🔑 文档治理规范（归属+内容+操作）

│
│  ╔═══════════════════════════════════════════════════════════╗
│  ║  Part B: 外部内容（Public - 面向用户/营销/AI客服）         ║
│  ╚═══════════════════════════════════════════════════════════╝
│
├── public/
│   │
│   │  ─────────────────────────────────────────────────────────
│   │  用户手册（→ Manual 页面）
│   │  ─────────────────────────────────────────────────────────
│   │
│   ├── manual/                          # 📖 用户手册
│   │   ├── README.md                    # Manual 结构说明
│   │   │
│   │   ├── getting-started/             # 快速入门
│   │   │   ├── what-is-decodables.md    # 产品介绍
│   │   │   ├── create-account.md        # 创建账号
│   │   │   ├── first-project.md         # 创建第一个项目
│   │   │   └── interface-overview.md    # 界面概览
│   │   │
│   │   ├── editor/                      # 编辑器使用
│   │   │   ├── canvas-basics.md         # 画布基础
│   │   │   ├── add-elements.md          # 添加元素
│   │   │   ├── text-editing.md          # 文字编辑
│   │   │   ├── image-editing.md         # 图片编辑
│   │   │   ├── drawing-tools.md         # 绘图工具
│   │   │   ├── ai-features.md           # AI 功能
│   │   │   ├── import-export.md         # 导入导出
│   │   │   └── keyboard-shortcuts.md    # 快捷键
│   │   │
│   │   ├── dashboard/                   # Dashboard 使用
│   │   │   ├── manage-projects.md       # 管理项目
│   │   │   ├── folders.md               # 文件夹
│   │   │   └── workspace.md             # 工作空间
│   │   │
│   │   ├── marketplace/                 # Marketplace 使用
│   │   │   ├── browse-templates.md      # 浏览模板
│   │   │   ├── purchase.md              # 购买
│   │   │   └── sell-your-work.md        # 出售作品
│   │   │
│   │   ├── billing/                     # 账单与订阅
│   │   │   ├── plans-pricing.md         # 套餐与定价
│   │   │   ├── manage-subscription.md   # 管理订阅
│   │   │   ├── credits.md               # 积分说明
│   │   │   └── invoices.md              # 发票
│   │   │
│   │   └── account/                     # 账号管理
│   │       ├── profile-settings.md      # 个人设置
│   │       ├── security.md              # 安全设置
│   │       └── notifications.md         # 通知设置
│   │
│   │  ─────────────────────────────────────────────────────────
│   │  常见问题（→ FAQ 区 + AI 客服知识）
│   │  ─────────────────────────────────────────────────────────
│   │
│   ├── faq/                             # ❓ 常见问题
│   │   ├── README.md                    # FAQ 结构说明
│   │   ├── general.md                   # 常规问题
│   │   ├── account.md                   # 账号相关
│   │   ├── editor.md                    # 编辑器相关
│   │   ├── billing.md                   # 账单相关
│   │   ├── marketplace.md               # Marketplace 相关
│   │   └── troubleshooting.md           # 故障排除
│   │
│   │  ─────────────────────────────────────────────────────────
│   │  产品动态（→ News 页 + SEO + 社媒）
│   │  ─────────────────────────────────────────────────────────
│   │
│   ├── news/                            # 📰 产品动态
│   │   ├── README.md                    # News 内容策略
│   │   │
│   │   ├── releases/                    # 版本发布
│   │   │   └── _template.md             # 发布文章模板
│   │   │
│   │   ├── tutorials/                   # 教程文章（SEO）
│   │   │   └── _template.md             # 教程模板
│   │   │
│   │   ├── use-cases/                   # 使用案例（SEO）
│   │   │   └── _template.md             # 案例模板
│   │   │
│   │   └── announcements/               # 公告
│   │       └── _template.md             # 公告模板
│   │
│   │  ─────────────────────────────────────────────────────────
│   │  法律文档（→ 网站法律页面）
│   │  ─────────────────────────────────────────────────────────
│   │
│   ├── legal/                           # ⚖️ 法律文档
│   │   ├── terms-of-service.md          # 服务条款
│   │   ├── privacy-policy.md            # 隐私政策
│   │   ├── billing-policy.md            # 账单政策
│   │   └── content-guidelines.md        # 内容准则
│   │
│   │  ─────────────────────────────────────────────────────────
│   │  AI 客服知识库（→ Help AI 客服）
│   │  ─────────────────────────────────────────────────────────
│   │
│   └── ai-knowledge-base/               # 🤖 AI 客服知识库
│       ├── README.md                    # 知识库说明
│       │
│       ├── intents/                     # 意图分类
│       │   ├── account.md
│       │   ├── billing.md
│       │   ├── editor.md
│       │   └── general.md
│       │
│       ├── responses/                   # 标准回复
│       │   ├── account.md
│       │   ├── billing.md
│       │   ├── editor.md
│       │   └── escalation.md            # 转人工条件
│       │
│       └── context/                     # 上下文信息
│           ├── product-summary.md       # 产品信息摘要
│           ├── pricing-summary.md       # 定价信息摘要
│           └── policy-summary.md        # 政策摘要

│
│  ╔═══════════════════════════════════════════════════════════╗
│  ║  归档                                                     ║
│  ╚═══════════════════════════════════════════════════════════╝
│
└── archive/                             # 📦 归档
    └── ...
```

---

## 3. 内容转化流程

内部文档是"单一来源"，外部内容从内部文档转化而来：

```
┌─────────────────────────────────────────────────────────────────────┐
│                        内容转化流程                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  internal/02-product/features/    ──→    public/manual/             │
│    editor.md (功能规格)                    editor/*.md (用户教程)    │
│                                                                     │
│  internal/05-business/            ──→    public/faq/                │
│    tier-system.md (业务规则)               billing.md (定价FAQ)      │
│    credits-system.md                                                │
│                                                                     │
│  internal/09-compliance/          ──→    public/legal/              │
│    legal-requirements.md                   terms-of-service.md      │
│                                                                     │
│  internal/06-growth/              ──→    public/news/               │
│    content-strategy.md (内容计划)          tutorials/, use-cases/   │
│                                                                     │
│  public/manual/ + public/faq/     ──→    public/ai-knowledge-base/  │
│    (用户手册 + FAQ)                        (AI 客服知识库)           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 转化规则

| 来源 | 目标 | 转化方式 |
|------|------|----------|
| 功能规格 | Manual | 去除技术细节，添加操作步骤和截图 |
| 业务规则 | FAQ | 转为问答格式，使用用户语言 |
| 法务要求 | Legal | 转为正式法律条款格式 |
| 内容策略 | News | 按模板创作具体文章 |
| Manual + FAQ | AI 知识库 | 提取意图和标准回复 |

---

## 4. 角色视图索引

### 🧑‍💻 开发任务时（AI 编码辅助）

```
优先读取:
├── internal/01-project/README.md        # 项目背景
├── internal/04-engineering/             # 技术规范
│   ├── architecture/                    # 架构设计
│   ├── modules/{module}/                # 模块设计
│   └── development/                     # 开发规范
├── internal/05-business/                # 业务规则
└── internal/03-design/                  # 设计规范（前端）
```

### 📋 产品决策时

```
优先读取:
├── internal/01-project/vision.md        # 产品愿景
├── internal/02-product/                 # 产品规格
├── internal/05-business/                # 业务规则
└── internal/07-analytics/metrics.md     # 核心指标
```

### 📈 运营增长时

```
优先读取:
├── internal/06-growth/                  # 增长策略
├── internal/07-analytics/               # 数据分析
└── public/news/                         # 内容素材

需要产出:
├── public/manual/                       # 更新用户手册
├── public/faq/                          # 更新 FAQ
└── public/news/tutorials|use-cases/     # 发布内容
```

### 🤖 AI 客服维护时

```
优先读取:
├── public/manual/                       # 用户手册（知识来源）
├── public/faq/                          # FAQ（知识来源）
└── internal/05-business/                # 业务规则

需要产出:
├── public/ai-knowledge-base/intents/    # 意图分类
├── public/ai-knowledge-base/responses/  # 标准回复
└── public/ai-knowledge-base/context/    # 上下文信息
```

---

## 5. 前后端同步策略

### 5.1 文档分类

| 文档类型 | 存放位置 | 同步方式 |
|----------|----------|----------|
| 共享规则（业务、设计） | 两边都有 `internal/05-business/` | 内容相同，标注 `[fullstack]` |
| 后端专属（DDD、API） | 仅 `decodables/docs/v3/internal/04-engineering/` | 标注 `[backend]` |
| 前端专属（组件、状态） | 仅 `decodables-fe/docs/v3/internal/04-engineering/` | 标注 `[frontend]` |
| 外部内容（manual/faq/news） | 仅 `decodables-fe/docs/v3/public/` | 前端仓库管理，发布到网站 |

### 5.2 标注规范

在文档元数据中使用 `scope` 字段：

```yaml
---
scope: fullstack  # 或 backend | frontend
---
```

或在文档内容中使用内联标注：

```markdown
## 用户注册流程

### [fullstack] 业务规则
- 注册赠送 100 永久积分
- user_code 格式：26位数字

### [backend] 实现细节
- 使用 `UserService.register()` 方法
- 事务保证积分发放

### [frontend] UI 实现
- 使用 `useAuth()` hook
- 表单验证规则
```

---

## 6. 文档数量统计

| 区域 | 子目录 | 文档数 |
|------|--------|--------|
| **internal/** | | **~55** |
| | 01-project | 5 |
| | 02-product | 10 |
| | 03-design | 5 |
| | 04-engineering | 20 |
| | 05-business | 8 |
| | 06-growth | 10 |
| | 07-analytics | 5 |
| | 08-operations | 4 |
| | 09-compliance | 3 |
| | 10-governance | 4 |
| **public/** | | **~50** |
| | manual | 25 |
| | faq | 7 |
| | news (模板) | 5 |
| | legal | 4 |
| | ai-knowledge-base | 12 |
| **总计** | | **~105** |

---

## 7. 从 v2 迁移

### 7.1 v2 → v3 映射

| v2 目录 | v3 位置 | 说明 |
|---------|---------|------|
| `00-governance/` | `internal/10-governance/` | 文档治理 |
| `01-architecture/` | `internal/04-engineering/architecture/` | 架构设计 |
| `02-standards/` | `internal/04-engineering/development/` + `internal/03-design/` | 拆分 |
| `03-business/` | `internal/05-business/` | 业务规则 |
| `04-features/` | `internal/02-product/features/` + `internal/04-engineering/modules/` | 拆分 |
| `05-api/` | `internal/04-engineering/api/` | API 参考 |
| `06-operations/` | `internal/08-operations/` | 运维 |
| `07-plans/` | archive | 归档 |
| `08-reports/` | archive | 归档 |
| `09-reference/` | `internal/10-governance/` | 参考资料 |
| `10-product/` | `internal/02-product/pages/` | 页面设计 |
| `11-go-to-market/` | `internal/06-growth/` | 增长策略 |
| `12-support/` | `internal/06-growth/support/` + `public/faq/` | 拆分 |
| `13-legal-compliance/` | `internal/09-compliance/` + `public/legal/` | 拆分 |

### 7.2 迁移优先级

| 优先级 | 目录 | 原因 |
|--------|------|------|
| P0 | `internal/01-project/` | AI 上下文入口 |
| P0 | `internal/05-business/` | 核心业务规则 |
| P1 | `internal/04-engineering/` | 开发常用 |
| P1 | `public/manual/` | 支撑 Manual 页 |
| P2 | `public/faq/` | 支撑 FAQ + AI 客服 |
| P2 | `internal/06-growth/` | 增长运营 |
| P3 | 其他 | 按需迁移 |

---

## 8. 变更历史

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| 4.0.0 | 2026-02-05 | 初始版本，整合 1人+AI 结构与内外分离设计 |
