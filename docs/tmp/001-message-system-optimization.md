# 消息系统统一优化方案 v1.0

> **状态**: 待确认
> **创建日期**: 2026-01-19
> **预计工期**: 4-6 天

---

## 一、背景

### 1.1 问题概述

基于对项目的全面调研，发现当前消息处理存在以下问题：

**前端问题**:
- 501 个 `console.log/error/warn` 调用分散在 173 个文件
- Toast 显示时机不一致（有时全局 toast，有时手动，有时不显示）
- 错误处理逻辑在各个 hook 中重复实现
- 错误信息对用户不够友好（如显示 `validation_error`）
- 46 个文件中各自维护 `setError` 状态

**后端问题**:
- 日志级别使用不规范
- `context` 字段内容不统一
- 部分日志可能包含敏感信息

**前后端不一致**:
- 错误代码基本一致，但缺少同步机制
- Request ID 获取方式不统一

### 1.2 调研数据

| 指标 | 前端 | 后端 |
|------|------|------|
| 日志调用数 | 501 | 1,450 |
| 涉及文件数 | 173 | 195 |
| Toast 组件 | 自定义 (Toast.tsx) | - |
| 错误日志服务 | errorLogger.ts | Sentry + JSON Logger |
| 统一异常框架 | ApiError 类 | AppException 基类 |

---

## 二、业界最佳实践参考

| 公司 | 实践 |
|------|------|
| **Stripe** | 统一错误代码 + 用户友好消息 + Request ID 追踪 |
| **GitHub** | Toast 通知分层（success/error/warning/info）+ 表单内联错误 |
| **Vercel** | 开发环境详细日志 + 生产环境精简日志 + Sentry 集成 |
| **Linear** | 全局错误边界 + 统一 Toast 系统 + 操作反馈一致性 |

---

## 三、核心设计原则

### 3.1 分层架构

```
┌─────────────────────────────────────────────────────────────────┐
│                       消息处理分层架构                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐ │
│  │   用户层    │    │   开发层    │    │      监控层         │ │
│  │  (Toast)   │    │   (Log)    │    │   (Sentry/日志)     │ │
│  └─────────────┘    └─────────────┘    └─────────────────────┘ │
│        ↑                  ↑                      ↑             │
│        │                  │                      │             │
│  ┌─────┴──────────────────┴──────────────────────┴───────────┐ │
│  │                  统一消息处理中心                          │ │
│  │              (MessageService / useMessage)                │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 消息类型矩阵

| 场景 | 用户看到 (Toast) | 开发者看到 (Log) | 上报 Sentry |
|------|------------------|------------------|-------------|
| **操作成功** | ✅ success toast | ❌ 不打印 | ❌ |
| **业务警告** | ⚠️ warning toast | ⚠️ console.warn (dev) | ❌ |
| **API 错误** | ❌ error toast | ❌ console.error (dev) | ✅ |
| **网络错误** | ❌ error toast | ❌ console.error (dev) | ✅ |
| **表单验证** | 📍 内联错误 | ❌ 不打印 | ❌ |
| **权限不足** | ❌ error toast + 引导 | ⚠️ console.warn | ✅ |
| **调试信息** | ❌ 不显示 | 🔍 console.log (dev) | ❌ |

---

## 四、前端优化方案

### 4.1 统一消息 Hook (`useMessage`)

```typescript
// hooks/useMessage.ts
interface MessageService {
  // 用户通知 (Toast)
  success(message: string, options?: ToastOptions): void;
  error(message: string, options?: ToastOptions): void;
  warning(message: string, options?: ToastOptions): void;
  info(message: string, options?: ToastOptions): void;

  // 开发日志 (仅开发环境打印)
  log(context: string, data?: any): void;
  debug(context: string, data?: any): void;

  // 错误上报 (开发环境打印 + 生产环境上报)
  reportError(error: Error | ApiError, context?: ErrorContext): void;
}
```

### 4.2 错误消息用户友好化

```typescript
// lib/errorMessages.ts
const USER_FRIENDLY_MESSAGES: Record<ErrorCode, string> = {
  // 认证
  'auth_unauthorized': '请先登录后再操作',
  'auth_forbidden': '您没有权限执行此操作',
  'auth_token_expired': '登录已过期，请重新登录',

  // 资源
  'resource_not_found': '找不到请求的资源',
  'project_not_found': '项目不存在或已被删除',

  // 计费
  'billing_insufficient_credits': '积分不足，请充值后重试',
  'billing_payment_failed': '支付失败，请检查支付方式',

  // AI
  'ai_generation_failed': 'AI 生成失败，请稍后重试',
  'ai_provider_timeout': 'AI 服务响应超时，请重试',
  'ai_content_policy': '内容不符合使用规范，请修改后重试',

  // 网络
  'network_error': '网络连接失败，请检查网络设置',
  'timeout': '请求超时，请稍后重试',

  // 上传
  'upload_file_too_large': '文件太大，请选择更小的文件',
  'upload_invalid_type': '不支持的文件格式',

  // 默认
  'server_error': '服务器出错了，我们正在处理中',
};
```

### 4.3 Logger 工具类

```typescript
// lib/logger.ts
class Logger {
  private context: string;

  constructor(context: string) {
    this.context = context;
  }

  // 开发环境打印
  log(message: string, data?: any): void {
    if (process.env.NODE_ENV === 'development') {
      console.log(`[${this.context}]`, message, data);
    }
  }

  warn(message: string, data?: any): void {
    if (process.env.NODE_ENV === 'development') {
      console.warn(`[${this.context}]`, message, data);
    }
  }

  // 错误上报（开发+生产）
  error(message: string, error?: Error, data?: any): void {
    if (process.env.NODE_ENV === 'development') {
      console.error(`[${this.context}]`, message, error, data);
    }
    // 生产环境上报到 errorLogger
    errorLogger.log({
      message,
      error,
      context: this.context,
      ...data
    });
  }
}

// 使用方式
const logger = new Logger('CreateProjectModal');
logger.log('Creating project', { title });
logger.error('Failed to create project', error);
```

---

## 五、后端优化方案

### 5.1 日志级别标准化

| 级别 | 使用场景 | 示例 |
|------|----------|------|
| **ERROR** | 需要立即处理的错误 | 数据库连接失败、支付处理失败 |
| **WARNING** | 潜在问题但不影响功能 | 用户达到限制、重试成功 |
| **INFO** | 重要业务事件 | 用户注册、订阅购买、项目创建 |
| **DEBUG** | 调试信息 | SQL 查询、请求参数 |

### 5.2 日志结构标准化

```python
# 标准日志格式
logger.info(
    "Project created successfully",
    extra={
        "event": "project.created",     # 事件标识符
        "user_id": user_id,             # 用户 ID
        "project_id": project_id,       # 资源 ID
        "tier": user_tier,              # 上下文信息
        "duration_ms": 120,             # 性能指标
    }
)

# 错误日志格式
logger.error(
    "Payment processing failed",
    extra={
        "event": "payment.failed",
        "user_id": user_id,
        "error_code": "stripe_declined",
        "amount": amount,
    },
    exc_info=True  # 包含堆栈跟踪
)
```

### 5.3 敏感数据脱敏规则

```python
SENSITIVE_KEYS = [
    'password', 'token', 'secret', 'key', 'authorization',
    'credit_card', 'ssn', 'api_key', 'access_token', 'refresh_token',
    'bearer', 'credential', 'private_key'
]

SENSITIVE_PATTERNS = [
    r'sk_live_[a-zA-Z0-9]+',  # Stripe live key
    r'sk_test_[a-zA-Z0-9]+',  # Stripe test key
    r'Bearer\s+[a-zA-Z0-9\-_]+',  # Bearer token
]
```

---

## 六、实施计划

### Phase 1: 前端消息统一 (2-3 天)

| 任务 | 优先级 | 说明 | 预计时间 |
|------|--------|------|----------|
| 创建 `useMessage` hook | P0 | 统一消息处理入口 | 2h |
| 创建 `errorMessages.ts` | P0 | 用户友好消息映射 | 1h |
| 创建 `Logger` 工具类 | P0 | 开发日志统一管理 | 1h |
| 重构 API 错误处理 | P0 | 统一使用 useMessage | 4h |
| 移除冗余 console.log | P1 | 清理 501 处 console 调用 | 4h |
| 统一表单错误处理 | P1 | 创建 `useFormError` hook | 2h |

### Phase 2: 后端日志优化 (1-2 天)

| 任务 | 优先级 | 说明 | 预计时间 |
|------|--------|------|----------|
| 创建日志规范文档 | P0 | 标准化日志级别和格式 | 1h |
| 统一日志 extra 字段 | P1 | 标准化 context 内容 | 3h |
| 增强敏感数据脱敏 | P1 | 完善脱敏规则 | 2h |
| 审查关键模块日志 | P2 | 支付/认证模块 | 2h |

### Phase 3: 前后端协同 (1 天)

| 任务 | 优先级 | 说明 | 预计时间 |
|------|--------|------|----------|
| 同步错误代码定义 | P0 | 确保前后端一致 | 1h |
| Request ID 显示优化 | P1 | 方便用户反馈 | 1h |
| 创建错误处理最佳实践文档 | P2 | 团队规范 | 2h |

---

## 七、预期效果

| 指标 | 当前 | 优化后 |
|------|------|--------|
| 前端 console 调用数 | 501 | < 50 (仅保留必要调试) |
| 用户错误消息可读性 | 60% | 95% |
| 错误可追溯性 | 中 | 高 (统一 Request ID) |
| 代码重复度 | 高 | 低 (统一 hook) |
| 日志查询效率 | 低 | 高 (结构化日志) |

---

## 八、待确认事项

1. **Toast 位置**: 当前右下角，是否需要调整？
2. **错误消息语言**: 当前中英文混用，是否统一为中文？
3. **日志保留时间**: 前端本地日志最多保留 100 条，是否需要调整？
4. **敏感数据**: 是否有其他需要脱敏的字段？

---

**文档版本**: v1.0
**最后更新**: 2026-01-19
