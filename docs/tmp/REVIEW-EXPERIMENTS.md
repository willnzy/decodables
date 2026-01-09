# Experiments Module Deep Review (v3.28)

**审查日期**: 2026-01-09
**审查范围**: Experiments 模块 14 个接口 (api/admin/experiments.py)
**当前版本**: v3.28
**审查标准**: ⭐⭐⭐⭐⭐ (5-Star Deep Review)

---

## 📋 Executive Summary

### 🔴 Critical Finding: EXP-CRITICAL-1

**Experiments 模块存在完整的 DDD 实现但从未被使用**

| 组件 | 状态 | 说明 |
|------|------|------|
| **Repository** | ❌ 未使用 | 308 行完整实现存在但从未被调用 |
| **Service Layer** | ❌ 直接访问 DB | 违反 DDD 分层原则 |
| **API Layer** | ❌ 调用旧 Service | 使用直接 DB 访问的 Service |
| **测试** | ✅ 全部通过 | 35/35 tests passed (100%) |

### 质量评分

**总评**: 🔴 **C (需要重构 / Needs Refactoring)**

| 维度 | 评分 | 说明 |
|------|------|------|
| **DDD 架构合规性** | 🔴 0% | 完全未使用 DDD 架构 |
| **功能完整性** | 🟢 100% | 所有功能正常工作 |
| **测试覆盖** | 🟡 70% | API 层测试完整,Service/Repository 层无测试 |
| **安全性** | 🟡 85% | 认证正常,部分缺少错误处理 |
| **性能** | 🟢 90% | 无明显性能问题 |

---

## 🏗️ Architecture Analysis

### Current Architecture (v3.28)

```
❌ 当前实现 (违反 DDD)
┌─────────────────────────────────────────┐
│ API Layer (api/admin/experiments.py)   │
│ 14 endpoints                            │
└─────────────┬───────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Domain Service (直接访问 DB)            │
│ domains/platform/experiments/crud.py   │
│ - Imports: from .core import supabase  │
│ - Direct DB calls: supabase.table()    │
└─────────────┬───────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Supabase PostgreSQL                     │
└─────────────────────────────────────────┘

❗ 未被使用的组件 (308 lines)
┌─────────────────────────────────────────┐
│ SupabaseExperimentRepository            │
│ infrastructure/repositories/            │
│   experiment_repository.py              │
│ - 完整的 CRUD 实现                      │
│ - 符合 DDD 规范                         │
│ - 从未被调用                            │
└─────────────────────────────────────────┘
```

### Target DDD Architecture (应该是)

```
✅ 目标架构 (DDD 标准)
┌─────────────────────────────────────────┐
│ API Layer                                │
│ api/admin/experiments.py                │
└─────────────┬───────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Application Service (业务编排)          │
│ application/services/experiment.py      │
└─────────────┬───────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Domain Service (领域逻辑)               │
│ domains/platform/experiments/           │
│ - Uses Repository Interface             │
│ - NO direct DB access                   │
└─────────────┬───────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Repository Interface                     │
│ domains/platform/repository.py          │
└─────────────┬───────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Repository Implementation                │
│ infrastructure/repositories/            │
│   experiment_repository.py              │
│ + @retry_on_network_error               │
└─────────────┬───────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Database (PostgreSQL)                    │
└─────────────────────────────────────────┘
```

---

## 📊 Interface Inventory (14 Endpoints)

### CRUD Operations (6)

| Endpoint | Method | Rate Limit | Auth | Status |
|----------|--------|------------|------|--------|
| `/experiments` | GET | 30/min | ✅ Admin | ✅ 正常 |
| `/experiments` | POST | 20/min | ✅ Admin | ✅ 正常 |
| `/experiments/{key}` | GET | 30/min | ✅ Admin | ✅ 正常 |
| `/experiments/{key}` | PUT | 20/min | ✅ Admin | ✅ 正常 |
| `/experiments/{key}` | DELETE | 20/min | ✅ Admin | ✅ 正常 |
| `/experiments/{key}/status` | PUT | 20/min | ✅ Admin | ✅ 正常 |

### Results & Analysis (5)

| Endpoint | Method | Rate Limit | Auth | Status |
|----------|--------|------------|------|--------|
| `/experiments/{key}/results` | GET | 30/min | ✅ Admin | ✅ 正常 |
| `/experiments/{key}/aggregate` | POST | 10/min | ✅ Admin | ✅ 正常 |
| `/experiments/aggregate-all` | POST | 5/min | ✅ Admin | ✅ 正常 |
| `/experiments/cache/clear` | POST | 10/min | ✅ Admin | ✅ 正常 |
| `/experiments/{key}/ai-analysis` | POST | 5/min | ✅ Admin | ✅ 正常 |

### Trends & Recommendations (3)

| Endpoint | Method | Rate Limit | Auth | Status |
|----------|--------|------------|------|--------|
| `/experiments/{key}/quick-recommendation` | GET | 30/min | ✅ Admin | ✅ 正常 |
| `/experiments/{key}/trend` | GET | 30/min | ✅ Admin | ✅ 正常 |
| `/experiments/{key}/hourly-trend` | GET | 30/min | ✅ Admin | ✅ 正常 |

---

## 🔍 Detailed Code Analysis

### 1. API Layer - [api/admin/experiments.py](api/admin/experiments.py)

**文件信息**:
- **版本**: v3.28
- **行数**: 659 lines
- **接口数**: 14 endpoints
- **依赖**: experiment_service (旧 Service)

**关键代码分析**:

```python
# Line 6-12: Imports
from core.auth import require_admin
from core.rate_limiter import limiter
from domains.platform import experiment_service  # ❌ 旧 Service (直接 DB 访问)

# Line 197-222: list_experiments - 典型调用模式
@router.get("", response_model=ExperimentListResponse)
@limiter.limit("30/minute")
async def list_experiments(
    request: Request,
    status: Optional[str] = Query(None, max_length=50),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    admin: dict = Depends(require_admin)
):
    """List all experiments."""
    try:
        # ❌ Calls old Service that directly accesses DB
        experiments, total = experiment_service.list_experiments(
            status=status,
            limit=limit,
            offset=offset
        )

        return ExperimentListResponse(
            experiments=experiments,
            total=total,
            offset=offset,
            limit=limit
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[Admin {admin.get('id')}] List experiments failed: "
            f"{type(e).__name__} - {e}"
        )
        raise HTTPException(500, "Failed to list experiments")
```

**问题**:
1. ❌ 调用 `experiment_service` (旧 Service) 而非 DDD Service
2. ❌ 旧 Service 直接访问 Supabase (违反分层)
3. ✅ 错误处理完善
4. ✅ 认证和限流正确
5. ⚠️ 缺少 Pydantic Response Models (部分端点)

### 2. Domain Service - [domains/platform/experiments/crud.py](domains/platform/experiments/crud.py)

**文件信息**:
- **版本**: v3.28
- **行数**: 196+ lines
- **问题**: 直接访问 Supabase

**关键代码分析**:

```python
# Line 15: Direct Supabase import
from .core import supabase, logger, parse_experiment  # ❌ supabase is DB client

# Line 119-156: list_experiments() - 直接 DB 访问
def list_experiments(
    status: str = None,
    experiment_type: str = None,
    offset: int = 0,
    limit: int = 20
) -> tuple[List[Dict], int]:  # ✅ v3.28: 已修复返回类型
    """List experiments with filters."""
    if not supabase:  # ❌ Direct Supabase usage
        return ([], 0)

    try:
        # ❌ Direct DB query without Repository
        query = supabase.table("experiments").select("*", count="exact")

        if status:
            query = query.eq("status", status)
        if experiment_type:
            query = query.eq("experiment_type", experiment_type)

        result = query.order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()  # ❌ No retry mechanism

        items = [parse_experiment(e) for e in (result.data or [])]
        return (items, result.count or 0)  # ✅ Correct tuple unpacking

    except Exception as e:
        logger.error(f"[Experiment] Failed to list: {e}")
        return ([], 0)
```

**问题**:
1. 🔴 **EXP-CRITICAL-2**: 直接使用 `supabase.table()` 访问数据库
2. 🔴 **违反 DDD**: Domain Layer 依赖 Infrastructure (Supabase SDK)
3. ❌ 无重试机制 (@retry_on_network_error)
4. ❌ 无 Repository 抽象
5. ✅ v3.28 修复: 返回类型正确 (tuple[List[Dict], int])

### 3. Analysis Module - [domains/platform/experiments/analysis.py](domains/platform/experiments/analysis.py)

**文件信息**:
- **版本**: v3.25 → v3.28
- **行数**: 321 lines
- **功能**: 实验结果聚合、统计分析

**关键代码分析**:

```python
# Line 38-39: EXP-HIGH-5 Bug Fix (v3.28)
# v3.28: EXP-HIGH-5 - Fixed tuple unpacking (list_experiments now returns tuple)
experiments, _ = list_experiments(status="running")  # ✅ Fixed in v3.28

# Before (v3.25):
# result = list_experiments(status="running")
# experiments = result.get("items", [])  # ❌ Would cause AttributeError
```

**变更记录**:
- ✅ **EXP-HIGH-5 已修复**: 在 v3.28 中修复了 tuple 解包问题
- ✅ 注释清晰标注了修复内容
- ✅ 聚合逻辑使用 SQL 聚合避免 OOM

**问题**:
- ⚠️ 仍然使用旧 Service (直接 DB 访问)
- ⚠️ 应该迁移到 Repository 模式

### 4. Repository Implementation - [infrastructure/repositories/experiment_repository.py](infrastructure/repositories/experiment_repository.py)

**文件信息**:
- **版本**: (未标注)
- **行数**: 308 lines
- **状态**: 🔴 **完整实现但从未被使用**

**关键代码分析**:

```python
# Line 27-41: Properly structured Repository
class SupabaseExperimentRepository(IExperimentRepository):
    """Supabase implementation of experiment repository."""

    def __init__(self, client=None):
        """Initialize repository with Supabase client."""
        self._client = client

    @property
    def client(self):
        """Lazy load Supabase client."""
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    # Line 43-59: get_by_id implementation
    async def get_by_id(self, experiment_id: str) -> Optional[Experiment]:
        """Get experiment by ID."""
        try:
            result = self.client.table("experiments").select("*").eq(
                "experiment_id", experiment_id
            ).single().execute()

            if not result.data:
                return None

            return self._map_to_experiment(result.data)

        except Exception as e:
            logger.error(f"Failed to get experiment {experiment_id}: {e}")
            return None
```

**已实现的方法** (308 lines):
- ✅ `get_by_id()` - 按 ID 获取
- ✅ `get_by_key()` - 按 Key 获取
- ✅ `save()` - 保存实验
- ✅ `create()` - 创建实验
- ✅ `update()` - 更新实验
- ✅ `delete()` - 删除实验
- ✅ `get_all()` - 列出所有
- ✅ `get_running()` - 获取运行中的
- ✅ `record_assignment()` - 记录分配
- ✅ `get_user_assignment()` - 获取用户分配
- ✅ `_map_to_experiment()` - 映射函数
- ✅ `_map_to_row()` - 反向映射

**问题**:
1. 🔴 **EXP-CRITICAL-3**: 308 行完整代码从未被调用
2. ❌ **缺失**: 没有 `@retry_on_network_error` 装饰器
3. ❌ **缺失**: 没有 OOM 保护 (limit)
4. ✅ **优点**: 结构良好,符合 DDD 规范
5. ✅ **优点**: 有完整的 Protocol 接口定义

---

## 🔴 Critical Issues

### EXP-CRITICAL-1: Dual Implementation (最严重)

**问题**: 系统中存在**双重实现**

| 实现 | 位置 | 状态 | 调用方 |
|------|------|------|--------|
| **旧实现** | `domains/platform/experiments/crud.py` | ❌ 在使用 | API Layer |
| **新实现** | `infrastructure/repositories/experiment_repository.py` | ✅ 未使用 | 无 |

**影响**:
- 🔴 **架构混乱**: 有 DDD 实现但不用,有旧实现在用
- 🔴 **维护负担**: 两套代码需要同步更新
- 🔴 **技术债务**: 308 行未使用代码
- 🔴 **违反规范**: 不符合项目 DDD 架构标准

**对比其他模块**:

| 模块 | 版本 | DDD 合规 | Repository 使用 |
|------|------|----------|----------------|
| Metrics | v3.28 | ✅ 100% | ✅ SupabaseMetricsRepository |
| Config | v3.26 | ✅ 100% | ✅ SupabaseConfigRepository |
| Events | v3.27 | ✅ 100% | ✅ SupabaseEventsRepository |
| Logs | v3.26 | ✅ 100% | ✅ SupabaseLogsRepository |
| Users | v3.26 | ✅ 100% | ✅ SupabaseUsersRepository |
| **Experiments** | **v3.28** | **❌ 0%** | **❌ 未使用** |

**Experiments 是唯一未使用 DDD 的 Admin API 模块**

### EXP-CRITICAL-2: Domain Layer 违反分层原则

**位置**: `domains/platform/experiments/crud.py:15`

**问题**:
```python
# Domain Layer 直接导入 Infrastructure
from .core import supabase  # ❌ supabase is Supabase Client

# Domain Layer 直接操作数据库
def create_experiment(...):
    result = supabase.table("experiments").insert(data).execute()  # ❌
```

**违反原则**:
- ❌ **依赖方向错误**: Domain → Infrastructure (应该是 Infrastructure → Domain)
- ❌ **无法测试**: 模块级实例无法 mock
- ❌ **无法扩展**: 无法切换数据库实现

### EXP-CRITICAL-3: Repository 完整但未使用

**问题**: `experiment_repository.py` 有 308 行完整实现,但从未被调用

**已实现的功能** (全部未被使用):
- ✅ 完整 CRUD 方法 (10+ 方法)
- ✅ Protocol 接口定义
- ✅ 数据映射函数
- ✅ 错误处理
- ✅ 符合 DDD 规范

**浪费的工作量**:
- 308 lines of code
- Interface design
- Mapping logic
- Error handling

**维护风险**:
- 两套实现容易不同步
- 需要同时维护两套逻辑
- 代码审查负担加倍

---

## 🟠 High Priority Issues

### EXP-HIGH-1: 缺少重试机制

**问题**: Repository 方法没有 `@retry_on_network_error` 装饰器

**对比 Metrics 模块** (v3.28):
```python
# ✅ Metrics Repository (正确)
@retry_on_network_error(max_retries=3, delay=1.0)
async def get_daily_metrics(...):
    result = self.client.table("metrics_daily")...

# ❌ Experiments Repository (缺失)
async def get_by_id(self, experiment_id: str):
    result = self.client.table("experiments")...  # No retry
```

**影响**:
- 网络抖动会导致请求失败
- 无自动重试机制
- 用户体验差

### EXP-HIGH-2: 缺少 OOM 保护

**问题**: Repository 查询无 `.limit()` 限制

**风险代码**:
```python
# experiment_repository.py - 缺少 limit
async def get_all(self, status: Optional[str] = None):
    query = self.client.table("experiments").select("*", count="exact")
    # ❌ No limit() - 可能返回数万条记录
    result = query.order("created_at", desc=True).execute()
```

**对比 Metrics 模块**:
```python
# ✅ Metrics Repository (安全)
result = query.limit(10000).execute()  # OOM protection
```

### EXP-HIGH-3: 缺少 Pydantic Response Models

**问题**: 部分端点返回原始 dict,无类型验证

**缺失的 Models**:
- ⚠️ `ExperimentResultsResponse`
- ⚠️ `TrendDataResponse`
- ⚠️ `RecommendationResponse`
- ⚠️ `AIAnalysisResponse`

**已有的 Models** (部分端点):
- ✅ `ExperimentListResponse`
- ✅ `ExperimentResponse`

### EXP-HIGH-4: 同步方法阻塞事件循环

**问题**: Domain Service 使用同步方法

```python
# crud.py - Synchronous methods
def create_experiment(...):  # ❌ Sync
    result = supabase.table("experiments").insert(data).execute()

def list_experiments(...):  # ❌ Sync
    result = supabase.table("experiments").select("*").execute()
```

**API Layer 调用**:
```python
async def create_experiment(...):  # Async endpoint
    experiment = experiment_service.create_experiment(...)  # ❌ Calls sync
```

**影响**:
- 阻塞 FastAPI 事件循环
- 降低并发性能
- 不符合 async/await 最佳实践

---

## 🟡 Medium Priority Issues

### EXP-MEDIUM-1: 双重缓存机制

**问题**: 两套缓存逻辑

1. **内存字典缓存** (domains/platform/experiments/core.py):
```python
CACHE_TTL = 300  # 5 minutes
_experiment_cache = {}  # Module-level dict
```

2. **Redis 缓存** (可能):
```python
from core.cache import cache_service
```

**影响**:
- 缓存不一致风险
- 维护成本高
- 内存泄漏风险

**建议**: 统一使用 `cache_service` (Redis)

### EXP-MEDIUM-2: 日期解析不一致

**问题**: 时区处理不统一

```python
# 有的地方手动处理时区
result_datetime = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
if result_datetime.replace(tzinfo=timezone.utc) < start_time:

# 有的地方不处理
start_dt = datetime.fromisoformat(start_date) if start_date else None  # ❌
```

**建议**: 创建统一的 `parse_iso_date()` helper

---

## 🔵 Low Priority Issues

### EXP-LOW-1: 魔术数字

**问题**: 未定义常量

```python
days: int = Query(30, ge=1, le=90, ...)  # 30, 90 - magic numbers
hours: int = Query(24, ge=1, le=168, ...)  # 24, 168 - magic numbers
```

**建议**:
```python
DEFAULT_TREND_DAYS = 30
MAX_TREND_DAYS = 90
DEFAULT_TREND_HOURS = 24
MAX_TREND_HOURS = 168
```

### EXP-LOW-2: 限流配置可优化

**当前配置**:
- CRUD: 20-30/minute
- 查询: 30/minute
- 趋势: 30/minute

**建议**:
- CRUD: 20/minute (保持)
- 查询: 20/minute (从 30 降低)
- 趋势: 15/minute (从 30 降低,因为涉及复杂聚合)

---

## 📈 Test Coverage Analysis

### Test Execution Results

```bash
pytest tests/api/admin/test_experiments.py -v

✅ Result: 35/35 PASSED (100%)
```

### Test Coverage Breakdown

| 测试类别 | 测试数 | 覆盖内容 | 状态 |
|---------|--------|----------|------|
| **认证测试** | 14 | 所有端点需要 Admin 权限 | ✅ 完整 |
| **参数验证** | 7 | Query/Path/Body 参数边界 | ✅ 完整 |
| **常量测试** | 3 | VALID_STATUSES, VALID_TYPES | ✅ 完整 |
| **字段验证** | 9 | 日期格式、范围等 | ✅ 完整 |
| **Repository 测试** | 0 | Repository 方法单元测试 | ❌ 缺失 |
| **Service 测试** | 0 | Domain Service 单元测试 | ❌ 缺失 |
| **集成测试** | 2 | 完整流程测试 | ⚠️ 基础 |

### Test Gaps

**缺失的测试**:
1. ❌ **Repository 单元测试** - 308 行代码完全未测试
2. ❌ **Domain Service 测试** - crud.py/analysis.py 未测试
3. ❌ **聚合逻辑测试** - 复杂的统计计算未验证
4. ❌ **缓存失效测试** - 更新后缓存是否正确清除
5. ❌ **错误场景测试** - 数据库失败、数据不一致

**测试覆盖率估算**:
- API Layer: ~90% (35 tests)
- Service Layer: ~0% (no tests)
- Repository Layer: ~0% (no tests, and unused)
- **Overall: ~70%**

---

## 🔧 Refactoring Plan

### Phase 1: Repository Layer Enhancement (高优先级)

**目标**: 增强 Repository,添加缺失功能

#### Step 1.1: 添加重试机制

**文件**: `infrastructure/repositories/experiment_repository.py`

**修改**:
```python
from core.decorators import retry_on_network_error

class SupabaseExperimentRepository(IExperimentRepository):

    @retry_on_network_error(max_retries=3, delay=1.0)  # ✅ Add retry
    async def get_by_id(self, experiment_id: str) -> Optional[Experiment]:
        ...

    @retry_on_network_error(max_retries=3, delay=1.0)  # ✅ Add retry
    async def get_by_key(self, experiment_key: str) -> Optional[Experiment]:
        ...

    # ... 所有其他方法类似
```

#### Step 1.2: 添加 OOM 保护

**修改**:
```python
@retry_on_network_error(max_retries=3, delay=1.0)
async def list_experiments(
    self,
    status: Optional[str] = None,
    offset: int = 0,
    limit: int = 20
) -> tuple[List[Dict], int]:
    query = self.client.table("experiments").select("*", count="exact")

    if status:
        query = query.eq("status", status)

    result = query.order("created_at", desc=True)\
        .range(offset, offset + limit - 1)\
        .limit(10000)\  # ✅ Add OOM protection
        .execute()

    return ([self._map_to_experiment(row) for row in result.data], result.count or 0)
```

#### Step 1.3: 添加趋势查询方法

**新增方法**:
```python
@retry_on_network_error(max_retries=3, delay=1.0)
async def get_trend_data(
    self,
    experiment_id: str,
    start_date: str,
    days: int
) -> List[Dict]:
    """Get daily trend data."""
    result = self.client.table("experiment_results").select("*")\
        .eq("experiment_id", experiment_id)\
        .gte("date", start_date)\
        .order("date")\
        .limit(10000)\  # OOM protection
        .execute()

    return result.data or []

@retry_on_network_error(max_retries=3, delay=1.0)
async def get_hourly_trend_data(
    self,
    experiment_id: str,
    start_date: str,
    hours: int
) -> List[Dict]:
    """Get hourly trend data."""
    result = self.client.table("experiment_results").select("*")\
        .eq("experiment_id", experiment_id)\
        .gte("date", start_date)\
        .order("date").order("hour")\
        .limit(10000)\
        .execute()

    return result.data or []
```

### Phase 2: Service Layer Migration (核心重构)

**目标**: 创建新 Service 层使用 Repository

#### Step 2.1: 创建 ExperimentService 类

**新建文件**: `application/services/experiment_service.py`

```python
"""
Experiment Application Service - Business orchestration layer.

@module application.services.experiment_service
@version 1.0.0 (v3.28)
"""

from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta, timezone

from domains.platform.experiments.repository import IExperimentRepository
from core.logger import logger


class ExperimentService:
    """Experiment application service using Repository pattern."""

    def __init__(self, experiment_repo: IExperimentRepository):
        """Initialize service with repository."""
        self.experiment_repo = experiment_repo

    async def list_experiments(
        self,
        status: Optional[str] = None,
        offset: int = 0,
        limit: int = 20
    ) -> tuple[List[Dict], int]:
        """List experiments with filters."""
        try:
            experiments, total = await self.experiment_repo.list_experiments(
                status=status,
                offset=offset,
                limit=limit
            )
            return (experiments, total)
        except Exception as e:
            logger.error(f"[ExperimentService] List failed: {e}")
            return ([], 0)

    async def get_experiment(
        self,
        experiment_key: str,
        use_cache: bool = True
    ) -> Optional[Dict]:
        """Get experiment by key."""
        try:
            experiment = await self.experiment_repo.get_by_key(experiment_key)
            return experiment
        except Exception as e:
            logger.error(f"[ExperimentService] Get {experiment_key} failed: {e}")
            return None

    async def create_experiment(self, data: Dict) -> Optional[Dict]:
        """Create new experiment."""
        try:
            experiment = await self.experiment_repo.create(data)
            return experiment
        except Exception as e:
            logger.error(f"[ExperimentService] Create failed: {e}")
            return None

    async def update_experiment(
        self,
        experiment_key: str,
        data: Dict
    ) -> Optional[Dict]:
        """Update experiment."""
        try:
            experiment = await self.experiment_repo.update(experiment_key, data)
            return experiment
        except Exception as e:
            logger.error(f"[ExperimentService] Update {experiment_key} failed: {e}")
            return None

    async def delete_experiment(self, experiment_key: str) -> bool:
        """Delete experiment."""
        try:
            success = await self.experiment_repo.delete(experiment_key)
            return success
        except Exception as e:
            logger.error(f"[ExperimentService] Delete {experiment_key} failed: {e}")
            return False

    async def get_daily_trend(
        self,
        experiment_key: str,
        days: int
    ) -> Optional[Dict]:
        """Get daily trend data."""
        try:
            experiment = await self.experiment_repo.get_by_key(experiment_key)
            if not experiment:
                return None

            start_date = (
                datetime.now(timezone.utc) - timedelta(days=days)
            ).strftime("%Y-%m-%d")

            results = await self.experiment_repo.get_trend_data(
                experiment["id"],
                start_date,
                days
            )

            return {
                "experiment_key": experiment_key,
                "days": days,
                "trend": results
            }
        except Exception as e:
            logger.error(f"[ExperimentService] Get trend {experiment_key} failed: {e}")
            return None
```

#### Step 2.2: 更新 API Layer 使用新 Service

**文件**: `api/admin/experiments.py`

**修改**:
```python
# Line 6-12: Update imports
from application.services.experiment_service import ExperimentService
from infrastructure.repositories.experiment_repository import SupabaseExperimentRepository
from core.database import get_database_client

# Add helper function
def _get_experiment_service() -> ExperimentService:
    """Get experiment service with repository."""
    db_client = get_database_client()
    experiment_repo = SupabaseExperimentRepository(db_client)
    return ExperimentService(experiment_repo)

# Update all endpoints
@router.get("", response_model=ExperimentListResponse)
@limiter.limit("30/minute")
async def list_experiments(
    request: Request,
    status: Optional[str] = Query(None, max_length=50),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    admin: dict = Depends(require_admin)
):
    """List all experiments."""
    try:
        service = _get_experiment_service()  # ✅ New Service
        experiments, total = await service.list_experiments(
            status=status,
            offset=offset,
            limit=limit
        )

        return ExperimentListResponse(
            experiments=experiments,
            total=total,
            offset=offset,
            limit=limit
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[Admin {admin.get('id')}] List experiments failed: "
            f"{type(e).__name__} - {e}"
        )
        raise HTTPException(500, "Failed to list experiments")
```

### Phase 3: 清理旧代码 (重要!)

#### Step 3.1: 标记旧 Service 为 Deprecated

**文件**: `domains/platform/experiments/crud.py`

**添加 Deprecation Warning**:
```python
"""
Experiments CRUD Operations (DEPRECATED in v3.28)

⚠️ DEPRECATED: This module is deprecated in v3.28
Use application.services.experiment_service.ExperimentService instead.

This file will be removed in v3.30.
"""

import warnings

def list_experiments(*args, **kwargs):
    warnings.warn(
        "list_experiments() is deprecated. Use ExperimentService instead.",
        DeprecationWarning,
        stacklevel=2
    )
    # ... existing implementation
```

#### Step 3.2: 删除计划

**v3.28 (当前)**:
- ✅ 添加 Deprecation Warning
- ✅ 迁移所有调用点到新 Service
- ⏳ 保留旧代码 2 个版本

**v3.29 (下一版本)**:
- ⏳ 继续保留旧代码
- ⏳ 确认无调用点

**v3.30 (未来)**:
- 🗑️ 删除 `domains/platform/experiments/crud.py`
- 🗑️ 删除 `domains/platform/experiments/core.py` (如果不再需要)

---

## ✅ Verification Checklist

### 架构验收

- [ ] **Repository 被使用**: 所有数据访问通过 Repository
- [ ] **Service 无直接 DB 访问**: Domain Service 只调用 Repository
- [ ] **API Layer 调用 Service**: API 不直接访问 Repository
- [ ] **所有方法有重试**: @retry_on_network_error 装饰器
- [ ] **所有查询有 limit**: OOM 保护

### 功能验收

- [ ] **所有 14 个端点正常**: 测试通过
- [ ] **趋势数据准确**: 验证聚合逻辑
- [ ] **缓存正确工作**: 更新后缓存失效
- [ ] **错误处理完善**: 异常不泄露

### 测试验收

- [ ] **现有测试全部通过**: 35/35 tests
- [ ] **新增 Repository 测试**: 覆盖所有方法
- [ ] **新增 Service 测试**: 业务逻辑单元测试
- [ ] **测试覆盖率 ≥ 70%**: 包含 Service/Repository

### 代码质量验收

- [ ] **无 Deprecation Warning**: 新代码不调用旧 API
- [ ] **Async/Await 一致**: 所有方法异步
- [ ] **错误日志完善**: 所有异常记录
- [ ] **代码注释清晰**: 重构原因标注

---

## 📊 Comparison with Other Modules

### Metrics Module (v3.28) - 标杆模块

| 方面 | Metrics (v3.28) | Experiments (v3.28) | 差距 |
|------|----------------|---------------------|------|
| **Repository 使用** | ✅ 100% | ❌ 0% | 🔴 关键 |
| **@retry_on_network_error** | ✅ 所有方法 | ❌ 无 | 🔴 高 |
| **OOM 保护** | ✅ limit(10000) | ❌ 无 | 🔴 高 |
| **Response Models** | ✅ 9 models | ⚠️ 部分 | 🟡 中 |
| **DDD 合规** | ✅ 100% | ❌ 0% | 🔴 关键 |
| **测试覆盖** | 🟢 90% | 🟡 70% | 🟡 中 |
| **质量评分** | 🟢 A+ | 🔴 C | 🔴 关键 |

### Architecture Alignment Gap

**当前状态**: Experiments 是**唯一**未使用 DDD 的 Admin API 模块

```
✅ DDD 合规模块 (6/7)
├── Metrics v3.28 ✅
├── Config v3.26 ✅
├── Events v3.27 ✅
├── Logs v3.26 ✅
├── Users v3.26 ✅
└── AI Models v3.26 ✅

❌ 非 DDD 模块 (1/7)
└── Experiments v3.28 ❌ ← 需要立即重构
```

---

## 🎯 Priority & Timeline

### P0 - 立即执行 (本次任务)

**目标**: DDD 架构合规,激活 Repository

**任务**:
1. ✅ 增强 Repository (retry + OOM + trend methods)
2. ✅ 创建 ExperimentService
3. ✅ 更新 API Layer
4. ✅ 标记旧代码为 Deprecated
5. ✅ 运行测试验证 (35/35 tests)
6. ✅ Git commit + push

**时间估算**: 2-3 hours

### P1 - 后续完善 (下一版本)

**目标**: 完善细节,提升质量

**任务**:
1. ⏳ 添加 Repository 单元测试
2. ⏳ 添加 Service 单元测试
3. ⏳ 完善 Pydantic Response Models
4. ⏳ 统一缓存策略
5. ⏳ 统一日期处理

**时间估算**: 1-2 hours

### P2 - 最终清理 (v3.30)

**目标**: 删除旧代码

**任务**:
1. 🗑️ 删除 domains/platform/experiments/crud.py
2. 🗑️ 删除 domains/platform/experiments/core.py (如不需要)
3. 🗑️ 删除相关 imports

**时间估算**: 30 minutes

---

## 📝 Summary

### Current Status (v3.28)

- **功能**: ✅ 所有功能正常工作
- **测试**: ✅ 35/35 tests passed (100%)
- **架构**: 🔴 完全违反 DDD 原则
- **质量**: 🔴 C (需要重构)

### Critical Finding

**Experiments 模块拥有 308 行完整的 DDD 实现,但从未被使用,是唯一未使用 DDD 的 Admin API 模块**

### Recommended Action

**立即进行 DDD 架构重构**:
1. 激活 SupabaseExperimentRepository (308 lines)
2. 创建 ExperimentService 使用 Repository
3. 更新 API Layer 调用新 Service
4. 标记旧代码为 Deprecated
5. 验证所有测试通过

**预期结果**:
- ✅ 100% DDD 架构合规
- ✅ 与其他 6 个模块一致
- ✅ 激活 308 行未使用代码
- ✅ 消除技术债务

---

**审查完成**: 2026-01-09
**审查人**: Claude Sonnet 4.5
**下一步**: 执行 DDD 架构重构 (Phase 1-3)
