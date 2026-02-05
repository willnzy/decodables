# 文档治理

> **说明**: 定义文档规范和管理策略

---

## 目录结构

```
10-governance/
├── README.md                          # 本文件
├── documentation-governance.md        # 🔴 核心：文档治理规范（归属决策+内容管理+操作规范）
├── documentation-architecture-v4.md   # 文档架构设计
└── templates/                         # 文档模板
    ├── faq-template.md               # FAQ 模板
    └── news-template.md              # News 模板
```

---

## 核心文档

| 文档 | 说明 | 状态 |
|------|------|------|
| `documentation-governance.md` | **核心治理规范**：归属决策原则、内容管理规则、操作规范 | 🟢 |
| `documentation-architecture-v4.md` | 完整的文档架构设计，包含目录结构、角色视图、迁移计划 | 🟢 |

---

## documentation-governance.md 内容概览

整合了原 `classification-principles.md` 和 `content-management-rules.md` 的内容，包含三大部分：

### Part 1: 归属决策

- **三步决策树**：判断内容性质 → 判断主要读者 → 处理跨领域内容
- **各目录收录原则**：明确每个目录应该放什么、不应该放什么
- **同步范围判断**：`[fullstack]` / `[backend]` / `[frontend]` 的判断标准
- **粒度判断**：何时拆分、何时合并
- **与代码路径的对应关系**
- **边界案例处理**

### Part 2: 内容管理

- **内容来源优先级**：代码 > v1/v2 文档 > 人工确认
- **内容分类及处理规则**：A-H 八类内容的处理方式
- **状态标注**：🟢 已验证 / 🟡 待验证 / 🔴 已过时
- **更新触发规则**
- **废弃与归档策略**
- **文档优先级**：核心文档 vs 扩展文档

### Part 3: 操作规范

- **命名规范**：文件和目录的命名规则
- **README 角色**：每个目录 README 应包含什么
- **前后端同步流程**
- **tmp/ 临时目录规范**
- **决策流程图**

---

## templates/ 文档模板

| 模板 | 用途 |
|------|------|
| `faq-template.md` | FAQ 文档模板，包含 AI 标签规范 |
| `news-template.md` | News 文章模板，包含 SEO 和社媒文案规范 |

**待添加模板**：
- `feature-spec-template.md` - 功能规格模板
- `module-design-template.md` - 模块设计模板
- `adr-template.md` - 架构决策记录模板

---

## 与其他目录的关系

| 目录 | 关系 |
|------|------|
| 所有目录 | 治理规范适用于所有文档 |

---

## 变更记录

| 日期 | 变更 |
|------|------|
| 2026-02-05 | 整合 classification-principles.md + content-management-rules.md → documentation-governance.md |
