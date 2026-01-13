# 临时文档目录 (docs/tmp)

> **更新日期**: 2026-01-13  
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

### 待实施计划 (6个)

| 文件名 | 状态 | 优先级 | 说明 |
|--------|------|--------|------|
| `async-client-migration-plan.md` | 📋 待审核 | P2 | Supabase 异步客户端迁移计划 |
| `daily_themes_schema_update_plan.md` | 📋 待实施 | P2 | 日常主题 Schema 更新计划 |
| `repository-sql-audit-plan.md` | 📋 待实施 | P2 | Repository SQL 审计计划 |
| `themes_backend_implementation_plan.md` | 📋 待实施 | P2 | 主题系统后端实施计划 |
| `TIER-FEATURE-FLAG-INTEGRATION-PLAN.md` | 📋 待实施 | P1 | Tier 和 Feature Flag 集成计划 |
| `TIER-PERMISSIONS-BACKEND-IMPLEMENTATION.md` | 📋 待实施 | P1 | Tier 权限后端实施计划 |

### 说明文档 (1个)

| 文件名 | 状态 | 说明 |
|--------|------|------|
| `README.md` | ✅ 当前文档 | 临时目录使用指南 |

---

## 🗑️ 已清理文档 (15个)

### 2026-01-13 清理记录

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

**示例流程**:

```bash
# 1. 创建计划文档
docs/tmp/feature-x-implementation-plan.md

# 2. 实施完成后，同步到固定文档
# 编辑: docs/main/backend-architecture.md (添加架构说明)
# 编辑: docs/main/api-reference.md (添加 API 说明)

# 3. 删除临时文档
git rm docs/tmp/feature-x-implementation-plan.md
```

---

## ⚠️ 注意事项

1. **定期清理**: 建议每月清理一次已完成的临时文档
2. **命名规范**: 使用描述性文件名，避免 `doc1.md`, `temp.md` 等
3. **归档标记**: 使用 `[archived]` 前缀标记已归档的文档
4. **状态标记**: 使用 emoji 标记文档状态（📋 待实施，✅ 已完成，❌ 已废弃）

---

**最后清理**: 2026-01-13  
**下次清理**: 2026-02-13（建议）  
**维护者**: 后端团队
