# Experiments 模块完整 Review 报告 v1.0.0

**Review Date**: 2026-01-10
**Module**: Experiments (4 interfaces)
**Reviewer**: Claude Code

---

## 模块概览

**文件清单**:
```
api/user/experiments.py                         (149 lines) - API 层
domains/platform/experiments/__init__.py        (62 lines) - Package 导出
domains/platform/experiments/assignment.py      (151 lines) - 分配逻辑
domains/platform/experiments/tracking.py        (127 lines) - 曝光/转化追踪
domains/platform/experiments/crud.py            (~300 lines) - CRUD 操作
domains/platform/experiments/analysis.py        (~200 lines) - 结果分析
```

**接口清单** (4 个):
1. `POST /api/v2/user/experiments/{key}/assign` - 分配变体
2. `POST /api/v2/user/experiments/{key}/exposure` - 追踪曝光
3. `POST /api/v2/user/experiments/{key}/conversion` - 追踪转化
4. `GET /api/v2/user/experiments/user/{identifier}` - 获取用户实验

---

## 调用链分析

### 1. POST /{key}/assign - 分配变体

**完整调用链**:
```
API: assign_variant() [experiments.py:74-100]
  ├─ AssignmentRequest (Pydantic validation)
  └─ experiment_service.assign_variant() [assignment.py:19-84]
      ├─ get_experiment(experiment_key) [crud.py:75-95]
      │   └─ Repository.get_by_key() → DB Query
      ├─ _check_targeting() [assignment.py:87-114]
      │   └─ 业务逻辑: 检查用户资格 (tiers, include/exclude lists)
      ├─ DB: SELECT variant_key FROM experiment_assignments
      │       WHERE experiment_id=? AND user_identifier=?
      ├─ calculate_variant() [core.py] - 哈希计算
      └─ DB: UPSERT INTO experiment_assignments
             (experiment_id, experiment_key, user_identifier, variant_key)
             ON CONFLICT (experiment_id, user_identifier) DO UPDATE
```

**上游依赖**:
- ✅ 无认证 (公开接口, 支持匿名用户)
- ✅ Pydantic validation
- ✅ Database schema - `experiments`, `experiment_assignments` 表

**下游影响**:
- ✅ 返回 variant key 或 None
- ✅ 幂等性 - UPSERT 保证同一用户总是得到相同变体

---

### 2. POST /{key}/exposure - 追踪曝光

**完整调用链**:
```
API: track_exposure() [experiments.py:103-118]
  ├─ ExposureRequest (Pydantic validation)
  └─ experiment_service.track_exposure() [tracking.py:15-63]
      ├─ get_experiment(experiment_key) [crud.py:75-95]
      ├─ DB: SELECT id FROM experiment_exposures
      │       WHERE experiment_key=? AND user_identifier=?
      │       AND created_at >= (NOW - 1 hour)  -- 去重
      └─ DB: INSERT INTO experiment_exposures
             (experiment_id, experiment_key, user_identifier, variant_key, context)
```

**上游依赖**:
- ✅ 无认证
- ✅ 1 小时去重窗口

**下游影响**:
- ✅ 返回 success boolean
- ✅ 记录曝光事件

---

### 3. POST /{key}/conversion - 追踪转化

**完整调用链**:
```
API: track_conversion() [experiments.py:121-137]
  ├─ ConversionRequest (Pydantic validation)
  └─ experiment_service.track_conversion() [tracking.py:66-119]
      ├─ get_experiment(experiment_key) [crud.py:75-95]
      ├─ DB: SELECT variant_key FROM experiment_assignments
      │       WHERE experiment_key=? AND user_identifier=?
      └─ DB: INSERT INTO experiment_conversions
             (experiment_id, experiment_key, user_identifier, variant_key, metric_key, value, metadata)
```

**上游依赖**:
- ✅ 无认证
- ✅ 需要先 assign variant (查询 experiment_assignments)

**下游影响**:
- ✅ 返回 success boolean
- ✅ 记录转化事件

---

### 4. GET /user/{identifier} - 获取用户实验

**完整调用链**:
```
API: get_user_experiments() [experiments.py:140-148]
  └─ experiment_service.get_user_experiments() [assignment.py:136-150]
      └─ DB: SELECT experiment_key, variant_key, created_at
             FROM experiment_assignments
             WHERE user_identifier=?
```

**上游依赖**:
- ✅ 无认证
- ✅ 简单查询

**下游影响**:
- ✅ 返回实验列表

---

## 数据库验证

### Schema 检查

**experiments 表** (✅ 存在):
```sql
CREATE TABLE experiments (
    id UUID PRIMARY KEY,
    experiment_key TEXT UNIQUE NOT NULL,
    experiment_name TEXT NOT NULL,
    description TEXT,
    hypothesis TEXT,
    variants JSONB NOT NULL,
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'paused', 'completed')),
    traffic_percentage INTEGER DEFAULT 100,
    target_tiers TEXT[] DEFAULT ARRAY[]::TEXT[],
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

**⚠️ 发现问题 #EXP-HIGH-6**: **status 枚举值不匹配**

**数据库定义**:
```sql
CHECK (status IN ('draft', 'active', 'paused', 'completed'))
```

**代码中使用**:
```python
# assignment.py:44-45
if experiment.get('status') != 'running':  # ← 'running' 不在数据库枚举中
    return None
```

**冲突分析**:
- 数据库允许: `draft`, `active`, `paused`, `completed`
- 代码检查: `running` (不存在)
- **Mismatch!**

**影响**:
- 🔴 **P0 Bug**: 所有 status='active' 的实验无法分配变体 (因为 != 'running')
- 用户无法参与任何实验

---

**experiment_assignments 表** (✅ 存在, 但字段名不匹配):
```sql
CREATE TABLE experiment_assignments (
    id UUID PRIMARY KEY,
    experiment_id UUID NOT NULL REFERENCES experiments(id),
    user_id TEXT NOT NULL REFERENCES profiles(id),  -- ← 数据库字段名
    variant_key TEXT NOT NULL,
    assigned_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(experiment_id, user_id)
);
```

**⚠️ 发现问题 #EXP-HIGH-7**: **字段名不匹配 - user_id vs user_identifier**

**代码中使用**:
```python
# assignment.py:54-56, 71-79
supabase.table("experiment_assignments").select("variant_key")\
    .eq("experiment_id", experiment.get('id'))\
    .eq("user_identifier", user_identifier).execute()  # ← 数据库中是 'user_id'

supabase.table("experiment_assignments").upsert({
    "experiment_id": experiment.get('id'),
    "experiment_key": experiment_key,
    "user_identifier": user_identifier,  # ← 数据库中是 'user_id'
    "variant_key": variant_key,
    ...
})
```

**影响**:
- 🔴 **P0 Bug**: 所有查询会失败 (字段不存在)
- 所有 upsert 会失败 (字段不存在)
- 用户无法分配变体

---

**UNIQUE constraint 不匹配**:
```sql
UNIQUE(experiment_id, user_id)  -- 数据库定义
```

```python
# assignment.py:79
on_conflict="experiment_id,user_identifier"  # ← 代码中使用
```

**影响**:
- 🔴 **P0 Bug**: UPSERT 的 on_conflict 不会生效 (字段名错误)
- 可能导致重复插入或错误

---

## 发现的问题汇总

### 🔴 P0 - 关键 Bug (阻塞功能)

#### #EXP-HIGH-6: experiment.status 枚举值不匹配 (P0)

**位置**: `assignment.py:44-45`

**问题描述**:
- 数据库 CHECK: `('draft', 'active', 'paused', 'completed')`
- 代码检查: `status != 'running'`
- **完全不匹配**, 导致所有实验无法分配变体

**受影响代码**:
```python
# assignment.py:44-45
if experiment.get('status') != 'running':
    return None
```

**修复建议**: `'running'` → `'active'`

---

#### #EXP-HIGH-7: 字段名不匹配 - user_id vs user_identifier (P0)

**位置**: `assignment.py:54-56, 71-79` + `tracking.py:95-97, 123-125`

**问题描述**:
- 数据库字段: `user_id` (引用 profiles.id)
- 代码使用: `user_identifier` (不存在的字段)
- 导致所有查询/插入失败

**受影响代码**:
```python
# assignment.py:54-56
existing = supabase.table("experiment_assignments").select("variant_key")\
    .eq("experiment_id", experiment.get('id'))\
    .eq("user_identifier", user_identifier).execute()  # ← 错误字段名

# assignment.py:71-79
supabase.table("experiment_assignments").upsert({
    "experiment_id": experiment.get('id'),
    "experiment_key": experiment_key,
    "user_identifier": user_identifier,  # ← 错误字段名
    "variant_key": variant_key,
    ...
}, on_conflict="experiment_id,user_identifier")  # ← 错误 UNIQUE 约束

# tracking.py:95-97
assignment = supabase.table("experiment_assignments").select("variant_key")\
    .eq("experiment_key", experiment_key)\
    .eq("user_identifier", user_identifier).execute()  # ← 错误字段名

# assignment.py:123-125 (get_user_variant)
result = supabase.table("experiment_assignments").select("variant_key")\
    .eq("experiment_key", experiment_key)\
    .eq("user_identifier", user_identifier).execute()  # ← 错误字段名

# assignment.py:142-144 (get_user_experiments)
result = supabase.table("experiment_assignments").select(...)\
    .eq("user_identifier", user_identifier).execute()  # ← 错误字段名
```

**修复建议**: 全局替换 `user_identifier` → `user_id` (在 database queries 中)

---

### ✅ 已修复问题

#### #EXP-HIGH-5: list_experiments() 返回类型不匹配 - 已修复 ✅

**位置**: `analysis.py:38-39` (v3.28)

**修复前**:
```python
# analysis.py (before v3.28)
result = list_experiments(status="running")
experiments = result.get("items", [])  # ← BUG: result 是 tuple
```

**修复后**:
```python
# analysis.py:38-39 (v3.28)
# v3.28: EXP-HIGH-5 - Fixed tuple unpacking (list_experiments now returns tuple)
experiments, _ = list_experiments(status="running")
```

**验证**: ✅ 已正确修复

---

### 🟡 P2 - 中等优先级 (代码质量)

#### #EXP-LOW-1: experiment_key 字段冗余存储 (P2)

**位置**: `assignment.py:74`, `tracking.py:53, 107`

**问题描述**:
```python
# experiment_assignments 表同时存储 experiment_id + experiment_key
supabase.table("experiment_assignments").upsert({
    "experiment_id": experiment.get('id'),
    "experiment_key": experiment_key,  # ← 冗余字段 (可通过 JOIN 获取)
    ...
})
```

**数据库 Schema**:
- `experiment_assignments` 表只有 `experiment_id` 字段
- 代码尝试插入不存在的 `experiment_key` 字段

**影响**:
- 🟠 可能导致插入失败 (字段不存在)
- 或者被数据库忽略 (取决于 ORM 行为)

**修复建议**: 移除冗余的 `experiment_key` 字段

---

#### #EXP-LOW-2: 异常处理过于宽泛 (P2)

**位置**: `assignment.py:60-61, 81-82`, `tracking.py:61-63, 117-119`

**问题描述**:
```python
# assignment.py:60-61
except Exception as e:
    logger.debug(f"[Assignment] Failed to check existing assignment: {e}")
    # ← 吞噬异常, 继续执行 (可能导致重复分配)

# assignment.py:81-82
except Exception as e:
    logger.warning(f"[Assignment] Upsert failed: {e}")
    # ← 吞噬异常, 但仍返回 variant_key (数据库中可能未保存)
```

**影响**:
- 数据库错误时, 继续执行或返回错误结果
- 难以排查问题

**修复建议**: 区分预期异常 vs 意外异常, 并正确处理

---

### 🟢 P3 - 低优先级 (优化建议)

#### #EXP-OPT-1: DDD Migration 未完全完成 (P3)

**位置**: `assignment.py`, `tracking.py`

**问题描述**:
- `crud.py` 已迁移到 Repository 模式 (v3.28)
- 但 `assignment.py`, `tracking.py` 仍直接使用 Supabase client
- 架构不一致

**建议**: 创建 AssignmentService + TrackingService, 统一使用 Repository

---

## 优先级统计

| 优先级 | 数量 | 问题 ID |
|--------|------|---------|
| 🔴 P0 | 2 | EXP-HIGH-6, EXP-HIGH-7 |
| 🟠 P1 | 0 | - |
| 🟡 P2 | 2 | EXP-LOW-1, EXP-LOW-2 |
| 🟢 P3 | 1 | EXP-OPT-1 |
| ✅ 已修复 | 1 | EXP-HIGH-5 (v3.28) |
| **Total** | **6** | |

---

## 测试覆盖验证

**测试文件位置**: `tests/api/user/test_experiments.py` (待检查)

**需要覆盖的场景**:
1. ✅ POST /assign - 首次分配 + 重复分配 (幂等性)
2. ✅ POST /exposure - 曝光追踪 + 1小时去重
3. ✅ POST /conversion - 转化追踪 + 查询 variant
4. ✅ GET /user/{id} - 获取用户实验列表
5. ❌ status='active' 实验可正常分配
6. ❌ user_id 字段正确使用
7. ❌ UPSERT on_conflict 正确处理

**测试覆盖率评估**: 待补充测试代码后分析

---

## 向后兼容性分析

### Breaking Changes 风险

1. **#EXP-HIGH-6 修复 (status 枚举值)**:
   - ⚠️ 如果数据库中有 status='running' 的实验, 需要迁移为 'active'
   - 建议: 数据迁移脚本

2. **#EXP-HIGH-7 修复 (字段名)**:
   - ⚠️ 如果已有数据使用 'user_identifier' 字段, 需要检查
   - 根据 schema, 数据库只有 'user_id', 所以代码是错误的

---

## 修复建议优先级

**立即修复 (P0)**:
1. ✅ #EXP-HIGH-7: user_identifier → user_id (5 处代码)
2. ✅ #EXP-HIGH-6: 'running' → 'active' (1 处代码)

**短期优化 (P2)**:
3. ⏳ #EXP-LOW-1: 移除冗余 experiment_key 字段
4. ⏳ #EXP-LOW-2: 优化异常处理

**长期优化 (P3)**:
5. ⏳ #EXP-OPT-1: 完成 DDD 迁移 (Assignment + Tracking Service)

---

## 下一步行动

1. ✅ **立即修复 P0 问题** (阻塞功能)
2. ⏳ 添加测试用例覆盖字段名修正
3. ⏳ 数据迁移脚本 (如果需要)
4. ✅ 继续 Review 剩余 19 个模块

---

**Review Status**: ✅ **完成** (发现 6 个问题, 需修复 2 个 P0, 1 个已修复)
