# 文档治理

> **说明**: 定义文档规范和管理策略

---

## 目录结构

```
10-governance/
├── README.md                          # 本文件
├── documentation-architecture-v4.md   # 文档架构设计
├── templates/                         # 文档模板
│   ├── faq-template.md               # FAQ 模板
│   └── news-template.md              # News 模板
├── conventions.md                     # 命名规范
└── sync-policy.md                     # 前后端同步策略
```

---

## 核心文档

| 文档 | 说明 |
|------|------|
| `documentation-architecture-v4.md` | 完整的文档架构设计，包含目录结构、角色视图、迁移计划 |
| `conventions.md` | 文档命名、格式、元数据规范 |
| `sync-policy.md` | 前后端文档同步策略 |

---

## templates/ 文档模板

| 模板 | 用途 |
|------|------|
| `faq-template.md` | FAQ 文档模板，包含 AI 标签规范 |
| `news-template.md` | News 文章模板，包含 SEO 和社媒文案规范 |

**其他待添加模板**：
- `feature-spec-template.md` - 功能规格模板
- `module-design-template.md` - 模块设计模板
- `adr-template.md` - 架构决策记录模板

---

## conventions.md 内容大纲

```markdown
## 文件命名
- 全小写，连字符分隔：`user-system.md`
- README 大写：`README.md`
- 模板文件前缀下划线：`_template.md`

## 文档元数据
---
title: 文档标题
status: draft | review | published
scope: fullstack | backend | frontend
version: 1.0.0
created: YYYY-MM-DD
updated: YYYY-MM-DD
owner: 负责人
---

## 内容格式
- 使用 Markdown
- 一级标题只有一个
- 代码块标注语言
- 表格用于结构化数据
```

---

## sync-policy.md 内容大纲

```markdown
## 同步范围

| 内容类型 | 后端 | 前端 | 同步 |
|----------|------|------|------|
| 业务规则 | ✅ | ✅ | 必须 |
| 后端架构 | ✅ | 📋 | 单向 |
| 前端架构 | 📋 | ✅ | 单向 |
| 外部内容 | ❌ | ✅ | 无 |

## 同步机制
1. 修改后端共享文档
2. 复制到前端对应位置
3. 更新 shared-docs-registry

## 冲突处理
- 后端为主
- 记录差异原因
```

---

## 与其他目录的关系

| 目录 | 关系 |
|------|------|
| 所有目录 | 治理规范适用于所有文档 |
