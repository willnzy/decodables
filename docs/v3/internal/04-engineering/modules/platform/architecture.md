# 平台服务模块架构

> **同步范围**: [fullstack]
> **状态**: 🟡 待验证
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `domains/platform/`, `shared/`

---

## 一、模块概述

### 1.1 职责

平台服务模块提供跨业务的基础能力，包括配置管理、Feature Flags、新手引导等。

### 1.2 核心功能

| 功能 | 说明 |
|------|------|
| 系统配置 | 动态配置管理 |
| Feature Flags | 功能开关和实验 |
| Onboarding | 新手引导流程 |
| Events | 事件追踪 |

---

## 二、系统架构

### 2.1 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                   Platform Services                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ System       │  │ Feature      │  │ Onboarding   │      │
│  │ Configs      │  │ Flags        │  │ Service      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                │                  │               │
│         └────────────────┴──────────────────┘               │
│                          │                                  │
│                          ▼                                  │
│                   ┌──────────────┐                          │
│                   │  PostgreSQL  │                          │
│                   │  + Cache     │                          │
│                   └──────────────┘                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、系统配置

### 3.1 配置类型

| 类型 | 说明 | 示例 |
|------|------|------|
| 业务配置 | 业务规则参数 | `tier.t2.monthly_credits = 100` |
| 功能配置 | 功能开关 | `feature.ai_page.enabled = true` |
| 系统配置 | 系统参数 | `system.maintenance = false` |

### 3.2 配置服务

```python
class ConfigService:
    async def get_config(self, key: str) -> Any
    async def set_config(self, key: str, value: Any) -> None
    async def get_all_configs(self, prefix: str) -> Dict[str, Any]
```

### 3.3 配置缓存

- 使用内存缓存 + Redis
- TTL: 5 分钟
- 支持强制刷新

---

## 四、Feature Flags

### 4.1 Flag 类型

| 类型 | 说明 |
|------|------|
| Boolean | 开/关 |
| Percentage | 百分比灰度 |
| User Segment | 用户分群 |

### 4.2 Flag 评估

```python
class FeatureFlagService:
    async def is_enabled(self, flag_key: str, user_id: UUID) -> bool
    async def get_variant(self, flag_key: str, user_id: UUID) -> str
```

### 4.3 实验系统

```sql
CREATE TABLE experiments (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    flag_key VARCHAR(100) NOT NULL,
    variants JSONB NOT NULL,
    allocation JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'draft',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 五、Onboarding 服务

### 5.1 引导步骤

| 步骤 | 说明 |
|------|------|
| welcome | 欢迎页面 |
| create_project | 创建第一个项目 |
| add_element | 添加元素 |
| use_ai | 使用 AI 功能 |
| export | 导出作品 |

### 5.2 进度追踪

```python
class OnboardingService:
    async def get_progress(self, user_id: UUID) -> OnboardingProgress
    async def complete_step(self, user_id: UUID, step: str) -> None
    async def skip_onboarding(self, user_id: UUID) -> None
```

### 5.3 数据模型

```sql
CREATE TABLE onboarding_progress (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES profiles(id),
    steps_completed TEXT[],
    current_step VARCHAR(50),
    completed_at TIMESTAMPTZ,
    skipped_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 六、Events 服务

### 6.1 事件类型

| 类型 | 说明 | 示例 |
|------|------|------|
| 用户行为 | 用户操作 | `page_view`, `button_click` |
| 业务事件 | 业务流程 | `project_created`, `export_completed` |
| 系统事件 | 系统状态 | `error`, `performance` |

### 6.2 事件追踪

```python
class EventService:
    async def track(self, event: str, properties: Dict, user_id: UUID) -> None
    async def batch_track(self, events: List[Event]) -> None
```

### 6.3 事件存储

```sql
CREATE TABLE events (
    id UUID PRIMARY KEY,
    user_id UUID,
    event_name VARCHAR(100) NOT NULL,
    properties JSONB,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    session_id VARCHAR(100)
);

-- 按时间分区
CREATE INDEX idx_events_timestamp ON events(timestamp);
CREATE INDEX idx_events_user ON events(user_id, timestamp);
```

---

## 七、API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/config/{key}` | GET | 获取配置 |
| `/feature-flags/evaluate` | POST | 评估 Feature Flag |
| `/onboarding/progress` | GET | 获取引导进度 |
| `/onboarding/complete` | POST | 完成引导步骤 |
| `/events/track` | POST | 追踪事件 |

---

## 八、相关文档

- [系统架构总览](../../architecture/overview.md)
- [数据分析](../../07-analytics/README.md)

---

**END OF DOCUMENT**
