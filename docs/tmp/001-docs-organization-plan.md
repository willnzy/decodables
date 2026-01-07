# 文档整理计划 #001

> **创建日期**: 2026-01-07
> **状态**: 进行中
> **目标**: 整理 docs/ 目录，区分永久文档、共享文档和临时文档

---

## 📋 当前文档清单 (共 32 个)

### docs/ 根目录 (23 个)
1. API-ENDPOINTS-INVENTORY.md (17K)
2. API-HTTP-METHODS-GUIDELINES.md (8.0K)
3. API-METHODS-AUDIT.md (11K)
4. API-OPTIMIZATION-PLAN.md (4.2K)
5. BACKEND-DEVELOPMENT-SOP.md (22K)
6. BACKEND-NEXT-STEPS-SUMMARY.md (5.7K)
7. BACKEND_ARCHITECTURE_GUIDE.md (42K) ⭐ 核心文档
8. CI-TESTING-LIMITATIONS.md (13K)
9. CREDIT_SERVICE_MIGRATION_ANALYSIS.md (19K)
10. DDD-Migration-Guide.md (17K)
11. GITHUB-ACTIONS-V2-API-TESTING.md (8.9K)
12. LEGACY_CODE_CLEANUP_PLAN.md (8.7K)
13. MIGRATION_PLAN.md (6.2K)
14. PHASE-1-COMPLETION-REPORT.md (13K) ✅ 已完成
15. PHASE-2-COMPLETION-REPORT.md (12K) ✅ 已完成
16. PHASE-2-EXECUTION-PLAN.md (17K)
17. PHASE_8_MIGRATION_PLAN.md (6.4K)
18. SERVICES_MIGRATION_PLAN.md (16K)
19. TEST_COVERAGE_PLAN.md (10K) ⭐ 核心文档
20. WEBHOOK-V2-STAGING-TESTING-GUIDE.md (12K)
21. [Phase-11]Async-Repository-Refactoring.md (16K) 🔮 未来计划
22. [Phase-9-10]Architecture-Cleanup-Plan.md (26K) 🔮 未来计划
23. 后台业务逻辑说明.md (55K) ⭐ 核心文档

### docs/shared/ (6 个) - 前后端共享
24. [重构后]Asset-Category-System-Design.md
25. [重构后]Feature-Flag-Experiments-Unified-Design.md
26. [重构后]Onboarding-System-Design.md
27. [重构后]Project-Implementation-Plan.md
28. [重构后]System-Refactoring-Proposal-v2.md
29. [重构后]Theme-Daily-Doodle-Design.md

### docs/adr/ (3 个) - Architecture Decision Records
30. 0001-use-ddd-architecture.md
31. 0002-database-driven-config.md
32. README.md

---

## 🗂️ 整理方案

### 1. docs/ - 永久核心文档 (保留 7 个)

**架构设计**:
- ✅ BACKEND_ARCHITECTURE_GUIDE.md (42K) - DDD 架构指南
- ✅ 后台业务逻辑说明.md (55K) - 业务规则和数据库
- ✅ DDD-Migration-Guide.md (17K) - DDD 迁移指南

**开发规范**:
- ✅ BACKEND-DEVELOPMENT-SOP.md (22K) - 开发标准操作流程
- ✅ API-HTTP-METHODS-GUIDELINES.md (8.0K) - API 方法规范

**测试和质量**:
- ✅ TEST_COVERAGE_PLAN.md (10K) - 测试覆盖计划
- ✅ CI-TESTING-LIMITATIONS.md (13K) - CI 测试限制说明

### 2. docs/shared/ - 前后端共享 (已存在，保持 6 个)

- ✅ [重构后]System-Refactoring-Proposal-v2.md - 重构方案
- ✅ [重构后]Project-Implementation-Plan.md - 实施计划
- ✅ [重构后]Feature-Flag-Experiments-Unified-Design.md - Feature Flag
- ✅ [重构后]Asset-Category-System-Design.md - 素材分类
- ✅ [重构后]Onboarding-System-Design.md - 新手引导
- ✅ [重构后]Theme-Daily-Doodle-Design.md - 主题系统

### 3. docs/adr/ - Architecture Decision Records (保持 3 个)

- ✅ 0001-use-ddd-architecture.md
- ✅ 0002-database-driven-config.md
- ✅ README.md

### 4. docs/tmp/ - 临时文档 (新建，移动 16 个)

**已完成的 Phase 报告** (移动后可删除):
- → tmp/002-phase-1-completion-report.md (PHASE-1-COMPLETION-REPORT.md)
- → tmp/003-phase-2-completion-report.md (PHASE-2-COMPLETION-REPORT.md)
- → tmp/004-phase-2-execution-plan.md (PHASE-2-EXECUTION-PLAN.md)

**已完成的迁移计划** (移动后可删除):
- → tmp/005-migration-plan.md (MIGRATION_PLAN.md)
- → tmp/006-services-migration-plan.md (SERVICES_MIGRATION_PLAN.md)
- → tmp/007-phase-8-migration-plan.md (PHASE_8_MIGRATION_PLAN.md)
- → tmp/008-credit-service-migration-analysis.md (CREDIT_SERVICE_MIGRATION_ANALYSIS.md)

**临时分析和审计** (移动后可删除):
- → tmp/009-api-endpoints-inventory.md (API-ENDPOINTS-INVENTORY.md)
- → tmp/010-api-methods-audit.md (API-METHODS-AUDIT.md)
- → tmp/011-api-optimization-plan.md (API-OPTIMIZATION-PLAN.md)
- → tmp/012-legacy-code-cleanup-plan.md (LEGACY_CODE_CLEANUP_PLAN.md)

**临时指南** (移动后可删除):
- → tmp/013-webhook-v2-staging-testing-guide.md (WEBHOOK-V2-STAGING-TESTING-GUIDE.md)
- → tmp/014-github-actions-v2-api-testing.md (GITHUB-ACTIONS-V2-API-TESTING.md)
- → tmp/015-backend-next-steps-summary.md (BACKEND-NEXT-STEPS-SUMMARY.md)

**未来计划** (保留在 tmp):
- ✅ tmp/016-phase-9-10-architecture-cleanup-plan.md ([Phase-9-10]Architecture-Cleanup-Plan.md)
- ✅ tmp/017-phase-11-async-repository-refactoring.md ([Phase-11]Async-Repository-Refactoring.md)

---

## 📝 执行步骤

### Step 1: 创建 tmp/ 目录
```bash
mkdir -p docs/tmp
```

### Step 2: 移动已完成的 Phase 报告
```bash
git mv docs/PHASE-1-COMPLETION-REPORT.md docs/tmp/002-phase-1-completion-report.md
git mv docs/PHASE-2-COMPLETION-REPORT.md docs/tmp/003-phase-2-completion-report.md
git mv docs/PHASE-2-EXECUTION-PLAN.md docs/tmp/004-phase-2-execution-plan.md
```

### Step 3: 移动已完成的迁移计划
```bash
git mv docs/MIGRATION_PLAN.md docs/tmp/005-migration-plan.md
git mv docs/SERVICES_MIGRATION_PLAN.md docs/tmp/006-services-migration-plan.md
git mv docs/PHASE_8_MIGRATION_PLAN.md docs/tmp/007-phase-8-migration-plan.md
git mv docs/CREDIT_SERVICE_MIGRATION_ANALYSIS.md docs/tmp/008-credit-service-migration-analysis.md
```

### Step 4: 移动临时分析文档
```bash
git mv docs/API-ENDPOINTS-INVENTORY.md docs/tmp/009-api-endpoints-inventory.md
git mv docs/API-METHODS-AUDIT.md docs/tmp/010-api-methods-audit.md
git mv docs/API-OPTIMIZATION-PLAN.md docs/tmp/011-api-optimization-plan.md
git mv docs/LEGACY_CODE_CLEANUP_PLAN.md docs/tmp/012-legacy-code-cleanup-plan.md
```

### Step 5: 移动临时指南
```bash
git mv docs/WEBHOOK-V2-STAGING-TESTING-GUIDE.md docs/tmp/013-webhook-v2-staging-testing-guide.md
git mv docs/GITHUB-ACTIONS-V2-API-TESTING.md docs/tmp/014-github-actions-v2-api-testing.md
git mv docs/BACKEND-NEXT-STEPS-SUMMARY.md docs/tmp/015-backend-next-steps-summary.md
```

### Step 6: 移动未来计划
```bash
git mv docs/[Phase-9-10]Architecture-Cleanup-Plan.md docs/tmp/016-phase-9-10-architecture-cleanup-plan.md
git mv docs/[Phase-11]Async-Repository-Refactoring.md docs/tmp/017-phase-11-async-repository-refactoring.md
```

### Step 7: 创建 tmp/README.md
创建说明文档，解释 tmp 目录的用途和清理规则。

### Step 8: 提交更改
```bash
git add docs/tmp/
git commit -m "docs: reorganize documentation structure

Created docs/tmp/ for temporary documents:
- Phase completion reports (Phase 1-2)
- Completed migration plans (Phase 8, services, credits)
- Temporary analysis and audits
- Temporary guides
- Future plans (Phase 9-11)

Kept in docs/ root:
- Core architecture guides (3 files)
- Development SOPs (2 files)
- Testing plans (2 files)

Kept in docs/shared/:
- 6 frontend-backend shared design docs

Kept in docs/adr/:
- 3 Architecture Decision Records

Total: 7 permanent + 6 shared + 3 ADR + 17 temporary

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## 🔄 未来清理规则

### 何时删除 tmp/ 文件？

1. **Phase 完成报告**: 内容已合并到主文档后可删除
2. **迁移计划**: 迁移完成且验证稳定后可删除
3. **分析和审计**: 结论已应用到代码后可删除
4. **临时指南**: 流程已标准化后可删除
5. **未来计划**: 执行完成后移到 completed/ 或删除

### 定期清理检查点

- ✅ Phase 8 完成 → 删除 tmp/005-008 (迁移计划)
- ⏳ Phase 9-10 完成 → 删除 tmp/016
- ⏳ Phase 11 完成 → 删除 tmp/017
- ⏳ 所有 Phase 完成 → 删除 tmp/002-004 (报告)

---

## 📊 整理后的目录结构

```
docs/
├── README.md (需新建 - 文档导航)
│
├── 核心文档 (7 个)
│   ├── BACKEND_ARCHITECTURE_GUIDE.md (42K) - DDD 架构
│   ├── 后台业务逻辑说明.md (55K) - 业务规则
│   ├── DDD-Migration-Guide.md (17K) - 迁移指南
│   ├── BACKEND-DEVELOPMENT-SOP.md (22K) - 开发 SOP
│   ├── API-HTTP-METHODS-GUIDELINES.md (8K) - API 规范
│   ├── TEST_COVERAGE_PLAN.md (10K) - 测试计划
│   └── CI-TESTING-LIMITATIONS.md (13K) - CI 限制
│
├── shared/ - 前后端共享 (6 个)
│   ├── [重构后]System-Refactoring-Proposal-v2.md
│   ├── [重构后]Project-Implementation-Plan.md
│   ├── [重构后]Feature-Flag-Experiments-Unified-Design.md
│   ├── [重构后]Asset-Category-System-Design.md
│   ├── [重构后]Onboarding-System-Design.md
│   └── [重构后]Theme-Daily-Doodle-Design.md
│
├── adr/ - Architecture Decision Records (3 个)
│   ├── README.md
│   ├── 0001-use-ddd-architecture.md
│   └── 0002-database-driven-config.md
│
└── tmp/ - 临时文档 (17 个，包括本文档)
    ├── README.md (需新建 - 临时文档说明)
    ├── 001-docs-organization-plan.md (本文档)
    ├── 002-phase-1-completion-report.md
    ├── 003-phase-2-completion-report.md
    ├── 004-phase-2-execution-plan.md
    ├── 005-migration-plan.md
    ├── 006-services-migration-plan.md
    ├── 007-phase-8-migration-plan.md
    ├── 008-credit-service-migration-analysis.md
    ├── 009-api-endpoints-inventory.md
    ├── 010-api-methods-audit.md
    ├── 011-api-optimization-plan.md
    ├── 012-legacy-code-cleanup-plan.md
    ├── 013-webhook-v2-staging-testing-guide.md
    ├── 014-github-actions-v2-api-testing.md
    ├── 015-backend-next-steps-summary.md
    ├── 016-phase-9-10-architecture-cleanup-plan.md
    └── 017-phase-11-async-repository-refactoring.md
```

---

## ✅ 完成标准

- [ ] tmp/ 目录创建
- [ ] 17 个临时文档移动到 tmp/
- [ ] 创建 docs/README.md (文档导航)
- [ ] 创建 docs/tmp/README.md (临时文档说明)
- [ ] 提交 git commit
- [ ] 验证所有文档链接正常

---

**下一步**: 执行 Step 1-8
