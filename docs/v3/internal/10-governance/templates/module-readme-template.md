# 模块 README 模板

> **版本**: 1.0.0
> **创建日期**: 2026-02-05

---

## 使用说明

此模板用于创建 `04-engineering/modules/{module}/README.md` 文件。

---

## 模板

```markdown
# {模块名称}模块

> **同步范围**: [fullstack] / [backend] / [frontend]
> **状态**: 🟢 已验证 / 🟡 待验证 / 🔴 已过时 / 📋 待创建

---

## 模块概述

简要描述模块的用途和职责（2-3 句话）。

---

## 代码结构

### 后端 (如适用)

```
decodables/
├── domains/{domain}/
│   ├── entity.py        # 领域实体
│   ├── repository.py    # 仓储接口
│   ├── service.py       # 领域服务
│   └── exceptions.py    # 领域异常
├── application/{domain}/
│   └── use_cases.py     # 用例
├── infrastructure/{domain}/
│   └── repository_impl.py  # 仓储实现
└── api/routers/{domain}.py  # API 路由
```

### 前端 (如适用)

```
decodables-fe/
├── @business/{module}/
│   ├── stores/          # 状态管理
│   ├── hooks/           # 自定义 hooks
│   └── services/        # API 调用
└── app/{routes}/        # 页面组件
```

---

## 核心概念

### 实体 / 数据模型

| 实体 | 说明 | 主要字段 |
|------|------|----------|
| Entity1 | ... | field1, field2 |
| Entity2 | ... | field1, field2 |

### 主要流程

1. **流程 1**: 简要描述
2. **流程 2**: 简要描述

---

## API 概览

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/xxx` | GET | ... |
| `/api/v1/xxx` | POST | ... |

详见 [API 文档](./api.md)（如有）

---

## 状态管理 (前端)

| Store | 用途 | 主要状态 |
|-------|------|----------|
| useXxxStore | ... | state1, state2 |

---

## 依赖关系

### 依赖的模块

- **模块 A**: 原因
- **模块 B**: 原因

### 被依赖

- **模块 C**: 原因

---

## 相关文档

- [架构设计](./architecture.md)（如有）
- [API 文档](./api.md)（如有）
- [数据模型](./data-model.md)（如有）
```

---

## 状态说明

| 状态 | 含义 |
|------|------|
| 🟢 已验证 | 文档内容与代码一致 |
| 🟡 待验证 | 需要与代码对照确认 |
| 🔴 已过时 | 代码已变更，文档需更新 |
| 📋 待创建 | 计划创建，尚未开始 |

---

## 同步范围说明

| 标签 | 含义 |
|------|------|
| [fullstack] | 前后端都需要了解 |
| [backend] | 仅后端相关 |
| [frontend] | 仅前端相关 |
