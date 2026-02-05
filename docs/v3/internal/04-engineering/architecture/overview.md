# 架构总览

> **同步范围**: [fullstack]
> **状态**: 🟢 已验证
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: 代码结构分析, v2/01-architecture/

---

## 一、设计目标

### 1.1 核心目标

1. **可维护性**: 代码结构清晰，职责边界明确
2. **可扩展性**: 新功能易于添加，不影响现有模块
3. **可测试性**: 业务逻辑可独立测试
4. **性能**: 响应迅速，资源占用合理

### 1.2 架构原则

| 原则 | 说明 |
|------|------|
| **分层架构** | 清晰的层级划分，依赖方向单一 |
| **DDD 轻量化** | 领域驱动设计的核心概念，不过度设计 |
| **前后端分离** | 独立部署，API 通信 |
| **代码优于配置** | 类型安全，编译时检查 |

---

## 二、系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Client Layer                               │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                      Web Browser                              │    │
│  │  Desktop (Chrome/Safari/Firefox/Edge)  Mobile (iOS/Android)  │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend (Vercel)                            │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    Next.js 16 (App Router)                    │    │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  │    │
│  │  │   @core   │  │  @shared  │  │ @business │  │    app    │  │    │
│  │  │  框架层   │  │  共享层   │  │  业务层   │  │  页面层   │  │    │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘  │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ REST API
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Backend (Railway)                            │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    FastAPI + Python 3.12                      │    │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  │    │
│  │  │    api    │  │application│  │  domains  │  │  infra    │  │    │
│  │  │  路由层   │  │  应用层   │  │  领域层   │  │  基础设施 │  │    │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘  │    │
│  │  ┌───────────────────────────┐  ┌───────────────────────────┐│    │
│  │  │          core             │  │          shared           ││    │
│  │  │        框架层             │  │        共享服务           ││    │
│  │  └───────────────────────────┘  └───────────────────────────┘│    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  Supabase   │  │    Redis    │  │   Stripe    │  │  AI Services│
│ PostgreSQL  │  │   Cache     │  │   Payment   │  │ OpenAI/FAL  │
│  + Storage  │  │   + Queue   │  │             │  │             │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
```

### 2.2 数据流

```
用户操作
    │
    ▼
┌─────────────────┐
│  React 组件     │  触发 Action
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Zustand Store  │  更新本地状态
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  TanStack Query │  管理服务端状态
└────────┬────────┘
         │
         ▼ HTTP Request
┌─────────────────┐
│  FastAPI Router │  路由分发
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Application    │  用例编排
│  Service        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Domain Service │  业务逻辑
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Repository     │  数据访问
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Supabase       │  数据持久化
└─────────────────┘
```

---

## 三、分层架构

### 3.1 后端分层

```
decodables/
├── api/                 # HTTP 入口层
│   ├── user/           # 用户端 API
│   └── admin/          # 管理端 API
├── application/         # 应用层（用例编排）
│   ├── commands/       # 写操作命令
│   ├── queries/        # 读操作查询
│   └── services/       # 应用服务
├── domains/             # 领域层（业务核心）
│   ├── {domain}/
│   │   ├── entity.py       # 领域实体
│   │   ├── service.py      # 领域服务
│   │   ├── repository.py   # 仓储接口
│   │   └── exceptions.py   # 领域异常
├── infrastructure/      # 基础设施层
│   ├── repositories/   # 仓储实现
│   ├── cache/          # 缓存
│   └── external/       # 外部服务
├── core/                # 框架层
│   ├── auth/           # 认证
│   ├── database/       # 数据库
│   └── exceptions/     # 异常
└── shared/              # 共享服务
    ├── ai/             # AI 服务
    ├── payment/        # 支付服务
    └── storage/        # 存储服务
```

**依赖方向**:

```
api → application → domains ← infrastructure
                       ↓
                 core + shared
```

### 3.2 前端分层

```
decodables-fe/
├── @core/               # 框架层（100% 复用）
│   ├── editor/         # 编辑器核心
│   ├── platform/       # 平台服务
│   └── utils/          # 工具函数
├── @shared/             # 共享层
│   ├── auth/           # 认证
│   ├── analytics/      # 分析
│   └── components/     # 通用组件
├── @business/           # 业务层
│   ├── editor/         # 编辑器业务
│   ├── dashboard/      # 仪表盘业务
│   ├── marketplace/    # 素材市场业务
│   └── billing/        # 计费业务
└── app/                 # 页面层 (Next.js App Router)
    ├── (user)/         # 用户端路由
    ├── (admin)/        # 管理端路由
    └── api/            # API 路由 (BFF)
```

**依赖方向**:

```
app → @business → @shared → @core
```

---

## 四、核心模式

### 4.1 Repository 模式

```python
# domains/creation/repository.py (接口)
class ProjectRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[Project]: ...
    
    @abstractmethod
    async def save(self, project: Project) -> Project: ...

# infrastructure/repositories/project_repository.py (实现)
class SupabaseProjectRepository(ProjectRepository):
    async def get_by_id(self, id: UUID) -> Optional[Project]:
        result = await self.client.table("projects").select("*").eq("id", str(id)).single().execute()
        return Project.from_dict(result.data) if result.data else None
```

### 4.2 Service 模式

```python
# domains/creation/service.py
class ProjectService:
    def __init__(self, repository: ProjectRepository):
        self.repository = repository
    
    async def create_project(self, user_id: UUID, data: CreateProjectData) -> Project:
        project = Project.create(user_id=user_id, **data.dict())
        return await self.repository.save(project)
```

### 4.3 Store 拆分模式（前端）

```typescript
// @business/editor/stores/canvas-store.ts
export const useCanvasStore = create<CanvasState>((set) => ({
  objects: [],
  selectedIds: [],
  addObject: (obj) => set((state) => ({ objects: [...state.objects, obj] })),
}));

// @business/editor/stores/history-store.ts
export const useHistoryStore = create<HistoryState>((set) => ({
  past: [],
  future: [],
  undo: () => { /* ... */ },
}));
```

---

## 五、技术选型

| 层级 | 前端 | 后端 |
|------|------|------|
| 框架 | Next.js 16.1.1 (App Router) | FastAPI 0.128.0 |
| 语言 | TypeScript 5.9 / React 19.2.3 | Python 3.12.7 / Pydantic 2.12.5 |
| 状态 | Zustand 5.0.9 (拆分式) | - |
| 编辑器 | Fabric.js 5.3.0 | - |
| 数据库 | - | Supabase (PostgreSQL) |
| 认证 | 自建 (BFF 代理) | JWT HS256 + OTP (Email) |
| 支付 | - | Stripe |
| AI | Vercel AI SDK | FAL.ai + OpenAI |
| 部署 | Vercel | Railway |

---

## 六、部署架构

### 6.1 生产环境

```
                    ┌─────────────────────────────────────┐
                    │           Cloudflare CDN            │
                    └───────────────┬─────────────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
          ▼                         ▼                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     Vercel      │     │     Railway     │     │    Supabase     │
│    Frontend     │────▶│     Backend     │────▶│    Database     │
│   (Edge SSR)    │     │   (Container)   │     │   (PostgreSQL)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
              ┌─────────┐ ┌─────────┐ ┌─────────┐
              │  Redis  │ │ Stripe  │ │   AI    │
              │ (Cache) │ │(Payment)│ │Services │
              └─────────┘ └─────────┘ └─────────┘
```

### 6.2 环境配置

| 环境 | 前端 | 后端 | 数据库 |
|------|------|------|--------|
| Development | localhost:3000 | localhost:8000 | Supabase (dev) |
| Staging | Vercel Preview | Railway (staging) | Supabase (staging) |
| Production | Vercel | Railway | Supabase (prod) |

---

## 七、相关文档

- [技术栈](../01-project/tech-stack.md)
- [后端架构](./backend.md)
- [前端架构](./frontend.md)
- [数据库设计](./database.md)

---

**END OF DOCUMENT**
