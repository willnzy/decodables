# 用户运营系统设计

> **同步范围**: [backend]
> **状态**: 🟢 已验证 (来源: 代码分析 + v2 文档)
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `api/admin/users.py`

---

## 一、概述

### 1.1 核心能力

| 能力 | 说明 |
|------|------|
| 用户检索 | 搜索、筛选、详情查看 |
| 订阅管理 | Tier 变更、折扣设置 |
| 积分运营 | 积分调整、记录查看 |
| 资产管理 | 项目恢复、素材统计 |
| 环境诊断 | 设备、会话信息 |
| 审计追踪 | 操作历史、变更记录 |

### 1.2 数据流

```
Admin UI → Admin API → Domain Service → Repository → Database
                ↓
           Audit Logging
```

---

## 二、API 端点

### 2.1 用户查询

| 端点 | 方法 | Rate Limit | 说明 |
|------|------|------------|------|
| `/api/admin/users` | GET | 30/min | 用户列表 |
| `/api/admin/users/by-tier/{tier}` | GET | 30/min | 按 Tier 筛选 |
| `/api/admin/users/{user_id}` | GET | 30/min | 用户详情 |

### 2.2 用户操作

| 端点 | 方法 | Rate Limit | 风险 | 说明 |
|------|------|------------|:----:|------|
| `/api/admin/users/{user_id}` | PATCH | 10/min | 🟡 | 更新用户 |
| `/api/admin/users/{user_id}/credits` | POST | 10/min | 🔴 | 调整积分 |
| `/api/admin/users/{user_id}/discount` | POST | 10/min | 🟠 | 设置折扣 |

### 2.3 关联数据

| 端点 | 方法 | Rate Limit | 说明 |
|------|------|------------|------|
| `/api/admin/users/{user_id}/payments` | GET | 30/min | 支付记录 |
| `/api/admin/users/{user_id}/projects` | GET | 30/min | 项目列表 |
| `/api/admin/users/{user_id}/asset-usage` | GET | 30/min | 素材使用 |
| `/api/admin/users/{user_id}/env-stats` | GET | 30/min | 环境统计 |

### 2.4 项目操作

| 端点 | 方法 | Rate Limit | 说明 |
|------|------|------------|------|
| `/api/admin/projects/{project_id}/restore` | POST | 10/min | 恢复项目 |
| `/api/admin/projects/feed` | GET | 30/min | 项目动态 |

---

## 三、数据结构

### 3.1 用户搜索结果

```python
class UserSearchResult:
    id: UUID
    email: str
    name: Optional[str]
    user_code: str           # 26 位用户码
    tier: str               # t1/t2/t3
    credits_monthly: int    # 月度积分
    credits_permanent: int  # 永久积分
    created_at: datetime
    last_login_at: Optional[datetime]
```

### 3.2 用户审计数据

```python
class UserAudit:
    activities: List[Activity]
    subscription_history: List[SubscriptionEvent]
    credit_history: List[CreditEvent]

class Activity:
    action: str
    timestamp: datetime
    details: dict

class SubscriptionEvent:
    event_type: str  # created/upgraded/downgraded/cancelled/renewed
    from_tier: Optional[str]
    to_tier: str
    timestamp: datetime

class CreditEvent:
    event_type: str  # adjusted/consumed/refunded/monthly_reset
    amount: int
    bucket: str      # monthly/permanent
    reason: str
    timestamp: datetime
```

### 3.3 素材使用统计

```python
class UserAssetUsage:
    images_count: int
    projects_count: int
    total_storage_mb: float
    last_upload_at: Optional[datetime]
```

### 3.4 环境统计

```python
class UserEnvStats:
    last_browser: str
    last_os: str
    last_device_type: str  # desktop/tablet/mobile
    last_login_at: datetime
    sessions: List[Session]

class Session:
    id: str
    device_type: str
    browser: str
    os: str
    ip_address: str
    created_at: datetime
    last_active_at: datetime
```

---

## 四、业务规则

### 4.1 积分调整

```python
async def adjust_credits(
    user_id: UUID,
    amount: int,
    bucket: Literal["monthly", "permanent"],
    reason: str,
    admin_id: UUID
):
    """
    调整用户积分
    
    规则:
    - amount 可正可负
    - bucket 必须是 monthly 或 permanent
    - 必须提供 reason
    - 操作记录审计日志
    """
    # 验证用户存在
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise UserNotFoundError()
    
    # 计算新余额
    if bucket == "monthly":
        new_balance = user.credits_monthly + amount
    else:
        new_balance = user.credits_permanent + amount
    
    # 不允许负余额
    if new_balance < 0:
        raise InsufficientCreditsError()
    
    # 更新积分
    await credits_repo.update_balance(user_id, bucket, new_balance)
    
    # 记录交易
    await credits_repo.create_transaction(
        user_id=user_id,
        amount=amount,
        bucket=bucket,
        type="admin_adjustment",
        reason=reason,
        operator_id=admin_id
    )
    
    # 审计日志
    await audit_log.create(
        action="credits_adjusted",
        target_id=user_id,
        operator_id=admin_id,
        details={"amount": amount, "bucket": bucket, "reason": reason}
    )
```

### 4.2 状态与类型枚举

```python
# Tier
class Tier(str, Enum):
    T1 = "t1"
    T2 = "t2"
    T3 = "t3"

# 积分桶
class CreditBucket(str, Enum):
    MONTHLY = "monthly"
    PERMANENT = "permanent"

# 订阅事件类型
class SubscriptionEventType(str, Enum):
    CREATED = "created"
    UPGRADED = "upgraded"
    DOWNGRADED = "downgraded"
    CANCELLED = "cancelled"
    RENEWED = "renewed"

# 积分事件类型
class CreditEventType(str, Enum):
    ADJUSTED = "adjusted"
    CONSUMED = "consumed"
    REFUNDED = "refunded"
    MONTHLY_RESET = "monthly_reset"

# 设备类型
class DeviceType(str, Enum):
    DESKTOP = "desktop"
    TABLET = "tablet"
    MOBILE = "mobile"

# 支付状态
class PaymentStatus(str, Enum):
    SUCCEEDED = "succeeded"
    PENDING = "pending"
    FAILED = "failed"
    REFUNDED = "refunded"
```

---

## 五、安全与护栏

### 5.1 权限控制

- 所有端点需要 Admin 角色
- 敏感操作 (积分调整) 需要二次确认

### 5.2 Rate Limiting

| 操作类型 | 限制 |
|----------|------|
| 读取操作 | 30/min |
| 写入操作 | 10/min |
| 敏感操作 | 5/min |

### 5.3 审计日志

所有变更操作自动记录:

```python
AuditLog(
    id=uuid4(),
    action="credits_adjusted",
    target_type="user",
    target_id=user_id,
    operator_id=admin_id,
    details={"amount": 100, "bucket": "permanent"},
    ip_address="...",
    user_agent="...",
    created_at=datetime.now()
)
```

---

## 六、前端交互

### 6.1 布局

```
┌──────────────────┬────────────────────────────────┐
│                  │                                │
│   搜索/筛选      │         用户详情               │
│                  │                                │
│   用户列表       │   ┌─────────────────────────┐ │
│   - email       │   │ 基本信息 | 订阅 | 积分  │ │
│   - tier        │   │ 项目 | 支付 | 环境     │ │
│   - created_at  │   └─────────────────────────┘ │
│                  │                                │
│                  │   [调整积分] [设置折扣]       │
│                  │                                │
└──────────────────┴────────────────────────────────┘
```

### 6.2 操作弹窗

- 积分调整: 选择桶、输入金额、填写原因
- Tier 变更: 选择新 Tier、确认影响
- 退款: 选择订单、确认金额

---

## 七、相关文档

- [Admin API 端点](../../api/admin-endpoints.md)
- [权限矩阵](../../../05-business/entitlement/permission-matrix.md)
- [积分系统](../billing/architecture.md)

---

**END OF DOCUMENT**
