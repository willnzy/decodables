# 临时文档目录 (docs/tmp)

> **更新日期**: 2026-01-16
> **状态**: 已清理完成

---

## 📋 目录用途

此目录用于存放**临时的技术文档**，包括：
- ✅ **待实施的计划文档**
- ✅ **技术调研和分析**
- ✅ **重构方案和执行记录**

**重要规则**:
- ❌ **不要存放长期文档**：完成后应同步到 `docs/main/` 或 `docs/shared/`
- ❌ **不要存放过时文档**：定期清理已归档和已完成的文档
- ✅ **命名规范**：使用 `[状态]标题-日期.md` 或 `标题-plan.md` 格式

---

## 📂 当前文件状态

### 审计报告 (1个)

| 文件名 | 状态 | 优先级 | 说明 |
|--------|------|--------|------|
| `backend-comprehensive-audit.md` | 📋 活跃 | P0 | 后端综合审计报告 (57 个问题) |

### 待实施计划 (1个)

| 文件名 | 状态 | 优先级 | 说明 |
|--------|------|--------|------|
| `api-consolidation-plan.md` | 📋 待实施 | P1 | API 整合重构方案 (~40% 完成) |

### 说明文档 (1个)

| 文件名 | 状态 | 说明 |
|--------|------|------|
| `README.md` | ✅ 当前文档 | 临时目录使用指南 |

---

## 🗑️ 清理记录

### 2026-01-16 清理 (8个)

**已删除 - 已完成或已合并**:
- `backend-documentation-audit-report.md` → 已合并到 `backend-comprehensive-audit.md`
- `security-audit-report.md` → 已合并到 `backend-comprehensive-audit.md`
- `TIER-FEATURE-FLAG-INTEGRATION-PLAN.md` → 状态"已完成"
- `TIER-PERMISSIONS-BACKEND-IMPLEMENTATION.md` → 状态"已完成"
- `daily_themes_schema_update_plan.md` → 状态"已完成"
- `repository-sql-audit-plan.md` → 已过时
- `async-client-migration-plan.md` → ✅ 已实施 (100% 完成，结论同步到审计报告)
- `themes_backend_implementation_plan.md` → ✅ 已实施 (100% 完成，结论同步到审计报告)

**已重命名 - 符合命名规范** (4个):
- `API-CONSOLIDATION-RESTRUCTURE-PLAN.md` → `api-consolidation-plan.md`
- `docs/NAMING-CONVENTIONS.md` → `docs/naming-conventions.md`
- `docs/shared/TIER-PERMISSIONS.md` → `docs/shared/tier-permissions.md`
- `docs/monitoring/GRAFANA-SETUP-GUIDE.md` → `docs/monitoring/grafana-setup-guide.md`

### 2026-01-13 清理 (15个)

**已归档** (4个):
- `[archived]api-db-audit-2026-01-10.md`
- `[archived]api-db-fix-progress-2026-01-10.md`
- `[archived]backend-analysis-2026-01-11.md`
- `[archived]refactoring-plan-phase-a-2026-01-11.md`

**日常修复记录** (4个):
- `2026-01-13-async-handler-fixes.md`
- `2026-01-13-final-async-fixes-summary.md`
- `2026-01-13-repository-analysis-findings.md`
- `2026-01-13-test-fixes-summary.md`

**已完成并同步到固定文档** (7个):
- `P0-HOTFIX-EXECUTION-SUMMARY.md` → `docs/main/deployment-scaling.md`
- `P1-P2-EXECUTION-SUMMARY.md` → `docs/main/deployment-scaling.md`
- `P1-P2-ARCHITECTURE-REVIEW.md` → `docs/main/backend-architecture.md`
- `HOTFIX-APPLICATION-LAYER.md` → `docs/main/deployment-scaling.md`
- `REMAINING-TASKS-CHECKLIST.md` → 已完成
- `IDEMPOTENT-USER-CREATION-IMPLEMENTATION.md` → `docs/main/deployment-scaling.md`
- `IDEMPOTENT-USER-CREATION-RISK-ANALYSIS.md` → `docs/main/deployment-scaling.md`

---

## 📚 固定文档位置

**完成的临时文档内容已迁移到以下固定文档:**

| 固定文档 | 内容 | 更新日期 |
|----------|------|----------|
| `docs/main/deployment-scaling.md` | Part 3: 维护与监控 | 2026-01-13 |
| `docs/main/backend-architecture.md` | infrastructure/tasks/, infrastructure/monitoring/ | 2026-01-13 |
| `docs/main/database-guide.md` | Part 4: 数据库维护任务 | 2026-01-13 |

---

## 🔄 文档生命周期

```
1. 创建临时文档 (docs/tmp/)
   ↓
2. 实施和验证
   ↓
3. 同步到固定文档 (docs/main/ 或 docs/shared/)
   ↓
4. 删除临时文档 ✅
```

---

## ⚠️ 注意事项

1. **定期清理**: 建议每月清理一次已完成的临时文档
2. **命名规范**: 使用描述性文件名，避免 `doc1.md`, `temp.md` 等
3. **归档标记**: 使用 `[archived]` 前缀标记已归档的文档
4. **状态标记**: 使用 emoji 标记文档状态（📋 待实施，✅ 已完成，❌ 已废弃）

---

**最后清理**: 2026-01-16
**下次清理**: 2026-02-16（建议）
**维护者**: 后端团队
