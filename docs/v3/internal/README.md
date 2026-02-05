# Internal - 内部开发文档

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟢 结构完成
> **同步范围**: [fullstack]

---

## 目录说明

内部开发文档，面向开发者、产品、设计等内部角色。

---

## 目录索引

| 目录 | 说明 | 主要内容 |
|------|------|----------|
| [01-project](01-project/) | 项目总览 | AI 上下文入口、技术栈、愿景 |
| [02-product](02-product/) | 产品规格 | 功能规格、页面设计、路线图 |
| [03-design](03-design/) | 设计系统 | 设计令牌、组件规范、交互模式 |
| [04-engineering](04-engineering/) | 技术文档 | 架构、开发规范、模块、API、数据 |
| [05-business](05-business/) | 业务规则 | 用户体系、Tier、积分、权限 |
| [06-growth](06-growth/) | 运营增长 | 获客、留存、变现、支持 |
| [07-analytics](07-analytics/) | 数据分析 | 指标定义、埋点规范 |
| [08-operations](08-operations/) | 运维 | 部署、监控、故障处理 |
| [09-compliance](09-compliance/) | 合规 | 隐私、GDPR、条款 |
| [10-governance](10-governance/) | 文档治理 | 模板、规范、架构设计 |
| [11-reference](11-reference/) | 参考资料 | 术语表、功能矩阵、速查 |

---

## 按角色导航

### 🧑‍💻 开发者

```
优先阅读:
├── 01-project/README.md         # 项目背景
├── 04-engineering/architecture/ # 架构设计
├── 04-engineering/development/  # 开发规范
├── 04-engineering/modules/      # 模块文档
└── 05-business/                 # 业务规则
```

### 📋 产品经理

```
优先阅读:
├── 01-project/vision.md         # 产品愿景
├── 02-product/features/         # 功能规格
├── 02-product/roadmap/          # 路线图
└── 05-business/                 # 业务规则
```

### 🎨 设计师

```
优先阅读:
├── 03-design/                   # 设计系统
├── 02-product/pages/            # 页面设计
└── 02-product/features/         # 功能规格
```

---

## 文档状态说明

| 状态 | 含义 |
|------|------|
| 🟢 已验证 | 内容与代码一致 |
| 🟡 待验证 | 需要与代码对照 |
| 🔴 已过时 | 内容需要更新 |
| 📋 待创建 | 计划文档，尚未创建 |

---

## 与 public/ 的关系

```
internal/02-product/features/   →   public/manual/
internal/05-business/           →   public/faq/
internal/09-compliance/         →   public/legal/
internal/06-growth/             →   public/news/
```
