# Experiments P0 问题修复报告 v1.0.0

**Fix Date**: 2026-01-10
**Module**: Experiments
**Previous Version**: v3.25 (assignment), v3.24 (tracking)
**New Version**: v3.26 (assignment), v3.25 (tracking)

---

## 修复概述

修复了 Experiments 模块 Review 中发现的 **2 个 P0 关键问题** + 顺带修复 **1 个 P2 问题**。

**问题来源**: `EXPERIMENTS-FULL-REVIEW-v1.0.0.md`

---

## 修复清单

### ✅ #EXP-HIGH-6: experiment.status 枚举值不匹配 (P0)

**问题描述**:
- 数据库 CHECK 约束: `('draft', 'active', 'paused', 'completed')`
- 代码检查: `status != 'running'` (不存在的值)
- **完全不匹配**, 导致所有实验无法分配变体

**受影响代码**:
```python
# assignment.py:44-45 (before)
if experiment.get('status') != 'running':  # ← 'running' not in database enum
    return None
```

**修复后**:
```python
# assignment.py:44-46 (after)
# Check if experiment is running
# EXP-HIGH-6 FIX: Database uses 'active', not 'running'
if experiment.get('status') != 'active':
    return None
```

**影响**: 🔴 极高 → ✅ 已解决
**变更**: `assignment.py` (+2/-1)

---

### ✅ #EXP-HIGH-7: 字段名不匹配 - user_id vs user_identifier (P0)

**问题描述**:
- 数据库字段: `user_id` (experiment_assignments 表)
- 代码使用: `user_identifier` (不存在的字段)
- 导致所有查询/插入失败

**受影响代码 (6 处)**:

#### 1. assignment.py:56-58 - 查询已有分配
```python
# Before
existing = supabase.table("experiment_assignments").select("variant_key")\
    .eq("experiment_id", experiment.get('id'))\
    .eq("user_identifier", user_identifier).execute()  # ← Wrong field

# After
# EXP-HIGH-7 FIX: Database field is 'user_id', not 'user_identifier'
existing = supabase.table("experiment_assignments").select("variant_key")\
    .eq("experiment_id", experiment.get('id'))\
    .eq("user_id", user_identifier).execute()
```

#### 2. assignment.py:75-84 - UPSERT 分配记录
```python
# Before
supabase.table("experiment_assignments").upsert({
    "experiment_id": experiment.get('id'),
    "experiment_key": experiment_key,  # ← Not in schema (EXP-LOW-1)
    "user_identifier": user_identifier,  # ← Wrong field
    "variant_key": variant_key,
    "user_properties": user_properties or {},  # ← Not in schema
}, on_conflict="experiment_id,user_identifier")  # ← Wrong constraint

# After
# EXP-HIGH-7 FIX: Database field is 'user_id', not 'user_identifier'
# EXP-LOW-1 FIX: Remove redundant 'experiment_key' (not in schema)
supabase.table("experiment_assignments").upsert({
    "experiment_id": experiment.get('id'),
    "user_id": user_identifier,
    "variant_key": variant_key,
    # Note: user_properties field doesn't exist in database schema
    # Removed to match actual schema
}, on_conflict="experiment_id,user_id")
```

#### 3. assignment.py:127-133 - get_user_variant()
```python
# Before
result = supabase.table("experiment_assignments").select("variant_key")\
    .eq("experiment_key", experiment_key)\  # ← experiment_key not in this table
    .eq("user_identifier", user_identifier).execute()

# After
# EXP-HIGH-7 FIX: Database field is 'user_id', not 'user_identifier'
# Need to join with experiments table to filter by experiment_key
result = supabase.table("experiment_assignments").select(
    "variant_key, experiments!inner(experiment_key)"
).eq("experiments.experiment_key", experiment_key).eq(
    "user_id", user_identifier
).execute()
```

#### 4. assignment.py:152-154 - get_user_experiments()
```python
# Before
result = supabase.table("experiment_assignments").select(
    "experiment_key, variant_key, created_at"  # ← experiment_key not in this table
).eq("user_identifier", user_identifier).execute()

# After
# EXP-HIGH-7 FIX: Database field is 'user_id', not 'user_identifier'
# Join with experiments table to get experiment_key
result = supabase.table("experiment_assignments").select(
    "variant_key, assigned_at, experiments!inner(experiment_key)"
).eq("user_id", user_identifier).execute()

# Flatten the nested structure
experiments = []
for row in (result.data or []):
    experiments.append({
        "experiment_key": row.get("experiments", {}).get("experiment_key"),
        "variant_key": row.get("variant_key"),
        "created_at": row.get("assigned_at")  # Note: field is 'assigned_at' in schema
    })
return experiments
```

#### 5. tracking.py:97-101 - track_conversion() 查询分配
```python
# Before
assignment = supabase.table("experiment_assignments").select("variant_key")\
    .eq("experiment_key", experiment_key)\  # ← experiment_key not in this table
    .eq("user_identifier", user_identifier).execute()

# After
# EXP-HIGH-7 FIX: Database field is 'user_id', not 'user_identifier'
# Need to join with experiments table to filter by experiment_key
assignment = supabase.table("experiment_assignments").select(
    "variant_key, experiments!inner(experiment_key)"
).eq("experiments.experiment_key", experiment_key).eq(
    "user_id", user_identifier
).execute()
```

**数据库 Schema**:
```sql
CREATE TABLE experiment_assignments (
    id UUID PRIMARY KEY,
    experiment_id UUID NOT NULL REFERENCES experiments(id),
    user_id TEXT NOT NULL REFERENCES profiles(id),  -- ← Correct field name
    variant_key TEXT NOT NULL,
    assigned_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(experiment_id, user_id)
);
```

**影响**: 🔴 极高 → ✅ 已解决
**变更**: `assignment.py` (+35/-17), `tracking.py` (+7/-3)

---

### ✅ #EXP-LOW-1: 移除冗余字段 (P2 - 顺带修复)

**问题描述**:
- UPSERT 时插入了不存在的字段 `experiment_key`, `user_properties`
- 数据库 schema 中没有这些字段

**修复**: 移除不存在的字段 (见上 #EXP-HIGH-7 修复)

---

## 代码变更统计

| 文件 | 行数变化 | 说明 |
|------|----------|------|
| `assignment.py` | +37 / -18 | status 枚举值 + user_id 字段名 + JOIN 查询 |
| `tracking.py` | +7 / -3 | user_id 字段名 + JOIN 查询 |

**总变更**: +44 / -21 (净增加 23 行)

---

## 向后兼容性

### ⚠️ Breaking Changes

1. **#EXP-HIGH-6 修复 (status 枚举值)**:
   - ⚠️ 如果数据库中有 status='running' 的实验, 需要迁移为 'active'
   - 建议数据迁移:
   ```sql
   UPDATE experiments SET status='active' WHERE status='running';
   ```
   - 但根据 schema CHECK 约束, 不应该有 'running' 值存在

2. **#EXP-HIGH-7 修复 (字段名)**:
   - ✅ **无 Breaking Change**
   - 修正了代码错误, 匹配数据库 schema
   - 之前的代码无法运行, 修复后才能正常工作

---

## 测试验证

### 需要添加的测试

**文件**: `tests/api/user/test_experiments.py`

#### 1. Test #EXP-HIGH-6: status='active' 实验可分配

```python
async def test_assign_variant_with_active_experiment():
    """
    Test: Active experiments can assign variants

    Given: Experiment with status='active'
    When: POST /experiments/{key}/assign
    Then: Variant assigned successfully
    """
    # Create experiment with status='active'
    experiment = await create_test_experiment(status="active")

    response = client.post(
        f"/api/v2/user/experiments/{experiment['experiment_key']}/assign",
        json={"user_identifier": "test_user_123"}
    )

    assert response.status_code == 200
    assert response.json()["assigned"] is True
    assert response.json()["variant"] is not None
```

#### 2. Test #EXP-HIGH-7: user_id 字段正确使用

```python
async def test_assignment_uses_correct_user_id_field():
    """
    Test: Assignments stored with correct user_id field

    Given: User assignment
    When: POST /experiments/{key}/assign
    Then: Assignment stored in database with user_id field
    """
    experiment = await create_test_experiment()
    user_id = "test_user_456"

    response = client.post(
        f"/api/v2/user/experiments/{experiment['experiment_key']}/assign",
        json={"user_identifier": user_id}
    )

    assert response.status_code == 200

    # Verify in database
    result = supabase.table("experiment_assignments").select("*").eq(
        "experiment_id", experiment["id"]
    ).eq("user_id", user_id).execute()

    assert len(result.data) == 1
    assert result.data[0]["user_id"] == user_id
```

#### 3. Test: get_user_experiments() 返回正确数据

```python
async def test_get_user_experiments_returns_correct_data():
    """
    Test: get_user_experiments returns experiments with correct structure
    """
    experiment = await create_test_experiment()
    user_id = "test_user_789"

    # Assign variant
    client.post(
        f"/api/v2/user/experiments/{experiment['experiment_key']}/assign",
        json={"user_identifier": user_id}
    )

    # Get user experiments
    response = client.get(f"/api/v2/user/experiments/user/{user_id}")

    assert response.status_code == 200
    experiments = response.json()["experiments"]
    assert len(experiments) > 0
    assert experiments[0]["experiment_key"] == experiment["experiment_key"]
    assert "variant_key" in experiments[0]
    assert "created_at" in experiments[0]
```

---

## 数据库 Schema 说明

### experiment_assignments 表字段

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| experiment_id | UUID | 实验 ID (FK → experiments.id) |
| user_id | TEXT | 用户 ID (FK → profiles.id) ✅ |
| variant_key | TEXT | 变体键 |
| assigned_at | TIMESTAMPTZ | 分配时间 ✅ |

**注意**:
- ❌ `experiment_key` - 不在 schema 中, 通过 JOIN 获取
- ❌ `user_identifier` - 不在 schema 中, 正确字段是 `user_id`
- ❌ `user_properties` - 不在 schema 中
- ✅ `assigned_at` - schema 中的字段名 (不是 `created_at`)

### UNIQUE 约束

```sql
UNIQUE(experiment_id, user_id)  -- ← 正确的约束
```

**UPSERT on_conflict 参数**:
```python
on_conflict="experiment_id,user_id"  # ✅ Correct
```

---

## JOIN 查询说明

由于 `experiment_assignments` 表不存储 `experiment_key`, 需要通过 JOIN 获取:

```python
# Supabase PostgREST JOIN syntax
supabase.table("experiment_assignments").select(
    "variant_key, experiments!inner(experiment_key)"
).eq("experiments.experiment_key", "my_experiment").execute()

# SQL equivalent:
SELECT ea.variant_key, e.experiment_key
FROM experiment_assignments ea
INNER JOIN experiments e ON ea.experiment_id = e.id
WHERE e.experiment_key = 'my_experiment';
```

---

## 下一步行动

1. ✅ **修复完成** (2 个 P0 + 1 个 P2 问题)
2. ⏳ **添加测试用例** (3 个测试场景)
3. ⏳ **数据验证** (检查是否有 status='running' 的实验)
4. ✅ **继续 Review 剩余 19 个模块**

---

## Git Commit 建议

```bash
# Commit message
fix(experiments): align code with database schema - P0 fixes

- #EXP-HIGH-6: Fix experiment.status enum mismatch
  Database uses 'active', not 'running'
  Experiments with status='active' can now assign variants correctly

- #EXP-HIGH-7: Fix field name mismatch (user_identifier → user_id)
  Database field is 'user_id', not 'user_identifier'
  Fixed 6 query locations in assignment.py and tracking.py
  Added JOIN with experiments table to get experiment_key

- #EXP-LOW-1: Remove redundant fields from UPSERT
  Removed 'experiment_key' and 'user_properties' (not in schema)
  Match actual database schema

Database schema reference:
- experiment_assignments table has: experiment_id, user_id, variant_key, assigned_at
- UNIQUE constraint: (experiment_id, user_id)

Related: EXPERIMENTS-FULL-REVIEW-v1.0.0.md
```

---

**Status**: ✅ **修复完成** (2/2 P0 问题已修复, 1 个 P2 顺带修复)
**Next**: 添加测试用例 + 继续 Review 剩余模块
