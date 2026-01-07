# Make Decodables 系统重构方案 v2

> **版本**: v2.0  
> **日期**: 2026-01-06  
> **架构**: 三层架构 + 轻量级 DDD 融合

---

## 目录

1. [架构概览](#1-架构概览)
2. [后端架构设计](#2-后端架构设计)
3. [前端架构设计](#3-前端架构设计)
4. [Feature Flag 系统](#4-feature-flag-系统)
5. [Theme 主题系统](#5-theme-主题系统)
6. [Onboarding 新手引导](#6-onboarding-新手引导)
7. [登录注册方案](#7-登录注册方案)
8. [迁移计划](#8-迁移计划)
9. [验收标准](#9-验收标准)

---

## 1. 架构概览

### 1.1 设计理念

```
┌─────────────────────────────────────────────────────────────────┐
│                      架构设计理念                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  三层架构 (复用性)              轻量级 DDD (业务表达)             │
│  ┌─────────────────┐           ┌─────────────────┐             │
│  │ core (100%复用) │           │ 领域划分        │             │
│  │ shared (结构复用)│    ＋     │ 聚合根/值对象    │             │
│  │ business (业务) │           │ 仓储模式        │             │
│  └─────────────────┘           │ 领域服务        │             │
│                                └─────────────────┘             │
│                          ↓                                      │
│              ┌─────────────────────────────────────┐           │
│              │         融合架构                     │           │
│              │  • 框架层与业务层清晰分离             │           │
│              │  • 业务逻辑按领域组织                │           │
│              │  • 规则内聚在聚合内                  │           │
│              │  • 数据访问通过仓储抽象              │           │
│              └─────────────────────────────────────┘           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 核心原则

| 原则 | 要求 | 验证方式 |
|------|------|----------|
| **单文件 ≤300 行** | 强制执行 | CI 检查 |
| **框架层 100% 复用** | core/ 可直接用于新项目 | 无业务代码 |
| **业务规则内聚** | 聚合根封装不变量 | 代码审查 |
| **依赖倒置** | 领域层不依赖基础设施 | 仓储接口 |
| **测试覆盖 ≥60%** | 核心逻辑必测 | Coverage 报告 |

### 1.3 领域划分

```
┌─────────────────────────────────────────────────────────────────┐
│                    业务领域划分                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Identity   │  │   Billing   │  │  Creation   │             │
│  │   身份域     │  │   计费域    │  │   创作域     │             │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤             │
│  │ 聚合:       │  │ 聚合:       │  │ 聚合:       │             │
│  │ • User      │  │ • UserCredits│ │ • Project   │             │
│  │             │  │             │  │             │             │
│  │ 值对象:     │  │ 值对象:     │  │ 值对象:     │             │
│  │ • Tier      │  │ • Credits   │  │ • PaperSize │             │
│  │ • Role      │  │ • Price     │  │ • Element   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Marketplace │  │     AI      │  │  Platform   │             │
│  │   市场域     │  │  生成域     │  │   平台域     │             │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤             │
│  │ 聚合:       │  │ 聚合:       │  │ 实体:       │             │
│  │ • Listing   │  │ • GenTask   │  │ • FeatureFlag│            │
│  │             │  │             │  │ • Experiment │            │
│  │ 值对象:     │  │ 值对象:     │  │ • Config     │            │
│  │ • Moderation│  │ • Prompt    │  │             │             │
│  │   Status    │  │ • ModelConfig│ │             │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 后端架构设计

### 2.1 目录结构

```
decodables/
│
├── 🔷 core/                            # 框架层 (100% 复用)
│   ├── __init__.py
│   │
│   ├── auth/                           # 认证抽象
│   │   ├── __init__.py
│   │   ├── interface.py               # IAuthProvider (<80 行)
│   │   ├── clerk_provider.py          # Clerk 实现 (<200 行)
│   │   └── jwt_utils.py               # JWT 工具 (<100 行)
│   │
│   ├── cache/                          # 缓存服务
│   │   ├── __init__.py
│   │   ├── interface.py               # ICacheProvider (<50 行)
│   │   ├── redis_provider.py          # Redis 实现 (<150 行)
│   │   └── memory_provider.py         # 内存实现 (<100 行)
│   │
│   ├── database/                       # 数据库抽象
│   │   ├── __init__.py
│   │   ├── interface.py               # IDatabase (<50 行)
│   │   ├── supabase_client.py         # Supabase 客户端 (<150 行)
│   │   └── transaction.py             # 事务管理 (<100 行)
│   │
│   ├── feature_flag/                   # Feature Flag 系统
│   │   ├── __init__.py
│   │   ├── types.py                   # 类型定义 (<100 行)
│   │   ├── interface.py               # IFeatureFlagProvider (<80 行)
│   │   ├── evaluator.py               # 统一评估引擎 (<200 行)
│   │   ├── service.py                 # Facade 服务 (<150 行)
│   │   └── providers/
│   │       ├── self_hosted.py         # 自建实现 (<250 行)
│   │       └── growthbook.py          # GrowthBook (<150 行)
│   │
│   ├── exceptions/                     # 统一异常
│   │   ├── __init__.py
│   │   ├── base.py                    # 基础异常类 (<80 行)
│   │   ├── auth.py                    # 认证异常 (<50 行)
│   │   ├── validation.py              # 验证异常 (<50 行)
│   │   └── resource.py                # 资源异常 (<50 行)
│   │
│   ├── middleware/                     # 中间件
│   │   ├── __init__.py
│   │   ├── request_id.py              # 请求 ID (<50 行)
│   │   ├── logging.py                 # 日志 (<80 行)
│   │   └── error_handler.py           # 错误处理 (<100 行)
│   │
│   └── utils/                          # 工具函数
│       ├── __init__.py
│       ├── datetime.py                # 时间处理 (<100 行)
│       ├── hash.py                    # 哈希工具 (<50 行)
│       └── validators.py              # 通用验证 (<100 行)
│
├── 🔸 shared/                          # 共享层 (结构复用)
│   ├── __init__.py
│   │
│   ├── ai/                             # AI 服务
│   │   ├── __init__.py
│   │   ├── interface.py               # IAIProvider (<80 行)
│   │   ├── unified_service.py         # 统一入口 (<200 行)
│   │   ├── model_config.py            # 模型配置 (<150 行)
│   │   └── adapters/
│   │       ├── base.py                # 适配器基类 (<100 行)
│   │       ├── openai.py              # OpenAI (<200 行)
│   │       └── fal.py                 # FAL (<200 行)
│   │
│   ├── payment/                        # 支付服务
│   │   ├── __init__.py
│   │   ├── interface.py               # IPaymentProvider (<80 行)
│   │   ├── stripe_provider.py         # Stripe (<250 行)
│   │   └── webhook_handler.py         # Webhook (<200 行)
│   │
│   ├── storage/                        # 存储服务
│   │   ├── __init__.py
│   │   ├── interface.py               # IStorageProvider (<50 行)
│   │   └── supabase_storage.py        # Supabase Storage (<200 行)
│   │
│   └── analytics/                      # 分析追踪
│       ├── __init__.py
│       ├── interface.py               # IAnalyticsProvider (<50 行)
│       ├── tracker.py                 # 事件追踪 (<150 行)
│       └── capi.py                    # CAPI 服务 (<200 行)
│
├── 🔶 domains/                         # 领域层 (业务核心)
│   │
│   ├── identity/                       # 身份域
│   │   ├── __init__.py
│   │   ├── aggregates/
│   │   │   └── user.py                # User 聚合根 (<200 行)
│   │   ├── value_objects.py           # Tier, Role (<100 行)
│   │   ├── repository.py              # IUserRepository (<80 行)
│   │   ├── service.py                 # 领域服务 (<200 行)
│   │   └── exceptions.py              # (<50 行)
│   │
│   ├── billing/                        # 计费域
│   │   ├── __init__.py
│   │   ├── aggregates/
│   │   │   └── user_credits.py        # UserCredits 聚合根 (<250 行)
│   │   ├── value_objects.py           # Credits, Price, TransactionType (<150 行)
│   │   ├── repository.py              # ICreditsRepository (<100 行)
│   │   ├── service.py                 # 领域服务 (<200 行)
│   │   ├── events.py                  # 领域事件 (<80 行)
│   │   └── exceptions.py              # (<50 行)
│   │
│   ├── creation/                       # 创作域
│   │   ├── __init__.py
│   │   ├── aggregates/
│   │   │   └── project.py             # Project 聚合根 (<250 行)
│   │   ├── entities/
│   │   │   └── page.py                # Page 实体 (<150 行)
│   │   ├── value_objects.py           # PaperSize, Element (<150 行)
│   │   ├── repository.py              # IProjectRepository (<100 行)
│   │   ├── service.py                 # (<200 行)
│   │   └── exceptions.py              # (<50 行)
│   │
│   ├── marketplace/                    # 市场域
│   │   ├── __init__.py
│   │   ├── aggregates/
│   │   │   └── listing.py             # Listing 聚合根 (<250 行)
│   │   ├── value_objects.py           # ModerationStatus (<100 行)
│   │   ├── repository.py              # IMarketplaceRepository (<100 行)
│   │   ├── service.py                 # 购买逻辑 (<250 行)
│   │   ├── events.py                  # (<80 行)
│   │   └── exceptions.py              # (<50 行)
│   │
│   ├── ai_generation/                  # AI 生成域
│   │   ├── __init__.py
│   │   ├── aggregates/
│   │   │   └── generation_task.py     # 生成任务 (<200 行)
│   │   ├── value_objects.py           # Prompt, ModelConfig (<100 行)
│   │   ├── repository.py              # (<80 行)
│   │   ├── service.py                 # (<250 行)
│   │   └── exceptions.py              # (<50 行)
│   │
│   └── platform/                       # 平台域
│       ├── __init__.py
│       ├── entities/
│       │   ├── feature_flag.py        # (<150 行)
│       │   └── experiment.py          # (<150 行)
│       ├── repository.py              # (<100 行)
│       └── service.py                 # (<200 行)
│
├── 🔶 application/                     # 应用层 (用例编排)
│   ├── __init__.py
│   │
│   ├── commands/                       # 写操作命令
│   │   ├── __init__.py
│   │   ├── identity/
│   │   │   └── update_profile.py      # (<100 行)
│   │   ├── billing/
│   │   │   ├── deduct_credits.py      # (<100 行)
│   │   │   └── add_credits.py         # (<100 行)
│   │   ├── creation/
│   │   │   ├── create_project.py      # (<120 行)
│   │   │   ├── update_project.py      # (<120 行)
│   │   │   └── delete_project.py      # (<80 行)
│   │   ├── marketplace/
│   │   │   ├── publish_listing.py     # (<120 行)
│   │   │   └── purchase_listing.py    # (<150 行)
│   │   └── ai_generation/
│   │       └── generate_images.py     # (<150 行)
│   │
│   ├── queries/                        # 读操作查询
│   │   ├── __init__.py
│   │   ├── identity/
│   │   │   └── get_user_profile.py    # (<80 行)
│   │   ├── creation/
│   │   │   ├── get_project.py         # (<80 行)
│   │   │   └── list_projects.py       # (<100 行)
│   │   └── marketplace/
│   │       ├── get_listing.py         # (<80 行)
│   │       └── list_marketplace.py    # (<100 行)
│   │
│   └── event_handlers/                 # 事件处理器
│       ├── __init__.py
│       ├── on_credits_deducted.py     # (<80 行)
│       ├── on_purchase_completed.py   # (<100 行)
│       └── on_generation_completed.py # (<80 行)
│
├── 🔸 infrastructure/                  # 基础设施层 (仓储实现)
│   ├── __init__.py
│   │
│   ├── repositories/                   # 仓储实现
│   │   ├── __init__.py
│   │   ├── supabase_user_repo.py      # (<200 行)
│   │   ├── supabase_credits_repo.py   # (<200 行)
│   │   ├── supabase_project_repo.py   # (<250 行)
│   │   ├── supabase_listing_repo.py   # (<200 行)
│   │   └── supabase_flag_repo.py      # (<200 行)
│   │
│   ├── event_bus/                      # 事件总线
│   │   ├── __init__.py
│   │   ├── interface.py               # IEventBus (<50 行)
│   │   └── simple_bus.py              # 简单实现 (<100 行)
│   │
│   └── unit_of_work/                   # 工作单元
│       ├── __init__.py
│       └── supabase_uow.py            # (<150 行)
│
├── 🔶 api/                             # API 层 (HTTP 入口)
│   ├── __init__.py
│   │
│   ├── routers/                        # 路由
│   │   ├── __init__.py
│   │   ├── users.py                   # (<150 行)
│   │   ├── projects.py                # (<150 行)
│   │   ├── credits.py                 # (<120 行)
│   │   ├── marketplace.py             # (<150 行)
│   │   ├── generation.py              # (<150 行)
│   │   ├── feature_flags.py           # (<120 行)
│   │   ├── webhooks/
│   │   │   ├── clerk.py               # (<150 行)
│   │   │   └── stripe.py              # (<200 行)
│   │   └── admin/
│   │       ├── users.py               # (<120 行)
│   │       ├── credits.py             # (<120 行)
│   │       ├── marketplace.py         # (<120 行)
│   │       ├── feature_flags.py       # (<150 行)
│   │       └── metrics.py             # (<150 行)
│   │
│   ├── schemas/                        # 请求/响应模型
│   │   ├── __init__.py
│   │   ├── common.py                  # 通用模型 (<80 行)
│   │   ├── users.py                   # (<100 行)
│   │   ├── projects.py                # (<120 行)
│   │   ├── marketplace.py             # (<100 行)
│   │   └── generation.py              # (<80 行)
│   │
│   └── dependencies/                   # API 依赖
│       ├── __init__.py
│       ├── auth.py                    # 认证依赖 (<100 行)
│       └── pagination.py              # 分页依赖 (<50 行)
│
├── migrations/                         # 数据库迁移
├── tests/                              # 测试
│   ├── conftest.py
│   ├── unit/
│   │   └── domains/
│   ├── integration/
│   └── e2e/
│
├── app.py                              # FastAPI 入口 (<100 行)
├── config.py                           # 配置 (<100 行)
├── dependencies.py                     # 全局依赖注入 (<150 行)
└── container.py                        # DI 容器 (<200 行)
```

### 2.2 层级职责与依赖规则

```
┌─────────────────────────────────────────────────────────────────┐
│                      依赖方向 (由外向内)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  api/ → application/ → domains/ ← infrastructure/              │
│                            ↓                                    │
│                    core/ + shared/                              │
│                                                                 │
│  依赖规则:                                                      │
│  • domains/ 不依赖 infrastructure/ (依赖倒置)                   │
│  • domains/ 定义仓储接口，infrastructure/ 实现                  │
│  • application/ 编排领域服务，不包含业务规则                    │
│  • api/ 只做参数验证和响应格式化                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 现有代码迁移映射

| 现有文件 | 迁移到 | 说明 |
|----------|--------|------|
| `services/user_service.py` | `domains/identity/` + `application/` | 拆分 |
| `services/credit_service.py` | `domains/billing/` | 聚合化 |
| `services/project_service.py` | `domains/creation/` | 聚合化 |
| `services/marketplace_service.py` | `domains/marketplace/` | 聚合化 |
| `services/ai/` | `shared/ai/` | 保留适配器 |
| `services/cache_service.py` | `core/cache/` | 框架层 |
| `routers/*.py` | `api/routers/` | 调用 application |
| `exceptions/` | `core/exceptions/` + `domains/*/exceptions.py` | 拆分 |

---

## 3. 前端架构设计

### 3.1 目录结构

```
decodables-fe/
│
├── 🔷 @core/                           # 框架层 (100% 复用)
│   ├── providers/                      # ThemeProvider, FeatureFlagProvider
│   ├── hooks/                          # 通用 Hooks
│   ├── components/ui/                  # shadcn/ui
│   ├── feature-flags/                  # Feature Flag 模块
│   ├── theme/                          # 主题系统
│   ├── onboarding/                     # 新手引导
│   ├── api/                            # HTTP 客户端
│   └── utils/                          # 工具函数
│
├── 🔸 @shared/                         # 共享层
│   ├── auth/                           # 认证模块
│   ├── analytics/                      # 分析追踪
│   └── notifications/                  # 通知
│
├── 🔶 @business/                       # 业务层
│   ├── domains/                        # 前端领域类型
│   │   ├── user/types.ts
│   │   ├── project/types.ts
│   │   └── billing/types.ts
│   ├── stores/                         # Zustand Stores (拆分)
│   │   ├── user/
│   │   │   ├── state.ts
│   │   │   ├── actions.ts
│   │   │   └── selectors.ts
│   │   └── editor/
│   ├── hooks/                          # 业务 Hooks
│   ├── services/                       # API 服务
│   ├── components/                     # 业务组件
│   └── onboarding/                     # 引导配置
│
└── app/                                # Next.js App Router
```

### 3.2 Store 拆分原则

| 原则 | 说明 |
|------|------|
| 单文件 ≤150 行 | state/actions/selectors 分离 |
| 选择性订阅 | 使用 selector 避免不必要重渲染 |
| 持久化策略 | 明确哪些字段需要 persist |

---

## 4. Feature Flag 系统

> 详细设计见: `Feature-Flag-Experiments-Unified-Design.md`

**核心决策**:
- 方案 C: Feature Flag 为基础，Experiments 扩展
- 统一评估引擎
- 可切换 Provider (自建/GrowthBook/Unleash)

---

## 5. Theme 主题系统

### 5.1 设计原则

| 原则 | 实现 |
|------|------|
| CSS 变量驱动 | 运行时切换 |
| 配置化 | 新主题只需配置文件 |
| 时间调度 | 节日自动切换 |

### 5.2 主题结构

```typescript
interface Theme {
  id: string;
  name: string;
  colors: {
    primary: string;
    success: string;
    background: string;
    text: string;
    // ...
  };
  schedule?: {
    startDate: string;
    endDate: string;
  };
}
```

---

## 6. Onboarding 新手引导

### 6.1 功能

| 功能 | 说明 |
|------|------|
| Welcome Tour | 新用户自动触发 |
| Editor Tour | 编辑器功能引导 |
| Checklist | 新手任务清单 |

### 6.2 触发条件

```typescript
trigger: {
  type: 'auto',
  isNewUser: true,
  newUserDays: 7,
  requireNotCompleted: ['welcome_tour'],
}
```

---

## 7. 登录注册方案

**决策**: 继续使用 Clerk，抽象接口便于未来切换

```typescript
// @shared/auth/interface.ts
interface IAuthProvider {
  getCurrentUser(): Promise<User | null>;
  signIn(): Promise<void>;
  signOut(): Promise<void>;
  getToken(): Promise<string | null>;
}
```

---

## 8. 迁移计划

### 8.1 时间线

| 周次 | 内容 |
|------|------|
| Week 1-2 | core/ 层 + domains/ 骨架 + Feature Flag |
| Week 3 | billing/creation/marketplace 域迁移 |
| Week 4 | application/ + infrastructure/ |
| Week 5 | 前端迁移 + Store 拆分 |
| Week 6 | Theme + Onboarding + 测试 |

### 8.2 检查清单

| 阶段 | 验收标准 |
|------|----------|
| core/ 迁移 | 测试通过，无业务代码 |
| domains/ 迁移 | 聚合逻辑正确，仓储接口定义 |
| application/ | 用例编排正确 |
| infrastructure/ | 仓储实现，数据正确 |
| 前端迁移 | 页面功能正常 |

---

## 9. 验收标准

### 9.1 代码质量

| 指标 | 标准 |
|------|------|
| 单文件行数 | ≤300 行 |
| 测试覆盖率 | ≥60% |
| TypeScript | 100% |

### 9.2 功能验收

| 功能 | 标准 |
|------|------|
| 积分扣费 | 先月度后永久 |
| Feature Flag | 白名单、百分比、规则 |
| Theme | 热切换、持久化 |
| Onboarding | 自动触发、进度保存 |

---

**方案已确认，请告诉我继续讨论哪些问题！**
