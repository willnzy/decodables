# 后端架构完整指南

**状态**: active  
**版本**: 3.27.0  
**版本日期**: 2026-01-16  
**最后复核**: 2026-02-04  
**负责人**: Backend Team  
**适用范围**: backend  
**source_repo**: backend  
**sync_required**: no

---

## 1. 架构总览

### 1.1 设计理念

三层架构 + 轻量级 DDD 融合：

- 框架层与业务层清晰分离
- 业务逻辑按领域组织
- 规则内聚在聚合内
- 数据访问通过仓储抽象

### 1.2 分层结构

```
api/  -> application/ -> domains/ <- infrastructure/
            ↓
         core/ + shared/
```

**依赖方向规则**:

```
api → application → domains ← infrastructure
                       ↓
                core + shared
```

**关键约束**:
- domains 可以依赖 core/shared
- infrastructure 可以依赖 domains (实现 repository 接口)
- domains 不能依赖 infrastructure/application
- 同级 domain 之间不能直接依赖

---

## 2. 目录结构标准 (v3.1)

```
decodables/
├── api/                 # HTTP 入口
├── application/         # 用例编排 (commands/queries)
├── domains/             # 业务核心 (aggregates/entities/value_objects)
├── infrastructure/      # 技术实现 (repo/clients/queue)
├── core/                # 框架层 (auth/cache/db/exceptions)
└── shared/              # 共享服务 (ai/payment/storage)
```

---

## 3. 分层职责

- api: 路由、参数验证、DTO、调用应用层
- application: 用例编排、跨域协作、事务边界
- domains: 业务规则、聚合、领域服务、仓储接口
- infrastructure: 仓储实现、第三方集成、事件总线
- core: 认证/缓存/数据库/异常/中间件/工具
- shared: 跨域共享业务服务

---

## 4. 代码放置决策

**判断规则**:

1. 是否业务无关工具？→ core  
2. 是否跨域共享服务？→ shared  
3. 是否业务规则/实体？→ domains  
4. 是否技术实现？→ infrastructure  
5. 是否用例编排？→ application  
6. 是否 HTTP 接口？→ api

---

## 5. 命名与规范

- 分页统一使用 `offset + limit`
- API 层只调用 Service，不直连 Repository
- Repository 实现必须符合接口定义
- 返回类型优先 `List[Entity]`

---

## 6. 文件大小建议

单文件超过 300 行时评估拆分，以下条件可接受:

- 逻辑高度内聚
- 函数职责单一
- 测试覆盖充分

---

## 7. 常见场景示例

- 新增业务能力：先定义 domain entity → service → repository interface
- 接入第三方：放在 infrastructure/external_services
- 新增 API：api → application → domain service → repository

---

## 8. 迁移指南摘要

- 旧路径 `routers/` 迁移到 `api/user` / `api/admin`
- 旧 service 迁移到 `application` + `domains`
- Repository 统一放到 `infrastructure/repositories`

---

## 9. 参考文档

- `docs/v2/02-standards/backend-naming-standards.md`
- `docs/v2/02-standards/testing-guide.md`
