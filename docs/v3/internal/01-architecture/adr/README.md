# Architecture Decision Records (ADR)

> 架构决策记录

---

## 什么是 ADR

ADR (Architecture Decision Record) 是记录重要架构决策的文档，包括:

- 决策背景和问题
- 考虑的选项
- 最终决策及理由
- 决策的影响

---

## ADR 列表

| 编号 | 标题 | 状态 | 日期 |
|------|------|------|------|
| [ADR-0001](./0001-use-ddd-architecture.md) | 使用 DDD 架构 | ✅ Active | 2026-01-09 |
| [ADR-0002](./0002-database-driven-config.md) | 数据库驱动配置 | ✅ Active | 2026-01-09 |
| [ADR-0003](./0003-dual-credit-model.md) | 双桶积分模型 | ✅ Active | 2026-01-15 |
| [ADR-0004](./0004-jwt-dual-key-rotation.md) | JWT 双密钥轮换 | ✅ Active | 2026-01-20 |

---

## ADR 状态

| 状态 | 说明 |
|------|------|
| ✅ Active | 当前生效 |
| 🔄 Superseded | 已被新决策取代 |
| ❌ Deprecated | 已废弃 |
| 📝 Proposed | 提议中 |

---

## ADR 模板

```markdown
# ADR-XXXX 标题

**状态**: proposed / active / superseded / deprecated
**日期**: YYYY-MM-DD
**决策者**: Team/Person

## 背景

描述问题背景和决策需求。

## 决策

我们决定采用 XXX 方案。

## 考虑的选项

1. **选项 A**: 描述
   - 优点: ...
   - 缺点: ...

2. **选项 B**: 描述
   - 优点: ...
   - 缺点: ...

## 理由

选择该方案的原因。

## 影响

- 正面影响: ...
- 负面影响: ...
- 需要的改动: ...

## 相关文档

- [相关链接]
```
