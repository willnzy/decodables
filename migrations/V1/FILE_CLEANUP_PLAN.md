# V1 目录 SQL 文件清理计划

> **日期**: 2026-01-09
> **目的**: 清理已同步到 ddl.sql 的冗余文件，保持目录整洁

---

## 当前状态

**ddl.sql 版本**: v3.27 (最新，已包含所有迁移)

**总文件数**: 30 个 SQL 文件

---

## 文件分类

### ✅ 核心文件（必须保留）- 1 个

| 文件名 | 说明 | 操作 |
|--------|------|------|
| `ddl.sql` | 主 DDL 文件，v3.27 版本，包含完整数据库定义 | **保留** |

---

### 📦 增量迁移文件（已同步，建议归档）- 20 个

这些文件的内容已经全部同步到 `ddl.sql` 中，不再需要单独执行。

**建议操作**: 移动到 `V1/archived/migrations/` 目录归档保存。

| 文件名 | 版本 | 说明 | 操作 |
|--------|------|------|------|
| `v3.8_naming_convention_refactor.sql` | v3.8 | 命名规范重构 | 归档 |
| `v3.9_timezone_dual_storage.sql` | v3.9 | 时区双存储 | 归档 |
| `v3.10_system_configs.sql` | v3.10 | 系统配置重构 | 归档 |
| `v3.11_analytics_events.sql` | v3.11 | Analytics 事件增强 | 归档 |
| `v3.12_analytics_aggregation.sql` | v3.12 | Analytics 聚合表 | 归档 |
| `v3.13_holiday_themes_campaigns.sql` | v3.13 | 节日主题和营销活动 | 归档 |
| `v3.14_add_assets_usage_count.sql` | v3.14 | 素材使用计数 | 归档 |
| `v3.14_global_holidays_expansion.sql` | v3.14 | 全球节日扩展 | 归档 |
| `v3.15_scheduled_task_logs.sql` | v3.15 | 调度任务日志 | 归档 |
| `v3.16_tooltip_configs.sql` | v3.16 | Tooltip 配置 | 归档 |
| `v3.17_system_resources_enhancement.sql` | v3.17 | 系统资源增强 | 归档 |
| `v3.18_storage_buckets_setup.sql` | v3.18 | Storage Buckets 设置 | 归档 |
| `v3.19_event_id_for_capi.sql` | v3.19 | CAPI event_id | 归档 |
| `v3.20_ab_testing.sql` | v3.20 | A/B 测试系统 | 归档 |
| `v3.21_ai_model_configs.sql` | v3.21 | AI 模型配置 | 归档 |
| `v3.22_atomic_transactions.sql` | v3.22 | 原子事务 | 归档 |
| `v3.23_task_queue.sql` | v3.23 | 任务队列系统 | 归档 |
| `v3.24_user_generations.sql` | v3.24 | 用户生成历史 | 归档 |
| `v3.26_marketplace_two_level_category.sql` | v3.26 | 市场两级分类 | 归档 |
| `v3.27_campaign_atomic_increment.sql` | v3.27 | 活动原子递增 | 归档 |

---

### 🗑️ 修复/清理脚本（一次性执行，建议删除）- 7 个

这些是一次性修复脚本，执行后不再需要。

**建议操作**: 移动到 `V1/archived/fixes/` 目录归档（或直接删除）。

| 文件名 | 说明 | 操作 |
|--------|------|------|
| `FINAL_fix_all_tables.sql` | 最终表修复脚本 | 归档或删除 |
| `data_cleanup_only.sql` | 数据清理脚本 | 归档或删除 |
| `fix_admin_tables.sql` | 修复管理员表 | 归档或删除 |
| `fix_system_configs_final.sql` | 修复 system_configs（最终版） | 归档或删除 |
| `fix_system_configs_schema.sql` | 修复 system_configs 结构 | 归档或删除 |
| `fix_system_configs_v2.sql` | 修复 system_configs v2 | 归档或删除 |
| `production_launch_cleanup.sql` | 生产环境启动清理 | 归档或删除 |

---

### 🛠️ 工具脚本（保留）- 3 个

这些是可重复使用的工具脚本。

| 文件名 | 说明 | 操作 |
|--------|------|------|
| `db_health_check.sql` | 数据库健康检查 | **保留** |
| `reset_database.sql` | 重置数据库（开发环境） | **保留** |
| `verify_database.sql` | 验证数据库完整性 | **保留** |

---

## 推荐目录结构

```
decodables/migrations/V1/
├── ddl.sql                           ✅ 保留（核心文件）
├── db_health_check.sql               ✅ 保留（工具）
├── reset_database.sql                ✅ 保留（工具）
├── verify_database.sql               ✅ 保留（工具）
├── FILE_CLEANUP_PLAN.md              ✅ 保留（本文件）
│
├── archived/                         📦 新建归档目录
│   ├── migrations/                   📦 增量迁移归档
│   │   ├── v3.8_naming_convention_refactor.sql
│   │   ├── v3.9_timezone_dual_storage.sql
│   │   ├── ... (共 20 个文件)
│   │   └── v3.27_campaign_atomic_increment.sql
│   │
│   └── fixes/                        🗑️ 修复脚本归档
│       ├── FINAL_fix_all_tables.sql
│       ├── data_cleanup_only.sql
│       └── ... (共 7 个文件)
```

---

## 执行步骤

### 方案 A: 归档保存（推荐）

保留所有历史文件，便于追溯。

```bash
cd /Users/zhangyi/Code_all/AI-WEB/decodables/migrations/V1

# 1. 创建归档目录
mkdir -p archived/migrations
mkdir -p archived/fixes

# 2. 移动增量迁移文件
mv v3.*.sql archived/migrations/

# 3. 移动修复脚本
mv FINAL_fix_all_tables.sql archived/fixes/
mv data_cleanup_only.sql archived/fixes/
mv fix_*.sql archived/fixes/
mv production_launch_cleanup.sql archived/fixes/

# 4. 验证结果
ls -lh
ls -lh archived/migrations/
ls -lh archived/fixes/
```

**结果**: V1 目录只剩 5 个文件（ddl.sql + 3个工具 + 本清理计划）

---

### 方案 B: 直接删除（不推荐）

如果确定不需要历史文件，可以直接删除。

```bash
cd /Users/zhangyi/Code_all/AI-WEB/decodables/migrations/V1

# ⚠️ 危险操作，请备份后再执行
rm v3.*.sql
rm FINAL_fix_all_tables.sql data_cleanup_only.sql
rm fix_*.sql production_launch_cleanup.sql
```

**不推荐原因**: 无法追溯历史变更，不符合最佳实践。

---

## 执行清理

**推荐执行方案 A**。

执行后提交到 Git:

```bash
git add .
git commit -m "chore(migrations): archive old migration and fix scripts to V1/archived/"
git push
```

---

## 验证清单

清理完成后，验证以下内容：

- [ ] `ddl.sql` 文件完整且是 v3.27 版本
- [ ] `db_health_check.sql` 可正常运行
- [ ] `verify_database.sql` 可正常运行
- [ ] `reset_database.sql` 可正常运行（仅开发环境测试）
- [ ] 所有增量迁移文件已移动到 `archived/migrations/`
- [ ] 所有修复脚本已移动到 `archived/fixes/`
- [ ] Git 提交完成

---

## 清理后的目录结构

```
decodables/migrations/V1/
├── ddl.sql                    (108 KB) - v3.27 完整 DDL
├── db_health_check.sql        (7.7 KB) - 健康检查
├── reset_database.sql         (7.3 KB) - 重置数据库
├── verify_database.sql        (4.1 KB) - 验证数据库
├── FILE_CLEANUP_PLAN.md       (本文件)
│
└── archived/
    ├── migrations/            (20 个迁移文件)
    └── fixes/                 (7 个修复脚本)
```

**文件数量**: 从 30 个减少到 5 个（+ archived 目录）

**优点**:
- ✅ 目录清爽，一目了然
- ✅ 历史文件归档保存，可追溯
- ✅ 减少维护负担
- ✅ 符合最佳实践

---

**清理计划结束**
