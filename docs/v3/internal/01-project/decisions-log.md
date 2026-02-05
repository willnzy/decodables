# 重要决策记录

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟢 已验证
> **同步范围**: [fullstack]

---

## 概述

记录项目开发过程中的重要决策，便于追溯和理解设计意图。

> 详细的架构决策记录 (ADR) 请参考：`04-engineering/architecture/decisions/`

---

## 决策索引

### 架构决策

| ID | 决策 | 日期 | 文档 |
|----|------|------|------|
| ADR-0001 | 采用 DDD 架构 | 2026-01 | [0001-use-ddd-architecture.md](../04-engineering/architecture/decisions/0001-use-ddd-architecture.md) |
| ADR-0002 | 数据库驱动配置 | 2026-01 | [0002-database-driven-config.md](../04-engineering/architecture/decisions/0002-database-driven-config.md) |
| ADR-0003 | 双积分模型 | 2026-01 | [0003-dual-credit-model.md](../04-engineering/architecture/decisions/0003-dual-credit-model.md) |
| ADR-0004 | JWT 双密钥轮换 | 2026-01 | [0004-jwt-dual-key-rotation.md](../04-engineering/architecture/decisions/0004-jwt-dual-key-rotation.md) |

### 业务决策

| 决策 | 日期 | 说明 |
|------|------|------|
| Tier 体系采用 t1/t2/t3/t4 | 2026-01 | 系统代码永不变，显示名称可配置 |
| 双用户标识符 (user_id + user_code) | 2026-01 | UUID 用于系统，26位数字用于用户 |
| 积分优先级：月度 → 永久 | 2026-01 | 先扣月度积分，后扣永久积分 |

### 技术选型

| 决策 | 日期 | 说明 |
|------|------|------|
| 后端框架：FastAPI | 2026-01 | 高性能、异步支持、类型提示 |
| 前端框架：Next.js 16 | 2026-01 | App Router、RSC、良好 DX |
| 数据库：Supabase (PostgreSQL) | 2026-01 | 托管服务、实时订阅、RLS |
| 画布：Fabric.js | 2026-01 | 成熟稳定、功能丰富 |

---

## 决策模板

新决策记录格式：

```markdown
### [决策标题]

**日期**: YYYY-MM-DD
**状态**: 提议/已采纳/已废弃

**背景**:
描述导致这个决策的背景和问题

**决策**:
描述做出的决策

**后果**:
- 正面影响
- 负面影响
- 需要注意的事项
```

---

## 相关文档

- [架构决策记录 (ADR)](../04-engineering/architecture/decisions/)
- [技术栈](./tech-stack.md)
- [业务规则](../05-business/)
