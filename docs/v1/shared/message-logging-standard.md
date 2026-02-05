# 消息与日志处理规范 v1.0

> Make Decodables 前后端统一的消息、日志、错误处理标准

**版本**: v1.0
**创建日期**: 2026-01-19
**适用范围**: 前端 (decodables-fe) + 后端 (decodables)

---

## 1. 设计原则

### 1.1 核心理念

```
用户消息 ≠ 开发日志 ≠ 监控告警
```

| 层级 | 目标受众 | 输出方式 | 内容要求 |
|------|----------|----------|----------|
| **用户层** | 终端用户 | Toast/Modal | 友好、可操作、中英文 |
| **开发层** | 开发人员 | Console/Log | 详细、可追踪、结构化 |
| **监控层** | 运维/SRE | Sentry/Metrics | 自动聚合、告警规则 |

### 1.2 信息分类

| 类型 | 用户看到 | 开发日志 | Sentry |
|------|----------|----------|--------|
| **成功** | Toast (success) | INFO | - |
| **警告** | Toast (warning) | WARN | 可选 |
| **业务错误** | Toast (error) | WARN | - |
| **系统错误** | Toast (error) | ERROR | 自动 |
| **调试信息** | - | DEBUG (dev only) | - |

---

## 2. 前端规范

### 2.1 消息 Hook (useMessage)

```typescript
// @shared/hooks/useMessage.ts
import { toast } from 'sonner'

type MessageType = 'success' | 'error' | 'warning' | 'info'

interface MessageOptions {
  description?: string
  duration?: number
  action?: {
    label: string
    onClick: () => void
  }
}

export function useMessage() {
  const showMessage = (
    type: MessageType,
    title: string,
    options?: MessageOptions
  ) => {
    // 生产环境：显示 Toast
    toast[type](title, {
      description: options?.description,
      duration: options?.duration ?? 4000,
      action: options?.action
    })

    // 开发环境：同时输出日志
    if (process.env.NODE_ENV === 'development') {
      const logLevel = type === 'error' ? 'error' : type === 'warning' ? 'warn' : 'info'
      console[logLevel](`[Message] ${type.toUpperCase()}: ${title}`, options)
    }
  }

  return {
    success: (title: string, options?: MessageOptions) => showMessage('success', title, options),
    error: (title: string, options?: MessageOptions) => showMessage('error', title, options),
    warning: (title: string, options?: MessageOptions) => showMessage('warning', title, options),
    info: (title: string, options?: MessageOptions) => showMessage('info', title, options),
  }
}
```

### 2.2 错误码映射

```typescript
// @shared/constants/errorMessages.ts

// 后端错误码 → 用户友好消息
export const ERROR_MESSAGES: Record<string, string> = {
  // 认证错误 (AUTH_xxx)
  AUTH_EXPIRED: 'Session expired. Please sign in again.',
  AUTH_INVALID: 'Invalid credentials. Please try again.',
  AUTH_FORBIDDEN: 'You don\'t have permission to perform this action.',

  // 资源错误 (RES_xxx)
  RES_NOT_FOUND: 'The requested item was not found.',
  RES_LIMIT_REACHED: 'You\'ve reached the limit for this feature.',
  RES_ALREADY_EXISTS: 'This item already exists.',

  // 支付错误 (PAY_xxx)
  PAY_FAILED: 'Payment failed. Please try again.',
  PAY_INSUFFICIENT: 'Insufficient credits. Please top up.',
  PAY_CARD_DECLINED: 'Card declined. Please use a different card.',

  // 网络错误 (NET_xxx)
  NET_TIMEOUT: 'Request timed out. Please try again.',
  NET_OFFLINE: 'No internet connection.',
  NET_SERVER_ERROR: 'Server error. Please try again later.',

  // 通用错误
  UNKNOWN: 'Something went wrong. Please try again.',
}

// HTTP 状态码 → 错误码
export const HTTP_ERROR_MAP: Record<number, string> = {
  401: 'AUTH_EXPIRED',
  403: 'AUTH_FORBIDDEN',
  404: 'RES_NOT_FOUND',
  409: 'RES_ALREADY_EXISTS',
  429: 'NET_TIMEOUT',
  500: 'NET_SERVER_ERROR',
  502: 'NET_SERVER_ERROR',
  503: 'NET_SERVER_ERROR',
}

// 获取用户友好的错误消息
export function getUserFriendlyMessage(
  errorCode?: string,
  httpStatus?: number,
  fallback?: string
): string {
  if (errorCode && ERROR_MESSAGES[errorCode]) {
    return ERROR_MESSAGES[errorCode]
  }
  if (httpStatus && HTTP_ERROR_MAP[httpStatus]) {
    return ERROR_MESSAGES[HTTP_ERROR_MAP[httpStatus]]
  }
  return fallback || ERROR_MESSAGES.UNKNOWN
}
```

### 2.3 日志工具类

```typescript
// @shared/utils/logger.ts

type LogLevel = 'debug' | 'info' | 'warn' | 'error'

interface LogContext {
  module?: string
  action?: string
  userId?: string
  [key: string]: unknown
}

class Logger {
  private isDev = process.env.NODE_ENV === 'development'

  private formatMessage(level: LogLevel, message: string, context?: LogContext): string {
    const timestamp = new Date().toISOString()
    const module = context?.module ? `[${context.module}]` : ''
    return `${timestamp} ${level.toUpperCase()} ${module} ${message}`
  }

  debug(message: string, context?: LogContext) {
    if (this.isDev) {
      console.log(this.formatMessage('debug', message, context), context)
    }
  }

  info(message: string, context?: LogContext) {
    if (this.isDev) {
      console.info(this.formatMessage('info', message, context), context)
    }
  }

  warn(message: string, context?: LogContext) {
    console.warn(this.formatMessage('warn', message, context), context)
  }

  error(message: string, error?: Error, context?: LogContext) {
    console.error(this.formatMessage('error', message, context), { error, ...context })

    // 生产环境：发送到 Sentry
    if (!this.isDev && typeof window !== 'undefined') {
      import('@sentry/nextjs').then(Sentry => {
        Sentry.captureException(error || new Error(message), {
          tags: { module: context?.module },
          extra: context
        })
      })
    }
  }
}

export const logger = new Logger()
```

### 2.4 使用示例

```typescript
// 组件中使用
function ProjectCard() {
  const message = useMessage()

  const handleDelete = async () => {
    try {
      await deleteProject(projectId)
      message.success('Project deleted successfully')
    } catch (error) {
      logger.error('Failed to delete project', error, {
        module: 'ProjectCard',
        projectId
      })
      message.error(getUserFriendlyMessage(error.code, error.status))
    }
  }
}
```

### 2.5 禁止事项

```typescript
// ❌ 错误：直接使用 console
console.log('User clicked button')
console.error('API failed:', error)

// ❌ 错误：向用户显示技术细节
toast.error(`Error: ${error.message}`)
toast.error('PGRST205: relation "projects" not found')

// ❌ 错误：在生产环境输出调试信息
console.log('Debug:', userData)

// ✅ 正确：使用 logger
logger.debug('User clicked button', { module: 'ProjectCard' })
logger.error('API failed', error, { module: 'ProjectService' })

// ✅ 正确：向用户显示友好消息
message.error(getUserFriendlyMessage(error.code))
```

---

## 3. 后端规范

### 3.1 日志配置

```python
# core/logging_config.py
import logging
import sys
from typing import Any, Dict

class StructuredFormatter(logging.Formatter):
    """结构化日志格式器"""

    def format(self, record: logging.LogRecord) -> str:
        # 基础信息
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # 添加 extra 字段
        if hasattr(record, 'extra'):
            log_data.update(record.extra)

        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return str(log_data)


def setup_logging(level: str = "INFO"):
    """配置日志系统"""
    logging.basicConfig(
        level=getattr(logging, level),
        format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
```

### 3.2 日志使用规范

```python
import logging

logger = logging.getLogger(__name__)

# ✅ 正确：使用 extra 字段
logger.info(
    "Project created successfully",
    extra={
        "user_id": user_id,
        "project_id": project.id,
        "title": project.title
    }
)

# ✅ 正确：错误日志包含上下文
logger.error(
    "Failed to create project",
    extra={
        "user_id": user_id,
        "error_type": type(e).__name__,
        "error_message": str(e)
    },
    exc_info=True  # 包含完整堆栈
)

# ❌ 错误：信息不完整
logger.info("Project created")

# ❌ 错误：使用 print
print(f"User {user_id} created project")

# ❌ 错误：日志中包含敏感信息
logger.info(f"User password: {password}")
```

### 3.3 错误码定义

```python
# core/error_codes.py
from enum import Enum

class ErrorCode(str, Enum):
    """统一错误码"""

    # 认证错误 (AUTH_xxx)
    AUTH_EXPIRED = "AUTH_EXPIRED"
    AUTH_INVALID = "AUTH_INVALID"
    AUTH_FORBIDDEN = "AUTH_FORBIDDEN"

    # 资源错误 (RES_xxx)
    RES_NOT_FOUND = "RES_NOT_FOUND"
    RES_LIMIT_REACHED = "RES_LIMIT_REACHED"
    RES_ALREADY_EXISTS = "RES_ALREADY_EXISTS"

    # 支付错误 (PAY_xxx)
    PAY_FAILED = "PAY_FAILED"
    PAY_INSUFFICIENT = "PAY_INSUFFICIENT"
    PAY_CARD_DECLINED = "PAY_CARD_DECLINED"

    # 验证错误 (VAL_xxx)
    VAL_INVALID_INPUT = "VAL_INVALID_INPUT"
    VAL_MISSING_FIELD = "VAL_MISSING_FIELD"
```

### 3.4 API 错误响应

```python
# core/exceptions.py
from fastapi import HTTPException
from typing import Optional

class APIError(HTTPException):
    """统一 API 错误"""

    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: Optional[dict] = None
    ):
        super().__init__(
            status_code=status_code,
            detail={
                "error_code": error_code,
                "message": message,
                "details": details or {}
            }
        )

# 使用示例
raise APIError(
    status_code=403,
    error_code=ErrorCode.RES_LIMIT_REACHED,
    message="User has reached the project limit",
    details={"current": 1, "limit": 1, "tier": "t1"}
)
```

### 3.5 日志级别指南

| 级别 | 使用场景 | 示例 |
|------|----------|------|
| **DEBUG** | 开发调试信息 | 变量值、中间状态 |
| **INFO** | 正常业务流程 | 用户登录、项目创建 |
| **WARNING** | 异常但可恢复 | 重试成功、降级处理 |
| **ERROR** | 错误需要关注 | API 失败、数据库错误 |
| **CRITICAL** | 系统级故障 | 服务不可用、数据损坏 |

---

## 4. 前后端协作

### 4.1 错误响应格式

后端返回标准错误格式：

```json
{
  "error_code": "RES_LIMIT_REACHED",
  "message": "User has reached the project limit",
  "details": {
    "current": 1,
    "limit": 1,
    "tier": "t1"
  }
}
```

前端处理：

```typescript
try {
  await api.createProject(data)
} catch (error) {
  const errorCode = error.response?.data?.error_code
  const details = error.response?.data?.details

  // 特殊处理：项目限制
  if (errorCode === 'RES_LIMIT_REACHED') {
    message.error('Project limit reached', {
      description: `Upgrade to create more projects (${details.current}/${details.limit})`,
      action: {
        label: 'Upgrade',
        onClick: () => router.push('/pricing')
      }
    })
    return
  }

  // 通用处理
  message.error(getUserFriendlyMessage(errorCode))
}
```

### 4.2 错误码对照表

| 错误码 | HTTP | 用户消息 | 触发场景 |
|--------|------|----------|----------|
| AUTH_EXPIRED | 401 | Session expired. Please sign in again. | JWT 过期 |
| AUTH_FORBIDDEN | 403 | You don't have permission to perform this action. | 权限不足 |
| RES_NOT_FOUND | 404 | The requested item was not found. | 资源不存在 |
| RES_LIMIT_REACHED | 403 | You've reached the limit for this feature. | 配额用尽 |
| PAY_INSUFFICIENT | 402 | Insufficient credits. Please top up. | 积分不足 |
| VAL_INVALID_INPUT | 400 | Invalid input. Please check and try again. | 参数校验失败 |
| NET_SERVER_ERROR | 500 | Server error. Please try again later. | 服务器异常 |

---

## 5. 迁移指南

### 5.1 前端迁移

```typescript
// Step 1: 替换 console.log
// Before
console.log('Project created:', project)

// After
logger.info('Project created', { module: 'ProjectService', projectId: project.id })

// Step 2: 替换直接 toast
// Before
toast.error(`Error: ${error.message}`)

// After
message.error(getUserFriendlyMessage(error.code, error.status))

// Step 3: 替换内联错误处理
// Before
catch (error) {
  console.error(error)
  alert('Something went wrong')
}

// After
catch (error) {
  logger.error('Operation failed', error, { module: 'Component' })
  message.error(getUserFriendlyMessage(error.code))
}
```

### 5.2 后端迁移

```python
# Step 1: 替换 print
# Before
print(f"Creating project for user {user_id}")

# After
logger.info("Creating project", extra={"user_id": user_id})

# Step 2: 添加结构化 extra
# Before
logger.info(f"Project {project_id} created by {user_id}")

# After
logger.info(
    "Project created",
    extra={
        "project_id": project_id,
        "user_id": user_id,
        "title": title
    }
)

# Step 3: 使用标准错误码
# Before
raise HTTPException(status_code=403, detail="Project limit reached")

# After
raise APIError(
    status_code=403,
    error_code=ErrorCode.RES_LIMIT_REACHED,
    message="User has reached the project limit",
    details={"current": current, "limit": limit}
)
```

---

## 6. 检查清单

### 6.1 代码审查

- [ ] 无直接 `console.log/error` (前端)
- [ ] 无直接 `print()` (后端)
- [ ] 错误消息用户友好
- [ ] 日志包含足够上下文
- [ ] 敏感信息未暴露

### 6.2 新功能开发

- [ ] 使用 `useMessage()` 显示用户消息
- [ ] 使用 `logger` 记录开发日志
- [ ] 定义必要的错误码
- [ ] 错误码映射到用户消息

---

## 附录 A: 相关文档

- [CLAUDE.md](../../CLAUDE.md) - 项目配置主文档
- [.claude/guides/MESSAGE-LOGGING-STANDARD.md](../../../.claude/guides/MESSAGE-LOGGING-STANDARD.md) - Claude Code 指南版本
- [docs/tmp/001-message-system-optimization.md](../tmp/001-message-system-optimization.md) - 优化实施计划

---

**文档版本**: v1.0
**最后更新**: 2026-01-19
