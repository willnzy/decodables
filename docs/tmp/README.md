# Temporary Documents (临时文档)

> 临时性文档存放目录，包括已完成的 Phase 报告、迁移计划、分析审计等

**目录创建**: 2026-01-07
**管理规则**: 自增序号，完成后定期清理

---

## 📋 文档清单 (共 17 个)

### 001-009: 管理和报告

| 序号 | 文档 | 说明 | 状态 | 删除条件 |
|------|------|------|------|---------|
| 001 | docs-organization-plan.md | 文档整理计划 | ✅ 已完成 | 整理完成后可删除 |
| 002 | phase-1-completion-report.md | Phase 1 完成报告 (API 层) | ✅ 已完成 | 所有 Phase 完成后删除 |
| 003 | phase-2-completion-report.md | Phase 2 完成报告 (测试覆盖) | ✅ 已完成 | 所有 Phase 完成后删除 |
| 004 | phase-2-execution-plan.md | Phase 2 执行计划 | ✅ 已完成 | Phase 2 完成后可删除 |
| 005 | migration-plan.md | 总体迁移计划 | ✅ 已完成 | 迁移完成后可删除 |
| 006 | services-migration-plan.md | Services 层迁移计划 | ✅ 已完成 | Phase 8 完成后可删除 |
| 007 | phase-8-migration-plan.md | Phase 8 迁移计划 (db → repositories) | ✅ 已完成 | Phase 8 完成后可删除 |
| 008 | credit-service-migration-analysis.md | 积分服务迁移分析 | ✅ 已完成 | Phase 8 完成后可删除 |
| 009 | api-endpoints-inventory.md | API 端点清单 | 📊 参考 | API 稳定后可删除 |

### 010-015: 临时分析和指南

| 序号 | 文档 | 说明 | 状态 | 删除条件 |
|------|------|------|------|---------|
| 010 | api-methods-audit.md | API 方法审计 | 📊 参考 | 审计完成后可删除 |
| 011 | api-optimization-plan.md | API 优化计划 | 📝 规划 | 优化完成后可删除 |
| 012 | legacy-code-cleanup-plan.md | 遗留代码清理计划 | 📝 规划 | 清理完成后可删除 |
| 013 | webhook-v2-staging-testing-guide.md | Webhook v2 测试指南 | 🧪 测试 | 流程标准化后删除 |
| 014 | github-actions-v2-api-testing.md | GitHub Actions 测试指南 | 🧪 测试 | 流程标准化后删除 |
| 015 | backend-next-steps-summary.md | 后端后续步骤总结 | 📝 规划 | 步骤完成后可删除 |

### 016-017: 未来 Phase 计划

| 序号 | 文档 | 说明 | 状态 | 删除条件 |
|------|------|------|------|---------|
| 016 | phase-9-10-architecture-cleanup-plan.md | Phase 9-10: 架构清理 (routers → api) | 🔮 未来 | Phase 9-10 完成后删除 |
| 017 | phase-11-async-repository-refactoring.md | Phase 11: Repository 异步改造 | 🔮 未来 | Phase 11 完成后删除 |

---

## 🗂️ 分类说明

### ✅ 已完成 (9 个)
这些文档记录了已完成的工作，主要用于历史回顾和审计。

**何时删除**:
- Phase 报告 (002-004): 所有 Phase 完成，项目稳定后
- 迁移计划 (005-008): 迁移完成且稳定运行 2 周后
- 整理计划 (001): 本次整理完成后

### 📊 参考文档 (2 个)
这些文档提供了临时的分析数据，可作为参考。

**何时删除**:
- API 清单 (009): API 稳定，不再频繁变更时
- API 审计 (010): 审计结论已应用到代码时

### 📝 规划文档 (3 个)
这些文档描述了待执行的优化和清理计划。

**何时删除**:
- 优化计划 (011): 优化完成并验证效果后
- 清理计划 (012): 清理完成并提交代码后
- 后续步骤 (015): 步骤全部完成后

### 🧪 测试指南 (2 个)
临时性的测试指南，帮助团队完成特定测试任务。

**何时删除**:
- 测试流程已标准化，集成到 CI/CD 流程
- 相关内容已合并到 `TEST_COVERAGE_PLAN.md` 或 `CI-TESTING-LIMITATIONS.md`

### 🔮 未来计划 (2 个)
尚未开始执行的 Phase 计划。

**何时删除**:
- Phase 执行完成并验证稳定后
- 执行过程中的经验总结已合并到核心文档

---

## 🔄 管理规则

### 1. 创建新临时文档

```bash
# 1. 检查当前最大序号
ls -1 docs/tmp/ | grep -E '^[0-9]{3}-' | sort -n | tail -1

# 2. 使用下一个序号创建
# 如果最后一个是 017，则新文档是 018
touch docs/tmp/018-new-document-name.md

# 3. 在文档开头标注
# > **序号**: 018
# > **创建日期**: YYYY-MM-DD
# > **状态**: 进行中/已完成/已废弃
# > **删除条件**: 明确的删除条件
```

### 2. 定期检查和清理

**每次创建新文档时**:
1. 阅读 `docs/tmp/README.md` 的文档清单
2. 检查是否有文档已满足删除条件
3. 删除已完成的临时文档
4. 更新本 README 的文档清单

**清理检查点**:
- ✅ **Phase 1-2 完成** → 可删除 002-004 (报告和计划)
- ✅ **Phase 8 完成** → 可删除 005-008 (迁移计划)
- ⏳ **Phase 9-10 完成** → 可删除 016
- ⏳ **Phase 11 完成** → 可删除 017
- ⏳ **API 稳定** → 可删除 009-011 (清单和优化)
- ⏳ **测试标准化** → 可删除 013-014 (测试指南)

### 3. 合并有价值的内容

在删除前，检查是否有内容应该合并到核心文档：

| 临时文档内容 | 合并目标 |
|-------------|---------|
| Phase 执行经验 | `BACKEND-DEVELOPMENT-SOP.md` |
| 架构决策 | `adr/` 新建 ADR |
| 业务规则变更 | `后台业务逻辑说明.md` |
| 测试策略 | `TEST_COVERAGE_PLAN.md` |
| API 设计原则 | `API-HTTP-METHODS-GUIDELINES.md` |

### 4. 归档 vs 删除

**删除**:
- 纯粹的进度报告
- 已过时的分析
- 一次性的临时指南

**归档** (移到 `docs/tmp/archive/`):
- 重要的决策过程记录
- 可能需要回顾的历史数据
- 复杂问题的分析过程

```bash
# 归档示例
mkdir -p docs/tmp/archive
git mv docs/tmp/002-phase-1-completion-report.md docs/tmp/archive/
```

---

## 📊 清理进度

### Phase 完成情况

| Phase | 状态 | 相关文档 | 清理状态 |
|-------|------|---------|---------|
| Phase 1 | ✅ 已完成 | 002 | 🔒 保留 (历史记录) |
| Phase 2 | ✅ 已完成 | 003, 004 | 🔒 保留 (历史记录) |
| Phase 8 | ✅ 已完成 | 005-008 | ⏳ 可清理 |
| Phase 9-10 | 📝 规划中 | 016 | 🔮 未来执行 |
| Phase 11 | 📝 规划中 | 017 | 🔮 未来执行 |

### 清理建议

#### 立即可删除 (Phase 8 已完成)
```bash
# Phase 8 迁移计划已完成，可以删除
git rm docs/tmp/005-migration-plan.md
git rm docs/tmp/006-services-migration-plan.md
git rm docs/tmp/007-phase-8-migration-plan.md
git rm docs/tmp/008-credit-service-migration-analysis.md

# 提交
git commit -m "docs: remove completed Phase 8 migration plans

Phase 8 migration completed successfully:
- services/db/ → infrastructure/repositories/ ✅
- db_compat.py兼容层创建 ✅
- 所有 Repository 测试通过 ✅

Removed temporary documents:
- 005-migration-plan.md
- 006-services-migration-plan.md
- 007-phase-8-migration-plan.md
- 008-credit-service-migration-analysis.md
"
```

#### Phase 9-10 完成后可删除
```bash
git rm docs/tmp/016-phase-9-10-architecture-cleanup-plan.md
```

#### Phase 11 完成后可删除
```bash
git rm docs/tmp/017-phase-11-async-repository-refactoring.md
```

---

## 🔍 快速查找

### 我想了解某个 Phase 的执行情况
- **Phase 1-2**: 查看 002-004
- **Phase 8**: 查看 005-008
- **Phase 9-11**: 查看 016-017

### 我想优化 API 性能
- 查看 011-api-optimization-plan.md

### 我想清理遗留代码
- 查看 012-legacy-code-cleanup-plan.md

### 我想了解 API 现状
- 查看 009-api-endpoints-inventory.md
- 查看 010-api-methods-audit.md

### 我想设置测试流程
- 查看 013-webhook-v2-staging-testing-guide.md
- 查看 014-github-actions-v2-api-testing.md

---

## 📝 序号分配规则

- **001-009**: 管理、报告、总体计划
- **010-019**: 分析、审计、优化计划
- **020-029**: 临时指南、操作手册
- **030-099**: 预留给未来的临时文档
- **100+**: 特殊情况或大型临时项目

---

## ⚠️ 注意事项

1. **不要删除进行中的文档** - 即使觉得不需要了，也要等到明确完成
2. **删除前先检查引用** - 确保没有其他文档引用
3. **重要内容先合并** - 删除前将有价值的内容合并到核心文档
4. **保留重要决策** - 关键的决策过程可以归档而不是删除
5. **定期审查** - 每个 Phase 完成后审查一次临时文档

---

**管理者**: 开发团队
**最后检查**: 2026-01-07
**下次检查**: Phase 9-10 开始前
