# Temporary Documents (临时文档)

> 临时性文档存放目录，包括已完成的 Phase 报告、迁移计划、分析审计等

**目录创建**: 2026-01-07
**管理规则**: 自增序号，完成后定期清理

---

## 📋 文档清单 (共 4 个)

### 未来 Phase 计划 (2 个)

| 序号 | 文档 | 说明 | 状态 | 删除条件 |
|------|------|------|------|---------|
| 016 | phase-9-10-architecture-cleanup-plan.md | Phase 9-10: 架构清理 (routers → api) | 🔮 未来 | Phase 9-10 完成后删除 |
| 017 | phase-11-async-repository-refactoring.md | Phase 11: Repository 异步改造 | 🔮 未来 | Phase 11 完成后删除 |

### 执行计划与分析 (2 个)

| 序号 | 文档 | 说明 | 状态 | 删除条件 |
|------|------|------|------|---------|
| 018 | phase-9-10-execution-plan.md | Phase 9-10 详细执行计划 (9 个 Stage) | 🔄 进行中 | Phase 9-10 完成后删除 |
| 019 | v1-v2-api-comparison.md | v1/v2 API 功能差异对比报告 (Stage 1 产物) | ✅ 已完成 | Stage 2 补全完成后删除 |

---

## 📝 已删除文档记录 (2026-01-07)

以下文档已删除,关键结论已记录在核心文档中:

### Phase 报告 (001-004)
- 001: docs-organization-plan.md - 文档整理计划已执行完成
- 002: phase-1-completion-report.md - 38 个 API 文件创建完成
- 003: phase-2-completion-report.md - 测试覆盖率达到 80%+
- 004: phase-2-execution-plan.md - Phase 2 执行计划已完成

**关键结论**: api/ (v2 DDD) 与 routers/ (v1) 并行运行，URL 前缀分别为 /api/v2/* 和 /api/*

### 迁移计划 (005-008)
- 005: migration-plan.md - 采用 Strangler Fig Pattern 渐进式迁移
- 006: services-migration-plan.md - Services 层迁移策略
- 007: phase-8-migration-plan.md - Phase 8 迁移 (db → repositories)
- 008: credit-service-migration-analysis.md - 积分服务迁移分析

**关键结论**: Phase 8 完成 - services/db/ (3088 行) 完全迁移到 infrastructure/repositories/, 创建 14 个新 Repository, db_compat.py 提供向后兼容

### 临时分析 (009-012, 015)
- 009: api-endpoints-inventory.md - API 端点静态快照 (已过时)
- 010: api-methods-audit.md - API 方法审计 (结论已合并到 API-HTTP-METHODS-GUIDELINES.md)
- 011: api-optimization-plan.md - API 优化已应用
- 012: legacy-code-cleanup-plan.md - 已被 Phase 9-10 计划替代
- 015: backend-next-steps-summary.md - 步骤已过时

### 测试指南 (013-014) - 已合并
- 013: webhook-v2-staging-testing-guide.md - 已合并到 TEST_COVERAGE_PLAN.md "集成测试指南"章节
- 014: github-actions-v2-api-testing.md - 已合并到 CI-TESTING-LIMITATIONS.md "GitHub Actions 配置优化"章节

---

## 🗂️ 分类说明

### 🔮 未来 Phase 计划 (2 个 - 保留中)
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
| Phase 1-2 | ✅ 已完成 | 002-004 | ✅ 已删除 (2026-01-07) |
| Phase 8 | ✅ 已完成 | 005-008 | ✅ 已删除 (2026-01-07) |
| Phase 9-10 | 📝 规划中 | 016 | 🔮 未来执行 |
| Phase 11 | 📝 规划中 | 017 | 🔮 未来执行 |

### 清理建议

#### ✅ 已完成清理 (2026-01-07)
```bash
# 已删除 15 个完成的临时文档:
# - Phase 报告: 001-004
# - 迁移计划: 005-008
# - 临时分析: 009-012, 015
# - 测试指南: 013-014 (已合并到主文档)
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
- **Phase 1-2**: 已完成并删除，关键结论见上方"已删除文档记录"
- **Phase 8**: 已完成并删除，关键结论见上方"已删除文档记录"
- **Phase 9-10**:
  - 总体计划: 016-phase-9-10-architecture-cleanup-plan.md
  - 详细执行: 018-phase-9-10-execution-plan.md
- **Phase 11**: 查看 017-phase-11-async-repository-refactoring.md

### 我想设置测试流程
- Webhook 集成测试: 查看 ../TEST_COVERAGE_PLAN.md "集成测试指南"章节
- GitHub Actions 配置: 查看 ../CI-TESTING-LIMITATIONS.md "GitHub Actions 配置优化"章节

### 我想了解已完成的工作
- 查看本文档"已删除文档记录"章节，包含所有关键结论

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
**最后更新**: 2026-01-08 (创建 018-phase-9-10-execution-plan.md)
**下次检查**: Phase 9-10 开始前
