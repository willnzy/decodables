# Make Decodables 系统重构方案 v2

> **版本**: v2.1
> **日期**: 2026-01-12
> **架构**: 三层架构 + 轻量级 DDD 融合
> **更新**: v2.1 更新 Feature Flag 章节至 v1.2 规范

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
| **单文件 300 行指标** | 超过时审视拆分（启发式，非硬性限制） | 代码审查 |
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

> 📍 **完整目录结构和层级职责详见**: [backend-architecture.md](backend-architecture.md) Part 1

### 2.1 架构快速参考

**依赖方向**: `api/ → application/ → domains/ ← infrastructure/`

**核心分层**:

| 层 | 目录 | 职责 |
|----|------|------|
| 框架层 | `core/` | 100% 复用，无业务代码 |
| 共享层 | `shared/` | AI/支付/存储等跨域服务 |
| 领域层 | `domains/` | 业务核心，聚合根+领域服务 |
| 应用层 | `application/` | 用例编排，命令+查询 |
| 基础设施层 | `infrastructure/` | 仓储实现 |
| API 层 | `api/` | HTTP 入口 |

### 2.2 现有代码迁移映射

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

> **版本**: v1.2 (2026-01-12)
> **详细设计**: [feature-flag-design.md](../shared/feature-flag-design.md)

### 4.1 核心决策

| 决策 | 选择 | 说明 |
|------|------|------|
| 架构方案 | 方案 C | Feature Flag 为基础，Experiments 扩展 |
| 评估引擎 | 统一引擎 | 共享分配算法、曝光追踪 |
| Provider | 自建 | 支持未来切换 (GrowthBook/Unleash) |

### 4.2 Flag 类型

| 类型 | flag_type | 变体数 | 统计分析 | 使用场景 |
|------|-----------|--------|----------|----------|
| 布尔开关 | `boolean` | 2 (on/off) | ❌ | 功能灰度、紧急关闭 |
| 多变体 | `multivariate` | N | ❌ | 配置切换、UI 变体 |
| A/B 实验 | `experiment` | N | ✅ | 转化优化、假设验证 |

### 4.3 评估引擎流程

```
1. Check enabled           → Flag 是否启用
2. Check time window       → 时间窗口
3. Check environment       → 环境检查
4. Check allowed_tiers     → Tier 分层筛选 (v1.2)
5. Check blacklist         → 黑名单
6. Check whitelist         → 白名单 (优先)
7. Evaluate targeting      → 定向规则 (支持规则级 tiers)
8. Assign variant          → 确定性哈希分配
9. Track exposure          → 曝光追踪
```

### 4.4 v1.2 新增功能

**Tier 分层筛选**:
```json
{
  "allowed_tiers": ["t2", "t3"],  // 仅 Starter/Pro 可见
  "targeting_rules": [
    {
      "id": "rule1",
      "tiers": ["t3"],           // 规则级 Tier 筛选
      "conditions": [...],
      "variant": "treatment"
    }
  ]
}
```

### 4.5 数据库表

| 表名 | 用途 |
|------|------|
| `feature_flags` | Flag 核心配置 |
| `experiment_configs` | A/B 实验扩展配置 |
| `flag_exposures` | 曝光事件记录 |
| `experiment_results` | 实验结果聚合 |

### 4.6 API 端点

**User API**:
- `GET /api/experiments/flags` - 批量获取 Flag 状态
- `GET /api/experiments/{key}/variant` - 获取单个变体
- `POST /api/experiments/{key}/convert` - 记录转化

**Admin API**:
- `GET /api/v2/admin/feature-flags` - 列表
- `POST /api/v2/admin/feature-flags` - 创建
- `PUT /api/v2/admin/feature-flags/{id}` - 更新
- `DELETE /api/v2/admin/feature-flags/{id}` - 删除
- `GET /api/v2/admin/experiments/{key}/stats` - 实验统计

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
