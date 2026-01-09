# Temporary Documentation

**目录用途**: 临时执行规划和审查报告
**清理策略**: 完成任务后定期清理过时文档

---

## 📁 Current Files (12)

### 📊 5-Star Review System

| 文档 | 模块 | 状态 | 说明 |
|------|------|------|------|
| [5-STAR-REVIEW-PLAN.md](5-STAR-REVIEW-PLAN.md) | - | 📋 总体计划 | 所有模块的5星审查计划 |
| [ANALYTICS-5STAR-REVIEW-v1.0.0.md](ANALYTICS-5STAR-REVIEW-v1.0.0.md) | Analytics | ✅ 完成 | v1.0.0 5星审查报告 |
| [BILLING-5STAR-REVIEW-v1.0.0.md](BILLING-5STAR-REVIEW-v1.0.0.md) | Billing | ✅ 完成 | v1.0.0 5星审查报告 |
| [CAMPAIGNS-5STAR-REVIEW-v1.0.0.md](CAMPAIGNS-5STAR-REVIEW-v1.0.0.md) | Campaigns | ✅ 完成 | v1.0.0 5星审查报告 |
| [EVENTS-5-STAR-FINAL.md](EVENTS-5-STAR-FINAL.md) | Events | ⭐⭐⭐⭐⭐ | v3.27 最终报告 (5/5星) |

### 🏗️ Architecture & Migration

| 文档 | 用途 | 状态 |
|------|------|------|
| [API-Architecture-Review-2026-01-10.md](API-Architecture-Review-2026-01-10.md) | API 架构审查 | ✅ 最新 (2026-01-10) |
| [AI-MODELS-REPO-DI-MIGRATION.md](AI-MODELS-REPO-DI-MIGRATION.md) | AI Models DI 迁移指南 | 📝 迁移中 |
| [CAMPAIGNS-REPO-DI-MIGRATION.md](CAMPAIGNS-REPO-DI-MIGRATION.md) | Campaigns DI 迁移指南 | 📝 迁移中 |
| [NOTIFICATIONS-REPO-DI-MIGRATION.md](NOTIFICATIONS-REPO-DI-MIGRATION.md) | Notifications DI 迁移指南 | 📝 迁移中 |
| [AUDIT-LOG-DECORATOR-USAGE.md](AUDIT-LOG-DECORATOR-USAGE.md) | 审计日志装饰器使用说明 | 📋 参考 |

### 📈 Project Status

| 文档 | 用途 | 更新日期 |
|------|------|----------|
| [PROJECT-OVERVIEW-2026-01-09.md](PROJECT-OVERVIEW-2026-01-09.md) | 项目总览 | 2026-01-09 |
| [REFACTORING-PROGRESS-REPORT.md](REFACTORING-PROGRESS-REPORT.md) | 重构进度报告 | 2026-01-09 |

---

## 🗑️ Cleanup History

**最近清理**: 2026-01-10

**删除文件数**: 40个

**删除类别**:
- ❌ 过时的审查文档 (5个): DEEP-REVIEW-*, HONEST-REVIEW-*, P0-CRITICAL-*
- ❌ 重复的模块审查 (24个): *-FIX-*, *-FULL-REVIEW-*, *-MODULE-REVIEW-*
- ❌ 旧式 REVIEW-XXX 系列 (12个): REVIEW-AI.md, REVIEW-CONFIG.md, etc.
- ❌ 过时的 API 审查 (3个): API-REVIEW-ADMIN.md (68KB), API-REVIEW-USER.md (98KB)
- ❌ 其他过时文档 (2个): GENERATION-IMAGES-*, NOTIFICATIONS-AUDIT-*

**保留原则**:
- ✅ 最新的5星审查报告
- ✅ 当前使用的迁移指南
- ✅ 最新的架构审查
- ✅ 活跃的项目状态文档

---

## 📋 Usage Guidelines

### 添加新文档

**命名规范**:
```
{模块名}-{类型}-{版本}.md

类型:
- 5STAR-REVIEW: 5星审查报告
- FIX: 修复记录
- MIGRATION: 迁移指南
- REVIEW: 审查报告
```

**示例**:
```
CONFIG-5STAR-REVIEW-v1.0.0.md     ✅ 正确
CONFIG-FIX-v2.0.0.md              ✅ 正确
BILLING-MIGRATION-DI.md           ✅ 正确

review-config.md                  ❌ 错误 (小写)
CONFIG_REVIEW.md                  ❌ 错误 (下划线)
config-review-latest.md           ❌ 错误 (无版本)
```

### 清理策略

**每周清理**: 删除已完成任务的临时文档

**保留时限**:
- 执行规划: 完成后 7 天
- 审查报告: 完成后 30 天 (除非是最终版本)
- 迁移指南: 迁移完成后 30 天
- 项目状态: 每月只保留最新版

---

**Last Updated**: 2026-01-10
**Total Files**: 12 (从 52 个清理到 12 个)
