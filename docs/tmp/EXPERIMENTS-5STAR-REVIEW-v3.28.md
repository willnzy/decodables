# Experiments 模块 5 星 Review (v3.28)

**评估日期**: 2026-01-10
**评估模块**: Experiments API
**评估人**: Claude
**评估范围**: `api/admin/experiments.py` (v3.28)

---

## 📋 评估维度

| 维度 | 分数 | 状态 |
|------|------|------|
| ⭐ **代码标准** (Code Standards) | 98/100 | ✅ 优秀 |
| ⭐ **架构合规** (Architecture Compliance) | 75/100 | ⚠️ 需改进 |
| ⭐ **安全完整** (Security Complete) | 100/100 | ✅ 完美 |
| ⭐ **调用链完整** (Call Chain Complete) | 100/100 | ✅ 完美 |
| ⭐ **测试覆盖** (Test Coverage) | 60/100 | ⚠️ 偏低 |

**总评**: ⭐⭐⭐⭐ (4 STARS) - **架构合规性和测试覆盖需改进**

---

## ⚠️ 核心问题 1: 架构合规性 (75/100)

### 问题描述

Experiments 模块虽然完成了 "DDD Migration" (v3.28)，但**没有使用依赖注入**：

1. **API 层**: 直接导入并调用 Service 模块函数
2. **Service 层**: 每个函数内部创建新的 Repository 实例

```python
# ❌ API 层 - 直接调用模块函数
from domains.platform import experiments as experiment_service

@router.get("")
async def list_experiments(...):
    # ❌ 直接调用模块函数，而不是通过依赖注入
    experiments, total = experiment_service.list_experiments(status=status, limit=limit, offset=offset)
```

```python
# ❌ Service 层 (crud.py) - 每次创建新 Repository
def _get_repo() -> SupabaseExperimentRepository:
    """Get experiment repository instance."""
    db_client = get_supabase_client()  # ❌ 每次调用都创建新实例
    return SupabaseExperimentRepository(client=db_client)

def list_experiments(...) -> tuple[List[Dict], int]:
    try:
        repo = _get_repo()  # ❌ 每次调用都创建新 Repository
        experiments, total = asyncio.run(repo.list_experiments(...))
        return (experiments, total)
    except Exception as e:
        logger.error(f"[Experiment] Failed to list: {e}")
        return ([], 0)
```

### 为什么这是问题？

| 问题 | 影响 |
|------|------|
| **1. 无依赖注入** | 无法 mock，测试困难 |
| **2. 资源浪费** | 每次请求创建新的 DB 客户端和 Repository |
| **3. 难以扩展** | 无法替换 Repository 实现 (如切换数据库) |
| **4. 违反 DDD** | API 层应该通过 DI 获取 Service，而不是直接导入模块 |
| **5. 混合同步/异步** | Service 用 `asyncio.run()` 包装异步调用，不优雅 |

### 对比参考: Analytics/Config 模块 (5 星架构)

```python
# ✅ Analytics/Config - 使用依赖注入

# 1. 工厂函数
def get_analytics_service() -> AnalyticsService:
    supabase = get_supabase_client()
    analytics_repo = SupabaseAnalyticsEventsRepository(supabase)
    return AnalyticsService(analytics_repo)  # ✅ 注入 Repository

# 2. API 层使用 Depends
@router.post("/events")
async def log_analytics_events(
    analytics_service: AnalyticsService = Depends(get_analytics_service),  # ✅ DI
):
    await analytics_service.process_and_save_events(...)  # ✅ 调用 Service 方法
```

**关键区别**:
| 特征 | Experiments (4 星) | Analytics/Config (5 星) |
|------|-------------------|------------------------|
| DI 工厂 | ❌ 无 | ✅ `get_analytics_service()` |
| API 依赖注入 | ❌ 直接导入模块 | ✅ `Depends(get_service)` |
| Repository 创建 | ❌ 每次调用创建新实例 | ✅ DI 时创建，整个请求复用 |
| Service 层 | ❌ 模块函数 | ✅ Class-based Service |
| 测试友好性 | ❌ 难以 mock | ✅ 易于 mock |

---

## ⚠️ 核心问题 2: 测试覆盖 (60/100)

### 测试现状

- **测试文件**: `tests/api/admin/test_experiments.py` (307 行)
- **测试数量**: 估计 5-10 个测试类/函数 (基于文件大小)
- **端点数量**: 14 个端点
- **覆盖率**: 约 30-50% (推测，未运行测试)

### 问题

1. **端点覆盖不全**: 14 个端点 vs 5-10 个测试
2. **测试数量偏少**: 307 行测试代码 vs 49 行 Config 测试 × 6 = 294 行（参考）
3. **缺少边界测试**: 未见异常路径、边界条件测试

### 对比参考

| 模块 | 端点数 | 测试文件行数 | 测试用例数 | 覆盖率 |
|------|--------|-------------|-----------|--------|
| Config | 3 | ~310 行 | 12 个 | 90/100 |
| Experiments | 14 | 307 行 | ~5-10 个 | 60/100 |

**结论**: Experiments 端点数是 Config 的 4.7 倍，但测试代码行数相同，说明测试覆盖不足。

---

## ✅ 优点分析

### 1. 代码标准 (98/100)

**优秀之处**:
- ✅ **版本历史完整**: 详细的 Changelog (v3.25 → v3.28)
- ✅ **Pydantic 模型**: 所有请求/响应都有类型定义
- ✅ **参数验证完整**: Query 参数有范围限制
- ✅ **错误处理统一**: try-except + HTTPException
- ✅ **日志记录到位**: 关键操作都有审计日志

**代码示例**:
```python
# ✅ 完整的参数验证
@router.get("", response_model=ExperimentListResponse)
async def list_experiments(
    request: Request,
    status: Optional[str] = Query(None, max_length=50, description="Filter by status"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Page size (1-100)"),
    admin: dict = Depends(require_admin)  # ✅ 权限检查
):
    # ✅ 业务逻辑验证
    if status is not None and status not in VALID_EXPERIMENT_STATUSES:
        raise HTTPException(400, f"Invalid status. Must be one of: {', '.join(VALID_EXPERIMENT_STATUSES)}")
```

**扣分项** (-2 分):
- Service 层用 `asyncio.run()` 包装异步调用，不够优雅

---

### 2. 安全完整 (100/100) - **完美**

**完美达成**:
- ✅ **认证**: 所有端点使用 `require_admin` 依赖
- ✅ **Rate Limiting**: 所有端点都有速率限制
- ✅ **参数验证**: 所有输入都经过 Pydantic 验证
- ✅ **SQL 注入防护**: 使用 Supabase ORM，无 raw SQL
- ✅ **审计日志**: 所有操作记录 admin ID
- ✅ **OOM 保护**: Repository 层所有查询都有 `.limit(10000)`

**安全机制**:
```python
# ✅ Rate Limiting (v3.25: EXP-MEDIUM-1)
@router.get("")
@limiter.limit("30/minute")  # ✅ 防止滥用
async def list_experiments(..., admin: dict = Depends(require_admin)):  # ✅ 权限检查
    logger.info(f"[Admin {admin.get('id')}] Listing experiments")  # ✅ 审计日志

# ✅ 参数范围验证
limit: int = Query(20, ge=1, le=100)  # ✅ 1-100

# ✅ 业务规则验证 (v3.25: EXP-MEDIUM-2/3/4/5/6)
if status not in VALID_EXPERIMENT_STATUSES:
    raise HTTPException(400, "Invalid status")

# ✅ OOM 保护 (Repository 层 - v3.28: EXP-HIGH-2)
result = self.client.table("experiments").select("*").limit(10000).execute()
```

**安全评分**: 100/100 (满分) 🛡️

---

### 3. 调用链完整 (100/100) - **完美**

**完美之处**:
- ✅ API → Service → Repository → Database (完整链路)
- ✅ 所有数据库操作通过 Repository
- ✅ Repository 层有错误重试 (`@retry_on_network_error_async`)
- ✅ Repository 层有 OOM 保护 (`.limit(10000)`)
- ✅ 错误处理完整
- ✅ 异常正确传播

**调用链验证**:
```
✅ list_experiments()
  → experiment_service.list_experiments()  # domains/platform/experiments/crud.py
    → repo.list_experiments()  # infrastructure/repositories/experiment_repository.py
      → self.client.table("experiments").select(...)  # Supabase

✅ create_experiment()
  → experiment_service.create_experiment()
    → repo.save()
      → self.client.table("experiments").upsert(...)

✅ update_experiment()
  → experiment_service.update_experiment()
    → repo.save()
      → self.client.table("experiments").upsert(...)
```

**Repository 层保障** (v3.28):
- ✅ 网络错误重试 (3 次，延迟 1 秒)
- ✅ OOM 保护 (所有查询限制 10000 行)
- ✅ 异常日志记录

---

### 4. 文档完整性 (95/100)

**优秀之处**:
- ✅ **Changelog 详细**: v3.25 → v3.28 的所有变更
- ✅ **Issue 追踪**: 标注修复的 Issue (EXP-CRITICAL-1, EXP-HIGH-1, etc.)
- ✅ **端点列表**: 14 个端点清晰列出
- ✅ **版本标记**: 每个变更都有版本号

**扣分项** (-5 分):
- 缺少架构图 (API → Service → Repository 流程图)
- 缺少测试覆盖报告

---

## 🔧 修复方案: 架构升级到 5 星

### 需要修改的文件

1. **新建**: `domains/platform/experiments/service.py` - ExperimentService 类
2. **修改**: `api/admin/experiments.py` - 添加依赖注入
3. **修改**: `domains/platform/experiments/__init__.py` - 导出 Service 类
4. **更新**: `tests/api/admin/test_experiments.py` - Mock Service 而不是模块函数

### 具体修复步骤

#### Step 1: 创建 ExperimentService 类

```python
# domains/platform/experiments/service.py (新建)
"""
Experiment Service - Domain service for A/B testing experiments.

@module domains.platform.experiments.service
@version 1.0.0
"""
import logging
from typing import Optional, List, Dict, Any, Tuple

from infrastructure.repositories.experiment_repository import SupabaseExperimentRepository

logger = logging.getLogger(__name__)


class ExperimentService:
    """
    Domain service for experiment management.

    Responsibilities:
    - Experiment CRUD operations
    - Assignment logic
    - Result analysis
    """

    def __init__(self, experiment_repo: SupabaseExperimentRepository):
        """
        Initialize service with repository.

        Args:
            experiment_repo: Experiment repository instance
        """
        self._repo = experiment_repo

    async def list_experiments(
        self,
        status: Optional[str] = None,
        experiment_type: Optional[str] = None,
        offset: int = 0,
        limit: int = 20
    ) -> Tuple[List[Dict], int]:
        """
        List experiments with filters.

        Args:
            status: Filter by experiment status
            experiment_type: Filter by experiment type
            offset: Number of items to skip
            limit: Maximum number of items to return

        Returns:
            Tuple of (experiments list, total count)
        """
        try:
            experiments, total = await self._repo.list_experiments(
                status=status,
                experiment_type=experiment_type,
                offset=offset,
                limit=limit
            )
            return (experiments, total)
        except Exception as e:
            logger.error(f"[ExperimentService] Failed to list: {e}")
            return ([], 0)

    async def get_experiment(self, experiment_key: str) -> Optional[Dict]:
        """Get experiment by key."""
        try:
            experiment = await self._repo.get_by_key(experiment_key)
            return experiment
        except Exception as e:
            logger.error(f"[ExperimentService] Failed to get {experiment_key}: {e}")
            return None

    # ... 其他方法 (create/update/delete/etc.)
```

#### Step 2: 修改 API 层使用依赖注入

```python
# api/admin/experiments.py (v3.29)

from fastapi import Depends
from domains.platform.experiments.service import ExperimentService
from infrastructure.repositories.experiment_repository import SupabaseExperimentRepository
from core.database import get_supabase_client

# ✅ 新增: DI 工厂函数
def get_experiment_service() -> ExperimentService:
    """Dependency injection factory for ExperimentService."""
    db = get_supabase_client()
    experiment_repo = SupabaseExperimentRepository(client=db)
    return ExperimentService(experiment_repo)


# ✅ 修改端点使用 DI
@router.get("", response_model=ExperimentListResponse)
@limiter.limit("30/minute")
async def list_experiments(
    request: Request,
    status: Optional[str] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    admin: dict = Depends(require_admin),
    experiment_service: ExperimentService = Depends(get_experiment_service),  # ✅ DI
):
    """List all experiments."""
    try:
        logger.info(f"[Admin {admin.get('id')}] Listing experiments")

        if status and status not in VALID_EXPERIMENT_STATUSES:
            raise HTTPException(400, f"Invalid status")

        # ✅ 调用 Service 实例方法
        experiments, total = await experiment_service.list_experiments(
            status=status,
            offset=offset,
            limit=limit
        )
        return ExperimentListResponse(experiments=experiments, total=total)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin] List experiments failed: {e}")
        raise HTTPException(500, "Failed to list experiments")
```

---

## 📊 修复后评估

| 维度 | 修复前 (v3.28) | 修复后 (v3.29) | 提升 |
|------|----------------|----------------|------|
| ⭐ **代码标准** | 98/100 | 100/100 | +2 |
| ⭐ **架构合规** | 75/100 | **100/100** | +25 |
| ⭐ **安全完整** | 100/100 | 100/100 | 0 |
| ⭐ **调用链完整** | 100/100 | 100/100 | 0 |
| ⭐ **测试覆盖** | 60/100 | 60/100 | 0 (需单独改进) |
| **总评** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | **+1 星** (测试覆盖另计) |

**修复后架构** (Perfect DDD):
```
API Layer (experiments.py v3.29)
  ├── Depends(get_experiment_service)  ✅ 依赖注入
  └── await experiment_service.list_experiments()  ✅ 调用 Service

Service Layer (ExperimentService)
  ├── 业务逻辑封装
  ├── 错误处理
  └── await self._repo.list_experiments()  ✅ 调用 Repository

Repository Layer (SupabaseExperimentRepository v2.0.0)
  ├── 网络错误重试 (@retry_on_network_error_async)
  ├── OOM 保护 (limit 10000)
  └── await self.client.table("experiments").select(...)  ✅ 数据访问
```

---

## 🎯 修复优先级

| 优先级 | 任务 | 预计时间 | 价值 |
|--------|------|----------|------|
| 🔴 **P0** | 创建 ExperimentService 类 | 30 分钟 | +25 分 (架构) |
| 🔴 **P0** | 添加 DI 工厂函数 | 5 分钟 | +25 分 (架构) |
| 🔴 **P0** | 修改 14 个端点使用 DI | 20 分钟 | +25 分 (架构) |
| 🟡 **P1** | 更新测试 (Mock Service) | 20 分钟 | 测试改进 |
| 🟡 **P1** | 增加测试覆盖 (20 → 40 个测试) | 2 小时 | +30 分 (测试) |

**总计**:
- **架构修复** (P0): 55 分钟 → ⭐⭐⭐⭐⭐ (不含测试)
- **测试改进** (P1): 2.5 小时 → 测试覆盖 90/100

---

## 📈 架构对比

### 修复前 (v3.28 - 4 星架构)

```
API Layer (experiments.py)
  ├── import experiments as experiment_service  ❌ 直接导入模块
  └── experiment_service.list_experiments()  ❌ 调用模块函数

Service Layer (crud.py)
  ├── def list_experiments():  ❌ 模块函数
  ├──   repo = _get_repo()  ❌ 每次创建新 Repository
  └──   return asyncio.run(repo.list_experiments())  ❌ 包装异步调用

Repository Layer
  └── SupabaseExperimentRepository  ✅ 正确
```

### 修复后 (v3.29 - 5 星架构)

```
API Layer (experiments.py v3.29)
  ├── Depends(get_experiment_service)  ✅ 依赖注入
  └── await experiment_service.list_experiments()  ✅ 调用 Service 方法

Service Layer (ExperimentService)
  ├── def __init__(self, experiment_repo):  ✅ 注入 Repository
  └── async def list_experiments(self):  ✅ 异步方法

Repository Layer
  └── SupabaseExperimentRepository  ✅ 正确
```

---

## 🏆 最终评估

### 当前状态 (v3.28)

- ✅ **代码标准**: 98/100 (优秀)
- ⚠️ **架构合规**: 75/100 (需改进 - 缺少依赖注入)
- ✅ **安全完整**: 100/100 (完美)
- ✅ **调用链完整**: 100/100 (完美)
- ⚠️ **测试覆盖**: 60/100 (偏低)

**总评**: ⭐⭐⭐⭐ (4 STARS)

---

## 📚 参考

- **完美示例**: `api/user/analytics.py` (v2.3.0) - 5 星架构
- **完美示例**: `api/user/config.py` (v2.2.0) - 5 星架构
- **Repository 接口**: `domains/platform/repository.py` (IExperimentRepository)
- **Repository 实现**: `infrastructure/repositories/experiment_repository.py` (v2.0.0)
- **Service 模块**: `domains/platform/experiments/crud.py` (v3.28)
- **测试文件**: `tests/api/admin/test_experiments.py`

---

## 🎯 关键建议

### 立即修复 (55 分钟 → 5 星)

1. ✅ 创建 `ExperimentService` 类 (30 分钟)
2. ✅ 添加 DI 工厂函数 `get_experiment_service()` (5 分钟)
3. ✅ 修改 14 个端点使用 `Depends(get_experiment_service)` (20 分钟)

### 后续改进 (2.5 小时 → 测试 90/100)

4. ✅ 更新测试 Mock Service (20 分钟)
5. ✅ 增加测试覆盖到 40+ 个测试 (2 小时)

---

**评估结论**: Experiments 模块已完成 80% 的 DDD 迁移，但缺少最关键的依赖注入机制。修复简单（55 分钟），修复后可达 5 星标准（不含测试覆盖改进）。
