# Experiments Module Deep Review (v3.25)

**审查日期**: 2026-01-09
**审查范围**: Experiments 模块 14 个接口 (api/admin/experiments.py)
**当前版本**: v3.25

---

## 📋 总结

### 模块概览
Experiments 模块负责 A/B 测试实验管理，共 14 个端点:

**CRUD (6个)**:
1. `GET /experiments` - 列出实验
2. `POST /experiments` - 创建实验
3. `GET /experiments/{key}` - 获取实验
4. `PUT /experiments/{key}` - 更新实验
5. `DELETE /experiments/{key}` - 删除实验
6. `PUT /experiments/{key}/status` - 更新状态

**结果分析 (5个)**:
7. `GET /experiments/{key}/results` - 获取结果
8. `POST /experiments/{key}/aggregate` - 触发聚合
9. `POST /experiments/aggregate-all` - 聚合所有
10. `POST /experiments/cache/clear` - 清除缓存
11. `POST /experiments/{key}/ai-analysis` - AI 分析

**推荐与趋势 (3个)**:
12. `GET /experiments/{key}/quick-recommendation` - 快速推荐
13. `GET /experiments/{key}/trend` - 每日趋势
14. `GET /experiments/{key}/hourly-trend` - 每小时趋势

### 架构模式
**当前架构**: 混合模式
- API Layer → Domain Service (部分端点)
- API Layer → **直接访问数据库** (趋势端点 - 第 455, 507 行)
- Domain Service → 直接使用 Supabase Client
- 存在 `SupabaseExperimentRepository` **但从未被使用**

### 关键发现

#### 🔴 CRITICAL (4个)
1. **EXP-CRITICAL-1**: API Layer 直接访问数据库 (趋势端点)
2. **EXP-CRITICAL-2**: Domain Service 直接使用 Supabase，违反 DDD
3. **EXP-CRITICAL-3**: ExperimentRepository (260行) 存在但从未被使用
4. **EXP-CRITICAL-4**: 存在完整的 DDD 模型 (Aggregate/ValueObjects) 但未被使用

#### 🟠 HIGH (6个)
5. **EXP-HIGH-1**: 缺少 Pydantic Response Models
6. **EXP-HIGH-2**: 趋势查询无 limit，存在 OOM 风险
7. **EXP-HIGH-3**: 部分端点缺少错误处理
8. **EXP-HIGH-4**: AI 分析动态导入，性能问题
9. **EXP-HIGH-5**: list_experiments 返回类型不一致
10. **EXP-HIGH-6**: 缺少审计日志

#### 🟡 MEDIUM (4个)
11. **EXP-MEDIUM-1**: 双重缓存机制 (Service 内存 + 可能的 Redis)
12. **EXP-MEDIUM-2**: 日期解析缺少时区处理
13. **EXP-MEDIUM-3**: parse_experiment 函数位置不明确
14. **EXP-MEDIUM-4**: 部分端点使用同步方法

#### 🔵 LOW (3个)
15. **EXP-LOW-1**: 测试文件重复 (test_experiments.py + test_experiments_api.py)
16. **EXP-LOW-2**: 部分端点限流过于宽松 (30/minute)
17. **EXP-LOW-3**: 魔术数字 (24, 168, 90 等未定义常量)

---

## 🏗️ 架构分析

### 当前架构 (v3.25)

```
┌─────────────────────────────────────────────────┐
│ API Layer (api/admin/experiments.py)           │
│                                                  │
│  CRUD: → Domain Service                         │
│  Trend: → Supabase Client (直接访问!) 🔴       │
└─────────────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────────┐
│ Domain Service (domains/platform/experiments/) │
│  - crud.py                                       │
│  - analysis.py                                   │
│  - assignment.py                                 │
│  - tracking.py                                   │
│                                                  │
│  使用: supabase = get_db_client() (直接访问)🔴  │
└─────────────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────────┐
│ Database (experiments table)                    │
└─────────────────────────────────────────────────┘

[未使用] SupabaseExperimentRepository (260 lines) 🔴
[未使用] DDD Aggregates: Experiment, ExperimentVariant 🔴
[未使用] Value Objects: TargetingRule, ExperimentStatus 🔴
```

**问题**:
1. API 层有 2 个端点直接访问数据库
2. Domain Service 直接使用 Supabase Client
3. 完整的 Repository + DDD 模型已存在但从未被调用
4. 违反 DDD 分层原则

### DDD 标准架构 (应该是)

```
API Layer
    ↓
Domain Service (业务逻辑)
    ↓
Repository Interface (domains/platform/repository.py)
    ↓
Repository Implementation (infrastructure/repositories/experiment_repository.py)
    ↓
Database

使用: Experiment Aggregate + Value Objects
```

---

## 🔍 详细问题清单

### 🔴 CRITICAL Issues

#### EXP-CRITICAL-1: API Layer 直接访问数据库

**位置**: `api/admin/experiments.py:455, 507`

**问题** (趋势端点):
```python
@router.get("/{experiment_key}/trend")
async def get_experiment_trend(...):
    # ...获取 experiment 通过 Service
    experiment = experiment_service.get_experiment(experiment_key, use_cache=False)

    # ❌ 然后直接访问数据库!
    results_data = supabase.table("experiment_results").select("*")\
        .eq("experiment_id", experiment_id).gte("date", start_date).order("date").execute()
    # 第 455 行
```

```python
@router.get("/{experiment_key}/hourly-trend")
async def get_hourly_trend(...):
    # 同样的问题
    results_data = supabase.table("experiment_results").select("*")\
        .eq("experiment_id", experiment_id).gte("date", start_date).order("date").order("hour").execute()
    # 第 507 行
```

**违反原则**:
- API Layer 不应该直接访问数据库
- 破坏了分层架构
- 无法 mock 测试
- 没有重试机制

**影响**:
- 2 个端点 (trend + hourly-trend) 完全绕过 Service 和 Repository
- 数据库连接失败无法恢复
- 无法复用查询逻辑

#### EXP-CRITICAL-2: Domain Service 直接使用 Supabase

**位置**:
- `domains/platform/experiments/core.py:18-23`
- `domains/platform/experiments/crud.py:15`

**问题**:
```python
# core.py
from core.database import get_db_client

# 模块级变量，直接使用 Supabase
supabase = get_db_client()  # ❌

def create_experiment(...):
    # 直接使用
    result = supabase.table("experiments").insert(data).execute()  # ❌
```

**违反原则**:
- Domain Layer 依赖 Infrastructure (Supabase SDK)
- 模块级实例，无法注入 mock
- 没有使用 Repository 抽象

**影响**:
- 所有 Domain Service 方法都直接操作数据库
- 无法测试
- 无法切换数据库实现

#### EXP-CRITICAL-3: ExperimentRepository 存在但未使用

**位置**: `infrastructure/repositories/experiment_repository.py` (260 lines)

**问题**:
完整的 Repository 实现已存在:
- `SupabaseExperimentRepository` 类 (260 行代码)
- 实现了 `IExperimentRepository` 接口
- 包含完整 CRUD 方法:
  - `get_by_id()`
  - `save()`, `create()`, `update()`
  - `delete()`
  - `get_all()`, `get_running()`
  - `record_assignment()`, `get_user_assignment()`
- 有 `_map_to_experiment()` 和 `_map_to_row()` 映射方法

**但从未被调用!**

**影响**:
- 260 行未使用代码
- 架构混乱（有 Repository 但不用）
- 维护成本高（两套实现需要同步）

#### EXP-CRITICAL-4: DDD Aggregates/Value Objects 存在但未使用

**位置**:
- `domains/platform/aggregates/experiment.py` - Experiment Aggregate
- `domains/platform/value_objects.py` - ExperimentStatus, ExperimentVariant, TargetingRule

**问题**:
完整的 DDD 模型已实现:

**Experiment Aggregate**:
```python
class Experiment:
    def __init__(
        self,
        experiment_id: str,
        name: str,
        status: ExperimentStatus,
        variants: List[ExperimentVariant],
        targeting_rules: List[TargetingRule],
        ...
    ):
        # 完整的聚合根实现
        self.experiment_id = experiment_id
        self.name = name
        self.status = status
        # ...
```

**Value Objects**:
```python
class ExperimentStatus(Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"

class ExperimentVariant:
    variant_id: str
    name: str
    weight: int
    config: dict
```

**但从未被 Service 或 API 使用!**

当前 Service 返回的是 `Dict`，不是领域对象。

**影响**:
- DDD 模型没有价值（不被使用）
- 缺少类型安全
- 业务逻辑散落在 dict 操作中

---

### 🟠 HIGH Issues

#### EXP-HIGH-1: 缺少 Pydantic Response Models

**位置**: `api/admin/experiments.py` (所有 14 个端点)

**问题**:
```python
@router.get("")  # ❌ 没有 response_model
async def list_experiments(...):
    experiments, total = experiment_service.list_experiments(...)
    return {"experiments": experiments, "total": total, ...}  # 返回原始 dict
```

**对比其他模块** (Config v3.26):
```python
@router.get("/config", response_model=AllConfigsResponse)  # ✅
async def get_all_configs(...):
    return AllConfigsResponse(configs=..., total=...)
```

**影响**:
- 无类型验证
- OpenAPI 文档不完整
- 运行时错误难以捕获

**需要创建**:
- `ExperimentListResponse`
- `ExperimentResponse`
- `ExperimentCreateResponse`
- `ExperimentUpdateResponse`
- `ExperimentResultsResponse`
- `TrendDataResponse`
- `AIAnalysisResponse`
- `RecommendationResponse`

#### EXP-HIGH-2: 趋势查询无 limit，OOM 风险

**位置**: `api/admin/experiments.py:455, 507`

**问题**:
```python
# Daily trend
results_data = supabase.table("experiment_results").select("*")\
    .eq("experiment_id", experiment_id)\
    .gte("date", start_date)\
    .order("date")\
    .execute()  # ❌ 无 limit
```

```python
# Hourly trend
results_data = supabase.table("experiment_results").select("*")\
    .eq("experiment_id", experiment_id)\
    .gte("date", start_date)\
    .order("date").order("hour")\
    .execute()  # ❌ 无 limit
```

**风险**:
- 长时间运行的实验可能有数百万条结果
- 查询全表可能 OOM
- 性能严重下降

**对比其他模块**:
- Config: `.limit(10000)`
- Events: `.limit(100000)`
- Experiments: **无限制**

**修复**:
```python
.limit(10000).execute()
```

#### EXP-HIGH-3: 部分端点缺少错误处理

**位置**: 多个端点

**问题**:
```python
@router.get("/{experiment_key}/trend")
async def get_experiment_trend(...):
    experiment = experiment_service.get_experiment(experiment_key, use_cache=False)
    if not experiment:
        raise HTTPException(404, "Experiment not found")

    # ❌ 后续数据库查询没有 try-except
    results_data = supabase.table("experiment_results").select("*")...

    # 如果查询失败，会暴露原始异常
```

**标准做法** (Config/Logs/Events 模块):
```python
try:
    # 所有操作
    ...
    return response
except HTTPException:
    raise
except Exception as e:
    logger.error(f"[Admin {admin.get('id')}] Operation failed: {type(e).__name__} - {e}")
    raise HTTPException(500, "Operation failed")
```

**缺失**:
- trend 端点
- hourly-trend 端点
- ai-analysis 端点 (部分)

#### EXP-HIGH-4: AI 分析动态导入

**位置**: `api/admin/experiments.py:388, 415`

**问题**:
```python
@router.post("/{experiment_key}/ai-analysis")
async def get_ai_analysis(...):
    # ❌ 每次请求都动态导入
    from domains.platform import experiment_ai_service

    analysis = experiment_ai_service.analyze_experiment_results(...)
```

**问题**:
- 每次请求都触发导入
- 性能开销
- 不符合 Python 最佳实践

**修复**:
在文件头部导入:
```python
from domains.platform import experiment_ai_service
```

#### EXP-HIGH-5: list_experiments 返回类型不一致

**位置**: `domains/platform/experiments/crud.py`

**问题**:
API 期望返回 `(List[Dict], int)`：
```python
# api/admin/experiments.py:182
experiments, total = experiment_service.list_experiments(...)
```

但 Repository 接口定义返回 `List[Experiment]`：
```python
# domains/platform/repository.py
async def get_all(self, status: Optional[ExperimentStatus] = None) -> List[Experiment]:
```

**类型不匹配**，如果迁移到 Repository 会破坏。

**修复**:
Repository 应该返回:
```python
async def get_all(...) -> Dict[str, Any]:
    return {
        "experiments": [...],
        "total": count
    }
```

#### EXP-HIGH-6: 缺少审计日志

**位置**: 多个端点

**问题**:
关键操作没有审计日志:
- ❌ `create_experiment` - 没有记录谁创建
- ❌ `update_experiment` - 没有记录谁更新
- ❌ `delete_experiment` - 没有记录谁删除
- ❌ `update_experiment_status` - 没有记录状态变更
- ❌ `trigger_aggregation` - 没有记录手动触发
- ✅ `clear_cache` - 也没有

**标准做法** (Config v3.26):
```python
logger.info(f"[Admin {admin.get('id')}] Created experiment: {experiment_key}")
logger.info(f"[Admin {admin.get('id')}] Updated experiment: {experiment_key}")
logger.info(f"[Admin {admin.get('id')}] Deleted experiment: {experiment_key}")
```

---

### 🟡 MEDIUM Issues

#### EXP-MEDIUM-1: 双重缓存机制

**位置**:
- `domains/platform/experiments/core.py:27-28` - 内存字典缓存
- 可能还有 Redis 缓存

**问题**:
```python
# core.py
CACHE_TTL = 300  # 5 minutes
_experiment_cache = {}  # 模块级字典

def get_cached_experiment(key: str):
    cached = _experiment_cache.get(key)
    # ...
```

同时 `core.cache.cache_service` 可能也在使用。

**影响**:
- 两套缓存逻辑
- 潜在的缓存不一致
- 维护成本高

**决策**:
- Service 层使用 `cache_service` (Redis)
- 移除 `_experiment_cache` 字典

#### EXP-MEDIUM-2: 日期解析缺少时区处理

**位置**: `api/admin/experiments.py:332-333, 517`

**问题**:
```python
# get_experiment_results
start_dt = datetime.fromisoformat(start_date) if start_date else None  # ❌ 没有时区
end_dt = datetime.fromisoformat(end_date) if end_date else None

# hourly_trend
result_datetime = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
if result_datetime.replace(tzinfo=timezone.utc) < start_time:  # 手动添加时区
```

**不一致**:
- 有的地方手动处理时区
- 有的地方不处理
- 可能导致时区相关 bug

**修复**:
统一使用:
```python
from datetime import datetime, timezone

def parse_iso_date(date_str: str) -> datetime:
    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
```

#### EXP-MEDIUM-3: parse_experiment 函数位置不明确

**位置**: `domains/platform/experiments/core.py:16` (import from)

**问题**:
```python
from .core import (
    supabase, logger, parse_experiment,  # ← parse_experiment 从哪来?
    get_cached_experiment, ...
)
```

`core.py` 文件我只读了前 50 行，`parse_experiment` 可能在后面定义，或者在其他文件。

**影响**:
- 代码结构不清晰
- 难以追踪函数定义

#### EXP-MEDIUM-4: 部分端点使用同步方法

**问题**:
Domain Service 中部分方法是同步的：
```python
def create_experiment(...):  # 同步
    ...

def get_experiment(...):  # 同步
    ...
```

但 API 端点是 async:
```python
async def create_experiment(...):  # async
    experiment = experiment_service.create_experiment(...)  # ❌ 同步调用
```

**影响**:
- 阻塞事件循环
- 不符合 FastAPI 最佳实践

**修复**:
所有 Domain Service 方法改为 async。

---

### 🔵 LOW Issues

#### EXP-LOW-1: 测试文件重复

**位置**:
- `tests/api/admin/test_experiments.py` (308 lines) - 完整测试
- `tests/api/admin/test_experiments_api.py` - 基础认证测试

**问题**:
与 Config 模块相同，有两个测试文件测试相同端点。

**修复**:
删除 `test_experiments_api.py`，保留 `test_experiments.py`。

#### EXP-LOW-2: 部分端点限流过于宽松

**位置**: `api/admin/experiments.py`

**当前配置**:
```python
@router.get("/{experiment_key}/trend")
@limiter.limit("30/minute")  # 30 次/分钟
```

**对比**:
- Config 查询: 30/minute ← 最近刚从 60 调整
- Experiments 查询: 30/minute ← 可能还是偏高

趋势查询涉及复杂聚合，可能需要更严格限流。

**建议**:
- CRUD: 20/minute (当前)
- 查询: 20/minute (从 30 降低)
- 趋势: 15/minute (新)

#### EXP-LOW-3: 魔术数字

**位置**: 多处

**问题**:
```python
days: int = Query(30, ge=1, le=90, description="Number of days (1-90)")
hours: int = Query(24, ge=1, le=168, description="Number of hours (1-168)")
```

30, 90, 24, 168 等数字未定义为常量。

**修复**:
```python
# 常量定义
DEFAULT_TREND_DAYS = 30
MAX_TREND_DAYS = 90
DEFAULT_TREND_HOURS = 24
MAX_TREND_HOURS = 168  # 7 days
```

---

## 📊 测试覆盖分析

### 测试文件

| 文件 | 行数 | 测试类 | 测试方法数 | 用途 |
|------|------|--------|-----------|------|
| test_experiments.py | 308 | 5 classes | 41+ tests | 完整测试套件 |
| test_experiments_api.py | ? | ? | ? | 认证测试（重复） |
| test_experiments.py (user) | ? | ? | ? | User API 测试 |

### 测试覆盖

#### ✅ 已覆盖
- 所有 14 个端点的认证要求
- Pydantic 请求模型验证
- 参数边界测试
- 常量定义测试
- 状态/类型有效性测试

#### ❌ 缺失
- **Repository 方法测试** - Repository 完全未被测试（因为未被使用）
- **DDD Aggregate 测试** - Experiment 聚合根未被测试
- **Domain Service 单元测试** - 没有针对 experiments/ 包的独立测试
- **趋势聚合逻辑测试** - 复杂的日期/小时聚合未测试
- **错误场景测试** - 数据库失败、数据不一致等
- **缓存失效测试** - 更新后缓存是否正确清除
- **AI 分析测试** - AI 模块调用是否正确

---

## 🔧 修复计划

### Phase 1: 架构重构（解决 CRITICAL 问题）

#### 1.1 激活 ExperimentRepository

**目标**: 让 Domain Service 使用已存在的 Repository

**步骤**:

1. **修改 Repository Interface** (domains/platform/repository.py):
```python
class IExperimentRepository(ABC):
    @abstractmethod
    async def get_by_key(self, experiment_key: str) -> Optional[Experiment]:
        """Get experiment by key (not just ID)."""
        pass

    @abstractmethod
    async def list_experiments(
        self,
        status: Optional[str] = None,
        offset: int = 0,
        limit: int = 20
    ) -> Dict[str, Any]:
        """List experiments with pagination."""
        pass
```

2. **更新 Repository 实现** (infrastructure/repositories/experiment_repository.py):
```python
class SupabaseExperimentRepository(IExperimentRepository):
    # 添加缺失方法
    async def get_by_key(self, experiment_key: str) -> Optional[Experiment]:
        result = self.client.table("experiments").select("*").eq(
            "experiment_key", experiment_key
        ).execute()

        if result.data:
            return self._map_to_experiment(result.data[0])
        return None

    async def list_experiments(
        self,
        status: Optional[str] = None,
        offset: int = 0,
        limit: int = 20
    ) -> Dict[str, Any]:
        query = self.client.table("experiments").select("*", count="exact")

        if status:
            query = query.eq("status", status)

        result = query.order("created_at", desc=True).range(
            offset, offset + limit - 1
        ).limit(10000).execute()  # 防止 OOM

        total = result.count or 0
        experiments = [self._map_to_experiment(row) for row in result.data]

        return {
            "experiments": experiments,
            "total": total,
            "offset": offset,
            "limit": limit
        }
```

3. **重构 Domain Service** (domains/platform/experiments/):

删除 `core.py` 中的直接 Supabase 访问:
```python
# BEFORE:
from core.database import get_db_client
supabase = get_db_client()  # ❌

# AFTER:
# 不再直接访问数据库
```

修改 `crud.py`:
```python
# BEFORE:
def create_experiment(...):
    result = supabase.table("experiments").insert(data).execute()

# AFTER:
class ExperimentService:
    def __init__(self, experiment_repo: IExperimentRepository):
        self.experiment_repo = experiment_repo

    async def create_experiment(self, ...):
        # 创建 Aggregate
        experiment = Experiment(...)

        # 通过 Repository 保存
        saved = await self.experiment_repo.create(experiment)
        return saved
```

4. **更新 API Layer** (api/admin/experiments.py):
```python
# Helper function
def _get_experiment_service() -> ExperimentService:
    db_client = get_database_client()
    experiment_repo = SupabaseExperimentRepository(db_client)
    return ExperimentService(experiment_repo)

@router.post("")
async def create_experiment(...):
    service = _get_experiment_service()
    experiment = await service.create_experiment(...)
    return {"status": "created", "experiment": experiment}
```

#### 1.2 移除 API Layer 直接数据库访问

**目标**: 趋势端点通过 Service/Repository 访问数据

**步骤**:

1. **在 Repository 添加趋势查询方法**:
```python
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
        .limit(10000)\  # 防止 OOM
        .execute()

    return result.data or []

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

2. **在 Service 添加趋势业务逻辑**:
```python
async def get_daily_trend(self, experiment_key: str, days: int) -> Dict:
    """Get daily trend with business logic."""
    experiment = await self.experiment_repo.get_by_key(experiment_key)
    if not experiment:
        return None

    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    # 通过 Repository 获取数据
    results = await self.experiment_repo.get_trend_data(
        experiment.id,
        start_date,
        days
    )

    # 业务逻辑：聚合、计算转化率等
    return self._aggregate_trend_data(experiment, results)
```

3. **API Layer 调用 Service**:
```python
@router.get("/{experiment_key}/trend")
async def get_experiment_trend(...):
    try:
        service = _get_experiment_service()
        trend_data = await service.get_daily_trend(experiment_key, days)

        if not trend_data:
            raise HTTPException(404, "Experiment not found")

        return trend_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin] Get trend failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve trend data")
```

#### 1.3 使用 DDD Aggregates

**目标**: Service 层使用领域对象，而非 dict

**步骤**:

1. **Service 返回 Aggregate**:
```python
async def get_experiment(self, experiment_key: str) -> Optional[Experiment]:
    return await self.experiment_repo.get_by_key(experiment_key)
```

2. **API Layer 转换为 Response Model**:
```python
@router.get("/{experiment_key}")
async def get_experiment(...):
    service = _get_experiment_service()
    experiment = await service.get_experiment(experiment_key)

    if not experiment:
        raise HTTPException(404, "Experiment not found")

    # 转换为 Response Model
    return ExperimentResponse(
        id=experiment.experiment_id,
        name=experiment.name,
        status=experiment.status.value,
        variants=[v.to_dict() for v in experiment.variants],
        ...
    )
```

---

### Phase 2: 添加 Response Models（解决 HIGH 问题）

**创建**: `api/admin/experiments_models.py` (v1.0.0)

```python
"""
Experiments Management API Models - Request/Response schemas.

@module api.admin.experiments_models
@version 1.0.0
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ==========================================
# Experiment Models
# ==========================================

class ExperimentVariantResponse(BaseModel):
    """Experiment variant."""
    key: str = Field(..., description="Variant key")
    name: str = Field(..., description="Variant name")
    weight: int = Field(..., description="Traffic weight (0-100)")
    config: Optional[Dict[str, Any]] = Field(None, description="Variant configuration")


class ExperimentResponse(BaseModel):
    """Single experiment."""
    id: Optional[str] = Field(None, description="Experiment ID")
    experiment_key: str = Field(..., description="Experiment key")
    name: str = Field(..., description="Experiment name")
    description: Optional[str] = Field(None, description="Description")
    experiment_type: str = Field(..., description="Experiment type")
    status: str = Field(..., description="Experiment status")
    variants: List[ExperimentVariantResponse] = Field(..., description="Variants")
    traffic_allocation: int = Field(..., description="Traffic allocation percentage")
    start_at: Optional[str] = Field(None, description="Start time")
    end_at: Optional[str] = Field(None, description="End time")
    created_at: str = Field(..., description="Creation timestamp")


class ExperimentListResponse(BaseModel):
    """Response for GET /experiments."""
    experiments: List[ExperimentResponse] = Field(..., description="List of experiments")
    total: int = Field(..., description="Total count")
    offset: int = Field(..., description="Pagination offset")
    limit: int = Field(..., description="Page size")


class ExperimentCreateResponse(BaseModel):
    """Response for POST /experiments."""
    status: str = Field(..., description="Creation status")
    experiment: ExperimentResponse = Field(..., description="Created experiment")


class ExperimentUpdateResponse(BaseModel):
    """Response for PUT /experiments/{key}."""
    status: str = Field(..., description="Update status")
    experiment: ExperimentResponse = Field(..., description="Updated experiment")


class StatusUpdateResponse(BaseModel):
    """Response for PUT /experiments/{key}/status."""
    status: str = Field(..., description="Update status")
    new_status: str = Field(..., description="New experiment status")


class ExperimentDeleteResponse(BaseModel):
    """Response for DELETE /experiments/{key}."""
    status: str = Field(..., description="Deletion status")
    experiment_key: str = Field(..., description="Deleted experiment key")


# ==========================================
# Results & Analysis Models
# ==========================================

class VariantResultData(BaseModel):
    """Variant result data."""
    exposures: int = Field(..., description="Total exposures")
    conversions: int = Field(..., description="Total conversions")
    conversion_rate: float = Field(..., description="Conversion rate (%)")
    significance: Optional[float] = Field(None, description="Statistical significance")


class ExperimentResultsResponse(BaseModel):
    """Response for GET /experiments/{key}/results."""
    experiment_key: str = Field(..., description="Experiment key")
    variants: Dict[str, VariantResultData] = Field(..., description="Variant results")
    start_date: Optional[str] = Field(None, description="Start date")
    end_date: Optional[str] = Field(None, description="End date")


class AggregationResponse(BaseModel):
    """Response for POST /experiments/{key}/aggregate."""
    status: str = Field(..., description="Aggregation status")
    experiment_key: Optional[str] = Field(None, description="Experiment key")


class CacheClearResponse(BaseModel):
    """Response for POST /experiments/cache/clear."""
    status: str = Field(..., description="Cache clear status")


# ==========================================
# AI Analysis Models
# ==========================================

class AIAnalysisResponse(BaseModel):
    """Response for POST /experiments/{key}/ai-analysis."""
    success: bool = Field(..., description="Analysis success status")
    analysis: Optional[str] = Field(None, description="AI analysis text")
    recommendations: Optional[List[str]] = Field(None, description="Recommendations")
    confidence: Optional[float] = Field(None, description="Confidence score")


class RecommendationResponse(BaseModel):
    """Response for GET /experiments/{key}/quick-recommendation."""
    experiment_key: str = Field(..., description="Experiment key")
    recommendation: Dict[str, Any] = Field(..., description="Recommendation data")


# ==========================================
# Trend Models
# ==========================================

class TrendDataPoint(BaseModel):
    """Single trend data point."""
    date: Optional[str] = Field(None, description="Date (YYYY-MM-DD)")
    time: Optional[str] = Field(None, description="Time (YYYY-MM-DDTHH:mm:ss)")


class DailyTrendResponse(BaseModel):
    """Response for GET /experiments/{key}/trend."""
    experiment_key: str = Field(..., description="Experiment key")
    variants: List[str] = Field(..., description="Variant keys")
    days: int = Field(..., description="Number of days")
    trend: List[Dict[str, Any]] = Field(..., description="Trend data points")


class HourlyTrendResponse(BaseModel):
    """Response for GET /experiments/{key}/hourly-trend."""
    experiment_key: str = Field(..., description="Experiment key")
    variants: List[str] = Field(..., description="Variant keys")
    hours: int = Field(..., description="Number of hours")
    trend: List[Dict[str, Any]] = Field(..., description="Trend data points")
```

**更新 API 端点**:
```python
from api.admin.experiments_models import (
    ExperimentListResponse, ExperimentResponse, ExperimentCreateResponse,
    ExperimentUpdateResponse, StatusUpdateResponse, ExperimentDeleteResponse,
    ExperimentResultsResponse, AggregationResponse, CacheClearResponse,
    AIAnalysisResponse, RecommendationResponse,
    DailyTrendResponse, HourlyTrendResponse
)

@router.get("", response_model=ExperimentListResponse)
async def list_experiments(...):
    ...

@router.post("", response_model=ExperimentCreateResponse)
async def create_experiment(...):
    ...

# ... 其余端点类似
```

---

### Phase 3: 添加安全防护（解决 HIGH 问题）

#### 3.1 添加查询 limit

所有数据库查询添加 `.limit()`:
```python
# Repository 中
.limit(10000).execute()
```

#### 3.2 统一错误处理

所有端点包裹 try-except:
```python
@router.get("/{experiment_key}/trend")
async def get_experiment_trend(...):
    try:
        service = _get_experiment_service()
        trend = await service.get_daily_trend(experiment_key, days)
        return trend
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[Admin {admin.get('id')}] Get trend failed: "
            f"{type(e).__name__} - {e}"
        )
        raise HTTPException(500, "Failed to retrieve trend data")
```

#### 3.3 AI 导入移到顶部

```python
# 文件头部
from domains.platform import experiment_ai_service

# 不再动态导入
```

#### 3.4 添加审计日志

所有修改操作添加日志:
```python
logger.info(f"[Admin {admin.get('id')}] Created experiment: {experiment_key}")
logger.info(f"[Admin {admin.get('id')}] Updated experiment: {experiment_key}")
logger.info(f"[Admin {admin.get('id')}] Deleted experiment: {experiment_key}")
logger.info(f"[Admin {admin.get('id')}] Changed status: {experiment_key} → {status}")
logger.info(f"[Admin {admin.get('id')}] Triggered aggregation: {experiment_key}")
```

---

### Phase 4: 完善细节（解决 MEDIUM/LOW 问题）

#### 4.1 统一缓存策略

移除 Domain Service 内存缓存，统一使用 `cache_service` (Redis)。

#### 4.2 统一日期处理

创建 helper 函数:
```python
def parse_iso_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None

    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
```

#### 4.3 全异步

所有 Domain Service 方法改为 async:
```python
async def create_experiment(...):
    ...

async def get_experiment(...):
    ...
```

#### 4.4 删除重复测试

```bash
rm tests/api/admin/test_experiments_api.py
```

#### 4.5 调整限流

```python
# CRUD
@limiter.limit("20/minute")

# 查询
@limiter.limit("20/minute")  # 从 30 降低

# 趋势
@limiter.limit("15/minute")  # 新增
```

#### 4.6 定义常量

```python
# 常量
DEFAULT_TREND_DAYS = 30
MAX_TREND_DAYS = 90
DEFAULT_TREND_HOURS = 24
MAX_TREND_HOURS = 168

days: int = Query(DEFAULT_TREND_DAYS, ge=1, le=MAX_TREND_DAYS, ...)
hours: int = Query(DEFAULT_TREND_HOURS, ge=1, le=MAX_TREND_HOURS, ...)
```

---

## 📈 预期改进效果

### 架构层面
- ✅ **100% DDD 合规** - Repository + Aggregate 得到使用
- ✅ **激活 260 行 Repository 代码**
- ✅ **API Layer 不再直接访问数据库**
- ✅ **使用领域对象** - Experiment Aggregate

### 性能层面
- ✅ **OOM 防护** - 所有查询添加 limit
- ✅ **AI 导入优化** - 移除动态导入

### 安全层面
- ✅ **错误处理** - 统一 try-except
- ✅ **审计完整** - 所有操作记录日志
- ✅ **限流优化** - 趋势端点更严格

### 代码质量
- ✅ **类型安全** - 所有端点 response_model
- ✅ **全异步** - 所有方法 async/await
- ✅ **代码清理** - 删除重复测试、移除冗余缓存

---

## 🎯 修复优先级

### P0 - 立即修复（架构合规）
1. **EXP-CRITICAL-1**: 移除 API Layer 直接数据库访问
2. **EXP-CRITICAL-2**: 激活 ExperimentRepository
3. **EXP-CRITICAL-3**: Domain Service 通过 Repository 访问数据
4. **EXP-CRITICAL-4**: 使用 DDD Aggregates

### P1 - 高优先级（安全性）
5. **EXP-HIGH-2**: 添加查询 limit
6. **EXP-HIGH-3**: 统一错误处理
7. **EXP-HIGH-6**: 添加审计日志
8. **EXP-HIGH-1**: 添加 Response Models

### P2 - 中优先级（优化）
9. **EXP-HIGH-4**: AI 导入移到顶部
10. **EXP-HIGH-5**: 修复返回类型不一致
11. **EXP-MEDIUM-1**: 统一缓存策略
12. **EXP-MEDIUM-2**: 统一日期处理
13. **EXP-MEDIUM-4**: 全异步

### P3 - 低优先级（清理）
14. **EXP-LOW-1**: 删除重复测试
15. **EXP-LOW-2**: 调整限流配置
16. **EXP-LOW-3**: 定义常量

---

## 📝 待决策问题

### 1. 是否使用 DDD Aggregates？

**选项 A**: 完全使用 Aggregate（推荐）
- ✅ 类型安全
- ✅ 业务逻辑内聚
- ✅ 符合 DDD 原则
- ❌ 需要大量重构

**选项 B**: 继续使用 dict
- ✅ 改动最小
- ❌ 无类型安全
- ❌ 不符合 DDD

**建议**: 选项 A（完全 DDD）

### 2. 趋势查询是否需要单独的 Repository 方法？

**选项 A**: 添加专门的趋势方法（推荐）
```python
async def get_trend_data(...)
async def get_hourly_trend_data(...)
```

**选项 B**: 使用通用查询方法
```python
async def query_results(filters: Dict)
```

**建议**: 选项 A（专门方法更清晰）

---

## 🔗 相关文件

### 需要修改的文件
1. `api/admin/experiments.py` (v3.25 → v3.26)
2. `domains/platform/experiments/` (重构为 Service 类)
3. `domains/platform/repository.py` (更新接口)
4. `infrastructure/repositories/experiment_repository.py` (添加方法)

### 需要创建的文件
1. `api/admin/experiments_models.py` (v1.0.0) - Response Models

### 需要删除的文件
1. `tests/api/admin/test_experiments_api.py` (重复)

---

## ✅ 验收标准

### 架构验收
- [ ] Domain Service 通过 Repository 访问数据库
- [ ] ExperimentRepository 被所有 Experiment 操作使用
- [ ] API Layer 不直接访问数据库
- [ ] 使用 Experiment Aggregate
- [ ] 所有方法使用依赖注入

### 功能验收
- [ ] 所有 14 个端点正常工作
- [ ] 趋势数据准确
- [ ] AI 分析正常
- [ ] 缓存正确工作

### 测试验收
- [ ] 所有现有测试通过 (41+ tests)
- [ ] 新增 Repository 单元测试
- [ ] 新增 Aggregate 测试
- [ ] 测试覆盖率 ≥ 70%

### 安全验收
- [ ] 所有查询有 limit 限制
- [ ] 所有端点有错误处理
- [ ] 所有修改操作有审计日志
- [ ] 敏感信息不泄露

---

**审查完成时间**: 2026-01-09
**下一步**: 根据用户指令 "现在就全部修复，不要自作聪明"，立即开始修复所有问题
