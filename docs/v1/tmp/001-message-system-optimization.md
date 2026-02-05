# 消息系统统一优化方案 v2.0

> **状态**: 审计完成，待执行
> **创建日期**: 2026-01-19
> **审计日期**: 2026-01-19
> **预计工期**: 4-6 天 (22.5h)

---

## 一、审计摘要

### 1.1 总体发现

| 类别 | 文件数 | 问题数 | 合规率 |
|------|--------|--------|--------|
| **前端 console 调用** | 131 | 379 | ~20% |
| **前端 toast 调用** | 101 | 237 | ~60% |
| **后端 logger 调用** | 185 | 1,422 | ~1.4% (结构化) |
| **后端 print 调用** | 2 | 2 | 0% |

### 1.2 核心问题

1. **前端**: 大量直接使用 `console.*`，未使用统一的 Logger 工具
2. **前端**: 部分 toast 显示原始错误信息给用户
3. **后端**: 仅 1.4% 的日志使用结构化 `extra=` 字段
4. **后端**: 2 处源代码中使用 `print()`

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

## 四、前端审计详情

### 4.1 Console 调用统计

**总计**: 131 文件，379 调用

| 调用类型 | 数量 | 占比 |
|----------|------|------|
| console.log | 101 | 26.6% |
| console.error | 189 | 49.9% |
| console.warn | 82 | 21.6% |
| console.info | 1 | 0.3% |
| console.debug | 6 | 1.6% |

### 4.2 Console 调用按优先级分类

#### P0 - Critical (服务层核心文件)

| 文件 | 调用数 | 问题描述 |
|------|--------|----------|
| `services/errorLogger.ts` | 15+ | 日志服务自身使用 console |
| `services/taskService.ts` | 10+ | WebSocket 调试信息 |
| `services/generateService.ts` | 8+ | AI 生成服务日志 |
| `services/analyticsService.ts` | 5+ | 分析服务调试 |
| `services/api.ts` | 5+ | API 基础请求日志 |

#### P1 - Important (Admin 和 Editor)

| 文件 | 调用数 | 问题描述 |
|------|--------|----------|
| `components/admin/*.tsx` | 41 | Admin 面板调试日志 (11 个文件) |
| `app/create/_hooks/*.ts` | 40+ | 编辑器 hooks 调试 (15 个文件) |
| `app/create/_stores/*.ts` | 15+ | 状态管理调试 |

#### P2 - Low (组件和工具)

| 文件 | 调用数 | 问题描述 |
|------|--------|----------|
| `lib/*.ts` | 25+ | 工具库调试 (10 个文件) |
| `hooks/*.ts` | 20+ | 通用 hooks (8 个文件) |

### 4.3 Toast 调用问题

**总计**: 101 文件，237 调用

#### 问题类型 A: 硬编码消息 (50+)

```
位置: components/admin/*.tsx
问题: 50+ 处硬编码错误消息
示例: toast.error("Failed to load users")
应改: message.error(getUserFriendlyMessage(error.code))
```

#### 问题类型 B: 显示原始错误 (10+)

```
位置: app/create/_hooks/ai/useAIGeneration.ts:196
问题: 直接显示 error.message 给用户
代码: toast.error(error.message)
风险: 可能暴露技术细节
```

#### 问题类型 C: 重复 toast + console.error (7+)

```
位置: 多个文件
问题: 同时调用 toast.error 和 console.error
应改: 使用 useMessage + logger 统一处理
```

#### 问题类型 D: Marketplace 硬编码 (8)

```
位置: hooks/usePurchase.ts, hooks/usePurchaseFlow.ts
问题: 购买流程的 8 个硬编码消息
示例: "Purchase successful!", "Failed to purchase item"
```

---

## 五、后端审计详情

### 5.1 Logger 调用统计

**总计**: 185 文件，1,422 调用

| 调用类型 | 数量 |
|----------|------|
| logger.info | 512 |
| logger.error | 389 |
| logger.warning | 287 |
| logger.debug | 198 |
| logger.exception | 36 |

### 5.2 结构化日志合规率

**使用 `extra=` 的文件**: 仅 7 个 (~1.4%)

```
domains/platform/events/service.py        # ✅ 示范文件
domains/platform/events/repository.py     # ✅ 示范文件
api/routers/events.py                     # ✅ 示范文件
(其他 4 个文件)
```

### 5.3 高优先级文件 (调用数最多)

| 文件 | 调用数 | 优先级 |
|------|--------|--------|
| `domains/platform/ai/service.py` | 145 | P0 |
| `shared/payment/stripe_webhook_service.py` | 56 | P0 |
| `domains/billing/service.py` | 48 | P0 |
| `domains/identity/service.py` | 42 | P0 |
| `api/routers/admin/*.py` | 120+ | P1 |
| `shared/ai/*.py` | 80+ | P1 |

### 5.4 Print 语句 (严重违规)

| 文件 | 行号 | 代码 |
|------|------|------|
| `core/feature_flag/service.py` | 150 | `print(f"Feature flag {key} evaluated...")` |
| `shared/ai/story_generator.py` | 233 | `print(f"Generated story: {len(story)} chars")` |

---

## 六、前端优化方案

### 6.1 统一消息 Hook (`useMessage`)

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

### 6.2 错误消息用户友好化

```typescript
// lib/errorMessages.ts
const USER_FRIENDLY_MESSAGES: Record<ErrorCode, string> = {
  // 认证
  'AUTH_EXPIRED': 'Session expired. Please sign in again.',
  'AUTH_INVALID': 'Invalid credentials. Please try again.',
  'AUTH_FORBIDDEN': 'You don\'t have permission to perform this action.',

  // 资源
  'RES_NOT_FOUND': 'The requested item was not found.',
  'RES_LIMIT_REACHED': 'You\'ve reached the limit for this feature.',
  'RES_ALREADY_EXISTS': 'This item already exists.',

  // 支付
  'PAY_FAILED': 'Payment failed. Please try again.',
  'PAY_INSUFFICIENT': 'Insufficient credits. Please top up.',
  'PAY_CARD_DECLINED': 'Card declined. Please use a different card.',

  // AI
  'AI_GENERATION_FAILED': 'AI generation failed. Please try again.',
  'AI_PROVIDER_TIMEOUT': 'AI service timed out. Please retry.',
  'AI_CONTENT_POLICY': 'Content doesn\'t meet guidelines. Please modify.',

  // 网络
  'NET_TIMEOUT': 'Request timed out. Please try again.',
  'NET_OFFLINE': 'No internet connection.',
  'NET_SERVER_ERROR': 'Server error. Please try again later.',

  // 上传
  'UPLOAD_FILE_TOO_LARGE': 'File too large. Please choose a smaller file.',
  'UPLOAD_INVALID_TYPE': 'Unsupported file format.',

  // 默认
  'UNKNOWN': 'Something went wrong. Please try again.',
};
```

### 6.3 Logger 工具类

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

## 七、后端优化方案

### 7.1 日志级别标准化

| 级别 | 使用场景 | 示例 |
|------|----------|------|
| **ERROR** | 需要立即处理的错误 | 数据库连接失败、支付处理失败 |
| **WARNING** | 潜在问题但不影响功能 | 用户达到限制、重试成功 |
| **INFO** | 重要业务事件 | 用户注册、订阅购买、项目创建 |
| **DEBUG** | 调试信息 | SQL 查询、请求参数 |

### 7.2 日志结构标准化

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

### 7.3 敏感数据脱敏规则

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

## 八、实施计划

### Phase 1: 前端基础设施建设 (Day 1) - 2h

**目标**: 创建前端统一日志/消息工具

| 任务 | 文件 | 预估 |
|------|------|------|
| 1.1 创建 Logger 工具类 | `lib/logger.ts` | 30min |
| 1.2 创建 useMessage hook | `hooks/useMessage.ts` | 30min |
| 1.3 创建错误码映射 | `lib/errorMessages.ts` | 30min |
| 1.4 导出统一接口 | `lib/index.ts` | 10min |

### Phase 2: 后端 print 清理 (Day 1) - 0.5h

**目标**: 消除所有 print 语句

| 任务 | 文件 | 行号 |
|------|------|------|
| 2.1 替换 feature_flag print | `core/feature_flag/service.py` | 150 |
| 2.2 替换 story_generator print | `shared/ai/story_generator.py` | 233 |

### Phase 3: 前端 Services 层迁移 (Day 2-3) - 4h

**目标**: 服务层使用 Logger

| 优先级 | 文件 | 调用数 |
|--------|------|--------|
| P0 | `services/errorLogger.ts` | 15 |
| P0 | `services/taskService.ts` | 10 |
| P0 | `services/generateService.ts` | 8 |
| P0 | `services/analyticsService.ts` | 5 |
| P0 | `services/api.ts` | 5 |
| P1 | `services/projectService.ts` | 5 |
| P1 | `services/userService.ts` | 5 |
| P1 | 其他 services (6 个文件) | 20+ |

### Phase 4: 后端结构化日志 (Day 3-5) - 8h

**目标**: 高优先级文件添加 extra 字段

**规则**: 每个 logger 调用添加 `extra={"user_id": ..., "action": ..., ...}`

| 优先级 | 模块 | 文件数 | 调用数 |
|--------|------|--------|--------|
| P0 | 支付/计费 | 5 | 100+ |
| P0 | AI 服务 | 8 | 225 |
| P1 | 用户/认证 | 6 | 80+ |
| P1 | 项目/素材 | 8 | 100+ |
| P2 | Admin API | 15 | 120+ |

### Phase 5: 前端 Toast 优化 (Day 5-6) - 4h

**目标**: 使用错误码映射，消除硬编码

| 任务 | 范围 | 消息数 |
|------|------|--------|
| 5.1 Admin 面板 | `components/admin/*.tsx` | 50+ |
| 5.2 编辑器 hooks | `app/create/_hooks/*.ts` | 20+ |
| 5.3 购买流程 | `hooks/usePurchase*.ts` | 8 |

### Phase 6: 前端组件层 (Day 6-7) - 4h

**目标**: 组件使用 logger + useMessage

| 模块 | 文件数 | 调用数 |
|------|--------|--------|
| Editor 组件 | 20+ | 50+ |
| Common 组件 | 15+ | 30+ |
| Page 组件 | 10+ | 25+ |

---

## 九、验收标准

### 9.1 前端检查清单

- [ ] 无直接 `console.log/error/warn` (使用 logger)
- [ ] 无硬编码 toast 消息 (使用 useMessage + 错误码)
- [ ] 无 `toast.error(error.message)` (使用 getUserFriendlyMessage)
- [ ] 开发环境可见调试日志
- [ ] 生产环境无调试输出

### 9.2 后端检查清单

- [ ] 无 `print()` 语句
- [ ] 100% logger 调用使用 `extra=` 字段
- [ ] extra 包含: user_id (如适用), action, 关键业务数据
- [ ] 无敏感信息泄露 (密码、token 等)
- [ ] 错误日志包含 `exc_info=True`

### 9.3 自动化检查

```bash
# 前端检查
grep -r "console\." --include="*.ts" --include="*.tsx" | grep -v node_modules | wc -l
# 目标: 0

# 后端检查
grep -r "print(" --include="*.py" | grep -v __pycache__ | grep -v test | wc -l
# 目标: 0

grep -r "logger\." --include="*.py" | grep -v "extra=" | wc -l
# 目标: 显著减少
```

---

## 十、预期效果

| 指标 | 当前 | 优化后 |
|------|------|--------|
| 前端 console 调用数 | 379 | < 50 (仅保留必要调试) |
| 后端结构化日志率 | 1.4% | > 90% |
| 用户错误消息可读性 | 60% | 95% |
| 错误可追溯性 | 中 | 高 (统一 Request ID) |
| 代码重复度 | 高 | 低 (统一 hook) |
| 日志查询效率 | 低 | 高 (结构化日志) |

---

## 十一、附录

### 11.1 后端使用 extra 的示范文件

```python
# domains/platform/events/service.py (示范)
logger.info(
    "Event tracked successfully",
    extra={
        "user_id": user_id,
        "event_type": event_type,
        "event_id": event.id
    }
)
```

### 11.2 前端 Logger 使用示范

```typescript
// 目标格式
import { logger } from '@/lib/logger'
import { useMessage, getUserFriendlyMessage } from '@/lib'

// 替换前
console.error('Failed to load project:', error)
toast.error(error.message)

// 替换后
logger.error('Failed to load project', error, { module: 'ProjectService', projectId })
message.error(getUserFriendlyMessage(error.code))
```

### 11.3 相关文档

- **规范文档**: `docs/shared/message-logging-standard.md`
- **项目配置**: `CLAUDE.md`

---

**文档版本**: v2.0
**最后更新**: 2026-01-19
**审计完成**: ✅
**执行状态**: 待开始
