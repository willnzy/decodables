# Support System - 客服支持系统

> 用户支持、工单管理、反馈收集

> **同步范围**: [fullstack]
> **状态**: 🟡 待验证
> **最后更新**: 2026-02-05
> **数据来源**: `domains/support/`, `api/user/support.py`

---

## 一、概述

支持系统提供用户反馈渠道、工单管理和客服响应流程，确保用户问题得到及时处理。

---

## 二、系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Support 系统架构                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐         ┌─────────────┐         ┌───────────┐ │
│  │   用户入口   │         │   工单系统   │         │   通知    │ │
│  │  (多渠道)   │ ──────▶ │   (处理)    │ ──────▶ │   系统    │ │
│  └─────────────┘         └──────┬──────┘         └───────────┘ │
│                                 │                              │
│                                 ↓                              │
│                          ┌─────────────┐                       │
│                          │   Admin     │                       │
│                          │   Panel     │                       │
│                          └─────────────┘                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、支持入口

### 3.1 入口类型

| 入口 | 位置 | 用户类型 | 验证要求 |
|------|------|----------|----------|
| Help 页面 | `/help` | 所有用户 | 无 |
| Contact Us | `/contact` | 所有用户 | 验证码 |
| Dashboard 帮助 | `/dashboard` | 登录用户 | 已登录 |
| Billing 帮助 | `/billing` | 登录用户 | 已登录 |

### 3.2 入口流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    支持入口流程                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  访客                                登录用户                    │
│    │                                    │                       │
│    ▼                                    ▼                       │
│  Contact Us 页面                    Dashboard 内帮助入口         │
│    │                                    │                       │
│    ▼                                    ▼                       │
│  验证码校验                          自动关联用户 ID             │
│    │                                    │                       │
│    └────────────────┬───────────────────┘                       │
│                     │                                           │
│                     ▼                                           │
│               选择问题类型                                       │
│                     │                                           │
│                     ▼                                           │
│               填写问题描述                                       │
│                     │                                           │
│                     ▼                                           │
│               创建工单                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 四、工单系统

### 4.1 工单实体

```python
class Ticket:
    id: UUID
    user_id: Optional[UUID]      # 可选 (访客无 user_id)
    email: str                   # 联系邮箱
    category: str                # bug/billing/account/other
    subject: str                 # 标题
    description: str             # 描述
    status: str                  # open/pending/resolved/closed
    priority: str                # low/medium/high/urgent
    assigned_to: Optional[UUID]  # 处理人
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]
```

### 4.2 工单消息

```python
class TicketMessage:
    id: UUID
    ticket_id: UUID
    sender_type: str             # user/admin
    sender_id: Optional[UUID]
    content: str
    attachments: List[str]       # 附件 URL 列表
    created_at: datetime
```

### 4.3 数据库 Schema

```sql
CREATE TABLE support_tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id),
    email VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL,
    subject VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'open',
    priority VARCHAR(20) DEFAULT 'medium',
    assigned_to UUID REFERENCES profiles(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE TABLE ticket_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id UUID NOT NULL REFERENCES support_tickets(id),
    sender_type VARCHAR(20) NOT NULL,
    sender_id UUID,
    content TEXT NOT NULL,
    attachments TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_tickets_user ON support_tickets(user_id);
CREATE INDEX idx_tickets_status ON support_tickets(status);
CREATE INDEX idx_tickets_created ON support_tickets(created_at);
CREATE INDEX idx_messages_ticket ON ticket_messages(ticket_id);
```

---

## 五、状态流转

### 5.1 工单状态

| 状态 | 描述 | 可转换到 |
|------|------|----------|
| `open` | 新建，待处理 | pending, resolved, closed |
| `pending` | 等待用户回复 | open, resolved, closed |
| `resolved` | 已解决 | closed, open (重开) |
| `closed` | 已关闭 | open (重开) |

### 5.2 状态流转图

```
          ┌─────────────────────────────────────┐
          │                                     │
          ▼                                     │
       ┌──────┐     回复      ┌─────────┐      │
       │ open │ ───────────▶ │ pending │      │
       └──┬───┘              └────┬────┘      │
          │                       │            │
          │    用户回复           │            │
          │  ◀──────────────────┘            │
          │                                     │
          │     解决                            │ 重开
          ▼                                     │
     ┌──────────┐                              │
     │ resolved │ ─────────────────────────────┘
     └────┬─────┘
          │
          │ 确认关闭
          ▼
     ┌────────┐
     │ closed │
     └────────┘
```

---

## 六、问题分类

### 6.1 分类定义

| 分类 | 代码 | 描述 | 优先级 |
|------|------|------|--------|
| Bug 报告 | `bug` | 功能异常、错误 | 高 |
| 账号问题 | `account` | 登录、注册、密码 | 高 |
| 计费问题 | `billing` | 订阅、付款、退款 | 紧急 |
| 功能建议 | `feature` | 新功能请求 | 低 |
| 其他 | `other` | 其他问题 | 中 |

### 6.2 自动优先级

```python
def determine_priority(category: str, user_tier: str) -> str:
    """根据分类和用户层级确定优先级"""
    
    # 计费问题始终紧急
    if category == 'billing':
        return 'urgent'
    
    # Pro 用户优先
    if user_tier == 't3':
        return 'high'
    
    # Bug 报告中等
    if category in ['bug', 'account']:
        return 'medium'
    
    return 'low'
```

---

## 七、API 端点

### 7.1 用户端

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v1/support/tickets` | 创建工单 |
| GET | `/api/v1/support/tickets` | 获取我的工单列表 |
| GET | `/api/v1/support/tickets/{id}` | 获取工单详情 |
| POST | `/api/v1/support/tickets/{id}/messages` | 回复工单 |

### 7.2 请求示例

**创建工单**:
```json
POST /api/v1/support/tickets
{
    "category": "billing",
    "subject": "无法完成支付",
    "description": "使用 Visa 卡支付时显示失败...",
    "email": "user@example.com"
}
```

**响应**:
```json
{
    "id": "uuid",
    "ticket_number": "TK-2026-001234",
    "status": "open",
    "created_at": "2026-01-15T10:00:00Z",
    "message": "工单已创建，我们会尽快处理"
}
```

### 7.3 Admin 端

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/admin/v1/support/tickets` | 获取所有工单 |
| PATCH | `/api/admin/v1/support/tickets/{id}` | 更新工单状态 |
| POST | `/api/admin/v1/support/tickets/{id}/assign` | 分配工单 |
| POST | `/api/admin/v1/support/tickets/{id}/reply` | 管理员回复 |

---

## 八、通知机制

### 8.1 通知触发

| 事件 | 通知对象 | 渠道 |
|------|----------|------|
| 工单创建 | 用户 + Admin | 邮件 |
| 工单回复 | 对方 | 邮件 + 站内 |
| 工单解决 | 用户 | 邮件 + 站内 |
| 长时间未回复 | Admin | 站内 |

### 8.2 邮件模板

```python
TICKET_EMAIL_TEMPLATES = {
    'ticket_created': {
        'subject': '您的支持请求已收到 [#{ticket_number}]',
        'body': '''
亲爱的用户，

感谢您联系我们的支持团队。

您的工单信息：
- 工单号：{ticket_number}
- 类别：{category}
- 状态：待处理

我们会尽快回复您的问题。

祝好，
Make Decodables 支持团队
'''
    },
    'ticket_replied': {
        'subject': '您的工单有新回复 [#{ticket_number}]',
        'body': '''...'''
    },
}
```

---

## 九、前端交互

### 9.1 工单列表

```typescript
interface TicketListItem {
  id: string;
  ticket_number: string;
  subject: string;
  category: string;
  status: 'open' | 'pending' | 'resolved' | 'closed';
  created_at: string;
  updated_at: string;
  unread_count: number;
}

function TicketList() {
  const { data: tickets } = useQuery({
    queryKey: ['tickets'],
    queryFn: () => api.get('/api/v1/support/tickets'),
  });
  
  return (
    <div>
      {tickets.map(ticket => (
        <TicketCard key={ticket.id} ticket={ticket} />
      ))}
    </div>
  );
}
```

### 9.2 工单详情

```typescript
function TicketDetail({ ticketId }: { ticketId: string }) {
  const { data: ticket } = useQuery({
    queryKey: ['ticket', ticketId],
    queryFn: () => api.get(`/api/v1/support/tickets/${ticketId}`),
  });
  
  const replyMutation = useMutation({
    mutationFn: (content: string) => 
      api.post(`/api/v1/support/tickets/${ticketId}/messages`, { content }),
  });
  
  return (
    <div>
      <TicketHeader ticket={ticket} />
      <MessageList messages={ticket.messages} />
      <ReplyForm onSubmit={replyMutation.mutate} />
    </div>
  );
}
```

---

## 十、安全措施

### 10.1 访客提交限制

```python
# 访客提交限频
GUEST_RATE_LIMIT = "5/hour"

# 验证码要求
CAPTCHA_REQUIRED = True

# 邮箱验证
async def validate_guest_submission(email: str, captcha_token: str):
    # 1. 验证验证码
    if not await verify_captcha(captcha_token):
        raise InvalidCaptchaError()
    
    # 2. 验证邮箱格式
    if not is_valid_email(email):
        raise InvalidEmailError()
    
    # 3. 检查是否被封禁
    if await is_email_banned(email):
        raise EmailBannedError()
```

### 10.2 敏感信息处理

```python
# 工单内容脱敏
def sanitize_ticket_content(content: str) -> str:
    """脱敏敏感信息"""
    # 移除信用卡号
    content = re.sub(r'\d{16}', '****', content)
    # 移除完整邮箱
    content = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 
                     lambda m: mask_email(m.group()), content)
    return content
```

---

## 十一、相关文档

- [通知系统](../notifications/architecture.md)
- [Admin Moderation](../admin/moderation-ops.md)
- [邮件服务](../../03-infrastructure/email-service.md)
