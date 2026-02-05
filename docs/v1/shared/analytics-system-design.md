# Analytics 统一追踪系统设计

**文档版本**: v2.0  
**创建日期**: 2026-01-13  
**状态**: ✅ 已实施  
**负责人**: Make Decodables Team

---

## 目录

- [1. 系统概述](#1-系统概述)
- [2. 业务需求](#2-业务需求)
- [3. 架构设计](#3-架构设计)
- [4. 数据模型](#4-数据模型)
- [5. API 设计](#5-api-设计)
- [6. 实施细节](#6-实施细节)
- [7. 测试策略](#7-测试策略)
- [8. 监控和运维](#8-监控和运维)

---

## 1. 系统概述

### 1.1 背景

Analytics 系统负责追踪和记录用户行为事件，用于：
- 产品数据分析（用户行为、漏斗分析）
- 业务指标监控（日活、留存、转化率）
- 异常检测和告警
- 个性化推荐基础数据

### 1.2 设计目标

| 目标 | 描述 | 优先级 |
|------|------|--------|
| **统一性** | 统一前端批处理和后端追踪 | P0 |
| **合规性** | 完全符合 DDD 架构规范 | P0 |
| **可测试性** | 支持单元测试和集成测试 | P0 |
| **可扩展性** | 易于切换存储（ClickHouse） | P1 |
| **高性能** | 支持批量写入，不阻塞业务 | P1 |
| **向后兼容** | 现有代码无需修改 | P0 |

### 1.3 核心特性

- ✅ **前后端统一**: 一套 API 同时支持前端批处理和后端服务端追踪
- ✅ **DDD 架构**: Repository Pattern + Dependency Injection
- ✅ **事件类型**: 支持用户事件、分析事件、活动日志三类
- ✅ **便捷函数**: 提供 `track_ai_generation`, `track_payment` 等高级 API
- ✅ **Fire-and-Forget**: Analytics 失败不影响主业务流程

---

## 2. 业务需求

### 2.1 功能需求

#### FR1: 前端事件批处理
- **描述**: 前端周期性上报批量事件（Page View, Button Click, etc.）
- **优先级**: P0
- **状态**: ✅ 已实现

#### FR2: 后端服务端追踪
- **描述**: 后端关键业务节点追踪（AI 生成、支付、项目操作等）
- **优先级**: P0
- **状态**: ✅ 已实现

#### FR3: 事件查询
- **描述**: 按用户、时间、事件类型查询历史事件
- **优先级**: P1
- **状态**: ✅ 已实现

#### FR4: 事件统计
- **描述**: 统计特定事件的发生次数
- **优先级**: P1
- **状态**: ✅ 已实现

### 2.2 非功能需求

| 需求 | 指标 | 状态 |
|------|------|------|
| **可用性** | 99.9% (Analytics 故障不影响主业务) | ✅ |
| **性能** | 单次写入 < 50ms, 批量写入 < 200ms | ✅ |
| **可扩展性** | 支持 10,000 events/min | ✅ |
| **数据保留** | 180 天（后续可配置） | ⏳ |

---

## 3. 架构设计

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                    │
│  /api/v2/user/analytics/events (前端批处理)                 │
│  各业务 API (后端服务端追踪)                                │
└────────────┬────────────────────────────────┬───────────────┘
             │                                │
             ▼                                ▼
┌────────────────────────┐        ┌──────────────────────────┐
│  Application Layer     │        │ Infrastructure Layer     │
│  (依赖注入)            │        │  (便捷函数)              │
│                        │        │                          │
│  Depends(              │        │  analytics_tracker.py    │
│    get_analytics_      │        │  - track_ai_generation() │
│    service)            │        │  - track_payment()       │
└──────────┬─────────────┘        └────────────┬─────────────┘
           │                                   │
           └──────────────┬────────────────────┘
                          ▼
              ┌──────────────────────────┐
              │   Domain Layer           │
              │                          │
              │  AnalyticsService        │
              │  - track_event()         │
              │  - track_ai_generation() │
              │  - track_payment()       │
              │  - process_and_save_     │
              │    events()              │
              └──────────┬───────────────┘
                         │
                         │ depends on
                         ▼
              ┌──────────────────────────┐
              │  IAnalyticsRepository    │
              │  (Interface)             │
              └──────────┬───────────────┘
                         │
                         │ implements
                         ▼
              ┌──────────────────────────┐
              │  Infrastructure Layer    │
              │                          │
              │  SupabaseAnalytics       │
              │  EventsRepository        │
              │  - save()                │
              │  - save_batch()          │
              │  - get_user_events()     │
              └──────────┬───────────────┘
                         │
                         ▼
              ┌──────────────────────────┐
              │   Database (Supabase)    │
              │  - analytics_events      │
              │  - user_events           │
              │  - activity_logs         │
              └──────────────────────────┘
```

### 3.2 DDD 分层

| 层 | 职责 | 核心文件 |
|-----|------|----------|
| **Domain** | 业务逻辑和规则 | `domains/analytics/service.py`<br>`domains/analytics/entities.py`<br>`domains/analytics/repository.py` |
| **Application** | 依赖注入配置 | `dependencies.py` |
| **Infrastructure** | 技术实现 | `infrastructure/repositories/analytics_events_repository.py`<br>`infrastructure/monitoring/analytics_tracker.py` |
| **API** | HTTP 端点 | `api/user/analytics.py` |

### 3.3 关键设计模式

#### 3.3.1 Repository Pattern
```python
# Domain 层定义接口
class IAnalyticsRepository(ABC):
    @abstractmethod
    async def save(self, event: AnalyticsEvent) -> None: ...

# Infrastructure 层实现
class SupabaseAnalyticsEventsRepository(IAnalyticsRepository):
    async def save(self, event: AnalyticsEvent) -> None:
        await self.client.table("analytics_events").insert(...)
```

**优点**:
- ✅ Domain 层无基础设施依赖
- ✅ 易于切换存储（ClickHouse, MongoDB）
- ✅ 可 Mock 测试

#### 3.3.2 Dependency Injection
```python
# dependencies.py
@lru_cache()
def get_analytics_service() -> AnalyticsService:
    db_client = get_async_db_client()
    repository = SupabaseAnalyticsEventsRepository(db_client)
    return AnalyticsService(repository)

# API 使用
@router.post("/projects")
async def create_project(
    analytics: AnalyticsService = Depends(get_analytics_service)
):
    await analytics.track_event(...)
```

**优点**:
- ✅ 解耦依赖
- ✅ 单例模式（性能优化）
- ✅ 易于测试

#### 3.3.3 Fire-and-Forget
```python
async def track_event(...) -> AnalyticsEvent:
    try:
        await self._repo.save(event)
    except Exception as e:
        logger.error(f"Failed to track event: {e}")
        # 业务决策: Analytics 失败不影响主流程
    return event
```

**优点**:
- ✅ Analytics 故障不影响主业务
- ✅ 降低用户感知延迟

---

## 4. 数据模型

### 4.1 核心实体

#### AnalyticsEvent (Domain Entity)

```python
@dataclass
class AnalyticsEvent:
    """Analytics 事件领域实体"""
    id: UUID                          # 事件唯一 ID
    event_id: str                     # 自定义事件 ID
    event_name: str                   # 人类可读名称
    event_type: str                   # 机器类型
    user_id: Optional[str]            # 用户 ID
    session_id: Optional[str]         # 会话 ID
    properties: Dict[str, Any]        # 事件属性
    source: str = "server"            # 来源 (server/web/mobile)
    created_at: datetime              # 创建时间
    
    def __post_init__(self):
        """业务规则验证"""
        if not self.event_name:
            raise ValueError("event_name is required")
        # 规范化
        self.event_name = self.event_name.lower().strip()
        self.event_type = self.event_type.lower().strip()
        self.event_id = self.event_id or str(self.id)
```

### 4.2 数据库表结构

#### analytics_events (主表)

| 字段 | 类型 | 说明 | 索引 |
|------|------|------|------|
| `id` | UUID | 主键 | PK |
| `event_id` | TEXT | 自定义事件 ID | - |
| `event_name` | TEXT | 事件名称 | - |
| `event_type` | TEXT | 事件类型 | ✅ |
| `user_id` | TEXT | 用户 ID | ✅ |
| `session_id` | TEXT | 会话 ID | - |
| `properties` | JSONB | 事件属性 | - |
| `source` | TEXT | 来源 | ✅ |
| `created_at` | TIMESTAMPTZ | 创建时间 | ✅ |

**索引设计**:
```sql
CREATE INDEX idx_analytics_events_user_id ON analytics_events(user_id);
CREATE INDEX idx_analytics_events_event_type ON analytics_events(event_type);
CREATE INDEX idx_analytics_events_created_at ON analytics_events(created_at DESC);
CREATE INDEX idx_analytics_events_source ON analytics_events(source);
```

#### user_events (用户事件)

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 主键 |
| `user_id` | TEXT | 用户 ID |
| `event_type` | TEXT | 事件类型 |
| `metadata` | JSONB | 元数据 |
| `created_at` | TIMESTAMPTZ | 创建时间 |

#### activity_logs (活动日志)

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | BIGSERIAL | 主键 |
| `user_id` | TEXT | 用户 ID |
| `action` | TEXT | 操作 |
| `resource_type` | TEXT | 资源类型 |
| `resource_id` | TEXT | 资源 ID |
| `metadata` | JSONB | 元数据 |
| `created_at` | TIMESTAMPTZ | 创建时间 |

### 4.3 事件类型定义

#### 标准事件类型 (StandardEventTypes)

```python
class StandardEventTypes:
    """标准事件类型定义"""
    
    # 用户行为
    USER_SIGNUP = "user_signup"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    
    # AI 生成
    AI_GENERATE_SUCCESS = "ai_generate_success"
    AI_GENERATE_FAILURE = "ai_generate_failure"
    
    # 支付
    CHECKOUT_STARTED = "checkout_started"
    CHECKOUT_COMPLETED = "checkout_completed"
    SUBSCRIPTION_STARTED = "subscription_started"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    
    # 项目
    PROJECT_CREATED = "project_created"
    PROJECT_UPDATED = "project_updated"
    PROJECT_DELETED = "project_deleted"
    PROJECT_EXPORTED = "project_exported"
    
    # 市场
    MARKETPLACE_VIEW = "marketplace_view"
    MARKETPLACE_PURCHASE = "marketplace_purchase"
    MARKETPLACE_PUBLISH = "marketplace_publish"
```

#### 用户事件类型 (USER_EVENT_TYPES)

```python
USER_EVENT_TYPES = {
    "button_click", "page_view", "form_submit",
    "user_signup", "user_login", "user_logout"
}
```

#### 活动日志映射 (ACTIVITY_LOG_EVENT_MAPPING)

```python
ACTIVITY_LOG_EVENT_MAPPING = {
    "project_created": {"action": "create", "resource_type": "project"},
    "project_updated": {"action": "update", "resource_type": "project"},
    "project_deleted": {"action": "delete", "resource_type": "project"},
    ...
}
```

---

## 5. API 设计

### 5.1 前端批处理 API

#### POST /api/v2/user/analytics/events

**请求体**:
```json
{
  "events": [
    {
      "event_type": "page_view",
      "properties": {
        "page": "/dashboard",
        "referrer": "/"
      },
      "env": {
        "browser": "Chrome",
        "os": "Windows"
      }
    },
    {
      "event_type": "button_click",
      "properties": {
        "button": "create_project"
      }
    }
  ]
}
```

**响应**:
```json
{
  "success": true,
  "requested": 2,
  "inserted": 5  // 可能插入到多个表
}
```

### 5.2 后端服务端追踪 API

#### 便捷函数（推荐）

```python
from infrastructure.monitoring.analytics_tracker import (
    track_ai_generation,
    track_payment,
    track_project_action
)

# AI 生成追踪
await track_ai_generation(
    user_id="user_123",
    success=True,
    model="flux",
    cost_credits=5,
    duration_ms=3200
)

# 支付追踪
await track_payment(
    user_id="user_123",
    event_name="checkout_completed",
    amount_cents=2990,
    plan="t3",
    stripe_payment_id="pi_xxx"
)

# 项目操作追踪
await track_project_action(
    user_id="user_123",
    action="created",
    project_id="proj_456"
)
```

#### 依赖注入（FastAPI）

```python
from fastapi import Depends
from dependencies import get_analytics_service
from domains.analytics import AnalyticsService

@router.post("/projects")
async def create_project(
    analytics: AnalyticsService = Depends(get_analytics_service)
):
    await analytics.track_event(
        event_name="Project Created",
        event_type="project_created",
        user_id="user_123",
        properties={"title": "My Project"}
    )
```

---

## 6. 实施细节

### 6.1 目录结构

```
decodables/
├── domains/analytics/
│   ├── __init__.py                 # 导出 AnalyticsService
│   ├── entities.py                 # AnalyticsEvent 实体
│   ├── value_objects.py            # EventSource, StandardEventTypes
│   ├── repository.py               # IAnalyticsRepository 接口
│   └── service.py                  # AnalyticsService 业务逻辑
│
├── infrastructure/
│   ├── repositories/
│   │   └── analytics_events_repository.py  # Supabase 实现
│   └── monitoring/
│       └── analytics_tracker.py    # 便捷函数
│
├── api/user/
│   └── analytics.py                # API 端点
│
├── dependencies.py                 # 依赖注入配置
│
└── tests/
    └── unit/domains/analytics/
        └── test_analytics_service.py  # 单元测试
```

### 6.2 关键代码示例

#### AnalyticsService.track_event()

```python
async def track_event(
    self,
    event_name: str,
    event_type: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    properties: Optional[Dict[str, Any]] = None,
    source: str = "server"
) -> AnalyticsEvent:
    """追踪事件（业务逻辑层）"""
    # 创建领域实体（自动验证业务规则）
    event = AnalyticsEvent(
        event_name=event_name,
        event_type=event_type,
        user_id=user_id,
        session_id=session_id,
        properties=properties or {},
        source=source
    )
    
    # 持久化（Fire-and-Forget）
    try:
        await self._repo.save(event)
        logger.info(f"[Analytics] Tracked: {event_name}")
    except Exception as e:
        logger.error(f"[Analytics] Failed: {e}", exc_info=True)
        # 业务决策: Analytics 失败不影响主流程
    
    return event
```

#### SupabaseAnalyticsEventsRepository.save()

```python
async def save(self, event: AnalyticsEvent) -> None:
    """保存单个事件到 Supabase"""
    try:
        row = event.to_dict()
        await self.client.table("analytics_events").insert(row).execute()
    except Exception as e:
        logger.error(f"[AnalyticsRepo] Failed to save: {e}")
        raise
```

### 6.3 依赖注入配置

```python
# dependencies.py
from functools import lru_cache
from core.database import get_async_db_client
from domains.analytics.service import AnalyticsService
from domains.analytics.repository import IAnalyticsRepository
from infrastructure.repositories.analytics_events_repository import (
    SupabaseAnalyticsEventsRepository
)

@lru_cache()
def get_analytics_service() -> AnalyticsService:
    """获取 Analytics Service（单例）"""
    db_client = get_async_db_client()
    repository: IAnalyticsRepository = SupabaseAnalyticsEventsRepository(db_client)
    return AnalyticsService(repository)

# 全局单例（向后兼容）
def get_global_analytics_service():
    return get_analytics_service()
```

---

## 7. 测试策略

### 7.1 单元测试

**文件**: `tests/unit/domains/analytics/test_analytics_service.py`

```python
@pytest.fixture
def mock_repository():
    """Mock Repository"""
    repo = Mock(spec=IAnalyticsRepository)
    repo.save = AsyncMock()
    return repo

@pytest.mark.asyncio
async def test_track_event_creates_entity(analytics_service, mock_repository):
    """Should create AnalyticsEvent and save to repository"""
    event = await analytics_service.track_event(
        event_name="Test Event",
        event_type="test_event",
        user_id="user_123"
    )
    
    assert isinstance(event, AnalyticsEvent)
    assert event.event_name == "test event"  # Normalized
    mock_repository.save.assert_called_once()
```

### 7.2 集成测试（待实现）

```python
@pytest.mark.integration
async def test_save_event_to_database(test_db_client):
    """Should save event to real database"""
    repo = SupabaseAnalyticsEventsRepository(test_db_client)
    service = AnalyticsService(repo)
    
    event = await service.track_event(
        event_name="Integration Test",
        event_type="test_event",
        user_id="test_user"
    )
    
    # Verify event in database
    result = await test_db_client.table("analytics_events")\
        .select("*")\
        .eq("id", str(event.id))\
        .execute()
    
    assert len(result.data) == 1
    assert result.data[0]["event_name"] == "integration test"
```

---

## 8. 监控和运维

### 8.1 关键日志

```python
# 成功追踪
logger.info(
    f"[Analytics] Tracked event: {event_name} "
    f"(type={event_type}, user={user_id})"
)

# 失败追踪
logger.error(
    f"[Analytics] Failed to track event {event_name}: {e}",
    exc_info=True,
    extra={
        "event_name": event_name,
        "event_type": event_type,
        "user_id": user_id
    }
)
```

### 8.2 Sentry 集成

所有 Analytics 失败会自动上报到 Sentry（通过 `exc_info=True`）。

### 8.3 性能监控

**关键指标**:
- 单次写入延迟: < 50ms (P95)
- 批量写入延迟: < 200ms (P95)
- 成功率: > 99.9%
- 错误率: < 0.1%

**监控查询**:
```sql
-- 每小时事件数量
SELECT 
    date_trunc('hour', created_at) AS hour,
    COUNT(*) AS event_count
FROM analytics_events
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour DESC;

-- 失败率监控 (通过日志)
-- 需要配合 Sentry / Grafana
```

### 8.4 数据清理

**保留策略**: 180 天（可配置）

```sql
-- 清理 180 天前的数据
DELETE FROM analytics_events
WHERE created_at < NOW() - INTERVAL '180 days';

DELETE FROM user_events
WHERE created_at < NOW() - INTERVAL '180 days';

DELETE FROM activity_logs
WHERE created_at < NOW() - INTERVAL '180 days';
```

**定时任务**: 每周日凌晨 2:00 执行

---

## 9. 未来优化

### 9.1 性能优化

#### P1: 切换到 ClickHouse
- **目标**: 10x 写入性能, 100x 查询性能
- **工作量**: 2-3 周
- **实施**: 只需实现新的 `ClickHouseAnalyticsRepository`

```python
class ClickHouseAnalyticsRepository(IAnalyticsRepository):
    """ClickHouse 实现（未来）"""
    async def save(self, event: AnalyticsEvent) -> None:
        await self.clickhouse_client.insert(...)
```

#### P2: 异步队列批处理
- **目标**: 减少数据库连接数
- **方案**: Redis Queue + 批量插入
- **工作量**: 1 周

### 9.2 功能扩展

#### P1: 实时数据流
- **需求**: Kafka + Flink 实时计算
- **用例**: 实时大屏、异常告警
- **工作量**: 3-4 周

#### P2: 数据仓库集成
- **需求**: Snowflake / BigQuery 集成
- **用例**: BI 报表、数据分析
- **工作量**: 2 周

---

## 10. 参考资料

### 10.1 理论基础
- [Martin Fowler - Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html)
- [Eric Evans - Domain-Driven Design](https://domainlanguage.com/ddd/)
- [Segment - Analytics API Best Practices](https://segment.com/docs/connections/spec/)

### 10.2 内部文档
- `docs/main/backend-architecture.md` - 后端 DDD 架构
- `docs/main/database-guide.md` - 数据库设计指南
- `docs/main/testing-guide.md` - 测试策略

### 10.3 代码位置
- Domain 层: `domains/analytics/`
- Infrastructure 层: `infrastructure/repositories/analytics_events_repository.py`
- 便捷函数: `infrastructure/monitoring/analytics_tracker.py`
- API 端点: `api/user/analytics.py`
- 单元测试: `tests/unit/domains/analytics/test_analytics_service.py`

---

## 11. 版本历史

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|----------|
| v1.0 | 2025-01 | Team | 初版设计（未完全符合 DDD） |
| v2.0 | 2026-01-13 | Team | 完整 DDD 重构, 统一前后端追踪 |

---

**文档版本**: v2.0  
**最后更新**: 2026-01-13  
**维护者**: Make Decodables Team  
**Commit**: 181ec75
