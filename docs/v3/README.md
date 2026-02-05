# Make Decodables 文档中心 v3

> **版本**: 3.0.0
> **创建日期**: 2026-02-05
> **架构设计**: [documentation-architecture-v4.md](internal/10-governance/documentation-architecture-v4.md)

---

## 快速导航

### 🔧 Internal（内部开发文档）

| 目录 | 说明 | 适用场景 |
|------|------|----------|
| [01-project](internal/01-project/) | 项目基础 | AI 上下文入口 |
| [02-product](internal/02-product/) | 产品规格 | 产品决策 |
| [03-design](internal/03-design/) | 设计系统 | UI 开发 |
| [04-engineering](internal/04-engineering/) | 技术文档 | 开发实现 |
| [05-business](internal/05-business/) | 业务规则 | 业务逻辑 |
| [06-growth](internal/06-growth/) | 运营增长 | 增长策略 |
| [07-analytics](internal/07-analytics/) | 数据分析 | 数据洞察 |
| [08-operations](internal/08-operations/) | 运维 | 部署监控 |
| [09-compliance](internal/09-compliance/) | 合规 | 法务要求 |
| [10-governance](internal/10-governance/) | 文档治理 | 模板规范 |

### 📢 Public（外部内容）

| 目录 | 说明 | 输出到 |
|------|------|--------|
| [manual](public/manual/) | 用户手册 | 网站 /manual |
| [faq](public/faq/) | 常见问题 | 网站 FAQ + AI 客服 |
| [news](public/news/) | 产品动态 | 网站 /news + 社媒 |
| [legal](public/legal/) | 法律文档 | 网站法律页 |
| [ai-knowledge-base](public/ai-knowledge-base/) | AI 客服知识库 | Help AI 客服 |

---

## 角色视图

### 🧑‍💻 开发任务时

```
优先读取:
├── internal/01-project/README.md        # 项目背景
├── internal/04-engineering/             # 技术规范
└── internal/05-business/                # 业务规则
```

### 📋 产品决策时

```
优先读取:
├── internal/01-project/vision.md        # 产品愿景
├── internal/02-product/                 # 产品规格
└── internal/05-business/                # 业务规则
```

### 📈 运营增长时

```
优先读取:
├── internal/06-growth/                  # 增长策略
└── public/news/                         # 内容素材

需要产出:
├── public/manual/                       # 用户手册
├── public/faq/                          # FAQ
└── public/news/                         # 内容文章
```

### 🤖 AI 客服维护时

```
优先读取:
├── public/manual/                       # 用户手册
├── public/faq/                          # FAQ
└── internal/05-business/                # 业务规则

需要产出:
└── public/ai-knowledge-base/            # AI 知识库
```

---

## 内容转化流程

```
internal/02-product/features/   →   public/manual/
internal/05-business/           →   public/faq/
internal/09-compliance/         →   public/legal/
internal/06-growth/             →   public/news/
public/manual/ + public/faq/    →   public/ai-knowledge-base/
```

---

## 前后端同步

| 文档类型 | 同步要求 |
|----------|----------|
| 业务规则 (`05-business/`) | ✅ 两边保持一致 |
| 技术文档 (`04-engineering/`) | ⚠️ 按 scope 区分 |
| 外部内容 (`public/`) | 📍 仅前端仓库 |

---

## 版本说明

- **v1**: 原始文档（已归档）
- **v2**: 重构中间版本
- **v3**: 当前版本 - internal/public 分离架构
