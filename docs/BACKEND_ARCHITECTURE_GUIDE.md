# Make Decodables v3.1 后端架构规范

> **版本**: v3.1
> **日期**: 2026-01-08
> **状态**: 标准规范 (所有新代码必须遵循)
> **DDD 合规性**: ~98%

---

## 目录

1. [架构总览](#1-架构总览)
2. [分层职责详解](#2-分层职责详解)
3. [目录结构标准](#3-目录结构标准)
4. [代码放置决策树](#4-代码放置决策树)
5. [依赖规则](#5-依赖规则)
6. [文件大小指导](#6-文件大小指导)
7. [命名规范](#7-命名规范)
8. [常见场景示例](#8-常见场景示例)

---

## 1. 架构总览

### 1.1 设计理念

```
┌─────────────────────────────────────────────────────────┐
│           三层架构 + 轻量级 DDD 融合架构                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  框架层与业务层清晰分离                                   │
│  业务逻辑按领域组织                                       │
│  规则内聚在聚合内                                         │
│  数据访问通过仓储抽象                                     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 1.2 分层结构

```
┌──────────────────────────────────────────────────────┐
│ api/                   API 层 (HTTP 入口)             │
│  - 路由定义                                           │
│  - 参数验证                                           │
│  - 响应格式化                                         │
└────────────────┬─────────────────────────────────────┘
                 │ 依赖
                 ▼
┌──────────────────────────────────────────────────────┐
│ application/           应用层 (用例编排)              │
│  - Commands (写操作)                                 │
│  - Queries (读操作)                                  │
│  - Event Handlers (事件处理)                         │
└────────────────┬─────────────────────────────────────┘
                 │ 依赖
                 ▼
┌──────────────────────────────────────────────────────┐
│ domains/               领域层 (业务核心)              │
│  - Aggregates (聚合根)                               │
│  - Entities (实体)                                   │
│  - Value Objects (值对象)                            │
│  - Domain Services (领域服务)                        │
│  - Repository Interfaces (仓储接口)                  │
└────────────────┬─────────────────────────────────────┘
                 │ 被实现
                 ▼
┌──────────────────────────────────────────────────────┐
│ infrastructure/        基础设施层 (技术实现)          │
│  - Repository Implementations (仓储实现)             │
│  - Event Bus (事件总线)                              │
│  - Unit of Work (工作单元)                           │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│ core/                  框架层 (100% 可复用)           │
│  - Auth, Cache, Database, Exceptions, Middleware     │
│  - Utils (通用工具)                                   │
│  - 🚫 不包含任何业务逻辑                              │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│ shared/                共享层 (服务抽象)              │
│  - AI, Payment, Storage, Analytics                   │
│  - 🔧 结构可复用，内容是业务相关的服务                 │
└──────────────────────────────────────────────────────┘
```

---

## 2. 分层职责详解

### 2.1 core/ - 框架层 (100% 复用)

**定义**: 完全业务无关的基础设施代码，可以直接复制到任何其他 FastAPI 项目使用。

**职责**:
- ✅ 认证抽象 (IAuthProvider)
- ✅ 缓存抽象 (ICacheProvider, Redis/Memory 实现)
- ✅ 数据库抽象 (IDatabase, Supabase Client)
- ✅ 统一异常 (BaseException, AuthException, ValidationException)
- ✅ 中间件 (Request ID, Logging, Error Handler, CORS)
- ✅ 通用工具 (datetime, hash, validators, pagination)

**禁止**:
- ❌ 任何业务逻辑 (用户等级、积分计算、项目限制等)
- ❌ 业务相关的异常类型 (InsufficientCreditsException 应在 domains 里)
- ❌ 业务相关的缓存键 (md:config:*, md:experiment:* 应在 infrastructure 里)
- ❌ 领域实体或值对象

**示例**:
```python
# ✅ core/utils/datetime.py
def utc_now() -> datetime:
    """获取当前 UTC 时间 (业务无关)"""
    return datetime.now(timezone.utc)

# ❌ 不应该在 core/
def get_monthly_reset_time() -> datetime:
    """获取月度积分重置时间 (业务相关，应在 domains/billing/)"""
```

#### 2.1.1 Async/Sync 最佳实践

**问题背景**: Supabase Python SDK 是同步的，但 FastAPI 是异步框架。在 `async def` 函数中直接调用同步 SDK 会阻塞事件循环。

**行业最佳实践**: 使用 `run_in_threadpool` 将同步调用移到线程池执行。

**参考来源**:
- [FastAPI 官方文档: Concurrency and async/await](https://fastapi.tiangolo.com/async/)
- [FastAPI GitHub Discussion #7623](https://github.com/fastapi/fastapi/discussions/7623)
- [Sentry: run_in_executor vs run_in_threadpool](https://sentry.io/answers/fastapi-difference-between-run-in-executor-and-run-in-threadpool/)

**工具函数** (`core/database/async_utils.py`):

```python
from fastapi.concurrency import run_in_threadpool
from core.database import run_sync, run_sync_safe

# 方式 1: 使用 run_in_threadpool (FastAPI 官方推荐)
result = await run_in_threadpool(
    lambda: supabase.table("users").select("*").execute()
)

# 方式 2: 使用 run_sync (项目封装)
result = await run_sync(
    lambda: supabase.table("users").select("*").execute()
)

# 方式 3: 使用 run_sync_safe (非关键操作，自动捕获异常)
await run_sync_safe(log_activity, user_id, "action", metadata, default=None)
```

**迁移策略**:
1. **新代码**: 必须使用 `run_in_threadpool` 或 `run_sync`
2. **现有代码**: 按模块优先级逐步迁移
3. **非关键操作**: 使用 `run_sync_safe` 并添加 try-catch

**示例 - Analytics API**:
```python
from fastapi.concurrency import run_in_threadpool

@router.post("/events")
async def log_analytics_events(...):
    # ❌ 旧方式 (阻塞事件循环)
    supabase.table("analytics_events").insert(data).execute()

    # ✅ 新方式 (非阻塞)
    await run_in_threadpool(
        lambda: supabase.table("analytics_events").insert(data).execute()
    )
```

---

### 2.2 shared/ - 共享层 (服务抽象)

**定义**: 跨领域的外部服务抽象，结构可复用但内容是业务相关的。

**职责**:
- ✅ AI 服务抽象 (ITextAIService, IImageAIService)
- ✅ 支付服务抽象 (IPaymentService)
- ✅ 存储服务抽象 (IStorageService)
- ✅ 分析追踪抽象 (IAnalyticsProvider)

**特点**:
- 提供接口定义 (interfaces.py)
- 提供数据类型 (types.py)
- 提供具体实现 (providers/)

**与 core 的区别**:
- `core/`: 纯技术框架，任何项目都能用
- `shared/`: 服务抽象，接口通用但实现可能包含业务配置

**示例**:
```python
# ✅ shared/ai/interfaces.py
class ITextAIService(ABC):
    """AI 文本服务抽象 (接口通用)"""
    @abstractmethod
    async def chat_completion(self, messages, model, **kwargs) -> AIResponse:
        pass

# ✅ shared/ai/providers/openai_provider.py
class OpenAITextProvider(ITextAIService):
    """OpenAI 实现 (可能包含业务配置，如默认模型)"""
    async def chat_completion(self, messages, model="gpt-4", **kwargs):
        # 实现细节...
```

---

### 2.3 domains/ - 领域层 (业务核心)

**定义**: 业务逻辑的核心，包含聚合根、实体、值对象、领域服务、仓储接口。

**职责**:
- ✅ 定义业务规则 (积分扣除优先级、等级权限判断)
- ✅ 聚合根封装不变量 (UserCredits.deduct() 保证不为负)
- ✅ 值对象表达业务概念 (Tier, Credits, PaperSize)
- ✅ 领域服务编排复杂业务逻辑
- ✅ 仓储接口定义数据访问抽象

**领域划分**:
```
domains/
├── identity/          # 身份域 (用户资料、等级、角色)
├── billing/           # 计费域 (积分、订阅、交易)
├── creation/          # 创作域 (项目、页面、元素)
├── marketplace/       # 市场域 (Listing、购买、审核)
├── ai_generation/     # AI 生成域 (生成任务、Prompt)
└── platform/          # 平台域 (Feature Flag, Experiment, Config)
```

**依赖规则**:
- ✅ 可以依赖: `core/`, `shared/` (抽象接口)
- ❌ 不能依赖: `infrastructure/`, `application/`, `api/`

**示例**:
```python
# ✅ domains/billing/aggregates/user_credits.py
@dataclass
class UserCredits:
    """用户积分聚合根 (封装业务规则)"""
    user_id: str
    credits_monthly: int
    credits_permanent: int

    def deduct(self, amount: int) -> TransactionRecord:
        """扣除积分 (先月度后永久)"""
        if self.total_credits < amount:
            raise InsufficientCreditsException(...)

        # 业务规则: 先扣月度积分
        if self.credits_monthly >= amount:
            self.credits_monthly -= amount
            return TransactionRecord(type=TransactionType.MONTHLY, amount=amount)
        else:
            # 月度不足，扣除月度 + 永久
            remaining = amount - self.credits_monthly
            self.credits_monthly = 0
            self.credits_permanent -= remaining
            return TransactionRecord(type=TransactionType.MIXED, ...)
```

---

### 2.4 application/ - 应用层 (用例编排)

**定义**: 编排领域对象和服务来完成具体用例，不包含业务规则。

**职责**:
- ✅ Commands (写操作): `DeductCreditsCommand`, `CreateProjectCommand`
- ✅ Queries (读操作): `GetUserProfileQuery`, `ListProjectsQuery`
- ✅ Event Handlers: `OnCreditsDeductedHandler`, `OnPurchaseCompletedHandler`
- ✅ 编排事务边界 (Unit of Work)
- ✅ 调用领域服务和仓储

**禁止**:
- ❌ 业务规则判断 (应在 domains 里)
- ❌ 直接操作数据库 (应通过 repository)
- ❌ 复杂计算逻辑 (应在 domains 里)

**示例**:
```python
# ✅ application/commands/billing/deduct_credits.py
@dataclass
class DeductCreditsCommand:
    user_id: str
    amount: int
    reason: str

async def handle(cmd: DeductCreditsCommand, repo: ICreditRepository) -> TransactionRecord:
    """用例编排: 扣除积分"""
    # 1. 加载聚合
    credits = await repo.get_by_user_id(cmd.user_id)

    # 2. 执行业务逻辑 (委托给聚合根)
    record = credits.deduct(cmd.amount)  # 业务规则在这里面

    # 3. 持久化
    await repo.save(credits)

    # 4. 发布事件
    await event_bus.publish(CreditsDeductedEvent(user_id=cmd.user_id, amount=cmd.amount))

    return record
```

---

### 2.5 infrastructure/ - 基础设施层 (技术实现)

**定义**: 实现 domains 层定义的仓储接口，以及其他技术基础设施。

**职责**:
- ✅ 仓储实现 (SupabaseUserRepository 实现 IUserRepository)
- ✅ 事件总线实现 (SimpleEventBus 实现 IEventBus)
- ✅ 工作单元实现 (SupabaseUnitOfWork)
- ✅ 业务相关的缓存键定义 (cache/keys.py)

**为什么 cache/keys.py 在这里?**
- `core/cache/`: 提供缓存抽象 (ICacheProvider, Redis/Memory 实现)
- `infrastructure/cache/keys.py`: 定义业务相关的缓存键 (md:config:*, md:experiment:*)
- 类比: `core/database/` 提供数据库抽象，`infrastructure/repositories/` 实现具体查询

**示例**:
```python
# ✅ infrastructure/repositories/supabase_credits_repo.py
class SupabaseCreditRepository(ICreditRepository):
    """实现领域层定义的仓储接口"""

    async def get_by_user_id(self, user_id: str) -> UserCredits:
        # Supabase 查询实现
        result = await self.client.table("user_credits").select("*").eq("user_id", user_id).single().execute()

        # 将数据库记录转换为领域对象
        return UserCredits(
            user_id=result.data["user_id"],
            credits_monthly=result.data["credits_monthly"],
            credits_permanent=result.data["credits_permanent"],
        )

    async def save(self, credits: UserCredits) -> None:
        # 持久化聚合根
        await self.client.table("user_credits").update({
            "credits_monthly": credits.credits_monthly,
            "credits_permanent": credits.credits_permanent,
        }).eq("user_id", credits.user_id).execute()

# ✅ infrastructure/cache/keys.py
PREFIX = "md:"  # Make Decodables 业务前缀

class CacheNamespace:
    """业务相关的缓存命名空间"""
    CONFIG = f"{PREFIX}config:"
    EXPERIMENT = f"{PREFIX}experiment:"
    AI = f"{PREFIX}ai:"
    RATE_LIMIT = f"{PREFIX}rl:"
    STATS = f"{PREFIX}stats:"

def config_key(key: str) -> str:
    """构建配置缓存键"""
    return f"{CacheNamespace.CONFIG}{key}"
```

---

### 2.6 api/ - API 层 (HTTP 入口)

**定义**: HTTP 路由层，处理请求验证、响应格式化，调用 application 层。

**职责**:
- ✅ 路由定义 (`@router.post("/credits/deduct")`)
- ✅ 请求参数验证 (Pydantic models)
- ✅ 响应格式化 (200/400/500 等)
- ✅ 认证授权 (调用 core/auth)
- ✅ 调用 application commands/queries

**禁止**:
- ❌ 业务逻辑 (应在 domains 里)
- ❌ 数据库查询 (应在 infrastructure 里)
- ❌ 复杂编排 (应在 application 里)

**示例**:
```python
# ✅ api/routers/credits.py
@router.post("/credits/deduct")
async def deduct_credits(
    request: DeductCreditsRequest,
    user_id: str = Depends(get_current_user_id),
    repo: ICreditRepository = Depends(get_credit_repo)
):
    """扣除积分 API"""
    # 1. 参数验证 (Pydantic 自动完成)

    # 2. 调用 application 层
    command = DeductCreditsCommand(
        user_id=user_id,
        amount=request.amount,
        reason=request.reason
    )
    result = await deduct_credits_handler(command, repo)

    # 3. 响应格式化
    return {"success": True, "transaction": result.dict()}
```

---

## 3. 目录结构标准

### 3.1 完整目录树

```
decodables/
│
├── core/                            # 框架层 (100% 复用)
│   ├── __init__.py
│   ├── auth/                        # 认证抽象
│   │   ├── __init__.py
│   │   ├── interface.py             # IAuthProvider
│   │   ├── clerk_provider.py        # Clerk 实现
│   │   └── jwt_utils.py             # JWT 工具
│   ├── cache/                       # 缓存抽象
│   │   ├── __init__.py
│   │   ├── interface.py             # ICacheProvider
│   │   ├── redis_provider.py        # Redis 实现
│   │   ├── memory_provider.py       # 内存实现
│   │   └── service.py               # CacheService (Facade)
│   ├── database/                    # 数据库抽象
│   │   ├── __init__.py
│   │   ├── interface.py             # IDatabase
│   │   ├── supabase_client.py       # Supabase 客户端
│   │   ├── retry.py                 # 重试装饰器
│   │   └── transaction.py           # 事务管理
│   ├── exceptions/                  # 统一异常
│   │   ├── __init__.py
│   │   ├── base.py                  # AppException
│   │   ├── auth.py                  # AuthException
│   │   ├── validation.py            # ValidationException
│   │   └── resource.py              # ResourceNotFoundException
│   ├── middleware/                  # 中间件
│   │   ├── __init__.py
│   │   ├── request_id.py            # Request ID
│   │   ├── logging.py               # 日志
│   │   ├── error_handler.py         # 错误处理
│   │   └── cors.py                  # CORS
│   └── utils/                       # 工具函数
│       ├── __init__.py
│       ├── datetime.py              # 时间处理
│       ├── hash.py                  # 哈希工具
│       ├── string.py                # 字符串工具
│       └── pagination.py            # 分页工具
│
├── shared/                          # 共享层 (服务抽象)
│   ├── __init__.py
│   ├── ai/                          # AI 服务
│   │   ├── __init__.py
│   │   ├── interfaces.py            # ITextAIService, IImageAIService
│   │   ├── types.py                 # AIResponse, AIMessage, AICallType
│   │   └── providers/
│   │       ├── __init__.py
│   │       ├── openai_provider.py   # OpenAI 实现
│   │       ├── fal_provider.py      # FAL 实现
│   │       └── qwen_provider.py     # Qwen 实现
│   ├── payment/                     # 支付服务
│   │   ├── __init__.py
│   │   ├── interfaces.py            # IPaymentService
│   │   ├── types.py                 # CheckoutSession, SubscriptionInfo
│   │   └── providers/
│   │       ├── __init__.py
│   │       └── stripe_provider.py   # Stripe 实现
│   ├── storage/                     # 存储服务
│   │   ├── __init__.py
│   │   ├── interfaces.py            # IStorageService
│   │   ├── types.py                 # UploadResult, FileInfo
│   │   └── providers/
│   │       ├── __init__.py
│   │       └── supabase_provider.py # Supabase Storage 实现
│   └── analytics/                   # 分析追踪
│       ├── __init__.py
│       ├── interfaces.py            # IAnalyticsProvider
│       ├── types.py                 # Event, EventProperties
│       └── providers/
│           ├── __init__.py
│           └── capi_provider.py     # CAPI 实现
│
├── domains/                         # 领域层 (业务核心)
│   │
│   ├── identity/                    # 身份域
│   │   ├── __init__.py
│   │   ├── aggregates/
│   │   │   └── user_profile.py      # UserProfile 聚合根
│   │   ├── value_objects.py         # Tier, Role, Permission
│   │   ├── repository.py            # IUserRepository (接口)
│   │   ├── service.py               # 领域服务
│   │   └── exceptions.py            # UserNotFoundException
│   │
│   ├── billing/                     # 计费域
│   │   ├── __init__.py
│   │   ├── aggregates/
│   │   │   └── user_credits.py      # UserCredits 聚合根
│   │   ├── value_objects.py         # Credits, Price, TransactionType
│   │   ├── repository.py            # ICreditRepository (接口)
│   │   ├── service.py               # 领域服务
│   │   ├── events.py                # CreditsDeductedEvent
│   │   └── exceptions.py            # InsufficientCreditsException
│   │
│   ├── creation/                    # 创作域
│   │   ├── __init__.py
│   │   ├── aggregates/
│   │   │   └── project.py           # Project 聚合根
│   │   ├── entities/
│   │   │   └── page.py              # Page 实体
│   │   ├── value_objects.py         # PaperSize, Element
│   │   ├── repository.py            # IProjectRepository (接口)
│   │   ├── service.py               # 领域服务
│   │   └── exceptions.py            # ProjectLimitExceededException
│   │
│   ├── marketplace/                 # 市场域
│   │   ├── __init__.py
│   │   ├── aggregates/
│   │   │   └── listing.py           # Listing 聚合根
│   │   ├── value_objects.py         # ModerationStatus, Category
│   │   ├── repository.py            # IMarketplaceRepository (接口)
│   │   ├── service.py               # 购买逻辑
│   │   ├── events.py                # ListingPublishedEvent
│   │   └── exceptions.py            # ListingNotApprovedException
│   │
│   ├── ai_generation/               # AI 生成域
│   │   ├── __init__.py
│   │   ├── aggregates/
│   │   │   └── generation_task.py   # GenerationTask 聚合根
│   │   ├── value_objects.py         # Prompt, ModelConfig
│   │   ├── repository.py            # IGenerationRepository (接口)
│   │   ├── service.py               # 生成逻辑
│   │   └── exceptions.py            # GenerationFailedException
│   │
│   └── platform/                    # 平台域
│       ├── __init__.py
│       ├── entities/
│       │   ├── feature_flag.py      # FeatureFlag 实体
│       │   ├── experiment.py        # Experiment 实体
│       │   └── config.py            # Config 实体
│       ├── repository.py            # IPlatformRepository (接口)
│       └── service.py               # 平台服务
│
├── application/                     # 应用层 (用例编排)
│   ├── __init__.py
│   │
│   ├── commands/                    # 写操作命令
│   │   ├── __init__.py
│   │   ├── identity/
│   │   │   └── update_profile.py    # UpdateProfileCommand
│   │   ├── billing/
│   │   │   ├── deduct_credits.py    # DeductCreditsCommand
│   │   │   └── add_credits.py       # AddCreditsCommand
│   │   ├── creation/
│   │   │   ├── create_project.py    # CreateProjectCommand
│   │   │   ├── update_project.py    # UpdateProjectCommand
│   │   │   └── delete_project.py    # DeleteProjectCommand
│   │   ├── marketplace/
│   │   │   ├── publish_listing.py   # PublishListingCommand
│   │   │   └── purchase_listing.py  # PurchaseListingCommand
│   │   └── ai_generation/
│   │       └── generate_images.py   # GenerateImagesCommand
│   │
│   ├── queries/                     # 读操作查询
│   │   ├── __init__.py
│   │   ├── identity/
│   │   │   └── get_user_profile.py  # GetUserProfileQuery
│   │   ├── creation/
│   │   │   ├── get_project.py       # GetProjectQuery
│   │   │   └── list_projects.py     # ListProjectsQuery
│   │   └── marketplace/
│   │       ├── get_listing.py       # GetListingQuery
│   │       └── list_marketplace.py  # ListMarketplaceQuery
│   │
│   └── handlers/                    # 事件处理器
│       ├── __init__.py
│       ├── on_credits_deducted.py   # OnCreditsDeductedHandler
│       ├── on_purchase_completed.py # OnPurchaseCompletedHandler
│       └── on_generation_completed.py # OnGenerationCompletedHandler
│
├── infrastructure/                  # 基础设施层 (技术实现)
│   ├── __init__.py
│   │
│   ├── repositories/                # 仓储实现
│   │   ├── __init__.py
│   │   ├── supabase_user_repo.py    # IUserRepository 实现
│   │   ├── supabase_credits_repo.py # ICreditRepository 实现
│   │   ├── supabase_project_repo.py # IProjectRepository 实现
│   │   ├── supabase_listing_repo.py # IMarketplaceRepository 实现
│   │   └── supabase_platform_repo.py # IPlatformRepository 实现
│   │
│   ├── cache/                       # 业务缓存实现
│   │   ├── __init__.py
│   │   └── keys.py                  # 业务相关缓存键定义
│   │
│   ├── event_bus/                   # 事件总线
│   │   ├── __init__.py
│   │   ├── interface.py             # IEventBus
│   │   └── simple_bus.py            # 简单实现
│   │
│   └── unit_of_work/                # 工作单元
│       ├── __init__.py
│       └── supabase_uow.py          # Supabase UoW
│
├── api/                             # API 层 (HTTP 入口)
│   ├── __init__.py
│   │
│   ├── routers/                     # 路由
│   │   ├── __init__.py
│   │   ├── users.py                 # 用户 API
│   │   ├── projects.py              # 项目 API
│   │   ├── credits.py               # 积分 API
│   │   ├── marketplace.py           # 市场 API
│   │   ├── generation.py            # AI 生成 API
│   │   ├── feature_flags.py         # Feature Flag API
│   │   ├── webhooks/
│   │   │   ├── clerk.py             # Clerk Webhook
│   │   │   └── stripe.py            # Stripe Webhook
│   │   └── admin/
│   │       ├── users.py             # 管理后台 - 用户
│   │       ├── credits.py           # 管理后台 - 积分
│   │       ├── marketplace.py       # 管理后台 - 市场
│   │       ├── feature_flags.py     # 管理后台 - Feature Flag
│   │       └── metrics.py           # 管理后台 - 指标
│   │
│   ├── dependencies.py              # API 依赖
│   └── schemas.py                   # 请求/响应 Pydantic 模型
│
├── migrations/                      # 数据库迁移
├── tests/                           # 测试
├── scripts/                         # 脚本工具
├── docs/                            # 文档
│
├── app.py                           # FastAPI 入口
├── config.py                        # 配置
└── dependencies.py                  # 全局依赖注入
```

---

## 4. 代码放置决策树

当你不确定代码应该放在哪里时，使用这个决策树:

```
┌─────────────────────────────────────────────────────────┐
│ 这段代码是什么?                                          │
└────────────┬────────────────────────────────────────────┘
             │
             ├─ 业务无关的基础设施 (任何项目都能用)
             │  └─> core/
             │      例: 认证抽象、缓存抽象、通用工具
             │
             ├─ 外部服务抽象 (AI/支付/存储)
             │  └─> shared/
             │      例: IPaymentService, StripeProvider
             │
             ├─ 业务规则和逻辑
             │  └─> domains/
             │      │
             │      ├─ 用户资料、等级、权限?  → domains/identity/
             │      ├─ 积分、订阅、交易?      → domains/billing/
             │      ├─ 项目、页面、元素?      → domains/creation/
             │      ├─ Listing、购买、审核?  → domains/marketplace/
             │      ├─ AI 生成任务、Prompt?  → domains/ai_generation/
             │      └─ Feature Flag、实验?   → domains/platform/
             │
             ├─ 用例编排 (调用领域对象完成任务)
             │  └─> application/
             │      │
             │      ├─ 写操作? → application/commands/
             │      ├─ 读操作? → application/queries/
             │      └─ 事件处理? → application/handlers/
             │
             ├─ 数据库操作、技术实现
             │  └─> infrastructure/
             │      │
             │      ├─ 实现仓储接口?       → infrastructure/repositories/
             │      ├─ 业务相关缓存键?     → infrastructure/cache/keys.py
             │      ├─ 事件总线?           → infrastructure/event_bus/
             │      └─ 工作单元?           → infrastructure/unit_of_work/
             │
             └─ HTTP 路由、API 端点
                └─> api/routers/
                    │
                    ├─ 普通路由?   → api/routers/{domain}.py
                    ├─ Webhook?   → api/routers/webhooks/
                    └─ 管理后台?   → api/routers/admin/
```

---

## 5. 依赖规则

### 5.1 依赖方向图

```
┌──────────────────────────────────────────────────────┐
│                  依赖方向 (由外向内)                    │
├──────────────────────────────────────────────────────┤
│                                                      │
│  api/ ────────┐                                      │
│               ▼                                      │
│         application/ ────┐                           │
│                          ▼                           │
│                     domains/ ◄───── infrastructure/  │
│                          │                           │
│                          ▼                           │
│                  core/ + shared/                     │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### 5.2 依赖矩阵

| 层级 | 可以依赖 | 禁止依赖 |
|------|---------|---------|
| **core/** | 标准库、第三方框架 | 其他所有层 |
| **shared/** | core/, 标准库、第三方框架 | domains/, application/, infrastructure/, api/ |
| **domains/** | core/, shared/ (接口) | infrastructure/, application/, api/ |
| **application/** | core/, shared/, domains/ | infrastructure/ (只能依赖接口), api/ |
| **infrastructure/** | core/, shared/, domains/ (接口) | application/, api/ |
| **api/** | core/, shared/, domains/, application/, infrastructure/ (通过 DI) | 无 |

### 5.3 关键规则

1. **依赖倒置**: domains 定义接口,infrastructure 实现
   ```python
   # ✅ domains/billing/repository.py
   class ICreditRepository(ABC):
       @abstractmethod
       async def get_by_user_id(self, user_id: str) -> UserCredits:
           pass

   # ✅ infrastructure/repositories/supabase_credits_repo.py
   class SupabaseCreditRepository(ICreditRepository):
       async def get_by_user_id(self, user_id: str) -> UserCredits:
           # 实现细节...
   ```

2. **application 不直接导入 infrastructure**
   ```python
   # ❌ 错误: application 直接依赖 infrastructure
   from infrastructure.repositories.supabase_credits_repo import SupabaseCreditRepository

   # ✅ 正确: application 依赖接口,通过 DI 注入实现
   from domains.billing.repository import ICreditRepository

   async def deduct_credits(user_id: str, amount: int, repo: ICreditRepository):
       # repo 通过依赖注入传入 (可以是任何实现)
   ```

3. **domains 完全独立于技术细节**
   ```python
   # ❌ 错误: domains 导入 Supabase
   from supabase import Client

   # ✅ 正确: domains 只依赖抽象
   from domains.billing.repository import ICreditRepository
   ```

---

## 6. 文件大小指导

### 6.1 单文件 300 行指标

**原则**: 这是一个**启发式指标**，不是硬性限制。

- ✅ 超过 300 行时，审视是否需要拆分
- ✅ 如果函数职责单一、逻辑清晰，超过 300 行也可接受
- ❌ 不要为了凑 300 行而过度拆分

### 6.2 拆分建议

**检查项**:
1. 函数是否职责单一?
2. 逻辑是否过于复杂?
3. 是否有重复代码?
4. 是否有多个不相关的概念?

**拆分方式**:
```python
# 示例: user_service.py (600 行) 过大

# 拆分方案 1: 按功能拆分
user_service.py        # 用户 CRUD (200 行)
user_tier_service.py   # 等级逻辑 (150 行)
user_auth_service.py   # 认证逻辑 (150 行)

# 拆分方案 2: 按 DDD 拆分 (推荐)
domains/identity/aggregates/user_profile.py  # 聚合根 (200 行)
domains/identity/service.py                  # 领域服务 (150 行)
application/commands/identity/update_profile.py  # 用例 (100 行)
```

### 6.3 各层典型文件大小

| 层级 | 文件类型 | 典型大小 | 最大建议 |
|------|---------|---------|---------|
| **core/** | interface.py | 50-80 行 | 100 行 |
| **core/** | provider.py | 100-200 行 | 300 行 |
| **core/** | utils.py | 50-100 行 | 200 行 |
| **shared/** | interfaces.py | 80-150 行 | 200 行 |
| **shared/** | providers/*.py | 150-300 行 | 400 行 |
| **domains/** | aggregates/*.py | 150-250 行 | 350 行 |
| **domains/** | value_objects.py | 100-150 行 | 200 行 |
| **domains/** | service.py | 150-250 行 | 350 行 |
| **application/** | commands/*.py | 80-120 行 | 200 行 |
| **application/** | queries/*.py | 60-100 行 | 150 行 |
| **infrastructure/** | repositories/*.py | 150-250 行 | 350 行 |
| **api/** | routers/*.py | 100-150 行 | 250 行 |

---

## 7. 命名规范

### 7.1 文件命名

| 类型 | 命名规范 | 示例 |
|------|---------|------|
| 接口 | `interface.py` 或 `i{name}.py` | `interface.py`, `irepository.py` |
| 实现类 | `{tech}_{name}.py` | `supabase_client.py`, `redis_provider.py` |
| 聚合根 | `{domain}.py` | `user_credits.py`, `project.py` |
| 值对象 | `value_objects.py` | `value_objects.py` |
| 命令 | `{action}_{domain}.py` | `deduct_credits.py`, `create_project.py` |
| 查询 | `get_{domain}.py` / `list_{domain}.py` | `get_user_profile.py`, `list_projects.py` |
| 事件处理 | `on_{event}.py` | `on_credits_deducted.py` |

### 7.2 类命名

| 类型 | 命名规范 | 示例 |
|------|---------|------|
| 接口 | `I{Name}` | `ICacheProvider`, `IUserRepository` |
| 实现类 | `{Tech}{Name}` | `RedisCacheProvider`, `SupabaseUserRepository` |
| 聚合根 | `{Domain}` | `UserCredits`, `Project`, `Listing` |
| 值对象 | `{Concept}` | `Tier`, `Credits`, `PaperSize` |
| 命令 | `{Action}{Domain}Command` | `DeductCreditsCommand`, `CreateProjectCommand` |
| 查询 | `Get{Domain}Query` / `List{Domain}Query` | `GetUserProfileQuery`, `ListProjectsQuery` |
| 事件 | `{Domain}{Action}Event` | `CreditsDeductedEvent`, `ListingPublishedEvent` |
| 异常 | `{Domain}{Reason}Exception` | `InsufficientCreditsException` |

### 7.3 函数命名

| 类型 | 命名规范 | 示例 |
|------|---------|------|
| 查询 | `get_{resource}`, `list_{resources}` | `get_user_by_id()`, `list_projects()` |
| 创建 | `create_{resource}` | `create_project()` |
| 更新 | `update_{resource}` | `update_profile()` |
| 删除 | `delete_{resource}` | `delete_project()` |
| 业务动作 | `{action}_{object}` | `deduct_credits()`, `publish_listing()` |
| 验证 | `validate_{subject}`, `check_{condition}` | `validate_credits()`, `check_tier_access()` |
| 转换 | `to_{format}`, `from_{source}` | `to_dict()`, `from_db_record()` |

---

## 8. 常见场景示例

### 8.1 场景 1: 添加新的业务规则

**需求**: 添加 "VIP 用户 AI 生成有 20% 折扣" 规则

**决策流程**:
1. 这是业务规则 → **domains/**
2. 与积分扣除相关 → **domains/billing/**
3. 修改聚合根 → **domains/billing/aggregates/user_credits.py**

**实现**:
```python
# domains/billing/aggregates/user_credits.py
@dataclass
class UserCredits:
    user_id: str
    tier: Tier
    credits_monthly: int
    credits_permanent: int

    def deduct_for_ai_generation(self, base_cost: int) -> TransactionRecord:
        """AI 生成扣费 (VIP 用户 20% 折扣)"""
        # 业务规则: VIP 用户有折扣
        actual_cost = base_cost
        if self.tier == Tier.PRO:
            actual_cost = int(base_cost * 0.8)  # 20% 折扣

        return self.deduct(actual_cost)
```

---

### 8.2 场景 2: 集成新的 AI 服务商

**需求**: 添加对 Anthropic Claude 的支持

**决策流程**:
1. 这是外部服务 → **shared/**
2. AI 服务 → **shared/ai/**
3. 新增提供商 → **shared/ai/providers/anthropic_provider.py**

**实现**:
```python
# 1. shared/ai/providers/anthropic_provider.py
from shared.ai.interfaces import ITextAIService
from shared.ai.types import AIResponse

class AnthropicTextProvider(ITextAIService):
    """Anthropic Claude 实现"""

    async def chat_completion(self, messages, model="claude-3-sonnet", **kwargs) -> AIResponse:
        # 调用 Anthropic API...
        pass

    def get_available_models(self) -> List[str]:
        return ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"]

# 2. shared/ai/providers/__init__.py
from .anthropic_provider import AnthropicTextProvider

__all__ = [
    # ... 其他 providers
    "AnthropicTextProvider",
]
```

---

### 8.3 场景 3: 添加新的 API 端点

**需求**: 添加 "获取用户积分历史" API

**决策流程**:
1. 这是 HTTP 端点 → **api/routers/**
2. 积分相关 → **api/routers/credits.py**
3. 需要查询用例 → **application/queries/billing/get_credit_history.py**
4. 需要仓储方法 → **domains/billing/repository.py** + **infrastructure/repositories/supabase_credits_repo.py**

**实现**:
```python
# 1. domains/billing/repository.py (定义接口)
class ICreditRepository(ABC):
    @abstractmethod
    async def get_transaction_history(self, user_id: str, limit: int) -> List[TransactionRecord]:
        pass

# 2. infrastructure/repositories/supabase_credits_repo.py (实现)
class SupabaseCreditRepository(ICreditRepository):
    async def get_transaction_history(self, user_id: str, limit: int) -> List[TransactionRecord]:
        result = await self.client.table("credit_transactions") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()

        return [TransactionRecord.from_dict(r) for r in result.data]

# 3. application/queries/billing/get_credit_history.py (用例)
@dataclass
class GetCreditHistoryQuery:
    user_id: str
    limit: int = 20

async def handle(query: GetCreditHistoryQuery, repo: ICreditRepository) -> List[TransactionRecord]:
    return await repo.get_transaction_history(query.user_id, query.limit)

# 4. api/routers/credits.py (API 端点)
from application.queries.billing.get_credit_history import GetCreditHistoryQuery, handle as get_history

@router.get("/credits/history")
async def get_credit_history(
    user_id: str = Depends(get_current_user_id),
    limit: int = Query(20, ge=1, le=100),
    repo: ICreditRepository = Depends(get_credit_repo)
):
    query = GetCreditHistoryQuery(user_id=user_id, limit=limit)
    history = await get_history(query, repo)
    return {"transactions": [t.dict() for t in history]}
```

---

### 8.4 场景 4: 添加缓存

**需求**: 给 "用户资料查询" 添加缓存

**决策流程**:
1. 缓存键是业务相关 → **infrastructure/cache/keys.py**
2. 缓存逻辑在仓储实现 → **infrastructure/repositories/supabase_user_repo.py**

**实现**:
```python
# 1. infrastructure/cache/keys.py (定义缓存键)
def user_profile_key(user_id: str) -> str:
    """用户资料缓存键"""
    return f"{CacheNamespace.USER}profile:{user_id}"

# 2. infrastructure/repositories/supabase_user_repo.py (使用缓存)
from core.cache import cache_service
from infrastructure.cache.keys import user_profile_key

class SupabaseUserRepository(IUserRepository):
    async def get_by_id(self, user_id: str) -> Optional[UserProfile]:
        # 1. 尝试从缓存获取
        cache_key = user_profile_key(user_id)
        cached = await cache_service.get(cache_key)
        if cached:
            return UserProfile.from_dict(json.loads(cached))

        # 2. 缓存未命中，查询数据库
        result = await self.client.table("users").select("*").eq("id", user_id).single().execute()
        if not result.data:
            return None

        profile = UserProfile.from_dict(result.data)

        # 3. 写入缓存
        await cache_service.set(cache_key, json.dumps(profile.dict()), ttl=300)

        return profile
```

---

## 9. 总结速查表

### 9.1 快速决策表

| 我要做什么? | 放在哪里? |
|------------|---------|
| 添加通用工具函数 (任何项目都能用) | `core/utils/` |
| 添加认证、缓存、数据库抽象 | `core/` |
| 集成新的 AI/支付/存储服务 | `shared/{service}/providers/` |
| 添加业务规则 (积分扣除、等级判断) | `domains/{domain}/` |
| 添加新用例 (创建项目、购买 Asset) | `application/commands/` 或 `application/queries/` |
| 实现数据库查询逻辑 | `infrastructure/repositories/` |
| 定义业务相关缓存键 | `infrastructure/cache/keys.py` |
| 添加 API 端点 | `api/routers/` |
| 添加 Webhook 处理 | `api/routers/webhooks/` |

### 9.2 核心原则速查

```
✅ core/ 必须 100% 业务无关
✅ shared/ 提供服务抽象，接口通用但可能包含业务配置
✅ domains/ 封装业务规则，不依赖技术细节
✅ application/ 编排用例，不包含业务逻辑
✅ infrastructure/ 实现技术细节，依赖 domains 接口
✅ api/ 只做参数验证和响应格式化

❌ domains/ 不能导入 infrastructure/
❌ application/ 不能直接导入 infrastructure/ 实现
❌ 业务逻辑不能放在 api/ 或 application/
❌ 技术细节不能放在 domains/
❌ 业务相关代码不能放在 core/
```

---

## 附录 A: 检查清单

在提交代码前，使用这个清单验证:

- [ ] 文件放在正确的层级?
- [ ] 依赖方向符合规则?
- [ ] 业务逻辑在 domains 里?
- [ ] 技术实现在 infrastructure 里?
- [ ] 用例编排在 application 里?
- [ ] API 只做参数验证和响应格式化?
- [ ] core/ 没有业务逻辑?
- [ ] 文件大小合理? (超过 300 行审视拆分)
- [ ] 命名符合规范?
- [ ] 有对应的测试?

---

**文档版本**: v3.1
**最后更新**: 2026-01-08
**维护者**: Make Decodables Team
