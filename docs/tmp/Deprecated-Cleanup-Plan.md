# Deprecated 接口清理计划

**日期**: 2026-01-11
**任务**: Phase 4 - Task 7 - 清理 Deprecated 接口
**预计时间**: 2小时

---

## 📊 审计结果总结

### 1. **已注释的旧路由** (app.py) ✅ 无需操作

**状态**: 已删除实现,仅保留注释供参考

**位置**: `app.py:164-290`

**详情**:
- `routers/` 目录已完全删除
- 所有旧路由已迁移至 `api/user/` 和 `api/admin/`
- 注释清晰说明迁移状态

**决策**: ✅ **保留注释** - 有价值的迁移历史记录

---

### 2. **Deprecated API 端点** (3个)

#### 2.1 `POST /users/{uid}/tier` ✅ 保留

**位置**: `api/admin/users.py:223-248`

**状态**: 标记 `deprecated=True`,返回 410 Gone

**实现**:
```python
@router.post("/users/{uid}/tier", deprecated=True)
async def update_user_tier(...):
    """DEPRECATED - REMOVED in v3.26."""
    raise HTTPException(410, detail={
        "error": "Endpoint removed",
        "replacement_endpoint": "PATCH /admin/users/{uid}",
        "migration_guide": "Change from POST to PATCH"
    })
```

**测试**: ✅ 有测试 `test_update_user_tier_deprecated_endpoint()`

**前端调用**: ❌ 无调用

**决策**: ✅ **保留** - 提供明确的迁移指导,帮助旧客户端优雅过渡

---

#### 2.2 `POST /generations/{id}/favorite` ⚠️ 仍在使用

**位置**: `api/user/generations.py:179-215`

**状态**: 标记 `deprecated=True`,但**仍然工作**

**实现**: 调用相同的 Service 方法 (与 `PATCH /generations/{id}` 相同)

**测试**: ✅ 有测试 `test_toggle_favorite_deprecated()`

**前端调用**: ❌ **未发现直接调用**

**决策**: ✅ **保留至 v4.0** - 文档说明 "This endpoint will be removed in v4.0"

---

#### 2.3 `DELETE /generations/batch` ⚠️ 前端仍在使用!

**位置**: `api/user/generations.py:218-245`

**状态**: 标记 `deprecated=True`,但**仍然工作**

**前端调用**: ✅ **发现调用!**
- 文件: `decodables-fe/services/generateService.js:220-226`
- 函数: `clearGenerationHistory(token, keepFavorites)`

```javascript
export const clearGenerationHistory = async (token, keepFavorites = true) => {
  const params = new URLSearchParams({ keep_favorites: keepFavorites.toString() });
  return apiRequest(`/api/generations/batch?${params.toString()}`, {
    method: 'DELETE',
    token,
  });
};
```

**替代接口**: `POST /generations/batch-delete` (已存在)

**决策**: ⚠️ **需要前端迁移!**

**行动计划**:
1. ✅ 保留后端 deprecated 接口 (向后兼容)
2. 🔴 **前端迁移**: 修改 `decodables-fe/services/generateService.js`
3. 🔴 **前端发布**: 确保新前端部署后,再考虑删除后端接口
4. 📅 **时间表**: v4.0 前必须完成前端迁移

---

#### 2.4 `POST /export/zip` ✅ 保留

**位置**: `api/user/export.py:253-297`

**状态**: 标记 `deprecated=True`,但**仍然工作**

**实现**: 调用 `export_service.export_custom_zip()`

**测试**: ✅ 有测试 `TestExportZIPDeprecated`

**前端调用**: ❌ 无调用

**替代接口**: `GET /projects/{project_id}/zip`

**决策**: ✅ **保留至 v4.0** - 文档说明 "This endpoint will be removed in v4.0"

---

### 3. **Deprecated Domain Functions** (4个)

#### 3.1 Experiment CRUD Functions ✅ 可删除

**位置**: `domains/platform/experiments/crud.py:140-170`

**函数**:
- `create_experiment()` - 返回 None,记录错误
- `update_experiment()` - 返回 None,记录错误
- `update_experiment_status()` - 返回 None,记录错误

**调用情况**: ❌ **无外部调用**

**决策**: ✅ **删除** - 这些函数已经失效,不再使用

**操作**:
```python
# 删除 lines 140-170
def create_experiment(...) -> Optional[Dict]: ...
def update_experiment(...) -> Optional[Dict]: ...
def update_experiment_status(...) -> Optional[Dict]: ...
```

---

#### 3.2 `clear_experiment_cache()` ✅ 可删除

**位置**: `domains/platform/experiments/crud.py:210-216`

**实现**: 空函数,仅保留 API 兼容性

**调用情况**: ❌ **无外部调用**

**决策**: ✅ **删除** - 缓存已移除,函数无用

---

### 4. **Backward Compatibility Wrappers** (2个)

#### 4.1 `application/services/capi_service.py` ✅ 可删除

**状态**: Re-export from `application.services.capi`

**调用情况**: ❌ **无调用**

**决策**: ✅ **删除整个文件**

---

#### 4.2 `application/services/ai_report_service.py` ⚠️ 仍在使用

**状态**: Re-export from `application.services.ai_reports`

**调用情况**: ✅ **有调用!**
- 文件: `api/admin/ai.py:278, 326`
- 导入: `from application.services.ai_report_service import ...`

**决策**: ⚠️ **先迁移调用,再删除**

**操作**:
1. 修改 `api/admin/ai.py` 导入路径:
   ```python
   # OLD
   from application.services.ai_report_service import generate_ai_business_report

   # NEW
   from application.services.ai_reports import generate_ai_business_report
   ```
2. 删除 `application/services/ai_report_service.py`

---

### 5. **Deprecated Constants/Aliases**

#### 5.1 `domains/identity/value_objects.py:29`

**内容**: Backward compatibility aliases (已注释)

**决策**: ✅ **保留注释** - 无实际代码

---

#### 5.2 `domains/subscriptions/subscription_service.py:44`

**内容**: Deprecated constants (use domains.identity.constants instead)

**决策**: ✅ **保留注释** - 仅说明性注释

---

#### 5.3 `config.py:57`

**内容**: Trial Period (Legacy - deprecated)

**调用情况**: 需检查

**决策**: ⚠️ **需进一步检查**

---

## ✅ 执行计划

### Phase 1: 安全删除 (无依赖项) - 30 分钟

**文件删除**:
1. ✅ `application/services/capi_service.py` - 无调用

**代码删除**:
1. ✅ `domains/platform/experiments/crud.py:140-170` - 3个失效函数
2. ✅ `domains/platform/experiments/crud.py:210-216` - `clear_experiment_cache()`

**测试验证**:
```bash
python -m pytest tests/domains/platform/ -v
python -m pytest tests/application/ -v
```

---

### Phase 2: 迁移后删除 - 30 分钟

#### 2.1 迁移 `ai_report_service.py` 调用

**修改文件**: `api/admin/ai.py`

**变更**:
```python
# Line 278
- from application.services.ai_report_service import generate_ai_business_report
+ from application.services.ai_reports import generate_ai_business_report

# Line 326
- from application.services.ai_report_service import get_quick_insights
+ from application.services.ai_reports import get_quick_insights
```

**删除文件**: `application/services/ai_report_service.py`

**测试验证**:
```bash
python -m pytest tests/api/admin/test_ai.py -v
```

---

#### 2.2 检查 `config.py` 中的 Trial Period

**位置**: `config.py:57`

**操作**:
1. 搜索 `TRIAL_DURATION_DAYS` 的调用
2. 如果无调用,删除该常量定义

---

### Phase 3: 前端迁移 (跨仓库协作) - 1 小时

**⚠️ 重要**: 此步骤需要前后端协同,不在本次 Phase 4 范围内

**目标**: 迁移 `DELETE /generations/batch` 调用

**前端修改**:
```javascript
// decodables-fe/services/generateService.js:220-226

export const clearGenerationHistory = async (token, keepFavorites = true) => {
  // OLD: DELETE /api/generations/batch
  // NEW: POST /api/v2/user/generations/batch-delete
  return apiRequest(`/api/v2/user/generations/batch-delete`, {
    method: 'POST',
    token,
    body: JSON.stringify({ keep_favorites: keepFavorites }),
    headers: { 'Content-Type': 'application/json' },
  });
};
```

**后端验证**: 确认 `POST /generations/batch-delete` 已存在

**时间表**:
- v3.29: 前端完成迁移并发布
- v4.0: 删除后端 deprecated 接口

---

## 📝 不删除项 (保留原因)

| 项目 | 位置 | 原因 |
|------|------|------|
| `POST /users/{uid}/tier` | `api/admin/users.py:223` | 返回 410 Gone,提供迁移指导 |
| `POST /generations/{id}/favorite` | `api/user/generations.py:179` | 向后兼容,v4.0 前保留 |
| `DELETE /generations/batch` | `api/user/generations.py:218` | **前端仍在使用!** |
| `POST /export/zip` | `api/user/export.py:253` | 向后兼容,v4.0 前保留 |
| `app.py:164-290` 注释 | `app.py` | 迁移历史参考 |
| Deprecated 注释 | 多个文件 | 说明性注释,无实际代码 |

---

## 🎯 成功标准

### 功能测试
- ✅ `pytest tests/domains/platform/` - 所有测试通过
- ✅ `pytest tests/application/` - 所有测试通过
- ✅ `pytest tests/api/admin/test_ai.py` - Admin AI 接口正常

### 回归测试
- ✅ `pytest tests/api/user/test_generations.py` - Generations API 无变化
- ✅ `pytest tests/api/user/test_export.py` - Export API 无变化
- ✅ `pytest tests/api/admin/test_users.py` - Users API 无变化

### 代码质量
- ✅ 无未使用的 import
- ✅ 无孤立的函数定义
- ✅ 文档注释更新

---

## 🔄 回滚策略

### 文件删除回滚
```bash
git restore application/services/capi_service.py
git restore application/services/ai_report_service.py
```

### 代码删除回滚
```bash
git diff HEAD domains/platform/experiments/crud.py
git checkout HEAD -- domains/platform/experiments/crud.py
```

---

**预计总时间**: 1.5 小时 (不含前端迁移)

**风险等级**: 🟢 LOW
- Phase 1/2: 删除无依赖的代码,风险极低
- Phase 3: 需前端配合,暂不执行

---

**执行者**: Claude Code
**审核者**: 用户确认
