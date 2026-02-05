# Analytics System - 用户分析系统

> 事件追踪、用户行为分析、业务指标统计

**验证状态**: 🟢 已验证  
**同步范围**: [fullstack]  
**代码来源**: `domains/analytics/`, `api/v2/user/analytics.py`

---

## 一、概述

分析系统负责收集、处理和存储用户行为事件，为产品优化和业务决策提供数据支持。

---

## 二、系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Analytics 系统架构                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐         ┌─────────────┐         ┌───────────┐ │
│  │   前端 SDK   │ ──────▶ │   API 层    │ ──────▶ │  Service  │ │
│  │  (批量上报)  │         │ /analytics  │         │   层      │ │
│  └─────────────┘         └─────────────┘         └─────┬─────┘ │
│                                                        │       │
│  ┌─────────────┐                                       │       │
│  │  后端服务    │ ──────────────────────────────────────┤       │
│  │  (服务端)   │                                       │       │
│  └─────────────┘                                       ↓       │
│                                                 ┌─────────────┐ │
│                                                 │  Repository │ │
│                                                 │   (批量写)  │ │
│                                                 └──────┬──────┘ │
│                                                        │       │
│         ┌──────────────────────────────────────────────┼───┐   │
│         │                 数据存储层                     │   │   │
│         │  ┌────────────┐ ┌────────────┐ ┌────────────┐│   │   │
│         │  │user_events │ │ analytics_ │ │ activity_  ││   │   │
│         │  │            │ │   events   │ │    logs    ││   │   │
│         │  └────────────┘ └────────────┘ └────────────┘│   │   │
│         └──────────────────────────────────────────────┘   │   │
│                                                             │   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、核心实体

### 3.1 AnalyticsEvent Entity

```python
@dataclass
class AnalyticsEvent:
    """
    Analytics Event Domain Entity
    """
    # 核心字段
    event_name: str              # 事件名称 (e.g., "user_login")
    event_type: str              # 事件类型 (e.g., "auth")
    
    # 标识字段
    id: UUID = field(default_factory=uuid4)
    event_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # 数据字段
    properties: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    
    # 元数据
    source: str = "server"       # server/web/mobile/api
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
```

### 3.2 业务规则

```python
def __post_init__(self):
    """Entity 业务规则验证"""
    # Rule 1: event_name 必填
    if not self.event_name:
        raise ValueError("event_name is required")
    
    # Rule 2: 长度限制
    if len(self.event_name) > 100:
        raise ValueError("event_name too long (max 100 chars)")
    
    # Rule 3: 自动标准化 (小写)
    self.event_name = self.event_name.lower().strip()
    self.event_type = self.event_type.lower().strip()
    
    # Rule 4: 自动生成 event_id
    if not self.event_id:
        self.event_id = str(self.id)
```

---

## 四、数据收集

### 4.1 前端事件上报

```typescript
// 前端 SDK 使用
import { analytics } from '@/lib/analytics';

// 追踪事件
analytics.track('button_clicked', {
  button_name: 'upgrade',
  page: 'pricing',
});

// 追踪页面浏览
analytics.page('Pricing', {
  referrer: document.referrer,
});

// 批量上报 (自动)
// SDK 会自动批量上报，减少网络请求
```

### 4.2 后端事件追踪

```python
# 服务端追踪
class AnalyticsService:
    
    async def track_event(
        self,
        event_name: str,
        event_type: str,
        user_id: Optional[str] = None,
        properties: Optional[Dict] = None,
        source: str = "server"
    ) -> AnalyticsEvent:
        """
        追踪单个事件
        
        特点:
        - Fire-and-forget (不阻塞主流程)
        - 失败时仅记录日志，不影响业务
        """
        event = AnalyticsEvent(
            event_name=event_name,
            event_type=event_type,
            user_id=user_id,
            properties=properties or {},
            source=source
        )
        
        try:
            await self._repo.save(event)
        except Exception as e:
            logger.error(f"Failed to track event: {e}")
            # 不抛出异常，分析失败不影响业务
        
        return event
```

### 4.3 便捷追踪方法

```python
# AI 生成事件
await analytics.track_ai_generation(
    user_id="user_123",
    success=True,
    model="flux",
    cost_credits=5,
    duration_ms=3200
)

# 支付事件
await analytics.track_payment(
    user_id="user_123",
    event_name="checkout_completed",
    amount_cents=990,
    plan="t2"
)

# Marketplace 事件
await analytics.track_marketplace_action(
    user_id="user_123",
    action="purchase",
    listing_id="listing_456"
)

# 项目事件
await analytics.track_project_action(
    user_id="user_123",
    action="created",
    project_id="project_789"
)
```

---

## 五、数据存储

### 5.1 数据库表

```sql
-- 主事件表 (全量)
CREATE TABLE analytics_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id VARCHAR(100),
    event_name VARCHAR(100) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    user_id UUID,
    session_id VARCHAR(100),
    properties JSONB DEFAULT '{}',
    context JSONB DEFAULT '{}',
    source VARCHAR(20) DEFAULT 'server',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 用户事件表 (用于用户维度查询)
CREATE TABLE user_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id),
    event_type VARCHAR(50) NOT NULL,
    event_data JSONB DEFAULT '{}',
    session_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 活动日志表 (关键事件)
CREATE TABLE activity_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id),
    action VARCHAR(100) NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_analytics_events_user ON analytics_events(user_id);
CREATE INDEX idx_analytics_events_name ON analytics_events(event_name);
CREATE INDEX idx_analytics_events_created ON analytics_events(created_at);
CREATE INDEX idx_user_events_user ON user_events(user_id);
CREATE INDEX idx_activity_logs_user ON activity_logs(user_id);
```

### 5.2 事件类型映射

```python
# 用户事件类型 (写入 user_events)
USER_EVENT_TYPES = {
    'page_view',
    'button_click',
    'form_submit',
    'project_created',
    'project_updated',
    'ai_generate_success',
    'ai_generate_failure',
    'marketplace_view',
    'marketplace_purchase',
}

# 活动日志映射 (写入 activity_logs)
ACTIVITY_LOG_EVENT_MAPPING = {
    'user_login': 'login',
    'user_signup': 'signup',
    'project_created': 'create_project',
    'project_deleted': 'delete_project',
    'subscription_started': 'subscribe',
    'subscription_cancelled': 'cancel_subscription',
}
```

---

## 六、批量处理

### 6.1 批量写入

```python
async def process_and_save_events(
    self,
    events: List[Dict],
    user_id: Optional[str],
    location_info: Dict[str, str],
    user_agent: str,
    accept_language: str,
) -> Tuple[int, int]:
    """
    批量处理事件
    
    流程:
    1. 构建批量数据 (无 DB 调用)
    2. 批量 INSERT (最多 3 次 DB 调用)
    """
    # 构建数据
    user_event_rows, analytics_event_rows, activity_rows = self._build_batch_data(
        events, user_id, location_info, user_agent, accept_language
    )
    
    # 批量插入
    return await self._repo.batch_insert_all(
        user_event_rows, 
        analytics_event_rows, 
        activity_rows
    )
```

### 6.2 服务端上下文丰富

```python
# 服务端自动添加上下文 (防止客户端篡改)
enriched_properties = {
    **properties,
    "__server_ip": client_ip,
    "__server_country": location_info.get("country_code"),
    "__server_city": location_info.get("city"),
    "__server_user_agent": user_agent,
    "__server_accept_language": accept_language,
    "__client_browser": env_info.get("browser"),
    "__client_os": env_info.get("os"),
    "__client_device_type": env_info.get("device_type"),
}
```

---

## 七、API 端点

### 7.1 前端上报

```http
POST /api/v2/user/analytics/events
Content-Type: application/json

{
    "events": [
        {
            "event_type": "page_view",
            "event_name": "pricing_page",
            "timestamp": "2026-01-15T10:00:00Z",
            "session_id": "sess_123",
            "properties": {
                "referrer": "https://google.com"
            },
            "env": {
                "browser": "Chrome",
                "os": "macOS",
                "device_type": "desktop"
            }
        }
    ]
}
```

### 7.2 响应

```json
{
    "status": "ok",
    "requested": 5,
    "inserted": 5
}
```

---

## 八、前端 SDK

### 8.1 初始化

```typescript
// lib/analytics.ts
class AnalyticsClient {
  private queue: AnalyticsEvent[] = [];
  private flushInterval: number = 5000; // 5 秒
  private maxBatchSize: number = 20;
  
  constructor() {
    // 定时批量上报
    setInterval(() => this.flush(), this.flushInterval);
    
    // 页面卸载前上报
    window.addEventListener('beforeunload', () => this.flush());
  }
  
  track(eventName: string, properties?: Record<string, any>) {
    this.queue.push({
      event_type: eventName,
      event_name: eventName,
      properties,
      timestamp: new Date().toISOString(),
      session_id: this.getSessionId(),
      env: this.getEnvInfo(),
    });
    
    if (this.queue.length >= this.maxBatchSize) {
      this.flush();
    }
  }
  
  async flush() {
    if (this.queue.length === 0) return;
    
    const events = [...this.queue];
    this.queue = [];
    
    try {
      await fetch('/api/v2/user/analytics/events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ events }),
      });
    } catch (error) {
      // 失败时重新入队
      this.queue.unshift(...events);
    }
  }
}

export const analytics = new AnalyticsClient();
```

### 8.2 自动追踪

```typescript
// 自动追踪页面浏览
useEffect(() => {
  analytics.track('page_view', {
    page: pathname,
    title: document.title,
  });
}, [pathname]);

// 自动追踪错误
window.addEventListener('error', (event) => {
  analytics.track('client_error', {
    message: event.message,
    filename: event.filename,
    lineno: event.lineno,
  });
});
```

---

## 九、数据分析

### 9.1 常用查询

```sql
-- 日活用户 (DAU)
SELECT COUNT(DISTINCT user_id) as dau
FROM analytics_events
WHERE created_at >= CURRENT_DATE
  AND user_id IS NOT NULL;

-- 事件漏斗
SELECT 
    event_name,
    COUNT(*) as count,
    COUNT(DISTINCT user_id) as unique_users
FROM analytics_events
WHERE event_name IN ('page_view', 'click_upgrade', 'checkout_started', 'checkout_completed')
  AND created_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY event_name;

-- 用户留存 (Day 1)
WITH first_visit AS (
    SELECT user_id, MIN(created_at::date) as first_date
    FROM analytics_events
    WHERE user_id IS NOT NULL
    GROUP BY user_id
)
SELECT 
    first_date,
    COUNT(DISTINCT fv.user_id) as new_users,
    COUNT(DISTINCT CASE WHEN ae.created_at::date = fv.first_date + 1 THEN fv.user_id END) as day1_retained
FROM first_visit fv
LEFT JOIN analytics_events ae ON fv.user_id = ae.user_id
WHERE fv.first_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY first_date;
```

---

## 十、相关文档

- [Admin Analytics](../admin/analytics-ops.md)
- [日志标准](../../02-standards/logging-standard.md)
- [Feature Flag 引擎](../../02-standards/feature-flag-engine.md)
