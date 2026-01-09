# Database v4.0 Refactoring Documentation

> **项目**: Make Decodables (MagicZine AI)
> **版本**: v3.27 → v4.0
> **日期**: 2026-01-09
> **状态**: ✅ 完成

---

## 📋 重构概览

本次数据库重构的主要目标：

1. **标准化命名和结构** - 统一 Snake Case 命名规范
2. **补充缺失内容** - 新增 13 张表 + 57 行配置初始化数据
3. **性能优化** - 128 个索引（单列、复合、部分、GIN/GIST）
4. **保持业务规则** - 双 ID 系统、积分扣费顺序、幂等性设计

**重构成果**:
- ✅ **42 张表** (29 原有 + 13 新增)
- ✅ **128 个索引**
- ✅ **23 个触发器**
- ✅ **7 个核心函数**
- ✅ **57 行 system_configs 初始化数据**

---

## 📚 核心文档

### 1. [refactored_schema_v2.sql](refactored_schema_v2.sql) - 完整的数据库 DDL

**用途**: 生产环境数据库初始化或重建
**目标读者**: DBA、数据库工程师
**文件大小**: 89 KB (2,160 行)

**包含内容**:
- 42 张表的完整定义
- 128 个索引（性能优化）
- 23 个触发器（自动维护 updated_at、deleted_at 等）
- 7 个核心业务函数（积分扣除、任务清理等）
- 57 行 system_configs 初始化数据

**快速开始**:
```bash
# 测试环境
psql -h localhost -U postgres -d decodables_test < refactored_schema_v2.sql

# 生产环境（谨慎！）
psql -h prod-host -U postgres -d decodables_prod < refactored_schema_v2.sql
```

---

### 2. [design_reasoning.md](design_reasoning.md) - 设计理念和决策说明

**用途**: 理解重构背后的设计思想和技术决策
**目标读者**: 架构师、技术负责人、高级工程师
**文件大小**: 50 KB (~1,100 行)

**章节概览**:
- **第 1-7 章**: 核心设计原则（命名规范、审计字段、索引策略、特殊表设计）
- **第 8 章**: 新增 13 张表的详细设计（P0/P1/P2 分级说明）
- **第 9 章**: system_configs 初始化数据设计（57 行配置的完整说明）
- **第 10-15 章**: 索引策略、数据完整性、扩展性、迁移建议

**适用场景**:
- 新成员了解数据库架构
- 技术方案评审
- 数据库优化决策参考

---

### 3. [mapping_and_changes.md](mapping_and_changes.md) - 字段映射表（代码迁移指南）

**用途**: 代码迁移时的字段对照表
**目标读者**: 后端工程师（Python/FastAPI）
**文件大小**: 66 KB (~1,550 行)

**包含内容**:
- 42 张表的字段映射（旧字段 → 新字段）
- 改动类型标注（🔄 重命名、🔧 类型变更、✨ 新增、❌ 删除）
- 索引和约束变更说明
- 新增表汇总（第 14 章）

**使用示例**:
```python
# 旧代码
user = db.query(User).filter(User.userId == clerk_id).first()

# 新代码（参考映射表）
user = db.query(User).filter(User.id == clerk_id).first()
```

**快速查找**:
- Ctrl+F 搜索表名或字段名
- 查看 "改动类型" 列确认是否需要修改代码

---

### 4. [VERIFICATION_CHECKLIST.md](VERIFICATION_CHECKLIST.md) - 验证清单和测试指南

**用途**: 验证数据库迁移是否成功
**目标读者**: QA、DBA、测试工程师
**文件大小**: 15 KB (~620 行)

**验证维度** (16 个):
1. 基础验证（表数量、索引数量）
2. 扩展验证（uuid-ossp、pg_trgm、ltree）
3. 表结构验证（P0/P1/P2 表是否存在）
4. 字段验证（关键字段类型检查）
5. 索引验证（性能优化索引）
6. 触发器验证（自动维护逻辑）
7. 函数验证（业务函数）
8. system_configs 验证（57 行配置）
9. ... （其他 8 个维度）

**使用方式**:
```bash
# 1. 连接数据库
psql -d decodables_test

# 2. 逐项执行验证 SQL（文档中提供）
SELECT COUNT(*) FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
-- Expected: 42

# 3. 对比预期结果
```

---

## 📦 归档文档

### [archived/analysis/](archived/analysis/) - 分析过程文档

记录重构过程中的分析和评估，便于追溯决策过程：

| 文档 | 用途 | 大小 |
|------|------|------|
| `DATABASE_DIFF_ANALYSIS_REPORT.md` | V1 vs V2 完整差异分析 | 51 KB |
| `DATABASE_DESIGN_REVIEW.md` | 初步设计评估（发现 13 张缺失表） | 28 KB |
| `EXECUTIVE_SUMMARY.md` | 执行摘要（5 页快速参考） | 7 KB |

**适用场景**: 复盘重构决策、理解为什么补充某些表

---

### [archived/drafts/](archived/drafts/) - 历史草稿版本

| 文档 | 说明 | 大小 |
|------|------|------|
| `refactored_schema_v1.sql` | 初版 DDL（仅 29 张表） | 93 KB |

**为什么保留 v1**:
- v1 有更详细的 COMMENT 注释（每个字段都有）
- 可作为注释参考

**为什么使用 v2**:
- ✅ 表更完整（42 张 vs 29 张）
- ✅ 基于最新 v3.27（而非 v3.24）
- ✅ 注释精简但保留关键信息

---

## 🚀 快速开始

### 场景 1: 新成员了解数据库架构

```
1. 先读 design_reasoning.md（第 1-7 章） - 了解设计原则
2. 再读 design_reasoning.md（第 8-9 章） - 了解新增内容
3. 查看 refactored_schema_v2.sql - 查看具体实现
```

---

### 场景 2: 代码迁移（后端工程师）

```
1. 先读 mapping_and_changes.md（第 1-10 章） - 查看字段映射
2. 使用 Ctrl+F 搜索要修改的表/字段
3. 根据 "改动类型" 列修改代码
4. 运行测试验证
```

**代码迁移示例**:

| 旧代码 (v3.27) | 新代码 (v4.0) | 改动类型 |
|----------------|---------------|----------|
| `User.userId` | `User.id` | 🔄 字段名不变（已是 id） |
| `User.createdAt` | `User.created_at` | 🔄 重命名（Snake Case） |
| - | `User.cohort_month` | ✨ 新增字段 |

---

### 场景 3: 数据库迁移（DBA）

```bash
# 1. 备份现有数据库
pg_dump -h prod-host -U postgres decodables_prod > backup_$(date +%Y%m%d).sql

# 2. 在测试环境验证
createdb decodables_test
psql -d decodables_test < refactored_schema_v2.sql

# 3. 运行验证清单
# 参考 VERIFICATION_CHECKLIST.md 中的 SQL

# 4. 生产环境迁移
# （推荐使用蓝绿部署，参考 design_reasoning.md 第 11 章）
```

---

### 场景 4: 验证迁移结果（QA）

```
1. 打开 VERIFICATION_CHECKLIST.md
2. 逐项执行验证 SQL（16 个维度）
3. 对比预期结果
4. 记录任何差异
```

---

## 🎯 重要提示

### ⚠️ 核心业务规则（绝对不变）

1. **双 ID 系统**:
   - `user_id` (TEXT) - Clerk ID 格式 `user_2xxx...`（**非 UUID**！）
   - `user_code` (TEXT UNIQUE) - 26位格式 `26010914305278900123456ABC` (包含注册时间+用户序号)

2. **积分扣费顺序**:
   - 先扣 `credits_monthly` → 再扣 `credits_permanent`

3. **幂等性设计**:
   - `credit_transactions.idempotency_key` UNIQUE
   - `user_purchases.idempotency_key` UNIQUE

4. **Append-Only 账本**:
   - `credit_transactions` 表禁止 UPDATE/DELETE（有触发器强制执行）

5. **system_configs 字段名**:
   - 使用 `key`/`value`（不是 `config_key`/`config_value`）
   - 保持向后兼容

---

### 📊 新增内容汇总 (v4.0)

#### 新增 13 张表

**P0 级别（关键阻塞）- 4 张**:
- `ai_call_logs` - AI API 调用日志（成本追踪）
- `ai_usage_daily` - AI 使用量日汇总
- `asset_categories` - 素材分类树（LTREE）
- `system_assets` - 系统内置素材

**P1 级别（重要功能）- 5 张**:
- `daily_themes` - 每日主题
- `holidays` - 节日日历
- `activity_logs` - 活动日志
- `analytics_aggregation` - 分析聚合表
- `scheduled_task_logs` - 定时任务日志

**P2 级别（增强功能）- 4 张**:
- `config_audit_logs` - 配置审计日志
- `content_reports` - 内容举报
- `system_resource_audit_logs` - 系统资源审计
- `asset_prompt_templates` - AI 提示词模板

详见: [design_reasoning.md - 第 8 章](design_reasoning.md#8-新增表设计说明)

---

#### 新增 57 行 system_configs 初始化数据

| 配置分组 | 数量 | 用途 |
|----------|------|------|
| Rate Limits | 24 | API 速率限制（防滥用） |
| AI Providers | 8 | AI 提供商和模型配置 |
| Credits | 9 | 积分成本和业务规则 |
| Feature Flags | 4 | 功能开关（灰度发布） |
| Limits | 5 | 业务限制（项目数量等） |
| Pricing | 4 | 定价信息（展示用） |
| Analytics | 3 | 分析配置 |

详见: [design_reasoning.md - 第 9 章](design_reasoning.md#9-system_configs-初始化数据)

---

## 🔗 相关资源

### 项目文档
- [CLAUDE.md](/CLAUDE.md) - 项目配置和开发规范
- [docs/shared/USER-ID-SYSTEM.md](/docs/shared/USER-ID-SYSTEM.md) - 双 ID 系统说明
- [docs/shared/TIER-NAMING-SYSTEM.md](/docs/shared/TIER-NAMING-SYSTEM.md) - 用户等级系统
- [docs/后台业务逻辑说明.md](/docs/后台业务逻辑说明.md) - 后端业务逻辑

### V1 数据库
- [V1/ddl.sql](../V1/ddl.sql) - 当前生产环境 DDL (v3.27)
- [V1/FILE_CLEANUP_PLAN.md](../V1/FILE_CLEANUP_PLAN.md) - V1 目录清理计划

---

## 📞 支持

如有问题，请联系：
- **架构师**: Claude Sonnet 4.5
- **DBA**: [Your DBA Name]
- **技术负责人**: [Your Tech Lead Name]

---

**文档版本**: v1.0
**最后更新**: 2026-01-09
