# Temporary Documentation

**目录用途**: 临时执行规划和审查报告
**清理策略**: 完成任务后定期清理过时文档

---

## 📁 Current Files (4)

| 文档 | 用途 | 大小 |
|------|------|------|
| [5-STAR-REVIEW-PLAN.md](5-STAR-REVIEW-PLAN.md) | 所有模块的5星审查总体计划 | 8.9K |
| [API-REVIEW-ADMIN.md](API-REVIEW-ADMIN.md) | Admin API 详细审查报告 | 19K |
| [API-REVIEW-USER.md](API-REVIEW-USER.md) | User API 详细审查报告 | 46K |
| README.md | 本文档 (目录说明) | 3.7K |

**总大小**: ~78K

---

## 🗑️ Cleanup History

### 第一次清理 (2026-01-10)
- **删除**: 38个过时文档
- **保留**: 14个文档
- **意外删除**: API-REVIEW-ADMIN.md, API-REVIEW-USER.md
- **恢复**: 从 git commit 恢复 (d39971a, 2d5ec13)

### 第二次清理 (2026-01-10)
- **删除**: 11个已完成/临时文档
  - 4个 5星审查报告 (已完成任务)
  - 3个 DI 迁移指南 (迁移已完成)
  - 3个 架构/项目状态文档 (已过期)
  - 1个 装饰器使用说明
- **保留**: 4个核心文档

**清理结果**: 52 → 4 文件 (92% 减少)

---

## ⚠️ Important Note

**删除文件前必须**:
1. 列出完整清单
2. 向用户确认
3. 等待批准后执行

避免误删重要文档!

---

## 📋 Usage Guidelines

### docs/tmp/ 目录原则

**用途**: 存放临时执行规划、审查报告

**清理规则**:
- ✅ 任务完成后 7 天内清理
- ✅ 每周定期检查并删除过期文档
- ✅ 保留关键参考文档 (如 API 审查)

**命名规范**:
```
{模块名}-{类型}-{版本}.md

示例:
CONFIG-5STAR-REVIEW-v1.0.0.md     ✅
BILLING-MIGRATION-DI.md           ✅
PROJECT-OVERVIEW-2026-01-10.md    ✅
```

---

**Last Updated**: 2026-01-10
**Total Files**: 4 (从 52 个清理到 4 个)
