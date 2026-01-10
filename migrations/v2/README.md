# Migration v2 - Schema Files

## 文件说明

| 文件 | 大小 | 用途 | 执行顺序 |
|------|------|------|----------|
| `refactored_schema_v2.sql` | 185KB | 完整 schema (原始文件) | 单文件执行 |
| `schema_tables.sql` | 70KB | 表结构定义 (60张表) | ① 第一步 |
| `schema_indexes_functions.sql` | 39KB | 索引和函数 (273条) | ② 第二步 |
| `schema_data.sql` | 5.6KB | 初始数据 (6条插入) | ③ 第三步 |

## 执行方式

### 方式 1: 单文件执行（推荐用于新建数据库）

```bash
psql -U postgres -d decodables -f refactored_schema_v2.sql
```

### 方式 2: 分步执行（推荐用于调试或分阶段部署）

```bash
# 1. 创建表结构
psql -U postgres -d decodables -f schema_tables.sql

# 2. 创建索引和函数
psql -U postgres -d decodables -f schema_indexes_functions.sql

# 3. 插入初始数据
psql -U postgres -d decodables -f schema_data.sql
```

## 为什么要分离？

**优势**:
1. **可读性**: 表定义、索引、数据分开，更易理解
2. **可维护性**: 修改索引不需要重跑整个 schema
3. **灵活性**: 可以选择性执行（如只更新索引）
4. **调试友好**: 错误定位更精准

**使用场景**:
- ✅ 新建数据库 → 使用单文件 `refactored_schema_v2.sql`
- ✅ 增量迁移 → 使用分离文件
- ✅ 索引优化 → 只执行 `schema_indexes_functions.sql`
- ✅ 更新配置 → 只执行 `schema_data.sql`

## 已废弃的迁移文件

以下文件内容已合并到 `refactored_schema_v2.sql`，无需再执行：

- ❌ `003_create_pricing_tables.sql` (内容已包含)
- ❌ `add_experiment_tracking_tables.sql` (内容已包含)
- ❌ `../v3/001_add_soft_delete_to_core_tables.sql` (内容已包含)

## 工具脚本

**自动分离工具**: `/scripts/tools/split_schema.py`

```bash
# 使用方法
python3 /Users/zhangyi/Code_all/AI-WEB/decodables/scripts/tools/split_schema.py
```

## 详细报告

完整的执行报告和验证结果请查看: `SCHEMA_SPLIT_REPORT.md`

---

**最后更新**: 2026-01-10
**维护者**: Claude Code
