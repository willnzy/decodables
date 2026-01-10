# V1 数据库 Schema - 已废弃

**废弃时间**: 2026-01-10
**原因**: 项目重构,V2 refactored schema 已成为单一数据源
**状态**: ✅ 已删除

---

## 📋 废弃说明

V1 目录及其内容已被删除,原因:

1. **项目未上线**: 无需保留生产环境兼容性
2. **V2 已完成**: `migrations/v2/refactored_schema_v2.sql` 已包含所有表定义
3. **避免混淆**: 单一数据源,避免维护两套 Schema

---

## 🗂️ 原 V1 目录内容 (已删除)

```
migrations/V1/                    (504K, 已删除)
├── ddl.sql                       (107K) - v3.27 完整 DDL
├── db_health_check.sql           (7.7K) - 数据库健康检查
├── reset_database.sql            (7.2K) - 重置脚本
├── verify_database.sql           (4.1K) - 验证脚本
├── FILE_CLEANUP_PLAN.md          (6.7K) - 清理计划
├── MIGRATION_SYNC_REPORT.md      (5.8K) - 迁移同步报告
└── archived/                     - 归档文件
```

---

## 🔄 迁移到 V2

### V1 → V2 对比

| 特性 | V1 (ddl.sql v3.27) | V2 (refactored_schema_v2.sql v4.0) |
|------|-------------------|-------------------------------------|
| 表数量 | 42 | 60 (+18 张新表) |
| 命名规范 | 混合 | Snake Case 统一 |
| 审计字段 | 不完整 | 完整 (created_at/updated_at/is_deleted/deleted_at) |
| 软删除支持 | 3 张表 | 24 张表 (40%) |
| 索引优化 | 基础 | 条件索引 + 性能优化 |
| 文档 | 简单 | 完整注释 + 文档 |

### 新表 (V2 新增的 18 张)

**Phase 2 补充的 13 张表**:
1. daily_themes - 每日主题
2. holidays - 节假日
3. generation_tasks - AI 生成任务
4. content_reports - 内容举报
5. marketplace_reports - 市场举报
6. listing_usages - 列表使用记录
7. asset_prompt_templates - 素材提示模板
8. pricing_history - 价格历史
9. user_price_overrides - 用户价格覆盖
10. user_discounts - 用户折扣
11. support_tickets - 支持工单
12. support_replies - 工单回复
13. referrals - 推荐记录

**其他补充**:
14-18. 统计与日志表

---

## 📂 新的 Schema 文件位置

**主 DDL 文件**: [`migrations/v2/refactored_schema_v2.sql`](v2/refactored_schema_v2.sql)

**版本**: v4.0
**表数量**: 60 张
**总行数**: ~4,000 行

**详细说明**: [docs/DATABASE-SCHEMA-LOCATION.md](../docs/DATABASE-SCHEMA-LOCATION.md)

---

## 🔧 如何使用 V2 Schema

### 新环境初始化

```bash
# 使用 V2 主 DDL 初始化
psql -U postgres -d decodables < migrations/v2/refactored_schema_v2.sql

# (可选) 应用 Phase 3 增量迁移
psql -U postgres -d decodables < migrations/v3/001_add_soft_delete_to_core_tables.sql
```

### 查看 Schema

```bash
# 查看完整 Schema
cat migrations/v2/refactored_schema_v2.sql

# 查看所有表名
grep "CREATE TABLE" migrations/v2/refactored_schema_v2.sql
```

---

## 📚 相关文档

### V2 Schema 文档

- [refactored_schema_v2.sql](v2/refactored_schema_v2.sql) - 完整 DDL (v4.0)
- [v2/docs/README.md](v2/docs/README.md) - V2 文档索引
- [v2/docs/REFACTORING_REPORT.md](v2/docs/REFACTORING_REPORT.md) - 重构报告

### 数据库迁移指南

- [docs/DATABASE-SCHEMA-LOCATION.md](../docs/DATABASE-SCHEMA-LOCATION.md) - Schema 文件位置说明
- [.claude/guides/DATABASE-MIGRATION.md](../../.claude/guides/DATABASE-MIGRATION.md) - 迁移最佳实践

---

## ✅ 验证 V2 完整性

V2 Schema 已包含 V1 的所有功能,并新增:

- ✅ 所有 V1 表 (42 张) → V2 已包含
- ✅ 新增 18 张业务表
- ✅ 统一命名规范
- ✅ 完整审计字段
- ✅ 软删除支持 (24/60 表)
- ✅ 索引优化
- ✅ 完整文档

**结论**: V1 目录可以安全删除,不会丢失任何功能。

---

**Git Commit**: `ebad733` - "docs: update DDL references from V1 to V2"
**删除时间**: 2026-01-10
**责任人**: 开发团队

如有疑问,请查阅:
- [V2 重构报告](v2/docs/REFACTORING_REPORT.md)
- [Schema 位置说明](../docs/DATABASE-SCHEMA-LOCATION.md)
