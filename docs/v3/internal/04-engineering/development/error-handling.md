# 错误处理规范

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [fullstack]
> **来源**: v1 2-Rules/coding/ERROR-HANDLING

---

## 概述

前后端错误处理的统一规范。

---

## 后端错误处理

### 异常层次

```python
# 基础异常
class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code

# 业务异常
class NotFoundError(AppError):
    def __init__(self, resource: str):
        super().__init__("NOT_FOUND", f"{resource} not found", 404)

class UnauthorizedError(AppError):
    def __init__(self):
        super().__init__("UNAUTHORIZED", "Authentication required", 401)

class ForbiddenError(AppError):
    def __init__(self):
        super().__init__("FORBIDDEN", "Permission denied", 403)
```

### API 错误响应格式

```json
{
  "error": {
    "code": "INSUFFICIENT_CREDITS",
    "message": "Not enough credits to perform this action",
    "details": {
      "required": 10,
      "available": 5
    }
  }
}
```

---

## 前端错误处理

### API 错误处理

```typescript
try {
  const result = await api.doSomething();
} catch (error) {
  if (error instanceof ApiError) {
    // 业务错误
    toast.error(error.message);
  } else {
    // 未知错误
    toast.error('Something went wrong');
    logger.error(error);
  }
}
```

### 错误边界

```typescript
<ErrorBoundary fallback={<ErrorPage />}>
  <App />
</ErrorBoundary>
```

---

## 错误码列表

| 错误码 | HTTP | 说明 |
|--------|------|------|
| UNAUTHORIZED | 401 | 未认证 |
| FORBIDDEN | 403 | 无权限 |
| NOT_FOUND | 404 | 资源不存在 |
| VALIDATION_ERROR | 400 | 参数验证失败 |
| INSUFFICIENT_CREDITS | 402 | 积分不足 |
| RATE_LIMITED | 429 | 请求过于频繁 |
| INTERNAL_ERROR | 500 | 服务器内部错误 |

---

## 相关文档

- [API 错误码](../api/error-codes.md)
- [日志规范](./logging-standard.md)
