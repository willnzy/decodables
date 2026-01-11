# Backend Documentation

> Make Decodables 后端文档导航

**最后更新**: 2026-01-07

---

## 📚 文档分类

### 1. 核心架构文档 (必读)

| 文档 | 说明 | 大小 |
|------|------|------|
| [BACKEND_ARCHITECTURE_GUIDE.md](./BACKEND_ARCHITECTURE_GUIDE.md) | **DDD 架构设计指南** - 三层架构、依赖注入、分层职责 | 42KB |
| [后台业务逻辑说明.md](./后台业务逻辑说明.md) | **业务规则和数据库设计** - 积分系统、用户等级、支付流程 | 55KB |
| [DDD-Migration-Guide.md](./DDD-Migration-Guide.md) | **DDD 迁移指南** - 如何将旧代码迁移到新架构 | 17KB |

### 2. 开发规范 (团队协作)

| 文档 | 说明 | 大小 |
|------|------|------|
| [BACKEND-DEVELOPMENT-SOP.md](./BACKEND-DEVELOPMENT-SOP.md) | **开发标准操作流程** - Phase 执行、Git 规范、Code Review | 22KB |
| [API-HTTP-METHODS-GUIDELINES.md](./API-HTTP-METHODS-GUIDELINES.md) | **API 方法规范** - RESTful 设计、HTTP 动词使用 | 8KB |

### 3. 测试和质量

| 文档 | 说明 | 大小 |
|------|------|------|
| [TEST_COVERAGE_PLAN.md](./TEST_COVERAGE_PLAN.md) | **测试覆盖计划** - 单元测试、集成测试、测试策略 | 10KB |
| [CI-TESTING-LIMITATIONS.md](./CI-TESTING-LIMITATIONS.md) | **CI 测试限制说明** - GitHub Actions 限制和解决方案 | 13KB |

---

## 🤝 前后端共享文档

这些文档在前端和后端仓库都有一份副本，修改时需要同步。

| 文档 | 说明 |
|------|------|
| [shared/architecture-proposal.md](./shared/architecture-proposal.md) | 系统重构方案 v2 |
| [shared/[wip]refactoring-plan.md](./shared/[wip]refactoring-plan.md) | 重构实施计划 |
| [shared/feature-flag-design.md](./shared/feature-flag-design.md) | Feature Flag 系统设计 |
| [shared/asset-category-design.md](./shared/asset-category-design.md) | 素材分类系统设计 (10 类) |
| [shared/[draft]onboarding-design.md](./shared/[draft]onboarding-design.md) | 新手引导系统设计 |
| [shared/[draft]theme-system-design.md](./shared/[draft]theme-system-design.md) | 主题系统设计 |

---

## 🏛️ Architecture Decision Records (ADR)

记录重要的架构决策和理由。

| ADR | 标题 | 状态 |
|-----|------|------|
| [adr/0001-use-ddd-architecture.md](./adr/0001-use-ddd-architecture.md) | 采用 DDD 架构 | ✅ Accepted |
| [adr/0002-database-driven-config.md](./adr/0002-database-driven-config.md) | 数据库驱动的配置系统 | ✅ Accepted |

---

## 🗂️ 临时文档 (tmp/)

临时性文档，包括已完成的 Phase 报告、迁移计划、临时分析等。

**详见**: [tmp/README.md](./tmp/README.md)

**包含**:
- Phase 完成报告 (Phase 1-2)
- 已完成的迁移计划 (Phase 8, services, credits)
- 临时分析和审计
- 临时测试指南
- 未来 Phase 计划 (Phase 9-11)

---

## 📖 快速导航

### 我是新成员，应该先读什么？

1. **必读三件套** (按顺序):
   - [后台业务逻辑说明.md](./后台业务逻辑说明.md) - 了解业务规则
   - [BACKEND_ARCHITECTURE_GUIDE.md](./BACKEND_ARCHITECTURE_GUIDE.md) - 了解架构设计
   - [BACKEND-DEVELOPMENT-SOP.md](./BACKEND-DEVELOPMENT-SOP.md) - 了解开发流程

2. **开始开发前**:
   - [DDD-Migration-Guide.md](./DDD-Migration-Guide.md) - 学习如何写新代码
   - [API-HTTP-METHODS-GUIDELINES.md](./API-HTTP-METHODS-GUIDELINES.md) - API 设计规范

3. **写测试前**:
   - [TEST_COVERAGE_PLAN.md](./TEST_COVERAGE_PLAN.md) - 测试策略和覆盖要求

### 我要开发新功能，应该参考什么？

1. **确定功能归属**:
   - 查看 [BACKEND_ARCHITECTURE_GUIDE.md](./BACKEND_ARCHITECTURE_GUIDE.md) 确定属于哪个 Domain

2. **参考设计文档**:
   - 如果涉及前端，查看 [shared/](./shared/) 中的设计文档
   - 如果是新的架构决策，考虑创建新的 ADR

3. **遵循开发流程**:
   - 按照 [BACKEND-DEVELOPMENT-SOP.md](./BACKEND-DEVELOPMENT-SOP.md) 的 Phase 流程执行

### 我要修复 Bug，应该怎么做？

1. **定位问题**:
   - 查看 [后台业务逻辑说明.md](./后台业务逻辑说明.md) 确认业务规则
   - 查看 [BACKEND_ARCHITECTURE_GUIDE.md](./BACKEND_ARCHITECTURE_GUIDE.md) 确认代码位置

2. **修复和测试**:
   - 按照 [TEST_COVERAGE_PLAN.md](./TEST_COVERAGE_PLAN.md) 编写测试
   - 确保测试覆盖 Bug 场景

3. **提交代码**:
   - 遵循 [BACKEND-DEVELOPMENT-SOP.md](./BACKEND-DEVELOPMENT-SOP.md) 的 Git 规范

---

## 🔄 文档维护规则

### 何时更新文档？

1. **业务规则变更** → 更新 `后台业务逻辑说明.md`
2. **架构调整** → 更新 `BACKEND_ARCHITECTURE_GUIDE.md` 并考虑创建 ADR
3. **开发流程优化** → 更新 `BACKEND-DEVELOPMENT-SOP.md`
4. **API 规范变更** → 更新 `API-HTTP-METHODS-GUIDELINES.md`
5. **测试策略变更** → 更新 `TEST_COVERAGE_PLAN.md`

### 如何管理临时文档？

1. **创建临时文档**: 放在 `tmp/` 目录，使用自增序号 (如 `018-xxx.md`)
2. **检查旧文档**: 每次创建新文档时，检查 `tmp/` 中是否有已完成的可以删除
3. **合并到主文档**: 如果临时文档内容有价值，合并到相应的核心文档
4. **定期清理**: Phase 完成后，删除相关的临时文档

**详见**: [tmp/README.md](./tmp/README.md)

---

## 📝 文档编写规范

### 文档命名

- **核心文档**: `UPPERCASE-WITH-DASHES.md` (如 `BACKEND_ARCHITECTURE_GUIDE.md`)
- **中文文档**: 直接使用中文 (如 `后台业务逻辑说明.md`)
- **临时文档**: `NNN-lowercase-with-dashes.md` (如 `001-docs-organization-plan.md`)
- **ADR**: `NNNN-kebab-case.md` (如 `0001-use-ddd-architecture.md`)

### 文档结构

```markdown
# 标题

> 简短描述

**创建日期**: YYYY-MM-DD
**状态**: 进行中/已完成/已废弃
**作者**: 作者名

---

## 目录
...

## 正文
...
```

### 文档大小建议

- **核心架构文档**: 20-50KB (详细完整)
- **开发规范**: 10-30KB (清晰易读)
- **临时文档**: <20KB (简洁明了)
- **ADR**: 2-5KB (重点突出)

---

## 🔗 相关资源

- **前端文档**: `decodables-fe/docs/`
- **共享设计**: `docs/shared/` (两边同步)
- **数据库 DDL**: `database/ddl.sql`
- **数据库迁移**: `database/migrations/`

---

## 📞 联系方式

如有文档相关问题，请联系：
- 架构问题 → 技术负责人
- 业务问题 → 产品经理
- 流程问题 → 项目经理

---

**文档版本**: 1.0.0
**最后更新**: 2026-01-07
**维护者**: 开发团队
