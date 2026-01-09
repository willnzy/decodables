# Metrics 模块深度审查报告

> **审查日期**: 2026-01-09
> **审查版本**: v3.28 (Target)
> **审查标准**: ⭐⭐⭐⭐⭐ 5星深度审查
> **接口数量**: 7个
> **当前版本**: v3.25 (基础安全审查完成)

---

## 执行摘要

### 审查范围

完整调用链分析:
1. ✅ API Layer (`api/admin/metrics.py` - 246 lines)
2. ✅ Scheduler Module (`scheduler.py`)
3. ✅ Database Schema (daily_metrics, monthly_metrics, aggregated_stats, user_events, error_logs)
4. ✅ Test Coverage (`tests/api/admin/test_metrics.py` - 189 lines)

### 已完成工作 (v3.25)

v3.25 完成了基础安全审查:
- ✅ Rate limiting (所有接口)
- ✅ 参数验证 (date format, months, hours, days, period, metric_type)
- ✅ 错误信息清理 (不暴露敏感信息)
- ✅ 常量定义 (DATE_PATTERN, VALID_PERIODS, VALID_METRIC_TYPES)

### 发现问题汇总

| 严重度 | 数量 | 问题 ID |
|--------|------|---------|
| 🔴 CRITICAL | 1 | MET-CRITICAL-1 |
| 🔴 HIGH | 5 | MET-HIGH-1, MET-HIGH-2, MET-HIGH-3, MET-HIGH-4, MET-HIGH-5 |
| 🟡 MEDIUM | 6 | MET-MEDIUM-1 ~ MET-MEDIUM-6 |
| 🟢 LOW | 3 | MET-LOW-1 ~ MET-LOW-3 |
| **总计** | **15** | |

---

## 接口调用链分析

### 接口 #1: `GET /metrics/daily`

**调用链**:
```
API: get_daily_metrics()
  → supabase.table("daily_metrics").select("*")
    .gte("date", start_date)
    .lte("date", end_date)
    .order("date")
    .execute()
  → DB: daily_metrics (直接访问)
```

**🔴 问题**:
1. **MET-CRITICAL-1**: API 直接访问数据库，违反 DDD 架构
2. **MET-HIGH-1**: 缺少查询数量限制 (OOM 风险)
3. **MET-HIGH-2**: 缺少 Pydantic Response Model
4. **MET-MEDIUM-1**: 缺少 @retry_on_network_error 装饰器

**当前代码** (Line 92):
```python
result = supabase.table("daily_metrics").select("*").gte("date", start_date).lte("date", end_date).order("date").execute()
return {"metrics": result.data or [], "start_date": start_date, "end_date": end_date}
```

**风险分析**:
- ❌ 如果用户查询 1 年的数据 (365 天)，无 limit 保护
- ❌ 没有 Repository 抽象，无法统一添加重试、审计、监控
- ❌ 返回原始 dict，类型不安全

---

### 接口 #2: `GET /metrics/monthly`

**调用链**:
```
API: get_monthly_metrics()
  → supabase.table("monthly_metrics").select("*")
    .order("month", desc=True)
    .limit(months)  # ✅ 有 limit
    .execute()
  → DB: monthly_metrics (直接访问)
```

**🟡 问题**:
1. **MET-CRITICAL-1**: 同上，违反 DDD
2. **MET-HIGH-2**: 缺少 Pydantic Response Model
3. **MET-MEDIUM-1**: 缺少 @retry_on_network_error

**当前代码** (Line 110):
```python
result = supabase.table("monthly_metrics").select("*").order("month", desc=True).limit(months).execute()
return {"metrics": result.data or [], "months": months}
```

**优点**:
- ✅ 有 limit (参数范围 1-24)

---

### 接口 #3: `GET /metrics/retention`

**调用链**:
```
API: get_retention_metrics()
  → supabase.table("aggregated_stats").select("data")
    .eq("stat_type", "user_retention_30d")
    .order("date", desc=True)
    .limit(1)  # ✅ 有 limit
    .execute()
  → DB: aggregated_stats (直接访问)
```

**🟡 问题**:
1. **MET-CRITICAL-1**: 同上，违反 DDD
2. **MET-HIGH-2**: 缺少 Pydantic Response Model
3. **MET-MEDIUM-1**: 缺少 @retry_on_network_error
4. **MET-LOW-1**: 返回类型不一致 (可能是 {} 或 dict)

**当前代码** (Line 125-128):
```python
result = supabase.table("aggregated_stats").select("data").eq("stat_type", "user_retention_30d").order("date", desc=True).limit(1).execute()
if result.data:
    return result.data[0].get("data", {})
return {}
```

**优点**:
- ✅ 只查询最新的 1 条记录

---

### 接口 #4: `GET /metrics/funnel`

**调用链**:
```
API: get_funnel_metrics()
  → 循环 6 次:
      supabase.table("user_events").select("id", count="exact")
        .eq("event_type", step["query"])
        .execute()
  → DB: user_events (直接访问，6 次查询)
```

**🔴 问题**:
1. **MET-CRITICAL-1**: 同上，违反 DDD
2. **MET-HIGH-2**: 缺少 Pydantic Response Model
3. **MET-HIGH-3**: **N+6 查询问题** (每个 funnel step 单独查询)
4. **MET-HIGH-4**: **查询无时间范围限制** (period 参数未使用!)
5. **MET-MEDIUM-1**: 缺少 @retry_on_network_error
6. **MET-MEDIUM-2**: **性能问题** - 6 次独立查询，可优化为 1 次聚合查询

**当前代码** (Line 148-166):
```python
# 定义 funnel steps
steps = [
    {"name": "visitors", "query": "page_view"},
    {"name": "signups", "query": "user_created"},
    {"name": "first_project", "query": "project_create"},
    {"name": "first_generation", "query": "ai_generate"},
    {"name": "first_export", "query": "download_pdf"},
    {"name": "payment", "query": "payment_success"},
]

funnel_data = []
for step in steps:
    count_result = supabase.table("user_events").select("id", count="exact").eq("event_type", step["query"]).execute()
    funnel_data.append({
        "step": step["name"],
        "count": count_result.count or 0
    })

return {"funnel": funnel_data, "period": period}
```

**严重风险**:
- ❌ **period 参数完全未使用** - 前端传 "7d" 和 "90d" 结果完全一样!
- ❌ 查询整个 user_events 表的所有历史数据，无时间限制
- ❌ 性能差: 6 次独立查询

---

### 接口 #5: `GET /metrics/errors`

**调用链**:
```
API: get_error_metrics()
  → supabase.table("error_logs").select("error_type, status_code")
    .gte("created_at", cutoff)
    .execute()
  → DB: error_logs (直接访问，无 limit)
```

**🔴 问题**:
1. **MET-CRITICAL-1**: 同上，违反 DDD
2. **MET-HIGH-1**: **缺少查询数量限制** (如果 24 小时内有 10 万条错误日志，全部加载到内存)
3. **MET-HIGH-2**: 缺少 Pydantic Response Model
4. **MET-MEDIUM-1**: 缺少 @retry_on_network_error
5. **MET-MEDIUM-3**: 聚合逻辑在 API 层，应该在 Repository/Service 层

**当前代码** (Line 184-202):
```python
cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

result = supabase.table("error_logs").select("error_type, status_code").gte("created_at", cutoff).execute()

errors = result.data or []
by_type = {}
by_status = {}

for err in errors:
    t = err.get("error_type", "UNKNOWN")
    by_type[t] = by_type.get(t, 0) + 1

    s = err.get("status_code", 0)
    by_status[s] = by_status.get(s, 0) + 1

return {
    "total": len(errors),
    "hours": hours,
    "by_type": by_type,
    "by_status": by_status
}
```

**严重风险**:
- ❌ 无 `.limit()` - 如果 24 小时内有大量错误，会 OOM
- ❌ 聚合逻辑在 Python 代码中，应该用 SQL GROUP BY

---

### 接口 #6: `GET /metrics/dau-trend`

**调用链**:
```
API: get_dau_trend()
  → supabase.table("daily_metrics").select("date, dau")
    .order("date", desc=True)
    .limit(days)  # ✅ 有 limit
    .execute()
  → DB: daily_metrics (直接访问)
```

**🟡 问题**:
1. **MET-CRITICAL-1**: 同上，违反 DDD
2. **MET-HIGH-2**: 缺少 Pydantic Response Model
3. **MET-MEDIUM-1**: 缺少 @retry_on_network_error

**当前代码** (Line 218):
```python
result = supabase.table("daily_metrics").select("date, dau").order("date", desc=True).limit(days).execute()
return {"trend": result.data or [], "days": days}
```

**优点**:
- ✅ 有 limit (参数范围 1-365)

---

### 接口 #7: `POST /metrics/refresh`

**调用链**:
```
API: refresh_metrics()
  → scheduler.run_aggregation_now(metric_type)
    → run_hourly_aggregation() or run_daily_aggregation()
      → application.services.metrics.run_hourly_etl()
      → application.services.metrics.run_daily_etl()
      → application.services.aggregators.run_hourly_tasks()
      → application.services.aggregators.run_daily_tasks()
      → application.services.experiments.run_hourly_experiment_tasks()
      → application.services.experiments.run_daily_experiment_tasks()
```

**🟡 问题**:
1. **MET-HIGH-5**: **功能逻辑错误** - `metric_type` 参数验证了 5 个值 (all/daily/monthly/retention/funnel)，但实际只支持 3 个 (all/hourly/daily)
2. **MET-MEDIUM-4**: 缺少 Pydantic Response Model (虽然很简单)
3. **MET-MEDIUM-5**: **参数语义不一致** - 前端传 "daily"，但实际调用的是 `run_aggregation_now("daily")` → 触发整个 daily aggregation pipeline
4. **MET-LOW-2**: 函数直接 import scheduler，未通过依赖注入

**当前代码** (Line 230-245):
```python
# v3.25: MET-MEDIUM-7 - Added metric_type enum validation
metric_type: str = Query("all", max_length=50),

# v3.25: MET-MEDIUM-7 - Validate metric_type
if metric_type not in VALID_METRIC_TYPES:
    raise HTTPException(400, f"Invalid metric_type. Must be one of: {', '.join(VALID_METRIC_TYPES)}")

from scheduler import run_aggregation_now

try:
    result = run_aggregation_now(metric_type)
    return {"status": "refreshed", "type": metric_type, "result": result}
except Exception as e:
    logger.error(f"[Admin] Error refreshing metrics: {e}")
    raise HTTPException(500, "Failed to refresh metrics")
```

**问题分析**:
- ❌ VALID_METRIC_TYPES = {"all", "daily", "monthly", "retention", "funnel"}
- ❌ 但 `run_aggregation_now()` 只支持 "all", "hourly", "daily"
- ❌ 如果传 "monthly" → 会执行 "all" (默认分支)
- ❌ 如果传 "retention" → 会执行 "all"
- ❌ 如果传 "funnel" → 会执行 "all"

---

## 问题详细清单

### 🔴 CRITICAL (1个)

#### MET-CRITICAL-1: 所有接口直接访问数据库，违反 DDD 架构

**影响范围**: 全部 7 个接口

**问题描述**:
- API Layer 直接使用 `supabase.table().select().execute()`
- 没有 Repository 抽象层
- 无法统一添加:
  - 重试机制 (@retry_on_network_error)
  - 审计日志
  - 性能监控
  - 错误处理

**修复方案**:
1. 创建 `infrastructure/repositories/metrics_repository.py`
2. 定义 `MetricsRepository` 接口 (Protocol)
3. 实现 `SupabaseMetricsRepository`
4. 所有 Repository 方法添加 `@retry_on_network_error`
5. API Layer 通过依赖注入使用 Repository

**参考**: Config 模块 v3.26, Stats 模块 v3.26, Tasks 模块 v3.27

---

### 🔴 HIGH (5个)

#### MET-HIGH-1: 2个接口查询无数量限制 (OOM 风险)

**影响接口**:
- `GET /metrics/daily` (Line 92) - 可能查询 365 天数据
- `GET /metrics/errors` (Line 184) - 可能查询 168 小时内的所有错误

**风险**:
- 如果 daily_metrics 有 1 年数据 (365 条)，全部加载
- 如果 24 小时内有 10 万条错误日志，全部加载到内存 → OOM

**修复方案**:
```python
# daily_metrics - 添加合理 limit
result = supabase.table("daily_metrics").select("*")\
    .gte("date", start_date)\
    .lte("date", end_date)\
    .order("date")\
    .limit(366)  # 最多 1 年 + 1 天
    .execute()

# error_logs - 添加 limit + 使用 SQL 聚合
# 方案1: 限制数据量
result = supabase.table("error_logs").select("error_type, status_code")\
    .gte("created_at", cutoff)\
    .limit(10000)  # 最多查询 1 万条
    .execute()

# 方案2 (推荐): 使用 PostgreSQL 聚合函数
# 通过 Repository 层使用原生 SQL:
# SELECT error_type, status_code, COUNT(*) as count
# FROM error_logs
# WHERE created_at >= $1
# GROUP BY error_type, status_code
```

---

#### MET-HIGH-2: 所有接口缺少 Pydantic Response Models

**影响范围**: 全部 7 个接口

**问题描述**:
- 所有接口返回原始 dict
- 类型不安全
- 前端无法自动生成类型定义

**修复方案**:
创建 `api/admin/metrics_models.py`:

```python
from pydantic import BaseModel
from typing import List, Dict, Optional

class DailyMetricItem(BaseModel):
    date: str
    dau: int
    mau: int
    new_users: int
    # ... 其他字段

class DailyMetricsResponse(BaseModel):
    metrics: List[DailyMetricItem]
    start_date: str
    end_date: str

class MonthlyMetricItem(BaseModel):
    month: str
    total_users: int
    # ... 其他字段

class MonthlyMetricsResponse(BaseModel):
    metrics: List[MonthlyMetricItem]
    months: int

class RetentionMetricsResponse(BaseModel):
    day_1: Optional[float] = None
    day_7: Optional[float] = None
    day_30: Optional[float] = None

class FunnelStepData(BaseModel):
    step: str
    count: int

class FunnelMetricsResponse(BaseModel):
    funnel: List[FunnelStepData]
    period: str

class ErrorMetricsResponse(BaseModel):
    total: int
    hours: int
    by_type: Dict[str, int]
    by_status: Dict[int, int]

class DAUTrendItem(BaseModel):
    date: str
    dau: int

class DAUTrendResponse(BaseModel):
    trend: List[DAUTrendItem]
    days: int

class RefreshMetricsResponse(BaseModel):
    status: str
    type: str
    result: Dict[str, str]
```

---

#### MET-HIGH-3: Funnel 接口 N+6 查询问题

**位置**: `GET /metrics/funnel` (Line 160-164)

**问题描述**:
- 循环 6 次查询数据库
- 每个 funnel step 独立查询 user_events 表

**性能影响**:
```
当前: 6 次 SELECT COUNT(*) 查询 (串行)
优化后: 1 次 GROUP BY 查询
```

**修复方案**:
```python
# Repository 层使用单次聚合查询
async def get_funnel_counts(
    self,
    event_types: List[str],
    start_date: str,
    end_date: str
) -> Dict[str, int]:
    """Get event counts for funnel analysis with single query."""
    # SQL:
    # SELECT event_type, COUNT(*) as count
    # FROM user_events
    # WHERE event_type IN ($1, $2, ..., $6)
    #   AND created_at >= $7
    #   AND created_at <= $8
    # GROUP BY event_type
```

---

#### MET-HIGH-4: Funnel 接口 period 参数完全未使用

**位置**: `GET /metrics/funnel` (Line 139-169)

**问题描述**:
- 接口接收 `period` 参数 (7d/14d/30d/60d/90d)
- 但查询时没有添加时间范围过滤
- **查询整个 user_events 表的所有历史数据**
- 前端传 "7d" 和 "90d" 结果完全一样

**业务影响**:
- 数据不准确
- 性能差
- 功能失效

**修复方案**:
```python
# 根据 period 计算时间范围
period_days = {
    "7d": 7,
    "14d": 14,
    "30d": 30,
    "60d": 60,
    "90d": 90
}

days = period_days.get(period, 30)
cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

# 查询时添加时间过滤
for step in steps:
    count_result = supabase.table("user_events")\
        .select("id", count="exact")\
        .eq("event_type", step["query"])\
        .gte("created_at", cutoff)  # ✅ 添加时间过滤
        .execute()
```

---

#### MET-HIGH-5: refresh 接口参数语义不一致

**位置**: `POST /metrics/refresh` (Line 230-245)

**问题描述**:
- `VALID_METRIC_TYPES = {"all", "daily", "monthly", "retention", "funnel"}`
- 但 `run_aggregation_now()` 只支持 `{"all", "hourly", "daily"}`
- 传入 "monthly"/"retention"/"funnel" 都会执行 "all" (默认分支)

**代码冲突**:
```python
# metrics.py 验证
VALID_METRIC_TYPES = {"all", "daily", "monthly", "retention", "funnel"}

# scheduler.py 实现
def run_aggregation_now(task_type: str = "all"):
    if task_type == "hourly":
        run_hourly_aggregation()
    elif task_type == "daily":
        run_daily_aggregation()
    else:  # ❌ 其他值都执行 "all"
        run_daily_aggregation()
        run_hourly_aggregation()
```

**修复方案**:
1. 统一 metric_type 定义为 `{"all", "hourly", "daily"}`
2. 或在 scheduler.py 中添加对 "monthly"/"retention"/"funnel" 的支持

---

### 🟡 MEDIUM (6个)

#### MET-MEDIUM-1: 所有接口缺少 @retry_on_network_error

**影响范围**: 全部 7 个接口

**问题描述**:
- 数据库查询无重试机制
- 网络瞬时故障会直接失败

**修复方案**:
- 通过 Repository 层统一添加 @retry_on_network_error 装饰器

---

#### MET-MEDIUM-2: Funnel 接口性能可优化

**位置**: `GET /metrics/funnel` (Line 160-164)

**问题描述**:
- 6 次独立查询，串行执行
- 可优化为 1 次 GROUP BY 查询

**性能提升**:
- 当前: ~600ms (6 × 100ms)
- 优化后: ~100ms (1 次查询)
- 提升: 6x

---

#### MET-MEDIUM-3: Error 接口聚合逻辑在 API 层

**位置**: `GET /metrics/errors` (Line 187-195)

**问题描述**:
- Python 代码中循环聚合
- 应该使用 SQL GROUP BY

**修复方案**:
```python
# Repository 层使用原生 SQL
async def get_error_stats(self, hours: int) -> Dict[str, Any]:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    # SQL GROUP BY 聚合
    query = """
        SELECT
            error_type,
            status_code,
            COUNT(*) as count
        FROM error_logs
        WHERE created_at >= %s
        GROUP BY error_type, status_code
        ORDER BY count DESC
        LIMIT 100
    """
    # 执行查询并处理结果
```

---

#### MET-MEDIUM-4: refresh 接口缺少 Response Model

**位置**: `POST /metrics/refresh` (Line 242)

**问题描述**:
- 返回原始 dict
- 虽然简单，但为了一致性应该有 Response Model

---

#### MET-MEDIUM-5: refresh 接口参数语义不清晰

**位置**: `POST /metrics/refresh` (Line 230)

**问题描述**:
- 参数名 `metric_type` 让人以为是刷新某个具体 metric (daily/monthly/retention)
- 实际是刷新整个 aggregation pipeline
- 应该改名为 `aggregation_type` 或 `task_type`

---

#### MET-MEDIUM-6: daily 接口默认查询 30 天可能过长

**位置**: `GET /metrics/daily` (Line 86-89)

**问题描述**:
- 如果不传参数，默认查询 30 天
- 对于 dashboard 首页，可能只需要 7 天

**修复建议**:
- 考虑改为默认 7 天
- 或前端明确传参

---

### 🟢 LOW (3个)

#### MET-LOW-1: retention 接口返回类型不一致

**位置**: `GET /metrics/retention` (Line 125-131)

**问题描述**:
- 有数据时返回 `result.data[0].get("data", {})`
- 无数据时返回 `{}`
- 类型一致但语义不够清晰

**修复建议**:
- 使用 Pydantic Response Model 明确类型

---

#### MET-LOW-2: refresh 接口直接 import scheduler

**位置**: `POST /metrics/refresh` (Line 238)

**问题描述**:
```python
from scheduler import run_aggregation_now
```
- 函数内 import
- 未通过依赖注入
- 不利于测试

**修复建议**:
- 移到文件顶部
- 或通过依赖注入

---

#### MET-LOW-3: 测试覆盖率不足

**位置**: `tests/api/admin/test_metrics.py`

**当前测试**:
- ✅ 7 个接口的 auth 测试
- ✅ 常量定义测试
- ✅ 验证函数测试
- ✅ 参数范围测试
- ❌ 缺少业务逻辑测试 (mock 数据库响应)
- ❌ 缺少错误场景测试
- ❌ 缺少边界条件测试

**目标覆盖率**: >90%

---

## 修复方案总览

### Phase 1: 架构重构 (DDD)

**目标**: 解决 MET-CRITICAL-1

1. **创建 MetricsRepository**
   - `infrastructure/repositories/metrics_repository.py`
   - 定义 MetricsRepository 接口 (Protocol)
   - 实现 SupabaseMetricsRepository
   - 所有方法添加 @retry_on_network_error
   - 添加查询 limit 保护

2. **创建 MetricsService (可选)**
   - `domains/metrics/metrics_service.py`
   - 处理业务逻辑 (如 funnel 数据组装)
   - 如果逻辑简单，可以跳过，直接 API → Repository

3. **重构 API Layer**
   - 通过依赖注入使用 Repository
   - 移除直接数据库访问
   - 精简为纯粹的请求/响应处理

### Phase 2: Response Models

**目标**: 解决 MET-HIGH-2

1. 创建 `api/admin/metrics_models.py`
2. 定义 7 个 Response Models
3. 更新所有接口签名

### Phase 3: 业务逻辑修复

**目标**: 解决 MET-HIGH-3, MET-HIGH-4, MET-HIGH-5

1. **Funnel 接口优化**:
   - 添加时间范围过滤 (使用 period 参数)
   - 优化为单次 GROUP BY 查询

2. **Error 接口优化**:
   - 添加 limit
   - 使用 SQL 聚合

3. **Refresh 接口修复**:
   - 统一 metric_type 定义
   - 更新文档说明

### Phase 4: 测试完善

**目标**: 解决 MET-LOW-3

1. 编写 Repository 层单元测试
2. 编写 API 层集成测试 (mock Repository)
3. 测试覆盖率达到 >90%

---

## 预期成果

### 代码质量指标

| 指标 | 当前 | 目标 | 提升 |
|------|------|------|------|
| DDD 架构合规 | 0% | 100% | +100% |
| Response Models | 0/7 | 7/7 | +100% |
| 查询保护 (limit) | 4/7 | 7/7 | +43% |
| 重试机制 | 0/7 | 7/7 | +100% |
| 测试覆盖率 | ~40% | >90% | +125% |
| 代码行数 | 246 | ~200 (API) + 300 (Repo) | - |

### 架构对比

**Before (v3.25)**:
```
API Layer (246 lines)
  ↓ 直接访问
Database (5 tables)
```

**After (v3.28)**:
```
API Layer (~150 lines)
  ↓ 依赖注入
Repository Layer (~300 lines)
  ↓ @retry_on_network_error
Database (5 tables)
```

### 性能提升

| 接口 | 优化项 | 提升 |
|------|--------|------|
| GET /metrics/funnel | 6次查询→1次 | 6x |
| GET /metrics/errors | Python聚合→SQL聚合 | 3x |
| GET /metrics/daily | 添加limit保护 | 稳定性↑ |

---

## 下一步行动

### 立即执行

1. ✅ 创建 `MetricsRepository` (infrastructure/repositories/metrics_repository.py)
2. ✅ 创建 Response Models (api/admin/metrics_models.py)
3. ✅ 重构 API Layer
4. ✅ 修复 Funnel/Error/Refresh 接口业务逻辑
5. ✅ 编写完整测试用例 (>90% coverage)
6. ✅ 运行测试验证
7. ✅ 更新文档
8. ✅ Git commit + push

### 验收标准

- ✅ 所有接口通过 Repository 访问数据库
- ✅ 所有接口有 Pydantic Response Models
- ✅ 所有查询有合理的 limit
- ✅ Funnel 接口正确使用 period 参数
- ✅ Error 接口使用 SQL 聚合
- ✅ Refresh 接口参数语义修复
- ✅ 测试覆盖率 >90%
- ✅ 所有测试通过

---

## 审查完成状态

- [x] 完整调用链分析
- [x] 问题识别和分类
- [ ] 问题修复 (待执行)
- [ ] 测试验证 (待执行)
- [ ] 文档更新 (待执行)

**预计修复时间**: 3-4 小时
**预计测试时间**: 1-2 小时
**总计**: 4-6 小时
