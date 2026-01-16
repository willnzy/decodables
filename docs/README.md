# Backend Documentation

> Make Decodables 后端文档导航

**最后更新**: 2026-01-16

---

## 📚 文档分类

### 1. 核心架构文档 (必读)

| 文档 | 说明 | 大小 |
|------|------|------|
| [main/backend-architecture.md](./main/backend-architecture.md) | **DDD 架构设计指南** - 三层架构、依赖注入、分层职责 | 82KB |
| [main/backend-business-logic.md](./main/backend-business-logic.md) | **业务规则和数据库设计** - 积分系统、用户等级、支付流程 | 80KB |
| [main/api-reference.md](./main/api-reference.md) | **API 参考** - API 设计规范和端点列表 | 28KB |

### 2. 开发规范 (团队协作)

| 文档 | 说明 | 大小 |
|------|------|------|
| [main/testing-guide.md](./main/testing-guide.md) | **测试指南** - 单元测试、集成测试、测试策略 | 34KB |
| [main/deployment-scaling.md](./main/deployment-scaling.md) | **部署与扩展** - 部署流程、扩展策略 | 31KB |
| [NAMING-CONVENTIONS.md](./NAMING-CONVENTIONS.md) | **命名规范** - 代码命名、文件命名规范 | 9KB |

### 3. 数据库架构

| 文档 | 说明 | 大小 |
|------|------|------|
| [main/database-guide.md](./main/database-guide.md) | **数据库指南** - Schema 设计、RPC 函数 | 80KB |

---

## 🤝 前后端共享文档

这些文档在前端和后端仓库都有一份副本，修改时需要同步。详见 [shared/README.md](./shared/README.md)

| 文档 | 说明 |
|------|------|
| [shared/system-refactoring-proposal-v2.md](./shared/system-refactoring-proposal-v2.md) | 系统重构方案 v2 |
| [shared/project-implementation-plan.md](./shared/project-implementation-plan.md) | 项目实施计划 |
| [shared/feature-flag-design.md](./shared/feature-flag-design.md) | Feature Flag 系统设计 |
| [shared/asset-category-design.md](./shared/asset-category-design.md) | 素材分类系统设计 (10 类) |
| [shared/onboarding-design.md](./shared/onboarding-design.md) | 新手引导系统设计 |
| [shared/theme-system-design.md](./shared/theme-system-design.md) | 主题系统设计 |
| [shared/tier-naming-system.md](./shared/tier-naming-system.md) | Tier 命名规范 |
| [shared/user-id-system.md](./shared/user-id-system.md) | 用户 ID 系统 |
| [shared/pricing-system-design.md](./shared/pricing-system-design.md) | 定价系统设计 |
| [shared/canvas-data-schema.md](./shared/canvas-data-schema.md) | Canvas 数据结构 |
| [shared/analytics-system-design.md](./shared/analytics-system-design.md) | Analytics 系统设计 |
| [shared/articles-system-design.md](./shared/articles-system-design.md) | 文章系统设计 |
| [shared/static-pages-cms-design.md](./shared/static-pages-cms-design.md) | 静态页面 CMS 设计 |
| [shared/user-api-review.md](./shared/user-api-review.md) | User API 完整参考 (128 端点) |
| [shared/admin-api-review.md](./shared/admin-api-review.md) | Admin API 完整参考 (171 端点) |

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
   - [main/backend-business-logic.md](./main/backend-business-logic.md) - 了解业务规则
   - [main/backend-architecture.md](./main/backend-architecture.md) - 了解架构设计
   - [main/testing-guide.md](./main/testing-guide.md) - 了解测试策略

2. **开始开发前**:
   - [main/api-reference.md](./main/api-reference.md) - API 设计规范
   - [NAMING-CONVENTIONS.md](./NAMING-CONVENTIONS.md) - 命名规范

3. **写测试前**:
   - [main/testing-guide.md](./main/testing-guide.md) - 测试策略和覆盖要求

### 我要开发新功能，应该参考什么？

1. **确定功能归属**:
   - 查看 [main/backend-architecture.md](./main/backend-architecture.md) 确定属于哪个 Domain

2. **参考设计文档**:
   - 如果涉及前端，查看 [shared/](./shared/) 中的设计文档
   - 如果是新的架构决策，考虑创建新的 ADR

3. **遵循开发流程**:
   - 查看 [main/backend-architecture.md](./main/backend-architecture.md) 了解分层规则

### 我要修复 Bug，应该怎么做？

1. **定位问题**:
   - 查看 [main/backend-business-logic.md](./main/backend-business-logic.md) 确认业务规则
   - 查看 [main/backend-architecture.md](./main/backend-architecture.md) 确认代码位置

2. **修复和测试**:
   - 按照 [main/testing-guide.md](./main/testing-guide.md) 编写测试
   - 确保测试覆盖 Bug 场景

3. **提交代码**:
   - 遵循 Git 规范，确保 commit message 清晰

---

## 🔄 文档维护规则

### 何时更新文档？

1. **业务规则变更** → 更新 `main/backend-business-logic.md`
2. **架构调整** → 更新 `main/backend-architecture.md` 并考虑创建 ADR
3. **API 变更** → 更新 `main/api-reference.md` 和 `shared/user-api-review.md` 或 `shared/admin-api-review.md`
4. **数据库变更** → 更新 `main/database-guide.md`
5. **测试策略变更** → 更新 `main/testing-guide.md`

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
- **数据库 Schema**: `migrations/v2/` (3 个主文件)
- **Claude 指南**: 根目录 `.claude/guides/` (7 个专项指南)
- **Claude Skills**: 根目录 `.claude/skills/` (4 个开发规范)

---

## 📞 联系方式

如有文档相关问题，请联系：
- 架构问题 → 技术负责人
- 业务问题 → 产品经理
- 流程问题 → 项目经理

---

**文档版本**: 2.0.0
**最后更新**: 2026-01-16
**维护者**: 开发团队
