# 通知模块架构

> **同步范围**: [fullstack]
> **状态**: 🟡 待验证
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `domains/notifications/`

---

## 一、模块概述

### 1.1 职责

通知模块负责系统内通知的创建、存储、推送和管理。

### 1.2 核心功能

| 功能 | 说明 |
|------|------|
| 通知创建 | 系统/管理员创建通知 |
| 通知存储 | 持久化通知内容 |
| 通知推送 | 实时/延迟推送 |
| 通知管理 | 已读/删除/设置 |

---

## 二、系统架构

### 2.1 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                  Notifications Module                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐                                          │
│  │  Triggers    │ ← 订阅事件、系统事件、管理员操作           │
│  └──────┬───────┘                                          │
│         │                                                   │
│         ▼                                                   │
│  ┌──────────────┐     ┌──────────────┐                     │
│  │ Notification │────▶│  PostgreSQL  │                     │
│  │   Service    │     │   Storage    │                     │
│  └──────┬───────┘     └──────────────┘                     │
│         │                                                   │
│         ▼                                                   │
│  ┌──────────────┐     ┌──────────────┐                     │
│  │   Delivery   │────▶│    Email     │                     │
│  │   Service    │     │   (Resend)   │                     │
│  └──────────────┘     └──────────────┘                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、通知类型

### 3.1 类型定义

| 类型 | 优先级 | 渠道 | 示例 |
|------|--------|------|------|
| system | 高 | 应用内 + 邮件 | 系统维护通知 |
| billing | 高 | 应用内 + 邮件 | 支付成功/失败 |
| subscription | 中 | 应用内 + 邮件 | 订阅续期/到期 |
| credits | 中 | 应用内 | 积分变动 |
| promotion | 低 | 应用内 | 活动促销 |

### 3.2 通知模板

```python
NOTIFICATION_TEMPLATES = {
    "subscription_renewed": {
        "title": "Subscription Renewed",
        "body": "Your {plan_name} subscription has been renewed.",
        "action_url": "/profile/subscription",
    },
    "credits_granted": {
        "title": "Credits Granted",
        "body": "{credits} credits have been added to your account.",
        "action_url": "/profile",
    },
}
```

---

## 四、后端架构

### 4.1 目录结构

```
domains/notifications/
├── entities.py          # Notification 实体
├── repository.py        # 数据访问
├── service.py           # 业务逻辑
└── templates.py         # 通知模板
```

### 4.2 核心实体

```python
@dataclass
class Notification:
    id: UUID
    user_id: UUID
    type: str
    title: str
    body: str
    action_url: Optional[str]
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime]
```

### 4.3 服务层

```python
class NotificationService:
    # 创建通知
    async def create(self, user_id: UUID, type: str, data: Dict) -> Notification
    async def create_bulk(self, user_ids: List[UUID], type: str, data: Dict) -> int
    
    # 查询
    async def list_by_user(self, user_id: UUID, offset: int, limit: int) -> List[Notification]
    async def get_unread_count(self, user_id: UUID) -> int
    
    # 管理
    async def mark_read(self, notification_id: UUID) -> None
    async def mark_all_read(self, user_id: UUID) -> None
    async def delete(self, notification_id: UUID) -> None
```

---

## 五、触发机制

### 5.1 自动触发

| 事件 | 通知类型 | 触发条件 |
|------|----------|----------|
| 订阅成功 | subscription | Stripe webhook |
| 订阅续期 | subscription | Stripe webhook |
| 订阅取消 | subscription | 用户操作 |
| 积分发放 | credits | 月度发放 |
| 积分不足 | credits | 余额 < 10 |

### 5.2 手动触发

- 管理员创建系统公告
- 管理员发送促销通知

---

## 六、推送渠道

### 6.1 应用内通知

- 实时更新 (WebSocket/轮询)
- 未读计数徽章
- 通知中心列表

### 6.2 邮件通知

| 类型 | 是否发邮件 |
|------|------------|
| 系统通知 | ✅ 始终 |
| 计费通知 | ✅ 始终 |
| 订阅通知 | ✅ 始终 |
| 积分通知 | ❌ 仅应用内 |
| 促销通知 | 🟡 用户可选 |

---

## 七、数据库设计

### 7.1 表结构

```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id),
    type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    body TEXT NOT NULL,
    action_url TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    read_at TIMESTAMPTZ
);
```

### 7.2 索引

```sql
CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_unread ON notifications(user_id, is_read) WHERE is_read = FALSE;
CREATE INDEX idx_notifications_created ON notifications(created_at DESC);
```

---

## 八、API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/notifications` | GET | 获取通知列表 |
| `/notifications/unread-count` | GET | 获取未读数量 |
| `/notifications/{id}/read` | POST | 标记已读 |
| `/notifications/read-all` | POST | 全部标记已读 |

---

## 九、相关文档

- [通知功能规格](../../02-product/features/notifications.md)
- [邮件服务](../../../08-operations/email.md)

---

**END OF DOCUMENT**
