# 数据库 Schema 文件位置说明

**更新时间**: 2026-01-10
**重要**: 数据库 DDL 文件已从 V1 迁移到 V2

---

## 📂 当前使用的 Schema 文件

### ⭐ 主 DDL 文件 (单一数据源)

**文件路径**: [`migrations/v2/refactored_schema_v2.sql`](../migrations/v2/refactored_schema_v2.sql)

**版本**: v4.0
**表数量**: 60 张
**总行数**: ~4,000 行
**状态**: ✅ 当前使用

**用途**:
- 新环境初始化
- 数据库结构参考
- Schema 对比基准
- 完整的表定义、索引、触发器、函数

---

## 🗂️ 文件结构

```
decodables/
├── migrations/
│   ├── v2/
│   │   ├── refactored_schema_v2.sql  ⭐ 主 DDL (v4.0)
│   │   ├── docs/
│   │   │   ├── README.md             # V2 文档索引
│   │   │   ├── REFACTORING_REPORT.md # 重构报告
│   │   │   └── MIGRATION_GUIDE.md    # 迁移指南
│   │   └── patches/                  # V2 补丁
│   │
│   ├── v3/                           # Phase 3 软删除迁移
│   │   └── 001_add_soft_delete_to_core_tables.sql
│   │
│   └── V1/                           # 已废弃 (仅供参考)
│       └── ddl.sql                   ❌ 旧版 (v3.27)
│
└── docs/
    └── DATABASE-SCHEMA-LOCATION.md   # 本文档
```

---

## 🔄 版本历史

| 版本 | 文件路径 | 表数量 | 状态 | 说明 |
|------|----------|--------|------|------|
| **v4.0** | `migrations/v2/refactored_schema_v2.sql` | 60 | ✅ 当前使用 | DDD 架构重构 + Phase 2/3 |
| v3.27 | `migrations/V1/ddl.sql` | 42 | ❌ 已废弃 | 旧版生产环境 |

---

## 📋 V4.0 主要改进

### 1. 架构重构

- ✅ 统一命名规范 (Snake Case)
- ✅ 标准化审计字段 (created_at, updated_at, is_deleted, deleted_at)
- ✅ 补充缺失的 13 张表
- ✅ 修复现有表的缺失字段
- ✅ 补充缺失的索引、触发器、函数

### 2. 软删除支持

**Phase 2 完成** (16 张表):
- profiles, projects, project_versions, assets
- marketplace_listings, asset_categories, system_assets
- notifications, campaign_participations, campaign_dismissals
- onboarding_steps, user_onboarding_progress
- referrals, page_prompt_templates
- credit_transactions, payment_records

**Phase 3.1 新增** (8 张表):
- marketplace_favorites, marketplace_reviews
- campaigns, daily_themes, holidays
- asset_prompt_templates
- support_tickets, support_replies

**合计**: 24/60 (40%) 表支持软删除

---

## 🚀 如何使用

### 新环境初始化

```bash
# 1. 使用 V2 主 DDL 初始化数据库
psql -U postgres -d decodables < migrations/v2/refactored_schema_v2.sql

# 2. (可选) 应用 Phase 3 增量迁移
psql -U postgres -d decodables < migrations/v3/001_add_soft_delete_to_core_tables.sql
```

### 查看 Schema 定义

```bash
# 查看完整 Schema
cat migrations/v2/refactored_schema_v2.sql

# 查看特定表
grep -A 50 "CREATE TABLE profiles" migrations/v2/refactored_schema_v2.sql

# 查看所有表名
grep "CREATE TABLE" migrations/v2/refactored_schema_v2.sql
```

### Schema 对比

```bash
# 对比 V1 和 V2 差异
diff migrations/V1/ddl.sql migrations/v2/refactored_schema_v2.sql

# 查看新增的表
grep "CREATE TABLE" migrations/v2/refactored_schema_v2.sql | \
  grep -v -f <(grep "CREATE TABLE" migrations/V1/ddl.sql)
```

---

## ⚠️ 重要提示

### 不要使用旧版 DDL

❌ **错误**:
```bash
# 不要使用 V1 DDL (已废弃)
psql < migrations/V1/ddl.sql
```

✅ **正确**:
```bash
# 使用 V2 主 DDL
psql < migrations/v2/refactored_schema_v2.sql
```

### Schema 同步规则

当进行数据库变更时:

1. **创建增量迁移文件**
   ```
   migrations/v3/XXX_description.sql
   ```

2. **同步到主 DDL**
   ```
   更新 migrations/v2/refactored_schema_v2.sql
   ```

3. **更新版本号**
   ```sql
   -- 文件头部
   -- Make Decodables - Refactored Database Schema (vX.X)
   ```

4. **提交 Git**
   ```bash
   git add migrations/v2/refactored_schema_v2.sql migrations/v3/*.sql
   git commit -m "feat(db): description"
   ```

---

## 📚 相关文档

### V2 数据库文档

- [refactored_schema_v2.sql](../migrations/v2/refactored_schema_v2.sql) - 完整 DDL (v4.0)
- [V2/docs/README.md](../migrations/v2/docs/README.md) - V2 文档索引
- [V2/docs/REFACTORING_REPORT.md](../migrations/v2/docs/REFACTORING_REPORT.md) - 重构报告

### Phase 3 软删除文档

- [SOFT-DELETE-UNIFICATION-PLAN.md](./tmp/SOFT-DELETE-UNIFICATION-PLAN.md) - 软删除统一化计划
- [PHASE-3.1-COMPLETION-REPORT.md](./tmp/PHASE-3.1-COMPLETION-REPORT.md) - Phase 3.1 完成报告

### 业务逻辑文档

- [后台业务逻辑说明.md](./main/后台业务逻辑说明.md) - 后端架构和业务规则

---

## 🔧 维护者信息

**责任人**: 开发团队
**最后更新**: 2026-01-10
**版本**: v1.0

如有疑问,请参考:
- V2 重构报告: `migrations/v2/docs/REFACTORING_REPORT.md`
- 提交 Issue: GitHub Issues

---

**快速链接**:
- [主 DDL 文件](../migrations/v2/refactored_schema_v2.sql) ⭐
- [V2 文档目录](../migrations/v2/docs/)
- [Phase 3 迁移目录](../migrations/v3/)
