# ADR-0001: 采用 DDD 三层架构

## Status
Accepted

## Context

原有后端架构存在以下问题：
1. 业务逻辑分散在 routers 和 services 中，职责不清晰
2. 数据访问直接使用 Supabase 客户端，缺乏抽象
3. 业务规则（如积分扣除优先级）隐藏在数据库 RPC 函数中
4. 测试困难，难以进行单元测试
5. 代码复用性低，难以扩展到其他项目

## Decision

采用 DDD (Domain-Driven Design) 三层架构重构后端代码：

```
API 层 → Application 层 (CQRS) → Domain 层 ← Infrastructure 层
  ↓           ↓                      ↓              ↓
路由       Commands/Queries       Aggregates    Repositories
         (用例编排)              (业务规则)    (数据访问)
```

### 核心概念

1. **Core 层** - 框架层（100% 复用）
   - 异常处理、缓存、数据库抽象、中间件

2. **Domain 层** - 业务核心
   - Aggregates (聚合根): UserCredits, Project, Listing
   - Value Objects: Credits, CreditBucket, TransactionType
   - Domain Services: BillingService
   - Repository Interfaces: ICreditRepository

3. **Infrastructure 层** - 基础设施
   - Repository 实现: SupabaseCreditRepository
   - 外部服务集成

4. **Application 层** - 用例编排
   - Commands (写操作): DeductCreditsCommand
   - Queries (读操作): GetUserCreditsQuery

5. **API 层** - HTTP 接口
   - 参数验证、错误处理、响应格式化

## Consequences

### Positive
- ✅ 业务逻辑集中在 Domain 层，易于理解和维护
- ✅ Repository 接口使测试变得简单（可 mock）
- ✅ Core 层可 100% 复用到其他项目
- ✅ 依赖方向清晰：API → Application → Domain ← Infrastructure
- ✅ 符合 SOLID 原则，易于扩展

### Negative
- ⚠️ 初期开发成本增加（需要定义接口和实现）
- ⚠️ 学习曲线：团队需要理解 DDD 概念
- ⚠️ 代码量增加（更多抽象层）

## Alternatives Considered

### 方案 A: 保持现有架构 + 轻微重构
- **优点**: 改动小，风险低
- **缺点**: 无法解决根本问题，技术债持续累积
- **结论**: 不可接受，无法支撑长期发展

### 方案 B: 微服务架构
- **优点**: 服务独立部署，技术栈灵活
- **缺点**: 运维复杂度高，过度设计（当前规模不需要）
- **结论**: 暂不采用，未来可考虑

### 方案 C: Clean Architecture + DDD (选中)
- **优点**: 代码组织清晰，易测试，可复用
- **缺点**: 初期投入较大
- **结论**: 最适合当前阶段

## Implementation

### 已完成的领域
- ✅ billing (计费域) - UserCredits aggregate
- ✅ identity (身份域) - UserProfile aggregate
- ✅ creation (创作域) - Project aggregate
- ✅ marketplace (市场域) - Listing aggregate
- ✅ platform (平台域) - FeatureFlag, Experiment aggregates

### 文件结构
```
decodables/
├── core/                   # 框架层
├── domains/                # 领域层
│   ├── billing/
│   ├── identity/
│   ├── creation/
│   ├── marketplace/
│   └── platform/
├── application/            # 应用层
│   ├── commands/
│   └── queries/
├── infrastructure/         # 基础设施层
│   └── repositories/
└── api/                    # API 层
```

### 相关提交
- Phase 1 Core Framework: commits a1b2c3d - d4e5f6g
- Phase 2 Domain Layer: commits h7i8j9k - l0m1n2o
- Phase 3 Application Layer: commits p3q4r5s - t6u7v8w

### 参考文档
- `.claude/skills/backend.md` - 后端开发规范
- `docs/shared/architecture-proposal.md` - 重构方案

## Notes

此架构决策是项目的基石，所有后续开发都应遵循此架构原则。
