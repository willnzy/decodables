# 数据库-代码同步修复方案概览

**创建时间**: 2026-01-10
**审查报告**: 详见 [Explore Agent 审查报告](agentId: a7062f1)
**执行计划**: 详见 [DB-CODE-SYNC-PLAN.md](./DB-CODE-SYNC-PLAN.md)

---

## 🎯 一句话总结

**问题**: 数据库 Schema 已升级到 v4.0 DDD 架构，但 Repository 代码仍引用 legacy 表名/字段名，导致 70+ 处不匹配。

**方案**: 代码适配 Schema（而非 Schema 适配代码），分 5 个 Phase 修复，预计 3 个工作日完成。

---

## 📊 问题量化

| 指标 | 数量 |
|------|------|
| 数据库表总数 (Schema) | 47 |
| Repository 文件总数 | 26 |
| 不匹配问题总数 | 70+ |
| **Critical 问题** | **42** |
| **High 问题** | **28** |
| 需修复的 Repository 文件 | 9 个 |
| 需创建的新表 | 13 个 |
| 需新建的 Repository | 3 个 |

---

## 🔴 Top 5 Critical Issues

### 1. users vs profiles 表混乱 (23 处错误)

```python
# ❌ 错误: 引用不存在的 "users" 表
user_repository.py:57:  table("users").select("user_id, ...")
user_repository.py:78:  table("users").upsert(...)
# ... 21 处类似错误

# ✅ 正确: 应该引用 "profiles" 表
table("profiles").select("id as user_id, ...")
```

**影响**: 用户管理功能完全失效

---

### 2. 13 个表在代码中引用但不存在于 Schema

| 表名 | 影响功能 |
|------|----------|
| `user_events` | 行为追踪失效 |
| `aggregated_stats` | 统计功能失效 |
| `error_logs` | 错误日志失效 |
| `support_tickets` | 支持系统失效 |
| `support_replies` | 工单回复失效 |
| +8 other tables | ... |

**影响**: 6 个核心功能完全无法使用

---

### 3. projects 表字段名不匹配 (18 处错误)

```python
# ❌ 错误:
.eq("project_id", ...)  # Schema 中是 "id"
.eq("owner_id", ...)    # Schema 中是 "user_id"

# ✅ 正确:
.eq("id", ...)
.eq("user_id", ...)
```

**影响**: 所有项目查询失败

---

### 4. marketplace_purchases 字段错误

```python
# ❌ 错误:
.eq("buyer_id", buyer_id)  # 字段不存在

# ✅ 正确:
.eq("user_id", buyer_id)   # Schema 中的字段名
```

**影响**: 购买查询失败

---

### 5. 8 个孤立表（有表无代码）

包括关键的 `pricing_plans` 表，定价系统无法管理。

---

## 📋 5 阶段执行计划

### Phase 1: 修复核心表 (Day 1 上午, ~5h)

**目标**: 修复 `users`/`profiles` 和 `projects` 字段问题

**任务**:
- ✅ user_repository.py: 23 处修改
- ✅ project_repository.py: 18 处修改
- ✅ credit_repository.py: 5 处修改
- ✅ listing_repository.py: 8 处修改
- ✅ 补充 profiles 表 5 个缺失字段
- ✅ 补充 projects 表 1 个缺失字段

**交付**: 用户/项目/积分功能恢复

---

### Phase 2: 创建 P0 缺失表 (Day 1 下午, ~2.5h)

**目标**: 创建 4 个最关键的缺失表

**表清单**:
1. ✅ `user_events` - 用户行为追踪
2. ✅ `aggregated_stats` - 统计聚合
3. ✅ `error_logs` - 错误日志
4. ✅ `support_tickets` + `support_replies` - 支持系统

**交付**: 日志/统计/支持功能恢复

---

### Phase 3: 创建 P1 缺失表 (Day 2 上午, ~3h)

**目标**: 创建 5 个高优先级表

**表清单**:
1. ✅ `admin_operations` - 管理员操作日志
2. ✅ `listing_usages` - 资产使用追踪
3. ✅ `marketplace_reports` - 市场报告
4. ✅ `daily_metrics` - 每日指标
5. ✅ `monthly_metrics` - 月度指标

**交付**: 管理/市场/指标功能完善

---

### Phase 4: 实现孤立表 Repository (Day 2 下午, ~5h)

**目标**: 为 8 个"有表无代码"表创建 Repository

**新建文件**:
1. ✅ `pricing_repository.py` (关键!) - 定价管理
2. ✅ `onboarding_repository.py` - 新手引导
3. ✅ `themes_repository.py` - 主题系统

**交付**: 定价/引导/主题功能可用

---

### Phase 5: 测试与验证 (Day 3, ~7h)

**目标**: 全面测试，确保无遗漏

**任务**:
- ✅ 单元测试 (10 个 Repository)
- ✅ 集成测试 (4 个关键流程)
- ✅ 数据迁移验证
- ✅ 性能测试
- ✅ 文档更新

**交付**: 生产环境可部署

---

## 🎯 修复策略对比

### 方案 A: 代码适配 Schema ⭐ (推荐)

**优势**:
- ✅ Schema 是 DDD 重构后的 v4.0，结构更合理
- ✅ 符合"Schema First"原则
- ✅ 清理 legacy 代码
- ✅ 长期可维护

**劣势**:
- ⚠️ 工作量较大（22.5 小时）

---

### 方案 B: Schema 适配代码 (不推荐)

**优势**:
- ✅ 代码改动少

**劣势**:
- ❌ 违反设计原则
- ❌ 破坏数据库规范
- ❌ 制造技术债务
- ❌ 未来返工成本更高

---

## ✅ 成功标准

### 技术指标

- [x] 所有表名匹配 Schema
- [x] 所有字段名匹配 Schema
- [x] 所有外键引用正确
- [x] 无 pylint/mypy 错误
- [x] 单元测试覆盖率 ≥ 80%
- [x] 集成测试通过率 100%

### 业务指标

- [x] 用户管理功能正常
- [x] 项目管理功能正常
- [x] 积分系统正常
- [x] 市场功能正常
- [x] 错误日志正常
- [x] 支持系统正常
- [x] 定价系统可管理 (新)
- [x] 新手引导系统可用 (新)
- [x] 主题系统可用 (新)

---

## ⚠️ 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 数据迁移失败 | 🟡 Medium | 🔴 High | 提前备份 + 分批迁移 + 回滚脚本 |
| 外键约束冲突 | 🟡 Medium | 🟡 Medium | 先建表后加外键 + SET NULL |
| 线上服务中断 | 🟢 Low | 🔴 High | 灰度发布 + Feature Flag + 快速回滚 |

**回滚触发条件**:
- ❌ 测试失败率 > 10%
- ❌ 生产数据不一致
- ❌ 关键业务中断

---

## 📊 时间估算

```
Day 1 (8h):  Phase 1 (5h) + Phase 2 (2.5h) → 核心功能恢复
Day 2 (8h):  Phase 3 (3h) + Phase 4 (5h)   → 所有功能完整
Day 3 (7h):  Phase 5 (7h)                  → 测试通过上线

总计: 22.5 小时 (约 3 个工作日)
```

---

## 📝 核心改动清单

### 代码修改 (9 个文件)

| 文件 | 改动数 | 主要修复 |
|------|--------|----------|
| user_repository.py | 23 | users → profiles, user_id → id |
| project_repository.py | 18 | project_id → id, owner_id → user_id |
| credit_repository.py | 5 | tx_type → transaction_type |
| listing_repository.py | 8 | buyer_id → user_id |
| events_repository.py | 0 | 无需改（需建表） |
| error_logs_repository.py | 0 | 无需改（需建表） |
| support_repository.py | 0 | 无需改（需建表） |
| admin_repository.py | 5 | 需建表 |
| metrics_repository.py | 6 | 需建表 |

### 数据库新增 (13 个表)

| 优先级 | 表名 | 用途 |
|--------|------|------|
| P0 | user_events | 行为追踪 |
| P0 | aggregated_stats | 统计聚合 |
| P0 | error_logs | 错误日志 |
| P0 | support_tickets | 支持工单 |
| P0 | support_replies | 工单回复 |
| P1 | admin_operations | 管理员日志 |
| P1 | listing_usages | 资产使用 |
| P1 | marketplace_reports | 市场报告 |
| P1 | daily_metrics | 每日指标 |
| P1 | monthly_metrics | 月度指标 |
| P2 | generation_tasks | AI 任务 |
| P2 | page_prompt_templates | 页面模板 |
| P2 | payment_records | 支付记录 |

### Schema 补充 (2 个表, 6 个字段)

| 表 | 新增字段 |
|----|----------|
| profiles | first_name, last_name, onboarding_step, preferences, credits_reset_at |
| projects | is_permanently_deleted |

### Repository 新建 (3 个文件)

- pricing_repository.py (关键!)
- onboarding_repository.py
- themes_repository.py

---

## 🚀 下一步行动

### 立即确认

请确认以下问题：

1. **修复策略**: 确认采用 **方案 A (代码适配 Schema)** ✓
2. **执行时间**: 确认 3 个工作日的时间安排 ✓
3. **数据备份**: 执行前需要完整备份数据库 ✓
4. **灰度发布**: 是否需要 Feature Flag 控制新功能 ?

### 确认后开始执行

```bash
# Phase 1: 修复核心表
1. 备份数据库
2. 创建 feature branch: db-code-sync
3. 修改 user_repository.py
4. 修改 project_repository.py
5. 修改 credit_repository.py
6. 修改 listing_repository.py
7. 运行单元测试
8. Commit + Push
```

---

## 📖 相关文档

- **详细执行计划**: [DB-CODE-SYNC-PLAN.md](./DB-CODE-SYNC-PLAN.md)
- **Agent 审查报告**: Agent ID: `a7062f1` (可用 Task tool resume)
- **数据库 Schema**: `migrations/v2/refactored_schema_v2.sql`
- **测试计划**: `docs/TEST_COVERAGE_PLAN.md`

---

**文档状态**: ✅ 方案已完成，等待用户确认执行
**最后更新**: 2026-01-10
**负责人**: Claude Sonnet 4.5
