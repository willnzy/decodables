# ADR-0001 使用 DDD 架构

> **状态**: ✅ Active
> **日期**: 2026-01-09
> **决策者**: Backend Team

---

## 背景

随着项目功能增加，原有的扁平化架构导致:

1. 代码耦合度高，难以维护
2. 业务逻辑分散在 API 层和数据层
3. 测试困难，依赖关系复杂
4. 新功能开发需要修改多处代码

需要一个更好的架构来支持项目的长期发展。

---

## 决策

采用轻量级 DDD (Domain-Driven Design) 分层架构:

```
┌─────────────────────────────────────────────────┐
│                    API Layer                     │
│              (FastAPI Routers)                   │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│               Application Layer                  │
│           (Use Cases / Services)                │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│                 Domain Layer                     │
│      (Entities / Value Objects / Rules)         │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│             Infrastructure Layer                 │
│        (Repositories / External Services)       │
└─────────────────────────────────────────────────┘
```

---

## 考虑的选项

### 选项 A: 保持扁平架构

- **优点**: 无需重构，短期成本低
- **缺点**: 长期维护困难，技术债务累积

### 选项 B: 完整 DDD

- **优点**: 最佳实践，领域隔离完美
- **缺点**: 对当前项目规模过重，学习曲线陡峭

### 选项 C: 轻量级 DDD (选中)

- **优点**: 清晰分层，适度抽象，易于理解
- **缺点**: 某些 DDD 概念简化

---

## 理由

1. **项目规模适中**: 不需要完整 DDD 的复杂性
2. **团队熟悉度**: Python/FastAPI 生态更适合轻量级方案
3. **渐进式迁移**: 可以逐模块重构，不需要一次性完成
4. **测试友好**: 分层后单元测试更容易编写

---

## 影响

### 正面影响

- 代码组织更清晰
- 业务逻辑集中在 Domain 层
- 测试覆盖率提升
- 新人更容易理解项目结构

### 负面影响

- 短期重构成本
- 代码量略有增加
- 需要团队学习新的架构规范

### 需要的改动

1. 创建 `domains/` 目录，按业务领域划分
2. 创建 `application/` 目录，放置用例
3. 重构 `infrastructure/` 目录，提取 Repository
4. API 层只负责 HTTP 处理，调用 Application 层

---

## 实施规则

### 依赖方向

```
api → application → domains ← infrastructure
             ↓
         core + shared
```

### 层间调用规则

| 调用方 | 可调用 |
|--------|--------|
| API | Application, Shared |
| Application | Domain, Infrastructure (via Interface) |
| Domain | Core, Shared |
| Infrastructure | Domain (implements Interface), Core |

### 禁止

- API 直接调用 Repository
- Domain 依赖 Infrastructure 具体实现
- 循环依赖

---

## 相关文档

- [后端架构](../backend.md)
- [模块重构指南](../../guides/MODULE-REFACTOR-SOP.md)
