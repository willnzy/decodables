# 日志标准

> 后端日志规范与审计要求

**验证状态**: 🟢 已验证  
**同步范围**: [backend]  
**代码来源**: `core/logging.py`, `core/config.py`

---

## 一、核心原则

1. **结构化日志**: 使用 JSON 格式，便于搜索和分析
2. **审计追踪**: 关键操作必须记录审计日志
3. **隐私保护**: 禁止记录敏感信息明文
4. **性能考量**: 避免过度日志影响性能

---

## 二、日志级别

| 级别 | 用途 | 示例 |
|------|------|------|
| DEBUG | 调试信息 | 变量值、流程追踪 |
| INFO | 正常操作 | 请求完成、任务执行 |
| WARNING | 潜在问题 | 重试、降级 |
| ERROR | 错误 | 异常、失败 |
| CRITICAL | 严重故障 | 系统不可用 |

---

## 三、日志格式

### 3.1 结构化日志

```python
import structlog

logger = structlog.get_logger()

# 正确示例
logger.info(
    "user_login_success",
    user_id=user_id,
    method="email",
    ip_address=request.client.host
)

# 错误示例 - 避免
logger.info(f"User {user_id} logged in")  # 非结构化
```

### 3.2 标准字段

```python
LOG_CONTEXT = {
    "timestamp": "ISO 8601",
    "level": "INFO/ERROR/...",
    "event": "事件名称",
    "request_id": "请求追踪 ID",
    "user_id": "用户 ID (如果有)",
    "module": "模块名称",
    "duration_ms": "操作耗时",
}
```

### 3.3 输出格式

```json
{
    "timestamp": "2026-01-15T10:30:00.000Z",
    "level": "INFO",
    "event": "payment_completed",
    "request_id": "req_abc123",
    "user_id": "uuid",
    "amount": 9.99,
    "currency": "USD",
    "duration_ms": 1250
}
```

---

## 四、审计日志

### 4.1 必须审计的操作

| 类别 | 操作 |
|------|------|
| 认证 | 登录、登出、密码修改 |
| 支付 | 订阅、退款、积分变动 |
| 权限 | Tier 变更、权限授予 |
| 数据 | 删除操作、导出操作 |
| Admin | 所有管理操作 |

### 4.2 审计日志格式

```python
logger.info(
    "audit_credit_deduction",
    user_id=user_id,
    action="deduct_credits",
    amount=5,
    reason="ai_generation",
    before_monthly=100,
    before_permanent=50,
    after_monthly=95,
    after_permanent=50,
    operator_id=None,  # None = 系统操作
    ip_address=request.client.host
)
```

### 4.3 审计日志存储

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,
    user_id UUID,
    operator_id UUID,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    changes JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 五、敏感数据处理

### 5.1 禁止记录

- 密码 (包括哈希)
- 完整银行卡号
- 完整身份证号
- API 密钥
- JWT Token

### 5.2 脱敏规则

```python
def mask_email(email: str) -> str:
    """邮箱脱敏: u***@example.com"""
    parts = email.split('@')
    if len(parts) == 2:
        return f"{parts[0][0]}***@{parts[1]}"
    return "***"

def mask_card(card: str) -> str:
    """卡号脱敏: **** **** **** 1234"""
    return f"**** **** **** {card[-4:]}"

def mask_phone(phone: str) -> str:
    """手机脱敏: 138****5678"""
    return f"{phone[:3]}****{phone[-4:]}"
```

### 5.3 安全日志示例

```python
# 正确
logger.info("payment_success", user_email=mask_email(email), amount=9.99)

# 错误
logger.info("payment_success", user_email=email, card_number=card)
```

---

## 六、错误日志

### 6.1 异常记录

```python
try:
    result = await process_payment(...)
except PaymentError as e:
    logger.error(
        "payment_failed",
        user_id=user_id,
        error_type=type(e).__name__,
        error_message=str(e),
        stripe_error_code=e.code if hasattr(e, 'code') else None,
        exc_info=True  # 包含堆栈
    )
    raise
```

### 6.2 错误上下文

```python
logger.error(
    "external_api_error",
    service="stripe",
    endpoint="/v1/subscriptions",
    status_code=500,
    response_body=truncate(response.text, 500),  # 限制长度
    retry_count=3,
    duration_ms=elapsed
)
```

---

## 七、性能日志

### 7.1 慢查询日志

```python
SLOW_QUERY_THRESHOLD_MS = 500

@log_slow_query(threshold_ms=SLOW_QUERY_THRESHOLD_MS)
async def get_user_projects(...):
    ...

# 自动记录
logger.warning(
    "slow_query",
    function="get_user_projects",
    duration_ms=1200,
    params={"user_id": "..."}
)
```

### 7.2 请求日志

```python
# 中间件自动记录
logger.info(
    "http_request",
    method="POST",
    path="/api/v1/projects",
    status_code=201,
    duration_ms=350,
    user_id="...",
    request_id="..."
)
```

---

## 八、日志配置

### 8.1 环境配置

```python
# config.py
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "json")  # json/console

# 开发环境: console 格式，DEBUG 级别
# 生产环境: json 格式，INFO 级别
```

### 8.2 日志轮转

```yaml
# 生产环境日志配置
logging:
  max_size: 100MB
  max_files: 10
  retention_days: 30
```

---

## 九、最佳实践

### 9.1 DO

- ✅ 使用结构化日志
- ✅ 包含 request_id 追踪
- ✅ 记录操作耗时
- ✅ 敏感数据脱敏
- ✅ 异常包含堆栈

### 9.2 DON'T

- ❌ 记录密码/密钥
- ❌ 过度日志
- ❌ 日志中拼接字符串
- ❌ 忽略错误日志
- ❌ 生产环境使用 DEBUG

---

## 十、相关文档

- [测试指南](./testing-guide.md)
- [部署与扩展](../06-operations/deployment-scaling.md)
