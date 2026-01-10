# docs/tmp - 临时文档目录

**最后整理**: 2026-01-10 (激进清理)
**剩余文档**: 7 个

---

## 📋 目录说明

此目录**仅存放待执行的任务**文档：
- V3.0.0 升级计划（待执行）
- API 评审计划（待执行）

**清理原则**: 已完成的文档会立即迁移到 `docs/main/` 或删除，不保留详细文档。

---

## 📁 当前文档 (7个)

### 🚀 V3.0.0 升级计划 (4个)

| 文档 | 模块 | 预计工时 | 优先级 | 状态 |
|------|------|----------|--------|------|
| RESOURCES-UPGRADE-v3.0.0-PLAN.md | Resources | 8h | P0 | 📋 待执行 |
| USER-ASSETS-V3.0.0-PLAN.md | User Assets | 6h | P1 | 📋 待执行 |
| TEMPLATES-V3.0.0-PLAN.md | Templates | 6h | P1 | 📋 待执行 |
| SYSTEM-RESOURCES-V3.0.0-PLAN.md | System Resources | 4h | P2 | 📋 待执行 |

**汇总**: 升级路线图已整合到 [`docs/main/V3-UPGRADE-ROADMAP.md`](../main/V3-UPGRADE-ROADMAP.md)

**总工时**: 24 小时

### 📝 API 评审计划 (2个)

| 文档 | 范围 | 状态 |
|------|------|------|
| API-REVIEW-ADMIN.md | 管理员 API 评审 | 📋 待执行 |
| API-REVIEW-USER.md | 用户 API 评审 | 📋 待执行 |

### 📖 目录索引 (1个)

| 文档 | 用途 |
|------|------|
| README.md | 本文档 (目录说明) |

---

## 📊 清理历史

### 第一次整理 (2026-01-10 上午)

**整理前**: 54 个文档

**操作**:
- ✅ 创建 4 个汇总文档到 `docs/main/`
- ✅ 移动 2 个实用文档到 `docs/main/`
- ✅ 删除 30 个已完成的临时文档

**整理后**: 24 个文档

### 第二次清理 (2026-01-10 下午) - 激进清理

**整理前**: 24 个文档

**操作**:
- ✅ 删除 16 个已完成评审的详细文档（关键结论已汇总）
- ✅ 删除 2 个整理计划文档（任务已完成）

**整理后**: 7 个文档 (**仅保留待执行任务**)

**删除的评审文档** (已汇总到 `MODULE-QUALITY-REVIEWS.md`):
- EXPERIMENTS-5STAR-REVIEW-v3.31.md (⭐⭐⭐⭐⭐)
- CONFIG-5STAR-REVIEW-v2.2.0.md (⭐⭐⭐⭐⭐)
- WEBHOOKS-5STAR-REVIEW-v2.5.0.md (⭐⭐⭐⭐⭐)
- PAYMENT-5STAR-REVIEW-v2.3.0.md (⭐⭐⭐⭐⭐)
- ANALYTICS-5STAR-REVIEW-v2.3.0.md (⭐⭐⭐⭐)
- GENERATIONS-5STAR-REVIEW-v3.0.0.md (⭐⭐⭐⭐)
- EXPORT-5STAR-REVIEW-v3.0.0.md (⭐⭐⭐⭐)
- MARKETPLACE-5STAR-REVIEW-v3.0.0.md (⭐⭐⭐⭐)
- USER-PROFILE-5STAR-REVIEW-v2.2.0.md (⭐⭐⭐⭐)
- GENERATION-IMAGES-5STAR-REVIEW-v3.28.md (⭐⭐⭐⭐)
- GENERATION-PDF-5STAR-REVIEW-v3.26.md (⭐⭐⭐)
- GENERATION-STORY-5STAR-REVIEW-v3.28.md (⭐⭐⭐)
- LOGS-5STAR-REVIEW-PLAN-v3.0.0.md
- LOGS-5STAR-REVIEW-v3.0.0.md
- THEMES-5STAR-REVIEW-PLAN-v3.0.0.md
- THEMES-5STAR-REVIEW-v3.0.0.md

---

## 📊 整理统计

| 阶段 | 文档数 | 变化 | 说明 |
|------|--------|------|------|
| **原始状态** | 54 | - | Phase 报告、评审、升级计划 |
| **第一次整理** | 24 | -30 (-55%) | 删除临时文档，创建汇总 |
| **激进清理** | **7** | -17 (-71%) | **只保留待执行任务** |

**总清理**: 54 → 7 (**减少 87%**)

---

## 🔄 维护规则

### tmp/ 目录原则

**用途**: **仅存放待执行任务的计划文档**

**严格规则**:
- ✅ 任务开始前：创建计划文档放在 tmp/
- ✅ 任务进行中：可创建临时进度文档
- ✅ 任务完成后：立即删除，关键结论合并到 main/
- ❌ **禁止保留已完成任务的详细文档**

### 文档生命周期

```
创建任务计划 (tmp/)
   ↓
执行任务
   ↓
任务完成
   ↓
提取关键结论 → 合并到 main/ 汇总文档
   ↓
删除 tmp/ 中的所有相关文档 (不保留详细版)
```

### 定期检查

- **每周一**: 检查 tmp/ 目录，删除已完成任务的文档
- **原则**: tmp/ 目录应该始终保持在 **10 个文档以内**

---

## 📚 相关文档

### 汇总文档 (在 docs/main/)

已完成任务的所有关键信息都在这里：

| 文档 | 内容 | 来源 |
|------|------|------|
| [SOFT-DELETE-SYSTEM.md](../main/SOFT-DELETE-SYSTEM.md) | 软删除系统完整文档 | Phase 3 所有文档 |
| [SOFT-DELETE-HISTORY.md](../main/SOFT-DELETE-HISTORY.md) | 实施历史 | Phase 1/2/3 报告 |
| [MODULE-QUALITY-REVIEWS.md](../main/MODULE-QUALITY-REVIEWS.md) | 质量评审汇总 | 12 个评审文档 |
| [V3-UPGRADE-ROADMAP.md](../main/V3-UPGRADE-ROADMAP.md) | V3 升级路线图 | 4 个升级计划 |

### 其他重要文档

- [docs/main/](../main/) - 主文档目录（长期保留的架构和设计文档）
- [docs/shared/](../shared/) - 前后端共用文档
- [.claude/guides/](../../.claude/guides/) - 开发指南和最佳实践

---

## ✅ 当前状态

**tmp/ 目录状态**: 🟢 **干净整洁**

- ✅ 只包含 7 个待执行任务文档
- ✅ 所有已完成任务的关键结论已汇总到 main/
- ✅ 无冗余、无过时文档
- ✅ 维护规则明确

---

**Last Updated**: 2026-01-10 (激进清理后)
**Total Files**: 7 (从 54 个清理到 7 个，减少 87%)

🎉 **tmp/ 目录保持最小化，仅待执行任务！**
