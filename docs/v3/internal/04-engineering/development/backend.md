# 后端开发规范

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [backend]
> **对应代码**: `decodables/`

---

## 概述

后端开发规范，基于 FastAPI + Python 3.12 + DDD 架构。

---

## 技术栈

| 组件 | 版本 | 用途 |
|------|------|------|
| FastAPI | 0.128.0 | Web 框架 |
| Python | 3.12.7 | 运行时 |
| Pydantic | 2.12.5 | 数据验证 |
| Supabase | - | 数据库 (PostgreSQL) |

---

## 架构层次

```
api/routers/     → API 层（路由）
application/     → 应用层（用例编排）
domains/         → 领域层（业务核心）
infrastructure/  → 基础设施层
shared/          → 共享层（AI/支付/存储）
core/            → 框架层
```

---

## 开发规范

### 依赖方向

```
api → application → domains ← infrastructure
          ↓
     core + shared
```

### 编码规范

- 使用 async/await 处理异步操作
- 所有时间使用 UTC（`datetime.now(timezone.utc)`）
- 类型注解完整
- 单文件 300 行指标

---

## 详细规范

- [backend/ 详细规范](./backend/)
- [API 设计规范](./api-guide.md)
- [数据库规范](./database.md)
- [测试规范](./testing-guide.md)
