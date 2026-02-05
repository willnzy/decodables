# Analytics 系统设计

> **同步范围**: [backend]
> **状态**: 🟢 已验证 (来源: 代码分析 + v2 文档)
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `api/admin/stats.py`, `api/admin/metrics.py`, `api/admin/events.py`

---

## 一、概述

### 1.1 核心能力

| 模块 | 说明 |
|------|------|
| Stats | Dashboard KPI、业务统计 |
| Metrics | 系统指标、留存、漏斗 |
| Events | 事件追踪、聚合分析 |
| AI Insights | 智能洞察、建议 |

### 1.2 数据流

```
用户行为 → Event Tracking → Events 表
                              ↓
                         聚合任务
                              ↓
                       Aggregated Stats
                              ↓
                     Dashboard / Reports
```

---

## 二、Stats (业务统计)

### 2.1 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/admin/stats/dashboard` | GET | Dashboard KPI |
| `/api/admin/stats/user-growth` | GET | 用户增长 |
| `/api/admin/stats/revenue` | GET | 收入统计 |
| `/api/admin/stats/projects` | GET | 项目统计 |
| `/api/admin/stats/credits` | GET | 积分统计 |
| `/api/admin/stats/tier-distribution` | GET | Tier 分布 |
| `/api/admin/stats/conversion-funnel` | GET | 转化漏斗 |
| `/api/admin/stats/exports` | GET | 导出统计 |
| `/api/admin/stats/assets` | GET | 素材统计 |
| `/api/admin/stats/tier-activity` | GET | Tier 活跃度 |
| `/api/admin/stats/subscription-events` | GET | 订阅事件 |
| `/api/admin/stats/page-views` | GET | 页面浏览 |
| `/api/admin/stats/returning-users` | GET | 回访用户 |
| `/api/admin/stats/performance` | GET | 性能指标 |
| `/api/admin/stats/user-distribution` | GET | 用户分布 |

### 2.2 Dashboard KPI

```python
class DashboardStats:
    total_users: int
    new_users_today: int
    new_users_week: int
    
    total_revenue: float
    revenue_today: float
    revenue_week: float
    
    total_projects: int
    projects_today: int
    
    credits_used_today: int
    credits_used_week: int
    
    active_subscribers: int
    churn_rate: float
```

### 2.3 查询参数

```python
# 通用查询参数
class StatsQueryParams:
    period: Period = "week"  # week/month/quarter/year
    group_by: GroupBy = "day"  # hour/day/week/month
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class Period(str, Enum):
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"

class GroupBy(str, Enum):
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
```

---

## 三、Metrics (系统指标)

### 3.1 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v2/admin/metrics/daily` | GET | 日指标 |
| `/api/v2/admin/metrics/monthly` | GET | 月指标 |
| `/api/v2/admin/metrics/retention` | GET | 留存率 |
| `/api/v2/admin/metrics/funnel` | GET | 漏斗数据 |
| `/api/v2/admin/metrics/errors` | GET | 错误指标 |
| `/api/v2/admin/metrics/dau-trend` | GET | DAU 趋势 |
| `/api/v2/admin/metrics/refresh` | POST | 刷新指标 |

### 3.2 日指标

```python
class DailyMetrics:
    date: date
    signups: int           # 注册数
    active_users: int      # 活跃用户
    dau: int              # DAU
    projects_created: int  # 新建项目
    exports: int          # 导出次数
    revenue: float        # 收入
    credits_used: int     # 积分消耗
```

### 3.3 留存率

```python
class RetentionData:
    cohort_date: date
    day_1_retention: float   # 次日留存
    day_7_retention: float   # 7日留存
    day_14_retention: float  # 14日留存
    day_30_retention: float  # 30日留存
    
    cohorts: List[CohortRow]

class CohortRow:
    date: date
    users: int
    retention: List[float]  # [d1, d7, d14, d30]
```

### 3.4 转化漏斗

```python
class FunnelData:
    stages: List[FunnelStage]
    overall_conversion: float

class FunnelStage:
    name: str              # visit/signup/create_project/subscribe
    count: int
    conversion_rate: float # 相对上一步的转化率
```

---

## 四、Events (事件追踪)

### 4.1 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/admin/events/events` | GET | 事件列表 |
| `/api/admin/events/events/stats` | GET | 事件统计 |
| `/api/admin/events/aggregated/{stat_type}` | GET | 聚合数据 |
| `/api/admin/events/aggregated/{stat_type}/range` | GET | 范围聚合 |
| `/api/admin/events/aggregation/run` | POST | 执行聚合 |

### 4.2 事件类型

```python
class EventType(str, Enum):
    # 用户行为
    PAGE_VIEW = "page_view"
    SIGNUP = "signup"
    LOGIN = "login"
    
    # 项目操作
    PROJECT_CREATED = "project_created"
    PROJECT_SAVED = "project_saved"
    PROJECT_EXPORTED = "project_exported"
    
    # AI 使用
    AI_GENERATION_STARTED = "ai_generation_started"
    AI_GENERATION_COMPLETED = "ai_generation_completed"
    
    # 支付
    SUBSCRIPTION_CREATED = "subscription_created"
    CREDITS_PURCHASED = "credits_purchased"
```

### 4.3 事件数据结构

```python
class Event:
    id: UUID
    event_type: EventType
    user_id: Optional[UUID]
    session_id: str
    properties: dict       # 事件属性
    timestamp: datetime
    
    # 上下文
    page_url: str
    referrer: Optional[str]
    user_agent: str
    ip_address: str
    
    # 设备信息
    device_type: str
    browser: str
    os: str
    country: str
```

---

## 五、AI Insights

### 5.1 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/admin/ai/insights` | GET | AI 洞察 |
| `/api/admin/ai/recommendations` | GET | 推荐建议 |
| `/api/admin/ai/behavior-analysis` | GET | 行为分析 |
| `/api/admin/ai/generate-report` | POST | 生成报告 |
| `/api/admin/ai/quick-insights` | GET | 快速洞察 |

### 5.2 洞察类型

```python
class Insight:
    type: InsightType
    title: str
    description: str
    severity: Severity    # info/warning/critical
    data: dict
    recommendations: List[str]
    created_at: datetime

class InsightType(str, Enum):
    CHURN_RISK = "churn_risk"
    GROWTH_OPPORTUNITY = "growth_opportunity"
    ANOMALY_DETECTED = "anomaly_detected"
    TREND_CHANGE = "trend_change"
```

### 5.3 推荐建议

```python
class Recommendation:
    id: str
    category: str         # retention/growth/monetization
    title: str
    description: str
    impact: Impact        # high/medium/low
    effort: Effort        # high/medium/low
    priority_score: float
```

---

## 六、数据聚合

### 6.1 聚合任务

```python
AGGREGATION_TASKS = {
    "hourly": {
        "schedule": "0 * * * *",  # 每小时
        "metrics": ["page_views", "events"]
    },
    "daily": {
        "schedule": "0 2 * * *",  # 每天凌晨2点
        "metrics": ["dau", "revenue", "signups", "retention"]
    },
    "weekly": {
        "schedule": "0 3 * * 0",  # 每周日凌晨3点
        "metrics": ["wau", "conversion_funnel", "cohort_retention"]
    }
}
```

### 6.2 聚合存储

```sql
CREATE TABLE aggregated_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stat_type VARCHAR(50) NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    granularity VARCHAR(20) NOT NULL,  -- hourly/daily/weekly/monthly
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(stat_type, period_start, granularity)
);

CREATE INDEX idx_aggregated_stats_lookup 
ON aggregated_stats(stat_type, period_start, granularity);
```

---

## 七、用户分布维度

```python
class UserDistributionDimension(str, Enum):
    COUNTRY = "country"
    BROWSER = "browser"
    OS = "os"
    DEVICE_TYPE = "device_type"
    LANGUAGE = "language"
    TIMEZONE = "timezone"

# 查询示例
GET /api/admin/stats/user-distribution?dimension=country&period=month
```

---

## 八、相关文档

- [Admin API 端点](../../api/admin-endpoints.md)
- [Events 模块架构](../platform/architecture.md)
- [A/B 实验](../../../02-standards/feature-flag-engine.md)

---

**END OF DOCUMENT**
